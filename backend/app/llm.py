"""LLM wrapper for multimodal Gemini calls with caching, retries, and fallback."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import random
import time
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, Protocol, Type, TypeVar
from pydantic import BaseModel, ValidationError

from google import genai
from google.genai import types

from .clock import now as clock_now
from .config import get_settings

logger = logging.getLogger("resolveit.llm")

T = TypeVar("T", bound=BaseModel)

TOTAL_MEDIA_LIMIT_BYTES: int = 18 * 1024 * 1024  # 18 MB inline limit


class LLMError(Exception):
    """Base exception for LLM operations."""
    pass


class LLMConfigError(LLMError):
    """Raised when LLM configuration or credentials are missing or invalid."""
    pass


class MediaError(LLMError):
    """Raised when media loading fails (unsupported type, missing, or oversize)."""
    pass


@dataclass
class MediaPart:
    kind: Literal["IMAGE", "AUDIO", "VIDEO"]
    mime_type: str
    data: bytes
    name: str


@dataclass
class LLMResult(Generic[T]):
    parsed: T
    model_used: str
    cached: bool
    latency_ms: float
    attempts: int


MEDIA_WHITELIST: Dict[str, tuple[Literal["IMAGE", "AUDIO", "VIDEO"], str, int]] = {
    # Images (10 MB limit)
    ".jpg": ("IMAGE", "image/jpeg", 10 * 1024 * 1024),
    ".jpeg": ("IMAGE", "image/jpeg", 10 * 1024 * 1024),
    ".png": ("IMAGE", "image/png", 10 * 1024 * 1024),
    ".webp": ("IMAGE", "image/webp", 10 * 1024 * 1024),
    # Audio (15 MB limit)
    ".mp3": ("AUDIO", "audio/mpeg", 15 * 1024 * 1024),
    ".wav": ("AUDIO", "audio/wav", 15 * 1024 * 1024),
    ".ogg": ("AUDIO", "audio/ogg", 15 * 1024 * 1024),
    ".m4a": ("AUDIO", "audio/mp4", 15 * 1024 * 1024),
    ".aac": ("AUDIO", "audio/aac", 15 * 1024 * 1024),
    ".flac": ("AUDIO", "audio/flac", 15 * 1024 * 1024),
    ".webm": ("VIDEO", "video/webm", 15 * 1024 * 1024),
    # Video (15 MB limit)
    ".mp4": ("VIDEO", "video/mp4", 15 * 1024 * 1024),
    ".mov": ("VIDEO", "video/quicktime", 15 * 1024 * 1024),
}


def load_media(path: str | Path, expected_kind: Optional[str] = None) -> MediaPart:
    """Load and validate media file according to type and size limits."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise MediaError(f"Media file not found: {path}")

    ext = p.suffix.lower()
    if ext not in MEDIA_WHITELIST:
        supported = ", ".join(MEDIA_WHITELIST.keys())
        raise MediaError(f"Unsupported media extension '{ext}'. Supported extensions: {supported}")

    kind, mime_type, max_bytes = MEDIA_WHITELIST[ext]

    # Handle ambiguous extensions such as .webm which can be AUDIO or VIDEO
    if ext == ".webm" and expected_kind == "AUDIO":
        kind = "AUDIO"
        mime_type = "audio/webm"

    if expected_kind and kind != expected_kind:
        raise MediaError(
            f"File '{p.name}' is of type {kind}, but was uploaded to the {expected_kind.lower()} field"
        )

    size = p.stat().st_size
    if size > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        file_mb = size / (1024 * 1024)
        raise MediaError(
            f"File '{p.name}' ({file_mb:.2f} MB) exceeds maximum allowed size for {kind} ({max_mb} MB)"
        )

    data = p.read_bytes()
    return MediaPart(kind=kind, mime_type=mime_type, data=data, name=p.name)


class LLMBackend(Protocol):
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
        """Return raw JSON response string."""
        ...


