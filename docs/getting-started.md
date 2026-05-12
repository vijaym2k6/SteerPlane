# Getting Started

Get SteerPlane running locally in a few minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (recommended) or PostgreSQL 16+ (manual setup)

## Option A: Docker Compose (Recommended) — New in v0.4.0

The fastest way to start. Brings up API, Dashboard, PostgreSQL, and Redis:

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane

# Copy and configure environment
cp .env.example .env
# Edit .env to set STEERPLANE_ADMIN_TOKEN and other variables

docker compose up -d
```

Services start on:
- **API**: `http://localhost:8000`
- **Dashboard**: `http://localhost:3000`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

## Option B: Manual Setup

### 1. Clone the Repo

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane
```

### 2. Start the API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`.

Admin access:

- Set `STEERPLANE_ADMIN_TOKEN` before startup for a stable admin token.
- If you do not set one, the API generates a temporary admin token and prints it in the startup logs.

### 3. Start the Dashboard

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

### 4. Install the Python SDK

```bash
# From PyPI
pip install steerplane

# Or from source (development)
cd sdk
pip install -e ".[all]"
```

Install with extras for framework integrations:

```bash
pip install steerplane[langchain]    # LangChain callback handler
pip install steerplane[cli]          # CLI tool (steerplane command)
pip install steerplane[all]          # Everything
```

### 5. Install the CLI Tool — New in v0.4.0

```bash
pip install steerplane[cli]

# Verify
steerplane status
```

### 6. Run a Demo Agent

```bash
python examples/simple_agent/agent_example.py
```

Then open `http://localhost:3000/dashboard` to inspect the run timeline.

### 7. Optional: Use the Gateway

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

The gateway now supports SSE streaming — set `stream=True` in your completions call for real-time responses with mid-stream cost enforcement.

`X-SteerPlane-Session-ID` is optional but recommended if you want deterministic session-level budgeting.

If you need a custom OpenAI-compatible upstream, add its base URL to
`STEERPLANE_ALLOWED_PROVIDER_URLS` on the API before sending `X-Provider-URL`.

### 8. Optional: Config File (.steerplane.yml) — New in v0.4.0

Create a `.steerplane.yml` in your project root to set defaults:

```yaml
api_url: http://localhost:8000
agent_name: my_bot
max_cost_usd: 10.0
max_steps: 100
detect_loops: true
```

The SDK auto-discovers this file walking up from the current directory.
