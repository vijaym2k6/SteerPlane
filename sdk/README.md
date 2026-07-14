# SteerPlane SDK

**Runtime guardrails for autonomous AI agents.**

> Cost limits · Loop detection · Dual enforcement (Kill/Alert) · SSE streaming gateway · Policy engine · Human-in-the-loop · CLI · Docker · 4 framework integrations

[![PyPI](https://img.shields.io/pypi/v/steerplane?style=flat-square&color=3B82F6&label=PyPI)](https://pypi.org/project/steerplane/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)

## Install

```bash
pip install steerplane            # Core SDK
pip install steerplane[cli]       # + CLI tool
pip install steerplane[all]       # + CLI + YAML config + LangChain
```

## Quick Start

### Option 1: Gateway Mode (Zero Code Changes)

Point your existing OpenAI client to SteerPlane. Every LLM call is automatically monitored, rate-limited, and cost-tracked — including SSE streaming with mid-stream cost enforcement.

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="sk_sp_...",  # SteerPlane API key
    default_headers={"X-LLM-API-Key": "sk-..."}
)

# All calls — including stream=True — are now guarded.
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True  # SSE streaming with real-time cost tracking
)
```

### Option 2: Decorator Mode

```python
from steerplane import guard

@guard(
    agent_name="support_bot",
    max_cost_usd=10.00,
    max_steps=50,
    denied_actions=["DROP TABLE*", "rm -rf *"],
    rate_limits=[{"pattern": "send_email", "max_count": 5, "window_seconds": 60}],
    require_approval=["execute_trade*"]
)
def run_agent():
    agent.run()
```

### Option 3: Context Manager

```python
from steerplane import SteerPlane

sp = SteerPlane(agent_id="my_bot")

with sp.run(max_cost_usd=10.0, max_steps=50) as run:
    run.log_step("query_db", tokens=380, cost=0.002, latency_ms=45)
    run.log_step("generate_response", tokens=1240, cost=0.008, latency_ms=320)
```

## What's New in v0.4.0

### 🌊 SSE Streaming Gateway
The AI Gateway now supports Server-Sent Events (SSE) streaming. It accumulates token costs per chunk in real time and can **terminate a stream mid-response** by injecting a `steerplane_enforcement` event when the cost ceiling is breached — without corrupting the SSE protocol.

### 🖥️ CLI Tool
```bash
steerplane status              # Check API health
steerplane runs list           # List recent runs
steerplane runs inspect <id>   # Inspect a run
steerplane runs kill <id>      # Kill a running agent
steerplane keys list           # List API keys
steerplane keys create         # Create new gateway key
steerplane logs --tail         # Live log stream
```

### 🐳 Docker Compose
Full 3-service production stack in one command:
```bash
docker compose up -d
# API (8000) + Dashboard (3000) + PostgreSQL (5432)
```

### 📄 Config File (.steerplane.yml)
Project-level defaults auto-discovered from your working directory:
```yaml
api_url: http://localhost:8000
agent_name: my_bot
max_cost_usd: 10.0
max_steps: 100
detect_loops: true
```

### 🔌 Framework Integrations

Native support for 4 frameworks — all use lazy imports, so framework dependencies are only required when used:

**LangChain:**
```python
from steerplane.integrations import SteerPlaneLangChainHandler
handler = SteerPlaneLangChainHandler(agent_name="lc_bot", max_cost_usd=5.0)
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])
```

**OpenAI Agents SDK:**
```python
from steerplane.integrations import SteerPlaneAgentHooks
hooks = SteerPlaneAgentHooks(agent_name="openai_agent", max_cost_usd=10.0)
```

**CrewAI:**
```python
from steerplane.integrations import SteerPlaneCrewMonitor
monitor = SteerPlaneCrewMonitor(agent_name="crew_bot", max_cost_usd=15.0)
```

**AutoGen:**
```python
from steerplane.integrations import SteerPlaneAutoGenMonitor
monitor = SteerPlaneAutoGenMonitor(agent_name="autogen_bot", max_cost_usd=10.0)
```

## All Features

| Feature | Description |
|---------|-------------|
| 🌉 **AI Gateway Proxy** | OpenAI-compatible proxy. Point your client, get instant monitoring. |
| 🌊 **SSE Streaming** | Real-time chunk forwarding with mid-stream cost enforcement. |
| 🛡️ **Policy Engine** | Allow/deny rules, sliding-window rate limits, human-approval callbacks. |
| 🔄 **Loop Detection** | Sliding-window pattern detector catches infinite agent loops. |
| 💰 **Hard Cost Ceiling** | Per-run and monthly USD limits across 25+ LLM models. |
| 🚫 **Step Limits** | Cap maximum execution steps. |
| 📊 **Deep Telemetry** | Tokens, cost, latency per step — synced to the dashboard. |
| 🛡️ **Graceful Degradation** | API down? SDK still enforces guards locally. |
| 🖥️ **CLI Tool** | `steerplane status`, `runs`, `keys`, `logs` from terminal. |
| 🐳 **Docker Compose** | 3-service production stack in one command. |
| 📄 **Config File** | `.steerplane.yml` for project-level defaults. |
| 🔌 **4 Integrations** | LangChain, OpenAI Agents SDK, CrewAI, AutoGen. |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────────┐
│  AI Agent   │────▶│ SteerPlane   │────▶│  FastAPI    │────▶│  PostgreSQL   │
│  (Your App) │     │  SDK / GW    │     │  Server     │     │  Database     │
└─────────────┘     └──────────────┘     └────────────┘     └───────────────┘
                                                │
                                                ▼
                                         ┌───────────────┐
                                         │   Next.js     │
                                         │   Dashboard   │
                                         └───────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Python SDK | Python 3.10+, Decorator/Context Manager API, CLI, Config files |
| TypeScript SDK | TypeScript, `guard()` wrapper, npm-ready |
| Gateway | FastAPI + httpx, SSE streaming, 25+ model pricing |
| API | FastAPI, Alembic migrations, OpenAPI docs |
| Database | PostgreSQL 17 + SQLAlchemy ORM |
| Infrastructure | Docker Compose (API + Dashboard + PostgreSQL) |
| CI/CD | GitHub Actions (lint, test, Docker build) |
| Dashboard | Next.js 16, React 19, Framer Motion |

## Links

- **GitHub**: [github.com/vijaym2k6/SteerPlane](https://github.com/vijaym2k6/SteerPlane)
- **npm**: [npmjs.com/package/steerplane](https://www.npmjs.com/package/steerplane)
- **Dashboard**: `http://localhost:3000`
- **API Docs**: `http://localhost:8000/docs`

## License

MIT — [Patent Pending](https://github.com/vijaym2k6/SteerPlane)
