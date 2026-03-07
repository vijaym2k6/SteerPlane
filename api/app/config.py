"""
SteerPlane API — Configuration

App settings via environment variables.
"""

import os


class Settings:
    """Application settings."""
    APP_NAME: str = "SteerPlane API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./steerplane.db")
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
