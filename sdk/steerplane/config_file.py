"""
SteerPlane SDK — Config File Discovery

Auto-discovers a .steerplane.yml (or .steerplane.yaml) in the project root
and applies its settings as defaults. Explicit decorator/constructor parameters
always take precedence over file-based config.

Config file search order:
  1. STEERPLANE_CONFIG env var (explicit path)
  2. .steerplane.yml in current directory
  3. .steerplane.yaml in current directory
  4. .steerplane.yml walking up to filesystem root

Example .steerplane.yml:
    api_url: http://localhost:8000
    agent_name: my_bot
    defaults:
      max_cost_usd: 25.0
      max_steps: 100
      max_runtime_sec: 1800
      enforcement: alert
      loop_window_size: 10
    policy:
      denied_actions:
        - "delete_*"
        - "drop_*"
      allowed_actions: []
      rate_limits:
        - pattern: "search_*"
          max_count: 10
          window_seconds: 60
      require_approval:
        - "refund_*"
    alerts:
      email: ops@company.com
      webhook_url: https://hooks.slack.com/...
      threshold: 0.8
      timeout_sec: 1800
"""

import os
from pathlib import Path
from typing import Any


_FILENAMES = (".steerplane.yml", ".steerplane.yaml")
_cached_config: dict[str, Any] | None = None


def _find_config_file() -> Path | None:
    """Walk up directories looking for .steerplane.yml."""
    # 1. Explicit env var
    env_path = os.getenv("STEERPLANE_CONFIG", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        return None

    # 2. Current directory and parents
    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        for name in _FILENAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate

    return None


def _parse_yaml(path: Path) -> dict[str, Any]:
    """Parse YAML config file. Returns empty dict on failure."""
    try:
        import yaml
    except ImportError:
        # PyYAML not installed — skip config file
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_config_file(force_reload: bool = False) -> dict[str, Any]:
    """
    Load and cache the .steerplane.yml config.

    Returns a flat dict with all values. Cached after first load.
    """
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    path = _find_config_file()
    if path is None:
        _cached_config = {}
        return _cached_config

    raw = _parse_yaml(path)

    # Flatten into a usable config dict
    defaults = raw.get("defaults", {})
    policy = raw.get("policy", {})
    alerts = raw.get("alerts", {})

    config = {
        # Top-level
        "api_url": raw.get("api_url"),
        "api_key": raw.get("api_key"),
        "agent_name": raw.get("agent_name"),
        "log_to_console": raw.get("log_to_console"),
        # Defaults
        "max_cost_usd": defaults.get("max_cost_usd"),
        "max_steps": defaults.get("max_steps"),
        "max_runtime_sec": defaults.get("max_runtime_sec"),
        "enforcement": defaults.get("enforcement"),
        "loop_window_size": defaults.get("loop_window_size"),
        "model": defaults.get("model"),
        # Policy
        "denied_actions": policy.get("denied_actions"),
        "allowed_actions": policy.get("allowed_actions"),
        "rate_limits": policy.get("rate_limits"),
        "require_approval": policy.get("require_approval"),
        # Alerts
        "alert_email": alerts.get("email"),
        "alert_webhook_url": alerts.get("webhook_url"),
        "alert_threshold": alerts.get("threshold"),
        "alert_timeout_sec": alerts.get("timeout_sec"),
    }

    # Remove None values — so explicit params always win
    _cached_config = {k: v for k, v in config.items() if v is not None}
    return _cached_config


def get_with_fallback(explicit_value: Any, config_key: str, default: Any = None) -> Any:
    """
    Return the explicit value if set, else the config file value, else the default.

    This is the merge function: decorator params > config file > hardcoded default.
    """
    if explicit_value is not None:
        return explicit_value
    file_config = load_config_file()
    return file_config.get(config_key, default)
