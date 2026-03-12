"""
SteerPlane SDK — Guard Decorator

The primary developer-facing API. Wrap any agent function with @guard
to get automatic loop detection, cost limits, step limits, and telemetry.

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
from .config import get_config

logger = logging.getLogger("steerplane")


# Thread-local storage for the active run manager
_active_run: RunManager | None = None


def get_active_run() -> RunManager | None:
    """Get the currently active RunManager (if inside a guarded function)."""
    return _active_run


def guard(
    max_cost_usd: float = 50.0,
    max_steps: int = 200,
    max_runtime_sec: int = 3600,
    agent_name: str | None = None,
    model: str = "default",
    loop_window_size: int = 8,
    log_to_console: bool = True,
    api_url: str | None = None,
    api_key: str | None = None,
    allowed_actions: list[str] | None = None,
    denied_actions: list[str] | None = None,
    rate_limits: list[RateLimitSpec | dict] | None = None,
    require_approval: list[str] | None = None,
    approval_callback=None,
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
            global _active_run

            name = agent_name or func.__name__

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

            # Create run manager with guard configuration
            run = RunManager(
                agent_name=name,
                max_cost_usd=max_cost_usd,
                max_steps=max_steps,
                max_runtime_sec=max_runtime_sec,
                loop_window_size=loop_window_size,
                model=model,
                api_url=api_url,
                api_key=api_key,
                log_to_console=log_to_console,
                policy=policy,
            )

            # Set as active run
            _active_run = run

            try:
                run.start()
                result = func(*args, **kwargs)
                run.end(status="completed")
                return result
            except Exception as e:
                run.end(status="failed", error=str(e))
                raise
            finally:
                _active_run = None

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
        approval_callback=None,
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
        )

    def create_run(self, **kwargs) -> RunManager:
        """Create a run without starting it (for explicit management)."""
        return self.run(**kwargs)
