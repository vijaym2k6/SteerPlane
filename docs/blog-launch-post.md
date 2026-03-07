# I Built a Runtime Control Plane to Stop AI Agents From Burning Money

*March 2026*

---

Two weeks ago, I watched an AI agent burn through $47 in API credits in 20 minutes. It had gotten stuck in a search loop — querying the same thing over and over — and nobody noticed until the OpenAI bill came in.

This wasn't a toy experiment. This was a real agent, doing real work, in a real system.

And it's not just me. **87% of enterprises deploying AI agents have no security framework** for their autonomous systems. Agents can call APIs, execute code, browse the web, and spend real money — with zero guardrails.

So I built SteerPlane.

## What Is SteerPlane?

SteerPlane is an open-source **runtime control plane** for AI agents. It sits inside your agent code (not as a proxy or gateway) and enforces safety policies in real time:

- **Cost limits**: Set a hard USD ceiling. If your agent hits it, the run is terminated instantly.
- **Loop detection**: A sliding-window algorithm watches for repeating action patterns. If your agent does [search → think → search → think] 20 times, SteerPlane catches it.
- **Step limits**: Cap the total number of actions your agent can take.
- **Full telemetry**: Every step is logged — action name, token count, cost, latency. All visible in a real-time dashboard.

The entire integration is one decorator:

```python
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50, detect_loops=True)
def run_agent():
    agent.run()  # Your code doesn't change
```

That's it. Your agent now has guardrails.

## Why Not Just Use [Competitor]?

I looked at everything out there. Here's what I found:

**LangSmith** — Great tracing, but locked to the LangChain ecosystem. If you're using OpenAI SDK directly or CrewAI, it doesn't help.

**Portkey** — Acts as a proxy between you and the LLM. Good for routing, but it doesn't sit inside your agent. It can't detect application-level loops or enforce step limits.

**Guardrails AI** — Validates LLM outputs (is this response toxic? Does it contain PII?). Doesn't monitor what the *agent* is doing.

**Helicone** — Proxy for cost tracking. Doesn't enforce limits — just reports them after the damage is done.

What I wanted was something that:
1. Works with **any** framework (LangChain, CrewAI, OpenAI, custom)
2. **Actively enforces** limits (not just reports them)
3. Catches **agent-level** problems (loops, runaway steps)
4. Requires **zero infrastructure changes** (no proxy, no gateway)

That's SteerPlane.

## How It Works

### The Architecture

```
Your Agent → SteerPlane SDK → FastAPI Server → Dashboard
              (embedded)        (telemetry)     (monitoring)
```

The SDK lives *inside* your agent process. Every time your agent takes an action, the SDK:

1. **Logs it** (action, tokens, cost, latency)
2. **Checks the cost** against your limit
3. **Runs loop detection** on the action history
4. **Counts the step** against your limit
5. **Reports to the API** (for the dashboard)

If any check fails, the SDK raises a specific exception (`CostLimitExceeded`, `LoopDetectedError`, `StepLimitExceeded`) and the run is terminated.

### The Loop Detection Algorithm

The loop detector uses a sliding window over the last N actions. For each possible pattern length (1 to N/2), it checks if the pattern repeats consecutively:

```
Window: [search, think, search, think, search, think]
Pattern length 2: [search, think] → repeats 3 times → LOOP DETECTED
```

Simple, fast, and catches the #1 failure mode in production agents.

### Graceful Degradation

If your SteerPlane API server goes down, the SDK **keeps working locally**. Cost limits, step limits, and loop detection all run in-process. You just lose the dashboard data until the API comes back.

Your agents are **never left unprotected**.

## The Dashboard

The monitoring dashboard is built with Next.js and Framer Motion. It shows:

- **All runs** with status, cost, steps, and duration
- **Step-by-step timeline** for each run
- **Color-coded status** badges (running, completed, failed, loop detected, cost exceeded)
- **Auto-refresh** every 5 seconds

## TypeScript Too

Most agent guardrail tools are Python-only. SteerPlane has a TypeScript SDK:

```typescript
import { guard } from 'steerplane';

const runAgent = guard(async () => {
    await agent.run();
}, { maxCostUsd: 10, maxSteps: 50 });

await runAgent();
```

Works with Vercel AI SDK, LangChain.js, or any Node.js agent framework.

## What's Next

SteerPlane is open source (MIT) and free. Here's the roadmap:

1. **Auto-detect OpenAI/Anthropic calls** — no manual token tracking
2. **Slack/Discord alerts** — instant notifications when agents fail
3. **Hosted cloud version** — sign up, paste API key, done
4. **Visual cost analytics** — charts, trends, per-agent breakdowns

## Try It

```bash
pip install steerplane
```

GitHub: [https://github.com/vijaym2k6/SteerPlane](https://github.com/vijaym2k6/SteerPlane)

I'd love to hear what you think. If you're running agents in production, what keeps you up at night?

---

*SteerPlane is MIT licensed. Star the repo if you find it useful.*
