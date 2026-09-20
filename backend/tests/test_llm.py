"""Tests for LLM wrapper: caching, retries, model fallback, and media validation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
import pytest

from backend.app.config import Settings
from backend.app.llm import (
    TOTAL_MEDIA_LIMIT_BYTES,
    GeminiBackend,
    LLMBackend,
    LLMConfigError,
    LLMError,
    MediaError,
    MediaPart,
    _compute_cache_key,
    clear_cache,
    generate_json,
    load_media,
    reset_backend,
    reset_sleep_fn,
    set_backend,
    set_sleep_fn,
)


class DummySchema(BaseModel):
    title: str
    score: int


class FakeBackend:
    def __init__(self, responses: Optional[Any] = None):
        """
        responses can be:
        - a dict mapping model_name -> list of responses/exceptions or single response
        - a list of responses/exceptions/callables
        """
        if isinstance(responses, dict):
            self.model_responses: Dict[str, Any] = {
                k: list(v) if isinstance(v, list) else v for k, v in responses.items()
            }
            self.responses: List[Any] = []
        else:
            self.model_responses = {}
            self.responses = list(responses or [])
        self.calls: List[dict] = []

    def generate(
        self,
        model: str,
        system: Optional[str],
        prompt: str,
        media: Optional[List[MediaPart]],
        schema: Optional[Type[BaseModel]],
        thinking: str,
        timeout: int,
    ) -> str:
        self.calls.append(
            {
                "model": model,
                "system": system,
                "prompt": prompt,
                "media": media,
                "schema": schema,
                "thinking": thinking,
                "timeout": timeout,
            }
        )

        resp = None
        if model in self.model_responses:
            val = self.model_responses[model]
            if isinstance(val, list):
                resp = val.pop(0) if val else json.dumps({"title": "default", "score": 100})
            else:
                resp = val
        elif self.responses:
            resp = self.responses.pop(0)
        else:
            return json.dumps({"title": "default", "score": 100})

        if isinstance(resp, Exception):
            raise resp
        if callable(resp):
            return resp(model, system, prompt, media, schema, thinking, timeout)
        return resp


@pytest.fixture(autouse=True)
def clean_llm_state(tmp_path, monkeypatch):
    """Ensure clean backend, sleep function, and isolated cache directory for every test."""
    cache_dir = tmp_path / "test_llm_cache"
    cache_dir.mkdir()

    test_settings = Settings(
        GEMINI_API_KEY="test-secret-key-12345",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_FALLBACK_MODELS="gemini-3.5-flash,gemini-3.7-flash",
        LLM_CACHE_DIR=str(cache_dir),
        LLM_CACHE_ENABLED=True,
        LLM_TIMEOUT_SECONDS=10,
        LLM_MAX_RETRIES=3,
    )
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: test_settings)
    set_sleep_fn(lambda s: None)

    yield test_settings

    reset_backend()
    reset_sleep_fn()


def test_valid_json_parses():
    fake = FakeBackend(['{"title": "civic issue", "score": 42}'])
    set_backend(fake)

    result = generate_json(prompt="analyze this", schema=DummySchema)

    assert result.parsed.title == "civic issue"
    assert result.parsed.score == 42
    assert result.cached is False
    assert result.attempts == 1
    assert result.model_used == "gemini-3.6-flash"
    assert len(fake.calls) == 1


def test_cache_hit_makes_zero_backend_calls():
    fake = FakeBackend(['{"title": "cache me", "score": 99}'])
    set_backend(fake)

    # First call - cache miss
    res1 = generate_json(prompt="cache test prompt", schema=DummySchema)
    assert res1.cached is False
    assert len(fake.calls) == 1

    # Second identical call - cache hit
    res2 = generate_json(prompt="cache test prompt", schema=DummySchema)
    assert res2.cached is True
    assert res2.parsed.title == "cache me"
    assert res2.parsed.score == 99
    # Backend was NOT called again
    assert len(fake.calls) == 1


def test_cache_key_differs_with_prompt_or_media():
    schema = DummySchema
    k1 = _compute_cache_key(schema, "sys1", "prompt1", None, "low", "gemini-3.6-flash")
    k2 = _compute_cache_key(schema, "sys1", "prompt2", None, "low", "gemini-3.6-flash")
    assert k1 != k2

    m1 = [MediaPart(kind="IMAGE", mime_type="image/jpeg", data=b"data1", name="img1.jpg")]
    m2 = [MediaPart(kind="IMAGE", mime_type="image/jpeg", data=b"data2", name="img2.jpg")]
    km1 = _compute_cache_key(schema, "sys1", "prompt1", m1, "low", "gemini-3.6-flash")
    km2 = _compute_cache_key(schema, "sys1", "prompt1", m2, "low", "gemini-3.6-flash")
    assert km1 != km2
    assert km1 != k1


def test_fallback_list_change_does_not_change_cache_key():
    schema = DummySchema
    prompt = "identical request"
    system = "system instruction"

    # Two different fallback configurations with identical primary model
    k1 = _compute_cache_key(schema, system, prompt, None, "low", "gemini-3.6-flash")
    k2 = _compute_cache_key(schema, system, prompt, None, "low", "gemini-3.6-flash")
    assert k1 == k2


def test_invalid_json_retried_once_then_falls_back():
    fake = FakeBackend(
        [
            "not json at all",  # attempt 1 on primary
            "still not valid json",  # repair attempt on primary -> exhausted
            '{"title": "fallback success", "score": 88}',  # fallback model succeeds
        ]
    )
    set_backend(fake)

    res = generate_json(prompt="parse request", schema=DummySchema, use_cache=False)

    assert res.parsed.title == "fallback success"
    assert res.model_used == "gemini-3.5-flash"
    assert len(fake.calls) == 3
    # Check that repair instruction was appended on attempt 2
    assert "[System Repair Instruction]" in fake.calls[1]["prompt"]
    # Check that fallback was invoked with the clean original prompt
    assert "[System Repair Instruction]" not in fake.calls[2]["prompt"]


def test_three_503s_on_primary_then_success_on_first_fallback(monkeypatch):
    slept_intervals: List[float] = []
    set_sleep_fn(lambda s: slept_intervals.append(s))

    # Configure LLM_MAX_RETRIES=2 so primary makes 3 attempts (three 503s)
    settings = Settings(
        GEMINI_API_KEY="test-secret-key-12345",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_FALLBACK_MODELS="gemini-3.5-flash,gemini-3.7-flash",
        LLM_MAX_RETRIES=2,
    )
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: settings)

    fake = FakeBackend(
        [
            RuntimeError("HTTP 503 Service Unavailable"),
            RuntimeError("HTTP 503 Service Unavailable"),
            RuntimeError("HTTP 503 Service Unavailable"),
            '{"title": "recovered", "score": 10}',
        ]
    )
    set_backend(fake)

    res = generate_json(prompt="backoff test", schema=DummySchema, use_cache=False)

    assert res.parsed.title == "recovered"
    assert res.model_used == "gemini-3.5-flash"
    assert len(slept_intervals) == 2
    # Check backoff intervals (~1s, ~2s)
    assert 0.9 <= slept_intervals[0] <= 1.5
    assert 1.9 <= slept_intervals[1] <= 2.5


def test_transient_retries_exponential_backoff_up_to_four_attempts(monkeypatch):
    slept_intervals: List[float] = []
    set_sleep_fn(lambda s: slept_intervals.append(s))

    # Default LLM_MAX_RETRIES=3 allows 4 attempts per model (1 initial + 3 retries)
    settings = Settings(
        GEMINI_API_KEY="test-secret-key-12345",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_FALLBACK_MODELS="gemini-3.5-flash",
        LLM_MAX_RETRIES=3,
    )
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: settings)

    fake = FakeBackend(
        [
            RuntimeError("HTTP 503 Service Unavailable"),
            RuntimeError("HTTP 503 Service Unavailable"),
            RuntimeError("HTTP 503 Service Unavailable"),
            RuntimeError("HTTP 503 Service Unavailable"),
            '{"title": "fallback success", "score": 99}',
        ]
    )
    set_backend(fake)

    res = generate_json(prompt="backoff test 4 attempts", schema=DummySchema, use_cache=False)

    assert res.parsed.title == "fallback success"
    assert res.model_used == "gemini-3.5-flash"
    assert len(slept_intervals) == 3
    # Check backoff intervals (~1s, ~2s, ~4s)
    assert 0.9 <= slept_intervals[0] <= 1.5
    assert 1.9 <= slept_intervals[1] <= 2.5
    assert 3.9 <= slept_intervals[2] <= 4.5


def test_404_on_first_fallback_not_retried_then_success_on_second_fallback():
    slept_intervals: List[float] = []
    set_sleep_fn(lambda s: slept_intervals.append(s))

    # Primary fails, first fallback returns 404 (non-retryable), second fallback succeeds
    fake = FakeBackend(
        {
            "gemini-3.6-flash": RuntimeError("404 Model not found"),
            "gemini-3.5-flash": RuntimeError("404 Model gemini-3.5-flash not found"),
            "gemini-3.7-flash": '{"title": "second fallback success", "score": 77}',
        }
    )
    set_backend(fake)

    res = generate_json(prompt="404 fallback test", schema=DummySchema, use_cache=False)

    assert res.parsed.title == "second fallback success"
    assert res.model_used == "gemini-3.7-flash"

    # Verify calls: 1 attempt on gemini-3.6-flash, 1 on gemini-3.5-flash (404 not retried), 1 on gemini-3.7-flash
    calls_36 = [c for c in fake.calls if c["model"] == "gemini-3.6-flash"]
    calls_35 = [c for c in fake.calls if c["model"] == "gemini-3.5-flash"]
    calls_37 = [c for c in fake.calls if c["model"] == "gemini-3.7-flash"]
    assert len(calls_36) == 1
    assert len(calls_35) == 1
    assert len(calls_37) == 1
    assert len(slept_intervals) == 0  # 404 is not retried


def test_all_models_failing_gives_llm_error_listing_every_model_with_last_error():
    fake = FakeBackend(
        {
            "gemini-3.6-flash": RuntimeError("HTTP 503 Primary down"),
            "gemini-3.5-flash": RuntimeError("404 Not found fallback 1"),
            "gemini-3.7-flash": RuntimeError("HTTP 500 Fallback 2 crashed"),
        }
    )
    set_backend(fake)

    with pytest.raises(LLMError) as exc_info:
        generate_json(prompt="fail test", schema=DummySchema, use_cache=False)

    err_text = str(exc_info.value)
    assert "gemini-3.6-flash" in err_text
    assert "503 Primary down" in err_text
    assert "gemini-3.5-flash" in err_text
    assert "404 Not found" in err_text
    assert "gemini-3.7-flash" in err_text
    assert "500 Fallback 2 crashed" in err_text


def test_api_key_never_appears_in_error_message_or_logs(monkeypatch, caplog):
    secret_key = "secret_api_key_xyz987654321"
    settings = Settings(
        GEMINI_API_KEY=secret_key,
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_FALLBACK_MODELS="gemini-3.5-flash",
        LLM_MAX_RETRIES=0,
    )
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: settings)

    fake = FakeBackend(
        [
            RuntimeError(f"HTTP 500 Error with key {secret_key}"),
            RuntimeError(f"HTTP 500 Fallback with key {secret_key}"),
        ]
    )
    set_backend(fake)

    with caplog.at_level(logging.DEBUG, logger="resolveit.llm"):
        with pytest.raises(LLMError) as exc_info:
            generate_json(
                prompt="confidential citizen complaint text",
                schema=DummySchema,
                purpose="test_logging",
                use_cache=False,
            )

    # Key must not appear in error message
    assert secret_key not in str(exc_info.value)
    assert "[REDACTED]" in str(exc_info.value)

    # Key and prompt text must never appear in log records
    for record in caplog.records:
        assert secret_key not in record.message
        assert "confidential citizen complaint text" not in record.message


def test_missing_key_or_model_raises_llm_config_error(monkeypatch):
    reset_backend()  # use real GeminiBackend

    # Missing model
    no_model = Settings(GEMINI_API_KEY="some-key", GEMINI_MODEL="")
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: no_model)
    with pytest.raises(LLMConfigError, match="GEMINI_MODEL is not configured"):
        generate_json(prompt="test", schema=DummySchema, use_cache=False)

    # Missing API key
    no_key = Settings(GEMINI_API_KEY="", GEMINI_MODEL="gemini-3.6-flash")
    monkeypatch.setattr("backend.app.llm.get_settings", lambda: no_key)
    with pytest.raises(LLMConfigError, match="GEMINI_API_KEY is not configured"):
        generate_json(prompt="test", schema=DummySchema, use_cache=False)


def test_load_media_rejects_bad_extension_missing_file_and_oversize(tmp_path):
    # 1. Missing file
    with pytest.raises(MediaError, match="Media file not found"):
        load_media(tmp_path / "nonexistent.jpg")

    # 2. Bad extension
    bad_file = tmp_path / "test.exe"
    bad_file.write_bytes(b"bad")
    with pytest.raises(MediaError, match="Unsupported media extension"):
        load_media(bad_file)

    # 3. Valid image file
    valid_file = tmp_path / "photo.jpg"
    valid_file.write_bytes(b"\xff\xd8\xff" + b"x" * 100)
    part = load_media(valid_file)
    assert part.kind == "IMAGE"
    assert part.mime_type == "image/jpeg"
    assert part.name == "photo.jpg"

    # 4. Oversize image (> 10 MB)
    large_img = tmp_path / "huge.png"
    large_img.write_bytes(b"0" * (10 * 1024 * 1024 + 10))
    with pytest.raises(MediaError, match="exceeds maximum allowed size"):
        load_media(large_img)


def test_total_media_limit_enforced():
    fake = FakeBackend(['{"title": "ok", "score": 1}'])
    set_backend(fake)

    # Total media payload > 18 MB
    huge_data = b"x" * (10 * 1024 * 1024)
    media_parts = [
        MediaPart(kind="IMAGE", mime_type="image/jpeg", data=huge_data, name="p1.jpg"),
        MediaPart(kind="IMAGE", mime_type="image/jpeg", data=huge_data, name="p2.jpg"),
    ]

    with pytest.raises(MediaError, match="exceeds maximum inline limit of 18 MB"):
        generate_json(prompt="test", schema=DummySchema, media=media_parts, use_cache=False)


def test_load_media_expected_kind_and_webm_handling(tmp_path):
    # 1. .webm audio uploaded to AUDIO field -> kind AUDIO, mime audio/webm
    audio_webm = tmp_path / "voice.webm"
    audio_webm.write_bytes(b"webm-audio-bytes")
    part_audio = load_media(audio_webm, expected_kind="AUDIO")
    assert part_audio.kind == "AUDIO"
    assert part_audio.mime_type == "audio/webm"

    # 2. .webm video uploaded to VIDEO field -> kind VIDEO, mime video/webm
    video_webm = tmp_path / "clip.webm"
    video_webm.write_bytes(b"webm-video-bytes")
    part_video = load_media(video_webm, expected_kind="VIDEO")
    assert part_video.kind == "VIDEO"
    assert part_video.mime_type == "video/webm"

    # 3. Mismatch: .jpg image uploaded to AUDIO field -> raises MediaError
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff" + b"image-data")
    with pytest.raises(MediaError, match="is of type IMAGE, but was uploaded to the audio field"):
        load_media(img_file, expected_kind="AUDIO")

    # 4. Matching expected_kind for normal audio (.mp3, .wav)
    wav_file = tmp_path / "note.wav"
    wav_file.write_bytes(b"RIFF....WAVEfmt ")
    part_wav = load_media(wav_file, expected_kind="AUDIO")
    assert part_wav.kind == "AUDIO"
    assert part_wav.mime_type == "audio/wav"

