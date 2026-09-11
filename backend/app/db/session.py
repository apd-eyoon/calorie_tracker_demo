"""Database engine / session management.

The connection string is read from the ``DATABASE_URL`` environment variable,
e.g. ``postgresql+psycopg2://calorie:calorie@db:5432/calorie``.
"""

from __future__ import annotations

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@db:5432/calorie"


def normalize_database_url(url: str) -> str:
    """Normalize a Postgres URL so SQLAlchemy always gets an explicit driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str:
    """Return the effective database URL for the running process."""
    return normalize_database_url(
        os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    )


engine: Engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a transactional :class:`Session`."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
