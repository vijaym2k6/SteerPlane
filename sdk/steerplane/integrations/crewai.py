"""
SteerPlane SDK — CrewAI Integration

Enforces SteerPlane limits through CrewAI's own before and after hooks for model
calls and tool calls. Each model call and each tool call counts as one step. A
call that would go past a limit is refused before it starts, and the refusal
ends the run.

Usage:
    from steerplane.integrations.crewai import SteerPlaneCrewMonitor

    monitor = SteerPlaneCrewMonitor(
        agent_name="my_crew",
        max_cost_usd=25.0,
        max_steps=200,
    )

    crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task])

    # Raises the SteerPlane error if a limit stops the crew
    result = monitor.kickoff(crew)

Calling ``crew.kickoff()`` yourself works too, with ``monitor.start()`` before it
and ``monitor.finish()`` after it. CrewAI then raises its own "blocked" error, and
the reason is in ``monitor.stop_error``.

Needs CrewAI 1.15.35 or newer. CrewAI's hooks apply to the whole process, so use one
monitor per crew, and run monitored crews one at a time unless they go through
``monitor.kickoff``. One monitor is one run. Create a new one for each run.
"""

import logging
import threading
from typing import Any, Optional

from ..run_manager import RunManager
from ..policy_engine import PolicyEngine
from ..exceptions import SteerPlaneError

logger = logging.getLogger("steerplane.crewai")


def _model_name(llm: Any, default: str) -> str:
    """The model name from a CrewAI LLM, which may be an object or a plain string."""
    if isinstance(llm, str):
        return llm
    return str(getattr(llm, "model", "") or default)


def _usage_totals(llm: Any) -> tuple[int, int, int]:
    """Prompt tokens, completion tokens and requests this LLM object has used so far."""
    getter = getattr(llm, "get_token_usage_summary", None)
    if not callable(getter):
        return 0, 0, 0
    usage = getter()
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
        int(getattr(usage, "successful_requests", 0) or 0),
    )


