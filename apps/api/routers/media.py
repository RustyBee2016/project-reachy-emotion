from __future__ import annotations

import hashlib
import os
import logging
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List

from fastapi import Depends, APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pythonjsonlogger.jsonlogger import JsonFormatter    # type: ignore[import]
from sqlalchemy import insert, or_, select
from sqlalchemy.exc import SQLAlchemyError

from ..app.config import AppConfig, get_config
from ..app.db.models import PromotionLog, Video
from ..app.deps import get_db
from ..app.fs import FileMover, FileMoverError
from ..app.metrics import (
    PROMOTION_FILESYSTEM_FAILURES,
    PROMOTION_OPERATION_COUNTER,
    PROMOTION_OPERATION_DURATION,
)
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


CANONICAL_PROMOTE_PATH = "/api/v1/media/promote"
LEGACY_PROMOTE_PATH = "/api/media/promote"
LEGACY_PROMOTE_WARNING = f"299 - Deprecated endpoint: use {CANONICAL_PROMOTE_PATH}"


def _promote_json_response(*, content: Dict[str, Any], status_code: int, legacy_path_used: bool) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content)
    if legacy_path_used:
        response.headers["Warning"] = LEGACY_PROMOTE_WARNING
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = f"<{CANONICAL_PROMOTE_PATH}>; rel=\"successor-version\""
    return response


