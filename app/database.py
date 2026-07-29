"""
Database engine and session management.

Provides a single SQLAlchemy engine + sessionmaker for the whole app,
and a `get_db()` dependency for use in FastAPI routes / handlers.

Works with both SQLite (local dev) and PostgreSQL (Railway production)
via the same DATABASE_URL-driven engine — no code changes needed when
you switch environments.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

# SQLite needs this flag when accessed from multiple threads (which
# python-telegram-bot's async handlers effectively do). Postgres doesn't
# need or accept this argument, so we only add it conditionally.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # avoids "server closed the connection" errors on Railway Postgres
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI-style dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context-manager version for use inside Telegram command handlers,
    where there's no FastAPI dependency injection available.

    Usage:
        with get_db_context() as db:
            db.query(Link)...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Creates all tables if they don't exist yet.

    Note: this is fine for getting started, but for production schema
    changes you should switch to Alembic migrations (covered later)
    rather than relying on create_all, which can't handle altering
    existing tables.
    """
    import app.models  # noqa: F401 — ensures models are registered on Base before create_all

    logger.info("Initializing database (create_all)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")
