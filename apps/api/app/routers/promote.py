"""Router scaffolding for promotion endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..deps import get_promote_service
from ..schemas import (
    ResetManifestRequest,
    ResetManifestResponse,
)
from ..services import (
    PromoteService,
)

router = APIRouter(prefix="/api/v1/promote", tags=["promote"])

CORRELATION_ID_HEADER = "X-Correlation-ID"


def _resolve_correlation_id(request: Request) -> str:
    header_value = request.headers.get(CORRELATION_ID_HEADER)
    if header_value:
        return header_value.strip()
    return str(uuid4())


def _error_detail(message: str, correlation_id: str) -> dict[str, str]:
    return {"error": message, "correlation_id": correlation_id}


@router.post("/stage", status_code=status.HTTP_410_GONE)
async def stage_videos(request_ctx: Request):
    """Removed — use POST /api/v1/media/promote with dest_split='train'."""

    correlation_id = _resolve_correlation_id(request_ctx)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=_error_detail(
            "This endpoint has been removed. "
            "Use POST /api/v1/media/promote with dest_split='train' and a 3-class label.",
            correlation_id,
        ),
        headers={CORRELATION_ID_HEADER: correlation_id},
    )


@router.post(
    "/reset-manifest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ResetManifestResponse,
)
async def reset_manifest(  # noqa: D401
    payload: ResetManifestRequest,
    request_ctx: Request,
    response: Response,
    service: PromoteService = Depends(get_promote_service),
):
    """Reset manifest state for training orchestrators."""

    correlation_id = _resolve_correlation_id(request_ctx)
    service.set_correlation_id(correlation_id)
    run_id = str(payload.run_id) if payload.run_id is not None else None
    service.reset_manifest(reason=payload.reason, run_id=run_id)
    await service.commit()
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return ResetManifestResponse.from_request(request=payload)


@router.post("/sample", status_code=status.HTTP_410_GONE)
async def sample_split(request_ctx: Request):
    """Removed — use run-scoped frame dataset preparation instead."""

    correlation_id = _resolve_correlation_id(request_ctx)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=_error_detail(
            "This endpoint has been removed. "
            "Use run-scoped frame dataset preparation for training runs.",
            correlation_id,
        ),
        headers={CORRELATION_ID_HEADER: correlation_id},
    )

