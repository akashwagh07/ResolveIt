from enum import Enum
from typing import Any, Optional
from sqlalchemy.orm import Session

from .clock import now as clock_now
from .events import log_event
from .models import Complaint


class Status(str, Enum):
    # Main workflow
    SUBMITTED = "SUBMITTED"
    AI_ANALYZING = "AI_ANALYZING"
    CLASSIFIED = "CLASSIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLUTION_SUBMITTED = "RESOLUTION_SUBMITTED"
    AI_VERIFICATION = "AI_VERIFICATION"
    ADMIN_VERIFICATION = "ADMIN_VERIFICATION"
    CITIZEN_CONFIRMATION = "CITIZEN_CONFIRMATION"
    RESOLVED = "RESOLVED"

    # Other states
    HUMAN_REVIEW = "HUMAN_REVIEW"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    MERGED = "MERGED"
    ESCALATED = "ESCALATED"
    REOPENED = "REOPENED"
    ERROR = "ERROR"


TERMINAL_STATES = {
    Status.RESOLVED,
    Status.OUT_OF_SCOPE,
    Status.MERGED,
}

ACTIVE_STATES = {status for status in Status if status not in TERMINAL_STATES and status != Status.ESCALATED}

ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.SUBMITTED: {Status.AI_ANALYZING},
    Status.AI_ANALYZING: {
        Status.CLASSIFIED,
        Status.HUMAN_REVIEW,
        Status.OUT_OF_SCOPE,
        Status.MERGED,
        Status.ERROR,
    },
    Status.HUMAN_REVIEW: {Status.CLASSIFIED, Status.OUT_OF_SCOPE},
    Status.CLASSIFIED: {Status.UNDER_REVIEW},
    Status.UNDER_REVIEW: {Status.ASSIGNED},
    Status.ASSIGNED: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.RESOLUTION_SUBMITTED},
    Status.RESOLUTION_SUBMITTED: {Status.AI_VERIFICATION},
    Status.AI_VERIFICATION: {Status.ADMIN_VERIFICATION, Status.IN_PROGRESS},
    Status.ADMIN_VERIFICATION: {Status.CITIZEN_CONFIRMATION, Status.IN_PROGRESS},
    Status.CITIZEN_CONFIRMATION: {Status.RESOLVED, Status.REOPENED},
    Status.REOPENED: {Status.IN_PROGRESS},
    Status.ERROR: {Status.AI_ANALYZING},
    Status.RESOLVED: set(),
    Status.OUT_OF_SCOPE: set(),
    Status.MERGED: set(),
    Status.ESCALATED: set(),  # dynamically resolved by previous_status
}


class InvalidTransition(Exception):
    """Raised when a state machine transition is not allowed."""
    pass


def can_transition(
    from_status: Status | str,
    to_status: Status | str,
    previous_status: Optional[Status | str] = None,
) -> bool:
    """Check whether a transition between two statuses is valid."""
    try:
        from_s = Status(from_status)
        to_s = Status(to_status)
    except ValueError:
        return False

    # Any active state can move to ESCALATED
    if to_s == Status.ESCALATED:
        return from_s in ACTIVE_STATES

    # ESCALATED can only return to previous_status
    if from_s == Status.ESCALATED:
        if not previous_status:
            return False
        try:
            prev_s = Status(previous_status)
            return to_s == prev_s
        except ValueError:
            return False

    return to_s in ALLOWED_TRANSITIONS.get(from_s, set())


def transition(
    db: Session,
    complaint: Complaint,
    new_status: Status | str,
    actor: str,
    reasoning: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> Complaint:
    """Validate and perform state transition on a complaint, writing an audit event."""
    try:
        to_s = Status(new_status)
    except ValueError:
        raise InvalidTransition(f"Invalid status value: {new_status}")

    current_status = Status(complaint.status)

    if not can_transition(current_status, to_s, complaint.previous_status):
        raise InvalidTransition(
            f"Cannot transition complaint from {current_status.value} to {to_s.value} "
            f"(previous_status: {complaint.previous_status})"
        )

    old_status_val = complaint.status

    if to_s == Status.ESCALATED:
        complaint.previous_status = old_status_val
        complaint.escalation_level = (complaint.escalation_level or 0) + 1
    elif current_status == Status.ESCALATED:
        # Returning from ESCALATED back to previous_status
        complaint.previous_status = Status.ESCALATED.value
    else:
        complaint.previous_status = old_status_val

    complaint.status = to_s.value
    complaint.updated_at = clock_now()

    if to_s == Status.RESOLVED:
        complaint.resolved_at = clock_now()

    event_detail: dict[str, Any] = {
        "from_status": old_status_val,
        "to_status": to_s.value,
    }
    if detail:
        event_detail.update(detail)

    log_event(
        db=db,
        complaint_id=complaint.id,
        actor=actor,
        action="STATE_TRANSITION",
        detail=event_detail,
        reasoning=reasoning,
    )

    db.flush()
    return complaint
