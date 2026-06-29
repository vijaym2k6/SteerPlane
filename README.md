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
  <a href="PATENTS.md"><img src="https://img.shields.io/badge/Patent%20Pending-IN%20202641071111%20A1-orange?style=flat-square" alt="Patent Pending — IN 202641071111 A1"></a>
  <a href="https://steerplane.com"><img src="https://img.shields.io/badge/Website-steerplane.com-3B82F6?style=flat-square" alt="steerplane.com"></a>
</p>

<p align="center">
  <b>Runtime guardrails for autonomous AI agents.</b><br>
  Cost limits · Loop detection · Dual enforcement (Kill/Alert) · Streaming gateway · Policy engine · Human-in-the-loop · CLI · Docker · 4 framework integrations<br><br>
  <code>pip install steerplane</code> · <code>npm install steerplane</code><br><br>
  🌐 <a href="https://steerplane.com"><b>steerplane.com</b></a>
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
| 🌊 | **Streaming Gateway** | Real-time SSE chunk forwarding with mid-stream cost kill — if the budget is exceeded during a stream, SteerPlane injects a termination event and cuts the connection |
| 🛡️ | **Policy Engine** | Allow/deny lists with glob patterns, sliding-window rate limits, and human-in-the-loop approval gates |
| 🌐 | **Gateway Proxy** | OpenAI-compatible API proxy — change only `base_url` for zero-code enforcement. Real LLM keys never exposed to agents |
| 🖥️ | **Real-Time Dashboard** | Next.js dashboard with auto-refresh, animated timelines, cost breakdowns, policy management, and approval workflows |
| 🔧 | **CLI Tool** | `steerplane runs list`, `steerplane status`, `steerplane keys create` — manage everything from your terminal |
| 📄 | **Config File** | `.steerplane.yml` auto-discovery — set defaults without hardcoding limits in source code |
| 🔗 | **4 Framework Integrations** | LangChain, OpenAI Agents SDK, CrewAI, AutoGen — zero-config drop-in handlers |
| 🐳 | **Docker Compose** | One command brings up API + Dashboard + PostgreSQL + Redis |
| 🔌 | **Graceful Degradation** | If the API goes down, the SDK enforces all limits locally. Alert mode degrades to kill mode. Agents are never unprotected |
| 📧 | **Notifications** | Multi-channel dispatch — SMTP email and HTTP webhooks (Slack, Discord, PagerDuty, etc.) |
| 🧪 | **CI/CD** | GitHub Actions pipeline — lint, test, build Docker on every push |

---

## Quick Start

### Option A: Docker (Recommended)

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane
cp .env.example .env
docker compose up -d
```

API at `localhost:8000` · Dashboard at `localhost:3000` · PostgreSQL + Redis auto-configured.

### Option B: Manual Setup

```bash
# Install the SDK
pip install steerplane

# Start the API
cd api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Start the Dashboard
cd dashboard && npm install && npm run dev
```

### Option C: CLI

```bash
pip install steerplane[cli]
steerplane status          # Check API health
steerplane runs list       # List recent runs
steerplane keys create -n prod  # Generate API key
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
    enforcement="alert",
    alert_threshold=0.8,
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

## Config File (.steerplane.yml)

Set defaults in a `.steerplane.yml` at your project root instead of hardcoding limits:

```yaml
api_url: http://localhost:8000
agent_name: my_bot

defaults:
  max_cost_usd: 25.0
  max_steps: 100
  max_runtime_sec: 1800
  enforcement: alert
  loop_window_size: 10

policy:
  denied_actions:
    - "delete_*"
    - "drop_*"
  rate_limits:
    - pattern: "search_*"
      max_calls: 10
      window_sec: 60

alerts:
  email: ops@company.com
  webhook_url: https://hooks.slack.com/...
  threshold: 0.8
```

**Merge order:** Explicit decorator params → `.steerplane.yml` → hardcoded defaults. The config file is auto-discovered by walking up from the current directory.

---

## Framework Integrations

### LangChain

```python
from steerplane.integrations.langchain import SteerPlaneCallbackHandler

handler = SteerPlaneCallbackHandler(
    agent_name="research_bot",
    max_cost_usd=5.0,
    max_steps=30,
)

llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
agent.run("Analyze this data", callbacks=[handler])
handler.finish()
```

### OpenAI Agents SDK

