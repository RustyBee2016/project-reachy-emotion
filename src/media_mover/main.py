"""Ubuntu 1 — Media Mover API (FastAPI)

Responsible for safe file promotions from /videos/temp → /videos/{train|test}.
This is a stub implementation that only validates input and simulates success.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from pythonjsonlogger.json import JsonFormatter

app = FastAPI(title="Media Mover API", version="0.1.1")

logger = logging.getLogger("media_mover")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

VIDEOS_ROOT = Path("/videos")


@app.post("/api/media/promote")
@app.post("/api/v1/media/promote")
async def promote(request: Request) -> JSONResponse:
    """Stub: validate payload and simulate an atomic move.

    Expected body:
    { "schema_version": "v1", "clip": "clip.mp4", "target": "train|test", "label": "sad", "correlation_id": "..." }
    """
    body: Dict[str, Any] = await request.json()
    required = {"schema_version", "clip", "target", "label", "correlation_id"}
    missing = [k for k in required if k not in body]
    if missing:
        raise HTTPException(status_code=400, detail={
            "schema_version": "v1",
            "error": "validation_error",
            "message": f"Missing fields: {', '.join(missing)}",
            "correlation_id": body.get("correlation_id", ""),
            "fields": missing,
        })
    if body["schema_version"] != "v1":
        raise HTTPException(status_code=400, detail={
            "schema_version": "v1",
            "error": "validation_error",
            "message": "schema_version must be 'v1'",
            "correlation_id": body.get("correlation_id", ""),
            "fields": ["/schema_version"],
        })
    if body["target"] not in {"train", "test"}:
        raise HTTPException(status_code=400, detail={
            "schema_version": "v1",
            "error": "validation_error",
            "message": "target must be 'train' or 'test'",
            "correlation_id": body.get("correlation_id", ""),
            "fields": ["/target"],
        })

    clip = body["clip"]
    src = VIDEOS_ROOT / "temp" / clip
    dst = VIDEOS_ROOT / body["target"] / clip

    logger.info("media_mover_promote_stub", extra={
        "clip": clip,
        "target": body["target"],
        "label": body["label"],
        "src": str(src),
        "dst": str(dst),
        "correlation_id": body["correlation_id"],
    })
    # TODO: implement atomic move with temp name + fsync; handle conflicts; idempotency
    return JSONResponse(status_code=200, content={"status": "ok", "src": str(src), "dst": str(dst)})

@app.post("/api/promote")
async def promote_alias(request: Request) -> JSONResponse:
    """Compatibility alias for clients calling /api/promote.

    Delegates to the canonical /api/v1/media/promote handler.
    """
    return await promote(request)

@app.get("/api/media")
async def media_base() -> Dict[str, Any]:
    return {"status": "ok", "service": "media-mover", "version": app.version}


@app.get("/health")
async def health() -> str:
    return "ok"
