# Database Concepts for Beginners

This document explains fundamental database concepts used in the Reachy Emotion Detection system. If you're new to databases, start here.

## What is a Database?

A **database** is an organized collection of data stored electronically. Think of it like a very powerful spreadsheet system:

- **Spreadsheet**: One file with multiple sheets
- **Database**: One server with multiple tables, plus powerful query capabilities

We use **PostgreSQL** (often called "Postgres"), which is a free, open-source relational database management system (RDBMS).

## Core Concepts

### Tables

A **table** is like a spreadsheet - it has rows and columns:

```
┌──────────────────────────────────────────────────────────────────┐
│                         video TABLE                               │
├─────────────┬───────────────────┬────────┬───────┬───────────────┤
│  video_id   │     file_path     │ split  │ label │  created_at   │
├─────────────┼───────────────────┼────────┼───────┼───────────────┤
│ abc-123-def │ videos/temp/a.mp4 │ temp   │ NULL  │ 2025-01-05... │
│ def-456-ghi │ videos/train/b.mp4│ train  │ happy │ 2025-01-04... │
│ ghi-789-jkl │ videos/test/c.mp4 │ test   │ NULL  │ 2025-01-03... │
└─────────────┴───────────────────┴────────┴───────┴───────────────┘
```

- **Columns** (vertical): Define WHAT data is stored (video_id, file_path, etc.)
- **Rows** (horizontal): Each row is one record (one video in this case)

### Columns and Data Types

Each column has a **data type** that defines what kind of data it holds:

| Data Type | Description | Example |
|-----------|-------------|---------|
| `UUID` | Unique identifier (36-character string) | `'abc-123-def-456-ghi'` |
| `VARCHAR(n)` | Variable-length text up to n characters | `'videos/temp/clip.mp4'` |
| `TEXT` | Unlimited length text | Long descriptions |
| `INTEGER` / `BIGINT` | Whole numbers | `1920`, `1234567890` |
| `NUMERIC(p,s)` | Precise decimal numbers | `5.23` (duration) |
| `BOOLEAN` | True or false | `TRUE`, `FALSE` |
| `TIMESTAMPTZ` | Date and time with timezone | `'2025-01-05 14:30:00+00'` |
| `JSONB` | Flexible JSON data | `{"fps": 30, "codec": "h264"}` |
| `ENUM` | Fixed set of allowed values | `'happy'`, `'sad'`, `'angry'` |

### Primary Keys

A **primary key** is a column (or columns) that uniquely identifies each row:

```sql
-- video_id is the primary key - no two videos can have the same ID
CREATE TABLE video (
    video_id UUID PRIMARY KEY,  -- <-- This makes it the primary key
    file_path VARCHAR(500),
    ...
);
```

In our system, most primary keys are **UUIDs** (Universally Unique Identifiers) - random 36-character strings that are virtually impossible to duplicate.

### Foreign Keys

A **foreign key** creates a link between two tables:

```
┌─────────────────────┐         ┌────────────────────────┐
│    training_run     │         │   training_selection   │
├─────────────────────┤         ├────────────────────────┤
│ run_id (PK)   ─────────────────────▶ run_id (FK)      │
│ strategy            │         │ video_id (FK)          │
│ train_fraction      │         │ target_split           │
└─────────────────────┘         └────────────────────────┘
                                         │
                                         ▼
                                ┌────────────────────────┐
                                │        video           │
                                ├────────────────────────┤
                                │ video_id (PK)          │
                                │ file_path              │
                                └────────────────────────┘
```

Foreign keys ensure **referential integrity** - you can't reference a training run or video that doesn't exist.

### Indexes

An **index** is like a book's index - it speeds up searches:

```sql
-- Without index: Database scans ALL rows to find videos with split='train'
-- With index: Database jumps directly to matching rows

CREATE INDEX idx_video_split ON video(split);
```

We create indexes on columns that are frequently searched:
- `video.split` - We often filter by split type
- `video.label` - We often filter by emotion
- `video.created_at` - We often sort by time

