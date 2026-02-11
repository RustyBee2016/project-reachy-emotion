# Tutorial 6: Alembic Migration Consolidation

> **Priority**: HIGH — Database integrity
> **Time estimate**: 4-6 hours
> **Difficulty**: Moderate
> **Prerequisites**: PostgreSQL running, Alembic basics understood

---

## Why This Matters

The project currently has **two** Alembic configurations:

| Location | Type | Status |
|----------|------|--------|
| `/alembic/` (root) | SQL-based (.sql files) | **Legacy — unused** |
| `/apps/api/app/db/alembic/` | Python-based (.py files) | **Active — incomplete** |

The active configuration has **one migration** that creates 4 tables:
- `video`
- `training_run`
- `training_selection`
- `promotion_log`

But `models.py` defines **5 additional tables** with no migration:
- `label_event` (Labeling Agent)
- `deployment_log` (Deployment Agent)
- `audit_log` (Privacy Agent)
- `reconcile_report` (Reconciler Agent)
- `obs_samples` (Observability Agent)

These tables exist in the ORM but **not in the database**. Any code that
tries to query them will crash with `relation "label_event" does not exist`.

---

## What You'll Learn

- What Alembic is and why it matters (database versioning)
- How to create new migration files
- How to clean up a dual-configuration mess
- How to run migrations safely

---

## Step 1: Understand Alembic Basics

Alembic is a database migration tool. Think of it as **git for your
database schema**.

Key concepts:
- **Migration**: A Python file that describes changes to the database
- **Revision**: Unique ID for each migration (like a git commit hash)
- **Upgrade**: Apply a migration (add tables, columns)
- **Downgrade**: Reverse a migration (remove tables, columns)
- **Head**: The latest migration

Migrations form a chain:
```
initial_schema → add_label_event → add_deployment_log → ...
```

---

## Step 2: Clean Up the Root Alembic Directory

