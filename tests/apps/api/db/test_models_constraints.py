from __future__ import annotations

import uuid
from pathlib import Path

import pytest
pytest.importorskip("alembic.command")
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.db import models
from tests.apps.api.db.test_migrations import _alembic_config


@pytest.fixture(name="engine")
def engine_fixture(tmp_path: Path):
    db_path = tmp_path / "models.db"
    url = f"sqlite:///{db_path}"
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    engine = create_engine(url, future=True)
    yield engine
    engine.dispose()
    command.downgrade(cfg, "base")


def test_video_split_label_policy(engine) -> None:
    with Session(engine) as session:
        valid_video = models.Video(
            file_path="dataset_all/clip1.mp4",
            split="dataset_all",
            label="happy",
            size_bytes=1048576,
            sha256="a" * 64,
        )
        session.add(valid_video)
        session.commit()

        invalid = models.Video(
            file_path="dataset_all/clip2.mp4",
            split="dataset_all",
            label=None,
            size_bytes=2048,
            sha256="b" * 64,
        )
        session.add(invalid)
        with pytest.raises(IntegrityError):
            session.commit()
            session.rollback()


def test_video_unique_hash_size(engine) -> None:
    with Session(engine) as session:
        video_a = models.Video(
            file_path="dataset_all/clip3.mp4",
            split="dataset_all",
            label="sad",
            size_bytes=4096,
            sha256="c" * 64,
        )
        session.add(video_a)
        session.commit()

        duplicate = models.Video(
            file_path="train/clip3.mp4",
            split="train",
            label="sad",
            size_bytes=4096,
            sha256="c" * 64,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
            session.rollback()


def test_training_selection_cascade(engine) -> None:
    with Session(engine) as session:
        video = models.Video(
            file_path="dataset_all/clip4.mp4",
            split="dataset_all",
            label="neutral",
            size_bytes=1024,
            sha256="d" * 64,
        )
        run = models.TrainingRun(
            strategy="balanced_random",
            train_fraction=0.7,
            test_fraction=0.3,
        )
        session.add_all([video, run])
        session.commit()

        selection = models.TrainingSelection(
            run_id=run.run_id,
            video_id=video.video_id,
            target_split="train",
        )
        session.add(selection)
        session.commit()

        session.delete(run)
        session.commit()

        remaining = session.execute(select(models.TrainingSelection)).scalars().all()
        assert not remaining
