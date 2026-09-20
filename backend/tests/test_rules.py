"""Tests for deterministic rule engines: severity, priority, and department routing."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.engines.department import TRIAGE_DEPARTMENT_CODE, department_for_category
from backend.app.engines.priority import compute_priority
from backend.app.engines.severity import (
    BASE_RISK,
    compute_severity,
    severity_level_for_score,
)
from backend.app.ontology import CATEGORIES
from backend.app.seed import seed_departments


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_departments(db)
    yield db
    db.close()


def test_streetlight_not_working_no_tags_gives_score_2_low():
    res = compute_severity("STREET_LIGHTING", "LIGHT_NOT_WORKING")
    assert res.score == 2
    assert res.level == "LOW"
    assert len(res.factors) == 1
    assert res.factors[0]["factor"] == "base_risk"
    assert res.factors[0]["points"] == 2


def test_large_pothole_safety_hazard_school_7_days_gives_critical():
    res = compute_severity(
        category="ROADS",
        issue="POTHOLE",
        size_hint="LARGE",
        duration_days=7.0,
        context_tags=["SAFETY_HAZARD", "SCHOOL_NEARBY"],
    )
    # base 3 + safety 2 + large 2 + duration(7d) 1 + school 1 = 9
    assert res.score == 9
    assert res.level == "CRITICAL"

    factor_names = [f["factor"] for f in res.factors]
    assert "base_risk" in factor_names
    assert "public_safety" in factor_names
    assert "affected_area" in factor_names
    assert "duration" in factor_names
    assert "sensitive_context" in factor_names

    # Check points breakdown
    factors_by_name = {f["factor"]: f["points"] for f in res.factors}
    assert factors_by_name["base_risk"] == 3
    assert factors_by_name["public_safety"] == 2
    assert factors_by_name["affected_area"] == 2
    assert factors_by_name["duration"] == 1
    assert factors_by_name["sensitive_context"] == 1


def test_score_capped_at_10():
    res = compute_severity(
        category="STREET_LIGHTING",
        issue="FALLEN_POLE",  # 5
        size_hint="LARGE",  # +2
        duration_days=20.0,  # +2
        context_tags=[
            "SAFETY_HAZARD",  # +2
            "MAJOR_ROAD",  # +1
            "HIGH_PEDESTRIAN",  # +1
            "HOSPITAL_NEARBY",  # +1
        ],
    )
    # 5 + 2 + 2 + 2 + 1 + 1 + 1 = 14 -> capped at 10
    assert res.score == 10
    assert res.level == "CRITICAL"


def test_unmapped_issue_defaults_to_2():
    res = compute_severity("NONEXISTENT_CAT", "UNMAPPED_ISSUE_XYZ")
    assert res.score == 2
    assert res.level == "LOW"
    assert res.factors[0]["points"] == 2


def test_whole_ontology_covered_in_base_risk():
    for cat, issues in CATEGORIES.items():
        for iss in issues:
            assert iss in BASE_RISK, f"Issue {iss} in category {cat} is missing from BASE_RISK table"


def test_priority_bump_rules():
    # LOW never bumps
    low_res = compute_priority("LOW", context_tags=["SCHOOL_NEARBY"])
    assert low_res.priority == "NORMAL"

    # CRITICAL never bumps
    crit_res = compute_priority("CRITICAL", context_tags=["HOSPITAL_NEARBY"])
    assert crit_res.priority == "EMERGENCY"

    # MEDIUM bumps from STANDARD to HIGH when sensitive context present
    med_res_nobump = compute_priority("MEDIUM", context_tags=[])
    assert med_res_nobump.priority == "STANDARD"

    med_res_bump = compute_priority("MEDIUM", context_tags=["SCHOOL_NEARBY"])
    assert med_res_bump.priority == "HIGH"
    assert any(f["factor"] == "sensitive_facility_bump" for f in med_res_bump.factors)

    # HIGH bumps from HIGH to EMERGENCY when sensitive context present
    high_res_nobump = compute_priority("HIGH", context_tags=[])
    assert high_res_nobump.priority == "HIGH"

    high_res_bump = compute_priority("HIGH", context_tags=["HOSPITAL_NEARBY"])
    assert high_res_bump.priority == "EMERGENCY"
    assert any(f["factor"] == "sensitive_facility_bump" for f in high_res_bump.factors)


def test_rules_determinism():
    inp = {
        "category": "DRAINAGE",
        "issue": "SEWAGE_OVERFLOW",
        "size_hint": "MEDIUM",
        "duration_days": 10.0,
        "context_tags": ["HEALTH_HAZARD", "TRANSIT_AREA"],
    }
    s1 = compute_severity(**inp)
    s2 = compute_severity(**inp)
    assert s1.model_dump() == s2.model_dump()

    p1 = compute_priority(s1.level, inp["context_tags"])
    p2 = compute_priority(s1.level, inp["context_tags"])
    assert p1.model_dump() == p2.model_dump()


def test_department_mapping_for_every_category(db_session):
    for cat in CATEGORIES:
        dept = department_for_category(db_session, cat)
        assert dept is not None
        if cat == "OTHER":
            assert dept.code == TRIAGE_DEPARTMENT_CODE
        else:
            assert cat in dept.categories
