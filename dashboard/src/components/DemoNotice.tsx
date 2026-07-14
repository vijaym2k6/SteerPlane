"use client";

import { usePathname } from "next/navigation";
import { DEMO_MODE } from "@/services/demo-data";

/**
 * In-content notice (distinct from the top DemoBanner) shown at the start of
 * each data/console page in demo mode, making explicit that the data on screen
 * is sample data and not real. Hidden on the marketing landing page ("/") and
 * for self-hosted installs.
 */
export default function DemoNotice() {
    const pathname = usePathname();

    if (!DEMO_MODE) return null;
    if (pathname === "/") return null; // landing page has no data to caveat

    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                flexWrap: "wrap",
                margin: "0 0 26px",
                padding: "11px 16px",
                borderRadius: 10,
                fontSize: 13,
                lineHeight: 1.5,
                color: "#e2cfa6",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.30)",
            }}
        >
            <span
                style={{
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    color: "#0b1120",
                    background: "#f59e0b",
                    padding: "2px 9px",
                    borderRadius: 6,
                    flexShrink: 0,
                }}
            >
                SAMPLE DATA
            </span>
            <span>
                Everything on this page is <strong style={{ color: "#fff" }}>demo data — not real</strong>.
                These runs, costs, and policies are illustrative. To monitor your own agents,
                run SteerPlane locally.
            </span>
        </div>
    );
}
