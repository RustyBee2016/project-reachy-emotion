"""Application settings for the Media Mover API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List


def _env_list(key: str, default: List[str]) -> List[str]:
    """Read a comma-separated environment variable into a list."""

    raw = os.getenv(key)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Runtime configuration sourced from environment variables or .env files."""

    api_root_path: str = field(default_factory=lambda: os.getenv("MEDIA_MOVER_API_ROOT_PATH", "/api/media"))
    ui_origins: List[str] = field(
        default_factory=lambda: _env_list(
            "MEDIA_MOVER_UI_ORIGINS",
            ["https://10.0.4.140", "https://10.0.4.130"],
        )
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "MEDIA_MOVER_DATABASE_URL",
            "postgresql+psycopg2://reachy_app:reachy_app@localhost:5432/reachy_local",
        )
    )
    videos_root: str = field(
        default_factory=lambda: os.getenv("MEDIA_MOVER_VIDEOS_ROOT", "/mnt/videos"),
    )
    manifests_root: str = field(
        default_factory=lambda: os.getenv(
            "MEDIA_MOVER_MANIFESTS_ROOT",
            "/mnt/videos/manifests",
        ),
    )
    enable_cors: bool = field(
        default_factory=lambda: os.getenv("MEDIA_MOVER_ENABLE_CORS", "true").lower() in {"1", "true", "yes"}
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
