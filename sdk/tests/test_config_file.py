"""Tests for .steerplane.yml loading."""

import pytest

from steerplane.config_file import load_config_file

yaml = pytest.importorskip("yaml")


@pytest.fixture
def load(tmp_path, monkeypatch):
    def _load(text: str) -> dict:
        path = tmp_path / ".steerplane.yml"
        path.write_text(text, encoding="utf-8")
        monkeypatch.setenv("STEERPLANE_CONFIG", str(path))
        monkeypatch.setattr("steerplane.config_file._cached_config", None)
        return load_config_file(force_reload=True)

    return _load


def test_limits_under_defaults(load):
    cfg = load("defaults:\n  max_cost_usd: 10.0\n  max_steps: 100\n")
    assert cfg["max_cost_usd"] == 10.0
    assert cfg["max_steps"] == 100


def test_limits_at_top_level_are_not_ignored(load):
    """The form older docs showed. It used to be dropped silently."""
    cfg = load("max_cost_usd: 10.0\nmax_steps: 100\nmax_runtime_sec: 600\n")
    assert cfg["max_cost_usd"] == 10.0
    assert cfg["max_steps"] == 100
    assert cfg["max_runtime_sec"] == 600


def test_defaults_section_wins_over_top_level(load):
    cfg = load("max_cost_usd: 99.0\ndefaults:\n  max_cost_usd: 10.0\n")
    assert cfg["max_cost_usd"] == 10.0


def test_false_under_defaults_is_kept(load):
    cfg = load("detect_loops: true\ndefaults:\n  detect_loops: false\n")
    assert cfg["detect_loops"] is False


def test_empty_sections_do_not_crash(load):
    cfg = load("defaults:\npolicy:\nalerts:\nagent_name: bot\n")
    assert cfg["agent_name"] == "bot"
    assert "max_cost_usd" not in cfg
