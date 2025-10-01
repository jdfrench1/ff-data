from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_database_url


_engine = create_engine(get_database_url(), future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)


def get_engine():
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
