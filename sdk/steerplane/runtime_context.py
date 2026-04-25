"""
Runtime context helpers for the active SteerPlane run.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .run_manager import RunManager


_active_run: ContextVar["RunManager | None"] = ContextVar(
    "steerplane_active_run",
    default=None,
)


def get_active_run() -> "RunManager | None":
    """Get the run active in the current execution context."""
    return _active_run.get()


def set_active_run(run: "RunManager") -> Token:
    """Bind a run to the current execution context."""
    return _active_run.set(run)


def reset_active_run(token: Token) -> None:
    """Restore the previous execution context binding."""
    _active_run.reset(token)
