# Database Setup Guide

This guide walks you through setting up the PostgreSQL database for development and testing.

## Prerequisites

- Ubuntu 20.04+ or macOS
- PostgreSQL 15 or 16
- Python 3.10+
- Git

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

# Apply migrations
psql -h localhost -U reachy_app -d reachy_local \
    -f alembic/versions/001_phase1_schema.sql
psql -h localhost -U reachy_app -d reachy_local \
    -f alembic/versions/002_stored_procedures.sql
psql -h localhost -U reachy_app -d reachy_local \
    -f alembic/versions/003_missing_tables.sql

# Verify
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

# Apply migrations
psql -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -U reachy_app -d reachy_local -f alembic/versions/003_missing_tables.sql
```

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

### Step 4: Apply Migrations

```bash
cd /home/user/project-reachy-emotion

# Apply in order
psql -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -U reachy_app -d reachy_local -f alembic/versions/003_missing_tables.sql
```

### Step 5: Verify Installation

```bash
# Connect to database
psql -U reachy_app -d reachy_local

# List tables (should show 12)
\dt

# Check enums
\dT

# Test a stored procedure
SELECT * FROM check_dataset_balance(10, 2.0);

# Exit
\q
```

---

## Configuration

### Environment Variables

Create `.env` file in `apps/api/`:

```bash
# apps/api/.env
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:dev_password@localhost:5432/reachy_local
REACHY_VIDEOS_ROOT=/mnt/videos
REACHY_API_PORT=8083
```

### Python Configuration

The database URL is configured in `apps/api/app/config.py`:

```python
class Settings(BaseSettings):
    REACHY_DATABASE_URL: str = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"
```

### Connection Strings

| Use Case | Connection String |
|----------|-------------------|
| psql CLI | `psql -U reachy_app -d reachy_local` |
| Python sync | `postgresql://reachy_app:pass@localhost:5432/reachy_local` |
| Python async | `postgresql+asyncpg://reachy_app:pass@localhost:5432/reachy_local` |

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
        "postgresql+asyncpg://reachy_app:dev_password@localhost/reachy_local"
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        print(result.scalar())

asyncio.run(test())
```

### Test Stored Procedures

```sql
-- In psql
SELECT * FROM get_class_distribution('dataset_all');
SELECT * FROM check_dataset_balance(100, 1.5);
```

### Insert Test Data

```sql
-- Insert test videos
INSERT INTO video (file_path, split, size_bytes) VALUES
    ('videos/test/001.mp4', 'temp', 1024000),
    ('videos/test/002.mp4', 'temp', 2048000);

-- Verify
SELECT * FROM video;

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
      - ./alembic/versions:/docker-entrypoint-initdb.d:ro
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
# Start
docker-compose up -d

# Check logs
docker-compose logs postgres

# Connect
psql -h localhost -U reachy_app -d reachy_local

# Stop
docker-compose down

# Stop and remove data
docker-compose down -v
```

---

## Resetting the Database

### Drop and Recreate

```bash
# Drop database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS reachy_local;"

# Recreate
sudo -u postgres psql -c "CREATE DATABASE reachy_local OWNER reachy_app;"

# Reapply migrations
psql -U reachy_app -d reachy_local -f alembic/versions/001_phase1_schema.sql
psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql
psql -U reachy_app -d reachy_local -f alembic/versions/003_missing_tables.sql
```

### Docker Reset

```bash
docker stop reachy_postgres
docker rm reachy_postgres
docker volume rm project-reachy-emotion_postgres_data

# Restart
docker-compose up -d
```

---

## Next Steps

1. Read the [Schema Reference](./curriculum/02-SCHEMA-REFERENCE.md) in the curriculum
2. Complete the [Curriculum](./curriculum/00-CURRICULUM-OVERVIEW.md)
3. Review [Known Issues](./07-KNOWN-ISSUES.md)
