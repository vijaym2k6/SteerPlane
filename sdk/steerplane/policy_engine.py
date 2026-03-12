"""
SteerPlane SDK — Policy Engine

Rule-based action control for agent runs.
Supports allow/deny lists (with glob patterns), per-action rate limiting,
and human-in-the-loop approval workflows.
"""

import time
import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .exceptions import PolicyViolationError

logger = logging.getLogger("steerplane")


@dataclass
class PolicyDecision:
    """Result of a policy check."""
    allowed: bool
    action: str
    rule: str = ""       # Which rule matched (e.g. "deny:delete_*")
    reason: str = ""     # Human-readable explanation


@dataclass
class RateLimitSpec:
    """Rate limit specification for an action pattern."""
    pattern: str
    max_count: int
    window_seconds: float


class PolicyEngine:
    """
    Evaluates incoming actions against a set of policy rules.

    Rules are checked in order:
      1. Deny list (block immediately)
      2. Allow list (if non-empty, action must match at least one pattern)
      3. Rate limits (sliding-window counters per action pattern)
      4. Approval workflow (calls callback; block if denied or no callback)

    Args:
        allowed_actions: Glob patterns for permitted actions. If empty, all
            actions are permitted (unless denied).
        denied_actions: Glob patterns for forbidden actions.
        rate_limits: List of RateLimitSpec or dicts with keys
            ``pattern``, ``max_count``, ``window_seconds``.
        require_approval: Glob patterns requiring human approval.
        approval_callback: ``(action, metadata) → bool`` called when an
            action matches a require_approval pattern.
    """

    def __init__(
        self,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        rate_limits: list[RateLimitSpec | dict] | None = None,
        require_approval: list[str] | None = None,
        approval_callback: Callable[[str, dict | None], bool] | None = None,
    ):
        self.allowed_actions: list[str] = allowed_actions or []
        self.denied_actions: list[str] = denied_actions or []
        self.require_approval: list[str] = require_approval or []
        self.approval_callback = approval_callback

        # Normalise rate-limit specs
        self.rate_limits: list[RateLimitSpec] = []
        for rl in (rate_limits or []):
            if isinstance(rl, dict):
                self.rate_limits.append(RateLimitSpec(**rl))
            else:
                self.rate_limits.append(rl)

        # Sliding-window timestamps keyed by pattern
        self._rate_windows: dict[str, list[float]] = {
            rl.pattern: [] for rl in self.rate_limits
        }

    # ────────────────────── public API ──────────────────────

    def check(self, action: str, metadata: dict | None = None) -> PolicyDecision:
        """
        Evaluate *action* against all policy rules.

        Returns a ``PolicyDecision`` on success.
        Raises ``PolicyViolationError`` if the action is denied.
        """
        # 1. Deny list — checked first, always wins
        for pattern in self.denied_actions:
            if fnmatch.fnmatch(action, pattern):
                self._deny(action, rule=f"deny:{pattern}",
                           reason=f"Action '{action}' matches deny pattern '{pattern}'")

        # 2. Allow list — if non-empty, action MUST match at least one entry
        if self.allowed_actions:
            if not any(fnmatch.fnmatch(action, p) for p in self.allowed_actions):
                self._deny(action, rule="allow_list",
                           reason=f"Action '{action}' is not in the allow list")

        # 3. Rate limits
        now = time.monotonic()
        for rl in self.rate_limits:
            if fnmatch.fnmatch(action, rl.pattern):
                window = self._rate_windows[rl.pattern]
                # Prune expired timestamps
                cutoff = now - rl.window_seconds
                window[:] = [t for t in window if t > cutoff]

                if len(window) >= rl.max_count:
                    self._deny(
                        action,
                        rule=f"rate_limit:{rl.pattern}",
                        reason=(
                            f"Rate limit exceeded for '{action}': "
                            f"{rl.max_count} calls per {rl.window_seconds}s"
                        ),
                    )
                # Record this call
                window.append(now)

        # 4. Approval workflow
        for pattern in self.require_approval:
            if fnmatch.fnmatch(action, pattern):
                if self.approval_callback is None:
                    self._deny(
                        action,
                        rule=f"approval:{pattern}",
                        reason=f"Action '{action}' requires approval but no callback is set",
                    )
                elif not self.approval_callback(action, metadata):
                    self._deny(
                        action,
                        rule=f"approval:{pattern}",
                        reason=f"Action '{action}' was denied by the approval callback",
                    )

        return PolicyDecision(allowed=True, action=action)

    @property
    def has_rules(self) -> bool:
        """True if at least one rule is configured."""
        return bool(
            self.allowed_actions
            or self.denied_actions
            or self.rate_limits
            or self.require_approval
        )

    # ────────────────────── internals ──────────────────────

    @staticmethod
    def _deny(action: str, rule: str, reason: str):
        """Raise a PolicyViolationError."""
        raise PolicyViolationError(action=action, rule=rule, reason=reason)