class SteerPlaneCrewMonitor:
    """
    CrewAI integration.

    Records model calls with their reported token usage, and tool calls.

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
        agent_name: str = "crewai_crew",
        max_cost_usd: float = 50.0,
        max_steps: int = 200,
        max_runtime_sec: int = 3600,
        model: str = "gpt-4o",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        log_to_console: bool = True,
        allowed_actions: Optional[list[str]] = None,
        denied_actions: Optional[list[str]] = None,
        rate_limits: Optional[list[dict]] = None,
        require_approval: Optional[list[str]] = None,
        approval_callback: Optional[Any] = None,
        enforcement: str = "kill",
        detect_loops: bool = False,
    ):
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
        self._task_count = 0
        self._crew: Any = None
        self._hooks_on = False
        self._usage_seen: dict[int, tuple[int, int, int]] = {}
        self._pending_llm: Optional[tuple[Any]] = None
        self._lock = threading.RLock()
        self.stop_error: Optional[SteerPlaneError] = None

    @property
    def run_manager(self) -> RunManager:
        """Access the underlying RunManager."""
        return self._run_manager

    def start(self):
        """Start the SteerPlane run and turn on the hooks. Call before crew.kickoff()."""
        self._register_hooks()
        self._run_manager.start()
        self._started = True
        self._task_count = 0

    def finish(self):
        """End the SteerPlane run and turn off the hooks. Call after crew.kickoff()."""
        self._unregister_hooks()
        try:
            self._settle_model_call()
        except SteerPlaneError as e:
            self._refuse(e)
        if self._started:
            if not self._run_manager.is_terminated:
                self._run_manager.end(status="completed")
            self._started = False

    # ─── CrewAI hooks ────────────────────────────────────

    def _register_hooks(self) -> None:
        if self._hooks_on:
            return
        try:
            from crewai.hooks import (
                register_after_llm_call_hook,
                register_after_tool_call_hook,
                register_before_llm_call_hook,
                register_before_tool_call_hook,
            )
        except ImportError as e:
            raise ImportError(
                "SteerPlaneCrewMonitor needs CrewAI's call hooks. "
                "Install with: pip install 'crewai>=1.15.35'"
            ) from e

        register_before_llm_call_hook(self._before_llm_call)
        register_after_llm_call_hook(self._after_llm_call)
        register_before_tool_call_hook(self._before_tool_call)
        register_after_tool_call_hook(self._after_tool_call)
        self._hooks_on = True

    def _unregister_hooks(self) -> None:
        if not self._hooks_on:
            return
        from crewai.hooks import (
            unregister_after_llm_call_hook,
            unregister_after_tool_call_hook,
            unregister_before_llm_call_hook,
            unregister_before_tool_call_hook,
        )

        unregister_before_llm_call_hook(self._before_llm_call)
        unregister_after_llm_call_hook(self._after_llm_call)
        unregister_before_tool_call_hook(self._before_tool_call)
        unregister_after_tool_call_hook(self._after_tool_call)
        self._hooks_on = False

    def _is_other_crew(self, context: Any) -> bool:
        crew = getattr(context, "crew", None)
        return self._crew is not None and crew is not None and crew is not self._crew

    def _refuse(self, error: SteerPlaneError) -> bool:
        """Remember why the run stopped, and tell CrewAI not to make the call."""
        if self.stop_error is None:
            self.stop_error = error
        return False

    def _settle_model_call(self) -> None:
        """
        Record the model call that has finished, if there is one.

        CrewAI runs its after-call hook only when a model call returns text, not
        when it asks for tools. So a model call is recorded at whichever comes
        first: that hook, the next call's before hook, or the end of the run.
        """
        with self._lock:
            pending, self._pending_llm = self._pending_llm, None
            if pending is None:
                return
            llm = pending[0]
            before = self._usage_seen.get(id(llm), (0, 0, 0))
            after = _usage_totals(llm)
            self._usage_seen[id(llm)] = after
            model = _model_name(llm, self._model)
            self._run_manager.log_step(
                action=f"llm:{model}",
                input_tokens=max(after[0] - before[0], 0),
                output_tokens=max(after[1] - before[1], 0),
                model=model,
                check_policy=False,
            )
            # CrewAI retries an empty answer once inside the same call, without
            # running the before hook again. Count each extra request as a step.
            for _ in range(after[2] - before[2] - 1):
                self._run_manager.log_step(
                    action=f"llm:{model}",
                    model=model,
                    check_policy=False,
                    metadata={"retry_of_empty_answer": True},
                )

    def _before_llm_call(self, context: Any) -> Optional[bool]:
        if self._is_other_crew(context):
            return None
        if self.stop_error is not None:
            return False
        try:
            self._settle_model_call()
            with self._lock:
                self._run_manager.check_before_step()
                self._pending_llm = (getattr(context, "llm", None),)
        except SteerPlaneError as e:
            return self._refuse(e)
        return None

    def _after_llm_call(self, context: Any) -> None:
        if self._is_other_crew(context):
            return None
        try:
            self._settle_model_call()
        except SteerPlaneError as e:
            self._refuse(e)
        return None

    def _before_tool_call(self, context: Any) -> Optional[bool]:
        if self._is_other_crew(context):
            return None
        if self.stop_error is not None:
            return False
        name = str(getattr(context, "tool_name", "unknown_tool"))
        try:
            self._settle_model_call()
            with self._lock:
                self._run_manager.check_before_step(name, {"input": str(context.tool_input)[:500]})
        except SteerPlaneError as e:
            return self._refuse(e)
        return None

    def _after_tool_call(self, context: Any) -> None:
        if self._is_other_crew(context):
            return None
        name = str(getattr(context, "tool_name", "unknown_tool"))
        try:
            with self._lock:
                self._run_manager.log_step(
                    action=f"tool:{name}",
                    check_policy=False,
                    metadata={"result_preview": str(getattr(context, "tool_result", ""))[:200]},
                )
        except SteerPlaneError as e:
            self._refuse(e)
        return None

    # ─── Callbacks kept for existing Crew(...) setups ────

    def step_callback(self, step_output: Any) -> None:
        """
        Kept so ``Crew(step_callback=monitor.step_callback)`` keeps working.

        The hooks do the counting, so this records nothing. If the run hasn't been
        started it starts it here, which is too late for the crew's first call. Use
        ``monitor.kickoff(crew)``.
        """
        if not self._started:
            self.start()

    def task_callback(self, task_output: Any) -> None:
        """Kept for ``Crew(task_callback=...)``. Counts completed tasks, not steps."""
        self._task_count += 1

    def kickoff(self, crew: Any, **kwargs) -> Any:
        """
        Start the run, run the crew, finish. Raises the SteerPlane error if a limit
        stopped the crew.

        Usage:
            result = monitor.kickoff(crew)
        """
        self._crew = crew
        self.start()
        try:
            result = crew.kickoff(**kwargs)
        except Exception as e:
            self._after_failure(e)
            raise
        return self._after_success(result)

    async def kickoff_async(self, crew: Any, **kwargs) -> Any:
        """
        Async version of ``kickoff``. Raises the SteerPlane error if a limit stopped
        the crew.

        Usage:
            result = await monitor.kickoff_async(crew)
        """
        self._crew = crew
        self.start()
        try:
            result = await crew.kickoff_async(**kwargs)
        except Exception as e:
            self._after_failure(e)
            raise
        return self._after_success(result)

    def _after_success(self, result: Any) -> Any:
        self.finish()
        if self.stop_error is not None:
            raise self.stop_error
        return result

    def _after_failure(self, error: Exception) -> None:
        """End the run after the crew raised. Raises the SteerPlane error behind it, if any."""
        if isinstance(error, SteerPlaneError):
            self.finish()
            return
        self._unregister_hooks()
        if self.stop_error is not None:
            self.finish()
            raise self.stop_error from error
        if self._started:
            self._run_manager.end(status="failed", error=str(error))
            self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finish()
        else:
            self._unregister_hooks()
            if self._started:
                self._run_manager.end(status="failed", error=str(exc_val))
                self._started = False
        return False
