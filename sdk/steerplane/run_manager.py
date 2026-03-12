"""
SteerPlane SDK — Run Manager

Orchestrates the full run lifecycle:
start_run → log_step → detect_loop → check_cost → end_run
"""

import time
import logging
from typing import Any

from .client import SteerPlaneClient
from .telemetry import TelemetryCollector, StepEvent
from .loop_detector import LoopDetector
from .cost_tracker import CostTracker
from .utils import generate_run_id, format_cost, format_duration
from .config import get_config
from .policy_engine import PolicyEngine
from .exceptions import (
    LoopDetectedError,
    CostLimitExceeded,
    StepLimitExceeded,
    RunTerminatedError,
    PolicyViolationError,
)

logger = logging.getLogger("steerplane")


class RunManager:
    """
    Manages a single agent run with full guard capabilities.
    
    Provides:
    - Step logging with telemetry
    - Loop detection
    - Cost tracking and limits
    - Step limit enforcement
    - API reporting
    """

    def __init__(
        self,
        agent_name: str = "default_agent",
        run_id: str | None = None,
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        max_runtime_sec: int = 3600,
        loop_window_size: int = 8,
        model: str = "default",
        api_url: str | None = None,
        api_key: str | None = None,
        log_to_console: bool = True,
        policy: PolicyEngine | None = None,
    ):
        self.agent_name = agent_name
        self.run_id = run_id or generate_run_id()
        self.max_steps = max_steps
        self.max_runtime_sec = max_runtime_sec
        self.log_to_console = log_to_console

        # Initialize subsystems
        self.client = SteerPlaneClient(api_url=api_url, api_key=api_key)
        self.telemetry = TelemetryCollector(self.run_id)
        self.loop_detector = LoopDetector(window_size=loop_window_size)
        self.cost_tracker = CostTracker(max_cost_usd=max_cost_usd, model=model)
        self.policy = policy

        # Run state
        self.status = "pending"
        self.start_time: float = 0
        self.end_time: float = 0
        self._terminated = False
        self._termination_reason: str | None = None

    def start(self):
        """Start the run. Call this before logging any steps."""
        self.status = "running"
        self.start_time = time.time()

        if self.log_to_console:
            print(f"\n🚀 SteerPlane | Run Started")
            print(f"   Run ID:  {self.run_id}")
            print(f"   Agent:   {self.agent_name}")
            print(f"   Limits:  ${self.cost_tracker.max_cost_usd} cost / {self.max_steps} steps")
            print(f"   {'─' * 45}")

        # Report to API
        self.client.start_run(
            run_id=self.run_id,
            agent_name=self.agent_name,
            max_cost_usd=self.cost_tracker.max_cost_usd,
            max_steps=self.max_steps,
        )

    def log_step(
        self,
        action: str,
        tokens: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float | None = None,
        latency_ms: float | None = None,
        status: str = "completed",
        error: str | None = None,
        metadata: dict | None = None,
        model: str | None = None,
    ) -> StepEvent:
        """
        Log a step and run all guard checks.
        
        Args:
            action: Action name (e.g., 'search_web').
            tokens: Total tokens (if not split into input/output).
            input_tokens: Input/prompt tokens.
            output_tokens: Output/completion tokens.
            cost: Explicit cost override (auto-calculated if None).
            latency_ms: Step latency (auto-measured if None).
            status: Step status.
            error: Error message if failed.
            metadata: Additional data.
            model: Model name for cost calculation.
            
        Returns:
            The logged StepEvent.
            
        Raises:
            PolicyViolationError: If the action is blocked by policy.
            LoopDetectedError: If a loop pattern is detected.
            CostLimitExceeded: If cost exceeds the limit.
            StepLimitExceeded: If steps exceed the limit.
            RunTerminatedError: If the run was manually terminated.
        """
        if self._terminated:
            raise RunTerminatedError(self.run_id, self._termination_reason or "Run terminated")

        # Policy check (run first — block before incurring cost)
        if self.policy and self.policy.has_rules:
            try:
                self.policy.check(action, metadata)
            except PolicyViolationError:
                self._terminate("policy_violation")
                raise

        # Check step limit
        step_number = self.telemetry.step_count + 1
        if step_number > self.max_steps:
            self._terminate("step_limit_exceeded")
            raise StepLimitExceeded(step_number, self.max_steps)

        # Check runtime limit
        elapsed = time.time() - self.start_time
        if elapsed > self.max_runtime_sec:
            self._terminate("runtime_limit_exceeded")
            raise RunTerminatedError(
                self.run_id,
                f"Runtime exceeded: {format_duration(elapsed)} > {format_duration(self.max_runtime_sec)}"
            )

        # Calculate cost
        total_tokens = tokens or (input_tokens + output_tokens)
        step_cost = self.cost_tracker.calculate_step_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model=model,
            cost_override=cost,
        )

        # Create telemetry event
        event = self.telemetry.create_event(
            action=action,
            tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=step_cost.cost_usd,
            latency_ms=latency_ms or 0.0,
            status=status,
            error=error,
            metadata=metadata,
        )

        # Console output
        if self.log_to_console:
            status_icon = "✅" if status == "completed" else "❌"
            print(
                f"   {status_icon} Step {event.step_number}: {action} "
                f"| {total_tokens} tokens | {format_cost(step_cost.cost_usd)} "
                f"| {latency_ms or 0:.0f}ms"
            )

        # Report to API
        self.client.log_step(
            run_id=self.run_id,
            step_number=event.step_number,
            action=action,
            tokens=total_tokens,
            cost_usd=step_cost.cost_usd,
            latency_ms=latency_ms or 0.0,
            status=status,
            error=error,
            metadata=metadata,
        )

        # === GUARD CHECKS ===

        # 1. Cost limit check
        try:
            self.cost_tracker.add_step(step_cost)
        except CostLimitExceeded as e:
            self._terminate("cost_limit_exceeded")
            raise

        # 2. Loop detection
        result = self.loop_detector.record_action(action)
        if result.loop_detected:
            self._terminate("loop_detected")
            raise LoopDetectedError(result.pattern, result.window_size)

        return event

    def end(self, status: str | None = None, error: str | None = None):
        """End the run and report final status."""
        if self.status in ("completed", "failed", "terminated"):
            return  # Already ended

        self.end_time = time.time()
        self.status = status or ("terminated" if self._terminated else "completed")
        duration = self.end_time - self.start_time

        if self.log_to_console:
            print(f"   {'─' * 45}")
            status_icon = {"completed": "✅", "failed": "❌", "terminated": "⛔"}.get(self.status, "⬜")
            print(f"\n{status_icon} SteerPlane | Run {self.status.upper()}")
            print(f"   Run ID:     {self.run_id}")
            print(f"   Steps:      {self.telemetry.step_count}")
            print(f"   Cost:       {format_cost(self.cost_tracker.total_cost)}")
            print(f"   Tokens:     {self.cost_tracker.total_tokens:,}")
            print(f"   Duration:   {format_duration(duration)}")
            if error:
                print(f"   Error:      {error}")
            print()

        # Report to API
        self.client.end_run(
            run_id=self.run_id,
            status=self.status,
            total_cost=self.cost_tracker.total_cost,
            total_steps=self.telemetry.step_count,
            error=error,
        )

    def _terminate(self, reason: str):
        """Mark run as terminated."""
        self._terminated = True
        self._termination_reason = reason
        self.end(status="terminated", error=reason)

    def summary(self) -> str:
        """Get a short summary string."""
        duration = (self.end_time or time.time()) - self.start_time
        return (
            f"{self.telemetry.step_count} steps | "
            f"{format_cost(self.cost_tracker.total_cost)} | "
            f"{format_duration(duration)} | "
            f"{self.status}"
        )

    # Context manager support
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.end(status="failed", error=str(exc_val))
        else:
            self.end()
        return False  # Don't suppress exceptions
