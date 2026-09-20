import os
from pathlib import Path
import tempfile
from typing import Generator, Union
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from .config import get_settings


class Base(DeclarativeBase):
    pass


def assert_safe_for_destructive(engine_or_url: Union[Engine, str]) -> None:
    """
    Ensure the target database is safe for destructive operations (drop_all, table clearing).
    Raises RuntimeError unless the database is :memory:, located under a temp directory,
    or ALLOW_DESTRUCTIVE_DB=1 is explicitly set in the environment.
    """
    if os.getenv("ALLOW_DESTRUCTIVE_DB") == "1":
        return

    url = str(engine_or_url.url if hasattr(engine_or_url, "url") else engine_or_url)
    if ":memory:" in url or url == "sqlite://" or url == "sqlite:///:memory:":
        return

    # Extract file path from sqlite URL
    path_str = url
    if path_str.startswith("sqlite:///"):
        path_str = path_str[len("sqlite:///"):]
    elif path_str.startswith("sqlite://"):
        path_str = path_str[len("sqlite://"):]

    try:
        db_path = Path(path_str).resolve()
        temp_roots = [
            Path(tempfile.gettempdir()).resolve(),
            Path(os.environ.get("TEMP", tempfile.gettempdir())).resolve(),
            Path(os.environ.get("TMP", tempfile.gettempdir())).resolve(),
        ]
        for t_root in temp_roots:
            try:
                db_path.relative_to(t_root)
                return  # Verified inside temp directory
            except ValueError:
                continue
    except Exception:
        pass

    raise RuntimeError(
        f"Destructive operation refused: database '{url}' is not in a temporary directory "
        f"and ALLOW_DESTRUCTIVE_DB=1 is not set."
    )


settings = get_settings()
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

