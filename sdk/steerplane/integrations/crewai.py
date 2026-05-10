"""
SteerPlane SDK — CrewAI Integration

Step callback that automatically monitors all CrewAI task executions,
tool calls, and LLM interactions with SteerPlane guardrails.

Usage:
    from steerplane.integrations.crewai import SteerPlaneCrewMonitor

    monitor = SteerPlaneCrewMonitor(
        agent_name="my_crew",
        max_cost_usd=25.0,
        max_steps=200,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        step_callback=monitor.step_callback,
    )

    monitor.start()
    result = crew.kickoff()
    monitor.finish()
"""

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

logger = logging.getLogger("steerplane.crewai")

# Default pricing for CrewAI (typically uses OpenAI models)
_DEFAULT_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


def _estimate_cost(model: str, tokens: int) -> float:
    """Rough cost estimate from total tokens and model."""
    normalized = model.lower().strip()
    for prefix in sorted(_DEFAULT_PRICING, key=len, reverse=True):
        if normalized.startswith(prefix):
            pricing = _DEFAULT_PRICING[prefix]
            avg_per_token = (pricing["input"] + pricing["output"]) / 2 / 1_000_000
            return round(tokens * avg_per_token, 8)
    return round(tokens * 2.0 / 1_000_000, 8)


class SteerPlaneCrewMonitor:
    """
    CrewAI integration that auto-instruments Crew executions
    with SteerPlane guardrails.

    Automatically captures:
    - Task starts and completions
    - Tool usage within tasks
    - Token usage estimates
    - Total crew cost

    Automatically enforces:
    - Cost limits (hard ceiling)
    - Step limits
    - Loop detection
    - Policy engine rules
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
        )
        self._model = model
        self._started = False
        self._task_count = 0

    @property
    def run_manager(self) -> RunManager:
        """Access the underlying RunManager."""
        return self._run_manager

    def start(self):
        """Start the SteerPlane run. Call before crew.kickoff()."""
        self._run_manager.start()
        self._started = True
        self._task_count = 0

    def finish(self):
        """End the SteerPlane run. Call after crew.kickoff() completes."""
        if self._started:
            self._run_manager.end(status="completed")
            self._started = False

    def step_callback(self, step_output: Any) -> None:
        """
        CrewAI step callback — pass this to Crew(step_callback=...).

        Captures each agent step (thought, action, observation) and logs it
        through SteerPlane.
        """
        if not self._started:
            self.start()

        # Extract info from CrewAI step output
        try:
            # CrewAI's TaskOutput or AgentAction
            if hasattr(step_output, "raw"):
                raw = str(step_output.raw)[:500]
                action_name = "crew_task_output"
            elif hasattr(step_output, "tool"):
                action_name = f"tool:{step_output.tool}"
                raw = str(getattr(step_output, "tool_input", ""))[:500]
            elif hasattr(step_output, "text"):
                action_name = "crew_thought"
                raw = str(step_output.text)[:500]
            else:
                action_name = "crew_step"
                raw = str(step_output)[:500]

            # Estimate tokens from output length
            estimated_tokens = max(1, len(raw) // 4)
            cost = _estimate_cost(self._model, estimated_tokens)

            self._run_manager.log_step(
                action=action_name,
                tokens=estimated_tokens,
                cost=cost,
                metadata={"output_preview": raw[:200]},
            )
        except (CostLimitExceeded, StepLimitExceeded, LoopDetectedError, PolicyViolationError):
            raise
        except Exception as e:
            logger.warning(f"SteerPlane: Error logging CrewAI step: {e}")

    def task_callback(self, task_output: Any) -> None:
        """
        CrewAI task completion callback — pass to Crew(task_callback=...).

        Logs each completed task.
        """
        self._task_count += 1
        try:
            description = ""
            if hasattr(task_output, "description"):
                description = str(task_output.description)[:200]
            elif hasattr(task_output, "raw"):
                description = str(task_output.raw)[:200]

            self._run_manager.log_step(
                action=f"task_complete:{self._task_count}",
                metadata={
                    "task_number": self._task_count,
                    "description": description,
                },
            )
        except Exception as e:
            logger.warning(f"SteerPlane: Error logging CrewAI task: {e}")

    def kickoff(self, crew: Any, **kwargs) -> Any:
        """
        Convenience wrapper: start monitoring, run crew, finish.

        Usage:
            result = monitor.kickoff(crew)
        """
        self.start()
        try:
            result = crew.kickoff(**kwargs)
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
