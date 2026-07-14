"""Data-plane auth tests for /runs (STEERPLANE_REQUIRE_RUN_AUTH).

Default (off): keyless calls work and are warn-logged; runs are stamped when a
key is presented. Enforced (on): missing creds are rejected, admin is superuser,
and non-admin keys see only their own runs plus NULL-owned (legacy) runs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.config import settings
from api.app.db.base import Base
from api.app.db.database import get_db
from api.app.main import app
from api.app.models.api_key import APIKey, generate_api_key, hash_api_key


@pytest.fixture
def db_session():
    # StaticPool keeps a single shared connection so create_all and the request
    # sessions all see the same in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_require_auth():
    original = settings.REQUIRE_RUN_AUTH
    yield
    settings.REQUIRE_RUN_AUTH = original


def _make_key(db, name: str) -> str:
    raw = generate_api_key()
    key = APIKey(name=name, key_hash=hash_api_key(raw), key_prefix=raw[:14])
    db.add(key)
    db.commit()
    db.refresh(key)
    return raw, key.id


def _start(client, run_id, headers=None):
    return client.post(
        "/runs/start",
        json={"run_id": run_id, "agent_name": "bot", "max_cost_usd": 10, "max_steps": 50},
        headers=headers or {},
    )


# ── Default mode (auth off) ──────────────────────────────────────────────


def test_keyless_start_is_allowed_and_unowned(client, db_session):
    settings.REQUIRE_RUN_AUTH = False
    resp = _start(client, "run-anon")
    assert resp.status_code == 200

    from api.app.models.run import Run

    run = db_session.query(Run).filter(Run.id == "run-anon").first()
    assert run.api_key_id is None


def test_key_stamps_run_owner(client, db_session):
    settings.REQUIRE_RUN_AUTH = False
    raw, key_id = _make_key(db_session, "sdk-key")
    resp = _start(client, "run-owned", headers={"Authorization": f"Bearer {raw}"})
    assert resp.status_code == 200

    from api.app.models.run import Run

    run = db_session.query(Run).filter(Run.id == "run-owned").first()
    assert run.api_key_id == key_id


# ── Enforced mode (auth on) ──────────────────────────────────────────────


def test_enforced_requires_credentials(client):
    settings.REQUIRE_RUN_AUTH = True
    assert _start(client, "run-x").status_code == 401


def test_enforced_admin_is_superuser(client):
    settings.REQUIRE_RUN_AUTH = True
    headers = {settings.ADMIN_TOKEN_HEADER: settings.ADMIN_TOKEN}
    assert _start(client, "run-admin", headers=headers).status_code == 200


def test_enforced_strict_ownership_and_null_admin_only(client, db_session):
    """H3: non-admin keys see strictly their own runs; NULL-owned (legacy) runs
    are visible to admin only."""
    settings.REQUIRE_RUN_AUTH = True
    raw_a, _ = _make_key(db_session, "key-a")
    raw_b, _ = _make_key(db_session, "key-b")
    auth_a = {"Authorization": f"Bearer {raw_a}"}
    auth_b = {"Authorization": f"Bearer {raw_b}"}
    admin = {settings.ADMIN_TOKEN_HEADER: settings.ADMIN_TOKEN}

    # A NULL-owned legacy run exists (created while auth was off).
    settings.REQUIRE_RUN_AUTH = False
    _start(client, "run-legacy")
    settings.REQUIRE_RUN_AUTH = True

    assert _start(client, "run-a", headers=auth_a).status_code == 200
    assert _start(client, "run-b", headers=auth_b).status_code == 200

    # Reads: own=200, other=403, legacy NULL=403 for non-admin.
    assert client.get("/runs/run-a", headers=auth_a).status_code == 200
    assert client.get("/runs/run-a", headers=auth_b).status_code == 403
    assert client.get("/runs/run-legacy", headers=auth_b).status_code == 403

    # B's list shows strictly its own run — no A, no legacy.
    b_ids = {r["id"] for r in client.get("/runs", headers=auth_b).json()["runs"]}
    assert b_ids == {"run-b"}

    # Admin sees everything, including the legacy NULL-owned run.
    admin_ids = {r["id"] for r in client.get("/runs", headers=admin).json()["runs"]}
    assert {"run-a", "run-b", "run-legacy"} <= admin_ids


def test_enforced_write_ownership_step_and_end(client, db_session):
    """H2: writes are authorized by ownership — own=200, other=403, admin=200."""
    settings.REQUIRE_RUN_AUTH = True
    raw_a, _ = _make_key(db_session, "key-a")
    raw_b, _ = _make_key(db_session, "key-b")
    auth_a = {"Authorization": f"Bearer {raw_a}"}
    auth_b = {"Authorization": f"Bearer {raw_b}"}
    admin = {settings.ADMIN_TOKEN_HEADER: settings.ADMIN_TOKEN}

    _start(client, "run-a", headers=auth_a)

    step = {"run_id": "run-a", "step_number": 1, "action": "search"}
    assert client.post("/runs/step", json=step, headers=auth_a).status_code == 200
    assert client.post("/runs/step", json=step, headers=auth_b).status_code == 403
    assert client.post("/runs/step", json=step, headers=admin).status_code == 200

    end = {"run_id": "run-a", "status": "completed"}
    assert client.post("/runs/end", json=end, headers=auth_b).status_code == 403
    assert client.post("/runs/end", json=end, headers=auth_a).status_code == 200
