"""The gateway's low-latency path must keep enforcement exact.

Covers the shared upstream client (reused, never closed by a request), the
database write that happens after the response, and the in-memory counters
that replaced the per-request SUM/COUNT scans.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.db.database import get_db
from api.app.main import app
from api.app.models.api_key import APIKey, hash_api_key
from api.app.models.step import Step
from api.app.services.gateway_service import GatewayService, reset_gateway_state

RAW_KEY = "sk_sp_hot_path_test"
UPSTREAM = {
    "id": "x",
    "object": "chat.completion",
    "model": "gpt-4o",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    "usage": {"prompt_tokens": 1000, "completion_tokens": 1000, "total_tokens": 2000},
}


@pytest.fixture
def gw():
    reset_gateway_state()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    key = APIKey(
        name="hot",
        key_hash=hash_api_key(RAW_KEY),
        key_prefix="sk_sp_hot...",
        max_cost_usd=100.0,
        max_cost_monthly=1000.0,
        max_requests_per_min=1000,
        created_at=datetime.now(timezone.utc),
    )
    db.add(key)
    db.commit()

    seen = {"bodies": []}

    def handler(request: httpx.Request):
        seen["bodies"].append(json.loads(request.content))
        return httpx.Response(200, json=UPSTREAM)

    shared = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.state.upstream_client = shared
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield {"client": TestClient(app), "db": db, "key": key, "shared": shared, "seen": seen}
    finally:
        app.dependency_overrides.clear()
        del app.state.upstream_client
        db.close()
        reset_gateway_state()


def _post(client: TestClient, content: str, session: str = "s1"):
    return client.post(
        "/gateway/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {RAW_KEY}",
            "X-LLM-API-Key": "sk-upstream",
            "X-SteerPlane-Session-ID": session,
        },
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": content}]},
    )


def test_shared_client_is_reused_and_left_open(gw):
    for i in range(3):
        r = _post(gw["client"], f"question {i}")
        assert r.status_code == 200, r.text
    assert len(gw["seen"]["bodies"]) == 3
    assert gw["shared"].is_closed is False
    # The OpenAI body reaches the provider unchanged.
    assert gw["seen"]["bodies"][0]["messages"][0]["content"] == "question 0"


def test_request_is_persisted_after_the_response(gw):
    r = _post(gw["client"], "hello")
    assert r.status_code == 200
    data = r.json()["steerplane"]
    assert data["request_number"] == 1

    gw["db"].expire_all()
    steps = gw["db"].query(Step).all()
    assert len(steps) == 1
    assert steps[0].step_number == 1
    assert steps[0].cost_usd == pytest.approx(data["cost_usd"])
    key = gw["db"].get(APIKey, gw["key"].id)
    assert key.total_requests == 1


def test_step_numbers_keep_counting(gw):
    for i in range(3):
        assert _post(gw["client"], f"q{i}").status_code == 200
    gw["db"].expire_all()
    assert sorted(s.step_number for s in gw["db"].query(Step).all()) == [1, 2, 3]


def test_session_cost_limit_blocks_the_next_request(gw):
    gw["key"].max_cost_usd = 0.015  # one gpt-4o call here costs about $0.0125
    gw["db"].commit()
    assert _post(gw["client"], "a").status_code == 200
    assert _post(gw["client"], "b").status_code == 200
    blocked = _post(gw["client"], "c")
    assert blocked.status_code == 429
    assert "Session cost limit exceeded" in blocked.text


def test_rate_limit_counts_in_memory(gw):
    gw["key"].max_requests_per_min = 2
    gw["db"].commit()
    assert _post(gw["client"], "a").status_code == 200
    assert _post(gw["client"], "b").status_code == 200
    blocked = _post(gw["client"], "c")
    assert blocked.status_code == 429
    assert "Rate limit exceeded" in blocked.text


def test_counters_seed_from_the_database_after_a_restart(gw):
    svc = GatewayService(gw["db"])
    session = svc.resolve_session(gw["key"], "s1")
    svc.log_request(gw["key"], session, "gpt-4o", 10, 10, 0.40, 5.0)
    svc.log_request(gw["key"], session, "gpt-4o", 10, 10, 0.40, 5.0)

    reset_gateway_state()  # what a process restart loses
    session = svc.resolve_session(gw["key"], "s1")
    assert svc.get_session_cost(session) == pytest.approx(0.80)
    assert svc.get_monthly_cost(gw["key"]) == pytest.approx(0.80)
    assert svc.next_step_number(session.run_id) == 3
    gw["key"].max_requests_per_min = 2
    allowed, reason = svc.check_rate_limit(gw["key"])
    assert allowed is False and "Rate limit exceeded" in reason
