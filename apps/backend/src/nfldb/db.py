from __future__ import annotations

from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import get_database_url


_engine: Engine
SessionLocal: sessionmaker


def configure_engine(url: Optional[str] = None) -> None:
    """Configure the shared SQLAlchemy engine and session factory."""
    global _engine, SessionLocal
    engine_url = url or get_database_url()
    _engine = create_engine(engine_url, future=True)
    SessionLocal = sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        autoflush=False,
    )


configure_engine()


def get_engine() -> Engine:
    """Return shared SQLAlchemy engine."""
    return _engine


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
