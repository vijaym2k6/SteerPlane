"""Tests for PostgreSQL driver selection in DATABASE_URL."""

import pytest
from sqlalchemy import create_engine

from api.app.db.url import resolve_database_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            "postgresql://u:p@db:5432/steerplane",
            "postgresql+psycopg2://u:p@db:5432/steerplane",
        ),
        (
            "postgres://u:p@db:5432/steerplane",
            "postgresql+psycopg2://u:p@db:5432/steerplane",
        ),
        (
            "postgresql+psycopg2://u:p@db:5432/steerplane",
            "postgresql+psycopg2://u:p@db:5432/steerplane",
        ),
        (
            "postgresql+psycopg://u:p@db:5432/steerplane",
            "postgresql+psycopg://u:p@db:5432/steerplane",
        ),
        ("sqlite:///./steerplane.db", "sqlite:///./steerplane.db"),
    ],
)
def test_resolve_database_url(raw, expected):
    assert resolve_database_url(raw) == expected


def test_bare_postgres_url_uses_installed_driver():
    """A bare postgresql:// URL must build an engine with psycopg2.

    Creating the engine imports the driver but does not connect, so no database
    is needed. Without the fix this raises ModuleNotFoundError on SQLAlchemy 2.1.
    """
    engine = create_engine(resolve_database_url("postgresql://u:p@localhost:5432/x"))
    assert engine.dialect.driver == "psycopg2"
    engine.dispose()
