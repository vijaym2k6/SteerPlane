"""
SteerPlane API — Step Model

SQLAlchemy ORM model for the steps table.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from ..db.base import Base


class Step(Base):
    __tablename__ = "steps"

    id = Column(String(50), primary_key=True, default=lambda: f"step_{uuid.uuid4().hex[:8]}")
    run_id = Column(String(50), ForeignKey("runs.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    action = Column(String(200), nullable=False)
    tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="completed")  # completed, failed, terminated
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to run
    run = relationship("Run", back_populates="steps")

    def __repr__(self):
        return f"<Step(id={self.id}, run={self.run_id}, step={self.step_number}, action={self.action})>"
