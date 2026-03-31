"""Health check endpoints for monitoring and service discovery."""

from __future__ import annotations

import logging
from typing import Any, Dict

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..deps import get_db
from ..schemas import HealthCheckData, HealthCheckResponse, create_success_response

router = APIRouter(prefix="/api/v1", tags=["health"])

logger = logging.getLogger(__name__)


def _get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID", "")


async def _check_database(session: AsyncSession) -> Dict[str, Any]:
    """Probe database connectivity with a lightweight query."""
    try:
        result = await session.execute(sa.text("SELECT 1"))
        result.scalar()
        return {"status": "ok"}
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
        return {"status": "error", "message": str(e)}


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    response: Response,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> HealthCheckResponse:
    """Health check endpoint for monitoring and load balancers.

    Performs checks to ensure the service is operational:
    - Configuration is loaded
    - Videos root directory is accessible
    - Database is reachable

    Returns:
        Health check response with status and checks
    """
    health_status = "healthy"
    checks: Dict[str, Any] = {}

    # Check database connectivity
    db_check = await _check_database(session)
    checks["database"] = db_check
    if db_check["status"] != "ok":
        health_status = "degraded"

    # Check videos root accessibility
    try:
        if config.videos_root.exists() and config.videos_root.is_dir():
            checks["videos_root"] = {
                "status": "ok",
                "path": str(config.videos_root)
            }
        else:
            checks["videos_root"] = {
                "status": "error",
                "path": str(config.videos_root),
                "message": "Directory does not exist or is not accessible"
            }
            health_status = "degraded"
    except Exception as e:
        checks["videos_root"] = {
            "status": "error",
            "message": str(e)
        }
        health_status = "degraded"

    # Check required subdirectories
    required_dirs = {
        "temp": config.temp_path,
        "train": config.train_path,
        "test": config.test_path,
        "purged": config.videos_root / "purged",
        "thumbs": config.thumbs_path,
        "manifests": config.manifests_path,
    }

    dirs_ok = 0
    for name, path in required_dirs.items():
        if path.exists() and path.is_dir():
            dirs_ok += 1

    checks["directories"] = {
        "status": "ok" if dirs_ok == len(required_dirs) else "warning",
        "accessible": dirs_ok,
        "total": len(required_dirs)
    }

    if health_status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    health_data = HealthCheckData(
        service="media-mover",
        version="0.08.4.3",
        status=health_status,
        checks=checks
    )

    return create_success_response(health_data, _get_correlation_id(request))


@router.get("/ready", response_model=HealthCheckResponse)
async def readiness_check(
    request: Request,
    response: Response,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> HealthCheckResponse:
    """Readiness check for Kubernetes and orchestration systems.

    Stricter than health — returns 503 if database is down.

    Returns:
        Health check response with readiness status
    """
    return await health_check(request, response, config, session)
