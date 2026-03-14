"""
SteerPlane SDK — LangChain Integration

Callback handler that automatically captures all LLM calls from LangChain
and feeds them into SteerPlane for cost tracking, loop detection, and policy enforcement.

Usage:
    from steerplane.integrations.langchain import SteerPlaneCallbackHandler

    handler = SteerPlaneCallbackHandler(
        agent_name="my_langchain_bot",
        max_cost_usd=10.0,
        max_steps=100,
    )

    llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
    # That's it. Every LLM call is now monitored and limited.
"""

import time
from typing import Any, Optional
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
        from langchain.schema import LLMResult
    except ImportError:
        raise ImportError(
            "LangChain is required for this integration. "
            "Install it with: pip install langchain-core"
        )

from ..run_manager import RunManager
from ..policy_engine import PolicyEngine
from ..exceptions import CostLimitExceeded, LoopDetectedError, StepLimitExceeded, PolicyViolationError


class SteerPlaneCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that auto-instruments all LLM calls
    with SteerPlane guardrails.

    Automatically captures:
    - Token usage (input + output)
    - Cost calculation with built-in pricing
    - Latency per call
    - Model name

    Automatically enforces:
    - Cost limits (hard ceiling)
    - Step limits
    - Loop detection (repeated prompt patterns)
    - Policy engine (allow/deny lists, rate limits)
    """

    def __init__(
        self,
        agent_name: str = "langchain_agent",
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        max_runtime_sec: int = 3600,
        model: str = "default",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        log_to_console: bool = True,
        # Policy engine options
        allowed_actions: Optional[list[str]] = None,
        denied_actions: Optional[list[str]] = None,
        rate_limits: Optional[list[dict]] = None,
        require_approval: Optional[list[str]] = None,
        approval_callback: Optional[Any] = None,
    ):
        super().__init__()

        # Build policy engine if any rules provided
        policy = None
        if any([allowed_actions, denied_actions, rate_limits, require_approval]):
            from ..policy_engine import RateLimitSpec
            rl_specs = None
            if rate_limits:
                rl_specs = [
                    RateLimitSpec(
                        pattern=r.get("pattern", "*"),
                        max_count=r.get("max_count", 100),
                        window_seconds=r.get("window_seconds", 60),
                    )
                    for r in rate_limits
                ]
            policy = PolicyEngine(
                allowed_actions=allowed_actions or [],
                denied_actions=denied_actions or [],
                rate_limits=rl_specs or [],
                require_approval=require_approval or [],
                approval_callback=approval_callback,
            )

        self.run_manager = RunManager(
            agent_name=agent_name,
            max_cost_usd=max_cost_usd,
            max_steps=max_steps,
            max_runtime_sec=max_runtime_sec,
            model=model,
            api_url=api_url,
            api_key=api_key,
            log_to_console=log_to_console,
            policy=policy,
        )

        self._started = False
        self._call_start_times: dict[str, float] = {}
        self._call_models: dict[str, str] = {}
        self._call_prompts: dict[str, str] = {}

    def _ensure_started(self):
        """Start the run manager if not already started."""
        if not self._started:
            self.run_manager.start()
            self._started = True

    # ─── LLM Callbacks ───────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call starts."""
        self._ensure_started()
        self._call_start_times[str(run_id)] = time.time()

        # Extract model name
        model = kwargs.get("invocation_params", {}).get("model_name", "")
        if not model:
            model = kwargs.get("invocation_params", {}).get("model", "")
        if not model:
            model = serialized.get("kwargs", {}).get("model_name", "unknown")
        self._call_models[str(run_id)] = model

        if prompts:
            self._call_prompts[str(run_id)] = prompts[0][:200]

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chat model call starts."""
        self._ensure_started()
        self._call_start_times[str(run_id)] = time.time()

        model = kwargs.get("invocation_params", {}).get("model_name", "")
        if not model:
            model = kwargs.get("invocation_params", {}).get("model", "")
        if not model:
            model = serialized.get("kwargs", {}).get("model_name", "unknown")
        self._call_models[str(run_id)] = model

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call completes. Logs the step with full telemetry."""
        rid = str(run_id)
        start = self._call_start_times.pop(rid, time.time())
        latency_ms = (time.time() - start) * 1000
        model = self._call_models.pop(rid, "unknown")
        self._call_prompts.pop(rid, None)

        # Extract token usage from response
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if response.llm_output and isinstance(response.llm_output, dict):
            usage = response.llm_output.get("token_usage", {})
            if not usage:
                usage = response.llm_output.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # Log the step — this triggers all guardrail checks
        action = f"llm:{model}"
        self.run_manager.log_step(
            action=action,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens=total_tokens,
            latency_ms=latency_ms,
            model=model,
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call errors."""
        rid = str(run_id)
        start = self._call_start_times.pop(rid, time.time())
        latency_ms = (time.time() - start) * 1000
        model = self._call_models.pop(rid, "unknown")
        self._call_prompts.pop(rid, None)

        self.run_manager.log_step(
            action=f"llm:{model}",
            latency_ms=latency_ms,
            status="failed",
            error=str(error),
        )

    # ─── Tool Callbacks ──────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts."""
        self._call_start_times[str(run_id)] = time.time()
        tool_name = serialized.get("name", "unknown_tool")
        self._call_models[str(run_id)] = tool_name

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool completes."""
        rid = str(run_id)
        start = self._call_start_times.pop(rid, time.time())
        latency_ms = (time.time() - start) * 1000
        tool_name = self._call_models.pop(rid, "unknown_tool")

        self.run_manager.log_step(
            action=f"tool:{tool_name}",
            latency_ms=latency_ms,
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a tool errors."""
        rid = str(run_id)
        start = self._call_start_times.pop(rid, time.time())
        latency_ms = (time.time() - start) * 1000
        tool_name = self._call_models.pop(rid, "unknown_tool")

        self.run_manager.log_step(
            action=f"tool:{tool_name}",
            latency_ms=latency_ms,
            status="failed",
            error=str(error),
        )

    # ─── Lifecycle ───────────────────────────────────────

    def finish(self, status: str = "completed", error: Optional[str] = None):
        """Manually end the run. Call this when your agent finishes."""
        if self._started:
            self.run_manager.end(status=status, error=error)
            self._started = False

    def __del__(self):
        """Auto-end run on garbage collection if not already ended."""
        if self._started:
            try:
                self.run_manager.end(status="completed")
            except Exception:
                pass
