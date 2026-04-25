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
  <a href="PATENTS.md"><img src="https://img.shields.io/badge/Patent-Pending-orange?style=flat-square" alt="Patent Pending"></a>
</p>

<p align="center">
  <b>Runtime guardrails for autonomous AI agents.</b><br>
  Cost limits · Loop detection · Dual enforcement (Kill/Alert) · Gateway proxy · Policy engine · Human-in-the-loop approvals · Real-time dashboard<br><br>
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
    enforcement="alert",
    alert_threshold=0.8,
    alert_timeout_sec=1800,
)
def run_agent():
    # Your agent runs normally.
    # SteerPlane silently monitors every step.
    # Financial/runtime limits can pause for human approval.
    # Loops and policy violations still terminate immediately.
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
| 🔄 | **Loop Detection** | O(W²) sliding-window algorithm catches single-action, alternating, and multi-step repeating patterns in sub-millisecond time — no LLM calls |
| 💰 | **Hard Cost Ceiling** | Per-run USD limits with built-in pricing for 25+ models across OpenAI, Anthropic, Google, Meta, and Mistral |
| 🔔 | **Dual Enforcement (Kill/Alert)** | Kill mode terminates instantly. Alert mode pauses, notifies humans (email/webhook), and waits for approve/deny/extend |
| 🚫 | **Step Limit** | Cap maximum execution steps to prevent unbounded resource consumption |
| ⏱️ | **Runtime Limit** | Maximum wall-clock time per run — either alerts or terminates based on enforcement mode |
| 🛡️ | **Policy Engine** | Allow/deny lists with glob patterns (`fnmatch`), sliding-window rate limits, and human-in-the-loop approval gates |
| 🌐 | **Gateway Proxy** | OpenAI-compatible API proxy — change only `base_url` for zero-code enforcement. Real LLM keys never exposed to agents |
| 📊 | **Deep Telemetry** | Every step's action name, tokens, cost, latency, and status — captured automatically |
| 🖥️ | **Real-Time Dashboard** | Next.js dashboard with 3s auto-refresh, animated timelines, cost breakdowns, policy management, and approval workflows |
| 🔗 | **LangChain Integration** | Drop-in callback handler for LangChain/LangGraph agents — zero refactoring |
| 📧 | **Notifications** | Multi-channel dispatch — SMTP email and HTTP webhooks (Slack, Discord, PagerDuty, etc.) |
| 🔌 | **Graceful Degradation** | If the API goes down, the SDK enforces all limits locally. Alert mode degrades to kill mode. Agents are never unprotected |

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

If you want a stable admin token for dashboard management screens, set
`STEERPLANE_ADMIN_TOKEN` before starting the API. Otherwise SteerPlane
generates a temporary token and prints it in the startup logs.

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

Use the dashboard's `Admin Token` button to unlock policy, API key, and approval management.

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
    enforcement="alert",
    alert_threshold=0.8,
    alert_timeout_sec=1800,
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

## Gateway Proxy (Zero-Code Mode)

For agents you can't modify, SteerPlane provides an OpenAI-compatible gateway proxy. Change **two lines** — the agent gets full enforcement without touching its code:

```python
from openai import OpenAI

# Before: direct to OpenAI
# client = OpenAI(api_key="sk-...")

# After: route through SteerPlane gateway
client = OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="sp_your_steerplane_key",  # SteerPlane key — real LLM key stays server-side
)

# Everything else stays the same
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
```

**Security model:** The agent process never holds the real LLM API key. SteerPlane stores it server-side and injects it during request forwarding.

**What the gateway enforces per request:**
- Policy rules (deny/allow/rate limits)
- Session cost vs. ceiling
- SHA-256 prompt-hash loop detection
- Per-key enforcement mode (kill or alert)
- Monthly budget tracking

---

## LangChain Integration

```python
from steerplane.integrations.langchain import SteerPlaneCallbackHandler

handler = SteerPlaneCallbackHandler(
    agent_name="research_bot",
    max_cost_usd=5.0,
    max_steps=30,
)

# Pass as callback to any LangChain agent or chain
agent.run("Analyze this data", callbacks=[handler])
```

Zero refactoring. Works with LangChain, LangGraph, and any `Runnable`.

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

## Dual Enforcement (Kill / Alert)

SteerPlane supports two enforcement modes for every limit:

| Mode | Behavior |
|------|----------|
| **Kill** (default) | Immediately terminates the agent on any violation. Fast, deterministic. |
| **Alert** | Pauses execution → dispatches notifications (email/webhook) → waits for human to approve, deny, or extend the limit → auto-terminates on timeout as safety net |

