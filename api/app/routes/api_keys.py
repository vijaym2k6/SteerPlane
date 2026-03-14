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


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# ─── Schemas ─────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for this key")
    max_cost_usd: float = Field(default=50.0, description="Per-session cost ceiling in USD")
    max_cost_monthly: float = Field(default=500.0, description="Monthly budget in USD")
    max_requests_per_min: int = Field(default=60, description="Rate limit per minute")
    allowed_models: Optional[str] = Field(default=None, description="Comma-separated allowed models")
    denied_models: Optional[str] = Field(default=None, description="Comma-separated denied models")


class KeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    max_cost_usd: float
    max_cost_monthly: float
    max_requests_per_min: int
    allowed_models: Optional[str] = None
    denied_models: Optional[str] = None
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
    total = db.query(func.count(APIKey.id)).scalar()
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()

    return KeyListResponse(
        keys=[
            KeyResponse(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                max_cost_usd=k.max_cost_usd,
                max_cost_monthly=k.max_cost_monthly,
                max_requests_per_min=k.max_requests_per_min,
                allowed_models=k.allowed_models,
                denied_models=k.denied_models,
                is_active=k.is_active,
                total_requests=k.total_requests,
                total_cost=k.total_cost,
                total_tokens=k.total_tokens,
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                created_at=k.created_at.isoformat(),
            )
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

    return KeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        max_cost_usd=api_key.max_cost_usd,
        max_cost_monthly=api_key.max_cost_monthly,
        max_requests_per_min=api_key.max_requests_per_min,
        allowed_models=api_key.allowed_models,
        denied_models=api_key.denied_models,
        is_active=api_key.is_active,
        total_requests=api_key.total_requests,
        total_cost=api_key.total_cost,
        total_tokens=api_key.total_tokens,
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        created_at=api_key.created_at.isoformat(),
    )


@router.put("/{key_id}", response_model=KeyResponse)
def update_key(key_id: str, req: UpdateKeyRequest, db: Session = Depends(get_db)):
    """Update an API key's settings."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if req.name is not None:
        api_key.name = req.name
    if req.max_cost_usd is not None:
        api_key.max_cost_usd = req.max_cost_usd
    if req.max_cost_monthly is not None:
        api_key.max_cost_monthly = req.max_cost_monthly
    if req.max_requests_per_min is not None:
        api_key.max_requests_per_min = req.max_requests_per_min
    if req.allowed_models is not None:
        api_key.allowed_models = req.allowed_models
    if req.denied_models is not None:
        api_key.denied_models = req.denied_models
    if req.is_active is not None:
        api_key.is_active = req.is_active

    db.commit()
    db.refresh(api_key)

    return KeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        max_cost_usd=api_key.max_cost_usd,
        max_cost_monthly=api_key.max_cost_monthly,
        max_requests_per_min=api_key.max_requests_per_min,
        allowed_models=api_key.allowed_models,
        denied_models=api_key.denied_models,
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
