<p align="center">
  <img src="assets/banner.png" alt="SteerPlane Banner" width="100%" />
</p>

<p align="center">
  <a href="https://pypi.org/project/steerplane/"><img src="https://img.shields.io/pypi/v/steerplane?style=flat-square&color=3B82F6&label=PyPI" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/steerplane"><img src="https://img.shields.io/npm/v/steerplane?style=flat-square&color=3B82F6&label=npm" alt="npm"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Node.js-18+-green?style=flat-square&logo=node.js&logoColor=white" alt="Node">
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome"></a>
</p>

<p align="center">
  <b>Runtime guardrails for autonomous AI agents.</b><br>
  Cost limits · Loop detection · Step caps · Full telemetry · Real-time dashboard<br><br>
  <code>pip install steerplane</code> · <code>npm install steerplane</code>
</p>

---

## The Problem

AI agents can call APIs, execute code, browse the web, and make real-world decisions. Without guardrails:

- 🔄 A single misconfigured agent can **enter an infinite loop**  
- 💸 A runaway agent can **burn through $10,000+ in API credits overnight**  
- 💀 Agents can take **destructive actions** with **zero visibility**

SteerPlane fixes this with **one line of code.**

## How It Works

```python
from steerplane import guard

@guard(
    agent_name="support_bot",
    max_cost_usd=10.00,
    max_steps=50,
    detect_loops=True
)
def run_agent():
    # Your agent runs normally.
    # SteerPlane silently monitors every step.
    # If it loops, overspends, or exceeds limits — terminated instantly.
    agent.run()
```

```
🚀 SteerPlane | Run Started
   Run ID:  a3f8d2b1-...
   Agent:   support_bot
   Limits:  $10.00 cost / 50 steps
   ─────────────────────────────────────────────
   ✅ Step 1: query_database     | 380 tokens  | $0.0020 | 45ms
   ✅ Step 2: call_llm_analyze   | 1240 tokens | $0.0080 | 320ms
   ✅ Step 3: search_knowledge   | 560 tokens  | $0.0030 | 89ms
   ✅ Step 4: generate_response  | 1800 tokens | $0.0120 | 450ms
   ✅ Step 5: send_notification  | 120 tokens  | $0.0010 | 200ms
   ─────────────────────────────────────────────

✅ SteerPlane | Run COMPLETED
   Steps:      5
   Cost:       $0.0260
   Tokens:     4,100
   Duration:   1.1s
```

---

## Features

| | Feature | What It Does |
|---|---------|-------------|
| 🔄 | **Loop Detection** | Sliding-window pattern detector catches repeating agent behavior in real time |
| 💰 | **Hard Cost Ceiling** | Set a per-run USD limit. The instant cumulative spend crosses your threshold — terminated |
| 🚫 | **Step Limit** | Cap maximum execution steps to prevent unbounded resource consumption |
| 📊 | **Deep Telemetry** | Every step's action name, tokens, cost, latency, and status — captured automatically |
| 🖥️ | **Real-Time Dashboard** | Next.js dashboard with auto-refresh, visual timelines, and cost breakdowns |
| 🛡️ | **Graceful Degradation** | If the API goes down, the SDK enforces limits locally. Agents are never unprotected |

---

## Quick Start

### Install

```bash
# Python
pip install steerplane

# TypeScript / Node.js
npm install steerplane
```

### Start the API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Start the Dashboard

```bash
cd dashboard
npm install && npm run dev
```

### Run the Demo Agent

```bash
python examples/simple_agent/agent_example.py
```

