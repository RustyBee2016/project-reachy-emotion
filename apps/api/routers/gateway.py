from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.api.app.metrics_registry import get_registry
from jsonschema import Draft202012Validator
from pythonjsonlogger.json import JsonFormatter

# Ubuntu 1 Media Mover base URL
MEDIA_MOVER_URL = os.getenv("GATEWAY_MEDIA_MOVER_URL", "http://10.0.4.130:8083")

# Module-level fallback client (used if app.state.http_client is not set).
# Prefer the lifespan-managed client via get_http_client(request).
_fallback_client: httpx.AsyncClient | None = None


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the lifespan-managed httpx client, falling back to a module-level singleton."""
    global _fallback_client
    app_client = getattr(request.app.state, "http_client", None)
    if app_client is not None:
        return app_client
    if _fallback_client is None:
        _fallback_client = httpx.AsyncClient()
    return _fallback_client

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
            "happy", "sad", "neutral"
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
        http_client = get_http_client(request)
        media_mover_url = getattr(request.app.state, "config", None)
        base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
        
        body = await request.json()
        # Prefer canonical v1 endpoint and fall back to legacy only for partial deployments.
        canonical_url = f"{base_url}/api/v1/media/promote"
        legacy_url = f"{base_url}/api/media/promote"
        upstream = await http_client.post(
            canonical_url,
            json=body,
            headers={"Idempotency-Key": idempotency_key},
        )
        promote_url_used = canonical_url
        fallback_used = False
        if upstream.status_code == 404:
            upstream = await http_client.post(
                legacy_url,
                json=body,
                headers={"Idempotency-Key": idempotency_key},
            )
            promote_url_used = legacy_url
            fallback_used = True
        logger.info(
            "promotion_proxy_result",
            extra={
                "correlation_id": body.get("correlation_id"),
                "idempotency_key": idempotency_key,
                "upstream_status": upstream.status_code,
                "promote_url_used": promote_url_used,
                "fallback_used": fallback_used,
            },
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
    http_client = get_http_client(request)
    body = await request.json()
    url = f"{MEDIA_MOVER_URL}/api/relabel"
    response = await http_client.post(url, json=body, headers={"Idempotency-Key": idempotency_key})
    return JSONResponse(content=response.json(), status_code=response.status_code)

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
_generation_status: Dict[str, Dict[str, Any]] = {}


@router.get("/api/training/status/{pipeline_id}")
async def get_training_status(pipeline_id: str, request: Request):
    """Get training status for a pipeline run from Media Mover DB-backed API."""
    http_client = get_http_client(request)
    media_mover_url = getattr(request.app.state, "config", None)
    base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
    url = f"{base_url}/api/training/status/{pipeline_id}"
    response = await http_client.get(url)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.post("/api/training/status/{pipeline_id}")
async def update_training_status(pipeline_id: str, request: Request):
    """Update training status for a pipeline run via Media Mover DB-backed API."""
    try:
        body = await request.json()
        http_client = get_http_client(request)
        media_mover_url = getattr(request.app.state, "config", None)
        base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
        url = f"{base_url}/api/training/status/{pipeline_id}"
        response = await http_client.post(url, json=body)
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception:
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))


@router.post("/api/media/ingest")
async def ingest_media_file(
    request: Request,
    file: UploadFile = File(...),
    for_training: bool = Form(default=False),
    correlation_id: Optional[str] = Form(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """Proxy direct multipart upload to Media Mover ingest endpoint."""
    corr_id = correlation_id or str(uuid.uuid4())
    http_client = get_http_client(request)
    media_cfg = getattr(request.app.state, "config", None)
    base_url = media_cfg.media_mover_url if media_cfg and hasattr(media_cfg, "media_mover_url") else MEDIA_MOVER_URL

    file_bytes = await file.read()
    files = {"file": (file.filename or "upload.mp4", file_bytes, file.content_type or "video/mp4")}
    data = {
        "for_training": str(bool(for_training)).lower(),
        "correlation_id": corr_id,
    }

    headers: Dict[str, str] = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    upstream = await http_client.post(
        f"{base_url}/api/v1/ingest/upload",
        files=files,
        data=data,
        headers=headers or None,
    )
    return JSONResponse(content=upstream.json(), status_code=upstream.status_code)


@router.post("/api/gen/request")
async def enqueue_generation(request: Request):
    """Create a generation request record (local stub pending n8n integration)."""
    body = await request.json()
    correlation_id = body.get("correlation_id") or str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    _generation_status[request_id] = {
        "status": "queued",
        "prompt": body.get("prompt"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "message": "Generation request queued. Connect n8n workflow to execute.",
        },
    )


@router.get("/api/gen/status/{request_id}")
async def get_generation_status(request_id: str):
    status_obj = _generation_status.get(request_id)
    if not status_obj:
        return JSONResponse(status_code=404, content={"status": "not_found", "request_id": request_id})
    return JSONResponse(status_code=200, content={"request_id": request_id, **status_obj})


@router.post("/api/privacy/redact/{video_id}")
async def redact_video(
    video_id: str,
    request: Request,
):
    """Proxy redact/purge requests to Media Mover privacy endpoint."""
    body = await request.json()
    corr_id = body.get("correlation_id")
    reason = body.get("reason")

    http_client = get_http_client(request)
    media_cfg = getattr(request.app.state, "config", None)
    base_url = media_cfg.media_mover_url if media_cfg and hasattr(media_cfg, "media_mover_url") else MEDIA_MOVER_URL

    params = {}
    if reason:
        params["reason"] = reason
    if corr_id:
        params["correlation_id"] = corr_id

    upstream = await http_client.post(
        f"{base_url}/api/v1/privacy/redact/{video_id}",
        params=params or None,
    )
    return JSONResponse(content=upstream.json(), status_code=upstream.status_code)


@router.get("/api/deployment/status/{pipeline_id}")
async def get_deployment_status(pipeline_id: str, request: Request):
    """Get deployment status for a pipeline run from Media Mover DB-backed API."""
    http_client = get_http_client(request)
    media_mover_url = getattr(request.app.state, "config", None)
    base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
    url = f"{base_url}/api/deployment/status/{pipeline_id}"
    response = await http_client.get(url)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.post("/api/deployment/status/{pipeline_id}")
async def update_deployment_status(pipeline_id: str, request: Request):
    """Update deployment status via Media Mover DB-backed API."""
    try:
        body = await request.json()
        http_client = get_http_client(request)
        media_mover_url = getattr(request.app.state, "config", None)
        base_url = media_mover_url.media_mover_url if media_mover_url and hasattr(media_mover_url, "media_mover_url") else MEDIA_MOVER_URL
        url = f"{base_url}/api/deployment/status/{pipeline_id}"
        response = await http_client.post(url, json=body)
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception:
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))
