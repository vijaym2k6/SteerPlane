# Changelog

All notable changes to SteerPlane are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **`detectLoops` option in the TypeScript SDK** (default `true`). Set it to `false` on
  `guard()`, `SteerPlane.run()`, `createRun()` or `RunManager` to stop loop detection from
  ending a run. Cost, step, runtime and policy limits still apply.
- **`docker-compose.hosted.yml`** for running one server for several teams. Run auth is
  always on, the admin token is required, the Postgres port is not published, and the
  API and dashboard listen on `127.0.0.1` behind your HTTPS proxy. Settings live in
  `.env.hosted` (template: `.env.hosted.example`, git-ignored). Guide:
  `docs/hosted-deployment.md`.
- **Team sign-in on the dashboard.** The navbar **Sign In** box now accepts a team API key
  (`sk_sp_...`) as well as the admin token. A team key is sent as
  `Authorization: Bearer`, so with run auth on the team sees only its own runs. Policies
  and API keys stay admin-only. The API Keys page snippets now show the dashboard's
  configured API address instead of always `http://localhost:8000`.

### Fixed
- **Dashboard image now uses the configured API address.** `NEXT_PUBLIC_API_URL` is
  compiled into the browser bundle at build time, but the Dockerfile never received it,
  so a dashboard built from it always called `http://localhost:8000`. It is now a build
  argument (default unchanged), and both compose files pass it.
- **API works again on a fresh install with SQLAlchemy 2.1.** SQLAlchemy 2.1 changed the
  driver behind a bare `postgresql://` URL from psycopg2 to psycopg 3, which is not
  installed, so the API and its migrations failed at startup with
  `ModuleNotFoundError: No module named 'psycopg'`. `DATABASE_URL` now names psycopg2
  explicitly (`postgres://` is accepted too). URLs that already name a driver are left
  alone.

### Security
- **The API no longer prints the database password at startup.** The startup banner
  echoed `DATABASE_URL` as-is, so the Postgres password ended up in console and container
  logs. It is now shown with the password masked (`postgresql://user:***@host/db`).
- **`detect_loops` now works in the Python SDK.** The docs have listed
  `@guard(detect_loops=True)` since v0.1.0, but the parameter did not exist, so passing it
  raised `TypeError`. It is now accepted (default `True`) by `@guard`, `SteerPlane.run()`,
  `RunManager` and the LangChain, CrewAI, AutoGen and OpenAI Agents integrations, and can
  be set in `.steerplane.yml` either under `defaults:` or at the top level. Setting it to
  `False` stops loop detection from ending a run; cost, step, runtime and policy limits
  still apply.

## [1.0.0]

First stable release. Security hardening, an open-core tier split, and a less
false-positive-prone loop detector. The public API is unchanged from 0.4.1, so
existing SDK and gateway integrations keep working without edits.

### Added
- **Optional data-plane authentication** (`STEERPLANE_REQUIRE_RUN_AUTH`, default off).
  When enabled, `/runs/*` and `/telemetry` require a SteerPlane API key
  (`Authorization: Bearer sk_sp_...`) or the admin token (superuser). Reads **and writes**
  are authorized by run ownership: a non-admin key may only read/write/step/end runs it
  owns; legacy NULL-owned runs are visible to admin only. Runs are stamped with the owning
  API key (`runs.api_key_id`, new migration). While off, unauthenticated calls are
  warn-logged so the existing keyless SDK/self-host flow is unchanged.

### Changed
- **Open-core tier split.** Alert-mode human-approval workflow (with email/webhook
  notifications), server-side provider-key vaulting, and the Redis-backed gateway state
  backend are now part of the hosted/enterprise plan and no longer ship in this public
  repo. The free self-hosted API runs kill-mode enforcement with an in-memory gateway
  state store. The SDK still exposes the `enforcement="alert"` client-side options — they
  work automatically against a hosted/enterprise deployment, and fail closed (safely
  terminate the run) against the free self-hosted API.

