#!/usr/bin/env sh
# Container entrypoint: run Alembic migrations, then serve the API on 0.0.0.0.
set -eu

cd "$(dirname "$0")/.."

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

sh ./scripts/run_migrations.sh

echo "[start] launching uvicorn on ${HOST}:${PORT}"
exec uvicorn app.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --proxy-headers \
    --forwarded-allow-ips '*'
