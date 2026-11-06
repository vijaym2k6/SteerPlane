"""
Runs each framework for real against a local OpenAI-compatible server and counts
the requests that arrive. A limit that only records, and doesn't stop the run,
fails these tests.

A framework that isn't installed is skipped. CI installs them in its own job.
"""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from steerplane.exceptions import (
    CostLimitExceeded,
    PolicyViolationError,
    RunTerminatedError,
    SteerPlaneError,
    StepLimitExceeded,
)

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("AUTOGEN_USE_DOCKER", "False")

MODEL = "gpt-4o-mini"
PROMPT_TOKENS = 1000
COMPLETION_TOKENS = 500
# gpt-4o-mini at $0.15 and $0.60 per million tokens
COST_PER_CALL = 0.00045
FOREVER = 10_000


class CountingServer:
    """Asks for a tool `tool_turns` times, then answers. Counts every request."""

    def __init__(self):
        self.requests = 0
        self.tool_turns = FOREVER
        self.tool_name = None
        self.tool_calls_per_turn = 1
        self.text_mode = False
        self.empty_turns = set()
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                with owner._lock:
                    owner.requests += 1
                    turn = owner.requests
                message, finish = owner.reply(turn, body)
                if body.get("stream"):
                    self._send_stream(body, turn, message, finish)
                else:
                    self._send_json(
                        {
                            "id": f"chatcmpl-{turn}",
                            "object": "chat.completion",
                            "created": 1,
                            "model": body.get("model", MODEL),
                            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                            "usage": owner.usage(),
                        }
                    )

            def _send_json(self, payload):
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_stream(self, body, turn, message, finish):
                base = {
                    "id": f"chatcmpl-{turn}",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": body.get("model", MODEL),
                }
                delta = {"role": "assistant", "content": message.get("content")}
                if message.get("tool_calls"):
                    delta["tool_calls"] = [
                        {**call, "index": i} for i, call in enumerate(message["tool_calls"])
                    ]
                chunks = [
                    {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                    {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
                    {**base, "choices": [], "usage": owner.usage()},
                ]
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                for chunk in chunks:
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")

            def log_message(self, *args):
                pass

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._httpd.server_port}/v1"
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    @staticmethod
    def usage():
        return {
            "prompt_tokens": PROMPT_TOKENS,
            "completion_tokens": COMPLETION_TOKENS,
            "total_tokens": PROMPT_TOKENS + COMPLETION_TOKENS,
        }

    def reply(self, turn, body):
        if turn in self.empty_turns:
            return {"role": "assistant", "content": ""}, "stop"
        if self.text_mode:
            if turn > self.tool_turns:
                return {"role": "assistant", "content": "Final Answer: done"}, "stop"
            text = (
                f"Thought: use the tool\nAction: {self.tool_name or 'lookup'}\n"
                f'Action Input: {{"item": "i{turn}"}}'
            )
            return {"role": "assistant", "content": text}, "stop"
        tools = body.get("tools") or []
        if not tools or turn > self.tool_turns:
            return {"role": "assistant", "content": "All done. TERMINATE"}, "stop"
        name = self.tool_name or tools[0]["function"]["name"]
        calls = [
            {
                "id": f"call_{turn}_{i}",
                "type": "function",
                # A new argument each time, so no framework serves it from a cache.
                "function": {"name": name, "arguments": json.dumps({"item": f"i{turn}_{i}"})},
            }
            for i in range(self.tool_calls_per_turn)
        ]
        return {"role": "assistant", "content": None, "tool_calls": calls}, "tool_calls"

    def stop(self):
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture
def server():
    counting = CountingServer()
    yield counting
    counting.stop()


class Tools:
    """Tool bodies that record every real execution."""

    def __init__(self):
        self.executed = executed = []

        def lookup(item: str) -> str:
            """Look up an item."""
            executed.append(("lookup", item))
            return f"value of {item}"

        def delete_everything(item: str) -> str:
            """Delete an item."""
            executed.append(("delete_everything", item))
            return "deleted"

        self.lookup = lookup
        self.delete_everything = delete_everything

    def all(self):
        return [self.lookup, self.delete_everything]


class LangChainAdapter:
    name = "langchain"

    def __init__(self):
        pytest.importorskip("langchain_openai")
        pytest.importorskip("langchain.agents")

    def _agent(self, server, tools, streaming=False):
        from langchain.agents import create_agent
        from langchain_core.tools import StructuredTool
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=MODEL,
            base_url=server.url,
            api_key="test",
            streaming=streaming,
            stream_usage=True,
        )
        return create_agent(model, [StructuredTool.from_function(t) for t in tools.all()])

    def _handler(self, limits):
        from steerplane.integrations.langchain import SteerPlaneCallbackHandler

        return SteerPlaneCallbackHandler(log_to_console=False, **limits)

    def run(self, server, tools, **limits):
        handler = self._handler(limits)
        agent = self._agent(server, tools)
        config = {"callbacks": [handler], "recursion_limit": 1000}
        try:
            agent.invoke({"messages": [("user", "go")]}, config=config)
        except SteerPlaneError as e:
            return e, handler.run_manager
        handler.finish()
        return None, handler.run_manager


