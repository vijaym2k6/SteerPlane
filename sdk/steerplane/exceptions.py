"""
SteerPlane SDK — Custom Exceptions

All errors raised by the SteerPlane guard system.
"""


class SteerPlaneError(Exception):
    """Base exception for all SteerPlane errors."""
    pass


class LoopDetectedError(SteerPlaneError):
    """Raised when a repeating action pattern is detected."""

    def __init__(self, pattern: list, window_size: int):
        self.pattern = pattern
        self.window_size = window_size
        super().__init__(
            f"🔄 Loop detected! Repeating pattern {pattern} "
            f"found in last {window_size} actions. Run terminated."
        )


class CostLimitExceeded(SteerPlaneError):
    """Raised when cumulative run cost exceeds the configured limit."""

    def __init__(self, current_cost: float, max_cost: float):
        self.current_cost = current_cost
        self.max_cost = max_cost
        super().__init__(
            f"💰 Cost limit exceeded! Current: ${current_cost:.4f}, "
            f"Limit: ${max_cost:.2f}. Run terminated."
        )


class StepLimitExceeded(SteerPlaneError):
    """Raised when the number of steps exceeds the configured limit."""

    def __init__(self, current_steps: int, max_steps: int):
        self.current_steps = current_steps
        self.max_steps = max_steps
        super().__init__(
            f"🚫 Step limit exceeded! Steps: {current_steps}, "
            f"Limit: {max_steps}. Run terminated."
        )


class RunTerminatedError(SteerPlaneError):
    """Raised when a run is forcefully terminated."""

    def __init__(self, run_id: str, reason: str = "Manual termination"):
        self.run_id = run_id
        self.reason = reason
        super().__init__(
            f"⛔ Run {run_id} terminated. Reason: {reason}"
        )


class PolicyViolationError(SteerPlaneError):
    """Raised when an action is blocked by the policy engine."""

    def __init__(self, action: str, rule: str, reason: str):
        self.action = action
        self.rule = rule
        self.reason = reason
        super().__init__(
            f"🛡️ Policy violation: {reason} [rule={rule}]"
        )


class APIConnectionError(SteerPlaneError):
    """Raised when the SDK cannot connect to the SteerPlane API."""

    def __init__(self, url: str, detail: str = ""):
        self.url = url
        self.detail = detail
        super().__init__(
            f"🔌 Cannot connect to SteerPlane API at {url}. {detail}"
        )
