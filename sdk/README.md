# SteerPlane SDK

**Agent Control Plane for Autonomous Systems**

> "Agents don't fail in the dark anymore."

## Quick Start

```bash
pip install steerplane
```

### Decorator API (Minimal Integration)

```python
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50)
def run_agent():
    agent.run()
```

### Context Manager API (Full Control)

```python
from steerplane import SteerPlane

sp = SteerPlane(agent_id="my_bot")

with sp.run(max_cost_usd=10) as run:
    run.log_step("query_db", tokens=380, cost=0.002)
    run.log_step("generate_response", tokens=1240, cost=0.008)
```

## Features

- 🛡️ **Policy Engine (New in v0.3.0)** — Define strict allow/deny rules, rate limits (sliding windows), and human-in-the-loop approval workflows for agents.
- 🌉 **AI Gateway Proxy (New in v0.3.0)** — Zero-code integration. Point your default LangChain/OpenAI client to the SteerPlane gateway, and every LLM call gets token tracking, cost evaluation, and policy enforcement automatically.
- 🧩 **First-Class LangChain & CrewAI Support** — Drop in `SteerPlaneCallbackHandler` for total observability of your multi-agent networks without modifying agent chains.
- 🔄 **Infinite Loop Detection** — Automatically detects repeating agent behavior and breaks loops before they drain API budgets.
- 💰 **Hard Cost Limits** — Stop expensive agent runs the instant they cross a predefined USD ceiling. Tracks 25+ LLM models locally.
- 🚫 **Step Limits** — Cap maximum execution steps to prevent runway execution.
- 📊 **Deep Telemetry** — Full step-by-step execution tracking (tokens, latency, cost per step) synced instantly to the dashboard.

## Advanced Usage: Policy Engine

```python
from steerplane import guard

@guard(
    max_cost_usd=10, 
    denied_actions=["DROP TABLE*", "rm -rf *"],
    rate_limits=[{"pattern": "send_email", "max_count": 5, "window_seconds": 60}],
    require_approval=["execute_trade*"]
)
def autonomous_agent():
    agent.run()
```

## Documentation

See [docs.steerplane.ai](https://docs.steerplane.ai) for full documentation.
