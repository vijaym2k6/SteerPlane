"""
SteerPlane Example - Simple LLM Agent

A minimal example showing a single guarded LLM step.
"""

from steerplane import get_active_run, guard


def fake_llm_call(prompt: str) -> str:
    """Simulate an LLM call."""
    import time

    time.sleep(0.5)
    return f"Here is the answer to: {prompt}"


@guard(
    agent_name="simple_llm_agent",
    max_cost_usd=2.00,
    max_steps=10,
)
def run_simple_agent(prompt: str):
    """
    Answer a question and log the LLM step explicitly for telemetry.
    """
    print(f"Prompt: {prompt}")

    response = fake_llm_call(prompt)

    active_run = get_active_run()
    if active_run:
        active_run.log_step(
            action="llm:fake_completion",
            tokens=max(len(prompt.split()) * 8, 32),
            cost=0.0002,
            latency_ms=500,
            metadata={"provider": "demo", "prompt_preview": prompt[:80]},
        )

    print(f"Response: {response}")
    return response


if __name__ == "__main__":
    print("=" * 50)
    print("SteerPlane - Simple LLM Agent Example")
    print("=" * 50)

    run_simple_agent("Explain quantum computing in 3 sentences.")
    print("\nAgent completed successfully.")
    print("View this run at http://localhost:3000/dashboard")