### Fixed
- **LangChain enforcement is no longer advisory.** LangChain's callback manager caught
  `SteerPlaneError` raised from the handler and let the agent run to completion after a
  violation. Passing `enforce=True` to `SteerPlaneCallbackHandler` now sets `raise_error`
  so the exception propagates and the run actually stops. The handler also accepts
  `loop_window_size`, which it previously ignored.
- **Ending a run no longer masks the error that caused it.** When a framework starts a run
  on one context and ends it on another (LangGraph tool nodes, CrewAI workers, asyncio
  tasks), resetting the context token raised `ValueError` and hid the real
  `SteerPlaneError`. The reset is now best-effort.
- **Loop detector** is less false-positive prone: single-action loops now require **≥3**
  consecutive repetitions (a benign double-call no longer terminates a run); multi-step
  patterns are unchanged. The TypeScript detector was also brought to parity with the
  end-anchored Python algorithm (it was still start-anchored, missing phase-shifted loops).
- Gateway now accumulates usage and enforces the mid-stream cost kill for **Anthropic**
  streams (previously dead code: Claude streams logged $0 and never tripped the ceiling).
- `@guard` now supports **async** agent functions instead of silently no-op'ing them.
- Client degrades once on an API **timeout** instead of stalling every step.
- Baseline **Alembic** migration added; `entrypoint.sh` fails loudly on migration errors.

### Changed
- Dashboard `middleware.ts` migrated to the Next.js 16 `proxy.ts` convention.
- Docs: corrected the gateway key-isolation and cost-ceiling descriptions to match behavior.
- **Single source of truth for model pricing.** `model_pricing.json` (USD per 1M tokens) is now
  canonical; the Python SDK, API gateway, and TypeScript SDK all derive their pricing from it, and
  a cross-language consistency test fails if the copies drift or resolve different costs. The
  Python SDK now prices all 24 models instead of falling back to a default for 16 of them.

## [0.4.1]

Patch release: stability, deployment correctness, and a hosted live demo. No
public API changes since 0.4.0 — existing SDK and gateway integrations keep working.

### Added
- **Env-gated demo mode** for the hosted live demo (`NEXT_PUBLIC_STEERPLANE_DEMO`).
  When enabled, the dashboard serves mock data and opens straight into the console;
  self-hosted installs (flag off) are unchanged and talk to the real API.
- API prints the dashboard URL on startup to remove localhost ambiguity.
- Patent-pending notice (IN 202641071111 A1) and `steerplane.com` across the project.

### Changed
- Synced every version reference to `0.4.1` (SDKs, API, dashboard, User-Agent strings).
- Dashboard hides alert-only fields in Kill mode instead of disabling them.

### Fixed
- **FastAPI lifespan**: migrated startup off the deprecated `@app.on_event("startup")`
  handler to the `lifespan` context manager.
- **Loop detector**: the sliding-window check is now anchored at the end of the window,
  so phase-shifted loops (e.g. `[X, A, B, A, B, A, B]`) are detected.
- **CI gating**: API tests now resolve and run from inside `api/` via `api/conftest.py`
  (the suite no longer silently collects nothing).
- Windows console Unicode safety for run logging output.

## [0.4.0]

Initial public feature set. See the "What's New in v0.4.0" sections in the package
READMEs and `docs/` for the full breakdown.

### Added
- SSE streaming in the gateway with mid-stream cost enforcement.
- Docker Compose (API + Dashboard + PostgreSQL + Redis) and Alembic migration scaffolding.
- GitHub Actions CI/CD pipeline (lint, test, Docker build).
- CLI tool (`steerplane runs`, `steerplane keys`, `steerplane status`).
- Config file support (`.steerplane.yml`) with auto-discovery.
- Framework integrations: LangChain, OpenAI Agents SDK, CrewAI, AutoGen.

[1.0.0]: https://github.com/vijaym2k6/SteerPlane/releases/tag/v1.0.0
[0.4.1]: https://github.com/vijaym2k6/SteerPlane/releases/tag/v0.4.1
[0.4.0]: https://github.com/vijaym2k6/SteerPlane/releases/tag/v0.4.0
