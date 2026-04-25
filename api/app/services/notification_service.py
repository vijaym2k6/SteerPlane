"""
Notification delivery for SteerPlane alert mode.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from ..config import settings
from ..models.approval_request import ApprovalRequest


logger = logging.getLogger("steerplane.notifications")


class NotificationService:
    """Dispatch alert-mode notifications to configured channels."""

    def build_payload(self, approval: ApprovalRequest) -> dict:
        dashboard_run_url = f"{settings.DASHBOARD_URL}/dashboard/runs/{approval.run_id}"
        approvals_url = f"{settings.DASHBOARD_URL}/approvals"
        return {
            "title": f"SteerPlane approval needed for {approval.agent_name}",
            "run_id": approval.run_id,
            "agent_name": approval.agent_name,
            "scope": approval.scope,
            "approval_type": approval.approval_type,
            "message": approval.message,
            "current_value": approval.current_value,
            "limit_value": approval.limit_value,
            "unit": approval.unit,
            "status": approval.status,
            "expires_at": approval.expires_at.isoformat(),
            "approvals_url": approvals_url,
            "run_url": dashboard_run_url,
            "metadata": approval.metadata_json or {},
        }

    def dispatch(self, approval: ApprovalRequest):
        payload = self.build_payload(approval)
        channels = {
            channel.lower().strip()
            for channel in (approval.channels_json or [])
            if isinstance(channel, str) and channel.strip()
        }

        logger.warning(
            "SteerPlane approval requested | run=%s agent=%s type=%s expires=%s",
            approval.run_id,
            approval.agent_name,
            approval.approval_type,
            approval.expires_at.isoformat(),
        )

        if "email" in channels and approval.alert_email:
            self._send_email(approval.alert_email, payload)
        if "webhook" in channels and approval.alert_webhook_url:
            self._send_webhook(approval.alert_webhook_url, payload)

    def _send_email(self, recipient: str, payload: dict):
        if not settings.SMTP_HOST or not settings.SMTP_FROM:
            logger.warning(
                "Skipping SteerPlane email alert to %s because SMTP is not configured",
                recipient,
            )
            return

        message = EmailMessage()
        message["Subject"] = payload["title"]
        message["From"] = settings.SMTP_FROM
        message["To"] = recipient
        message.set_content(
            "\n".join(
                [
                    payload["message"],
                    "",
                    f"Run: {payload['run_id']}",
                    f"Agent: {payload['agent_name']}",
                    f"Type: {payload['approval_type']}",
                    f"Current: {payload['current_value']} {payload['unit']}",
                    f"Limit: {payload['limit_value']} {payload['unit']}",
                    f"Expires: {payload['expires_at']}",
                    f"Approvals: {payload['approvals_url']}",
                    f"Run: {payload['run_url']}",
                ]
            )
        )

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except Exception as exc:  # pragma: no cover - network/system dependent
            logger.warning("Failed to send SteerPlane alert email: %s", exc)

    def _send_webhook(self, url: str, payload: dict):
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(url, json=payload)
        except Exception as exc:  # pragma: no cover - network/system dependent
            logger.warning("Failed to send SteerPlane alert webhook: %s", exc)
