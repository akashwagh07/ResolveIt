import pytest
from backend.app.commands import Actor
from backend.app.executor import execute_command
from backend.app.models import CommandRejection, Complaint, Evidence, User


def sample_create_payload(outcome="CLASSIFIED", confidence=0.95, merge_into_id=None):
    return {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Ganesh Kadam",
        "citizen_contact": "+91 9822001122",
        "raw_text": "Massive pothole near bus stand",
        "language": "en",
        "latitude": 16.71,
        "longitude": 74.24,
        "address_text": "Central Bus Stand, Kolhapur",
        "category": "ROADS",
        "issue": "POTHOLE",
        "category_confidence": confidence,
        "civic_relevance": "HIGH",
        "severity_score": 6,
        "severity_level": "HIGH",
        "priority": "HIGH",
        "severity_factors": [{"factor": "traffic", "points": 3, "reason": "busy area"}],
        "department_code": "ROADS",
        "structured_summary": "Pothole at Central Bus Stand",
        "ai_reasoning": {"route": "cbs"},
        "missing_info": [],
        "evidence": [{"type": "IMAGE", "file_path": "uploads/pothole.jpg"}],
        "outcome": outcome,
        "merge_into_id": merge_into_id,
    }


def test_permission_failures(db):
    c = db.query(Complaint).filter_by(status="CITIZEN_CONFIRMATION").first()
    assert c is not None

    # CITIZEN cannot ASSIGN
    res = execute_command(
        db,
        {"command": "ASSIGN", "complaint_id": c.id, "officer_id": 1},
        actor=Actor.CITIZEN,
        actor_ref=c.citizen_contact,
    )
    assert res.ok is False
    assert "not permitted to execute 'ASSIGN'" in res.error

    # AGENT cannot CLOSE
    res2 = execute_command(
        db,
        {"command": "CLOSE", "complaint_id": c.id, "closure_reason": "CITIZEN_CONFIRMED"},
        actor=Actor.AGENT2,
    )
    assert res2.ok is False
    assert "not permitted to execute 'CLOSE'" in res2.error


def test_wrong_state_rejection(db):
    c = db.query(Complaint).filter_by(status="RESOLVED").first()
    assert c is not None

    # ASSIGN only allowed in UNDER_REVIEW
    res = execute_command(
        db,
        {"command": "ASSIGN", "complaint_id": c.id, "officer_id": 1},
        actor=Actor.ADMIN,
    )
    assert res.ok is False
    assert "not allowed when status is 'RESOLVED'" in res.error


def test_identity_checks(db):
    c = db.query(Complaint).filter_by(status="CITIZEN_CONFIRMATION").first()
    assert c is not None

    # Wrong citizen contact
    res = execute_command(
        db,
        {"command": "CLOSE", "complaint_id": c.id, "closure_reason": "CITIZEN_CONFIRMED"},
        actor=Actor.CITIZEN,
        actor_ref="+91 0000000000",  # mismatched contact
    )
    assert res.ok is False
    assert "actor_ref does not match complaint contact" in res.error


def test_wrong_department_assignment_rejected(db):
    # Create complaint in UNDER_REVIEW
    res_create = execute_command(db, sample_create_payload(), actor=Actor.AGENT2)
    assert res_create.ok is True
    cid = res_create.complaint_id

    # Move CLASSIFIED -> UNDER_REVIEW
    res_move = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": cid, "new_status": "UNDER_REVIEW", "reason": "Triage"},
        actor=Actor.ADMIN,
    )
    assert res_move.ok is True

    # Find officer of a DIFFERENT department (e.g. WATER)
    water_officer = db.query(User).filter(User.role == "OFFICER", User.department_id != 1).first()
    assert water_officer is not None

    res_assign = execute_command(
        db,
        {"command": "ASSIGN", "complaint_id": cid, "officer_id": water_officer.id},
        actor=Actor.ADMIN,
    )
    assert res_assign.ok is False
    assert "belongs to department" in res_assign.error


