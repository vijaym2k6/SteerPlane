"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import RunConsole from "@/components/RunConsole";
import "./home.css";

const ease = [0.16, 1, 0.3, 1] as const;

export default function Home() {
    return (
        <div className="home">
            <div className="site wrap">
                <section className="screen home-hero" aria-labelledby="hero-title">
                    <div className="hero-panel">
                        <div className="hero-copy">
                            <motion.div className="hero-badge" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
                                <span className="hero-badge-dot" />
                                Open source · Self-hosted
                            </motion.div>
                            <motion.h1
                                id="hero-title"
                                className="h-display"
                                initial={{ opacity: 0, y: 24 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.9, delay: 0.08, ease }}
                            >
                                The safety layer for the AGI era.
                            </motion.h1>
                            <motion.p className="lede" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.2, ease }}>
                                Stops loops, caps spend and blocks unsafe calls while your agent runs.
                            </motion.p>
                            <motion.div className="hero-actions" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.32, ease }}>
                                <Link href="/dashboard" className="btn-primary">Open dashboard</Link>
                                <a href="https://docs.steerplane.com" className="btn-secondary" target="_blank" rel="noopener noreferrer">Docs</a>
                                <a href="https://www.steerplane.com" className="btn-secondary" target="_blank" rel="noopener noreferrer">steerplane.com ↗</a>
                            </motion.div>
                            <motion.div className="install-row" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.5 }}>
                                <code className="install"><span>$</span> pip install steerplane</code>
                                <span className="install-sep" aria-hidden="true">|</span>
                                <code className="install"><span>$</span> npm install steerplane</code>
                            </motion.div>
                        </div>

                        <motion.div className="hero-visual" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 0.2, ease }}>
                            <RunConsole />
                        </motion.div>
                    </div>
                </section>

            </div>
        </div>
    );
}
