# Architecture

## System Overview

SteerPlane uses a clean **4-tier architecture** where each component has a single responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR APPLICATION                        │
│                                                                │
│   ┌─────────┐    ┌──────────────────────────────────────┐      │
│   │   AI    │───▶│         SteerPlane SDK               │      │
│   │  Agent  │    │                                      │      │
│   └─────────┘    │  ┌────────────┐  ┌──────────────┐   │      │
│                  │  │   Guard    │  │    Cost      │   │      │
│                  │  │  Engine    │  │   Tracker    │   │      │
│                  │  └────────────┘  └──────────────┘   │      │
│                  │  ┌────────────┐  ┌──────────────┐   │      │
│                  │  │   Loop     │  │  Telemetry   │   │      │
│                  │  │  Detector  │  │   Client     │   │      │
│                  │  └────────────┘  └──────────────┘   │      │
│                  └─────────────┬────────────────────────┘      │
│                               │                                │
└───────────────────────────────┼────────────────────────────────┘
                                │ HTTP (REST)
                                ▼
                   ┌────────────────────────┐
                   │     FastAPI Server     │
                   │                        │
                   │  ┌──────┐ ┌────────┐   │
                   │  │Routes│ │Services│   │
                   │  └──┬───┘ └───┬────┘   │
                   │     │         │        │
                   │  ┌──▼─────────▼──┐     │
                   │  │  SQLAlchemy   │     │
                   │  │    ORM        │     │
                   │  └───────┬───────┘     │
                   └──────────┼─────────────┘
                              │
                              ▼
                   ┌────────────────────────┐
                   │     PostgreSQL 17      │
                   │                        │
                   │  ┌──────┐ ┌──────┐     │
                   │  │ runs │ │steps │     │
                   │  └──────┘ └──────┘     │
                   │  ┌──────┐              │
                   │  │agents│              │
                   │  └──────┘              │
                   └────────────────────────┘
                              ▲
                              │ SQL Queries
                              │
                   ┌────────────────────────┐
                   │   Next.js Dashboard    │
                   │                        │
                   │  ┌───────┐ ┌────────┐  │
                   │  │Landing│ │  Run   │  │
                   │  │ Page  │ │ Table  │  │
                   │  └───────┘ └────────┘  │
                   │  ┌───────┐ ┌────────┐  │
                   │  │ Step  │ │ Cost   │  │
                   │  │Timelin│ │ Badge  │  │
                   │  └───────┘ └────────┘  │
                   └────────────────────────┘
```

## Data Flow

### 1. Agent Execution

```
Agent calls @guard decorated function
    → Guard wraps execution in RunManager
    → RunManager creates a new run via API
    → Each step is intercepted:
        → CostTracker checks cumulative cost
        → LoopDetector checks for patterns
        → Telemetry logs the step via API
    → On completion/failure, run status is updated
```

### 2. Step Interception

```
Agent performs action
    → SDK logs: action_name, tokens, cost, latency
    → Cost tracker: cumulative_cost += step_cost
        → If cumulative_cost > max_cost → raise CostLimitExceeded
    → Loop detector: add action to window
        → If pattern repeats → raise LoopDetected
    → Step counter: steps += 1
        → If steps > max_steps → raise StepLimitExceeded
    → Telemetry: POST /runs/{id}/steps
```

### 3. Dashboard Rendering

```
Browser loads dashboard
    → Next.js fetches GET /runs from API
    → Renders RunTable with status badges
    → User clicks a run → fetches GET /runs/{id}
    → Renders StepTimeline with per-step metrics
    → Auto-refresh polls every 5 seconds
```

## Database Schema

### `runs` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | VARCHAR | Agent identifier |
| `status` | ENUM | running, completed, failed, cost_exceeded, loop_detected |
| `total_cost` | FLOAT | Cumulative cost in USD |
| `total_tokens` | INT | Cumulative token count |
| `total_steps` | INT | Number of steps executed |
| `max_cost_usd` | FLOAT | Cost limit for this run |
| `max_steps` | INT | Step limit for this run |
| `error` | TEXT | Error message if failed |
| `started_at` | TIMESTAMP | Run start time |
| `ended_at` | TIMESTAMP | Run end time |

### `steps` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | Foreign key → runs |
| `action` | VARCHAR | Action name |
| `tokens` | INT | Tokens used |
| `cost` | FLOAT | Step cost in USD |
| `latency_ms` | INT | Execution time |
| `status` | VARCHAR | Step status |
| `created_at` | TIMESTAMP | Step timestamp |

## Technology Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| **SDK** | Python 3.10+ | Most AI agents are written in Python |
| **API** | FastAPI | Auto-generated OpenAPI docs, async support, Pydantic validation |
| **ORM** | SQLAlchemy | Battle-tested, supports PostgreSQL + SQLite |
| **Database** | PostgreSQL 17 | Reliable, scalable, JSON support for future metadata |
| **Dashboard** | Next.js 16 | React ecosystem, server components, fast dev experience |
| **Animations** | Framer Motion | Production-grade animation library for React |
| **Styling** | Vanilla CSS | Maximum control, no framework lock-in |
