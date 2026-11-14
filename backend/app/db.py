"""Database engine and session handling (SQLite through SQLAlchemy)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def init_db(url: str) -> Engine:
    """Create the engine, bind the session factory and create tables."""
    global _engine
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    from app import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    SessionLocal.configure(bind=engine)
    if _engine is not None and _engine is not engine:
        _engine.dispose()
    _engine = engine
    return engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database is not initialised. Call init_db() first.")
    return _engine


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