```python
from steerplane.integrations.openai_agents import SteerPlaneAgentHooks

hooks = SteerPlaneAgentHooks(
    agent_name="my_openai_agent",
    max_cost_usd=10.0,
    max_steps=100,
)

# Convenience wrapper
result = await hooks.run(agent, "Hello!")

# Or manual lifecycle
hooks.start()
result = await Runner.run(agent, "Hello!")
hooks.finish()
```

### CrewAI

```python
from steerplane.integrations.crewai import SteerPlaneCrewMonitor

monitor = SteerPlaneCrewMonitor(
    agent_name="my_crew",
    max_cost_usd=25.0,
    max_steps=200,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    step_callback=monitor.step_callback,
)

result = monitor.kickoff(crew)
```

### AutoGen

```python
from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor

monitor = SteerPlaneAutoGenMonitor(
    agent_name="my_autogen_group",
    max_cost_usd=15.0,
    max_steps=150,
)

result = monitor.initiate_chat(user_proxy, assistant, message="Hello!")
```

Install only the integration you need:
```bash
pip install steerplane[langchain]   # LangChain
pip install steerplane[cli]         # CLI tool
pip install steerplane[yaml]        # Config file support
pip install steerplane[all]         # Everything
```

---

## Gateway Proxy (Zero-Code Mode)

For agents you can't modify, SteerPlane provides an OpenAI-compatible gateway proxy with **real-time streaming** and **mid-stream cost enforcement**:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="sk_sp_your_steerplane_key",
)

# Streaming works — chunks forwarded in real-time
for chunk in client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
):
    print(chunk.choices[0].delta.content, end="")
```

**What the gateway enforces per request:**
- Policy rules (deny/allow/rate limits)
- Session cost vs. ceiling (including mid-stream kill)
- SHA-256 prompt-hash loop detection
- Per-key enforcement mode (kill or alert)
- Monthly budget tracking
- Anthropic + OpenAI streaming support

**Security model:** The agent process never holds the real LLM API key. SteerPlane stores it server-side and injects it during request forwarding.

---

## CLI Tool

```bash
pip install steerplane[cli]
```

| Command | Description |
|---------|-------------|
| `steerplane status` | Check API server health |
| `steerplane runs list` | List recent runs (filter by `--status`) |
| `steerplane runs inspect <id>` | Full run detail with step-by-step table |
| `steerplane runs kill <id>` | Force-terminate a live run |
| `steerplane keys list` | List all API keys |
| `steerplane keys create --name prod` | Generate a new API key |
| `steerplane keys revoke <id>` | Revoke a key |
| `steerplane logs --tail` | Live polling of running agents |

---

## Policy Engine

The policy engine runs **before** any cost is incurred, enforcing rules in strict priority order:

```
Deny List → Allow List → Rate Limits → Approval Workflow
```

| Rule Type | How It Works |
|-----------|-------------|
| **Deny list** | Glob patterns (e.g. `delete_*`) — any match is blocked immediately |
| **Allow list** | If set, action must match at least one pattern to proceed |
| **Rate limits** | Sliding-window counters per pattern — blocks when count exceeds threshold |
| **Approval workflow** | Matched actions trigger a callback for human-in-the-loop approval |

Available in Python and TypeScript SDKs, the dashboard UI, REST API, and `.steerplane.yml` config file.

---

## Dual Enforcement (Kill / Alert)

| Mode | Behavior |
|------|----------|
| **Kill** (default) | Immediately terminates the agent on any violation. Fast, deterministic. |
| **Alert** | Pauses execution → dispatches notifications (email/webhook) → waits for human to approve, deny, or extend the limit → auto-terminates on timeout as safety net |

> **Safety invariant:** Loop detection and policy violations **always** trigger immediate termination regardless of enforcement mode. These are non-overridable security constraints.

---

## Docker Deployment

```bash
cp .env.example .env    # Edit with your values
docker compose up -d    # Starts all 4 services
```

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Pub/sub (future WebSocket) |
| `api` | steerplane-api | 8000 | FastAPI backend |
| `dashboard` | steerplane-dashboard | 3000 | Next.js UI |

Database migrations via Alembic:
```bash
cd api
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Agent Application                   │
│    (OpenAI SDK, LangChain, CrewAI, AutoGen, etc.)    │
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
│   Policy Engine      │  │   → Loop → Stream Fwd    │
│   Cost Tracker       │  │                          │
│   Loop Detector      │  │   Mid-stream cost kill   │
│   Run Manager        │  │   Real LLM key isolated  │
│   Config File        │  │                          │
└──────────┬───────────┘  └──────────┬───────────────┘
           │                         │
           ▼                         ▼
