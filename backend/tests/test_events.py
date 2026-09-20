import pytest
from backend.app.events import AuditLogImmutableError, log_event
from backend.app.models import ComplaintEvent


def test_log_event_creates_record(db):
    complaint_id = "c0000001-0000-0000-0000-000000000001"
    evt = log_event(
        db=db,
        complaint_id=complaint_id,
        actor="CITIZEN",
        action="TEST_ACTION",
        detail={"info": "sample"},
        reasoning="Testing audit log creation",
        confidence=0.99,
    )
    assert evt.id is not None
    assert evt.action == "TEST_ACTION"
    assert evt.actor == "CITIZEN"
    assert evt.confidence == 0.99


def test_complaint_event_append_only_prevent_update(db):
    complaint_id = "c0000001-0000-0000-0000-000000000001"
    evt = log_event(
        db=db,
        complaint_id=complaint_id,
        actor="SYSTEM",
        action="INITIAL_ACTION",
    )
    db.commit()

    # Attempt to modify an existing audit log entry
    evt.action = "ILLEGALLY_MODIFIED_ACTION"
    with pytest.raises(AuditLogImmutableError):
        db.flush()
    db.rollback()


def test_complaint_event_append_only_prevent_delete(db):
    complaint_id = "c0000001-0000-0000-0000-000000000001"
    evt = log_event(
        db=db,
        complaint_id=complaint_id,
        actor="SYSTEM",
        action="TO_BE_DELETED",
    )
    db.commit()

    # Attempt to delete an existing audit log entry
    db.delete(evt)
    with pytest.raises(AuditLogImmutableError):
        db.flush()
    db.rollback()
