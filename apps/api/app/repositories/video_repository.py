"""Database-facing helpers for promotion workflows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Collection, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import models


@dataclass(frozen=True)
class VideoRecord:
    """Lightweight representation of a video row."""

    video_id: str  # UUID stored as string in database
    split: str
    label: str | None
    file_path: str
    sha256: str
    size_bytes: int


@dataclass
class StageMutation:
    """Requested transition from temp to a labeled target split for a video."""

    video_id: str  # UUID stored as string
    from_split: str
    to_split: str
    intended_label: str
    actor: str
    new_file_path: str


@dataclass
class SamplingMutation:
    """Requested transition for legacy train/test sampling compatibility."""

    video_id: str  # UUID stored as string
    from_split: str
    to_split: str
    current_label: str | None
    actor: str
    new_file_path: str


class VideoRepository:
    """Async persistence helpers for promotion operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_videos_for_stage(self, video_ids: Sequence[str]) -> list[VideoRecord]:
        """Return video metadata for ids targeted for staging."""

        if not video_ids:
            return []

        stmt = sa.select(models.Video).where(models.Video.video_id.in_(video_ids))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_record(row) for row in rows]

    async def fetch_dataset_all_for_sampling(
        self,
        *,
        exclude_ids: Collection[str] | None = None,
    ) -> list[VideoRecord]:
        """Legacy compatibility hook retained for deprecated sample endpoint.

        The runtime promotion flow no longer stages clips in dataset_all.
        Sampling from dataset_all has been removed in favor of run-scoped
        frame dataset preparation from train/<label> sources.
        """

        _ = exclude_ids
        return []

    async def get_existing_selection_ids(
        self,
        *,
        run_id: str,
        target_split: str,
    ) -> set[str]:
        """Return the set of video ids already selected for the given run/split."""

        training_selection_table = models.TrainingSelection.__table__
        stmt = sa.select(training_selection_table.c.video_id).where(
            training_selection_table.c.run_id == run_id,
            training_selection_table.c.target_split == target_split,
        )
        existing_ids = (await self._session.execute(stmt)).scalars().all()
        return set(existing_ids)

    async def persist_stage_results(self, mutations: Sequence[StageMutation]) -> None:
        """Apply split/label updates and log promotion mutations."""

        if not mutations:
            return

        logs: list[models.PromotionLog] = []
        for mutation in mutations:
            await self._session.execute(
                sa.update(models.Video)
                .where(models.Video.video_id == mutation.video_id)
                .values(
                    split=mutation.to_split,
                    label=mutation.intended_label,
                    file_path=mutation.new_file_path,
                )
            )
            logs.append(
                models.PromotionLog(
                    video_id=mutation.video_id,
                    from_split=mutation.from_split,
                    to_split=mutation.to_split,
                    intended_label=mutation.intended_label,
                    actor=mutation.actor,
                    success=True,
                )
            )

        if logs:
            self._session.add_all(logs)
        await self._session.flush()

    async def persist_sampling_results(
        self,
        *,
        run_id: str,
        strategy: str,
        target_split: str,
        sample_fraction: float,
        selections: Sequence[SamplingMutation],
    ) -> None:
        """Persist legacy selection outcomes and associated promotion logs."""

        if not selections:
            return

        run = await self._session.get(models.TrainingRun, run_id)
        if run is None:
            run = models.TrainingRun(
                run_id=run_id,
                strategy=strategy,
                train_fraction=sample_fraction if target_split == "train" else 0.0,
                test_fraction=sample_fraction if target_split == "test" else 0.0,
            )
            self._session.add(run)
            await self._session.flush()
        else:
            run.strategy = strategy
            if target_split == "train":
                run.train_fraction = sample_fraction
            else:
                run.test_fraction = sample_fraction

        existing_ids = await self.get_existing_selection_ids(
            run_id=run_id, target_split=target_split
        )

        logs: list[models.PromotionLog] = []
        selections_models: list[models.TrainingSelection] = []

        for mutation in selections:
            if mutation.video_id in existing_ids:
                continue

            new_label = mutation.current_label if target_split != "test" else None
            await self._session.execute(
                sa.update(models.Video)
                .where(models.Video.video_id == mutation.video_id)
                .values(
                    split=mutation.to_split,
                    label=new_label,
                    file_path=mutation.new_file_path,
                )
            )

            selections_models.append(
                models.TrainingSelection(
                    run_id=run_id,
                    video_id=mutation.video_id,
                    target_split=target_split,
                )
            )
            logs.append(
                models.PromotionLog(
                    video_id=mutation.video_id,
                    from_split=mutation.from_split,
                    to_split=mutation.to_split,
                    intended_label=mutation.current_label,
                    actor=mutation.actor,
                    success=True,
                )
            )

        if selections_models:
            self._session.add_all(selections_models)
        if logs:
            self._session.add_all(logs)

        await self._session.flush()

    @staticmethod
    def _to_record(row: models.Video) -> VideoRecord:
        def _normalize(value):
            if value is None:
                return None
            return value.value if hasattr(value, "value") else str(value)

        return VideoRecord(
            video_id=row.video_id,
            split=_normalize(row.split) or "",
            label=_normalize(row.label),
            file_path=row.file_path,
            sha256=row.sha256,
            size_bytes=row.size_bytes,
        )
