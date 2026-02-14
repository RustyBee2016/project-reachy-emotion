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
    PromotionConflictError,
    PromotionError,
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
async def test_stage_to_dataset_all_promotes_and_logs(tmp_path: Path) -> None:
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

        _write_file(videos_root / "temp" / "clip_stage.mp4")

        service, backend = _make_service(session, videos_root)
        result = await service.stage_to_dataset_all([str(video.video_id)], label="happy")
        await session.commit()

        refreshed = await session.get(models.Video, video.video_id)
        assert refreshed is not None
        assert refreshed.split == "dataset_all"
        assert refreshed.label == "happy"
        assert result.promoted_ids == (str(video.video_id),)
        assert result.skipped_ids == ()
        assert result.failed_ids == ()

        assert (videos_root / "dataset_all" / "clip_stage.mp4").exists()

        assert backend.schedule_calls == [("stage_to_dataset_all", None)]

        promotions = (
            await session.execute(
                select(models.PromotionLog).where(models.PromotionLog.video_id == video.video_id)
            )
        ).scalars().all()
        assert len(promotions) == 1
        assert promotions[0].from_split == "temp"
        assert promotions[0].to_split == "dataset_all"

        assert get_metric_sample(
            "promotion_operations_total",
            {"action": "stage", "outcome": "success"},
        ) == 1.0
        assert get_metric_sample(
            "promotion_operation_duration_seconds_count",
            {"action": "stage"},
        ) == 1.0

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_stage_filesystem_failure_increments_metrics(tmp_path: Path) -> None:
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
        with pytest.raises(PromotionError):
            await service.stage_to_dataset_all([str(video.video_id)], label="happy")

        assert get_metric_sample(
            "promotion_operations_total",
            {"action": "stage", "outcome": "error"},
        ) == 1.0
        assert get_metric_sample(
            "promotion_filesystem_failures_total",
            {"action": "stage"},
        ) == 1.0
        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_stage_skips_non_temp_and_duplicates(tmp_path: Path) -> None:
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
            file_path="dataset_all/clip_existing.mp4",
            split="dataset_all",
            label="happy",
            size_bytes=2048,
            sha256="d" * 64,
        )
        session.add_all([temp_video, dataset_video])
        await session.flush()

        _write_file(videos_root / "temp" / "clip_temp.mp4", b"temp")
        _write_file(videos_root / "dataset_all" / "clip_existing.mp4", b"dataset")

        service, backend = _make_service(session, videos_root)
        result = await service.stage_to_dataset_all(
            [str(temp_video.video_id), str(dataset_video.video_id), str(temp_video.video_id)],
            label="sad",
        )
        await session.commit()

        assert result.promoted_ids == (str(temp_video.video_id),)
        assert str(dataset_video.video_id) in result.skipped_ids
        assert result.failed_ids == ()

        refreshed_temp = await session.get(models.Video, temp_video.video_id)
        assert refreshed_temp is not None
        refreshed_dataset = await session.get(models.Video, dataset_video.video_id)
        assert refreshed_dataset is not None
        assert refreshed_temp.split == "dataset_all"
        assert refreshed_temp.label == "sad"
        assert refreshed_dataset.split == "dataset_all"
        assert refreshed_dataset.label == "happy"

        assert (videos_root / "dataset_all" / "clip_temp.mp4").exists()
        assert (videos_root / "dataset_all" / "clip_existing.mp4").exists()

        assert backend.schedule_calls == [("stage_to_dataset_all", None)]

        logs = (
            await session.execute(select(models.PromotionLog))
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].video_id == temp_video.video_id

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_stage_rejects_invalid_uuid(tmp_path: Path) -> None:
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
            await service.stage_to_dataset_all(["not-a-uuid"], label="happy")

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_stage_skips_when_no_eligible_videos(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_no_eligible.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        video = models.Video(
            file_path="dataset_all/clip_exists.mp4",
            split="dataset_all",
            label="happy",
            size_bytes=1024,
            sha256="e" * 64,
        )
        session.add(video)
        await session.flush()

        _write_file(videos_root / "dataset_all" / "clip_exists.mp4")

        service, backend = _make_service(session, videos_root)
        result = await service.stage_to_dataset_all([str(video.video_id)], label="happy")
        await session.commit()

        assert result.promoted_ids == ()
        assert result.skipped_ids == (str(video.video_id),)
        assert result.failed_ids == ()

        assert backend.schedule_calls == []

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


@pytest.mark.asyncio
async def test_stage_returns_skipped_for_missing_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_conflict_missing.db"
    sync_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    videos_root = tmp_path / "videos"
    async with sessionmaker() as session:
        service, backend = _make_service(session, videos_root)
        result = await service.stage_to_dataset_all([str(uuid.uuid4())], label="happy")
        assert result.promoted_ids == ()
        assert len(result.skipped_ids) == 1
        assert result.failed_ids == ()

        assert get_metric_sample(
            "promotion_operations_total",
            {"action": "stage", "outcome": "success"},
        ) == 1.0

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
        clips = [
            models.Video(
                file_path=f"dataset_all/clip_{idx}.mp4",
                split="dataset_all",
                label="happy",
                size_bytes=1000 + idx,
                sha256=f"{idx + 10:064x}",
            )
            for idx in range(3)
        ]
        session.add_all(clips)
        await session.flush()

        for idx in range(3):
            _write_file(videos_root / "dataset_all" / f"clip_{idx}.mp4", bytes([idx]))

        run_id = uuid.uuid4()
        service, backend = _make_service(session, videos_root)
        result = await service.sample_split(
            run_id=str(run_id),
            target_split="train",
            sample_fraction=2.0,
            strategy="balanced_random",
        )
        await session.commit()

        selections = (
            await session.execute(select(models.TrainingSelection))
        ).scalars().all()
        assert len(selections) == 3
        assert set(result.copied_ids) == {str(video.video_id) for video in clips}
        assert result.failed_ids == ()

        for video in clips:
            assert (videos_root / "dataset_all" / Path(video.file_path).name).exists()
        for video in clips:
            assert (videos_root / "train" / str(run_id) / Path(video.file_path).name).exists()

        assert get_metric_sample(
            "promotion_operations_total",
            {"action": "sample", "outcome": "success"},
        ) == 1.0
        assert get_metric_sample(
            "promotion_operation_duration_seconds_count",
            {"action": "sample"},
        ) == 1.0

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
        video = models.Video(
            file_path="dataset_all/clip_test.mp4",
            split="dataset_all",
            label="sad",
            size_bytes=5555,
            sha256="f" * 64,
        )
        session.add(video)
        await session.flush()

        _write_file(videos_root / "dataset_all" / "clip_test.mp4")

        run_id = uuid.uuid4()
        service, backend = _make_service(session, videos_root)
        result = await service.sample_split(
            run_id=str(run_id),
            target_split="test",
            sample_fraction=1.0,
            strategy="balanced_random",
        )
        await session.commit()

        refreshed = await session.get(models.Video, video.video_id)
        assert refreshed is not None
        assert refreshed.split == "test"
        assert refreshed.label is None

        selection = await session.get(
            models.TrainingSelection,
            {
                "run_id": str(run_id),
                "video_id": str(video.video_id),
                "target_split": "test",
            },
        )
        assert selection is not None

        assert result.copied_ids == (str(video.video_id),)
        assert result.failed_ids == ()

        assert (videos_root / "dataset_all" / "clip_test.mp4").exists()
        assert (videos_root / "test" / str(run_id) / "clip_test.mp4").exists()

        assert backend.schedule_calls == [("sample_split", str(run_id))]

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")


def test_reset_manifest_invokes_backend() -> None:
    backend = _StubManifestBackend()
    service = PromoteService(cast(AsyncSession, object()), manifest_backend=backend)

    service.reset_manifest(reason="manual_reset", run_id="abc123")
    assert backend.reset_calls == [("manual_reset", "abc123")]


@pytest.mark.asyncio
async def test_stage_requires_label(tmp_path: Path) -> None:
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
            await service.stage_to_dataset_all([str(video.video_id)], label=None)

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
        videos = []
        for idx, label in enumerate(["happy", "sad", "happy", "sad"], start=1):
            video = models.Video(
                file_path=f"dataset_all/clip_{idx}.mp4",
                split="dataset_all",
                label=label,
                size_bytes=10_000 + idx,
                sha256=f"{idx:064x}",
            )
            session.add(video)
            videos.append(video)
        await session.flush()

        for idx in range(1, 5):
            _write_file(videos_root / "dataset_all" / f"clip_{idx}.mp4", bytes([idx]))

        run_id = uuid.uuid4()
        service, backend = _make_service(session, videos_root)
        result = await service.sample_split(
            run_id=str(run_id),
            target_split="train",
            sample_fraction=0.5,
            strategy="balanced_random",
            seed=42,
        )
        await session.commit()

        selections = (
            await session.execute(select(models.TrainingSelection))
        ).scalars().all()
        assert selections
        assert all(selection.target_split == "train" for selection in selections)
        assert all(selection.run_id == str(run_id) for selection in selections)

        promoted_videos = (
            await session.execute(
                select(models.Video).where(models.Video.split == "train")
            )
        ).scalars().all()
        assert promoted_videos
        assert len(promoted_videos) == len(selections)
        assert all(video.label in {"happy", "sad"} for video in promoted_videos)

        logs = (
            await session.execute(select(models.PromotionLog))
        ).scalars().all()
        assert len(logs) == len(selections)
        assert all(log.to_split == "train" for log in logs)

        assert set(result.copied_ids) == {str(selection.video_id) for selection in selections}
        assert result.failed_ids == ()

        for selection in selections:
            clip_name = Path(next(v.file_path for v in videos if v.video_id == selection.video_id)).name
            assert (videos_root / "train" / str(run_id) / clip_name).exists()

        assert backend.schedule_calls == [("sample_split", str(run_id))]

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")
