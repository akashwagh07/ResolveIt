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
