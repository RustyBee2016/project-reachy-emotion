# Module 2: PostgreSQL Essentials

**Duration**: 4 hours
**Prerequisites**: Module 1 (Database Fundamentals)
**Goal**: Master PostgreSQL-specific features and command-line tools

---

## Learning Objectives

By the end of this module, you will be able to:
1. Navigate PostgreSQL using `psql` command-line tool
2. Understand and use ENUMs, UUIDs, and JSONB
3. Create and use indexes effectively
4. Use PostgreSQL-specific query features
5. Manage roles and permissions

---

## Lesson 2.1: The psql Command-Line Tool (45 minutes)

### Connecting to PostgreSQL

```bash
# Basic connection
psql -U username -d database_name

# With host and port
psql -h localhost -p 5432 -U reachy_app -d reachy_local

# Using connection string
psql "postgresql://reachy_app:password@localhost:5432/reachy_local"
```

### Essential psql Commands

Commands starting with `\` are psql meta-commands (not SQL):

| Command | Description |
|---------|-------------|
| `\l` | List all databases |
| `\c dbname` | Connect to database |
| `\dt` | List tables |
| `\d tablename` | Describe table structure |
| `\di` | List indexes |
| `\df` | List functions |
| `\dT` | List data types (including ENUMs) |
| `\du` | List roles/users |
| `\q` | Quit psql |

### Viewing Table Structure

```sql
reachy_local=# \d video
                                     Table "public.video"
    Column     |           Type           | Collation | Nullable |      Default
---------------+--------------------------+-----------+----------+-------------------
 video_id      | uuid                     |           | not null | uuid_generate_v4()
 file_path     | character varying(500)   |           | not null |
 split         | video_split              |           | not null | 'temp'::video_split
 label         | emotion_label            |           |          |
 sha256        | character(64)            |           |          |
 duration_sec  | numeric(10,2)            |           |          |
 width         | integer                  |           |          |
 height        | integer                  |           |          |
 fps           | numeric(5,2)             |           |          |
 size_bytes    | bigint                   |           |          |
 created_at    | timestamp with time zone |           |          | now()
 updated_at    | timestamp with time zone |           |          | now()
Indexes:
    "video_pkey" PRIMARY KEY, btree (video_id)
    "idx_video_created" btree (created_at DESC)
    "idx_video_label" btree (label)
    "idx_video_sha256" btree (sha256)
    "idx_video_split" btree (split)
    "video_sha256_size_bytes_key" UNIQUE CONSTRAINT, btree (sha256, size_bytes)
```

### Query Formatting

```sql
-- Enable expanded display for wide tables
\x on

-- Example output:
-[ RECORD 1 ]----------------------------------
video_id     | 550e8400-e29b-41d4-a716-446655440000
file_path    | videos/temp/001.mp4
split        | temp
label        |
created_at   | 2025-01-05 14:30:00+00

-- Toggle off
\x off
```

### Running SQL Files

```bash
# Running a SQL file from the command line
psql -d reachy_local -f my_script.sql

# Running a SQL file from within psql
\i my_script.sql

# IMPORTANT: For actual schema setup, always use Alembic:
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
# The legacy SQL files (001_phase1_schema.sql, etc.) are deprecated.
```

### Output to File

```sql
-- Save query results to file
\o /tmp/results.txt
SELECT * FROM video LIMIT 10;
\o  -- Stop output to file

