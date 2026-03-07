"use client";

interface StatusBadgeProps {
    status: string;
}

const statusConfig: Record<string, { icon: string; className: string }> = {
    running: { icon: "⚡", className: "status-running" },
    completed: { icon: "✅", className: "status-completed" },
    failed: { icon: "❌", className: "status-failed" },
    terminated: { icon: "⛔", className: "status-terminated" },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
    const config = statusConfig[status] || { icon: "⬜", className: "status-unknown" };

    return (
        <span className={`status-badge ${config.className}`}>
            <span className="status-icon">{config.icon}</span>
            {status}
        </span>
    );
}
