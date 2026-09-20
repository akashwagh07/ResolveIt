from datetime import datetime, timezone
from backend.app.clock import advance, now, reset


def test_clock_returns_naive_datetime():
    current = now()
    assert isinstance(current, datetime)
    assert current.tzinfo is None


def test_clock_advance_moves_forward():
    reset()
    t1 = now()
    t2 = advance(2.5)  # advance 2.5 hours
    delta = (t2 - t1).total_seconds()
    # Should be at least 2.5 hours (9000 seconds)
    assert delta >= 8999
    assert delta <= 9005


def test_clock_reset():
    reset()
    advance(10.0)
    t_advanced = now()
    t_reset = reset()
    diff = (t_advanced - t_reset).total_seconds()
    # Reset should eliminate the 10 hour (36000s) offset
    assert diff >= 35900
