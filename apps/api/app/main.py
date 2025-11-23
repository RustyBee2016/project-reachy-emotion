"""Media Mover FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logging.getLogger(__name__).info(f"Loaded environment from {env_file}")

from ..routers import media
from .routers import dialogue, health, legacy, media_v1, metrics, promote, websocket_cues
from .config import load_and_validate_config
from .services.thumbnail_watcher import ThumbnailWatcherService

logger = logging.getLogger(__name__)

# Global thumbnail watcher instance
_thumbnail_watcher: ThumbnailWatcherService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Perform setup/teardown for the FastAPI application."""
    global _thumbnail_watcher

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
    
    # Start thumbnail watcher service
    try:
        _thumbnail_watcher = ThumbnailWatcherService(
            videos_root=config.videos_root,
            watch_splits=["temp"],
            poll_interval=5.0,
        )
        await _thumbnail_watcher.start()
        logger.info("Thumbnail watcher service started")
    except Exception as e:
        logger.error(f"Failed to start thumbnail watcher: {e}", exc_info=True)
        # Don't fail startup if thumbnail watcher fails
    
    yield
    
    # Cleanup: stop thumbnail watcher
    if _thumbnail_watcher:
        try:
            await _thumbnail_watcher.stop()
            logger.info("Thumbnail watcher service stopped")
        except Exception as e:
            logger.error(f"Error stopping thumbnail watcher: {e}", exc_info=True)


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
    app.include_router(dialogue.router)
    app.include_router(websocket_cues.router)
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
