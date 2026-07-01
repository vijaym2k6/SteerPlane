"""
SteerPlane API configuration.
"""

import os
import secrets


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _parse_allowed_provider_urls() -> list[str]:
    raw = os.getenv("STEERPLANE_ALLOWED_PROVIDER_URLS", "").strip()
    if not raw:
        return []
    return [url.strip().rstrip("/") for url in raw.split(",") if url.strip()]


def _resolve_admin_token() -> tuple[str, str]:
    env_token = os.getenv("STEERPLANE_ADMIN_TOKEN", "").strip()
    if env_token:
        return env_token, "env"
    return secrets.token_urlsafe(24), "generated"


class Settings:
    """Application settings."""

    APP_NAME: str = "SteerPlane API"
    APP_VERSION: str = "0.4.1"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./steerplane.db")
    CORS_ORIGINS: list[str] = _parse_cors_origins()
    ADMIN_TOKEN_HEADER: str = "X-SteerPlane-Admin-Token"
    ADMIN_TOKEN, ADMIN_TOKEN_SOURCE = _resolve_admin_token()
    # Data-plane auth on /runs, /telemetry, /approvals/request. Default off so
    # existing keyless SDK/self-host flows keep working; when off, unauthenticated
    # calls are warn-logged. Set to "true" to enforce (admin token = superuser).
    REQUIRE_RUN_AUTH: bool = os.getenv("STEERPLANE_REQUIRE_RUN_AUTH", "false").lower() == "true"
    GATEWAY_SESSION_IDLE_SEC: int = int(os.getenv("STEERPLANE_GATEWAY_SESSION_IDLE_SEC", "1800"))
    # Optional Redis backend for gateway session + loop state (multi-worker /
    # restart-safe). Unset = in-process memory (single-worker default).
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip()
    ALLOWED_PROVIDER_URLS: list[str] = _parse_allowed_provider_urls()
    DASHBOARD_URL: str = os.getenv("STEERPLANE_DASHBOARD_URL", "http://localhost:3000").rstrip("/")
    SMTP_HOST: str = os.getenv("STEERPLANE_SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("STEERPLANE_SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("STEERPLANE_SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("STEERPLANE_SMTP_PASSWORD", "").strip()
    SMTP_FROM: str = os.getenv("STEERPLANE_SMTP_FROM", "").strip()
    SMTP_USE_TLS: bool = os.getenv("STEERPLANE_SMTP_USE_TLS", "true").lower() == "true"


settings = Settings()
