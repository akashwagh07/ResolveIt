"""Tests for Agent 2: Deterministic decision making and command generation."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.agents.agent1 import (
    Agent1Output,
    Agent1Result,
    EvidenceFlags,
    LocationResult,
)
from backend.app.agents.agent2 import Agent2Input, decide
from backend.app.commands import Actor, parse_command
from backend.app.database import Base
from backend.app.executor import execute_command
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


def _make_agent1_result(
    category: str = "ROADS",
    issue: str = "POTHOLE",
    confidence: float = 0.95,
    civic_relevance: str = "HIGH",
    relevance_reason: str = "Civic public road hazard",
    description: str = "Pothole on main road.",
    duration_days: float | None = None,
    size_hint: str = "MEDIUM",
    context_tags: list[str] | None = None,
) -> Agent1Result:
    out = Agent1Output(
        civic_relevance=civic_relevance,
        relevance_reason=relevance_reason,
        category=category,
        issue=issue,
        description=description,
        duration_days=duration_days,
        size_hint=size_hint,
        context_tags=context_tags or [],
        confidence=confidence,
        confidence_reason="Clear report",
        observations=[],
        missing_info=[],
        alternatives=[],
    )
    return Agent1Result(
        output=out,
        location=LocationResult(latitude=16.70, longitude=74.24, address_text="Main Chowk", source="TEXT"),
        evidence_flags=EvidenceFlags(text=True, image=False, audio=False, video=False),
        model_used="gemini-3.6-flash",
        cached=False,
        latency_ms=10.0,
        warnings=[],
    )


def test_outcome_1_ai_unavailable(db_session):
    inp = Agent2Input(
        agent1=None,
        citizen_name="Citizen One",
        citizen_contact="+91 9999999991",
        raw_text="Random text when AI down",
        latitude=16.70,
        longitude=74.24,
        ai_unavailable=True,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "HUMAN_REVIEW"
    assert dec.needs_review is True
    assert "AI unavailable" in dec.review_reasons
    assert dec.command.category == "OTHER"
    assert dec.command.issue == "OTHER"
    assert dec.command.category_confidence == 0.0

    # Parse and execute through executor
    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "HUMAN_REVIEW"


def test_outcome_2_civic_relevance_low_out_of_scope(db_session):
    a1 = _make_agent1_result(
        category="OTHER",
        issue="OTHER",
        civic_relevance="LOW",
        relevance_reason="Private domestic property repair",
        confidence=0.95,
    )
    inp = Agent2Input(
        agent1=a1,
        citizen_name="Citizen Two",
        citizen_contact="+91 9999999992",
        raw_text="Fix tap in private kitchen",
        latitude=16.70,
        longitude=74.24,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "OUT_OF_SCOPE"
    assert dec.severity.score == 0
    assert dec.severity.level == "LOW"
    assert dec.priority.priority == "NORMAL"
    assert any("Private domestic property repair" in t for t in dec.trace)

    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "OUT_OF_SCOPE"


def test_outcome_3_category_other_human_review(db_session):
    a1 = _make_agent1_result(
        category="OTHER",
        issue="OTHER",
        civic_relevance="HIGH",
        relevance_reason="Unusual public obstruction",
        confidence=0.90,
    )
    inp = Agent2Input(
        agent1=a1,
        citizen_name="Citizen Three",
        citizen_contact="+91 9999999993",
        raw_text="Unusual object on public ground",
        latitude=16.70,
        longitude=74.24,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "HUMAN_REVIEW"
    assert dec.needs_review is True

    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "HUMAN_REVIEW"


def test_outcome_4_confidence_below_0_60_human_review(db_session):
    a1 = _make_agent1_result(
        category="ROADS",
        issue="POTHOLE",
        confidence=0.55,
        civic_relevance="HIGH",
    )
    inp = Agent2Input(
        agent1=a1,
        citizen_name="Citizen Four",
        citizen_contact="+91 9999999994",
        raw_text="Unclear blurry photo and text",
        latitude=16.70,
        longitude=74.24,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "HUMAN_REVIEW"
    assert dec.needs_review is True

    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "HUMAN_REVIEW"


def test_outcome_5_classified_with_0_7_confidence_needs_review(db_session):
    # Confidence in review band [0.60, 0.84] -> CLASSIFIED with needs_review=True
    a1 = _make_agent1_result(
        category="WATER",
        issue="WATER_LEAKAGE",
        confidence=0.70,
        civic_relevance="HIGH",
        size_hint="MEDIUM",
    )
    inp = Agent2Input(
        agent1=a1,
        citizen_name="Citizen Five",
        citizen_contact="+91 9999999995",
        raw_text="Water pipe leaking moderately",
        latitude=16.70,
        longitude=74.24,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "CLASSIFIED"
    assert dec.needs_review is True

    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "CLASSIFIED"


def test_outcome_5_high_confidence_classified(db_session):
    # Confidence >= 0.85 -> CLASSIFIED with needs_review=False
    a1 = _make_agent1_result(
        category="WASTE",
        issue="GARBAGE_NOT_COLLECTED",
        confidence=0.95,
        civic_relevance="HIGH",
        size_hint="LARGE",
    )
    inp = Agent2Input(
        agent1=a1,
        citizen_name="Citizen Six",
        citizen_contact="+91 9999999996",
        raw_text="Garbage pile outside community hall",
        latitude=16.70,
        longitude=74.24,
    )
    dec = decide(db_session, inp)
    assert dec.outcome == "CLASSIFIED"
    assert dec.needs_review is False
    assert len(dec.trace) > 0
    assert "thresholds_used" in dec.command.ai_reasoning
    assert "decision_trace" in dec.command.ai_reasoning

    parsed = parse_command(dec.command.model_dump())
    res = execute_command(db_session, parsed, Actor.AGENT2)
    assert res.ok is True
    assert res.new_status == "CLASSIFIED"


def test_address_text_resolution_precedence(db_session):
    a1 = _make_agent1_result()
    a1.location = LocationResult(latitude=16.70, longitude=74.24, address_text="Agent1 Extracted Address", source="TEXT")

    # 1. Citizen address provided -> wins over Agent 1 address
    inp1 = Agent2Input(
        agent1=a1,
        citizen_name="Citizen A",
        citizen_contact="+91 9999999901",
        raw_text="Road issue",
        latitude=16.70,
        longitude=74.24,
        address_text="Citizen Explicit Address",
    )
    dec1 = decide(db_session, inp1)
    assert dec1.command.address_text == "Citizen Explicit Address"

    # 2. Citizen address None -> falls back to Agent 1 address
    inp2 = Agent2Input(
        agent1=a1,
        citizen_name="Citizen B",
        citizen_contact="+91 9999999902",
        raw_text="Road issue",
        latitude=16.70,
        longitude=74.24,
        address_text=None,
    )
    dec2 = decide(db_session, inp2)
    assert dec2.command.address_text == "Agent1 Extracted Address"

    # 3. Neither provided -> falls back to coordinates
    a1_no_addr = _make_agent1_result()
    a1_no_addr.location = LocationResult(latitude=16.70123, longitude=74.24567, address_text=None, source="GPS")
    inp3 = Agent2Input(
        agent1=a1_no_addr,
        citizen_name="Citizen C",
        citizen_contact="+91 9999999903",
        raw_text="Road issue",
        latitude=16.70123,
        longitude=74.24567,
        address_text="",
    )
    dec3 = decide(db_session, inp3)
    assert dec3.command.address_text == "Coordinates: 16.70123, 74.24567"


def test_triage_department_assignment_for_out_of_scope_and_other(db_session):
    # OUT_OF_SCOPE routes to SANITATION (triage department)
    a1_oos = _make_agent1_result(civic_relevance="LOW", relevance_reason="Irrelevant")
    inp_oos = Agent2Input(
        agent1=a1_oos,
        citizen_name="Citizen OOS",
        citizen_contact="+91 9999999911",
        raw_text="Non-civic question",
        latitude=16.70,
        longitude=74.24,
    )
    dec_oos = decide(db_session, inp_oos)
    assert dec_oos.outcome == "OUT_OF_SCOPE"
    assert dec_oos.department_code == "SANITATION"
    assert dec_oos.command.department_code == "SANITATION"

    # Category OTHER routes to SANITATION (triage department)
    a1_other = _make_agent1_result(category="OTHER", issue="OTHER", civic_relevance="HIGH")
    inp_other = Agent2Input(
        agent1=a1_other,
        citizen_name="Citizen Other",
        citizen_contact="+91 9999999912",
        raw_text="Unusual issue",
        latitude=16.70,
        longitude=74.24,
    )
    dec_other = decide(db_session, inp_other)
    assert dec_other.outcome == "HUMAN_REVIEW"
    assert dec_other.department_code == "SANITATION"
    assert dec_other.command.department_code == "SANITATION"
