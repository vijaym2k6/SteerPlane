"""
SteerPlane API — Policy Model

SQLAlchemy ORM model for the policies table.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, Boolean
from datetime import datetime, timezone

from ..db.base import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Allow / deny lists stored as JSON arrays of glob patterns
    allowed_actions = Column(JSON, nullable=True)   # e.g. ["search_*", "read_*"]
    denied_actions = Column(JSON, nullable=True)     # e.g. ["delete_*", "sudo_*"]

    # Rate limits: JSON array of {action, max_calls, window_seconds}
    rate_limits = Column(JSON, nullable=True)

    # Actions requiring approval: JSON array of glob patterns
    require_approval = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Policy(id={self.id}, name={self.name}, active={self.is_active})>"
