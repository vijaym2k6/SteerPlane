"""
SteerPlane quickstart: watch SteerPlane stop a runaway agent.

No API key and no LLM needed. The "agent" below is simulated so you can see
the three stops in a few seconds:

    1. Cost limit   - the run keeps spending until it hits max_cost_usd
    2. Loop         - the agent calls the same tool over and over
    3. Denied action - the agent tries to call a tool you blocked

Usage:
    pip install steerplane
    python runaway_agent.py

Optional: start the API and dashboard first (docker compose up from the repo
root) and every run below also shows up at http://localhost:3000.
"""

from steerplane import SteerPlane
from steerplane.exceptions import (
    CostLimitExceeded,
    LoopDetectedError,
    PolicyViolationError,
)

sp = SteerPlane(agent_id="quickstart_agent")


def runaway_cost():
    """An agent that keeps researching and never decides it is done."""
    print("\n=== 1. Cost limit: the agent keeps spending ===")
    try:
        with sp.run(max_cost_usd=0.05, max_steps=100) as run:
            for i in range(1, 101):
                # Each step is a different page, so this is not a loop.
                # It just costs about $0.008 a call and never ends.
                run.log_step(f"read_page_{i}", tokens=1200, cost=0.008)
    except CostLimitExceeded as e:
        print(f"\nStopped by SteerPlane: {e}")


def stuck_in_a_loop():
    """An agent that retries the same empty search forever."""
    print("\n=== 2. Loop: the agent repeats the same call ===")
    try:
        with sp.run(max_cost_usd=5.0, max_steps=100) as run:
            for _ in range(100):
                run.log_step("search_orders", tokens=300, cost=0.001)
    except LoopDetectedError as e:
        print(f"\nStopped by SteerPlane: {e}")


def blocked_action():
    """An agent that tries to drop a table it should never touch."""
    print("\n=== 3. Denied action: the agent calls a blocked tool ===")
    try:
        with sp.run(max_cost_usd=5.0, denied_actions=["drop_*", "delete_*"]) as run:
            run.log_step("read_policy", tokens=400, cost=0.002)
            run.log_step("drop_table_orders", tokens=50, cost=0.0005)
    except PolicyViolationError as e:
        print(f"\nBlocked by SteerPlane: {e}")


if __name__ == "__main__":
    runaway_cost()
    stuck_in_a_loop()
    blocked_action()
