"""Tests for the cost tracker."""

import pytest
from steerplane.cost_tracker import CostTracker
from steerplane.exceptions import CostLimitExceeded


class TestCostTracker:

    def test_basic_cost_tracking(self):
        tracker = CostTracker(max_cost_usd=10.0)
        step = tracker.calculate_step_cost(total_tokens=1000)
        tracker.add_step(step)
        assert tracker.total_cost > 0
        assert tracker.total_tokens == 1000

    def test_cost_override(self):
        tracker = CostTracker(max_cost_usd=10.0)
        step = tracker.calculate_step_cost(cost_override=0.50)
        tracker.add_step(step)
        assert tracker.total_cost == 0.50

    def test_cost_limit_exceeded(self):
        tracker = CostTracker(max_cost_usd=1.0)
        step = tracker.calculate_step_cost(cost_override=1.50)
        with pytest.raises(CostLimitExceeded):
            tracker.add_step(step)

    def test_cumulative_cost(self):
        tracker = CostTracker(max_cost_usd=10.0)
        for _ in range(5):
            step = tracker.calculate_step_cost(cost_override=0.10)
            tracker.add_step(step)
        assert abs(tracker.total_cost - 0.50) < 0.001

    def test_cost_projection(self):
        tracker = CostTracker(max_cost_usd=100.0)
        for _ in range(4):
            step = tracker.calculate_step_cost(cost_override=0.20)
            tracker.add_step(step)
        projected = tracker.project_final_cost(steps_completed=4, expected_total_steps=20)
        assert abs(projected - 4.0) < 0.01  # $0.80 * (20/4) = $4.00

    def test_input_output_token_split(self):
        tracker = CostTracker(max_cost_usd=10.0, model="default")
        step = tracker.calculate_step_cost(input_tokens=500, output_tokens=500)
        assert step.cost_usd > 0
        assert step.input_tokens == 500
        assert step.output_tokens == 500

    def test_reset(self):
        tracker = CostTracker(max_cost_usd=10.0)
        step = tracker.calculate_step_cost(cost_override=1.0)
        tracker.add_step(step)
        tracker.reset()
        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 0

    def test_summary(self):
        tracker = CostTracker(max_cost_usd=10.0)
        step = tracker.calculate_step_cost(cost_override=0.50, total_tokens=100)
        tracker.add_step(step)
        summary = tracker.get_summary()
        assert summary.total_cost_usd == 0.50
        assert len(summary.step_costs) == 1
