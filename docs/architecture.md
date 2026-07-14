# Architecture

## Overview

SteerPlane v1.0.0 is a monorepo with five main layers:

1. `sdk/` and `sdk-ts/`
The Python and TypeScript SDKs enforce local guardrails such as step limits, cost ceilings, loop detection, and policy checks. They also stream run telemetry to the API when it is available. The Python SDK includes a CLI tool (`steerplane`) and `.steerplane.yml` config file support.

2. `api/`
The FastAPI control plane stores runs, steps, policies, and gateway API keys. It also exposes the OpenAI-compatible gateway used for zero-code LLM interception with real-time SSE streaming and mid-stream cost enforcement.

3. `dashboard/`
The Next.js dashboard reads run telemetry from the API, auto-refreshes every 3 seconds on run pages, and lets admins manage policies and gateway keys. Ships as a standalone Docker image.

4. `infrastructure/`
Docker Compose orchestrates a 3-service stack: API, Dashboard, and PostgreSQL. GitHub Actions CI/CD runs lint, test, and Docker build on every push.

5. `integrations/`
Native integration modules for LangChain, OpenAI Agents SDK, CrewAI, and AutoGen. All use lazy imports so framework dependencies are only required when actually used.

## Request Flows

### SDK Guard Flow

```text
Agent code
  -> SteerPlane RunManager
  -> local checks: policy, runtime, step count, cost, loop detection
  -> POST /runs/start
  -> POST /runs/step
  -> POST /runs/end
```

The SDK still enforces local limits if the API is unavailable. Dashboard visibility degrades, but agent protection does not.

### Gateway Flow (Non-Streaming)

```text
OpenAI-compatible client
  -> POST /gateway/v1/chat/completions
  -> SteerPlane API key validation
  -> model, session budget, monthly budget, rate limit, loop checks
  -> proxy to upstream provider
  -> log run + step telemetry
  -> return provider response plus SteerPlane metadata
```

### Gateway Flow (SSE Streaming) — New in v0.4.0

```text
OpenAI-compatible client (stream=true)
  -> POST /gateway/v1/chat/completions
  -> SteerPlane API key validation
  -> pre-request policy checks
  -> SSE stream from upstream provider
  -> per-chunk token accumulation + cost tracking
  -> if cost > ceiling: inject steerplane_enforcement event + sever stream
  -> forward chunks to client in real time
  -> log final telemetry on stream completion
```

The gateway accumulates tokens per SSE chunk and can terminate a stream mid-response by injecting a protocol-conformant `steerplane_enforcement` event before severing the upstream connection.

### CLI Flow — New in v0.4.0

```text
steerplane status   -> GET /health
steerplane runs     -> GET /runs, GET /runs/{id}, POST /runs/end
steerplane keys     -> GET /api-keys, POST /api-keys, DELETE /api-keys/{id}
steerplane logs     -> GET /runs (polling with --tail)
```

Important gateway headers:

- `Authorization: Bearer sk_sp_...`
- `X-LLM-API-Key: <real provider key>`
- `X-SteerPlane-Session-ID: <optional stable session id>`
- `X-Provider-URL: <optional custom OpenAI-compatible upstream, if allowlisted>`

If `X-SteerPlane-Session-ID` is omitted, the API creates an automatic session that expires after an idle timeout. For deterministic budgeting across workers and restarts, provide a stable session id from the client.

## Data Model

### `runs`

Stores one governed execution or gateway session.

Core fields:

- `id`
- `agent_name`
- `status`
- `start_time`
- `end_time`
- `total_cost`
- `total_steps`
- `total_tokens`
- `max_cost_usd`
- `max_steps_limit`
- `error`

### `steps`

Stores per-step telemetry for a run.

Core fields:

- `id`
- `run_id`
- `step_number`
- `action`
- `tokens`
- `cost_usd`
- `latency_ms`
- `status`
- `error`
- `metadata_json`
- `timestamp`

### `policies`

Stores reusable allow/deny, approval, and rate-limit policy definitions.

### `api_keys`

Stores gateway API keys plus usage counters and budget configuration.

## Security Model

- Sensitive control-plane routes for `policies` and `api-keys` require an admin token via `X-SteerPlane-Admin-Token`.
- If `STEERPLANE_ADMIN_TOKEN` is not set, the API generates a process-local token at startup and prints it to the server logs.
- The dashboard stores the admin token in browser local storage and attaches it only to sensitive requests.

## Dashboard Behavior

- `/dashboard` lists runs and refreshes every 3 seconds.
- `/dashboard/runs/[runId]` shows step timelines and refreshes every 3 seconds.
- `/policies` and `/api-keys` are admin-only views and require a valid admin token.

## Infrastructure — New in v0.4.0

### Docker Compose Stack

```yaml
services:
  api        # Python 3.11, FastAPI, Alembic migrations
  dashboard  # Node 20, Next.js standalone
  postgres   # PostgreSQL 16-alpine
```

### CI/CD Pipeline

```
push to main → Lint (ruff) → Test SDK → Test API → Test TS → Build Docker Images
```

### Database Migrations

Alembic manages PostgreSQL schema versioning:

```bash
cd api
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Tradeoffs

- SDK protections are intentionally local-first so agents stay protected even if the API is down.
- Gateway monthly accounting is DB-backed and calendar-month scoped.
- Automatic gateway sessions are convenient for local development, but explicit session ids are recommended for production-grade accounting.
- SSE streaming enforcement adds per-chunk overhead but ensures sub-second response to budget violations.
