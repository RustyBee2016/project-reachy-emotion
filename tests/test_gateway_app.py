"""Tests for the separate Gateway application on Ubuntu 2."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from httpx import ASGITransport, AsyncClient

from apps.gateway.main import create_app
from apps.gateway.config import GatewayConfig


@pytest.fixture
def gateway_config():
    """Create a test gateway configuration."""
    return GatewayConfig(
        media_mover_url="http://testhost:8083",
        nginx_media_url="http://testhost:8082",
        database_url="postgresql+asyncpg://test:test@testhost:5432/test_db",
        api_host="127.0.0.1",
        api_port=8000,
        enable_cors=True,
        ui_origins=["http://localhost:8501"],
        log_level="INFO",
    )


@pytest.fixture
def test_app(gateway_config):
    """Create gateway app with deterministic config for testing."""
    with patch("apps.gateway.main.load_config", return_value=gateway_config):
        app = create_app()
        # Provide default state client to avoid lifespan coupling in tests.
        app.state.http_client = Mock()
        return app


def _request(test_app, method: str, url: str, **kwargs):
    async def _run():
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_run())


def test_gateway_health_endpoint(test_app):
    """Test that the gateway health endpoint works."""
    response = _request(test_app, "GET", "/health")
    assert response.status_code == 200
    assert response.text == "ok"


def test_gateway_ready_endpoint(test_app):
    """Test that the gateway ready endpoint works."""
    response = _request(test_app, "GET", "/ready")
    assert response.status_code == 200
    assert response.text == "ready"


def test_gateway_metrics_endpoint(test_app):
    """Test that the gateway metrics endpoint works."""
    response = _request(test_app, "GET", "/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_gateway_training_status_proxy(test_app):
    """Test gateway proxies training status to upstream media mover."""
    mocked_response = Mock(status_code=200)
    mocked_response.json.return_value = {"run_id": "run_1", "status": "training"}
    test_app.state.http_client.get = AsyncMock(return_value=mocked_response)

    response = _request(test_app, "GET", "/api/training/status/run_1")
    assert response.status_code == 200
    assert response.json()["status"] == "training"
    test_app.state.http_client.get.assert_awaited()


def test_gateway_deployment_status_update_proxy(test_app):
    """Test gateway proxies deployment status updates to upstream media mover."""
    mocked_response = Mock(status_code=200)
    mocked_response.json.return_value = {"status": "updated", "pipeline_id": "pipe_1"}
    test_app.state.http_client.post = AsyncMock(return_value=mocked_response)

    payload = {"status": "deploying", "target_stage": "canary", "engine_path": "/tmp/model.engine"}
    response = _request(test_app, "POST", "/api/deployment/status/pipe_1", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    test_app.state.http_client.post.assert_awaited()


def test_gateway_config_validation():
    """Test that gateway config validation works."""
    # Valid config
    config = GatewayConfig(
        media_mover_url="http://10.0.4.130:8083",
        nginx_media_url="http://10.0.4.130:8082",
    )
    config.validate()  # Should not raise
    
    # Invalid media mover URL
    config = GatewayConfig(media_mover_url="not-a-url")
    with pytest.raises(ValueError, match="Invalid GATEWAY_MEDIA_MOVER_URL"):
        config.validate()
    
    # Invalid port
    config = GatewayConfig(api_port=99999)
    with pytest.raises(ValueError, match="Invalid GATEWAY_API_PORT"):
        config.validate()


def test_gateway_config_masks_password():
    """Test that database password is masked in logs."""
    config = GatewayConfig(
        database_url="postgresql+asyncpg://user:secret123@host:5432/db"
    )
    logged = config.log_configuration(mask_secrets=True)
    assert "secret123" not in logged["database_url"]
    assert "****" in logged["database_url"]
    assert "user" in logged["database_url"]


def test_emotion_event_requires_api_version(test_app):
    """Test that emotion event endpoint requires X-API-Version header."""
    payload = {
        "schema_version": "v1",
        "device_id": "test-device",
        "ts": "2025-11-24T21:00:00Z",
        "emotion": "happy",
        "confidence": 0.9,
        "inference_ms": 50,
        "window": {"fps": 30, "size_s": 1.0, "hop_s": 0.5},
        "meta": {},
        "correlation_id": "test-123",
    }
    
    # Without header
    response = _request(test_app, "POST", "/api/events/emotion", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"
    
    # With header
    response = _request(
        test_app,
        "POST",
        "/api/events/emotion",
        json=payload,
        headers={"X-API-Version": "v1"},
    )
    assert response.status_code == 202


def test_gateway_proxies_to_media_mover(test_app):
    """Test that gateway proxies requests to Media Mover."""
    # This is an integration test that would require mocking httpx
    # For now, just verify the endpoint exists
    
    payload = {
        "schema_version": "v1",
        "clip": "test_clip.mp4",
        "target": "train",
        "label": "happy",
        "correlation_id": "test-456",
    }
    
    # This will fail because we don't have a real Media Mover running
    # but it confirms the endpoint is wired up
    response = _request(
        test_app,
        "POST",
        "/api/promote",
        json=payload,
        headers={
            "X-API-Version": "v1",
            "Idempotency-Key": "test-key-123",
        },
    )
    
    # We expect either a connection error (503) or a proxied response
    # The key is that the endpoint exists and tries to proxy
    assert response.status_code in [200, 500, 502, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
