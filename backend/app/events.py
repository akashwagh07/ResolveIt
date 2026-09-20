from typing import Any, Optional
from sqlalchemy import event
from sqlalchemy.orm import Session

from .clock import now as clock_now
from .models import ComplaintEvent


class AuditLogImmutableError(RuntimeError):
    """Raised when an attempt is made to update or delete an audit event."""
    pass


@event.listens_for(ComplaintEvent, "before_update")
def _prevent_complaint_event_update(mapper, connection, target):
    raise AuditLogImmutableError("ComplaintEvent is strictly append-only: updates are prohibited.")


@event.listens_for(ComplaintEvent, "before_delete")
def _prevent_complaint_event_delete(mapper, connection, target):
    raise AuditLogImmutableError("ComplaintEvent is strictly append-only: deletes are prohibited.")


def log_event(
    db: Session,
    complaint_id: str,
    actor: str,
    action: str,
    detail: Optional[Any] = None,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
) -> ComplaintEvent:
    """Add and flush an append-only audit event with virtual clock timestamp."""
    audit_event = ComplaintEvent(
        complaint_id=complaint_id,
        timestamp=clock_now(),
        actor=actor,
        action=action,
        detail=detail,
        reasoning=reasoning,
        confidence=confidence,
    )
    db.add(audit_event)
    db.flush()
    return audit_event
