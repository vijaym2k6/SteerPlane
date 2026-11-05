"""
SteerPlane SDK — AutoGen (AG2) Integration

Enforces SteerPlane limits in AG2's classic conversation API, using its own reply
functions and message hooks. Each model call and each tool call counts as one
step. A call that would go past a limit is refused before it starts, and the
refusal ends the run.

Usage:
    from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

    monitor = SteerPlaneAutoGenMonitor(
        agent_name="my_autogen_group",
        max_cost_usd=15.0,
        max_steps=150,
    )

    user_proxy = UserProxyAgent("user", human_input_mode="NEVER")
    assistant = AssistantAgent("assistant", llm_config=llm_config)

    result = monitor.initiate_chat(user_proxy, assistant, message="Hello!")

To run the chat yourself, call ``monitor.attach(user_proxy, assistant)``, then
``monitor.start()`` and ``monitor.finish()`` around it.

Needs ``ag2`` before 1.0, which has the classic API (``pip install "ag2[openai]<1"``).
The newer ``autogen-agentchat`` package is a different API and is not supported.
A group chat manager's own speaker selection calls are not counted. To limit every
call whatever the agent structure, use the SteerPlane gateway.

One monitor is one run. Create a new one for each run.
"""

import logging
from typing import Any, Optional

from ..run_manager import RunManager
from ..policy_engine import PolicyEngine
from ..exceptions import SteerPlaneError

logger = logging.getLogger("steerplane.autogen")


def _usage_by_model(agent: Any) -> dict[str, tuple[int, int]]:
    """Prompt and completion tokens per model that this agent's client has used so far."""
    client = getattr(agent, "client", None)
    summary = getattr(client, "actual_usage_summary", None) or {}
    totals = {}
    for model, usage in summary.items():
        if isinstance(usage, dict):
            totals[model] = (
                int(usage.get("prompt_tokens", 0) or 0),
                int(usage.get("completion_tokens", 0) or 0),
            )
    return totals


def _tool_names(message: Any) -> list[str]:
    """Names of the tools a message asks for."""
    if not isinstance(message, dict):
        return []
    names = [
        (call.get("function") or {}).get("name", "")
        for call in message.get("tool_calls") or []
        if isinstance(call, dict)
    ]
    function_call = message.get("function_call")
    if isinstance(function_call, dict):
        names.append(function_call.get("name", ""))
    return [name for name in names if name]


