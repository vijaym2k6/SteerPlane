"""
Approval workflow routes for alert-mode enforcement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..config import settings
from ..db.database import get_db
from ..models.run import Run
from ..security import RunAuthContext, require_admin, resolve_run_auth
from ..services.approval_service import ApprovalService


router = APIRouter(tags=["approvals"])


def _authorize_run(db: Session, run_id: str, auth: RunAuthContext) -> None:
    """403 if the caller may not act on this run's approvals (enforced mode only)."""
    if not settings.REQUIRE_RUN_AUTH:
        return
    run = db.query(Run).filter(Run.id == run_id).first()
    if run is not None and not auth.can_write_run(run):
        raise HTTPException(status_code=403, detail="Not authorized for this run")


class CreateApprovalRequestBody(BaseModel):
    run_id: str = Field(..., description="Run awaiting approval")
    agent_name: str = Field(..., description="Human-readable agent name")
    approval_type: str = Field(..., description="cost_limit, step_limit, runtime_limit, ...")
    current_value: float = Field(..., description="Current measured value")
    limit_value: float = Field(..., description="Configured limit when alert fired")
    unit: str = Field(..., description="usd, steps, seconds, ...")
    message: str = Field(..., description="Alert message sent to humans")
    timeout_sec: int = Field(default=1800, description="How long to wait before expiring")
    scope: str = Field(default="sdk", description="sdk or gateway")
    session_id: Optional[str] = None
    api_key_id: Optional[str] = None
    channels: list[str] = Field(default_factory=list)
    alert_email: Optional[str] = None
    alert_webhook_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ResolveApprovalRequestBody(BaseModel):
    note: Optional[str] = None
    extension_value: Optional[float] = Field(
        default=None,
        description="Optional explicit extension amount. Defaults to doubling the current limit.",
    )


class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    agent_name: str
    scope: str
    approval_type: str
    status: str
    message: str
    current_value: float
    limit_value: float
    unit: str
    timeout_sec: int
    session_id: Optional[str] = None
    api_key_id: Optional[str] = None
    channels_json: list[str] = Field(default_factory=list)
    alert_email: Optional[str] = None
    alert_webhook_url: Optional[str] = None
    metadata_json: Optional[dict] = None
    resolution_json: Optional[dict] = None
    created_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None

    @field_validator("channels_json", mode="before")
    @classmethod
    def _default_channels(cls, value):
        return value or []

    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]
    total: int


@router.post("/approvals/request", response_model=ApprovalResponse)
def create_approval(
    req: CreateApprovalRequestBody,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    _authorize_run(db, req.run_id, auth)
    service = ApprovalService(db)
    approval = service.create_approval(
        run_id=req.run_id,
        agent_name=req.agent_name,
        approval_type=req.approval_type,
        current_value=req.current_value,
        limit_value=req.limit_value,
        unit=req.unit,
        message=req.message,
        timeout_sec=req.timeout_sec,
        scope=req.scope,
        session_id=req.session_id,
        api_key_id=req.api_key_id,
        channels=req.channels,
        alert_email=req.alert_email,
        alert_webhook_url=req.alert_webhook_url,
        metadata=req.metadata,
    )
    return approval


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    service = ApprovalService(db)
    approval = service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    _authorize_run(db, approval.run_id, auth)
    return approval


@router.get(
    "/approvals",
    response_model=ApprovalListResponse,
    dependencies=[Depends(require_admin)],
)
def list_approvals(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    service = ApprovalService(db)
    approvals = service.list_approvals(status=status, limit=limit)
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalResponse,
    dependencies=[Depends(require_admin)],
)
def approve_approval(
    approval_id: str,
    req: ResolveApprovalRequestBody,
    request: Request,
    db: Session = Depends(get_db),
):
    service = ApprovalService(db)
    actor = request.headers.get("X-SteerPlane-Admin-Token", "dashboard-admin")
    approval = service.approve(
        approval_id,
        resolved_by=actor,
        note=req.note,
        extension_value=req.extension_value,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post(
    "/approvals/{approval_id}/deny",
    response_model=ApprovalResponse,
    dependencies=[Depends(require_admin)],
)
def deny_approval(
    approval_id: str,
    req: ResolveApprovalRequestBody,
    request: Request,
    db: Session = Depends(get_db),
):
    service = ApprovalService(db)
    actor = request.headers.get("X-SteerPlane-Admin-Token", "dashboard-admin")
    approval = service.deny(
        approval_id,
        resolved_by=actor,
        note=req.note,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval
