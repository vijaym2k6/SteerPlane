"""
SteerPlane SDK — Guard Decorator

The primary developer-facing API. Wrap any agent function with @guard
to get automatic loop detection, cost limits, step limits, and telemetry.

Supports .steerplane.yml config file for default values.
Explicit decorator parameters always override config file values.

Usage:
    from steerplane import guard

    @guard(max_cost_usd=10, max_steps=50)
    def run_agent():
        agent.run()
"""

import functools
import logging
from typing import Callable, Any

from .run_manager import RunManager
from .policy_engine import PolicyEngine, RateLimitSpec
from .config_file import get_with_fallback

logger = logging.getLogger("steerplane")


def guard(
    max_cost_usd: float | None = None,
    max_steps: int | None = None,
    max_runtime_sec: int | None = None,
    agent_name: str | None = None,
    model: str | None = None,
    loop_window_size: int | None = None,
    log_to_console: bool = True,
    api_url: str | None = None,
    api_key: str | None = None,
    allowed_actions: list[str] | None = None,
    denied_actions: list[str] | None = None,
    rate_limits: list[RateLimitSpec | dict] | None = None,
    require_approval: list[str] | None = None,
    approval_callback: Callable[[str, dict | None], bool] | None = None,
    enforcement: str | None = None,
    alert_threshold: float | None = None,
    alert_timeout_sec: int | None = None,
    alert_channels: list[str] | None = None,
    alert_email: str | None = None,
    alert_webhook_url: str | None = None,
) -> Callable:
    """
    Guard decorator for agent functions.

    Wraps an agent function with SteerPlane's guard system:
    - Policy engine (allow/deny lists, rate limits, approval)
    - Loop detection (sliding window)
    - Cost limit enforcement
    - Step limit enforcement
    - Runtime limit enforcement
    - Full telemetry logging

    Parameters merge in priority order:
        1. Explicit decorator arguments (highest)
        2. .steerplane.yml config file
        3. Hardcoded defaults (lowest)

    Args:
        max_cost_usd: Maximum allowed cost in USD.
        max_steps: Maximum number of steps allowed.
        max_runtime_sec: Maximum runtime in seconds.
        agent_name: Name of the agent (defaults to function name).
        model: Default model for cost calculation.
        loop_window_size: Window size for loop detection.
        log_to_console: Whether to print step logs to console.
        api_url: SteerPlane API URL (overrides config).
        api_key: API key (overrides config).
        allowed_actions: Glob patterns for permitted actions.
        denied_actions: Glob patterns for forbidden actions.
        rate_limits: Per-action rate limits.
        require_approval: Actions requiring human approval.
        approval_callback: Callback for approval workflow.
        enforcement: "kill" or "alert" for financial/runtime limits.
        alert_threshold: Trigger approval at this fraction of the limit.
        alert_timeout_sec: Timeout before an unanswered alert auto-terminates.
        alert_channels: Notification channels such as ["email", "webhook"].
        alert_email: Email recipient for alert notifications.
        alert_webhook_url: Webhook target for alert notifications.

    Returns:
        Decorated function with guard capabilities.

    Example:
        @guard(max_cost_usd=10, max_steps=50, denied_actions=["delete_*"])
        def run_my_agent():
            agent.run()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Merge: explicit params > .steerplane.yml > hardcoded defaults
            _cost = get_with_fallback(max_cost_usd, "max_cost_usd", 50.0)
            _steps = get_with_fallback(max_steps, "max_steps", 200)
            _runtime = get_with_fallback(max_runtime_sec, "max_runtime_sec", 3600)
            _model = get_with_fallback(model, "model", "default")
            _window = get_with_fallback(loop_window_size, "loop_window_size", 8)
            _enforcement = get_with_fallback(enforcement, "enforcement", "kill")
            _threshold = get_with_fallback(alert_threshold, "alert_threshold", 0.8)
            _timeout = get_with_fallback(alert_timeout_sec, "alert_timeout_sec", 1800)
            _api_url = get_with_fallback(api_url, "api_url", None)
            _api_key = get_with_fallback(api_key, "api_key", None)
            _email = get_with_fallback(alert_email, "alert_email", None)
            _webhook = get_with_fallback(alert_webhook_url, "alert_webhook_url", None)
            _denied = denied_actions or get_with_fallback(None, "denied_actions", None)
            _allowed = allowed_actions or get_with_fallback(None, "allowed_actions", None)
            _require = require_approval or get_with_fallback(None, "require_approval", None)
            name = agent_name or func.__name__

            # Build policy engine if any rules are specified
            policy = None
            if _allowed or _denied or rate_limits or _require:
                policy = PolicyEngine(
                    allowed_actions=_allowed,
                    denied_actions=_denied,
                    rate_limits=rate_limits,
                    require_approval=_require,
                    approval_callback=approval_callback,
                )

            # Create run manager with guard configuration
            run = RunManager(
                agent_name=name,
                max_cost_usd=_cost,
                max_steps=_steps,
                max_runtime_sec=_runtime,
                loop_window_size=_window,
                model=_model,
                api_url=_api_url,
                api_key=_api_key,
                log_to_console=log_to_console,
                policy=policy,
                enforcement=_enforcement,
                alert_threshold=_threshold,
                alert_timeout_sec=_timeout,
                alert_channels=alert_channels,
                alert_email=_email,
                alert_webhook_url=_webhook,
            )

            try:
                run.start()
                result = func(*args, **kwargs)
                run.end(status="completed")
                return result
            except Exception as e:
                run.end(status="failed", error=str(e))
                raise

        # Attach run manager accessor to the wrapper
        wrapper._steerplane_guarded = True
        return wrapper

    return decorator


class SteerPlane:
    """
    Main SDK entry point for programmatic usage.

    Provides both context manager and explicit API for run management.

    Usage (context manager):
        sp = SteerPlane(agent_id="my_bot")
        with sp.run() as run:
            run.log_step("query_db", tokens=380, cost=0.002)
            run.log_step("generate_response", tokens=1240, cost=0.008)

    Usage (explicit):
        sp = SteerPlane(agent_id="my_bot")
        run = sp.create_run(max_cost_usd=10)
        run.start()
        run.log_step("search", tokens=100)
        run.end()
    """

    def __init__(
        self,
        agent_id: str = "default_agent",
        api_url: str | None = None,
        api_key: str | None = None,
        model: str = "default",
    ):
        self.agent_id = agent_id
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def run(
        self,
        run_id: str | None = None,
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        max_runtime_sec: int = 3600,
        loop_window_size: int = 8,
        log_to_console: bool = True,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        rate_limits: list[RateLimitSpec | dict] | None = None,
        require_approval: list[str] | None = None,
        approval_callback: Callable[[str, dict | None], bool] | None = None,
        enforcement: str = "kill",
        alert_threshold: float = 0.8,
        alert_timeout_sec: int = 1800,
        alert_channels: list[str] | None = None,
        alert_email: str | None = None,
        alert_webhook_url: str | None = None,
    ) -> RunManager:
        """
        Create a new run context manager.

        Usage:
            with sp.run(max_cost_usd=10, denied_actions=["delete_*"]) as run:
                run.log_step("action", tokens=100)
        """
        # Build policy engine if any rules are specified
        policy = None
        if allowed_actions or denied_actions or rate_limits or require_approval:
            policy = PolicyEngine(
                allowed_actions=allowed_actions,
                denied_actions=denied_actions,
                rate_limits=rate_limits,
                require_approval=require_approval,
                approval_callback=approval_callback,
            )

        return RunManager(
            agent_name=self.agent_id,
            run_id=run_id,
            max_cost_usd=max_cost_usd,
            max_steps=max_steps,
            max_runtime_sec=max_runtime_sec,
            loop_window_size=loop_window_size,
            model=self.model,
            api_url=self.api_url,
            api_key=self.api_key,
            log_to_console=log_to_console,
            policy=policy,
            enforcement=enforcement,
            alert_threshold=alert_threshold,
            alert_timeout_sec=alert_timeout_sec,
            alert_channels=alert_channels,
            alert_email=alert_email,
            alert_webhook_url=alert_webhook_url,
        )

    def create_run(self, **kwargs) -> RunManager:
        """Create a run without starting it (for explicit management)."""
        return self.run(**kwargs)
