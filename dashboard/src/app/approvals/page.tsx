"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import {
    ApprovalRequest,
    approveRequest,
    denyRequest,
    fetchApprovals,
} from "@/services/api";
import { ADMIN_TOKEN_EVENT } from "@/services/admin-auth";

type ApprovalView = "pending" | "resolved" | "all";

function formatRemaining(expiresAt: string) {
    const ms = new Date(expiresAt).getTime() - Date.now();
    if (ms <= 0) return "Expired";
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}m ${sec}s`;
}

function formatValue(approval: ApprovalRequest) {
    if (approval.unit === "usd") {
        return `$${approval.current_value.toFixed(4)} / $${approval.limit_value.toFixed(2)}`;
    }
    return `${approval.current_value} / ${approval.limit_value} ${approval.unit}`;
}

function formatExtensionPlaceholder(approval: ApprovalRequest) {
    const fallback = approval.limit_value;
    return approval.unit === "usd" ? `e.g. ${fallback}` : `e.g. ${Math.round(fallback)}`;
}

function statusClass(status: string) {
    if (status === "approved") return "badge-active";
    if (status === "pending") return "badge-warning";
    return "badge-inactive";
}

function ApprovalCard({
    approval,
    busy,
    onApprove,
    onDeny,
}: {
    approval: ApprovalRequest;
    busy: boolean;
    onApprove: (id: string, body: { note?: string; extension_value?: number }) => Promise<void>;
    onDeny: (id: string, body: { note?: string }) => Promise<void>;
}) {
    const isPending = approval.status === "pending";
    const [note, setNote] = useState("");
    const [extensionValue, setExtensionValue] = useState("");

    const parsedExtension = extensionValue.trim() ? Number(extensionValue) : undefined;
    const resolution = approval.resolution_json;

    return (
        <motion.div
            className={`approval-card ${isPending ? "approval-card-pending" : "approval-card-resolved"}`}
            layout
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
        >
            <div className="approval-card-header">
                <div>
                    <div className="approval-card-title">{approval.agent_name}</div>
                    <div className="approval-card-subtitle">
                        {approval.approval_type.replace(/_/g, " ")} · {approval.scope}
                    </div>
                </div>
                <div className="approval-card-status">
                    <span className={`badge ${statusClass(approval.status)}`}>{approval.status}</span>
                    {isPending && <div className="approval-chip">Expires in {formatRemaining(approval.expires_at)}</div>}
                </div>
            </div>

            <p className="approval-card-message">{approval.message}</p>

            <div className="approval-meta-grid">
                <div className="approval-meta">
                    <span className="approval-meta-label">Run</span>
                    <span className="approval-meta-value">{approval.run_id}</span>
                </div>
                <div className="approval-meta">
                    <span className="approval-meta-label">Current vs limit</span>
                    <span className="approval-meta-value">{formatValue(approval)}</span>
                </div>
                {approval.session_id && (
                    <div className="approval-meta">
                        <span className="approval-meta-label">Session</span>
                        <span className="approval-meta-value">{approval.session_id}</span>
                    </div>
                )}
                <div className="approval-meta">
                    <span className="approval-meta-label">Channels</span>
                    <span className="approval-meta-value">
                        {approval.channels_json.length ? approval.channels_json.join(", ") : "dashboard only"}
                    </span>
                </div>
            </div>

            <div className="approval-links">
                <Link href={`/dashboard/runs/${approval.run_id}`} className="back-link approval-link">
                    View run details
                </Link>
            </div>

            {isPending ? (
                <>
                    <div className="approval-form-grid">
                        <div className="form-group">
                            <label>Extension Amount</label>
                            <input
                                type="number"
                                step={approval.unit === "usd" ? "0.01" : "1"}
                                min="0"
                                value={extensionValue}
                                onChange={(e) => setExtensionValue(e.target.value)}
                                className="form-input"
                                placeholder={formatExtensionPlaceholder(approval)}
                            />
                        </div>
                        <div className="form-group">
                            <label>Decision Note</label>
                            <input
                                type="text"
                                value={note}
                                onChange={(e) => setNote(e.target.value)}
                                className="form-input"
                                placeholder="Why are we continuing or killing this run?"
                            />
                        </div>
                    </div>

                    <div className="approval-actions">
                        <button
                            type="button"
                            className="btn btn-success"
                            onClick={() => void onApprove(approval.id, { note: note.trim() || undefined, extension_value: parsedExtension })}
                            disabled={busy || (extensionValue.trim().length > 0 && Number.isNaN(parsedExtension))}
                        >
                            {busy ? "Working..." : "Continue"}
                        </button>
                        <button
                            type="button"
                            className="btn btn-danger"
                            onClick={() => void onDeny(approval.id, { note: note.trim() || undefined })}
                            disabled={busy}
                        >
                            {busy ? "Working..." : "Kill Run"}
                        </button>
                    </div>
                </>
            ) : (
                <div className="approval-resolution">
                    <div className="approval-resolution-title">Resolution</div>
                    <div className="approval-resolution-body">
                        <div>
                            <span className="approval-meta-label">Resolved by</span>
                            <span className="approval-meta-value">{approval.resolved_by || "system"}</span>
                        </div>
                        {resolution?.new_limit !== undefined && (
                            <div>
                                <span className="approval-meta-label">New limit</span>
                                <span className="approval-meta-value">
                                    {approval.unit === "usd" ? `$${resolution.new_limit}` : `${resolution.new_limit} ${approval.unit}`}
                                </span>
                            </div>
                        )}
                        {(approval.resolution_note || resolution?.reason || resolution?.note) && (
                            <div className="approval-resolution-note">
                                <span className="approval-meta-label">Note</span>
                                <span className="approval-meta-value">
                                    {approval.resolution_note || resolution?.reason || resolution?.note}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </motion.div>
    );
}

export default function ApprovalsPage() {
    const [allApprovals, setAllApprovals] = useState<ApprovalRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);
    const [view, setView] = useState<ApprovalView>("pending");

    const loadApprovals = useCallback(async () => {
        try {
            const approvals = await fetchApprovals(undefined, 150);
            setAllApprovals(approvals);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load approvals");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadApprovals();
        const interval = setInterval(() => void loadApprovals(), 5000);
        window.addEventListener(ADMIN_TOKEN_EVENT, loadApprovals);
        return () => {
            clearInterval(interval);
            window.removeEventListener(ADMIN_TOKEN_EVENT, loadApprovals);
        };
    }, [loadApprovals]);

    const visibleApprovals = useMemo(() => {
        if (view === "pending") {
            return allApprovals.filter((approval) => approval.status === "pending");
        }
        if (view === "resolved") {
            return allApprovals.filter((approval) => approval.status !== "pending");
        }
        return allApprovals;
    }, [allApprovals, view]);

    const counts = useMemo(() => ({
        pending: allApprovals.filter((approval) => approval.status === "pending").length,
        approved: allApprovals.filter((approval) => approval.status === "approved").length,
        resolved: allApprovals.filter((approval) => approval.status !== "pending").length,
        expired: allApprovals.filter((approval) => approval.status === "expired").length,
    }), [allApprovals]);

    const handleApprove = async (
        id: string,
        body: { note?: string; extension_value?: number }
    ) => {
        setBusyId(id);
        try {
            await approveRequest(id, body);
            await loadApprovals();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to approve request");
        } finally {
            setBusyId(null);
        }
    };

    const handleDeny = async (
        id: string,
        body: { note?: string }
    ) => {
        setBusyId(id);
        try {
            await denyRequest(id, body);
            await loadApprovals();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to deny request");
        } finally {
            setBusyId(null);
        }
    };

    const filters: Array<{ id: ApprovalView; label: string; count: number }> = [
        { id: "pending", label: "Pending", count: counts.pending },
        { id: "resolved", label: "Resolved", count: counts.resolved },
        { id: "all", label: "All", count: allApprovals.length },
    ];

    return (
        <main className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Approvals Console</h1>
                    <p className="page-subtitle">
                        Review paused runs, extend budgets when the work is important, or terminate safely.
                    </p>
                </div>
            </div>

            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-label">Pending</div>
                    <div className="stat-value">{counts.pending}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Approved</div>
                    <div className="stat-value success">{counts.approved}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Resolved</div>
                    <div className="stat-value">{counts.resolved}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Expired</div>
                    <div className="stat-value warning">{counts.expired}</div>
                </div>
            </div>

            <div className="approval-toolbar">
                <div className="approval-filters">
                    {filters.map((filter) => (
                        <button
                            key={filter.id}
                            type="button"
                            className={`approval-filter ${view === filter.id ? "active" : ""}`}
                            onClick={() => setView(filter.id)}
                        >
                            {filter.label}
                            <span>{filter.count}</span>
                        </button>
                    ))}
                </div>
                <div className="approval-toolbar-note">
                    Default continue behavior doubles the current limit if you leave extension blank.
                </div>
            </div>

            {error && <div className="policy-error">{error}</div>}

            {loading ? (
                <div className="loading-state">Loading approvals...</div>
            ) : visibleApprovals.length === 0 ? (
                <div className="empty-state">
                    <h3>No approvals in this view</h3>
                    <p>
                        {view === "pending"
                            ? "Alert-mode runs will appear here when they cross a configured threshold."
                            : "Once decisions are made, they will appear here for auditability."}
                    </p>
                </div>
            ) : (
                <div className="approval-list">
                    <AnimatePresence>
                        {visibleApprovals.map((approval) => (
                            <ApprovalCard
                                key={`${approval.id}:${approval.status}`}
                                approval={approval}
                                busy={busyId === approval.id}
                                onApprove={handleApprove}
                                onDeny={handleDeny}
                            />
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </main>
    );
}
