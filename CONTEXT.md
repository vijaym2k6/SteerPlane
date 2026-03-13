# SteerPlane — Full Project Context

> **Purpose of this document:** Give any contributor (human or AI) complete context about what SteerPlane is, what's been built, how it works, and what to build next. Paste this into your AI coding assistant to get started.

---

## 1. What is SteerPlane?

SteerPlane is an **open-source runtime control plane for AI agents**. It sits between your agent code and the LLMs/tools it calls, enforcing guardrails in real-time.

**One-liner:** "One decorator. Full control over your AI agents."

### The Problem

AI agents run autonomously — calling LLMs, invoking tools, querying databases. Without runtime controls:
- A single agent can burn **$50+ in minutes** through unchecked API calls
- Agents get stuck in **infinite loops** repeating the same actions
- Agents can call **dangerous actions** (delete data, send emails, make payments) without oversight
- There's **zero visibility** into what agents are doing until it's too late

### The Solution

SteerPlane provides runtime guardrails that **prevent** bad outcomes, not just report them:

```python
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50)
def run_agent():
    agent.run()
```

That single decorator gives you: cost limits, step limits, loop detection, runtime limits, and full telemetry — all enforced at runtime.

### Why SteerPlane is Different from Competitors

| Tool | What It Does | SteerPlane Difference |
|------|-------------|----------------------|
| **LangSmith** | Traces + debugs agent runs AFTER they happen | SteerPlane **prevents** bad runs in real-time |
| **Langfuse** | Open-source LLM observability | SteerPlane adds **enforcement** (policy, kill switch) not just observation |
| **AgentOps** | Agent monitoring + replay | SteerPlane **blocks** actions, not just monitors them |
| **Guardrails AI** | Validates LLM input/output format | SteerPlane controls the **agent runtime**, not just I/O validation |

**Analogy:** LangSmith is a **security camera** (shows you what happened). SteerPlane is a **lock** (prevents it from happening).

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Developer's Code                      │
│                                                         │
│   @guard(max_cost_usd=10, max_steps=50)                │
│   def run_agent():                                      │
│       agent.run()                                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Python SDK (sdk/)                       │
│                                                         │
│   guard.py ──→ run_manager.py ──→ cost_tracker.py      │
│                      │          ──→ loop_detector.py     │
│                      │          ──→ telemetry.py         │
│                      │          ──→ [NEW] policy.py      │
│                      ▼                                   │
│               client.py (HTTP)                           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (POST /runs/start, /runs/step, /runs/end)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Backend (api/)                     │
│                                                         │
│   routes/runs.py ──→ services/run_service.py            │
│                  ──→ models/run.py, step.py              │
│                  ──→ SQLite (steerplane.db)               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API (GET /runs, GET /runs/:id)
                       ▼
