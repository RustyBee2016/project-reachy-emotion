"""Create tables for all ORM models not yet in the Alembic chain.

Tables created (all with IF NOT EXISTS guards for live DB safety):
- label_event   (R1 — labeling audit trail, Phase 1)
- run_link      (R2 — MLflow lineage, Phase 1)
- audit_log     (R5 — privacy audit, used by gateway_upstream.py)
- deployment_log (R8 — deployment tracking, used by gateway_upstream.py)
- obs_samples   (R8 — observability metrics, Phase 3)
- reconcile_report (R8 — reconciler agent, Phase 3)

Downgrade is intentionally no-op to avoid data loss.

Revision ID: 20260227_000005
Revises: 20260227_000004
Create Date: 2026-02-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260227_000005"
down_revision = "20260227_000004"
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

    # -----------------------------------------------------------------
    # R1: label_event — labeling audit trail
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "label_event"):
        op.create_table(
            "label_event",
            # Integer (not BigInteger) for SQLite autoincrement compat;
            # PostgreSQL uses SERIAL which is sufficient for audit logs.
            sa.Column(
                "event_id", sa.Integer(), primary_key=True, autoincrement=True
            ),
            sa.Column(
                "video_id",
                sa.String(length=36),
                sa.ForeignKey("video.video_id", ondelete="SET NULL"),
                nullable=True,
            ),
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
                nullable=False,
            ),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("rater_id", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "idempotency_key",
                sa.String(length=64),
                unique=True,
                nullable=True,
            ),
            sa.Column("correlation_id", sa.String(length=36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "action IN ('label_only','promote_train','promote_test',"
                "'discard','relabel')",
                name="chk_label_event_action",
            ),
        )

    if not _index_exists(inspector, "label_event", "ix_label_event_video"):
        op.create_index("ix_label_event_video", "label_event", ["video_id"])
    if not _index_exists(inspector, "label_event", "ix_label_event_created"):
        op.create_index("ix_label_event_created", "label_event", ["created_at"])
    if not _index_exists(inspector, "label_event", "ix_label_event_idempotency"):
        op.create_index(
            "ix_label_event_idempotency", "label_event", ["idempotency_key"]
        )

    # -----------------------------------------------------------------
    # R2: run_link — MLflow lineage
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "run_link"):
        op.create_table(
            "run_link",
            sa.Column("mlflow_run_id", sa.Text(), primary_key=True),
            sa.Column("dataset_hash", sa.Text(), nullable=False),
            sa.Column("snapshot_ref", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # -----------------------------------------------------------------
    # R5: audit_log — privacy audit trail
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column(
                "entity_type",
                sa.String(length=50),
                nullable=False,
                server_default="video",
            ),
            sa.Column("entity_id", sa.String(length=36), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("operator", sa.String(length=255), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("correlation_id", sa.String(length=36), nullable=True),
        )

    if not _index_exists(inspector, "audit_log", "ix_audit_action"):
        op.create_index("ix_audit_action", "audit_log", ["action"])
    if not _index_exists(inspector, "audit_log", "ix_audit_entity"):
        op.create_index(
            "ix_audit_entity", "audit_log", ["entity_type", "entity_id"]
        )
    if not _index_exists(inspector, "audit_log", "ix_audit_timestamp"):
        op.create_index("ix_audit_timestamp", "audit_log", ["timestamp"])

    # -----------------------------------------------------------------
    # R8: deployment_log — deployment tracking
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "deployment_log"):
        op.create_table(
            "deployment_log",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("engine_path", sa.String(length=500), nullable=False),
            sa.Column("model_version", sa.String(length=100), nullable=True),
            sa.Column("target_stage", sa.String(length=50), nullable=False),
            sa.Column(
                "deployed_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(length=50),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("rollback_from", sa.String(length=500), nullable=True),
            sa.Column("mlflow_run_id", sa.String(length=255), nullable=True),
            sa.Column("gate_b_passed", sa.Boolean(), nullable=True),
            sa.Column("fps_measured", sa.Numeric(6, 2), nullable=True),
            sa.Column("latency_p50_ms", sa.Numeric(8, 2), nullable=True),
            sa.Column("latency_p95_ms", sa.Numeric(8, 2), nullable=True),
            sa.Column("gpu_memory_gb", sa.Numeric(4, 2), nullable=True),
            sa.Column("correlation_id", sa.String(length=36), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.CheckConstraint(
                "target_stage IN ('shadow','canary','rollout')",
                name="chk_deployment_stage",
            ),
            sa.CheckConstraint(
                "status IN ('pending','deploying','success','failed','rolled_back')",
                name="chk_deployment_status",
            ),
        )

    if not _index_exists(inspector, "deployment_log", "ix_deployment_stage"):
        op.create_index(
            "ix_deployment_stage", "deployment_log", ["target_stage"]
        )
    if not _index_exists(inspector, "deployment_log", "ix_deployment_status"):
        op.create_index("ix_deployment_status", "deployment_log", ["status"])
    if not _index_exists(inspector, "deployment_log", "ix_deployment_time"):
        op.create_index("ix_deployment_time", "deployment_log", ["deployed_at"])

    # -----------------------------------------------------------------
    # R8: obs_samples — observability metrics
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "obs_samples"):
        op.create_table(
            "obs_samples",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "ts",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("src", sa.String(length=100), nullable=False),
            sa.Column("metric", sa.String(length=100), nullable=False),
            sa.Column("value", sa.Numeric(15, 4), nullable=True),
            sa.Column("labels", sa.JSON(), nullable=True),
        )

    if not _index_exists(inspector, "obs_samples", "ix_obs_ts"):
        op.create_index("ix_obs_ts", "obs_samples", ["ts"])
    if not _index_exists(inspector, "obs_samples", "ix_obs_src_metric"):
        op.create_index("ix_obs_src_metric", "obs_samples", ["src", "metric"])

    # -----------------------------------------------------------------
    # R8: reconcile_report — reconciler agent
    # -----------------------------------------------------------------
    if not _table_exists(inspector, "reconcile_report"):
        op.create_table(
            "reconcile_report",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "run_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("trigger_type", sa.String(length=50), nullable=False),
            sa.Column(
                "orphan_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "missing_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "mismatch_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "drift_detected",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "auto_fixed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("correlation_id", sa.String(length=36), nullable=True),
            sa.CheckConstraint(
                "trigger_type IN ('scheduled','manual','webhook')",
                name="chk_reconcile_trigger",
            ),
        )

    if not _index_exists(inspector, "reconcile_report", "ix_reconcile_time"):
        op.create_index("ix_reconcile_time", "reconcile_report", ["run_at"])
    if not _index_exists(inspector, "reconcile_report", "ix_reconcile_drift"):
        op.create_index(
            "ix_reconcile_drift", "reconcile_report", ["drift_detected"]
        )


def downgrade() -> None:
    # Intentionally no-op: do not drop data-bearing tables.
    # Matches pattern from 20260218_000002 and 20260223_000003.
    pass
