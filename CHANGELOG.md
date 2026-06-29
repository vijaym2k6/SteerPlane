# Changelog

All notable changes to SteerPlane are documented here. The project follows
[Semantic Versioning](https://semver.org/).

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