┌─────────────────────────────────────────────────────────┐
│             Next.js Dashboard (dashboard/)               │
│                                                         │
│   RunTable ──→ StepTimeline ──→ CostBadge              │
│   StatusBadge ──→ Navbar                                │
│                                                         │
│   Fetches from FastAPI, displays runs + steps           │
└─────────────────────────────────────────────────────────┘
```

There's also a **TypeScript SDK** (`sdk-ts/`) published on npm — it mirrors the Python SDK's API but is less complete.

---

## 3. Complete File Map

### Python SDK (`sdk/steerplane/`)

| File | Purpose | Lines |
|------|---------|-------|
| `__init__.py` | Public API exports — `guard`, `SteerPlane`, `RunManager`, all exceptions | 70 |
| `guard.py` | `@guard` decorator + `SteerPlane` class (context manager API) | 180 |
| `run_manager.py` | **Core orchestrator** — manages full run lifecycle: start → log_step → guard checks → end | 267 |
| `cost_tracker.py` | Token counting, cost calculation using model pricing table, cost limit enforcement | 172 |
| `loop_detector.py` | Sliding window algorithm to detect repeating action patterns like [A,B,A,B,A,B] | 125 |
| `telemetry.py` | `StepEvent` dataclass, `TelemetryCollector` for event creation and storage | 114 |
| `client.py` | HTTP client that sends telemetry to FastAPI backend — gracefully degrades if API is offline | 130 |
| `config.py` | `SteerPlaneConfig` with env var overrides (`STEERPLANE_API_URL`, `STEERPLANE_API_KEY`) | 50 |
| `exceptions.py` | All custom exceptions: `LoopDetectedError`, `CostLimitExceeded`, `StepLimitExceeded`, `RunTerminatedError`, `APIConnectionError` | 69 |
| `utils.py` | ID generators (`generate_run_id`, `generate_step_id`), formatters (`format_cost`, `format_duration`) | ~50 |

### FastAPI Backend (`api/app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with CORS, routes registration |
| `config.py` | Database URL config |
| `routes/runs.py` | REST endpoints: `POST /runs/start`, `POST /runs/step`, `POST /runs/end`, `GET /runs`, `GET /runs/{id}` |
| `routes/telemetry.py` | Telemetry ingestion endpoint |
| `services/run_service.py` | Business logic — create run, log step, end run, list runs |
| `models/run.py` | SQLAlchemy model: `Run` (id, agent_name, status, start_time, end_time, total_cost, total_steps, total_tokens, max_cost_usd, max_steps_limit, error) |
| `models/step.py` | SQLAlchemy model: `Step` (id, run_id, step_number, action, tokens, cost_usd, latency_ms, status, error, metadata_json, timestamp) |
| `db/__init__.py` | SQLAlchemy engine, session factory, Base |

### Dashboard (`dashboard/`)

| File | Purpose |
|------|---------|
| `src/app/page.tsx` | Home page — shows RunTable |
| `src/app/runs/[id]/page.tsx` | Run detail page — shows StepTimeline |
| `src/components/RunTable.tsx` | Table of all runs with status, cost, steps, duration |
| `src/components/StepTimeline.tsx` | Timeline visualization of each step in a run |
| `src/components/StatusBadge.tsx` | Color-coded badge (running=blue, completed=green, failed=red, terminated=orange) |
| `src/components/CostBadge.tsx` | Cost display with color-coding based on threshold |
| `src/components/Navbar.tsx` | Top navigation bar |
| `src/services/api.ts` | Axios client for fetching data from FastAPI |

### TypeScript SDK (`sdk-ts/`)

Mirrors the Python SDK. Published on npm as `steerplane`. Less feature-complete than Python SDK.

---

## 4. How it Works — Code Flow

### When a developer runs a guarded agent:

```python
@guard(max_cost_usd=10, max_steps=50)
def run_my_agent():
    # Inside the agent loop, each step logs to SteerPlane:
    run = get_active_run()
    run.log_step("search_web", tokens=500, cost=0.002)
    run.log_step("call_llm", tokens=1200, cost=0.008)
    run.log_step("search_web", tokens=500, cost=0.002)  # loop detection watches this
```

### Step-by-step execution flow:

1. `@guard(...)` creates a `RunManager` with configured limits
2. `RunManager.start()` → sets status to "running", sends `POST /runs/start` to API
3. Each `run.log_step(action, tokens, cost)`:
   - Checks if run was terminated (`_terminated` flag)
   - Checks step limit (`step_number > max_steps` → raises `StepLimitExceeded`)
   - Checks runtime limit (`elapsed > max_runtime_sec` → raises `RunTerminatedError`)
   - Calculates cost via `CostTracker.calculate_step_cost()` using model pricing table
   - Creates `StepEvent` via `TelemetryCollector`
   - Sends step to API via `SteerPlaneClient.log_step()`
   - Adds cost to tracker — if total exceeds limit → raises `CostLimitExceeded`
   - Feeds action to `LoopDetector.record_action()` — if pattern detected → raises `LoopDetectedError`
4. `RunManager.end()` → sends final status to API, prints summary

### Key design choices:
- **SDK works offline** — if API is unreachable, guards still enforce locally (cost/step/loop limits work without the server)
- **Exceptions terminate the run** — when a limit is hit, an exception is raised. The developer can catch it or let it propagate
- **Global `_active_run`** — thread-local storage so code inside the guarded function can access the run via `get_active_run()`

---

## 5. How to Run the Project