def test_create_complaint_outcomes_and_confidence_gating(db):
    # 1. CLASSIFIED outcome (auto band >= 0.85)
    r1 = execute_command(db, sample_create_payload(outcome="CLASSIFIED", confidence=0.90), actor=Actor.AGENT2)
    assert r1.ok is True
    c1 = db.query(Complaint).filter_by(id=r1.complaint_id).first()
    assert c1.status == "CLASSIFIED"
    assert c1.needs_review is False
    assert c1.sla_deadline is not None

    # 2. REVIEW band (0.60 to 0.84) keeps CLASSIFIED but flags needs_review
    r2 = execute_command(db, sample_create_payload(outcome="CLASSIFIED", confidence=0.75), actor=Actor.AGENT2)
    assert r2.ok is True
    c2 = db.query(Complaint).filter_by(id=r2.complaint_id).first()
    assert c2.status == "CLASSIFIED"
    assert c2.needs_review is True

    # 3. HUMAN band (< 0.60) forces outcome to HUMAN_REVIEW
    r3 = execute_command(db, sample_create_payload(outcome="CLASSIFIED", confidence=0.50), actor=Actor.AGENT2)
    assert r3.ok is True
    c3 = db.query(Complaint).filter_by(id=r3.complaint_id).first()
    assert c3.status == "HUMAN_REVIEW"
    assert c3.needs_review is True

    # 4. OUT_OF_SCOPE outcome
    r4 = execute_command(db, sample_create_payload(outcome="OUT_OF_SCOPE", confidence=0.90), actor=Actor.AGENT2)
    assert r4.ok is True
    c4 = db.query(Complaint).filter_by(id=r4.complaint_id).first()
    assert c4.status == "OUT_OF_SCOPE"

    # 5. MERGED outcome increments parent duplicate_count
    parent = c1
    initial_dups = parent.duplicate_count
    r5 = execute_command(
        db,
        sample_create_payload(outcome="MERGED", confidence=0.95, merge_into_id=parent.id),
        actor=Actor.AGENT2,
    )
    assert r5.ok is True
    c5 = db.query(Complaint).filter_by(id=r5.complaint_id).first()
    assert c5.status == "MERGED"
    assert c5.duplicate_of == parent.id

    db.refresh(parent)
    assert parent.duplicate_count == initial_dups + 1


def test_full_happy_path_to_resolved(db):
    # 1. CREATE_COMPLAINT -> CLASSIFIED
    r_create = execute_command(db, sample_create_payload(outcome="CLASSIFIED"), actor=Actor.AGENT2)
    assert r_create.ok is True
    cid = r_create.complaint_id

    # 2. CHANGE_STATUS: CLASSIFIED -> UNDER_REVIEW
    r_triage = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": cid, "new_status": "UNDER_REVIEW", "reason": "Triage complete"},
        actor=Actor.ADMIN,
    )
    assert r_triage.ok is True

    # 3. ASSIGN: UNDER_REVIEW -> ASSIGNED
    roads_officer = db.query(User).filter_by(role="OFFICER", department_id=1).first()
    assert roads_officer is not None
    r_assign = execute_command(
        db,
        {"command": "ASSIGN", "complaint_id": cid, "officer_id": roads_officer.id, "note": "Assigned to Ward 3"},
        actor=Actor.ADMIN,
    )
    assert r_assign.ok is True

    # 4. CHANGE_STATUS: ASSIGNED -> IN_PROGRESS
    r_progress = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": cid, "new_status": "IN_PROGRESS", "reason": "Starting repair"},
        actor=Actor.OFFICER,
        actor_ref=roads_officer.id,
    )
    assert r_progress.ok is True

    # Add resolution evidence row with role RESOLUTION_AFTER
    ev_after = Evidence(
        complaint_id=cid,
        type="IMAGE",
        role="RESOLUTION_AFTER",
        file_path="uploads/pothole_fixed.jpg",
        uploaded_by="Roads Officer",
    )
    db.add(ev_after)
    db.commit()

    # 5. SUBMIT_RESOLUTION: IN_PROGRESS -> RESOLUTION_SUBMITTED
    r_res = execute_command(
        db,
        {
            "command": "SUBMIT_RESOLUTION",
            "complaint_id": cid,
            "officer_id": roads_officer.id,
            "description": "Pothole filled and sealed",
            "after_evidence_ids": [ev_after.id],
        },
        actor=Actor.OFFICER,
        actor_ref=roads_officer.id,
    )
    assert r_res.ok is True

    # 6. CHANGE_STATUS: RESOLUTION_SUBMITTED -> AI_VERIFICATION
    r_ai_v = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": cid, "new_status": "AI_VERIFICATION", "reason": "Initiate AI check"},
        actor=Actor.SYSTEM,
    )
    assert r_ai_v.ok is True

    # 7. RECORD_VERIFICATION: AI_VERIFICATION -> ADMIN_VERIFICATION
    r_rec_v = execute_command(
        db,
        {
            "command": "RECORD_VERIFICATION",
            "complaint_id": cid,
            "evidence_relevant": True,
            "location_consistent": True,
            "visual_change_detected": True,
            "confidence": 0.94,
            "recommendation": "ADMIN_REVIEW",
            "reasoning": "Clear before/after fix visible",
        },
        actor=Actor.AGENT3,
    )
    assert r_rec_v.ok is True

    # 8. CHANGE_STATUS: ADMIN_VERIFICATION -> CITIZEN_CONFIRMATION
    r_admin_v = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": cid, "new_status": "CITIZEN_CONFIRMATION", "reason": "Admin approved fix"},
        actor=Actor.ADMIN,
    )
    assert r_admin_v.ok is True

    # 9. CLOSE: CITIZEN_CONFIRMATION -> RESOLVED
    complaint_obj = db.query(Complaint).filter_by(id=cid).first()
    r_close = execute_command(
        db,
        {"command": "CLOSE", "complaint_id": cid, "closure_reason": "CITIZEN_CONFIRMED"},
        actor=Actor.CITIZEN,
        actor_ref=complaint_obj.citizen_contact,
    )
    assert r_close.ok is True
    assert r_close.new_status == "RESOLVED"

    db.refresh(complaint_obj)
    assert complaint_obj.status == "RESOLVED"
    assert complaint_obj.resolved_at is not None


