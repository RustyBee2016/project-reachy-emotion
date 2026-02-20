# Week 1: Database Fundamentals & PostgreSQL Essentials

**Phase 1 Tutorial Series**  
**Duration**: ~8 hours  
**Prerequisites**: Python basics, project cloned

---

## Overview

This week covers the first two modules of the database curriculum:
- **Module 1**: Database Fundamentals (4 hours)
- **Module 2**: PostgreSQL Essentials (4 hours)

### Weekly Goals
- [ ] Understand relational database concepts
- [ ] Write basic SQL queries
- [ ] Set up PostgreSQL locally
- [ ] Connect using `psql` command-line tool

---

## Day 1-2: Module 1 — Database Fundamentals

### Study Materials

Read the complete module:
```
docs/database/curriculum/01-MODULE-DATABASE-FUNDAMENTALS.md
```

### Key Concepts to Master

#### 1. Why Databases?

Databases solve problems that files/spreadsheets can't:
- **Duplicates** → UNIQUE constraints
- **Invalid data** → CHECK constraints, ENUMs
- **Slow searches** → Indexes
- **Concurrent access** → Transactions, locking
- **Undo mistakes** → Rollback, recovery

#### 2. Tables, Rows, Columns

Think of a table like a spreadsheet:
```
┌─────────────────────────────────────────────────────────────────────┐
│                         video (table)                                │
├──────────────────┬──────────────────┬─────────────┬─────────────────┤
│ video_id (PK)    │ file_path        │ split       │ label           │
├──────────────────┼──────────────────┼─────────────┼─────────────────┤
│ abc-123-def      │ videos/001.mp4   │ dataset_all │ happy           │
│ xyz-789-ghi      │ videos/002.mp4   │ train       │ sad             │
└──────────────────┴──────────────────┴─────────────┴─────────────────┘
```

#### 3. Primary Keys vs Foreign Keys

| Key Type | Purpose | Example |
|----------|---------|---------|
| **Primary Key** | Uniquely identifies each row | `video_id` |
| **Foreign Key** | References another table | `run_id REFERENCES training_run` |

#### 4. Basic SQL Commands (CRUD)

```sql
-- CREATE (Insert)
INSERT INTO video (file_path, split) VALUES ('videos/001.mp4', 'temp');

-- READ (Select)
SELECT * FROM video WHERE split = 'train';

-- UPDATE
UPDATE video SET label = 'happy' WHERE video_id = 'abc-123';

-- DELETE
DELETE FROM video WHERE split = 'temp';
```

#### 5. Transactions and ACID

A **transaction** groups operations that must all succeed or all fail:

```sql
BEGIN;
UPDATE video SET split = 'dataset_all', label = 'happy' WHERE video_id = 'abc-123';
INSERT INTO promotion_log (video_id, from_split, to_split) VALUES ('abc-123', 'temp', 'dataset_all');
COMMIT;  -- All or nothing!
```

### Exercises

Complete the hands-on exercises in Module 1:
1. Insert test videos
2. Promote a video to dataset_all
3. Query to verify changes
4. Try to violate a constraint (observe the error)
5. Clean up test data

### Checkpoint: Days 1-2
- [ ] Read Module 1 completely
- [ ] Understand tables, rows, columns, keys
- [ ] Know the four CRUD operations
- [ ] Understand transactions and ACID

---

## Day 3-4: Module 2 — PostgreSQL Essentials

### Study Materials

Read the complete module:
```
docs/database/curriculum/02-MODULE-POSTGRESQL-ESSENTIALS.md
```

### Key Concepts to Master

#### 1. PostgreSQL Setup

```bash
# Install PostgreSQL 16
sudo apt install postgresql-16

# Start the service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
CREATE USER reachy_app WITH PASSWORD 'dev_password';
CREATE DATABASE reachy_local OWNER reachy_app;
\q
```

#### 2. Using psql

```bash
# Connect to database
psql -U reachy_app -d reachy_local

# Common psql commands
\dt          -- List tables
\d video     -- Describe video table
\l           -- List databases
\du          -- List users
\q           -- Quit
```

#### 3. PostgreSQL Data Types

| Type | Description | Example |
|------|-------------|---------|
| `UUID` | Unique identifier | `'550e8400-e29b-41d4-a716-446655440000'` |
| `VARCHAR(n)` | Text up to n chars | `'videos/001.mp4'` |
| `INTEGER` | Whole numbers | `42` |
| `NUMERIC(p,s)` | Precise decimals | `3.14159` |
| `BOOLEAN` | True/false | `TRUE` |
| `TIMESTAMPTZ` | Date/time with timezone | `'2025-01-05 14:30:00+00'` |
| `JSONB` | JSON data (binary) | `'{"key": "value"}'` |

