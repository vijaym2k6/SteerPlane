"""A small cost limit must be readable in error messages.

Before, every limit was printed with two decimals, so a $0.001 ceiling read
"Current: $0.0011, Limit: $0.00". Limits of $1 or more must print as before.
"""

import pytest

from steerplane import RunManager
from steerplane.exceptions import CostLimitExceeded
from steerplane.utils import format_limit


@pytest.mark.parametrize(
    "limit, expected",
    [
        (100.0, "$100.00"),
        (5.0, "$5.00"),
        (1.0, "$1.00"),
        (0.5, "$0.5000"),
        (0.01, "$0.0100"),
        (0.001, "$0.0010"),
        (0.0001, "$0.0001"),
        (0.00005, "$0.000050"),
        (0.000001, "$0.000001"),
        (1e-9, "$1.0e-09"),
        (0.0, "$0.00"),
    ],
)
def test_format_limit(limit, expected):
    assert format_limit(limit) == expected


def test_large_limit_message_is_unchanged():
    assert str(CostLimitExceeded(5.2, 5.0)) == (
        "[COST] Cost limit exceeded! Current: $5.2000, Limit: $5.00. Run terminated."
    )


def test_small_limit_message_shows_the_limit():
    msg = str(CostLimitExceeded(0.0011, 0.001))
    assert "Limit: $0.0010." in msg
    assert "$0.00." not in msg


def test_run_stopped_by_a_small_limit_reports_it():
    run = RunManager(agent_name="bot", max_cost_usd=0.001, log_to_console=False)
    run.start()
    run.log_step("a", cost=0.0006)
    with pytest.raises(CostLimitExceeded) as exc:
        run.log_step("b", cost=0.0006)
    assert "Limit: $0.0010." in str(exc.value)
    assert "> $0.0010." in run._termination_details["message"]


def test_check_before_step_reports_a_small_limit():
    run = RunManager(agent_name="bot", max_cost_usd=0.001, log_to_console=False)
    run.start()
    run.cost_tracker.total_cost = 0.001  # budget already used up
    with pytest.raises(CostLimitExceeded):
        run.check_before_step("next_tool")
    assert "of $0.0010." in run._termination_details["message"]
