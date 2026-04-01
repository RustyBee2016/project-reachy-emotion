"""Schemas for emotion event persistence (Phase 3 — Jetson edge events)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .responses import SuccessResponse


class EmotionEventCreate(BaseModel):
    """Incoming emotion event from Jetson edge device."""

    device_id: str = Field(
        ..., description="Device identifier (e.g. reachy-mini-01)", max_length=100
    )
    emotion: str = Field(
        ..., description="Detected emotion label", pattern="^(happy|sad|neutral)$"
    )
    confidence: float = Field(
        ..., description="Detection confidence score", ge=0.0, le=1.0
    )
    inference_ms: Optional[float] = Field(
        None, description="Inference latency in milliseconds", ge=0.0
    )
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracing", max_length=64
    )
    session_id: Optional[str] = Field(
        None, description="Session identifier for Gate C metrics", max_length=64
    )
    ts: Optional[datetime] = Field(
        None, description="Original event timestamp from device (ISO 8601)"
    )
    meta: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata (model version, temperature, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_id": "reachy-mini-01",
                    "emotion": "happy",
                    "confidence": 0.92,
                    "inference_ms": 42.3,
                    "correlation_id": "a1b2c3d4",
                    "session_id": "sess-001",
                    "ts": "2026-04-01T12:00:00Z",
                }
            ]
        }
    }


class EmotionEventData(BaseModel):
    """Persisted emotion event returned by the API."""

    id: str = Field(description="Event UUID")
    device_id: str
    emotion: str
    confidence: float
    inference_ms: Optional[float] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    device_ts: Optional[datetime] = None
    created_at: datetime


class EmotionEventStatsData(BaseModel):
    """Aggregated emotion event statistics."""

    total_events: int = Field(description="Total events in the window")
    by_emotion: Dict[str, int] = Field(description="Count per emotion class")
    avg_confidence: Optional[float] = Field(None, description="Mean confidence score")
    avg_inference_ms: Optional[float] = Field(None, description="Mean inference latency (ms)")
    abstention_count: int = Field(0, description="Events below confidence threshold")
    abstention_rate: Optional[float] = Field(None, description="Abstention rate (0-1)")
    device_ids: List[str] = Field(default_factory=list, description="Active device IDs")

    @field_validator("avg_confidence", "avg_inference_ms", "abstention_rate", mode="before")
    @classmethod
    def round_floats(cls, v):
        if v is not None:
            return round(v, 4)
        return v


# Response type aliases
EmotionEventResponse = SuccessResponse[EmotionEventData]
EmotionEventListResponse = SuccessResponse[List[EmotionEventData]]
EmotionEventStatsResponse = SuccessResponse[EmotionEventStatsData]
