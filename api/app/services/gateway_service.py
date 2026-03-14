"""
SteerPlane API — Gateway Service

Core gateway logic: proxies LLM API calls, auto-captures telemetry,
enforces cost limits, detects loops, and applies policies.

This is the heart of SteerPlane — the chokepoint that makes
everything automatic with zero user instrumentation.
"""

import time
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.api_key import APIKey, hash_api_key
from ..models.run import Run
from ..models.step import Step


# ─── Pricing Table ───────────────────────────────────────

MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "claude-4-sonnet": {"input": 3.00, "output": 15.00},
    "claude-4-opus": {"input": 15.00, "output": 75.00},
    # Google
    "gemini-pro": {"input": 0.25, "output": 0.50},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # Meta
    "llama-3-70b": {"input": 0.59, "output": 0.79},
    "llama-3-8b": {"input": 0.05, "output": 0.08},
    # Mistral
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-small": {"input": 0.20, "output": 0.60},
    # Default fallback
    "default": {"input": 2.00, "output": 2.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD from token counts. Pricing is per 1M tokens."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    cost = (input_tokens * pricing["input"] / 1_000_000) + \
           (output_tokens * pricing["output"] / 1_000_000)
    return round(cost, 8)


def normalize_model_name(model: str) -> str:
    """Normalize model names for pricing lookup (strip date suffixes, etc.)."""
    model = model.lower().strip()
    # Strip date suffixes like -2024-01-01, -20240101
    for prefix in MODEL_PRICING:
        if model.startswith(prefix):
            return prefix
    return model


# ─── Loop Detection ──────────────────────────────────────

class GatewayLoopDetector:
    """Detects repeated prompt patterns at the gateway level."""

    def __init__(self):
        # Map of api_key_hash -> list of recent prompt hashes
        self._histories: dict[str, list[str]] = defaultdict(list)
        self._window_size = 10
        self._min_repetitions = 3

    def record_and_check(self, key_hash: str, prompt_hash: str) -> tuple[bool, str]:
        """Record a prompt hash and check for loops. Returns (is_loop, pattern_info)."""
        history = self._histories[key_hash]
        history.append(prompt_hash)

        # Keep window bounded
        if len(history) > self._window_size * 2:
            self._histories[key_hash] = history[-self._window_size * 2:]
            history = self._histories[key_hash]

        if len(history) < self._min_repetitions:
            return False, ""

        # Check if the last N entries are all the same (exact repeat)
        recent = history[-self._min_repetitions:]
        if len(set(recent)) == 1:
            return True, f"Same prompt repeated {self._min_repetitions} times"

        # Check for A-B-A-B patterns
        window = history[-self._window_size:]
        for pattern_len in range(1, len(window) // 2 + 1):
            pattern = window[:pattern_len]
            reps = 0
            for i in range(0, len(window) - pattern_len + 1, pattern_len):
                if window[i:i + pattern_len] == pattern:
                    reps += 1
                else:
                    break
            if reps >= self._min_repetitions:
                return True, f"Repeating pattern of length {pattern_len} detected ({reps} reps)"

        return False, ""

    def clear(self, key_hash: str):
        """Clear history for an API key."""
        self._histories.pop(key_hash, None)


# ─── Session Tracker ─────────────────────────────────────

class SessionTracker:
    """Tracks active gateway sessions (maps API key -> active run)."""

    def __init__(self):
        # Map of key_hash -> { run_id, step_count, total_cost, started_at }
        self._sessions: dict[str, dict] = {}

    def get_or_create_session(self, key_hash: str, key_name: str, max_cost: float) -> dict:
        """Get existing session or create a new one."""
        if key_hash not in self._sessions:
            self._sessions[key_hash] = {
                "run_id": f"gw_{uuid.uuid4().hex[:12]}",
                "agent_name": f"gateway:{key_name}",
                "step_count": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "max_cost": max_cost,
                "started_at": time.time(),
            }
        return self._sessions[key_hash]

    def increment(self, key_hash: str, cost: float, tokens: int) -> dict:
        """Increment session counters."""
        session = self._sessions.get(key_hash)
        if session:
            session["step_count"] += 1
            session["total_cost"] += cost
            session["total_tokens"] += tokens
        return session

    def get_session(self, key_hash: str) -> Optional[dict]:
        return self._sessions.get(key_hash)

    def reset_session(self, key_hash: str):
        self._sessions.pop(key_hash, None)


# ─── Gateway Service ─────────────────────────────────────

# ─── Singletons ───────────────────────────────────────
# Loop detector: in-memory by design — moving to DB would add latency to every
# request. Acceptable trade-off: loops reset on worker restart, but cost/rate
# limits are now DB-backed and multi-worker safe.
_loop_detector = GatewayLoopDetector()
_session_tracker = SessionTracker()


class GatewayService:
    """Core gateway logic: auth, enforce, proxy, log."""

    def __init__(self, db: Session):
        self.db = db

    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key record if valid."""
        key_hashed = hash_api_key(raw_key)
        api_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hashed,
            APIKey.is_active == True,
        ).first()
        return api_key

    def check_model_allowed(self, api_key: APIKey, model: str) -> tuple[bool, str]:
        """Check if the requested model is allowed by the API key policy."""
        if api_key.denied_models:
            denied = [m.strip().lower() for m in api_key.denied_models.split(",")]
            if model.lower() in denied:
                return False, f"Model '{model}' is denied by your API key policy"

        if api_key.allowed_models:
            allowed = [m.strip().lower() for m in api_key.allowed_models.split(",")]
            if model.lower() not in allowed:
                return False, f"Model '{model}' is not in your allowed models list"

        return True, ""

    def check_cost_limit(self, api_key: APIKey) -> tuple[bool, str]:
        """Check if the API key has exceeded its cost limits (session + monthly)."""
        # Session cost limit: check both in-memory tracker and DB
        session = _session_tracker.get_session(api_key.key_hash)
        session_cost = session["total_cost"] if session else 0.0

        # Also query DB for the active gateway run's cost (multi-worker safe)
        db_session_cost = (
            self.db.query(func.coalesce(func.sum(Step.cost_usd), 0.0))
            .filter(Step.run_id.like("gw_%"))
            .join(Run, Run.id == Step.run_id)
            .filter(Run.agent_name == f"gateway:{api_key.name}", Run.status == "running")
            .scalar()
        ) or 0.0

        effective_session_cost = max(session_cost, float(db_session_cost))
        if effective_session_cost >= api_key.max_cost_usd:
            return False, f"Session cost limit exceeded: ${effective_session_cost:.4f} >= ${api_key.max_cost_usd:.2f}"

        # Monthly budget limit (checked from DB-persisted total_cost)
        if api_key.total_cost >= api_key.max_cost_monthly:
            return False, f"Monthly budget exceeded: ${api_key.total_cost:.2f} >= ${api_key.max_cost_monthly:.2f}"

        return True, ""

    def check_rate_limit(self, api_key: APIKey) -> tuple[bool, str]:
        """Strict sliding-window rate limit: count DB steps in the last 60 seconds."""
        one_min_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
        recent_count = (
            self.db.query(func.count(Step.id))
            .filter(
                Step.run_id.like("gw_%"),
                Step.timestamp >= one_min_ago,
                Step.action.like(f"llm:%"),
            )
            .join(Run, Run.id == Step.run_id)
            .filter(Run.agent_name == f"gateway:{api_key.name}")
            .scalar()
        ) or 0

        if recent_count >= api_key.max_requests_per_min:
            return False, f"Rate limit exceeded: {recent_count} requests in last 60s >= {api_key.max_requests_per_min}/min"
        return True, ""

    def check_loop(self, api_key: APIKey, messages: list[dict]) -> tuple[bool, str]:
        """Check for repeated prompt patterns."""
        prompt_hash = hashlib.md5(str(messages).encode()).hexdigest()
        is_loop, info = _loop_detector.record_and_check(api_key.key_hash, prompt_hash)
        return not is_loop, info  # Returns (is_ok, reason)

    def pre_request_checks(
        self, api_key: APIKey, model: str, messages: list[dict]
    ) -> tuple[bool, str]:
        """Run all pre-request checks. Returns (allowed, denial_reason)."""
        # 1. Model allowed?
        ok, reason = self.check_model_allowed(api_key, model)
        if not ok:
            return False, reason

        # 2. Cost limit?
        ok, reason = self.check_cost_limit(api_key)
        if not ok:
            return False, reason

        # 3. Rate limit?
        ok, reason = self.check_rate_limit(api_key)
        if not ok:
            return False, reason

        # 4. Loop detection?
        ok, reason = self.check_loop(api_key, messages)
        if not ok:
            return False, f"Loop detected: {reason}"

        return True, ""

    def log_request(
        self,
        api_key: APIKey,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: float,
        status: str = "completed",
        error: Optional[str] = None,
    ):
        """Log a gateway request as a run step and update API key usage."""
        session = _session_tracker.get_or_create_session(
            api_key.key_hash, api_key.name, api_key.max_cost_usd
        )
        _session_tracker.increment(api_key.key_hash, cost, input_tokens + output_tokens)

        total_tokens = input_tokens + output_tokens

        # Ensure run exists in DB
        run = self.db.query(Run).filter(Run.id == session["run_id"]).first()
        if not run:
            run = Run(
                id=session["run_id"],
                agent_name=session["agent_name"],
                status="running",
                start_time=datetime.now(timezone.utc),
                max_cost_usd=api_key.max_cost_usd,
                max_steps_limit=9999,
            )
            self.db.add(run)

        # Create step
        step = Step(
            run_id=session["run_id"],
            step_number=session["step_count"],
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
            },
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)

        # Update run totals
        run.total_steps = session["step_count"]
        run.total_cost = session["total_cost"]
        run.total_tokens = session["total_tokens"]

        # Update API key usage
        api_key.total_requests += 1
        api_key.total_cost += cost
        api_key.total_tokens += total_tokens
        api_key.last_used_at = datetime.now(timezone.utc)

        self.db.commit()

    def log_blocked_request(
        self,
        api_key: APIKey,
        model: str,
        reason: str,
    ):
        """Log a blocked gateway request."""
        session = _session_tracker.get_or_create_session(
            api_key.key_hash, api_key.name, api_key.max_cost_usd
        )
        _session_tracker.increment(api_key.key_hash, 0.0, 0)

        run = self.db.query(Run).filter(Run.id == session["run_id"]).first()
        if not run:
            run = Run(
                id=session["run_id"],
                agent_name=session["agent_name"],
                status="running",
                start_time=datetime.now(timezone.utc),
                max_cost_usd=api_key.max_cost_usd,
                max_steps_limit=9999,
            )
            self.db.add(run)

        step = Step(
            run_id=session["run_id"],
            step_number=session["step_count"],
            action=f"blocked:{model}",
            tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
            status="blocked",
            error=reason,
            metadata_json={"source": "gateway", "model": model, "blocked_reason": reason},
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(step)
        run.total_steps = session["step_count"]
        self.db.commit()
