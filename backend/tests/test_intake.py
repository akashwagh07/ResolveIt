"""Tests for citizen intake endpoint, media uploads, secure evidence serving, and pipeline."""

import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.database import Base, SessionLocal, assert_safe_for_destructive, engine
from backend.app.llm import LLMError, reset_backend, set_backend
from backend.app.main import app
from backend.app.models import Evidence
from backend.app.seed import seed_database
from backend.tests.test_llm import FakeBackend

# Valid minimal 1x1 PNG bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _agent1_civic_json(category="ROADS", issue="POTHOLE", confidence=0.95, civic_relevance="HIGH"):
    return json.dumps({
        "civic_relevance": civic_relevance,
        "relevance_reason": "Hazardous road condition affecting public safety",
        "category": category,
        "issue": issue,
        "description": "Deep pothole on road causing dangerous driving conditions.",
        "duration_text": "2 days",
        "duration_days": 2.0,
        "size_hint": "MEDIUM",
        "context_tags": ["SAFETY_HAZARD"],
        "language": "en",
        "transcript": None,
        "translation_en": None,
        "location_mentions": ["Station Road"],
        "image_matches_text": True,
        "observations": [{"fact": "Pothole visible on road surface", "source": "IMAGE"}],
        "missing_info": [],
        "alternatives": [],
        "confidence": confidence,
        "confidence_reason": "Clear photo evidence and description",
    })


