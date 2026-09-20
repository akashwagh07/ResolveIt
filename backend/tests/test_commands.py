import pytest
from backend.app.commands import parse_command


def test_parse_valid_create_complaint():
    data = {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Test Citizen",
        "citizen_contact": "+91 9999999999",
        "raw_text": "Pothole on main road",
        "language": "en",
        "latitude": 16.7,
        "longitude": 74.2,
        "address_text": "Kolhapur Main Road",
        "category": "ROADS",
        "issue": "POTHOLE",
        "category_confidence": 0.95,
        "civic_relevance": "HIGH",
        "severity_score": 6,
        "severity_level": "HIGH",
        "priority": "HIGH",
        "severity_factors": [{"factor": "risk", "points": 3, "reason": "danger"}],
        "department_code": "ROADS",
        "structured_summary": "Pothole on main road",
        "ai_reasoning": {"info": "clear"},
        "outcome": "CLASSIFIED",
    }
    cmd = parse_command(data)
    assert cmd.command == "CREATE_COMPLAINT"
    assert cmd.category == "ROADS"
    assert cmd.issue == "POTHOLE"


def test_parse_unknown_command():
    with pytest.raises(ValueError) as exc:
        parse_command({"command": "FLY_TO_MARS"})
    assert "Invalid or malformed command" in str(exc.value) or "Validation error" in str(exc.value)


def test_parse_category_issue_mismatch():
    data = {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Test Citizen",
        "citizen_contact": "+91 9999999999",
        "raw_text": "Fallen tree on road",
        "latitude": 16.7,
        "longitude": 74.2,
        "address_text": "Some road",
        "category": "ROADS",
        "issue": "FALLEN_TREE",  # Belongs to PARKS_ENVIRONMENT, not ROADS
        "category_confidence": 0.95,
        "civic_relevance": "HIGH",
        "severity_score": 6,
        "severity_level": "HIGH",
        "priority": "HIGH",
        "severity_factors": [],
        "department_code": "ROADS",
        "structured_summary": "Fallen tree",
        "ai_reasoning": {},
        "outcome": "CLASSIFIED",
    }
    with pytest.raises(ValueError) as exc:
        parse_command(data)
    assert "does not belong to category" in str(exc.value)


def test_parse_severity_band_mismatch():
    data = {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Test Citizen",
        "citizen_contact": "+91 9999999999",
        "raw_text": "Pothole on road",
        "latitude": 16.7,
        "longitude": 74.2,
        "address_text": "Some road",
        "category": "ROADS",
        "issue": "POTHOLE",
        "category_confidence": 0.95,
        "civic_relevance": "HIGH",
        "severity_score": 2,
        "severity_level": "CRITICAL",  # Score 2 is LOW band, not CRITICAL
        "priority": "HIGH",
        "severity_factors": [],
        "department_code": "ROADS",
        "structured_summary": "Pothole",
        "ai_reasoning": {},
        "outcome": "CLASSIFIED",
    }
    with pytest.raises(ValueError) as exc:
        parse_command(data)
    assert "does not match expected band" in str(exc.value)


def test_parse_invalid_priority():
    data = {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Test Citizen",
        "citizen_contact": "+91 9999999999",
        "raw_text": "Pothole on road",
        "latitude": 16.7,
        "longitude": 74.2,
        "address_text": "Some road",
        "category": "ROADS",
        "issue": "POTHOLE",
        "category_confidence": 0.95,
        "civic_relevance": "HIGH",
        "severity_score": 6,
        "severity_level": "HIGH",
        "priority": "SUPER_URGENT",  # Invalid priority
        "severity_factors": [],
        "department_code": "ROADS",
        "structured_summary": "Pothole",
        "ai_reasoning": {},
        "outcome": "CLASSIFIED",
    }
    with pytest.raises(ValueError) as exc:
        parse_command(data)
    assert "Priority 'SUPER_URGENT' is invalid" in str(exc.value)


def test_parse_merged_outcome_requires_merge_into_id():
    data = {
        "command": "CREATE_COMPLAINT",
        "citizen_name": "Test Citizen",
        "citizen_contact": "+91 9999999999",
        "raw_text": "Pothole on road",
        "latitude": 16.7,
        "longitude": 74.2,
        "address_text": "Some road",
        "category": "ROADS",
        "issue": "POTHOLE",
        "category_confidence": 0.95,
        "civic_relevance": "HIGH",
        "severity_score": 6,
        "severity_level": "HIGH",
        "priority": "HIGH",
        "severity_factors": [],
        "department_code": "ROADS",
        "structured_summary": "Pothole",
        "ai_reasoning": {},
        "outcome": "MERGED",
        # missing merge_into_id
    }
    with pytest.raises(ValueError) as exc:
        parse_command(data)
    assert "merge_into_id is required" in str(exc.value)


def test_parse_link_cluster_mutually_exclusive():
    with pytest.raises(ValueError) as exc:
        parse_command({
            "command": "LINK_CLUSTER",
            "complaint_id": "c1",
            "kind": "DUPLICATE",
            "cluster_id": 1,
            "new_cluster": {"lat": 16.7, "lng": 74.2, "hypothesis": "h", "confidence": 0.9},
            "confidence": 0.9,
            "reasoning": "Both provided",
        })
    assert "Exactly one of cluster_id or new_cluster" in str(exc.value)


def test_parse_submit_resolution_empty_evidence():
    with pytest.raises(ValueError):
        parse_command({
            "command": "SUBMIT_RESOLUTION",
            "complaint_id": "c1",
            "officer_id": 1,
            "description": "Fixed",
            "after_evidence_ids": [],
        })
