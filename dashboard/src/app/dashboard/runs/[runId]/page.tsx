"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRun, RunDetail } from "@/services/api";
import StepTimeline from "@/components/StepTimeline";
import StatusBadge from "@/components/StatusBadge";
import CostBadge from "@/components/CostBadge";
import Link from "next/link";

const stagger = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};

const fadeUp = {
    hidden: { opacity: 0, y: 24, filter: "blur(6px)" },
    visible: {
        opacity: 1,
        y: 0,
        filter: "blur(0px)",
        transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
    },
};

export default function RunDetailPage() {
    const params = useParams();
    const runId = params.runId as string;

    const [run, setRun] = useState<RunDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchRun(runId);
                setRun(data);
                setError(null);
            } catch {
                setError(`Failed to load run ${runId}`);
            } finally {
                setLoading(false);
            }
        };

        load();
        const interval = setInterval(load, 3000);
        return () => clearInterval(interval);
    }, [runId]);

    if (loading) {
        return (
            <motion.div className="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="loading-spinner" />
                Loading run...
            </motion.div>
        );
    }

    if (error || !run) {
        return (
            <motion.div
                className="error-card"
                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            >
                <h4>⚠️ Error</h4>
                <p>{error || "Run not found"}</p>
                <Link href="/dashboard" className="back-link">← Back to dashboard</Link>
            </motion.div>
        );
    }

    const formatTime = (iso: string) =>
        new Date(iso).toLocaleString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit", second: "2-digit",
        });

    const duration = run.end_time
        ? ((new Date(run.end_time).getTime() - new Date(run.start_time).getTime()) / 1000).toFixed(1) + "s"
        : "Running...";

    const stats = [
        { label: "Steps", value: run.total_steps, extra: `/${run.max_steps_limit}`, cls: "accent" },
        { label: "Total Cost", value: null, costVal: run.total_cost, cls: "" },
        { label: "Tokens", value: run.total_tokens.toLocaleString(), cls: "" },
        { label: "Duration", value: duration, cls: "" },
    ];
    const isAwaitingApproval = run.status === "awaiting_approval";

    return (
        <>
            <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
            >
                <Link href="/dashboard" className="back-link">← Back to all runs</Link>
            </motion.div>

            <motion.div
                className="run-detail-header"
                initial={{ opacity: 0, y: -15, filter: "blur(8px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] as const }}
            >
                <div>
                    <h1 className="page-title">{run.agent_name}</h1>
                    <p className="page-subtitle" style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
                        {run.id}
                    </p>
                </div>
                <StatusBadge status={run.status} />
            </motion.div>

            <motion.div
                className="stats-row"
                variants={stagger}
                initial="hidden"
                animate="visible"
            >
                {stats.map((s) => (
                    <motion.div
                        key={s.label}
                        className="stat-card"
                        variants={fadeUp}
                        whileHover={{
                            y: -3,
                            boxShadow: "0 0 40px rgba(124, 58, 237, 0.15)",
                            borderColor: "rgba(120, 90, 255, 0.3)",
                            transition: { duration: 0.25 },
                        }}
                    >
                        <div className="stat-label">{s.label}</div>
                        <div className={`stat-value ${s.cls}`}>
                            {s.costVal !== undefined && s.costVal !== null ? (
                                <CostBadge cost={s.costVal} size="lg" />
                            ) : (
                                <>
                                    {s.value}
                                    {s.extra && <span style={{ fontSize: 14, color: "var(--text-dim)" }}>{s.extra}</span>}
                                </>
                            )}
                        </div>
                    </motion.div>
                ))}
            </motion.div>

            <motion.div
                className="run-meta"
                style={{ marginBottom: 24 }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
            >
                <div className="run-meta-item">
                    <span className="run-meta-label">Started</span>
                    <span className="run-meta-value">{formatTime(run.start_time)}</span>
                </div>
                {run.end_time && (
                    <div className="run-meta-item">
                        <span className="run-meta-label">Ended</span>
                        <span className="run-meta-value">{formatTime(run.end_time)}</span>
                    </div>
                )}
                <div className="run-meta-item">
                    <span className="run-meta-label">Cost Limit</span>
                    <span className="run-meta-value">${run.max_cost_usd}</span>
                </div>
            </motion.div>

            <AnimatePresence>
                {run.error && (
                    <motion.div
                        className="error-card"
                        initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        <h4>{isAwaitingApproval ? "🔔 Awaiting Human Approval" : "⛔ Run Terminated"}</h4>
                        <p style={{ fontSize: 15, marginBottom: run.error_details ? 16 : 0 }}>{run.error}</p>

                        {run.error_details && (
                            <div style={{
                                background: "rgba(0,0,0,0.25)",
                                borderRadius: 10,
                                padding: "14px 18px",
                                display: "grid",
                                gridTemplateColumns: "1fr 1fr",
                                gap: "10px 24px",
                                fontSize: 13,
                                fontFamily: "var(--font-mono)",
                            }}>
                                <div>
                                    <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Error Type</span>
                                    <span style={{
                                        color: run.error_details.error_type === "policy_violation" ? "#ff6b6b"
                                            : run.error_details.error_type === "loop_detected" ? "#feca57"
                                            : run.error_details.error_type === "cost_limit_exceeded" ? "#ff9f43"
                                            : "#a29bfe",
                                        fontWeight: 600,
                                    }}>
                                        {run.error_details.error_type?.replace(/_/g, " ").toUpperCase()}
                                    </span>
                                </div>

                                {run.error_details.blocked_action && (
                                    <div>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Blocked Action</span>
                                        <span style={{ color: "#dfe6e9" }}>{run.error_details.blocked_action}</span>
                                    </div>
                                )}

                                {run.error_details.rule_matched && (
                                    <div>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Rule Matched</span>
                                        <span style={{ color: "#74b9ff" }}>{run.error_details.rule_matched}</span>
                                    </div>
                                )}

                                {run.error_details.reason && (
                                    <div style={{ gridColumn: "1 / -1" }}>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Reason</span>
                                        <span style={{ color: "#dfe6e9" }}>{run.error_details.reason}</span>
                                    </div>
                                )}

                                {run.error_details.pattern_detected && (
                                    <div style={{ gridColumn: "1 / -1" }}>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Loop Pattern</span>
                                        <span style={{ color: "#feca57" }}>
                                            [{run.error_details.pattern_detected.join(" → ")}]
                                            {run.error_details.window_size && <span style={{ color: "var(--text-dim)" }}> (window: {run.error_details.window_size})</span>}
                                        </span>
                                    </div>
                                )}

                                {run.error_details.recent_actions && (
                                    <div style={{ gridColumn: "1 / -1" }}>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Recent Actions</span>
                                        <span style={{ color: "#b2bec3", wordBreak: "break-all" }}>
                                            {run.error_details.recent_actions.join(" → ")}
                                        </span>
                                    </div>
                                )}

                                {run.error_details.current_cost !== undefined && run.error_details.max_cost !== undefined && (
                                    <div>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Cost at Termination</span>
                                        <span style={{ color: "#ff9f43" }}>
                                            ${run.error_details.current_cost.toFixed(4)} / ${run.error_details.max_cost.toFixed(2)} limit
                                        </span>
                                    </div>
                                )}

                                {run.error_details.step_number && (
                                    <div>
                                        <span style={{ color: "var(--text-dim)", display: "block", marginBottom: 2 }}>Terminated at Step</span>
                                        <span style={{ color: "#dfe6e9" }}>{run.error_details.step_number}</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            <motion.div
                className="page-header"
                style={{ marginTop: 8 }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
            >
                <h2 className="page-title" style={{ fontSize: 20 }}>Execution Timeline</h2>
                <p className="page-subtitle">Step-by-step agent execution trace</p>
            </motion.div>

            <StepTimeline steps={run.steps} />
        </>
    );
}
