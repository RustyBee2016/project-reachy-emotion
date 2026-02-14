"""Tests for DB-backed training/deployment status endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_training_status_persistence_roundtrip(client: AsyncClient):
    pipeline_id = "train_status_001"
    payload = {
        "status": "training",
        "metrics": {"epoch": 3, "f1_macro": 0.81},
        "strategy": "balanced_random",
    }

    update_response = await client.post(f"/api/training/status/{pipeline_id}", json=payload)
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "updated"

    get_response = await client.get(f"/api/training/status/{pipeline_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["run_id"] == pipeline_id
    assert body["status"] == "training"
    assert body["metrics"]["epoch"] == 3
    assert body["metrics"]["f1_macro"] == 0.81


@pytest.mark.asyncio
async def test_training_status_latest_returns_most_recent(client: AsyncClient):
    await client.post("/api/training/status/train_status_a", json={"status": "pending", "metrics": {"epoch": 1}})
    await client.post("/api/training/status/train_status_b", json={"status": "completed", "metrics": {"epoch": 5}})

    latest_response = await client.get("/api/training/status/latest")
    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["run_id"] == "train_status_b"
    assert latest["status"] == "completed"


@pytest.mark.asyncio
async def test_deployment_status_persistence_roundtrip(client: AsyncClient):
    pipeline_id = "deploy_status_001"
    payload = {
        "status": "deploying",
        "target_stage": "canary",
        "engine_path": "/opt/reachy/models/emotion.engine",
        "fps_measured": 27.5,
        "latency_p50_ms": 95.0,
    }

    update_response = await client.post(f"/api/deployment/status/{pipeline_id}", json=payload)
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "updated"

    get_response = await client.get(f"/api/deployment/status/{pipeline_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["pipeline_id"] == pipeline_id
    assert body["status"] == "deploying"
    assert body["target_stage"] == "canary"
    assert body["fps_measured"] == 27.5


@pytest.mark.asyncio
async def test_deployment_status_latest_returns_most_recent(client: AsyncClient):
    await client.post(
        "/api/deployment/status/deploy_status_a",
        json={"status": "pending", "target_stage": "shadow", "engine_path": "/tmp/a.engine"},
    )
    await client.post(
        "/api/deployment/status/deploy_status_b",
        json={"status": "success", "target_stage": "rollout", "engine_path": "/tmp/b.engine"},
    )

    latest_response = await client.get("/api/deployment/status/latest")
    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["pipeline_id"] == "deploy_status_b"
    assert latest["status"] == "success"
