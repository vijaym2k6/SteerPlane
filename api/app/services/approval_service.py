"""
Approval workflow service for alert-mode enforcement.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.api_key_enforcement import APIKeyEnforcement
from ..models.approval_request import ApprovalRequest
from ..models.run import Run
from ..models.step import Step
from .notification_service import NotificationService


DEFAULT_ENFORCEMENT_MODE = "kill"
DEFAULT_ALERT_THRESHOLD = 0.8
DEFAULT_ALERT_TIMEOUT_SEC = 1800


class ApprovalService:
    """Create, resolve, and inspect human-approval requests."""

    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationService()

    def get_or_create_api_key_enforcement(self, api_key_id: str) -> APIKeyEnforcement:
        config = (
            self.db.query(APIKeyEnforcement)
            .filter(APIKeyEnforcement.api_key_id == api_key_id)
            .first()
        )
        if config:
            return config

        config = APIKeyEnforcement(api_key_id=api_key_id)
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_api_key_enforcement(self, api_key_id: str) -> APIKeyEnforcement:
        return self.get_or_create_api_key_enforcement(api_key_id)

    def find_pending(
        self,
        run_id: str,
        approval_type: str,
        session_id: str | None = None,
    ) -> Optional[ApprovalRequest]:
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.approval_type == approval_type,
            ApprovalRequest.status == "pending",
        )
        if session_id:
            query = query.filter(ApprovalRequest.session_id == session_id)
        approval = query.order_by(ApprovalRequest.created_at.desc()).first()
        if approval:
            return self.sync_expiry(approval)
        return None

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        approval = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if approval:
            return self.sync_expiry(approval)
        return None

    def list_approvals(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        self.expire_stale_pending()
        query = self.db.query(ApprovalRequest)
        if status:
            query = query.filter(ApprovalRequest.status == status)
        return query.order_by(ApprovalRequest.created_at.desc()).limit(limit).all()

    def expire_stale_pending(self):
        pending = self.db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").all()
        for approval in pending:
            self.sync_expiry(approval)

    def sync_expiry(self, approval: ApprovalRequest) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if approval.status == "pending" and expires_at <= now:
            approval.status = "expired"
            approval.resolved_at = now
            approval.resolution_json = {
                "decision": "expired",
                "reason": "Approval timed out with no response",
            }
            self._append_resolution_step(
                approval,
                action=f"approval:expired:{approval.approval_type}",
                status="terminated",
                error="Alert timed out with no response",
            )
            self._terminate_run_for_resolution(
                approval,
                error_type="alert_timeout",
                message=(
                    f"Alert timed out for {approval.approval_type.replace('_', ' ')}. "
                    "No human response was received before the timeout."
                ),
            )
            self.db.commit()
            self.db.refresh(approval)
        return approval

    def create_approval(
        self,
        *,
        run_id: str,
        agent_name: str,
        approval_type: str,
        current_value: float,
        limit_value: float,
        unit: str,
        message: str,
        timeout_sec: int,
        scope: str = "sdk",
        session_id: str | None = None,
        api_key_id: str | None = None,
        channels: list[str] | None = None,
        alert_email: str | None = None,
        alert_webhook_url: str | None = None,
        metadata: dict | None = None,
    ) -> ApprovalRequest:
        existing = self.find_pending(run_id, approval_type, session_id=session_id)
        if existing:
            return existing

        approval = ApprovalRequest(
            run_id=run_id,
            agent_name=agent_name,
            scope=scope,
            approval_type=approval_type,
            status="pending",
            message=message,
            current_value=current_value,
            limit_value=limit_value,
            unit=unit,
            timeout_sec=timeout_sec,
            session_id=session_id,
            api_key_id=api_key_id,
            channels_json=channels or [],
            alert_email=(alert_email or "").strip() or None,
            alert_webhook_url=(alert_webhook_url or "").strip() or None,
            metadata_json=metadata or {},
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=timeout_sec),
        )
        self.db.add(approval)
        self._mark_run_awaiting_approval(approval)
        self._append_resolution_step(
            approval,
            action=f"approval_requested:{approval_type}",
            status="awaiting_approval",
            error=message,
        )
        self.db.commit()
        self.db.refresh(approval)
        self.notifications.dispatch(approval)
        return approval

    def approve(
        self,
        approval_id: str,
        *,
        resolved_by: str = "dashboard-admin",
        note: str | None = None,
        extension_value: float | None = None,
    ) -> Optional[ApprovalRequest]:
        approval = self.get_approval(approval_id)
        if not approval or approval.status != "pending":
            return approval

        extension = extension_value if extension_value is not None else approval.limit_value
        new_limit = approval.limit_value + extension
        approval.status = "approved"
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by = resolved_by
        approval.resolution_note = note
        approval.resolution_json = {
            "decision": "approved",
            "extension_value": extension,
            "new_limit": new_limit,
            "note": note,
        }
        self._resume_run_after_approval(approval)
        self._append_resolution_step(
            approval,
            action=f"approval:approved:{approval.approval_type}",
            status="completed",
            error=note,
        )
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def deny(
        self,
        approval_id: str,
        *,
        resolved_by: str = "dashboard-admin",
        note: str | None = None,
    ) -> Optional[ApprovalRequest]:
        approval = self.get_approval(approval_id)
        if not approval or approval.status != "pending":
            return approval

        approval.status = "denied"
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by = resolved_by
        approval.resolution_note = note
        approval.resolution_json = {
            "decision": "denied",
            "note": note,
        }
        self._append_resolution_step(
            approval,
            action=f"approval:denied:{approval.approval_type}",
            status="terminated",
            error=note or "Human operator denied continuation",
        )
        self._terminate_run_for_resolution(
            approval,
            error_type="approval_denied",
            message=(
                note
                or f"Alert for {approval.approval_type.replace('_', ' ')} was denied by a human operator."
            ),
        )
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def get_gateway_cost_extension(self, run_id: str, session_id: str) -> float:
        approvals = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.run_id == run_id,
                ApprovalRequest.session_id == session_id,
                ApprovalRequest.scope == "gateway",
                ApprovalRequest.approval_type == "cost_limit",
                ApprovalRequest.status == "approved",
            )
            .all()
        )
        total_extension = 0.0
        for approval in approvals:
            resolution = approval.resolution_json or {}
            total_extension += float(resolution.get("extension_value") or 0.0)
        return total_extension

    def _mark_run_awaiting_approval(self, approval: ApprovalRequest):
        run = self.db.query(Run).filter(Run.id == approval.run_id).first()
        if not run:
            return

        run.status = "awaiting_approval"
        run.error = approval.message
        run.error_details = json.dumps(
            {
                "error_type": "pending_approval",
                "approval_id": approval.id,
                "approval_type": approval.approval_type,
                "message": approval.message,
                "current_value": approval.current_value,
                "limit_value": approval.limit_value,
                "unit": approval.unit,
                "expires_at": approval.expires_at.isoformat(),
            }
        )

    def _resume_run_after_approval(self, approval: ApprovalRequest):
        run = self.db.query(Run).filter(Run.id == approval.run_id).first()
        if not run:
            return

        resolution = approval.resolution_json or {}
        run.status = "running"
        run.error = None
        run.error_details = None
        run.end_time = None
        new_limit = resolution.get("new_limit")
        if new_limit is not None:
            if approval.approval_type == "cost_limit":
                run.max_cost_usd = float(new_limit)
            elif approval.approval_type == "step_limit":
                run.max_steps_limit = int(new_limit)

    def _terminate_run_for_resolution(
        self,
        approval: ApprovalRequest,
        *,
        error_type: str,
        message: str,
    ):
        run = self.db.query(Run).filter(Run.id == approval.run_id).first()
        if not run:
            return

        run.status = "terminated"
        run.end_time = datetime.now(timezone.utc)
        run.error = message
        run.error_details = json.dumps(
            {
                "error_type": error_type,
                "approval_id": approval.id,
                "approval_type": approval.approval_type,
                "message": message,
                "current_value": approval.current_value,
                "limit_value": approval.limit_value,
                "unit": approval.unit,
            }
        )

    def _append_resolution_step(
        self,
        approval: ApprovalRequest,
        *,
        action: str,
        status: str,
        error: str | None,
    ):
        next_step = (
            self.db.query(func.coalesce(func.max(Step.step_number), 0))
            .filter(Step.run_id == approval.run_id)
            .scalar()
        ) or 0
        step = Step(
            run_id=approval.run_id,
            step_number=int(next_step) + 1,
            action=action,
            tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
            status=status,
            error=error,
            metadata_json={
                "approval_id": approval.id,
                "approval_type": approval.approval_type,
                "scope": approval.scope,
                "session_id": approval.session_id,
            },
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)

        run = self.db.query(Run).filter(Run.id == approval.run_id).first()
        if run:
            run.total_steps = step.step_number
