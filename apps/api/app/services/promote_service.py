"""Promotion service for dataset staging and sampling orchestration."""

from __future__ import annotations

import logging
import math
import random
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.enums import EmotionEnum, SelectionTargetEnum
from ..fs import FileMover, FileMoverError
from ..manifest import ManifestBackend, get_default_backend
from ..metrics import (
    PROMOTION_FILESYSTEM_FAILURES,
    PROMOTION_OPERATION_COUNTER,
    PROMOTION_OPERATION_DURATION,
)
from ..repositories import SamplingMutation, StageMutation, VideoRecord, VideoRepository


class PromotionError(RuntimeError):
    """Raised when promotion or sampling cannot be completed."""


class PromotionValidationError(PromotionError):
    """Raised when user-provided inputs fail validation."""


class PromotionConflictError(PromotionError):
    """Raised when the requested operation violates current state."""


@dataclass(slots=True)
class StageResult:
    """Outcome summary when staging clips into dataset_all."""

    promoted_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool = False


@dataclass(slots=True)
class SampleResult:
    """Outcome summary when sampling clips into train/test splits."""

    run_id: str
    target_split: str
    copied_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool = False


_VALID_LABELS = frozenset(str(label) for label in EmotionEnum.enums)
_VALID_TARGET_SPLITS = frozenset(str(split) for split in SelectionTargetEnum.enums)


