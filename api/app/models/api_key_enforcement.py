"""
SteerPlane API — API Key Enforcement Settings

Optional per-key configuration for alert-vs-kill gateway enforcement.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey

from ..db.base import Base


class APIKeyEnforcement(Base):
    __tablename__ = "api_key_enforcements"

    api_key_id = Column(String(50), ForeignKey("api_keys.id"), primary_key=True)
    enforcement_mode = Column(String(20), nullable=False, default="kill")
    alert_threshold = Column(Float, nullable=False, default=0.8)
    alert_timeout_sec = Column(Integer, nullable=False, default=1800)
    alert_channels_json = Column(JSON, nullable=False, default=list)
    alert_email = Column(String(320), nullable=True)
    alert_webhook_url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<APIKeyEnforcement(api_key_id={self.api_key_id}, mode={self.enforcement_mode})>"
