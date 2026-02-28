"""Reconcile missing indexes and add composite indexes for Phase 1.

Backfills single-column indexes that were defined in the initial migration
but never created on the live DB (bootstrapped from legacy SQL):
- ix_video_split, ix_video_label
- ix_training_run_status, ix_training_run_created
- ix_promotion_log_idempotency

Adds new composite indexes for Phase 1 statistical queries:
- ix_video_split_label on video(split, label)
- ix_extracted_frame_run_label on extracted_frame(run_id, label)

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

    # --- Backfill missing single-column indexes from initial migration ---
    # These were defined in 202510280000 but never applied to the live DB
    # because it was bootstrapped from legacy SQL then stamped at head.
    if not _index_exists(inspector, "video", "ix_video_split"):
        op.create_index("ix_video_split", "video", ["split"])
    if not _index_exists(inspector, "video", "ix_video_label"):
        op.create_index("ix_video_label", "video", ["label"])
    if not _index_exists(inspector, "training_run", "ix_training_run_status"):
        op.create_index("ix_training_run_status", "training_run", ["status"])
    if not _index_exists(inspector, "training_run", "ix_training_run_created"):
        op.create_index("ix_training_run_created", "training_run", ["created_at"])
    if not _index_exists(inspector, "promotion_log", "ix_promotion_log_idempotency"):
        op.create_index("ix_promotion_log_idempotency", "promotion_log", ["idempotency_key"])

    # --- New composite indexes (R3, R4) ---
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
    # Only drop the NEW composite indexes introduced by this migration.
    # The backfilled single-column indexes (ix_video_split, ix_video_label,
    # ix_training_run_status, ix_training_run_created, ix_promotion_log_idempotency)
    # are also defined in the initial migration (202510280000) which handles
    # dropping them in its own downgrade.  Dropping them here would conflict
    # on SQLite where the initial migration already creates them.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table, idx in [
        ("extracted_frame", "ix_extracted_frame_run_label"),
        ("video", "ix_video_split_label"),
    ]:
        if _index_exists(inspector, table, idx):
            op.drop_index(idx, table_name=table)
