"""
SteerPlane API — Pydantic Schemas

Request and response schemas for the API endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ──────────────── Request Schemas ────────────────

class StartRunRequest(BaseModel):
    run_id: str = Field(..., description="Unique run identifier")
    agent_name: str = Field(default="default_agent", description="Agent name")
    max_cost_usd: float = Field(default=50.0, description="Maximum cost limit")
    max_steps: int = Field(default=200, description="Maximum step limit")


class LogStepRequest(BaseModel):
    run_id: str = Field(..., description="Run ID this step belongs to")
    step_number: int = Field(..., description="Step sequence number")
    action: str = Field(..., description="Action name (e.g., search_web)")
    tokens: int = Field(default=0, description="Total tokens used")
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    latency_ms: float = Field(default=0.0, description="Latency in milliseconds")
    status: str = Field(default="completed", description="Step status")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class EndRunRequest(BaseModel):
    run_id: str = Field(..., description="Run ID to end")
    status: str = Field(default="completed", description="Final run status")
    total_cost: float = Field(default=0.0, description="Total run cost")
    total_steps: int = Field(default=0, description="Total steps executed")
    error: Optional[str] = Field(default=None, description="Error if failed/terminated")


# ──────────────── Response Schemas ────────────────

class StepResponse(BaseModel):
    id: str
    run_id: str
    step_number: int
    action: str
    tokens: int
    cost_usd: float
    latency_ms: float
    status: str
    error: Optional[str] = None
    metadata_json: Optional[dict] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class RunResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_cost: float
    total_steps: int
    total_tokens: int
    max_cost_usd: float
    max_steps_limit: int
    error: Optional[str] = None

    class Config:
        from_attributes = True


class RunDetailResponse(RunResponse):
    steps: list[StepResponse] = []


class RunListResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    limit: int
    offset: int


class StatusResponse(BaseModel):
    status: str
    message: str = ""