class SteerPlaneAutoGenMonitor:
    """
    AG2 integration.

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
        agent_name: str = "autogen_group",
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
        self._message_count = 0
        self._attached: set[int] = set()
        self._send_hooked: set[int] = set()
        self._pending_model_call: set[int] = set()
        self._usage_seen: dict[int, dict[str, tuple[int, int]]] = {}

    @property
    def run_manager(self) -> RunManager:
        """Access the underlying RunManager."""
        return self._run_manager

    def start(self):
        """Start the SteerPlane run."""
        self._run_manager.start()
        self._started = True
        self._message_count = 0

    def finish(self):
        """End the SteerPlane run."""
        if self._started:
            self._run_manager.end(status="completed")
            self._started = False

    def attach(self, *agents: Any) -> None:
        """
        Put these agents under the monitor. ``initiate_chat`` does this for you.

        A group chat manager brings in the agents of its group chat.
        """
        try:
            from autogen import Agent
        except ImportError as e:
            raise ImportError(
                'AG2 is required for this integration. Install with: pip install "ag2[openai]<1"'
            ) from e

        for agent in agents:
            group = getattr(agent, "groupchat", None)
            if group is not None:
                self.attach(*group.agents)
                continue
            if id(agent) in self._attached:
                continue
            self._attached.add(id(agent))
            agent.register_reply([Agent, None], self.create_reply_hook(), position=0)
            self._hook_send(agent)

    def _hook_send(self, agent: Any) -> None:
        if id(agent) in self._send_hooked:
            return
        self._send_hooked.add(id(agent))

        def _after_reply(sender: Any, message: Any, recipient: Any, silent: bool) -> Any:
            self._record_model_call(agent)
            return message

        agent.register_hook("process_message_before_send", _after_reply)

    def _record_model_call(self, agent: Any) -> None:
        """Count a finished model call, with the tokens its client reports for it."""
        if id(agent) not in self._pending_model_call:
            return
        self._pending_model_call.discard(id(agent))

        before = self._usage_seen.get(id(agent), {})
        after = _usage_by_model(agent)
        self._usage_seen[id(agent)] = after

        used_model, input_tokens, output_tokens = self._model, 0, 0
        for model, (prompt, completion) in after.items():
            seen = before.get(model, (0, 0))
            if prompt > seen[0] or completion > seen[1]:
                used_model = model
                input_tokens = prompt - seen[0]
                output_tokens = completion - seen[1]
                break

        self._run_manager.log_step(
            action=f"llm:{used_model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=used_model,
            check_policy=False,
        )

    def log_message(
        self,
        sender: str,
        content: str,
        role: str = "assistant",
        model: str | None = None,
        tokens: int | None = None,
    ):
        """Log a message as one step yourself. The monitor doesn't need this to enforce."""
        if not self._started:
            self.start()

        self._message_count += 1
        self._run_manager.log_step(
            action=f"message:{sender}",
            tokens=tokens or 0,
            model=model or self._model,
            metadata={
                "sender": sender,
                "role": role,
                "content_preview": content[:200],
                "message_number": self._message_count,
            },
        )

    def log_function_call(
        self,
        agent_name: str,
        function_name: str,
        arguments: dict | None = None,
        result: str = "",
    ):
        """Log a tool call as one step yourself. The monitor doesn't need this to enforce."""
        self._run_manager.log_step(
            action=f"function:{function_name}",
            metadata={
                "agent": agent_name,
                "arguments": str(arguments)[:500] if arguments else "",
                "result_preview": result[:200],
            },
        )

    def create_reply_hook(self):
        """
        Create the reply function that checks limits before an agent replies.

        ``attach`` registers it for you. To register it by hand:
            assistant.register_reply([Agent, None], monitor.create_reply_hook(), position=0)
        """
        monitor = self

        def _hook(
            recipient: Any,
            messages: list | None = None,
            sender: Any = None,
            config: Any = None,
        ) -> tuple[bool, Any]:
            """Runs first in the agent's reply. Returns False so AG2 continues as normal."""
            if not monitor._started:
                monitor.start()
            monitor._hook_send(recipient)
            run = monitor._run_manager

            # A reply that produced nothing to send still used its model call.
            monitor._record_model_call(recipient)

            last = messages[-1] if messages else None
            names = _tool_names(last)
            can_execute = getattr(recipient, "can_execute_function", None)
            if names and callable(can_execute) and can_execute(names):
                for name in names:
                    run.check_before_step(name)
                    run.log_step(action=f"tool:{name}", check_policy=False)
                return False, None

            if getattr(recipient, "client", None) is not None:
                run.check_before_step()
                monitor._pending_model_call.add(id(recipient))
            return False, None

        return _hook

    def initiate_chat(
        self,
        initiator: Any,
        recipient: Any,
        message: str = "",
        **kwargs,
    ) -> Any:
        """
        Attach the agents, start the run, run the chat, finish.

        Usage:
            result = monitor.initiate_chat(user_proxy, assistant, message="Hello!")
        """
        self.attach(initiator, recipient)
        self.start()
        try:
            result = initiator.initiate_chat(recipient, message=message, **kwargs)
        except SteerPlaneError:
            raise
        except Exception as e:
            if self._started:
                self._run_manager.end(status="failed", error=str(e))
                self._started = False
            raise
        self.finish()
        return result

    async def a_initiate_chat(
        self,
        initiator: Any,
        recipient: Any,
        message: str = "",
        **kwargs,
    ) -> Any:
        """Async version of ``initiate_chat``."""
        self.attach(initiator, recipient)
        self.start()
        try:
            result = await initiator.a_initiate_chat(recipient, message=message, **kwargs)
        except SteerPlaneError:
            raise
        except Exception as e:
            if self._started:
                self._run_manager.end(status="failed", error=str(e))
                self._started = False
            raise
        self.finish()
        return result

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