class GeminiBackend:
    """Production backend using Google GenAI Python SDK."""

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
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise LLMConfigError("GEMINI_API_KEY is not configured")

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Build contents: media parts followed by prompt
        contents: List[Any] = []
        if media:
            for m in media:
                contents.append(types.Part.from_bytes(data=m.data, mime_type=m.mime_type))
        contents.append(prompt)

        # Thinking configuration
        thinking_cfg = None
        norm_thinking = thinking.lower()
        if norm_thinking != "minimal":  # NEVER use minimal
            if "gemini-3" in model.lower():
                level_map = {
                    "low": getattr(types.ThinkingLevel, "LOW", "LOW"),
                    "medium": getattr(types.ThinkingLevel, "MEDIUM", "MEDIUM"),
                    "high": getattr(types.ThinkingLevel, "HIGH", "HIGH"),
                }
                level = level_map.get(norm_thinking, getattr(types.ThinkingLevel, "LOW", "LOW"))
                thinking_cfg = types.ThinkingConfig(thinking_level=level)
            else:
                budget_map = {"low": 512, "medium": 1024, "high": 2048}
                budget = budget_map.get(norm_thinking, 512)
                thinking_cfg = types.ThinkingConfig(thinking_budget=budget)

        config_kwargs: Dict[str, Any] = {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        }
        if system:
            config_kwargs["system_instruction"] = system
        if thinking_cfg is not None:
            config_kwargs["thinking_config"] = thinking_cfg
        if schema is not None:
            config_kwargs["response_schema"] = schema

        try:
            config = types.GenerateContentConfig(**config_kwargs)
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            err_msg = str(exc).lower()
            # If response_schema was rejected for this model, fall back to injecting schema text in prompt
            if schema is not None and ("schema" in err_msg or "unsupported" in err_msg):
                schema_json = json.dumps(schema.model_json_schema(), indent=2)
                fallback_prompt = f"{prompt}\n\nRequired JSON Schema:\n{schema_json}"
                fallback_contents: List[Any] = []
                if media:
                    for m in media:
                        fallback_contents.append(types.Part.from_bytes(data=m.data, mime_type=m.mime_type))
                fallback_contents.append(fallback_prompt)

                config_kwargs.pop("response_schema", None)
                config_fallback = types.GenerateContentConfig(**config_kwargs)
                response = client.models.generate_content(
                    model=model,
                    contents=fallback_contents,
                    config=config_fallback,
                )
                return response.text or ""
            raise exc


# Injectable backend and sleep
_backend_override: Optional[LLMBackend] = None
_sleep_fn: Callable[[float], None] = time.sleep


def get_backend() -> LLMBackend:
    global _backend_override
    if _backend_override is not None:
        return _backend_override
    return GeminiBackend()


def set_backend(backend: Optional[LLMBackend]) -> None:
    global _backend_override
    _backend_override = backend


def reset_backend() -> None:
    global _backend_override
    _backend_override = None


def set_sleep_fn(fn: Callable[[float], None]) -> None:
    global _sleep_fn
    _sleep_fn = fn


def reset_sleep_fn() -> None:
    global _sleep_fn
    _sleep_fn = time.sleep


def clear_cache() -> int:
    """Delete all cached LLM responses in the cache directory."""
    settings = get_settings()
    cache_dir = Path(settings.LLM_CACHE_DIR)
    if not cache_dir.exists():
        return 0
    count = 0
    for f in cache_dir.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    return count


def _compute_cache_key(
    schema: Type[BaseModel],
    system: Optional[str],
    prompt: str,
    media: Optional[List[MediaPart]],
    thinking: str,
    primary_model: str,
) -> str:
    hasher = hashlib.sha256()
    try:
        schema_json = json.dumps(schema.model_json_schema(), sort_keys=True)
    except Exception:
        schema_json = schema.__name__
    hasher.update(schema_json.encode("utf-8"))
    hasher.update((system or "").encode("utf-8"))
    hasher.update(prompt.encode("utf-8"))
    if media:
        for m in media:
            hasher.update(hashlib.sha256(m.data).digest())
    hasher.update(thinking.encode("utf-8"))
    hasher.update(primary_model.encode("utf-8"))
    return hasher.hexdigest()


