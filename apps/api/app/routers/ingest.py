"""Ingest API endpoints for video pulling and manifest management.

These endpoints support the n8n Ingest Agent (Agent 1) and Promotion Agent (Agent 3).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db.models import ExtractedFrame, Video
from ..deps import get_db

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

logger = logging.getLogger(__name__)
EMOTION_LABELS = {"happy", "sad", "neutral"}
FRAME_NAME_RE = re.compile(r"^(happy|sad|neutral)_.+_f(\d{2})_idx(\d{5})\.jpg$")


def utcnow_naive() -> datetime:
    """Return UTC timestamp as naive datetime for legacy DB timestamp columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================================
# Request/Response Models
# ============================================================================


class PullVideoRequest(BaseModel):
    """Request to pull a video from an external URL."""
    source_url: str = Field(..., description="URL to download video from")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    intended_emotion: Optional[str] = Field(None, description="Expected emotion label (happy/sad)")
    generator: Optional[str] = Field(None, description="Video generator (luma, runway, etc.)")
    prompt: Optional[str] = Field(None, description="Generation prompt used")


class PullVideoResponse(BaseModel):
    """Response from video pull operation."""
    status: str
    video_id: str
    sha256: str
    file_path: str
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    correlation_id: Optional[str] = None
    duplicate: bool = False


class UploadVideoResponse(PullVideoResponse):
    """Response from direct file upload operation."""

    file_name: Optional[str] = None


class RegisterLocalVideoRequest(BaseModel):
    """Register a locally available video (already on disk)."""
    file_path: str = Field(..., description="Path relative to videos root, e.g., temp/luma_123.mp4")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for storage")
    file_name: Optional[str] = Field(None, description="Original file name for reference")


class RegisterLocalVideoResponse(PullVideoResponse):
    """Response from local registration operation."""
    file_name: Optional[str] = None


class RebuildManifestRequest(BaseModel):
    """Request to rebuild dataset manifests."""
    splits: List[str] = Field(default=["train", "test"], description="Splits to rebuild")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class RebuildManifestResponse(BaseModel):
    """Response from manifest rebuild operation."""
    status: str
    dataset_hash: str
    manifests_rebuilt: List[str]
    train_count: int = 0
    test_count: int = 0
    correlation_id: Optional[str] = None


class PrepareRunFramesRequest(BaseModel):
    """Request payload for run-scoped frame extraction."""

    run_id: Optional[str] = Field(
        default=None,
        description="Optional run identifier (run_xxxx). Auto-generated when omitted.",
    )
    train_fraction: float = Field(
        default=0.7,
        gt=0.0,
        le=1.0,
        description="Compatibility field retained for orchestration parity.",
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2**31 - 1,
        description="Optional deterministic seed for frame sampling.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, validate and estimate outputs without writing frames/manifests.",
    )
    face_crop: bool = Field(
        default=False,
        description="If true, use OpenCV DNN face detection and save cropped face frames only.",
    )
    face_target_size: int = Field(
        default=224,
        ge=64,
        le=1024,
        description="Face crop output size (square).",
    )
    face_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum OpenCV DNN face detection confidence.",
    )
    split_run: bool = Field(
        default=False,
        description=(
            "DEPRECATED: If true, move extracted frames into train_ds_<run_id>/valid_ds_<run_id> "
            "subdirectories after extraction (90/10 split). This is a legacy fallback - "
            "use dedicated AffectNet validation datasets instead via /api/v1/datasets/validation/create."
        ),
    )
    split_train_ratio: float = Field(
        default=0.9,
        gt=0.0,
        lt=1.0,
        description="Train ratio used when split_run=true (e.g., 0.9 => 90/10 train/valid).",
    )
    strip_valid_labels: bool = Field(
        default=True,
        description=(
            "When split_run=true, remove label prefixes from valid_ds filenames "
            "while preserving labels in manifests."
        ),
    )
    persist_valid_metadata: bool = Field(
        default=False,
        description=(
            "If true, persist valid_ds metadata rows into extracted_frame when "
            "valid manifests exist for the run."
        ),
    )
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class PrepareRunFramesResponse(BaseModel):
    """Response payload for run-scoped frame extraction."""

    status: str
    run_id: str
    train_count: int
    test_count: int
    videos_processed: int
    frames_per_video: int
    train_manifest_path: str
    test_manifest_path: str
    train_run_root: str
    dataset_hash: str
    seed: int
    dry_run: bool = False
    face_crop: bool = False
    face_target_size: int = 224
    face_confidence: float = 0.6
    split_run_applied: bool = False
    persisted_train_frames: int = 0
    persisted_valid_frames: int = 0
    train_ds_manifest_path: Optional[str] = None
    valid_ds_manifest_path: Optional[str] = None
    correlation_id: Optional[str] = None


