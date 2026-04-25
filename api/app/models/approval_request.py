"""
SteerPlane API — Approval Request Model

Stores pending human approvals for alert-mode enforcement.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON

from ..db.base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(50), primary_key=True, default=lambda: f"apr_{uuid.uuid4().hex[:12]}")
    run_id = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(200), nullable=False, default="default_agent")
    scope = Column(String(20), nullable=False, default="sdk")  # sdk, gateway
    approval_type = Column(String(50), nullable=False)  # cost_limit, step_limit, runtime_limit
    status = Column(String(30), nullable=False, default="pending")  # pending, approved, denied, expired
    message = Column(Text, nullable=False)
    current_value = Column(Float, nullable=False, default=0.0)
    limit_value = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), nullable=False, default="count")
    timeout_sec = Column(Integer, nullable=False, default=1800)
    session_id = Column(String(80), nullable=True, index=True)
    api_key_id = Column(String(50), nullable=True, index=True)
    channels_json = Column(JSON, nullable=False, default=list)
    alert_email = Column(String(320), nullable=True)
    alert_webhook_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    resolution_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(120), nullable=True)
    resolution_note = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<ApprovalRequest(id={self.id}, run_id={self.run_id}, "
            f"type={self.approval_type}, status={self.status})>"
        )
