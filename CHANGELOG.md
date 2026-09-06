# Changelog

All notable changes to SteerPlane are documented here. The project follows
[Semantic Versioning](https://semver.org/).

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

[0.4.1]: https://github.com/vijaym2k6/SteerPlane/releases/tag/v0.4.1
[0.4.0]: https://github.com/vijaym2k6/SteerPlane/releases/tag/v0.4.0
