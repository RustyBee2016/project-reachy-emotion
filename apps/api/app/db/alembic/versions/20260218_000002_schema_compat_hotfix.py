"""Schema compatibility hotfix for live DB drift.

Revision ID: 20260218_000002
Revises: 20260214_000001
Create Date: 2026-02-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260218_000002"
down_revision = "20260214_000001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ---------------------------------------------------------------------
    # video
    # ---------------------------------------------------------------------
    if _table_exists(inspector, "video"):
        if not _column_exists(inspector, "video", "metadata"):
            op.add_column("video", sa.Column("metadata", sa.JSON(), nullable=True))
        if not _column_exists(inspector, "video", "deleted_at"):
            op.add_column("video", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # ---------------------------------------------------------------------
    # promotion_log
    # ---------------------------------------------------------------------
    if _table_exists(inspector, "promotion_log"):
        if not _column_exists(inspector, "promotion_log", "idempotency_key"):
            op.add_column("promotion_log", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        if not _column_exists(inspector, "promotion_log", "correlation_id"):
            op.add_column("promotion_log", sa.Column("correlation_id", sa.String(length=36), nullable=True))
        if not _column_exists(inspector, "promotion_log", "dry_run"):
            op.add_column(
                "promotion_log",
                sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if not _column_exists(inspector, "promotion_log", "error_message"):
            op.add_column("promotion_log", sa.Column("error_message", sa.Text(), nullable=True))
        if not _column_exists(inspector, "promotion_log", "metadata"):
            op.add_column("promotion_log", sa.Column("metadata", sa.JSON(), nullable=True))

    # ---------------------------------------------------------------------
    # training_run
    # ---------------------------------------------------------------------
    if _table_exists(inspector, "training_run"):
        if not _column_exists(inspector, "training_run", "started_at"):
            op.add_column("training_run", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        if not _column_exists(inspector, "training_run", "completed_at"):
            op.add_column("training_run", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        if not _column_exists(inspector, "training_run", "dataset_hash"):
            op.add_column("training_run", sa.Column("dataset_hash", sa.String(length=64), nullable=True))
        if not _column_exists(inspector, "training_run", "mlflow_run_id"):
            op.add_column("training_run", sa.Column("mlflow_run_id", sa.String(length=255), nullable=True))
        if not _column_exists(inspector, "training_run", "model_path"):
            op.add_column("training_run", sa.Column("model_path", sa.String(length=500), nullable=True))
        if not _column_exists(inspector, "training_run", "engine_path"):
            op.add_column("training_run", sa.Column("engine_path", sa.String(length=500), nullable=True))
        if not _column_exists(inspector, "training_run", "metrics"):
            op.add_column("training_run", sa.Column("metrics", sa.JSON(), nullable=True))
        if not _column_exists(inspector, "training_run", "config"):
            op.add_column("training_run", sa.Column("config", sa.JSON(), nullable=True))
        if not _column_exists(inspector, "training_run", "error_message"):
            op.add_column("training_run", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    # Intentionally no-op: this migration backfills live schema drift and is
    # designed to be safe on heterogeneous environments.
    pass