```python
@guard(
    max_cost_usd=10.00,
    enforcement="alert",      # "kill" or "alert"
    alert_threshold=0.8,      # Pause at 80% of limit
    alert_timeout_sec=1800,   # Auto-terminate after 30min if no response
    alert_email="ops@company.com",
    alert_webhook_url="https://hooks.slack.com/services/xxx",
)
def run_agent():
    agent.run()
```

> **Safety invariant:** Loop detection and policy violations **always** trigger immediate termination regardless of enforcement mode. These are non-overridable security constraints.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Agent Application                   │
│         (OpenAI SDK, LangChain, CrewAI, etc.)        │
└──────────────┬────────────────────┬──────────────────┘
               │                    │
      SDK Mode │          Gateway Mode
     (@guard)  │       (base_url change)
               ▼                    ▼
┌──────────────────────┐  ┌──────────────────────────┐
│   SteerPlane SDK     │  │   Gateway Proxy          │
│   (In-Process)       │  │   (Network Layer)        │
│                      │  │                          │
│   Guard Engine       │  │   Auth → Policy → Cost   │
│   Policy Engine      │  │   → Loop → Forward       │
│   Cost Tracker       │  │                          │
│   Loop Detector      │  │   Real LLM key stored    │
│   Run Manager        │  │   server-side only       │
└──────────┬───────────┘  └──────────┬───────────────┘
           │                         │
           ▼                         ▼
┌────────────────────────────────────────────────────┐
│              SteerPlane API Server                  │
│      (FastAPI + SQLAlchemy + PostgreSQL/SQLite)     │
│    Runs · Steps · Policies · Approvals · API Keys  │
└───────────────┬──────────────┬─────────────────────┘
                │              │
        ┌───────▼──────┐  ┌───▼──────────────────┐
        │   Next.js    │  │  Notifications       │
        │   Dashboard  │  │  (Email / Webhook)   │
        └──────────────┘  └──────────────────────┘
```

| Layer | Stack | Purpose |
|-------|-------|---------|
| **SDK** | Python 3.10+ / Node.js 18+ | `@guard` decorator, cost tracking, loop detection, policy engine, dual enforcement |
| **Gateway Proxy** | FastAPI + HTTPX | OpenAI-compatible proxy with policy enforcement, cost tracking, and key isolation |
| **API** | FastAPI + SQLAlchemy + Pydantic | REST endpoints for runs, steps, policies, approvals, API keys, telemetry |
| **Database** | PostgreSQL / SQLite | Persistent storage for runs, steps, policies, approvals, and API keys |
| **Dashboard** | Next.js + React + Framer Motion | Real-time monitoring, run timelines, policy management, approval workflows |
| **Notifications** | smtplib + HTTPX | Multi-channel alert dispatch (email, Slack, Discord, PagerDuty) |

---

## Project Structure

```
SteerPlane/
├── sdk/                     # Python SDK (pip install steerplane)
│   └── steerplane/
│       ├── guard.py         # @guard decorator + SteerPlane class
│       ├── run_manager.py   # Run lifecycle + dual enforcement (kill/alert)
│       ├── cost_tracker.py  # Cost calculation + model pricing
│       ├── loop_detector.py # O(W²) sliding-window loop detection
│       ├── policy_engine.py # Allow/deny, rate limits, approval gates
│       ├── client.py        # HTTP client with graceful degradation
│       ├── runtime_context.py # Active run tracking for signal handling
│       ├── telemetry.py     # Step event collection
│       ├── exceptions.py    # 6 typed exception classes
│       └── integrations/
│           └── langchain.py # LangChain/LangGraph callback handler
├── sdk-ts/                  # TypeScript SDK (npm install steerplane)
│   └── src/
│       ├── guard.ts         # guard() HOF + SteerPlane class
│       ├── run-manager.ts   # Run lifecycle + dual enforcement
│       ├── cost-tracker.ts  # Cost tracking + limits
│       ├── loop-detector.ts # Loop detection
│       ├── policy-engine.ts # Policy engine + glob matching
│       ├── client.ts        # HTTP client (native fetch)
│       └── errors.ts        # 7 typed error classes
├── api/                     # FastAPI backend
│   └── app/
│       ├── main.py          # App entry point + CORS + startup
│       ├── security.py      # Admin token auth middleware
│       ├── routes/
│       │   ├── runs.py      # Run lifecycle endpoints
│       │   ├── policies.py  # Policy CRUD + evaluation
│       │   ├── approvals.py # Approval create/approve/deny/list
│       │   ├── gateway.py   # OpenAI-compatible proxy endpoints
│       │   ├── api_keys.py  # API key management with enforcement
│       │   └── telemetry.py # Batch telemetry ingestion
│       ├── models/          # Run, Step, Policy, ApprovalRequest, APIKeyEnforcement
│       ├── schemas/         # Pydantic request/response schemas
│       └── services/
│           ├── run_service.py       # Run business logic
│           ├── policy_service.py    # Policy business logic
│           ├── gateway_service.py   # Gateway proxy + 25 model pricing
│           ├── approval_service.py  # Approval lifecycle management
│           └── notification_service.py # Email (SMTP) + webhook dispatch
├── dashboard/               # Next.js real-time dashboard
│   └── src/
│       ├── app/
│       │   ├── dashboard/   # Run list + run detail pages
│       │   ├── policies/    # Policy management UI
│       │   ├── approvals/   # Approve/deny/extend pending requests
│       │   └── api-keys/    # API key management with enforcement config
│       ├── components/      # RunTable, StepTimeline, StatusBadge, CostBadge, Navbar
│       └── services/        # API client + admin auth
├── examples/                # Example agent integrations
│   ├── simple_agent/        # 3-scenario demo (normal, loop, cost)
│   ├── simple_llm_agent/    # Minimal @guard decorator usage
│   ├── openai_agent/        # OpenAI tool-use pattern
│   └── langgraph_agent/     # LangGraph workflow pattern
└── docs/                    # Documentation
```

---

## API Endpoints

The FastAPI server exposes endpoints with auto-generated docs at `/docs`:

**Runs**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/runs/start` | Start a governed agent run |
| `POST` | `/runs/step` | Log an execution step |
| `POST` | `/runs/end` | Finalize a run |
| `GET` | `/runs/{run_id}` | Get run details with all steps |
| `GET` | `/runs` | List runs (paginated) |

