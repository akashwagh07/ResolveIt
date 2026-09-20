"""Tests for auth, action layer, and resolution uploads."""

from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from backend.app.commands import Actor
from backend.app.config import get_settings
from backend.app.executor import execute_command
from backend.app.models import CommandRejection, Complaint, ComplaintEvent, Department, Evidence, Resolution, User
from backend.scripts.demo_flow import generate_tiny_png


def _get_admin_headers(passcode="officer123"):
    return {
        "X-Demo-Role": "ADMIN",
        "X-Demo-User-Id": "1",
        "X-Demo-Passcode": passcode,
    }


def _get_officer_headers(user_id=2, passcode="officer123"):
    return {
        "X-Demo-Role": "OFFICER",
        "X-Demo-User-Id": str(user_id),
        "X-Demo-Passcode": passcode,
    }


def _get_citizen_headers(contact="+91 9822012345"):
    return {
        "X-Demo-Role": "CITIZEN",
        "X-Citizen-Contact": contact,
    }


def test_auth_headers_and_validation(client):
    # 1. Missing X-Demo-Role -> 401
    res = client.get("/api/auth/whoami")
    assert res.status_code == 401

    # 2. Invalid role -> 401
    res = client.get("/api/auth/whoami", headers={"X-Demo-Role": "INVALID"})
    assert res.status_code == 401

    # 3. Citizen missing contact -> 401
    res = client.get("/api/auth/whoami", headers={"X-Demo-Role": "CITIZEN"})
    assert res.status_code == 401

    # 4. Officer missing user_id or passcode -> 401
    res = client.get("/api/auth/whoami", headers={"X-Demo-Role": "OFFICER", "X-Demo-User-Id": "2"})
    assert res.status_code == 401

    res = client.get("/api/auth/whoami", headers={"X-Demo-Role": "OFFICER", "X-Demo-Passcode": "officer123"})
    assert res.status_code == 401

    # 5. Officer wrong passcode -> 401
    res = client.get("/api/auth/whoami", headers=_get_officer_headers(2, passcode="wrongpass"))
    assert res.status_code == 401

    # 6. Non-existent user -> 401
    res = client.get("/api/auth/whoami", headers=_get_officer_headers(999))
    assert res.status_code == 401

    # 7. Role mismatch -> 403 (e.g. user 1 is ADMIN, but role header claims OFFICER)
    res = client.get("/api/auth/whoami", headers=_get_officer_headers(1))
    assert res.status_code == 403

    # 8. Valid whoami for Officer
    res = client.get("/api/auth/whoami", headers=_get_officer_headers(2))
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "OFFICER"
    assert data["department"] is not None
    assert "code" in data["department"]

    # 9. Valid whoami for Citizen
    res = client.get("/api/auth/whoami", headers=_get_citizen_headers("+91 9999900000"))
    assert res.status_code == 200
    assert res.json()["role"] == "CITIZEN"


