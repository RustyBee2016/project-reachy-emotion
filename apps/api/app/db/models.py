from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID  # type: ignore[attr-defined]
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

    promotions: Mapped[list["PromotionLog"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    selections: Mapped[list["TrainingSelection"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size"),
        CheckConstraint(
            """
            (
                split IN ('temp', 'test') AND label IS NULL
            ) OR (
                split IN ('dataset_all', 'train') AND label IS NOT NULL
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

    selections: Mapped[list["TrainingSelection"]] = relationship(
        back_populates="training_run",
        cascade="all, delete-orphan",
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

    video: Mapped[Video] = relationship(back_populates="promotions")

    __table_args__ = (
        Index("ix_promotion_log_video_time", "video_id", "created_at"),
    )