Open **[localhost:3000](http://localhost:3000)** → See your agent run in real time.

---

## SDK Reference

### Python — Decorator API

```python
from steerplane import guard

@guard(
    agent_name="my_bot",
    max_cost_usd=10.00,
    max_steps=50,
    detect_loops=True
)
def run_my_agent():
    agent.run()
```

### Python — Context Manager API

```python
from steerplane import SteerPlane

sp = SteerPlane(agent_id="my_bot")

with sp.run(max_cost_usd=10.0) as run:
    run.log_step("query_db", tokens=380, cost=0.002, latency_ms=45)
    run.log_step("generate", tokens=1240, cost=0.008, latency_ms=320)
```

### TypeScript

```typescript
import { guard, GuardConfig } from 'steerplane';

const config: GuardConfig = {
  agentName: 'support_bot',
  maxCostUsd: 10.0,
  maxSteps: 50,
  detectLoops: true,
};

const result = await guard(config, async (run) => {
  run.logStep('query_db', { tokens: 380, cost: 0.002 });
  run.logStep('generate', { tokens: 1240, cost: 0.008 });
  return 'done';
});
```

### Exception Handling

```python
from steerplane.exceptions import CostLimitExceeded, LoopDetected, StepLimitExceeded

@guard(max_cost_usd=5, detect_loops=True)
def run_agent():
    try:
        agent.run()
    except CostLimitExceeded as e:
        print(f"💰 Budget exceeded: {e}")
    except LoopDetected as e:
        print(f"🔄 Loop detected: {e}")
    except StepLimitExceeded as e:
        print(f"🚫 Step limit hit: {e}")
```

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────────┐
│  AI Agent   │────▶│ SteerPlane   │────▶│  FastAPI    │────▶│  PostgreSQL   │
│  (Your App) │     │  SDK         │     │  Server     │     │  Database     │
└─────────────┘     └──────────────┘     └────────────┘     └───────────────┘
                                                │
                                                ▼
                                         ┌───────────────┐
                                         │   Next.js     │
                                         │   Dashboard   │
                                         └───────────────┘
```

| Layer | Stack | Purpose |
|-------|-------|---------|
| **SDK** | Python 3.10+ / TypeScript | `@guard` decorator, cost tracking, loop detection |
| **API** | FastAPI | REST endpoints, SQLAlchemy ORM, auto-generated docs |
| **Database** | PostgreSQL 17 | Persistent storage for runs, steps, agents |
| **Dashboard** | Next.js 16 | Real-time monitoring with Framer Motion animations |

---

## Project Structure

```
SteerPlane/
├── sdk/                     # Python SDK (pip install steerplane)
│   └── steerplane/
│       ├── guard.py         # @guard decorator
│       ├── run_manager.py   # Run lifecycle management
│       ├── cost_tracker.py  # Cost limit enforcement
│       ├── loop_detector.py # Infinite loop detection
│       ├── telemetry.py     # Step-by-step telemetry
│       └── client.py        # HTTP client for API
├── sdk-ts/                  # TypeScript SDK (npm install steerplane)
│   └── src/
│       ├── guard.ts         # guard() wrapper
│       ├── run-manager.ts   # Run lifecycle
│       ├── cost-tracker.ts  # Cost limit enforcement
│       └── loop-detector.ts # Loop detection
├── api/                     # FastAPI backend
│   └── app/
│       ├── main.py          # App entry point + CORS
│       ├── routes/          # API endpoints
│       ├── models/          # SQLAlchemy models
│       ├── schemas/         # Pydantic schemas
│       └── services/        # Business logic
├── dashboard/               # Next.js real-time dashboard
│   └── src/
│       ├── app/             # Pages (landing, dashboard, run detail)
│       └── components/      # React components
├── examples/                # Example agent integrations
│   ├── simple_agent/        # Basic demo
│   ├── openai_agent/        # OpenAI with tool use
│   └── langgraph_agent/     # LangGraph workflow
└── docs/                    # Documentation
```

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | 5-minute quickstart guide |
| [Installation](docs/installation.md) | Full setup instructions |
| [SDK Usage](docs/sdk-usage.md) | Complete API reference |
| [Example Agents](docs/example-agents.md) | Integration examples |
| [Dashboard Guide](docs/dashboard-guide.md) | Dashboard usage |
| [Architecture](docs/architecture.md) | System design deep dive |

---

## Roadmap

- [x] Python SDK with `@guard` decorator
- [x] TypeScript SDK  
- [x] Cost tracking & hard limits
- [x] Infinite loop detection
- [x] Step limit enforcement
- [x] Real-time Next.js dashboard
- [x] Full telemetry capture
- [ ] Webhook alerts (Slack, Discord, email)
- [ ] Multi-agent fleet monitoring
- [ ] Custom guardrail rules engine
- [ ] Cloud-hosted dashboard (SaaS)

---

## Contributors

Thanks to these wonderful people:

| Avatar | Name |
|--------|------|
| <img src="https://github.com/shiri-09.png" width="50" style="border-radius:50%" /> | [@shiri-09](https://github.com/shiri-09) |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone the repo
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane

# Set up the API
cd api && pip install -r requirements.txt

# Set up the dashboard
cd dashboard && npm install

# Run tests
cd sdk && python -m pytest tests/
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <img src="assets/logo.jpg" alt="SteerPlane" width="48" /><br>
  <b>SteerPlane</b><br>
  <em>"Ship agents. Not incidents."</em>
</p>