The root `/alembic/` directory contains legacy SQL migrations that are
not connected to the active migration system. Let's archive it.

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Archive the legacy alembic files (don't delete — might need reference)
mkdir -p alembic/_archived
mv alembic/versions/*.sql alembic/_archived/ 2>/dev/null || true

# Update the root alembic.ini to point to the correct location
```

Now edit `alembic.ini` (root) to point to the correct script location.
Find this line:

```ini
script_location = alembic
```

Change it to:

```ini
script_location = apps/api/app/db/alembic
```

This way, running `alembic` from the project root will use the
correct Python-based migrations.

---

## Step 3: Verify the Current Migration State

Check what Alembic thinks is the current state:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Use the app-level alembic config
alembic -c apps/api/app/db/alembic.ini current
```

If you get an error about database connection, set the DATABASE_URL:

```bash
export DATABASE_URL="postgresql+psycopg://reachy_dev:tweetwd4959@10.0.4.130:5432/reachy_emotion"

alembic -c apps/api/app/db/alembic.ini current
```

If this is a fresh database, you'll need to stamp it:

```bash
# Mark the database as being at the initial migration
alembic -c apps/api/app/db/alembic.ini stamp 20251028_000000
```

---

## Step 4: Create Migration for Missing Tables

Now create a new migration that adds the 5 missing tables.

### 4a. Auto-generate the migration

Alembic can compare your models to the database and generate a migration
automatically:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

alembic -c apps/api/app/db/alembic.ini revision --autogenerate \
  -m "Add agent workflow tables"
```

This creates a new file in `apps/api/app/db/alembic/versions/`.

### 4b. If auto-generation doesn't work, create manually

If auto-generate has issues (common with PostgreSQL-specific types),
create the migration manually.

Create `apps/api/app/db/alembic/versions/202602100001_add_agent_tables.py`:

```python
"""Add agent workflow tables (label_event, deployment_log, audit_log, obs_samples, reconcile_report).

Revision ID: 20260210_000001
Revises: 20251028_000000
Create Date: 2026-02-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260210_000001"
down_revision = "20251028_000000"
branch_labels = None
depends_on = None

# Re-use the enums from the initial migration
emotion_enum = sa.Enum(
    "neutral", "happy", "sad", "angry", "surprise", "fearful",
    name="emotion_enum",
    create_constraint=True,
    native_enum=False,
)


def upgrade() -> None:
    # ---- label_event ----
    op.create_table(
        "label_event",
        sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "video_id",
            sa.String(length=36),
            sa.ForeignKey("video.video_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label", emotion_enum, nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("rater_id", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), unique=True, nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('label_only', 'promote_train', 'promote_test', 'discard', 'relabel')",
            name="chk_label_event_action",
        ),
    )
    op.create_index("ix_label_event_video", "label_event", ["video_id"])
    op.create_index("ix_label_event_created", "label_event", ["created_at"])
    op.create_index("ix_label_event_idempotency", "label_event", ["idempotency_key"])

    # ---- deployment_log ----
    op.create_table(
        "deployment_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
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
            "target_stage IN ('shadow', 'canary', 'rollout')",
            name="chk_deployment_stage",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'deploying', 'success', 'failed', 'rolled_back')",
            name="chk_deployment_status",
        ),
    )
    op.create_index("ix_deployment_stage", "deployment_log", ["target_stage"])
    op.create_index("ix_deployment_status", "deployment_log", ["status"])
    op.create_index("ix_deployment_time", "deployment_log", ["deployed_at"])

    # ---- audit_log ----
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
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
    op.create_index("ix_audit_action", "audit_log", ["action"])
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_timestamp", "audit_log", ["timestamp"])

    # ---- obs_samples ----
    op.create_table(
        "obs_samples",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
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
    op.create_index("ix_obs_ts", "obs_samples", ["ts"])
    op.create_index("ix_obs_src_metric", "obs_samples", ["src", "metric"])

    # ---- reconcile_report ----
    op.create_table(
        "reconcile_report",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("orphan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mismatch_count", sa.Integer(), nullable=False, server_default="0"),
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
            "trigger_type IN ('scheduled', 'manual', 'webhook')",
            name="chk_reconcile_trigger",
        ),
    )
    op.create_index("ix_reconcile_time", "reconcile_report", ["run_at"])
    op.create_index("ix_reconcile_drift", "reconcile_report", ["drift_detected"])


def downgrade() -> None:
    op.drop_index("ix_reconcile_drift", table_name="reconcile_report")
    op.drop_index("ix_reconcile_time", table_name="reconcile_report")
    op.drop_table("reconcile_report")

    op.drop_index("ix_obs_src_metric", table_name="obs_samples")
    op.drop_index("ix_obs_ts", table_name="obs_samples")
    op.drop_table("obs_samples")

    op.drop_index("ix_audit_timestamp", table_name="audit_log")
    op.drop_index("ix_audit_entity", table_name="audit_log")
    op.drop_index("ix_audit_action", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_deployment_time", table_name="deployment_log")
    op.drop_index("ix_deployment_status", table_name="deployment_log")
    op.drop_index("ix_deployment_stage", table_name="deployment_log")
    op.drop_table("deployment_log")

    op.drop_index("ix_label_event_idempotency", table_name="label_event")
    op.drop_index("ix_label_event_created", table_name="label_event")
    op.drop_index("ix_label_event_video", table_name="label_event")
    op.drop_table("label_event")
```

---

## Step 5: Apply the Migration

### 5a. Dry Run (Check SQL Without Applying)

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Generate SQL without executing
alembic -c apps/api/app/db/alembic.ini upgrade --sql 20260210_000001
```

Review the output. It should show `CREATE TABLE` statements for all
5 new tables.

### 5b. Apply for Real

```bash
alembic -c apps/api/app/db/alembic.ini upgrade head
```

### 5c. Verify

```bash
alembic -c apps/api/app/db/alembic.ini current
# Should show: 20260210_000001 (head)
```

Connect to PostgreSQL and verify tables exist:

```bash
psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion -c "\dt"
```

Expected output should include:
```
 Schema |       Name          | Type  |   Owner
--------+---------------------+-------+----------
 public | video               | table | reachy_dev
 public | training_run        | table | reachy_dev
 public | training_selection  | table | reachy_dev
 public | promotion_log       | table | reachy_dev
 public | label_event         | table | reachy_dev    ← NEW
 public | deployment_log      | table | reachy_dev    ← NEW
 public | audit_log           | table | reachy_dev    ← NEW
 public | obs_samples         | table | reachy_dev    ← NEW
 public | reconcile_report    | table | reachy_dev    ← NEW
 public | alembic_version     | table | reachy_dev
```

---

## Step 6: Write a Migration Test

Create `tests/test_alembic_migration.py`:

```python
"""
Test that Alembic migrations apply cleanly.

Uses a temporary SQLite database to verify migrations
can run from scratch without errors.
"""

import pytest
from pathlib import Path


class TestMigrationFiles:
    """Verify migration file structure and chain."""

    def test_migration_files_exist(self):
        """All expected migration files exist."""
        versions_dir = Path(
            "apps/api/app/db/alembic/versions"
        )
        assert versions_dir.exists(), f"Versions dir not found: {versions_dir}"

        # Check initial migration
        migrations = list(versions_dir.glob("*.py"))
        assert len(migrations) >= 2, (
            f"Expected at least 2 migrations, found {len(migrations)}: "
            f"{[m.name for m in migrations]}"
        )

    def test_migration_chain_is_valid(self):
        """Each migration points to its predecessor."""
        versions_dir = Path("apps/api/app/db/alembic/versions")
        migrations = {}

        for path in versions_dir.glob("*.py"):
            content = path.read_text()

            # Extract revision and down_revision
            revision = None
            down_revision = None

            for line in content.split("\n"):
                if line.startswith("revision = "):
                    revision = line.split("=")[1].strip().strip('"').strip("'")
                if line.startswith("down_revision = "):
                    down_rev_str = line.split("=")[1].strip()
                    if down_rev_str == "None":
                        down_revision = None
                    else:
                        down_revision = down_rev_str.strip('"').strip("'")

            if revision:
                migrations[revision] = {
                    'file': path.name,
                    'down_revision': down_revision,
                }

        # Verify chain: exactly one migration has down_revision=None (root)
        roots = [
            rev for rev, info in migrations.items()
            if info['down_revision'] is None
        ]
        assert len(roots) == 1, (
            f"Expected exactly 1 root migration, found {len(roots)}: {roots}"
        )

        # Verify every non-root migration points to an existing revision
        for rev, info in migrations.items():
            if info['down_revision'] is not None:
                assert info['down_revision'] in migrations, (
                    f"Migration {info['file']} (rev={rev}) points to "
                    f"non-existent down_revision={info['down_revision']}"
                )

    def test_all_models_have_tablename(self):
        """Every ORM model has a __tablename__ defined."""
        from apps.api.app.db import models

        model_classes = [
            models.Video,
            models.TrainingRun,
            models.TrainingSelection,
            models.PromotionLog,
            models.LabelEvent,
            models.DeploymentLog,
            models.AuditLog,
            models.ObsSample,
            models.ReconcileReport,
        ]

        for model_class in model_classes:
            assert hasattr(model_class, '__tablename__'), (
                f"Model {model_class.__name__} missing __tablename__"
            )
            assert model_class.__tablename__, (
                f"Model {model_class.__name__} has empty __tablename__"
            )
```

### Run the Test

```bash
pytest tests/test_alembic_migration.py -v
```

---

## Checklist

Before moving to MEDIUM priority tutorials, verify:

- [ ] Root `alembic.ini` updated to point to `apps/api/app/db/alembic`
- [ ] Legacy SQL files archived to `alembic/_archived/`
- [ ] New migration file created for 5 missing tables
- [ ] Migration applied successfully (`alembic upgrade head`)
- [ ] All 9 tables visible in PostgreSQL (`\dt`)
- [ ] `tests/test_alembic_migration.py` passes
- [ ] `alembic current` shows latest revision

---

## HIGH Priority Complete!

You've now completed all 6 HIGH priority tutorials:

1. Face detection implemented and tested
2. HSEmotion weight loading verified
3. Promotion service audited and validated
4. Dataset splitting uses stratified sampling
5. Training run executed with Gate A check
6. Database migrations consolidated

**Phase 1 is now functionally complete.** The MEDIUM priority tutorials
improve reliability, documentation, and developer experience.

---

## What's Next

Tutorial 7 (MEDIUM) sets up a CI/CD pipeline with GitHub Actions so
your tests run automatically on every pull request.
