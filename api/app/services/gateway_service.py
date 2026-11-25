"""
Gateway service: auth, session accounting, proxy telemetry, and enforcement.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models.api_key import APIKey, hash_api_key
from ..models.run import Run
from ..models.step import Step
from .state_store import StateStore, build_state_store


def format_usd_limit(limit: float) -> str:
    """Two decimals for $1 or more; more for a small limit, so $0.001 is not shown as $0.00."""
    if limit >= 1.0 or limit <= 0:
        return f"${limit:.2f}"
    if limit >= 0.0001:
        return f"${limit:.4f}"
    if limit >= 0.000001:
        return f"${limit:.6f}"
    return f"${limit:.1e}"


# Canonical per-1M USD pricing, loaded from model_pricing.json. This file is kept
# byte-identical to the SDK's copy (sdk/steerplane/model_pricing.json) and the TS
# mirror; api/tests/test_pricing_consistency.py fails if they drift.
_PRICING_PATH = Path(__file__).with_name("model_pricing.json")
MODEL_PRICING: dict[str, dict[str, float]] = json.loads(_PRICING_PATH.read_text("utf-8"))

_SESSION_ID_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:.")


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD from token counts. Pricing is per 1M tokens."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    cost = (input_tokens * pricing["input"] / 1_000_000) + (
        output_tokens * pricing["output"] / 1_000_000
    )
    return round(cost, 8)


def normalize_model_name(model: str) -> str:
    """Normalize model names for pricing lookup."""
    normalized = model.lower().strip()
    prefixes = sorted(MODEL_PRICING, key=len, reverse=True)
    # A routed name such as "openai/gpt-4o-mini" is priced by its last segment.
    for name in (normalized, normalized.rsplit("/", 1)[-1]):
        for prefix in prefixes:
            if prefix != "default" and name.startswith(prefix):
                return prefix
    return normalized


def normalize_session_id(session_id: str | None) -> str:
    """Normalize an optional session id from request headers."""
    raw = (session_id or "").strip()
    if not raw:
        return ""
    sanitized = "".join(ch for ch in raw if ch in _SESSION_ID_ALLOWED)
    return sanitized[:64]


def gateway_run_prefix(key_hash: str) -> str:
    """Stable run id prefix for all gateway runs issued by an API key."""
    return f"gw_{key_hash[:12]}_"


def build_gateway_run_id(key_hash: str, session_id: str, explicit: bool) -> str:
    """Build a run id for a gateway session."""
    session_hash = hashlib.sha1(session_id.encode()).hexdigest()[:12]
    prefix = gateway_run_prefix(key_hash)
    if explicit:
        return f"{prefix}{session_hash}"
    return f"{prefix}{session_hash}_{secrets.token_hex(3)}"


def loop_storage_key(key_hash: str, session_id: str) -> str:
    return f"{key_hash}:{session_id}"


def month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return the current UTC month bounds [start, next_start)."""
    current = now or datetime.now(timezone.utc)
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


