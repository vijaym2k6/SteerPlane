/**
 * SteerPlane SDK — Canonical model pricing (USD per 1M tokens).
 *
 * This MUST stay byte-identical to the SDK/API copies
 * (sdk/steerplane/model_pricing.json, api/app/services/model_pricing.json).
 * api/tests/test_pricing_consistency.py parses this object and fails if it
 * drifts. Edit pricing in one place and update the others to match.
 *
 * The object below is intentionally written as strict JSON (quoted keys, no
 * trailing commas) so the cross-language consistency test can parse it.
 */
export const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  "gpt-4o": { "input": 2.5, "output": 10.0 },
  "gpt-4o-mini": { "input": 0.15, "output": 0.6 },
  "gpt-4-turbo": { "input": 10.0, "output": 30.0 },
  "gpt-4": { "input": 30.0, "output": 60.0 },
  "gpt-3.5-turbo": { "input": 0.5, "output": 1.5 },
  "o1": { "input": 15.0, "output": 60.0 },
  "o1-mini": { "input": 3.0, "output": 12.0 },
  "o3-mini": { "input": 1.1, "output": 4.4 },
  "claude-3-opus": { "input": 15.0, "output": 75.0 },
  "claude-3-sonnet": { "input": 3.0, "output": 15.0 },
  "claude-3-haiku": { "input": 0.25, "output": 1.25 },
  "claude-3.5-sonnet": { "input": 3.0, "output": 15.0 },
  "claude-3.5-haiku": { "input": 0.8, "output": 4.0 },
  "claude-4-sonnet": { "input": 3.0, "output": 15.0 },
  "claude-4-opus": { "input": 15.0, "output": 75.0 },
  "gemini-pro": { "input": 0.25, "output": 0.5 },
  "gemini-1.5-pro": { "input": 1.25, "output": 5.0 },
  "gemini-1.5-flash": { "input": 0.075, "output": 0.3 },
  "gemini-2.0-flash": { "input": 0.1, "output": 0.4 },
  "llama-3-70b": { "input": 0.59, "output": 0.79 },
  "llama-3-8b": { "input": 0.05, "output": 0.08 },
  "mistral-large": { "input": 2.0, "output": 6.0 },
  "mistral-small": { "input": 0.2, "output": 0.6 },
  "default": { "input": 2.0, "output": 2.0 }
};

const PER_MILLION = 1_000_000;

/** Resolve a model name to its pricing key by longest matching prefix. */
export function normalizeModelName(model: string): string {
  const normalized = (model ?? "").toLowerCase().trim();
  const keys = Object.keys(MODEL_PRICING)
    .filter((k) => k !== "default")
    .sort((a, b) => b.length - a.length);
  for (const key of keys) {
    if (normalized.startsWith(key)) return key;
  }
  return normalized;
}

/** Per-token input/output price for a model (falls back to `default`). */
export function pricePerToken(model: string): { input: number; output: number } {
  const rates = MODEL_PRICING[normalizeModelName(model)] ?? MODEL_PRICING["default"];
  return { input: rates.input / PER_MILLION, output: rates.output / PER_MILLION };
}
