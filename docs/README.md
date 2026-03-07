# SteerPlane Documentation

Welcome to the SteerPlane documentation. SteerPlane is a **runtime control plane for autonomous AI agents** — providing safety guardrails, cost control, loop detection, and full observability.

## 📖 Documentation Pages

| Page | Description |
|------|-------------|
| [Getting Started](getting-started.md) | 5-minute quickstart guide |
| [Installation](installation.md) | Detailed installation for all components |
| [SDK Usage](sdk-usage.md) | Complete SDK reference and patterns |
| [Example Agents](example-agents.md) | Real-world agent integration examples |
| [Dashboard Guide](dashboard-guide.md) | Using the monitoring dashboard |
| [Architecture](architecture.md) | System design and data flow |

## 🏗️ Architecture Overview

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

## 🔗 Quick Links

- **GitHub**: [github.com/vijaym2k6/SteerPlane](https://github.com/vijaym2k6/SteerPlane)
- **API Docs**: `http://localhost:8000/docs` (auto-generated OpenAPI)
- **Dashboard**: `http://localhost:3000`