class PromoteService:
    """Core promotion orchestration between filesystem and database."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: VideoRepository | None = None,
        file_mover: FileMover | None = None,
        manifest_backend: ManifestBackend | None = None,
        actor: str = "system",
        logger: logging.Logger | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or VideoRepository(session)
        self._file_mover = file_mover or FileMover(Path("."))
        self._actor = actor
        self._logger = logger or logging.getLogger(__name__)
        self._correlation_id = correlation_id or str(uuid.uuid4())
        self._manifest = manifest_backend or get_default_backend(self._logger)

    @asynccontextmanager
    async def _track_operation(self, action: str):
        start = perf_counter()
        try:
            yield
        except PromotionError:
            PROMOTION_OPERATION_COUNTER.labels(action=action, outcome="error").inc()
            raise
        except Exception:
            PROMOTION_OPERATION_COUNTER.labels(action=action, outcome="exception").inc()
            raise
        else:
            PROMOTION_OPERATION_COUNTER.labels(action=action, outcome="success").inc()
        finally:
            duration = perf_counter() - start
            PROMOTION_OPERATION_DURATION.labels(action=action).observe(duration)

    def set_correlation_id(self, correlation_id: str) -> None:
        """Update the correlation identifier used for logging and metrics."""

        self._correlation_id = correlation_id

    async def commit(self) -> None:
        """Commit the underlying database session."""

        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the underlying database session."""

        await self._session.rollback()

    def reset_manifest(self, *, reason: str, run_id: str | None = None) -> None:
        """Invoke the manifest backend reset hook."""

        self._manifest.reset(reason=reason, run_id=run_id)

    async def stage_to_dataset_all(
        self,
        video_ids: Iterable[str],
        *,
        label: str | None,
        dry_run: bool = False,
    ) -> StageResult:
        """Validate and move labelled clips from temp to dataset_all."""

        action = "stage"
        async with self._track_operation(action):
            parsed_ids = self._parse_video_ids(video_ids)
            normalized_label = self._normalize_label(label)

            records = await self._repository.fetch_videos_for_stage(parsed_ids)
            found_map = {record.video_id: record for record in records}

            missing_ids = [vid for vid in parsed_ids if vid not in found_map]
            skipped_ids: list[str] = [str(video_id) for video_id in missing_ids]
            failed_ids: list[str] = []

            mutations: list[StageMutation] = []
            for record in records:
                if record.split != "temp":
                    skipped_ids.append(str(record.video_id))
                    continue

                mutations.append(
                    StageMutation(
                        video_id=record.video_id,
                        from_split=record.split,
                        to_split="dataset_all",
                        intended_label=normalized_label,
                        actor=self._actor,
                        new_file_path=record.file_path,
                    )
                )

            if not mutations and not skipped_ids:
                raise PromotionConflictError("No videos eligible for staging.")

            promoted_ids: list[str] = []
            if mutations:
                if self._file_mover is None:
                    raise PromotionError("File mover is not configured for staging operations.")

                if dry_run:
                    try:
                        for mutation in mutations:
                            transition = self._file_mover.plan_stage_to_dataset_all(
                                video_id=mutation.video_id,
                                file_path=found_map[mutation.video_id].file_path,
                            )
                            mutation.new_file_path = str(transition.destination)
                    except FileMoverError as exc:
                        self._logger.error(
                            "stage_to_dataset_all_plan_error",
                            extra={
                                "error": str(exc),
                                "correlation_id": self._correlation_id,
                            },
                        )
                        raise PromotionError(str(exc)) from exc
                else:
                    file_transitions = []
                    try:
                        for mutation in mutations:
                            transition = self._file_mover.stage_to_dataset_all(
                                video_id=mutation.video_id,
                                file_path=found_map[mutation.video_id].file_path,
                            )
                            mutation.new_file_path = str(transition.destination)
                            file_transitions.append(transition)
                    except FileMoverError as exc:
                        self._file_mover.rollback(file_transitions)
                        await self._session.rollback()
                        PROMOTION_FILESYSTEM_FAILURES.labels(action=action).inc()
                        self._logger.error(
                            "stage_to_dataset_all_fs_error",
                            extra={
                                "error": str(exc),
                                "correlation_id": self._correlation_id,
                            },
                        )
                        raise PromotionError(str(exc)) from exc

                    await self._repository.persist_stage_results(mutations)
                    self._manifest.schedule_rebuild(reason="stage_to_dataset_all", run_id=None)

                promoted_ids = [str(mutation.video_id) for mutation in mutations]

            self._logger.info(
                "stage_to_dataset_all",
                extra={
                    "promoted_count": len(promoted_ids),
                    "skipped_count": len(skipped_ids),
                    "failed_count": len(failed_ids),
                    "label": normalized_label,
                    "dry_run": dry_run,
                    "correlation_id": self._correlation_id,
                },
            )

            return StageResult(
                promoted_ids=tuple(promoted_ids),
                skipped_ids=tuple(skipped_ids),
                failed_ids=tuple(failed_ids),
                dry_run=dry_run,
            )

    async def sample_split(
        self,
        *,
        run_id: str,
        target_split: str,
        sample_fraction: float,
        strategy: str,
        seed: int | None = None,
        dry_run: bool = False,
    ) -> SampleResult:
        """Select randomized clips from dataset_all into train/test splits."""

        action = "sample"
        async with self._track_operation(action):
            run_uuid = self._parse_uuid(run_id, "run_id")
            normalized_target = self._normalize_target_split(target_split)
            fraction = self._normalize_fraction(sample_fraction)
            self._validate_strategy(strategy)

            existing_ids = await self._repository.get_existing_selection_ids(
                run_id=run_uuid,
                target_split=normalized_target,
            )
            candidates = await self._repository.fetch_dataset_all_for_sampling(exclude_ids=existing_ids)

            if not candidates:
                self._logger.info(
                    "sample_split_no_candidates",
                    extra={
                        "run_id": str(run_uuid),
                        "target_split": normalized_target,
                        "skipped_count": len(existing_ids),
                        "correlation_id": self._correlation_id,
                    },
                )
                return SampleResult(
                    run_id=str(run_uuid),
                    target_split=normalized_target,
                    copied_ids=tuple(),
                    skipped_ids=tuple(str(video_id) for video_id in existing_ids),
                    failed_ids=tuple(),
                )

            desired_total = len(candidates) if fraction >= 1 else max(1, math.floor(len(candidates) * fraction))
            selections = self._balanced_sample(candidates, desired_total, seed)

            selection_mutations = [
                SamplingMutation(
                    video_id=record.video_id,
                    from_split=record.split,
                    to_split=normalized_target,
                    current_label=record.label,
                    actor=self._actor,
                    new_file_path=record.file_path,
                )
                for record in selections
            ]

            failed_ids: list[str] = []
            file_map = {record.video_id: record.file_path for record in candidates}
            if selection_mutations:
                if self._file_mover is None:
                    raise PromotionError("File mover is not configured for sampling operations.")

                if dry_run:
                    try:
                        for mutation in selection_mutations:
                            original_path = file_map.get(mutation.video_id)
                            if original_path is None:
                                failed_ids.append(str(mutation.video_id))
                                continue
                            transition = self._file_mover.plan_copy_to_split(
                                video_id=mutation.video_id,
                                file_path=original_path,
                                target_split=normalized_target,
                                run_id=run_uuid,
                            )
                            mutation.new_file_path = str(transition.destination)
                        if failed_ids:
                            raise PromotionError(
                                "Filesystem copy skipped some videos; aborting sampling."
                                + f" Skipped: {failed_ids}"
                            )
                    except (FileMoverError, PromotionError) as exc:
                        self._logger.error(
                            "sample_split_plan_error",
                            extra={
                                "error": str(exc),
                                "run_id": str(run_uuid),
                                "target_split": normalized_target,
                                "correlation_id": self._correlation_id,
                            },
                        )
                        raise PromotionError(str(exc)) from exc
                else:
                    file_transitions = []
                    try:
                        for mutation in selection_mutations:
                            original_path = file_map.get(mutation.video_id)
                            if original_path is None:
                                failed_ids.append(str(mutation.video_id))
                                continue
                            transition = self._file_mover.copy_to_split(
                                video_id=mutation.video_id,
                                file_path=original_path,
                                target_split=normalized_target,
                                run_id=run_uuid,
                            )
                            mutation.new_file_path = str(transition.destination)
                            file_transitions.append(transition)
                        if failed_ids:
                            raise PromotionError(
                                "Filesystem copy skipped some videos; aborting sampling."
                                + f" Skipped: {failed_ids}"
                            )
                    except (FileMoverError, PromotionError) as exc:
                        if self._file_mover is not None:
                            self._file_mover.rollback(file_transitions)
                        await self._session.rollback()
                        PROMOTION_FILESYSTEM_FAILURES.labels(action=action).inc()
                        self._logger.error(
                            "sample_split_fs_error",
                            extra={
                                "error": str(exc),
                                "run_id": str(run_uuid),
                                "target_split": normalized_target,
                                "correlation_id": self._correlation_id,
                            },
                        )
                        raise PromotionError(str(exc)) from exc

                    await self._repository.persist_sampling_results(
                        run_id=run_uuid,
                        strategy=strategy,
                        target_split=normalized_target,
                        sample_fraction=fraction,
                        selections=selection_mutations,
                    )
                    self._manifest.schedule_rebuild(
                        reason="sample_split",
                        run_id=str(run_uuid),
                    )

            copied_ids = [str(mutation.video_id) for mutation in selection_mutations if mutation.new_file_path]
            skipped_ids = [str(video_id) for video_id in existing_ids]

            self._logger.info(
                "sample_split",
                extra={
                    "run_id": str(run_uuid),
                    "target_split": normalized_target,
                    "copied_count": len(copied_ids),
                    "skipped_count": len(skipped_ids),
                    "failed_count": len(failed_ids),
                    "strategy": strategy,
                    "dry_run": dry_run,
                    "correlation_id": self._correlation_id,
                },
            )

            return SampleResult(
                run_id=str(run_uuid),
                target_split=normalized_target,
                copied_ids=tuple(copied_ids),
                skipped_ids=tuple(skipped_ids),
                failed_ids=tuple(failed_ids),
                dry_run=dry_run,
            )

    def _parse_video_ids(self, video_ids: Iterable[str]) -> list[uuid.UUID]:
        ids = [self._parse_uuid(raw_id, "video_id") for raw_id in video_ids]
        if not ids:
            raise PromotionValidationError("At least one video_id must be provided.")
        # Preserve original order while deduplicating
        seen: set[uuid.UUID] = set()
        unique_ids: list[uuid.UUID] = []
        for item in ids:
            if item not in seen:
                seen.add(item)
                unique_ids.append(item)
        return unique_ids

    @staticmethod
    def _parse_uuid(value: str, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise PromotionValidationError(f"Invalid {field}: {value}") from exc

    def _normalize_label(self, label: str | None) -> str:
        if label is None:
            raise PromotionValidationError("Label is required when staging to dataset_all.")
        normalized = label.strip().lower()
        if normalized not in _VALID_LABELS:
            raise PromotionValidationError(f"Unsupported label '{label}'.")
        return normalized

    def _normalize_target_split(self, target_split: str) -> str:
        normalized = target_split.strip().lower()
        if normalized not in _VALID_TARGET_SPLITS:
            raise PromotionValidationError(f"Unsupported target_split '{target_split}'.")
        return normalized

    @staticmethod
    def _normalize_fraction(sample_fraction: float) -> float:
        try:
            fraction = float(sample_fraction)
        except (TypeError, ValueError) as exc:
            raise PromotionValidationError("sample_fraction must be numeric.") from exc
        if fraction <= 0:
            raise PromotionValidationError("sample_fraction must be greater than 0.")
        return fraction

    @staticmethod
    def _validate_strategy(strategy: str) -> None:
        if strategy not in {"balanced_random"}:
            raise PromotionValidationError(f"Unsupported sampling strategy '{strategy}'.")

    def _balanced_sample(
        self,
        candidates: Sequence[VideoRecord],
        desired_total: int,
        seed: int | None,
    ) -> list[VideoRecord]:
        if desired_total <= 0:
            return []

        rng = random.Random(seed)
        buckets: dict[str | None, list[VideoRecord]] = {}
        for record in candidates:
            buckets.setdefault(record.label, []).append(record)

        queues: dict[str | None, deque[VideoRecord]] = {}
        for label, records in buckets.items():
            shuffled = list(records)
            rng.shuffle(shuffled)
            queues[label] = deque(shuffled)

        label_order = [label for label, queue in queues.items() if queue]
        rng.shuffle(label_order)

        selected: list[VideoRecord] = []
        while label_order and len(selected) < desired_total:
            for label in list(label_order):
                queue = queues[label]
                if not queue:
                    label_order.remove(label)
                    continue
                selected.append(queue.popleft())
                if len(selected) >= desired_total:
                    break
        return selected
