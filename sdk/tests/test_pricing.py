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
    # 83 models plus "default" (checked against the providers' pricing pages, 21 Oct 2026).
    assert len(MODEL_PRICING) == 84
    for key in ("gpt-4o", "claude-4-opus", "gemini-2.0-flash", "llama-3-70b", "mistral-large"):
        assert key in MODEL_PRICING


@pytest.mark.parametrize(
    "model,expected_input,expected_output",
    [
        # Real API ids, including dated ones, resolve to their own row.
        ("gpt-4.1-2025-04-14", 2.0, 8.0),  # used to fall through to gpt-4 ($30/$60)
        ("gpt-4o-2024-08-06", 2.5, 10.0),
        ("gpt-5.2-2025-12-11", 1.75, 14.0),
        ("o3-2025-04-16", 2.0, 8.0),
        ("claude-sonnet-5-5", 2.0, 10.0),
        ("claude-sonnet-4-5-20250929", 3.0, 15.0),
        ("claude-opus-4-20250514", 15.0, 75.0),
        ("gemini-3.8-flash", 0.75, 3.75),
        ("gemini-3.1-pro-preview", 2.0, 12.0),
    ],
)
def test_real_model_ids_resolve_to_their_own_price(model, expected_input, expected_output):
    rates = MODEL_PRICING[normalize_model_name(model)]
    assert (rates["input"], rates["output"]) == (expected_input, expected_output)
