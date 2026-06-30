"""
SteerPlane API — Telemetry Router

Endpoint for batch telemetry ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db.database import get_db
from ..security import RunAuthContext, resolve_run_auth
from ..services.run_service import RunService
from ..schemas import StatusResponse

router = APIRouter(tags=["telemetry"])


class TelemetryEvent(BaseModel):
    run_id: str
    step_number: int
    action: str
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "completed"
    error: str | None = None
    metadata: dict = Field(default_factory=dict)


class BatchTelemetryRequest(BaseModel):
    events: list[TelemetryEvent]


@router.post("/telemetry", response_model=StatusResponse)
def ingest_telemetry(
    req: BatchTelemetryRequest,
    db: Session = Depends(get_db),
    auth: RunAuthContext = Depends(resolve_run_auth),
):
    """Batch ingest telemetry events."""
    service = RunService(db)

    for event in req.events:
        if settings.REQUIRE_RUN_AUTH:
            run = service.get_run(event.run_id)
            if run is not None and not auth.can_write_run(run):
                raise HTTPException(
                    status_code=403,
                    detail=f"Not authorized for run {event.run_id}",
                )
        service.log_step(
            run_id=event.run_id,
            step_number=event.step_number,
            action=event.action,
            tokens=event.tokens,
            cost_usd=event.cost_usd,
            latency_ms=event.latency_ms,
            status=event.status,
            error=event.error,
            metadata=event.metadata,
        )

    return StatusResponse(status="ok", message=f"{len(req.events)} events ingested")
