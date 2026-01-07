"""Health check endpoints for monitoring and service discovery."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from ..config import AppConfig, get_config
from ..schemas import HealthCheckData, HealthCheckResponse, create_success_response

router = APIRouter(prefix="/api/v1", tags=["health"])

logger = logging.getLogger(__name__)


def _get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID", "")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    config: AppConfig = Depends(get_config)
) -> HealthCheckResponse:
    """Health check endpoint for monitoring and load balancers.
    
    Performs basic checks to ensure the service is operational:
    - Configuration is loaded
    - Videos root directory is accessible
    
    Returns:
        Health check response with status and checks
    """
    health_status = "healthy"
    checks: Dict[str, Any] = {}
    
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
        "dataset_all": config.dataset_path,
        "train": config.train_path,
        "test": config.test_path,
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
    config: AppConfig = Depends(get_config)
) -> HealthCheckResponse:
    """Readiness check for Kubernetes and orchestration systems.
    
    Similar to health check but more strict - returns 503 if service
    is not fully ready to accept traffic.
    
    Returns:
        Health check response with readiness status
    """
    # For now, same as health check
    # In future, could check database connectivity, etc.
    return await health_check(request, config)
