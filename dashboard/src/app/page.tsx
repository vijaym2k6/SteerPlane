"use client";

import { motion } from "framer-motion";
import Link from "next/link";

/* ─── Animation Variants ─── */
const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.15 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 30, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] as const },
  },
};

/* ─── Features ─── */
const features = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="m15 9-6 6" /><path d="m9 9 6 6" /></svg>
    ),
    title: "Infinite Loop Termination",
    desc: "Our sliding-window pattern detector identifies repeating agent action sequences in real time. The moment a loop is confirmed, the run is gracefully terminated — before it drains your API budget on redundant calls.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
    ),
    title: "Hard Cost Ceiling",
    desc: "Define a per-run USD cost limit. Every step's token cost is tracked cumulatively. The instant cumulative spend crosses your threshold, the run is automatically terminated and the overage is logged.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
    ),
    title: "Step Limit Enforcement",
    desc: "Cap the maximum number of execution steps. Even if the agent avoids loops and stays under cost, it cannot execute indefinitely. This prevents creative workarounds from consuming unbounded resources.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12h4l2-9 5 18 2-9h5" /></svg>
    ),
    title: "Deep Telemetry Capture",
    desc: "Captures every step's action name, input/output tokens, cost, latency, and final status. This telemetry feeds directly into the dashboard for visual debugging and long-term trend analysis.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="9" y1="3" x2="9" y2="21" /></svg>
    ),
    title: "Real-Time Dashboard",
    desc: "A Next.js dashboard with auto-refresh that visualizes run history, execution timelines, cost breakdowns, and error traces. Designed for both debugging individual runs and monitoring fleet-wide agent health.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
    ),
    title: "Graceful SDK Degradation",
    desc: "If the SteerPlane API goes down, the SDK continues to enforce loop detection and cost limits locally. Your agents are never left unprotected, even during infrastructure failures.",
  },
];

/* ─── How It Works ─── */
const howSteps = [
  { num: 1, title: "Install SDK", desc: "pip install steerplane — one dependency, zero config required." },
  { num: 2, title: "Wrap Your Agent", desc: "Add the @guard decorator with your cost and step limits." },
  { num: 3, title: "Agent Runs", desc: "Your agent executes normally. SteerPlane intercepts every step." },
  { num: 4, title: "Guards Activate", desc: "Loop detection, cost limits, and step limits are enforced in real time." },
  { num: 5, title: "Dashboard Shows", desc: "Every run, step, cost, and error is visualized in the live dashboard." },
];

/* ─── Architecture ─── */
const archNodes = ["AI Agent", "SteerPlane SDK", "Guard Engine", "REST API", "PostgreSQL", "Dashboard UI"];

/* ─── Tech Stack ─── */
const techStack = [
  { layer: "SDK", tech: "Python 3.10+", detail: "Decorator API, context managers, async-ready client" },
  { layer: "API", tech: "FastAPI", detail: "Auto-generated OpenAPI docs, CORS, connection pooling" },
  { layer: "Database", tech: "PostgreSQL 17", detail: "Persistent storage with SQLAlchemy ORM" },
  { layer: "Dashboard", tech: "Next.js 16", detail: "TypeScript, Framer Motion, server components" },
];

/* ─── Code ─── */
const codeExample = `from steerplane import guard

@guard(
    agent_name="support_bot",
    max_cost_usd=10.00,
    max_steps=50,
    detect_loops=True
)
def run_support_agent():
    while task_queue.has_tasks():
        task = task_queue.next()
        result = llm.complete(task.prompt)
        task.resolve(result)

# SteerPlane silently monitors every step.
# If the agent loops, overspends, or exceeds
# step limits — it's terminated instantly.`;

