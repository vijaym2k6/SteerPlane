"""
SteerPlane CLI — Command-line interface for SteerPlane.

Install:  pip install steerplane[cli]
Usage:    steerplane --help

Commands:
    status          Check if the API server is healthy
    runs list       List recent agent runs
    runs inspect    View full detail for a run
    runs kill       Force-terminate a live run
    keys create     Generate a new API key
    keys list       List all API keys
    logs            Stream live telemetry (polling)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import click
except ImportError:
    print(
        "SteerPlane CLI requires 'click'. Install with:\n"
        "  pip install steerplane[cli]"
    )
    sys.exit(1)

import requests

from . import __version__


def _api_url() -> str:
    return os.getenv("STEERPLANE_API_URL", "http://localhost:8000").rstrip("/")


def _admin_token() -> str:
    return os.getenv("STEERPLANE_ADMIN_TOKEN", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    token = _admin_token()
    if token:
        h["X-SteerPlane-Admin-Token"] = token
    return h


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{_api_url()}{path}"
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        click.echo(click.style(f"[X] Cannot connect to {_api_url()}", fg="red"))
        sys.exit(1)
    except requests.HTTPError as e:
        click.echo(click.style(f"[X] HTTP {e.response.status_code}: {e.response.text}", fg="red"))
        sys.exit(1)


def _post(path: str, data: dict | None = None) -> dict:
    url = f"{_api_url()}{path}"
    try:
        resp = requests.post(url, headers=_headers(), json=data or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        click.echo(click.style(f"[X] Cannot connect to {_api_url()}", fg="red"))
        sys.exit(1)
    except requests.HTTPError as e:
        click.echo(click.style(f"[X] HTTP {e.response.status_code}: {e.response.text}", fg="red"))
        sys.exit(1)


def _delete(path: str) -> dict:
    url = f"{_api_url()}{path}"
    try:
        resp = requests.delete(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        click.echo(click.style(f"[X] Cannot connect to {_api_url()}", fg="red"))
        sys.exit(1)
    except requests.HTTPError as e:
        click.echo(click.style(f"[X] HTTP {e.response.status_code}: {e.response.text}", fg="red"))
        sys.exit(1)


# ─── Root Group ──────────────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="steerplane")
def cli():
    """SteerPlane — Agent Control Plane for Autonomous Systems."""
    pass


# ─── status ──────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Check if the SteerPlane API server is healthy."""
    data = _get("/health")
    click.echo(click.style("[OK] SteerPlane API is healthy", fg="green"))
    click.echo(f"  Service:  {data.get('service', '?')}")
    click.echo(f"  Version:  {data.get('version', '?')}")
    click.echo(f"  API URL:  {_api_url()}")


# ─── runs ────────────────────────────────────────────────────────────────

@cli.group()
def runs():
    """Manage agent runs."""
    pass


@runs.command("list")
@click.option("--limit", "-n", default=20, help="Number of runs to show")
@click.option("--status", "-s", "run_status", default=None, help="Filter by status")
def runs_list(limit, run_status):
    """List recent agent runs."""
    params = {"limit": limit}
    if run_status:
        params["status"] = run_status

    data = _get("/runs", params)
    runs_data = data if isinstance(data, list) else data.get("runs", [])

    if not runs_data:
        click.echo(click.style("No runs found.", fg="yellow"))
        return

    # Header
    click.echo(
        f"{'ID':<36}  {'Agent':<20}  {'Status':<12}  {'Cost':>8}  {'Steps':>6}  {'Started':<20}"
    )
    click.echo("-" * 110)

    for run in runs_data[:limit]:
        run_id = str(run.get("id", run.get("run_id", "?")))[:36]
        agent = (run.get("agent_id", run.get("agent_name", "?")) or "?")[:20]
        status = run.get("status", "?")
        cost = run.get("total_cost_usd", run.get("cost_usd", 0)) or 0
        steps = run.get("step_count", run.get("steps", 0)) or 0
        started = run.get("started_at", run.get("created_at", "?"))

        status_color = {
            "running": "cyan",
            "completed": "green",
            "terminated": "red",
            "paused": "yellow",
        }.get(status, "white")

        click.echo(
            f"{run_id:<36}  {agent:<20}  "
            f"{click.style(status, fg=status_color):<21}  "
            f"${cost:>7.4f}  {steps:>5}   {str(started)[:20]}"
        )


@runs.command("inspect")
@click.argument("run_id")
def runs_inspect(run_id):
    """View full detail for a specific run."""
    data = _get(f"/runs/{run_id}")

    click.echo(click.style(f"\n=== Run: {run_id} ===", fg="cyan", bold=True))
    click.echo(f"  Agent:       {data.get('agent_id', '?')}")
    click.echo(f"  Status:      {data.get('status', '?')}")
    click.echo(f"  Cost:        ${data.get('total_cost_usd', 0):.6f}")
    click.echo(f"  Steps:       {data.get('step_count', 0)}")
    click.echo(f"  Started:     {data.get('started_at', '?')}")
    click.echo(f"  Ended:       {data.get('ended_at', 'still running')}")

    if data.get("termination_reason"):
        click.echo(
            click.style(f"  Terminated:  {data['termination_reason']}", fg="red")
        )

    steps = data.get("steps", [])
    if steps:
        click.echo(f"\n  {'#':<4}  {'Action':<30}  {'Cost':>8}  {'Tokens':>7}  {'Latency':>8}")
        click.echo("  " + "-" * 75)
        for i, step in enumerate(steps, 1):
            action = (step.get("action", step.get("action_name", "?")) or "?")[:30]
            cost = step.get("cost_usd", 0) or 0
            tokens = step.get("total_tokens", step.get("tokens", 0)) or 0
            latency = step.get("latency_ms", 0) or 0
            click.echo(
                f"  {i:<4}  {action:<30}  ${cost:>7.4f}  {tokens:>6}  {latency:>6.0f}ms"
            )


