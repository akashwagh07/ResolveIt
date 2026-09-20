from datetime import datetime, timezone, timedelta
import time
from .config import get_settings

_process_start_utc: datetime = datetime.now(timezone.utc).replace(tzinfo=None)
_process_start_mono: float = time.monotonic()
_manual_offset_seconds: float = 0.0


def now() -> datetime:
    """Return current virtual time as a naive UTC datetime."""
    settings = get_settings()
    time_scale = float(settings.TIME_SCALE)
    elapsed_real = time.monotonic() - _process_start_mono
    scaled_elapsed = elapsed_real * time_scale
    total_offset = scaled_elapsed + _manual_offset_seconds
    return _process_start_utc + timedelta(seconds=total_offset)


def advance(hours: float) -> datetime:
    """Advance the virtual clock by a given number of hours."""
    global _manual_offset_seconds
    _manual_offset_seconds += float(hours) * 3600.0
    return now()


def reset() -> datetime:
    """Reset virtual clock to real UTC start time and clear manual offset."""
    global _process_start_utc, _process_start_mono, _manual_offset_seconds
    _process_start_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    _process_start_mono = time.monotonic()
    _manual_offset_seconds = 0.0
    return now()
