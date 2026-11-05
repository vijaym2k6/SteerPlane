# Installation

## SDK Installation

### From PyPI

```bash
pip install steerplane
```

### With Extras

```bash
pip install steerplane[cli]          # CLI tool (steerplane command)
pip install "steerplane[langchain]"       # LangChain callback handler
pip install "steerplane[openai-agents]"   # OpenAI Agents SDK
pip install "steerplane[crewai]"          # CrewAI
pip install "steerplane[autogen]"         # AutoGen (AG2)
pip install steerplane[all]          # CLI + YAML config + LangChain
```

### From Source (Development)

```bash
cd sdk
pip install -e ".[all,dev]"
```

### Dependencies

The SDK has minimal dependencies:
- `requests` — HTTP client for API communication

Optional dependencies:
- `click` — CLI tool
- `pyyaml` — Config file support
- `langchain-core` — LangChain integration
- `openai-agents` — OpenAI Agents SDK integration
- `crewai` 1.15.35 or newer — CrewAI integration
- `ag2` before 1.0 — AutoGen integration (AG2's classic API)

### TypeScript SDK

```bash
npm install steerplane
```

## API Server

### Requirements

- Python 3.10+
- PostgreSQL 16+ (recommended) or SQLite (development)

### Setup

```bash
cd api
pip install -r requirements.txt
```

### Database Configuration

**SQLite (default for development):**
No configuration needed — the database file is created automatically at `api/steerplane.db`.

**PostgreSQL (recommended for production):**

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/steerplane"
```

Run Alembic migrations:

```bash
cd api
alembic upgrade head
```

### Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Dashboard

### Requirements

- Node.js 18+
- npm 9+

### Setup

```bash
cd dashboard
npm install
```

### Start the Dashboard

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### Production Build

```bash
npm run build
npm start
```

## Docker Compose (Full Stack) — New in v0.4.0

The recommended way to run all services together:

```bash
cp .env.example .env
# Edit .env with your settings

docker compose up -d
```

This starts 3 services:
- **API** (port 8000)
- **Dashboard** (port 3000)
- **PostgreSQL** (port 5432)

## CLI Tool — New in v0.4.0

```bash
pip install steerplane[cli]

# Check API health
steerplane status

# List recent runs
steerplane runs list

# Manage API keys
steerplane keys list
steerplane keys create --name "my-agent"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEERPLANE_API_URL` | `http://localhost:8000` | API server URL (SDK + CLI) |
| `STEERPLANE_ADMIN_TOKEN` | auto-generated | Admin token for sensitive routes |
| `DATABASE_URL` | `sqlite:///steerplane.db` | Database connection string |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Dashboard → API URL |
| `STEERPLANE_CONFIG` | auto-discovered | Path to `.steerplane.yml` |

## Verification

After starting all services, verify everything is connected:

1. **API**: Visit `http://localhost:8000/docs` — you should see the Swagger UI
2. **Dashboard**: Visit `http://localhost:3000` — the navbar should show "API Connected"
3. **CLI**: Run `steerplane status` — should show API health
4. **SDK**: Run the demo and check the dashboard for new runs