@runs.command("kill")
@click.argument("run_id")
@click.option("--reason", "-r", default="Killed via CLI", help="Termination reason")
@click.confirmation_option(prompt="Are you sure you want to kill this run?")
def runs_kill(run_id, reason):
    """Force-terminate a live run."""
    data = _post(f"/runs/end", {"run_id": run_id, "status": "terminated", "error": reason})
    click.echo(click.style(f"[OK] Run {run_id} terminated", fg="green"))


# ─── keys ────────────────────────────────────────────────────────────────

@cli.group()
def keys():
    """Manage API keys."""
    pass


@keys.command("list")
def keys_list():
    """List all API keys."""
    data = _get("/api-keys/")
    keys_data = data if isinstance(data, list) else data.get("keys", [])

    if not keys_data:
        click.echo(click.style("No API keys found.", fg="yellow"))
        return

    click.echo(
        f"{'Name':<25}  {'Key Prefix':<20}  {'Active':<8}  {'Requests':>10}  {'Monthly Cost':>12}"
    )
    click.echo("-" * 85)

    for key in keys_data:
        name = (key.get("name", "?") or "?")[:25]
        prefix = (key.get("key_prefix", key.get("key", "?")) or "?")[:20]
        active = "[OK]" if key.get("is_active", True) else "[X]"
        requests_count = key.get("total_requests", 0) or 0
        monthly_cost = key.get("monthly_cost_usd", 0) or 0
        active_color = "green" if key.get("is_active", True) else "red"

        click.echo(
            f"{name:<25}  {prefix:<20}  "
            f"{click.style(active, fg=active_color):<17}  "
            f"{requests_count:>9}  ${monthly_cost:>10.4f}"
        )


@keys.command("create")
@click.option("--name", "-n", required=True, help="Key name/label")
@click.option("--max-cost", type=float, default=None, help="Monthly cost limit (USD)")
@click.option("--max-rpm", type=int, default=None, help="Max requests per minute")
def keys_create(name, max_cost, max_rpm):
    """Generate a new API key."""
    payload = {"name": name}
    if max_cost is not None:
        payload["max_cost_monthly"] = max_cost
    if max_rpm is not None:
        payload["rate_limit_rpm"] = max_rpm

    data = _post("/api-keys/", payload)

    click.echo(click.style("\n[OK] API Key Created", fg="green", bold=True))
    click.echo(f"  Name:    {name}")
    if "key" in data:
        click.echo(click.style(f"  Key:     {data['key']}", fg="yellow", bold=True))
        click.echo(
            click.style(
                "  [!] Save this key now — it cannot be retrieved again.",
                fg="red",
            )
        )
    click.echo(f"  ID:      {data.get('id', '?')}")


@keys.command("revoke")
@click.argument("key_id")
@click.confirmation_option(prompt="Are you sure you want to revoke this key?")
def keys_revoke(key_id):
    """Revoke (deactivate) an API key."""
    data = _delete(f"/api-keys/{key_id}")
    click.echo(click.style(f"[OK] API key {key_id} revoked", fg="green"))


# ─── logs ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--tail", "-f", is_flag=True, help="Continuously poll for new events")
@click.option("--interval", default=2, help="Poll interval in seconds (with --tail)")
def logs(tail, interval):
    """Stream live telemetry events."""
    seen_ids = set()

    def fetch_and_display():
        data = _get("/runs", {"limit": 5, "status": "running"})
        runs_data = data if isinstance(data, list) else data.get("runs", [])

        for run in runs_data:
            run_id = run.get("id", run.get("run_id"))
            if not run_id:
                continue

            agent = run.get("agent_id", run.get("agent_name", "?"))
            cost = run.get("total_cost_usd", 0) or 0
            steps = run.get("step_count", 0) or 0
            status = run.get("status", "?")

            event_key = f"{run_id}:{steps}"
            if event_key not in seen_ids:
                seen_ids.add(event_key)
                ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                status_color = {"running": "cyan", "terminated": "red"}.get(
                    status, "white"
                )
                click.echo(
                    f"[{ts}] "
                    f"{click.style(agent, fg='white', bold=True)} "
                    f"steps={steps} cost=${cost:.4f} "
                    f"{click.style(status, fg=status_color)}"
                )

    try:
        fetch_and_display()
        if tail:
            click.echo(click.style(f"Polling every {interval}s... (Ctrl+C to stop)", fg="yellow"))
            while True:
                time.sleep(interval)
                fetch_and_display()
    except KeyboardInterrupt:
        click.echo("\nStopped.")


# ─── Entry point ─────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
