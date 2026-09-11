# ---------------------------------------------------------------------------
# Stage 1 - build the React + TypeScript SPA to static files
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend

WORKDIR /build

# package-lock.json is optional (matched by the glob alongside package.json).
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 - FastAPI runtime that serves the API and the built SPA on one port
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    STATIC_DIR=/app/backend/static

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Backend source (API layer + db layer). Requirements are installed from
# whichever requirements file the backend layer provides.
COPY backend/ /app/backend/

RUN set -eux; \
    pip install --upgrade pip; \
    if [ -f /app/backend/requirements.txt ]; then \
        pip install -r /app/backend/requirements.txt; \
    fi; \
    if [ -f /app/backend/requirements-db.txt ]; then \
        pip install -r /app/backend/requirements-db.txt; \
    fi; \
    pip install "fastapi>=0.110" "uvicorn[standard]>=0.29"

# Built SPA -> served by FastAPI from "/" (single port, no nginx).
COPY --from=frontend /build/dist/ /app/backend/static/
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/ui_static_server.py /app/ui_static_server.py
RUN chmod +x /app/entrypoint.sh \
    && if [ -f /app/backend/scripts/run_migrations.sh ]; then chmod +x /app/backend/scripts/run_migrations.sh; fi

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
