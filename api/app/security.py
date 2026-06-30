"""
Security helpers for admin-only and data-plane routes.
"""

import logging
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .db.database import get_db
from .models.api_key import APIKey, hash_api_key

logger = logging.getLogger("steerplane")


def extract_admin_token(request: Request) -> str:
    """Extract an admin token from supported request headers."""
    token = request.headers.get(settings.ADMIN_TOKEN_HEADER, "").strip()
    if token:
        return token

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return ""


def _extract_bearer(request: Request) -> str:
    """Extract the raw Authorization: Bearer token (the SDK/gateway API key)."""
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return ""


def is_admin_request(request: Request) -> bool:
    """True if the request carries a valid admin token."""
    provided = extract_admin_token(request)
    return bool(provided) and secrets.compare_digest(provided, settings.ADMIN_TOKEN)


def require_admin(request: Request) -> None:
    """Require a valid admin token for sensitive control-plane routes."""
    if not is_admin_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Missing or invalid admin token. Send '{settings.ADMIN_TOKEN_HEADER}: <token>'."
            ),
        )


@dataclass
class RunAuthContext:
    """Resolved identity for a data-plane request.

    - ``is_admin`` → superuser, sees and writes everything.
    - ``api_key`` → the SDK/gateway key that authenticated, used to scope and
      stamp runs. ``None`` for unauthenticated callers (allowed only when
      ``STEERPLANE_REQUIRE_RUN_AUTH`` is off).
    """

    is_admin: bool = False
    api_key: APIKey | None = None

    @property
    def api_key_id(self) -> str | None:
        return self.api_key.id if self.api_key else None

    def can_write_run(self, run) -> bool:
        """Whether this identity may write to / read an existing run."""
        if self.is_admin:
            return True
        owner = getattr(run, "api_key_id", None)
        # NULL-owned (legacy/keyless) runs stay open; otherwise must match.
        return owner is None or owner == self.api_key_id


def resolve_run_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> RunAuthContext:
    """Authenticate a data-plane request (admin token or SDK/gateway API key).

    When ``STEERPLANE_REQUIRE_RUN_AUTH`` is off, missing/invalid credentials are
    allowed but warn-logged (returns an anonymous context). When on, valid
    credentials are required.
    """
    if is_admin_request(request):
        return RunAuthContext(is_admin=True)

    bearer = _extract_bearer(request)
    if bearer.startswith("sk_sp_"):
        api_key = (
            db.query(APIKey)
            .filter(APIKey.key_hash == hash_api_key(bearer), APIKey.is_active == True)  # noqa: E712
            .first()
        )
        if api_key:
            return RunAuthContext(api_key=api_key)
        if settings.REQUIRE_RUN_AUTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key",
            )

    if settings.REQUIRE_RUN_AUTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authentication required. Send a SteerPlane API key as "
                f"'Authorization: Bearer sk_sp_...' or an admin token "
                f"'{settings.ADMIN_TOKEN_HEADER}: <token>'."
            ),
        )

    logger.warning(
        "[WARN] Unauthenticated data-plane request to %s %s (STEERPLANE_REQUIRE_RUN_AUTH is off).",
        request.method,
        request.url.path,
    )
    return RunAuthContext()