@router.post(LEGACY_PROMOTE_PATH)
@router.post(CANONICAL_PROMOTE_PATH)
async def promote(
    request: Request,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    body: Dict[str, Any] = await request.json()
    legacy_path_used = request.url.path == LEGACY_PROMOTE_PATH

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

    logger.info(
        "media_mover_promote_roots",
        extra={
            "config_videos_root": str(config.videos_root),
            "media_videos_root": str(VIDEOS_ROOT),
            "clip": str(clip),
            "correlation_id": payload.get("correlation_id", ""),
        },
    )

    video = await db.get(Video, video_id)
    if video is None:
        candidate_file_names = []
        for candidate in (raw_video_id, clip):
            if candidate is None:
                continue
            candidate_path = Path(str(candidate))
            name = candidate_path.name
            stem = candidate_path.stem
            suffix = candidate_path.suffix
            if name:
                candidate_file_names.append(name)
            if stem and not suffix:
                candidate_file_names.append(f"{stem}.mp4")
        for file_name in candidate_file_names:
            stmt = select(Video).where(
                or_(
                    Video.file_path.endswith(f"/{file_name}"),
                    Video.file_path.endswith(file_name),
                )
            )
            video = (await db.execute(stmt)).scalar_one_or_none()
            if video is not None:
                video_id = str(video.video_id)
                break
    if video is None:
        candidate_paths: List[Path] = []
        candidate_stems = set()
        roots_to_try = (config.videos_root, VIDEOS_ROOT)
        for candidate in (raw_video_id, clip):
            if candidate is None:
                continue
            candidate_path = Path(str(candidate))
            if candidate_path.name:
                for root in roots_to_try:
                    candidate_paths.append(root / "temp" / candidate_path.name)
            if candidate_path.stem:
                candidate_stems.add(candidate_path.stem)
                if not candidate_path.suffix:
                    for root in roots_to_try:
                        candidate_paths.append(root / "temp" / f"{candidate_path.stem}.mp4")

        existing_path = next((path for path in candidate_paths if path.exists() and path.is_file()), None)
        if existing_path is None and candidate_stems:
            for root in roots_to_try:
                temp_root = root / "temp"
                if not temp_root.exists() or not temp_root.is_dir():
                    continue
                for stem in candidate_stems:
                    _VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
                    wildcard_matches = sorted(
                        [p for p in temp_root.glob(f"{stem}.*")
                         if p.is_file() and p.suffix.lower() in _VIDEO_EXTENSIONS],
                        key=lambda p: str(p),
                    )
                    if wildcard_matches:
                        existing_path = wildcard_matches[0]
                        break
                    bare_match = temp_root / stem
                    if bare_match.exists() and bare_match.is_file():
                        existing_path = bare_match
                        break
                if existing_path is not None:
                    break
        if existing_path is not None:
            stat = existing_path.stat()
            digest = hashlib.sha256()
            with existing_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            logger.warning(
                "media_mover_promote_auto_register",
                extra={
                    "file_path": str(existing_path),
                    "correlation_id": payload.get("correlation_id", ""),
                    "message": "Auto-registering file found on disk; bypasses ingest agent metadata extraction",
                },
            )
            video_root = config.videos_root if str(existing_path).startswith(str(config.videos_root)) else VIDEOS_ROOT
            now = datetime.now(timezone.utc)
            new_video_id = str(uuid.uuid4())
            insert_values = {
                "video_id": new_video_id,
                "file_path": str(existing_path.relative_to(video_root)),
                "split": "temp",
                "label": None,
                "size_bytes": stat.st_size,
                "sha256": digest.hexdigest(),
                "created_at": now,
                "updated_at": now,
            }
            try:
                result = await db.execute(
                    insert(Video).values(**insert_values).returning(Video.video_id)
                )
                video_id = str(result.scalar_one())
                video = await db.get(Video, video_id)
                logger.info(
                    "media_mover_promote_registered_missing_video",
                    extra={
                        "video_id": video_id,
                        "file_path": insert_values["file_path"],
                        "correlation_id": payload.get("correlation_id", ""),
                    },
                )
            except SQLAlchemyError:
                await db.rollback()
                existing_stmt = select(Video).where(
                    Video.sha256 == digest.hexdigest(),
                    Video.size_bytes == stat.st_size,
                )
                video = (await db.execute(existing_stmt)).scalar_one_or_none()
                if video is not None:
                    video_id = str(video.video_id)
                    logger.info(
                        "media_mover_promote_reused_existing_video",
                        extra={
                            "video_id": video_id,
                            "file_path": video.file_path,
                            "correlation_id": payload.get("correlation_id", ""),
                        },
                    )
                else:
                    raise
    if video is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Video not found: {video_id}",
                "correlation_id": payload.get("correlation_id", ""),
            },
        )

    # --- Idempotency check (FIX #4) ---
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        existing_log = (await db.execute(
            select(PromotionLog).where(PromotionLog.idempotency_key == idempotency_key)
        )).scalar_one_or_none()
        if existing_log is not None:
            cached_video = await db.get(Video, existing_log.video_id)
            cached_dst = str(config.videos_root / cached_video.file_path) if cached_video else ""
            logger.info(
                "media_mover_promote_idempotent_replay",
                extra={
                    "idempotency_key": idempotency_key,
                    "video_id": existing_log.video_id,
                    "correlation_id": payload.get("correlation_id", ""),
                },
            )
            return _promote_json_response(
                status_code=200,
                legacy_path_used=legacy_path_used,
                content={
                    "status": "ok",
                    "video_id": existing_log.video_id,
                    "dst": cached_dst,
                    "dry_run": False,
                    "adapter_mode": adapter_mode,
                    "idempotent_replay": True,
                },
            )

    src = config.videos_root / str(video.file_path)
    dst_name = Path(str(video.file_path)).name
    if target_split == "train":
        if train_label is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "Train promotion requires label in {happy, sad, neutral}",
                    "correlation_id": payload.get("correlation_id", ""),
                },
            )
        dst = config.videos_root / target_split / train_label / dst_name
    else:
        dst = config.videos_root / target_split / dst_name
    dry_run = bool(payload.get("dry_run", body.get("dry_run", False)))

    logger.info(
        "media_mover_promote_request",
        extra={
            "clip": clip,
            "target": payload["target"],
            "label": payload["label"],
            "src": str(src),
            "dst": str(dst),
            "correlation_id": payload["correlation_id"],
            "dry_run": dry_run,
            "adapter_mode": adapter_mode,
            "legacy_path_used": legacy_path_used,
        },
    )
    if dry_run:
        return _promote_json_response(
            status_code=200,
            legacy_path_used=legacy_path_used,
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

    # --- Atomic file move via FileMover (FIX #10) with Prometheus metrics ---
    # DESIGN NOTE (FIX #3): The file is moved *before* the DB commit. If the
    # process crashes between the move and the commit, the filesystem and
    # database will be out of sync. This is an accepted trade-off: the
    # Reconciler Agent (Agent 4) detects and repairs such drift during its
    # scheduled reconciliation runs.  The structured "promote_pending" /
    # "promote_committed" log pair below enables the reconciler to identify
    # incomplete promotions by searching for "pending" entries without a
    # matching "committed" entry.
    logger.info(
        "media_mover_promote_pending",
        extra={
            "video_id": video_id,
            "from_split": str(getattr(video.split, "value", video.split)),
            "to_split": target_split,
            "label": train_label,
            "correlation_id": payload.get("correlation_id", ""),
        },
    )
    file_mover = FileMover(config.videos_root)
    transition = None
    promote_start = perf_counter()
    try:
        if target_split == "train" and train_label:
            transition = file_mover.stage_to_train(
                video_id=video_id,
                file_path=str(video.file_path),
                label=train_label,
            )
        else:
            # For test split, use direct move (FileMover.stage_to_train is train-specific)
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            transition = None  # no FileMover transition to rollback for test
        PROMOTION_OPERATION_COUNTER.labels(action="promote", outcome="success").inc()
    except FileMoverError as exc:
        PROMOTION_OPERATION_COUNTER.labels(action="promote", outcome="error").inc()
        PROMOTION_FILESYSTEM_FAILURES.labels(action="promote").inc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "filesystem_error",
                "message": str(exc),
                "correlation_id": payload.get("correlation_id", ""),
            },
        ) from exc
    except OSError as exc:
        PROMOTION_OPERATION_COUNTER.labels(action="promote", outcome="error").inc()
        PROMOTION_FILESYSTEM_FAILURES.labels(action="promote").inc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "filesystem_error",
                "message": f"File move failed: {exc}",
                "correlation_id": payload.get("correlation_id", ""),
            },
        ) from exc
    finally:
        PROMOTION_OPERATION_DURATION.labels(action="promote").observe(perf_counter() - promote_start)

    # Compute actual destination from transition or manual move
    if transition is not None:
        dst = config.videos_root / transition.destination

    from_split = str(getattr(video.split, "value", video.split))
    video.split = target_split
    video.label = train_label if target_split == "train" else None
    video.file_path = str(dst.relative_to(config.videos_root))

    db.add(
        PromotionLog(
            video_id=video.video_id,
            from_split=from_split,
            to_split=target_split,
            intended_label=train_label if target_split == "train" else None,
            actor="media_mover_promote",
            dry_run=False,
            success=True,
            idempotency_key=idempotency_key,
            correlation_id=payload.get("correlation_id"),
            extra_data={"adapter_mode": adapter_mode},
        )
    )
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        # Compensating rollback: reverse the file move
        try:
            if transition is not None:
                file_mover.rollback([transition])
            elif dst.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                os.replace(dst, src)
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

    logger.info(
        "media_mover_promote_committed",
        extra={
            "video_id": video_id,
            "from_split": from_split,
            "to_split": target_split,
            "label": train_label,
            "dst": str(dst),
            "correlation_id": payload.get("correlation_id", ""),
        },
    )

    return _promote_json_response(
        status_code=200,
        legacy_path_used=legacy_path_used,
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
