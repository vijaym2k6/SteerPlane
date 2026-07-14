"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import {
    APIKeyConfig,
    CreateKeyRequest,
    createAPIKey,
    deleteAPIKey,
    fetchAPIKeys,
    updateAPIKey,
} from "../../services/api";
import { ADMIN_TOKEN_EVENT } from "@/services/admin-auth";

type KeyFormValues = {
    name: string;
    maxCost: number;
    maxMonthly: number;
    rateLimit: number;
    allowedModels: string;
    deniedModels: string;
};

function toFormValues(key?: APIKeyConfig | null): KeyFormValues {
    return {
        name: key?.name ?? "",
        maxCost: key?.max_cost_usd ?? 50,
        maxMonthly: key?.max_cost_monthly ?? 500,
        rateLimit: key?.max_requests_per_min ?? 60,
        allowedModels: key?.allowed_models ?? "",
        deniedModels: key?.denied_models ?? "",
    };
}

function toKeyRequest(values: KeyFormValues): CreateKeyRequest {
    return {
        name: values.name.trim(),
        max_cost_usd: values.maxCost,
        max_cost_monthly: values.maxMonthly,
        max_requests_per_min: values.rateLimit,
        allowed_models: values.allowedModels.trim() || null,
        denied_models: values.deniedModels.trim() || null,
    };
}

