import { DEMO_MODE } from "@/services/demo-data";

const DOCS_QUICKSTART = "https://docs.steerplane.com/docs/quickstart";
const GITHUB_URL = "https://github.com/vijaym2k6/SteerPlane";

/**
 * Top banner shown only on the hosted demo (NEXT_PUBLIC_STEERPLANE_DEMO=true).
 * Makes clear the data is sample/read-only and points visitors to run the real
 * thing locally. Renders nothing for self-hosted installs.
 */
export default function DemoBanner() {
    if (!DEMO_MODE) return null;

    return (
        <div
            style={{
                position: "relative",
                zIndex: 50,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 14,
                flexWrap: "wrap",
                padding: "10px 20px",
                fontSize: 13,
                color: "#dbe6fb",
                background:
                    "linear-gradient(90deg, rgba(29,78,216,0.22) 0%, rgba(37,99,235,0.16) 50%, rgba(29,78,216,0.22) 100%)",
                borderBottom: "1px solid rgba(147,197,253,0.18)",
                backdropFilter: "blur(12px)",
                WebkitBackdropFilter: "blur(12px)",
            }}
        >
            <span
                style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "#60a5fa",
                    boxShadow: "0 0 10px #60a5fa",
                    flexShrink: 0,
                }}
            />
            <span>
                <strong style={{ color: "#fff" }}>Live demo</strong> — sample data, read-only. To
                monitor and control your <em>own</em> agents, run SteerPlane in your terminal.
            </span>
            <a
                href={DOCS_QUICKSTART}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                    color: "#fff",
                    fontWeight: 600,
                    textDecoration: "none",
                    padding: "4px 12px",
                    borderRadius: 6,
                    border: "1px solid rgba(147,197,253,0.35)",
                    background: "rgba(59,130,246,0.25)",
                    whiteSpace: "nowrap",
                }}
            >
                Quickstart →
            </a>
            <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "#93c5fd", textDecoration: "none", whiteSpace: "nowrap" }}
            >
                GitHub
            </a>
        </div>
    );
}
