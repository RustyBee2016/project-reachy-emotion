"""V1 Media API endpoints for listing and accessing video metadata."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db.models import ExtractedFrame, Video
from ..deps import get_db
from ...routers import media as legacy_media_router
from ..schemas import (
    ListVideosData,
    ListVideosResponse,
    PaginationMeta,
    ThumbnailData,
    ThumbnailResponse,
    VideoMetadata,
    VideoMetadataResponse,
    create_single_error_response,
    create_success_response,
)

router = APIRouter(prefix="/api/v1/media", tags=["media"])

logger = logging.getLogger(__name__)
EMOTION_LABELS = {"happy", "sad", "neutral"}
FRAME_LABEL_RE = re.compile(r"^(happy|sad|neutral)_")


def _get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID", "")


def _infer_label_from_path(split: str, rel_path: Path) -> Optional[str]:
    """Infer labels from train directory names and frame filename prefixes."""
    if split != "train":
        return None

    parts = rel_path.parts
    if len(parts) >= 3 and parts[0] == "train" and parts[1] in EMOTION_LABELS:
        return parts[1]

    match = FRAME_LABEL_RE.match(rel_path.name.lower())
    if match:
        return match.group(1)

    return None


async def _load_label_maps(
    db: AsyncSession,
    *,
    file_paths: list[str],
) -> tuple[Dict[str, str], Dict[str, str]]:
    """Load labels from video and extracted_frame tables using relative file paths."""
    if not file_paths:
        return {}, {}

    video_labels: Dict[str, str] = {}
    frame_labels: Dict[str, str] = {}

    try:
        video_rows = await db.execute(
            select(Video.file_path, Video.label).where(Video.file_path.in_(file_paths))
        )
        for file_path, label in video_rows.all():
            if file_path and label:
                video_labels[str(file_path)] = str(label)
    except Exception:
        # Keep media listing available even if DB session is unavailable/misaligned.
        logger.warning("video table unavailable while resolving labels")

    try:
        frame_rows = await db.execute(
            select(ExtractedFrame.frame_path, ExtractedFrame.label).where(
                ExtractedFrame.frame_path.in_(file_paths)
            )
        )
        for frame_path, label in frame_rows.all():
            if frame_path and label:
                frame_labels[str(frame_path)] = str(label)
    except Exception:
        # Backward-compatible fallback for environments pending the extracted_frame migration.
        logger.warning("extracted_frame table unavailable while resolving labels")

    return video_labels, frame_labels


@router.get("/list", response_model=ListVideosResponse)
async def list_videos(
    request: Request,
    split: str = Query(..., pattern="^(temp|train|test|purged)$", description="Video split to list"),
    limit: int = Query(10, ge=1, le=10, description="Maximum number of videos to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
) -> ListVideosResponse:
    """List videos from the specified split.
    
    This endpoint reads from the filesystem and returns video metadata including
    video_id, file_path, size, and modification time.
    
    Args:
        split: Video split (temp, train, test, purged)
        limit: Maximum number of videos to return (1-10)
        offset: Pagination offset for retrieving subsequent pages
        config: Application configuration (injected)
        
    Returns:
        JSONResponse with:
            - items: List of video metadata dictionaries
            - total: Total number of videos in the split
            - limit: Requested limit
            - offset: Requested offset
            
    Raises:
        HTTPException: 400 if split is invalid, 500 if filesystem scan fails
    """
    if split not in {"temp", "train", "test", "purged"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": f"Invalid split: {split}. Must be one of: temp, train, test, purged"
            }
        )

    root = config.videos_root / split
    if not root.exists() or not root.is_dir():
        # Return empty list with pagination
        data = ListVideosData(
            items=[],
            pagination=PaginationMeta.from_params(total=0, limit=limit, offset=offset)
        )
        return create_success_response(data, _get_correlation_id(request))

    files = []
    try:
        if split == "train":
            # Only scan label subdirectories (happy/sad/neutral), not run/ or other dirs
            label_dirs = [root / lbl for lbl in ("happy", "sad", "neutral") if (root / lbl).is_dir()]
            iterator = (f for d in label_dirs for f in d.iterdir())
        else:
            iterator = root.iterdir()
        for p in iterator:
            if not p.is_file():
                continue
            try:
                st = p.stat()
                rel = p.relative_to(config.videos_root)
                files.append((p, st, rel))
            except Exception as e:
                # Skip unreadable entries but log the error
                logger.warning(f"Failed to read video metadata: {p}", exc_info=e)
                continue
    except Exception as e:
        logger.exception("list_videos_scan_failed", extra={"split": split})
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to scan video directory"
            }
        ) from e

    rel_file_paths = [str(rel) for _, _, rel in files]
    video_labels, frame_labels = await _load_label_maps(db, file_paths=rel_file_paths)

    videos = []
    for p, st, rel in files:
        rel_str = str(rel)
        label = frame_labels.get(rel_str) or video_labels.get(rel_str) or _infer_label_from_path(split, rel)
        if label not in EMOTION_LABELS:
            label = None
        videos.append(
            VideoMetadata(
                video_id=p.stem,
                file_path=rel_str,
                size_bytes=st.st_size,
                mtime=st.st_mtime,
                split=split,
                label=label,
            )
        )

    total = len(videos)
    sliced = videos[offset : offset + limit]
    
    data = ListVideosData(
        items=sliced,
        pagination=PaginationMeta.from_params(total=total, limit=limit, offset=offset)
    )
    
    return create_success_response(data, _get_correlation_id(request))


@router.post("/promote")
async def promote_video(
    request: Request,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
):
    """Canonical direct promotion endpoint.

    Delegates to the existing promotion implementation to preserve current
    filesystem/database behavior while clients migrate off legacy paths.
    """
    return await legacy_media_router.promote(request=request, config=config, db=db)


@router.get("/{video_id}", response_model=VideoMetadataResponse)
async def get_video_metadata(
    request: Request,
    video_id: str,
    config: AppConfig = Depends(get_config),
) -> VideoMetadataResponse:
    """Get metadata for a specific video.
    
    Searches across all splits to find the video and returns its metadata.
    
    Args:
        request: FastAPI request object
        video_id: Video ID (filename without extension)
        config: Application configuration (injected)
        
    Returns:
        Video metadata response
        
    Raises:
        HTTPException: 404 if video not found
    """
    # Search across all splits
    splits = ["temp", "train", "test", "purged"]
    
    for split in splits:
        split_path = config.videos_root / split
        if not split_path.exists():
            continue

        iterator = split_path.rglob("*") if split == "train" else split_path.iterdir()
        for p in iterator:
            if p.stem == video_id and p.is_file():
                try:
                    st = p.stat()
                    rel = p.relative_to(config.videos_root)
                    metadata = VideoMetadata(
                        video_id=video_id,
                        file_path=str(rel),
                        size_bytes=st.st_size,
                        mtime=st.st_mtime,
                        split=split,
                    )
                    return create_success_response(metadata, _get_correlation_id(request))
                except Exception as e:
                    logger.error(f"Failed to read video metadata: {p}", exc_info=e)
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "internal_error",
                            "message": "Failed to read video metadata"
                        }
                    ) from e
    
    # Video not found in any split
    raise HTTPException(
        status_code=404,
        detail={
            "error": "not_found",
            "message": f"Video not found: {video_id}"
        }
    )


@router.get("/{video_id}/thumb", response_model=ThumbnailResponse)
async def get_video_thumbnail(
    request: Request,
    video_id: str,
    config: AppConfig = Depends(get_config),
) -> ThumbnailResponse:
    """Get thumbnail URL for a specific video.
    
    Returns a URL to the thumbnail served by Nginx.
    
    Args:
        request: FastAPI request object
        video_id: Video ID (filename without extension)
        config: Application configuration (injected)
        
    Returns:
        Thumbnail URL response
    """
    thumb_path = config.thumbs_path / f"{video_id}.jpg"
    
    # Check if thumbnail exists
    if not thumb_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Thumbnail not found for video: {video_id}"
            }
        )
    
    # Return URL to thumbnail (served by Nginx)
    thumb_url = f"{config.nginx_base_url}/thumbs/{video_id}.jpg"
    
    thumbnail_data = ThumbnailData(
        video_id=video_id,
        thumbnail_url=thumb_url
    )
    
    return create_success_response(thumbnail_data, _get_correlation_id(request))
