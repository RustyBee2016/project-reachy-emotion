"""Pydantic models for training pipeline API endpoints."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ExtractFramesRequest(BaseModel):
    """Request to extract frames from classified training videos."""

    run_id: Optional[str] = Field(
        default=None,
        description=(
            "Run identifier (run_xxxx format). "
            "Auto-generated as the next sequential ID if omitted."
        ),
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2**31 - 1,
        description="Random seed for reproducible frame sampling.",
    )
    frames_per_video: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of random frames to sample from each video.",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, validate inputs and report what would happen without extracting.",
    )

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        import re
        normalized = value.strip()
        if not re.fullmatch(r"run_\d{4}", normalized):
            raise ValueError("run_id must match pattern run_xxxx (e.g., run_0001)")
        return normalized


class ExtractFramesResponse(BaseModel):
    """Response from a frame extraction operation."""

    status: str = Field(description="Operation result: accepted, completed, or error.")
    run_id: str = Field(description="Run identifier used for this extraction.")
    train_count: int = Field(description="Total frames extracted for training.")
    test_count: int = Field(description="Total frames extracted for testing (0 in current workflow).")
    videos_processed: int = Field(description="Number of source videos processed.")
    frames_per_video: int = Field(description="Frames sampled per video.")
    seed: int = Field(description="Random seed used for sampling.")
    dataset_hash: str = Field(description="SHA-256 hash of the extracted frame dataset.")
    dry_run: bool = Field(description="Whether this was a dry-run.")
    emotion_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Number of source videos per emotion class.",
    )
    frame_output_dirs: Dict[str, str] = Field(
        default_factory=dict,
        description="Paths to per-emotion frame directories.",
    )
    consolidated_dir: str = Field(
        default="",
        description="Path to the consolidated run dataset.",
    )


class InitiateRunRequest(BaseModel):
    """Request to initiate ML fine-tuning for an extracted frame dataset."""

    run_id: str = Field(
        ...,
        description="Run identifier from a completed frame extraction (run_xxxx format).",
    )
    config_path: str = Field(
        default="trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml",
        description="Path to the training YAML configuration.",
    )

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        import re
        normalized = value.strip()
        if not re.fullmatch(r"run_\d{4}", normalized):
            raise ValueError("run_id must match pattern run_xxxx (e.g., run_0001)")
        return normalized


class InitiateRunResponse(BaseModel):
    """Response after submitting a training run to the n8n orchestrator."""

    status: str = Field(description="Submission result: accepted or error.")
    run_id: str = Field(description="Run identifier.")
    n8n_notified: bool = Field(description="Whether n8n training webhook was called.")
    n8n_status_code: Optional[int] = Field(
        default=None,
        description="HTTP status code from n8n webhook (None if notification skipped).",
    )
    dataset_hash: Optional[str] = Field(
        default=None,
        description="Dataset hash from the extraction phase.",
    )
    config_path: str = Field(description="Training YAML config used.")
    message: str = Field(default="", description="Human-readable status message.")


class TrainingRunStatus(BaseModel):
    """Status snapshot of a training run."""

    run_id: str
    status: str
    train_count: int = 0
    test_count: int = 0
    videos_processed: int = 0
    dataset_hash: Optional[str] = None
    seed: Optional[int] = None
    error_message: Optional[str] = None
