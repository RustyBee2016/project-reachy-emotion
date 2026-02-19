"""Promotion service for promotion/manifest orchestration.

Legacy stage/sample compatibility endpoints are intentionally deprecated.
Current runtime flow promotes clips directly temp -> train/<label> via
/api/media/promote and builds run-scoped frame datasets during training prep.
"""

from __future__ import annotations

import logging
import math
import random
import re
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


@dataclass
class StageResult:
    """Outcome summary for stage compatibility operations."""

    promoted_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool = False


@dataclass
class SampleResult:
    """Outcome summary for sample compatibility operations."""

    run_id: str
    target_split: str
    copied_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool = False


_VALID_LABELS = frozenset(str(label) for label in EmotionEnum.enums)
_VALID_TARGET_SPLITS = frozenset(str(split) for split in SelectionTargetEnum.enums)
_RUN_ID_PATTERN = re.compile(r"^run_\d{4}$")


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

    async def stage_to_train(
        self,
        video_ids: Iterable[str],
        *,
        label: str | None,
        dry_run: bool = False,
    ) -> StageResult:
        """Compatibility shim for deprecated /api/v1/promote/stage endpoint.

        Current runtime policy uses direct promotion via `/api/media/promote` with:
        - dest_split='train'
        - label in {'happy','sad','neutral'}
        """

        async with self._track_operation("stage"):
            # Touch validators for consistent error messaging if payload is malformed.
            self._parse_video_ids(video_ids)
            self._normalize_label(label)
            _ = dry_run
            raise PromotionValidationError(
                "Deprecated endpoint: /api/v1/promote/stage is no longer supported. "
                "Use /api/media/promote with dest_split='train' and a 3-class label."
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
        """Compatibility shim for deprecated /api/v1/promote/sample endpoint.

        Run-scoped frame datasets are now created by training dataset preparation
        from train/<label> sources (e.g., train/<label>/run_xxxx) and consolidated
        train/run/run_xxxx and test/run_xxxx outputs.
        """

        async with self._track_operation("sample"):
            self._normalize_run_id(run_id)
            self._normalize_target_split(target_split)
            self._normalize_fraction(sample_fraction)
            self._validate_strategy(strategy)
            _ = seed
            _ = dry_run
            raise PromotionValidationError(
                "Deprecated endpoint: /api/v1/promote/sample is no longer supported. "
                "Use run-scoped frame dataset preparation for training runs."
            )

    def _parse_video_ids(self, video_ids: Iterable[str]) -> list[str]:
        ids = [self._parse_uuid(raw_id, "video_id") for raw_id in video_ids]
        if not ids:
            raise PromotionValidationError("At least one video_id must be provided.")
        # Preserve original order while deduplicating
        seen: set[str] = set()
        unique_ids: list[str] = []
        for item in ids:
            if item not in seen:
                seen.add(item)
                unique_ids.append(item)
        return unique_ids

    @staticmethod
    def _parse_uuid(value: str, field: str) -> str:
        """Parse and validate UUID string, returning normalized string format."""
        try:
            # Validate it's a proper UUID, but return as string
            parsed = uuid.UUID(str(value))
            return str(parsed)
        except ValueError as exc:
            raise PromotionValidationError(f"Invalid {field}: {value}") from exc

    def _normalize_label(self, label: str | None) -> str:
        if label is None:
            raise PromotionValidationError("Label is required for train promotion.")
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
    def _normalize_run_id(run_id: str) -> str:
        normalized = run_id.strip().lower()
        if not _RUN_ID_PATTERN.fullmatch(normalized):
            raise PromotionValidationError("run_id must match run_xxxx (e.g., run_0001)")
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
