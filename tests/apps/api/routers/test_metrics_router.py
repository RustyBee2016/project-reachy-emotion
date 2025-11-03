from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.main import create_app
from apps.api.app.metrics import PROMOTION_OPERATION_COUNTER, reset_metrics


@pytest_asyncio.fixture
async def metrics_client():
    reset_metrics()
    PROMOTION_OPERATION_COUNTER.labels(action="stage", outcome="success").inc()

    app = create_app()
    transport = ASGITransport(app=app, root_path="/api/media")
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_promotion_metrics(metrics_client: AsyncClient) -> None:
    response = await metrics_client.get("/metrics")
    assert response.status_code == 200
    assert "promotion_operations_total" in response.text
    assert response.headers["content-type"].startswith("text/plain")