class GatewayLoopDetector:
    """Detect repeated prompt patterns for a specific session (store-backed)."""

    def __init__(self, store: StateStore, window_size: int = 10, min_repetitions: int = 3):
        self._store = store
        self._window_size = window_size
        self._min_repetitions = min_repetitions

    def record_and_check(self, storage_key: str, prompt_hash: str) -> tuple[bool, str]:
        history = self._store.append_loop(storage_key, prompt_hash, self._window_size * 2)

        if len(history) < self._min_repetitions:
            return False, ""

        recent = history[-self._min_repetitions :]
        if len(set(recent)) == 1:
            return True, f"Same prompt repeated {self._min_repetitions} times"

        window = history[-self._window_size :]
        for pattern_len in range(1, len(window) // 2 + 1):
            pattern = window[:pattern_len]
            reps = 0
            for idx in range(0, len(window) - pattern_len + 1, pattern_len):
                if window[idx : idx + pattern_len] == pattern:
                    reps += 1
                else:
                    break
            if reps >= self._min_repetitions:
                return True, (f"Repeating pattern of length {pattern_len} detected ({reps} reps)")

        return False, ""

    def clear(self, storage_key: str):
        self._store.clear_loop(storage_key)


@dataclass
class GatewaySession:
    """Active gateway session state."""

    key_hash: str
    session_id: str
    run_id: str
    explicit: bool
    last_seen_at: float


def _session_to_dict(session: GatewaySession) -> dict:
    return {
        "key_hash": session.key_hash,
        "session_id": session.session_id,
        "run_id": session.run_id,
        "explicit": session.explicit,
        "last_seen_at": session.last_seen_at,
    }


def _session_from_dict(data: dict) -> GatewaySession:
    return GatewaySession(
        key_hash=data["key_hash"],
        session_id=data["session_id"],
        run_id=data["run_id"],
        explicit=bool(data["explicit"]),
        last_seen_at=float(data["last_seen_at"]),
    )


@dataclass
class GatewayPreflightResult:
    """Gateway decision before a proxied request is sent upstream."""

    decision: str  # allow, blocked
    reason: str
    session: GatewaySession


class SessionTracker:
    """Track default and explicit gateway sessions via a pluggable StateStore."""

    def __init__(self, store: StateStore, idle_timeout_sec: int = 1800):
        self._store = store
        self._idle_timeout_sec = idle_timeout_sec

    def resolve_session(
        self,
        key_hash: str,
        requested_session_id: str | None = None,
    ) -> tuple[GatewaySession, list[GatewaySession]]:
        now_ts = time.time()
        expired = self._cleanup_expired(key_hash, now_ts)
        normalized = normalize_session_id(requested_session_id)

        if normalized:
            data = self._store.get_session(key_hash, normalized)
            if data is None:
                session = GatewaySession(
                    key_hash=key_hash,
                    session_id=normalized,
                    run_id=build_gateway_run_id(key_hash, normalized, explicit=True),
                    explicit=True,
                    last_seen_at=now_ts,
                )
            else:
                session = _session_from_dict(data)
            session.last_seen_at = now_ts
            self._store.put_session(key_hash, normalized, _session_to_dict(session))
            return session, expired

        default_session_id = self._store.get_default_session_id(key_hash)
        session = None
        if default_session_id:
            data = self._store.get_session(key_hash, default_session_id)
            if data:
                session = _session_from_dict(data)

        if session is None:
            generated_session_id = f"auto_{secrets.token_urlsafe(9)}"
            session = GatewaySession(
                key_hash=key_hash,
                session_id=generated_session_id,
                run_id=build_gateway_run_id(key_hash, generated_session_id, explicit=False),
                explicit=False,
                last_seen_at=now_ts,
            )
            self._store.set_default_session_id(key_hash, generated_session_id)

        session.last_seen_at = now_ts
        self._store.put_session(key_hash, session.session_id, _session_to_dict(session))
        return session, expired

    def _cleanup_expired(
        self,
        key_hash: str,
        now_ts: float,
    ) -> list[GatewaySession]:
        expired: list[GatewaySession] = []
        for session_id, data in self._store.all_sessions(key_hash).items():
            if data.get("explicit"):
                continue
            if now_ts - float(data.get("last_seen_at", 0.0)) > self._idle_timeout_sec:
                expired.append(_session_from_dict(data))
                self._store.delete_session(key_hash, session_id)
                if self._store.get_default_session_id(key_hash) == session_id:
                    self._store.delete_default_session_id(key_hash)
        return expired


_state_store = build_state_store()
_loop_detector = GatewayLoopDetector(_state_store)
_session_tracker = SessionTracker(_state_store, settings.GATEWAY_SESSION_IDLE_SEC)


def reset_gateway_state() -> None:
    """Clear all gateway session + loop state (used by tests)."""
    _state_store.reset()


# ─── Hot-path usage counters ────────────────────────────────
# Session cost, monthly cost, the per-minute request window and step numbers are
# kept in the state store and seeded from the database once, on first use. This
# replaces a SUM/COUNT/MAX scan per request (the monthly and rate scans grew with
# every request a key ever made). The database stays the record; the counters
# are updated synchronously, before the response, so enforcement never lags.


def _run_cost_key(run_id: str) -> str:
    return f"cost:run:{run_id}"


def _month_cost_key(key_hash: str, now: datetime | None = None) -> str:
    start, _ = month_bounds(now)
    return f"cost:month:{key_hash}:{start:%Y-%m}"


def _rate_key(key_hash: str) -> str:
    return f"rate:{key_hash}"


def _steps_key(run_id: str) -> str:
    return f"steps:{run_id}"


def _to_epoch(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


def persist_gateway_request(
    db: Session,
    api_key_id: str,
    session: GatewaySession,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    latency_ms: float,
    step_number: int,
    status: str | None = "completed",
    error: str | None = None,
    agent_name: str | None = None,
    max_cost_usd: float | None = None,
) -> None:
    """Write one proxied request to the database (step row + run/key totals)."""
    total_tokens = input_tokens + output_tokens
    api_key = db.get(APIKey, api_key_id)
    run = db.get(Run, session.run_id)
    if run is None:
        run = Run(
            id=session.run_id,
            agent_name=agent_name or f"gateway:{api_key.name if api_key else 'unknown'}",
            status="running",
            start_time=datetime.now(timezone.utc),
            max_cost_usd=max_cost_usd
            if max_cost_usd is not None
            else (api_key.max_cost_usd if api_key else 50.0),
            max_steps_limit=9999,
        )
        db.add(run)

    db.add(
        Step(
            run_id=session.run_id,
            step_number=step_number,
            action=f"llm:{model}",
            tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            error=error,
            metadata_json={
                "source": "gateway",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "session_id": session.session_id,
                "session_explicit": session.explicit,
            },
            timestamp=datetime.now(timezone.utc),
        )
    )

    run.total_steps = max(run.total_steps or 0, step_number)
    run.total_cost = (run.total_cost or 0.0) + cost
    run.total_tokens = (run.total_tokens or 0) + total_tokens

    if api_key is not None:
        api_key.total_requests = (api_key.total_requests or 0) + 1
        api_key.total_cost = (api_key.total_cost or 0.0) + cost
        api_key.total_tokens = (api_key.total_tokens or 0) + total_tokens
        api_key.last_used_at = datetime.now(timezone.utc)

    db.commit()


class GatewayService:
    """Core gateway logic: auth, enforce, proxy, and log."""

    def __init__(self, db: Session):
        self.db = db

    def resolve_provider_key(self, api_key: APIKey, header_value: str | None) -> str:
        """Pick the upstream provider key from the X-LLM-API-Key header."""
        return (header_value or "").strip()

    def validate_api_key(self, raw_key: str) -> APIKey | None:
        key_hashed = hash_api_key(raw_key)
        return (
            self.db.query(APIKey)
            .filter(
                APIKey.key_hash == key_hashed,
                APIKey.is_active == True,
            )
            .first()
        )

    def close_expired_sessions(self, expired_sessions: list[GatewaySession]):
        """Mark expired auto sessions as completed in the dashboard."""
        if not expired_sessions:
            return

        now = datetime.now(timezone.utc)
        updated = False
        for session in expired_sessions:
            run = self.db.query(Run).filter(Run.id == session.run_id).first()
            if run and run.status == "running":
                run.status = "completed"
                run.end_time = now
                updated = True
            _loop_detector.clear(loop_storage_key(session.key_hash, session.session_id))
            _state_store.delete_counter(_run_cost_key(session.run_id))
            _state_store.delete_counter(_steps_key(session.run_id))

        if updated:
            self.db.commit()

    def resolve_session(
        self,
        api_key: APIKey,
        requested_session_id: str | None = None,
    ) -> GatewaySession:
        session, expired_sessions = _session_tracker.resolve_session(
            api_key.key_hash,
            requested_session_id,
        )
        self.close_expired_sessions(expired_sessions)
        return session

    def get_session_cost(self, session: GatewaySession) -> float:
        key = _run_cost_key(session.run_id)
        value = _state_store.get_counter(key)
        if value is None:
            value = self._db_session_cost(session.run_id)
            _state_store.set_counter(key, value)
        return float(value)

    def get_monthly_cost(self, api_key: APIKey) -> float:
        key = _month_cost_key(api_key.key_hash)
        value = _state_store.get_counter(key)
        if value is None:
            value = self._db_monthly_cost(api_key)
            _state_store.set_counter(key, value)
        return float(value)

    def _db_session_cost(self, run_id: str) -> float:
        return float(
            self.db.query(func.coalesce(func.sum(Step.cost_usd), 0.0))
            .filter(Step.run_id == run_id)
            .scalar()
            or 0.0
        )

    def _db_monthly_cost(self, api_key: APIKey) -> float:
        month_start, month_end = month_bounds()
        run_prefix = gateway_run_prefix(api_key.key_hash)
        return float(
            self.db.query(func.coalesce(func.sum(Step.cost_usd), 0.0))
            .join(Run, Run.id == Step.run_id)
            .filter(
                Run.id.like(f"{run_prefix}%"),
                Step.timestamp >= month_start,
                Step.timestamp < month_end,
            )
            .scalar()
            or 0.0
        )

    def get_session_cost_limit(self, api_key: APIKey, session: GatewaySession) -> float:
        return api_key.max_cost_usd

    def get_run(self, run_id: str) -> Run | None:
        return self.db.query(Run).filter(Run.id == run_id).first()

    def check_model_allowed(self, api_key: APIKey, model: str) -> tuple[bool, str]:
        requested_model = normalize_model_name(model)

        if api_key.denied_models:
            denied = {
                normalize_model_name(entry.strip())
                for entry in api_key.denied_models.split(",")
                if entry.strip()
            }
            if requested_model in denied:
                return False, f"Model '{model}' is denied by your API key policy"

        if api_key.allowed_models:
            allowed = {
                normalize_model_name(entry.strip())
                for entry in api_key.allowed_models.split(",")
                if entry.strip()
            }
            if requested_model not in allowed:
                return False, f"Model '{model}' is not in your allowed models list"

        return True, ""

    def check_cost_limit(
        self,
        api_key: APIKey,
        session: GatewaySession,
    ) -> tuple[bool, str, float]:
        session_cost = self.get_session_cost(session)
        session_limit = self.get_session_cost_limit(api_key, session)
        if session_cost >= session_limit:
            return (
                False,
                f"Session cost limit exceeded: ${session_cost:.4f} >= {format_usd_limit(session_limit)}",
                session_limit,
            )

        monthly_cost = self.get_monthly_cost(api_key)
        if monthly_cost >= api_key.max_cost_monthly:
            return (
                False,
                f"Monthly budget exceeded: ${monthly_cost:.4f} >= {format_usd_limit(api_key.max_cost_monthly)}",
                session_limit,
            )

        return True, "", session_limit

    def _ensure_rate_window(self, api_key: APIKey) -> str:
        key = _rate_key(api_key.key_hash)
        if not _state_store.has_events(key):
            one_min_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
            run_prefix = gateway_run_prefix(api_key.key_hash)
            rows = (
                self.db.query(Step.timestamp)
                .join(Run, Run.id == Step.run_id)
                .filter(
                    Run.id.like(f"{run_prefix}%"),
                    Step.timestamp >= one_min_ago,
                    Step.action.like("llm:%"),
                )
                .all()
            )
            _state_store.seed_events(key, [_to_epoch(r[0]) for r in rows])
        return key

    def check_rate_limit(self, api_key: APIKey) -> tuple[bool, str]:
        key = self._ensure_rate_window(api_key)
        recent_count = _state_store.count_events_since(key, time.time() - 60)

        if recent_count >= api_key.max_requests_per_min:
            return (
                False,
                "Rate limit exceeded: "
                f"{recent_count} requests in last 60s >= {api_key.max_requests_per_min}/min",
            )
        return True, ""

    def check_loop(
        self,
        api_key: APIKey,
        session: GatewaySession,
        messages: list[dict],
    ) -> tuple[bool, str]:
        prompt_payload = json.dumps(
            messages,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        prompt_hash = hashlib.sha256(prompt_payload.encode("utf-8")).hexdigest()
        is_loop, info = _loop_detector.record_and_check(
            loop_storage_key(api_key.key_hash, session.session_id),
            prompt_hash,
        )
        return not is_loop, info

    def pre_request_checks(
        self,
        api_key: APIKey,
        model: str,
        messages: list[dict],
        requested_session_id: str | None = None,
    ) -> GatewayPreflightResult:
        session = self.resolve_session(api_key, requested_session_id)
        run = self.get_run(session.run_id)
        if run and run.status == "terminated":
            return GatewayPreflightResult(
                decision="blocked",
                reason=run.error or "Run was previously terminated",
                session=session,
            )

        ok, reason = self.check_model_allowed(api_key, model)
        if not ok:
            return GatewayPreflightResult("blocked", reason, session)

        ok, reason, _session_limit = self.check_cost_limit(api_key, session)
        if not ok:
            return GatewayPreflightResult("blocked", reason, session)

        ok, reason = self.check_rate_limit(api_key)
        if not ok:
            return GatewayPreflightResult("blocked", reason, session)

        ok, reason = self.check_loop(api_key, session, messages)
        if not ok:
            return GatewayPreflightResult("blocked", f"Loop detected: {reason}", session)

        return GatewayPreflightResult("allow", "", session)

    def ensure_run(self, api_key: APIKey, session: GatewaySession) -> Run:
        run = self.db.query(Run).filter(Run.id == session.run_id).first()
        if run:
            return run

        run = Run(
            id=session.run_id,
            agent_name=f"gateway:{api_key.name}",
            status="running",
            start_time=datetime.now(timezone.utc),
            max_cost_usd=api_key.max_cost_usd,
            max_steps_limit=9999,
        )
        self.db.add(run)
        return run

    def next_step_number(self, run_id: str) -> int:
        key = _steps_key(run_id)
        if _state_store.get_counter(key) is None:
            current_max = (
                self.db.query(func.coalesce(func.max(Step.step_number), 0))
                .filter(Step.run_id == run_id)
                .scalar()
            ) or 0
            _state_store.set_counter(key, float(current_max))
        return int(_state_store.add_counter(key, 1))

    def record_usage(self, api_key: APIKey, session: GatewaySession, cost: float) -> int:
        """Update the in-memory enforcement counters for one proxied request.

        Runs synchronously before the response so limits see this request at
        once, even when the database write happens after the response. Returns
        the step number to persist.
        """
        # Seed from the database first, so the seed never already includes this request.
        self.get_session_cost(session)
        self.get_monthly_cost(api_key)
        rate_key = self._ensure_rate_window(api_key)

        _state_store.add_counter(_run_cost_key(session.run_id), cost)
        _state_store.add_counter(_month_cost_key(api_key.key_hash), cost)
        _state_store.add_event(rate_key, time.time())
        return self.next_step_number(session.run_id)

    def log_request(
        self,
        api_key: APIKey,
        session: GatewaySession,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: float,
        status: str = "completed",
        error: str | None = None,
    ):
        step_number = self.record_usage(api_key, session, cost)
        persist_gateway_request(
            self.db,
            api_key.id,
            session,
            model,
            input_tokens,
            output_tokens,
            cost,
            latency_ms,
            step_number,
            status,
            error,
            agent_name=f"gateway:{api_key.name}",
            max_cost_usd=api_key.max_cost_usd,
        )

    def log_blocked_request(
        self,
        api_key: APIKey,
        session: GatewaySession,
        model: str,
        reason: str,
    ):
        run = self.ensure_run(api_key, session)
        step_number = self.next_step_number(session.run_id)

        step = Step(
            run_id=session.run_id,
            step_number=step_number,
            action=f"blocked:{model}",
            tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
            status="blocked",
            error=reason,
            metadata_json={
                "source": "gateway",
                "model": model,
                "blocked_reason": reason,
                "session_id": session.session_id,
                "session_explicit": session.explicit,
            },
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)

        run.total_steps = step_number
        lowered_reason = reason.lower()
        if "loop detected" in lowered_reason or "cost limit exceeded" in lowered_reason:
            run.status = "terminated"
            run.end_time = datetime.now(timezone.utc)
            run.error = reason

        self.db.commit()