-- Or from command line
psql -d reachy_local -c "SELECT * FROM video" > results.txt
```

---

## Lesson 2.2: PostgreSQL Data Types (45 minutes)

### ENUMs: Named Value Lists

**What is an ENUM?**

An ENUM (enumerated type) restricts a column to specific allowed values.

PostgreSQL supports two approaches for enforcing allowed values:

**Approach 1: Native ENUM types** (used in the legacy SQL files)
```sql
-- Legacy approach from 001_phase1_schema.sql (DEPRECATED)
CREATE TYPE video_split AS ENUM (
    'temp', 'dataset_all', 'train', 'test', 'purged'
);
CREATE TYPE emotion_label AS ENUM (
    'neutral', 'happy', 'sad', 'angry', 'surprise', 'fearful'
);
```

**Approach 2: CHECK constraints** (used by the current Alembic migration)

The Reachy project uses `native_enum=False` in SQLAlchemy, which means enums are enforced
via CHECK constraints rather than native PostgreSQL ENUM types:

```python
# From apps/api/app/db/enums.py
SplitEnum = Enum(
    "temp", "dataset_all", "train", "test", "purged",
    name="video_split_enum",
    native_enum=False,     # ← Uses CHECK constraint, not native ENUM
    create_constraint=True,
)
```

This creates a CHECK constraint like:
```sql
CHECK (split IN ('temp', 'dataset_all', 'train', 'test', 'purged'))
```

**Why CHECK constraints instead of native ENUMs?**
- ✅ Works with SQLite (used for testing) — native ENUMs are PostgreSQL-only
- ✅ Easier to add/remove values (just update the constraint)
- ✅ No `ALTER TYPE ... ADD VALUE` migration complexity
- ❌ Slightly less storage-efficient than native ENUMs (negligible for this project)

**The allowed values are:**

| Enum | Values | Defined In |
|------|--------|------------|
| `video_split_enum` | `temp`, `dataset_all`, `train`, `test`, `purged` | `enums.py` line 9-20 |
| `emotion_enum` | `neutral`, `happy`, `sad`, `angry`, `surprise`, `fearful` | `enums.py` line 22-33 |
| `training_selection_target_enum` | `train`, `test` | `enums.py` line 35-41 |

**Using ENUMs:**

```sql
-- Valid insert
INSERT INTO video (video_id, file_path, split, size_bytes, sha256)
VALUES ('a0000001', 'test.mp4', 'temp', 1024, 'abc123...');

-- Invalid insert (will fail with CHECK constraint violation)
INSERT INTO video (video_id, file_path, split, size_bytes, sha256)
VALUES ('a0000002', 'test.mp4', 'invalid_split', 1024, 'def456...');
-- ERROR: new row for relation "video" violates check constraint
```

**Viewing CHECK constraints on a table:**
```sql
-- Show all constraints on the video table
\d video
-- Look for lines like:
--   Check constraints:
--     "chk_video_split_label_policy" CHECK (...)
```

---

> ✅ **Resolved**: Issues #1 (Missing 'fearful'), #2 (Missing 'purged'), and #9 (Enum name mismatch)
> have all been fixed. The authoritative enum definitions are in `apps/api/app/db/enums.py`
> and include all expected values. The legacy SQL files with different enum type names are
> deprecated. See `docs/database/07-KNOWN-ISSUES.md` for the full resolution history.

---

### UUIDs: Universally Unique Identifiers

**What is a UUID?**

A UUID is a 128-bit identifier that's globally unique:
```
550e8400-e29b-41d4-a716-446655440000
^^^^^^^^ ^^^^ ^^^^ ^^^^ ^^^^^^^^^^^^
  time   ver  var   clock   node
```

**Why use UUIDs instead of auto-increment integers?**

| Feature | Integer ID | UUID |
|---------|-----------|------|
| Uniqueness | Per table | Globally unique |
| Predictability | Sequential (1, 2, 3...) | Random |
| Merging data | Conflicts possible | No conflicts |
| URL-safe | Easy to guess | Hard to guess |
| Storage | 4-8 bytes | 16 bytes |

**Creating UUIDs:**

```sql
-- Enable UUID extension (done in 001_phase1_schema.sql line 5)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Generate a UUID
SELECT uuid_generate_v4();
-- Result: 550e8400-e29b-41d4-a716-446655440000

