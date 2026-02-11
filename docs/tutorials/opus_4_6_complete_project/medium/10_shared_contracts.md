# Tutorial 10: Shared API Contracts

> **Priority**: MEDIUM — Prevents schema divergence
> **Time estimate**: 6-8 hours
> **Difficulty**: Moderate
> **Prerequisites**: Pydantic basics, API structure understood

---

## Why This Matters

The file `shared/contracts/schemas.py` is a placeholder with a single
comment: "Placeholder until models are extracted from routers." API
schemas (Pydantic models) are scattered across `apps/api/app/schemas/`.
If the gateway and web app define the same model differently, you get
silent data corruption.

---

## What You'll Build

A centralized schema module that:
1. Defines all API request/response models in one place
2. Is imported by both the API and web client
3. Provides validation for data moving through the pipeline

---

## Step 1: Audit Existing Schemas

List all schema files:

```bash
find apps/api/app/schemas/ -name "*.py" -exec echo {} \;
```

Read each one and note the Pydantic models defined:
- `video.py` — VideoMetadata, VideoListResponse
- `promote.py` — StageRequest, SampleRequest, StageResponse, SampleResponse
- `dialogue.py` — DialogueRequest, DialogueResponse
- `responses.py` — General response models

---

## Step 2: Create the Shared Module

Replace `shared/contracts/schemas.py` with consolidated models:

```python
"""
Shared API schemas — single source of truth.

All Pydantic models used in API requests/responses are defined here.
Both the FastAPI gateway and web client import from this module.

Usage:
    from shared.contracts.schemas import VideoMetadata, StageRequest
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field, field_validator


# ---- Enums ----

class EmotionLabel(str, Enum):
    """Valid emotion labels."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISE = "surprise"
    FEARFUL = "fearful"


class SplitName(str, Enum):
    """Valid dataset split names."""
    TEMP = "temp"
    DATASET_ALL = "dataset_all"
    TRAIN = "train"
    TEST = "test"
    PURGED = "purged"


class TrainingStatus(str, Enum):
    """Training run status values."""
    PENDING = "pending"
    SAMPLING = "sampling"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---- Video Schemas ----

class VideoMetadata(BaseModel):
    """Video metadata as returned by the API."""
    video_id: str
    file_path: str
    split: SplitName
    label: Optional[EmotionLabel] = None
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: int
    sha256: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    """Paginated list of videos."""
    videos: List[VideoMetadata]
    total: int
    limit: int
    offset: int


# ---- Promotion Schemas ----

class StageRequest(BaseModel):
    """Request to stage videos from temp to dataset_all."""
    video_ids: List[str] = Field(..., min_length=1)
    label: EmotionLabel
    dry_run: bool = False

    @field_validator("video_ids")
    @classmethod
    def validate_video_ids(cls, v):
        if not v:
            raise ValueError("At least one video_id required")
        return v


class StageResponse(BaseModel):
    """Response from staging operation."""
    promoted_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool


class SampleRequest(BaseModel):
    """Request to sample videos into train/test splits."""
    run_id: str
    target_split: str = Field(..., pattern="^(train|test)$")
    sample_fraction: float = Field(..., gt=0, le=1)
    strategy: str = "balanced_random"
    seed: Optional[int] = None
    dry_run: bool = False


class SampleResponse(BaseModel):
    """Response from sampling operation."""
    run_id: str
    target_split: str
    copied_ids: Sequence[str]
    skipped_ids: Sequence[str]
    failed_ids: Sequence[str]
    dry_run: bool


# ---- Training Schemas ----

class TrainingRunSummary(BaseModel):
    """Summary of a training run."""
    run_id: str
    status: TrainingStatus
    strategy: str
    train_fraction: float
    dataset_hash: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GateAResult(BaseModel):
    """Gate A validation result."""
    passed: bool
    f1_macro: float
    balanced_accuracy: float
    ece: float
    brier: float
    per_class_f1: Dict[str, float]
    thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "f1_macro": 0.84,
            "per_class_f1": 0.75,
            "balanced_accuracy": 0.85,
            "ece": 0.08,
            "brier": 0.16,
        }
    )


# ---- Dialogue Schemas ----

class DialogueRequest(BaseModel):
    """Request for emotion-conditioned dialogue."""
    emotion: EmotionLabel
    confidence: float = Field(..., ge=0, le=1)
    context: Optional[str] = None


class DialogueResponse(BaseModel):
    """LLM-generated dialogue response."""
    text: str
    tone: str
    gesture_cue: Optional[str] = None
    model_used: Optional[str] = None


# ---- Health Schemas ----

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: Optional[str] = None
```

---

## Step 3: Add `__init__.py` for Clean Imports

Create `shared/contracts/__init__.py`:

```python
"""Shared API contracts for Reachy emotion pipeline."""
from .schemas import (
    EmotionLabel,
    SplitName,
    TrainingStatus,
    VideoMetadata,
    VideoListResponse,
    StageRequest,
    StageResponse,
    SampleRequest,
    SampleResponse,
    TrainingRunSummary,
    GateAResult,
    DialogueRequest,
    DialogueResponse,
    HealthResponse,
)

__all__ = [
    "EmotionLabel",
    "SplitName",
    "TrainingStatus",
    "VideoMetadata",
    "VideoListResponse",
    "StageRequest",
    "StageResponse",
    "SampleRequest",
    "SampleResponse",
    "TrainingRunSummary",
    "GateAResult",
    "DialogueRequest",
    "DialogueResponse",
    "HealthResponse",
]
```

---

## Step 4: Write a Schema Validation Test

Create `tests/test_shared_contracts.py`:

```python
"""Tests for shared API contract schemas."""

import pytest
from shared.contracts.schemas import (
    StageRequest,
    SampleRequest,
    VideoMetadata,
    EmotionLabel,
    GateAResult,
)


class TestStageRequest:
    def test_valid_request(self):
        req = StageRequest(
            video_ids=["abc-123"],
            label=EmotionLabel.HAPPY,
        )
        assert req.label == EmotionLabel.HAPPY
        assert req.dry_run is False

    def test_empty_ids_rejected(self):
        with pytest.raises(ValueError):
            StageRequest(video_ids=[], label=EmotionLabel.HAPPY)


class TestGateAResult:
    def test_passing_result(self):
        result = GateAResult(
            passed=True,
            f1_macro=0.90,
            balanced_accuracy=0.88,
            ece=0.05,
            brier=0.12,
            per_class_f1={"happy": 0.91, "sad": 0.89, "neutral": 0.90},
        )
        assert result.passed is True

    def test_thresholds_have_defaults(self):
        result = GateAResult(
            passed=False,
            f1_macro=0.70,
            balanced_accuracy=0.68,
            ece=0.15,
            brier=0.25,
            per_class_f1={"happy": 0.65},
        )
        assert result.thresholds["f1_macro"] == 0.84
```

```bash
pytest tests/test_shared_contracts.py -v
```

---

## Checklist

- [ ] `shared/contracts/schemas.py` contains all Pydantic models
- [ ] `shared/contracts/__init__.py` exports all models
- [ ] `tests/test_shared_contracts.py` passes
- [ ] Models can be imported: `from shared.contracts import StageRequest`
