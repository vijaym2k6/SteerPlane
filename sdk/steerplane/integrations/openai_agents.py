"""
SteerPlane SDK — OpenAI Agents SDK Integration

Enforces SteerPlane limits through the Agents SDK's own ``RunHooks``. Each model
call and each tool call counts as one step. A call that would go past a limit is
refused before it starts, and the refusal ends the run.

Usage:
    from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

    hooks = SteerPlaneAgentHooks(
        agent_name="my_openai_agent",
        max_cost_usd=10.0,
        max_steps=100,
    )

    # Option 1: let SteerPlane call the Runner
    result = await hooks.run(agent, "Hello!")

    # Option 2: call the Runner yourself and pass the hooks
    hooks.start()
    result = await Runner.run(agent, "Hello!", hooks=hooks.run_hooks)
    hooks.finish()

Calling the Runner yourself, a stop made before a tool call reaches you wrapped in
the Agents SDK's ``UserError``, with the SteerPlane error as its cause. ``hooks.run``
raises the SteerPlane error directly.

Coverage: RunHooks see the run they are passed to. An agent used through
``Agent.as_tool()`` runs as a separate run, so its calls are not counted. To
limit every call whatever the agent structure, use the SteerPlane gateway.

One instance is one run. Create a new one for each run.
"""

import logging
from typing import Any, Optional

from ..run_manager import RunManager
from ..policy_engine import PolicyEngine
from ..exceptions import SteerPlaneError

logger = logging.getLogger("steerplane.openai_agents")


def _steerplane_cause(error: BaseException) -> Optional[SteerPlaneError]:
    """The SteerPlane error behind this one. The Agents SDK wraps errors from tool hooks."""
    seen: BaseException | None = error
    while seen is not None:
        if isinstance(seen, SteerPlaneError):
            return seen
        seen = seen.__cause__ or seen.__context__
    return None


def _model_name(agent: Any, default: str) -> str:
    """The agent's model as a string. It may be a name, a Model object or unset."""
    model = getattr(agent, "model", None)
    if isinstance(model, str) and model:
        return model
    return str(getattr(model, "model", "") or default)


class SteerPlaneAgentHooks:
    """
    OpenAI Agents SDK integration.

    Records model calls with their reported token usage, tool calls and handoffs.

    Enforces, before each model call and tool call:
    - Cost limit
    - Step limit
    - Runtime limit
    - Policy rules, matched against the tool's name

    Loop detection is off by default here. It matches on action names only, so
    with it on, a run calling the same tool over a list is stopped as a loop.
    Pass ``detect_loops=True`` to turn it on.
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
        detect_loops: bool = False,
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
            detect_loops=detect_loops,
        )
        self._model = model
        self._started = False
        self._run_hooks: Any = None

    @property
    def run_manager(self) -> RunManager:
        """Access the underlying RunManager."""
        return self._run_manager

    @property
    def run_hooks(self) -> Any:
        """The ``RunHooks`` object to pass as ``Runner.run(..., hooks=...)``."""
        if self._run_hooks is None:
            self._run_hooks = _build_run_hooks(self)
        return self._run_hooks

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
        """Log a model call. The hooks do this for you when you pass them to the Runner."""
        used_model = model or self._model
        self._run_manager.log_step(
            action=f"llm_call:{used_model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=used_model,
            check_policy=False,
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
        """Log a tool call. The hooks do this for you when you pass them to the Runner."""
        self._run_manager.log_step(
            action=f"tool:{tool_name}",
            metadata={
                "arguments": str(arguments)[:500] if arguments else "",
                "result_preview": result_preview[:200],
            },
        )

    def log_handoff(self, from_agent: str, to_agent: str, reason: str = ""):
        """Log an agent handoff yourself. This counts as one step."""
        self._run_manager.log_step(
            action=f"handoff:{from_agent}->{to_agent}",
            metadata={"reason": reason},
        )

    async def run(self, agent: Any, input_text: str, **kwargs) -> Any:
        """
        Start SteerPlane, run the agent with the hooks attached, and finish.

        Usage:
            result = await hooks.run(agent, "Hello!")
        """
        try:
            from agents import Runner
        except ImportError:
            raise ImportError(
                "OpenAI Agents SDK is required. Install with: pip install openai-agents"
            )

        if "hooks" in kwargs:
            raise ValueError(
                "hooks.run() attaches its own RunHooks. To use yours as well, call "
                "Runner.run() yourself and combine them with hooks.run_hooks."
            )

        self.start()
        try:
            result = await Runner.run(agent, input_text, hooks=self.run_hooks, **kwargs)
            self.finish()
            return result
        except SteerPlaneError:
            raise
        except Exception as e:
            cause = _steerplane_cause(e)
            if cause is not None:
                raise cause from e
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


def _build_run_hooks(owner: SteerPlaneAgentHooks) -> Any:
    """Build the RunHooks adapter. The Agents SDK is imported only when it's needed."""
    try:
        from agents import RunHooks
    except ImportError:
        raise ImportError("OpenAI Agents SDK is required. Install with: pip install openai-agents")

    run = owner.run_manager

    class _SteerPlaneRunHooks(RunHooks):
        async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
            if not owner._started:
                owner.start()
            run.check_before_step()

        async def on_llm_end(self, context, agent, response) -> None:
            usage = getattr(response, "usage", None)
            model = _model_name(agent, owner._model)
            run.log_step(
                action=f"llm_call:{model}",
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                model=model,
                check_policy=False,
            )

        async def on_tool_start(self, context, agent, tool) -> None:
            if not owner._started:
                owner.start()
            run.check_before_step(tool.name)

        async def on_tool_end(self, context, agent, tool, result) -> None:
            run.log_step(
                action=f"tool:{tool.name}",
                check_policy=False,
                metadata={"result_preview": str(result)[:200]},
            )

    return _SteerPlaneRunHooks()
