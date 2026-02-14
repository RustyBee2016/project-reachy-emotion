# Database Setup Guide

This guide walks you through setting up the PostgreSQL database for development and testing.

> **Important — Schema Management Change (v08.4.2)**
>
> The database schema is now managed exclusively through **SQLAlchemy models + Alembic migrations**.
> The legacy SQL files (`001_phase1_schema.sql`, `002_stored_procedures.sql`, `003_missing_tables.sql`)
> are retained for historical reference only and should **not** be used to create or modify the schema.
>
> **Authoritative source files:**
>
> | File | Purpose |
> |------|---------|
> | `apps/api/app/db/models.py` | Python classes that define every table, column, constraint, and relationship |
> | `apps/api/app/db/enums.py` | Enum value definitions (`video_split_enum`, `emotion_enum`, `training_selection_target_enum`) |
> | `apps/api/app/db/base.py` | `Base` class and `TimestampMixin` shared by all models |
> | `apps/api/app/db/alembic/versions/202510280000_initial_schema.py` | Alembic migration that translates the models into SQL DDL |

## Prerequisites

- Ubuntu 20.04+ or macOS
- PostgreSQL 15 or 16
- Python 3.10+
- Git
- Python dependencies installed (`pip install -r requirements-phase1.txt`)

---

## Quick Start (5 Minutes)

### Option 1: Docker (Fastest)

```bash
# Start PostgreSQL in Docker
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

# Verify — should list the tables created by the migration
psql -h localhost -U reachy_app -d reachy_local -c "\dt"
```

### Option 2: Native PostgreSQL

```bash
# Install PostgreSQL (Ubuntu)
sudo apt update
sudo apt install postgresql-16 postgresql-client-16

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE reachy_local OWNER postgres;
CREATE ROLE reachy_app WITH LOGIN PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;
GRANT ALL PRIVILEGES ON SCHEMA public TO reachy_app;
EOF

# Install Python dependencies (if not already done)
pip install -r requirements-phase1.txt

# Apply schema via Alembic
alembic -c apps/api/app/db/alembic.ini upgrade head
```

---

## How Tables Get Created — Step by Step

If you are new to PostgreSQL and wondering "where do the tables come from?", here is exactly
what happens when you run `alembic upgrade head`:

```
Step 1                Step 2                Step 3                Step 4
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  enums.py    │     │  models.py   │     │  env.py      │     │  Alembic     │
│              │     │              │     │              │     │  migration   │
│ Defines the  │────▶│ Defines      │────▶│ Imports Base │────▶│ upgrade()    │
│ allowed      │     │ Python       │     │ .metadata +  │     │ emits SQL:   │
│ values for   │     │ classes that │     │ all models   │     │ CREATE TABLE │
│ split, label │     │ map to DB    │     │ so Alembic   │     │ CREATE INDEX │
│ etc.         │     │ tables       │     │ knows the    │     │ etc.         │
└──────────────┘     └──────────────┘     │ target schema│     └──────┬───────┘
                                          └──────────────┘            │
                                                                      ▼
                                                              ┌──────────────┐
                                                              │ PostgreSQL   │
                                                              │              │
                                                              │ Tables now   │
                                                              │ exist in the │
                                                              │ database     │
                                                              └──────────────┘
```

1. **`enums.py`** — Defines allowed values for `split` (`temp`, `dataset_all`, `train`, `test`, `purged`),
   `label` (`neutral`, `happy`, `sad`, `angry`, `surprise`, `fearful`), and `target_split`.
   Uses `native_enum=False`, meaning PostgreSQL enforces these via CHECK constraints rather than
   native ENUM types.

2. **`models.py`** — Each Python class (e.g., `class Video(TimestampMixin, Base)`) maps to one
   database table. Columns, types, constraints, indexes, and relationships are all declared here.

