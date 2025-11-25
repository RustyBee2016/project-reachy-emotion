"""Upstream handlers backing the Ubuntu 2 gateway proxy.

These endpoints run on Ubuntu 1 (Media Mover) and expose lightweight APIs
that the gateway forwards requests to. They integrate with the filesystem,
PostgreSQL models, and manifest orchestration to provide real data to the
Reachy UI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db import models
from ..manifest import ManifestBackend
from ..deps import get_db, get_manifest_backend
_default_emotions = {"neutral", "happy", "sad", "angry", "surprise"}
_env_emotions = os.getenv("MEDIA_MOVER_EMOTIONS")
if _env_emotions:
    VALID_EMOTIONS = {item.strip().lower() for item in _env_emotions.split(",") if item.strip()}
    if not VALID_EMOTIONS:
        VALID_EMOTIONS = _default_emotions
else:
    VALID_EMOTIONS = _default_emotions

router = APIRouter(tags=["gateway-upstream"])

_SPLITS = ("temp", "dataset_all", "train", "test")


@router.get("/api/upstream/health")
async def upstream_health() -> dict[str, str]:
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


def _find_video_file(video_identifier: str, config: AppConfig) -> tuple[Path, str]:
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


@router.get("/api/videos/{video_identifier}")
async def get_video_metadata(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
) -> dict[str, object]:
    """Return metadata for the requested video file."""

    video_path, split = _find_video_file(video_identifier, config)
    stat_info = video_path.stat()
    relative_path = video_path.relative_to(config.videos_root)
    payload = VideoMetadataPayload(
        video_id=Path(video_path).stem,
        file_name=video_path.name,
        split=split,
        file_path=str(relative_path),
        size_bytes=stat_info.st_size,
        mtime=stat_info.st_mtime,
    )
    return {"status": "ok", "video": payload.dict()}


@router.get("/api/videos/{video_identifier}/thumb")
async def get_video_thumbnail(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
) -> Response:
    """Return the thumbnail image for a given video."""

    video_stem = Path(video_identifier).stem
    thumb_path = config.thumbs_path / f"{video_stem}.jpg"
    if not thumb_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Thumbnail not found for video: {video_identifier}"},
        )

    return FileResponse(thumb_path, media_type="image/jpeg")


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
) -> dict[str, object]:
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
) -> dict[str, object]:
    """Schedule a manifest rebuild (and optionally reset state)."""

    if payload.reset:
        manifest_backend.reset(reason=payload.reason, run_id=payload.run_id)
    manifest_backend.schedule_rebuild(reason=payload.reason, run_id=payload.run_id)

    return {"status": "accepted", "reason": payload.reason, "run_id": payload.run_id}
