"""Dev reset script: drops, recreates and reseeds demo database without deleting the file."""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Reset and reseed ResolveIt demo database without deleting SQLite file."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm execution of database drop, recreate and reseed.",
    )
    args = parser.parse_args()

    if not args.yes:
        print(
            "DRY RUN (no changes made):\n"
            "This script will drop and recreate all tables on the configured ResolveIt database,\n"
            "and reseed departments, users, and 6 baseline Kolhapur complaints.\n"
            "The SQLite file itself is NOT deleted, allowing live uvicorn dev servers to stay attached.\n"
            "\nTo proceed, re-run with '--yes':\n"
            "  python -m backend.scripts.reset_demo_db --yes"
        )
        sys.exit(0)

    # Enable destructive operation explicitly
    os.environ["ALLOW_DESTRUCTIVE_DB"] = "1"

    from backend.app.database import Base, SessionLocal, assert_safe_for_destructive, engine
    from backend.app.models import Complaint, Department, User
    from backend.app.seed import seed_database

    print(f"Resetting database at: {engine.url}")
    assert_safe_for_destructive(engine)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_database(db)
        dept_count = db.query(Department).count()
        user_count = db.query(User).count()
        complaint_count = db.query(Complaint).count()
        print(
            f"Successfully reset and reseeded demo database:\n"
            f"  - Departments: {dept_count}\n"
            f"  - Users: {user_count}\n"
            f"  - Complaints: {complaint_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
