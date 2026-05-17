"""
SteerPlane SDK — Run Manager

Orchestrates the full run lifecycle:
start_run → log_step → detect_loop → check_cost → end_run
"""

import time
import logging
from contextvars import Token

from .client import SteerPlaneClient
from .telemetry import TelemetryCollector, StepEvent
from .loop_detector import LoopDetector
from .cost_tracker import CostTracker
from .utils import generate_run_id, format_cost, format_duration
from .policy_engine import PolicyEngine
from .runtime_context import reset_active_run, set_active_run
from .exceptions import (
    LoopDetectedError,
    CostLimitExceeded,
    StepLimitExceeded,
    RunTerminatedError,
    PolicyViolationError,
)

import sys

logger = logging.getLogger("steerplane")


def _safe_print(*args, **kwargs):
    """Print that handles Unicode encoding errors on Windows (cp1252)."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        print(
            text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ),
            **kwargs,
        )


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
        enforcement: str = "kill",
        alert_threshold: float = 0.8,
        alert_timeout_sec: int = 1800,
        alert_channels: list[str] | None = None,
        alert_email: str | None = None,
        alert_webhook_url: str | None = None,
        alert_poll_interval_sec: int = 5,
    ):
        self.agent_name = agent_name
        self.run_id = run_id or generate_run_id()
        self.max_steps = max_steps
        self.max_runtime_sec = max_runtime_sec
        self.log_to_console = log_to_console
        self.enforcement = (enforcement or "kill").lower()
        self.alert_threshold = min(max(alert_threshold, 0.0), 1.0)
        self.alert_timeout_sec = max(int(alert_timeout_sec), 1)
        self.alert_channels = list(alert_channels or [])
        self.alert_email = alert_email
        self.alert_webhook_url = alert_webhook_url
        self.alert_poll_interval_sec = max(int(alert_poll_interval_sec), 1)

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
        self._termination_details: dict | None = None
        self._context_token: Token | None = None

    def start(self):
        """Start the run. Call this before logging any steps."""
        if self.status == "running":
            return

        self.status = "running"
        self.start_time = time.time()
        self._context_token = set_active_run(self)

        if self.log_to_console:
            _safe_print("\n>> SteerPlane | Run Started")
            _safe_print(f"   Run ID:  {self.run_id}")
            _safe_print(f"   Agent:   {self.agent_name}")
            _safe_print(
                f"   Limits:  ${self.cost_tracker.max_cost_usd} cost / {self.max_steps} steps"
            )
            if self.enforcement == "alert":
                _safe_print(
                    f"   Mode:    alert @ {int(self.alert_threshold * 100)}% "
                    f"({self.alert_timeout_sec}s timeout)"
                )
            _safe_print(f"   {'-' * 45}")

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
            except PolicyViolationError as e:
                self._terminate(
                    "policy_violation",
                    details={
                        "error_type": "policy_violation",
                        "blocked_action": action,
                        "rule_matched": e.rule,
                        "reason": e.reason,
                        "step_number": self.telemetry.step_count + 1,
                        "total_cost_at_termination": self.cost_tracker.total_cost,
                        "message": str(e),
                    },
                )
                raise

        # Check step limit
        step_number = self.telemetry.step_count + 1
        if step_number > self.max_steps:
            if self._uses_alert_mode():
                self._pause_for_limit(
                    approval_type="step_limit",
                    action=action,
                    current_value=float(step_number),
                    limit_value=float(self.max_steps),
                    unit="steps",
                    message=(
                        f"Run '{self.agent_name}' hit its step limit "
                        f"({step_number}/{self.max_steps}). Approve to extend and continue."
                    ),
                    metadata={
                        "blocked_action": action,
                        "current_steps": step_number,
                        "max_steps": self.max_steps,
                    },
                )
            else:
                self._terminate(
                    "step_limit_exceeded",
                    details={
                        "error_type": "step_limit_exceeded",
                        "blocked_action": action,
                        "current_steps": step_number,
                        "max_steps": self.max_steps,
                        "total_cost_at_termination": self.cost_tracker.total_cost,
                        "message": f"Step limit exceeded: {step_number}/{self.max_steps}. Agent attempted action '{action}'.",
                    },
                )
                raise StepLimitExceeded(step_number, self.max_steps)

        # Check runtime limit
        elapsed = time.time() - self.start_time
        if elapsed > self.max_runtime_sec:
            if self._uses_alert_mode():
                self._pause_for_limit(
                    approval_type="runtime_limit",
                    action=action,
                    current_value=float(round(elapsed, 1)),
                    limit_value=float(self.max_runtime_sec),
                    unit="seconds",
                    message=(
                        f"Run '{self.agent_name}' exceeded its runtime limit "
                        f"({format_duration(elapsed)} > {format_duration(self.max_runtime_sec)}). "
                        "Approve to continue or let it terminate."
                    ),
                    metadata={
                        "blocked_action": action,
                        "elapsed_seconds": round(elapsed, 1),
                        "max_runtime_seconds": self.max_runtime_sec,
                    },
                )
            else:
                self._terminate(
                    "runtime_limit_exceeded",
                    details={
                        "error_type": "runtime_limit_exceeded",
                        "blocked_action": action,
                        "elapsed_seconds": round(elapsed, 1),
                        "max_runtime_seconds": self.max_runtime_sec,
                        "total_cost_at_termination": self.cost_tracker.total_cost,
                        "message": f"Runtime exceeded: {format_duration(elapsed)} > {format_duration(self.max_runtime_sec)}. Agent was running action '{action}'.",
                    },
                )
                raise RunTerminatedError(
                    self.run_id,
                    f"Runtime exceeded: {format_duration(elapsed)} > {format_duration(self.max_runtime_sec)}",
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
            status_icon = "[OK]" if status == "completed" else "[ERR]"
            _safe_print(
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
            if self._uses_alert_mode():
                self._pause_for_limit(
                    approval_type="cost_limit",
                    action=action,
                    current_value=float(e.current_cost),
                    limit_value=float(e.max_cost),
                    unit="usd",
                    message=(
                        f"Run '{self.agent_name}' exceeded its cost limit "
                        f"(${e.current_cost:.4f} > ${e.max_cost:.2f}). "
                        "Approve to extend and continue or let it terminate."
                    ),
                    metadata={
                        "blocked_action": action,
                        "current_cost": e.current_cost,
                        "max_cost": e.max_cost,
                        "step_number": event.step_number,
                    },
                )
            else:
                self._terminate(
                    "cost_limit_exceeded",
                    details={
                        "error_type": "cost_limit_exceeded",
                        "blocked_action": action,
                        "current_cost": e.current_cost,
                        "max_cost": e.max_cost,
                        "step_number": event.step_number,
                        "message": f"Cost limit exceeded: ${e.current_cost:.4f} > ${e.max_cost:.2f}. Last action was '{action}'.",
                    },
                )
                raise

        # 2. Loop detection
        result = self.loop_detector.record_action(action)
        if result.loop_detected:
            self._terminate(
                "loop_detected",
                details={
                    "error_type": "loop_detected",
                    "blocked_action": action,
                    "pattern_detected": result.pattern,
                    "window_size": result.window_size,
                    "step_number": event.step_number,
                    "total_cost_at_termination": self.cost_tracker.total_cost,
                    "recent_actions": list(self.loop_detector.action_history),
                    "message": f"Loop detected: pattern {result.pattern} repeating in last {result.window_size} actions. Run terminated at step {event.step_number}.",
                },
            )
            raise LoopDetectedError(result.pattern, result.window_size)

        self._check_alert_thresholds(action, event.step_number)

        return event

    def end(self, status: str | None = None, error: str | None = None):
        """End the run and report final status."""
        if self.status in ("completed", "failed", "terminated"):
            return  # Already ended

        self.end_time = time.time()
        self.status = status or ("terminated" if self._terminated else "completed")
        duration = self.end_time - self.start_time

        if self.log_to_console:
            _safe_print(f"   {'-' * 45}")
            status_icon = {"completed": "[OK]", "failed": "[ERR]", "terminated": "[STOP]"}.get(
                self.status, "[--]"
            )
            _safe_print(f"\n{status_icon} SteerPlane | Run {self.status.upper()}")
            _safe_print(f"   Run ID:     {self.run_id}")
            _safe_print(f"   Steps:      {self.telemetry.step_count}")
            _safe_print(f"   Cost:       {format_cost(self.cost_tracker.total_cost)}")
            _safe_print(f"   Tokens:     {self.cost_tracker.total_tokens:,}")
            _safe_print(f"   Duration:   {format_duration(duration)}")
            if error:
                _safe_print(f"   Error:      {error}")
            _safe_print()

        # Report to API
        self.client.end_run(
            run_id=self.run_id,
            status=self.status,
            total_cost=self.cost_tracker.total_cost,
            total_steps=self.telemetry.step_count,
            error=error,
            error_details=self._termination_details,
        )

        if self._context_token is not None:
            reset_active_run(self._context_token)
            self._context_token = None

    def _terminate(self, reason: str, details: dict | None = None):
        """Mark run as terminated with detailed context."""
        self._terminated = True
        self._termination_reason = reason
        self._termination_details = details
        # Use the detailed message if available, otherwise use the short reason
        error_msg = details.get("message", reason) if details else reason
        self.end(status="terminated", error=error_msg)

    def _uses_alert_mode(self) -> bool:
        return self.enforcement == "alert"

    def _check_alert_thresholds(self, action: str, step_number: int):
        if not self._uses_alert_mode():
            return

        current_cost = self.cost_tracker.total_cost
        if self.cost_tracker.max_cost_usd > 0:
            if current_cost >= self.cost_tracker.max_cost_usd * self.alert_threshold:
                self._pause_for_limit(
                    approval_type="cost_limit",
                    action=action,
                    current_value=float(current_cost),
                    limit_value=float(self.cost_tracker.max_cost_usd),
                    unit="usd",
                    message=(
                        f"Run '{self.agent_name}' has crossed "
                        f"{int(self.alert_threshold * 100)}% of its cost budget "
                        f"(${current_cost:.4f}/${self.cost_tracker.max_cost_usd:.2f}). "
                        "Approve to continue or let it terminate on timeout."
                    ),
                    metadata={
                        "blocked_action": action,
                        "current_cost": current_cost,
                        "max_cost": self.cost_tracker.max_cost_usd,
                        "step_number": step_number,
                        "threshold": self.alert_threshold,
                    },
                )
                return

        elapsed = time.time() - self.start_time
        if self.max_runtime_sec > 0 and elapsed >= self.max_runtime_sec * self.alert_threshold:
            self._pause_for_limit(
                approval_type="runtime_limit",
                action=action,
                current_value=float(round(elapsed, 1)),
                limit_value=float(self.max_runtime_sec),
                unit="seconds",
                message=(
                    f"Run '{self.agent_name}' has crossed "
                    f"{int(self.alert_threshold * 100)}% of its runtime budget "
                    f"({format_duration(elapsed)}/{format_duration(self.max_runtime_sec)}). "
                    "Approve to continue or let it terminate on timeout."
                ),
                metadata={
                    "blocked_action": action,
                    "elapsed_seconds": round(elapsed, 1),
                    "max_runtime_seconds": self.max_runtime_sec,
                    "step_number": step_number,
                    "threshold": self.alert_threshold,
                },
            )
            return

        if self.max_steps > 0 and step_number >= self.max_steps * self.alert_threshold:
            self._pause_for_limit(
                approval_type="step_limit",
                action=action,
                current_value=float(step_number),
                limit_value=float(self.max_steps),
                unit="steps",
                message=(
                    f"Run '{self.agent_name}' has crossed "
                    f"{int(self.alert_threshold * 100)}% of its step budget "
                    f"({step_number}/{self.max_steps}). "
                    "Approve to continue or let it terminate on timeout."
                ),
                metadata={
                    "blocked_action": action,
                    "current_steps": step_number,
                    "max_steps": self.max_steps,
                    "threshold": self.alert_threshold,
                },
            )

    def _pause_for_limit(
        self,
        *,
        approval_type: str,
        action: str,
        current_value: float,
        limit_value: float,
        unit: str,
        message: str,
        metadata: dict | None = None,
    ):
        if not self.client.is_connected:
            self._terminate(
                "alert_mode_unavailable",
                details={
                    "error_type": "alert_mode_unavailable",
                    "approval_type": approval_type,
                    "blocked_action": action,
                    "message": (
                        "Alert mode requires a reachable SteerPlane API. "
                        "The API is offline, so the run was terminated instead."
                    ),
                },
            )
            raise RunTerminatedError(
                self.run_id,
                "Alert mode requires a reachable SteerPlane API but the API is offline",
            )

        approval = self.client.request_approval(
            run_id=self.run_id,
            agent_name=self.agent_name,
            approval_type=approval_type,
            current_value=current_value,
            limit_value=limit_value,
            unit=unit,
            message=message,
            timeout_sec=self.alert_timeout_sec,
            channels=self.alert_channels,
            alert_email=self.alert_email,
            alert_webhook_url=self.alert_webhook_url,
            metadata=metadata or {},
        )
        if not approval or not approval.get("id"):
            self._terminate(
                "approval_request_failed",
                details={
                    "error_type": "approval_request_failed",
                    "approval_type": approval_type,
                    "blocked_action": action,
                    "message": (
                        "SteerPlane could not create an approval request, so the run was "
                        "terminated instead of continuing without control."
                    ),
                },
            )
            raise RunTerminatedError(
                self.run_id,
                "Could not create a SteerPlane approval request",
            )

        approval_id = approval["id"]
        self.status = "awaiting_approval"

        if self.log_to_console:
            _safe_print(
                f"   [ALERT] Approval requested for {approval_type.replace('_', ' ')} "
                f"({current_value:.4f} {unit} / {limit_value:.4f} {unit})"
            )
            _safe_print(f"      Waiting up to {self.alert_timeout_sec}s for continue/kill...")

        local_deadline = time.time() + self.alert_timeout_sec + self.alert_poll_interval_sec
        while time.time() <= local_deadline:
            time.sleep(self.alert_poll_interval_sec)
            latest = self.client.get_approval(approval_id)
            if not latest:
                continue

            latest_status = str(latest.get("status", "")).lower()
            if latest_status == "pending":
                continue

            if latest_status == "approved":
                resolution = latest.get("resolution_json") or {}
                self._apply_approval_resolution(approval_type, resolution)
                self.status = "running"
                if self.log_to_console:
                    new_limit = resolution.get("new_limit")
                    if new_limit is not None:
                        _safe_print(
                            f"   [OK] Approval granted. New {approval_type.replace('_', ' ')} "
                            f"limit: {new_limit}"
                        )
                    else:
                        _safe_print("   [OK] Approval granted. Run resumed.")
                return

            error_type = "approval_denied" if latest_status == "denied" else "alert_timeout"
            failure_message = (
                latest.get("resolution_note")
                or (latest.get("resolution_json") or {}).get("reason")
                or latest.get("message")
                or f"Approval {latest_status}"
            )
            self._terminate(
                error_type,
                details={
                    "error_type": error_type,
                    "approval_id": approval_id,
                    "approval_type": approval_type,
                    "blocked_action": action,
                    "message": failure_message,
                },
            )
            raise RunTerminatedError(self.run_id, failure_message)

        self._terminate(
            "alert_timeout",
            details={
                "error_type": "alert_timeout",
                "approval_id": approval_id,
                "approval_type": approval_type,
                "blocked_action": action,
                "message": (
                    f"Approval timed out locally while waiting for {approval_type.replace('_', ' ')} "
                    "continuation."
                ),
            },
        )
        raise RunTerminatedError(
            self.run_id,
            f"Approval timed out while waiting for {approval_type.replace('_', ' ')} continuation",
        )

    def _apply_approval_resolution(self, approval_type: str, resolution: dict):
        new_limit = resolution.get("new_limit")
        if new_limit is None:
            return

        if approval_type == "cost_limit":
            self.cost_tracker.max_cost_usd = float(new_limit)
        elif approval_type == "step_limit":
            self.max_steps = int(new_limit)
        elif approval_type == "runtime_limit":
            self.max_runtime_sec = int(new_limit)

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
        # If _terminate() already called end(), don't overwrite the status
        if self.status in ("terminated", "failed", "completed"):
            return False  # Already finalized
        if exc_type:
            self.end(status="failed", error=str(exc_val))
        else:
            self.end()
        return False  # Don't suppress exceptions
