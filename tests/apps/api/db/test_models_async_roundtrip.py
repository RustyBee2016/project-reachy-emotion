from __future__ import annotations

import uuid
import shutil
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db import models
from apps.api.app.db.session import get_async_engine, get_async_sessionmaker
from tests.apps.api.db.test_migrations import _alembic_config


@pytest.mark.asyncio
async def test_async_roundtrip(tmp_path: Path) -> None:
    migrated_db = tmp_path / "migrated.db"
    db_path = tmp_path / "async.db"
    sync_url = f"sqlite:///{migrated_db}"
    cfg = _alembic_config(sync_url)
    command.upgrade(cfg, "head")
    shutil.copy2(migrated_db, db_path)

    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    # type: AsyncSession
    async with sessionmaker() as session:  
        video = models.Video(
            file_path="dataset_all/clip_async.mp4",
            split="dataset_all",
            label="sad",
            size_bytes=8192,
            sha256="e" * 64,
        )
        run = models.TrainingRun(
            strategy="balanced_random",
            train_fraction=0.6,
            test_fraction=0.4,
        )
        session.add_all([video, run])
        await session.flush()

        selection = models.TrainingSelection(
            run_id=run.run_id,
            video_id=video.video_id,
            target_split="train",
        )
        session.add(selection)
        await session.commit()

        rows = (
            await session.execute(select(models.TrainingSelection))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].video_id == video.video_id

    async_engine = get_async_engine(async_url)
    await async_engine.dispose()
    command.downgrade(cfg, "base")