class VideoMetadataFFprobe(BaseModel):
    """Video metadata extracted via FFprobe."""
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None


# ============================================================================
# Helper Functions
# ============================================================================


async def download_video(url: str, timeout: float = 120.0) -> bytes:
    """Download video from URL with timeout."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of data."""
    return hashlib.sha256(data).hexdigest()


async def ffprobe_metadata(file_path: Path) -> VideoMetadataFFprobe:
    """Extract video metadata using FFprobe.
    
    Returns metadata dict with duration, fps, width, height.
    Falls back gracefully if FFprobe is not available.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        
        if proc.returncode != 0:
            logger.warning(f"FFprobe failed for {file_path}: {stderr.decode()}")
            return VideoMetadataFFprobe()
        
        data = json.loads(stdout.decode())
        
        # Extract format info
        format_info = data.get("format", {})
        duration = float(format_info.get("duration", 0)) if format_info.get("duration") else None
        bitrate = int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None
        
        # Find video stream
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break
        
        if video_stream:
            width = video_stream.get("width")
            height = video_stream.get("height")
            codec = video_stream.get("codec_name")
            
            # Parse FPS from avg_frame_rate (e.g., "30/1" or "30000/1001")
            fps = None
            fps_str = video_stream.get("avg_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                if int(den) > 0:
                    fps = round(int(num) / int(den), 2)
            
            return VideoMetadataFFprobe(
                duration_sec=duration,
                fps=fps,
                width=width,
                height=height,
                codec=codec,
                bitrate=bitrate
            )
        
        return VideoMetadataFFprobe(duration_sec=duration, bitrate=bitrate)
        
    except asyncio.TimeoutError:
        logger.warning(f"FFprobe timed out for {file_path}")
        return VideoMetadataFFprobe()
    except FileNotFoundError:
        logger.warning("FFprobe not found - metadata extraction skipped")
        return VideoMetadataFFprobe()
    except Exception as e:
        logger.warning(f"FFprobe error for {file_path}: {e}")
        return VideoMetadataFFprobe()


async def generate_thumbnail(
    video_path: Path,
    thumb_path: Path,
    timestamp: float = 1.0
) -> bool:
    """Generate thumbnail from video using FFmpeg.
    
    Args:
        video_path: Path to source video
        thumb_path: Path to output thumbnail
        timestamp: Time in seconds to extract frame from
        
    Returns:
        True if successful, False otherwise
    """
    try:
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=320:-1",
            str(thumb_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        
        return thumb_path.exists()
        
    except Exception as e:
        logger.warning(f"Thumbnail generation failed for {video_path}: {e}")
        return False


def compute_dataset_hash(videos: List[Dict[str, Any]]) -> str:
    """Compute a deterministic hash of the dataset for versioning.
    
    Args:
        videos: List of video records with video_id, file_path, label
        
    Returns:
        SHA256 hash of the sorted, concatenated video data
    """
    # Sort by video_id for deterministic ordering
    sorted_videos = sorted(videos, key=lambda v: v.get("video_id", ""))
    
    # Concatenate relevant fields
    parts = []
    for v in sorted_videos:
        parts.append(f"{v.get('video_id', '')}|{v.get('file_path', '')}|{v.get('label', '')}")
    
    combined = "\n".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()


def _normalize_relative_path(raw_path: str, videos_root: Path) -> str:
    """Return paths relative to videos root when possible."""
    path = Path(raw_path)
    if path.is_absolute():
        try:
            return str(path.relative_to(videos_root))
        except ValueError:
            return str(path)
    return str(path)


def _frame_indices_from_path(frame_path: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Extract frame order/index and label from canonical frame filenames."""
    match = FRAME_NAME_RE.match(Path(frame_path).name.lower())
    if not match:
        return None, None, None
    label = match.group(1)
    frame_order = int(match.group(2))
    frame_index = int(match.group(3))
    return frame_order, frame_index, label


