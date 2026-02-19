from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID  # type: ignore[attr-defined]
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import EmotionEnum, SelectionTargetEnum, SplitEnum

try:  # pragma: no cover - SQLAlchemy 2.0+ provides `sqlalchemy.Uuid`
    from sqlalchemy import Uuid as SAUuid
except ImportError:  # pragma: no cover
    SAUuid = PGUUID  # fallback for older SQLAlchemy versions


class Video(TimestampMixin, Base):
    __tablename__ = "video"

    video_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    split: Mapped[str] = mapped_column(SplitEnum, nullable=False, default="temp")
    label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, default=dict, nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    promotions: Mapped[List["PromotionLog"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    selections: Mapped[List["TrainingSelection"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    label_events: Mapped[List["LabelEvent"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size"),
        CheckConstraint(
            """
            (
                split IN ('temp', 'test', 'purged') AND label IS NULL
            ) OR (
                split = 'train' AND label IS NOT NULL
            )
            """,
            name="chk_video_split_label_policy",
        ),
        Index("ix_video_split", "split"),
        Index("ix_video_label", "label"),
    )


class TrainingRun(TimestampMixin, Base):
    __tablename__ = "training_run"

    run_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    train_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    test_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    seed: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dataset_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    engine_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    selections: Mapped[List["TrainingSelection"]] = relationship(
        back_populates="training_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "train_fraction > 0 AND train_fraction < 1",
            name="chk_train_fraction_range",
        ),
        CheckConstraint(
            "train_fraction + test_fraction <= 1.0",
            name="chk_valid_fractions",
        ),
        CheckConstraint(
            "status IN ('pending', 'sampling', 'training', 'evaluating', "
            "'completed', 'failed', 'cancelled')",
            name="chk_training_status",
        ),
        Index("ix_training_run_status", "status"),
        Index("ix_training_run_created", "created_at"),
    )


class TrainingSelection(TimestampMixin, Base):
    __tablename__ = "training_selection"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("training_run.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video.video_id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_split: Mapped[str] = mapped_column(
        SelectionTargetEnum,
        primary_key=True,
    )

    training_run: Mapped[TrainingRun] = relationship(back_populates="selections")
    video: Mapped[Video] = relationship(back_populates="selections")


class PromotionLog(TimestampMixin, Base):
    __tablename__ = "promotion_log"

    promotion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video.video_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    to_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    intended_label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, default=dict, nullable=True
    )

    video: Mapped[Video] = relationship(back_populates="promotions")

    __table_args__ = (
        Index("ix_promotion_log_video_time", "video_id", "created_at"),
        Index("ix_promotion_log_idempotency", "idempotency_key"),
    )


# ============================================================================
# New Models for n8n Agent Workflows (Phase 3)
# ============================================================================


class LabelEvent(Base):
    """Audit log for labeling actions (Labeling Agent - Agent 2)."""
    __tablename__ = "label_event"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("video.video_id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(EmotionEnum, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    rater_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    video: Mapped[Optional[Video]] = relationship(back_populates="label_events")

    __table_args__ = (
        CheckConstraint(
            "action IN ('label_only', 'promote_train', 'promote_test', 'discard', 'relabel')",
            name="chk_label_event_action",
        ),
        Index("ix_label_event_video", "video_id"),
        Index("ix_label_event_created", "created_at"),
        Index("ix_label_event_idempotency", "idempotency_key"),
    )


class DeploymentLog(Base):
    """Tracks model deployments (Deployment Agent - Agent 7)."""
    __tablename__ = "deployment_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    engine_path: Mapped[str] = mapped_column(String(500), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    rollback_from: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gate_b_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fps_measured: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    latency_p50_ms: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    latency_p95_ms: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    gpu_memory_gb: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "target_stage IN ('shadow', 'canary', 'rollout')",
            name="chk_deployment_stage",
        ),
        CheckConstraint(
            "status IN ('pending', 'deploying', 'success', 'failed', 'rolled_back')",
            name="chk_deployment_status",
        ),
        Index("ix_deployment_stage", "target_stage"),
        Index("ix_deployment_status", "status"),
        Index("ix_deployment_time", "deployed_at"),
    )


class AuditLog(Base):
    """General audit log for privacy operations (Privacy Agent - Agent 8)."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="video")
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_audit_action", "action"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_timestamp", "timestamp"),
    )


class ObsSample(Base):
    """Time-series metrics storage (Observability Agent - Agent 9)."""
    __tablename__ = "obs_samples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    src: Mapped[str] = mapped_column(String(100), nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)

    __table_args__ = (
        Index("ix_obs_ts", "ts"),
        Index("ix_obs_src_metric", "src", "metric"),
    )


class ReconcileReport(Base):
    """Filesystem/database reconciliation reports (Reconciler Agent - Agent 4)."""
    __tablename__ = "reconcile_report"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    orphan_count: Mapped[int] = mapped_column(default=0, nullable=False)
    missing_count: Mapped[int] = mapped_column(default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(default=0, nullable=False)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('scheduled', 'manual', 'webhook')",
            name="chk_reconcile_trigger",
        ),
        Index("ix_reconcile_time", "run_at"),
        Index("ix_reconcile_drift", "drift_detected"),
    )