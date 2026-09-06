# SteerPlane Documentation

Welcome to the SteerPlane v1.0.0 documentation. SteerPlane is a **runtime control plane for autonomous AI agents** — providing safety guardrails, cost control, loop detection, SSE streaming enforcement, and full observability.

## Documentation Pages

| Page | Description |
|------|-------------|
| [Getting Started](getting-started.md) | 5-minute quickstart (Docker or manual) |
| [Installation](installation.md) | Detailed installation for all components |
| [SDK Usage](sdk-usage.md) | Complete SDK reference, config files, CLI, and framework integrations |
| [Example Agents](example-agents.md) | Real-world agent integration examples |
| [Dashboard Guide](dashboard-guide.md) | Using the monitoring dashboard |
| [Architecture](architecture.md) | System design, data flows, and infrastructure |

## Architecture Overview

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

## What's New in v1.0.0

- **Optional data-plane authentication** — `/runs/*` and `/telemetry` can require an API key, with run-ownership authorization
- **Open-core tier split** — alert-mode approvals, provider-key vaulting, and the Redis gateway backend moved to the hosted plan; the free self-hosted stack runs kill mode
- **Fewer loop false positives** — single-action loops now need at least 3 consecutive repetitions, so a benign double-call no longer terminates a run
- **TypeScript detector parity** — the TS loop detector now matches the end-anchored Python algorithm

## Previously in v0.4.0

- **SSE Streaming Gateway** — Real-time chunk forwarding with mid-stream cost enforcement
- **Docker Compose** — 3-service production stack (API + Dashboard + PostgreSQL)
- **CLI Tool** — `steerplane status`, `steerplane runs`, `steerplane keys`, `steerplane logs`
- **Config File** — `.steerplane.yml` auto-discovery with project-level defaults
- **Alembic Migrations** — Versioned PostgreSQL schema management
- **GitHub Actions CI/CD** — Lint, test, and Docker build pipeline
- **Framework Integrations** — Native support for OpenAI Agents SDK, CrewAI, and AutoGen (in addition to LangChain)

## Quick Links

- **GitHub**: [github.com/vijaym2k6/SteerPlane](https://github.com/vijaym2k6/SteerPlane)
- **PyPI**: [pypi.org/project/steerplane](https://pypi.org/project/steerplane/)
- **npm**: [npmjs.com/package/steerplane](https://www.npmjs.com/package/steerplane)
- **API Docs**: `http://localhost:8000/docs` (auto-generated OpenAPI)
- **Dashboard**: `http://localhost:3000`
