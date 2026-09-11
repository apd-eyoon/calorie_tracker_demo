"""Fallback FastAPI app that serves the built SPA only.

Used by the container entrypoint when the backend API module is not importable
yet, so the UI is still reachable at http://127.0.0.1:8080/. Once the backend
layer provides ``app.main:app``, that application is served instead and it is
responsible for mounting the same static directory at ``/``.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/backend/static"))
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(title="Calorie Tracker UI")


@app.get("/healthz", include_in_schema=False)
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "mode": "static-ui-only"})


if STATIC_DIR.is_dir():
    # html=True makes StaticFiles serve index.html for "/" and unknown paths,
    # which is what a client-side router needs.
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(INDEX_FILE)