def test_dispute_path_reopen(db):
    c = db.query(Complaint).filter_by(status="CITIZEN_CONFIRMATION").first()
    assert c is not None

    # Citizen disputes fix -> REOPENED
    res_reopen = execute_command(
        db,
        {"command": "REOPEN", "complaint_id": c.id, "reason": "Work was incomplete, debris remains"},
        actor=Actor.CITIZEN,
        actor_ref=c.citizen_contact,
    )
    assert res_reopen.ok is True
    assert res_reopen.new_status == "REOPENED"

    # Move back to IN_PROGRESS
    res_rework = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": c.id, "new_status": "IN_PROGRESS", "reason": "Re-dispatching team"},
        actor=Actor.ADMIN,
    )
    assert res_rework.ok is True
    assert res_rework.new_status == "IN_PROGRESS"


def test_escalate_and_return_to_previous_status(db):
    c = db.query(Complaint).filter_by(status="IN_PROGRESS").first()
    assert c is not None

    initial_status = c.status
    initial_esc_level = c.escalation_level

    # ESCALATE
    res_esc = execute_command(
        db,
        {"command": "ESCALATE", "complaint_id": c.id, "reason": "SLA deadline missed", "dossier": "Case dossier"},
        actor=Actor.AGENT3,
    )
    assert res_esc.ok is True
    assert res_esc.new_status == "ESCALATED"

    db.refresh(c)
    assert c.previous_status == initial_status
    assert c.escalation_level == initial_esc_level + 1

    # Attempt invalid return to wrong status
    res_bad = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": c.id, "new_status": "RESOLVED", "reason": "Try direct close"},
        actor=Actor.ADMIN,
    )
    assert res_bad.ok is False
    assert "may only return to previous_status" in res_bad.error

    # Valid return to previous_status by ADMIN
    res_return = execute_command(
        db,
        {"command": "CHANGE_STATUS", "complaint_id": c.id, "new_status": initial_status, "reason": "Higher authority intervened"},
        actor=Actor.ADMIN,
    )
    assert res_return.ok is True
    assert res_return.new_status == initial_status


def test_rejected_command_logs_command_rejection_and_leaves_complaint_unchanged(db):
    c = db.query(Complaint).filter_by(status="IN_PROGRESS").first()
    assert c is not None
    orig_status = c.status

    initial_rejections = db.query(CommandRejection).count()

    # Issue an illegal command: CITIZEN tries to ESCALATE
    res = execute_command(
        db,
        {"command": "ESCALATE", "complaint_id": c.id, "reason": "User anger", "dossier": "N/A"},
        actor=Actor.CITIZEN,
        actor_ref=c.citizen_contact,
    )
    assert res.ok is False

    # Complaint is unchanged
    db.refresh(c)
    assert c.status == orig_status

    # CommandRejection record exists
    new_rejections = db.query(CommandRejection).count()
    assert new_rejections == initial_rejections + 1
    last_rej = db.query(CommandRejection).order_by(CommandRejection.id.desc()).first()
    assert last_rej.command_type == "ESCALATE"
    assert last_rej.actor == "CITIZEN"
    assert "not permitted" in last_rej.reason
