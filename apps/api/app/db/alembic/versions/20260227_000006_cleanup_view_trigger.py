"""Cleanup deprecated dataset_all split, add updated_at trigger and statistics views.

R6  — Migrate any remaining split='dataset_all' rows to 'train' (labeled) or 'temp' (unlabeled).
R7  — Create updated_at trigger function on video and training_run (PostgreSQL only).
R9  — Create v_label_distribution and v_run_frame_stats views (PostgreSQL only).
R10 — Legacy SQL files (002, 003) deprecated via file headers (not migration DDL).

Downgrade reverses trigger/views but does NOT re-introduce dataset_all values.

Revision ID: 20260227_000006
Revises: 20260227_000005
Create Date: 2026-02-27
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision = "20260227_000006"
down_revision = "20260227_000005"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def _is_postgresql(bind) -> bool:
    return bind.dialect.name == "postgresql"


def _migrate_dataset_all(bind) -> None:
    """R6: Remap any legacy dataset_all rows to valid split values."""
    result = bind.execute(
        sa.text("SELECT COUNT(*) FROM video WHERE split = 'dataset_all'")
    )
    count = result.scalar()
    if count == 0:
        logger.info("No dataset_all rows found — nothing to migrate")
        return

    logger.warning("Found %d video rows with split='dataset_all' — migrating", count)

    # Labeled rows → train (satisfies chk_video_split_label_policy)
    bind.execute(
        sa.text(
            "UPDATE video SET split = 'train' "
            "WHERE split = 'dataset_all' AND label IS NOT NULL"
        )
    )
    # Unlabeled rows → temp (cannot go to train without a label)
    bind.execute(
        sa.text(
            "UPDATE video SET split = 'temp' "
            "WHERE split = 'dataset_all' AND label IS NULL"
        )
    )
    logger.info("dataset_all migration complete")


def _create_updated_at_trigger(bind) -> None:
    """R7: Create updated_at trigger (PostgreSQL only)."""
    if not _is_postgresql(bind):
        return

    bind.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )

    for table_name in ("video", "training_run"):
        trigger_name = f"trg_{table_name}_updated_at"
        bind.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}"))
        bind.execute(
            sa.text(
                f"CREATE TRIGGER {trigger_name} "
                f"BEFORE UPDATE ON {table_name} "
                f"FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
            )
        )
    logger.info("updated_at triggers created for video and training_run")


def _create_statistics_views(bind) -> None:
    """R9: Create statistics views (PostgreSQL only)."""
    if not _is_postgresql(bind):
        return

    bind.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW v_label_distribution AS
            SELECT
                v.split,
                v.label,
                COUNT(*) AS video_count,
                ROUND(
                    100.0 * COUNT(*) /
                        NULLIF(SUM(COUNT(*)) OVER (PARTITION BY v.split), 0),
                    2
                ) AS pct_of_split,
                SUM(v.size_bytes) AS total_size_bytes,
                ROUND(AVG(v.duration_sec)::NUMERIC, 2) AS avg_duration_sec,
                MIN(v.created_at) AS oldest_video,
                MAX(v.created_at) AS newest_video
            FROM video v
            WHERE v.deleted_at IS NULL
              AND v.label IS NOT NULL
            GROUP BY v.split, v.label
            ORDER BY v.split, v.label;
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW v_run_frame_stats AS
            SELECT
                ef.run_id,
                ef.split AS frame_split,
                ef.label,
                COUNT(*) AS frame_count,
                COUNT(DISTINCT ef.source_video_id) AS source_video_count
            FROM extracted_frame ef
            GROUP BY ef.run_id, ef.split, ef.label
            ORDER BY ef.run_id, ef.split, ef.label;
            """
        )
    )
    logger.info("Statistics views created: v_label_distribution, v_run_frame_stats")


def _drop_statistics_views(bind) -> None:
    """Drop statistics views on downgrade."""
    if not _is_postgresql(bind):
        return
    bind.execute(sa.text("DROP VIEW IF EXISTS v_run_frame_stats"))
    bind.execute(sa.text("DROP VIEW IF EXISTS v_label_distribution"))


def _drop_updated_at_trigger(bind) -> None:
    """Drop updated_at triggers on downgrade."""
    if not _is_postgresql(bind):
        return
    for table_name in ("video", "training_run"):
        trigger_name = f"trg_{table_name}_updated_at"
        bind.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}"))
    bind.execute(sa.text("DROP FUNCTION IF EXISTS update_updated_at_column()"))


def upgrade() -> None:
    bind = op.get_bind()

    _migrate_dataset_all(bind)
    _create_updated_at_trigger(bind)
    _create_statistics_views(bind)


def downgrade() -> None:
    bind = op.get_bind()

    _drop_statistics_views(bind)
    _drop_updated_at_trigger(bind)
    # dataset_all data migration is NOT reversed — do not re-introduce invalid splits
