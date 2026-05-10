# Architecture

## Overview

SteerPlane is a monorepo with four main layers:

1. `sdk/` and `sdk-ts/`
The Python and TypeScript SDKs enforce local guardrails such as step limits, cost ceilings, loop detection, and policy checks. They also stream run telemetry to the API when it is available.

2. `api/`
The FastAPI control plane stores runs, steps, policies, and gateway API keys. It also exposes the OpenAI-compatible gateway used for zero-code LLM interception.

3. `dashboard/`
The Next.js dashboard reads run telemetry from the API, auto-refreshes every 3 seconds on run pages, and lets admins manage policies and gateway keys.

4. `examples/`
Simulated agents that exercise the SDK and dashboard flow.

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

### Gateway Flow

```text
OpenAI-compatible client
  -> POST /gateway/v1/chat/completions
  -> SteerPlane API key validation
  -> model, session budget, monthly budget, rate limit, loop checks
  -> proxy to upstream provider
  -> log run + step telemetry
  -> return provider response plus SteerPlane metadata
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

## Tradeoffs

- SDK protections are intentionally local-first so agents stay protected even if the API is down.
- Gateway monthly accounting is DB-backed and calendar-month scoped.
- Automatic gateway sessions are convenient for local development, but explicit session ids are recommended for production-grade accounting.
