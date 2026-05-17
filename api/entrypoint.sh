#!/bin/sh
set -e

echo "[SteerPlane] Running database migrations..."
python -m alembic upgrade head 2>/dev/null || echo "[SteerPlane] No migrations pending (or running on fresh DB)."

echo "[SteerPlane] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
