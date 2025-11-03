from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pythonjsonlogger.json import JsonFormatter

router = APIRouter()

logger = logging.getLogger("media_mover")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

VIDEOS_ROOT = Path(os.getenv("MEDIA_VIDEOS_ROOT", "/media/project_data/reachy_emotion/videos"))


@router.post("/api/media/promote")
async def promote(request: Request) -> JSONResponse:
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
    src = VIDEOS_ROOT / "temp" / clip
    dst = VIDEOS_ROOT / payload["target"] / clip
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
        for p in root.iterdir():
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