function KeyModal({
    mode,
    keyConfig,
    onClose,
    onSaved,
    onError,
}: {
    mode: "create" | "edit";
    keyConfig?: APIKeyConfig | null;
    onClose: () => void;
    onSaved: (key: APIKeyConfig) => void;
    onError: (message: string) => void;
}) {
    const [values, setValues] = useState<KeyFormValues>(() => toFormValues(keyConfig));
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        setValues(toFormValues(keyConfig));
    }, [keyConfig]);

    const title = mode === "create" ? "Create Gateway API Key" : "Edit Gateway API Key";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!values.name.trim()) return;

        setLoading(true);
        try {
            const payload = toKeyRequest(values);
            const saved = mode === "create"
                ? await createAPIKey(payload)
                : await updateAPIKey(keyConfig!.id, payload);
            onSaved(saved);
        } catch (err) {
            onError(err instanceof Error ? err.message : `Failed to ${mode} API key`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <motion.div
                className="modal-content modal-content-wide"
                initial={{ opacity: 0, scale: 0.96, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 12 }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="modal-header">
                    <div>
                        <h2 className="modal-title">{title}</h2>
                        <p className="modal-helper-text">
                            {mode === "create"
                                ? "Set cost and rate limits for this gateway key. Limits are enforced deterministically — kill mode terminates immediately on breach."
                                : "Update cost limits and gateway behavior without rotating the key."}
                        </p>
                    </div>
                    {keyConfig && <code className="key-prefix">{keyConfig.key_prefix}</code>}
                </div>

                <form onSubmit={handleSubmit} className="modal-form">
                    <div className="form-group">
                        <label>Key Name</label>
                        <input
                            type="text"
                            value={values.name}
                            onChange={(e) => setValues((prev) => ({ ...prev, name: e.target.value }))}
                            placeholder="e.g. Production Client Workloads"
                            className="form-input"
                            autoFocus
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Session Cost Limit ($)</label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={values.maxCost}
                                onChange={(e) => setValues((prev) => ({ ...prev, maxCost: Number(e.target.value) }))}
                                className="form-input"
                            />
                        </div>
                        <div className="form-group">
                            <label>Monthly Budget ($)</label>
                            <input
                                type="number"
                                step="1"
                                min="0"
                                value={values.maxMonthly}
                                onChange={(e) => setValues((prev) => ({ ...prev, maxMonthly: Number(e.target.value) }))}
                                className="form-input"
                            />
                        </div>
                        <div className="form-group">
                            <label>Rate Limit (req/min)</label>
                            <input
                                type="number"
                                min="1"
                                value={values.rateLimit}
                                onChange={(e) => setValues((prev) => ({ ...prev, rateLimit: Number(e.target.value) }))}
                                className="form-input"
                            />
                        </div>
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Allowed Models</label>
                            <input
                                type="text"
                                value={values.allowedModels}
                                onChange={(e) => setValues((prev) => ({ ...prev, allowedModels: e.target.value }))}
                                className="form-input"
                                placeholder="gpt-4o,gpt-4o-mini"
                            />
                        </div>
                        <div className="form-group">
                            <label>Denied Models</label>
                            <input
                                type="text"
                                value={values.deniedModels}
                                onChange={(e) => setValues((prev) => ({ ...prev, deniedModels: e.target.value }))}
                                className="form-input"
                                placeholder="o1,claude-4-opus"
                            />
                        </div>
                    </div>

                    <div className="modal-actions">
                        <button type="button" onClick={onClose} className="btn btn-secondary">
                            Cancel
                        </button>
                        <button type="submit" disabled={loading || !values.name.trim()} className="btn btn-primary">
                            {loading ? (mode === "create" ? "Creating..." : "Saving...") : (mode === "create" ? "Create Key" : "Save Changes")}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

function RawKeyDisplay({
    rawKey,
    onDismiss,
}: {
    rawKey: string;
    onDismiss: () => void;
}) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(rawKey);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <motion.div className="raw-key-banner" initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="raw-key-header">
                <span className="raw-key-icon">&#x1f511;</span>
                <strong>Save your API key now — it won&apos;t be shown again!</strong>
            </div>
            <div className="raw-key-value">
                <code>{rawKey}</code>
                <button onClick={handleCopy} className="btn btn-sm btn-copy">
                    {copied ? "Copied!" : "Copy"}
                </button>
            </div>
            <div className="raw-key-usage">
                <strong>Quick Start:</strong>
                <code className="raw-key-code-block">
                    {`import openai\nclient = openai.OpenAI(\n    base_url="http://localhost:8000/gateway/v1",\n    api_key="${rawKey}",\n    default_headers={"X-LLM-API-Key": "your-openai-key"}\n)`}
                </code>
            </div>
            <button onClick={onDismiss} className="btn btn-secondary raw-key-dismiss">
                I&apos;ve saved it
            </button>
        </motion.div>
    );
}

function KeyCard({
    apiKey,
    onEdit,
    onToggle,
    onDelete,
}: {
    apiKey: APIKeyConfig;
    onEdit: (key: APIKeyConfig) => void;
    onToggle: (id: string, active: boolean) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <motion.div
            className={`key-card ${!apiKey.is_active ? "key-card-inactive" : ""}`}
            layout
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -18 }}
        >
            <div className="key-card-header">
                <div className="key-card-title">
                    <h3>{apiKey.name}</h3>
                    <code className="key-prefix">{apiKey.key_prefix}</code>
                </div>
                <div className="key-card-badges">
                    <span className={`badge ${apiKey.is_active ? "badge-active" : "badge-inactive"}`}>
                        {apiKey.is_active ? "Active" : "Inactive"}
                    </span>
                </div>
            </div>

            <div className="key-card-stats">
                <div className="key-stat">
                    <span className="key-stat-value">{apiKey.total_requests.toLocaleString()}</span>
                    <span className="key-stat-label">Requests</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">${apiKey.total_cost.toFixed(4)}</span>
                    <span className="key-stat-label">Total Cost</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">${apiKey.max_cost_usd.toFixed(2)}</span>
                    <span className="key-stat-label">Session Limit</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">${apiKey.max_cost_monthly.toFixed(0)}</span>
                    <span className="key-stat-label">Monthly Budget</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">{apiKey.max_requests_per_min}/min</span>
                    <span className="key-stat-label">Rate Limit</span>
                </div>
            </div>

            <div className="key-config-grid">
                <div className="key-config-item">
                    <span className="key-config-label">Models</span>
                    <span className="key-config-value">
                        {apiKey.allowed_models
                            ? `allow ${apiKey.allowed_models}`
                            : apiKey.denied_models
                                ? `deny ${apiKey.denied_models}`
                                : "all models"}
                    </span>
                </div>
            </div>

            <div className="key-card-footer">
                <span className="key-last-used">
                    {apiKey.last_used_at
                        ? `Last used: ${new Date(apiKey.last_used_at).toLocaleString()}`
                        : "Never used"}
                </span>
                <div className="key-card-actions">
                    <button onClick={() => onEdit(apiKey)} className="btn btn-sm btn-secondary">
                        Edit
                    </button>
                    <button
                        onClick={() => onToggle(apiKey.id, !apiKey.is_active)}
                        className={`btn btn-sm ${apiKey.is_active ? "btn-warning" : "btn-success"}`}
                    >
                        {apiKey.is_active ? "Disable" : "Enable"}
                    </button>
                    <button onClick={() => onDelete(apiKey.id)} className="btn btn-sm btn-danger">
                        Revoke
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

export default function APIKeysPage() {
    const [keys, setKeys] = useState<APIKeyConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [editingKey, setEditingKey] = useState<APIKeyConfig | null>(null);
    const [rawKey, setRawKey] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const loadPageData = useCallback(async () => {
        try {
            const result = await fetchAPIKeys();
            setKeys(result);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load API keys");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadPageData();
        window.addEventListener(ADMIN_TOKEN_EVENT, loadPageData);
        return () => window.removeEventListener(ADMIN_TOKEN_EVENT, loadPageData);
    }, [loadPageData]);

    const summary = useMemo(() => {
        const active = keys.filter((key) => key.is_active).length;
        return [
            { label: "Total Keys", value: keys.length },
            { label: "Active", value: active },
        ];
    }, [keys]);

    const handleCreated = (key: APIKeyConfig) => {
        setShowCreate(false);
        setEditingKey(null);
        if (key.raw_key) {
            setRawKey(key.raw_key);
        }
        setError(null);
        void loadPageData();
    };

    const handleUpdated = () => {
        setEditingKey(null);
        setError(null);
        void loadPageData();
    };

    const handleToggle = async (id: string, active: boolean) => {
        try {
            await updateAPIKey(id, { is_active: active });
            await loadPageData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update API key");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure? This will permanently revoke this API key.")) return;
        try {
            await deleteAPIKey(id);
            await loadPageData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete API key");
        }
    };

    return (
        <main className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Gateway API Keys</h1>
                    <p className="page-subtitle">
                        Manage runtime budgets and rate limits for every gateway workload from one place.
                    </p>
                </div>
                <button onClick={() => setShowCreate(true)} className="btn btn-primary">
                    + Create Key
                </button>
            </div>

            <div className="gateway-info-card">
                <h3>How enforcement works</h3>
                <p>
                    Every key runs in <strong>kill mode</strong> — deterministic, immediate termination
                    when a cost, rate, or loop limit is breached. No LLM judges another LLM.
                </p>
                <code className="gateway-code">
                    {`client = openai.OpenAI(base_url="http://localhost:8000/gateway/v1", api_key="sk_sp_...")`}
                </code>
            </div>

            <div className="stats-row">
                {summary.map((item) => (
                    <div key={item.label} className="stat-card">
                        <div className="stat-label">{item.label}</div>
                        <div className="stat-value">{item.value}</div>
                    </div>
                ))}
            </div>

            {error && <div className="policy-error">{error}</div>}

            <AnimatePresence>
                {rawKey && <RawKeyDisplay rawKey={rawKey} onDismiss={() => setRawKey(null)} />}
            </AnimatePresence>

            <AnimatePresence>
                {showCreate && (
                    <KeyModal
                        mode="create"
                        onClose={() => setShowCreate(false)}
                        onSaved={handleCreated}
                        onError={setError}
                    />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {editingKey && (
                    <KeyModal
                        mode="edit"
                        keyConfig={editingKey}
                        onClose={() => setEditingKey(null)}
                        onSaved={() => handleUpdated()}
                        onError={setError}
                    />
                )}
            </AnimatePresence>

            {loading ? (
                <div className="loading-state">Loading API keys...</div>
            ) : keys.length === 0 ? (
                <div className="empty-state">
                    <h3>No API keys yet</h3>
                    <p>Create your first API key to start using the SteerPlane Gateway.</p>
                    <button onClick={() => setShowCreate(true)} className="btn btn-primary">
                        Create your first key
                    </button>
                </div>
            ) : (
                <div className="keys-grid">
                    <AnimatePresence>
                        {keys.map((key) => (
                            <KeyCard
                                key={key.id}
                                apiKey={key}
                                onEdit={setEditingKey}
                                onToggle={handleToggle}
                                onDelete={handleDelete}
                            />
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </main>
    );
}
