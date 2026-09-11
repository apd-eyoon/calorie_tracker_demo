"""Application configuration, sourced entirely from environment variables.

Required / supported variables:

* ``DATABASE_URL``       - PostgreSQL connection string (see ``app.db.session``)
* ``JWT_SECRET``         - HMAC secret used to sign access tokens
* ``JWT_ALGORITHM``      - defaults to ``HS256``
* ``JWT_EXPIRES_MINUTES``- access-token lifetime in minutes (default 10080 = 7d)
* ``NUTRITION_API_KEY``  - USDA FoodData Central API key (server-side only, it
  is never returned to the client)
* ``FDC_BASE_URL``       - FDC API base URL (override for tests)
* ``FDC_TIMEOUT_SECONDS``- upstream timeout in seconds (default 10)
* ``STATIC_DIR``         - directory containing the built React app
* ``CORS_ORIGINS``       - comma separated list, ``*`` by default
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None or value == "" else value


def _default_static_dir() -> str:
    """Best-effort location of the built frontend assets."""
    here = Path(__file__).resolve()
    candidates = [
        Path("/app/static"),
        Path("/app/backend/static"),
        here.parents[2] / "static",  # <backend>/static
        here.parents[3] / "static",  # <repo>/static
        here.parents[3] / "frontend" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return str(candidate)
    return str(candidates[0])


class Settings:
    """Plain settings object (no external dependency required)."""

    def __init__(self) -> None:
        self.app_name: str = _env("APP_NAME", "Calorie Tracker API")
        self.host: str = _env("HOST", "0.0.0.0")
        self.port: int = int(_env("PORT", "8080"))

        self.database_url: str = _env("DATABASE_URL")

        self.jwt_secret: str = _env("JWT_SECRET", "dev-insecure-secret-change-me")
        self.jwt_algorithm: str = _env("JWT_ALGORITHM", "HS256")
        self.jwt_expires_minutes: int = int(_env("JWT_EXPIRES_MINUTES", "10080"))

        # Server-side only. Never serialize this into an API response.
        self.nutrition_api_key: str = _env("NUTRITION_API_KEY")
        self.fdc_base_url: str = _env(
            "FDC_BASE_URL", "https://api.nal.usda.gov/fdc/v1"
        ).rstrip("/")
        self.fdc_timeout_seconds: float = float(_env("FDC_TIMEOUT_SECONDS", "10"))
        self.fdc_page_size: int = int(_env("FDC_PAGE_SIZE", "10"))

        self.static_dir: str = _env("STATIC_DIR", _default_static_dir())
        self.cors_origins: List[str] = [
            origin.strip()
            for origin in _env("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]

        # eaten_at validation window
        self.max_past_days: int = int(_env("MAX_PAST_DAYS", "365"))
        # Tolerance (seconds) for client/server clock skew on "no future dates".
        self.future_skew_seconds: int = int(_env("FUTURE_SKEW_SECONDS", "60"))

    @property
    def has_nutrition_api_key(self) -> bool:
        return bool(self.nutrition_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
