# Database Setup Guide

This guide walks you through setting up the PostgreSQL database for development and testing.

## Prerequisites

- Ubuntu 20.04+ or macOS
- PostgreSQL 15 or 16
- Python 3.10+
- Git

## Quick Start (5 Minutes)

### Option 1: Docker (Fastest)

```bash
# Start PostgreSQL in Docker
docker run -d \
  --name reachy_postgres \
  -e POSTGRES_DB=reachy_local \
  -e POSTGRES_USER=reachy_app \
  -e POSTGRES_PASSWORD=reachy_password \
  -p 5432:5432 \
  postgres:16

# Wait for startup
sleep 5

# Apply migrations
docker exec -i reachy_postgres psql -U reachy_app -d reachy_local < alembic/versions/001_phase1_schema.sql
docker exec -i reachy_postgres psql -U reachy_app -d reachy_local < alembic/versions/002_stored_procedures.sql
docker exec -i reachy_postgres psql -U reachy_app -d reachy_local < alembic/versions/003_missing_tables.sql

# Verify
docker exec -it reachy_postgres psql -U reachy_app -d reachy_local -c "\dt"
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
sudo -u postgres psql <<SQL
CREATE DATABASE reachy_local;
CREATE USER reachy_app WITH PASSWORD 'reachy_password';
GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;
SQL

# Apply migrations
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/003_missing_tables.sql
```

---

## Detailed Setup

### Step 1: Install PostgreSQL

**Ubuntu/Debian**:
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Install
sudo apt update
sudo apt install postgresql-16 postgresql-contrib-16

# Verify
psql --version
# psql (PostgreSQL) 16.x
```

**macOS**:
```bash
brew install postgresql@16
brew services start postgresql@16
```

### Step 2: Start PostgreSQL Service

```bash
# Start
sudo systemctl start postgresql

# Enable on boot
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

### Step 3: Create Database and Roles

```bash
# Connect as postgres superuser
sudo -u postgres psql

# In psql:
```

```sql
-- Create database
CREATE DATABASE reachy_local OWNER postgres;

-- Create application role (for API)
CREATE ROLE reachy_app WITH LOGIN PASSWORD 'reachy_secure_password';
GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;

-- Create read-only role (for dashboards)
CREATE ROLE reachy_read WITH LOGIN PASSWORD 'reachy_read_password';
GRANT CONNECT ON DATABASE reachy_local TO reachy_read;

-- Connect to database
\c reachy_local

-- Grant schema permissions
GRANT USAGE ON SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO reachy_app;

GRANT USAGE ON SCHEMA public TO reachy_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reachy_read;

-- Exit
\q
```

### Step 4: Apply Migrations

```bash
cd /home/user/project-reachy-emotion

# Apply Phase 1: Core schema
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql

# Apply Phase 2: Stored procedures
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql

# Apply Phase 3: Agent support tables
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/003_missing_tables.sql
```

### Step 5: Verify Installation

```bash
# Connect and check tables
psql -h localhost -U reachy_app -d reachy_local

# In psql:
```

```sql
-- List tables (should show 12)
\dt

-- Expected output:
--              List of relations
--  Schema |        Name         | Type  |   Owner
-- --------+---------------------+-------+-----------
--  public | audit_log           | table | reachy_app
--  public | deployment_log      | table | reachy_app
--  public | emotion_event       | table | reachy_app
--  public | generation_request  | table | reachy_app
--  public | label_event         | table | reachy_app
--  public | obs_samples         | table | reachy_app
--  public | promotion_log       | table | reachy_app
--  public | reconcile_report    | table | reachy_app
--  public | training_run        | table | reachy_app
--  public | training_selection  | table | reachy_app
--  public | user_session        | table | reachy_app
--  public | video               | table | reachy_app

-- Check enum types
SELECT typname FROM pg_type WHERE typtype = 'e';
-- video_split, emotion_label, training_status

-- Test a function
SELECT * FROM check_dataset_balance(100, 1.5);

-- Exit
\q
```

---

## Configure Application

### Environment Variables

Create a `.env` file in the project root:

```bash
cat > .env <<EOF
# Database
MEDIA_MOVER_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_secure_password@localhost:5432/reachy_local

# Filesystem
MEDIA_MOVER_VIDEOS_ROOT=/media/project_data/reachy_emotion/videos
MEDIA_MOVER_MANIFESTS_ROOT=/media/project_data/reachy_emotion/videos/manifests

# API
MEDIA_MOVER_API_ROOT_PATH=/api/media
MEDIA_MOVER_ENABLE_CORS=true
MEDIA_MOVER_UI_ORIGINS=http://localhost:3000,http://localhost:8501
EOF
```

### Test Connection from Python

