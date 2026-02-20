# Week 4: Migrations & Troubleshooting

**Phase 1 Tutorial Series**  
**Duration**: ~5 hours  
**Prerequisites**: Weeks 1-3 complete

---

## Overview

This week covers:
- **Module 7**: Migrations & DevOps (3 hours)
- **Module 8**: Troubleshooting & Known Issues (2 hours)

### Weekly Goals
- [ ] Understand database migrations
- [ ] Run and create migrations
- [ ] Debug common database issues
- [ ] Complete the database track

---

## Day 1-2: Module 7 — Migrations & DevOps

### Study Materials

Read the complete module:
```
docs/database/curriculum/07-MODULE-MIGRATIONS-DEVOPS.md
```

Also review:
```
alembic/versions/001_phase1_schema.sql
alembic/versions/002_stored_procedures.sql
alembic/versions/003_missing_tables.sql
alembic.ini
```

### Key Concepts to Master

#### 1. What Are Migrations?

**Migrations** are versioned changes to your database schema:

```
Version 001: Create video table
Version 002: Add stored procedures
Version 003: Add agent support tables
```

**Benefits**:
- Track schema changes in version control
- Apply changes consistently across environments
- Roll back if something goes wrong
- Team members get same schema

#### 2. Reachy Migration Files

```
alembic/versions/
├── 001_phase1_schema.sql      # Core tables
├── 002_stored_procedures.sql  # Business logic
└── 003_missing_tables.sql     # Agent support
```

**001_phase1_schema.sql** creates:
- Custom types (emotion_label, video_split)
- Core tables (video, training_run, training_selection)
- Audit tables (promotion_log, label_event)
- Indexes for performance

**002_stored_procedures.sql** creates:
- promote_video()
- sample_for_training()
- get_dataset_stats()

**003_missing_tables.sql** creates:
- Agent support tables (ingest_job, reconcile_report, etc.)
- Metrics tables (inference_metric, training_metric)

#### 3. Running Migrations Manually

```bash
# Connect to PostgreSQL
psql -U reachy_app -d reachy_local

# Run migrations in order
\i alembic/versions/001_phase1_schema.sql
\i alembic/versions/002_stored_procedures.sql
\i alembic/versions/003_missing_tables.sql

# Verify tables created
\dt
```

#### 4. Using the Bootstrap Script

```bash
# Run the setup script
bash misc/code/bootstrap_reachy_db_and_media.sh

# This script:
# 1. Creates database and user
# 2. Runs all migrations
# 3. Creates media directories
# 4. Sets permissions
```

#### 5. Creating New Migrations

When you need to change the schema:

```sql
-- alembic/versions/004_add_confidence_column.sql

-- Add confidence column to video table
ALTER TABLE video ADD COLUMN confidence NUMERIC(4,3);

-- Add index for filtering by confidence
CREATE INDEX idx_video_confidence ON video(confidence);

-- Comment explaining the change
COMMENT ON COLUMN video.confidence IS 'Model confidence score for auto-labeled videos';
```

**Best Practices**:
- One logical change per migration
- Include rollback instructions in comments
- Test on development database first
- Never modify existing migrations

#### 6. Rollback Strategy

```sql
-- In 004_add_confidence_column.sql, add rollback section:

-- ROLLBACK:
-- ALTER TABLE video DROP COLUMN confidence;
-- DROP INDEX idx_video_confidence;
```

To rollback:
```bash
# Copy rollback SQL and run it
psql -U reachy_app -d reachy_local -c "ALTER TABLE video DROP COLUMN confidence;"
```

### Exercises

1. **Check current schema**:
   ```bash
   psql -U reachy_app -d reachy_local
   \dt                    # List tables
   \d video               # Describe video table
   \df                    # List functions
   ```

2. **Create a test migration**:
   ```sql
   -- Create file: alembic/versions/999_test_migration.sql
   
   -- Add a test column
   ALTER TABLE video ADD COLUMN test_column VARCHAR(50);
   
   -- Verify
   -- \d video
   
   -- ROLLBACK:
   -- ALTER TABLE video DROP COLUMN test_column;
   ```

3. **Run and rollback**:
   ```bash
   # Run migration
   psql -U reachy_app -d reachy_local -f alembic/versions/999_test_migration.sql
   
   # Verify column added
   psql -U reachy_app -d reachy_local -c "\d video"
   
   # Rollback
   psql -U reachy_app -d reachy_local -c "ALTER TABLE video DROP COLUMN test_column;"
   
   # Delete test file
   rm alembic/versions/999_test_migration.sql
   ```

