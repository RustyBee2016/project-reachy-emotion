from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from apps.api.app import deps
from apps.api.app.db import models
from apps.api.app.db.session import get_async_engine, get_async_sessionmaker
from apps.api.app.main import create_app
from apps.api.app.settings import Settings
from tests.apps.api.db.test_migrations import _alembic_config


class _ManifestRecorder:
    def __init__(self) -> None:
        self.schedule_calls: list[tuple[str, str | None]] = []
        self.reset_calls: list[tuple[str, str | None]] = []

    def schedule_rebuild(self, *, reason: str, run_id: str | None) -> None:
        self.schedule_calls.append((reason, run_id))

    def reset(self, *, reason: str, run_id: str | None) -> None:
        self.reset_calls.append((reason, run_id))


def _write_file(root: Path, relative_path: str, content: bytes = b"data") -> None:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


@pytest_asyncio.fixture
async def promote_app(tmp_path: Path):
    db_path = tmp_path / "promote.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    manifests_root = tmp_path / "manifests"
    videos_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)

    manifest_backend = _ManifestRecorder()

    test_settings = Settings(
        api_root_path="/api/media",
        ui_origins=["http://testserver"],
        database_url=async_url,
        videos_root=str(videos_root),
        manifests_root=str(manifests_root),
        enable_cors=False,
    )

    app = create_app()

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_settings_dep] = lambda: test_settings
    app.dependency_overrides[deps.get_manifest_backend] = lambda: manifest_backend

    transport = ASGITransport(app=app, root_path="/api/media")
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield {
            "client": client,
            "sessionmaker": sessionmaker,
            "videos_root": videos_root,
            "manifest_backend": manifest_backend,
            "cfg": cfg,
            "async_url": async_url,
            "app": app,
        }

    app.dependency_overrides.clear()
    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


async def _insert_video(
    sessionmaker,
    *,
    file_path: str,
    split: str,
    label: str | None,
    size_bytes: int,
    sha256: str,
) -> str:
    async with sessionmaker() as session:
        video = models.Video(
            file_path=file_path,
            split=split,
            label=label,
            size_bytes=size_bytes,
            sha256=sha256,
        )
        session.add(video)
        await session.commit()
        return video.video_id