3. **`base.py`** — Provides the `Base` class (SQLAlchemy's `DeclarativeBase`) and `TimestampMixin`
   which adds `created_at` / `updated_at` columns to every model that inherits it.

4. **`alembic/env.py`** — Imports `Base.metadata` and all models, making Alembic aware of the
   desired schema.

5. **`202510280000_initial_schema.py`** — The migration file containing `upgrade()` and `downgrade()`
   functions. `upgrade()` calls `op.create_table()`, `op.create_index()`, etc.

6. **`alembic upgrade head`** — Executes the `upgrade()` function, which sends SQL DDL to PostgreSQL.
   After this command completes, the tables exist in the database.

---

## Understanding the Two Paths (Legacy vs Current)

You will see two sets of schema files in the repository. Here is how they relate:

| | Legacy SQL Path (DEPRECATED) | Current Alembic Path (AUTHORITATIVE) |
|---|---|---|
| **Schema definition** | `alembic/versions/001_phase1_schema.sql` | `apps/api/app/db/models.py` + `enums.py` |
| **Migration tool** | `psql -f <file>.sql` | `alembic upgrade head` |
| **Stored procedures** | `alembic/versions/002_stored_procedures.sql` | Python services (`PromoteService`, `VideoRepository`) |
| **Agent tables** | `alembic/versions/003_missing_tables.sql` | Defined in `models.py`; migration pending |
| **Status** | Retained for historical reference; header says DEPRECATED | Active; used by the application |

**Why do the legacy SQL files still exist?**
They are kept for historical reference so you can see how the schema evolved. The file
`001_phase1_schema.sql` has a DEPRECATED header at the top. **Do not run these files** to
set up a new database — use `alembic upgrade head` instead.

---

## Tables Created by Alembic

The current Alembic migration (`202510280000_initial_schema.py`) creates these **4 core tables**:

| # | Table | Purpose |
|---|-------|---------|
| 1 | `video` | Every video file registered in the system — metadata, split, label, checksum |
| 2 | `training_run` | Each ML training experiment — strategy, fractions, seed, metrics, status |
| 3 | `training_selection` | Which videos were selected for a specific training run (train/test assignment) |
| 4 | `promotion_log` | Audit trail of every video promotion between splits |

**5 additional tables** are defined in `models.py` but do not yet have Alembic migration revisions:

| # | Table | Purpose | Defined in `models.py` |
|---|-------|---------|----------------------|
| 5 | `label_event` | Audit trail of labeling actions (label, relabel, discard) | Yes (line 198) |
| 6 | `deployment_log` | Tracks model deployments to Jetson (engine version, metrics) | Yes (line 233) |
| 7 | `audit_log` | Privacy-sensitive operations (purge, access, export) | Yes (line 270) |
| 8 | `obs_samples` | Time-series observability metrics from all agents | Yes (line 305) |
| 9 | `reconcile_report` | Filesystem/database consistency check results | Yes (line 327) |

> **Next step for the team:** Generate the missing migration to create tables 5–9:
> ```bash
> alembic -c apps/api/app/db/alembic/alembic.ini revision --autogenerate -m "add agent workflow tables"
> alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
> ```

### How to Locate Tables in the Database

After running `alembic upgrade head`, connect and verify:

```bash
psql -U reachy_dev -d reachy_emotion
```

```sql
-- List all tables
\dt

-- Example output (after initial migration):
--              List of relations
--  Schema |       Name          | Type  |   Owner
-- --------+---------------------+-------+-----------
--  public | alembic_version     | table | reachy_app
--  public | promotion_log       | table | reachy_app
--  public | training_run        | table | reachy_app
--  public | training_selection  | table | reachy_app
--  public | video               | table | reachy_app

-- Describe a specific table to see its columns
\d video

-- List all indexes
\di

-- Exit psql
\q
```

### To change the owner of the tables to reachy_dev:
#### log in as the OS postgres user:
sudo -u postgres psql -d reachy_emotion

ALTER TABLE promotion_log      OWNER TO reachy_dev;
ALTER TABLE training_run       OWNER TO reachy_dev;
ALTER TABLE training_selection OWNER TO reachy_dev;

---

## Detailed Setup

### Step 1: Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-16 postgresql-contrib-16
```

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Verify installation:**
```bash
psql --version
# psql (PostgreSQL) 16.x
```

### Step 2: Start PostgreSQL Service

```bash
# Ubuntu
sudo systemctl start postgresql
sudo systemctl status postgresql

# macOS
brew services start postgresql@16
```

### Step 3: Create Database and Roles

```bash
# Connect as superuser
sudo -u postgres psql

# In psql:
CREATE DATABASE reachy_local OWNER postgres;
CREATE ROLE reachy_app WITH LOGIN PASSWORD 'your_secure_password';
CREATE ROLE reachy_read WITH LOGIN PASSWORD 'read_password';

GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;
\c reachy_local
GRANT ALL PRIVILEGES ON SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO reachy_app;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO reachy_read;

\q
```

### Step 4: Install Python Dependencies

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Install project dependencies (includes SQLAlchemy, Alembic, asyncpg)
pip install -r requirements-phase1.txt
```

### Step 5: Apply Migrations with Alembic

```bash
# From the project root
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

**What this does:**
- Reads the database URL from `alembic.ini` (or the `REACHY_DATABASE_URL` environment variable)
- Checks which migrations have already been applied (tracked in the `alembic_version` table)
- Runs any pending `upgrade()` functions to create tables, indexes, and constraints

### Step 6: Verify Installation

```bash
# Connect to database
psql -U reachy_app -d reachy_local

# List tables — should show video, training_run, training_selection, promotion_log, alembic_version
\dt

# Describe the video table to confirm columns and constraints
\d video

# Quick data test
SELECT count(*) FROM video;

# Exit
\q
```

### Step 7 (Optional): Apply Legacy Stored Procedures

The stored procedures in `002_stored_procedures.sql` provide useful SQL functions for
ad-hoc queries and manual operations (`get_class_distribution`, `check_dataset_balance`,
`promote_video_safe`, `create_training_run_with_sampling`). The application does **not**
require them (business logic runs in Python services), but they are helpful for manual
database exploration.

```bash
# Optional — only if you want SQL-based helper functions
psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql
```

---

## Configuration

### Environment Variables

Create `.env` file in `apps/api/`:

```bash
# apps/api/.env

# previous config:
# REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:dev_password@localhost:5432/reachy_local
# auto-generated config:
# REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:dev_password@localhost:5432/reachy_emotion
# actual config:
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql

# previous config:
# REACHY_VIDEOS_ROOT=/mnt/videos
# actual config:
REACHY_VIDEOS_ROOT=/media/rusty_admin/project_data/reachy_emotion/videos
REACHY_API_PORT=8083
```

> **Ubuntu 2 mount requirement:** mount the Ubuntu 1 export to `/mnt/videos` so both Media Mover and the gateway see the same files. In `/etc/fstab` on Ubuntu 2 add:
>
> ```fstab
> 10.0.4.130:/media/rusty_admin/project_data/reachy_emotion/videos  /mnt/videos  nfs  defaults  0  0
> ```
>
> After saving run `sudo mount -a` and verify `ls /mnt/videos` shows `temp/`, `dataset_all/`, etc.

### Python Configuration

The database URL is configured in `apps/api/app/config.py`:


# Previous config is wrong:
```python
class Settings(BaseSettings):
    REACHY_DATABASE_URL: str = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"
```

### Connection Strings & Gateway Health

| Use Case | Connection String |
|----------|-------------------|
| psql CLI | `psql -U reachy_dev -d reachy_emotion` |
| Python sync | `postgresql://reachy_dev:tweetwd4959@localhost:5432/reachy_emotion` |
| Python async | `postgresql+asyncpg://reachy_dev:tweetwd4959@localhost:5432/reachy_emotion` |
| Alembic | Configured in `apps/api/app/db/alembic/alembic.ini` or via `REACHY_DATABASE_URL` env var |

**Gateway health endpoints:** Ubuntu 2 exposes `/health` and `/ready` (no `/api` prefix). When Nginx fronts the service, these appear externally as `/healthz` and `/readyz`, while Media Mover on Ubuntu 1 uses `/api/v1/health`. Keep the distinction in mind when writing monitoring checks.

---

## Testing the Setup

### Test Database Connection

```python
# test_connection.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine(
        "postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql"
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        print(result.scalar())

asyncio.run(test())
```

##### Call the script:
```bash
python scripts/diagnostics/test_connection.py
```



### Test Table Existence

```sql
-- In psql: verify the core tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Verify the Alembic version tracking table
SELECT * FROM alembic_version;
-- Should show: 202510280000
```

### Insert Test Data

```sql
-- Insert test videos (sha256 and size_bytes are required)
INSERT INTO video (video_id, file_path, split, size_bytes, sha256) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'videos/test/001.mp4', 'temp', 1024000, 'abc123def456abc123def456abc123def456abc123def456abc123def456abcd0001'),
    ('a0000000-0000-0000-0000-000000000002', 'videos/test/002.mp4', 'temp', 2048000, 'abc123def456abc123def456abc123def456abc123def456abc123def456abcd0002');

-- Verify
SELECT video_id, file_path, split, size_bytes FROM video;

-- Cleanup
DELETE FROM video WHERE file_path LIKE 'videos/test/%';
```

---

## Troubleshooting

### Connection Refused

```
psql: error: connection to server at "localhost" (127.0.0.1), port 5432 failed:
Connection refused
```

**Fix:**
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### Authentication Failed

```
FATAL: password authentication failed for user "reachy_app"
```

**Fix:**
```bash
sudo -u postgres psql -c "ALTER USER reachy_app PASSWORD 'new_password';"
```

### Permission Denied

```
ERROR: permission denied for table video
```

**Fix:**
```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reachy_app;
```

### Database Does Not Exist

```
FATAL: database "reachy_local" does not exist
```

**Fix:**
```bash
sudo -u postgres createdb reachy_local
```

### Alembic: "Can't locate revision"

```
alembic.util.exc.CommandError: Can't locate revision identified by '...'
```

**Fix:** The `alembic_version` table references a migration that no longer exists. Reset it:
```bash
psql -U reachy_app -d reachy_local -c "DELETE FROM alembic_version;"
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

### Alembic: "Target database is not up to date"

```
ERROR: Target database is not up to date.
```

**Fix:** Apply pending migrations first:
```bash
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

### Alembic: Import Error

```
ModuleNotFoundError: No module named 'apps'
```

**Fix:** Run Alembic from the project root directory, and ensure your virtual environment is activated:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate  # or your virtualenv path
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

---

## Docker Compose Setup

For a complete development environment:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: reachy_postgres
    environment:
      POSTGRES_DB: reachy_local
      POSTGRES_USER: reachy_app
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U reachy_app -d reachy_local"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Usage:**
```bash
# Start PostgreSQL
docker-compose up -d

# Wait for health check to pass
docker-compose logs postgres

# Apply schema via Alembic (run from project root on host)
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head

# Connect
psql -h localhost -U reachy_app -d reachy_local

# Stop
docker-compose down

# Stop and remove data
docker-compose down -v
```

> **Note:** The previous Docker Compose configuration mounted `./alembic/versions` into
> `/docker-entrypoint-initdb.d` to auto-apply the legacy SQL files. This is no longer
> recommended. Instead, start the container and then run `alembic upgrade head` from the host.

---

## Resetting the Database

### Drop and Recreate

```bash
# Drop database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS reachy_local;"

# Recreate
sudo -u postgres psql -c "CREATE DATABASE reachy_local OWNER reachy_app;"

# Reapply schema via Alembic
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

### Docker Reset

```bash
docker stop reachy_postgres
docker rm reachy_postgres
docker volume rm project-reachy-emotion_postgres_data

# Restart
docker-compose up -d

# Reapply schema
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
```

---

## Next Steps

1. Read the [Curriculum Overview](./curriculum/00-CURRICULUM-OVERVIEW.md) for the full learning path
2. Work through [Module 3: Reachy Schema](./curriculum/03-MODULE-REACHY-SCHEMA.md) to understand every table
3. Review [Known Issues](./07-KNOWN-ISSUES.md) for resolution status of historical schema discrepancies
