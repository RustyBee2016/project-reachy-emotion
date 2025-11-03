"""Expose Prometheus metrics for the Media Mover service."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..metrics import REGISTRY

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> Response:  # noqa: D401
    """Return all registered Prometheus metrics for scraping."""

    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
