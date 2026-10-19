"""Tests for the detect_loops switch.

detect_loops=False stops loop detection from ending a run. Every other limit
(cost, steps, runtime, policy) must keep working exactly as before.
"""

import pytest

from steerplane import SteerPlane, guard
from steerplane.exceptions import (
    CostLimitExceeded,
    LoopDetectedError,
    PolicyViolationError,
    StepLimitExceeded,
)
from steerplane.run_manager import RunManager
from steerplane.runtime_context import get_active_run


def _repeat(run, times: int, action: str = "search_web") -> None:
    for _ in range(times):
        run.log_step(action, tokens=10, cost=0.0001)


class TestRunManagerSwitch:
    def test_default_is_on(self):
        run = RunManager(agent_name="t", log_to_console=False)
        assert run.detect_loops is True

    def test_default_still_terminates_on_repeats(self):
        sp = SteerPlane(agent_id="t")
        with pytest.raises(LoopDetectedError):
            with sp.run(loop_window_size=6, log_to_console=False) as run:
                _repeat(run, 20)

    def test_off_lets_repeated_actions_finish(self):
        sp = SteerPlane(agent_id="t")
        with sp.run(loop_window_size=6, detect_loops=False, log_to_console=False) as run:
            _repeat(run, 20)
        assert run.status == "completed"
        assert run.telemetry.step_count == 20

    def test_off_still_enforces_step_limit(self):
        sp = SteerPlane(agent_id="t")
        with pytest.raises(StepLimitExceeded):
            with sp.run(max_steps=5, detect_loops=False, log_to_console=False) as run:
                _repeat(run, 20)

    def test_off_still_enforces_cost_limit(self):
        sp = SteerPlane(agent_id="t")
        with pytest.raises(CostLimitExceeded):
            with sp.run(max_cost_usd=0.01, detect_loops=False, log_to_console=False) as run:
                for _ in range(20):
                    run.log_step("search_web", tokens=1000, cost=0.005)

    def test_off_still_enforces_policy(self):
        sp = SteerPlane(agent_id="t")
        with pytest.raises(PolicyViolationError):
            with sp.run(
                denied_actions=["delete_*"], detect_loops=False, log_to_console=False
            ) as run:
                run.log_step("delete_table", tokens=10, cost=0.0001)


class TestGuardSwitch:
    def test_guard_off(self):
        @guard(loop_window_size=6, detect_loops=False, log_to_console=False)
        def agent():
            _repeat(get_active_run(), 20)
            return "done"

        assert agent() == "done"

    def test_guard_default_on(self):
        @guard(loop_window_size=6, log_to_console=False)
        def agent():
            _repeat(get_active_run(), 20)

        with pytest.raises(LoopDetectedError):
            agent()

    def test_config_file_value_is_used(self, monkeypatch):
        monkeypatch.setattr("steerplane.config_file._cached_config", {"detect_loops": False})

        @guard(loop_window_size=6, log_to_console=False)
        def agent():
            _repeat(get_active_run(), 20)
            return "done"

        assert agent() == "done"

    def test_explicit_value_beats_config_file(self, monkeypatch):
        monkeypatch.setattr("steerplane.config_file._cached_config", {"detect_loops": False})

        @guard(loop_window_size=6, detect_loops=True, log_to_console=False)
        def agent():
            _repeat(get_active_run(), 20)

        with pytest.raises(LoopDetectedError):
            agent()


class TestConfigFileParsing:
    @pytest.mark.parametrize(
        "yaml_text",
        ["defaults:\n  detect_loops: false\n", "detect_loops: false\n"],
        ids=["under-defaults", "top-level"],
    )
    def test_both_positions_are_read(self, tmp_path, monkeypatch, yaml_text):
        pytest.importorskip("yaml")
        from steerplane.config_file import load_config_file

        path = tmp_path / ".steerplane.yml"
        path.write_text(yaml_text, encoding="utf-8")
        monkeypatch.setenv("STEERPLANE_CONFIG", str(path))
        monkeypatch.setattr("steerplane.config_file._cached_config", None)

        assert load_config_file(force_reload=True)["detect_loops"] is False


class TestIntegrationsPassSwitch:
    def test_crewai_monitor(self):
        from steerplane.integrations.crewai import SteerPlaneCrewMonitor

        assert SteerPlaneCrewMonitor(log_to_console=False).run_manager.detect_loops is True
        monitor = SteerPlaneCrewMonitor(detect_loops=False, log_to_console=False)
        assert monitor.run_manager.detect_loops is False

    def test_autogen_monitor(self):
        from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

        monitor = SteerPlaneAutoGenMonitor(detect_loops=False, log_to_console=False)
        assert monitor.run_manager.detect_loops is False

    def test_openai_agents_hooks(self):
        from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

        hooks = SteerPlaneAgentHooks(detect_loops=False, log_to_console=False)
        assert hooks.run_manager.detect_loops is False

    def test_langchain_handler(self):
        pytest.importorskip("langchain_core")
        from steerplane.integrations.langchain import SteerPlaneCallbackHandler

        handler = SteerPlaneCallbackHandler(detect_loops=False, log_to_console=False)
        assert handler.run_manager.detect_loops is False
