"""
SteerPlane Example — OpenAI Agent with Tool Use

Demonstrates integrating SteerPlane with OpenAI's function calling API.
The agent uses tools to search a database and send emails, with SteerPlane
monitoring every step.

Requirements:
    pip install steerplane openai

Usage:
    1. Set your API key:  export OPENAI_API_KEY=sk-...
    2. Start the API:     cd api && uvicorn app.main:app --reload
    3. Run this agent:    python examples/openai_agent/agent.py
    4. View dashboard:    http://localhost:3000/dashboard
"""

import time
import random
from steerplane import SteerPlane

sp = SteerPlane(agent_id="openai_tool_agent")


# Simulated tool functions (replace with real implementations)
def search_database(query: str) -> str:
    """Simulated database search."""
    time.sleep(0.3)
    return f"Found 3 results for '{query}': [Customer #1042, #1089, #1123]"


def send_email(to: str, subject: str, body: str) -> str:
    """Simulated email sending."""
    time.sleep(0.2)
    return f"Email sent to {to} with subject '{subject}'"


def analyze_sentiment(text: str) -> str:
    """Simulated sentiment analysis."""
    time.sleep(0.1)
    sentiments = ["positive", "neutral", "negative"]
    return f"Sentiment: {random.choice(sentiments)}"


# Simulated multi-step agent workflow
WORKFLOW = [
    ("query_customer_db", search_database, {"query": "John Doe"}, 380, 0.002),
    ("analyze_sentiment", analyze_sentiment, {"text": "Customer complaint about billing"}, 200, 0.001),
    ("call_llm_draft_response", None, {}, 1800, 0.012),
    ("search_knowledge_base", search_database, {"query": "billing FAQ"}, 560, 0.003),
    ("call_llm_refine_response", None, {}, 1400, 0.009),
    ("send_email_response", send_email, {"to": "john@example.com", "subject": "RE: Billing", "body": "..."}, 120, 0.001),
    ("update_ticket_status", None, {}, 80, 0.0005),
]


def run_openai_agent():
    """Run a simulated OpenAI agent with tool use, monitored by SteerPlane."""
    print("🤖 Starting OpenAI Tool Agent...")
    print(f"   Task: Handle customer support ticket\n")

    with sp.run(max_cost_usd=5.0, max_steps=20) as run:
        for action, tool_fn, args, tokens, cost in WORKFLOW:
            # Execute the tool if it exists
            if tool_fn:
                result = tool_fn(**args)
                print(f"   🔧 {action}: {result}")
            else:
                time.sleep(0.4)  # Simulate LLM call
                print(f"   🧠 {action}: [LLM processing...]")

            # Log the step to SteerPlane
            run.log_step(
                action=action,
                tokens=tokens + random.randint(-50, 50),
                cost=cost * random.uniform(0.9, 1.1),
                latency_ms=random.randint(50, 500),
            )

    print(f"\n✅ Agent completed! Total steps: {len(WORKFLOW)}")
    print(f"📊 View this run at http://localhost:3000/dashboard")


if __name__ == "__main__":
    print("=" * 50)
    print("SteerPlane — OpenAI Tool Agent Example")
    print("=" * 50)
    run_openai_agent()