def test_users_list_endpoint(client):
    res = client.get("/api/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2
    for u in users:
        assert "contact" not in u
        assert u["role"] in {"OFFICER", "ADMIN"}

    res_off = client.get("/api/users?role=OFFICER")
    assert res_off.status_code == 200
    assert all(u["role"] == "OFFICER" for u in res_off.json())


def test_full_lifecycle_http(client, db):
    # Seeded complaint c6 is CLASSIFIED and in TRAFFIC department
    c6_id = "c0000001-0000-0000-0000-000000000006"
    c6 = db.query(Complaint).filter_by(id=c6_id).first()
    traffic_dept_id = c6.department_id

    traffic_officer = db.query(User).filter_by(department_id=traffic_dept_id, role="OFFICER").first()
    assert traffic_officer is not None

    admin_headers = _get_admin_headers()
    officer_headers = _get_officer_headers(traffic_officer.id)
    citizen_headers = _get_citizen_headers(c6.citizen_contact)

    # 1. Available actions for admin on CLASSIFIED
    actions_res = client.get(f"/api/complaints/{c6_id}/actions", headers=admin_headers)
    assert actions_res.status_code == 200
    actions = [a["action"] for a in actions_res.json()]
    assert "accept" in actions
    assert "assign" in actions

    # 2. Admin assign (from CLASSIFIED, executes accept then assign)
    assign_res = client.post(
        f"/api/complaints/{c6_id}/actions/assign",
        headers=admin_headers,
        json={"officer_id": traffic_officer.id, "note": "Assigned to traffic head"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "ASSIGNED"

    # 3. Officer starts work
    start_res = client.post(
        f"/api/complaints/{c6_id}/actions/start_work",
        headers=officer_headers,
        json={},
    )
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"

    # 4. Officer uploads resolution
    png_data = generate_tiny_png()
    upload_res = client.post(
        f"/api/complaints/{c6_id}/resolution",
        headers=officer_headers,
        data={"description": "Repaired traffic signal timing logic and replaced fuse."},
        files=[("after_images", ("proof.png", png_data, "image/png"))],
    )
    assert upload_res.status_code == 200
    upload_json = upload_res.json()
    assert upload_json["ok"] is True
    # Verification hook should move it to ADMIN_VERIFICATION
    assert upload_json["status"] == "ADMIN_VERIFICATION"

    # 5. Check detail endpoint includes resolutions, assigned_officer, and department
    detail_res = client.get(f"/api/complaints/{c6_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["assigned_officer"]["id"] == traffic_officer.id
    assert detail["department"]["id"] == traffic_dept_id
    assert len(detail["resolutions"]) == 1
    assert detail["resolutions"][0]["description"] == "Repaired traffic signal timing logic and replaced fuse."
    assert len(detail["resolutions"][0]["after_evidence"]) == 1
    assert detail["resolutions"][0]["after_evidence"][0]["url"].startswith("/api/evidence/")

    # 6. Admin approves resolution
    approve_res = client.post(
        f"/api/complaints/{c6_id}/actions/approve_resolution",
        headers=admin_headers,
        json={},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "CITIZEN_CONFIRMATION"

    # 7. Citizen confirms resolution
    confirm_res = client.post(
        f"/api/complaints/{c6_id}/actions/confirm_resolution",
        headers=citizen_headers,
        json={},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "RESOLVED"

    # Verify resolved_at is set
    db.expire_all()
    complaint_after = db.query(Complaint).filter_by(id=c6_id).first()
    assert complaint_after.status == "RESOLVED"
    assert complaint_after.resolved_at is not None

    # Check audit events recorded transitions
    events = db.query(ComplaintEvent).filter_by(complaint_id=c6_id).all()
    actions_recorded = [e.action for e in events]
    assert "STATE_TRANSITION" in actions_recorded


def test_dispute_and_reopen_path(client, db):
    # c1 is seeded in CITIZEN_CONFIRMATION
    c1_id = "c0000001-0000-0000-0000-000000000001"
    c1 = db.query(Complaint).filter_by(id=c1_id).first()
    citizen_headers = _get_citizen_headers(c1.citizen_contact)
    officer_headers = _get_officer_headers(c1.assigned_officer_id)

    # 1. Citizen disputes resolution
    disp_res = client.post(
        f"/api/complaints/{c1_id}/actions/dispute_resolution",
        headers=citizen_headers,
        json={"reason": "Pothole is still bumpy and not level."},
    )
    assert disp_res.status_code == 200
    assert disp_res.json()["status"] == "REOPENED"

    # 2. Officer resumes work
    resume_res = client.post(
        f"/api/complaints/{c1_id}/actions/resume_work",
        headers=officer_headers,
        json={},
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "IN_PROGRESS"


def test_reject_resolution_returns_to_in_progress(client, db):
    c1_id = "c0000001-0000-0000-0000-000000000001"
    c1 = db.query(Complaint).filter_by(id=c1_id).first()
    c1.status = "ADMIN_VERIFICATION"
    db.commit()

    admin_headers = _get_admin_headers()
    res = client.post(
        f"/api/complaints/{c1_id}/actions/reject_resolution",
        headers=admin_headers,
        json={"reason": "Asphalt work is incomplete on left side."},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"

    db.expire_all()
    c1_updated = db.query(Complaint).filter_by(id=c1_id).first()
    latest_res = db.query(Resolution).filter_by(complaint_id=c1_id).order_by(Resolution.created_at.desc()).first()
    assert latest_res.admin_decision == "REJECTED"


def test_permission_and_identity_guards(client, db):
    c4_id = "c0000001-0000-0000-0000-000000000004"
    c4 = db.query(Complaint).filter_by(id=c4_id).first()
    # c4 is WASTE, assigned to WASTE officer
    waste_officer_id = c4.assigned_officer_id

    # ROADS officer trying to start work on WASTE complaint -> 403
    roads_officer = db.query(User).filter(User.role == "OFFICER", User.id != waste_officer_id).first()
    wrong_officer_headers = _get_officer_headers(roads_officer.id)

    # Put c4 in ASSIGNED
    c4.status = "ASSIGNED"
    db.commit()

    res = client.post(
        f"/api/complaints/{c4_id}/actions/start_work",
        headers=wrong_officer_headers,
        json={},
    )
    assert res.status_code == 403

    # Officer calling admin action (e.g. assign) -> 403
    res_assign = client.post(
        f"/api/complaints/{c4_id}/actions/assign",
        headers=wrong_officer_headers,
        json={"officer_id": roads_officer.id},
    )
    assert res_assign.status_code == 403

    # Citizen with wrong contact trying to confirm -> 403
    c1_id = "c0000001-0000-0000-0000-000000000001"
    wrong_citizen_headers = _get_citizen_headers("+91 0000000000")
    res_confirm = client.post(
        f"/api/complaints/{c1_id}/actions/confirm_resolution",
        headers=wrong_citizen_headers,
        json={},
    )
    assert res_confirm.status_code == 403


def test_wrong_state_returns_409_and_writes_rejection(client, db):
    c5_id = "c0000001-0000-0000-0000-000000000005"  # ASSIGNED
    admin_headers = _get_admin_headers()

    # approve_resolution on ASSIGNED -> 409
    res = client.post(
        f"/api/complaints/{c5_id}/actions/approve_resolution",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 409


def test_invalid_resolution_upload_leaves_no_disk_files(client, db):
    c4_id = "c0000001-0000-0000-0000-000000000004"
    c4 = db.query(Complaint).filter_by(id=c4_id).first()
    c4.status = "IN_PROGRESS"
    db.commit()

    officer_headers = _get_officer_headers(c4.assigned_officer_id)

    # 1. Non-image file upload -> 422
    text_content = b"This is a text document, not an image"
    res = client.post(
        f"/api/complaints/{c4_id}/resolution",
        headers=officer_headers,
        data={"description": "Work was completed but upload is invalid."},
        files=[("after_images", ("bad_file.txt", text_content, "text/plain"))],
    )
    assert res.status_code == 422

    # Check directory on disk: no file ending in .txt
    settings = get_settings()
    res_dir = Path(settings.UPLOAD_DIR) / "resolutions" / c4_id
    if res_dir.exists():
        assert len(list(res_dir.glob("*.txt"))) == 0


def test_de_escalate_returns_to_previous_status(client, db):
    c3_id = "c0000001-0000-0000-0000-000000000003"
    c3 = db.query(Complaint).filter_by(id=c3_id).first()
    # c3 is ESCALATED with previous_status IN_PROGRESS
    assert c3.status == "ESCALATED"
    assert c3.previous_status == "IN_PROGRESS"

    admin_headers = _get_admin_headers()
    res = client.post(
        f"/api/complaints/{c3_id}/actions/de_escalate",
        headers=admin_headers,
        json={},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"

    db.expire_all()
    c3_updated = db.query(Complaint).filter_by(id=c3_id).first()
    assert c3_updated.status == "IN_PROGRESS"


def test_complaints_list_filters(client, db):
    # Test assigned_officer_id filter
    res = client.get("/api/complaints?assigned_officer_id=2")
    assert res.status_code == 200
    for c in res.json():
        assert c["assigned_officer_id"] == 2

    # Test needs_review filter
    res_nr = client.get("/api/complaints?needs_review=false")
    assert res_nr.status_code == 200
    for c in res_nr.json():
        assert c["needs_review"] is False

    # Test empty param treated as absent
    res_empty = client.get("/api/complaints?assigned_officer_id=&needs_review=")
    assert res_empty.status_code == 200
    assert len(res_empty.json()) >= 6
