"""
SteerPlane API — Database Connection

SQLAlchemy engine and session factory.
Supports both SQLite (default) and PostgreSQL.

To switch to PostgreSQL, set the environment variable:
    DATABASE_URL=postgresql://user:password@localhost:5432/steerplane

SQLite is the default for easy local development.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .base import Base

# Database URL — defaults to SQLite, easily swappable to PostgreSQL
# PostgreSQL: postgresql://steerplane:steerplane@localhost:5432/steerplane
# SQLite:     sqlite:///./steerplane.db
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./steerplane.db"
)

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
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency injection for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
