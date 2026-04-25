"""
Security helpers for admin-only routes.
"""

import secrets

from fastapi import HTTPException, Request, status

from .config import settings


def extract_admin_token(request: Request) -> str:
    """Extract an admin token from supported request headers."""
    token = request.headers.get(settings.ADMIN_TOKEN_HEADER, "").strip()
    if token:
        return token

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return ""


def require_admin(request: Request) -> None:
    """Require a valid admin token for sensitive control-plane routes."""
    provided = extract_admin_token(request)
    expected = settings.ADMIN_TOKEN

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing or invalid admin token. Send "
                f"'{settings.ADMIN_TOKEN_HEADER}: <token>'."
            ),
        )
