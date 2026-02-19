# Module 7: Migrations & DevOps

**Duration**: 3 hours
**Prerequisites**: Modules 1-6
**Goal**: Manage database schema changes and deployment using Alembic

---

## Learning Objectives

By the end of this module, you will be able to:
1. Understand how SQLAlchemy models become database tables via Alembic
2. Apply and manage Alembic migrations
3. Create new migrations when models change
4. Set up the database for development
5. Backup and restore databases
6. Monitor database health

---

## Lesson 7.1: Migration Strategies (30 minutes)

### Why Migrations?

As your application evolves, the database schema changes:
- New tables needed
- Columns added/removed
- Constraints modified
- Indexes optimized

**Migrations** track these changes in version control so every developer and environment
gets the same schema.

### The Reachy Migration Approach

Reachy uses **Alembic** (SQLAlchemy's migration tool) as the **single authoritative path**
for schema management:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  enums.py    │     │  models.py   │     │  Alembic     │     │  PostgreSQL  │
│              │     │              │     │  migration   │     │              │
│ Enum values  │────▶│ Python model │────▶│  upgrade()   │────▶│ CREATE TABLE │
│              │     │ classes      │     │  functions   │     │ CREATE INDEX │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

> **Historical note:** The repository also contains legacy SQL files (`001_phase1_schema.sql`,
> `002_stored_procedures.sql`, `003_missing_tables.sql`) in `alembic/versions/`. These are
> **deprecated** and retained for historical reference only. The file `001_phase1_schema.sql`
> has a DEPRECATED header. Do not use these files to create or modify the schema.
> See `docs/database/07-KNOWN-ISSUES.md` for the full story of why the project moved away
> from the dual SQL/Alembic approach.

---

## Lesson 7.2: Legacy SQL Files (Reference Only) (15 minutes)

> **⚠️ DEPRECATED — This section is for historical context only.**
>
> The legacy SQL files are no longer used for schema creation. They are retained so you can
> see how the schema evolved and understand the stored procedures available for ad-hoc queries.

### The Legacy SQL Files

```
alembic/versions/
├── 001_phase1_schema.sql      # DEPRECATED — replaced by 202510280000_initial_schema.py
├── 002_stored_procedures.sql  # Optional helper functions (still usable for ad-hoc queries)
└── 003_missing_tables.sql     # DEPRECATED — tables now defined in models.py
```

**`001_phase1_schema.sql`** — Originally created the core tables using raw SQL with native
PostgreSQL ENUM types. Now replaced by the Alembic migration backed by `models.py` and `enums.py`.

**`002_stored_procedures.sql`** — Contains SQL functions (`get_class_distribution`,
`check_dataset_balance`, `promote_video_safe`, `create_training_run_with_sampling`). These
are **not required** by the application (business logic runs in Python services) but remain
useful for manual database exploration. You may optionally apply this file after running
Alembic migrations.

**`003_missing_tables.sql`** — Originally added agent workflow tables. These tables are now
defined in `models.py` and will be created by a future Alembic migration.

### Idempotent SQL

The legacy SQL files used `IF NOT EXISTS` for safety:

```sql
CREATE TABLE IF NOT EXISTS video (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ...
);
```

**Idempotent** = Can run multiple times safely without errors. Alembic achieves this
differently — it tracks which migrations have been applied in the `alembic_version` table.

---

## Lesson 7.3: Alembic Migrations (60 minutes)

### What is Alembic?

**Alembic** is SQLAlchemy's migration tool. It:
- Auto-generates migrations from model changes
- Tracks applied migrations in the `alembic_version` database table
- Supports upgrade (apply) and downgrade (rollback)
- Ensures every environment gets the exact same schema

### How Alembic Knows the Target Schema

The key is in `env.py`:

**Source**: `apps/api/app/db/alembic/env.py` (lines 9-10)
```python
from apps.api.app.db.base import Base  # noqa: F401 - metadata import
from apps.api.app.db import models  # noqa: F401 - ensures model metadata is registered
```

By importing `Base` and `models`, Alembic loads all table definitions from `models.py` into
`Base.metadata`. When you run `alembic revision --autogenerate`, Alembic compares this
metadata against the actual database and generates the SQL needed to bring them in sync.

### Alembic Structure

```
apps/api/app/db/alembic/
├── alembic.ini              # Configuration (database URL, script location)
├── env.py                   # Migration environment (imports models)
└── versions/
    └── 202510280000_initial_schema.py  # Initial migration (creates 4 core tables)
```

### Configuration

**Source**: `apps/api/app/db/alembic/alembic.ini`
```ini
[alembic]
script_location = apps/api/app/db/alembic
sqlalchemy.url = postgresql+asyncpg://reachy_app:password@localhost/reachy_local
```

> **Tip:** You can override the database URL with the `REACHY_DATABASE_URL` environment
> variable instead of editing `alembic.ini`.

### Running Migrations

```bash
# All commands run from the project root directory
# Always specify the config file path:

# Check current migration version
alembic -c apps/api/app/db/alembic/alembic.ini current

# See migration history
alembic -c apps/api/app/db/alembic/alembic.ini history

# Apply all pending migrations
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head

# Apply one migration forward
alembic -c apps/api/app/db/alembic/alembic.ini upgrade +1

# Rollback one migration
alembic -c apps/api/app/db/alembic/alembic.ini downgrade -1

# Rollback to empty database
alembic -c apps/api/app/db/alembic/alembic.ini downgrade base
```

### Creating New Migrations

When you modify `models.py` (add a table, add a column, change a constraint), you need
a new migration:

```bash
# Step 1: Make your changes in models.py

# Step 2: Auto-generate a migration from the diff
alembic -c apps/api/app/db/alembic/alembic.ini revision --autogenerate -m "add processing status column"

# Step 3: Review the generated file in versions/
#         Alembic is good but not perfect — always review!

# Step 4: Apply the migration
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

### The Initial Migration — Walkthrough

**Source**: `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`

This migration creates the 4 core tables. Here is the structure (simplified):

```python
"""Initial schema for Media Mover

Revision ID: 202510280000
Revises:
Create Date: 2025-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "202510280000"
down_revision = None          # This is the first migration
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create enum-like constraints (using native_enum=False approach)
    split_enum = sa.Enum(
        "temp", "dataset_all", "train", "test", "purged",
        name="video_split_enum", create_constraint=True, native_enum=False
    )

    # 2. Create the video table
    op.create_table(
        "video",
        sa.Column("video_id", sa.String(length=36), primary_key=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("split", split_enum, nullable=False, server_default="temp"),
        sa.Column("label", emotion_enum, nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "(split IN ('temp', 'test', 'purged') AND label IS NULL) OR "
            "(split IN ('dataset_all', 'train') AND label IS NOT NULL)",
            name="chk_video_split_label_policy",
        ),
        sa.UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size"),
    )

    # 3. Create indexes
    op.create_index("ix_video_split", "video", ["split"])
    op.create_index("ix_video_label", "video", ["label"])

    # 4. Create training_run, training_selection, promotion_log tables...
    # (similar op.create_table calls)

def downgrade():
    # Drop everything in reverse order
    op.drop_table("promotion_log")
    op.drop_table("training_selection")
    op.drop_table("training_run")
    op.drop_index("ix_video_label")
    op.drop_index("ix_video_split")
    op.drop_table("video")
```

**Key points:**
- `upgrade()` creates tables — runs when you do `alembic upgrade head`
- `downgrade()` drops tables — runs when you do `alembic downgrade`
- `revision` and `down_revision` form a linked chain of migrations
- Enums use `native_enum=False` — enforced via CHECK constraints, not native PostgreSQL ENUMs

### Current Migration Gap

The initial migration creates **4 tables**: `video`, `training_run`, `training_selection`,
`promotion_log`.

However, `models.py` defines **9 tables** (the above 4 plus `label_event`, `deployment_log`,
`audit_log`, `obs_samples`, `reconcile_report`).

**The 5 additional tables need a new migration:**

```bash
# Generate the missing migration
alembic -c apps/api/app/db/alembic/alembic.ini revision --autogenerate -m "add agent workflow tables"

# Review the generated file, then apply
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

> **Historical note:** Issues #3, #4, and #9 from the Known Issues document described
> inconsistencies between the legacy SQL files and the Alembic migration. These are now
> **resolved** — the Alembic migration includes `purged` in the check constraint, and the
> legacy SQL files are deprecated. See `docs/database/07-KNOWN-ISSUES.md` for details.

---

## Lesson 7.4: Development Setup (30 minutes)

### Quick Start with Docker

```bash
# Start PostgreSQL
docker run -d \
  --name reachy_postgres \
  -e POSTGRES_DB=reachy_local \
  -e POSTGRES_USER=reachy_app \
  -e POSTGRES_PASSWORD=dev_password \
  -p 5432:5432 \
  postgres:16

# Wait for startup
sleep 5

# Install Python dependencies (if not already done)
pip install -r requirements-phase1.txt

# Apply schema via Alembic
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head

# Verify
psql -h localhost -U reachy_app -d reachy_local -c "\dt"
```

### Bootstrap Script

**Source**: `misc/code/bootstrap_reachy_db_and_media.sh`

```bash
#!/bin/bash
# Full setup script for Reachy development environment

# Create database
sudo -u postgres psql <<EOF
CREATE DATABASE reachy_local OWNER postgres;
CREATE ROLE reachy_app WITH LOGIN PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;
EOF

# Apply schema via Alembic
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head

# Optionally apply stored procedures for ad-hoc queries
# psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql

# Create directories
mkdir -p /mnt/videos/{temp,train,test,thumbs,manifests}
# Optional legacy compatibility only:
# mkdir -p /mnt/videos/dataset_all

echo "Setup complete!"
```

### Environment Configuration

Create `.env` file:
```bash
# apps/api/.env
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:dev_password@localhost:5432/reachy_local
REACHY_VIDEOS_ROOT=/mnt/videos
REACHY_API_PORT=8083
```

---

## Lesson 7.5: Backup and Restore (30 minutes)

### Creating Backups

```bash
# Full database backup
pg_dump -U reachy_app -d reachy_local > backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump -U reachy_app -d reachy_local | gzip > backup_$(date +%Y%m%d).sql.gz

# Schema only (no data)
pg_dump -U reachy_app -d reachy_local --schema-only > schema_backup.sql

# Data only (no schema)
pg_dump -U reachy_app -d reachy_local --data-only > data_backup.sql

# Specific tables
pg_dump -U reachy_app -d reachy_local -t video -t training_run > tables_backup.sql
```

### Restoring from Backup

```bash
# Restore to existing database
psql -U reachy_app -d reachy_local < backup_20250105.sql

# Restore compressed backup
gunzip -c backup_20250105.sql.gz | psql -U reachy_app -d reachy_local

# Create new database and restore
createdb -U postgres reachy_restored
psql -U reachy_app -d reachy_restored < backup_20250105.sql
```

### Automated Backups

```bash
#!/bin/bash
# backup_cron.sh - Add to crontab

BACKUP_DIR=/var/backups/postgresql
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -U reachy_app -d reachy_local | gzip > $BACKUP_DIR/reachy_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "reachy_*.sql.gz" -mtime +7 -delete
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup_cron.sh
```

---

## Lesson 7.6: Monitoring (30 minutes)

### Check Database Size

```sql
-- Database size
SELECT pg_size_pretty(pg_database_size('reachy_local'));

-- Table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;

-- Index sizes
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;
```

### Check Active Connections

```sql
-- Current connections
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    query
FROM pg_stat_activity
WHERE datname = 'reachy_local';

-- Connection counts
SELECT count(*) as connections FROM pg_stat_activity WHERE datname = 'reachy_local';
```

### Check Slow Queries

```sql
-- Enable query logging (in postgresql.conf)
-- log_min_duration_statement = 1000  # Log queries > 1 second

-- View slow query log
SELECT
    query,
    calls,
    total_time / 1000 as total_seconds,
    mean_time / 1000 as avg_seconds
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

### Health Check Endpoint

```python
@app.get("/health/db")
async def db_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## Knowledge Check

1. What does `IF NOT EXISTS` do in a CREATE TABLE statement?
2. What command applies all pending Alembic migrations?
3. How do you create a full database backup?
4. What's the difference between `upgrade` and `downgrade` in Alembic?

<details>
<summary>Click to see answers</summary>

1. Makes the statement idempotent - it only creates the table if it doesn't already exist, preventing errors on re-run.

2. `alembic upgrade head`

3. `pg_dump -U username -d database_name > backup.sql`

4. `upgrade` applies migrations forward (creates tables, adds columns). `downgrade` reverses migrations (drops tables, removes columns).

</details>

---

## Summary

In this module, you learned:

- ✅ How SQLAlchemy models become database tables via Alembic
- ✅ Apply and manage Alembic migrations (`upgrade head`, `downgrade`, `history`)
- ✅ Create new migrations when models change (`revision --autogenerate`)
- ✅ Set up development environment using Alembic
- ✅ Backup and restore databases
- ✅ Monitor database health

**Next**: [Module 8: Troubleshooting](./08-MODULE-TROUBLESHOOTING.md)
