"""Phase 3 integration tests — emotion events, Gate B/C, health, cue feedback.

Tests exercise the new endpoints added for edge deployment without
requiring Jetson hardware.  Database is in-memory SQLite via conftest.
"""

from __future__ import annotations

import os

import pytest

# The .env file loaded by main.py sets GATEWAY_TOKEN, so we must supply it.
_AUTH_TOKEN = os.getenv(
    "GATEWAY_TOKEN",
    "test-gateway-token-a7f3c9e2b1d4f8a6c3e5b7d9f1a3c5e7",
)
H = {"Authorization": f"Bearer {_AUTH_TOKEN}"}

pytestmark = pytest.mark.asyncio


# ── WS-3: Emotion Event Persistence ─────────────────────────────────

class TestEmotionEventEndpoints:
    """POST/GET /api/v1/events/emotion and /stats."""

    async def test_create_emotion_event(self, client):
        resp = await client.post(
            "/api/v1/events/emotion",
            headers=H,
            json={
                "device_id": "reachy-mini-01",
                "emotion": "happy",
                "confidence": 0.92,
                "inference_ms": 42.5,
                "session_id": "sess-1",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["emotion"] == "happy"
        assert body["data"]["confidence"] == 0.92
        assert body["data"]["device_id"] == "reachy-mini-01"

    async def test_create_event_invalid_emotion(self, client):
        resp = await client.post(
            "/api/v1/events/emotion",
            headers=H,
            json={
                "device_id": "dev-1",
                "emotion": "angry",
                "confidence": 0.9,
            },
        )
        assert resp.status_code == 422

    async def test_create_event_confidence_out_of_range(self, client):
        resp = await client.post(
            "/api/v1/events/emotion",
            headers=H,
            json={
                "device_id": "dev-1",
                "emotion": "sad",
                "confidence": 1.5,
            },
        )
        assert resp.status_code == 422

    async def test_list_emotion_events(self, client):
        for emotion in ("happy", "sad"):
            await client.post(
                "/api/v1/events/emotion",
                headers=H,
                json={
                    "device_id": "dev-1",
                    "emotion": emotion,
                    "confidence": 0.85,
                },
            )

        resp = await client.get("/api/v1/events/emotion", headers=H, params={"minutes": 60})
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 2

    async def test_list_filter_by_emotion(self, client):
        await client.post(
            "/api/v1/events/emotion",
            headers=H,
            json={"device_id": "dev-1", "emotion": "neutral", "confidence": 0.7},
        )
        resp = await client.get(
            "/api/v1/events/emotion",
            headers=H,
            params={"emotion": "neutral", "minutes": 60},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert all(e["emotion"] == "neutral" for e in items)

    async def test_emotion_event_stats(self, client):
        for _ in range(5):
            await client.post(
                "/api/v1/events/emotion",
                headers=H,
                json={
                    "device_id": "dev-1",
                    "emotion": "happy",
                    "confidence": 0.9,
                    "inference_ms": 45.0,
                },
            )
        for _ in range(3):
            await client.post(
                "/api/v1/events/emotion",
                headers=H,
                json={
                    "device_id": "dev-1",
                    "emotion": "sad",
                    "confidence": 0.4,
                    "inference_ms": 50.0,
                },
            )

        resp = await client.get("/api/v1/events/emotion/stats", headers=H, params={"minutes": 60})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_events"] >= 8
        assert "happy" in data["by_emotion"]
        assert data["avg_confidence"] is not None
        assert data["abstention_count"] >= 3


# ── WS-6: Gate C Metrics & Validation ─────────────────────────────────

class TestGateCEndpoints:
    """POST/GET /api/v1/gate-c/*."""

    async def test_session_start_end(self, client):
        resp = await client.post(
            "/api/v1/gate-c/session",
            headers=H,
            json={"device_id": "dev-1", "session_id": "s-1", "action": "start"},
        )
        assert resp.status_code == 200

        resp = await client.post(
            "/api/v1/gate-c/session",
            headers=H,
            json={"device_id": "dev-1", "session_id": "s-1", "action": "end"},
        )
        assert resp.status_code == 200

    async def test_record_complaint(self, client):
        resp = await client.post(
            "/api/v1/gate-c/complaint",
            headers=H,
            json={
                "device_id": "dev-1",
                "session_id": "s-1",
                "reason": "Robot didn't respond",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["reason"] == "Robot didn't respond"

    async def test_gate_c_metrics(self, client):
        await client.post(
            "/api/v1/events/emotion",
            headers=H,
            json={
                "device_id": "dev-1",
                "emotion": "happy",
                "confidence": 0.9,
                "inference_ms": 40.0,
                "session_id": "s-metrics",
            },
        )

        resp = await client.get("/api/v1/gate-c/metrics", headers=H, params={"minutes": 60})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_events" in data
        assert "abstention_rate" in data

    async def test_gate_c_validate(self, client):
        for _ in range(10):
            await client.post(
                "/api/v1/events/emotion",
                headers=H,
                json={
                    "device_id": "dev-1",
                    "emotion": "happy",
                    "confidence": 0.9,
                    "inference_ms": 40.0,
                    "session_id": "s-valid",
                },
            )

        resp = await client.get("/api/v1/gate-c/validate", headers=H, params={"minutes": 60})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "passed" in data
        assert "checks" in data
        assert "latency_e2e" in data["checks"]
        assert "abstention_rate" in data["checks"]


# ── WS-1: Gate B Validator Logic ─────────────────────────────────────

class TestGateBValidator:
    """Unit tests for the Gate B validator logic (no hardware needed)."""

    def test_import(self):
        import importlib
        import sys

        sys.path.insert(0, "jetson")
        try:
            mod = importlib.import_module("gate_b_validator")
            assert hasattr(mod, "GateBValidator")
            assert hasattr(mod, "GateBThresholds")
            assert hasattr(mod, "GateBResult")
        finally:
            sys.path.pop(0)

    def test_thresholds_defaults(self):
        import sys

        sys.path.insert(0, "jetson")
        try:
            from gate_b_validator import GateBThresholds

            t = GateBThresholds()
            assert t.latency_p50_ms == 120.0
            assert t.latency_p95_ms == 250.0
            assert t.gpu_memory_gb == 2.5
            assert t.macro_f1 == 0.80
        finally:
            sys.path.pop(0)

    def test_validate_skips_f1_without_test_set(self):
        import sys

        sys.path.insert(0, "jetson")
        try:
            from gate_b_validator import GateBValidator

            validator = GateBValidator()
            result = validator.validate(duration_s=0, test_set_dir=None)
            assert not result.passed
            assert any("no --test-set" in s for s in result.skipped)
        finally:
            sys.path.pop(0)


# ── WS-2: Health Endpoint ──────────────────────────────────────────

class TestHealthServer:
    """Tests for the Jetson health server module."""

    def test_import(self):
        import sys

        sys.path.insert(0, "jetson")
        try:
            from health_server import HealthServer

            assert HealthServer is not None
        except ImportError:
            pytest.skip("aiohttp not installed")
        finally:
            sys.path.pop(0)

    async def test_health_server_status_build(self):
        import sys

        sys.path.insert(0, "jetson")
        try:
            from health_server import HealthServer
        except ImportError:
            pytest.skip("aiohttp not installed")
            return
        finally:
            sys.path.pop(0)

        server = HealthServer()
        status = server._build_status()
        assert "status" in status
        assert "uptime_s" in status
        assert "deepstream_running" in status
        assert "websocket_connected" in status
        assert status["deepstream_running"] is False
        assert status["websocket_connected"] is False


# ── WS-5: Auth Middleware ──────────────────────────────────────────

class TestAuthMiddleware:
    """Verify auth is enforced."""

    async def test_health_is_public(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    async def test_unauthenticated_request_rejected(self, client):
        resp = await client.post(
            "/api/v1/events/emotion",
            json={"device_id": "x", "emotion": "happy", "confidence": 0.9},
        )
        assert resp.status_code == 401