-- Auto-generate on insert
INSERT INTO video (file_path, split) VALUES ('test.mp4', 'temp')
RETURNING video_id;
-- Returns: newly generated UUID
```

---

> ✅ **Resolved (by design)**: Issue #8 (UUID vs String Type Mismatch)
>
> The project intentionally uses `String(36)` instead of native PostgreSQL `UUID` for
> cross-database compatibility. This allows the same models to work with **SQLite** during
> testing and **PostgreSQL** in production. The trade-off is minimal — UUID string comparison
> is slightly slower than native UUID, but negligible at this project's scale.
>
> See `docs/database/07-KNOWN-ISSUES.md` for details.

---

### JSONB: JSON Binary

**What is JSONB?**

JSONB stores JSON data in a binary format, allowing queries into the JSON structure.

From `models.py` — the `video` table stores flexible extra data as JSON:
```python
extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict, nullable=True)
# DB column name is "metadata"; Python attribute is "extra_data" to avoid shadowing
```

**Storing JSONB:**

```sql
INSERT INTO video (file_path, split, metadata) VALUES (
    'test.mp4',
    'temp',
    '{"source": "jetson", "camera": "front", "tags": ["indoor", "daylight"]}'
);
```

**Querying JSONB:**

```sql
-- Access a key
SELECT metadata->>'source' FROM video;
-- Result: 'jetson'

-- Access nested values
SELECT metadata->'tags'->>0 FROM video;
-- Result: 'indoor'

-- Filter by JSON content
SELECT * FROM video
WHERE metadata->>'source' = 'jetson';

-- Check if key exists
SELECT * FROM video
WHERE metadata ? 'camera';

