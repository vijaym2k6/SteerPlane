"""Tests for the SteerPlane HTTP client's graceful degradation."""

import requests

from steerplane.client import SteerPlaneClient


def test_timeout_degrades_once_and_short_circuits(monkeypatch):
    """A hung/timing-out API must degrade the client once, not stall every call.

    Regression: read timeouts fell through to the generic handler that returned
    None without flipping the availability flag, so every subsequent step paid
    the full timeout again.
    """
    client = SteerPlaneClient(api_url="http://localhost:8000")

    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        raise requests.Timeout("read timed out")

    monkeypatch.setattr(client.session, "request", fake_request)

    # First call hits the network, times out, and degrades.
    assert client.start_run(run_id="r1", agent_name="bot") is None
    assert client.is_connected is False
    assert calls["count"] == 1

    # Subsequent calls short-circuit without touching the network again.
    assert client.log_step(run_id="r1", step_number=1, action="step") is None
    assert calls["count"] == 1


def test_connection_error_degrades(monkeypatch):
    """Connection errors also degrade the client to offline mode."""
    client = SteerPlaneClient(api_url="http://localhost:8000")

    def fake_request(*args, **kwargs):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(client.session, "request", fake_request)

    assert client.start_run(run_id="r1", agent_name="bot") is None
    assert client.is_connected is False
