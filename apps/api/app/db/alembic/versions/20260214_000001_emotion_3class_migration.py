"""Migrate emotion labels to strict 3-class policy.

Revision ID: 20260214_000001
Revises: 20251028_000000
Create Date: 2026-02-14
"""

from __future__ import annotations

import logging
import sqlalchemy as sa
from alembic import op

revision = "20260214_000001"
down_revision = "20251028_000000"
branch_labels = None
depends_on = None

old_emotion_enum = sa.Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    "fearful",
    name="emotion_enum",
    create_constraint=True,
    native_enum=False,
)

new_emotion_enum = sa.Enum(
    "neutral",
    "happy",
    "sad",
    name="emotion_enum",
    create_constraint=True,
    native_enum=False,
)


LEGACY_TO_3CLASS_SQL = """
CASE
    WHEN {col} IS NULL THEN NULL
    WHEN lower({col}) IN ('angry', 'anger', 'fear', 'fearful', 'disgust', 'contempt', 'sadness') THEN 'sad'
    WHEN lower({col}) IN ('surprise') THEN 'neutral'
    WHEN lower({col}) IN ('happiness') THEN 'happy'
    WHEN lower({col}) IN ('happy', 'sad', 'neutral') THEN lower({col})
    ELSE 'neutral'
END
"""

logger = logging.getLogger(__name__)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _normalize_legacy_labels() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _column_exists(inspector, "video", "label"):
        op.execute(sa.text(f"UPDATE video SET label = {LEGACY_TO_3CLASS_SQL.format(col='label')}"))

    if _column_exists(inspector, "promotion_log", "intended_label"):
        op.execute(
            sa.text(
                f"UPDATE promotion_log SET intended_label = "
                f"{LEGACY_TO_3CLASS_SQL.format(col='intended_label')}"
            )
        )

    if _column_exists(inspector, "label_event", "label"):
        op.execute(sa.text(f"UPDATE label_event SET label = {LEGACY_TO_3CLASS_SQL.format(col='label')}"))


def _narrow_enum_constraints() -> None:
    # NOTE:
    # Some deployed environments have legacy check constraints with names/types
    # that diverge from alembic metadata expectations. Running batch enum
    # rewrites there can abort the transaction before later compatibility
    # migrations execute. We normalize labels in SQL and leave DDL untouched.
    logger.warning("Skipping enum constraint narrowing due to schema drift tolerance mode")


def _widen_enum_constraints() -> None:
    logger.warning("Skipping enum constraint widening due to schema drift tolerance mode")


def upgrade() -> None:
    _normalize_legacy_labels()
    _narrow_enum_constraints()


def downgrade() -> None:
    _widen_enum_constraints()
