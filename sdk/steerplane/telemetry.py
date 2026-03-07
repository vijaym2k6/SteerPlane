"""
SteerPlane SDK — Telemetry

Step event generation, structured telemetry data, and event sending.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from .utils import generate_step_id, now_iso


@dataclass
class StepEvent:
    """A single execution step event."""
    step_id: str
    run_id: str
    step_number: int
    action: str
    tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "completed"  # completed, failed, terminated
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = now_iso()
        if not self.step_id:
            self.step_id = generate_step_id()

    def to_dict(self) -> dict:
        """Convert to dictionary for API submission."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


class TelemetryCollector:
    """
    Collects and manages telemetry events for a run.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[StepEvent] = []
        self._step_counter = 0

    def create_event(
        self,
        action: str,
        tokens: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        status: str = "completed",
        error: str | None = None,
        metadata: dict | None = None,
    ) -> StepEvent:
        """
        Create and record a step event.
        
        Args:
            action: Name of the action (e.g., 'search_web', 'call_llm').
            tokens: Total tokens used.
            input_tokens: Input/prompt tokens.
            output_tokens: Output/completion tokens.
            cost_usd: Cost for this step in USD.
            latency_ms: Execution time in milliseconds.
            status: Step status.
            error: Error message if step failed.
            metadata: Additional metadata.
            
        Returns:
            The created StepEvent.
        """
        self._step_counter += 1

        event = StepEvent(
            step_id=generate_step_id(),
            run_id=self.run_id,
            step_number=self._step_counter,
            action=action,
            tokens=tokens or (input_tokens + output_tokens),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            error=error,
            metadata=metadata or {},
        )
        self.events.append(event)
        return event

    @property
    def step_count(self) -> int:
        return self._step_counter

    @property
    def action_history(self) -> list[str]:
        """Get list of action names for loop detection."""
        return [e.action for e in self.events]

    def get_events_for_api(self) -> list[dict]:
        """Get all events as dicts for API submission."""
        return [e.to_dict() for e in self.events]
