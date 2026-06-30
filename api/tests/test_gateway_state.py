"""StateStore parity tests (#5).

The in-memory and Redis (fakeredis) backends must behave identically for session
tracking, idle expiry, and loop history — so switching to Redis for multi-worker
deployments does not change gateway behavior.
"""

from __future__ import annotations

import fakeredis
import pytest

from api.app.services.gateway_service import GatewayLoopDetector, SessionTracker
from api.app.services.state_store import InMemoryStateStore, RedisStateStore


@pytest.fixture(params=["memory", "redis"])
def store(request):
    if request.param == "memory":
        return InMemoryStateStore()
    return RedisStateStore(fakeredis.FakeStrictRedis(decode_responses=True))


def test_default_session_is_reused(store):
    tracker = SessionTracker(store, idle_timeout_sec=1800)
    first, expired = tracker.resolve_session("kh")
    assert expired == []
    second, _ = tracker.resolve_session("kh")
    assert second.session_id == first.session_id
    assert second.run_id == first.run_id


def test_explicit_session_is_stable(store):
    tracker = SessionTracker(store, idle_timeout_sec=1800)
    s1, _ = tracker.resolve_session("kh", "ticket-1")
    s2, _ = tracker.resolve_session("kh", "ticket-1")
    assert s1.session_id == s2.session_id == "ticket-1"
    assert s1.explicit is True


def test_idle_auto_session_expires_and_rotates(store):
    tracker = SessionTracker(store, idle_timeout_sec=1800)
    first, _ = tracker.resolve_session("kh")

    # Age the session past the idle window via the store.
    data = store.get_session("kh", first.session_id)
    data["last_seen_at"] -= 1801
    store.put_session("kh", first.session_id, data)

    second, expired = tracker.resolve_session("kh")
    assert second.session_id != first.session_id
    assert any(e.session_id == first.session_id for e in expired)


def test_explicit_session_does_not_expire(store):
    tracker = SessionTracker(store, idle_timeout_sec=1800)
    s1, _ = tracker.resolve_session("kh", "ticket-1")

    data = store.get_session("kh", "ticket-1")
    data["last_seen_at"] -= 99999
    store.put_session("kh", "ticket-1", data)

    _, expired = tracker.resolve_session("kh", "ticket-1")
    assert expired == []


def test_loop_same_prompt_three_times(store):
    det = GatewayLoopDetector(store)
    assert det.record_and_check("sk", "h1")[0] is False
    assert det.record_and_check("sk", "h1")[0] is False
    is_loop, info = det.record_and_check("sk", "h1")
    assert is_loop is True
    assert "repeated" in info.lower()


def test_loop_clear_resets_history(store):
    det = GatewayLoopDetector(store)
    det.record_and_check("sk", "h1")
    det.record_and_check("sk", "h1")
    det.clear("sk")
    # After clearing, two more of the same are not yet a loop (needs 3).
    assert det.record_and_check("sk", "h1")[0] is False
    assert det.record_and_check("sk", "h1")[0] is False


def test_loop_history_is_bounded(store):
    det = GatewayLoopDetector(store, window_size=10)
    for i in range(100):
        det.record_and_check("sk", f"h{i}")
    # Distinct prompts → no loop, and history is trimmed to window*2.
    history = store.append_loop("sk", "probe", 20)
    assert len(history) <= 20
