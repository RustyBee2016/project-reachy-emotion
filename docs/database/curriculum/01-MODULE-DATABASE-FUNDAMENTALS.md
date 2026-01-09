# Module 1: Database Fundamentals

**Duration**: 4 hours
**Prerequisites**: None
**Goal**: Understand what databases are and how to interact with them using SQL

---

## Learning Objectives

By the end of this module, you will be able to:

1. Explain what a database is and why we use one
2. Understand tables, rows, columns, and keys
3. Write basic SQL queries
4. Understand relationships between tables
5. Explain ACID properties and transactions

---

## Lesson 1.1: What is a Database? (30 minutes)

### The Problem Without Databases

Imagine tracking video files using text files or spreadsheets:

```
videos.csv:
path,emotion,created
/videos/001.mp4,happy,2025-01-01
/videos/002.mp4,sad,2025-01-02
...
```

**Problems with this approach:**

- No way to prevent duplicate entries
- Can't enforce rules (e.g., "emotion must be happy/sad/angry")
- Slow searches when file grows large
- Multiple users can corrupt data simultaneously
- No way to undo mistakes

### The Database Solution

A **database** solves all these problems:

| Problem           | Database Solution                |
| ----------------- | -------------------------------- |
| Duplicates        | UNIQUE constraints               |
| Invalid data      | CHECK constraints, ENUMs         |
| Slow searches     | Indexes                          |
| Concurrent access | Transactions, locking            |
| Undo mistakes     | Rollback, point-in-time recovery |

### Relational vs Other Databases

```
Database Types
├── Relational (SQL)         ← We use this (PostgreSQL)
│   ├── PostgreSQL
│   ├── MySQL
│   └── SQLite
├── Document (NoSQL)
│   ├── MongoDB
│   └── CouchDB
├── Key-Value
│   ├── Redis
│   └── DynamoDB
└── Graph
    ├── Neo4j
    └── Amazon Neptune
```

**Why PostgreSQL for Reachy?**

- Excellent for structured data (videos, training runs)
- Strong consistency guarantees
- Powerful query language
- Native support for UUIDs, JSON, arrays
- Free and open source

### Key Terms

| Term         | Definition                          | Example                 |
| ------------ | ----------------------------------- | ----------------------- |
| **Database** | A collection of organized data      | `reachy_local`          |
| **Table**    | A structure that holds related data | `video`                 |
| **Row**      | A single record in a table          | One video's information |
| **Column**   | A specific attribute                | `file_path`, `label`    |
| **Schema**   | The structure definition            | Table definitions       |

---

## Lesson 1.2: Tables, Rows, and Columns (45 minutes)

### Anatomy of a Table

Think of a table like a spreadsheet:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         video (table)                                │
├──────────────────┬──────────────────┬─────────────┬─────────────────┤
│ video_id (PK)    │ file_path        │ split       │ label           │
├──────────────────┼──────────────────┼─────────────┼─────────────────┤
│ abc-123-def      │ videos/001.mp4   │ dataset_all │ happy           │  ← Row 1
│ xyz-789-ghi      │ videos/002.mp4   │ train       │ sad             │  ← Row 2
│ mno-456-pqr      │ videos/003.mp4   │ temp        │ NULL            │  ← Row 3
└──────────────────┴──────────────────┴─────────────┴─────────────────┘
     ↑ Column 1         ↑ Column 2        ↑ Column 3    ↑ Column 4
