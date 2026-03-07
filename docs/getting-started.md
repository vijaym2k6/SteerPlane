# Getting Started

Get SteerPlane running in under 5 minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 17 (optional — SQLite works for development)

## Step 1: Clone the Repository

```bash
git clone https://github.com/vijaym2k6/SteerPlane.git
cd SteerPlane
```

## Step 2: Start the API Server

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive API documentation.

## Step 3: Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

## Step 4: Install the SDK

```bash
cd sdk
pip install -e .
```

## Step 5: Run the Demo

```bash
python examples/simple_agent/agent_example.py
```

This runs three demo scenarios:
1. **Normal agent** — completes successfully with 7 steps
2. **Loop detection** — agent gets stuck, SteerPlane catches it
3. **Cost limit** — agent overspends, SteerPlane terminates it

## Step 6: View Results

Open `http://localhost:3000` and click **Dashboard** to see your agent runs, step timelines, and cost breakdowns.

## What's Next?

- Read the [SDK Usage Guide](sdk-usage.md) for the full API reference
- Check out the [Example Agents](example-agents.md) for real-world integrations
- Explore the [Architecture](architecture.md) to understand the system design
