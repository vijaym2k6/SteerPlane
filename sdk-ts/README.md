# SteerPlane — TypeScript SDK

**Runtime guardrails for autonomous AI agents.**

> Cost limits · Loop detection · Dual enforcement (Kill/Alert) · SSE streaming gateway · Policy engine · Human-in-the-loop · Zero dependencies

[![npm](https://img.shields.io/npm/v/steerplane?style=flat-square&color=3B82F6&label=npm)](https://www.npmjs.com/package/steerplane)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Node](https://img.shields.io/badge/Node.js-18+-green?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org)

## Install

```bash
npm install steerplane
```

## Quick Start

### Option 1: Gateway Mode (Zero Code Changes)

Point your OpenAI client to SteerPlane. Every LLM call — including SSE streaming — is automatically monitored, rate-limited, and cost-tracked with mid-stream enforcement.

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/gateway/v1',
  apiKey: 'sk_sp_...',  // SteerPlane API key
  defaultHeaders: { 'X-LLM-API-Key': 'sk-...' }
});

// All calls are now guarded — including stream: true
const stream = await client.chat.completions.create({
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Hello' }],
  stream: true  // SSE streaming with real-time cost tracking
});
```

### Option 2: Higher-Order Function (Simplest)

```typescript
import { guard } from 'steerplane';

const runAgent = guard(
  async () => {
    await agent.run();
  },
  {
    agentName: 'support_bot',
    maxCostUsd: 10.00,
    maxSteps: 50,
  }
);

await runAgent();
```

### Option 3: Class API (Full Control)

```typescript
import { SteerPlane } from 'steerplane';

const sp = new SteerPlane({ agentId: 'my_bot' });

await sp.run(async (run) => {
  await run.logStep({ action: 'query_db', tokens: 380, cost: 0.002 });
  await run.logStep({ action: 'call_llm', tokens: 1240, cost: 0.008 });
  await run.logStep({ action: 'send_email', tokens: 120, cost: 0.001 });
}, { maxCostUsd: 10 });
```

### Option 4: Manual Lifecycle

```typescript
import { SteerPlane } from 'steerplane';

const sp = new SteerPlane({ agentId: 'my_bot' });
const run = sp.createRun({ maxCostUsd: 10 });

await run.start();
await run.logStep({ action: 'search', tokens: 100, cost: 0.001 });
await run.logStep({ action: 'generate', tokens: 1240, cost: 0.008 });
await run.end();
```

## What's New in v0.4.0

### 🌊 SSE Streaming Gateway
The AI Gateway now supports Server-Sent Events (SSE) streaming. It accumulates token costs per chunk in real time and can **terminate a stream mid-response** by injecting a `steerplane_enforcement` event when the cost ceiling is breached — without corrupting the SSE protocol.

### 🛡️ Policy Engine
Define strict allow/deny rules, sliding-window rate limits, and human-in-the-loop approval workflows:

```typescript
import { PolicyEngine } from 'steerplane';

const policy = new PolicyEngine();
policy.addDeny('DROP TABLE*');
policy.addDeny('rm -rf*');
policy.addRateLimit('send_email', { maxCount: 5, windowSeconds: 60 });
policy.addApproval('execute_trade*');
```

### 🐳 Docker Compose
Full 4-service production stack:
```bash
docker compose up -d
# API (8000) + Dashboard (3000) + PostgreSQL (5432) + Redis (6379)
```

### 🖥️ CLI Tool (Python SDK)
```bash
pip install steerplane[cli]
steerplane status          # Check API health
steerplane runs list       # List recent runs
steerplane keys create     # Create gateway API key
steerplane logs --tail     # Live log stream
```

## All Features

| Feature | Description |
|---------|-------------|
| 🌉 **AI Gateway Proxy** | OpenAI-compatible proxy. Point your client, get instant monitoring. |
| 🌊 **SSE Streaming** | Real-time chunk forwarding with mid-stream cost enforcement. |
| 🛡️ **Policy Engine** | Allow/deny rules, sliding-window rate limits, approval workflows. |
| 🔄 **Loop Detection** | Sliding-window pattern detector catches infinite agent loops. |
| 💰 **Hard Cost Ceiling** | Per-run and monthly USD limits across 25+ LLM models. |
| 🚫 **Step Limits** | Cap maximum execution steps to prevent runaway agents. |
| 📊 **Deep Telemetry** | Tokens, cost, latency per step — synced to the live dashboard. |
| 🛡️ **Graceful Degradation** | API down? Guards still enforce locally. |
| ⚡ **Zero Dependencies** | Uses native `fetch` — no bloat. |
| 🐳 **Docker Compose** | 4-service production stack in one command. |

## Error Handling

```typescript
import { guard, CostLimitExceeded, LoopDetectedError, PolicyViolationError } from 'steerplane';

const runAgent = guard(async () => {
  try {
    await agent.run();
  } catch (err) {
    if (err instanceof CostLimitExceeded) {
      console.log(`Budget exceeded: $${err.currentCost}`);
    }
    if (err instanceof LoopDetectedError) {
      console.log(`Loop detected: ${err.pattern}`);
    }
    if (err instanceof PolicyViolationError) {
      console.log(`Policy blocked: ${err.message}`);
    }
  }
}, { maxCostUsd: 5 });
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────────┐
│  AI Agent   │────▶│ SteerPlane   │────▶│  FastAPI    │────▶│  PostgreSQL   │
│  (Your App) │     │  SDK / GW    │     │  Server     │     │  Database     │
└─────────────┘     └──────────────┘     └────────────┘     └───────────────┘
                                                │                    │
                                                ▼                    ▼
                                         ┌───────────────┐   ┌───────────┐
                                         │   Next.js     │   │   Redis   │
                                         │   Dashboard   │   │   Cache   │
                                         └───────────────┘   └───────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| TypeScript SDK | TypeScript, `guard()` wrapper, zero dependencies |
| Python SDK | Python 3.10+, CLI, Config files, 4 framework integrations |
| Gateway | FastAPI + httpx, SSE streaming, 25+ model pricing |
| Database | PostgreSQL 17 + SQLAlchemy + Alembic |
| Infrastructure | Docker Compose (API + Dashboard + PostgreSQL + Redis) |
| CI/CD | GitHub Actions (lint, test, Docker build) |
| Dashboard | Next.js 16, React 19, Framer Motion |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEERPLANE_API_URL` | `http://localhost:8000` | SteerPlane API server URL |

## Requirements

- Node.js 18+
- SteerPlane API server (for dashboard integration)

## Links

- **GitHub**: [github.com/vijaym2k6/SteerPlane](https://github.com/vijaym2k6/SteerPlane)
- **PyPI**: [pypi.org/project/steerplane](https://pypi.org/project/steerplane/)
- **Dashboard**: `http://localhost:3000`
- **API Docs**: `http://localhost:8000/docs`

## License

MIT — [Patent Pending](https://github.com/vijaym2k6/SteerPlane)
