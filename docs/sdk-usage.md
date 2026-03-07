# SDK Usage Guide

## Overview

The SteerPlane SDK provides two APIs for monitoring AI agents:

1. **Decorator API** — Simplest way to add guardrails (one line)
2. **Context Manager API** — Full control over step logging

## Decorator API

### Basic Usage

```python
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50)
def run_agent():
    # Your agent code runs normally
    # SteerPlane monitors every step
    agent.run()
```

### Full Options

```python
@guard(
    agent_name="support_bot",      # Name shown in dashboard
    max_cost_usd=10.00,            # Hard cost ceiling (USD)
    max_steps=50,                  # Maximum execution steps
    detect_loops=True,             # Enable loop detection
    loop_window_size=6,            # Sliding window size for patterns
    api_url="http://localhost:8000" # SteerPlane API URL
)
def run_agent():
    agent.run()
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_name` | str | `"default"` | Agent identifier in the dashboard |
| `max_cost_usd` | float | `None` | Maximum cost per run in USD |
| `max_steps` | int | `None` | Maximum number of steps per run |
| `detect_loops` | bool | `True` | Enable infinite loop detection |
| `loop_window_size` | int | `6` | Number of actions in the pattern window |
| `api_url` | str | `http://localhost:8000` | SteerPlane API server URL |

## Context Manager API

For more control, use the context manager directly:

```python
from steerplane import SteerPlane

sp = SteerPlane(agent_id="my_bot")

with sp.run(max_cost_usd=10.0, max_steps=50) as run:
    # Log individual steps
    run.log_step(
        action="query_database",
        tokens=380,
        cost=0.002,
        latency_ms=45
    )

    run.log_step(
        action="generate_response",
        tokens=1240,
        cost=0.008,
        latency_ms=320
    )

# After the context manager exits, the run is automatically
# marked as completed (or failed if an exception occurred)
```

### Step Logging Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | str | ✅ | Name of the action being performed |
| `tokens` | int | ❌ | Number of tokens used |
| `cost` | float | ❌ | Cost of this step in USD |
| `latency_ms` | int | ❌ | Execution time in milliseconds |

## Exception Handling

SteerPlane raises specific exceptions when limits are hit:

```python
from steerplane import guard
from steerplane.exceptions import (
    CostLimitExceeded,
    StepLimitExceeded,
    LoopDetected
)

@guard(max_cost_usd=5, max_steps=20, detect_loops=True)
def run_agent():
    try:
        agent.run()
    except CostLimitExceeded as e:
        print(f"Agent exceeded cost limit: {e}")
        # Handle gracefully — save state, notify user
    except LoopDetected as e:
        print(f"Agent stuck in loop: {e}")
        # Log the loop pattern for debugging
    except StepLimitExceeded as e:
        print(f"Agent exceeded step limit: {e}")
```

## Graceful Degradation

If the SteerPlane API server is unreachable, the SDK continues to enforce **local** guardrails:

- ✅ Loop detection works locally
- ✅ Cost tracking works locally
- ✅ Step limits work locally
- ⚠️ Dashboard won't show data until API is back

This ensures your agents are **never left unprotected**.

## Configuration

### Environment Variables

```bash
export STEERPLANE_API_URL=http://localhost:8000
```

### Programmatic Configuration

```python
from steerplane import SteerPlane

sp = SteerPlane(
    agent_id="my_bot",
    api_url="http://my-server:8000",
)
```

## Best Practices

1. **Always set cost limits** — even generous ones prevent catastrophic spending
2. **Use meaningful action names** — `"query_customer_db"` is better than `"step_1"`
3. **Track token counts** — this enables accurate cost analytics
4. **Set reasonable step limits** — most agents should complete in under 100 steps
5. **Enable loop detection** — it has near-zero overhead and catches real bugs
