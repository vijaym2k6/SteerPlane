"""
SteerPlane Example — LangGraph Agent

Demonstrates integrating SteerPlane with LangChain's LangGraph framework.
The agent uses a multi-step graph workflow for research and report generation,
with SteerPlane monitoring the entire execution.

Requirements:
    pip install steerplane langgraph langchain-openai

Usage:
    1. Set your API key:  export OPENAI_API_KEY=sk-...
    2. Start the API:     cd api && uvicorn app.main:app --reload
    3. Run this agent:    python examples/langgraph_agent/agent.py
    4. View dashboard:    http://localhost:3000/dashboard

Note: This example uses simulated LLM calls. Replace with real LangGraph
      nodes in production.
"""

import time
import random
from steerplane import SteerPlane

sp = SteerPlane(agent_id="langgraph_research_agent")

# Simulated LangGraph-style workflow nodes
GRAPH_NODES = [
    {
        "node": "research_planner",
        "description": "Plan research strategy",
        "tokens": 800,
        "cost": 0.005,
        "output": "Research plan: 1) Search papers, 2) Analyze trends, 3) Synthesize findings"
    },
    {
        "node": "web_search",
        "description": "Search for recent papers",
        "tokens": 400,
        "cost": 0.002,
        "output": "Found 12 relevant papers on AI safety"
    },
    {
        "node": "paper_analyzer",
        "description": "Analyze paper abstracts",
        "tokens": 2200,
        "cost": 0.015,
        "output": "Key themes: alignment, interpretability, robustness"
    },
    {
        "node": "trend_detector",
        "description": "Detect emerging trends",
        "tokens": 1500,
        "cost": 0.010,
        "output": "Emerging trends: constitutional AI, red teaming, scalable oversight"
    },
    {
        "node": "fact_checker",
        "description": "Verify key claims",
        "tokens": 600,
        "cost": 0.004,
        "output": "3/3 claims verified against sources"
    },
    {
        "node": "report_synthesizer",
        "description": "Generate final report",
        "tokens": 3000,
        "cost": 0.020,
        "output": "Report: AI Safety Trends 2026 — 2,400 words generated"
    },
    {
        "node": "quality_reviewer",
        "description": "Review report quality",
        "tokens": 900,
        "cost": 0.006,
        "output": "Quality score: 8.5/10 — ready for publication"
    },
]


def run_langgraph_agent():
    """Run a simulated LangGraph research agent, monitored by SteerPlane."""
    print("🔬 Starting LangGraph Research Agent...")
    print(f"   Task: Research AI safety trends and generate report\n")

    with sp.run(max_cost_usd=3.0, max_steps=30, loop_window_size=4) as run:
        for i, node in enumerate(GRAPH_NODES):
            # Simulate node execution
            time.sleep(0.5)
            print(f"   [{i+1}/{len(GRAPH_NODES)}] 📦 {node['node']}: {node['description']}")
            print(f"         → {node['output']}")

            # Log the step to SteerPlane
            run.log_step(
                action=node["node"],
                tokens=node["tokens"] + random.randint(-100, 100),
                cost=node["cost"] * random.uniform(0.9, 1.1),
                latency_ms=random.randint(200, 2000),
            )

    print(f"\n✅ Research agent completed! Nodes executed: {len(GRAPH_NODES)}")
    print(f"📊 View this run at http://localhost:3000/dashboard")


def run_langgraph_loop_demo():
    """Demo: Agent gets stuck re-checking facts (SteerPlane catches the loop)."""
    print(f"\n{'='*50}")
    print("🔄 Demo: Loop Detection in LangGraph")
    print(f"{'='*50}\n")

    try:
        with sp.run(max_cost_usd=5.0, max_steps=50, loop_window_size=4) as run:
            # Normal nodes first
            run.log_step("research_planner", tokens=800, cost=0.005, latency_ms=300)
            run.log_step("web_search", tokens=400, cost=0.002, latency_ms=150)
            time.sleep(0.3)

            # Agent gets stuck in a fact-check → re-search loop
            print("   ⚠️ Agent entering fact-check loop...")
            for i in range(20):
                time.sleep(0.2)
                action = "fact_checker" if i % 2 == 0 else "web_search"
                run.log_step(action, tokens=500, cost=0.003, latency_ms=200)

    except Exception as e:
        print(f"\n   🛡️ SteerPlane caught the loop: {e}")
        print(f"   📊 View the terminated run at http://localhost:3000/dashboard")


if __name__ == "__main__":
    print("=" * 50)
    print("SteerPlane — LangGraph Agent Example")
    print("=" * 50)

    run_langgraph_agent()
    time.sleep(1)
    run_langgraph_loop_demo()
