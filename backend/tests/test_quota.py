"""Tests for quota handling, timeout budget, circuit breaker cooldown, and health/intake behavior."""

import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
import pytest

from backend.app.config import get_settings
from backend.app.llm import (
    LLMBackend,
    LLMError,
    LLMUnavailableError,
    MediaPart,
    clear_cache,
    generate_json,
    get_llm_status,
    reset_backend,
    reset_cooldown,
    reset_monotonic_clock,
    reset_sleep_fn,
    set_backend,
    set_monotonic_clock,
    set_sleep_fn,
)
from backend.app.models import ComplaintEvent


class DummySchema(BaseModel):
    title: str
    score: int


class SimClock:
    def __init__(self, start: float = 1000.0):
        self.current = start

    def time(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


class MockBackend(LLMBackend):
    def __init__(self, handler=None):
        self.handler = handler
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
        call_info = {"model": model, "prompt": prompt}
        self.calls.append(call_info)
        if callable(self.handler):
            return self.handler(model, len(self.calls))
        if isinstance(self.handler, Exception):
            raise self.handler
        return json.dumps({"title": "Mock Title", "score": 10})


@pytest.fixture(autouse=True)
def cleanup_llm_state():
    reset_backend()
    reset_sleep_fn()
    reset_monotonic_clock()
    reset_cooldown()
    clear_cache()
    yield
    reset_backend()
    reset_sleep_fn()
    reset_monotonic_clock()
    reset_cooldown()
    clear_cache()


def test_all_models_quota_enters_cooldown_within_budget():
    sim_clock = SimClock(1000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    backend = MockBackend(handler=Exception("429 RESOURCE_EXHAUSTED: quota exceeded"))
    set_backend(backend)

    # Call should try each model once (no retry delay <= 5s provided) and fail
    with pytest.raises(LLMError) as exc_info:
        generate_json("Test prompt", DummySchema, use_cache=False)

    assert "LLM generation failed across all models" in str(exc_info.value)
    # Should have tried 3 models (primary + 2 fallbacks), 1 attempt each
    assert len(backend.calls) == 3

    # Circuit breaker must now be in cooldown
    st, seconds_left = get_llm_status()
    assert st == "cooldown"
    assert seconds_left == 120


def test_quota_retry_with_delay_within_limit():
    sim_clock = SimClock(1000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    def handler(model, call_count):
        # Model 1 attempt 1 gives a 429 with 3s delay
        if call_count == 1:
            raise Exception("429 RESOURCE_EXHAUSTED retry after 3s")
        # All other attempts give 429 without delay
        raise Exception("429 RESOURCE_EXHAUSTED")

    backend = MockBackend(handler=handler)
    set_backend(backend)

    with pytest.raises(LLMError):
        generate_json("Test prompt", DummySchema, use_cache=False)

    # Model 1 should have had 2 attempts (1 initial + 1 retry because delay was 3s <= 5s)
    # Model 2 and 3 should each have had 1 attempt
    assert len(backend.calls) == 4
    # Clock should have advanced by 3 seconds
    assert sim_clock.current == 1003.0


def test_second_call_during_cooldown_makes_zero_backend_calls():
    sim_clock = SimClock(1000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    # Put LLM in cooldown
    backend = MockBackend(handler=Exception("429 RESOURCE_EXHAUSTED"))
    set_backend(backend)
    with pytest.raises(LLMError):
        generate_json("First call", DummySchema, use_cache=False)

    assert get_llm_status()[0] == "cooldown"
    backend.calls.clear()

    # Second call must raise LLMUnavailableError with 0 backend calls
    with pytest.raises(LLMUnavailableError) as exc_info:
        generate_json("Second call", DummySchema, use_cache=False)

    assert "quota cooldown" in str(exc_info.value)
    assert len(backend.calls) == 0


def test_cache_hit_served_during_cooldown_and_expiry():
    sim_clock = SimClock(1000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    # 1. Warm cache
    backend = MockBackend()
    set_backend(backend)
    res1 = generate_json("Cached prompt", DummySchema, use_cache=True)
    assert res1.cached is False
    assert len(backend.calls) == 1

    # 2. Enter cooldown
    backend.handler = Exception("429 RESOURCE_EXHAUSTED")
    with pytest.raises(LLMError):
        generate_json("Uncached prompt", DummySchema, use_cache=False)

    assert get_llm_status()[0] == "cooldown"

    # 3. Cache hit is served even during cooldown
    backend.calls.clear()
    cached_res = generate_json("Cached prompt", DummySchema, use_cache=True)
    assert cached_res.cached is True
    assert len(backend.calls) == 0

    # 4. Advance clock beyond 120s cooldown
    sim_clock.current += 121.0
    st, left = get_llm_status()
    assert st == "ok"
    assert left == 0

    # 5. Calls work again once cooldown expires
    backend.handler = None  # returns success JSON
    res_after = generate_json("New prompt after cooldown", DummySchema, use_cache=False)
    assert res_after.cached is False
    assert len(backend.calls) == 1


def test_health_endpoint_shows_cooldown_state(client):
    sim_clock = SimClock(2000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    # Initial health
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["llm"]["status"] == "ok"
    assert data["llm"]["cooldown_seconds_left"] == 0

    # Trigger cooldown
    backend = MockBackend(handler=Exception("429 RESOURCE_EXHAUSTED"))
    set_backend(backend)
    with pytest.raises(LLMError):
        generate_json("Trigger cooldown", DummySchema, use_cache=False)

    # Health now shows cooldown
    res2 = client.get("/api/health")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["llm"]["status"] == "cooldown"
    assert data2["llm"]["cooldown_seconds_left"] == 120


def test_plain_503_still_retries_as_before():
    sim_clock = SimClock(1000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    backend = MockBackend(handler=Exception("503 Service Unavailable"))
    set_backend(backend)

    with pytest.raises(LLMError):
        generate_json("Prompt", DummySchema, use_cache=False)

    # 503 is not a quota error: it should retry across models up to max_attempts
    assert len(backend.calls) > 3
    # Should NOT have entered cooldown
    st, _ = get_llm_status()
    assert st == "ok"


def test_intake_endpoint_returns_201_human_review_during_cooldown(client, db):
    sim_clock = SimClock(3000.0)
    set_monotonic_clock(sim_clock.time)
    set_sleep_fn(sim_clock.sleep)

    # Put LLM in cooldown
    backend = MockBackend(handler=Exception("429 RESOURCE_EXHAUSTED"))
    set_backend(backend)
    with pytest.raises(LLMError):
        generate_json("Trigger cooldown", DummySchema, use_cache=False)

    assert get_llm_status()[0] == "cooldown"

    # Submit complaint while in cooldown
    res = client.post(
        "/api/complaints",
        data={
            "citizen_name": "Quota Test User",
            "citizen_contact": "+91 9111122222",
            "text": "Pothole on road during quota cooldown",
            "latitude": 16.7112,
            "longitude": 74.2405,
            "address_text": "Tarabai Park",
        },
    )
    assert res.status_code == 201
    c_data = res.json()
    assert c_data["status"] == "HUMAN_REVIEW"
    assert c_data["needs_review"] is True

    # Verify audit event carries "AI unavailable (quota cooldown)"
    c_id = c_data["complaint_id"]
    events = db.query(ComplaintEvent).filter_by(complaint_id=c_id, actor="AGENT1", action="CLASSIFY").all()
    assert len(events) == 1
    assert events[0].reasoning == "AI unavailable (quota cooldown)"
