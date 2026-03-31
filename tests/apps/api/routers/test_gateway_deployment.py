"""Tests for the deployment status endpoints in gateway_upstream router."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_deployment_status_latest_empty_db(client: AsyncClient) -> None:
    resp = await client.get("/api/deployment/status/latest")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


@pytest.mark.asyncio
async def test_post_then_get_deployment_status(client: AsyncClient) -> None:
    payload = {
        "status": "pending",
        "target_stage": "canary",
        "engine_path": "s3://models/enet_b0.engine",
        "model_version": "v1.0",
    }
    resp = await client.post("/api/deployment/status/pipeline_001", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "updated"
    assert data["pipeline_id"] == "pipeline_001"

    # Retrieve it
    resp = await client.get("/api/deployment/status/pipeline_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["target_stage"] == "canary"
    assert data["engine_path"] == "s3://models/enet_b0.engine"
    assert data["model_version"] == "v1.0"


@pytest.mark.asyncio
async def test_get_deployment_status_unknown_pipeline(client: AsyncClient) -> None:
    resp = await client.get("/api/deployment/status/nonexistent_pipeline")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


@pytest.mark.asyncio
async def test_post_deployment_status_with_gate_b_metrics(client: AsyncClient) -> None:
    payload = {
        "status": "success",
        "target_stage": "shadow",
        "engine_path": "/engines/enet_b0_fp16.engine",
        "gate_b_passed": True,
        "fps_measured": 30.5,
        "latency_p50_ms": 45.2,
        "latency_p95_ms": 98.7,
        "gpu_memory_gb": 1.2,
    }
    resp = await client.post("/api/deployment/status/pipeline_002", json=payload)
    assert resp.status_code == 200

    resp = await client.get("/api/deployment/status/pipeline_002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gate_b_passed"] is True
    assert data["fps_measured"] == 30.5
    assert data["latency_p50_ms"] == 45.2
    assert data["latency_p95_ms"] == 98.7
    assert data["gpu_memory_gb"] == 1.2


@pytest.mark.asyncio
async def test_latest_returns_most_recent_deployment(client: AsyncClient) -> None:
    # Post two deployments
    await client.post("/api/deployment/status/first_deploy", json={
        "status": "success",
        "target_stage": "shadow",
    })
    await client.post("/api/deployment/status/second_deploy", json={
        "status": "pending",
        "target_stage": "canary",
    })

    resp = await client.get("/api/deployment/status/latest")
    assert resp.status_code == 200
    data = resp.json()
    # Latest should be the second deployment
    assert data["status"] == "pending"
    assert data["target_stage"] == "canary"
