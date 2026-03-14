"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    APIKeyConfig,
    CreateKeyRequest,
    fetchAPIKeys,
    createAPIKey,
    updateAPIKey,
    deleteAPIKey,
} from "../../services/api";

// ─── Create Key Modal ─────────────────────────────────────

function CreateKeyModal({
    onClose,
    onCreated,
}: {
    onClose: () => void;
    onCreated: (key: APIKeyConfig) => void;
}) {
    const [name, setName] = useState("");
    const [maxCost, setMaxCost] = useState(50);
    const [maxMonthly, setMaxMonthly] = useState(500);
    const [rateLimit, setRateLimit] = useState(60);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) return;
        setLoading(true);
        try {
            const req: CreateKeyRequest = {
                name: name.trim(),
                max_cost_usd: maxCost,
                max_cost_monthly: maxMonthly,
                max_requests_per_min: rateLimit,
            };
            const created = await createAPIKey(req);
            onCreated(created);
        } catch (err) {
            console.error("Failed to create key:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <motion.div
                className="modal-content"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
            >
                <h2 className="modal-title">Create Gateway API Key</h2>
                <form onSubmit={handleSubmit} className="modal-form">
                    <div className="form-group">
                        <label>Key Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Production Agent, Dev Testing"
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
                                value={maxCost}
                                onChange={(e) => setMaxCost(Number(e.target.value))}
                                className="form-input"
                            />
                        </div>
                        <div className="form-group">
                            <label>Monthly Budget ($)</label>
                            <input
                                type="number"
                                step="1"
                                value={maxMonthly}
                                onChange={(e) => setMaxMonthly(Number(e.target.value))}
                                className="form-input"
                            />
                        </div>
                        <div className="form-group">
                            <label>Rate Limit (req/min)</label>
                            <input
                                type="number"
                                value={rateLimit}
                                onChange={(e) => setRateLimit(Number(e.target.value))}
                                className="form-input"
                            />
                        </div>
                    </div>
                    <div className="modal-actions">
                        <button type="button" onClick={onClose} className="btn btn-secondary">
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !name.trim()}
                            className="btn btn-primary"
                        >
                            {loading ? "Creating..." : "Create Key"}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

// ─── Raw Key Display (shown once after creation) ──────────

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
        <motion.div
            className="raw-key-banner"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
        >
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

// ─── Key Card ─────────────────────────────────────────────

function KeyCard({
    apiKey,
    onToggle,
    onDelete,
}: {
    apiKey: APIKeyConfig;
    onToggle: (id: string, active: boolean) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <motion.div
            className={`key-card ${!apiKey.is_active ? "key-card-inactive" : ""}`}
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
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
                    <span className="key-stat-value">{apiKey.total_tokens.toLocaleString()}</span>
                    <span className="key-stat-label">Tokens</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">${apiKey.max_cost_usd}</span>
                    <span className="key-stat-label">Session Limit</span>
                </div>
                <div className="key-stat">
                    <span className="key-stat-value">{apiKey.max_requests_per_min}/min</span>
                    <span className="key-stat-label">Rate Limit</span>
                </div>
            </div>

            <div className="key-card-footer">
                <span className="key-last-used">
                    {apiKey.last_used_at
                        ? `Last used: ${new Date(apiKey.last_used_at).toLocaleDateString()}`
                        : "Never used"}
                </span>
                <div className="key-card-actions">
                    <button
                        onClick={() => onToggle(apiKey.id, !apiKey.is_active)}
                        className={`btn btn-sm ${apiKey.is_active ? "btn-warning" : "btn-success"}`}
                    >
                        {apiKey.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                        onClick={() => onDelete(apiKey.id)}
                        className="btn btn-sm btn-danger"
                    >
                        Revoke
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

// ─── Main Page ────────────────────────────────────────────

export default function APIKeysPage() {
    const [keys, setKeys] = useState<APIKeyConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [rawKey, setRawKey] = useState<string | null>(null);

    const loadKeys = async () => {
        try {
            const data = await fetchAPIKeys();
            setKeys(data);
        } catch (err) {
            console.error("Failed to load keys:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadKeys();
    }, []);

    const handleCreated = (key: APIKeyConfig) => {
        setShowCreate(false);
        if (key.raw_key) {
            setRawKey(key.raw_key);
        }
        loadKeys();
    };

    const handleToggle = async (id: string, active: boolean) => {
        try {
            await updateAPIKey(id, { is_active: active });
            loadKeys();
        } catch (err) {
            console.error("Failed to toggle key:", err);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure? This will permanently revoke this API key.")) return;
        try {
            await deleteAPIKey(id);
            loadKeys();
        } catch (err) {
            console.error("Failed to delete key:", err);
        }
    };

    return (
        <main className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Gateway API Keys</h1>
                    <p className="page-subtitle">
                        Manage API keys for the SteerPlane Gateway. Each key includes built-in cost limits,
                        rate limiting, model policies, and automatic loop detection.
                    </p>
                </div>
                <button onClick={() => setShowCreate(true)} className="btn btn-primary">
                    + Create Key
                </button>
            </div>

            {/* Gateway usage instructions */}
            <div className="gateway-info-card">
                <h3>How to use the Gateway</h3>
                <p>Point your OpenAI client to the SteerPlane Gateway. Every LLM call is automatically monitored, limited, and logged.</p>
                <code className="gateway-code">
                    {`client = openai.OpenAI(base_url="http://localhost:8000/gateway/v1", api_key="sk_sp_...")`}
                </code>
            </div>

            {/* Raw key display */}
            <AnimatePresence>
                {rawKey && (
                    <RawKeyDisplay rawKey={rawKey} onDismiss={() => setRawKey(null)} />
                )}
            </AnimatePresence>

            {/* Create modal */}
            <AnimatePresence>
                {showCreate && (
                    <CreateKeyModal
                        onClose={() => setShowCreate(false)}
                        onCreated={handleCreated}
                    />
                )}
            </AnimatePresence>

            {/* Key list */}
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