def _load_manifest_rows(manifest_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not manifest_path.exists():
        return rows
    with open(manifest_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_source_video_lookup(
    *,
    canonical_train_entries: List[Dict[str, Any]],
    videos_root: Path,
) -> Dict[str, str]:
    """Build file-name lookup for source_video paths from canonical run manifest."""
    source_by_name: Dict[str, str] = {}
    for entry in canonical_train_entries:
        src = entry.get("source_video")
        path = entry.get("path")
        if not src or not path:
            continue
        source_rel = _normalize_relative_path(str(src), videos_root)
        name = Path(str(path)).name
        source_by_name[name] = source_rel
        for label in EMOTION_LABELS:
            prefix = f"{label}_"
            if name.startswith(prefix):
                stripped = name[len(prefix):]
                source_by_name.setdefault(stripped, source_rel)
    return source_by_name


async def _persist_run_frame_metadata(
    *,
    db: AsyncSession,
    config: AppConfig,
    run_id: str,
    correlation_id: str,
    idempotency_key: Optional[str],
    split_run_applied: bool,
    persist_valid_metadata: bool,
) -> tuple[int, int]:
    """Persist extracted frame metadata for train and optional valid manifests."""
    canonical_train_manifest = config.manifests_path / f"{run_id}_train.jsonl"
    canonical_train_entries = _load_manifest_rows(canonical_train_manifest)
    if not canonical_train_entries:
        raise ValueError(f"Train manifest not found for run: {run_id}")

    source_by_name = _build_source_video_lookup(
        canonical_train_entries=canonical_train_entries,
        videos_root=config.videos_root,
    )

    selected_train_manifest = (
        config.manifests_path / f"{run_id}_train_ds.jsonl"
        if split_run_applied
        else canonical_train_manifest
    )
    train_entries = _load_manifest_rows(selected_train_manifest)
    if not train_entries and split_run_applied:
        # Fall back to canonical train manifest if split manifest was not created.
        train_entries = canonical_train_entries

    valid_entries: List[Dict[str, Any]] = []
    if persist_valid_metadata:
        valid_labeled_manifest = config.manifests_path / f"{run_id}_valid_ds_labeled.jsonl"
        valid_entries = _load_manifest_rows(valid_labeled_manifest)

    source_paths = set()
    for entry in train_entries + valid_entries:
        if entry.get("source_video"):
            source_paths.add(_normalize_relative_path(str(entry["source_video"]), config.videos_root))
            continue
        mapped = source_by_name.get(Path(str(entry.get("path", ""))).name)
        if mapped:
            source_paths.add(mapped)

    source_video_id_by_path: Dict[str, str] = {}
    if source_paths:
        rows = await db.execute(
            select(Video.video_id, Video.file_path).where(Video.file_path.in_(sorted(source_paths)))
        )
        for video_id, file_path in rows.all():
            if video_id and file_path:
                source_video_id_by_path[str(file_path)] = str(video_id)

    def _rows_from_entries(entries: List[Dict[str, Any]], split: str) -> List[Dict[str, Any]]:
        payload_rows: List[Dict[str, Any]] = []
        for entry in entries:
            raw_frame_path = str(entry.get("path", "")).strip()
            if not raw_frame_path:
                continue
            frame_path = _normalize_relative_path(raw_frame_path, config.videos_root)

            raw_label = str(entry.get("label", "")).strip().lower()
            label = raw_label if raw_label in EMOTION_LABELS else None
            frame_order, frame_index, inferred_label = _frame_indices_from_path(frame_path)
            if label is None and inferred_label in EMOTION_LABELS:
                label = inferred_label

            source_video_rel: Optional[str] = None
            source_video_id: Optional[str] = None
            if entry.get("source_video"):
                source_video_rel = _normalize_relative_path(str(entry["source_video"]), config.videos_root)
            else:
                source_video_rel = source_by_name.get(Path(frame_path).name)
            if source_video_rel:
                source_video_id = source_video_id_by_path.get(source_video_rel)

            row_metadata: Dict[str, Any] = {
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
            }
            for key in (
                "face_bbox",
                "face_confidence",
                "face_detector",
                "face_crop",
                "target_size",
                "source_frame_shape",
            ):
                if key in entry:
                    row_metadata[key] = entry[key]

            payload_rows.append(
                {
                    "run_id": run_id,
                    "split": split,
                    "frame_path": frame_path,
                    "label": label,
                    "source_video_id": source_video_id,
                    "source_video_path": source_video_rel,
                    "frame_order": frame_order,
                    "frame_index": frame_index,
                    "extra_data": row_metadata,
                }
            )
        return payload_rows

    train_rows = _rows_from_entries(train_entries, "train")
    valid_rows = _rows_from_entries(valid_entries, "valid")

    await db.execute(delete(ExtractedFrame).where(ExtractedFrame.run_id == run_id))
    if train_rows:
        await db.execute(insert(ExtractedFrame), train_rows)
    if valid_rows:
        await db.execute(insert(ExtractedFrame), valid_rows)
    await db.commit()
    return len(train_rows), len(valid_rows)


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/pull", response_model=PullVideoResponse)
async def pull_video(
    request: PullVideoRequest,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> PullVideoResponse:
    """Pull video from external URL, compute hash, and register in database.
    
    This endpoint:
    1. Downloads video from source_url
    2. Computes SHA256 checksum
    3. Checks for duplicates
    4. Saves to /videos/temp/
    5. Extracts metadata via FFprobe
    6. Generates thumbnail
    7. Inserts record into database
    
    Supports idempotency via Idempotency-Key header.
    
    Args:
        request: Pull video request with source URL
        config: Application configuration
        db: Database session
        idempotency_key: Optional idempotency key for deduplication
        
    Returns:
        Video metadata including video_id, sha256, and file path
        
    Raises:
        HTTPException: 400 if URL invalid, 409 if duplicate, 500 on internal error
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    
    try:
        # Download video
        logger.info(f"Pulling video from {request.source_url}", extra={
            "correlation_id": correlation_id,
            "source_url": request.source_url
        })
        
        try:
            video_bytes = await download_video(request.source_url)
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "download_failed",
                    "message": f"Failed to download video: HTTP {e.response.status_code}",
                    "correlation_id": correlation_id
                }
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "download_failed",
                    "message": f"Failed to download video: {str(e)}",
                    "correlation_id": correlation_id
                }
            )
        
        # Compute SHA256
        sha256 = compute_sha256(video_bytes)
        size_bytes = len(video_bytes)
        
        # Check for duplicate
        existing = await db.execute(
            select(Video).where(Video.sha256 == sha256, Video.size_bytes == size_bytes)
        )
        existing_video = existing.scalar_one_or_none()
        
        if existing_video:
            logger.info(f"Duplicate video detected: {existing_video.video_id}", extra={
                "correlation_id": correlation_id,
                "sha256": sha256
            })
            return PullVideoResponse(
                status="duplicate",
                video_id=existing_video.video_id,
                sha256=sha256,
                file_path=existing_video.file_path,
                size_bytes=existing_video.size_bytes,
                duration_sec=existing_video.duration_sec,
                fps=existing_video.fps,
                width=existing_video.width,
                height=existing_video.height,
                correlation_id=correlation_id,
                duplicate=True
            )
        
        # Generate video ID and save file
        video_id = str(uuid.uuid4())
        file_name = f"{video_id}.mp4"
        file_path = config.temp_path / file_name
        rel_path = f"temp/{file_name}"
        
        # Ensure temp directory exists
        config.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Write video file
        file_path.write_bytes(video_bytes)
        
        # Extract metadata
        metadata = await ffprobe_metadata(file_path)
        
        # Generate thumbnail
        thumb_path = config.thumbs_path / f"{video_id}.jpg"
        await generate_thumbnail(file_path, thumb_path)
        
        # Create database record
        # NOTE: Explicit timestamps are required for DBs where created_at/updated_at
        # are NOT NULL but server defaults are not present.
        now = utcnow_naive()
        video = Video(
            video_id=video_id,
            file_path=rel_path,
            split="temp",
            label=None,
            sha256=sha256,
            size_bytes=size_bytes,
            duration_sec=metadata.duration_sec,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            created_at=now,
            updated_at=now,
        )
        
        db.add(video)
        await db.commit()
        
        logger.info(f"Video ingested successfully: {video_id}", extra={
            "correlation_id": correlation_id,
            "video_id": video_id,
            "sha256": sha256,
            "size_bytes": size_bytes
        })
        
        return PullVideoResponse(
            status="done",
            video_id=video_id,
            sha256=sha256,
            file_path=rel_path,
            size_bytes=size_bytes,
            duration_sec=metadata.duration_sec,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            correlation_id=correlation_id,
            duplicate=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Video pull failed: {e}", extra={
            "correlation_id": correlation_id
        })
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Video pull failed: {str(e)}",
                "correlation_id": correlation_id
            }
        )


@router.post("/upload", response_model=UploadVideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    for_training: bool = Form(default=False),
    correlation_id: Optional[str] = Form(default=None),
    metadata_json: Optional[str] = Form(default=None),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> UploadVideoResponse:
    """Ingest a multipart-uploaded video into temp split and DB."""
    corr_id = correlation_id or str(uuid.uuid4())

    try:
        video_bytes = await file.read()
        if not video_bytes:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "Uploaded file is empty",
                    "correlation_id": corr_id,
                },
            )

        sha256 = compute_sha256(video_bytes)
        size_bytes = len(video_bytes)

        existing = await db.execute(
            select(Video).where(Video.sha256 == sha256, Video.size_bytes == size_bytes)
        )
        existing_video = existing.scalar_one_or_none()
        if existing_video:
            return UploadVideoResponse(
                status="duplicate",
                video_id=existing_video.video_id,
                sha256=sha256,
                file_path=existing_video.file_path,
                size_bytes=existing_video.size_bytes,
                duration_sec=existing_video.duration_sec,
                fps=existing_video.fps,
                width=existing_video.width,
                height=existing_video.height,
                correlation_id=corr_id,
                duplicate=True,
                file_name=file.filename,
            )

        suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
        video_id = str(uuid.uuid4())
        file_name = f"{video_id}{suffix}"
        file_path = config.temp_path / file_name
        rel_path = f"temp/{file_name}"

        config.temp_path.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(video_bytes)

        parsed_meta: Dict[str, Any] = {}
        if metadata_json:
            try:
                parsed_meta = json.loads(metadata_json)
            except json.JSONDecodeError:
                parsed_meta = {"raw_metadata": metadata_json}

        parsed_meta["for_training"] = bool(for_training)
        if idempotency_key:
            parsed_meta["idempotency_key"] = idempotency_key

        metadata = await ffprobe_metadata(file_path)
        thumb_path = config.thumbs_path / f"{video_id}.jpg"
        await generate_thumbnail(file_path, thumb_path)

        # NOTE: Explicit timestamps are required for DBs where created_at/updated_at
        # are NOT NULL but server defaults are not present.
        now = utcnow_naive()
        video = Video(
            video_id=video_id,
            file_path=rel_path,
            split="temp",
            label=None,
            sha256=sha256,
            size_bytes=size_bytes,
            duration_sec=metadata.duration_sec,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            extra_data=parsed_meta,
            created_at=now,
            updated_at=now,
        )
        db.add(video)
        await db.commit()

        return UploadVideoResponse(
            status="done",
            video_id=video_id,
            sha256=sha256,
            file_path=rel_path,
            size_bytes=size_bytes,
            duration_sec=metadata.duration_sec,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            correlation_id=corr_id,
            duplicate=False,
            file_name=file.filename,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("upload_video_failed", extra={"correlation_id": corr_id})
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Upload failed: {exc}",
                "correlation_id": corr_id,
            },
        ) from exc


@router.post("/register-local", response_model=RegisterLocalVideoResponse)
async def register_local_video(
    request: RegisterLocalVideoRequest,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> RegisterLocalVideoResponse:
    """Register an existing local file under temp/ into the DB.

    This does not move or copy the file; it only records metadata and generates a thumbnail.
    """
    corr_id = request.correlation_id or str(uuid.uuid4())
    raw_path = request.file_path.strip()
    try:
        rel_path = Path(raw_path)
        if rel_path.is_absolute():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "file_path must be relative (e.g., temp/luma_123.mp4)",
                    "correlation_id": corr_id,
                },
            )
        if not rel_path.parts or rel_path.parts[0] != "temp":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": "file_path must start with temp/",
                    "correlation_id": corr_id,
                },
            )

        roots_to_try: list[Path] = [config.videos_root]
        legacy_root = os.getenv("MEDIA_VIDEOS_ROOT")
        if legacy_root:
            legacy_path = Path(legacy_root)
            if legacy_path not in roots_to_try:
                roots_to_try.append(legacy_path)

        resolved_root: Optional[Path] = None
        file_path: Optional[Path] = None
        for root in roots_to_try:
            candidate = root / rel_path
            if candidate.exists() and candidate.is_file():
                resolved_root = root
                file_path = candidate
                break

        if file_path is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"File not found in configured roots: {raw_path}",
                    "correlation_id": corr_id,
                },
            )

        stored_rel_path = str(file_path.relative_to(resolved_root))
        video_bytes = file_path.read_bytes()
        sha256 = compute_sha256(video_bytes)
        size_bytes = len(video_bytes)

        existing = await db.execute(
            select(Video).where(Video.sha256 == sha256, Video.size_bytes == size_bytes)
        )
        existing_video = existing.scalar_one_or_none()
        if existing_video:
            return RegisterLocalVideoResponse(
                status="duplicate",
                video_id=existing_video.video_id,
                sha256=sha256,
                file_path=existing_video.file_path,
                size_bytes=existing_video.size_bytes,
                duration_sec=existing_video.duration_sec,
                fps=existing_video.fps,
                width=existing_video.width,
                height=existing_video.height,
                correlation_id=corr_id,
                duplicate=True,
                file_name=request.file_name,
            )

        parsed_meta = request.metadata or {}
        parsed_meta["for_training"] = False
        if request.file_name:
            parsed_meta["source_file_name"] = request.file_name
        if idempotency_key:
            parsed_meta["idempotency_key"] = idempotency_key

        metadata = await ffprobe_metadata(file_path)
        video_id = str(uuid.uuid4())
        thumb_path = config.thumbs_path / f"{video_id}.jpg"
        await generate_thumbnail(file_path, thumb_path)

        # NOTE: insert explicit UTC timestamps as naive datetimes for legacy DB schema.
        now = utcnow_naive()
        insert_values = {
            "video_id": video_id,
            "file_path": stored_rel_path,
            "split": "temp",
            "label": None,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "duration_sec": metadata.duration_sec,
            "fps": metadata.fps,
            "width": metadata.width,
            "height": metadata.height,
            "extra_data": parsed_meta,
            "created_at": now,
            "updated_at": now,
        }
        try:
            await db.execute(insert(Video).values(**insert_values))
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            # Handle race/duplicate insert by reusing the existing SHA+size row.
            existing = await db.execute(
                select(Video).where(Video.sha256 == sha256, Video.size_bytes == size_bytes)
            )
            existing_video = existing.scalar_one_or_none()
            if existing_video is not None:
                return RegisterLocalVideoResponse(
                    status="duplicate",
                    video_id=existing_video.video_id,
                    sha256=sha256,
                    file_path=existing_video.file_path,
                    size_bytes=existing_video.size_bytes,
                    duration_sec=existing_video.duration_sec,
                    fps=existing_video.fps,
                    width=existing_video.width,
                    height=existing_video.height,
                    correlation_id=corr_id,
                    duplicate=True,
                    file_name=request.file_name,
                )
            raise

        return RegisterLocalVideoResponse(
            status="done",
            video_id=video_id,
            sha256=sha256,
            file_path=stored_rel_path,
            size_bytes=size_bytes,
            duration_sec=metadata.duration_sec,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            correlation_id=corr_id,
            duplicate=False,
            file_name=request.file_name,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("register_local_video_failed", extra={"correlation_id": corr_id})
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Register local failed: {exc}",
                "correlation_id": corr_id,
            },
        ) from exc


@router.post("/manifest/rebuild", response_model=RebuildManifestResponse)
async def rebuild_manifest(
    request: RebuildManifestRequest,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> RebuildManifestResponse:
    """Rebuild JSONL manifests for train/test splits.
    
    This endpoint:
    1. Queries database for videos in specified splits
    2. Generates JSONL manifest files with video paths and labels
    3. Computes dataset hash for versioning
    
    Manifest format (one JSON object per line):
    {"path": "train/abc123.mp4", "label": "happy"}
    
    Args:
        request: Rebuild request with splits to process
        config: Application configuration
        db: Database session
        idempotency_key: Optional idempotency key
        
    Returns:
        Manifest rebuild status with dataset hash and counts
        
    Raises:
        HTTPException: 400 if invalid split, 500 on internal error
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    
    # Validate splits
    valid_splits = {"train", "test"}
    invalid_splits = set(request.splits) - valid_splits
    if invalid_splits:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": f"Invalid splits: {invalid_splits}. Valid: {valid_splits}",
                "correlation_id": correlation_id
            }
        )
    
    try:
        # Ensure manifests directory exists
        config.manifests_path.mkdir(parents=True, exist_ok=True)
        
        manifests_rebuilt = []
        all_videos = []
        train_count = 0
        test_count = 0
        
        for split in request.splits:
            # Query videos for this split
            result = await db.execute(
                select(Video).where(Video.split == split)
            )
            videos = result.scalars().all()
            
            # Build manifest
            manifest_path = config.manifests_path / f"{split}_manifest.jsonl"
            
            with open(manifest_path, "w") as f:
                for video in videos:
                    entry = {
                        "video_id": video.video_id,
                        "path": video.file_path,
                        "label": video.label,
                        "sha256": video.sha256,
                        "size_bytes": video.size_bytes,
                    }
                    f.write(json.dumps(entry) + "\n")
                    all_videos.append(entry)
            
            manifests_rebuilt.append(split)
            
            if split == "train":
                train_count = len(videos)
            elif split == "test":
                test_count = len(videos)
            
            logger.info(f"Manifest rebuilt for {split}: {len(videos)} videos", extra={
                "correlation_id": correlation_id,
                "split": split,
                "count": len(videos)
            })
        
        # Compute dataset hash
        dataset_hash = compute_dataset_hash(all_videos)
        
        logger.info(f"Manifests rebuilt successfully", extra={
            "correlation_id": correlation_id,
            "dataset_hash": dataset_hash,
            "splits": manifests_rebuilt
        })
        
        return RebuildManifestResponse(
            status="ok",
            dataset_hash=dataset_hash,
            manifests_rebuilt=manifests_rebuilt,
            train_count=train_count,
            test_count=test_count,
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Manifest rebuild failed: {e}", extra={
            "correlation_id": correlation_id
        })
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Manifest rebuild failed: {str(e)}",
                "correlation_id": correlation_id
            }
        )


