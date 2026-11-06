"""
SteerPlane SDK — LangChain Integration

Callback handler that enforces SteerPlane limits on LangChain and LangGraph runs.
Each model call and each tool call counts as one step. A call that would go past
a limit is refused before it starts, and the refusal ends the run.

Usage:
    from steerplane.integrations.langchain import SteerPlaneCallbackHandler

    handler = SteerPlaneCallbackHandler(
        agent_name="my_langchain_bot",
        max_cost_usd=10.0,
        max_steps=100,
    )

    # Pass it on the call, so it reaches the model and the tools
    result = agent.invoke(inputs, config={"callbacks": [handler]})
    handler.finish()

Coverage: LangChain callbacks reach only what they are passed to. A handler set on
the model alone doesn't see tools, and a model that reports no token usage costs
$0 here. To limit every call whatever the agent structure, use the SteerPlane
gateway.

One handler is one run. Create a new one for each run.
"""

import logging
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

logger = logging.getLogger("steerplane.langchain")


def _usage_from_response(response: Any) -> tuple[int, int, int]:
    """Input, output and total tokens from whichever place the model reported them."""
    if isinstance(response.llm_output, dict):
        usage = response.llm_output.get("token_usage") or response.llm_output.get("usage")
        if usage:
            input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            total = usage.get("total_tokens") or input_tokens + output_tokens
            return input_tokens, output_tokens, total

    # Newer chat models and streaming report usage on the message itself.
    input_tokens = output_tokens = 0
    for generations in response.generations or []:
        for generation in generations:
            usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
            if usage:
                input_tokens += usage.get("input_tokens", 0) or 0
                output_tokens += usage.get("output_tokens", 0) or 0
    return input_tokens, output_tokens, input_tokens + output_tokens


class SteerPlaneCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler.

    Records model calls with their reported token usage and cost, and tool calls.

    Enforces, before each model call and tool call:
    - Cost limit
    - Step limit
    - Runtime limit
    - Policy rules, matched against the tool's name

    A refusal is raised through LangChain and stops the run. Pass ``enforce=False``
    to record only: LangChain then logs the refusal and the agent keeps going.

    Loop detection is off by default here. It matches on action names only, so
    with it on, a run calling the same tool over a list is stopped as a loop.
    Pass ``detect_loops=True`` to turn it on.
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
        loop_window_size: int = 8,
        enforce: bool = True,
        # Policy engine options
        allowed_actions: Optional[list[str]] = None,
        denied_actions: Optional[list[str]] = None,
        rate_limits: Optional[list[dict]] = None,
        require_approval: Optional[list[str]] = None,
        approval_callback: Optional[Any] = None,
        detect_loops: bool = False,
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

        # Ask LangChain to re-raise exceptions from this handler instead of
        # logging and continuing. Without this, LangChain's callback manager
        # swallows SteerPlaneError (see langchain_core.callbacks.manager
        # .handle_event) and the agent keeps running after a violation.
        self.raise_error = enforce

        self.run_manager = RunManager(
            agent_name=agent_name,
            max_cost_usd=max_cost_usd,
            max_steps=max_steps,
            max_runtime_sec=max_runtime_sec,
            loop_window_size=loop_window_size,
            model=model,
            api_url=api_url,
            api_key=api_key,
            log_to_console=log_to_console,
            policy=policy,
            detect_loops=detect_loops,
        )

        self._started = False
        self._call_start_times: dict[str, float] = {}
        self._call_models: dict[str, str] = {}
        self._call_prompts: dict[str, str] = {}
        self._warned_no_usage = False

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
        """Called when an LLM call starts. Refuses it if the run is out of budget."""
        self._ensure_started()
        self.run_manager.check_before_step()
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
        """Called when a chat model call starts. Refuses it if the run is out of budget."""
        self._ensure_started()
        self.run_manager.check_before_step()
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

        input_tokens, output_tokens, total_tokens = _usage_from_response(response)
        if not total_tokens and not self._warned_no_usage:
            self._warned_no_usage = True
            logger.warning(
                "SteerPlane: model '%s' reported no token usage, so this call costs $0 "
                "against the cost limit. The step limit still applies.",
                model,
            )

        # Log the step — this triggers all guardrail checks
        self.run_manager.log_step(
            action=f"llm:{model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens=total_tokens,
            latency_ms=latency_ms,
            model=model,
            check_policy=False,
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

        if self.run_manager.is_terminated:
            return
        self.run_manager.log_step(
            action=f"llm:{model}",
            latency_ms=latency_ms,
            status="failed",
            error=str(error),
            check_policy=False,
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
        """Called before a tool runs. Refuses it if policy or the budget says no."""
        self._ensure_started()
        tool_name = (serialized or {}).get("name") or kwargs.get("name") or "unknown_tool"
        self.run_manager.check_before_step(tool_name, {"input": str(input_str)[:500]})
        self._call_start_times[str(run_id)] = time.time()
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
            check_policy=False,
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

        if self.run_manager.is_terminated:
            return
        self.run_manager.log_step(
            action=f"tool:{tool_name}",
            latency_ms=latency_ms,
            status="failed",
            error=str(error),
            check_policy=False,
        )

    # ─── Lifecycle ───────────────────────────────────────

    def finish(self, status: str = "completed", error: Optional[str] = None):
        """Manually end the run. Call this when your agent finishes."""
        if self._started:
            self.run_manager.end(status=status, error=error)
            self._started = False

    def __del__(self):
        """Auto-end run on garbage collection if not already ended."""
        if getattr(self, "_started", False):
            try:
                self.run_manager.end(status="completed")
            except Exception:
                pass
