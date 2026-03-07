"""
SteerPlane API — Run Model

SQLAlchemy ORM model for the runs table.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..db.base import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(String(50), primary_key=True, index=True)
    agent_name = Column(String(200), nullable=False, default="default_agent")
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed, terminated
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    total_cost = Column(Float, nullable=False, default=0.0)
    total_steps = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    max_cost_usd = Column(Float, nullable=False, default=50.0)
    max_steps_limit = Column(Integer, nullable=False, default=200)
    error = Column(Text, nullable=True)

    # Relationship to steps
    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan", order_by="Step.step_number")

    def __repr__(self):
        return f"<Run(id={self.id}, agent={self.agent_name}, status={self.status})>"
