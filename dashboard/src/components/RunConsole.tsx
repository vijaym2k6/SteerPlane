"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const revealEase = [0.16, 1, 0.3, 1] as const;

/* A scripted agent run. SteerPlane lets normal steps through and steps in on
   the failures teams told us they rebuild guards for. */
type LogLine = { step: string; cost: string; status: "ok" | "stop" | "block" | "info"; note?: string };

const runLog: LogLine[] = [
    { step: "search_orders(customer=4821)", cost: "$0.004", status: "ok" },
    { step: "read_policy(doc=refunds)", cost: "$0.011", status: "ok" },
    { step: "search_orders(customer=4821)", cost: "$0.015", status: "ok" },
    { step: "search_orders(customer=4821)", cost: "$0.019", status: "ok" },
    { step: "search_orders(customer=4821)", cost: "$0.023", status: "stop", note: "Same call repeating. Run stopped." },
    { step: "drop_table(name=orders)", cost: "$0.023", status: "block", note: "Matches deny rule drop_*. Blocked." },
    { step: "run total", cost: "$0.023 / $5.00", status: "info", note: "Under the ceiling. Every step logged." },
];

const STATUS_LABEL: Record<LogLine["status"], string> = {
    ok: "ALLOW",
    stop: "STOP",
    block: "BLOCK",
    info: "DONE",
};

export default function RunConsole() {
    const [shown, setShown] = useState(0);

    useEffect(() => {
        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        let i = 0;
        let timer: number;
        if (reduce) {
            timer = window.setTimeout(() => setShown(runLog.length), 0);
            return () => window.clearTimeout(timer);
        }
        const tick = () => {
            i += 1;
            setShown(i);
            if (i < runLog.length) {
                timer = window.setTimeout(tick, i >= 4 ? 1100 : 650);
            } else {
                // Hold the finished run, then replay it.
                timer = window.setTimeout(() => {
                    i = 0;
                    setShown(0);
                    timer = window.setTimeout(tick, 700);
                }, 6000);
            }
        };
        timer = window.setTimeout(tick, 900);
        return () => window.clearTimeout(timer);
    }, []);

    return (
        <div className="v2-console" role="img" aria-label="Example agent run: SteerPlane stops a repeating call and blocks a drop_table call">
            <div className="v2-console-head">
                <span className="code-dot red" />
                <span className="code-dot yellow" />
                <span className="code-dot green" />
                <span className="v2-console-title">support_bot · run 1f3a</span>
                <span className="v2-console-live">
                    <span className="v2-live-dot" /> guarded
                </span>
            </div>
            <div className="v2-console-body">
                {runLog.slice(0, shown).map((line, i) => (
                    <motion.div
                        key={`${i}-${line.step}`}
                        className={`v2-log v2-log-${line.status}`}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.35, ease: revealEase }}
                    >
                        <span className="v2-log-badge">{STATUS_LABEL[line.status]}</span>
                        <span className="v2-log-step">{line.step}</span>
                        <span className="v2-log-cost">{line.cost}</span>
                        {line.note && <span className="v2-log-note">{line.note}</span>}
                    </motion.div>
                ))}
                {shown < runLog.length && <span className="v2-cursor" />}
            </div>
        </div>
    );
}