class OpenAIAgentsAdapter:
    name = "openai_agents"

    def __init__(self):
        pytest.importorskip("agents")

    def _agent(self, server, tools):
        from agents import Agent, OpenAIChatCompletionsModel, function_tool, set_tracing_disabled
        from openai import AsyncOpenAI

        set_tracing_disabled(True)
        model = OpenAIChatCompletionsModel(
            model=MODEL, openai_client=AsyncOpenAI(base_url=server.url, api_key="test")
        )
        return Agent(
            name="tester",
            instructions="Use the tools.",
            model=model,
            tools=[function_tool(t) for t in tools.all()],
        )

    def run(self, server, tools, **limits):
        from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

        hooks = SteerPlaneAgentHooks(model=MODEL, log_to_console=False, **limits)
        agent = self._agent(server, tools)
        try:
            asyncio.run(hooks.run(agent, "go", max_turns=1000))
        except SteerPlaneError as e:
            return e, hooks.run_manager
        return None, hooks.run_manager


class CrewAIAdapter:
    name = "crewai"

    def __init__(self):
        pytest.importorskip("crewai")

    def _crew(self, server, tools):
        from crewai import LLM, Agent, Crew, Task
        from crewai.tools import tool

        llm = LLM(model=MODEL, base_url=server.url, api_key="test")
        crew_tools = []
        for fn in tools.all():
            crew_tools.append(tool(fn.__name__)(fn))
        agent = Agent(
            role="tester",
            goal="Use the tools",
            backstory="A tester.",
            llm=llm,
            tools=crew_tools,
            max_iter=1000,
            verbose=False,
        )
        task = Task(description="Use the tools.", expected_output="A result.", agent=agent)
        return Crew(agents=[agent], tasks=[task], verbose=False)

    def run(self, server, tools, **limits):
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        monitor = SteerPlaneCrewMonitor(model=MODEL, log_to_console=False, **limits)
        crew = self._crew(server, tools)
        try:
            monitor.kickoff(crew)
        except SteerPlaneError as e:
            return e, monitor.run_manager
        return None, monitor.run_manager


class AutoGenAdapter:
    name = "autogen"

    def __init__(self):
        pytest.importorskip("autogen")

    def agents(self, server, tools):
        from autogen import AssistantAgent, UserProxyAgent, register_function

        assistant = AssistantAgent(
            "assistant",
            llm_config={
                "config_list": [{"model": MODEL, "api_key": "test", "base_url": server.url}],
                "cache_seed": None,
            },
        )
        user = UserProxyAgent(
            "user",
            human_input_mode="NEVER",
            code_execution_config=False,
            max_consecutive_auto_reply=1000,
            is_termination_msg=lambda m: "TERMINATE" in (m.get("content") or ""),
        )
        for fn in tools.all():
            register_function(
                fn, caller=assistant, executor=user, name=fn.__name__, description=fn.__doc__
            )
        return user, assistant

    def run(self, server, tools, **limits):
        from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

        monitor = SteerPlaneAutoGenMonitor(model=MODEL, log_to_console=False, **limits)
        user, assistant = self.agents(server, tools)
        try:
            monitor.initiate_chat(user, assistant, message="go", silent=True)
        except SteerPlaneError as e:
            return e, monitor.run_manager
        return None, monitor.run_manager


ADAPTERS = [LangChainAdapter, OpenAIAgentsAdapter, CrewAIAdapter, AutoGenAdapter]


