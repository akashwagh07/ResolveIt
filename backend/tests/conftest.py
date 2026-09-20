import os
from pathlib import Path
import tempfile
import pytest

# 1. Project root and session temp directory setup
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SESSION_TEMP_DIR = tempfile.TemporaryDirectory(prefix="resolveit_test_session_", ignore_cleanup_errors=True)
_TEMP_DIR_PATH = Path(_SESSION_TEMP_DIR.name).resolve()
_SESSION_TEST_DB_PATH = _TEMP_DIR_PATH / "test_resolveit.db"
_SESSION_UPLOAD_DIR = _TEMP_DIR_PATH / "uploads"
_SESSION_CACHE_DIR = _TEMP_DIR_PATH / "cache"

_SESSION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_SESSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Set environment variables BEFORE any backend imports
os.environ["DATABASE_URL"] = f"sqlite:///{_SESSION_TEST_DB_PATH.as_posix()}"
os.environ["UPLOAD_DIR"] = str(_SESSION_UPLOAD_DIR)
os.environ["LLM_CACHE_DIR"] = str(_SESSION_CACHE_DIR)
os.environ["LLM_CACHE_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "true"

# Clear cached settings if already loaded
try:
    from backend.app.config import get_settings
    get_settings.cache_clear()
except ImportError:
    pass

# Real-database tripwire baseline
_REAL_DB_PATH = _PROJECT_ROOT / "resolveit.db"
_REAL_DB_INITIAL_EXISTS = _REAL_DB_PATH.exists()
_REAL_DB_INITIAL_STAT = (
    (_REAL_DB_PATH.stat().st_size, _REAL_DB_PATH.stat().st_mtime_ns)
    if _REAL_DB_INITIAL_EXISTS
    else None
)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.clock import reset as clock_reset
from backend.app.database import Base, SessionLocal, assert_safe_for_destructive, engine, get_db
from backend.app.main import app
from backend.app.seed import seed_database


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_LIVE_LLM") != "1":
        skip_live = pytest.mark.skip(reason="Live LLM tests skipped unless RUN_LIVE_LLM=1 is set")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture(scope="session", autouse=True)
def verify_test_db_isolation():
    """Verify the module-level engine URL is inside the temp directory."""
    from backend.app.database import engine
    engine_url = str(engine.url)

    temp_dir_str = _TEMP_DIR_PATH.as_posix().lower()
    url_norm = engine_url.replace("\\", "/").lower()

    is_temp = temp_dir_str in url_norm or ":memory:" in url_norm
    if not is_temp:
        pytest.exit("refusing to run: tests are pointed at a non-temp database", returncode=1)


def pytest_sessionfinish(session, exitstatus):
    """Tripwire check: ensure real resolveit.db was not modified or created during test session."""
    if _REAL_DB_INITIAL_EXISTS:
        if not _REAL_DB_PATH.exists():
            print("\n" + "!" * 80)
            print("ERROR: Real database 'resolveit.db' was DELETED during test run!")
            print("!" * 80 + "\n")
            session.exitstatus = 1
            return
        current_stat = (_REAL_DB_PATH.stat().st_size, _REAL_DB_PATH.stat().st_mtime_ns)
        if current_stat != _REAL_DB_INITIAL_STAT:
            print("\n" + "!" * 80)
            print("ERROR: Real database 'resolveit.db' was modified during test run!")
            print(f"Initial: {_REAL_DB_INITIAL_STAT}, Current: {current_stat}")
            print("!" * 80 + "\n")
            session.exitstatus = 1
    else:
        if _REAL_DB_PATH.exists():
            print("\n" + "!" * 80)
            print("ERROR: Real database 'resolveit.db' was created during test run!")
            print("!" * 80 + "\n")
            session.exitstatus = 1

    # Dispose all connections on the test engine to release file locks on Windows
    try:
        from backend.app.database import engine
        engine.dispose()
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_engine():
    assert_safe_for_destructive(engine)
    return engine


@pytest.fixture(scope="function")
def db(test_engine):
    """Provides a clean seeded database session for each test."""
    assert_safe_for_destructive(test_engine)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    clock_reset()
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def clean_llm_state():
    """Ensure clean LLM backend, circuit breaker cooldown, clock, and sleep function for every test."""
    from backend.app.llm import reset_backend, reset_cooldown, reset_monotonic_clock, reset_sleep_fn
    reset_backend()
    reset_cooldown()
    reset_monotonic_clock()
    reset_sleep_fn()
    yield
    reset_backend()
    reset_cooldown()
    reset_monotonic_clock()
    reset_sleep_fn()

