"""V1 Media API endpoints for listing and accessing video metadata."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..config import AppConfig, get_config
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


def _get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID", "")


@router.get("/list", response_model=ListVideosResponse)
async def list_videos(
    request: Request,
    split: str = Query(..., pattern="^(temp|dataset_all|train|test)$", description="Video split to list"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of videos to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    config: AppConfig = Depends(get_config),
) -> ListVideosResponse:
    """List videos from the specified split.
    
    This endpoint reads from the filesystem and returns video metadata including
    video_id, file_path, size, and modification time.
    
    Args:
        split: Video split (temp, dataset_all, train, test)
        limit: Maximum number of videos to return (1-1000)
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
    if split not in {"temp", "dataset_all", "train", "test"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": f"Invalid split: {split}. Must be one of: temp, dataset_all, train, test"
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

    videos = []
    try:
        for p in root.iterdir():
            if not p.is_file():
                continue
            try:
                st = p.stat()
                rel = p.relative_to(config.videos_root)
                videos.append(
                    VideoMetadata(
                        video_id=p.stem,
                        file_path=str(rel),
                        size_bytes=st.st_size,
                        mtime=st.st_mtime,
                        split=split,
                    )
                )
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

    # Apply offset/limit after collection
    total = len(videos)
    sliced = videos[offset : offset + limit]
    
    data = ListVideosData(
        items=sliced,
        pagination=PaginationMeta.from_params(total=total, limit=limit, offset=offset)
    )
    
    return create_success_response(data, _get_correlation_id(request))


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
    splits = ["temp", "dataset_all", "train", "test"]
    
    for split in splits:
        split_path = config.videos_root / split
        if not split_path.exists():
            continue
            
        for p in split_path.iterdir():
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
