from __future__ import annotations

import os

from fastapi import FastAPI

# Routers
from apps.api.routers import gateway, media, metrics_router


def create_app() -> FastAPI:            # '->' FastAPI object must be returned
    root_path = os.getenv("API_ROOT_PATH", "")
    app = FastAPI(title="Reachy Gateway API", version="0.08.3.3", root_path=root_path)

    # Mount routers (paths defined within each router, e.g., /api/videos/{video_id})
    app.include_router(gateway.router)
    app.include_router(media.router)
    app.include_router(metrics_router)

    return app


app = create_app()

