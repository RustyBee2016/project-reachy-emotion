from __future__ import annotations

import uuid
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db import models
from apps.api.app.db.session import get_async_engine, get_async_sessionmaker
from apps.api.app.fs import FileMover
from apps.api.app.metrics import get_metric_sample, reset_metrics
from apps.api.app.services import (
    PromoteService,
    PromotionValidationError,
)
from tests.apps.api.db.test_migrations import _alembic_config

class _StubManifestBackend:
    def __init__(self) -> None:
        self.schedule_calls: list[tuple[str, str | None]] = []
        self.reset_calls: list[tuple[str, str | None]] = []

    def schedule_rebuild(self, *, reason: str, run_id: str | None) -> None:
        self.schedule_calls.append((reason, run_id))

    def reset(self, *, reason: str, run_id: str | None) -> None:
        self.reset_calls.append((reason, run_id))


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    reset_metrics()


def _write_file(path: Path, content: bytes = b"data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_service(session, root: Path) -> tuple[PromoteService, _StubManifestBackend]:
    root.mkdir(parents=True, exist_ok=True)
    manifest_backend = _StubManifestBackend()
    service = PromoteService(session, file_mover=FileMover(root), manifest_backend=manifest_backend)
    return service, manifest_backend


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_promotes_and_logs(tmp_path: Path) -> None:
    db_path = tmp_path / "stage.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        video = models.Video(
            file_path="temp/clip_stage.mp4",
            split="temp",
            label=None,
            size_bytes=4096,
            sha256="a" * 64,
        )
        session.add(video)
        await session.flush()

        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train([str(video.video_id)], label="happy")

        refreshed = await session.get(models.Video, video.video_id)
        assert refreshed is not None
        assert refreshed.split == "temp"
        assert refreshed.label is None
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_filesystem_failure_increments_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_fs_failure.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        video = models.Video(
            file_path="temp/missing.mp4",
            split="temp",
            label=None,
            size_bytes=512,
            sha256="f" * 64,
        )
        session.add(video)
        await session.flush()

        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train([str(video.video_id)], label="happy")

        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_skips_non_temp_and_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_duplicates.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        temp_video = models.Video(
            file_path="temp/clip_temp.mp4",
            split="temp",
            label=None,
            size_bytes=1024,
            sha256="c" * 64,
        )
        dataset_video = models.Video(
            file_path="train/clip_existing.mp4",
            split="train",
            label="happy",
            size_bytes=2048,
            sha256="d" * 64,
        )
        session.add_all([temp_video, dataset_video])
        await session.flush()

        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train(
                [str(temp_video.video_id), str(dataset_video.video_id), str(temp_video.video_id)],
                label="sad",
            )

        refreshed_temp = await session.get(models.Video, temp_video.video_id)
        assert refreshed_temp is not None
        refreshed_dataset = await session.get(models.Video, dataset_video.video_id)
        assert refreshed_dataset is not None
        assert refreshed_temp.split == "temp"
        assert refreshed_temp.label is None
        assert refreshed_dataset.split == "train"
        assert refreshed_dataset.label == "happy"
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_rejects_invalid_uuid(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_invalid_uuid.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError):
            await service.stage_to_train(["not-a-uuid"], label="happy")

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_skips_when_no_eligible_videos(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_no_eligible.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        video = models.Video(
            file_path="train/clip_exists.mp4",
            split="train",
            label="happy",
            size_bytes=1024,
            sha256="e" * 64,
        )
        session.add(video)
        await session.flush()

        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train([str(video.video_id)], label="happy")
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_returns_skipped_for_missing_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_conflict_missing.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train([str(uuid.uuid4())], label="happy")
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_sample_fraction_greater_than_one_selects_all(tmp_path: Path) -> None:
    db_path = tmp_path / "sample_fraction_gt_one.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        run_id = "run_0001"
        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.sample_split(
                run_id=run_id,
                target_split="train",
                sample_fraction=2.0,
                strategy="balanced_random",
            )
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_sample_into_test_clears_labels(tmp_path: Path) -> None:
    db_path = tmp_path / "sample_test_split.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        run_id = "run_0001"
        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.sample_split(
                run_id=run_id,
                target_split="test",
                sample_fraction=1.0,
                strategy="balanced_random",
            )
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


def test_reset_manifest_invokes_backend() -> None:
    backend = _StubManifestBackend()
    service = PromoteService(cast(AsyncSession, object()), manifest_backend=backend)

    service.reset_manifest(reason="manual_reset", run_id="run_0001")
    assert backend.reset_calls == [("manual_reset", "run_0001")]


@pytest.mark.asyncio
async def test_legacy_stage_endpoint_deprecated_requires_label(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_label.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    async with sessionmaker() as session:
        video = models.Video(
            file_path="temp/clip_missing_label.mp4",
            split="temp",
            label=None,
            size_bytes=2048,
            sha256="b" * 64,
        )
        session.add(video)
        await session.flush()

        backend = _StubManifestBackend()
        service = PromoteService(session, manifest_backend=backend)
        with pytest.raises(PromotionValidationError):
            await service.stage_to_train([str(video.video_id)], label=None)

        assert get_metric_sample(
            "promotion_operations_total",
            {"action": "stage", "outcome": "error"},
        ) == 1.0

        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_sample_split_creates_training_selection(tmp_path: Path) -> None:
    db_path = tmp_path / "sample.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        run_id = "run_0001"
        service, backend = _make_service(session, videos_root)
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.sample_split(
                run_id=run_id,
                target_split="train",
                sample_fraction=0.5,
                strategy="balanced_random",
                seed=42,
            )

        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")
