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
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" /></svg>
    ),
    title: "AI Gateway Proxy",
    desc: "An OpenAI-compatible proxy server that sits between your agent and LLM providers. Point your existing OpenAI client to SteerPlane — every call is automatically monitored, rate-limited, and cost-tracked with zero code changes.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
    ),
    title: "Policy Engine",
    desc: "Define allow/deny rules for actions, rate limits with sliding windows, and approval workflows. The policy engine evaluates every action through a deny → allow → rate limit → approval chain before execution.",
  },
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
    desc: "Define per-run and monthly USD cost limits. Every step's token cost is tracked cumulatively across 25+ models with built-in pricing. The instant spend crosses your threshold, the run is terminated.",
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
    desc: "A Next.js dashboard with auto-refresh that visualizes run history, execution timelines, cost breakdowns, and error traces. Manage API keys, policies, and monitor fleet-wide agent health.",
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
  { num: 2, title: "Point to Gateway", desc: "Set your OpenAI client's base_url to SteerPlane. Or use the @guard decorator directly." },
  { num: 3, title: "Set Policies", desc: "Define cost limits, rate limits, allowed/denied actions, and approval workflows." },
  { num: 4, title: "Agent Runs", desc: "Your agent executes normally. SteerPlane intercepts every LLM call and action." },
  { num: 5, title: "Guards Activate", desc: "Loop detection, cost limits, policy engine, and rate limits are enforced in real time." },
  { num: 6, title: "Dashboard Shows", desc: "Every run, step, cost, and policy violation is visualized in the live dashboard." },
];

/* ─── Architecture ─── */
const archNodes = ["AI Agent", "AI Gateway", "Policy Engine", "SteerPlane SDK", "Guard Engine", "REST API", "PostgreSQL", "Dashboard UI"];

/* ─── Tech Stack ─── */
const techStack = [
  { layer: "Python SDK", tech: "Python 3.10+", detail: "Decorator API, context managers, LangChain integration" },
  { layer: "TypeScript SDK", tech: "TypeScript", detail: "guard() wrapper, async-ready, npm-ready" },
  { layer: "Gateway", tech: "FastAPI + httpx", detail: "OpenAI-compatible proxy with 25+ model pricing" },
  { layer: "API", tech: "FastAPI", detail: "Auto-generated OpenAPI docs, CORS, connection pooling" },
  { layer: "Database", tech: "PostgreSQL 17", detail: "Persistent storage with SQLAlchemy ORM" },
  { layer: "Dashboard", tech: "Next.js 16", detail: "React 19, Framer Motion, API key management" },
];

/* ─── Code ─── */
const codeExample = `# ── Option 1: Gateway Mode (zero code changes) ──
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="sk_sp_...",  # SteerPlane key
    default_headers={"X-LLM-API-Key": "sk-..."}
)
# Every LLM call is now monitored and limited.

# ── Option 2: Decorator Mode ──────────────────
from steerplane import guard

@guard(
    agent_name="support_bot",
    max_cost_usd=10.00,
    max_steps=50,
    denied_actions=["rm -rf", "DROP TABLE"]
)
def run_support_agent():
    while task_queue.has_tasks():
        task = task_queue.next()
        result = llm.complete(task.prompt)
        task.resolve(result)`;

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
          V0.3.0 · AI Gateway + Runtime Guardrails
        </motion.div>

        <motion.div
          className="hero-logo-section"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="hero-title-futuristic">STEERPLANE</h1>
        </motion.div>

        <motion.p
          className="hero-subtitle"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
        >
          An open-source runtime control plane for AI agents. It intercepts every LLM call
          through an OpenAI-compatible gateway, enforces safety policies, detects infinite loops,
          tracks token costs across 25+ models, and gives you complete observability — without
          modifying a single line of agent code.
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
            <Link href="/api-keys" className="btn-secondary">
              Manage API Keys →
            </Link>
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
            { num: "$7.6B+", label: "AI Agent Market (2025)" },
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
          <h2 className="section-title">Eight layers of runtime protection</h2>
          <p className="section-desc">
            Every capability is production-ready. Use the AI Gateway proxy for zero-code integration,
            the SDK decorator for deep control, or the LangChain callback handler for automatic instrumentation.
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
          <h2 className="section-title">Six-step integration. Zero complexity.</h2>
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
          <h2 className="section-title">Two integration paths. Total protection.</h2>
          <p className="section-desc">
            Use the Gateway proxy for zero-code monitoring, or the SDK decorator for deep
            programmatic control. Both give you cost tracking, loop detection, policy enforcement,
            and full telemetry out of the box.
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
            SteerPlane uses a modular architecture. The AI Gateway proxies LLM calls with built-in
            guardrails, the Policy Engine evaluates rules, the SDK instruments agent code,
            and the dashboard provides real-time visualization.
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
            SteerPlane is open-source and free. Point your OpenAI client to the gateway
            or add a single decorator — start monitoring your AI agents in under 5 minutes.
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
        <p>SteerPlane v0.3.0 — Open-source runtime guardrails for AI agents.</p>
        <p className="landing-footer-tagline">&quot;Ship agents. Not incidents.&quot;</p>
      </footer>
    </div>
  );
}
