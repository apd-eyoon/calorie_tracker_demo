#!/usr/bin/env sh
# Apply all Alembic migrations, waiting for PostgreSQL to accept connections.
# Intended to be invoked by the backend container entrypoint before serving.
set -eu

cd "$(dirname "$0")/.."

: "${DATABASE_URL:?DATABASE_URL must be set}"

echo "[migrations] waiting for database..."
i=0
until python -c "
import os, sys
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL']
if url.startswith('postgres://'):
    url = 'postgresql://' + url[len('postgres://'):]
if url.startswith('postgresql://'):
    url = 'postgresql+psycopg2://' + url[len('postgresql://'):]
try:
    create_engine(url).connect().execute(text('SELECT 1'))
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "[migrations] database not reachable after 60 attempts" >&2
        exit 1
    fi
    sleep 1
done

echo "[migrations] running alembic upgrade head"
alembic upgrade head
echo "[migrations] done"
