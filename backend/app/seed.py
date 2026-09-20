from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from .clock import now as clock_now
from .events import log_event
from .models import (
    Complaint,
    Department,
    Escalation,
    Evidence,
    Resolution,
    User,
)


def seed_departments(db: Session) -> dict[str, Department]:
    """Seed the 10 canonical municipal departments from JSON."""
    json_path = Path(__file__).parent / "seed" / "departments.json"
    with open(json_path, "r", encoding="utf-8") as f:
        departments_data = json.load(f)

    dept_map: dict[str, Department] = {}
    for item in departments_data:
        code = item["code"]
        existing = db.query(Department).filter_by(code=code).first()
        if existing:
            dept_map[code] = existing
            continue

        dept = Department(
            code=code,
            name=item["name"],
            categories=item.get("categories", [code]),
            escalation_chain=item.get("escalation_chain", []),
            sla_hours=item.get("sla_hours"),
        )
        db.add(dept)
        db.flush()
        dept_map[code] = dept

    return dept_map


def seed_users(db: Session, dept_map: dict[str, Department]) -> dict[str, User]:
    """Seed one ADMIN and one OFFICER per department."""
    users_map: dict[str, User] = {}

    # Seed Admin
    admin_contact = "+91 9800000000"
    admin = db.query(User).filter_by(contact=admin_contact).first()
    if not admin:
        admin = User(
            name="Municipal Admin",
            role="ADMIN",
            contact=admin_contact,
            department_id=None,
        )
        db.add(admin)
        db.flush()
    users_map["ADMIN"] = admin

    # Seed Officer for each department
    for idx, (code, dept) in enumerate(dept_map.items(), start=1):
        officer_contact = f"+91 98000000{idx:02d}"
        officer = db.query(User).filter_by(contact=officer_contact).first()
        if not officer:
            officer = User(
                name=f"{dept.name} Officer",
                role="OFFICER",
                contact=officer_contact,
                department_id=dept.id,
            )
            db.add(officer)
            db.flush()
        users_map[code] = officer

    return users_map


