# Dashboard Guide

The SteerPlane dashboard provides real-time monitoring and visualization of all your AI agent runs.

## Accessing the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Pages

### Landing Page (`/`)

The home page introduces SteerPlane with:
- Feature overview
- Architecture diagram
- Quick SDK code example
- Navigation to the dashboard

### Dashboard (`/dashboard`)

The main monitoring view showing all agent runs:

| Column | Description |
|--------|-------------|
| **Run ID** | Unique identifier (click to view details) |
| **Agent** | Agent name from the `@guard` decorator |
| **Status** | Running (pulsing), Completed (green), Failed (red) |
| **Steps** | Number of steps executed |
| **Total Cost** | Cumulative USD cost of the run |
| **Duration** | Total execution time |
| **Started** | Timestamp when the run began |

Features:
- **Auto-refresh**: Dashboard polls for new data every 5 seconds
- **Clickable rows**: Click any run to see step-by-step details
- **Color-coded status**: Instant visual status identification

### Run Detail Page (`/dashboard/runs/[runId]`)

Detailed view of a single agent run:

- **Run summary card**: Agent name, status, total cost, step count
- **Step timeline**: Visual timeline of every action the agent took
- **Per-step metrics**: Tokens, cost, latency, and status for each step
- **Error traces**: If the run failed, the error is highlighted

## Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| 🟢 `completed` | Green | Run finished successfully |
| 🔵 `running` | Blue (pulsing) | Run is currently active |
| 🔴 `failed` | Red | Run was terminated (loop, cost, or step limit) |
| 🟡 `cost_exceeded` | Amber | Run hit the cost ceiling |
| 🟣 `loop_detected` | Purple | Run was caught in an infinite loop |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Home` | Navigate to landing page |
| `D` | Navigate to dashboard |

## API Connection

The navbar shows "API Connected" (green dot) when the dashboard can reach the FastAPI backend. If you see issues:

1. Make sure the API is running: `uvicorn app.main:app --reload`
2. Check that the API URL matches (default: `http://localhost:8000`)
3. Verify CORS is configured in `api/app/main.py`
