from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pythonjsonlogger.jsonlogger import JsonFormatter    # type: ignore[import]
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..app.config import AppConfig, get_config
from ..app.db.models import PromotionLog, Video
from ..app.deps import get_db
from ..app.routers import health as health_router
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

logger = logging.getLogger("media_mover")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

VIDEOS_ROOT = Path(os.getenv("MEDIA_VIDEOS_ROOT", "/media/project_data/reachy_emotion/videos"))


@router.post("/api/media/promote")
async def promote(
    request: Request,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
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
    raw_video_id = body.get("video_id")
    video_id = Path(str(raw_video_id)).stem if raw_video_id is not None else Path(str(clip)).stem
    target_split = payload["target"]
    train_label = body.get("label") or payload.get("label")
    train_label = str(train_label).strip().lower() if train_label is not None else None
    if target_split == "train" and train_label not in {"happy", "sad", "neutral"}:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "Train promotion requires label in {happy, sad, neutral}",
                "correlation_id": payload.get("correlation_id", ""),
            },
        )

    video = await db.get(Video, video_id)
    if video is None:
        candidate_file_names = []
        for candidate in (raw_video_id, clip):
            if candidate is None:
                continue
            name = Path(str(candidate)).name
            if name:
                candidate_file_names.append(name)
        for file_name in candidate_file_names:
            stmt = select(Video).where(Video.file_path.endswith(f"/{file_name}"))
            video = (await db.execute(stmt)).scalar_one_or_none()
            if video is not None:
                video_id = str(video.video_id)
                break
    if video is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Video not found: {video_id}",
                "correlation_id": payload.get("correlation_id", ""),
            },
        )

    src = config.videos_root / str(video.file_path)
    dst_name = Path(str(video.file_path)).name
    if target_split == "train":
        dst = config.videos_root / target_split / train_label / dst_name
    else:
        dst = config.videos_root / target_split / dst_name
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
    if dry_run:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "video_id": video_id,
                "src": str(src),
                "dst": str(dst),
                "dry_run": True,
                "adapter_mode": adapter_mode,
            },
        )

    if not src.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "file_not_found",
                "message": f"Source file missing: {src}",
                "correlation_id": payload.get("correlation_id", ""),
            },
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))

    from_split = video.split.value if hasattr(video.split, "value") else str(video.split)
    video.split = target_split
    video.label = train_label if target_split == "train" else None
    video.file_path = str(dst.relative_to(config.videos_root))

    db.add(
        PromotionLog(
            video_id=video.video_id,
            from_split=from_split,
            to_split=target_split,
            intended_label=train_label if target_split == "train" else None,
            actor="gateway_legacy_promote",
            dry_run=False,
            success=True,
            correlation_id=payload.get("correlation_id"),
            extra_data={"adapter_mode": adapter_mode},
        )
    )
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        try:
            if dst.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
        except Exception:
            logger.exception(
                "media_mover_promote_compensation_failed",
                extra={
                    "video_id": video_id,
                    "src": str(src),
                    "dst": str(dst),
                    "correlation_id": payload.get("correlation_id", ""),
                },
            )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Promotion database commit failed after file move; rollback attempted",
                "correlation_id": payload.get("correlation_id", ""),
            },
        ) from exc

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "video_id": video_id,
            "src": str(src),
            "dst": str(dst),
            "dry_run": False,
            "adapter_mode": adapter_mode,
        },
    )


@router.get("/media/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


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
) -> JSONResponse:
    """List videos from the filesystem under /videos/{split}.
    This is a lightweight, read-only implementation to support the web UI.
    """
    if split not in {"temp", "train", "test"}:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": "invalid split"})

    root = VIDEOS_ROOT / split
    if not root.exists() or not root.is_dir():
        return JSONResponse(status_code=200, content={"items": [], "total": 0})

    entries: List[Dict[str, Any]] = []
    try:
        if split == "train":
            candidates = root.rglob("*")
        else:
            candidates = root.iterdir()
        for p in candidates:
            if not p.is_file():
                continue
            try:
                st = p.stat()
                rel = p.relative_to(VIDEOS_ROOT)
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
) -> JSONResponse:
    return await _list_videos_impl(split=split, limit=limit, offset=offset)


@router.get("/api/media/videos/list")
async def list_videos_compat(
    split: str = Query(..., pattern="^(temp|train|test)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    return await _list_videos_impl(split=split, limit=limit, offset=offset)