#### 4. Custom Types (ENUMs)

Reachy uses custom ENUM types:

```sql
-- Emotion labels
CREATE TYPE emotion_label AS ENUM (
    'anger', 'contempt', 'disgust', 'fear',
    'happiness', 'neutral', 'sadness', 'surprise'
);

-- Video splits
CREATE TYPE video_split AS ENUM (
    'temp', 'dataset_all', 'train', 'test', 'purged'
);
```

#### 5. Indexes for Performance

```sql
-- Create index for faster lookups
CREATE INDEX idx_video_split ON video(split);
CREATE INDEX idx_video_label ON video(label);

-- Query uses index automatically
SELECT * FROM video WHERE split = 'train';  -- Fast!
```

### Exercises

1. **Connect to PostgreSQL**:
   ```bash
   psql -U reachy_app -d reachy_local
   ```

2. **Explore the schema**:
   ```sql
   \dt                    -- List all tables
   \d video               -- Describe video table
   SELECT * FROM video LIMIT 5;
   ```

3. **Practice queries**:
   ```sql
   -- Count videos by split
   SELECT split, COUNT(*) FROM video GROUP BY split;
   
   -- Find videos without labels
   SELECT file_path FROM video WHERE label IS NULL;
   
   -- Join tables
   SELECT v.file_path, tr.strategy
   FROM video v
   JOIN training_selection ts ON v.video_id = ts.video_id
   JOIN training_run tr ON ts.run_id = tr.run_id;
   ```

### Checkpoint: Days 3-4
- [ ] PostgreSQL installed and running
- [ ] Can connect using psql
- [ ] Know common psql commands
- [ ] Understand PostgreSQL data types
- [ ] Can write basic queries

---

## Day 5: Practice & Review

### Comprehensive Exercise

Create a test workflow:

```sql
-- 1. Insert a test video
INSERT INTO video (file_path, split, size_bytes)
VALUES ('videos/week1_test.mp4', 'temp', 1024000)
RETURNING video_id;

-- 2. Check it exists
SELECT * FROM video WHERE file_path = 'videos/week1_test.mp4';

-- 3. Promote it (add label, change split)
UPDATE video 
SET split = 'dataset_all', label = 'happy'
WHERE file_path = 'videos/week1_test.mp4';

-- 4. Verify the promotion
SELECT file_path, split, label FROM video 
WHERE file_path = 'videos/week1_test.mp4';

-- 5. Clean up
DELETE FROM video WHERE file_path = 'videos/week1_test.mp4';
```

### Knowledge Check

Answer these questions (check Module 1 for answers):

1. What is the difference between PRIMARY KEY and FOREIGN KEY?
2. What SQL command reads data from a table?
3. Why does the `video` table allow NULL for the `label` column?
4. What does `ON DELETE CASCADE` do?
5. In a transaction, what happens if one operation fails?

### Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Tables, rows, columns | __ |
| Primary/foreign keys | __ |
| SELECT queries | __ |
| INSERT/UPDATE/DELETE | __ |
| Transactions | __ |
| psql commands | __ |
| PostgreSQL data types | __ |

**If any rating is 1**: Re-read that section of the module.  
**If any rating is 2**: Do more practice exercises.  
**If all ratings are 3**: Ready for Week 2!

---

## Week 1 Deliverables

| Deliverable | Status |
|-------------|--------|
| Module 1 read | [ ] |
| Module 2 read | [ ] |
| PostgreSQL installed | [ ] |
| psql connection working | [ ] |
| Practice queries completed | [ ] |
| Knowledge check passed | [ ] |

---

## Troubleshooting

### Can't connect to PostgreSQL

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check if user exists
sudo -u postgres psql -c "\du"
```

### Permission denied

```bash
# Grant permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE reachy_local TO reachy_app;"
```

### Database doesn't exist

```bash
# Create it
sudo -u postgres psql -c "CREATE DATABASE reachy_local OWNER reachy_app;"
```

---

## Next Week

[Week 2: Reachy Schema & Stored Procedures](WEEK_02_REACHY_SCHEMA.md) covers:
- All 12 Reachy database tables
- Video lifecycle (temp → dataset_all → train/test)
- Stored procedures for business logic
