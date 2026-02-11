from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.api.app.metrics_registry import get_registry
from jsonschema import Draft202012Validator
from pythonjsonlogger.json import JsonFormatter

# Ubuntu 1 Media Mover base URL
MEDIA_MOVER_URL = os.getenv("GATEWAY_MEDIA_MOVER_URL", "http://10.0.4.130:8083")

# Proxy client (reuse for efficiency)
client = httpx.AsyncClient()

# Embedded JSON Schemas (v1)
EMOTION_EVENT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "schema_version",
        "device_id",
        "ts",
        "emotion",
        "confidence",
        "inference_ms",
        "window",
        "meta",
        "correlation_id",
    ],
    "properties": {
        "schema_version": {"const": "v1"},
        "device_id": {"type": "string"},
        "ts": {"type": "string"},
        "emotion": {"type": "string", "enum": [
            "happy", "sad", "angry", "neutral", "surprise", "fearful"
        ]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "inference_ms": {"type": "number", "minimum": 0},
        "window": {
            "type": "object",
            "required": ["fps", "size_s", "hop_s"],
            "properties": {
                "fps": {"type": "number", "minimum": 1},
                "size_s": {"type": "number", "minimum": 0},
                "hop_s": {"type": "number", "minimum": 0},
            },
            "additionalProperties": True,
        },
        "meta": {"type": "object"},
        "correlation_id": {"type": "string"},
    },
    "additionalProperties": True,
}

PROMOTION_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "clip", "target", "label", "correlation_id"],
    "properties": {
        "schema_version": {"const": "v1"},
        "clip": {"type": "string"},
        "target": {"type": "string", "enum": ["train", "test"]},
        "label": {"type": "string"},
        "correlation_id": {"type": "string"},
    },
    "additionalProperties": True,
}

emotion_validator = Draft202012Validator(EMOTION_EVENT_SCHEMA)
promotion_validator = Draft202012Validator(PROMOTION_SCHEMA)

router = APIRouter()

# Logging setup
logger = logging.getLogger("gateway")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


def error_payload(
    error: str,
    message: str,
    correlation_id: Optional[str] = None,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": "v1",
        "error": error,
        "message": message,
        "correlation_id": correlation_id or "",
    }
    if fields:
        payload["fields"] = fields
    return payload


def ensure_api_version(x_api_version: Optional[str]):
    if x_api_version != "v1":
        raise HTTPException(
            status_code=400,
            detail=error_payload("validation_error", "X-API-Version must be 'v1'", ""),
        )


def _health_response() -> str:
    """Shared health response for legacy and /api variants."""
    return "ok"


def _ready_response() -> str:
    """Shared ready response for legacy and /api variants."""
    return "ready"


@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return _health_response()


@router.get("/api/health", response_class=PlainTextResponse)
async def api_health() -> str:
    return _health_response()


@router.get("/ready", response_class=PlainTextResponse)
async def ready() -> str:
    return _ready_response()


@router.get("/api/ready", response_class=PlainTextResponse)
async def api_ready() -> str:
    return _ready_response()


