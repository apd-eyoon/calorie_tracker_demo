# syntax=docker/dockerfile:1

# --------------------------------------------------------------------------- #
# Stage 1 - build the React (TypeScript) frontend, if it is present.
# The build is optional so the backend image can always be built on its own.
# --------------------------------------------------------------------------- #
FROM node:20-alpine AS frontend

WORKDIR /build
COPY . .

RUN set -eux; \
    mkdir -p /frontend-dist; \
    src=""; \
    for candidate in frontend ui client web app-ui; do \
        if [ -f "$candidate/package.json" ]; then src="$candidate"; break; fi; \
    done; \
    if [ -z "$src" ] && [ -f package.json ]; then src="."; fi; \
    if [ -n "$src" ]; then \
        cd "$src"; \
        if [ -f package-lock.json ]; then npm ci; else npm install; fi; \
        npm run build; \
        out=""; \
        for d in dist build out; do \
            if [ -f "$d/index.html" ]; then out="$d"; break; fi; \
        done; \
        if [ -n "$out" ]; then cp -r "$out"/. /frontend-dist/; \
        else echo "WARNING: frontend build produced no index.html"; fi; \
    else \
        echo "No frontend package.json found - building API-only image"; \
    fi

# --------------------------------------------------------------------------- #
# Stage 2 - FastAPI backend
# --------------------------------------------------------------------------- #
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    STATIC_DIR=/app/static

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Application code (alembic.ini, alembic/, app/, scripts/)
COPY backend/ /app/

# Built SPA (empty directory when no frontend was present)
COPY --from=frontend /frontend-dist/ /app/static/

RUN chmod +x /app/scripts/*.sh

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1

# Runs `alembic upgrade head` before starting uvicorn on 0.0.0.0:8080.
CMD ["sh", "/app/scripts/start.sh"]
