"""
SteerPlane Example — Simple LLM Agent

A minimal example showing how to wrap a single LLM call with SteerPlane.
This is the simplest possible integration.

Requirements:
    pip install steerplane openai

Usage:
    1. Start the API:    cd api && uvicorn app.main:app --reload
    2. Run this agent:   python examples/simple_llm_agent/agent.py
    3. View dashboard:   http://localhost:3000/dashboard
"""

from steerplane import guard


# Simulated LLM call (replace with real OpenAI call in production)
def fake_llm_call(prompt: str) -> str:
    """Simulates an LLM call. Replace with openai.ChatCompletion.create() in production."""
    import time
    time.sleep(0.5)  # Simulate latency
    return f"Here is the answer to: {prompt}"


@guard(
    agent_name="simple_llm_agent",
    max_cost_usd=2.00,
    max_steps=10
)
def run_simple_agent(prompt: str):
    """
    A simple agent that answers a question.
    SteerPlane monitors every step automatically.
    """
    print(f"📝 Prompt: {prompt}")

    response = fake_llm_call(prompt)
    print(f"🤖 Response: {response}")

    return response


if __name__ == "__main__":
    print("=" * 50)
    print("SteerPlane — Simple LLM Agent Example")
    print("=" * 50)

    result = run_simple_agent("Explain quantum computing in 3 sentences.")
    print(f"\n✅ Agent completed successfully!")
    print(f"📊 View this run at http://localhost:3000/dashboard")
