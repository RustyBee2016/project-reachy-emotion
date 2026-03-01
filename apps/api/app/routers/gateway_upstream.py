"""Upstream handlers backing the Ubuntu 2 gateway proxy.

These endpoints run on Ubuntu 1 (Media Mover) and expose lightweight APIs
that the gateway forwards requests to. They integrate with the filesystem,
PostgreSQL models, and manifest orchestration to provide real data to the
Reachy UI.
"""
# blank comment intentional to create commit
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db import models
from ..manifest import ManifestBackend
from ..deps import get_db, get_manifest_backend
from ..services.video_query_service import VideoQueryService
from ..schemas.video import EnhancedVideoMetadataPayload
_default_emotions = {"neutral", "happy", "sad"}
_env_emotions = os.getenv("MEDIA_MOVER_EMOTIONS")
if _env_emotions:
    VALID_EMOTIONS = {item.strip().lower() for item in _env_emotions.split(",") if item.strip()}
    if not VALID_EMOTIONS:
        VALID_EMOTIONS = _default_emotions
else:
    VALID_EMOTIONS = _default_emotions

router = APIRouter(tags=["gateway-upstream"])

_SPLITS = ("temp", "train", "test", "purged")


def _validate_pipeline_id(pipeline_id: str) -> str:
    normalized = pipeline_id.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": "pipeline_id must not be empty"},
        )
    if len(normalized) > 36:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": "pipeline_id must be <= 36 chars"},
        )
    return normalized


@router.get("/api/upstream/health")
async def upstream_health() -> Dict[str, str]:
    """Confirm the upstream router is loaded and responding."""
    return {"status": "ok", "router": "gateway_upstream"}


class VideoMetadataPayload(BaseModel):
    schema_version: str = Field(default="v1")
    video_id: str
    file_name: str
    split: str
    file_path: str
    size_bytes: int
    mtime: float


def _find_video_file(video_identifier: str, config: AppConfig) -> Tuple[Path, str]:
    """Find a video file across known splits.

    Args:
        video_identifier: Incoming identifier (may include extension).
        config: Application configuration with videos_root.

    Returns:
        Tuple of (absolute_path, split)

    Raises:
        HTTPException: 404 when no matching file is found.
    """

    candidate_names = {video_identifier}
    if "." in video_identifier:
        candidate_names.add(Path(video_identifier).stem)
    else:
        # Support common extension fallback (.mp4)
        candidate_names.add(f"{video_identifier}.mp4")

    for split in _SPLITS:
        split_root = config.videos_root / split
        if not split_root.exists():
            continue

        for candidate in candidate_names:
            candidate_path = split_root / candidate
            if candidate_path.exists():
                return candidate_path, split

    # Fallback: allow direct relative paths (e.g., "test/test_vid.mp4") or files stored
    # at the root of videos_root
    for candidate in candidate_names:
        direct_path = (config.videos_root / candidate).resolve()
        try:
            direct_path.relative_to(config.videos_root)
        except ValueError:
            # Candidate escaped the videos_root via ".."; skip it.
            continue

        if direct_path.exists() and direct_path.is_file():
            parent = direct_path.parent
            if parent == config.videos_root:
                split = "root"
            else:
                split = parent.relative_to(config.videos_root).parts[0]
            return direct_path, split

    # Optional shallow glob to catch legacy placements (one directory deep)
    for candidate in candidate_names:
        matches = list(config.videos_root.glob(f"*/{candidate}"))
        if not matches:
            continue
        match = matches[0]
        split = match.parent.relative_to(config.videos_root).parts[0]
        return match, split

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "message": f"Video not found: {video_identifier}"},
    )


