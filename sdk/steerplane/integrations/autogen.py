"""
SteerPlane SDK — AutoGen Integration

Hooks into Microsoft AutoGen's conversation flow to automatically monitor
all LLM calls and agent messages with SteerPlane guardrails.

Usage:
    from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

    monitor = SteerPlaneAutoGenMonitor(
        agent_name="my_autogen_group",
        max_cost_usd=15.0,
        max_steps=150,
    )

    # Use as a reply function filter
    user_proxy = UserProxyAgent(
        "user",
        human_input_mode="NEVER",
    )
    assistant = AssistantAgent("assistant", llm_config=llm_config)

    # Wrap the chat
    result = monitor.initiate_chat(user_proxy, assistant, message="Hello!")
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

logger = logging.getLogger("steerplane.autogen")

_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def _estimate_cost(model: str, tokens: int) -> float:
    """Rough cost estimate from total tokens."""
    normalized = model.lower().strip()
    for prefix in sorted(_PRICING, key=len, reverse=True):
        if normalized.startswith(prefix):
            pricing = _PRICING[prefix]
            avg = (pricing["input"] + pricing["output"]) / 2 / 1_000_000
            return round(tokens * avg, 8)
    return round(tokens * 2.0 / 1_000_000, 8)


class SteerPlaneAutoGenMonitor:
    """
    AutoGen integration that auto-instruments multi-agent conversations
    with SteerPlane guardrails.

    Automatically captures:
    - Agent messages and replies
    - LLM call token usage
    - Tool/function executions
    - Conversation flow and costs

    Automatically enforces:
    - Cost limits (hard ceiling)
    - Step limits
    - Loop detection (repeated message patterns)
    - Policy engine rules
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
        self._message_count = 0

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

    def log_message(
        self,
        sender: str,
        content: str,
        role: str = "assistant",
        model: str | None = None,
        tokens: int | None = None,
    ):
        """
        Log an agent message through SteerPlane.

        Can be called from a reply function registered on AutoGen agents.
        """
        if not self._started:
            self.start()

        self._message_count += 1
        used_model = model or self._model

        # Estimate tokens from content length if not provided
        estimated_tokens = tokens or max(1, len(content) // 4)
        cost = _estimate_cost(used_model, estimated_tokens)

        try:
            self._run_manager.log_step(
                action=f"message:{sender}",
                tokens=estimated_tokens,
                cost=cost,
                model=used_model,
                metadata={
                    "sender": sender,
                    "role": role,
                    "content_preview": content[:200],
                    "message_number": self._message_count,
                },
            )
        except (CostLimitExceeded, StepLimitExceeded, LoopDetectedError, PolicyViolationError):
            raise
        except Exception as e:
            logger.warning(f"SteerPlane: Error logging AutoGen message: {e}")

    def log_function_call(
        self,
        agent_name: str,
        function_name: str,
        arguments: dict | None = None,
        result: str = "",
    ):
        """Log a function/tool execution."""
        try:
            self._run_manager.log_step(
                action=f"function:{function_name}",
                metadata={
                    "agent": agent_name,
                    "arguments": str(arguments)[:500] if arguments else "",
                    "result_preview": result[:200],
                },
            )
        except (CostLimitExceeded, StepLimitExceeded, LoopDetectedError, PolicyViolationError):
            raise
        except Exception as e:
            logger.warning(f"SteerPlane: Error logging AutoGen function call: {e}")

    def create_reply_hook(self):
        """
        Create a reply function that can be registered with AutoGen agents.

        Usage:
            assistant.register_reply([Agent], monitor.create_reply_hook())
        """
        monitor = self

        def _hook(
            recipient: Any,
            messages: list | None = None,
            sender: Any = None,
            config: Any = None,
        ) -> tuple[bool, Any]:
            """AutoGen reply hook — logs each message, returns False to continue."""
            if messages:
                last = messages[-1]
                content = ""
                sender_name = "unknown"

                if isinstance(last, dict):
                    content = last.get("content", "")
                    sender_name = last.get("name", str(sender))
                elif isinstance(last, str):
                    content = last
                    sender_name = str(sender)

                if content:
                    monitor.log_message(
                        sender=sender_name,
                        content=str(content),
                    )

            # Return False to let AutoGen continue its normal flow
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
        Convenience wrapper: start monitoring, run chat, finish.

        Usage:
            result = monitor.initiate_chat(user_proxy, assistant, message="Hello!")
        """
        self.start()
        try:
            result = initiator.initiate_chat(recipient, message=message, **kwargs)
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
