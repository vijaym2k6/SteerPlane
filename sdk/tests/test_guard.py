"""Tests for the guard decorator."""

import pytest
from steerplane import guard, SteerPlane
from steerplane.exceptions import (
    LoopDetectedError,
    CostLimitExceeded,
    StepLimitExceeded,
    RunTerminatedError,
)


class TestGuardDecorator:
    def test_basic_guarded_function(self):
        """A guarded function should execute normally."""

        @guard(max_cost_usd=10, max_steps=50, log_to_console=False)
        def my_agent():
            return "done"

        result = my_agent()
        assert result == "done"

    def test_guard_marks_function(self):
        """Guarded functions should have the _steerplane_guarded attribute."""

        @guard(max_cost_usd=10, max_steps=50, log_to_console=False)
        def my_agent():
            pass

        assert hasattr(my_agent, "_steerplane_guarded")
        assert my_agent._steerplane_guarded is True


class TestSteerPlaneClient:
    def test_context_manager_run(self):
        """Context manager should start and end a run."""
        sp = SteerPlane(agent_id="test_bot")
        with sp.run(max_cost_usd=10, log_to_console=False) as run:
            run.log_step("test_action", tokens=100, cost=0.001)
        assert run.status == "completed"

    def test_step_limit_exceeded(self):
        """Should raise StepLimitExceeded when limit is hit."""
        sp = SteerPlane(agent_id="test_bot")
        with pytest.raises(StepLimitExceeded):
            with sp.run(max_steps=3, log_to_console=False) as run:
                for i in range(5):
                    run.log_step(f"action_{i}", tokens=10, cost=0.001)

    def test_cost_limit_exceeded(self):
        """Should raise CostLimitExceeded when cost limit is hit."""
        sp = SteerPlane(agent_id="test_bot")
        with pytest.raises(CostLimitExceeded):
            with sp.run(max_cost_usd=0.01, log_to_console=False) as run:
                for i in range(10):
                    run.log_step(f"action_{i}", tokens=1000, cost=0.005)

    def test_loop_detection_triggers(self):
        """Should raise LoopDetectedError on repeating actions."""
        sp = SteerPlane(agent_id="test_bot")
        with pytest.raises(LoopDetectedError):
            with sp.run(max_cost_usd=100, loop_window_size=6, log_to_console=False) as run:
                for _ in range(20):
                    run.log_step("search_web", tokens=10, cost=0.0001)

    def test_alert_mode_can_pause_and_resume_with_higher_limit(self, monkeypatch):
        approvals = {"polls": 0}

        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient._request",
            lambda self, method, path, **kwargs: {},
        )

        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient.request_approval",
            lambda self, **kwargs: {"id": "apr_test"},
        )

        def fake_get_approval(self, approval_id):
            approvals["polls"] += 1
            return {
                "id": approval_id,
                "status": "approved",
                "resolution_json": {"new_limit": 20.0, "extension_value": 10.0},
            }

        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient.get_approval",
            fake_get_approval,
        )
        monkeypatch.setattr("steerplane.run_manager.time.sleep", lambda _: None)

        sp = SteerPlane(agent_id="test_bot")
        with sp.run(
            max_cost_usd=10,
            enforcement="alert",
            alert_threshold=0.5,
            alert_timeout_sec=2,
            log_to_console=False,
        ) as run:
            run.log_step("expensive_step", tokens=100, cost=6.0)
            run.log_step("follow_up", tokens=100, cost=5.0)

        assert approvals["polls"] >= 1
        assert run.status == "completed"
        assert run.cost_tracker.max_cost_usd == 20.0

    def test_alert_mode_denial_terminates_run(self, monkeypatch):
        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient._request",
            lambda self, method, path, **kwargs: {},
        )
        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient.request_approval",
            lambda self, **kwargs: {"id": "apr_test"},
        )
        monkeypatch.setattr(
            "steerplane.client.SteerPlaneClient.get_approval",
            lambda self, approval_id: {
                "id": approval_id,
                "status": "denied",
                "message": "Manual denial",
                "resolution_note": "Manual denial",
            },
        )
        monkeypatch.setattr("steerplane.run_manager.time.sleep", lambda _: None)

        sp = SteerPlane(agent_id="test_bot")
        with pytest.raises(RunTerminatedError):
            with sp.run(
                max_cost_usd=10,
                enforcement="alert",
                alert_threshold=0.5,
                alert_timeout_sec=2,
                log_to_console=False,
            ) as run:
                run.log_step("expensive_step", tokens=100, cost=6.0)
