"""Tests for PostgreSQL driver selection in DATABASE_URL."""

import pytest
from sqlalchemy import create_engine

from api.app.db.url import mask_database_password, resolve_database_url


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


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgresql://u:s3cret@db:5432/sp", "postgresql://u:***@db:5432/sp"),
        ("postgresql+psycopg2://u:s3cret@db/sp", "postgresql+psycopg2://u:***@db/sp"),
        ("sqlite:///./steerplane.db", "sqlite:///./steerplane.db"),
    ],
)
def test_mask_database_password(raw, expected):
    assert mask_database_password(raw) == expected


def test_mask_never_echoes_an_unparseable_url():
    out = mask_database_password("not a url but has s3cret in it")
    assert "s3cret" not in out


def test_startup_banner_hides_the_password(monkeypatch, capsys):
    import asyncio

    from api.app import main

    monkeypatch.setattr(main.settings, "DATABASE_URL", "postgresql://u:s3cret@db:5432/sp")
    monkeypatch.setattr(main, "init_db", lambda: None)

    async def run_lifespan():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run_lifespan())
    out = capsys.readouterr().out
    assert "s3cret" not in out
    assert "postgresql://u:***@db:5432/sp" in out
