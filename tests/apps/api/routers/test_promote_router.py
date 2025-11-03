from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app import deps
from apps.api.app.main import create_app
from apps.api.app.routers import promote as promote_router
from apps.api.app.services import PromotionValidationError, SampleResult, StageResult


class StubServiceBase:
    def __init__(self) -> None:
        self.correlation_id = None
        self.committed = False
        self.rolled_back = False

    def set_correlation_id(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest_asyncio.fixture
async def api_client():
    app = create_app()
    transport = ASGITransport(app=app, root_path="/api/media")
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, app

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stage_videos_success(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        async def stage_to_dataset_all(self, video_ids, *, label, dry_run=False):
            return StageResult(
                promoted_ids=tuple(video_ids),
                skipped_ids=tuple(),
                failed_ids=tuple(),
                dry_run=dry_run,
            )

        async def sample_split(self, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("sample_split should not be called")

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {
        "video_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        "label": "happy",
    }
    response = await client.post("/promote/stage", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["promoted_ids"] == payload["video_ids"]
    assert promote_router.CORRELATION_ID_HEADER in response.headers
    assert stub.committed
    assert not stub.rolled_back


@pytest.mark.asyncio
async def test_stage_videos_service_validation_error(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        async def stage_to_dataset_all(self, video_ids, *, label, dry_run=False):
            raise PromotionValidationError("invalid label")

        async def sample_split(self, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("sample_split should not be called")

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {
        "video_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        "label": "happy",
    }
    response = await client.post("/promote/stage", json=payload)
    assert response.status_code == 422
    detail = response.json()
    assert detail["error"] == "invalid label"
    assert detail["correlation_id"]
    assert response.headers[promote_router.CORRELATION_ID_HEADER] == detail["correlation_id"]
    assert stub.rolled_back
    assert not stub.committed


@pytest.mark.asyncio
async def test_stage_videos_request_validation(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        def __init__(self) -> None:
            self.called = False

        async def stage_to_dataset_all(self, video_ids, *, label, dry_run=False):
            self.called = True
            return StageResult(
                promoted_ids=tuple(video_ids),
                skipped_ids=tuple(),
                failed_ids=tuple(),
                dry_run=dry_run,
            )

        async def sample_split(self, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("sample_split should not be called")

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {"video_ids": [], "label": "happy"}
    response = await client.post("/promote/stage", json=payload)
    assert response.status_code == 422
    assert stub.called is False
    assert promote_router.CORRELATION_ID_HEADER not in response.headers
    assert not stub.committed
    assert not stub.rolled_back


@pytest.mark.asyncio
async def test_sample_split_success(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        async def stage_to_dataset_all(self, *args, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("stage_to_dataset_all should not be called")

        async def sample_split(self, **kwargs):
            return SampleResult(
                run_id=kwargs["run_id"],
                target_split=kwargs["target_split"],
                copied_ids=(kwargs["run_id"],),
                skipped_ids=tuple(),
                failed_ids=tuple(),
                dry_run=kwargs.get("dry_run", False),
            )

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {
        "run_id": "313fad80-e652-4ec8-bc6b-248ccb89d96e",
        "target_split": "train",
        "sample_fraction": 0.5,
        "strategy": "balanced_random",
    }
    response = await client.post("/promote/sample", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["run_id"] == payload["run_id"]
    assert promote_router.CORRELATION_ID_HEADER in response.headers
    assert stub.committed
    assert not stub.rolled_back


@pytest.mark.asyncio
async def test_sample_split_service_validation_error(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        async def stage_to_dataset_all(self, *args, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("stage_to_dataset_all should not be called")

        async def sample_split(self, **kwargs):
            raise PromotionValidationError("bad request")

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    # Provide sample_fraction as string to exercise schema coercion
    payload = {
        "run_id": "313fad80-e652-4ec8-bc6b-248ccb89d96e",
        "target_split": "train",
        "sample_fraction": "0.50",
        "strategy": "balanced_random",
    }
    response = await client.post("/promote/sample", json=payload)
    assert response.status_code == 422
    detail = response.json()
    assert detail["error"] == "bad request"
    assert detail["correlation_id"]
    assert response.headers[promote_router.CORRELATION_ID_HEADER] == detail["correlation_id"]
    assert stub.rolled_back
    assert not stub.committed


@pytest.mark.asyncio
async def test_sample_split_request_validation(api_client):
    client, app = api_client

    class StubService(StubServiceBase):
        def __init__(self) -> None:
            self.called = False

        async def stage_to_dataset_all(self, *args, **kwargs):  # pragma: no cover - not used here
            raise AssertionError("stage_to_dataset_all should not be called")

        async def sample_split(self, **kwargs):
            self.called = True
            return SampleResult(
                run_id=kwargs["run_id"],
                target_split=kwargs["target_split"],
                copied_ids=(kwargs["run_id"],),
                skipped_ids=tuple(),
                failed_ids=tuple(),
                dry_run=kwargs.get("dry_run", False),
            )

    stub = StubService()
    app.dependency_overrides[deps.get_promote_service] = lambda: stub

    payload = {
        "run_id": "313fad80-e652-4ec8-bc6b-248ccb89d96e",
        "target_split": "train",
        "sample_fraction": 0.0,
        "strategy": "balanced_random",
    }
    response = await client.post("/promote/sample", json=payload)
    assert response.status_code == 422
    assert stub.called is False
    assert promote_router.CORRELATION_ID_HEADER not in response.headers
    assert not stub.committed
    assert not stub.rolled_back
