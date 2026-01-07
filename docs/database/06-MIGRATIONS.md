# Database Migrations

This document explains the database migration system and how to manage schema changes.

## What Are Migrations?

**Migrations** are versioned scripts that modify the database schema over time. They allow you to:
- Track schema changes in version control
- Apply changes consistently across environments
- Roll back changes if needed
- Collaborate on schema modifications

## Migration Approaches

The Reachy project supports TWO migration approaches:

### 1. Manual SQL Files (Production Recommended)

Direct SQL scripts for full control and PostgreSQL-specific features.

| File | Purpose | Lines |
|------|---------|-------|
| `alembic/versions/001_phase1_schema.sql` | Core tables | 193 |
| `alembic/versions/002_stored_procedures.sql` | Functions | 362 |
| `alembic/versions/003_missing_tables.sql` | Agent tables | 297 |

**Apply manually**:
```bash
psql -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -d reachy_local -f alembic/versions/003_missing_tables.sql
```

### 2. Alembic (Programmatic Migrations)

Python-based migrations using SQLAlchemy. Better for CI/CD and SQLite testing.

| File | Purpose |
|------|---------|
| `apps/api/app/db/alembic/env.py` | Alembic configuration |
| `apps/api/app/db/alembic/versions/202510280000_initial_schema.py` | Initial schema |

**Apply via Alembic**:
```bash
cd apps/api/app/db
alembic upgrade head
```

---

## SQL Migration Files

### 001_phase1_schema.sql

**Location**: `alembic/versions/001_phase1_schema.sql`

**Creates**:
- Extensions: `uuid-ossp`
- ENUMs: `video_split`, `emotion_label`, `training_status`
- Tables: `video`, `training_run`, `training_selection`, `promotion_log`, `user_session`, `generation_request`, `emotion_event`
- Triggers: `touch_updated_at()`
- Indexes on frequently queried columns

**Key Sections**:
```sql
-- Line 1-10: Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Line 13-28: ENUM types
CREATE TYPE video_split AS ENUM ('temp', 'dataset_all', 'train', 'test');
CREATE TYPE emotion_label AS ENUM ('neutral', 'happy', 'sad', 'angry', 'surprise', 'fearful');
CREATE TYPE training_status AS ENUM ('pending', 'sampling', 'training', ...);

-- Line 31-46: video table
CREATE TABLE IF NOT EXISTS video (...);

-- Line 180-193: Trigger setup
CREATE OR REPLACE FUNCTION touch_updated_at() ...
CREATE TRIGGER trg_video_updated ...
```

### 002_stored_procedures.sql

**Location**: `alembic/versions/002_stored_procedures.sql`

**Creates**:
- `get_class_distribution()`
- `check_dataset_balance()`
- `promote_video_safe()`
- `create_training_run_with_sampling()`
- `get_training_run_details()`

See [03-STORED-PROCEDURES.md](03-STORED-PROCEDURES.md) for details.

### 003_missing_tables.sql

**Location**: `alembic/versions/003_missing_tables.sql`

**Creates**:
- `label_event` - Labeling audit
- `deployment_log` - Model deployments
- `audit_log` - Privacy compliance
- `obs_samples` - Metrics
- `reconcile_report` - Filesystem consistency
- Additional stored procedures for agents
- Adds `purged` value to `video_split` enum

**Key Operations**:
```sql
-- Add enum value (must be done before any table references it)
ALTER TYPE video_split ADD VALUE IF NOT EXISTS 'purged';

-- Create agent support tables
CREATE TABLE IF NOT EXISTS label_event (...);
CREATE TABLE IF NOT EXISTS deployment_log (...);
```

---

## Alembic Migration System

### Configuration

**Location**: `apps/api/app/db/alembic/env.py`

```python
from alembic import context
from sqlalchemy import engine_from_config, pool
from apps.api.app.db.base import Base

# Target metadata for autogenerate
target_metadata = Base.metadata

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

### Initial Migration

**Location**: `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`

```python
"""Initial schema migration."""
from alembic import op
import sqlalchemy as sa

revision = "202510280000"
down_revision = None
branch_labels = None
depends_on = None

# ENUM definitions
split_enum = sa.Enum(
    "temp", "dataset_all", "train", "test",
    # NOTE: 'purged' is MISSING here!
    name="video_split_enum",
)

emotion_enum = sa.Enum(
    "neutral", "happy", "sad", "angry", "surprise",
    # NOTE: 'fearful' is MISSING here!
    name="emotion_enum",
)

