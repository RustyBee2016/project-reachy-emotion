"""Ubuntu 2 — App Gateway (FastAPI)

Endpoints:
- POST /api/events/emotion (v1)
- POST /api/promote (v1)
- GET  /health
- GET  /ready
- GET  /metrics

Validation:
- Enforce X-API-Version: v1
- Validate JSON bodies against ./api/schemas/*.json
- Return standard error payload (api/schemas/error_v1.json) on failures
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from jsonschema import Draft202012Validator, ValidationError
from pythonjsonlogger import jsonlogger

# ----------------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------------
logger = logging.getLogger("gateway")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

app = FastAPI(title="Reachy_Local_08.2 App Gateway", version="0.1.0")

# ----------------------------------------------------------------------------
# Schema loading helpers
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = PROJECT_ROOT / "api" / "schemas"

with open(SCHEMAS_DIR / "emotion_event_v1.json", "r") as f:
    EMOTION_EVENT_SCHEMA = json.load(f)
with open(SCHEMAS_DIR / "promotion_request_v1.json", "r") as f:
    PROMOTION_SCHEMA = json.load(f)
with open(SCHEMAS_DIR / "error_v1.json", "r") as f:
    ERROR_SCHEMA = json.load(f)

emotion_validator = Draft202012Validator(EMOTION_EVENT_SCHEMA)
promotion_validator = Draft202012Validator(PROMOTION_SCHEMA)


def error_payload(error: str, message: str, correlation_id: str | None = None, fields: list[str] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": "v1",
        "error": error,
        "message": message,
        "correlation_id": correlation_id or "",
    }
    if fields:
        payload["fields"] = fields
    return payload


def ensure_api_version(x_api_version: str | None):
    if x_api_version != "v1":
        raise HTTPException(status_code=400, detail=error_payload(
            "validation_error", "X-API-Version must be 'v1'", correlation_id=""))


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------
@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/ready", response_class=PlainTextResponse)
async def ready() -> str:
    # TODO: add DB and upstream checks
    return "ready"


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    # TODO: integrate Prometheus client; placeholder histogram counters
    return "# HELP gateway_placeholder 1\n# TYPE gateway_placeholder counter\ngateway_placeholder 1\n"


@app.post("/api/events/emotion")
async def post_emotion_event(
    request: Request,
    x_api_version: str | None = Header(default=None, alias="X-API-Version"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Ingest an emotion event from Jetson.

    Validates payload against emotion_event_v1.json and logs the event.
    Returns 202 Accepted on success.
    """
    try:
        ensure_api_version(x_api_version)
        body = await request.json()
        errors = sorted(emotion_validator.iter_errors(body), key=lambda e: e.path)
        if errors:
            fields = ["/" + "/".join(map(str, e.path)) for e in errors]
            logger.warning("emotion_event_validation_failed", extra={"fields": fields})
            return JSONResponse(status_code=400, content=error_payload(
                "validation_error", "Invalid emotion event payload", body.get("correlation_id", ""), fields))

        logger.info("emotion_event_received", extra={
            "device_id": body.get("device_id"),
            "emotion": body.get("emotion"),
            "confidence": body.get("confidence"),
            "correlation_id": body.get("correlation_id"),
        })
        # TODO: write to DB, dispatch to LLM orchestrator
        return Response(status_code=202)
    except ValidationError as ve:
        return JSONResponse(status_code=400, content=error_payload(
            "validation_error", str(ve.message)))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("emotion_event_internal_error")
        return JSONResponse(status_code=500, content=error_payload(
            "internal_error", "Unexpected error while processing emotion event"))


@app.post("/api/promote")
async def post_promotion(
    request: Request,
    x_api_version: str | None = Header(default=None, alias="X-API-Version"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Promote a clip from temp → train/test.

    Requires Idempotency-Key and validates payload against promotion_request_v1.json.
    """
    try:
        ensure_api_version(x_api_version)
        if not idempotency_key:
            return JSONResponse(status_code=400, content=error_payload(
                "validation_error", "Idempotency-Key header is required"))
        body = await request.json()
        errors = sorted(promotion_validator.iter_errors(body), key=lambda e: e.path)
        if errors:
            fields = ["/" + "/".join(map(str, e.path)) for e in errors]
            logger.warning("promotion_validation_failed", extra={"fields": fields})
            return JSONResponse(status_code=400, content=error_payload(
                "validation_error", "Invalid promotion request payload", body.get("correlation_id", ""), fields))

        logger.info("promotion_request_received", extra={
            "clip": body.get("clip"),
            "target": body.get("target"),
            "label": body.get("label"),
            "correlation_id": body.get("correlation_id"),
        })
        # TODO: orchestrate move on Ubuntu 1 and update PostgreSQL
        return JSONResponse(status_code=200, content={"status": "ok"})
    except ValidationError as ve:
        return JSONResponse(status_code=400, content=error_payload(
            "validation_error", str(ve.message)))
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("promotion_internal_error")
        return JSONResponse(status_code=500, content=error_payload(
            "internal_error", "Unexpected error while processing promotion request"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.gateway.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