```

### Data Types

Every column has a **data type** that defines what values it can hold:

| SQL Type       | Description                 | Example Values                           |
| -------------- | --------------------------- | ---------------------------------------- |
| `VARCHAR(n)`   | Text up to n characters     | `'hello'`, `'videos/001.mp4'`            |
| `INTEGER`      | Whole numbers               | `42`, `-100`, `0`                        |
| `BIGINT`       | Large whole numbers         | `9223372036854775807`                    |
| `NUMERIC(p,s)` | Precise decimals            | `3.14159`, `99.99`                       |
| `BOOLEAN`      | True or false               | `TRUE`, `FALSE`                          |
| `TIMESTAMPTZ`  | Date and time with timezone | `'2025-01-05 14:30:00+00'`               |
| `UUID`         | Unique identifier           | `'550e8400-e29b-41d4-a716-446655440000'` |
| `JSONB`        | JSON data (binary)          | `'{"key": "value"}'`                     |

### Reachy Example: The Video Table

From `alembic/versions/001_phase1_schema.sql` (lines 31-52):

```sql
CREATE TABLE video (
    video_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path    VARCHAR(500) NOT NULL,        -- Required
    split        video_split NOT NULL DEFAULT 'temp',
    label        emotion_label,                 -- Optional (can be NULL)
    sha256       CHAR(64),                      -- Exactly 64 characters
    duration_sec NUMERIC(10,2),                 -- Up to 10 digits, 2 decimal
    width        INTEGER,
    height       INTEGER,
    fps          NUMERIC(5,2),
    size_bytes   BIGINT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);
```

**Breaking this down:**

- `video_id UUID PRIMARY KEY` - Unique identifier, auto-generated
- `VARCHAR(500) NOT NULL` - Required text field, max 500 chars
- `NUMERIC(10,2)` - Number like `12345678.90`
- `DEFAULT 'temp'` - If not specified, use 'temp'
- No `NOT NULL` on `label` - It can be empty (NULL)

### NULL: The Absence of Value

**<mark>NULL is not the same as empty or zero!</mark>**

```sql
-- These are all different:
label = 'happy'     -- Has a value
label = ''          -- Empty string (still a value)
label = NULL        -- No value at all (unknown)
```

In Reachy:

- Videos in `temp` split have `label = NULL` (not yet labeled)
- Videos in `dataset_all` must have a label (NOT NULL)

---

## Lesson 1.3: Keys and Relationships (45 minutes)

### Primary Keys

A **primary key** uniquely identifies each row in a table.

```
video table:
┌──────────────────────────────────────────────────────────────┐
│ video_id (PRIMARY KEY)  │ file_path         │ label          │
├─────────────────────────┼───────────────────┼────────────────┤
│ abc-123-def             │ videos/001.mp4    │ happy          │
│ xyz-789-ghi             │ videos/002.mp4    │ sad            │
│ abc-123-def             │ videos/003.mp4    │ angry          │  ← ERROR!
└─────────────────────────┴───────────────────┴────────────────┘
                                                 Duplicate PK not allowed!
```

**Primary Key Rules:**

1. Must be unique (no duplicates)
2. Cannot be NULL
3. Should never change once assigned
4. One per table

### Foreign Keys

A **foreign key** creates a relationship to another table.

```
training_run table:
┌────────────────────────────────────────────────────────────────┐
│ run_id (PK)        │ strategy          │ train_fraction         │
├────────────────────┼───────────────────┼────────────────────────┤
│ run-001            │ balanced_random   │ 0.70                   │
│ run-002            │ stratified        │ 0.80                   │
└────────────────────┴───────────────────┴────────────────────────┘

training_selection table:
┌──────────────────────────────────────────────────────────────────┐
│ run_id (FK)        │ video_id (FK)     │ target_split           │
├────────────────────┼───────────────────┼────────────────────────┤
│ run-001            │ abc-123-def       │ train                  │
│ run-001            │ xyz-789-ghi       │ test                   │
│ run-002            │ abc-123-def       │ train                  │
│ run-003            │ mno-456-pqr       │ train                  │  ← ERROR!
└────────────────────┴───────────────────┴────────────────────────┘
                                           run-003 doesn't exist!
```

From `001_phase1_schema.sql` (lines 69-80):

```sql
CREATE TABLE training_selection (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES training_run(run_id) ON DELETE CASCADE,
    video_id     UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
    target_split video_split NOT NULL,
    selected_at  TIMESTAMPTZ DEFAULT now()
);
```

**Foreign Key Benefits:**

- Prevents orphaned records (can't reference non-existent data)
- `ON DELETE CASCADE` - When parent deleted, delete children too
- Database enforces data integrity automatically

### Relationship Types

```
1. One-to-Many (Most Common)
   ┌─────────────┐           ┌─────────────────────┐
   │ training_run│ 1 ─────── M │ training_selection  │
   │ (one run)   │           │ (many video choices)│
   └─────────────┘           └─────────────────────┘