def upgrade() -> None:
    # Create video table
    op.create_table(
        "video",
        sa.Column("video_id", sa.String(36), primary_key=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("split", split_enum, nullable=False, server_default="temp"),
        sa.Column("label", emotion_enum, nullable=True),
        # ... more columns
        sa.CheckConstraint(
            "(split IN ('temp', 'test') AND label IS NULL) OR ...",
            name="chk_video_split_label_policy",
        ),
    )
    # Create indexes
    op.create_index("idx_video_split", "video", ["split"])
    # ... more tables

def downgrade() -> None:
    op.drop_table("video")
    # ... drop other tables
```

---

## Running Migrations

### Fresh Database Setup

**Option 1: Manual SQL (Recommended for Production)**
```bash
# Connect to PostgreSQL
export PGHOST=localhost PGPORT=5432 PGUSER=postgres

# Create database
psql -c "CREATE DATABASE reachy_local OWNER postgres;"

# Run migrations in order
psql -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -d reachy_local -f alembic/versions/003_missing_tables.sql

# Verify
psql -d reachy_local -c "\dt"
```

**Option 2: Alembic**
```bash
cd apps/api/app/db

# Set database URL
export SQLALCHEMY_URL="postgresql://postgres:password@localhost:5432/reachy_local"

# Run all migrations
alembic upgrade head

# Verify current version
alembic current
```

### Check Current State

```bash
# Alembic version
alembic current

# List all migrations
alembic history

# Show pending migrations
alembic heads
```

### Rollback

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific version
alembic downgrade 202510280000

# Rollback all
alembic downgrade base
```

---

## Bootstrap Script

**Location**: `misc/code/bootstrap_reachy_db_and_media.sh`

A comprehensive script that sets up the complete environment:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Config
PGVER="${PGVER:-15}"
DB_NAME="${DB_NAME:-reachy_local}"
DB_OWNER="${DB_OWNER:-reachy_owner}"
APP_ROLE="${APP_ROLE:-reachy_app}"

# Create roles (idempotent)
psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_OWNER}') THEN
    CREATE ROLE ${DB_OWNER} LOGIN;
  END IF;
END
\$\$;
SQL

# Create database
psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_OWNER};"

# Create schema
psql -d "$DB_NAME" <<SQL
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS media AUTHORIZATION ${DB_OWNER};
CREATE TABLE IF NOT EXISTS media.video (...);
SQL
```

**Usage**:
```bash
cd /home/user/project-reachy-emotion
bash misc/code/bootstrap_reachy_db_and_media.sh
```

**Note**: This script creates a DIFFERENT schema (`media.video`) than the main SQL files (`public.video`). Be careful about which approach you use.

---

## Creating New Migrations

### SQL Approach

1. Create a new file with incremented number:
   ```
   alembic/versions/004_new_feature.sql
   ```

2. Use IF NOT EXISTS for idempotency:
   ```sql
   -- 004_new_feature.sql
   -- Add new column
   ALTER TABLE video ADD COLUMN IF NOT EXISTS new_field VARCHAR(100);

   -- Add new table
   CREATE TABLE IF NOT EXISTS new_table (...);
   ```

3. Document in commit message what changed

### Alembic Approach

1. Generate migration from model changes:
   ```bash
   alembic revision --autogenerate -m "Add new feature"
   ```

2. Review generated migration in `versions/`

3. Edit if needed (autogenerate isn't perfect)

4. Apply:
   ```bash
   alembic upgrade head
   ```

---

## Migration Best Practices

### DO

- Use `IF NOT EXISTS` / `IF EXISTS` for idempotency
- Test migrations on a copy of production data
- Back up before running migrations
- Run migrations in a transaction
- Document breaking changes

### DON'T

- Drop columns without a migration plan
- Change ENUM values in place (add new, migrate, then remove old)
- Run migrations during peak traffic
- Skip versions in sequence

### ENUM Changes

PostgreSQL ENUMs are tricky to modify:

```sql
-- Adding a value is easy
ALTER TYPE video_split ADD VALUE 'new_value';

-- Removing/renaming requires:
-- 1. Create new type
CREATE TYPE video_split_new AS ENUM ('temp', 'dataset_all', ...);

-- 2. Update column to use new type
ALTER TABLE video
  ALTER COLUMN split TYPE video_split_new
  USING split::text::video_split_new;

-- 3. Drop old type
DROP TYPE video_split;

-- 4. Rename new type
ALTER TYPE video_split_new RENAME TO video_split;
```

---

## Testing Migrations

**Source**: `tests/apps/api/db/test_migrations.py`

```python
import pytest
from alembic import command
from alembic.config import Config

def _alembic_config(db_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg

def test_upgrade_downgrade(tmp_path):
    """Test migrations can apply and rollback."""
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(f"sqlite:///{db_path}")

    # Upgrade
    command.upgrade(cfg, "head")

    # Downgrade
    command.downgrade(cfg, "base")
```

Run tests:
```bash
pytest tests/apps/api/db/test_migrations.py -v
```

---

## Troubleshooting

### Migration Failed Midway

```bash
# Check current state
alembic current

# Manually fix database if needed
psql -d reachy_local -c "DROP TABLE broken_table;"

# Retry migration
alembic upgrade head
```

### ENUM Type Already Exists

```sql
-- Check existing types
SELECT typname FROM pg_type WHERE typname LIKE '%enum%';

-- Drop if needed (CASCADE drops dependent columns!)
DROP TYPE IF EXISTS video_split_enum CASCADE;
```

### Column Already Exists

```sql
-- Safe add column
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'video' AND column_name = 'new_col'
  ) THEN
    ALTER TABLE video ADD COLUMN new_col VARCHAR(100);
  END IF;
END $$;
```

### Version Table Missing

```bash
# Alembic stores version in alembic_version table
# If missing, stamp current version
alembic stamp head
```

---

## Next Steps

- See [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for migration-related issues
- See [08-SETUP-GUIDE.md](08-SETUP-GUIDE.md) for complete setup instructions
