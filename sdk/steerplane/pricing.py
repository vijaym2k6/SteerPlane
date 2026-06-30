"""
SteerPlane SDK — Canonical model pricing.

``model_pricing.json`` (USD per 1M tokens) is the single source of truth for
model costs. The API gateway ships a byte-identical copy at
``api/app/services/model_pricing.json`` and the TypeScript SDK mirrors it in
``sdk-ts/src/model-pricing.ts``; ``api/tests/test_pricing_consistency.py`` fails
if any of them drift. Edit pricing in one place and update the others to match.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

# Per-1M USD pricing → per-token, for callers that price token-by-token.
_PER_MILLION = 1_000_000


@lru_cache(maxsize=1)
def load_pricing() -> dict[str, dict[str, float]]:
    """Load the canonical per-1M pricing table (cached)."""
    raw = resources.files("steerplane").joinpath("model_pricing.json").read_text("utf-8")
    return json.loads(raw)


MODEL_PRICING: dict[str, dict[str, float]] = load_pricing()


def normalize_model_name(model: str) -> str:
    """Resolve a model name to its pricing key by longest matching prefix."""
    normalized = (model or "").lower().strip()
    for prefix in sorted(MODEL_PRICING, key=len, reverse=True):
        if prefix != "default" and normalized.startswith(prefix):
            return prefix
    return normalized


def price_per_token(model: str) -> dict[str, float]:
    """Per-token input/output price for a model (falls back to ``default``)."""
    pricing = MODEL_PRICING.get(normalize_model_name(model), MODEL_PRICING["default"])
    return {
        "input": pricing["input"] / _PER_MILLION,
        "output": pricing["output"] / _PER_MILLION,
    }


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost from token counts using the canonical per-1M table."""
    pricing = MODEL_PRICING.get(normalize_model_name(model), MODEL_PRICING["default"])
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / _PER_MILLION
    return round(cost, 8)
