"""
SteerPlane API — API Key Model

SQLAlchemy ORM model for the api_keys table.
Stores gateway API keys with associated limits and metadata.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from datetime import datetime, timezone
import uuid
import hashlib
import secrets


from ..db.base import Base


def generate_api_key() -> str:
    """Generate a new API key with sk_sp_ prefix."""
    return f"sk_sp_{secrets.token_hex(24)}"


def hash_api_key(key: str) -> str:
    """SHA-256 hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(50), primary_key=True, default=lambda: f"key_{uuid.uuid4().hex[:12]}")
    name = Column(String(200), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(16), nullable=False)  # e.g. "sk_sp_a1b2c3..."

    # Limits
    max_cost_usd = Column(Float, nullable=False, default=50.0)       # Per-session cost ceiling
    max_cost_monthly = Column(Float, nullable=False, default=500.0)   # Monthly budget
    max_requests_per_min = Column(Integer, nullable=False, default=60)

    # Usage tracking
    total_requests = Column(Integer, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0.0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Policy: allowed models (JSON would be better, but keeping it simple)
    allowed_models = Column(Text, nullable=True)  # Comma-separated, e.g. "gpt-4o,claude-3-sonnet"
    denied_models = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"
