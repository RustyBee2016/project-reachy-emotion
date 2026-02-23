"""Add extracted_frame table for run-scoped frame metadata.

Revision ID: 20260223_000003
Revises: 20260218_000002
Create Date: 2026-02-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260223_000003"
down_revision = "20260218_000002"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "extracted_frame"):
        op.create_table(
            "extracted_frame",
            sa.Column("frame_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(length=32), nullable=False),
            sa.Column("split", sa.String(length=16), nullable=False, server_default="train"),
            sa.Column("frame_path", sa.String(length=1024), nullable=False),
            sa.Column(
                "label",
                sa.Enum(
                    "neutral",
                    "happy",
                    "sad",
                    name="emotion_enum",
                    create_constraint=True,
                    native_enum=False,
                ),
                nullable=True,
            ),
            sa.Column(
                "source_video_id",
                sa.String(length=36),
                sa.ForeignKey("video.video_id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("source_video_path", sa.String(length=1024), nullable=True),
            sa.Column("frame_order", sa.Integer(), nullable=True),
            sa.Column("frame_index", sa.Integer(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
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
                "split IN ('train', 'valid', 'test')",
                name="chk_extracted_frame_split",
            ),
            sa.CheckConstraint(
                "(split = 'test' AND label IS NULL) OR (split IN ('train', 'valid'))",
                name="chk_extracted_frame_test_unlabeled",
            ),
            sa.UniqueConstraint("run_id", "frame_path", name="uq_extracted_frame_run_path"),
        )

    if not _index_exists(inspector, "extracted_frame", "ix_extracted_frame_run_id"):
        op.create_index("ix_extracted_frame_run_id", "extracted_frame", ["run_id"])
    if not _index_exists(inspector, "extracted_frame", "ix_extracted_frame_label"):
        op.create_index("ix_extracted_frame_label", "extracted_frame", ["label"])
    if not _index_exists(inspector, "extracted_frame", "ix_extracted_frame_split"):
        op.create_index("ix_extracted_frame_split", "extracted_frame", ["split"])


def downgrade() -> None:
    # Intentionally no-op to avoid data loss in live systems.
    pass