@router.get("/metrics")
async def metrics() -> Response:
    payload = generate_latest(get_registry())
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@router.post("/api/events/emotion")
async def post_emotion_event(
    request: Request,
    x_api_version: Optional[str] = Header(default=None, alias="X-API-Version"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    try:
        ensure_api_version(x_api_version)
        body = await request.json()
        errors = sorted(emotion_validator.iter_errors(body), key=lambda e: e.path)
        if errors:
            fields = ["/" + "/".join(map(str, e.path)) for e in errors]
            logger.warning("emotion_event_validation_failed", extra={"fields": fields})
            return JSONResponse(
                status_code=400,
                content=error_payload(
                    "validation_error",
                    "Invalid emotion event payload",
                    body.get("correlation_id", ""),
                    fields,
                ),
            )
        logger.info(
            "emotion_event_received",
            extra={
                "device_id": body.get("device_id"),
                "emotion": body.get("emotion"),
                "confidence": body.get("confidence"),
                "correlation_id": body.get("correlation_id"),
            },
        )
        return Response(status_code=202)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("emotion_event_internal_error")
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Unexpected error while processing emotion event"),
        )


@router.post("/api/promote")
async def post_promotion(
    request: Request,
    x_api_version: Optional[str] = Header(default=None, alias="X-API-Version"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """Proxy promotion requests to Ubuntu 1 Media Mover."""
    try:
        ensure_api_version(x_api_version)
        if not idempotency_key:
            return JSONResponse(
                status_code=400,
                content=error_payload("validation_error", "Idempotency-Key header is required"),
            )
        
        # Use app.state for config and HTTP client if available
        http_client = getattr(request.app.state, "http_client", client)
        media_mover_url = getattr(request.app.state, "config", None)
        base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
        
        body = await request.json()
        # Optionally validate payload locally; forward regardless to let upstream enforce contract
        # (keeps behavior consistent with other proxy endpoints)
        url = f"{base_url}/api/media/promote"
        upstream = await http_client.post(
            url,
            json=body,
            headers={"Idempotency-Key": idempotency_key},
        )

        content_type = upstream.headers.get("content-type", "application/json")
        if upstream.is_error and content_type.startswith("application/json"):
            return JSONResponse(content=upstream.json(), status_code=upstream.status_code)

        if content_type.startswith("application/json"):
            return JSONResponse(content=upstream.json(), status_code=upstream.status_code)

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=content_type,
        )
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("promotion_proxy_error")
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Unexpected error while proxying promotion request"),
        )


# POST /api/relabel - Proxy to Media Mover
@router.post("/api/relabel")
async def relabel_video(
    request: Request,
    x_api_version: Optional[str] = Header(default=None, alias="X-API-Version"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    ensure_api_version(x_api_version)
    if not idempotency_key:
        raise HTTPException(status_code=400, detail=error_payload("validation_error", "Idempotency-Key required"))
    http_client = getattr(request.app.state, "http_client", client)
    body = await request.json()
    url = f"{MEDIA_MOVER_URL}/api/relabel"
    response = await http_client.post(url, json=body, headers={"Idempotency-Key": idempotency_key})
    return JSONResponse(content=response.json(), status_code=response.status_code)


# POST /api/manifest/rebuild - Proxy to Media Mover
@router.post("/api/manifest/rebuild")
async def rebuild_manifest(
    request: Request,
    x_api_version: Optional[str] = Header(default=None, alias="X-API-Version"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    ensure_api_version(x_api_version)
    if not idempotency_key:
        raise HTTPException(status_code=400, detail=error_payload("validation_error", "Idempotency-Key required"))
    http_client = getattr(request.app.state, "http_client", client)
    body = await request.json()
    url = f"{MEDIA_MOVER_URL}/api/manifest/rebuild"
    response = await http_client.post(url, json=body, headers={"Idempotency-Key": idempotency_key})
    return JSONResponse(content=response.json(), status_code=response.status_code)


# GET /api/videos/{video_id} - Proxy to Media Mover
@router.get("/api/videos/{video_id}")
async def get_video(video_id: str, request: Request):
    # Use app.state.http_client if available (gateway app), otherwise use module-level client
    http_client = getattr(request.app.state, "http_client", client)
    media_mover_url = getattr(request.app.state, "config", None)
    if media_mover_url and hasattr(media_mover_url, "media_mover_url"):
        base_url = media_mover_url.media_mover_url
    else:
        base_url = MEDIA_MOVER_URL
    
    url = f"{base_url}/api/videos/{video_id}"
    response = await http_client.get(url)
    return JSONResponse(content=response.json(), status_code=response.status_code)


# GET /api/videos/{video_id}/thumb - Proxy to Media Mover
@router.get("/api/videos/{video_id}/thumb")
async def get_thumbnail(video_id: str, request: Request):
    http_client = getattr(request.app.state, "http_client", client)
    media_mover_url = getattr(request.app.state, "config", None)
    base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
    
    url = f"{base_url}/api/videos/{video_id}/thumb"
    response = await http_client.get(url)
    # Return as-is (may be redirect or image)
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))


# ============================================================================
# n8n Agent Event Endpoints
# ============================================================================

@router.post("/api/events/ingest")
async def post_ingest_event(request: Request):
    """Receive ingest completion events from n8n Ingest Agent."""
    try:
        body = await request.json()
        logger.info("ingest_event_received", extra={
            "event_type": body.get("event_type"),
            "video_id": body.get("video_id"),
            "correlation_id": body.get("correlation_id"),
        })
        return JSONResponse(status_code=202, content={"status": "accepted"})
    except Exception:
        logger.exception("ingest_event_error")
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))


@router.post("/api/events/training")
async def post_training_event(request: Request):
    """Receive training events from n8n Training Orchestrator."""
    try:
        body = await request.json()
        logger.info("training_event_received", extra={
            "event_type": body.get("event_type"),
            "run_id": body.get("run_id"),
            "model": body.get("model"),
        })
        return JSONResponse(status_code=202, content={"status": "accepted"})
    except Exception:
        logger.exception("training_event_error")
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))


@router.post("/api/events/deployment")
async def post_deployment_event(request: Request):
    """Receive deployment events from n8n Deployment Agent."""
    try:
        body = await request.json()
        logger.info("deployment_event_received", extra={
            "event_type": body.get("event_type"),
            "run_id": body.get("run_id"),
        })
        return JSONResponse(status_code=202, content={"status": "accepted"})
    except Exception:
        logger.exception("deployment_event_error")
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))


@router.post("/api/events/pipeline")
async def post_pipeline_event(request: Request):
    """Receive pipeline events from n8n ML Pipeline Orchestrator."""
    try:
        body = await request.json()
        logger.info("pipeline_event_received", extra={
            "event_type": body.get("event_type"),
            "pipeline_id": body.get("pipeline_id"),
        })
        return JSONResponse(status_code=202, content={"status": "accepted"})
    except Exception:
        logger.exception("pipeline_event_error")
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))


# In-memory training status store
_training_status: Dict[str, Dict[str, Any]] = {}


@router.get("/api/training/status/{pipeline_id}")
async def get_training_status(pipeline_id: str):
    """Get training status for a pipeline run."""
    status = _training_status.get(pipeline_id, {"status": "unknown"})
    return JSONResponse(status_code=200, content=status)


@router.post("/api/training/status/{pipeline_id}")
async def update_training_status(pipeline_id: str, request: Request):
    """Update training status for a pipeline run."""
    try:
        body = await request.json()
        _training_status[pipeline_id] = body
        return JSONResponse(status_code=200, content={"status": "updated"})
    except Exception:
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))