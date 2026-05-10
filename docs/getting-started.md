# Getting Started

Get SteerPlane running locally in a few minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL is optional. SQLite works out of the box for development.

## 1. Clone the Repo

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane
```

## 2. Start the API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`.

Admin access:

- Set `STEERPLANE_ADMIN_TOKEN` before startup for a stable admin token.
- If you do not set one, the API generates a temporary admin token and prints it in the startup logs.

## 3. Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

When you visit the dashboard:

- the navbar checks API health automatically
- use the `Admin Token` button to paste the token from the API logs or environment
- policies and API keys will stay locked until that token is set

## 4. Install the Python SDK

```bash
cd sdk
pip install -e .
```

## 5. Run a Demo Agent

```bash
python examples/simple_agent/agent_example.py
```

Then open `http://localhost:3000/dashboard` to inspect the run timeline.

## 6. Optional: Use the Gateway

Point an OpenAI-compatible client at SteerPlane:

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/gateway/v1",
    api_key="sk_sp_...",
    default_headers={
        "X-LLM-API-Key": "your-provider-key",
        "X-SteerPlane-Session-ID": "support-ticket-1042",
    },
)
```

`X-SteerPlane-Session-ID` is optional but recommended if you want deterministic session-level budgeting.

If you need a custom OpenAI-compatible upstream, add its base URL to
`STEERPLANE_ALLOWED_PROVIDER_URLS` on the API before sending `X-Provider-URL`.