### Constraints

**Constraints** are rules that enforce data integrity:

| Constraint Type | Purpose | Example |
|-----------------|---------|---------|
| `NOT NULL` | Column cannot be empty | `file_path VARCHAR(500) NOT NULL` |
| `UNIQUE` | No duplicate values | `sha256 CHAR(64) UNIQUE` |
| `CHECK` | Custom validation rule | `CHECK (confidence >= 0 AND confidence <= 1)` |
| `FOREIGN KEY` | Must reference existing row | `REFERENCES training_run(run_id)` |
| `DEFAULT` | Automatic value if not provided | `DEFAULT 'temp'` |

### ENUMs (Enumerated Types)

An **ENUM** restricts a column to a specific set of values:

```sql
-- Define the allowed values
CREATE TYPE emotion_label AS ENUM (
    'neutral',
    'happy',
    'sad',
    'angry',
    'surprise',
    'fearful'
);

-- Use it in a table
CREATE TABLE video (
    label emotion_label,  -- Can ONLY be one of the values above
    ...
);
```

If you try to insert `label = 'excited'`, the database will reject it.

### Triggers

A **trigger** is automatic code that runs when data changes:

```sql
-- This trigger automatically updates the updated_at timestamp
CREATE TRIGGER trg_video_updated
    BEFORE UPDATE ON video
    FOR EACH ROW
    EXECUTE FUNCTION touch_updated_at();
```

In our system, triggers:
- Auto-update `updated_at` timestamps when rows change
- Validate business rules

### Stored Procedures (Functions)

A **stored procedure** is reusable code stored in the database:

```sql
-- Define a function
CREATE FUNCTION get_class_distribution(p_split video_split)
RETURNS TABLE(label TEXT, count BIGINT, percentage NUMERIC)
AS $$
BEGIN
    -- Complex query logic here
    RETURN QUERY SELECT ...;
END;
$$ LANGUAGE plpgsql;

-- Use it
SELECT * FROM get_class_distribution('dataset_all');
```

Benefits:
- Encapsulates complex business logic
- Faster than sending multiple queries from application
- Ensures consistent behavior across all callers

## SQL Basics

**SQL** (Structured Query Language) is how you interact with the database.

### SELECT - Reading Data

```sql
-- Get all videos
SELECT * FROM video;

-- Get specific columns
SELECT video_id, file_path, label FROM video;

-- Filter with WHERE
SELECT * FROM video WHERE split = 'train';

-- Sort with ORDER BY
SELECT * FROM video ORDER BY created_at DESC;

-- Combine conditions
SELECT * FROM video
WHERE split = 'dataset_all'
  AND label = 'happy'
ORDER BY created_at DESC
LIMIT 10;
```

### INSERT - Adding Data

```sql
-- Insert one row
INSERT INTO video (file_path, split, label)
VALUES ('videos/temp/new_clip.mp4', 'temp', NULL);

-- Insert with returning the created ID
INSERT INTO video (file_path, split)
VALUES ('videos/temp/clip.mp4', 'temp')
RETURNING video_id;
```

### UPDATE - Modifying Data

```sql
-- Update one video
UPDATE video
SET label = 'happy', split = 'dataset_all'
WHERE video_id = 'abc-123-def';

-- Update multiple rows
UPDATE video
SET split = 'train'
WHERE split = 'dataset_all' AND label IS NOT NULL;
```

### DELETE - Removing Data

```sql
-- Delete specific row
DELETE FROM video WHERE video_id = 'abc-123-def';

-- Delete with condition
DELETE FROM video WHERE split = 'temp' AND created_at < '2025-01-01';
```

### JOINs - Combining Tables

```sql
-- Get videos with their training run information
SELECT
    v.video_id,
    v.file_path,
    v.label,
    ts.target_split,
    tr.strategy
FROM video v
JOIN training_selection ts ON v.video_id = ts.video_id
JOIN training_run tr ON ts.run_id = tr.run_id
WHERE tr.status = 'completed';
```

