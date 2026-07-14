# Dashboard Guide

The SteerPlane dashboard provides real-time monitoring and visualization of all your AI agent runs.

## Accessing the Dashboard

### Docker (Recommended)

```bash
docker compose up -d
# Dashboard available at http://localhost:3000
```

### Manual

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Pages

### Landing Page (`/`)

The home page introduces SteerPlane v1.0.0 with:
- Feature overview (8 core capabilities)
- System architecture diagram
- Code examples (Gateway mode + Decorator mode)
- Technology stack (Python SDK, TS SDK, Gateway, API, Docker, CI/CD)
- Navigation to the dashboard

### Dashboard (`/dashboard`)

The main monitoring view showing all agent runs:

| Column | Description |
|--------|-------------|
| **Run ID** | Unique identifier (click to view details) |
| **Agent** | Agent name from the `@guard` decorator or integration |
| **Status** | Running (pulsing), Completed (green), Failed (red) |
| **Steps** | Number of steps executed |
| **Total Cost** | Cumulative USD cost of the run |
| **Duration** | Total execution time |
| **Started** | Timestamp when the run began |

Features:
- **Auto-refresh**: Dashboard polls for new data every 3 seconds
- **Clickable rows**: Click any run to see step-by-step details
- **Color-coded status**: Instant visual status identification
- **Source tracking**: Shows whether run came from SDK, Gateway, or integration

### Run Detail Page (`/dashboard/runs/[runId]`)

Detailed view of a single agent run:

- **Run summary card**: Agent name, status, total cost, step count
- **Step timeline**: Visual timeline of every action the agent took
- **Per-step metrics**: Tokens, cost, latency, and status for each step
- **Error traces**: If the run failed, the error is highlighted
- **Enforcement events**: Shows if a run was killed by cost ceiling, loop detection, or policy

### Policies Page (`/policies`) — Admin Only

Manage allow/deny rules, rate limits, and approval workflows:

- Create, edit, and delete policy definitions
- View policy evaluation logs
- Requires admin token authentication

### API Keys Page (`/api-keys`) — Admin Only

Manage gateway API keys:

- Create new keys with budget limits
- View usage counters and remaining budgets
- Revoke keys
- Requires admin token authentication

## Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| `completed` | Green | Run finished successfully |
| `running` | Blue (pulsing) | Run is currently active |
| `failed` | Red | Run was terminated (loop, cost, or step limit) |
| `cost_exceeded` | Amber | Run hit the cost ceiling |
| `loop_detected` | Purple | Run was caught in an infinite loop |
| `terminated` | Red | Run was manually killed via CLI or API |

## Admin Token

The dashboard requires an admin token for sensitive operations:

1. Set `STEERPLANE_ADMIN_TOKEN` before starting the API
2. Or copy the auto-generated token from API startup logs
3. Click the "Admin Token" button in the dashboard navbar
4. Paste the token — it's stored in browser localStorage

Without the admin token, you can still view runs and steps, but cannot manage policies or API keys.

## API Connection

The navbar shows "API Connected" (green dot) when the dashboard can reach the FastAPI backend. If you see issues:

1. Make sure the API is running: `uvicorn app.main:app --reload`
2. Check that the API URL matches (default: `http://localhost:8000`)
3. Verify CORS is configured in `api/app/main.py`
4. If using Docker: `docker compose ps` to check service health
