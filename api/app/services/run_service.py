"""
SteerPlane API — Run Service

Business logic layer for run and step management.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional

from ..models.run import Run
from ..models.step import Step


class RunService:
    """Service layer for run operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        run_id: str,
        agent_name: str = "default_agent",
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        api_key_id: Optional[str] = None,
    ) -> Run:
        """Create a new run, optionally owned by an API key for data-plane scoping."""
        run = Run(
            id=run_id,
            agent_name=agent_name,
            status="running",
            start_time=datetime.now(timezone.utc),
            max_cost_usd=max_cost_usd,
            max_steps_limit=max_steps,
            api_key_id=api_key_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def log_step(
        self,
        run_id: str,
        step_number: int,
        action: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        status: str = "completed",
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Step:
        """Log a step for a run."""
        step = Step(
            run_id=run_id,
            step_number=step_number,
            action=action,
            tokens=tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            error=error,
            metadata_json=metadata,
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)

        # Update run totals
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.total_steps = step_number
            run.total_cost = (run.total_cost or 0) + cost_usd
            run.total_tokens = (run.total_tokens or 0) + tokens

        self.db.commit()
        self.db.refresh(step)
        return step

    def end_run(
        self,
        run_id: str,
        status: str = "completed",
        total_cost: float = 0.0,
        total_steps: int = 0,
        error: Optional[str] = None,
        error_details: Optional[dict] = None,
    ) -> Optional[Run]:
        """Finalize a run with optional structured error details."""
        import json

        run = self.db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return None

        run.status = status
        run.end_time = datetime.now(timezone.utc)
        run.total_cost = total_cost
        run.total_steps = total_steps
        if error:
            run.error = error
        if error_details:
            run.error_details = json.dumps(error_details)

        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID with all steps."""
        return self.db.query(Run).filter(Run.id == run_id).first()

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        owner_key_id: Optional[str] = None,
        restricted: bool = False,
    ) -> tuple[list[Run], int]:
        """List runs with pagination.

        When ``restricted`` is set (enforced mode, non-admin caller), results are
        scoped strictly to runs owned by ``owner_key_id``. NULL-owned
        (legacy/keyless) runs are visible to admin only, preventing cross-tenant
        leakage.
        """
        query = self.db.query(Run)
        count_query = self.db.query(func.count(Run.id))
        if restricted:
            visibility = Run.api_key_id == owner_key_id
            query = query.filter(visibility)
            count_query = count_query.filter(visibility)

        total = count_query.scalar()
        runs = query.order_by(Run.start_time.desc()).offset(offset).limit(limit).all()
        return runs, total
