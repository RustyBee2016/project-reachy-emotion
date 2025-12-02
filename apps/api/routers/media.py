from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Query, Header
from fastapi.responses import JSONResponse, PlainTextResponse
from pythonjsonlogger.jsonlogger import JsonFormatter    # type: ignore[import]

from app.config import AppConfig, get_config
from app.routers import health as health_router

router = APIRouter()

# In-memory job store for pull operations (production would use Redis/DB)
_pull_jobs: Dict[str, Dict[str, Any]] = {}

logger = logging.getLogger("media_mover")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


@router.post("/api/media/promote")
async def promote(request: Request, config: AppConfig = Depends(get_config)) -> JSONResponse:
    body: Dict[str, Any] = await request.json()

    payload = body
    adapter_mode = "legacy"
    if "schema_version" not in body or "clip" not in body:
        required_new = {"video_id", "dest_split"}
        missing_new = [k for k in required_new if k not in body]
        if missing_new:
            raise HTTPException(
                status_code=400,
                detail={
                    "schema_version": "v1",
                    "error": "validation_error",
                    "message": f"Missing fields: {', '.join(missing_new)}",
                    "correlation_id": body.get("correlation_id", ""),
                    "fields": missing_new,
                },
            )
        adapter_mode = "adapter"
        payload = {
            "schema_version": "v1",
            "clip": str(body["video_id"]),
            "target": body["dest_split"],
            "label": body.get("label", ""),
            "correlation_id": body.get("correlation_id", ""),
            "dry_run": bool(body.get("dry_run", False)),
        }

    required = {"schema_version", "clip", "target", "label", "correlation_id"}
    missing = [k for k in required if k not in payload]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "schema_version": "v1",
                "error": "validation_error",
                "message": f"Missing fields: {', '.join(missing)}",
                "correlation_id": payload.get("correlation_id", ""),
                "fields": missing,
            },
        )
    if payload["schema_version"] != "v1":
        raise HTTPException(
            status_code=400,
            detail={
                "schema_version": "v1",
                "error": "validation_error",
                "message": "schema_version must be 'v1'",
                "correlation_id": payload.get("correlation_id", ""),
                "fields": ["/schema_version"],
            },
        )
    if payload["target"] not in {"train", "test"}:
        raise HTTPException(
            status_code=400,
            detail={
                "schema_version": "v1",
                "error": "validation_error",
                "message": "target must be 'train' or 'test'",
                "correlation_id": payload.get("correlation_id", ""),
                "fields": ["/target"],
            },
        )

    clip = payload["clip"]
    src = config.videos_root / "temp" / clip
    dst = config.videos_root / payload["target"] / clip
    dry_run = bool(payload.get("dry_run", body.get("dry_run", False)))

    logger.info(
        "media_mover_promote_stub",
        extra={
            "clip": clip,
            "target": payload["target"],
            "label": payload["label"],
            "src": str(src),
            "dst": str(dst),
            "correlation_id": payload["correlation_id"],
            "dry_run": dry_run,
            "adapter_mode": adapter_mode,
        },
    )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "src": str(src),
            "dst": str(dst),
            "dry_run": dry_run,
            "adapter_mode": adapter_mode,
        },
    )