### Backend API
```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Runs on `http://localhost:8000`
- SQLite database at `steerplane.db` (auto-created)
- API docs at `http://localhost:8000/docs`

### Dashboard
```bash
cd dashboard
npm install
npm run dev
```
- Runs on `http://localhost:3000`
- Fetches data from `http://localhost:8000`

### Python SDK (local dev)
```bash
cd sdk
pip install -e .
```

### Run an example
```bash
cd examples/simple_agent
python agent_example.py
```

---

## 6. What Needs to Be Built — Priority Order

### 🔴 PRIORITY 1: Policy Engine (THIS IS THE MOST IMPORTANT FEATURE)

**Why:** This is what makes SteerPlane more than "another monitoring tool." The policy engine controls WHAT agents are ALLOWED to do. No competitor has this.

**What to build:**

Create `sdk/steerplane/policy.py` with:

```python
class Policy:
    """
    Declarative policy engine for controlling agent actions.
    
    Modes:
    1. Deny list: Block specific dangerous actions
    2. Allow list: Only permit explicitly approved actions (whitelist)
    3. Both: Allow list takes precedence, deny list as fallback
    """
    
    def __init__(
        self,
        deny: list[str] | None = None,      # Actions to block
        allow: list[str] | None = None,      # Only these allowed (whitelist mode)
        require_approval: list[str] | None = None,  # Actions needing human approval
        rate_limits: dict[str, int] | None = None,   # Max calls per action per run
    ):
        ...
    
    def check(self, action: str) -> PolicyDecision:
        """
        Check if an action is allowed.
        Returns: PolicyDecision(allowed=True/False, reason="...")
        Raises: ActionDenied if action is blocked
        """
        ...
```

Create `ActionDenied` exception in `exceptions.py`:
```python
class ActionDenied(SteerPlaneError):
    """Raised when a policy blocks an agent action."""
    def __init__(self, action: str, reason: str):
        self.action = action
        self.reason = reason
        super().__init__(f"🚫 Action '{action}' denied by policy: {reason}")
```

**Wire it into `run_manager.py`:**
- Add `policy` parameter to `RunManager.__init__()`
- In `log_step()`, BEFORE any other checks, call `self.policy.check(action)` 
- If denied → raise `ActionDenied`, terminate run

**Wire it into `guard.py`:**
- Add `policy` parameter to `@guard()` decorator
- Pass it through to `RunManager`

**Target API:**
```python
@guard(
    max_cost_usd=10,
    max_steps=50,
    policy={
        "deny": ["delete_user", "drop_table", "send_money"],
        "allow": ["search", "read_db", "generate_text"],
        "rate_limits": {"send_email": 5}  # max 5 emails per run
    }
)
def run_agent():
    agent.run()
```

**Also add to the API backend:**
- Store policy violations in the database (new `PolicyViolation` model or add to Step model)
- `GET /runs/{id}` should return policy violations
- Dashboard should show red "BLOCKED" badges for denied actions

---

### 🟡 PRIORITY 2: Remote Kill Switch

**Why:** Right now, if an agent is running on a server and goes rogue, you can't stop it remotely. You need a "STOP" button in the dashboard.

**What to build:**

**API side:**
- New endpoint: `POST /runs/{run_id}/kill` — sets a `kill_requested` flag on the run in the database
- New endpoint: `GET /runs/{run_id}/status` — returns current status including kill flag (lightweight polling endpoint)

**SDK side:**
- In `RunManager.log_step()`, periodically (every N steps, like every 5) call `GET /runs/{run_id}/status` to check if kill was requested
- If kill requested → raise `RunTerminatedError("Remote kill requested")`
- Add `check_interval` parameter (default: check every 5 steps)

**Dashboard side:**
- Add red "Kill" button next to each running run in `RunTable.tsx`
- Button calls `POST /runs/{run_id}/kill`
- Show "Kill requested" status while waiting for agent to stop

---

### 🟢 PRIORITY 3: Framework Auto-Instrumentation

**Why:** Currently developers must manually call `run.log_step()`. With auto-instrumentation, SteerPlane automatically captures every LLM call.

**What to build:**

