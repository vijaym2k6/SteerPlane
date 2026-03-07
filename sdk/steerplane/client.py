"""
SteerPlane SDK — API Client

HTTP client that communicates with the SteerPlane API server.
Handles run lifecycle: start → log steps → end.
"""

import requests
import logging
from typing import Any

from .config import get_config
from .exceptions import APIConnectionError

logger = logging.getLogger("steerplane")


class SteerPlaneClient:
    """
    HTTP client for the SteerPlane API.
    
    Sends run events, step telemetry, and receives commands.
    Gracefully degrades if API is unavailable (SDK still works locally).
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        config = get_config()
        self.api_url = (api_url or config.api_url).rstrip("/")
        self.api_key = api_key or config.api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "SteerPlane-SDK/0.1.0",
        })
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

        self._api_available = True

    def _request(self, method: str, path: str, **kwargs) -> dict | None:
        """Make an HTTP request to the API. Returns None if API unavailable."""
        if not self._api_available:
            return None

        url = f"{self.api_url}{path}"
        try:
            response = self.session.request(method, url, timeout=5, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError:
            self._api_available = False
            logger.warning(
                f"⚠️  SteerPlane API not reachable at {self.api_url}. "
                f"Running in offline mode (guards still active, no dashboard data)."
            )
            return None
        except requests.RequestException as e:
            logger.warning(f"⚠️  API request failed: {e}")
            return None

    def start_run(
        self,
        run_id: str,
        agent_name: str,
        max_cost_usd: float = 0,
        max_steps: int = 0,
    ) -> dict | None:
        """Register a new run with the API."""
        return self._request("POST", "/runs/start", json={
            "run_id": run_id,
            "agent_name": agent_name,
            "max_cost_usd": max_cost_usd,
            "max_steps": max_steps,
        })

    def log_step(
        self,
        run_id: str,
        step_number: int,
        action: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        status: str = "completed",
        error: str | None = None,
        metadata: dict | None = None,
    ) -> dict | None:
        """Log a step event to the API."""
        return self._request("POST", "/runs/step", json={
            "run_id": run_id,
            "step_number": step_number,
            "action": action,
            "tokens": tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "status": status,
            "error": error,
            "metadata": metadata or {},
        })

    def end_run(
        self,
        run_id: str,
        status: str = "completed",
        total_cost: float = 0.0,
        total_steps: int = 0,
        error: str | None = None,
    ) -> dict | None:
        """Finalize a run."""
        return self._request("POST", "/runs/end", json={
            "run_id": run_id,
            "status": status,
            "total_cost": total_cost,
            "total_steps": total_steps,
            "error": error,
        })

    def get_run(self, run_id: str) -> dict | None:
        """Fetch run details."""
        return self._request("GET", f"/runs/{run_id}")

    def list_runs(self, limit: int = 50, offset: int = 0) -> dict | None:
        """List recent runs."""
        return self._request("GET", f"/runs?limit={limit}&offset={offset}")

    @property
    def is_connected(self) -> bool:
        """Check if API is reachable."""
        return self._api_available
