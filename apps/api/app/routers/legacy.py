"""Legacy endpoint compatibility layer.

This router provides backward compatibility for old endpoint paths.
All endpoints here are deprecated and will be removed in a future version.
Clients should migrate to the /api/v1/ endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from ..config import AppConfig, get_config
from .media_v1 import list_videos as list_videos_v1

router = APIRouter(tags=["legacy"])

logger = logging.getLogger(__name__)

DEPRECATION_WARNING = (
    "This endpoint is deprecated and will be removed in v0.09.x. "
    "Please migrate to /api/v1/ endpoints. "
    "See documentation at /docs for details."
)


def _add_deprecation_headers(response: Response) -> None:
    """Add deprecation warning headers to response."""
    response.headers["X-API-Deprecated"] = "true"
    response.headers["X-API-Deprecation-Message"] = DEPRECATION_WARNING
    response.headers["X-API-Sunset"] = "2026-01-01"  # Planned removal date


@router.get("/api/videos/list")
async def legacy_list_videos(
    request: Request,
    response: Response,
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config: AppConfig = Depends(get_config),
) -> Dict[str, Any]:
    """Legacy endpoint for listing videos.
    
    DEPRECATED: Use /api/v1/media/list instead.
    
    This endpoint redirects to the v1 API but returns the old response format
    for backward compatibility.
    """
    logger.warning(
        "Legacy endpoint accessed",
        extra={
            "endpoint": "/api/videos/list",
            "new_endpoint": "/api/v1/media/list"
        }
    )
    
    # Add deprecation headers
    _add_deprecation_headers(response)
    
    # Call v1 endpoint
    v1_response = await list_videos_v1(request=request, split=split, limit=limit, offset=offset, config=config)
    
    # Convert to old format (unwrap the envelope)
    old_format = {
        "items": v1_response.data.items,
        "total": v1_response.data.pagination.total,
        "limit": v1_response.data.pagination.limit,
        "offset": v1_response.data.pagination.offset,
    }
    
    return old_format


@router.get("/api/media/videos/list")
async def legacy_list_videos_compat(
    request: Request,
    response: Response,
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config: AppConfig = Depends(get_config),
) -> Dict[str, Any]:
    """Legacy compatibility endpoint for listing videos.
    
    DEPRECATED: Use /api/v1/media/list instead.
    
    This endpoint redirects to the v1 API but returns the old response format
    for backward compatibility.
    """
    logger.warning(
        "Legacy endpoint accessed",
        extra={
            "endpoint": "/api/media/videos/list",
            "new_endpoint": "/api/v1/media/list"
        }
    )
    
    # Add deprecation headers
    _add_deprecation_headers(response)
    
    # Call v1 endpoint
    v1_response = await list_videos_v1(request=request, split=split, limit=limit, offset=offset, config=config)
    
    # Convert to old format (unwrap the envelope)
    old_format = {
        "items": v1_response.data.items,
        "total": v1_response.data.pagination.total,
        "limit": v1_response.data.pagination.limit,
        "offset": v1_response.data.pagination.offset,
    }
    
    return old_format


@router.post("/api/media/promote")
async def legacy_promote(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> JSONResponse:
    """Legacy promote endpoint (stub).
    
    DEPRECATED: Use /api/v1/promote/stage instead.
    
    This endpoint is a stub that returns a success response but does not
    actually perform any promotion. It exists only for backward compatibility.
    """
    logger.warning(
        "Legacy endpoint accessed",
        extra={
            "endpoint": "/api/media/promote",
            "new_endpoint": "/api/v1/promote/stage"
        }
    )
    
    body: Dict[str, Any] = await request.json()
    
    response = JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "message": "This is a legacy stub endpoint. Use /api/v1/promote/stage for actual promotion.",
            "deprecated": True,
            "new_endpoint": "/api/v1/promote/stage"
        }
    )
    
    _add_deprecation_headers(response)
    
    return response


@router.get("/api/media")
async def legacy_media_root() -> JSONResponse:
    """Legacy media root endpoint.
    
    DEPRECATED: Use /api/v1/health instead.
    """
    logger.warning(
        "Legacy endpoint accessed",
        extra={
            "endpoint": "/api/media",
            "new_endpoint": "/api/v1/health"
        }
    )
    
    response = JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "media-mover",
            "deprecated": True,
            "message": DEPRECATION_WARNING
        }
    )
    
    _add_deprecation_headers(response)
    
    return response


@router.get("/media/health")
async def legacy_health() -> JSONResponse:
    """Legacy health check endpoint.
    
    DEPRECATED: Use /api/v1/health instead.
    """
    logger.warning(
        "Legacy endpoint accessed",
        extra={
            "endpoint": "/media/health",
            "new_endpoint": "/api/v1/health"
        }
    )
    
    response = JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "deprecated": True,
            "message": DEPRECATION_WARNING
        }
    )
    
    _add_deprecation_headers(response)
    
    return response