@pytest.fixture(params=ADAPTERS, ids=lambda a: a.name)
def framework(request):
    return request.param()


class TestEveryFramework:
    def test_step_limit_stops_the_run(self, framework, server):
        tools = Tools()
        error, _ = framework.run(server, tools, max_steps=5)
        assert isinstance(error, StepLimitExceeded)
        # model, tool, model, tool, model, and the next tool call is refused
        assert server.requests == 3
        assert len(tools.executed) == 2

    def test_step_limit_refuses_the_model_call(self, framework, server):
        tools = Tools()
        error, _ = framework.run(server, tools, max_steps=4)
        assert isinstance(error, StepLimitExceeded)
        # model, tool, model, tool, and the next model call is refused
        assert server.requests == 2
        assert len(tools.executed) == 2

    def test_cost_limit_stops_the_run(self, framework, server):
        tools = Tools()
        limit = COST_PER_CALL * 1.5
        error, run = framework.run(server, tools, max_cost_usd=limit)
        assert isinstance(error, CostLimitExceeded)
        # The call that crosses the limit is the last one.
        assert server.requests == 2
        assert run.cost_tracker.total_cost == pytest.approx(COST_PER_CALL * 2, rel=0.01)

    def test_denied_tool_never_runs(self, framework, server):
        tools = Tools()
        server.tool_name = "delete_everything"
        error, _ = framework.run(server, tools, denied_actions=["delete_everything"])
        assert isinstance(error, PolicyViolationError)
        assert tools.executed == []
        assert server.requests == 1

    def test_allowed_tool_still_runs_beside_a_deny_rule(self, framework, server):
        tools = Tools()
        server.tool_turns = 1
        error, _ = framework.run(server, tools, denied_actions=["delete_everything"])
        assert error is None
        assert [name for name, _ in tools.executed] == ["lookup"]

    def test_run_that_ends_exactly_on_the_limit_finishes(self, framework, server):
        tools = Tools()
        server.tool_turns = 1
        error, _ = framework.run(server, tools, max_steps=3)
        assert error is None
        assert server.requests == 2
        assert len(tools.executed) == 1

    def test_same_tool_over_a_list_is_not_stopped(self, framework, server):
        tools = Tools()
        server.tool_turns = 8
        error, run = framework.run(server, tools, max_steps=100)
        assert error is None
        assert len(tools.executed) == 8
        assert server.requests == 9
        assert run.telemetry.step_count == 17

    def test_real_usage_is_what_gets_charged(self, framework, server):
        tools = Tools()
        server.tool_turns = 2
        error, run = framework.run(server, tools, max_steps=100)
        assert error is None
        assert run.cost_tracker.total_cost == pytest.approx(COST_PER_CALL * 3, rel=0.01)


class TestParallelToolCalls:
    def test_batch_can_pass_the_step_limit_by_its_own_size_only(self, framework, server):
        tools = Tools()
        server.tool_calls_per_turn = 3
        error, _ = framework.run(server, tools, max_steps=2)
        assert isinstance(error, SteerPlaneError)
        assert server.requests == 1
        assert len(tools.executed) <= 3

    def test_denied_tool_in_a_batch_never_runs(self, framework, server):
        tools = Tools()
        server.tool_name = "delete_everything"
        server.tool_calls_per_turn = 3
        error, _ = framework.run(server, tools, denied_actions=["delete_everything"])
        # Calls that start after the first refusal are refused as a stopped run.
        assert isinstance(error, (PolicyViolationError, RunTerminatedError))
        assert tools.executed == []