@pytest.fixture(autouse=True)
def setup_environment(tmp_path, monkeypatch):
    """Set up temporary upload directory, isolated db, and clean backend."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    test_settings = Settings(
        GEMINI_API_KEY="test-secret-key",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_FALLBACK_MODELS="gemini-3.5-flash",
        UPLOAD_DIR=str(upload_dir),
        LLM_CACHE_DIR=str(cache_dir),
        LLM_CACHE_ENABLED=False,
    )
    monkeypatch.setattr("backend.app.pipeline.get_settings", lambda: test_settings)
    monkeypatch.setattr("backend.app.routers.complaints.get_settings", lambda: test_settings)

    # Initialize tables and seed
    assert_safe_for_destructive(engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield test_settings

    reset_backend()


def test_successful_submission_with_png_and_get():
    fake = FakeBackend([_agent1_civic_json()])
    set_backend(fake)
    client = TestClient(app)

    data = {
        "citizen_name": "Ajit Mane",
        "citizen_contact": "+91 9822998877",
        "latitude": "16.7020",
        "longitude": "74.2410",
        "text": "Huge pothole outside station",
        "address_text": "Station Chowk, Kolhapur",
    }
    files = {
        "image": ("citizen_secret_personal_camera_file.png", io.BytesIO(TINY_PNG), "image/png"),
    }

    # 1. POST /api/complaints
    resp = client.post("/api/complaints", data=data, files=files)
    assert resp.status_code == 201, resp.text
    res_data = resp.json()
    complaint_id = res_data["complaint_id"]
    assert res_data["status"] == "CLASSIFIED"
    assert res_data["category"] == "ROADS"
    assert res_data["issue"] == "POTHOLE"
    assert res_data["confidence"] == 0.95
    assert res_data["needs_review"] is False
    assert res_data["severity"]["level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(res_data["trace"]) > 0

    # 2. Verify in GET /api/complaints/{id}
    get_resp = client.get(f"/api/complaints/{complaint_id}")
    assert get_resp.status_code == 200
    c_detail = get_resp.json()
    assert c_detail["id"] == complaint_id
    assert c_detail["citizen_name"] == "Ajit Mane"
    assert len(c_detail["evidence"]) == 1

    ev = c_detail["evidence"][0]
    assert ev["type"] == "IMAGE"
    assert ev["url"] == f"/api/evidence/{ev['id']}/file"

    # 3. Verify original client filename is NOT in file_path
    assert "citizen_secret_personal_camera_file" not in ev["file_path"]

    # 4. Verify file exists on disk
    assert Path(ev["file_path"]).exists()

    # 5. Check audit events in GET /api/complaints/{id}/events
    events_resp = client.get(f"/api/complaints/{complaint_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    actors = [e["actor"] for e in events]
    actions = [e["action"] for e in events]
    assert "AGENT1" in actors
    assert "AGENT2" in actors
    assert "CLASSIFY" in actions
    assert "DECIDE" in actions

    # 6. Serve evidence file via GET /api/evidence/{id}/file
    file_resp = client.get(f"/api/evidence/{ev['id']}/file")
    assert file_resp.status_code == 200
    assert file_resp.content == TINY_PNG


def test_evidence_file_endpoint_path_traversal_rejection(tmp_path):
    client = TestClient(app)

    # 1. Non-existent id -> 404
    assert client.get("/api/evidence/999999/file").status_code == 404

    # 2. Database row with path pointing outside UPLOAD_DIR
    outside_file = tmp_path / "system_secret.txt"
    outside_file.write_text("classified data")

    db = SessionLocal()
    try:
        ev_traversal = Evidence(
            complaint_id="c0000001-0000-0000-0000-000000000001",
            type="IMAGE",
            role="COMPLAINT",
            file_path=str(outside_file.resolve()),
            uploaded_by="Malicious User",
        )
        db.add(ev_traversal)
        db.commit()
        ev_id = ev_traversal.id
    finally:
        db.close()

    # Access must be refused with 404
    trav_resp = client.get(f"/api/evidence/{ev_id}/file")
    assert trav_resp.status_code == 404


def test_missing_latitude_returns_422():
    client = TestClient(app)
    data = {
        "citizen_name": "Citizen Without Lat",
        "citizen_contact": "+91 9999999999",
        "longitude": "74.2410",
        "text": "Pothole somewhere",
    }
    resp = client.post("/api/complaints", data=data)
    assert resp.status_code == 422


def test_no_content_returns_422():
    client = TestClient(app)
    data = {
        "citizen_name": "Citizen Empty",
        "citizen_contact": "+91 9999999999",
        "latitude": "16.70",
        "longitude": "74.24",
        "text": "",
    }
    resp = client.post("/api/complaints", data=data)
    assert resp.status_code == 422
    assert "must contain either text or at least one" in resp.text


def test_disallowed_file_extension_returns_422():
    client = TestClient(app)
    data = {
        "citizen_name": "Citizen Bad File",
        "citizen_contact": "+91 9999999999",
        "latitude": "16.70",
        "longitude": "74.24",
        "text": "Here is an executable",
    }
    files = {
        "image": ("malicious_payload.exe", io.BytesIO(b"MZ executable header"), "application/x-msdownload"),
    }
    resp = client.post("/api/complaints", data=data, files=files)
    assert resp.status_code == 422
    assert "Unsupported media extension" in resp.text


def test_llm_failure_returns_201_human_review():
    # LLM throws error
    fake = FakeBackend([LLMError("API rate limit exceeded across all models")])
    set_backend(fake)
    client = TestClient(app)

    data = {
        "citizen_name": "Citizen LLM Down",
        "citizen_contact": "+91 9999999999",
        "latitude": "16.70",
        "longitude": "74.24",
        "text": "Some civic complaint while LLM is down",
    }
    resp = client.post("/api/complaints", data=data)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "HUMAN_REVIEW"
    assert res_data["needs_review"] is True
    assert res_data["category"] == "OTHER"
    assert res_data["confidence"] == 0.0


def test_non_civic_message_returns_out_of_scope():
    fake = FakeBackend([
        json.dumps({
            "civic_relevance": "LOW",
            "relevance_reason": "Private apartment plumbing request",
            "category": "OTHER",
            "issue": "OTHER",
            "description": "User requesting private plumbing help.",
            "duration_text": None,
            "duration_days": None,
            "size_hint": "UNKNOWN",
            "context_tags": [],
            "language": "en",
            "transcript": None,
            "translation_en": None,
            "location_mentions": [],
            "image_matches_text": None,
            "observations": [],
            "missing_info": [],
            "alternatives": [],
            "confidence": 0.95,
            "confidence_reason": "Clearly non-civic",
        })
    ])
    set_backend(fake)
    client = TestClient(app)

    data = {
        "citizen_name": "Citizen Non Civic",
        "citizen_contact": "+91 9999999999",
        "latitude": "16.70",
        "longitude": "74.24",
        "text": "Can someone recommend a movie to watch tonight?",
    }
    resp = client.post("/api/complaints", data=data)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "OUT_OF_SCOPE"
    assert res_data["severity"]["score"] == 0
    assert res_data["severity"]["level"] == "LOW"
    assert res_data["priority"]["value"] == "NORMAL"


def test_pipeline_logs_agent1_elapsed_milliseconds_without_prompt_or_text(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="resolveit.pipeline")
    fake = FakeBackend([_agent1_civic_json()])
    set_backend(fake)
    client = TestClient(app)

    unique_complaint_secret = "secret_citizen_complaint_text_unique_12345"
    data = {
        "citizen_name": "Citizen Logging Test",
        "citizen_contact": "+91 9822998877",
        "latitude": "16.7020",
        "longitude": "74.2410",
        "text": unique_complaint_secret,
    }

    resp = client.post("/api/complaints", data=data)
    assert resp.status_code == 201

    # Check pipeline log contains elapsed ms
    assert any("Agent 1 classification finished in" in record.message and "ms" in record.message for record in caplog.records)
    # Check pipeline log does NOT leak complaint text or prompt
    for record in caplog.records:
        assert unique_complaint_secret not in record.message
        assert "System Instructions" not in record.message
