"""
SteerPlane SDK — OpenAI Agents SDK Integration

Hooks into the OpenAI Agents SDK (agents-sdk) via the tracing/lifecycle
hooks to automatically monitor all LLM calls, tool invocations, and
handoffs with SteerPlane guardrails.

Usage:
    from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

    hooks = SteerPlaneAgentHooks(
        agent_name="my_openai_agent",
        max_cost_usd=10.0,
        max_steps=100,
    )

    # Option 1: Wrap the Runner
    result = await hooks.run(agent, "Hello!")

    # Option 2: Manual lifecycle
    hooks.start()
    result = await Runner.run(agent, "Hello!")
    hooks.finish()
"""

import time
import logging
from typing import Any, Optional

from ..run_manager import RunManager
from ..policy_engine import PolicyEngine
from ..exceptions import (
    CostLimitExceeded,
    LoopDetectedError,
    StepLimitExceeded,
    PolicyViolationError,
)

logger = logging.getLogger("steerplane.openai_agents")

# Pricing for OpenAI models (per 1M tokens)
_OPENAI_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD from token counts."""
    normalized = model.lower().strip()
    for prefix in sorted(_OPENAI_PRICING, key=len, reverse=True):
        if normalized.startswith(prefix):
            pricing = _OPENAI_PRICING[prefix]
            return round(
                input_tokens * pricing["input"] / 1_000_000
                + output_tokens * pricing["output"] / 1_000_000,
                8,
            )
    # Default pricing
    return round(
        input_tokens * 2.0 / 1_000_000 + output_tokens * 2.0 / 1_000_000, 8
    )


class SteerPlaneAgentHooks:
    """
    OpenAI Agents SDK integration that auto-instruments all agent activity
    with SteerPlane guardrails.

    Automatically captures:
    - LLM call costs and token usage
    - Tool invocations
    - Agent handoffs
    - Total run cost and step counts

    Automatically enforces:
    - Cost limits (hard ceiling)
    - Step limits
    - Loop detection
    - Policy engine rules
    """

    def __init__(
        self,
        agent_name: str = "openai_agent",
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        max_runtime_sec: int = 3600,
        model: str = "gpt-4o",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        log_to_console: bool = True,
        # Policy engine options
        allowed_actions: Optional[list[str]] = None,
        denied_actions: Optional[list[str]] = None,
        rate_limits: Optional[list[dict]] = None,
        require_approval: Optional[list[str]] = None,
        approval_callback: Optional[Any] = None,
        enforcement: str = "kill",
    ):
        # Build policy engine if any rules provided
        policy = None
        if allowed_actions or denied_actions or rate_limits or require_approval:
            policy = PolicyEngine(
                allowed_actions=allowed_actions,
                denied_actions=denied_actions,
                rate_limits=rate_limits,
                require_approval=require_approval,
                approval_callback=approval_callback,
            )

        self._run_manager = RunManager(
            agent_name=agent_name,
            max_cost_usd=max_cost_usd,
            max_steps=max_steps,
            max_runtime_sec=max_runtime_sec,
            model=model,
            api_url=api_url,
            api_key=api_key,
            log_to_console=log_to_console,
            policy=policy,
            enforcement=enforcement,
        )
        self._model = model
        self._started = False

    @property
    def run_manager(self) -> RunManager:
        """Access the underlying RunManager."""
        return self._run_manager

    def start(self):
        """Start the SteerPlane run. Call before running the agent."""
        self._run_manager.start()
        self._started = True

    def finish(self):
        """End the SteerPlane run. Call after the agent completes."""
        if self._started:
            self._run_manager.end(status="completed")
            self._started = False

    def log_llm_call(
        self,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0,
        prompt_preview: str = "",
    ):
        """Log an LLM call manually (if not using auto-instrumentation)."""
        used_model = model or self._model
        cost = _estimate_cost(used_model, input_tokens, output_tokens)
        self._run_manager.log_step(
            action=f"llm_call:{used_model}",
            tokens=input_tokens + output_tokens,
            cost=cost,
            model=used_model,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "prompt_preview": prompt_preview[:200],
            },
        )

    def log_tool_call(
        self,
        tool_name: str,
        arguments: dict | None = None,
        result_preview: str = "",
    ):
        """Log a tool invocation."""
        self._run_manager.log_step(
            action=f"tool:{tool_name}",
            metadata={
                "arguments": str(arguments)[:500] if arguments else "",
                "result_preview": result_preview[:200],
            },
        )

    def log_handoff(self, from_agent: str, to_agent: str, reason: str = ""):
        """Log an agent handoff."""
        self._run_manager.log_step(
            action=f"handoff:{from_agent}->{to_agent}",
            metadata={"reason": reason},
        )

    async def run(self, agent: Any, input_text: str, **kwargs) -> Any:
        """
        Convenience wrapper that starts SteerPlane, runs the agent, and finishes.

        Usage:
            result = await hooks.run(agent, "Hello!")
        """
        try:
            from agents import Runner
        except ImportError:
            raise ImportError(
                "OpenAI Agents SDK is required. Install with: pip install openai-agents"
            )

        self.start()
        try:
            result = await Runner.run(agent, input_text, **kwargs)
            self.finish()
            return result
        except (CostLimitExceeded, StepLimitExceeded, LoopDetectedError, PolicyViolationError):
            raise
        except Exception as e:
            if self._started:
                self._run_manager.end(status="failed", error=str(e))
                self._started = False
            raise

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finish()
        elif self._started:
            self._run_manager.end(status="failed", error=str(exc_val))
            self._started = False
        return False
