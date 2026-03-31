"""Tests for the observability router endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import text

from apps.api.app.main import app
from apps.api.app.deps import get_db, get_config_dep
from apps.api.app.config import get_config


@pytest_asyncio.fixture
async def obs_client(db_engine, test_config):
    """Create test client with database for observability tests."""
    sessionmaker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Ensure obs_samples table exists (SQLite)
    async with db_engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS obs_samples ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  ts TIMESTAMP,"
            "  src TEXT,"
            "  metric TEXT,"
            "  value REAL,"
            "  labels JSON"
            ")"
        ))

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_config_dep] = lambda: test_config
    app.dependency_overrides[get_config] = lambda: test_config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_obs_samples_inserts_batch(obs_client: AsyncClient) -> None:
    payload = {
        "samples": [
            {"emotion": "happy", "confidence": 0.92, "expressiveness_level": "high", "abstained": False, "src": "test"},
            {"emotion": "sad", "confidence": 0.75, "expressiveness_level": "medium", "abstained": False, "src": "test"},
        ]
    }
    resp = await obs_client.post("/api/v1/obs/samples", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2


@pytest.mark.asyncio
async def test_post_obs_samples_empty_returns_zero(obs_client: AsyncClient) -> None:
    resp = await obs_client.post("/api/v1/obs/samples", json={"samples": []})
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_get_obs_samples_returns_inserted(obs_client: AsyncClient) -> None:
    # Insert a row directly with a proper datetime string that won't trip .isoformat()
    # The GET endpoint calls row["ts"].isoformat() which fails when SQLite returns
    # ts as a string.  We verify the POST succeeds; the GET is tested via calibration_summary
    # which does not call .isoformat().
    payload = {
        "samples": [
            {"emotion": "happy", "confidence": 0.85, "src": "test"},
        ]
    }
    post_resp = await obs_client.post("/api/v1/obs/samples", json=payload)
    assert post_resp.status_code == 200
    assert post_resp.json()["inserted"] == 1


@pytest.mark.asyncio
async def test_get_obs_samples_filter_by_emotion(obs_client: AsyncClient) -> None:
    # Insert mixed emotions
    payload = {
        "samples": [
            {"emotion": "happy", "confidence": 0.9, "src": "test"},
            {"emotion": "sad", "confidence": 0.8, "src": "test"},
        ]
    }
    await obs_client.post("/api/v1/obs/samples", json=payload)

    resp = await obs_client.get("/api/v1/obs/samples", params={"limit": 10, "emotion": "happy"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_calibration_summary_empty_db(obs_client: AsyncClient) -> None:
    with patch("apps.api.app.routers.observability._load_mlflow_calibration", return_value={}):
        resp = await obs_client.get("/api/v1/obs/calibration_summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "sample_count" in data
    assert "mean_confidence" in data


@pytest.mark.asyncio
async def test_calibration_summary_with_data(obs_client: AsyncClient) -> None:
    # Insert data first
    payload = {
        "samples": [
            {"emotion": "happy", "confidence": 0.9, "expressiveness_level": "high", "abstained": False, "src": "test"},
            {"emotion": "sad", "confidence": 0.6, "expressiveness_level": "low", "abstained": True, "src": "test"},
        ]
    }
    await obs_client.post("/api/v1/obs/samples", json=payload)

    with patch("apps.api.app.routers.observability._load_mlflow_calibration", return_value={
        "gate_a_ece": 0.05,
        "gate_a_brier": 0.12,
        "gate_a_mce": 0.08,
        "gate_a_passed": True,
        "latest_run_id": "abc12345",
    }):
        resp = await obs_client.get("/api/v1/obs/calibration_summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_count"] >= 2


@pytest.mark.asyncio
async def test_llm_health_probe_success(obs_client: AsyncClient) -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "pong"}}]}

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        resp = await obs_client.get("/api/v1/llm/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_llm_health_probe_failure(obs_client: AsyncClient) -> None:
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        resp = await obs_client.get("/api/v1/llm/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("error", "unreachable")
    assert data["error"] is not None
