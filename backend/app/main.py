"""FastAPI application entrypoint.

Serves the JSON API under ``/auth``, ``/foods`` and ``/log`` and the built React
SPA (with history-API fallback) from ``/``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from app.api.routes import auth as auth_routes
from app.api.routes import foods as foods_routes
from app.api.routes import log as log_routes
from app.core.config import settings

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")

# Paths owned by the API; never answered with the SPA shell.
API_PREFIXES = ("/auth", "/foods", "/log", "/health", "/docs", "/redoc", "/openapi.json")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Calorie tracker API: authentication, USDA FoodData Central proxy and "
        "daily macro logging."
    ),
)

_allow_all_origins = settings.cors_origins == ["*"]

# The SPA is served from the same origin, so CORS only matters for local
# development (Vite dev server) - permissive by default, configurable via
# CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    # Credentials cannot be combined with the "*" wildcard.
    allow_credentials=not _allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_errors(exc: RequestValidationError):
    """JSON-serializable projection of pydantic validation errors."""
    return [
        {
            "loc": [str(part) for part in error.get("loc", [])],
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in exc.errors()
    ]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with a stable, serializable shape for validation failures."""
    errors = _safe_errors(exc)
    detail = "; ".join(
        f"{'.'.join(error['loc'][1:]) or 'body'}: {error['msg']}" for error in errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail or "Validation error", "errors": errors},
    )


# --------------------------------------------------------------------------- #
# Health / meta
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        # Boolean only - the key itself is never exposed.
        "nutrition_api_key_configured": settings.has_nutrition_api_key,
    }


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# API routers
# --------------------------------------------------------------------------- #
app.include_router(auth_routes.router)
app.include_router(foods_routes.router)
app.include_router(log_routes.router)


# --------------------------------------------------------------------------- #
# Static SPA
# --------------------------------------------------------------------------- #
class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` for client-side routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                # Do not shadow missing static assets with the HTML shell.
                if not path.startswith("assets/") and "." not in Path(path).name:
                    return await super().get_response("index.html", scope)
            raise


def _mount_spa() -> None:
    static_dir = Path(settings.static_dir)
    index_file = static_dir / "index.html"

    if static_dir.is_dir() and index_file.is_file():
        app.mount("/", SPAStaticFiles(directory=str(static_dir), html=True), name="spa")
        logger.info("Serving frontend from %s", static_dir)
        return

    logger.warning(
        "No built frontend found at %s - serving API-only placeholder at /",
        static_dir,
    )

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "message": "API is running. Frontend build not found.",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> Response:
        if any(("/" + full_path).startswith(prefix) for prefix in API_PREFIXES):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        index = Path(settings.static_dir) / "index.html"
        if index.is_file():
            return FileResponse(str(index))
        return JSONResponse(status_code=404, content={"detail": "Not Found"})


_mount_spa()
