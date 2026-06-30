"""Cross-language pricing consistency (#10).

The canonical model pricing lives in sdk/steerplane/model_pricing.json. The API
gateway and the TypeScript SDK ship mirrors; this test fails if any of the three
drift, and asserts the Python SDK and the gateway resolve identical USD costs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Repo root = three levels up from this file (api/tests/<file>).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SDK_JSON = _REPO_ROOT / "sdk" / "steerplane" / "model_pricing.json"
_API_JSON = _REPO_ROOT / "api" / "app" / "services" / "model_pricing.json"
_TS_FILE = _REPO_ROOT / "sdk-ts" / "src" / "model-pricing.ts"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def _parse_ts_pricing(path: Path) -> dict:
    """Extract the MODEL_PRICING object literal from the TS mirror as JSON."""
    text = path.read_text("utf-8")
    match = re.search(r"MODEL_PRICING[^=]*=\s*(\{.*?\})\s*;", text, re.DOTALL)
    assert match, "Could not find MODEL_PRICING object in the TS mirror"
    return json.loads(match.group(1))


def test_sdk_api_and_ts_pricing_are_identical():
    sdk = _load_json(_SDK_JSON)
    api = _load_json(_API_JSON)
    ts = _parse_ts_pricing(_TS_FILE)

    assert sdk == api, "SDK and API pricing tables differ"
    assert sdk == ts, "SDK and TS pricing tables differ"
    assert "default" in sdk


@pytest.mark.parametrize(
    "model,input_tokens,output_tokens",
    [
        ("gpt-4o", 1000, 500),
        ("claude-3-opus", 2000, 1200),
        ("gemini-1.5-flash", 333, 777),
        ("llama-3-70b", 10_000, 0),
        ("an-unknown-model", 1000, 1000),  # falls back to "default"
    ],
)
def test_sdk_and_gateway_resolve_identical_cost(model, input_tokens, output_tokens):
    from api.app.services.gateway_service import (
        calculate_cost as gw_cost,
        normalize_model_name as gw_norm,
    )
    from steerplane.pricing import calculate_cost as sdk_cost, normalize_model_name as sdk_norm

    assert sdk_norm(model) == gw_norm(model)
    gateway = gw_cost(gw_norm(model), input_tokens, output_tokens)
    sdk = sdk_cost(model, input_tokens, output_tokens)
    assert sdk == pytest.approx(gateway, abs=1e-9)
