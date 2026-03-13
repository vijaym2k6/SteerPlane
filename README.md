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
  Cost limits · Loop detection · Step caps · Policy engine · Full telemetry · Real-time dashboard<br><br>
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
    denied_actions=["delete_*", "sudo_*"],
)
def run_agent():
    # Your agent runs normally.
    # SteerPlane silently monitors every step.
    # If it loops, overspends, or violates policy — terminated instantly.
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
| 💰 | **Hard Cost Ceiling** | Set a per-run USD limit with built-in pricing for GPT-4o, Claude 3, Gemini Pro, and more |
| 🚫 | **Step Limit** | Cap maximum execution steps to prevent unbounded resource consumption |
| ⏱️ | **Runtime Limit** | Maximum wall-clock time per run — terminates agents that hang or stall |
| 🛡️ | **Policy Engine** | Allow/deny lists with glob patterns, sliding-window rate limits, and human-in-the-loop approval workflows |
| 📊 | **Deep Telemetry** | Every step's action name, tokens, cost, latency, and status — captured automatically |
| 🖥️ | **Real-Time Dashboard** | Next.js dashboard with 3-second auto-refresh, animated timelines, cost breakdowns, and policy management |
| 🔌 | **Graceful Degradation** | If the API goes down, the SDK enforces all limits locally. Agents are never unprotected |

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
    max_runtime_sec=300,
    denied_actions=["delete_*", "sudo_*"],
    allowed_actions=["search_*", "read_*", "generate_*"],
    rate_limits=[{"pattern": "call_llm*", "max_count": 20, "window_seconds": 60}],
)
def run_my_agent():
    agent.run()
```

### Python — Context Manager API

```python
from steerplane import SteerPlane

sp = SteerPlane(agent_id="my_bot")

with sp.run(max_cost_usd=10.0, max_steps=50) as run:
    run.log_step("query_db", tokens=380, cost=0.002, latency_ms=45)
    run.log_step("generate", tokens=1240, cost=0.008, latency_ms=320)
```

### TypeScript

```typescript
import { guard, GuardOptions } from 'steerplane';

const protectedAgent = guard(async (run) => {
  await run.logStep({ action: 'query_db', tokens: 380, cost: 0.002 });
  await run.logStep({ action: 'generate', tokens: 1240, cost: 0.008 });
  return 'done';
}, {
  agentName: 'support_bot',
  maxCostUsd: 10.0,
  maxSteps: 50,
  policy: {
    deniedActions: ['delete_*', 'sudo_*'],
  },
});

const result = await protectedAgent();
```

### Exception Handling

```python
from steerplane.exceptions import (
    CostLimitExceeded,
    LoopDetectedError,
    StepLimitExceeded,
    PolicyViolationError,
)

@guard(max_cost_usd=5, denied_actions=["delete_*"])
def run_agent():
    try:
        agent.run()
    except CostLimitExceeded as e:
        print(f"Budget exceeded: {e}")
    except LoopDetectedError as e:
        print(f"Loop detected: {e}")
    except StepLimitExceeded as e:
        print(f"Step limit hit: {e}")
    except PolicyViolationError as e:
        print(f"Policy violation: {e.action} blocked by {e.rule}")
```

---

## Policy Engine

The policy engine runs **before** any cost is incurred, enforcing rules in strict priority order:

```
Deny List → Allow List → Rate Limits → Approval Workflow
```

```python
from steerplane import SteerPlane, RateLimitSpec

sp = SteerPlane(agent_id="production_bot")

with sp.run(
    max_cost_usd=25.0,
    denied_actions=["delete_*", "drop_*", "sudo_*"],
    allowed_actions=["search_*", "read_*", "generate_*", "send_email"],
    rate_limits=[
        RateLimitSpec(pattern="send_email", max_count=5, window_seconds=60),
        RateLimitSpec(pattern="search_*", max_count=30, window_seconds=60),
    ],
    require_approval=["send_email"],
    approval_callback=lambda action, meta: input(f"Allow {action}? (y/n): ") == "y",
) as run:
    run.log_step("search_docs", tokens=200, cost=0.001, latency_ms=50)
    run.log_step("generate_response", tokens=800, cost=0.005, latency_ms=200)
```

| Rule Type | How It Works |
|-----------|-------------|
| **Deny list** | Glob patterns (e.g. `delete_*`) — any match is blocked immediately |
| **Allow list** | If set, action must match at least one pattern to proceed |
| **Rate limits** | Sliding-window counters per pattern — blocks when count exceeds threshold |
| **Approval workflow** | Matched actions trigger a callback for human-in-the-loop approval |

Available in both Python and TypeScript SDKs, and manageable via the dashboard UI and REST API.

---

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌────────────┐     ┌───────────────┐
│  AI Agent   │────▶│    SteerPlane SDK     │────▶│  FastAPI    │────▶│  PostgreSQL   │
│  (Your App) │     │                      │     │  Server     │     │  / SQLite     │
└─────────────┘     │  Guard Engine        │     └────────────┘     └───────────────┘
                    │  Policy Engine       │            │
                    │  Cost Tracker        │            ▼
                    │  Loop Detector       │     ┌───────────────┐
                    │  Run Manager         │     │   Next.js     │
                    │  Telemetry Client    │     │   Dashboard   │
                    └──────────────────────┘     └───────────────┘
```

