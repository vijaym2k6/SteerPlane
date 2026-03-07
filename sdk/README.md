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

- 🔄 **Loop Detection** — Automatically detects repeating agent behavior
- 💰 **Cost Limits** — Stop expensive agent runs before they blow budgets
- 🚫 **Step Limits** — Prevent runaway execution
- 📊 **Telemetry** — Full step-by-step execution tracking
- 🖥️ **Dashboard** — Visual execution monitoring

## Documentation

See [docs.steerplane.ai](https://docs.steerplane.ai) for full documentation.
