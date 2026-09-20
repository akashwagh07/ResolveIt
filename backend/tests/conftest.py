import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.clock import reset as clock_reset
from backend.app.database import Base, SessionLocal, get_db
from backend.app.main import app
from backend.app.seed import seed_database


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal.configure(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db(test_engine):
    """Provides a clean seeded database session for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    clock_reset()
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()
