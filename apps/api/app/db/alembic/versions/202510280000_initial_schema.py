"""Initial media mover schema."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20251028_000000"
down_revision = None
branch_labels = None
depends_on = None

split_enum = sa.Enum(
    "temp",
    "dataset_all",
    "train",
    "test",
    name="video_split_enum",
    create_constraint=True,
    native_enum=False,
)
emotion_enum = sa.Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    name="emotion_enum",
    create_constraint=True,
    native_enum=False,
)
selection_enum = sa.Enum(
    "train",
    "test",
    name="training_selection_target_enum",
    create_constraint=True,
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "video",
        sa.Column("video_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("split", split_enum, nullable=False, server_default="temp"),
        sa.Column("label", emotion_enum, nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            (
                split IN ('temp', 'test') AND label IS NULL
            ) OR (
                split IN ('dataset_all', 'train') AND label IS NOT NULL
            )
            """,
            name="chk_video_split_label_policy",
        ),
        sa.UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size"),
    )
    op.create_index("ix_video_split", "video", ["split"])
    op.create_index("ix_video_label", "video", ["label"])

    op.create_table(
        "training_run",
        sa.Column("run_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("train_fraction", sa.Float(), nullable=False),
        sa.Column("test_fraction", sa.Float(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "training_selection",
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("training_run.run_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "video_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("video.video_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("target_split", selection_enum, primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "promotion_log",
        sa.Column("promotion_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "video_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("video.video_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_split", split_enum, nullable=False),
        sa.Column("to_split", split_enum, nullable=False),
        sa.Column("intended_label", emotion_enum, nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_promotion_log_video_time",
        "promotion_log",
        ["video_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_promotion_log_video_time", table_name="promotion_log")
    op.drop_table("promotion_log")

    op.drop_table("training_selection")
    op.drop_table("training_run")

    op.drop_index("ix_video_label", table_name="video")
    op.drop_index("ix_video_split", table_name="video")
    op.drop_table("video")

    selection_enum.drop(op.get_bind(), checkfirst=True)
    emotion_enum.drop(op.get_bind(), checkfirst=True)
    split_enum.drop(op.get_bind(), checkfirst=True)