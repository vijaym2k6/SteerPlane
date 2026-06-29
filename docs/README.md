# SteerPlane Documentation

Welcome to the SteerPlane v0.4.1 documentation. SteerPlane is a **runtime control plane for autonomous AI agents** — providing safety guardrails, cost control, loop detection, SSE streaming enforcement, and full observability.

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
                                                │                    │
                                                ▼                    ▼
                                         ┌───────────────┐   ┌───────────┐
                                         │   Next.js     │   │   Redis   │
                                         │   Dashboard   │   │   Cache   │
                                         └───────────────┘   └───────────┘
```

## What's New in v0.4.0

- **SSE Streaming Gateway** — Real-time chunk forwarding with mid-stream cost enforcement
- **Docker Compose** — 4-service production stack (API + Dashboard + PostgreSQL + Redis)
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