```python
# test_connection.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    url = "postgresql+asyncpg://reachy_app:reachy_secure_password@localhost:5432/reachy_local"
    engine = create_async_engine(url)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        print(f"Connected: {result.scalar()}")

        result = await conn.execute(text("SELECT COUNT(*) FROM video"))
        print(f"Video count: {result.scalar()}")

    await engine.dispose()

asyncio.run(test_connection())
```

Run:
```bash
python test_connection.py
# Connected: PostgreSQL 16.x ...
# Video count: 0
```

---

## Insert Test Data

```sql
-- Connect to database
psql -h localhost -U reachy_app -d reachy_local

-- Insert test videos
INSERT INTO video (file_path, split, label, size_bytes, sha256, duration_sec)
VALUES
    ('videos/dataset_all/happy_001.mp4', 'dataset_all', 'happy', 1024000, 'a1' || repeat('0', 62), 5.5),
    ('videos/dataset_all/happy_002.mp4', 'dataset_all', 'happy', 1024000, 'a2' || repeat('0', 62), 4.8),
    ('videos/dataset_all/sad_001.mp4', 'dataset_all', 'sad', 1024000, 'b1' || repeat('0', 62), 6.2),
    ('videos/dataset_all/sad_002.mp4', 'dataset_all', 'sad', 1024000, 'b2' || repeat('0', 62), 5.1),
    ('videos/temp/unlabeled_001.mp4', 'temp', NULL, 512000, 'c1' || repeat('0', 62), 3.3);

-- Verify
SELECT split, label, COUNT(*) FROM video GROUP BY split, label;
--    split    | label | count
-- ------------+-------+-------
--  dataset_all| happy |     2
--  dataset_all| sad   |     2
--  temp       |       |     1

-- Test class distribution
SELECT * FROM get_class_distribution('dataset_all');

-- Test balance check
SELECT * FROM check_dataset_balance(1, 1.5);
```

---

## Running the API

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment
export MEDIA_MOVER_DATABASE_URL="postgresql+asyncpg://reachy_app:reachy_secure_password@localhost:5432/reachy_local"

# Run API
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload

# Test endpoint
curl http://localhost:8081/api/media/metrics
```

---

## Running Tests

### Unit Tests (SQLite)

Most tests use SQLite for speed:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/apps/api/db/test_models_constraints.py -v

# Run with coverage
pytest tests/ --cov=apps/api --cov-report=html
```

### Integration Tests (PostgreSQL)

```bash
# Set test database
export TEST_DATABASE_URL="postgresql+asyncpg://reachy_app:reachy_secure_password@localhost:5432/reachy_local_test"

# Create test database
psql -h localhost -U postgres -c "CREATE DATABASE reachy_local_test OWNER reachy_app;"

# Run integration tests
pytest tests/test_database_schema.py -v
```

---

## Common Issues

### Connection Refused

```
psql: error: connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

**Solution**:
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### Authentication Failed

```
psql: error: FATAL: password authentication failed for user "reachy_app"
```

**Solution**:
```bash
# Reset password
sudo -u postgres psql -c "ALTER USER reachy_app WITH PASSWORD 'new_password';"
```

### Permission Denied

```
ERROR: permission denied for table video
```

**Solution**:
```sql
-- As postgres superuser
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO reachy_app;
```

### Enum Type Already Exists

```
ERROR: type "video_split" already exists
```

**Solution**:
```sql
-- Drop and recreate (WARNING: loses data!)
DROP TYPE IF EXISTS video_split CASCADE;

-- Or check existing values
SELECT enum_range(NULL::video_split);
```

---

## Cleanup

### Reset Database

```bash
# Drop and recreate database
sudo -u postgres psql <<SQL
DROP DATABASE IF EXISTS reachy_local;
CREATE DATABASE reachy_local OWNER reachy_app;
SQL

# Re-apply migrations
psql -h localhost -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql
# ... etc
```

### Remove Docker Container

```bash
docker stop reachy_postgres
docker rm reachy_postgres
docker volume rm postgres_data  # If using volume
```

---

## Production Checklist

Before deploying to production:

- [ ] Change default passwords
- [ ] Enable SSL connections
- [ ] Configure `pg_hba.conf` for network access
- [ ] Set up automatic backups (`pg_dump`)
- [ ] Configure connection pooling (PgBouncer)
- [ ] Enable query logging (`log_statement = 'all'`)
- [ ] Set up monitoring (pg_stat_statements)
- [ ] Review [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) and apply fixes

---

## Next Steps

1. Review [00-DATABASE-OVERVIEW.md](00-DATABASE-OVERVIEW.md) for architecture context
2. Check [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for current limitations
3. Explore the API at http://localhost:8081/docs (Swagger UI)
4. Run the full test suite to verify setup