2. Many-to-Many (via Junction Table)
   ┌─────────────┐           ┌─────────────────────┐           ┌─────────────┐
   │ video       │ M ─────── M │ training_selection  │ M ─────── 1 │ training_run│
   │             │           │ (junction table)    │           │             │
   └─────────────┘           └─────────────────────┘           └─────────────┘

   One video can be in many runs
   One run can have many videos
```

### Reachy Relationship Diagram

```
                    ┌───────────────────┐
                    │    video          │
                    │─────────────────────│
                    │ video_id (PK)     │
                    │ file_path         │
                    │ split             │
                    │ label             │
                    └─────────┬─────────┘
                              │
                              │ 1:M
                              ▼
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│  promotion_log    │       │training_selection │       │   label_event     │
│───────────────────│       │───────────────────│       │───────────────────│
│ video_id (FK)     │       │ video_id (FK)     │       │ video_id (FK)     │
│ from_split        │       │ run_id (FK)       │       │ action            │
│ to_split          │       │ target_split      │       │ label             │
└───────────────────┘       └─────────┬─────────┘       └───────────────────┘
                                      │
                                      │ M:1
                                      ▼
                            ┌───────────────────┐
                            │   training_run    │
                            │───────────────────│
                            │ run_id (PK)       │
                            │ strategy          │
                            │ train_fraction    │
                            └───────────────────┘
```

---

## Lesson 1.4: Basic SQL Queries (1 hour)

### The Four Basic Operations: CRUD

| Operation  | SQL Command | Description          |
| ---------- | ----------- | -------------------- |
| **C**reate | `INSERT`    | Add new rows         |
| **R**ead   | `SELECT`    | Query existing rows  |
| **U**pdate | `UPDATE`    | Modify existing rows |
| **D**elete | `DELETE`    | Remove rows          |

### SELECT: Reading Data

**Basic syntax:**

```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition
ORDER BY column
LIMIT number;
```

**Examples:**

```sql
-- Select all columns from all videos
SELECT * FROM video;

-- Select specific columns
SELECT file_path, label FROM video;

-- Filter with WHERE
SELECT * FROM video WHERE split = 'train';

-- Multiple conditions
SELECT * FROM video
WHERE split = 'dataset_all'
  AND label = 'happy';

-- Sort results
SELECT * FROM video ORDER BY created_at DESC;

-- Limit results
SELECT * FROM video LIMIT 10;

-- Count rows
SELECT COUNT(*) FROM video WHERE label = 'happy';

-- Group and count
SELECT label, COUNT(*) as count
FROM video
WHERE split = 'dataset_all'
GROUP BY label;
```

### INSERT: Creating Data

```sql
-- Insert a single row
INSERT INTO video (file_path, split, label, size_bytes)
VALUES ('videos/test/001.mp4', 'temp', NULL, 1024000);

-- Insert with specific UUID
INSERT INTO video (video_id, file_path, split)
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'videos/002.mp4', 'temp');

-- Insert multiple rows
INSERT INTO video (file_path, split) VALUES
    ('videos/003.mp4', 'temp'),
    ('videos/004.mp4', 'temp'),
    ('videos/005.mp4', 'temp');
```

### UPDATE: Modifying Data

```sql
-- Update one row
UPDATE video
SET label = 'happy', split = 'dataset_all'
WHERE video_id = '550e8400-e29b-41d4-a716-446655440000';

-- Update multiple rows
UPDATE video
SET split = 'train'
WHERE split = 'dataset_all' AND label = 'happy';

-- DANGER: Without WHERE, updates ALL rows!
UPDATE video SET label = 'happy';  -- Don't do this!
```

### DELETE: Removing Data

```sql
-- Delete one row
DELETE FROM video
WHERE video_id = '550e8400-e29b-41d4-a716-446655440000';