┌────────────────────────────────────────────────────┐
│              SteerPlane API Server                  │
│      (FastAPI + SQLAlchemy + PostgreSQL/SQLite)     │
│    Runs · Steps · Policies · Approvals · API Keys  │
└──────┬──────────┬──────────────┬──────────────────┘
       │          │              │
  ┌────▼───┐  ┌───▼──────┐  ┌───▼──────────────────┐
  │ CLI    │  │ Next.js  │  │  Notifications       │
  │ Tool   │  │ Dashboard│  │  (Email / Webhook)   │
  └────────┘  └──────────┘  └──────────────────────┘
```

| Layer | Stack | Purpose |
|-------|-------|---------|
| **SDK** | Python 3.10+ / Node.js 18+ | `@guard` decorator, cost tracking, loop detection, policy engine, config file, dual enforcement |
| **Gateway Proxy** | FastAPI + HTTPX | OpenAI-compatible proxy with SSE streaming, mid-stream cost kill, and key isolation |
| **API** | FastAPI + SQLAlchemy + Alembic | REST endpoints for runs, steps, policies, approvals, API keys, telemetry |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Persistent storage with versioned migrations |
| **Dashboard** | Next.js + React + Framer Motion | Real-time monitoring, run timelines, policy management, approval workflows |
| **CLI** | Click | Terminal-based management — runs, keys, status, live logs |
| **CI/CD** | GitHub Actions | Lint → Test → Build Docker on every push |

---

## Project Structure

```
SteerPlane/
├── sdk/                         # Python SDK (pip install steerplane)
│   └── steerplane/
│       ├── guard.py             # @guard decorator + SteerPlane class
│       ├── run_manager.py       # Run lifecycle + dual enforcement (kill/alert)
│       ├── cost_tracker.py      # Cost calculation + model pricing
│       ├── loop_detector.py     # O(W²) sliding-window loop detection
│       ├── policy_engine.py     # Allow/deny, rate limits, approval gates
│       ├── client.py            # HTTP client with graceful degradation
│       ├── cli.py               # CLI tool (steerplane command)         ← NEW
│       ├── config_file.py       # .steerplane.yml auto-discovery       ← NEW
│       ├── runtime_context.py   # Active run tracking for signal handling
│       ├── telemetry.py         # Step event collection
│       ├── exceptions.py        # 6 typed exception classes
│       └── integrations/
│           ├── langchain.py     # LangChain/LangGraph callback handler
│           ├── openai_agents.py # OpenAI Agents SDK hooks              ← NEW
│           ├── crewai.py        # CrewAI step/task callbacks            ← NEW
│           └── autogen.py       # AutoGen reply hooks                   ← NEW
├── sdk-ts/                      # TypeScript SDK (npm install steerplane)
│   └── src/
│       ├── guard.ts             # guard() HOF + SteerPlane class
│       ├── run-manager.ts       # Run lifecycle + dual enforcement
│       ├── cost-tracker.ts      # Cost tracking + limits
│       ├── loop-detector.ts     # Loop detection
│       ├── policy-engine.ts     # Policy engine + glob matching
│       ├── client.ts            # HTTP client (native fetch)
│       └── errors.ts            # 7 typed error classes
├── api/                         # FastAPI backend
│   ├── Dockerfile               # Production container                  ← NEW
│   ├── alembic.ini              # Migration config                      ← NEW
│   ├── alembic/                 # Versioned database migrations         ← NEW
│   └── app/
│       ├── main.py              # App entry point + CORS + startup
│       ├── security.py          # Admin token auth middleware
│       ├── routes/
│       │   ├── runs.py          # Run lifecycle endpoints
│       │   ├── policies.py      # Policy CRUD + evaluation
│       │   ├── approvals.py     # Approval create/approve/deny/list
│       │   ├── gateway.py       # Streaming proxy + mid-stream kill     ← UPDATED
│       │   ├── api_keys.py      # API key management with enforcement
│       │   └── telemetry.py     # Batch telemetry ingestion
│       ├── models/              # Run, Step, Policy, APIKey, Approval
│       └── services/
│           ├── run_service.py
│           ├── policy_service.py
│           ├── gateway_service.py   # 25 model pricing
│           ├── approval_service.py
│           └── notification_service.py
├── dashboard/                   # Next.js real-time dashboard
│   ├── Dockerfile               # Multi-stage production build          ← NEW
│   └── src/
│       └── app/
│           ├── dashboard/       # Run list + run detail pages
│           ├── policies/        # Policy management UI
│           ├── approvals/       # Approve/deny/extend pending requests
│           └── api-keys/        # API key management
├── docker-compose.yml           # 4-service orchestration               ← NEW
├── .env.example                 # All env vars documented               ← NEW
├── .github/workflows/ci.yml    # CI/CD pipeline                         ← NEW
└── examples/                    # Example agent integrations
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