def seed_complaints(db: Session, dept_map: dict[str, Department], users_map: dict[str, User]) -> None:
    """Seed 6 Kolhapur complaints across different statuses with full event history."""

    # 1. Tarabai Park (approx lat 16.7112, lng 74.2405) # approximate, verify on a map
    c1_id = "c0000001-0000-0000-0000-000000000001"
    if not db.query(Complaint).filter_by(id=c1_id).first():
        roads_dept = dept_map["ROADS"]
        c1 = Complaint(
            id=c1_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Rahul Deshmukh",
            citizen_contact="+91 9822012345",
            raw_text="रस्त्यावर मोठा खड्डा पडला आहे आणि पाणी साचले आहे, तातडीने दुरुस्ती करा.",  # Marathi input
            language="mr",
            latitude=16.7112,  # approximate, verify on a map
            longitude=74.2405,  # approximate, verify on a map
            address_text="Tarabai Park Main Road, near Circuit House, Kolhapur",
            category="ROADS",
            issue="pothole",
            category_confidence=0.96,
            civic_relevance="HIGH",
            credibility=0.92,
            severity_score=6,  # HIGH band (5-7)
            severity_level="HIGH",
            priority="HIGH",
            severity_factors={"base_risk": 3, "public_safety": 2, "traffic_impact": 1},
            priority_factors={"major_road": True},
            department_id=roads_dept.id,
            assigned_officer_id=users_map["ROADS"].id,
            status="CITIZEN_CONFIRMATION",
            previous_status="ADMIN_VERIFICATION",
            escalation_level=0,
            structured_summary="Large waterlogged pothole on Tarabai Park Main Road posing risk to commuters.",
            ai_reasoning={"extracted_entities": ["pothole", "stagnant water"], "urgency": "high"},
            missing_info=[],
        )
        db.add(c1)
        db.flush()

        # Evidence before and after
        e1_before = Evidence(
            complaint_id=c1.id,
            type="IMAGE",
            role="COMPLAINT",
            file_path="uploads/tarabai_pothole_before.jpg",
            phash="a1b2c3d4e5f60101",
            uploaded_by="Rahul Deshmukh",
            created_at=clock_now(),
        )
        e1_after = Evidence(
            complaint_id=c1.id,
            type="IMAGE",
            role="RESOLUTION_AFTER",
            file_path="uploads/tarabai_pothole_fixed.jpg",
            phash="a1b2c3d4e5f60199",
            uploaded_by="Roads Officer",
            created_at=clock_now(),
        )
        db.add_all([e1_before, e1_after])

        # Resolution record
        r1 = Resolution(
            complaint_id=c1.id,
            officer_id=users_map["ROADS"].id,
            description="Pothole filled with cold mix asphalt and levelled.",
            ai_verdict={"visual_change": "HIGH", "relevance": "CONSISTENT", "recommendation": "APPROVE"},
            ai_confidence=0.91,
            admin_decision="APPROVED",
            citizen_decision=None,
            created_at=clock_now(),
        )
        db.add(r1)

        # Audit events following state transitions
        transitions_c1 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
            ("AGENT_DECIDE", "STATE_TRANSITION", {"from_status": "CLASSIFIED", "to_status": "UNDER_REVIEW"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "UNDER_REVIEW", "to_status": "ASSIGNED"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "ASSIGNED", "to_status": "IN_PROGRESS"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "IN_PROGRESS", "to_status": "RESOLUTION_SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "RESOLUTION_SUBMITTED", "to_status": "AI_VERIFICATION"}),
            ("AGENT_RESOLVE", "STATE_TRANSITION", {"from_status": "AI_VERIFICATION", "to_status": "ADMIN_VERIFICATION"}),
            ("ADMIN", "STATE_TRANSITION", {"from_status": "ADMIN_VERIFICATION", "to_status": "CITIZEN_CONFIRMATION"}),
        ]
        for actor, action, detail in transitions_c1:
            log_event(db, c1.id, actor, action, detail=detail)

    # 2. Rankala Lake (approx lat 16.6885, lng 74.2152) # approximate, verify on a map
    c2_id = "c0000001-0000-0000-0000-000000000002"
    if not db.query(Complaint).filter_by(id=c2_id).first():
        parks_dept = dept_map["PARKS_ENVIRONMENT"]
        c2 = Complaint(
            id=c2_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Priya Patil",
            citizen_contact="+91 9822054321",
            raw_text="A massive tree branch snapped and fell across the lakeside promenade near Rankala Lake.",
            language="en",
            latitude=16.6885,  # approximate, verify on a map
            longitude=74.2152,  # approximate, verify on a map
            address_text="Rankala Lake Chowpatty Promenade, Kolhapur",
            category="PARKS_ENVIRONMENT",
            issue="fallen tree",
            category_confidence=0.98,
            civic_relevance="HIGH",
            credibility=0.95,
            severity_score=7,  # HIGH band (5-7)
            severity_level="HIGH",
            priority="HIGH",
            severity_factors={"base_risk": 3, "public_safety": 3, "affected_area": 1},
            priority_factors={"tourist_area": True},
            department_id=parks_dept.id,
            assigned_officer_id=users_map["PARKS_ENVIRONMENT"].id,
            status="RESOLVED",
            previous_status="CITIZEN_CONFIRMATION",
            escalation_level=0,
            structured_summary="Fallen large branch blocking walking track at Rankala Lake.",
            ai_reasoning={"extracted_entities": ["fallen tree", "Rankala"], "safety_risk": "high"},
            missing_info=[],
            resolved_at=clock_now(),
        )
        db.add(c2)
        db.flush()

        e2 = Evidence(
            complaint_id=c2.id,
            type="IMAGE",
            role="COMPLAINT",
            file_path="uploads/rankala_tree_fallen.jpg",
            phash="b2c3d4e5f6a10011",
            uploaded_by="Priya Patil",
            created_at=clock_now(),
        )
        db.add(e2)

        r2 = Resolution(
            complaint_id=c2.id,
            officer_id=users_map["PARKS_ENVIRONMENT"].id,
            description="Branch cleared, sawed and removed from pathway.",
            ai_verdict={"visual_change": "COMPLETE", "relevance": "CONSISTENT", "recommendation": "APPROVE"},
            ai_confidence=0.95,
            admin_decision="APPROVED",
            citizen_decision="CONFIRMED",
            created_at=clock_now(),
        )
        db.add(r2)

        transitions_c2 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
            ("AGENT_DECIDE", "STATE_TRANSITION", {"from_status": "CLASSIFIED", "to_status": "UNDER_REVIEW"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "UNDER_REVIEW", "to_status": "ASSIGNED"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "ASSIGNED", "to_status": "IN_PROGRESS"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "IN_PROGRESS", "to_status": "RESOLUTION_SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "RESOLUTION_SUBMITTED", "to_status": "AI_VERIFICATION"}),
            ("AGENT_RESOLVE", "STATE_TRANSITION", {"from_status": "AI_VERIFICATION", "to_status": "ADMIN_VERIFICATION"}),
            ("ADMIN", "STATE_TRANSITION", {"from_status": "ADMIN_VERIFICATION", "to_status": "CITIZEN_CONFIRMATION"}),
            ("CITIZEN", "STATE_TRANSITION", {"from_status": "CITIZEN_CONFIRMATION", "to_status": "RESOLVED"}),
        ]
        for actor, action, detail in transitions_c2:
            log_event(db, c2.id, actor, action, detail=detail)

    # 3. Shahupuri (approx lat 16.7025, lng 74.2386) # approximate, verify on a map
    c3_id = "c0000001-0000-0000-0000-000000000003"
    if not db.query(Complaint).filter_by(id=c3_id).first():
        drainage_dept = dept_map["DRAINAGE"]
        c3 = Complaint(
            id=c3_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Amit Shinde",
            citizen_contact="+91 9823099887",
            raw_text="Blocked sewer line overflowing onto Shahupuri 2nd Lane market street. Acute stink and health hazard.",
            language="en",
            latitude=16.7025,  # approximate, verify on a map
            longitude=74.2386,  # approximate, verify on a map
            address_text="2nd Lane, Shahupuri Market, Kolhapur",
            category="DRAINAGE",
            issue="sewage overflow",
            category_confidence=0.97,
            civic_relevance="HIGH",
            credibility=0.90,
            severity_score=9,  # CRITICAL band (8-10)
            severity_level="CRITICAL",
            priority="EMERGENCY",
            severity_factors={"base_risk": 4, "public_safety": 3, "traffic_impact": 2},
            priority_factors={"dense_market": True, "health_hazard": True},
            department_id=drainage_dept.id,
            assigned_officer_id=users_map["DRAINAGE"].id,
            status="ESCALATED",
            previous_status="IN_PROGRESS",
            escalation_level=1,
            structured_summary="Critical sewage overflow in dense commercial market area.",
            ai_reasoning={"extracted_entities": ["sewage", "market", "overflow"], "health_risk": "critical"},
            missing_info=[],
        )
        db.add(c3)
        db.flush()

        esc3 = Escalation(
            complaint_id=c3.id,
            level=1,
            dossier="SLA response breach of 6 hours in commercial district; escalated to Department Head.",
            created_at=clock_now(),
        )
        db.add(esc3)

        transitions_c3 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
            ("AGENT_DECIDE", "STATE_TRANSITION", {"from_status": "CLASSIFIED", "to_status": "UNDER_REVIEW"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "UNDER_REVIEW", "to_status": "ASSIGNED"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "ASSIGNED", "to_status": "IN_PROGRESS"}),
            ("SCHEDULER", "STATE_TRANSITION", {"from_status": "IN_PROGRESS", "to_status": "ESCALATED"}, "SLA initial response breach"),
        ]
        for item in transitions_c3:
            actor, action, detail = item[0], item[1], item[2]
            reason = item[3] if len(item) > 3 else None
            log_event(db, c3.id, actor, action, detail=detail, reasoning=reason)

    # 4. Laxmipuri (approx lat 16.7001, lng 74.2308) # approximate, verify on a map
    c4_id = "c0000001-0000-0000-0000-000000000004"
    if not db.query(Complaint).filter_by(id=c4_id).first():
        waste_dept = dept_map["WASTE"]
        c4 = Complaint(
            id=c4_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Sunita Kamble",
            citizen_contact="+91 9822188776",
            raw_text="Garbage bins are overflowing with wet vegetable waste scattered across the street.",
            language="en",
            latitude=16.7001,  # approximate, verify on a map
            longitude=74.2308,  # approximate, verify on a map
            address_text="Laxmipuri Vegetable Market Yard, Kolhapur",
            category="WASTE",
            issue="overflowing bin",
            category_confidence=0.95,
            civic_relevance="HIGH",
            credibility=0.88,
            severity_score=4,  # MEDIUM band (3-4)
            severity_level="MEDIUM",
            priority="STANDARD",
            severity_factors={"base_risk": 2, "affected_area": 1, "duration": 1},
            priority_factors={},
            department_id=waste_dept.id,
            assigned_officer_id=users_map["WASTE"].id,
            status="IN_PROGRESS",
            previous_status="ASSIGNED",
            escalation_level=0,
            structured_summary="Overflowing garbage container in vegetable market area.",
            ai_reasoning={"extracted_entities": ["garbage bin", "vegetable waste"]},
            missing_info=[],
        )
        db.add(c4)
        db.flush()

        transitions_c4 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
            ("AGENT_DECIDE", "STATE_TRANSITION", {"from_status": "CLASSIFIED", "to_status": "UNDER_REVIEW"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "UNDER_REVIEW", "to_status": "ASSIGNED"}),
            ("OFFICER", "STATE_TRANSITION", {"from_status": "ASSIGNED", "to_status": "IN_PROGRESS"}),
        ]
        for actor, action, detail in transitions_c4:
            log_event(db, c4.id, actor, action, detail=detail)

    # 5. Rajarampuri (approx lat 16.6918, lng 74.2452) # approximate, verify on a map
    c5_id = "c0000001-0000-0000-0000-000000000005"
    if not db.query(Complaint).filter_by(id=c5_id).first():
        lighting_dept = dept_map["STREET_LIGHTING"]
        c5 = Complaint(
            id=c5_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Mahesh Kulkarni",
            citizen_contact="+91 9823123499",
            raw_text="Streetlight pole #12 not functioning for 3 days; dark corner at residential intersection.",
            language="en",
            latitude=16.6918,  # approximate, verify on a map
            longitude=74.2452,  # approximate, verify on a map
            address_text="7th Lane, Rajarampuri, Kolhapur",
            category="STREET_LIGHTING",
            issue="light not working",
            category_confidence=0.99,
            civic_relevance="HIGH",
            credibility=0.91,
            severity_score=2,  # LOW band (0-2)
            severity_level="LOW",
            priority="NORMAL",
            severity_factors={"base_risk": 1, "duration": 1},
            priority_factors={},
            department_id=lighting_dept.id,
            assigned_officer_id=users_map["STREET_LIGHTING"].id,
            status="ASSIGNED",
            previous_status="UNDER_REVIEW",
            escalation_level=0,
            structured_summary="Streetlight out in 7th lane Rajarampuri residential lane.",
            ai_reasoning={"extracted_entities": ["streetlight", "Rajarampuri"]},
            missing_info=[],
        )
        db.add(c5)
        db.flush()

        transitions_c5 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
            ("AGENT_DECIDE", "STATE_TRANSITION", {"from_status": "CLASSIFIED", "to_status": "UNDER_REVIEW"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "UNDER_REVIEW", "to_status": "ASSIGNED"}),
        ]
        for actor, action, detail in transitions_c5:
            log_event(db, c5.id, actor, action, detail=detail)

    # 6. Dabholkar Corner (approx lat 16.7058, lng 74.2420) # approximate, verify on a map
    c6_id = "c0000001-0000-0000-0000-000000000006"
    if not db.query(Complaint).filter_by(id=c6_id).first():
        traffic_dept = dept_map["TRAFFIC"]
        c6 = Complaint(
            id=c6_id,
            created_at=clock_now(),
            updated_at=clock_now(),
            citizen_name="Vikram Jadhav",
            citizen_contact="+91 9822334455",
            raw_text="Main traffic signal at Dabholkar Corner is erratic and blinking yellow, causing severe congestion.",
            language="en",
            latitude=16.7058,  # approximate, verify on a map
            longitude=74.2420,  # approximate, verify on a map
            address_text="Station Road, Dabholkar Corner Chowk, Kolhapur",
            category="TRAFFIC",
            issue="traffic signal failure",
            category_confidence=0.96,
            civic_relevance="HIGH",
            credibility=0.94,
            severity_score=6,  # HIGH band (5-7)
            severity_level="HIGH",
            priority="HIGH",
            severity_factors={"base_risk": 3, "public_safety": 2, "traffic_impact": 1},
            priority_factors={"major_junction": True},
            department_id=traffic_dept.id,
            status="CLASSIFIED",
            previous_status="AI_ANALYZING",
            escalation_level=0,
            structured_summary="Traffic signal failure at major intersection near railway station.",
            ai_reasoning={"extracted_entities": ["traffic signal", "congestion", "Dabholkar Corner"]},
            missing_info=[],
        )
        db.add(c6)
        db.flush()

        transitions_c6 = [
            ("CITIZEN", "SUBMIT_COMPLAINT", {"status": "SUBMITTED"}),
            ("SYSTEM", "STATE_TRANSITION", {"from_status": "SUBMITTED", "to_status": "AI_ANALYZING"}),
            ("AGENT_CLASSIFY", "STATE_TRANSITION", {"from_status": "AI_ANALYZING", "to_status": "CLASSIFIED"}),
        ]
        for actor, action, detail in transitions_c6:
            log_event(db, c6.id, actor, action, detail=detail)

    db.commit()


def seed_database(db: Session) -> None:
    """Run all seed operations idempotently."""
    dept_map = seed_departments(db)
    users_map = seed_users(db, dept_map)
    seed_complaints(db, dept_map, users_map)
