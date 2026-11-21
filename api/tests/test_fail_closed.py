"""If the API goes down mid-run, the SDK keeps enforcing its limits locally.

This backs the public claim "if the control plane goes down, the SDK keeps
enforcing limits locally". Each test starts a run against the real API app,
logs steps while it is up, then makes every HTTP call fail and checks the
step limit, the cost limit and a deny rule still stop the run.
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
from steerplane.exceptions import CostLimitExceeded, PolicyViolationError, StepLimitExceeded
from steerplane.policy_engine import PolicyEngine
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


class _Switch:
    """Routes SDK HTTP calls into the API app until `down` is set."""

    def __init__(self, api: TestClient, run: RunManager):
        self.api, self.run, self.down, self.calls_after_down = api, run, False, 0
        run.client.session.request = self

    def __call__(self, method, url, timeout=None, **kwargs):
        if self.down:
            self.calls_after_down += 1
            raise requests.ConnectionError("API is down")
        r = self.api.request(method, url.replace(self.run.client.api_url, ""), **kwargs)
        resp = requests.Response()
        resp.status_code, resp._content, resp.url = r.status_code, r.content, url
        resp.headers.update(r.headers)
        return resp


def _run(api, **kw):
    run = RunManager(agent_name="bot", log_to_console=False, **kw)
    switch = _Switch(api, run)
    run.start()
    return run, switch


def test_step_limit_holds_when_api_goes_down(api):
    run, switch = _run(api, max_steps=5, max_cost_usd=100)
    run.log_step("a")
    run.log_step("b")
    assert api.get(f"/runs/{run.run_id}").json()["total_steps"] == 2  # API really was up

    switch.down = True
    run.log_step("c")
    run.log_step("d")
    run.log_step("e")
    with pytest.raises(StepLimitExceeded):
        run.log_step("f")
    assert not run.client.is_connected
    assert switch.calls_after_down == 1  # degraded once, no timeout per step


def test_cost_limit_holds_when_api_goes_down(api):
    run, switch = _run(api, max_cost_usd=1.0)
    run.log_step("a", cost=0.4)

    switch.down = True
    run.log_step("b", cost=0.4)
    with pytest.raises(CostLimitExceeded):
        run.log_step("c", cost=0.4)


def test_deny_rule_holds_when_api_goes_down(api):
    run, switch = _run(api, policy=PolicyEngine(denied_actions=["delete_*"]))
    run.log_step("read_file")

    switch.down = True
    with pytest.raises(PolicyViolationError):
        run.log_step("delete_user")


def test_run_that_starts_with_api_down_still_enforces(api):
    run = RunManager(agent_name="bot", log_to_console=False, max_steps=2)
    switch = _Switch(api, run)
    switch.down = True
    run.start()
    run.log_step("a")
    run.log_step("b")
    with pytest.raises(StepLimitExceeded):
        run.log_step("c")
