"""Media Mover FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..routers import media
from .routers import metrics, promote
from .deps import get_settings_dep


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Perform setup/teardown for the FastAPI application."""

    # Future: initialize DB connections, background tasks, etc.
    yield
    # Cleanup hooks can be added here when needed.


def create_app() -> FastAPI:
    settings = get_settings_dep()

    app = FastAPI(title="Reachy Media Mover", version="0.08.4.3", root_path=settings.api_root_path, lifespan=lifespan)

    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ui_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    app.include_router(media.router)
    app.include_router(metrics.router)
    app.include_router(promote.router)

    return app


app = create_app()
