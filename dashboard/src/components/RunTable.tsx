"use client";

import { Run } from "@/services/api";
import StatusBadge from "./StatusBadge";
import CostBadge from "./CostBadge";
import Link from "next/link";

interface RunTableProps {
    runs: Run[];
}

export default function RunTable({ runs }: RunTableProps) {
    const formatTime = (iso: string) => {
        const d = new Date(iso);
        return d.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    };

    const formatDuration = (start: string, end: string | null) => {
        if (!end) return "—";
        const ms = new Date(end).getTime() - new Date(start).getTime();
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    };

    if (runs.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">🚀</div>
                <h3>No runs yet</h3>
                <p>Run an agent with SteerPlane SDK to see execution data here.</p>
                <code>pip install steerplane</code>
            </div>
        );
    }

    return (
        <div className="table-container">
            <table className="runs-table">
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Agent</th>
                        <th>Status</th>
                        <th>Steps</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Duration</th>
                        <th>Started</th>
                    </tr>
                </thead>
                <tbody>
                    {runs.map((run) => (
                        <tr key={run.id} className="run-row">
                            <td>
                                <Link href={`/dashboard/runs/${run.id}`} className="run-id-link">
                                    {run.id}
                                </Link>
                            </td>
                            <td className="agent-name">{run.agent_name}</td>
                            <td>
                                <StatusBadge status={run.status} />
                            </td>
                            <td className="mono">
                                {run.total_steps}
                                <span className="dim">/{run.max_steps_limit}</span>
                            </td>
                            <td className="mono">{run.total_tokens.toLocaleString()}</td>
                            <td>
                                <CostBadge cost={run.total_cost} size="sm" />
                            </td>
                            <td className="mono">
                                {formatDuration(run.start_time, run.end_time)}
                            </td>
                            <td className="time-cell">{formatTime(run.start_time)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
