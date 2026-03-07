"""
SteerPlane SDK

Agent Control Plane for Autonomous Systems.
"Agents don't fail in the dark anymore."

Usage:
    from steerplane import guard, SteerPlane

    # Decorator API (minimal integration)
    @guard(max_cost_usd=10, max_steps=50)
    def run_agent():
        agent.run()

    # Context Manager API (full control)
    sp = SteerPlane(agent_id="my_bot")
    with sp.run(max_cost_usd=10) as run:
        run.log_step("search", tokens=100)

    # Programmatic API
    sp = SteerPlane(agent_id="my_bot")
    run = sp.create_run(max_cost_usd=10)
    run.start()
    run.log_step("search", tokens=100)
    run.end()
"""

__version__ = "0.1.0"

from .guard import guard, SteerPlane, get_active_run
from .run_manager import RunManager
from .loop_detector import LoopDetector, detect_loop
from .cost_tracker import CostTracker
from .telemetry import TelemetryCollector, StepEvent
from .config import configure, get_config
from .exceptions import (
    SteerPlaneError,
    LoopDetectedError,
    CostLimitExceeded,
    StepLimitExceeded,
    RunTerminatedError,
    APIConnectionError,
)

__all__ = [
    # Main APIs
    "guard",
    "SteerPlane",
    "get_active_run",
    # Core classes
    "RunManager",
    "LoopDetector",
    "CostTracker",
    "TelemetryCollector",
    "StepEvent",
    # Utilities
    "detect_loop",
    "configure",
    "get_config",
    # Exceptions
    "SteerPlaneError",
    "LoopDetectedError",
    "CostLimitExceeded",
    "StepLimitExceeded",
    "RunTerminatedError",
    "APIConnectionError",
    # Metadata
    "__version__",
]
