"""`steerplane runs kill` must stop a live SDK run, and must not wipe its totals.

The CLI kills a run by POSTing /runs/end with status "terminated". These tests
drive a real SDK RunManager against the real API app (in-memory DB) and check:
  1. the run's next logged step raises RunTerminatedError,
  2. the kill keeps the cost and step totals the run had already recorded.
"""

from __future__ import annotations

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.db.database import get_db
from api.app.main import app
from steerplane.exceptions import RunTerminatedError
from steerplane.run_manager import RunManager


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    app.dependency_overrides[get_db] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


def _route_sdk_to(api: TestClient, run: RunManager) -> None:
    """Send the SDK client's HTTP calls into the in-process API app."""

    def fake_request(method, url, timeout=None, **kwargs):
        path = url.replace(run.client.api_url, "")
        r = api.request(method, path, **kwargs)
        resp = requests.Response()
        resp.status_code = r.status_code
        resp._content = r.content
        resp.headers.update(r.headers)
        resp.url = url
        return resp

    run.client.session.request = fake_request


def _kill_like_cli(api: TestClient, run_id: str) -> None:
    # Exactly what `steerplane runs kill` sends (sdk/steerplane/cli.py).
    r = api.post(
        "/runs/end", json={"run_id": run_id, "status": "terminated", "error": "Killed via CLI"}
    )
    assert r.status_code == 200


def test_kill_stops_live_run_at_next_step(api):
    run = RunManager(agent_name="bot", max_cost_usd=10, log_to_console=False)
    _route_sdk_to(api, run)
    run.start()
    run.log_step("search", cost=0.01)

    _kill_like_cli(api, run.run_id)

    with pytest.raises(RunTerminatedError):
        run.log_step("search_again", cost=0.01)
    assert run.is_terminated
    # And it stays stopped.
    with pytest.raises(RunTerminatedError):
        run.check_before_step("anything")


def test_kill_keeps_recorded_totals(api):
    run = RunManager(agent_name="bot", max_cost_usd=10, log_to_console=False)
    _route_sdk_to(api, run)
    run.start()
    run.log_step("a", cost=0.25)
    run.log_step("b", cost=0.25)

    _kill_like_cli(api, run.run_id)

    data = api.get(f"/runs/{run.run_id}").json()
    assert data["status"] == "terminated"
    assert data["total_steps"] == 2
    assert data["total_cost"] == pytest.approx(0.5)


def test_steps_still_accepted_for_running_run(api):
    run = RunManager(agent_name="bot", max_cost_usd=10, log_to_console=False)
    _route_sdk_to(api, run)
    run.start()
    for i in range(3):
        run.log_step(f"step_{i}", cost=0.01)
    assert not run.is_terminated