export default function Home() {
  return (
    <div className="landing">
      {/* ═══════ HERO ═══════ */}
      <motion.section
        className="hero"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <motion.div
          className="hero-badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="hero-badge-dot" />
          V0.1.0 · Runtime Agent Guardrails
        </motion.div>

        <motion.div
          className="hero-logo-section"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="hero-title-futuristic">STEER PLANE</h1>
          <p className="hero-tagline-futuristic">RUNTIME CONTROL PLANE FOR AI AGENTS</p>
        </motion.div>

        <motion.p
          className="hero-subtitle"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
        >
          An open-source runtime layer that sits between your AI agent
          and the outside world. It intercepts every action, enforces safety policies,
          detects infinite loops, tracks token costs, and gives you complete observability
          into autonomous agent behavior — without modifying agent code.
        </motion.p>

        <motion.div
          className="hero-actions"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
            <Link href="/dashboard" className="btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="9" y1="3" x2="9" y2="21" /></svg>
              Open Dashboard
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="btn-secondary">
              API Documentation →
            </a>
          </motion.div>
        </motion.div>
      </motion.section>

      <div className="section-divider" />

      {/* ═══════ THE PROBLEM ═══════ */}
      <section className="section">
        <motion.div
          className="section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <div className="section-label">The Problem</div>
          <h2 className="section-title">AI agents are powerful. And dangerous.</h2>
          <p className="section-desc">
            Autonomous agents can call APIs, execute code, browse the web, and make real-world
            decisions. But without guardrails, a single misconfigured agent can enter an infinite
            loop, burn through thousands of dollars in API credits, or take unintended destructive
            actions — all while the developer has zero visibility into what&apos;s happening.
          </p>
        </motion.div>

        <motion.div
          className="stats-banner"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
        >
          {[
            { num: "$2.4B+", label: "AI Agent Market (2025)" },
            { num: "73%", label: "Devs report runaway costs" },
            { num: "10x", label: "Growth in agent failures" },
            { num: "0", label: "Runtime control tools" },
          ].map((s) => (
            <motion.div key={s.label} className="stat-banner-item" variants={fadeUp}>
              <div className="stat-banner-number">{s.num}</div>
              <div className="stat-banner-label">{s.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <div className="section-divider" />

      {/* ═══════ CORE CAPABILITIES ═══════ */}
      <section className="section">
        <motion.div
          className="section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <div className="section-label">Core Capabilities</div>
          <h2 className="section-title">Six layers of runtime protection</h2>
          <p className="section-desc">
            Every capability is production-ready in the SDK. No external dependencies,
            no configuration files, no infrastructure setup. Just a decorator.
          </p>
        </motion.div>

        <motion.div
          className="features-grid"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
        >
          {features.map((f) => (
            <motion.div key={f.title} variants={fadeUp} className="feature-card">
              <div className="feature-icon">{f.icon}</div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <div className="section-divider" />

      {/* ═══════ HOW IT WORKS ═══════ */}
      <section className="section">
        <motion.div
          className="section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <div className="section-label">How It Works</div>
          <h2 className="section-title">Five-step integration. Zero complexity.</h2>
        </motion.div>

        <motion.div
          className="how-steps"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
        >
          {howSteps.map((step) => (
            <motion.div key={step.num} variants={fadeUp} className="how-step">
              <div className="how-step-number">{step.num}</div>
              <h3 className="how-step-title">{step.title}</h3>
              <p className="how-step-desc">{step.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <div className="section-divider" />

      {/* ═══════ SDK EXAMPLE ═══════ */}
      <motion.section
        className="section"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-80px" }}
        variants={scaleIn}
      >
        <div className="section-header">
          <div className="section-label">Developer Experience</div>
          <h2 className="section-title">One decorator. Total protection.</h2>
          <p className="section-desc">
            The SteerPlane SDK wraps your agent function with a single decorator.
            Under the hood, it initializes the run manager, telemetry client, loop detector,
            and cost tracker — all transparently.
          </p>
        </div>

        <motion.div
          className="code-block"
          whileHover={{ scale: 1.01, boxShadow: "0 20px 50px rgba(0,0,0,0.7), 0 0 20px rgba(37,99,235,0.2)" }}
          transition={{ duration: 0.3 }}
        >
          <div className="code-header">
            <span className="code-dot red" />
            <span className="code-dot yellow" />
            <span className="code-dot green" />
            <span className="code-filename">agent.py</span>
            <div style={{ marginLeft: "auto", fontSize: 10, color: "var(--text-dim)", letterSpacing: 2, textTransform: "uppercase" }}>Python 3.10+</div>
          </div>
          <pre className="code-content">{codeExample}</pre>
        </motion.div>
      </motion.section>

      <div className="section-divider" />

      {/* ═══════ ARCHITECTURE ═══════ */}
      <section className="section">
        <motion.div
          className="section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <div className="section-label">System Architecture</div>
          <h2 className="section-title">Simple. Modular. Production-ready.</h2>
          <p className="section-desc">
            SteerPlane uses a clean 4-tier architecture. The SDK intercepts agent calls,
            sends telemetry to the API, which persists data to PostgreSQL, and the
            dashboard reads it for real-time visualization.
          </p>
        </motion.div>

        <motion.div
          className="arch-flow"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
        >
          {archNodes.map((node, i) => (
            <motion.div key={node} variants={fadeUp} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <motion.div
                className="arch-node"
                whileHover={{ scale: 1.05, boxShadow: "0 0 20px rgba(37,99,235,0.3)" }}
              >
                {node}
              </motion.div>
              {i < archNodes.length - 1 && <span className="arch-arrow">→</span>}
            </motion.div>
          ))}
        </motion.div>
      </section>

      <div className="section-divider" />

      {/* ═══════ TECH STACK ═══════ */}
      <section className="section">
        <motion.div
          className="section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <div className="section-label">Technology</div>
          <h2 className="section-title">Built on proven foundations</h2>
        </motion.div>

        <motion.div
          className="tech-stack"
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
        >
          {techStack.map((item) => (
            <motion.div key={item.layer} variants={fadeUp} className="tech-card">
              <div className="tech-layer">{item.layer}</div>
              <div className="tech-name">{item.tech}</div>
              <div className="tech-detail">{item.detail}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <div className="section-divider" />

      {/* ═══════ CTA ═══════ */}
      <section className="section">
        <motion.div
          className="cta-card"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="cta-title">Ready to secure your agents?</h2>
          <p className="cta-desc">
            SteerPlane is open-source and free. Start monitoring your AI agents in under
            5 minutes with a single pip install.
          </p>
          <motion.div style={{ display: "flex", gap: 14, justifyContent: "center" }}>
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
              <Link href="/dashboard" className="btn-primary">Open Dashboard</Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="btn-secondary">
                View on GitHub →
              </a>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="landing-footer">
        <p>SteerPlane v0.1.0 — Open-source runtime guardrails for AI agents.</p>
        <p className="landing-footer-tagline">&quot;Ship agents. Not incidents.&quot;</p>
      </footer>
    </div>
  );
}
