"""
SteerPlane SDK — Utilities

Helper functions for ID generation, timestamps, and formatting.
"""

import uuid
import time
from datetime import datetime, timezone


def generate_run_id() -> str:
    """Generate a unique run ID."""
    short_id = uuid.uuid4().hex[:12]
    return f"run_{short_id}"


def generate_step_id() -> str:
    """Generate a unique step ID."""
    short_id = uuid.uuid4().hex[:8]
    return f"step_{short_id}"


def now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def now_epoch_ms() -> int:
    """Get current time as epoch milliseconds."""
    return int(time.time() * 1000)


def format_cost(cost: float) -> str:
    """Format a cost value for display."""
    if cost < 0.01:
        return f"${cost:.6f}"
    elif cost < 1.0:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"


def format_duration(seconds: float) -> str:
    """Format a duration in seconds for display."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