@router.get("/api/videos/list")
async def list_videos(
    split: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at", regex="^(created_at|updated_at|size_bytes)$"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """List videos with filtering and pagination.
    
    Query Parameters:
        split: Filter by split (temp, train, test, purged)
        label: Filter by emotion label
        limit: Number of results (1-500, default 50)
        offset: Pagination offset (default 0)
        order_by: Sort field (created_at, updated_at, size_bytes)
        order: Sort direction (asc, desc)
    """
    # Validate split
    if split and split not in ("temp", "train", "test", "purged"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_split", "message": f"Invalid split: {split}"},
        )
    
    # Validate label
    if label and label not in VALID_EMOTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_label", "message": f"Invalid label: {label}"},
        )
    
    # Build query
    stmt = select(models.Video)
    
    if split:
        stmt = stmt.where(models.Video.split == split)
    if label:
        stmt = stmt.where(models.Video.label == label)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    
    # Apply sorting
    order_col = getattr(models.Video, order_by)
    if order == "desc":
        stmt = stmt.order_by(desc(order_col))
    else:
        stmt = stmt.order_by(asc(order_col))
    
    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)
    
    # Execute query
    result = await session.execute(stmt)
    videos = result.scalars().all()
    
    # Build response
    video_summaries = []
    for video in videos:
        video_summaries.append({
            "video_id": video.video_id,
            "file_name": Path(video.file_path).name,
            "file_path": video.file_path,
            "split": video.split.value if hasattr(video.split, 'value') else str(video.split),
            "label": video.label.value if video.label and hasattr(video.label, 'value') else video.label,
            "size_bytes": video.size_bytes,
            "duration_sec": video.duration_sec,
            "fps": video.fps,
            "width": video.width,
            "height": video.height,
            "sha256": video.sha256,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "updated_at": video.updated_at.isoformat() if video.updated_at else None,
        })
    
    has_more = (offset + limit) < total
    
    return {
        "status": "ok",
        "videos": video_summaries,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": has_more,
        },
    }


@router.get("/api/videos/{video_identifier:path}")
async def get_video_metadata(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Return metadata for the requested video file.
    
    Accepts either UUID or filename. Returns canonical UUID from database.
    """
    
    # Try database first
    query_service = VideoQueryService(session, config)
    video_model, lookup_method = await query_service.get_video_by_identifier(video_identifier)
    
    if video_model:
        # Found in database - return full metadata
        video_path = config.videos_root / video_model.file_path
        
        # Verify file still exists
        if not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "file_missing",
                    "message": f"Video record exists but file not found: {video_model.file_path}",
                    "video_id": video_model.video_id,
                },
            )
        
        stat_info = video_path.stat()
        payload = EnhancedVideoMetadataPayload(
            video_id=video_model.video_id,
            file_name=video_path.name,
            file_path=video_model.file_path,
            split=video_model.split.value if hasattr(video_model.split, 'value') else str(video_model.split),
            label=video_model.label.value if video_model.label and hasattr(video_model.label, 'value') else video_model.label,
            size_bytes=video_model.size_bytes,
            duration_sec=video_model.duration_sec,
            fps=video_model.fps,
            width=video_model.width,
            height=video_model.height,
            sha256=video_model.sha256,
            mtime=stat_info.st_mtime,
            created_at=video_model.created_at.isoformat() if video_model.created_at else None,
            updated_at=video_model.updated_at.isoformat() if video_model.updated_at else None,
            lookup_method=lookup_method,
        )
        return {"status": "ok", "video": payload.dict()}
    
    # Fallback to filesystem-only lookup (legacy support)
    try:
        video_path, split = _find_video_file(video_identifier, config)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Video not found in database or filesystem: {video_identifier}",
            },
        )
    
    # Return filesystem-only metadata with warning
    stat_info = video_path.stat()
    relative_path = video_path.relative_to(config.videos_root)
    payload = VideoMetadataPayload(
        video_id=Path(video_path).stem,  # Filename stem (not UUID)
        file_name=video_path.name,
        split=split,
        file_path=str(relative_path),
        size_bytes=stat_info.st_size,
        mtime=stat_info.st_mtime,
    )
    
    return {
        "status": "ok",
        "video": payload.dict(),
        "warning": "Video found in filesystem but not in database. UUID is filename stem, not canonical ID.",
    }


@router.get("/api/videos/{video_identifier:path}/thumb")
async def get_video_thumbnail(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Return the thumbnail image for a given video.
    
    Checks database for video existence before serving thumbnail.
    """
    # Verify video exists in database
    query_service = VideoQueryService(session, config)
    video_model, _ = await query_service.get_video_by_identifier(video_identifier)
    
    if not video_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {video_identifier}"},
        )
    
    # Get thumbnail path
    video_stem = Path(video_model.file_path).stem
    thumb_path = config.thumbs_path / f"{video_stem}.jpg"
    
    if not thumb_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "thumbnail_not_found",
                "message": f"Thumbnail not found for video: {video_model.video_id}",
                "video_id": video_model.video_id,
            },
        )
    
    return FileResponse(thumb_path, media_type="image/jpeg")


@router.get("/api/videos/{video_identifier:path}/url")
async def get_video_url(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Generate streaming URL for video.
    
    Returns URLs for video streaming and thumbnail.
    """
    # Get video from database
    query_service = VideoQueryService(session, config)
    video_model, lookup_method = await query_service.get_video_by_identifier(video_identifier)
    
    if not video_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {video_identifier}"},
        )
    
    # Generate URLs
    stream_url = f"/videos/{video_model.file_path}"
    thumbnail_url = f"/thumbs/{Path(video_model.file_path).stem}.jpg"
    
    return {
        "status": "ok",
        "video_id": video_model.video_id,
        "stream_url": stream_url,
        "thumbnail_url": thumbnail_url,
        "expires_at": None,  # No expiration for now
    }