def _is_non_retryable_model_error(exc: Exception) -> bool:
    """Check if error is non-retryable for this model (HTTP 400, 404, or not found)."""
    err_str = str(exc).lower()
    type_str = exc.__class__.__name__.lower()
    status_code = getattr(exc, "code", getattr(exc, "status_code", None))
    if status_code in (400, 404):
        return True
    indicators = [
        "404", "not found", "not_found",
        "400", "bad request", "bad_request",
        "invalid argument", "invalidargument",
    ]
    return any(ind in err_str or ind in type_str for ind in indicators)


def _is_transient_error(exc: Exception) -> bool:
    """Check if error is transient (HTTP 429, 5xx, or network timeouts)."""
    err_str = str(exc).lower()
    type_str = exc.__class__.__name__.lower()
    transient_indicators = [
        "429", "500", "502", "503", "504",
        "resourceexhausted", "quota", "rate limit", "rate_limit",
        "timeout", "timed out", "connection reset", "connection refused",
        "unavailable", "internal error",
    ]
    return any(ind in err_str or ind in type_str for ind in transient_indicators)


def generate_json(
    prompt: str,
    schema: Type[T],
    *,
    system: Optional[str] = None,
    media: Optional[List[MediaPart]] = None,
    thinking: str = "low",
    purpose: str = "",
    use_cache: Optional[bool] = None,
) -> LLMResult[T]:
    """
    Execute structured LLM generation with disk caching, transient retry,
    validation repair, and model fallback.
    """
    settings = get_settings()
    backend = get_backend()

    # Enforce total media inline limit
    if media:
        total_media_size = sum(len(m.data) for m in media)
        if total_media_size > TOTAL_MEDIA_LIMIT_BYTES:
            limit_mb = TOTAL_MEDIA_LIMIT_BYTES // (1024 * 1024)
            actual_mb = total_media_size / (1024 * 1024)
            raise MediaError(
                f"Total media payload size ({actual_mb:.2f} MB) exceeds maximum inline limit of {limit_mb} MB"
            )

    primary_model = (settings.GEMINI_MODEL or "").strip()

    # Parse fallback models from GEMINI_FALLBACK_MODELS (and GEMINI_FALLBACK_MODEL)
    raw_fallbacks = (settings.GEMINI_FALLBACK_MODELS or "").split(",")
    fallback_candidates = [m.strip() for m in raw_fallbacks if m.strip()]
    if settings.GEMINI_FALLBACK_MODEL and settings.GEMINI_FALLBACK_MODEL.strip():
        for m in settings.GEMINI_FALLBACK_MODEL.split(","):
            m = m.strip()
            if m and m not in fallback_candidates:
                fallback_candidates.append(m)

    # Order: primary model first, then each fallback skipping duplicates and blanks
    models_to_try: List[str] = []
    if primary_model:
        models_to_try.append(primary_model)
    for fb in fallback_candidates:
        if fb not in models_to_try:
            models_to_try.append(fb)

    if not models_to_try:
        models_to_try = ["default"]

    # When using real GeminiBackend, model and key must be configured
    if isinstance(backend, GeminiBackend):
        if not primary_model:
            raise LLMConfigError("GEMINI_MODEL is not configured in settings")
        if not settings.GEMINI_API_KEY:
            raise LLMConfigError("GEMINI_API_KEY is not configured in settings")

    # Cache handling
    should_cache = settings.LLM_CACHE_ENABLED if use_cache is None else use_cache
    cache_key = _compute_cache_key(
        schema=schema,
        system=system,
        prompt=prompt,
        media=media,
        thinking=thinking,
        primary_model=primary_model or "default",
    )
    cache_file = Path(settings.LLM_CACHE_DIR) / f"{cache_key}.json"

    if should_cache and cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_payload = json.load(f)
            raw_text = cache_payload["raw_text"]
            model_used = cache_payload.get("model_used", primary_model or "cached")
            parsed = schema.model_validate_json(raw_text)
            logger.info(
                "LLM cache hit: purpose=%s, model=%s, cached=True, latency_ms=0.0, attempts=0",
                purpose,
                model_used,
            )
            return LLMResult(
                parsed=parsed,
                model_used=model_used,
                cached=True,
                latency_ms=0.0,
                attempts=0,
            )
        except Exception as exc:
            logger.warning("Cache read failed for key %s (bypassing): %s", cache_key, exc)

    max_attempts = max(1, settings.LLM_MAX_RETRIES + 1)
    timeout_secs = settings.LLM_TIMEOUT_SECONDS

    start_time = time.monotonic()
    total_attempts = 0
    model_failure_summaries: List[Dict[str, Any]] = []

    for model_idx, model_name in enumerate(models_to_try):
        current_prompt = prompt
        repair_attempted = False
        model_attempts = 0
        last_error: Optional[Exception] = None

        while model_attempts < max_attempts:
            model_attempts += 1
            total_attempts += 1
            try:
                raw_json = backend.generate(
                    model=model_name,
                    system=system,
                    prompt=current_prompt,
                    media=media,
                    schema=schema,
                    thinking=thinking,
                    timeout=timeout_secs,
                )

                # Validate raw output against Pydantic schema
                try:
                    parsed_obj = schema.model_validate_json(raw_json)
                except (ValidationError, ValueError, json.JSONDecodeError) as parse_exc:
                    last_error = parse_exc
                    logger.warning(
                        "LLM attempt failed: model=%s, attempt=%d, error=%s",
                        model_name,
                        model_attempts,
                        parse_exc.__class__.__name__,
                    )
                    if not repair_attempted:
                        # Retry once with repair instruction appended
                        repair_attempted = True
                        current_prompt = (
                            f"{prompt}\n\n[System Repair Instruction]: "
                            "Your previous output was invalid JSON or did not strictly conform to "
                            "the schema. Return only valid JSON conforming exactly to the schema."
                        )
                        continue
                    # Repair retry failed, skip remaining retries for this model
                    break

                # Success
                latency_ms = (time.monotonic() - start_time) * 1000.0

                # Write to cache
                if should_cache:
                    try:
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(
                                {
                                    "model_used": model_name,
                                    "created_at": clock_now().isoformat(),
                                    "raw_text": raw_json,
                                },
                                f,
                            )
                    except Exception as c_err:
                        logger.warning("Cache write failed for key %s: %s", cache_key, c_err)

                logger.info(
                    "LLM call: purpose=%s, model=%s, latency_ms=%.1f, cached=False, attempts=%d, prompt_len=%d",
                    purpose,
                    model_name,
                    latency_ms,
                    total_attempts,
                    len(prompt),
                )
                return LLMResult(
                    parsed=parsed_obj,
                    model_used=model_name,
                    cached=False,
                    latency_ms=latency_ms,
                    attempts=total_attempts,
                )

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM attempt failed: model=%s, attempt=%d, error=%s",
                    model_name,
                    model_attempts,
                    exc.__class__.__name__,
                )

                # 404 and 400 are non-retryable on that model: skip remaining retries and move straight to next model
                if _is_non_retryable_model_error(exc):
                    break

                # Transient errors: up to 4 attempts per model with exponential backoff plus random jitter (about 1s, 2s, 4s)
                if _is_transient_error(exc) and model_attempts < max_attempts:
                    backoff = float(2 ** (model_attempts - 1)) + random.uniform(0.0, 0.25)
                    _sleep_fn(backoff)
                    continue

                # Non-transient error or retries exhausted for this model
                break

        # Record this model's failure summary
        err_cls = last_error.__class__.__name__ if last_error else "UnknownError"
        err_msg = str(last_error) if last_error else "No error details"
        model_failure_summaries.append(
            {
                "model": model_name,
                "attempts": model_attempts,
                "err_class": err_cls,
                "err_msg": err_msg,
            }
        )

    # If all models and retries failed
    report_lines: List[str] = []
    for s in model_failure_summaries:
        clean_msg = s["err_msg"]
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY in clean_msg:
            clean_msg = clean_msg.replace(settings.GEMINI_API_KEY, "[REDACTED]")
        clean_msg = clean_msg[:300]
        report_lines.append(f"{s['model']} ({s['attempts']} attempts): {s['err_class']}: {clean_msg}")

    summary_str = "; ".join(report_lines)
    raise LLMError(f"LLM generation failed across all models: {summary_str}")
