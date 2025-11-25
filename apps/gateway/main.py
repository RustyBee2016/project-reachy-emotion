"""Reachy Gateway FastAPI application for Ubuntu 2.

This gateway proxies requests to the Media Mover on Ubuntu 1 and provides
a unified API surface for the Streamlit UI and external clients.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logging.getLogger(__name__).info(f"Loaded environment from {env_file}")

from apps.api.routers.gateway import router as gateway_router
from .config import load_config

logger = logging.getLogger(__name__)

# Global HTTP client for proxying requests
_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Perform setup/teardown for the Gateway application."""
    global _http_client
    
    # Load and validate configuration on startup
    try:
        config = load_config()
        logger.info("Gateway configuration loaded successfully")
        
        # Log configuration (with secrets masked)
        config_dict = config.log_configuration(mask_secrets=True)
        logger.info("Gateway configuration", extra={"config": config_dict})
        
        # Store config in app state for routers to access
        app.state.config = config
        
    except Exception as e:
        logger.error(f"Gateway configuration validation failed: {e}")
        raise
    
    # Initialize HTTP client for proxying
    try:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
        app.state.http_client = _http_client
        logger.info("HTTP client initialized for proxying")
    except Exception as e:
        logger.error(f"Failed to initialize HTTP client: {e}")
        raise
    
    yield
    
    # Cleanup: close HTTP client
    if _http_client:
        try:
            await _http_client.aclose()
            logger.info("HTTP client closed")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}", exc_info=True)


def create_app() -> FastAPI:
    """Create and configure the Gateway FastAPI application."""
    
    # Load configuration
    config = load_config()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = FastAPI(
        title="Reachy Gateway",
        version="0.08.4.3",
        description="API Gateway for Reachy Emotion system on Ubuntu 2",
        root_path=config.api_root_path,
        lifespan=lifespan,
    )

    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.ui_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    # Register gateway router
    app.include_router(gateway_router, tags=["gateway"])
    
    logger.info(
        f"Gateway app created - will listen on {config.api_host}:{config.api_port}"
    )

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    config = load_config()
    uvicorn.run(
        "apps.gateway.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=False,
        log_level=config.log_level.lower(),
    )