**Policies**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/policies` | Create a policy |
| `GET` | `/policies` | List policies |
| `GET` | `/policies/{policy_id}` | Get a policy |
| `PUT` | `/policies/{policy_id}` | Update a policy |
| `DELETE` | `/policies/{policy_id}` | Delete a policy |
| `POST` | `/policies/{policy_id}/evaluate` | Evaluate an action against a policy |

**Approvals (Human-in-the-Loop)**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/approvals` | Create an approval request |
| `GET` | `/approvals` | List pending/resolved approvals |
| `POST` | `/approvals/{id}/approve` | Approve with optional limit extension |
| `POST` | `/approvals/{id}/deny` | Deny and terminate the run |

**Gateway Proxy**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/gateway/v1/chat/completions` | OpenAI-compatible chat completions proxy |
| `GET` | `/gateway/v1/models` | List available models |

**API Keys**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api-keys` | Create an API key with enforcement config |
| `GET` | `/api-keys` | List API keys |
| `DELETE` | `/api-keys/{key_id}` | Revoke an API key |

**Other**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/telemetry` | Batch ingest telemetry events |

---

## Supported Models (25+)

Built-in pricing for cost tracking across all major providers:

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-Turbo, GPT-4, GPT-3.5-Turbo, o1, o1-mini, o3-mini |
| **Anthropic** | Claude 4 Opus/Sonnet, Claude 3.5 Sonnet/Haiku, Claude 3 Opus/Sonnet/Haiku |
| **Google** | Gemini 2.0 Flash, Gemini 1.5 Pro/Flash, Gemini Pro |
| **Meta** | Llama 3 70B, Llama 3 8B |
| **Mistral** | Mistral Large, Mistral Small |

Custom models can be added via the pricing table.

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
- [x] Cost tracking with built-in pricing for 25+ models (5 providers)
- [x] O(W²) sliding-window infinite loop detection
- [x] Step limit and runtime limit enforcement
- [x] Policy engine — allow/deny lists, rate limits, approval workflows
- [x] Real-time Next.js dashboard with auto-refresh
- [x] Step-by-step execution timelines
- [x] Dashboard policy management UI
- [x] Full per-step telemetry capture
- [x] Graceful offline degradation
- [x] REST API with policy CRUD and evaluation
- [x] Dual enforcement — kill mode + alert mode
- [x] Human-in-the-loop approval workflow with approve/deny/extend
- [x] Notification dispatch — SMTP email + HTTP webhooks
- [x] OpenAI-compatible gateway proxy (zero-code enforcement)
- [x] LangChain/LangGraph callback handler integration
- [x] API key management with per-key enforcement config
- [x] Dashboard approval management page
- [ ] Docker Compose for one-command deployment
- [ ] SSE streaming support in gateway proxy
- [ ] Multi-tenant RBAC authentication
- [ ] Multi-agent fleet monitoring dashboard
- [ ] SDK ↔ API policy sync (fetch stored policies into SDK)
- [ ] CLI tool (`steerplane init`, `steerplane status`)
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

# Run SDK tests
cd sdk && python -m pytest tests/

# Run API tests
cd api && python -m pytest tests/
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