class RelabelRequest(BaseModel):
    schema_version: str = Field(default="v1")
    video_id: str = Field(..., description="UUID of the video")
    new_label: str = Field(..., description="New emotion label")

    @validator("new_label")
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_EMOTIONS:
            raise ValueError(f"Label must be one of: {sorted(VALID_EMOTIONS)}")
        return normalized


@router.post("/api/relabel", status_code=status.HTTP_202_ACCEPTED)
async def relabel_video(
    payload: RelabelRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Update the label associated with a video record."""

    video = await session.get(models.Video, payload.video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {payload.video_id}"},
        )

    # SQLAlchemy Enum is configured with native_enum=False, so assigning the string is valid
    video.label = payload.new_label
    await session.commit()
    return {"status": "accepted", "video_id": payload.video_id, "new_label": payload.new_label}


class ManifestRebuildRequest(BaseModel):
    schema_version: str = Field(default="v1")
    reason: str = Field(..., description="Reason for triggering rebuild")
    run_id: Optional[str] = Field(None, description="Associated run identifier")
    reset: bool = Field(
        default=False, description="Whether to reset manifest state before scheduling rebuild"
    )


@router.post("/api/manifest/rebuild", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manifest_rebuild(
    payload: ManifestRebuildRequest,
    manifest_backend: ManifestBackend = Depends(get_manifest_backend),
) -> Dict[str, object]:
    """Schedule a manifest rebuild (and optionally reset state)."""

    if payload.reset:
        manifest_backend.reset(reason=payload.reason, run_id=payload.run_id)
    manifest_backend.schedule_rebuild(reason=payload.reason, run_id=payload.run_id)

    return {"status": "accepted", "reason": payload.reason, "run_id": payload.run_id}


@router.post("/api/v1/privacy/redact/{video_id}", status_code=status.HTTP_202_ACCEPTED)
async def redact_video(
    video_id: str,
    reason: Optional[str] = Query(default=None),
    correlation_id: Optional[str] = Query(default=None),
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Purge video media and mark the database record as purged."""
    video = await session.get(models.Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {video_id}"},
        )

    video_path = config.videos_root / str(video.file_path)
    thumb_path = config.thumbs_path / f"{Path(video.file_path).stem}.jpg"

    deleted_file = False
    deleted_thumb = False
    if video_path.exists() and video_path.is_file():
        video_path.unlink()
        deleted_file = True
    if thumb_path.exists() and thumb_path.is_file():
        thumb_path.unlink()
        deleted_thumb = True

    metadata = dict(video.extra_data or {})
    if reason:
        metadata["redact_reason"] = reason
    if correlation_id:
        metadata["correlation_id"] = correlation_id

    video.split = "purged"
    video.label = None
    video.deleted_at = datetime.now(timezone.utc)
    video.file_path = f"purged/{video_id}.mp4"
    video.extra_data = metadata

    session.add(
        models.AuditLog(
            action="privacy.redact",
            entity_type="video",
            entity_id=video_id,
            reason=reason,
            correlation_id=correlation_id,
            extra_data={"deleted_file": deleted_file, "deleted_thumb": deleted_thumb},
        )
    )
    await session.commit()

    return {
        "status": "accepted",
        "video_id": video_id,
        "deleted_file": deleted_file,
        "deleted_thumb": deleted_thumb,
        "correlation_id": correlation_id,
    }


@router.get("/api/training/status/{pipeline_id}")
async def get_training_status(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Get persisted training status from DB."""
    if pipeline_id == "latest":
        # Deterministic "latest" ordering:
        # updated_at ties can occur when inserts share the same DB timestamp resolution.
        stmt = (
            select(models.TrainingRun)
            .order_by(
                desc(models.TrainingRun.updated_at),
                desc(models.TrainingRun.created_at),
                desc(models.TrainingRun.run_id),
            )
            .limit(1)
        )
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return {"status": "unknown"}
    else:
        run_id = _validate_pipeline_id(pipeline_id)
        row = await session.get(models.TrainingRun, run_id)
        if row is None:
            return {"status": "unknown"}

    return {
        "run_id": row.run_id,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "metrics": row.metrics or {},
        "error_message": row.error_message,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/api/training/status/{pipeline_id}")
async def update_training_status(
    pipeline_id: str,
    payload: Dict[str, object],
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Persist training status updates to DB."""
    run_id = _validate_pipeline_id(pipeline_id)
    row = await session.get(models.TrainingRun, run_id)

    now = datetime.now(timezone.utc)
    if row is None:
        row = models.TrainingRun(
            run_id=run_id,
            strategy=str(payload.get("strategy") or "status_update"),
            train_fraction=0.5,
            test_fraction=0.5,
            status=str(payload.get("status") or "pending"),
            started_at=now if str(payload.get("status")) in {"pending", "sampling", "training", "evaluating"} else None,
            metrics=dict(payload.get("metrics") or {}),
            error_message=payload.get("error_message"),
        )
        session.add(row)
    else:
        if "status" in payload:
            row.status = str(payload.get("status") or row.status)
        if "metrics" in payload and isinstance(payload.get("metrics"), dict):
            merged = dict(row.metrics or {})
            merged.update(payload.get("metrics") or {})
            row.metrics = merged
        if "error_message" in payload:
            row.error_message = str(payload.get("error_message")) if payload.get("error_message") else None
        if row.started_at is None and row.status in {"pending", "sampling", "training", "evaluating"}:
            row.started_at = now

    if row.status in {"completed", "failed", "cancelled"} and row.completed_at is None:
        row.completed_at = now

    await session.commit()
    return {"status": "updated", "run_id": run_id}


@router.get("/api/deployment/status/{pipeline_id}")
async def get_deployment_status(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Get persisted deployment status from DB."""
    if pipeline_id == "latest":
        stmt = select(models.DeploymentLog).order_by(desc(models.DeploymentLog.deployed_at)).limit(1)
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return {"status": "unknown"}
    else:
        pid = _validate_pipeline_id(pipeline_id)
        stmt = (
            select(models.DeploymentLog)
            .where(models.DeploymentLog.correlation_id == pid)
            .order_by(desc(models.DeploymentLog.deployed_at))
            .limit(1)
        )
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return {"status": "unknown"}

    return {
        "pipeline_id": row.correlation_id,
        "status": row.status,
        "target_stage": row.target_stage,
        "engine_path": row.engine_path,
        "model_version": row.model_version,
        "gate_b_passed": row.gate_b_passed,
        "fps_measured": float(row.fps_measured) if row.fps_measured is not None else None,
        "latency_p50_ms": float(row.latency_p50_ms) if row.latency_p50_ms is not None else None,
        "latency_p95_ms": float(row.latency_p95_ms) if row.latency_p95_ms is not None else None,
        "gpu_memory_gb": float(row.gpu_memory_gb) if row.gpu_memory_gb is not None else None,
        "error_message": row.error_message,
        "deployed_at": row.deployed_at.isoformat() if row.deployed_at else None,
    }


@router.post("/api/deployment/status/{pipeline_id}")
async def update_deployment_status(
    pipeline_id: str,
    payload: Dict[str, object],
    session: AsyncSession = Depends(get_db),
) -> Dict[str, object]:
    """Persist deployment status updates to DB as log entries."""
    pid = _validate_pipeline_id(pipeline_id)
    now = datetime.now(timezone.utc)
    row = models.DeploymentLog(
        engine_path=str(payload.get("engine_path") or "unknown://engine"),
        model_version=str(payload.get("model_version")) if payload.get("model_version") else None,
        target_stage=str(payload.get("target_stage") or "shadow"),
        deployed_at=now,
        status=str(payload.get("status") or "pending"),
        metrics=dict(payload.get("metrics") or {}),
        rollback_from=str(payload.get("rollback_from")) if payload.get("rollback_from") else None,
        mlflow_run_id=str(payload.get("mlflow_run_id")) if payload.get("mlflow_run_id") else None,
        gate_b_passed=payload.get("gate_b_passed"),
        fps_measured=payload.get("fps_measured"),
        latency_p50_ms=payload.get("latency_p50_ms"),
        latency_p95_ms=payload.get("latency_p95_ms"),
        gpu_memory_gb=payload.get("gpu_memory_gb"),
        correlation_id=pid,
        error_message=str(payload.get("error_message")) if payload.get("error_message") else None,
    )
    session.add(row)
    await session.commit()
    return {"status": "updated", "pipeline_id": pid}
