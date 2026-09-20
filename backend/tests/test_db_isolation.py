"""Tests for database isolation, destructive safety checks, and pipeline 500 error handling."""

import io
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.database import assert_safe_for_destructive, engine
from backend.app.main import app
from backend.app.seed import seed_database
from backend.tests.test_intake import TINY_PNG


def test_engine_url_used_in_tests_is_temp_file():
    """Verify that the engine URL in tests points to a temporary directory file."""
    url = str(engine.url)
    temp_dir_str = tempfile.gettempdir().lower()
    url_norm = url.replace("\\", "/").lower()

    # Must be either inside system temp directory or :memory:
    assert (
        "temp" in url_norm
        or "tmp" in url_norm
        or temp_dir_str in url_norm
        or ":memory:" in url_norm
    ), f"Test engine URL '{url}' is not inside a temporary directory!"


def test_running_seed_leaves_real_db_untouched(db):
    """Running seed on the test database leaves real resolveit.db untouched."""
    real_db_path = PROJECT_ROOT / "resolveit.db"
    initial_stat = None
    if real_db_path.exists():
        initial_stat = (real_db_path.stat().st_size, real_db_path.stat().st_mtime_ns)

    # Run seed on test database session
    seed_database(db)

    if initial_stat is not None:
        current_stat = (real_db_path.stat().st_size, real_db_path.stat().st_mtime_ns)
        assert current_stat == initial_stat, "Real resolveit.db was modified by seed_database(db)!"


def test_assert_safe_for_destructive_refuses_non_temp_path(tmp_path, monkeypatch):
    """assert_safe_for_destructive raises RuntimeError on non-temp sqlite URLs unless ALLOW_DESTRUCTIVE_DB=1."""
    non_temp_engine = create_engine(f"sqlite:///{PROJECT_ROOT.as_posix()}/dangerous_file.db")

    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DB", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        assert_safe_for_destructive(non_temp_engine)
    assert "not in a temporary directory" in str(excinfo.value)

    # With ALLOW_DESTRUCTIVE_DB=1, it must succeed
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB", "1")
    assert_safe_for_destructive(non_temp_engine)


def test_relative_sqlite_url_resolves_consistently_regardless_of_cwd(tmp_path, monkeypatch):
    """Relative sqlite URLs resolve to the exact same absolute path regardless of current working directory."""
    expected_absolute_file = (PROJECT_ROOT / "resolveit.db").resolve()
    expected_url = f"sqlite:///{expected_absolute_file.as_posix()}"

    # Test from project root
    monkeypatch.chdir(PROJECT_ROOT)
    s1 = Settings(DATABASE_URL="sqlite:///./resolveit.db")
    assert s1.DATABASE_URL == expected_url

    # Test from backend/ folder
    backend_dir = PROJECT_ROOT / "backend"
    monkeypatch.chdir(backend_dir)
    s2 = Settings(DATABASE_URL="sqlite:///./resolveit.db")
    assert s2.DATABASE_URL == expected_url

    # Test from temp folder outside repo
    monkeypatch.chdir(tmp_path)
    s3 = Settings(DATABASE_URL="sqlite:///./resolveit.db")
    assert s3.DATABASE_URL == expected_url


def test_unexpected_pipeline_error_returns_json_500_and_deletes_uploads(tmp_path, monkeypatch):
    """Unexpected pipeline errors return 500 {"detail": "Internal error while processing the complaint"} and delete uploads."""
    client = TestClient(app)

    # Monkeypatch decide in agent2 to simulate an unexpected crash
    def crash_decide(*args, **kwargs):
        raise RuntimeError("Simulated internal pipeline failure")

    monkeypatch.setattr("backend.app.pipeline.decide", crash_decide)

    upload_dir = tmp_path / "uploads_err_test"
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_settings = Settings(UPLOAD_DIR=str(upload_dir))
    monkeypatch.setattr("backend.app.pipeline.get_settings", lambda: test_settings)

    data = {
        "citizen_name": "Error Citizen",
        "citizen_contact": "+91 9999999999",
        "latitude": "16.70",
        "longitude": "74.24",
        "text": "Complaint that will trigger unexpected pipeline error",
    }
    files = {
        "image": ("test_error_file.png", io.BytesIO(TINY_PNG), "image/png"),
    }

    resp = client.post("/api/complaints", data=data, files=files)
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal error while processing the complaint"}

    # Verify that no files remain in the upload directory
    all_saved_files = list(upload_dir.rglob("*.png"))
    assert len(all_saved_files) == 0, f"Saved files were not cleaned up: {all_saved_files}"
