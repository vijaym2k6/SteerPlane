"""
Gateway service: auth, session accounting, proxy telemetry, and enforcement.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models.api_key import APIKey, hash_api_key
from ..models.run import Run
from ..models.step import Step
from .approval_service import ApprovalService


MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "claude-4-sonnet": {"input": 3.00, "output": 15.00},
    "claude-4-opus": {"input": 15.00, "output": 75.00},
    "gemini-pro": {"input": 0.25, "output": 0.50},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "llama-3-70b": {"input": 0.59, "output": 0.79},
    "llama-3-8b": {"input": 0.05, "output": 0.08},
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-small": {"input": 0.20, "output": 0.60},
    "default": {"input": 2.00, "output": 2.00},
}

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
    for prefix in sorted(MODEL_PRICING, key=len, reverse=True):
        if normalized.startswith(prefix):
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
    """Detect repeated prompt patterns for a specific session."""

    def __init__(self):
        self._histories: dict[str, list[str]] = defaultdict(list)
        self._window_size = 10
        self._min_repetitions = 3

    def record_and_check(self, storage_key: str, prompt_hash: str) -> tuple[bool, str]:
        history = self._histories[storage_key]
        history.append(prompt_hash)

        if len(history) > self._window_size * 2:
            self._histories[storage_key] = history[-self._window_size * 2 :]
            history = self._histories[storage_key]

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
        self._histories.pop(storage_key, None)


@dataclass
class GatewaySession:
    """Active gateway session state."""

    key_hash: str
    session_id: str
    run_id: str
    explicit: bool
    last_seen_at: float


@dataclass
class GatewayPreflightResult:
    """Gateway decision before a proxied request is sent upstream."""

    decision: str  # allow, paused, blocked
    reason: str
    session: GatewaySession
    approval_id: str | None = None


class SessionTracker:
    """Track in-memory default sessions and active explicit sessions."""

    def __init__(self, idle_timeout_sec: int = 1800):
        self._idle_timeout_sec = idle_timeout_sec
        self._sessions: dict[str, dict[str, GatewaySession]] = defaultdict(dict)
        self._default_session_ids: dict[str, str] = {}

    def resolve_session(
        self,
        key_hash: str,
        requested_session_id: str | None = None,
    ) -> tuple[GatewaySession, list[GatewaySession]]:
        now_ts = time.time()
        expired = self._cleanup_expired(key_hash, now_ts)
        normalized = normalize_session_id(requested_session_id)

        if normalized:
            session = self._sessions[key_hash].get(normalized)
            if session is None:
                session = GatewaySession(
                    key_hash=key_hash,
                    session_id=normalized,
                    run_id=build_gateway_run_id(key_hash, normalized, explicit=True),
                    explicit=True,
                    last_seen_at=now_ts,
                )
                self._sessions[key_hash][normalized] = session
            session.last_seen_at = now_ts
            return session, expired

        default_session_id = self._default_session_ids.get(key_hash)
        session = None
        if default_session_id:
            session = self._sessions[key_hash].get(default_session_id)

        if session is None:
            generated_session_id = f"auto_{secrets.token_urlsafe(9)}"
            session = GatewaySession(
                key_hash=key_hash,
                session_id=generated_session_id,
                run_id=build_gateway_run_id(
                    key_hash,
                    generated_session_id,
                    explicit=False,
                ),
                explicit=False,
                last_seen_at=now_ts,
            )
            self._sessions[key_hash][generated_session_id] = session
            self._default_session_ids[key_hash] = generated_session_id

        session.last_seen_at = now_ts
        return session, expired

    def _cleanup_expired(
        self,
        key_hash: str,
        now_ts: float,
    ) -> list[GatewaySession]:
        expired: list[GatewaySession] = []
        sessions = self._sessions.get(key_hash, {})
        for session_id, session in list(sessions.items()):
            if session.explicit:
                continue
            if now_ts - session.last_seen_at > self._idle_timeout_sec:
                expired.append(session)
                del sessions[session_id]
                if self._default_session_ids.get(key_hash) == session_id:
                    del self._default_session_ids[key_hash]
        return expired


_loop_detector = GatewayLoopDetector()
_session_tracker = SessionTracker(settings.GATEWAY_SESSION_IDLE_SEC)


class GatewayService:
    """Core gateway logic: auth, enforce, proxy, and log."""

    def __init__(self, db: Session):
        self.db = db

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
        return float(
            self.db.query(func.coalesce(func.sum(Step.cost_usd), 0.0))
            .filter(Step.run_id == session.run_id)
            .scalar()
            or 0.0
        )

    def get_monthly_cost(self, api_key: APIKey) -> float:
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
        approval_service = ApprovalService(self.db)
        return api_key.max_cost_usd + approval_service.get_gateway_cost_extension(
            session.run_id,
            session.session_id,
        )

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
                f"Session cost limit exceeded: ${session_cost:.4f} >= ${session_limit:.2f}",
                session_limit,
            )

        monthly_cost = self.get_monthly_cost(api_key)
        if monthly_cost >= api_key.max_cost_monthly:
            return (
                False,
                f"Monthly budget exceeded: ${monthly_cost:.4f} >= ${api_key.max_cost_monthly:.2f}",
                session_limit,
            )

        return True, "", session_limit

    def check_rate_limit(self, api_key: APIKey) -> tuple[bool, str]:
        one_min_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
        run_prefix = gateway_run_prefix(api_key.key_hash)
        recent_count = (
            self.db.query(func.count(Step.id))
            .join(Run, Run.id == Step.run_id)
            .filter(
                Run.id.like(f"{run_prefix}%"),
                Step.timestamp >= one_min_ago,
                Step.action.like("llm:%"),
            )
            .scalar()
        ) or 0

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
        approval_service = ApprovalService(self.db)
        run = self.get_run(session.run_id)
        if run and run.status == "terminated":
            return GatewayPreflightResult(
                decision="blocked",
                reason=run.error or "Run was previously terminated",
                session=session,
            )

        pending = approval_service.find_pending(
            session.run_id,
            "cost_limit",
            session_id=session.session_id,
        )
        if pending and pending.status == "pending":
            return GatewayPreflightResult(
                decision="paused",
                reason=pending.message,
                session=session,
                approval_id=pending.id,
            )

        ok, reason = self.check_model_allowed(api_key, model)
        if not ok:
            return GatewayPreflightResult("blocked", reason, session)

        ok, reason, session_limit = self.check_cost_limit(api_key, session)
        if not ok:
            enforcement = approval_service.get_api_key_enforcement(api_key.id)
            if enforcement.enforcement_mode == "alert" and "Session cost limit exceeded" in reason:
                approval = approval_service.create_approval(
                    run_id=session.run_id,
                    agent_name=f"gateway:{api_key.name}",
                    approval_type="cost_limit",
                    current_value=self.get_session_cost(session),
                    limit_value=session_limit,
                    unit="usd",
                    message=(
                        f"Gateway session {session.session_id} for '{api_key.name}' "
                        f"has reached its cost limit. Approve to continue or let it terminate."
                    ),
                    timeout_sec=enforcement.alert_timeout_sec,
                    scope="gateway",
                    session_id=session.session_id,
                    api_key_id=api_key.id,
                    channels=enforcement.alert_channels_json or [],
                    alert_email=enforcement.alert_email,
                    alert_webhook_url=enforcement.alert_webhook_url,
                    metadata={
                        "key_name": api_key.name,
                        "session_cost_usd": self.get_session_cost(session),
                        "session_limit_usd": session_limit,
                    },
                )
                return GatewayPreflightResult(
                    "paused",
                    approval.message,
                    session,
                    approval_id=approval.id,
                )
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
        current_max = (
            self.db.query(func.coalesce(func.max(Step.step_number), 0))
            .filter(Step.run_id == run_id)
            .scalar()
        ) or 0
        return int(current_max) + 1

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
        total_tokens = input_tokens + output_tokens
        run = self.ensure_run(api_key, session)
        step_number = self.next_step_number(session.run_id)

        step = Step(
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
        self.db.add(step)

        run.total_steps = step_number
        run.total_cost = (run.total_cost or 0.0) + cost
        run.total_tokens = (run.total_tokens or 0) + total_tokens

        api_key.total_requests += 1
        api_key.total_cost += cost
        api_key.total_tokens += total_tokens
        api_key.last_used_at = datetime.now(timezone.utc)

        self.db.commit()

    def maybe_trigger_threshold_alert(
        self,
        api_key: APIKey,
        session: GatewaySession,
    ):
        approval_service = ApprovalService(self.db)
        enforcement = approval_service.get_api_key_enforcement(api_key.id)
        if enforcement.enforcement_mode != "alert":
            return None

        if approval_service.find_pending(
            session.run_id,
            "cost_limit",
            session_id=session.session_id,
        ):
            return None

        session_limit = self.get_session_cost_limit(api_key, session)
        if session_limit <= 0:
            return None

        session_cost = self.get_session_cost(session)
        threshold_value = session_limit * enforcement.alert_threshold
        if session_cost < threshold_value:
            return None

        return approval_service.create_approval(
            run_id=session.run_id,
            agent_name=f"gateway:{api_key.name}",
            approval_type="cost_limit",
            current_value=session_cost,
            limit_value=session_limit,
            unit="usd",
            message=(
                f"Gateway session {session.session_id} for '{api_key.name}' has crossed "
                f"{int(enforcement.alert_threshold * 100)}% of its cost budget. "
                "Approve to continue or let it terminate on timeout."
            ),
            timeout_sec=enforcement.alert_timeout_sec,
            scope="gateway",
            session_id=session.session_id,
            api_key_id=api_key.id,
            channels=enforcement.alert_channels_json or [],
            alert_email=enforcement.alert_email,
            alert_webhook_url=enforcement.alert_webhook_url,
            metadata={
                "key_name": api_key.name,
                "session_cost_usd": session_cost,
                "session_limit_usd": session_limit,
                "alert_threshold": enforcement.alert_threshold,
            },
        )

    def log_paused_request(
        self,
        api_key: APIKey,
        session: GatewaySession,
        model: str,
        reason: str,
        approval_id: str | None = None,
    ):
        run = self.ensure_run(api_key, session)
        step_number = self.next_step_number(session.run_id)

        step = Step(
            run_id=session.run_id,
            step_number=step_number,
            action=f"paused:{model}",
            tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
            status="awaiting_approval",
            error=reason,
            metadata_json={
                "source": "gateway",
                "model": model,
                "paused_reason": reason,
                "approval_id": approval_id,
                "session_id": session.session_id,
                "session_explicit": session.explicit,
            },
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)

        run.total_steps = step_number
        run.status = "awaiting_approval"
        run.error = reason
        self.db.commit()

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
