import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.api.main import app
from apps.api.routers.gateway import EMOTION_EVENT_SCHEMA, PROMOTION_SCHEMA

client = TestClient(app)


def valid_emotion_event():
    return {
        "schema_version": "v1",
        "device_id": "reachy-mini-01",
        "ts": "2025-09-16T20:11:33Z",
        "emotion": "happy",
        "confidence": 0.87,
        "inference_ms": 92,
        "window": {"fps": 30, "size_s": 1.2, "hop_s": 0.5},
        "meta": {"model_version": "actionrecog-0.8.2-trt", "temp": 68.2},
        "correlation_id": "test-corr-id",
    }


def valid_promotion_request():
    return {
        "schema_version": "v1",
        "clip": "clip_00123.mp4",
        "target": "train",
        "label": "sad",
        "correlation_id": "test-corr-id",
    }


def test_health_ready():
    assert client.get("/health").text == "ok"
    assert client.get("/ready").text == "ready"


def test_emotion_event_requires_version_header():
    resp = client.post("/api/events/emotion", json=valid_emotion_event())
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_error"


def test_emotion_event_valid_202():
    payload = valid_emotion_event()
    resp = client.post(
        "/api/events/emotion",
        headers={"X-API-Version": "v1"},
        json=payload,
    )
    assert resp.status_code == 202


def test_emotion_event_invalid_confidence_400():
    payload = valid_emotion_event()
    payload["confidence"] = 1.5
    resp = client.post(
        "/api/events/emotion",
        headers={"X-API-Version": "v1"},
        json=payload,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_error"


def test_promotion_requires_idempotency_key():
    resp = client.post(
        "/api/promote",
        headers={"X-API-Version": "v1"},
        json=valid_promotion_request(),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_error"


def test_promotion_valid_200():
    resp = client.post(
        "/api/promote",
        headers={"X-API-Version": "v1", "Idempotency-Key": "abc-123"},
        json=valid_promotion_request(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_schema_files_validate_examples():
    Draft202012Validator(EMOTION_EVENT_SCHEMA).validate(valid_emotion_event())
    Draft202012Validator(PROMOTION_SCHEMA).validate(valid_promotion_request())
