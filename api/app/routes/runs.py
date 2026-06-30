"""
SteerPlane API — Runs Router

Endpoints for managing agent runs and steps.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..security import RunAuthContext, resolve_run_auth
from ..services.run_service import RunService
from ..schemas import (
    StartRunRequest,
    LogStepRequest,
    EndRunRequest,
    RunResponse,
    RunDetailResponse,
    RunListResponse,
    StatusResponse,
)

router = APIRouter(tags=["runs"])


def _authorize_write(run, auth: RunAuthContext) -> None:
    """403 if the caller may not write/read this run (no-op unless enforced)."""
    from ..config import settings

    if settings.REQUIRE_RUN_AUTH and not auth.can_write_run(run):
        raise HTTPException(status_code=403, detail="Not authorized for this run")


@router.post("/runs/start", response_model=RunResponse)
def start_run(
    req: StartRunRequest,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """Start a new governed agent run."""
    service = RunService(db)

    # Check if run already exists
    existing = service.get_run(req.run_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Run {req.run_id} already exists")

    run = service.create_run(
        run_id=req.run_id,
        agent_name=req.agent_name,
        max_cost_usd=req.max_cost_usd,
        max_steps=req.max_steps,
        api_key_id=auth.api_key_id,
    )
    return run


@router.post("/runs/step", response_model=StatusResponse)
def log_step(
    req: LogStepRequest,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """Log an execution step for a run."""
    service = RunService(db)

    # Verify run exists
    run = service.get_run(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {req.run_id} not found")
    _authorize_write(run, auth)

    service.log_step(
        run_id=req.run_id,
        step_number=req.step_number,
        action=req.action,
        tokens=req.tokens,
        cost_usd=req.cost_usd,
        latency_ms=req.latency_ms,
        status=req.status,
        error=req.error,
        metadata=req.metadata,
    )
    return StatusResponse(status="ok", message=f"Step {req.step_number} logged")


@router.post("/runs/end", response_model=RunResponse)
def end_run(
    req: EndRunRequest,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """Finalize a run."""
    service = RunService(db)

    existing = service.get_run(req.run_id)
    if existing:
        _authorize_write(existing, auth)

    run = service.end_run(
        run_id=req.run_id,
        status=req.status,
        total_cost=req.total_cost,
        total_steps=req.total_steps,
        error=req.error,
        error_details=req.error_details,
    )
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {req.run_id} not found")

    return run


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """Get full run details including all steps."""
    service = RunService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    _authorize_write(run, auth)
    return run


@router.get("/runs", response_model=RunListResponse)
def list_runs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """List all runs with pagination (scoped to the caller when auth is enforced)."""
    from ..config import settings

    service = RunService(db)
    restricted = settings.REQUIRE_RUN_AUTH and not auth.is_admin
    runs, total = service.list_runs(
        limit=limit,
        offset=offset,
        owner_key_id=auth.api_key_id,
        restricted=restricted,
    )
    return RunListResponse(
        runs=runs,
        total=total,
        limit=limit,
        offset=offset,
    )