-- Delete multiple rows
DELETE FROM video WHERE split = 'temp';

-- DANGER: Without WHERE, deletes ALL rows!
DELETE FROM video;  -- Don't do this!
```

### Practice Queries for Reachy

Try these on your local database:

```sql
-- 1. How many videos are in each split?
SELECT split, COUNT(*) as count
FROM video
GROUP BY split;

-- 2. What's the total size of videos by label?
SELECT label, SUM(size_bytes) / 1048576.0 as total_mb
FROM video
WHERE label IS NOT NULL
GROUP BY label;

-- 3. Find videos longer than 10 seconds
SELECT file_path, duration_sec
FROM video
WHERE duration_sec > 10
ORDER BY duration_sec DESC;

-- 4. List training runs and their video counts
SELECT tr.run_id, tr.strategy, COUNT(ts.video_id) as video_count
FROM training_run tr
LEFT JOIN training_selection ts ON tr.run_id = ts.run_id
GROUP BY tr.run_id, tr.strategy;
```

---

## Lesson 1.5: Constraints and Data Integrity (30 minutes)

### What Are Constraints?

**Constraints** are rules that the database enforces automatically.

| Constraint    | Purpose                    | Example                                       |
| ------------- | -------------------------- | --------------------------------------------- |
| `PRIMARY KEY` | Unique identifier          | `video_id`                                    |
| `FOREIGN KEY` | Reference to another table | `run_id REFERENCES training_run`              |
| `NOT NULL`    | Value required             | `file_path VARCHAR(500) NOT NULL`             |
| `UNIQUE`      | No duplicates allowed      | `UNIQUE(sha256, size_bytes)`                  |
| `CHECK`       | Custom validation          | `CHECK (confidence >= 0 AND confidence <= 1)` |
| `DEFAULT`     | Value if not specified     | `DEFAULT 'temp'`                              |

### Reachy Constraint Examples

From `001_phase1_schema.sql`:

```sql
-- Unique constraint: Same hash + size = same file
UNIQUE (sha256, size_bytes)

-- Check constraint: Train + test fraction can't exceed 100%
CHECK (train_fraction + test_fraction <= 1.0)

-- Check constraint: Confidence must be 0-1
CHECK (confidence >= 0 AND confidence <= 1)
```

### The Video Split/Label Policy

The most important business rule in Reachy:

```sql
-- From models.py (line 66-75) - should be in SQL too!
CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
)
```

**In plain English:**

- `temp` videos: NOT labeled (waiting for human review)
- `dataset_all` videos: MUST be labeled
- `train` videos: MUST be labeled
- `test` videos: NOT labeled (to avoid test data leakage)
- `purged` videos: NOT labeled (deleted for privacy)

```
┌──────────────────────────────────────────────────────────────────────┐
│                       VIDEO LIFECYCLE                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────┐    label     ┌─────────────┐   sample    ┌─────────┐  │
│   │  temp   │ ──────────▶  │ dataset_all │ ─────────▶  │  train  │  │
│   │ (NULL)  │              │  (labeled)  │             │(labeled)│  │
│   └────┬────┘              └──────┬──────┘             └─────────┘  │
│        │                          │                                  │
│        │ discard                  │ sample             ┌─────────┐  │
│        │                          └─────────────────▶  │  test   │  │
│        ▼                                               │ (NULL)  │  │
│   ┌─────────┐                                          └─────────┘  │
│   │ purged  │ ◀──────── GDPR deletion request                       │
│   │ (NULL)  │                                                        │
│   └─────────┘                                                        │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Lesson 1.6: Transactions and ACID (30 minutes)

### What is a Transaction?

A **transaction** is a group of operations that must all succeed or all fail together.

**Example: Promoting a Video**

```sql
BEGIN;  -- Start transaction

-- Step 1: Update video
UPDATE video SET split = 'dataset_all', label = 'happy'
WHERE video_id = 'abc-123';

-- Step 2: Log the promotion
INSERT INTO promotion_log (video_id, from_split, to_split, label, user_id)
VALUES ('abc-123', 'temp', 'dataset_all', 'happy', 'alice@example.com');

COMMIT;  -- All or nothing!
```

