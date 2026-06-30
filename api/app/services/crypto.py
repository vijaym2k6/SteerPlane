"""Symmetric encryption for server-side provider-key vaulting.

Provider keys are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256). The
Fernet key is derived from ``STEERPLANE_SECRET_KEY`` with PBKDF2-HMAC-SHA256 so
the operator can supply any sufficiently-random secret string rather than a
base64 Fernet key.

The derivation is deterministic (fixed app salt) so the same secret always
yields the same key — that is what lets the server decrypt across restarts. The
flip side: rotating ``STEERPLANE_SECRET_KEY`` makes every previously-vaulted key
unrecoverable, so operators must re-enter provider keys after a rotation. The
secret is never auto-generated: if it is unset, vaulting is simply disabled.
Plaintext provider keys are never stored or logged.
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Fixed, app-specific salt: derivation must be deterministic so restarts can
# decrypt. (A random per-record salt would need to be stored alongside the
# ciphertext; a fixed salt keeps the at-rest format a single opaque token.)
_KDF_SALT = b"steerplane:provider-key-vault:v1"
_KDF_ITERATIONS = 600_000


class VaultError(Exception):
    """Raised when the vault is unusable (no secret set, or decryption fails)."""


def _secret() -> str:
    return os.getenv("STEERPLANE_SECRET_KEY", "").strip()


def vault_enabled() -> bool:
    """True if a secret is configured, so provider keys can be vaulted."""
    return bool(_secret())


@lru_cache(maxsize=8)
def _build_fernet(secret: str) -> Fernet:
    """Derive (once per process, per secret) a Fernet from the operator secret."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITERATIONS,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(derived)


def _fernet() -> Fernet:
    secret = _secret()
    if not secret:
        raise VaultError("STEERPLANE_SECRET_KEY is not set; provider-key vaulting is disabled")
    return _build_fernet(secret)


def encrypt(plaintext: str) -> str:
    """Encrypt a provider key for storage. Raises VaultError if no secret is set."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a stored provider key. Raises VaultError on a bad token/secret."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise VaultError("Could not decrypt provider key (wrong or rotated secret)") from exc
