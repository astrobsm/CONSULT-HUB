#!/bin/sh
set -e

echo "Applying database migrations…"
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding demo data…"
  python -m app.seed || echo "Seed skipped (already present or failed)."
fi

# Single worker: the escalation/reminder schedulers must run once, not per worker.
echo "Starting API…"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
