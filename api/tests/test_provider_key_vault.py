"""Tests for server-side provider-key vaulting (#1).

Covers crypto round-trip, the gateway's vault-primary / header-fallback
resolution, and that the plaintext key is never returned by read endpoints.
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
from api.app.services import crypto
from api.app.services.gateway_service import GatewayService

SECRET = "unit-test-secret-value"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _admin():
    return {settings.ADMIN_TOKEN_HEADER: settings.ADMIN_TOKEN}


# ── crypto ───────────────────────────────────────────────────────────────


def test_crypto_round_trip(monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    assert crypto.vault_enabled() is True
    token = crypto.encrypt("sk-provider-123")
    assert token != "sk-provider-123"
    assert crypto.decrypt(token) == "sk-provider-123"


def test_crypto_wrong_secret_raises(monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    token = crypto.encrypt("sk-provider-123")
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", "a-different-secret")
    crypto._build_fernet.cache_clear()
    with pytest.raises(crypto.VaultError):
        crypto.decrypt(token)


def test_derivation_is_stable_across_restart(monkeypatch):
    """The PBKDF2 derivation is deterministic, so a fresh process (cleared
    derivation cache) decrypts tokens written by a previous one."""
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    token = crypto.encrypt("sk-stable")

    # Simulate a restart: drop the cached Fernet and re-derive from the secret.
    crypto._build_fernet.cache_clear()
    assert crypto.decrypt(token) == "sk-stable"


def test_vault_disabled_without_secret(monkeypatch):
    monkeypatch.delenv("STEERPLANE_SECRET_KEY", raising=False)
    assert crypto.vault_enabled() is False
    with pytest.raises(crypto.VaultError):
        crypto.encrypt("x")


# ── gateway resolution ───────────────────────────────────────────────────


def test_resolve_prefers_vaulted_key(monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    key = APIKey(name="k", key_hash="c" * 64, key_prefix="sk_sp_x")
    key.provider_key_encrypted = crypto.encrypt("sk-vaulted")

    svc = GatewayService(None)
    assert svc.resolve_provider_key(key, "sk-header") == "sk-vaulted"


def test_resolve_falls_back_to_header(monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    key = APIKey(name="k", key_hash="c" * 64, key_prefix="sk_sp_x")  # no vaulted key

    svc = GatewayService(None)
    assert svc.resolve_provider_key(key, "sk-header") == "sk-header"


def test_resolve_falls_back_when_secret_missing(monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    key = APIKey(name="k", key_hash="c" * 64, key_prefix="sk_sp_x")
    key.provider_key_encrypted = crypto.encrypt("sk-vaulted")
    monkeypatch.delenv("STEERPLANE_SECRET_KEY", raising=False)

    svc = GatewayService(None)
    # Vault unusable → header fallback rather than a hard failure.
    assert svc.resolve_provider_key(key, "sk-header") == "sk-header"


# ── endpoint: set + never-leaked ─────────────────────────────────────────


def _seed_key(db) -> str:
    raw = generate_api_key()
    key = APIKey(name="prod", key_hash=hash_api_key(raw), key_prefix=raw[:14])
    db.add(key)
    db.commit()
    db.refresh(key)
    return key.id


def test_set_provider_key_then_never_returned(client, db_session, monkeypatch):
    monkeypatch.setenv("STEERPLANE_SECRET_KEY", SECRET)
    key_id = _seed_key(db_session)

    resp = client.post(
        f"/api-keys/{key_id}/provider-key",
        json={"provider_key": "sk-super-secret-upstream"},
        headers=_admin(),
    )
    assert resp.status_code == 200
    assert resp.json()["has_provider_key"] is True

    # Read endpoints must expose presence but never the value or ciphertext.
    get_resp = client.get(f"/api-keys/{key_id}", headers=_admin())
    body = get_resp.text
    assert get_resp.json()["has_provider_key"] is True
    assert "sk-super-secret-upstream" not in body
    assert "provider_key_encrypted" not in body

    list_body = client.get("/api-keys/", headers=_admin()).text
    assert "sk-super-secret-upstream" not in list_body


def test_set_provider_key_disabled_without_secret(client, db_session, monkeypatch):
    monkeypatch.delenv("STEERPLANE_SECRET_KEY", raising=False)
    key_id = _seed_key(db_session)

    resp = client.post(
        f"/api-keys/{key_id}/provider-key",
        json={"provider_key": "sk-x"},
        headers=_admin(),
    )
    assert resp.status_code == 400