### Checkpoint: Days 1-2
- [ ] Understand migration concept
- [ ] Can run existing migrations
- [ ] Can create simple migrations
- [ ] Understand rollback strategy

---

## Day 3-4: Module 8 — Troubleshooting

### Study Materials

Read the complete module:
```
docs/database/curriculum/08-MODULE-TROUBLESHOOTING.md
```

Also review:
```
docs/database/07-KNOWN-ISSUES.md
docs/database/08-SETUP-GUIDE.md
```

### Common Issues and Solutions

#### 1. Connection Refused

**Symptom**:
```
psql: error: connection refused
Is the server running on host "localhost" and accepting TCP/IP connections on port 5432?
```

**Solutions**:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check if listening on correct port
sudo netstat -tlnp | grep 5432

# Check pg_hba.conf for local connections
sudo cat /etc/postgresql/16/main/pg_hba.conf
```

#### 2. Authentication Failed

**Symptom**:
```
FATAL: password authentication failed for user "reachy_app"
```

**Solutions**:
```bash
# Reset password
sudo -u postgres psql -c "ALTER USER reachy_app WITH PASSWORD 'new_password';"

# Check user exists
sudo -u postgres psql -c "\du"

# Create user if missing
sudo -u postgres psql -c "CREATE USER reachy_app WITH PASSWORD 'password';"
```

#### 3. Database Does Not Exist

**Symptom**:
```
FATAL: database "reachy_local" does not exist
```

**Solutions**:
```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE reachy_local OWNER reachy_app;"

# List databases to verify
sudo -u postgres psql -c "\l"
```

#### 4. Permission Denied

**Symptom**:
```
ERROR: permission denied for table video
```

**Solutions**:
```bash
# Grant permissions
sudo -u postgres psql -d reachy_local -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO reachy_app;"
sudo -u postgres psql -d reachy_local -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO reachy_app;"
```

#### 5. Constraint Violation

**Symptom**:
```
ERROR: duplicate key value violates unique constraint "video_sha256_size_bytes_key"
```

**Solutions**:
```sql
-- Find the duplicate
SELECT sha256, size_bytes, COUNT(*) 
FROM video 
GROUP BY sha256, size_bytes 
HAVING COUNT(*) > 1;

-- Delete duplicates (keep one)
DELETE FROM video 
WHERE video_id IN (
    SELECT video_id FROM (
        SELECT video_id, ROW_NUMBER() OVER (
            PARTITION BY sha256, size_bytes 
            ORDER BY created_at
        ) as rn
        FROM video
    ) t WHERE rn > 1
);
```

#### 6. Foreign Key Violation

**Symptom**:
```
ERROR: insert or update on table "training_selection" violates foreign key constraint
```

**Solutions**:
```sql
-- Check if referenced record exists
SELECT * FROM training_run WHERE run_id = '<the-run-id>';
SELECT * FROM video WHERE video_id = '<the-video-id>';

-- Create missing record first, then retry
```

#### 7. Slow Queries

**Symptom**: Queries taking too long

**Solutions**:
```sql
-- Check if indexes exist
\di

-- Add missing indexes
CREATE INDEX idx_video_split ON video(split);
CREATE INDEX idx_video_label ON video(label);

-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM video WHERE split = 'train';

-- Update statistics
ANALYZE video;
```

#### 8. Connection Pool Exhausted

**Symptom**:
```
FATAL: too many connections for role "reachy_app"
```

**Solutions**:
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity WHERE usename = 'reachy_app';

-- Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE usename = 'reachy_app' AND state = 'idle';

-- Increase connection limit (in postgresql.conf)
-- max_connections = 200
```

### Debugging Checklist

When something goes wrong:

1. **Read the error message carefully**
2. **Check service status**: `systemctl status postgresql`
3. **Check logs**: `tail -f /var/log/postgresql/postgresql-16-main.log`
4. **Verify connection**: `psql -U reachy_app -d reachy_local -c "SELECT 1"`
5. **Check permissions**: `\dp` in psql
6. **Check constraints**: `\d tablename` in psql

### Exercises

