"""
SteerPlane Demo — Simulated Agent Run

This demo shows how SteerPlane monitors an AI agent:
- Step-by-step telemetry
- Cost tracking
- Loop detection

Usage:
    1. Start the API server:  cd api && uvicorn app.main:app --reload
    2. Run this demo:         python demo.py
    3. Open the dashboard:    cd dashboard && npm run dev
    4. Visit http://localhost:3000 to see your run
"""

import time
import random
from steerplane import SteerPlane

# Initialize SteerPlane client
sp = SteerPlane(agent_id="demo_support_bot")

# Simulate a support agent handling a customer ticket
ACTIONS = [
    ("query_customer_db", 380, 0.002, 45),
    ("call_llm_analyze", 1240, 0.008, 320),
    ("search_knowledge_base", 560, 0.003, 89),
    ("call_llm_generate_response", 1800, 0.012, 450),
    ("validate_response", 200, 0.001, 15),
    ("send_email_notification", 120, 0.001, 200),
    ("update_ticket_status", 80, 0.0005, 30),
]


def run_normal_agent():
    """Run a normal agent that completes successfully."""
    print("\n{'='*60}")
    print("DEMO 1: Normal Agent Run (Success)")
    print(f"{'='*60}")

    with sp.run(max_cost_usd=1.0, max_steps=20) as run:
        for action, tokens, cost, latency in ACTIONS:
            # Simulate some work
            time.sleep(0.3)

            # Log the step
            run.log_step(
                action=action,
                tokens=tokens + random.randint(-50, 50),
                cost=cost * random.uniform(0.8, 1.2),
                latency_ms=latency + random.randint(-10, 30),
            )

    print(f"\n📊 Summary: {run.summary()}")


def run_loop_agent():
    """Run an agent that gets stuck in a loop (detected by SteerPlane)."""
    print(f"\n{'='*60}")
    print("DEMO 2: Loop Detection (Agent gets stuck)")
    print(f"{'='*60}")

    try:
        with sp.run(max_cost_usd=5.0, max_steps=50, loop_window_size=6) as run:
            # Normal steps first
            run.log_step("query_db", tokens=380, cost=0.002, latency_ms=45)
            time.sleep(0.2)
            run.log_step("call_llm", tokens=1200, cost=0.008, latency_ms=300)
            time.sleep(0.2)

            # Agent gets stuck in a search loop
            for i in range(20):
                time.sleep(0.2)
                run.log_step("search_web", tokens=560, cost=0.003, latency_ms=89)
    except Exception as e:
        print(f"\n🛡️  SteerPlane caught it: {e}")


def run_expensive_agent():
    """Run an agent that exceeds cost limits."""
    print(f"\n{'='*60}")
    print("DEMO 3: Cost Limit Enforcement")
    print(f"{'='*60}")

    try:
        with sp.run(max_cost_usd=0.05, max_steps=100) as run:
            for i in range(50):
                time.sleep(0.2)
                run.log_step(
                    action=f"expensive_call_{i+1}",
                    tokens=2000,
                    cost=0.015,
                    latency_ms=500,
                )
    except Exception as e:
        print(f"\n🛡️  SteerPlane caught it: {e}")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║         SteerPlane MVP Demo                   ║
    ║         "Agents don't fail in the dark"       ║
    ╚═══════════════════════════════════════════════╝
    """)

    run_normal_agent()
    time.sleep(1)

    run_loop_agent()
    time.sleep(1)

    run_expensive_agent()

    print(f"\n{'='*60}")
    print("✅ Demo complete! Open http://localhost:3000 to see runs.")
    print(f"{'='*60}")