## Transactions

A **transaction** groups multiple operations into one atomic unit:

```sql
BEGIN;  -- Start transaction

-- Both of these must succeed together
UPDATE video SET split = 'dataset_all' WHERE video_id = 'abc';
INSERT INTO promotion_log (video_id, from_split, to_split)
VALUES ('abc', 'temp', 'dataset_all');

COMMIT;  -- Make changes permanent
-- or ROLLBACK; to undo everything
```

If any operation fails, ROLLBACK undoes ALL changes - the database never ends up in an inconsistent state.

## Idempotency

**Idempotency** means "doing the same operation twice has the same effect as doing it once":

```sql
-- Non-idempotent: Running twice creates two rows
INSERT INTO promotion_log (video_id, to_split) VALUES ('abc', 'train');
INSERT INTO promotion_log (video_id, to_split) VALUES ('abc', 'train');
-- Result: 2 duplicate rows!

-- Idempotent: Uses unique key to prevent duplicates
INSERT INTO promotion_log (video_id, to_split, idempotency_key)
VALUES ('abc', 'train', 'promo-2025-01-05-001')
ON CONFLICT (idempotency_key) DO NOTHING;
-- Running twice: Only 1 row created
```

Our `promotion_log` and `label_event` tables use idempotency keys to prevent accidental duplicate processing.

## ORM (Object-Relational Mapping)

Instead of writing raw SQL, we can use Python code with **SQLAlchemy ORM**:

```python
# Raw SQL approach
cursor.execute("SELECT * FROM video WHERE split = 'train'")
rows = cursor.fetchall()

# ORM approach (what we use)
from apps.api.app.db.models import Video
from sqlalchemy import select

stmt = select(Video).where(Video.split == "train")
videos = (await session.execute(stmt)).scalars().all()

for video in videos:
    print(f"{video.file_path}: {video.label}")
```

Benefits of ORM:
- Type safety and IDE autocomplete
- Automatic SQL generation
- Protection against SQL injection
- Easier testing with in-memory databases

## Database Roles and Permissions

PostgreSQL uses **roles** to control who can do what:

| Role | Permissions | Purpose |
|------|-------------|---------|
| `reachy_owner` | All (DDL: CREATE, ALTER, DROP) | Schema management |
| `reachy_app` | DML (SELECT, INSERT, UPDATE, DELETE) | Application access |
| `reachy_read` | SELECT only | Read-only dashboards |

```sql
-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON video TO reachy_app;
GRANT SELECT ON video TO reachy_read;
```

## Connection Strings

Applications connect to PostgreSQL using a **connection string**:

```
postgresql://username:password@host:port/database_name

Examples:
postgresql://reachy_app:secret@localhost:5432/reachy_local
postgresql://reachy_app:secret@10.0.4.130:5432/reachy_emotion
```

For async Python (what we use):
```
postgresql+asyncpg://reachy_app:secret@localhost:5432/reachy_local
```

## Key Terminology Reference

| Term | Definition |
|------|------------|
| **Schema** | The structure definition of the database (tables, columns, types) |
| **DDL** | Data Definition Language - CREATE, ALTER, DROP commands |
| **DML** | Data Manipulation Language - SELECT, INSERT, UPDATE, DELETE |
| **CRUD** | Create, Read, Update, Delete - the four basic operations |
| **Normalization** | Organizing data to reduce redundancy |
| **Migration** | Scripts that change the database schema over time |
| **Seed data** | Initial data loaded into a fresh database |
| **Connection pool** | Reusable database connections for performance |

## Next Steps

Now that you understand the basics:
1. Review [02-SCHEMA-REFERENCE.md](02-SCHEMA-REFERENCE.md) to see our actual tables
2. Learn about [03-STORED-PROCEDURES.md](03-STORED-PROCEDURES.md) for business logic
3. See [04-PYTHON-ORM-MODELS.md](04-PYTHON-ORM-MODELS.md) for how Python code interacts with the database
