"""
SteerPlane API — API Key Routes

CRUD endpoints for managing gateway API keys.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.database import get_db
from ..models.api_key import APIKey, generate_api_key, hash_api_key
from ..security import require_admin
from ..services.approval_service import ApprovalService, DEFAULT_ALERT_THRESHOLD, DEFAULT_ALERT_TIMEOUT_SEC


router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
    dependencies=[Depends(require_admin)],
)


# ─── Schemas ─────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for this key")
    max_cost_usd: float = Field(default=50.0, description="Per-session cost ceiling in USD")
    max_cost_monthly: float = Field(default=500.0, description="Monthly budget in USD")
    max_requests_per_min: int = Field(default=60, description="Rate limit per minute")
    allowed_models: Optional[str] = Field(default=None, description="Comma-separated allowed models")
    denied_models: Optional[str] = Field(default=None, description="Comma-separated denied models")
    enforcement_mode: str = Field(default="kill", description="kill or alert")
    alert_threshold: float = Field(default=DEFAULT_ALERT_THRESHOLD, description="Fraction of the limit that triggers an alert")
    alert_timeout_sec: int = Field(default=DEFAULT_ALERT_TIMEOUT_SEC, description="How long to wait for human approval")
    alert_channels: list[str] = Field(default_factory=list, description="email, webhook")
    alert_email: Optional[str] = Field(default=None, description="Email recipient for alert mode")
    alert_webhook_url: Optional[str] = Field(default=None, description="Webhook target for alert mode")


class KeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    max_cost_usd: float
    max_cost_monthly: float
    max_requests_per_min: int
    allowed_models: Optional[str] = None
    denied_models: Optional[str] = None
    enforcement_mode: str
    alert_threshold: float
    alert_timeout_sec: int
    alert_channels: list[str]
    alert_email: Optional[str] = None
    alert_webhook_url: Optional[str] = None
    is_active: bool
    total_requests: int
    total_cost: float
    total_tokens: int
    last_used_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class KeyCreatedResponse(KeyResponse):
    raw_key: str = Field(..., description="Full API key — shown only once!")


class UpdateKeyRequest(BaseModel):
    name: Optional[str] = None
    max_cost_usd: Optional[float] = None
    max_cost_monthly: Optional[float] = None
    max_requests_per_min: Optional[int] = None
    allowed_models: Optional[str] = None
    denied_models: Optional[str] = None
    enforcement_mode: Optional[str] = None
    alert_threshold: Optional[float] = None
    alert_timeout_sec: Optional[int] = None
    alert_channels: Optional[list[str]] = None
    alert_email: Optional[str] = None
    alert_webhook_url: Optional[str] = None
    is_active: Optional[bool] = None


class KeyListResponse(BaseModel):
    keys: list[KeyResponse]
    total: int


# ─── Endpoints ───────────────────────────────────────────

@router.post("/", response_model=KeyCreatedResponse, status_code=201)
def create_key(req: CreateKeyRequest, db: Session = Depends(get_db)):
    """Create a new API key. The raw key is shown only once — save it!"""
    raw_key = generate_api_key()
    key_hashed = hash_api_key(raw_key)
    key_prefix = raw_key[:14] + "..."

    api_key = APIKey(
        name=req.name,
        key_hash=key_hashed,
        key_prefix=key_prefix,
        max_cost_usd=req.max_cost_usd,
        max_cost_monthly=req.max_cost_monthly,
        max_requests_per_min=req.max_requests_per_min,
        allowed_models=req.allowed_models,
        denied_models=req.denied_models,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    approval_service = ApprovalService(db)
    enforcement = approval_service.get_or_create_api_key_enforcement(api_key.id)
    enforcement.enforcement_mode = req.enforcement_mode
    enforcement.alert_threshold = req.alert_threshold
    enforcement.alert_timeout_sec = req.alert_timeout_sec
    enforcement.alert_channels_json = req.alert_channels
    enforcement.alert_email = req.alert_email
    enforcement.alert_webhook_url = req.alert_webhook_url
    db.commit()
    db.refresh(enforcement)

    return KeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        max_cost_usd=api_key.max_cost_usd,
        max_cost_monthly=api_key.max_cost_monthly,
        max_requests_per_min=api_key.max_requests_per_min,
        allowed_models=api_key.allowed_models,
        denied_models=api_key.denied_models,
        enforcement_mode=enforcement.enforcement_mode,
        alert_threshold=enforcement.alert_threshold,
        alert_timeout_sec=enforcement.alert_timeout_sec,
        alert_channels=enforcement.alert_channels_json or [],
        alert_email=enforcement.alert_email,
        alert_webhook_url=enforcement.alert_webhook_url,
        is_active=api_key.is_active,
        total_requests=api_key.total_requests,
        total_cost=api_key.total_cost,
        total_tokens=api_key.total_tokens,
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("/", response_model=KeyListResponse)
def list_keys(db: Session = Depends(get_db)):
    """List all API keys (without the raw key)."""
    approval_service = ApprovalService(db)
    total = db.query(func.count(APIKey.id)).scalar()
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()

    return KeyListResponse(
        keys=[
            _build_key_response(k, approval_service.get_api_key_enforcement(k.id))
            for k in keys
        ],
        total=total,
    )


@router.get("/{key_id}", response_model=KeyResponse)
def get_key(key_id: str, db: Session = Depends(get_db)):
    """Get an API key by ID."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    approval_service = ApprovalService(db)
    return _build_key_response(api_key, approval_service.get_api_key_enforcement(api_key.id))


