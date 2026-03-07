# SteerPlane Launch Materials

## 1. Hacker News — "Show HN" Post

### Title:
```
Show HN: SteerPlane – Runtime guardrails for AI agents (cost limits, loop detection, telemetry)
```

### Body:
```
Hey HN,

I built SteerPlane because I kept watching AI agents burn through API credits overnight. One agent ran a search loop 400+ times before I noticed. Another accumulated $47 in OpenAI charges in 20 minutes doing nothing useful.

SteerPlane is an open-source runtime control plane that wraps any AI agent with a single decorator:

    from steerplane import guard

    @guard(max_cost_usd=10, max_steps=50, detect_loops=True)
    def run_agent():
        agent.run()

What it does:
- 💰 Hard cost limits — kills the run the instant it exceeds your USD ceiling
- 🔄 Loop detection — sliding-window algorithm catches repeating action patterns in real time
- 🚫 Step limits — caps total execution steps
- 📊 Full telemetry — every step's action, tokens, cost, latency logged to a dashboard
- 🛡️ Graceful degradation — if the API goes down, guardrails still work locally

It's framework-agnostic — works with LangChain, LangGraph, CrewAI, OpenAI SDK, or any custom agent. Python SDK and TypeScript SDK both available.

There's also a Next.js monitoring dashboard with real-time run tracking, step timelines, and cost breakdowns.

GitHub: https://github.com/vijaym2k6/SteerPlane
Dashboard demo: [link to deployed demo if available]

I'd love feedback on:
1. Would you use something like this?
2. What guardrails are you currently using for your agents (if any)?
3. What's missing that would make you switch?

Built with: Python, FastAPI, Next.js, PostgreSQL
```

---

## 2. Reddit Posts

### r/MachineLearning (Title)
```
[P] SteerPlane: Open-source runtime guardrails for AI agents — cost limits, loop detection, and full observability with one decorator
```

### r/LangChain (Title)
```
I built an open-source guardrail SDK that works with LangChain, LangGraph, CrewAI, and any Python agent — one decorator to add cost limits and loop detection
```

### r/LocalLLaMA (Title)
```
Built an open-source tool to stop AI agents from going rogue — cost limits, loop detection, and a real-time dashboard
```

### Reddit Body (use for all):
```
I kept running into the same problem: AI agents that overspend, loop infinitely, or run for hours doing nothing useful. So I built SteerPlane — an open-source runtime control plane.

**One line to add guardrails:**

```python
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50, detect_loops=True)
def run_agent():
    agent.run()
```

**What it catches:**
- Agent exceeds $10? → Terminated instantly.
- Agent repeats [search → think → search → think] 50 times? → Loop detected, killed.
- Agent runs 200+ steps? → Hard stop.

**What you get:**
- Real-time dashboard (Next.js) showing every run, step-by-step timeline, cost breakdown
- Works with ANY framework — LangChain, LangGraph, CrewAI, OpenAI SDK, custom agents
- Python SDK (`pip install steerplane`) + TypeScript SDK (`npm install steerplane`)
- Graceful degradation — if the monitoring API goes down, guards still work locally

**GitHub:** https://github.com/vijaym2k6/SteerPlane

Would love feedback. What guardrails are you currently using? What would make you adopt something like this?
```

---

## 3. Twitter/X Thread

```
🧵 I built an open-source tool to stop AI agents from burning money.

The problem: I watched an agent run a search loop 400 times. $47 in API charges. 20 minutes. Zero useful output.

So I built SteerPlane — runtime guardrails for AI agents. Here's how it works 👇
```

```
1/ The simplest integration possible — one decorator:

from steerplane import guard

@guard(max_cost_usd=10, max_steps=50)
def run_agent():
    agent.run()

That's it. Your agent now has:
✅ Hard cost ceiling
✅ Step limits  
✅ Loop detection
✅ Full telemetry
```

```
2/ Loop detection uses a sliding-window algorithm.

It watches the last N actions and detects repeating patterns:
[search, think, search, think, search, think] → 🔄 LOOP DETECTED

Catches the #1 failure mode in production agents.
```

```
3/ Every step is logged to a real-time dashboard:

- Action name
- Token count
- Cost in USD
- Latency
- Status

You can see exactly what your agent did, step by step. No more black boxes.

[ATTACH DASHBOARD SCREENSHOT]
```

```
4/ It's framework-agnostic:

Works with:
→ LangChain / LangGraph
→ CrewAI / AutoGen
→ OpenAI SDK
→ Anthropic SDK
→ Any custom agent

No proxy. No gateway. Embedded in your code.
```

```
5/ Python SDK + TypeScript SDK.

pip install steerplane
npm install steerplane

Most competitors are Python-only.
```

```
6/ 87% of enterprises deploying AI have NO security framework.

AI agents can call APIs, execute code, and spend real money — with zero guardrails.

SteerPlane is the seatbelt. 🛡️

GitHub: https://github.com/vijaym2k6/SteerPlane

Star if useful ⭐ Feedback welcome 🙏
```

---

## 4. Product Hunt Launch (Tagline Options)

```
Option A: "Runtime guardrails for AI agents — one decorator to prevent cost overruns, infinite loops, and runaway execution"

Option B: "The seatbelt for AI agents — cost limits, loop detection, and full observability in one line of code"

Option C: "Stop AI agents from burning money. Open-source runtime control plane with a single @guard decorator."
```

### Product Hunt Description:
```
SteerPlane is an open-source runtime control plane for autonomous AI agents.

🎯 The Problem: AI agents in production can loop infinitely, overspend on API credits, and run for hours with zero visibility. 87% of enterprises have no AI security framework.

🛡️ The Solution: One decorator that adds:
• Hard cost limits (USD ceiling per run)
• Loop detection (catches repeating patterns)  
• Step limits (caps total actions)
• Full telemetry (every step logged to a dashboard)

💻 Developer Experience:
from steerplane import guard

@guard(max_cost_usd=10, max_steps=50)
def run_agent():
    agent.run()

Works with LangChain, CrewAI, OpenAI SDK, or any custom agent.
Python + TypeScript SDKs available.
```

---

## 5. AI Tool Directory Submissions

Submit to these directories (free listings):

| Directory | URL | Priority |
|-----------|-----|----------|
| There's An AI For That | theresanaiforthat.com | P0 |
| Product Hunt | producthunt.com | P0 |
| AI Tools Directory | aitools.fyi | P1 |
| Future Tools | futuretools.io | P1 |
| AI Agent Store | aiagentstore.ai | P1 |
| TopAI.tools | topai.tools | P1 |
| SaaSHub | saashub.com | P2 |
| AlternativeTo | alternativeto.net | P2 |
