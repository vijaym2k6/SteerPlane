"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRuns, RunListResponse } from "@/services/api";
import RunTable from "@/components/RunTable";

const stagger = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
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

export default function DashboardPage() {
    const [data, setData] = useState<RunListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadRuns = async () => {
        try {
            const result = await fetchRuns();
            setData(result);
            setError(null);
        } catch {
            setError("Cannot connect to SteerPlane API. Make sure the server is running on port 8000.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadRuns();
        const interval = setInterval(loadRuns, 3000);
        return () => clearInterval(interval);
    }, []);

    const runs = data?.runs || [];
    const totalRuns = data?.total || 0;
    const activeRuns = runs.filter((r) => r.status === "running").length;
    const totalCost = runs.reduce((sum, r) => sum + r.total_cost, 0);
    const totalSteps = runs.reduce((sum, r) => sum + r.total_steps, 0);

    const stats = [
        { label: "Total Runs", value: totalRuns, cls: "accent" },
        { label: "Active Now", value: activeRuns, cls: "success" },
        { label: "Total Cost", value: `$${totalCost < 1 ? totalCost.toFixed(4) : totalCost.toFixed(2)}`, cls: "warning" },
        { label: "Total Steps", value: totalSteps.toLocaleString(), cls: "" },
    ];

    return (
        <>
            <motion.div
                className="page-header"
                initial={{ opacity: 0, y: -15, filter: "blur(8px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] as const }}
            >
                <h1 className="page-title">Agent Runs</h1>
                <p className="page-subtitle">Monitor all agent executions in real time</p>
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
                        <div className={`stat-value ${s.cls}`}>{s.value}</div>
                    </motion.div>
                ))}
            </motion.div>

            <AnimatePresence mode="wait">
                {loading ? (
                    <motion.div
                        key="loading"
                        className="loading"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                    >
                        <div className="loading-spinner" />
                        Loading runs...
                    </motion.div>
                ) : error ? (
                    <motion.div
                        key="error"
                        className="error-card"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                    >
                        <h4>⚠️ Connection Error</h4>
                        <p>{error}</p>
                    </motion.div>
                ) : (
                    <motion.div
                        key="table"
                        initial={{ opacity: 0, y: 15, filter: "blur(6px)" }}
                        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                        transition={{ delay: 0.25, duration: 0.5, ease: [0.22, 1, 0.36, 1] as const }}
                    >
                        <RunTable runs={runs} />
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
