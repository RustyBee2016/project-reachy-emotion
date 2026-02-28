"""Add composite indexes for Phase 1 statistical queries.

- ix_video_split_label on video(split, label) — label distribution queries
- ix_extracted_frame_run_label on extracted_frame(run_id, label) — per-run stats

Revision ID: 20260227_000004
Revises: 20260223_000003
Create Date: 2026-02-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260227_000004"
down_revision = "20260223_000003"
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

    # R3: composite index (split, label) on video for label distribution queries
    if not _index_exists(inspector, "video", "ix_video_split_label"):
        op.create_index("ix_video_split_label", "video", ["split", "label"])

    # R4: composite index (run_id, label) on extracted_frame for per-run stats
    if not _index_exists(inspector, "extracted_frame", "ix_extracted_frame_run_label"):
        op.create_index(
            "ix_extracted_frame_run_label",
            "extracted_frame",
            ["run_id", "label"],
        )


def downgrade() -> None:
    op.drop_index("ix_extracted_frame_run_label", table_name="extracted_frame")
    op.drop_index("ix_video_split_label", table_name="video")