**Gateway Proxy**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/gateway/v1/chat/completions` | OpenAI-compatible proxy (streaming + non-streaming) |
| `GET` | `/gateway/v1/models` | List available models |

**Policies · Approvals · API Keys · Telemetry · Health**  
See full API docs at `http://localhost:8000/docs`

---

## Supported Models (25+)

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-Turbo, GPT-4, GPT-3.5-Turbo, o1, o1-mini, o3-mini |
| **Anthropic** | Claude 4 Opus/Sonnet, Claude 3.5 Sonnet/Haiku, Claude 3 Opus/Sonnet/Haiku |
| **Google** | Gemini 2.0 Flash, Gemini 1.5 Pro/Flash, Gemini Pro |
| **Meta** | Llama 3 70B, Llama 3 8B |
| **Mistral** | Mistral Large, Mistral Small |

---

## Roadmap

- [x] Python SDK with `@guard` decorator and context manager API
- [x] TypeScript SDK with `guard()` HOF and class API
- [x] Cost tracking with built-in pricing for 25+ models (5 providers)
- [x] O(W²) sliding-window infinite loop detection
- [x] Policy engine — allow/deny lists, rate limits, approval workflows
- [x] Real-time Next.js dashboard
- [x] Dual enforcement — kill mode + alert mode
- [x] Human-in-the-loop approval workflow
- [x] OpenAI-compatible gateway proxy
- [x] LangChain/LangGraph callback handler integration
- [x] API key management with per-key enforcement config
- [x] Notification dispatch — SMTP email + HTTP webhooks
- [x] Graceful offline degradation
- [x] **SSE streaming in gateway with mid-stream cost kill** ← v0.4.0
- [x] **Docker Compose (API + Dashboard + PostgreSQL + Redis)** ← v0.4.0
- [x] **PostgreSQL support + Alembic migrations** ← v0.4.0
- [x] **GitHub Actions CI/CD pipeline** ← v0.4.0
- [x] **CLI tool (`steerplane runs`, `steerplane keys`, `steerplane status`)** ← v0.4.0
- [x] **Config file support (`.steerplane.yml`)** ← v0.4.0
- [x] **OpenAI Agents SDK integration** ← v0.4.0
- [x] **CrewAI integration** ← v0.4.0
- [x] **AutoGen integration** ← v0.4.0
- [ ] WebSocket real-time dashboard (replace polling)
- [ ] Webhook event system
- [ ] Recommendation engine (auto-suggest limits)
- [ ] Agent replay (flight recorder)
- [ ] Cost projection (live burn rate widget)
- [ ] Anomaly detection (deterministic thresholds)
- [ ] OpenTelemetry export
- [ ] Fleet monitoring dashboard
- [ ] Policy-as-code (GitOps YAML)
- [ ] Slack app with interactive approval buttons
- [ ] Multi-tenant RBAC
- [ ] Cloud-hosted SaaS

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane

# Option A: Docker
cp .env.example .env && docker compose up -d

# Option B: Manual
cd api && pip install -r requirements.txt
cd dashboard && npm install
cd sdk && pip install -e ".[dev,cli,yaml]"

# Run tests
cd sdk && pytest tests/
cd api && pytest tests/
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <img src="assets/logo.jpg" alt="SteerPlane" width="48" /><br>
  <b>SteerPlane v0.4.1</b><br>
  <a href="https://steerplane.com">steerplane.com</a> · <a href="PATENTS.md">Patent Pending — IN 202641071111 A1</a><br>
  <em>"Ship agents. Not incidents."</em>
</p>
