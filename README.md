<p align="center">
  <h1 align="center">SteerPlane</h1>
  <p align="center"><strong>Runtime Control Plane for Autonomous AI Agents</strong></p>
  <p align="center"><em>"Ship agents. Not incidents."</em></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/node-18+-green" alt="Node">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome">
</p>

SteerPlane is an open-source runtime layer that sits between your AI agents and the outside world. It intercepts every action, enforces safety policies, detects infinite loops, tracks token costs, and gives you complete observability — without modifying agent code.

```
🚀 SteerPlane | Run Started
   Run ID:  a3f8d2b1-...
   Agent:   support_bot
   Limits:  $10.00 cost / 50 steps
   ─────────────────────────────────────────────
   ✅ Step 1: query_database     | 380 tokens | $0.0020 | 45ms
   ✅ Step 2: call_llm_analyze   | 1240 tokens | $0.0080 | 320ms
   ✅ Step 3: search_knowledge   | 560 tokens | $0.0030 | 89ms
   ✅ Step 4: generate_response  | 1800 tokens | $0.0120 | 450ms
   ✅ Step 5: send_notification  | 120 tokens | $0.0010 | 200ms
   ─────────────────────────────────────────────

✅ SteerPlane | Run COMPLETED
   Steps:      5
   Cost:       $0.0260
   Tokens:     4,100
   Duration:   1.1s
```

---


## 🎯 Why SteerPlane?

Autonomous AI agents can call APIs, execute code, browse the web, and make real-world decisions. But without guardrails:

- A single misconfigured agent can **enter an infinite loop**
- A runaway agent can **burn through $10,000+ in API credits overnight**
- Agents can take **unintended destructive actions** with zero visibility

SteerPlane solves this with a **single decorator**.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Loop Detection** | Sliding-window pattern detector catches repeating agent behavior in real time |
| 💰 **Cost Limits** | Hard USD ceiling per run — terminate instantly when exceeded |
| 🚫 **Step Limits** | Cap maximum execution steps to prevent unbounded runs |
| 📊 **Full Telemetry** | Every step's action, tokens, cost, latency, and status — captured automatically |
| 🖥️ **Real-Time Dashboard** | Next.js dashboard with auto-refresh, visual timelines, and cost breakdowns |
| 🛡️ **Graceful Degradation** | If the API goes down, the SDK enforces limits locally |

## 🚀 Quick Start (5 Minutes)

### 1. Install the SDK

**Python:**
```bash
pip install steerplane
```

**TypeScript / Node.js:**
```bash
npm install steerplane
```

### 2. Wrap Your Agent

```python
from steerplane import guard

@guard(
    agent_name="support_bot",
    max_cost_usd=10.00,
    max_steps=50,
    detect_loops=True
)
def run_agent():
    # Your agent code runs normally
    # SteerPlane monitors every step silently
    agent.run()
```

### 3. Start the API Server

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### 5. Run the Demo

```bash
python examples/simple_agent/agent_example.py
```

### 6. View Results

Open [http://localhost:3000](http://localhost:3000) to see your agent runs in the dashboard.

## 🏗️ Architecture

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

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **SDK** | Python 3.10+ | `@guard` decorator, cost tracking, loop detection |
| **API** | FastAPI | REST API, SQLAlchemy ORM, auto-generated docs |
| **Database** | PostgreSQL 17 | Persistent storage for runs, steps, agents |
| **Dashboard** | Next.js 16 | Real-time monitoring with Framer Motion animations |

## 📦 Project Structure

```
SteerPlane/
├── sdk/                    # Python SDK
│   └── steerplane/
│       ├── guard.py        # @guard decorator
│       ├── run_manager.py  # Run lifecycle management
│       ├── cost_tracker.py # Cost limit enforcement
│       ├── loop_detector.py# Infinite loop detection
│       ├── telemetry.py    # Step-by-step telemetry
│       └── client.py       # HTTP client for API
├── api/                    # FastAPI backend
│   └── app/
│       ├── main.py         # App entry point
│       ├── routes/         # API endpoints
│       ├── models/         # SQLAlchemy models
│       ├── schemas/        # Pydantic schemas
│       └── services/       # Business logic
├── dashboard/              # Next.js dashboard
│   └── src/
│       ├── app/            # Pages (landing, dashboard, run detail)
│       └── components/     # React components
├── examples/               # Example integrations
│   ├── simple_agent/       # Basic demo agent
│   ├── simple_llm_agent/   # Single LLM call
│   ├── openai_agent/       # OpenAI with tool use
│   └── langgraph_agent/    # LangGraph workflow
├── docs/                   # Documentation
├── scripts/                # Setup scripts
├── CONTRIBUTING.md         # Contributor guide
├── LICENSE                 # MIT License
└── README.md               # This file
```

## 💻 SDK Usage

### Decorator API (Simplest)

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

with sp.run(max_cost_usd=10.0) as run:
    run.log_step("query_db", tokens=380, cost=0.002, latency_ms=45)
    run.log_step("generate_response", tokens=1240, cost=0.008, latency_ms=320)
```

### Exception Handling

```python
from steerplane.exceptions import CostLimitExceeded, LoopDetected

@guard(max_cost_usd=5, detect_loops=True)
def run_agent():
    try:
        agent.run()
    except CostLimitExceeded:
        print("Agent exceeded budget!")
    except LoopDetected:
        print("Agent stuck in a loop!")
```

## 📚 Documentation

| Page | Description |
|------|-------------|
| [Getting Started](docs/getting-started.md) | 5-minute quickstart |
| [Installation](docs/installation.md) | Detailed setup guide |
| [SDK Usage](docs/sdk-usage.md) | Complete API reference |
| [Example Agents](docs/example-agents.md) | Integration examples |
| [Dashboard Guide](docs/dashboard-guide.md) | Dashboard usage |
| [Architecture](docs/architecture.md) | System design |

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>SteerPlane</strong> — Runtime guardrails for AI agents<br>
  <em>"Agents don't fail in the dark anymore."</em>
</p>
