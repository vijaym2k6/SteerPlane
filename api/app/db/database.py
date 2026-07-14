"""
SteerPlane API — Database Connection

SQLAlchemy engine and session factory.
Supports both SQLite (default) and PostgreSQL.

To switch to PostgreSQL, set the environment variable:
    DATABASE_URL=postgresql://user:password@localhost:5432/steerplane

SQLite is the default for easy local development.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database URL — defaults to SQLite, easily swappable to PostgreSQL
# PostgreSQL: postgresql://steerplane:<your-password>@localhost:5432/steerplane
# SQLite:     sqlite:///./steerplane.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./steerplane.db")

# For SQLite, we need check_same_thread=False
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    # PostgreSQL-specific: pool size for production
    pool_size=10 if DATABASE_URL.startswith("postgresql") else 5,
    max_overflow=20 if DATABASE_URL.startswith("postgresql") else 0,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Bring the database schema up to the latest Alembic revision.

    Migrations are the single source of truth for the schema. We deliberately do
    NOT use ``Base.metadata.create_all()`` here: create_all() creates missing
    *tables* but never missing *columns*, so a database first built by an older
    create_all() (before a column was added) silently diverges from the models
    and 500s at query time (e.g. ``no such column: runs.api_key_id``). Running
    ``alembic upgrade head`` instead applies every pending migration, so a fresh
    database is built in full and an existing one is brought current — the same
    path the Docker ``entrypoint.sh`` already uses. It is idempotent: on a DB
    that is already at head this is a no-op.
    """
    from alembic import command
    from alembic.config import Config

    # database.py lives at api/app/db/database.py -> parents[2] is api/.
    api_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(api_root / "alembic.ini"))
    # Pin script_location and URL to absolute/current values so the upgrade
    # works regardless of the process's current working directory.
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


def get_db():
    """Dependency injection for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