If Step 2 fails, Step 1 is automatically undone.

### ACID Properties

| Property        | Meaning               | Guarantee                                  |
| --------------- | --------------------- | ------------------------------------------ |
| **A**tomicity   | All or nothing        | If one step fails, everything rolls back   |
| **C**onsistency | Data stays valid      | Constraints are always enforced            |
| **I**solation   | No interference       | Concurrent users don't see partial changes |
| **D**urability  | Changes are permanent | Once committed, data survives crashes      |

### Isolation Levels

PostgreSQL supports different isolation levels:

```sql
-- Default: Read Committed
BEGIN;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
-- ... operations ...
COMMIT;

-- Strictest: Serializable (slowest but safest)
BEGIN;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- ... operations ...
COMMIT;
```

### Deadlocks

When two transactions wait for each other:

```
Transaction A                Transaction B
─────────────                ─────────────
Lock video row 1             Lock video row 2
Try to lock row 2...         Try to lock row 1...
   (waiting)                    (waiting)
        └─────── DEADLOCK! ──────┘
```

PostgreSQL detects deadlocks and kills one transaction.

**Prevention:**

- Always lock resources in the same order
- Keep transactions short
- Use `FOR UPDATE SKIP LOCKED` when appropriate

---

## Knowledge Check

Test your understanding:

1. What is the difference between a PRIMARY KEY and a FOREIGN KEY?

2. What SQL command would you use to find all videos labeled 'happy'?

3. Why does the `video` table have `label` as nullable (can be NULL)?

4. What does `ON DELETE CASCADE` do?

5. In a transaction, what happens if one operation fails?

<details>
<summary>Click to see answers</summary>

1. **PRIMARY KEY** uniquely identifies rows in THIS table. **FOREIGN KEY** references rows in ANOTHER table.

2. `SELECT * FROM video WHERE label = 'happy';`

3. Because videos in 'temp', 'test', and 'purged' splits don't have labels (per business rules).

4. When the parent row is deleted, all child rows referencing it are also deleted automatically.

5. All operations in the transaction are rolled back (undone). The database returns to its state before the transaction started.

</details>

---

## Hands-On Exercise 1

### Setup

```bash
# Connect to your local PostgreSQL
psql -U reachy_app -d reachy_local
```

### Tasks

1. **Insert test videos:**
   
   ```sql
   INSERT INTO video (file_path, split, size_bytes) VALUES
    ('videos/exercise/001.mp4', 'temp', 1024000),
    ('videos/exercise/002.mp4', 'temp', 2048000),
    ('videos/exercise/003.mp4', 'temp', 512000);
   ```

2. **Promote one video to dataset_all:**
   
   ```sql
   UPDATE video
   SET split = 'dataset_all', label = 'happy'
   WHERE file_path = 'videos/exercise/001.mp4';
   ```

3. **Query to verify:**
   
   ```sql
   SELECT file_path, split, label
   FROM video
   WHERE file_path LIKE 'videos/exercise/%';
   ```

4. **Try to violate a constraint:**
   
   ```sql
   -- This should fail! (dataset_all requires label)
   UPDATE video
   SET split = 'dataset_all', label = NULL
   WHERE file_path = 'videos/exercise/002.mp4';
   ```

5. **Clean up:**
   
   ```sql
   DELETE FROM video WHERE file_path LIKE 'videos/exercise/%';
   ```

---

## Summary

In this module, you learned:

- ✅ What databases are and why we use PostgreSQL
- ✅ Tables, rows, columns, and data types
- ✅ Primary keys and foreign keys
- ✅ Basic SQL: SELECT, INSERT, UPDATE, DELETE
- ✅ Constraints: NOT NULL, UNIQUE, CHECK, FOREIGN KEY
- ✅ Transactions and ACID properties

**Next**: [Module 2: PostgreSQL Essentials](./02-MODULE-POSTGRESQL-ESSENTIALS.md)
