"""Media Mover FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..routers import media
from .routers import metrics, promote, media_v1, health, legacy
from .config import load_and_validate_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Perform setup/teardown for the FastAPI application."""

    # Load and validate configuration on startup
    try:
        config = load_and_validate_config(check_port=False)  # Port already bound by this point
        logger.info("Configuration loaded successfully")
        
        # Log configuration (with secrets masked)
        config_dict = config.log_configuration(mask_secrets=True)
        logger.info("Application configuration", extra={"config": config_dict})
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Future: initialize DB connections, background tasks, etc.
    yield
    # Cleanup hooks can be added here when needed.


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Load configuration
    config = load_and_validate_config(check_port=False)

    app = FastAPI(
        title="Reachy Media Mover",
        version="0.08.4.3",
        root_path=config.api_root_path,
        lifespan=lifespan
    )

    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.ui_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    # Register v1 routers (current API)
    app.include_router(health.router)
    app.include_router(media_v1.router)
    app.include_router(promote.router)
    app.include_router(metrics.router)
    
    # Register legacy routers for backward compatibility
    if config.enable_legacy_endpoints:
        app.include_router(legacy.router)
        app.include_router(media.router)  # Old media router
        logger.info("Legacy endpoints enabled (will be removed in v0.09.x)")
    else:
        logger.info("Legacy endpoints disabled")

    return app


app = create_app()
