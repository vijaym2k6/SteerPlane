/**
 * Model ids SteerPlane knows, used to warn about typos in the API key form.
 *
 * Mirrors the keys of the canonical pricing table
 * (sdk/steerplane/model_pricing.json, minus "default").
 * api/tests/test_pricing_consistency.py parses this array and fails if it
 * drifts, so update it whenever a model is added or removed there. The array
 * is written as strict JSON so that test can read it.
 */
export const KNOWN_MODELS: string[] = [
    "gpt-6-astra",
    "gpt-6.1-sol",
    "gpt-6-sol",
    "gpt-6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.6-cyber",
    "gpt-5.5",
    "gpt-5.5-pro",
    "gpt-5.5-cyber",
    "gpt-5.4",
    "gpt-5.4-pro",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.3-codex",
    "gpt-5.2",
    "gpt-5.2-pro",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-pro",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "chat-latest",
    "gpt-rosalind-research",
    "gpt-rosalind-discovery",
    "o1",
    "o1-pro",
    "o1-mini",
    "o3",
    "o3-pro",
    "o3-mini",
    "o4-mini",
    "claude-fable-5-1",
    "claude-fable-5",
    "claude-mythos-5-1",
    "claude-mythos-5",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-opus-4-1",
    "claude-opus-4",
    "claude-sonnet-5-5",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-haiku-5-5",
    "claude-haiku-4-5",
    "claude-3-5-haiku",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "claude-3.5-sonnet",
    "claude-3.5-haiku",
    "claude-4-sonnet",
    "claude-4-opus",
    "gemini-4-argon",
    "gemini-robotics-er-2-preview",
    "gemini-pro-latest",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro",
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-pro",
    "llama-3-70b",
    "llama-3-8b",
    "mistral-large",
    "mistral-small",
    "mistral-large-4",
    "mistral-large-2512",
    "mistral-large-latest",
    "mistral-medium-3-5",
    "mistral-medium-latest",
    "mistral-small-2603",
    "mistral-small-latest",
    "codestral-2508",
    "codestral-latest",
    "ministral-14b-2512",
    "ministral-14b-latest",
    "ministral-8b-2512",
    "ministral-8b-latest",
    "ministral-3b-2512",
    "ministral-3b-latest"
];

/** Full list in the docs; the API key form links here from its warnings. */
export const SUPPORTED_MODELS_URL = "https://docs.steerplane.com/docs/supported-models";

export type ModelCheck =
    | { entry: string; kind: "unknown" }
    | { entry: string; kind: "matched-as"; model: string };

/* Dated or numbered snapshots of a known model, e.g. gpt-4o-2024-08-06 or
   claude-sonnet-4-5-20250929, resolve to that model and need no warning. */
const SNAPSHOT_SUFFIX = /^-(\d{4}-?\d{2}-?\d{2}|\d{3,})$/;

/**
 * Check a comma-separated model list the way the gateway reads it: an entry is
 * matched to the longest known id it starts with (case-insensitive).
 * Returns one item per entry that is unknown, or that the gateway would quietly
 * treat as a different model.
 */
export function checkModelList(csv: string): ModelCheck[] {
    const byLength = [...KNOWN_MODELS].sort((a, b) => b.length - a.length);
    const issues: ModelCheck[] = [];

    for (const raw of csv.split(",")) {
        const entry = raw.trim();
        if (!entry) continue;
        const normalized = entry.toLowerCase();
        const match = byLength.find((model) => normalized.startsWith(model));

        if (!match) {
            issues.push({ entry, kind: "unknown" });
        } else if (match !== normalized && !SNAPSHOT_SUFFIX.test(normalized.slice(match.length))) {
            issues.push({ entry, kind: "matched-as", model: match });
        }
    }
    return issues;
}
