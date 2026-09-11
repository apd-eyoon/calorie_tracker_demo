"""Alembic environment - the DB URL always comes from ``DATABASE_URL``."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the application package importable (``backend/`` is the project root).
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registers all tables on Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    """Resolve the database URL from the environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            from app.db.session import get_database_url

            return get_database_url()
        except Exception:  # pragma: no cover - fall back to a sane default
            return "postgresql+psycopg2://postgres:postgres@db:5432/calorie"

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


config.set_main_option("sqlalchemy.url", _database_url().replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
