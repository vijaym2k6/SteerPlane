"""
SteerPlane API — Policy Routes

CRUD and evaluation endpoints for agent action policies.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from ..db.database import get_db
from ..services.policy_service import PolicyService


# ──────────────── Request / Response Schemas ────────────────

class CreatePolicyRequest(BaseModel):
    name: str = Field(..., description="Unique policy name")
    description: Optional[str] = Field(default=None, description="Human-readable description")
    allowed_actions: Optional[list[str]] = Field(default=None, description="Glob patterns for permitted actions")
    denied_actions: Optional[list[str]] = Field(default=None, description="Glob patterns for forbidden actions")
    rate_limits: Optional[list[dict]] = Field(default=None, description="Per-action rate limits [{action, max_calls, window_seconds}]")
    require_approval: Optional[list[str]] = Field(default=None, description="Actions requiring human approval")
    is_active: bool = Field(default=True, description="Whether policy is active")


class UpdatePolicyRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_actions: Optional[list[str]] = None
    denied_actions: Optional[list[str]] = None
    rate_limits: Optional[list[dict]] = None
    require_approval: Optional[list[str]] = None
    is_active: Optional[bool] = None


class EvaluateActionRequest(BaseModel):
    action: str = Field(..., description="Action name to evaluate")


class PolicyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    allowed_actions: Optional[list[str]] = None
    denied_actions: Optional[list[str]] = None
    rate_limits: Optional[list[dict]] = None
    require_approval: Optional[list[str]] = None

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    policies: list[PolicyResponse]
    total: int
    limit: int
    offset: int


class EvaluateActionResponse(BaseModel):
    allowed: bool
    requires_approval: bool = False
    reason: str


class StatusResponse(BaseModel):
    status: str
    message: str = ""


# ──────────────── Router ────────────────

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
def create_policy(req: CreatePolicyRequest, db: Session = Depends(get_db)):
    """Create a new action policy."""
    service = PolicyService(db)

    # Check name uniqueness
    existing = service.get_policy_by_name(req.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Policy '{req.name}' already exists")

    policy = service.create_policy(
        name=req.name,
        description=req.description,
        allowed_actions=req.allowed_actions,
        denied_actions=req.denied_actions,
        rate_limits=req.rate_limits,
        require_approval=req.require_approval,
        is_active=req.is_active,
    )
    return policy


@router.get("", response_model=PolicyListResponse)
def list_policies(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all policies with pagination."""
    service = PolicyService(db)
    policies, total = service.list_policies(active_only=active_only, limit=limit, offset=offset)
    return PolicyListResponse(policies=policies, total=total, limit=limit, offset=offset)


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(policy_id: str, db: Session = Depends(get_db)):
    """Get a policy by ID."""
    service = PolicyService(db)
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(policy_id: str, req: UpdatePolicyRequest, db: Session = Depends(get_db)):
    """Update an existing policy."""
    service = PolicyService(db)
    policy = service.update_policy(
        policy_id=policy_id,
        name=req.name,
        description=req.description,
        allowed_actions=req.allowed_actions,
        denied_actions=req.denied_actions,
        rate_limits=req.rate_limits,
        require_approval=req.require_approval,
        is_active=req.is_active,
    )
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return policy


@router.delete("/{policy_id}", response_model=StatusResponse)
def delete_policy(policy_id: str, db: Session = Depends(get_db)):
    """Delete a policy."""
    service = PolicyService(db)
    deleted = service.delete_policy(policy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return StatusResponse(status="ok", message=f"Policy '{policy_id}' deleted")


@router.post("/{policy_id}/evaluate", response_model=EvaluateActionResponse)
def evaluate_action(policy_id: str, req: EvaluateActionRequest, db: Session = Depends(get_db)):
    """Evaluate whether an action is allowed under a specific policy."""
    service = PolicyService(db)

    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")

    result = service.evaluate_action(policy_id=policy_id, action=req.action)
    return EvaluateActionResponse(
        allowed=result["allowed"],
        requires_approval=result.get("requires_approval", False),
        reason=result["reason"],
    )