@router.put("/{key_id}", response_model=KeyResponse)
def update_key(key_id: str, req: UpdateKeyRequest, db: Session = Depends(get_db)):
    """Update an API key's settings."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    provided_fields = req.model_fields_set

    if "name" in provided_fields:
        api_key.name = req.name
    if "max_cost_usd" in provided_fields:
        api_key.max_cost_usd = req.max_cost_usd
    if "max_cost_monthly" in provided_fields:
        api_key.max_cost_monthly = req.max_cost_monthly
    if "max_requests_per_min" in provided_fields:
        api_key.max_requests_per_min = req.max_requests_per_min
    if "allowed_models" in provided_fields:
        api_key.allowed_models = req.allowed_models
    if "denied_models" in provided_fields:
        api_key.denied_models = req.denied_models
    if "is_active" in provided_fields:
        api_key.is_active = req.is_active

    approval_service = ApprovalService(db)
    enforcement = approval_service.get_or_create_api_key_enforcement(api_key.id)
    if "enforcement_mode" in provided_fields:
        enforcement.enforcement_mode = req.enforcement_mode
    if "alert_threshold" in provided_fields:
        enforcement.alert_threshold = req.alert_threshold
    if "alert_timeout_sec" in provided_fields:
        enforcement.alert_timeout_sec = req.alert_timeout_sec
    if "alert_channels" in provided_fields:
        enforcement.alert_channels_json = req.alert_channels
    if "alert_email" in provided_fields:
        enforcement.alert_email = req.alert_email
    if "alert_webhook_url" in provided_fields:
        enforcement.alert_webhook_url = req.alert_webhook_url

    db.commit()
    db.refresh(api_key)
    db.refresh(enforcement)

    return _build_key_response(api_key, enforcement)


def _build_key_response(api_key: APIKey, enforcement) -> KeyResponse:
    return KeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        max_cost_usd=api_key.max_cost_usd,
        max_cost_monthly=api_key.max_cost_monthly,
        max_requests_per_min=api_key.max_requests_per_min,
        allowed_models=api_key.allowed_models,
        denied_models=api_key.denied_models,
        enforcement_mode=enforcement.enforcement_mode,
        alert_threshold=enforcement.alert_threshold,
        alert_timeout_sec=enforcement.alert_timeout_sec,
        alert_channels=enforcement.alert_channels_json or [],
        alert_email=enforcement.alert_email,
        alert_webhook_url=enforcement.alert_webhook_url,
        is_active=api_key.is_active,
        total_requests=api_key.total_requests,
        total_cost=api_key.total_cost,
        total_tokens=api_key.total_tokens,
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        created_at=api_key.created_at.isoformat(),
    )


@router.delete("/{key_id}")
def delete_key(key_id: str, db: Session = Depends(get_db)):
    """Delete (revoke) an API key permanently."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(api_key)
    db.commit()
    return {"status": "deleted", "id": key_id}