class TestLangChain:
    def test_async(self, server):
        adapter = LangChainAdapter()
        tools = Tools()
        handler = adapter._handler({"max_steps": 4})
        agent = adapter._agent(server, tools)
        config = {"callbacks": [handler], "recursion_limit": 1000}
        with pytest.raises(StepLimitExceeded):
            asyncio.run(agent.ainvoke({"messages": [("user", "go")]}, config=config))
        assert server.requests == 2
        assert len(tools.executed) == 2

    def test_streaming_reports_usage(self, server):
        adapter = LangChainAdapter()
        tools = Tools()
        handler = adapter._handler({"max_cost_usd": COST_PER_CALL * 1.5})
        agent = adapter._agent(server, tools, streaming=True)
        config = {"callbacks": [handler], "recursion_limit": 1000}
        with pytest.raises(CostLimitExceeded):
            agent.invoke({"messages": [("user", "go")]}, config=config)
        assert server.requests == 2

    def test_handler_on_a_plain_model(self, server):
        pytest.importorskip("langchain_openai")
        from langchain_openai import ChatOpenAI

        adapter = LangChainAdapter()
        handler = adapter._handler({"max_steps": 2})
        model = ChatOpenAI(model=MODEL, base_url=server.url, api_key="test", callbacks=[handler])
        model.invoke("hi")
        model.invoke("hi")
        with pytest.raises(StepLimitExceeded):
            model.invoke("hi")
        assert server.requests == 2

    def test_enforce_false_only_records(self, server):
        adapter = LangChainAdapter()
        tools = Tools()
        server.tool_turns = 3
        handler = adapter._handler({"max_steps": 2, "enforce": False})
        agent = adapter._agent(server, tools)
        agent.invoke(
            {"messages": [("user", "go")]},
            config={"callbacks": [handler], "recursion_limit": 1000},
        )
        assert server.requests == 4


class TestOpenAIAgents:
    def test_runner_with_hooks_passed_by_hand(self, server):
        adapter = OpenAIAgentsAdapter()
        from agents import Runner
        from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

        tools = Tools()
        hooks = SteerPlaneAgentHooks(model=MODEL, max_steps=4, log_to_console=False)
        agent = adapter._agent(server, tools)
        hooks.start()
        with pytest.raises(StepLimitExceeded):
            asyncio.run(Runner.run(agent, "go", hooks=hooks.run_hooks, max_turns=1000))
        assert server.requests == 2

    def test_passing_your_own_hooks_to_run_is_an_error(self, server):
        adapter = OpenAIAgentsAdapter()
        from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

        hooks = SteerPlaneAgentHooks(model=MODEL, log_to_console=False)
        agent = adapter._agent(server, Tools())
        with pytest.raises(ValueError):
            asyncio.run(hooks.run(agent, "go", hooks=object()))


class TestCrewAI:
    def test_kickoff_by_hand_with_a_crew_built_earlier(self, server):
        adapter = CrewAIAdapter()
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        tools = Tools()
        crew = adapter._crew(server, tools)
        monitor = SteerPlaneCrewMonitor(model=MODEL, max_steps=4, log_to_console=False)
        monitor.start()
        try:
            with pytest.raises(Exception):
                crew.kickoff()
        finally:
            monitor.finish()
        assert isinstance(monitor.stop_error, StepLimitExceeded)
        assert server.requests == 2

    def test_crewai_retry_of_an_empty_answer_counts_as_a_step(self, server):
        adapter = CrewAIAdapter()
        tools = Tools()
        # CrewAI retries an empty answer once inside the same model call.
        server.empty_turns = {2}
        error, run = adapter.run(server, tools, max_steps=4)
        assert isinstance(error, StepLimitExceeded)
        assert server.requests == 3
        assert len(tools.executed) == 1
        model_steps = [a for a in run.telemetry.action_history if a.startswith("llm")]
        assert len(model_steps) == server.requests

    def test_kickoff_async_raises_the_steerplane_error(self, server):
        adapter = CrewAIAdapter()
        from crewai.hooks import get_before_llm_call_hooks
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        tools = Tools()
        before = len(get_before_llm_call_hooks())
        monitor = SteerPlaneCrewMonitor(model=MODEL, max_steps=4, log_to_console=False)
        with pytest.raises(StepLimitExceeded):
            asyncio.run(monitor.kickoff_async(adapter._crew(server, tools)))
        assert server.requests == 2
        assert len(tools.executed) == 2
        assert len(get_before_llm_call_hooks()) == before

    def test_kickoff_async_denied_tool_never_runs(self, server):
        adapter = CrewAIAdapter()
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        tools = Tools()
        server.tool_name = "delete_everything"
        monitor = SteerPlaneCrewMonitor(
            model=MODEL, denied_actions=["delete_everything"], log_to_console=False
        )
        with pytest.raises(PolicyViolationError):
            asyncio.run(monitor.kickoff_async(adapter._crew(server, tools)))
        assert tools.executed == []

    def test_kickoff_async_clean_run(self, server):
        adapter = CrewAIAdapter()
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        tools = Tools()
        server.tool_turns = 2
        monitor = SteerPlaneCrewMonitor(model=MODEL, max_steps=100, log_to_console=False)
        asyncio.run(monitor.kickoff_async(adapter._crew(server, tools)))
        assert len(tools.executed) == 2
        assert monitor.run_manager.telemetry.step_count == 5

    def test_hooks_are_removed_after_a_stop(self, server):
        adapter = CrewAIAdapter()
        from crewai.hooks import get_before_llm_call_hooks

        before = len(get_before_llm_call_hooks())
        error, _ = adapter.run(server, Tools(), max_steps=4)
        assert isinstance(error, StepLimitExceeded)
        assert len(get_before_llm_call_hooks()) == before

    def test_hooks_are_removed_after_a_clean_run(self, server):
        adapter = CrewAIAdapter()
        from crewai.hooks import get_before_llm_call_hooks

        server.tool_turns = 1
        before = len(get_before_llm_call_hooks())
        error, _ = adapter.run(server, Tools(), max_steps=100)
        assert error is None
        assert len(get_before_llm_call_hooks()) == before