-- Check if array contains value
SELECT * FROM video
WHERE metadata->'tags' @> '"indoor"';
```

**JSONB Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `->` | Get JSON element (as JSON) | `metadata->'tags'` |
| `->>` | Get JSON element (as text) | `metadata->>'source'` |
| `@>` | Contains | `metadata @> '{"source":"jetson"}'` |
| `?` | Key exists | `metadata ? 'camera'` |
| `?&` | All keys exist | `metadata ?& array['source','camera']` |

### TIMESTAMPTZ: Timestamps with Time Zone

**Always use TIMESTAMPTZ**, not TIMESTAMP:

```sql
-- TIMESTAMPTZ stores in UTC, displays in your timezone
SELECT now();
-- Result: 2025-01-05 14:30:00-08 (if you're in PST)

-- Compare across timezones safely
SELECT * FROM video
WHERE created_at > '2025-01-01T00:00:00Z';
```

### INET: IP Address Type

PostgreSQL has a native `INET` type for IP addresses:

```sql
-- Store IPv4 or IPv6 addresses
ip_address INET

-- Query examples
SELECT * FROM user_session WHERE ip_address = '192.168.1.1';
SELECT * FROM user_session WHERE ip_address << '192.168.0.0/16';  -- Subnet match
```

---

> ✅ **Resolved (by design)**: Issue #13 (AuditLog IP Type Mismatch)
>
> The project uses `String(45)` instead of native PostgreSQL `INET` for the same reason as
> Issue #8: cross-database compatibility with SQLite during testing. `String(45)` accommodates
> both IPv4 (`15 chars`) and IPv6 (`45 chars`) addresses. Subnet-match queries (`<<` operator)
> are not needed by the application.
>
> See `docs/database/07-KNOWN-ISSUES.md` for details.

---

### NUMERIC: Precise Decimals

```sql
-- NUMERIC(precision, scale)
-- precision = total digits
-- scale = decimal places

NUMERIC(10, 2)  -- Up to 99999999.99
NUMERIC(5, 4)   -- Up to 9.9999

-- Examples from Reachy models.py:
-- video table uses Float for duration_sec and fps (approximate is fine)
-- deployment_log uses Numeric for precise Gate B metrics:
fps_measured    NUMERIC(6, 2)   -- e.g., 30.00 fps
latency_p50_ms  NUMERIC(8, 2)   -- e.g., 115.50 ms
gpu_memory_gb   NUMERIC(4, 2)   -- e.g., 2.10 GB
-- obs_samples uses Numeric for high-precision metric values:
value           NUMERIC(15, 4)  -- e.g., 67.2000
```

---

## Lesson 2.3: Indexes (45 minutes)

### What is an Index?

An **index** is like a book's index - it helps find data faster without scanning every row.

```
Without index: Scan all 1,000,000 rows → Slow!
With index:    Binary search → Fast!
```

### Index Types in PostgreSQL

| Type | Use Case | Example |
|------|----------|---------|
| B-tree (default) | Equality, range queries | `WHERE split = 'train'` |
| Hash | Equality only | `WHERE video_id = '...'` |
| GIN | JSONB, arrays, full-text | `WHERE metadata @> '{...}'` |
| GiST | Geometry, ranges | Spatial data |

### Creating Indexes

From `models.py` — indexes are declared in `__table_args__` and created by the Alembic migration:

```python
# In models.py, Video class:
__table_args__ = (
    Index("ix_video_split", "split"),
    Index("ix_video_label", "label"),
)
```

Which translates to this SQL when the migration runs:

```sql
-- Simple index on one column
CREATE INDEX ix_video_split ON video(split);
CREATE INDEX ix_video_label ON video(label);

-- Composite index (from promotion_log)
CREATE INDEX ix_promotion_log_video_time ON promotion_log(video_id, created_at);
```

### Composite Indexes

Index on multiple columns:

```sql
-- For queries filtering by both video_id AND created_at
CREATE INDEX idx_sel_video_created
ON training_selection(video_id, created_at DESC);

-- Order matters! This index helps:
-- WHERE video_id = 'abc' AND created_at > '2025-01-01'

-- But NOT:
-- WHERE created_at > '2025-01-01'  (video_id must be specified first)
```

### When to Create Indexes

**Do create indexes on:**
- Primary keys (automatic)
- Foreign keys
- Columns used in WHERE clauses
- Columns used in JOIN conditions
- Columns used in ORDER BY

**Don't create indexes on:**
- Small tables (< 1000 rows)
- Columns with few unique values (e.g., boolean)
- Columns rarely queried
- Every column (wastes space, slows writes)

### Checking Index Usage

```sql
-- See all indexes on a table
\di video

-- Check if query uses an index
EXPLAIN ANALYZE SELECT * FROM video WHERE split = 'train';

-- Example output:
-- Index Scan using idx_video_split on video  (cost=0.29..8.30 rows=1)
--   Index Cond: (split = 'train'::video_split)
--   Actual time: 0.023..0.024 rows=10
```

### Index Maintenance

```sql
-- Rebuild an index (fixes bloat)
REINDEX INDEX idx_video_split;

-- Rebuild all indexes on a table
REINDEX TABLE video;

-- Check index size
SELECT pg_size_pretty(pg_relation_size('idx_video_split'));
```

---

## Lesson 2.4: Advanced Queries (45 minutes)

### JOINs

Combine data from multiple tables:

```sql
-- INNER JOIN: Only matching rows
SELECT v.file_path, tr.strategy, ts.target_split
FROM video v
INNER JOIN training_selection ts ON v.video_id = ts.video_id
INNER JOIN training_run tr ON ts.run_id = tr.run_id
WHERE tr.status = 'completed';

-- LEFT JOIN: All videos, even if not in any training run
SELECT v.file_path, ts.target_split
FROM video v
LEFT JOIN training_selection ts ON v.video_id = ts.video_id;

-- Videos NOT in any training run
SELECT v.file_path
FROM video v
LEFT JOIN training_selection ts ON v.video_id = ts.video_id
WHERE ts.video_id IS NULL;
```

### Common Table Expressions (CTEs)

CTEs make complex queries readable:

```sql
-- Without CTE (hard to read):
SELECT * FROM (
    SELECT label, COUNT(*) as cnt FROM video WHERE split = 'dataset_all' GROUP BY label
) sub WHERE cnt > 100;

-- With CTE (clear):
WITH label_counts AS (
    SELECT label, COUNT(*) as cnt
    FROM video
    WHERE split = 'dataset_all'
    GROUP BY label
)
SELECT * FROM label_counts WHERE cnt > 100;
```

### Window Functions

Calculate values across rows without grouping:

```sql
-- Rank videos by duration within each label
SELECT
    file_path,
    label,
    duration_sec,
    RANK() OVER (PARTITION BY label ORDER BY duration_sec DESC) as duration_rank
FROM video
WHERE label IS NOT NULL;

-- Running total of videos over time
SELECT
    date_trunc('day', created_at) as day,
    COUNT(*) as daily_count,
    SUM(COUNT(*)) OVER (ORDER BY date_trunc('day', created_at)) as cumulative
FROM video
GROUP BY date_trunc('day', created_at);
```

### RETURNING Clause

Get data back from INSERT/UPDATE/DELETE:

```sql
-- Insert and get the generated ID
INSERT INTO video (file_path, split)
VALUES ('test.mp4', 'temp')
RETURNING video_id, created_at;

-- Update and see what changed
UPDATE video
SET split = 'dataset_all', label = 'happy'
WHERE file_path = 'test.mp4'
RETURNING video_id, split, label;

-- Delete and see what was removed
DELETE FROM video
WHERE created_at < '2024-01-01'
RETURNING video_id, file_path;
```

### UPSERT (INSERT ON CONFLICT)

Insert if new, update if exists:

```sql
-- Insert or update based on unique constraint
INSERT INTO video (sha256, size_bytes, file_path, split)
VALUES ('abc123...', 1024000, 'test.mp4', 'temp')
ON CONFLICT (sha256, size_bytes)
DO UPDATE SET
    file_path = EXCLUDED.file_path,
    updated_at = now();
```

---

## Lesson 2.5: Roles and Permissions (30 minutes)

### PostgreSQL Role Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     Roles in Reachy                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐                                       │
│   │    postgres     │  Superuser (full control)             │
│   └────────┬────────┘                                       │
│            │                                                 │
│   ┌────────┴────────────────────┐                           │
│   │                             │                            │
│   ▼                             ▼                            │
│ ┌─────────────────┐   ┌─────────────────┐                   │
│ │  reachy_owner   │   │   reachy_app    │                   │
│ │  DDL access     │   │   DML access    │                   │
│ │  (CREATE/DROP)  │   │   (CRUD only)   │                   │
│ └─────────────────┘   └────────┬────────┘                   │
│                                │                             │
│                       ┌────────┴────────┐                   │
│                       │                 │                    │
│                       ▼                 ▼                    │
│              ┌─────────────────┐  ┌─────────────────┐       │
│              │  reachy_read    │  │  reachy_write   │       │
│              │  SELECT only    │  │  INSERT/UPDATE  │       │
│              └─────────────────┘  └─────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Creating Roles

```sql
-- Create application role
CREATE ROLE reachy_app WITH LOGIN PASSWORD 'secure_password';

-- Create read-only role
CREATE ROLE reachy_read WITH LOGIN PASSWORD 'read_password';
```

### Granting Permissions

```sql
-- Grant all on database
GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;

-- Grant specific permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO reachy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO reachy_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO reachy_app;

-- Read-only access
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reachy_read;

-- Future tables get same permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO reachy_app;
```

### Best Practices

1. **Never use `postgres` in application code** - Use `reachy_app`
2. **Principle of least privilege** - Only grant what's needed
3. **Separate read/write roles** - Dashboards use `reachy_read`
4. **Rotate passwords** - Especially in production

---

## Lesson 2.6: PostgreSQL Configuration (30 minutes)

### Key Configuration Parameters

```sql
-- View current settings
SHOW max_connections;
SHOW shared_buffers;
SHOW work_mem;

-- Or query all settings
SELECT name, setting, short_desc
FROM pg_settings
WHERE name IN ('max_connections', 'shared_buffers', 'work_mem');
```

### Important Settings for Reachy

| Setting | Recommended | Description |
|---------|-------------|-------------|
| `max_connections` | 100 | Max simultaneous connections |
| `shared_buffers` | 256MB | Memory for caching |
| `work_mem` | 4MB | Memory per sort/hash operation |
| `effective_cache_size` | 1GB | Planner's memory estimate |
| `maintenance_work_mem` | 64MB | Memory for VACUUM, INDEX |

### Modifying Configuration

```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf

# Changes require restart
sudo systemctl restart postgresql
```

### Connection Strings

```python
# apps/api/app/config.py (lines 150-165)
REACHY_DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"

# Format:
# driver://user:password@host:port/database
```

---

## Knowledge Check

1. What psql command shows all tables in the current database?

2. Why would you use JSONB instead of creating more columns?

3. When should you create an index on a column?

4. What's the difference between `->` and `->>` for JSONB?

5. What does `RETURNING` do in an INSERT statement?

<details>
<summary>Click to see answers</summary>

1. `\dt` (or `\dt+` for more detail)

2. When the data structure varies between rows, or when you need flexible storage without schema changes.

3. On columns frequently used in WHERE, JOIN, or ORDER BY clauses, especially on large tables.

4. `->` returns a JSON object/array. `->>` returns text (string). Use `->>` when comparing to strings.

5. Returns the values of specified columns from the inserted/updated/deleted rows, so you can get auto-generated values like UUIDs or timestamps.

</details>

---

## Hands-On Exercise 2

### Part A: psql Navigation

```bash
# 1. Connect to database
psql -U reachy_app -d reachy_local

# 2. List all tables
\dt

# 3. Describe the video table
\d video

# 4. Show all enum types
\dT

# 5. List all indexes
\di
```

### Part B: Working with ENUMs and JSONB

```sql
-- 1. View available emotion labels
SELECT enum_range(NULL::emotion_label);

-- 2. Insert a video with metadata
INSERT INTO video (file_path, split, metadata) VALUES (
    'videos/test/json_test.mp4',
    'temp',
    '{"source": "jetson", "resolution": {"width": 1920, "height": 1080}}'
) RETURNING video_id;

-- 3. Query by JSONB content
SELECT file_path, metadata->>'source' as source
FROM video
WHERE metadata ? 'source';

-- 4. Query nested JSONB
SELECT file_path, metadata->'resolution'->>'width' as width
FROM video
WHERE metadata->'resolution' IS NOT NULL;
```

### Part C: Index Analysis

```sql
-- 1. Run a query and see the execution plan
EXPLAIN ANALYZE
SELECT * FROM video WHERE split = 'train';

-- 2. Check which index was used
-- Look for "Index Scan using idx_video_split"

-- 3. Try a query without index benefit
EXPLAIN ANALYZE
SELECT * FROM video WHERE size_bytes > 1000000;

-- 4. Compare with JSONB query
EXPLAIN ANALYZE
SELECT * FROM video WHERE metadata->>'source' = 'jetson';
-- Note: No index by default - will be "Seq Scan"

-- 5. Create a JSONB index and compare
CREATE INDEX idx_video_metadata_source ON video ((metadata->>'source'));
EXPLAIN ANALYZE
SELECT * FROM video WHERE metadata->>'source' = 'jetson';
```

---

## Summary

In this module, you learned:

- ✅ Navigate PostgreSQL using psql commands
- ✅ Use PostgreSQL-specific types: ENUM, UUID, JSONB, TIMESTAMPTZ
- ✅ Create and optimize indexes
- ✅ Write advanced queries: JOINs, CTEs, Window Functions
- ✅ Manage roles and permissions
- ✅ Configure PostgreSQL settings

**Next**: [Module 3: Reachy Schema Deep Dive](./03-MODULE-REACHY-SCHEMA.md)
