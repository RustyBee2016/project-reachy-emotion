# Module 7: Migrations & DevOps

**Duration**: 3 hours
**Prerequisites**: Modules 1-6
**Goal**: Manage database schema changes and deployment

---

## Learning Objectives

By the end of this module, you will be able to:
1. Apply database migrations using SQL files
2. Use Alembic for automated migrations
3. Set up the database for development
4. Backup and restore databases
5. Monitor database health

---

## Lesson 7.1: Migration Strategies (30 minutes)

### Why Migrations?

As your application evolves, the database schema changes:
- New tables needed
- Columns added/removed
- Constraints modified
- Indexes optimized

**Migrations** track these changes in version control.

### Two Approaches in Reachy

| Approach | Files | Best For |
|----------|-------|----------|
| Manual SQL | `alembic/versions/*.sql` | Production, PostgreSQL-specific features |
| Alembic | `apps/api/app/db/alembic/` | Development, cross-database compatibility |

---

## Lesson 7.2: Manual SQL Migrations (45 minutes)

### The SQL Migration Files

```
alembic/versions/
├── 001_phase1_schema.sql      # Core tables (193 lines)
├── 002_stored_procedures.sql  # Functions (362 lines)
└── 003_missing_tables.sql     # Agent tables (297 lines)
```

### Applying Migrations

```bash
# Connect to PostgreSQL
psql -U reachy_app -d reachy_local

# Apply in order
\i alembic/versions/001_phase1_schema.sql
\i alembic/versions/002_stored_procedures.sql
\i alembic/versions/003_missing_tables.sql

# Or from command line
psql -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -d reachy_local -f alembic/versions/003_missing_tables.sql
```

### Idempotent Migrations

The SQL files use `IF NOT EXISTS` for safety:

```sql
-- From 001_phase1_schema.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS video (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ...
);

CREATE INDEX IF NOT EXISTS idx_video_split ON video(split);
```

**Idempotent** = Can run multiple times safely without errors.

### Creating New Migrations

When adding new features:

```sql
-- 004_new_feature.sql

-- Add new column
ALTER TABLE video ADD COLUMN IF NOT EXISTS
    processing_status VARCHAR(50) DEFAULT 'pending';

-- Add new table
CREATE TABLE IF NOT EXISTS processing_job (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES video(video_id),
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add new index
CREATE INDEX IF NOT EXISTS idx_processing_job_status
ON processing_job(status);
```

---

## Lesson 7.3: Alembic Migrations (45 minutes)

### What is Alembic?

**Alembic** is SQLAlchemy's migration tool. It:
- Auto-generates migrations from model changes
- Tracks applied migrations in database
- Supports upgrade and downgrade

### Alembic Structure

```
apps/api/app/db/alembic/
├── alembic.ini              # Configuration
├── env.py                   # Migration environment
└── versions/
    └── 202510280000_initial_schema.py  # Migration file
```

### Configuration

**Source**: `alembic.ini`
```ini
[alembic]
script_location = apps/api/app/db/alembic
sqlalchemy.url = postgresql+asyncpg://reachy_app:password@localhost/reachy_local
```

### Running Migrations

```bash
# Navigate to project root
cd /home/user/project-reachy-emotion

# Check current version
alembic current

# See pending migrations
alembic history

# Apply all migrations
alembic upgrade head

# Apply one migration
alembic upgrade +1

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123
```

### Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "add processing status"

# Create empty migration
alembic revision -m "custom migration"
```

### Migration File Structure

**Source**: `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`

```python
"""Initial schema

Revision ID: 202510280000
Revises:
Create Date: 2025-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '202510280000'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enum types
    split_enum = sa.Enum('temp', 'dataset_all', 'train', 'test',
                         name='video_split_enum')
    split_enum.create(op.get_bind(), checkfirst=True)

    # Create tables
    op.create_table(
        'video',
        sa.Column('video_id', sa.String(36), primary_key=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('split', split_enum, nullable=False, server_default='temp'),
        sa.Column('label', sa.String(50), nullable=True),
        sa.Column('size_bytes', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_video_split', 'video', ['split'])

def downgrade():
    # Drop in reverse order
    op.drop_index('idx_video_split')
    op.drop_table('video')

    # Drop enum
    sa.Enum(name='video_split_enum').drop(op.get_bind(), checkfirst=True)
```

---

### Migration Pitfalls: Known Issues

When working with migrations, be aware of these synchronization issues:

> ⚠️ **Reminder: Issue #3 - Check Constraint Inconsistency**
>
> The Alembic migration is missing `'purged'` in the check constraint.
> Ensure your migration includes:
> ```python
> CheckConstraint(
>     "(split IN ('temp', 'test', 'purged') AND label IS NULL) OR ..."
> )
> ```
>
> See: Module 03 and `docs/database/07-KNOWN-ISSUES.md` for details.

> ⚠️ **Reminder: Issue #4 - Missing Check Constraint in SQL**
>
> The SQL schema files don't include the split/label policy constraint.
> If using SQL migrations, add:
> ```sql
> ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy CHECK (
>     (split IN ('temp', 'test', 'purged') AND label IS NULL)
>     OR (split IN ('dataset_all', 'train') AND label IS NOT NULL)
> );
> ```
>
> See: Module 03 and `docs/database/07-KNOWN-ISSUES.md` for details.

> ⚠️ **Reminder: Issue #9 - Enum Type Name Mismatch**
>
> SQL uses `video_split` and `emotion_label`, but Alembic uses `video_split_enum` and `emotion_enum`.
>
> **Risk**: Running both SQL and Alembic migrations creates duplicate enum types.
>
> **Best Practice**: Choose ONE migration approach per environment:
> - **Production**: Use SQL files only
> - **Development/Testing**: Use Alembic only
>
> See: Module 02 and `docs/database/07-KNOWN-ISSUES.md` for details.

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

# Apply migrations
psql -h localhost -U reachy_app -d reachy_local \
  -f alembic/versions/001_phase1_schema.sql
psql -h localhost -U reachy_app -d reachy_local \
  -f alembic/versions/002_stored_procedures.sql
psql -h localhost -U reachy_app -d reachy_local \
  -f alembic/versions/003_missing_tables.sql
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

# Apply migrations
for sql_file in alembic/versions/*.sql; do
    echo "Applying: $sql_file"
    psql -d reachy_local -f "$sql_file"
done

# Create directories
mkdir -p /mnt/videos/{temp,dataset_all,train,test}

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

- ✅ Apply SQL migrations manually
- ✅ Use Alembic for automated migrations
- ✅ Set up development environment
- ✅ Backup and restore databases
- ✅ Monitor database health

**Next**: [Module 8: Troubleshooting](./08-MODULE-TROUBLESHOOTING.md)
