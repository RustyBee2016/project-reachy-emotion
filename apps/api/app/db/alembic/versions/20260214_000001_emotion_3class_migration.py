"""Migrate emotion labels to strict 3-class policy.

Revision ID: 20260214_000001
Revises: 20251028_000000
Create Date: 2026-02-14
"""

from __future__ import annotations

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _column_exists(inspector, "video", "label"):
        with op.batch_alter_table("video") as batch_op:
            batch_op.alter_column(
                "label",
                existing_type=old_emotion_enum,
                type_=new_emotion_enum,
                existing_nullable=True,
            )
            batch_op.create_check_constraint(
                "chk_video_split_label_policy",
                """
                (
                    split IN ('temp', 'test', 'purged') AND label IS NULL
                ) OR (
                    split IN ('dataset_all', 'train') AND label IS NOT NULL
                )
                """,
            )

    if _column_exists(inspector, "promotion_log", "intended_label"):
        with op.batch_alter_table("promotion_log") as batch_op:
            batch_op.alter_column(
                "intended_label",
                existing_type=old_emotion_enum,
                type_=new_emotion_enum,
                existing_nullable=True,
            )

    if _column_exists(inspector, "label_event", "label"):
        with op.batch_alter_table("label_event") as batch_op:
            batch_op.alter_column(
                "label",
                existing_type=old_emotion_enum,
                type_=new_emotion_enum,
                existing_nullable=False,
            )


def _widen_enum_constraints() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _column_exists(inspector, "video", "label"):
        with op.batch_alter_table("video") as batch_op:
            batch_op.alter_column(
                "label",
                existing_type=new_emotion_enum,
                type_=old_emotion_enum,
                existing_nullable=True,
            )
            batch_op.create_check_constraint(
                "chk_video_split_label_policy",
                """
                (
                    split IN ('temp', 'test', 'purged') AND label IS NULL
                ) OR (
                    split IN ('dataset_all', 'train') AND label IS NOT NULL
                )
                """,
            )

    if _column_exists(inspector, "promotion_log", "intended_label"):
        with op.batch_alter_table("promotion_log") as batch_op:
            batch_op.alter_column(
                "intended_label",
                existing_type=new_emotion_enum,
                type_=old_emotion_enum,
                existing_nullable=True,
            )

    if _column_exists(inspector, "label_event", "label"):
        with op.batch_alter_table("label_event") as batch_op:
            batch_op.alter_column(
                "label",
                existing_type=new_emotion_enum,
                type_=old_emotion_enum,
                existing_nullable=False,
            )


def upgrade() -> None:
    _normalize_legacy_labels()
    _narrow_enum_constraints()


def downgrade() -> None:
    _widen_enum_constraints()
