"""Pydantic models for promotion API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional
from typing_extensions import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator

from ..db.enums import EmotionEnum, SelectionTargetEnum

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ..services.promote_service import SampleResult, StageResult

_ALLOWED_LABELS = frozenset({"happy", "sad", "neutral"})
_ALLOWED_TARGET_SPLITS = frozenset(str(split) for split in SelectionTargetEnum.enums)


VideoIdList = Annotated[List[UUID4], Field(min_length=1, max_length=200)]
SampleFraction = Annotated[float, Field(gt=0)]
OptionalSeed = Annotated[Optional[int], Field(ge=0, le=2**31 - 1)]
RunId = Annotated[str, Field(pattern=r"^run_\d{4}$")]


class StageRequest(BaseModel):
    """Deprecated compatibility request for legacy stage endpoint."""

    video_ids: VideoIdList = Field(
        ..., description="Video identifiers (legacy payload; prefer /api/v1/media/promote)."
    )
    label: str = Field(..., description="3-class label (happy|sad|neutral).")
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
    """Deprecated compatibility response for legacy stage endpoint."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["accepted", "error"] = "accepted"
    promoted_ids: List[str] = Field(default_factory=list)
    skipped_ids: List[str] = Field(default_factory=list)
    failed_ids: List[str] = Field(default_factory=list)
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
    """Deprecated compatibility request for legacy sample endpoint."""

    run_id: RunId
    target_split: str = Field(..., description="Destination split (train or test).")
    sample_fraction: SampleFraction = Field(
        ...,
        description=(
            "Legacy sampling fraction (>0). Endpoint is deprecated; "
            "run-scoped frame dataset preparation should be used instead."
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
    """Deprecated compatibility response for legacy sample endpoint."""

    model_config = ConfigDict(from_attributes=True)

    status: Literal["accepted", "error"] = "accepted"
    run_id: str
    target_split: str
    copied_ids: List[str] = Field(default_factory=list)
    skipped_ids: List[str] = Field(default_factory=list)
    failed_ids: List[str] = Field(default_factory=list)
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


class ResetManifestRequest(BaseModel):
    """Request body for resetting manifest state."""

    reason: str = Field(
        ...,
        description="Human-readable reason for triggering a manifest reset.",
    )
    run_id: Optional[RunId] = Field(
        default=None,
        description="Optional training run identifier scoped to the reset.",
    )

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be empty")
        return normalized


class ResetManifestResponse(BaseModel):
    """Response payload after invoking a manifest reset."""

    status: Literal["accepted", "error"] = "accepted"
    reason: str
    run_id: Optional[str] = None

    @classmethod
    def from_request(
        cls,
        *,
        request: ResetManifestRequest,
    ) -> "ResetManifestResponse":
        run_id = str(request.run_id) if request.run_id is not None else None
        return cls(
            status="accepted",
            reason=request.reason,
            run_id=run_id,
        )
