"""Router scaffolding for promotion endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..deps import get_promote_service
from ..schemas import (
    ResetManifestRequest,
    ResetManifestResponse,
    SampleRequest,
    SampleResponse,
    StageRequest,
    StageResponse,
)
from ..services import (
    PromoteService,
    PromotionConflictError,
    PromotionError,
    PromotionValidationError,
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


@router.post(
    "/stage",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StageResponse,
)
async def stage_videos(  # noqa: D401
    payload: StageRequest,
    request_ctx: Request,
    response: Response,
    service: PromoteService = Depends(get_promote_service),
):
    """Deprecated compatibility endpoint for legacy stage payloads."""

    correlation_id = _resolve_correlation_id(request_ctx)
    response.headers["Warning"] = (
        "299 - Deprecated endpoint: use /api/media/promote with dest_split='train'"
    )
    service.set_correlation_id(correlation_id)
    try:
        result = await service.stage_to_dataset_all(
            [str(video_id) for video_id in payload.video_ids],
            label=payload.label,
            dry_run=payload.dry_run,
        )
        if not payload.dry_run:
            await service.commit()
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return StageResponse.from_result(status="accepted", result=result)
    except PromotionValidationError as exc:
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc
    except PromotionConflictError as exc:
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc
    except PromotionError as exc:  # pragma: no cover (implementation pending)
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc


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


@router.post(
    "/sample",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SampleResponse,
)
async def sample_split(  # noqa: D401
    payload: SampleRequest,
    request_ctx: Request,
    response: Response,
    service: PromoteService = Depends(get_promote_service),
):
    """Deprecated compatibility endpoint for legacy sample payloads."""

    correlation_id = _resolve_correlation_id(request_ctx)
    response.headers["Warning"] = (
        "299 - Deprecated endpoint: use run-scoped frame dataset preparation"
    )
    service.set_correlation_id(correlation_id)
    try:
        result = await service.sample_split(
            run_id=str(payload.run_id),
            target_split=payload.target_split,
            sample_fraction=float(payload.sample_fraction),
            strategy=payload.strategy,
            seed=payload.seed,
            dry_run=payload.dry_run,
        )
        if not payload.dry_run:
            await service.commit()
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return SampleResponse.from_result(status="accepted", result=result)
    except PromotionValidationError as exc:
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc
    except PromotionConflictError as exc:
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc
    except PromotionError as exc:  # pragma: no cover (implementation pending)
        await service.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_detail(str(exc), correlation_id),
            headers={CORRELATION_ID_HEADER: correlation_id},
        ) from exc

