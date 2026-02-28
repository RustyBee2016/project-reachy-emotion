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
            file_path="train/clip1.mp4",
            split="train",
            label="happy",
            size_bytes=1048576,
            sha256="a" * 64,
        )
        session.add(valid_video)
        session.commit()

        invalid = models.Video(
            file_path="train/clip2.mp4",
            split="train",
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
            file_path="train/clip3.mp4",
            split="train",
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
            file_path="train/clip4.mp4",
            split="train",
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


# ============================================================================
# R2: RunLink roundtrip
# ============================================================================


def test_run_link_roundtrip(engine) -> None:
    """RunLink can be inserted and read back with all columns."""
    with Session(engine) as session:
        link = models.RunLink(
            mlflow_run_id="run_abc123",
            dataset_hash="e" * 64,
            snapshot_ref="@snap-2026-02-27",
        )
        session.add(link)
        session.commit()

        result = session.execute(
            select(models.RunLink).where(
                models.RunLink.mlflow_run_id == "run_abc123"
            )
        ).scalar_one()
        assert result.dataset_hash == "e" * 64
        assert result.snapshot_ref == "@snap-2026-02-27"
        assert result.created_at is not None


# ============================================================================
# R1: LabelEvent action constraint
# ============================================================================


def test_label_event_action_constraint(engine) -> None:
    """label_event.action must be one of the five allowed values."""
    with Session(engine) as session:
        valid = models.LabelEvent(
            label="happy",
            action="label_only",
        )
        session.add(valid)
        session.commit()
        assert valid.event_id is not None

    with Session(engine) as session:
        invalid = models.LabelEvent(
            label="sad",
            action="invalid_action",
        )
        session.add(invalid)
        with pytest.raises(IntegrityError):
            session.commit()


# ============================================================================
# R8: DeploymentLog stage constraint
# ============================================================================


def test_deployment_log_stage_constraint(engine) -> None:
    """deployment_log.target_stage must be shadow|canary|rollout."""
    with Session(engine) as session:
        valid = models.DeploymentLog(
            engine_path="/engines/emotionnet_v1.engine",
            target_stage="shadow",
            status="pending",
        )
        session.add(valid)
        session.commit()
        assert valid.id is not None

    with Session(engine) as session:
        invalid = models.DeploymentLog(
            engine_path="/engines/bad.engine",
            target_stage="production",
            status="pending",
        )
        session.add(invalid)
        with pytest.raises(IntegrityError):
            session.commit()


# ============================================================================
# R8: ReconcileReport trigger_type constraint
# ============================================================================


def test_reconcile_report_trigger_constraint(engine) -> None:
    """reconcile_report.trigger_type must be scheduled|manual|webhook."""
    with Session(engine) as session:
        valid = models.ReconcileReport(
            trigger_type="scheduled",
            orphan_count=0,
            missing_count=0,
            mismatch_count=0,
        )
        session.add(valid)
        session.commit()
        assert valid.id is not None

    with Session(engine) as session:
        invalid = models.ReconcileReport(
            trigger_type="cron",
            orphan_count=0,
            missing_count=0,
            mismatch_count=0,
        )
        session.add(invalid)
        with pytest.raises(IntegrityError):
            session.commit()
