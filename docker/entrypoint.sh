#!/usr/bin/env sh
# Container entrypoint:
#   1. run Alembic migrations (when the db layer ships the helper script)
#   2. serve the FastAPI app on 0.0.0.0:8080
#
# If the backend API module is not present/importable yet, fall back to a
# static-only server so the built SPA is still reachable in a browser.
set -eu

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8080}"
STATIC_DIR="${STATIC_DIR:-/app/backend/static}"
export STATIC_DIR

if [ -f /app/backend/scripts/run_migrations.sh ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "[entrypoint] applying database migrations"
    sh /app/backend/scripts/run_migrations.sh || echo "[entrypoint] migrations failed - continuing" >&2
fi

importable() {
    python - "$1" <<'PY' >/dev/null 2>&1
import sys
target = sys.argv[1]
mod, _, attr = target.partition(":")
module = __import__(mod, fromlist=["*"])
getattr(module, attr or "app")
PY
}

APP_MODULE="${APP_MODULE:-}"
if [ -z "$APP_MODULE" ]; then
    for candidate in app.main:app app.api.main:app main:app; do
        if importable "$candidate"; then
            APP_MODULE="$candidate"
            break
        fi
    done
elif ! importable "$APP_MODULE"; then
    APP_MODULE=""
fi

if [ -n "$APP_MODULE" ]; then
    echo "[entrypoint] starting $APP_MODULE on $HOST:$PORT"
    exec uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT"
fi

echo "[entrypoint] backend app module unavailable - serving static SPA only" >&2
exec uvicorn ui_static_server:app --app-dir /app --host "$HOST" --port "$PORT"
