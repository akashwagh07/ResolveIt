import pytest
from backend.app.models import Complaint
from backend.app.state_machine import (
    InvalidTransition,
    Status,
    can_transition,
    transition,
)


def test_can_transition_basic():
    # Direct valid transitions
    assert can_transition(Status.SUBMITTED, Status.AI_ANALYZING) is True
    assert can_transition(Status.AI_ANALYZING, Status.CLASSIFIED) is True
    assert can_transition(Status.AI_VERIFICATION, Status.IN_PROGRESS) is True
    assert can_transition(Status.CITIZEN_CONFIRMATION, Status.REOPENED) is True

    # Invalid transitions
    assert can_transition(Status.SUBMITTED, Status.RESOLVED) is False
    assert can_transition(Status.RESOLVED, Status.IN_PROGRESS) is False
    assert can_transition(Status.OUT_OF_SCOPE, Status.ASSIGNED) is False


def test_escalation_transitions():
    # Any active state can move to ESCALATED
    assert can_transition(Status.IN_PROGRESS, Status.ESCALATED) is True
    assert can_transition(Status.ASSIGNED, Status.ESCALATED) is True
    assert can_transition(Status.SUBMITTED, Status.ESCALATED) is True

    # Terminal states cannot move to ESCALATED
    assert can_transition(Status.RESOLVED, Status.ESCALATED) is False
    assert can_transition(Status.OUT_OF_SCOPE, Status.ESCALATED) is False
    assert can_transition(Status.MERGED, Status.ESCALATED) is False

    # ESCALATED may return only to previous_status
    assert can_transition(Status.ESCALATED, Status.IN_PROGRESS, previous_status=Status.IN_PROGRESS) is True
    assert can_transition(Status.ESCALATED, Status.RESOLVED, previous_status=Status.IN_PROGRESS) is False
    assert can_transition(Status.ESCALATED, Status.ASSIGNED, previous_status=Status.IN_PROGRESS) is False


def test_transition_execution(db):
    c = db.query(Complaint).filter_by(status="CLASSIFIED").first()
    assert c is not None

    # Valid step: CLASSIFIED -> UNDER_REVIEW
    transition(db, c, Status.UNDER_REVIEW, actor="AGENT_DECIDE")
    assert c.status == Status.UNDER_REVIEW.value
    assert c.previous_status == Status.CLASSIFIED.value

    # Invalid step: UNDER_REVIEW -> RESOLVED
    with pytest.raises(InvalidTransition):
        transition(db, c, Status.RESOLVED, actor="CITIZEN")

    # Move to ESCALATED
    transition(db, c, Status.ESCALATED, actor="SCHEDULER", reasoning="SLA breach")
    assert c.status == Status.ESCALATED.value
    assert c.previous_status == Status.UNDER_REVIEW.value
    assert c.escalation_level >= 1

    # Invalid return from ESCALATED to wrong state
    with pytest.raises(InvalidTransition):
        transition(db, c, Status.IN_PROGRESS, actor="OFFICER")

    # Valid return from ESCALATED back to previous_status
    transition(db, c, Status.UNDER_REVIEW, actor="DEPARTMENT_HEAD", reasoning="Addressed escalation")
    assert c.status == Status.UNDER_REVIEW.value