**LangChain integration** (`sdk/steerplane/integrations/langchain.py`):
```python
from steerplane.integrations.langchain import SteerPlaneCallbackHandler

handler = SteerPlaneCallbackHandler(max_cost_usd=10)
agent = create_agent(callbacks=[handler])
agent.run("do something")
# SteerPlane automatically logs every LLM call, tool use, chain step
```

**OpenAI integration** (`sdk/steerplane/integrations/openai.py`):
```python
from steerplane.integrations.openai import patch_openai
patch_openai(max_cost_usd=10)
# Now every openai.chat.completions.create() call is automatically tracked
```

---

### 🔵 PRIORITY 4: Authentication & Multi-Tenant

**Why:** Needed before deploying as a cloud service. Multiple users, API keys, data isolation.

**What to build:**
- API key generation + validation middleware
- User model + org/team support
- Runs scoped to authenticated user
- Dashboard login page

---

### ⚪ PRIORITY 5: Alerts & Notifications

**Why:** Proactive alerting when agents misbehave.

**What to build:**
- Slack webhook integration (on cost exceeded, loop detected, policy violation)
- Discord webhook integration
- Email alerts (via SendGrid or similar)
- Configurable alert rules

---

## 7. Coding Conventions

- **Python SDK:** Python 3.11+, type hints everywhere, dataclasses for data, no external deps except `requests`
- **API:** FastAPI + SQLAlchemy + SQLite (will migrate to PostgreSQL for production)
- **Dashboard:** Next.js 14 App Router, TypeScript, Tailwind CSS
- **TypeScript SDK:** Mirrors Python SDK's API shape
- **Error handling:** Custom exceptions with emoji prefixes for console readability
- **Naming:** snake_case for Python, camelCase for TypeScript, PascalCase for React components
- **Testing:** Not yet implemented — tests needed for policy engine, loop detector, cost tracker
- **Git:** Main branch, conventional commits

---

## 8. Current State (as of March 12, 2026)

### What's working:
- ✅ Python SDK on PyPI (`pip install steerplane`)
- ✅ TypeScript SDK on npm (`npm install steerplane`)
- ✅ `@guard` decorator with cost limits, step limits, runtime limits
- ✅ Loop detection (sliding window algorithm)
- ✅ FastAPI backend with SQLite storage
- ✅ Next.js dashboard showing runs + step timelines
- ✅ SDK works offline (guards enforce locally even without API)
- ✅ Example agent code in `examples/`

### What's NOT built yet:
- ❌ Policy engine (allow/deny actions) ← BUILD THIS NEXT
- ❌ Remote kill switch
- ❌ Framework integrations (LangChain, OpenAI, CrewAI)
- ❌ Authentication / API keys
- ❌ Alerts (Slack, Discord, email)
- ❌ Unit tests
- ❌ Cloud deployment
- ❌ Audit logs
- ❌ Human-in-the-loop approval workflows

---

## 9. Published / Live Links

- **GitHub:** https://github.com/vijaym2k6/SteerPlane
- **PyPI:** https://pypi.org/project/steerplane/
- **npm:** https://www.npmjs.com/package/steerplane
- **Dev.to article:** Published (has engagement)
- **Hacker News:** Posted
- **Hashnode:** Published

---

## 10. Key Design Principles

1. **One line to start** — `@guard(max_cost_usd=10)` should be all you need
2. **Guards work offline** — SDK enforces limits locally even if API is down
3. **Prevention over observation** — We STOP bad things, not just log them
4. **Framework agnostic** — Works with any agent framework, not locked to LangChain or OpenAI
5. **Open source first** — Core SDK and API are fully open source. Cloud offering comes later with premium features (team management, SSO, advanced analytics)

---

## 11. For Contributors: Getting Started

1. Clone the repo: `git clone https://github.com/vijaym2k6/SteerPlane.git`
2. Start the API: `cd api && pip install -r requirements.txt && uvicorn app.main:app --reload`
3. Start the dashboard: `cd dashboard && npm install && npm run dev`
4. Install SDK in dev mode: `cd sdk && pip install -e .`
5. Run an example: `cd examples/simple_agent && python agent_example.py`

**The #1 thing to build right now is the Policy Engine.** See Priority 1 above for exact specs.