1. **Simulate and fix connection error**:
   ```bash
   # Stop PostgreSQL
   sudo systemctl stop postgresql
   
   # Try to connect (should fail)
   psql -U reachy_app -d reachy_local
   
   # Start PostgreSQL
   sudo systemctl start postgresql
   
   # Connect (should work)
   psql -U reachy_app -d reachy_local
   ```

2. **Check for slow queries**:
   ```sql
   -- Enable query logging (temporarily)
   SET log_statement = 'all';
   SET log_duration = on;
   
   -- Run some queries
   SELECT * FROM video WHERE split = 'train';
   SELECT * FROM video WHERE label = 'happy';
   
   -- Check execution plans
   EXPLAIN ANALYZE SELECT * FROM video WHERE split = 'train';
   ```

3. **Practice constraint handling**:
   ```sql
   -- Try to insert duplicate (should fail)
   INSERT INTO video (file_path, split, sha256, size_bytes)
   VALUES ('test.mp4', 'temp', 'abc123', 1000);
   
   INSERT INTO video (file_path, split, sha256, size_bytes)
   VALUES ('test2.mp4', 'temp', 'abc123', 1000);  -- Same hash+size
   
   -- Clean up
   DELETE FROM video WHERE file_path LIKE 'test%.mp4';
   ```

### Checkpoint: Days 3-4
- [ ] Can diagnose connection issues
- [ ] Can fix permission problems
- [ ] Understand constraint violations
- [ ] Know how to check query performance

---

## Day 5: Database Track Review

### Comprehensive Review

You've completed the database curriculum! Let's verify your knowledge:

#### Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REACHY DATABASE QUICK REFERENCE                   │
├─────────────────────────────────────────────────────────────────────┤
│ CONNECTION                                                           │
│   psql -U reachy_app -d reachy_local                                │
│                                                                      │
│ COMMON COMMANDS                                                      │
│   \dt          List tables                                          │
│   \d video     Describe table                                       │
│   \df          List functions                                       │
│   \q           Quit                                                 │
│                                                                      │
│ VIDEO LIFECYCLE                                                      │
│   temp (NULL) → dataset_all (labeled) → train/test                  │
│                                                                      │
│ KEY TABLES                                                           │
│   video, training_run, training_selection, promotion_log            │
│                                                                      │
│ STORED PROCEDURES                                                    │
│   promote_video(), sample_for_training(), get_dataset_stats()       │
│                                                                      │
│ TROUBLESHOOTING                                                      │
│   systemctl status postgresql                                       │
│   tail -f /var/log/postgresql/postgresql-16-main.log               │
└─────────────────────────────────────────────────────────────────────┘
```

#### Final Knowledge Check

1. Name the 5 video splits and their label requirements
2. What is the purpose of the `training_selection` table?
3. How do you call the `promote_video` stored procedure?
4. What does `ON DELETE CASCADE` do?
5. How do you check if PostgreSQL is running?

#### Self-Assessment

Rate your understanding (1-3):

| Topic | Rating |
|-------|--------|
| SQL basics (CRUD) | __ |
| PostgreSQL setup | __ |
| Reachy schema | __ |
| Stored procedures | __ |
| SQLAlchemy ORM | __ |
| Repository pattern | __ |
| Migrations | __ |
| Troubleshooting | __ |

**All 3s?** → Ready for statistical analysis!  
**Any 1s or 2s?** → Review those modules before continuing.

---

## Week 4 Deliverables

| Deliverable | Status |
|-------------|--------|
| Module 7 read | [ ] |
| Module 8 read | [ ] |
| Migrations understood | [ ] |
| Troubleshooting practiced | [ ] |
| Final knowledge check passed | [ ] |
| **Database track complete** | [ ] |

---

## Database Track Complete! 🎉

Congratulations, Russ! You've completed the database portion of Phase 1.

### What You've Learned

- ✅ Relational database concepts
- ✅ SQL queries (SELECT, INSERT, UPDATE, DELETE)
- ✅ PostgreSQL setup and administration
- ✅ All 12 Reachy database tables
- ✅ Video lifecycle and split/label policy
- ✅ Stored procedures for business logic
- ✅ SQLAlchemy ORM in Python
- ✅ Repository and service patterns
- ✅ Database migrations
- ✅ Troubleshooting common issues

### Next: Statistical Analysis Track

[Week 5: Quality Gate Metrics](WEEK_05_QUALITY_GATE_METRICS.md) begins the statistical analysis portion of Phase 1.
