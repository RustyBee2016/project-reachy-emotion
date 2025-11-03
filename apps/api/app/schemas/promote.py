"""Pydantic models for promotion API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator

from ..db.enums import EmotionEnum, SelectionTargetEnum

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ..services.promote_service import SampleResult, StageResult

_ALLOWED_LABELS = frozenset(str(label) for label in EmotionEnum.enums)
_ALLOWED_TARGET_SPLITS = frozenset(str(split) for split in SelectionTargetEnum.enums)


VideoIdList = Annotated[list[UUID4], Field(min_length=1, max_length=200)]
SampleFraction = Annotated[float, Field(gt=0)]
OptionalSeed = Annotated[int | None, Field(ge=0, le=2**31 - 1)]


class StageRequest(BaseModel):
    """Request body for staging videos from temp into dataset_all."""

    video_ids: VideoIdList = Field(
        ..., description="Identifiers of videos to stage into dataset_all."
    )
    label: str = Field(..., description="Emotion label applied to staged clips.")
    dry_run: bool = Field(
        default=False,
        description="When true, validate and plan the operation without persisting changes.",
    )

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_LABELS:
            allowed = ", ".join(sorted(_ALLOWED_LABELS))
            raise ValueError(f"label must be one of: {allowed}")
        return normalized


class StageResponse(BaseModel):
    """Response payload after staging videos."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["accepted", "error"] = "accepted"
    promoted_ids: list[str] = Field(default_factory=list)
    skipped_ids: list[str] = Field(default_factory=list)
    failed_ids: list[str] = Field(default_factory=list)
    dry_run: bool = Field(
        default=False,
        description="Indicates whether the response represents a simulated operation.",
    )

    @classmethod
    def from_result(
        cls,
        *,
        status: Literal["accepted", "error"],
        result: "StageResult",
    ) -> "StageResponse":
        return cls(
            status=status,
            promoted_ids=list(result.promoted_ids),
            skipped_ids=list(result.skipped_ids),
            failed_ids=list(result.failed_ids),
            dry_run=result.dry_run,
        )


class SampleRequest(BaseModel):
    """Request body for sampling dataset_all clips into train/test splits."""

    run_id: UUID4
    target_split: str = Field(..., description="Destination split (train or test).")
    sample_fraction: SampleFraction = Field(
        ...,
        description=(
            "Fraction of dataset_all clips to sample (>0). Values greater than 1 select all"
            " available candidates."
        ),
    )
    strategy: Literal["balanced_random"] = Field(default="balanced_random")
    seed: OptionalSeed = Field(
        default=None,
        description="Optional deterministic seed for sampling.",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, validate and plan the sampling without persisting changes.",
    )

    @field_validator("target_split")
    @classmethod
    def _validate_target_split(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_TARGET_SPLITS:
            allowed = ", ".join(sorted(_ALLOWED_TARGET_SPLITS))
            raise ValueError(f"target_split must be one of: {allowed}")
        return normalized


class SampleResponse(BaseModel):
    """Response payload after sampling dataset_all clips."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["accepted", "error"] = "accepted"
    run_id: str
    target_split: str
    copied_ids: list[str] = Field(default_factory=list)
    skipped_ids: list[str] = Field(default_factory=list)
    failed_ids: list[str] = Field(default_factory=list)
    dry_run: bool = Field(
        default=False,
        description="Indicates whether the response represents a simulated operation.",
    )

    @classmethod
    def from_result(
        cls,
        *,
        status: Literal["accepted", "error"],
        result: "SampleResult",
    ) -> "SampleResponse":
        return cls(
            status=status,
            run_id=result.run_id,
            target_split=result.target_split,
            copied_ids=list(result.copied_ids),
            skipped_ids=list(result.skipped_ids),
            failed_ids=list(result.failed_ids),
            dry_run=result.dry_run,
        )
