from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app import deps
from apps.api.app.main import create_app
from apps.api.app.routers import promote as promote_router


@pytest_asyncio.fixture
async def api_client():
    app = create_app()
    transport = ASGITransport(app=app, root_path="/api/media")
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, app

    app.dependency_overrides.clear()


# ── /api/v1/promote/stage — removed, returns 410 ──────────────────────────


@pytest.mark.asyncio
async def test_stage_endpoint_returns_410_gone(api_client):
    client, app = api_client

    payload = {
        "video_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        "label": "happy",
    }
    response = await client.post("/api/v1/promote/stage", json=payload)
    assert response.status_code == 410
    body = response.json()
    assert "removed" in body["detail"]["error"].lower()
    assert "/api/v1/media/promote" in body["detail"]["error"]
    assert promote_router.CORRELATION_ID_HEADER in response.headers


# ── /api/v1/promote/sample — removed, returns 410 ─────────────────────────


@pytest.mark.asyncio
async def test_sample_endpoint_returns_410_gone(api_client):
    client, app = api_client

    payload = {
        "run_id": "run_0001",
        "target_split": "train",
        "sample_fraction": 0.5,
        "strategy": "balanced_random",
    }
    response = await client.post("/api/v1/promote/sample", json=payload)
    assert response.status_code == 410
    body = response.json()
    assert "removed" in body["detail"]["error"].lower()
    assert promote_router.CORRELATION_ID_HEADER in response.headers


# ── /api/v1/promote/reset-manifest — still functional ─────────────────────


@pytest.mark.asyncio
async def test_reset_manifest_still_works(api_client):
    """Ensure the non-deprecated endpoint wasn't affected."""
    client, app = api_client

    class StubService:
        def __init__(self) -> None:
            self.correlation_id = None
            self.committed = False
            self.reset_called = False

        def set_correlation_id(self, correlation_id: str) -> None:
            self.correlation_id = correlation_id

        async def commit(self) -> None:
            self.committed = True

        def reset_manifest(self, *, reason: str, run_id: str | None = None) -> None:
            self.reset_called = True

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {"reason": "test reset"}
    response = await client.post("/api/v1/promote/reset-manifest", json=payload)
    assert response.status_code == 202
    assert stub.committed
    assert stub.reset_called
