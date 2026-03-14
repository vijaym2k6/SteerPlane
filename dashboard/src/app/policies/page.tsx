"use client";

import React, { useEffect, useState, useCallback } from "react";
import type { PolicyConfig, RateLimitSpec } from "@/services/api";
import {
    fetchPolicies,
    createPolicy,
    updatePolicy,
    deletePolicy,
} from "@/services/api";

/* ═══════════════════════════════════════════════════════
   Helper — empty policy object
   ═══════════════════════════════════════════════════════ */
function emptyPolicy(): PolicyConfig {
    return {
        name: "",
        allowed_actions: [],
        denied_actions: [],
        rate_limits: [],
        require_approval: [],
        is_active: true,
    };
}

/* ═══════════════════════════════════════════════════════
   Chip component for pattern lists
   ═══════════════════════════════════════════════════════ */
function PatternChips({
    label,
    patterns,
    onChange,
}: {
    label: string;
    patterns: string[];
    onChange: (p: string[]) => void;
}) {
    const [draft, setDraft] = useState("");

    const add = () => {
        const trimmed = draft.trim();
        if (trimmed && !patterns.includes(trimmed)) {
            onChange([...patterns, trimmed]);
        }
        setDraft("");
    };

    return (
        <div className="policy-field">
            <label>{label}</label>
            <div className="policy-chips">
                {patterns.map((p) => (
                    <span key={p} className="policy-chip">
                        {p}
                        <button
                            onClick={() =>
                                onChange(patterns.filter((x) => x !== p))
                            }
                        >
                            ×
                        </button>
                    </span>
                ))}
            </div>
            <div className="policy-chip-input">
                <input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
                    placeholder="e.g. delete_* or send_email"
                />
                <button className="btn-sm" onClick={add}>
                    Add
                </button>
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════
   Rate-limit editor
   ═══════════════════════════════════════════════════════ */
function RateLimitsEditor({
    limits,
    onChange,
}: {
    limits: RateLimitSpec[];
    onChange: (l: RateLimitSpec[]) => void;
}) {
    const [draft, setDraft] = useState<RateLimitSpec>({
        pattern: "",
        max_count: 10,
        window_seconds: 60,
    });

    const add = () => {
        if (!draft.pattern.trim()) return;
        onChange([...limits, { ...draft, pattern: draft.pattern.trim() }]);
        setDraft({ pattern: "", max_count: 10, window_seconds: 60 });
    };

    return (
        <div className="policy-field">
            <label>Rate Limits</label>
            {limits.length > 0 && (
                <table className="rl-table">
                    <thead>
                        <tr>
                            <th>Pattern</th>
                            <th>Max Calls</th>
                            <th>Window (s)</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {limits.map((rl, i) => (
                            <tr key={i}>
                                <td>{rl.pattern}</td>
                                <td>{rl.max_count}</td>
                                <td>{rl.window_seconds}</td>
                                <td>
                                    <button
                                        className="btn-sm btn-danger"
                                        onClick={() =>
                                            onChange(
                                                limits.filter((_, j) => j !== i)
                                            )
                                        }
                                    >
                                        ×
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
            <div className="rl-add">
                <input
                    placeholder="Pattern"
                    value={draft.pattern}
                    onChange={(e) =>
                        setDraft({ ...draft, pattern: e.target.value })
                    }
                />
                <input
                    type="number"
                    placeholder="Max"
                    value={draft.max_count}
                    min={1}
                    onChange={(e) =>
                        setDraft({
                            ...draft,
                            max_count: parseInt(e.target.value) || 1,
                        })
                    }
                />
                <input
                    type="number"
                    placeholder="Window (s)"
                    value={draft.window_seconds}
                    min={1}
                    onChange={(e) =>
                        setDraft({
                            ...draft,
                            window_seconds: parseInt(e.target.value) || 1,
                        })
                    }
                />
                <button className="btn-sm" onClick={add}>
                    Add
                </button>
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════
   Policy Card
   ═══════════════════════════════════════════════════════ */
function PolicyCard({
    policy,
    onSave,
    onDelete,
    isNew,
}: {
    policy: PolicyConfig;
    onSave: (p: PolicyConfig) => void;
    onDelete?: () => void;
    isNew?: boolean;
}) {
    const [local, setLocal] = useState<PolicyConfig>({ ...policy });
    const [saving, setSaving] = useState(false);
    const [expanded, setExpanded] = useState(isNew ?? false);

    const save = async () => {
        setSaving(true);
        await onSave(local);
        setSaving(false);
        if (isNew) setLocal(emptyPolicy());
    };

    const ruleCount =
        local.allowed_actions.length +
        local.denied_actions.length +
        local.rate_limits.length +
        local.require_approval.length;

    return (
        <div className={`policy-card ${!local.is_active ? "inactive" : ""}`}>
            <div className="policy-card-header" onClick={() => setExpanded(!expanded)}>
                <div className="policy-card-title">
                    <span className="policy-icon">🛡️</span>
                    {isNew ? (
                        <input
                            className="agent-name-input"
                            placeholder="Policy name…"
                            value={local.name}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) =>
                                setLocal({ ...local, name: e.target.value })
                            }
                        />
                    ) : (
                        <span className="agent-name">{local.name}</span>
                    )}
                </div>
                <div className="policy-card-meta">
                    <span className="rule-count">{ruleCount} rules</span>
                    <span className={`status-dot ${local.is_active ? "active" : ""}`} />
                    <span className="expand-icon">{expanded ? "▲" : "▼"}</span>
                </div>
            </div>

            {expanded && (
                <div className="policy-card-body">
                    {/* Description field */}
                    <div className="policy-field">
                        <label>Description</label>
                        <input
                            className="form-input"
                            style={{ width: "100%" }}
                            value={local.description ?? ""}
                            onChange={(e) =>
                                setLocal({ ...local, description: e.target.value })
                            }
                            placeholder="Optional description…"
                        />
                    </div>
                    <PatternChips
                        label="Allowed Actions"
                        patterns={local.allowed_actions}
                        onChange={(p) => setLocal({ ...local, allowed_actions: p })}
                    />
                    <PatternChips
                        label="Denied Actions"
                        patterns={local.denied_actions}
                        onChange={(p) => setLocal({ ...local, denied_actions: p })}
                    />
                    <RateLimitsEditor
                        limits={local.rate_limits}
                        onChange={(l) => setLocal({ ...local, rate_limits: l })}
                    />
                    <PatternChips
                        label="Require Approval"
                        patterns={local.require_approval}
                        onChange={(p) => setLocal({ ...local, require_approval: p })}
                    />
                    <div className="policy-field toggle-row">
                        <label>
                            <input
                                type="checkbox"
                                checked={local.is_active}
                                onChange={(e) =>
                                    setLocal({ ...local, is_active: e.target.checked })
                                }
                            />
                            Policy Active
                        </label>
                    </div>
                    <div className="policy-card-actions">
                        <button
                            className="btn-primary"
                            onClick={save}
                            disabled={saving || !local.name.trim()}
                        >
                            {saving ? "Saving…" : isNew ? "Create Policy" : "Save Changes"}
                        </button>
                        {onDelete && (
                            <button className="btn-danger" onClick={onDelete}>
                                Delete
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ═══════════════════════════════════════════════════════
   Policies Page
   ═══════════════════════════════════════════════════════ */
export default function PoliciesPage() {
    const [policies, setPolicies] = useState<PolicyConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            const data = await fetchPolicies();
            setPolicies(data);
            setError(null);
        } catch {
            // If backend doesn't support policies yet, show empty
            setPolicies([]);
            setError(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const handleCreate = async (p: PolicyConfig) => {
        try {
            await createPolicy(p);
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Create failed");
        }
    };

    const handleUpdate = async (p: PolicyConfig) => {
        if (!p.id) return;
        try {
            await updatePolicy(p.id, p);
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Update failed");
        }
    };

    const handleDelete = async (policyId: string) => {
        try {
            await deletePolicy(policyId);
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Delete failed");
        }
    };

    return (
        <main className="policies-page">
            <div className="policies-header">
                <div>
                    <h1>🛡️ Policy Management</h1>
                    <p className="policies-subtitle">
                        Configure action allow/deny lists, rate limits, and
                        approval requirements per agent.
                    </p>
                </div>
            </div>

            {error && <div className="policy-error">{error}</div>}

            {/* New Policy */}
            <section className="policy-section">
                <h2>Create New Policy</h2>
                <PolicyCard
                    policy={emptyPolicy()}
                    onSave={handleCreate}
                    isNew
                />
            </section>

            {/* Existing Policies */}
            <section className="policy-section">
                <h2>
                    Existing Policies{" "}
                    <span className="count-badge">{policies.length}</span>
                </h2>
                {loading ? (
                    <div className="loading-spinner">Loading…</div>
                ) : policies.length === 0 ? (
                    <div className="empty-state">
                        <p>No policies configured yet.</p>
                        <p>
                            Create one above or configure them via the SDK with{" "}
                            <code>policy</code> options.
                        </p>
                    </div>
                ) : (
                    <div className="policy-list">
                        {policies.map((p) => (
                            <PolicyCard
                                key={p.id ?? p.name}
                                policy={p}
                                onSave={handleUpdate}
                                onDelete={() => p.id && handleDelete(p.id)}
                            />
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}
