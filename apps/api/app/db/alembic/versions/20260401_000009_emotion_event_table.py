"""Add emotion_event table for Phase 3 edge event persistence.

Stores real-time emotion detection events streamed from Jetson devices.
Used for analytics, Gate C metrics, and observability.

Revision ID: 20260401_000009
Revises: 20260228_000008
Create Date: 2026-04-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260401_000009"
down_revision = "20260228_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotion_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("emotion", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("inference_ms", sa.Float, nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column(
            "device_ts",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "meta",
            sa.dialects.postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "emotion IN ('happy', 'sad', 'neutral')",
            name="chk_emotion_event_label",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="chk_emotion_event_confidence",
        ),
    )

    op.create_index("ix_emotion_event_device_ts", "emotion_event", ["device_id", "created_at"])
    op.create_index("ix_emotion_event_session", "emotion_event", ["session_id"])
    op.create_index("ix_emotion_event_emotion", "emotion_event", ["emotion"])


def downgrade() -> None:
    op.drop_index("ix_emotion_event_emotion", table_name="emotion_event")
    op.drop_index("ix_emotion_event_session", table_name="emotion_event")
    op.drop_index("ix_emotion_event_device_ts", table_name="emotion_event")
    op.drop_table("emotion_event")