@pytest.mark.asyncio
async def test_stage_endpoint_is_deprecated(promote_app):
    env = promote_app
    client: AsyncClient = env["client"]
    sessionmaker = env["sessionmaker"]
    videos_root: Path = env["videos_root"]
    backend: _ManifestRecorder = env["manifest_backend"]

    file_name = "clip_stage.mp4"
    relative_path = f"temp/{file_name}"
    _write_file(videos_root, relative_path)

    video_id = await _insert_video(
        sessionmaker,
        file_path=relative_path,
        split="temp",
        label=None,
        size_bytes=1024,
        sha256="a" * 64,
    )

    response = await client.post(
        "/api/v1/promote/stage",
        json={"video_ids": [str(video_id)], "label": "happy"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "Deprecated endpoint" in body["detail"]["error"]

    async with sessionmaker() as session:
        refreshed = await session.get(models.Video, video_id)
        assert refreshed is not None
        assert refreshed.split == "temp"
        assert refreshed.label is None
        assert refreshed.file_path == relative_path

    assert (videos_root / "temp" / file_name).exists()
    assert not (videos_root / "train" / file_name).exists()

    assert backend.schedule_calls == []


@pytest.mark.asyncio
async def test_stage_endpoint_dry_run_is_deprecated(promote_app):
    env = promote_app
    client: AsyncClient = env["client"]
    sessionmaker = env["sessionmaker"]
    videos_root: Path = env["videos_root"]
    backend: _ManifestRecorder = env["manifest_backend"]

    file_name = "clip_stage_dry.mp4"
    relative_path = f"temp/{file_name}"
    _write_file(videos_root, relative_path)

    video_id = await _insert_video(
        sessionmaker,
        file_path=relative_path,
        split="temp",
        label=None,
        size_bytes=2048,
        sha256="b" * 64,
    )

    response = await client.post(
        "/api/v1/promote/stage",
        json={"video_ids": [str(video_id)], "label": "sad", "dry_run": True},
    )
    assert response.status_code == 422
    body = response.json()
    assert "Deprecated endpoint" in body["detail"]["error"]

    async with sessionmaker() as session:
        refreshed = await session.get(models.Video, video_id)
        assert refreshed is not None
        assert refreshed.split == "temp"
        assert refreshed.label is None
        assert refreshed.file_path == relative_path

    assert (videos_root / "temp" / file_name).exists()
    assert not (videos_root / "train" / file_name).exists()

    assert backend.schedule_calls == []


@pytest.mark.asyncio
async def test_sample_endpoint_is_deprecated(promote_app):
    env = promote_app
    client: AsyncClient = env["client"]
    sessionmaker = env["sessionmaker"]
    videos_root: Path = env["videos_root"]
    backend: _ManifestRecorder = env["manifest_backend"]

    file_name = "clip_sample.mp4"
    relative_path = f"train/{file_name}"
    _write_file(videos_root, relative_path)

    video_id = await _insert_video(
        sessionmaker,
        file_path=relative_path,
        split="train",
        label="happy",
        size_bytes=4096,
        sha256="c" * 64,
    )

    run_id = "run_0001"
    response = await client.post(
        "/api/v1/promote/sample",
        json={
            "run_id": run_id,
            "target_split": "train",
            "sample_fraction": 1.0,
            "strategy": "balanced_random",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert "Deprecated endpoint" in body["detail"]["error"]

    async with sessionmaker() as session:
        refreshed = await session.get(models.Video, video_id)
        assert refreshed is not None
        assert refreshed.split == "train"
        assert refreshed.label == "happy"
        assert refreshed.file_path == relative_path

        selections = (
            await session.execute(
                select(models.TrainingSelection)
            )
        ).scalars().all()
        assert len(selections) == 0

    assert (videos_root / "train" / file_name).exists()
    assert not (videos_root / "train" / run_id / file_name).exists()

    assert backend.schedule_calls == []


@pytest.mark.asyncio
async def test_sample_endpoint_dry_run_is_deprecated(promote_app):
    env = promote_app
    client: AsyncClient = env["client"]
    sessionmaker = env["sessionmaker"]
    videos_root: Path = env["videos_root"]
    backend: _ManifestRecorder = env["manifest_backend"]

    file_name = "clip_sample_dry.mp4"
    relative_path = f"train/{file_name}"
    _write_file(videos_root, relative_path)

    video_id = await _insert_video(
        sessionmaker,
        file_path=relative_path,
        split="train",
        label="sad",
        size_bytes=8192,
        sha256="d" * 64,
    )

    run_id = "run_0001"
    response = await client.post(
        "/api/v1/promote/sample",
        json={
            "run_id": run_id,
            "target_split": "test",
            "sample_fraction": 1.0,
            "strategy": "balanced_random",
            "dry_run": True,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert "Deprecated endpoint" in body["detail"]["error"]

    async with sessionmaker() as session:
        refreshed = await session.get(models.Video, video_id)
        assert refreshed is not None
        assert refreshed.split == "train"
        assert refreshed.label == "sad"
        assert refreshed.file_path == relative_path

        selections = (
            await session.execute(
                select(models.TrainingSelection)
            )
        ).scalars().all()
        assert selections == []

    assert (videos_root / "train" / file_name).exists()
    assert not (videos_root / "test" / run_id / file_name).exists()

    assert backend.schedule_calls == []


@pytest.mark.asyncio
async def test_reset_manifest_endpoint_records_reason(promote_app):
    env = promote_app
    client: AsyncClient = env["client"]
    backend: _ManifestRecorder = env["manifest_backend"]

    run_id = "run_0001"
    response = await client.post(
        "/api/v1/promote/reset-manifest",
        json={"reason": "manual_reset", "run_id": run_id},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["reason"] == "manual_reset"
    assert body["run_id"] == run_id

    assert backend.reset_calls == [("manual_reset", run_id)]
