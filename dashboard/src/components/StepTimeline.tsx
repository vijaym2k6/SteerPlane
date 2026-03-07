"use client";

import { motion } from "framer-motion";
import { Step } from "@/services/api";
import CostBadge from "./CostBadge";

interface StepTimelineProps {
    steps: Step[];
}

const itemVariants = {
    hidden: { opacity: 0, x: -30, filter: "blur(6px)" },
    visible: (i: number) => ({
        opacity: 1,
        x: 0,
        filter: "blur(0px)",
        transition: {
            delay: i * 0.05,
            duration: 0.5,
            ease: [0.22, 1, 0.36, 1] as const,
        },
    }),
};

const dotVariants = {
    hidden: { scale: 0, rotate: -180 },
    visible: (i: number) => ({
        scale: 1,
        rotate: 0,
        transition: {
            delay: i * 0.05 + 0.1,
            type: "spring" as const,
            stiffness: 260,
            damping: 15,
        },
    }),
};

export default function StepTimeline({ steps }: StepTimelineProps) {
    const getStatusIcon = (status: string) => {
        switch (status) {
            case "completed": return "✓";
            case "failed": return "✗";
            case "terminated": return "⛔";
            default: return "⚡";
        }
    };

    const getActionIcon = (action: string) => {
        const lower = action.toLowerCase();
        if (lower.includes("search") || lower.includes("web")) return "🔍";
        if (lower.includes("llm") || lower.includes("generate") || lower.includes("ai")) return "🤖";
        if (lower.includes("db") || lower.includes("query") || lower.includes("database")) return "🗄️";
        if (lower.includes("api") || lower.includes("call") || lower.includes("fetch")) return "🔌";
        if (lower.includes("email") || lower.includes("send")) return "📧";
        if (lower.includes("process") || lower.includes("transform")) return "⚙️";
        return "▶️";
    };

    if (steps.length === 0) {
        return (
            <div className="empty-state">
                <p>No steps recorded for this run.</p>
            </div>
        );
    }

    return (
        <div className="timeline">
            {steps.map((step, index) => (
                <motion.div
                    key={step.id}
                    className={`timeline-item ${step.status}`}
                    custom={index}
                    initial="hidden"
                    animate="visible"
                    variants={itemVariants}
                >
                    <div className="timeline-connector">
                        <motion.div
                            className="timeline-dot"
                            custom={index}
                            initial="hidden"
                            animate="visible"
                            variants={dotVariants}
                        >
                            {getStatusIcon(step.status)}
                        </motion.div>
                        {index < steps.length - 1 && <div className="timeline-line" />}
                    </div>

                    <motion.div
                        className="timeline-content"
                        whileHover={{
                            x: 6,
                            boxShadow: "0 0 40px rgba(124, 58, 237, 0.12)",
                            borderColor: "rgba(120, 90, 255, 0.3)",
                            transition: { duration: 0.25 },
                        }}
                    >
                        <div className="timeline-header">
                            <span className="step-number">Step {step.step_number}</span>
                            <span className="step-action">
                                {getActionIcon(step.action)} {step.action}
                            </span>
                        </div>

                        <div className="timeline-metrics">
                            <div className="metric">
                                <span className="metric-label">Tokens</span>
                                <span className="metric-value">{step.tokens.toLocaleString()}</span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Cost</span>
                                <span className="metric-value">
                                    <CostBadge cost={step.cost_usd} size="sm" />
                                </span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Latency</span>
                                <span className="metric-value">{step.latency_ms.toFixed(0)}ms</span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Status</span>
                                <span className={`metric-value status-text-${step.status}`}>
                                    {step.status}
                                </span>
                            </div>
                        </div>

                        {step.error && (
                            <motion.div
                                className="timeline-error"
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                transition={{ delay: 0.3 }}
                            >
                                ⚠️ {step.error}
                            </motion.div>
                        )}
                    </motion.div>
                </motion.div>
            ))}
        </div>
    );
}
