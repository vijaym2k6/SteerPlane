"""Symmetric encryption for server-side provider-key vaulting.

Provider keys are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256). The
Fernet key is derived from ``STEERPLANE_SECRET_KEY`` so the operator can supply
any sufficiently-random secret string rather than a base64 Fernet key. Plaintext
keys are never stored or logged.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


class VaultError(Exception):
    """Raised when the vault is unusable (no secret set, or decryption fails)."""


def _secret() -> str:
    return os.getenv("STEERPLANE_SECRET_KEY", "").strip()


def vault_enabled() -> bool:
    """True if a secret is configured, so provider keys can be vaulted."""
    return bool(_secret())


def _fernet() -> Fernet:
    secret = _secret()
    if not secret:
        raise VaultError("STEERPLANE_SECRET_KEY is not set; provider-key vaulting is disabled")
    # Derive a stable 32-byte Fernet key from an arbitrary secret string.
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    """Encrypt a provider key for storage. Raises VaultError if no secret is set."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a stored provider key. Raises VaultError on a bad token/secret."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise VaultError("Could not decrypt provider key (wrong or rotated secret)") from exc