@router.get("/media/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@router.get("/api/media/health")
async def api_media_health(
    request: Request,
    config: AppConfig = Depends(get_config)
):
    """Legacy health endpoint that mirrors /api/v1/health."""
    return await health_router.health_check(request, config)


@router.get("/api/media")
async def api_media_root() -> JSONResponse:
    """Service status endpoint for Media Mover base path.
    Returns minimal JSON to allow clients to verify availability.
    """
    return JSONResponse(status_code=200, content={"status": "ok", "service": "media-mover"})


async def _list_videos_impl(
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config: AppConfig = Depends(get_config),
) -> JSONResponse:
    """List videos from the filesystem under /videos/{split}.
    This is a lightweight, read-only implementation to support the web UI.
    """
    if split not in {"temp", "train", "test"}:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": "invalid split"})

    root = config.videos_root / split
    if not root.exists() or not root.is_dir():
        return JSONResponse(status_code=200, content={"items": [], "total": 0})

    entries: List[Dict[str, Any]] = []
    try:
        for p in root.iterdir():
            if not p.is_file():
                continue
            try:
                st = p.stat()
                rel = p.relative_to(config.videos_root)
                entries.append(
                    {
                        "video_id": p.stem,
                        "file_path": str(rel),
                        "size_bytes": st.st_size,
                        "mtime": st.st_mtime,
                        "split": split,
                    }
                )
            except Exception:
                # Skip unreadable entries but continue listing
                continue
    except Exception:
        logger.exception("list_videos_scan_failed", extra={"split": split})
        raise HTTPException(status_code=500, detail={"error": "internal_error", "message": "scan failed"})

    # Apply offset/limit after collection to keep logic simple; can optimize later
    total = len(entries)
    sliced = entries[offset : offset + limit]
    return JSONResponse(status_code=200, content={"items": sliced, "total": total, "limit": limit, "offset": offset})


@router.get("/api/videos/list")
async def list_videos(
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config: AppConfig = Depends(get_config),
) -> JSONResponse:
    return await _list_videos_impl(split=split, limit=limit, offset=offset, config=config)


@router.get("/api/media/videos/list")
async def list_videos_compat(
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config: AppConfig = Depends(get_config),
) -> JSONResponse:
    return await _list_videos_impl(split=split, limit=limit, offset=offset, config=config)


# ============================================================================
# Media Pull Endpoints (for n8n Ingest Agent)
# ============================================================================

async def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


async def _run_ffprobe(file_path: Path) -> Dict[str, Any]:
    """Extract video metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("ffprobe_failed", extra={"file": str(file_path), "stderr": result.stderr})
            return {}
        
        data = json.loads(result.stdout)
        
        # Extract video stream info
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )
        
        # Parse frame rate (e.g., "30/1" -> 30.0)
        fps = 0.0
        if "r_frame_rate" in video_stream:
            try:
                num, den = video_stream["r_frame_rate"].split("/")
                fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                fps = 0.0
        
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "fps": round(fps, 2),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "codec": video_stream.get("codec_name", "unknown"),
            "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
        }
    except subprocess.TimeoutExpired:
        logger.error("ffprobe_timeout", extra={"file": str(file_path)})
        return {}
    except Exception as e:
        logger.exception("ffprobe_error", extra={"file": str(file_path), "error": str(e)})
        return {}


async def _generate_thumbnail(video_path: Path, thumb_path: Path) -> bool:
    """Generate a thumbnail from the video using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", str(video_path),
            "-ss", "00:00:01",  # Seek to 1 second
            "-vframes", "1",  # Extract 1 frame
            "-vf", "scale=320:-1",  # Scale to 320px width
            str(thumb_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("thumbnail_failed", extra={"video": str(video_path), "stderr": result.stderr})
            return False
        return thumb_path.exists()
    except subprocess.TimeoutExpired:
        logger.error("thumbnail_timeout", extra={"video": str(video_path)})
        return False
    except Exception as e:
        logger.exception("thumbnail_error", extra={"video": str(video_path), "error": str(e)})
        return False


async def _download_video(source_url: str, dest_path: Path) -> bool:
    """Download video from URL to destination path."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        return dest_path.exists()
    except Exception as e:
        logger.exception("download_error", extra={"url": source_url, "error": str(e)})
        return False


async def _process_pull_job(
    job_id: str,
    source_url: str,
    dest_split: str,
    label: Optional[str],
    compute_thumb: bool,
    run_ffprobe: bool,
    config: AppConfig,
):
    """Background task to process a media pull job."""
    try:
        _pull_jobs[job_id]["status"] = "downloading"
        _pull_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Generate video ID and paths
        video_id = str(uuid.uuid4())
        video_filename = f"{video_id}.mp4"
        dest_dir = config.videos_root / dest_split
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / video_filename
        
        # Download the video
        logger.info("pull_downloading", extra={"job_id": job_id, "url": source_url})
        success = await _download_video(source_url, dest_path)
        if not success:
            _pull_jobs[job_id]["status"] = "failed"
            _pull_jobs[job_id]["error"] = "Download failed"
            return
        
        _pull_jobs[job_id]["status"] = "processing"
        _pull_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Compute SHA256
        sha256 = await _compute_sha256(dest_path)
        
        # Get file size
        size_bytes = dest_path.stat().st_size
        
        # Run ffprobe if requested
        ffprobe_data = {}
        if run_ffprobe:
            ffprobe_data = await _run_ffprobe(dest_path)
        
        # Generate thumbnail if requested
        thumb_path = None
        if compute_thumb:
            thumbs_dir = config.thumbs_path
            thumbs_dir.mkdir(parents=True, exist_ok=True)
            thumb_file = thumbs_dir / f"{video_id}.jpg"
            if await _generate_thumbnail(dest_path, thumb_file):
                thumb_path = str(thumb_file.relative_to(config.videos_root))
        
        # Update job with results
        _pull_jobs[job_id].update({
            "status": "done",
            "video_id": video_id,
            "file_path": f"{dest_split}/{video_filename}",
            "sha256": sha256,
            "size_bytes": size_bytes,
            "ffprobe": ffprobe_data,
            "thumb_path": thumb_path,
            "label": label,
            "updated_at": datetime.utcnow().isoformat(),
        })
        
        logger.info("pull_completed", extra={
            "job_id": job_id,
            "video_id": video_id,
            "sha256": sha256,
            "size_bytes": size_bytes,
        })
        
    except Exception as e:
        logger.exception("pull_job_error", extra={"job_id": job_id, "error": str(e)})
        _pull_jobs[job_id]["status"] = "failed"
        _pull_jobs[job_id]["error"] = str(e)


@router.post("/api/media/pull")
async def media_pull(
    request: Request,
    background_tasks: BackgroundTasks,
    config: AppConfig = Depends(get_config),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
) -> JSONResponse:
    """
    Pull a video from a remote URL into local storage.
    
    This endpoint initiates an async download job and returns immediately.
    Use the status_url to poll for completion.
    
    Required body parameters:
    - source_url: URL to download the video from
    
    Optional body parameters:
    - label: Emotion label (happy, sad, etc.)
    - dest_split: Destination split (temp, train, test) - default: temp
    - compute_thumb: Generate thumbnail (default: true)
    - ffprobe: Extract video metadata (default: true)
    - correlation_id: Tracking ID
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON body"})
    
    source_url = body.get("source_url")
    if not source_url:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": "source_url is required"}
        )
    
    # Check idempotency - return existing job if same key
    if idempotency_key:
        for job_id, job in _pull_jobs.items():
            if job.get("idempotency_key") == idempotency_key:
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": job["status"],
                        "job_id": job_id,
                        "status_url": f"/api/media/pull/status/{job_id}",
                        "idempotent": True,
                    }
                )
    
    # Create new job
    job_id = str(uuid.uuid4())
    label = body.get("label")
    dest_split = body.get("dest_split", "temp")
    compute_thumb = body.get("compute_thumb", True)
    run_ffprobe = body.get("ffprobe", True)
    
    if dest_split not in {"temp", "train", "test"}:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": "dest_split must be temp, train, or test"}
        )
    
    # Initialize job record
    _pull_jobs[job_id] = {
        "status": "pending",
        "source_url": source_url,
        "label": label,
        "dest_split": dest_split,
        "correlation_id": correlation_id or body.get("correlation_id"),
        "idempotency_key": idempotency_key,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    # Start background processing
    background_tasks.add_task(
        _process_pull_job,
        job_id,
        source_url,
        dest_split,
        label,
        compute_thumb,
        run_ffprobe,
        config,
    )
    
    logger.info("pull_job_created", extra={
        "job_id": job_id,
        "source_url": source_url,
        "correlation_id": correlation_id,
    })
    
    return JSONResponse(
        status_code=202,
        content={
            "status": "pending",
            "job_id": job_id,
            "status_url": f"/api/media/pull/status/{job_id}",
        }
    )


@router.get("/api/media/pull/status/{job_id}")
async def media_pull_status(job_id: str) -> JSONResponse:
    """
    Get the status of a media pull job.
    
    Returns the current status and, when complete, the video metadata.
    """
    job = _pull_jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Job {job_id} not found"}
        )
    
    # Return full job data
    return JSONResponse(status_code=200, content=job)
