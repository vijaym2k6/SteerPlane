# Example Agents

This page shows how to integrate SteerPlane with real AI agent frameworks.

## 1. Simple LLM Agent

The most basic integration — a single function that calls an LLM.

```python
# examples/simple_llm_agent/agent.py

from steerplane import guard
import openai

client = openai.OpenAI()

@guard(
    agent_name="simple_llm",
    max_cost_usd=2.00,
    max_steps=10
)
def run_simple_agent(prompt: str):
    """A simple agent that answers a question using GPT."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    result = run_simple_agent("Explain quantum computing in 3 sentences.")
    print(result)
```

## 2. OpenAI Agent with Tool Use

An agent that uses OpenAI's function calling to interact with tools.

```python
# examples/openai_agent/agent.py

from steerplane import SteerPlane
import openai
import json

client = openai.OpenAI()
sp = SteerPlane(agent_id="openai_tool_agent")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_database",
            "description": "Search the customer database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    }
]


def search_database(query: str) -> str:
    """Simulated database search."""
    return f"Found 3 results for '{query}'"


def send_email(to: str, subject: str, body: str) -> str:
    """Simulated email sending."""
    return f"Email sent to {to}"


def run_openai_agent():
    with sp.run(max_cost_usd=5.0, max_steps=20) as run:
        messages = [
            {"role": "system", "content": "You are a customer support agent."},
            {"role": "user", "content": "Find customer John Doe and send him a satisfaction survey."}
        ]

        for step in range(20):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
            )

            usage = response.usage
            run.log_step(
                action="llm_call",
                tokens=usage.total_tokens,
                cost=usage.total_tokens * 0.00001,  # approximate
                latency_ms=200,
            )

            choice = response.choices[0]

            if choice.finish_reason == "stop":
                print(f"Agent completed: {choice.message.content}")
                break

            if choice.finish_reason == "tool_calls":
                for tool_call in choice.message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    if fn_name == "search_database":
                        result = search_database(**fn_args)
                    elif fn_name == "send_email":
                        result = send_email(**fn_args)

                    run.log_step(
                        action=fn_name,
                        tokens=0,
                        cost=0,
                        latency_ms=50,
                    )

                    messages.append(choice.message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })


if __name__ == "__main__":
    run_openai_agent()
```

## 3. LangGraph Agent

Integration with LangChain's LangGraph framework.

```python
# examples/langgraph_agent/agent.py

from steerplane import SteerPlane
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
import operator

sp = SteerPlane(agent_id="langgraph_research_agent")


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    research_results: str
    final_report: str


llm = ChatOpenAI(model="gpt-4o-mini")


def research_node(state: AgentState):
    """Research a topic using the LLM."""
    response = llm.invoke(state["messages"])
    return {"research_results": response.content}


def report_node(state: AgentState):
    """Generate a final report from research."""
    response = llm.invoke([
        {"role": "system", "content": "Summarize the research into a report."},
        {"role": "user", "content": state["research_results"]}
    ])
    return {"final_report": response.content}


def should_continue(state: AgentState):
    if len(state.get("research_results", "")) > 100:
        return "report"
    return "research"


# Build the graph
workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("report", report_node)
workflow.set_entry_point("research")
workflow.add_conditional_edges("research", should_continue, {
    "research": "research",
    "report": "report",
})
workflow.add_edge("report", END)

app = workflow.compile()


def run_langgraph_agent():
    with sp.run(max_cost_usd=3.0, max_steps=30) as run:
        result = app.invoke({
            "messages": [{"role": "user", "content": "Research the latest trends in AI safety"}],
            "research_results": "",
            "final_report": "",
        })

        run.log_step(
            action="langgraph_complete",
            tokens=2000,
            cost=0.02,
            latency_ms=5000,
        )

        print(f"Report: {result['final_report'][:200]}...")


if __name__ == "__main__":
    run_langgraph_agent()
```

## Running the Examples

```bash
# Make sure the API is running first
cd api && uvicorn app.main:app --reload

# Then run any example
python examples/simple_llm_agent/agent.py
python examples/openai_agent/agent.py
python examples/langgraph_agent/agent.py

# View results in the dashboard
# Open http://localhost:3000/dashboard
```