class TestCrewAIWithoutNativeTools:
    """Models without function calling use CrewAI's text loop, which has other code paths."""

    def _run(self, server, tools, **limits):
        adapter = CrewAIAdapter()
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        crew = adapter._crew(server, tools)
        crew.agents[0].llm.supports_function_calling = lambda: False
        server.text_mode = True
        monitor = SteerPlaneCrewMonitor(model=MODEL, log_to_console=False, **limits)
        try:
            monitor.kickoff(crew)
        except SteerPlaneError as e:
            return e, monitor.run_manager
        return None, monitor.run_manager

    def test_step_limit(self, server):
        tools = Tools()
        error, _ = self._run(server, tools, max_steps=4)
        assert isinstance(error, StepLimitExceeded)
        assert server.requests == 2
        assert len(tools.executed) == 2

    def test_denied_tool(self, server):
        tools = Tools()
        server.tool_name = "delete_everything"
        error, _ = self._run(server, tools, denied_actions=["delete_everything"])
        assert isinstance(error, PolicyViolationError)
        assert tools.executed == []
        assert server.requests == 1

    def test_usage_and_clean_finish(self, server):
        tools = Tools()
        server.tool_turns = 2
        error, run = self._run(server, tools, max_steps=100)
        assert error is None
        assert server.requests == 3
        assert run.telemetry.step_count == 5
        assert run.cost_tracker.total_cost == pytest.approx(COST_PER_CALL * 3, rel=0.01)


class TestAutoGen:
    def test_async_chat(self, server):
        adapter = AutoGenAdapter()
        from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

        tools = Tools()
        monitor = SteerPlaneAutoGenMonitor(model=MODEL, max_steps=4, log_to_console=False)
        user, assistant = adapter.agents(server, tools)
        with pytest.raises(StepLimitExceeded):
            asyncio.run(monitor.a_initiate_chat(user, assistant, message="go", silent=True))
        assert server.requests == 2
        assert len(tools.executed) == 2

    def test_group_chat(self, server):
        adapter = AutoGenAdapter()
        from autogen import GroupChat, GroupChatManager
        from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

        tools = Tools()
        monitor = SteerPlaneAutoGenMonitor(model=MODEL, max_steps=4, log_to_console=False)
        user, assistant = adapter.agents(server, tools)
        group = GroupChat(
            agents=[user, assistant],
            messages=[],
            max_round=1000,
            speaker_selection_method="round_robin",
        )
        manager = GroupChatManager(groupchat=group, llm_config=False)
        with pytest.raises(StepLimitExceeded):
            monitor.initiate_chat(user, manager, message="go", silent=True)
        assert server.requests == 2
        assert len(tools.executed) == 2

    def test_attach_and_run_the_chat_yourself(self, server):
        adapter = AutoGenAdapter()
        from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

        tools = Tools()
        monitor = SteerPlaneAutoGenMonitor(model=MODEL, max_steps=4, log_to_console=False)
        user, assistant = adapter.agents(server, tools)
        monitor.attach(user, assistant)
        monitor.start()
        with pytest.raises(StepLimitExceeded):
            user.initiate_chat(assistant, message="go", silent=True)
        assert server.requests == 2
