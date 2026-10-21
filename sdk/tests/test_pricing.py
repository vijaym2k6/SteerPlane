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
    # 106 models plus "default" (checked against the providers' pricing pages, 21 Oct 2026).
    assert len(MODEL_PRICING) == 107
    for key in ("gpt-4o", "claude-4-opus", "gemini-2.0-flash", "llama-3-70b", "mistral-large"):
        assert key in MODEL_PRICING


@pytest.mark.parametrize(
    "model,expected_input,expected_output",
    [
        # Dated API ids resolve to their model's row.
        ("gpt-4.1-2025-04-14", 2.0, 8.0),  # used to fall through to gpt-4 ($30/$60)
        ("gpt-4o-2024-08-06", 2.5, 10.0),
        ("gpt-5.2-2025-12-11", 1.75, 14.0),
        ("o3-2025-04-16", 2.0, 8.0),
        # Every text model id on the OpenAI, Anthropic, Google and Mistral pricing pages (21 Oct 2026).
        ("gpt-6-astra", 10.0, 50.0),
        ("gpt-6.1-sol", 2.0, 10.0),
        ("gpt-6-luna", 0.1, 0.5),
        ("gpt-6-sol", 2.0, 10.0),
        ("gpt-5.6-sol", 4.0, 20.0),
        ("gpt-5.6-terra", 2.0, 12.0),
        ("gpt-5.6-luna", 0.2, 1.2),
        ("gpt-5.6-cyber", 12.5, 75.0),
        ("gpt-5.5", 5.0, 30.0),
        ("gpt-5.5-pro", 30.0, 180.0),
        ("gpt-5.5-cyber", 12.5, 75.0),
        ("gpt-5.4", 2.5, 15.0),
        ("gpt-5.4-pro", 30.0, 180.0),
        ("gpt-5.4-mini", 0.75, 4.5),
        ("gpt-5.4-nano", 0.2, 1.25),
        ("gpt-5.3-codex", 1.75, 14.0),
        ("gpt-5.2", 1.75, 14.0),
        ("gpt-5.2-pro", 21.0, 168.0),
        ("gpt-5.1", 1.25, 10.0),
        ("gpt-5", 1.25, 10.0),
        ("gpt-5-mini", 0.25, 2.0),
        ("gpt-5-nano", 0.05, 0.4),
        ("gpt-5-pro", 15.0, 120.0),
        ("gpt-5-search-api", 1.25, 10.0),
        ("gpt-4.1", 2.0, 8.0),
        ("gpt-4.1-mini", 0.4, 1.6),
        ("gpt-4.1-nano", 0.1, 0.4),
        ("gpt-4o", 2.5, 10.0),
        ("gpt-4o-2024-05-13", 5.0, 15.0),
        ("gpt-4o-mini", 0.15, 0.6),
        ("o1", 15.0, 60.0),
        ("o1-pro", 150.0, 600.0),
        ("o3-pro", 20.0, 80.0),
        ("o3", 2.0, 8.0),
        ("o4-mini", 1.1, 4.4),
        ("o3-mini", 1.1, 4.4),
        ("gpt-4-turbo-2024-04-09", 10.0, 30.0),
        ("gpt-4-0613", 30.0, 60.0),
        ("gpt-3.5-turbo", 0.5, 1.5),
        ("gpt-3.5-turbo-0125", 0.5, 1.5),
        ("chat-latest", 5.0, 30.0),
        ("gpt-rosalind-research", 5.0, 25.0),
        ("gpt-rosalind-discovery", 5.0, 25.0),
        ("claude-fable-5-1", 10.0, 50.0),
        ("claude-fable-5", 10.0, 50.0),
        ("claude-mythos-5-1", 10.0, 50.0),
        ("claude-mythos-5", 10.0, 50.0),
        ("claude-opus-5-5", 4.0, 20.0),
        ("claude-opus-5", 5.0, 25.0),
        ("claude-opus-4-8", 5.0, 25.0),
        ("claude-opus-4-7", 5.0, 25.0),
        ("claude-opus-4-6", 5.0, 25.0),
        ("claude-opus-4-5-20251101", 5.0, 25.0),
        ("claude-opus-4-1-20250805", 15.0, 75.0),
        ("claude-opus-4-20250514", 15.0, 75.0),
        ("claude-sonnet-5-5", 2.0, 10.0),
        ("claude-sonnet-5", 2.0, 10.0),
        ("claude-sonnet-4-6", 3.0, 15.0),
        ("claude-sonnet-4-5-20250929", 3.0, 15.0),
        ("claude-sonnet-4-20250514", 3.0, 15.0),
        ("claude-haiku-5-5", 0.1, 0.5),
        ("claude-haiku-4-5-20251001", 1.0, 5.0),
        ("claude-3-5-haiku-20241022", 0.8, 4.0),
        ("gemini-4-argon", 2.0, 10.0),
        ("gemini-3.8-flash", 0.75, 3.75),
        ("gemini-3.6-flash", 0.75, 3.75),
        ("gemini-3.5-flash-lite", 0.3, 2.5),
        ("gemini-3.1-pro-preview", 2.0, 12.0),
        ("gemini-3.1-flash-lite", 0.25, 1.5),
        ("gemini-3-flash-preview", 0.5, 3.0),
        ("gemini-robotics-er-2-preview", 1.0, 5.0),
        ("gemini-2.5-pro", 1.25, 10.0),
        ("gemini-2.5-flash", 0.3, 2.5),
        ("gemini-2.5-flash-lite", 0.1, 0.4),
        ("mistral-large-4", 1.36, 4.18),
        ("mistral-large-2512", 0.5, 1.5),
        ("mistral-medium-3-5", 1.5, 7.5),
        ("mistral-small-2603", 0.15, 0.6),
        ("codestral-2508", 0.3, 0.9),
        ("ministral-14b-2512", 0.2, 0.2),
        ("ministral-8b-2512", 0.15, 0.15),
        ("ministral-3b-2512", 0.1, 0.1),
        # -latest aliases, priced as the current model of that family on 21 Oct 2026.
        ("gemini-pro-latest", 2.0, 12.0),
        ("gemini-flash-latest", 0.75, 3.75),
        ("gemini-flash-lite-latest", 0.3, 2.5),
        ("mistral-large-latest", 1.36, 4.18),
        ("mistral-medium-latest", 1.5, 7.5),
        ("mistral-small-latest", 0.15, 0.6),
        ("codestral-latest", 0.3, 0.9),
        ("ministral-14b-latest", 0.2, 0.2),
        ("ministral-8b-latest", 0.15, 0.15),
        ("ministral-3b-latest", 0.1, 0.1),
    ],
)
def test_real_model_ids_resolve_to_their_own_price(model, expected_input, expected_output):
    rates = MODEL_PRICING[normalize_model_name(model)]
    assert (rates["input"], rates["output"]) == (expected_input, expected_output)