| Layer | Stack | Purpose |
|-------|-------|---------|
| **SDK** | Python 3.10+ / Node.js 18+ | `@guard` decorator, cost tracking, loop detection, policy engine |
| **API** | FastAPI + SQLAlchemy | REST endpoints for runs, steps, policies, telemetry |
| **Database** | PostgreSQL 17 / SQLite | Persistent storage for runs, steps, and policies |
| **Dashboard** | Next.js 16 + React 19 + Framer Motion | Real-time monitoring, run timelines, policy management |

---

## Project Structure

```
SteerPlane/
├── sdk/                     # Python SDK (pip install steerplane)
│   └── steerplane/
│       ├── guard.py         # @guard decorator + SteerPlane class
│       ├── run_manager.py   # Run lifecycle orchestration
│       ├── cost_tracker.py  # Cost calculation + limit enforcement
│       ├── loop_detector.py # Sliding-window loop detection
│       ├── policy_engine.py # Allow/deny, rate limits, approval
│       ├── telemetry.py     # Step event collection
│       ├── client.py        # HTTP client with graceful degradation
│       └── exceptions.py    # 6 typed exception classes
├── sdk-ts/                  # TypeScript SDK (npm install steerplane)
│   └── src/
│       ├── guard.ts         # guard() HOF + SteerPlane class
│       ├── run-manager.ts   # Run lifecycle orchestration
│       ├── cost-tracker.ts  # Cost tracking + limits
│       ├── loop-detector.ts # Loop detection
│       ├── policy-engine.ts # Policy engine + glob matching
│       ├── client.ts        # HTTP client (native fetch)
│       └── errors.ts        # 7 typed error classes
├── api/                     # FastAPI backend
│   └── app/
│       ├── main.py          # App entry point + CORS + startup
│       ├── routes/          # runs, policies, telemetry endpoints
│       ├── models/          # Run, Step, Policy ORM models
│       ├── schemas/         # Pydantic request/response schemas
│       └── services/        # Run + Policy business logic
├── dashboard/               # Next.js real-time dashboard
│   └── src/
│       ├── app/             # Landing, dashboard, run detail, policies
│       ├── components/      # RunTable, StepTimeline, StatusBadge, CostBadge
│       └── services/        # API client
├── examples/                # Example agent integrations
│   ├── simple_agent/        # 3-scenario demo (normal, loop, cost)
│   ├── simple_llm_agent/    # Minimal @guard decorator usage
│   ├── openai_agent/        # OpenAI tool-use pattern
│   └── langgraph_agent/     # LangGraph workflow pattern
└── docs/                    # Documentation
```

---

## API Endpoints

The FastAPI server exposes 11 endpoints with auto-generated docs at `/docs`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/runs/start` | Start a governed agent run |
| `POST` | `/runs/step` | Log an execution step |
| `POST` | `/runs/end` | Finalize a run |
| `GET` | `/runs/{run_id}` | Get run details with all steps |
| `GET` | `/runs` | List runs (paginated) |
| `POST` | `/telemetry` | Batch ingest telemetry events |
| `POST` | `/policies` | Create a policy |
| `GET` | `/policies` | List policies (paginated) |
| `GET` | `/policies/{policy_id}` | Get a policy |
| `PUT` | `/policies/{policy_id}` | Update a policy |
| `DELETE` | `/policies/{policy_id}` | Delete a policy |
| `POST` | `/policies/{policy_id}/evaluate` | Evaluate an action against a policy |

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | 5-minute quickstart guide |
| [Installation](docs/installation.md) | Full setup instructions |
| [SDK Usage](docs/sdk-usage.md) | Python and TypeScript API reference |
| [Example Agents](docs/example-agents.md) | Integration examples |
| [Dashboard Guide](docs/dashboard-guide.md) | Dashboard usage guide |
| [Architecture](docs/architecture.md) | System design deep dive |

---

## Roadmap

- [x] Python SDK with `@guard` decorator and context manager API
- [x] TypeScript SDK with `guard()` HOF and class API
- [x] Cost tracking with built-in pricing for 9 models
- [x] Sliding-window infinite loop detection
- [x] Step limit and runtime limit enforcement
- [x] Policy engine — allow/deny lists, rate limits, approval workflows
- [x] Real-time Next.js dashboard with auto-refresh
- [x] Step-by-step execution timelines
- [x] Dashboard policy management UI
- [x] Full per-step telemetry capture
- [x] Graceful offline degradation
- [x] REST API with policy CRUD and evaluation
- [ ] Webhook alerts (Slack, Discord, email)
- [ ] Multi-agent fleet monitoring
- [ ] SDK ↔ API policy sync (fetch stored policies into SDK)
- [ ] Cloud-hosted dashboard (SaaS)

---

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
