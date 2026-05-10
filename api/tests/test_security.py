from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.app.config import settings
from api.app.security import extract_admin_token, require_admin


def _request_with_headers(headers: dict[str, str]) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
    }
    return Request(scope)


def test_extract_admin_token_prefers_custom_header():
    request = _request_with_headers(
        {
            settings.ADMIN_TOKEN_HEADER: "admin-token",
            "Authorization": "Bearer ignored",
        }
    )

    assert extract_admin_token(request) == "admin-token"


def test_require_admin_rejects_invalid_token():
    request = _request_with_headers({settings.ADMIN_TOKEN_HEADER: "wrong-token"})

    with pytest.raises(HTTPException) as exc:
        require_admin(request)

    assert exc.value.status_code == 401


def test_require_admin_accepts_valid_token():
    request = _request_with_headers({settings.ADMIN_TOKEN_HEADER: settings.ADMIN_TOKEN})

    require_admin(request)
