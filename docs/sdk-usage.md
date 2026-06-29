# SDK Usage Guide

## Overview

The SteerPlane SDK provides multiple APIs for monitoring AI agents:

1. **Decorator API** — Simplest way to add guardrails (one line)
2. **Context Manager API** — Full control over step logging
3. **Config File** — `.steerplane.yml` for project-level defaults (v0.4.0)
4. **Framework Integrations** — Native hooks for LangChain, OpenAI Agents SDK, CrewAI, AutoGen (v0.4.0)

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
    max_cost_usd=10.00,            # Cost ceiling, USD (checked after each step)
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

All parameters can be overridden via `.steerplane.yml` config file. The merge order is:
**Explicit args > Config file > Hardcoded defaults**

## Config File (.steerplane.yml) — New in v0.4.0

Create a `.steerplane.yml` in your project root:

```yaml
api_url: http://localhost:8000
agent_name: my_bot
max_cost_usd: 10.0
max_steps: 100
detect_loops: true
loop_window_size: 8
```

The SDK auto-discovers this file by walking up from `cwd`. Override with:

```bash
export STEERPLANE_CONFIG=/path/to/.steerplane.yml
```

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
| `action` | str | Yes | Name of the action being performed |
| `tokens` | int | No | Number of tokens used |
| `cost` | float | No | Cost of this step in USD |
| `latency_ms` | int | No | Execution time in milliseconds |

## Framework Integrations — New in v0.4.0

### LangChain

```python
from steerplane.integrations import SteerPlaneLangChainHandler

handler = SteerPlaneLangChainHandler(agent_name="langchain_bot", max_cost_usd=5.0)
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])
# All LLM calls are automatically tracked
handler.finish()
```

### OpenAI Agents SDK

```python
from steerplane.integrations import SteerPlaneAgentHooks

hooks = SteerPlaneAgentHooks(agent_name="openai_agent", max_cost_usd=10.0)
async with hooks.run():
    result = await Runner.run(agent, input="Hello")
```

### CrewAI

```python
from steerplane.integrations import SteerPlaneCrewMonitor

monitor = SteerPlaneCrewMonitor(agent_name="crew_bot", max_cost_usd=15.0)
result = monitor.kickoff(crew, inputs={"topic": "AI Safety"})
```

### AutoGen

```python
from steerplane.integrations import SteerPlaneAutoGenMonitor

monitor = SteerPlaneAutoGenMonitor(agent_name="autogen_bot", max_cost_usd=10.0)
result = monitor.initiate_chat(agent, recipient, message="Analyze this data")
```

All integrations use lazy imports — framework dependencies are only required when actually used.

## Exception Handling

SteerPlane raises specific exceptions when limits are hit:

```python
from steerplane import guard
from steerplane.exceptions import (
    CostLimitExceeded,
    StepLimitExceeded,
    LoopDetectedError,
    PolicyViolationError,
)

@guard(max_cost_usd=5, max_steps=20, detect_loops=True)
def run_agent():
    try:
        agent.run()
    except CostLimitExceeded as e:
        print(f"Agent exceeded cost limit: {e}")
    except LoopDetectedError as e:
        print(f"Agent stuck in loop: {e}")
    except StepLimitExceeded as e:
        print(f"Agent exceeded step limit: {e}")
    except PolicyViolationError as e:
        print(f"Policy violation: {e}")
```

## Graceful Degradation

If the SteerPlane API server is unreachable, the SDK continues to enforce **local** guardrails:

- Loop detection works locally
- Cost tracking works locally
- Step limits work locally
- Dashboard won't show data until API is back

This ensures your agents are **never left unprotected**.

## Configuration

### Environment Variables

```bash
export STEERPLANE_API_URL=http://localhost:8000
export STEERPLANE_CONFIG=/path/to/.steerplane.yml
```

### Programmatic Configuration

```python
from steerplane import SteerPlane

sp = SteerPlane(
    agent_id="my_bot",
    api_url="http://my-server:8000",
)
```

## CLI Tool — New in v0.4.0

```bash
# Check API health
steerplane status

# Run management
steerplane runs list
steerplane runs inspect <run_id>
steerplane runs kill <run_id>

# API key management
steerplane keys list
steerplane keys create --name "my-agent"
steerplane keys revoke <key_id>

# Live logs
steerplane logs --tail
```

Set the API URL and admin token:

```bash
export STEERPLANE_API_URL=http://localhost:8000
export STEERPLANE_ADMIN_TOKEN=your-admin-token
```

## Best Practices

1. **Always set cost limits** — even generous ones prevent catastrophic spending
2. **Use meaningful action names** — `"query_customer_db"` is better than `"step_1"`
3. **Track token counts** — this enables accurate cost analytics
4. **Set reasonable step limits** — most agents should complete in under 100 steps
5. **Enable loop detection** — it has near-zero overhead and catches real bugs
6. **Use `.steerplane.yml`** — centralize defaults per project, override per-agent
7. **Use the CLI** — `steerplane status` and `steerplane runs list` for quick diagnostics
