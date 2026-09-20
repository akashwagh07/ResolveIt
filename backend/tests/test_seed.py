from backend.app.models import Complaint, Department, User
from backend.app.seed import seed_database


def test_seed_is_idempotent(db):
    initial_dept_count = db.query(Department).count()
    initial_user_count = db.query(User).count()
    initial_complaint_count = db.query(Complaint).count()

    assert initial_dept_count == 10
    assert initial_user_count == 11  # 1 Admin + 10 Officers
    assert initial_complaint_count == 6

    # Run seed again
    seed_database(db)

    assert db.query(Department).count() == initial_dept_count
    assert db.query(User).count() == initial_user_count
    assert db.query(Complaint).count() == initial_complaint_count


def test_seed_departments_upserts_existing_database(db):
    # Simulate an existing database where SANITATION did not have OTHER
    san_dept = db.query(Department).filter_by(code="SANITATION").first()
    assert san_dept is not None
    assert "OTHER" in san_dept.categories

    # Modify the department in DB
    san_dept.categories = ["SANITATION"]
    db.commit()

    # Re-run seed_departments to simulate picking up departments.json edits
    from backend.app.seed import seed_departments
    seed_departments(db)
    db.commit()

    reloaded = db.query(Department).filter_by(code="SANITATION").first()
    assert "OTHER" in reloaded.categories


def test_seeded_complaints_sla_deadlines(db):
    active_complaints = db.query(Complaint).filter(Complaint.status != "RESOLVED").all()
    assert len(active_complaints) == 5
    for c in active_complaints:
        assert c.sla_deadline is not None, f"Complaint {c.id} with status {c.status} missing sla_deadline"

    resolved_complaint = db.query(Complaint).filter(Complaint.status == "RESOLVED").first()
    assert resolved_complaint is not None
    assert resolved_complaint.sla_deadline is None