@router.post("/prepare-run-frames", response_model=PrepareRunFramesResponse)
async def prepare_run_frames(
    request: PrepareRunFramesRequest,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> PrepareRunFramesResponse:
    """Extract run-scoped random frames from train videos and generate manifests.

    Expected outputs:
    - train/run/<run_id>/*.jpg (single consolidated training dataset for the run)
    - manifests/<run_id>_train.jsonl and manifests/<run_id>_test.jsonl
    - optional split outputs when split_run=true:
      train/run/<run_id>/train_ds_<run_id>/ and valid_ds_<run_id>/ + split manifests
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    try:
        try:
            from trainer.prepare_dataset import DatasetPreparer
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "dependency_error",
                    "message": (
                        "Frame extraction dependency is missing. "
                        "Install trainer dependencies (opencv-python-headless)."
                    ),
                    "correlation_id": correlation_id,
                },
            ) from exc

        preparer = DatasetPreparer(str(config.videos_root))
        plan_kwargs: Dict[str, Any] = {
            "run_id": request.run_id,
            "train_fraction": request.train_fraction,
            "seed": request.seed,
        }
        prepare_kwargs: Dict[str, Any] = dict(plan_kwargs)
        if request.face_crop:
            plan_kwargs.update(
                {
                    "face_crop": True,
                    "target_size": request.face_target_size,
                    "face_confidence": request.face_confidence,
                }
            )
            prepare_kwargs.update(
                {
                    "face_crop": True,
                    "target_size": request.face_target_size,
                    "face_confidence": request.face_confidence,
                }
            )

        if request.dry_run:
            result = preparer.plan_training_dataset(**plan_kwargs)
            status = "dry_run"
        else:
            result = preparer.prepare_training_dataset(**prepare_kwargs)
            status = "ok"

        run_id = str(result["run_id"])
        train_manifest_path = config.manifests_path / f"{run_id}_train.jsonl"
        test_manifest_path = config.manifests_path / f"{run_id}_test.jsonl"
        train_run_root = config.videos_root / "train" / "run" / run_id
        split_run_applied = False
        train_ds_manifest_path: Optional[Path] = None
        valid_ds_manifest_path: Optional[Path] = None
        persisted_train_frames = 0
        persisted_valid_frames = 0
        if not request.dry_run:
            if request.split_run:
                split_result = preparer.split_run_dataset(
                    run_id=run_id,
                    train_ratio=request.split_train_ratio,
                    seed=request.seed,
                    strip_valid_labels=request.strip_valid_labels,
                )
                split_run_applied = True
                train_ds_manifest_path = Path(str(split_result["train_manifest"]))
                valid_ds_manifest_path = Path(str(split_result["valid_labeled_manifest"]))

            persisted_train_frames, persisted_valid_frames = await _persist_run_frame_metadata(
                db=db,
                config=config,
                run_id=run_id,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                split_run_applied=split_run_applied,
                persist_valid_metadata=bool(request.persist_valid_metadata or split_run_applied),
            )

        logger.info(
            "prepare_run_frames_completed",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "train_count": result["train_count"],
                "videos_processed": result["videos_processed"],
                "frames_per_video": result["frames_per_video"],
                "split_run_applied": split_run_applied,
                "persisted_train_frames": persisted_train_frames,
                "persisted_valid_frames": persisted_valid_frames,
                "idempotency_key": idempotency_key,
                "dry_run": request.dry_run,
            },
        )

        return PrepareRunFramesResponse(
            status=status,
            run_id=run_id,
            train_count=int(result["train_count"]),
            test_count=int(result["test_count"]),
            videos_processed=int(result["videos_processed"]),
            frames_per_video=int(result["frames_per_video"]),
            train_manifest_path=str(train_manifest_path),
            test_manifest_path=str(test_manifest_path),
            train_run_root=str(train_run_root),
            dataset_hash=str(result["dataset_hash"]),
            seed=int(result["seed"]),
            dry_run=bool(request.dry_run),
            face_crop=bool(result.get("face_crop", request.face_crop)),
            face_target_size=int(result.get("target_size", request.face_target_size)),
            face_confidence=float(result.get("face_confidence", request.face_confidence)),
            split_run_applied=split_run_applied,
            persisted_train_frames=persisted_train_frames,
            persisted_valid_frames=persisted_valid_frames,
            train_ds_manifest_path=str(train_ds_manifest_path) if train_ds_manifest_path else None,
            valid_ds_manifest_path=str(valid_ds_manifest_path) if valid_ds_manifest_path else None,
            correlation_id=correlation_id,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(exc),
                "correlation_id": correlation_id,
            },
        ) from exc
    except Exception as exc:
        logger.exception("prepare_run_frames_failed", extra={"correlation_id": correlation_id})
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Frame extraction failed: {exc}",
                "correlation_id": correlation_id,
            },
        ) from exc


@router.get("/status/{video_id}")
async def get_ingest_status(
    video_id: str,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get status of an ingested video.
    
    Used by n8n Ingest Agent for polling after pull request.
    
    Args:
        video_id: Video ID to check
        config: Application configuration
        db: Database session
        
    Returns:
        Video status and metadata
    """
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_found",
                "video_id": video_id
            }
        )
    
    # Check if file exists
    file_path = config.videos_root / video.file_path
    file_exists = file_path.exists()
    
    # Check if thumbnail exists
    thumb_path = config.thumbs_path / f"{video_id}.jpg"
    thumb_exists = thumb_path.exists()
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "done" if file_exists else "pending",
            "video_id": video_id,
            "file_path": video.file_path,
            "split": video.split,
            "sha256": video.sha256,
            "size_bytes": video.size_bytes,
            "duration_sec": video.duration_sec,
            "fps": video.fps,
            "width": video.width,
            "height": video.height,
            "file_exists": file_exists,
            "thumbnail_exists": thumb_exists
        }
    )
