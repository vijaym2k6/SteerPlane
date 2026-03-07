"use client";

interface CostBadgeProps {
    cost: number;
    size?: "sm" | "md" | "lg";
}

export default function CostBadge({ cost, size = "md" }: CostBadgeProps) {
    const formatCost = (c: number) => {
        if (c < 0.01) return `$${c.toFixed(6)}`;
        if (c < 1) return `$${c.toFixed(4)}`;
        return `$${c.toFixed(2)}`;
    };

    const getColor = (c: number) => {
        if (c < 0.1) return "var(--color-success)";
        if (c < 1) return "var(--color-warning)";
        return "var(--color-danger)";
    };

    const sizeClass = {
        sm: "cost-badge-sm",
        md: "cost-badge-md",
        lg: "cost-badge-lg",
    }[size];

    return (
        <span
            className={`cost-badge ${sizeClass}`}
            style={{ "--badge-color": getColor(cost) } as React.CSSProperties}
        >
            {formatCost(cost)}
        </span>
    );
}
