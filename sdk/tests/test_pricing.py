"""SDK side of the pricing consistency check (#10).

Asserts the Python SDK resolves the canonical per-1M pricing correctly. The
cross-language identity of the pricing files (SDK / API / TS) and the gateway's
resolution are checked in api/tests/test_pricing_consistency.py.
"""

import pytest

from steerplane.pricing import MODEL_PRICING, calculate_cost, normalize_model_name


def _canonical_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    return round((input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000, 8)


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
def test_sdk_resolves_canonical_cost(model, input_tokens, output_tokens):
    assert calculate_cost(model, input_tokens, output_tokens) == pytest.approx(
        _canonical_cost(normalize_model_name(model), input_tokens, output_tokens), abs=1e-9
    )


def test_model_coverage_includes_all_providers():
    # All 24 canonical entries are present (the SDK used to price only 8).
    assert len(MODEL_PRICING) == 24
    for key in ("gpt-4o", "claude-4-opus", "gemini-2.0-flash", "llama-3-70b", "mistral-large"):
        assert key in MODEL_PRICING
