# Installation

## SDK Installation

### From Source (Development)

```bash
cd sdk
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install steerplane
```

### Dependencies

The SDK has minimal dependencies:
- `httpx` — HTTP client for API communication
- `python-dotenv` — Environment variable management

## API Server

### Requirements

- Python 3.10+
- PostgreSQL 17 (recommended) or SQLite (development)

### Setup

```bash
cd api
pip install -r requirements.txt
```

### Database Configuration

**SQLite (default for development):**
No configuration needed — the database file is created automatically at `api/steerplane.db`.

**PostgreSQL (recommended for production):**

1. Install PostgreSQL 17
2. Create a database:
   ```sql
   CREATE DATABASE steerplane;
   ```
3. Run the setup script:
   ```bash
   python scripts/setup_postgres.py
   ```
4. Update `api/app/config.py` with your PostgreSQL connection string:
   ```python
   DATABASE_URL = "postgresql://user:password@localhost:5432/steerplane"
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

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEERPLANE_API_URL` | `http://localhost:8000` | API server URL |
| `DATABASE_URL` | `sqlite:///steerplane.db` | Database connection string |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Dashboard → API URL |

## Verification

After starting all services, verify everything is connected:

1. **API**: Visit `http://localhost:8000/docs` — you should see the Swagger UI
2. **Dashboard**: Visit `http://localhost:3000` — the navbar should show "API Connected"
3. **SDK**: Run the demo and check the dashboard for new runs
