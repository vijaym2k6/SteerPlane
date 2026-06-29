#!/bin/sh
set -e

echo "[SteerPlane] Running database migrations..."
# Fail loudly: with `set -e`, a non-zero exit here aborts startup rather than
# booting the API against an unmigrated/half-migrated schema.
python -m alembic upgrade head

echo "[SteerPlane] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
