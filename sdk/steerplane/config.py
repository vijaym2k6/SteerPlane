"""
SteerPlane SDK — Configuration

Default settings and environment variable overrides.
"""

import os


class SteerPlaneConfig:
    """SDK configuration with environment variable overrides."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        agent_id: str | None = None,
        default_max_cost_usd: float = 50.0,
        default_max_steps: int = 200,
        default_max_runtime_sec: int = 3600,
        loop_window_size: int = 8,
        enable_telemetry: bool = True,
        log_to_console: bool = True,
    ):
        self.api_url = api_url or os.getenv("STEERPLANE_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("STEERPLANE_API_KEY", "")
        self.agent_id = agent_id or os.getenv("STEERPLANE_AGENT_ID", "default_agent")
        self.default_max_cost_usd = default_max_cost_usd
        self.default_max_steps = default_max_steps
        self.default_max_runtime_sec = default_max_runtime_sec
        self.loop_window_size = loop_window_size
        self.enable_telemetry = enable_telemetry
        self.log_to_console = log_to_console


# Global default config (can be overridden)
_config = SteerPlaneConfig()


def get_config() -> SteerPlaneConfig:
    """Get the current global configuration."""
    return _config


def configure(**kwargs) -> SteerPlaneConfig:
    """Update global SDK configuration."""
    global _config
    _config = SteerPlaneConfig(**kwargs)
    return _config
