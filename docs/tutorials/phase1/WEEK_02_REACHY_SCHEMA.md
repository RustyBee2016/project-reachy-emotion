# Week 2: Reachy Schema & Stored Procedures

**Phase 1 Tutorial Series**  
**Duration**: ~7 hours  
**Prerequisites**: Week 1 complete, PostgreSQL running

---

## Overview

This week covers:
- **Module 3**: Reachy Schema Deep Dive (4 hours)
- **Module 4**: Stored Procedures & Business Logic (3 hours)

### Weekly Goals
- [ ] Understand all 12 Reachy database tables
- [ ] Master the video lifecycle (temp → dataset_all → train/test → purged)
- [ ] Use stored procedures for business operations
- [ ] Understand the split/label policy constraints

---

## Day 1-2: Module 3 — Reachy Schema Deep Dive

### Study Materials

Read the complete module:
```
docs/database/curriculum/03-MODULE-REACHY-SCHEMA.md
```

### Key Concepts to Master

#### 1. The 12 Reachy Tables

```
Core Tables (Phase 1)
├── video                 -- All video metadata
├── training_run          -- Training job configurations
├── training_selection    -- Which videos in which runs
├── promotion_log         -- Audit trail for promotions
└── label_event           -- Labeling history

Agent Support Tables
├── ingest_job            -- Ingest agent tracking
├── reconcile_report      -- Reconciler findings
├── purge_log             -- Privacy agent deletions
├── deployment_record     -- Model deployments
└── gate_validation       -- Gate A/B/C results

Metrics Tables
├── inference_metric      -- Real-time inference stats
└── training_metric       -- Training run metrics
```

#### 2. The Video Table (Core)

```sql
CREATE TABLE video (
    video_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path    VARCHAR(500) NOT NULL,
    split        video_split NOT NULL DEFAULT 'temp',
    label        emotion_label,                 -- Can be NULL!
    sha256       CHAR(64),
    duration_sec NUMERIC(10,2),
    width        INTEGER,
    height       INTEGER,
    fps          NUMERIC(5,2),
    size_bytes   BIGINT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE (sha256, size_bytes)  -- Prevent duplicates
);
```

#### 3. Video Lifecycle & Split/Label Policy

**The most important business rule**:

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

**Split/Label Rules**:

| Split | Label Required? | Why |
|-------|-----------------|-----|
| `temp` | NO (NULL) | Waiting for human review |
| `dataset_all` | YES | Approved for training |
| `train` | YES | Used for model training |
| `test` | NO (NULL) | Avoid test data leakage |
| `purged` | NO (NULL) | Deleted for privacy |

#### 4. Training Tables

```sql
-- Training run configuration
CREATE TABLE training_run (
    run_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy        VARCHAR(50) NOT NULL,      -- 'balanced_random', 'stratified'
    train_fraction  NUMERIC(3,2) NOT NULL,     -- 0.70 = 70% train
    test_fraction   NUMERIC(3,2) NOT NULL,     -- 0.30 = 30% test
    seed            INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now(),
    
    CHECK (train_fraction + test_fraction <= 1.0)
);

-- Which videos are in which run
CREATE TABLE training_selection (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES training_run(run_id) ON DELETE CASCADE,
    video_id     UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
    target_split video_split NOT NULL,
    selected_at  TIMESTAMPTZ DEFAULT now()
);
```

#### 5. Audit Tables

```sql
-- Track all promotions
CREATE TABLE promotion_log (
    id          BIGSERIAL PRIMARY KEY,
    video_id    UUID NOT NULL REFERENCES video(video_id),
    from_split  video_split NOT NULL,
    to_split    video_split NOT NULL,
    label       emotion_label,
    user_id     VARCHAR(255),
    promoted_at TIMESTAMPTZ DEFAULT now()
);

-- Track all labeling events
CREATE TABLE label_event (
    id          BIGSERIAL PRIMARY KEY,
    video_id    UUID NOT NULL REFERENCES video(video_id),
    action      VARCHAR(20) NOT NULL,  -- 'assign', 'change', 'remove'
    old_label   emotion_label,
    new_label   emotion_label,
    user_id     VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Exercises

1. **Explore the schema**:
   ```sql
   -- List all tables
   \dt
   
   -- Describe each core table
   \d video
   \d training_run
   \d training_selection
   \d promotion_log
   ```

2. **Query relationships**:
   ```sql
   -- Find all videos in a training run
   SELECT v.file_path, v.label, ts.target_split
   FROM video v
   JOIN training_selection ts ON v.video_id = ts.video_id
   WHERE ts.run_id = '<some-run-id>';
   
   -- Count videos by split and label
   SELECT split, label, COUNT(*) 
   FROM video 
   GROUP BY split, label 
   ORDER BY split, label;
   ```

3. **Test the lifecycle**:
   ```sql
   -- Insert a temp video
   INSERT INTO video (file_path, split) 
   VALUES ('videos/lifecycle_test.mp4', 'temp');
   
   -- Try to promote without label (should work for temp)
   SELECT * FROM video WHERE file_path = 'videos/lifecycle_test.mp4';
   
   -- Promote to dataset_all (must add label)
   UPDATE video 
   SET split = 'dataset_all', label = 'happy'
   WHERE file_path = 'videos/lifecycle_test.mp4';
   
   -- Clean up
   DELETE FROM video WHERE file_path = 'videos/lifecycle_test.mp4';
   ```

### Checkpoint: Days 1-2
- [ ] Know all 12 tables and their purposes
- [ ] Understand video lifecycle
- [ ] Know split/label policy rules
- [ ] Can query relationships between tables

---

## Day 3-4: Module 4 — Stored Procedures

### Study Materials

Read the complete module:
```
docs/database/curriculum/04-MODULE-STORED-PROCEDURES.md
```

Also review the SQL file:
```
alembic/versions/002_stored_procedures.sql
```

### Key Concepts to Master

#### 1. Why Stored Procedures?

- **Encapsulation**: Business logic in one place
- **Atomicity**: Multiple operations in one transaction
- **Performance**: Reduced network round-trips
- **Security**: Control access to data operations

#### 2. Key Stored Procedures

**Promote Video**:
```sql
-- Promotes a video from temp to dataset_all
CREATE OR REPLACE FUNCTION promote_video(
    p_video_id UUID,
    p_label emotion_label,
    p_user_id VARCHAR(255)
) RETURNS void AS $$
BEGIN
    -- Update video
    UPDATE video 
    SET split = 'dataset_all', label = p_label, updated_at = now()
    WHERE video_id = p_video_id AND split = 'temp';
    
    -- Log the promotion
    INSERT INTO promotion_log (video_id, from_split, to_split, label, user_id)
    VALUES (p_video_id, 'temp', 'dataset_all', p_label, p_user_id);
END;
$$ LANGUAGE plpgsql;
```

**Sample for Training**:
```sql
-- Samples videos for a training run
CREATE OR REPLACE FUNCTION sample_for_training(
    p_run_id UUID,
    p_train_fraction NUMERIC,
    p_seed INTEGER DEFAULT NULL
) RETURNS TABLE(video_id UUID, target_split video_split) AS $$
BEGIN
    -- Set random seed if provided
    IF p_seed IS NOT NULL THEN
        PERFORM setseed(p_seed::NUMERIC / 2147483647);
    END IF;
    
    -- Return sampled videos
    RETURN QUERY
    SELECT v.video_id,
           CASE WHEN random() < p_train_fraction 
                THEN 'train'::video_split 
                ELSE 'test'::video_split 
           END as target_split
    FROM video v
    WHERE v.split = 'dataset_all';
END;
$$ LANGUAGE plpgsql;
```

**Get Dataset Stats**:
```sql
-- Returns dataset statistics
CREATE OR REPLACE FUNCTION get_dataset_stats()
RETURNS TABLE(
    split video_split,
    label emotion_label,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT v.split, v.label, COUNT(*)::BIGINT
    FROM video v
    GROUP BY v.split, v.label
    ORDER BY v.split, v.label;
END;
$$ LANGUAGE plpgsql;
```

#### 3. Calling Stored Procedures

```sql
-- Promote a video
SELECT promote_video(
    'abc-123-def'::UUID,
    'happy'::emotion_label,
    'alice@example.com'
);

-- Get dataset stats
SELECT * FROM get_dataset_stats();

-- Sample for training
SELECT * FROM sample_for_training(
    'run-001'::UUID,
    0.7,  -- 70% train
    42    -- seed for reproducibility
);
```

#### 4. Error Handling

```sql
CREATE OR REPLACE FUNCTION safe_promote_video(
    p_video_id UUID,
    p_label emotion_label,
    p_user_id VARCHAR(255)
) RETURNS BOOLEAN AS $$
DECLARE
    v_current_split video_split;
BEGIN
    -- Check current state
    SELECT split INTO v_current_split
    FROM video WHERE video_id = p_video_id;
    
    IF v_current_split IS NULL THEN
        RAISE EXCEPTION 'Video not found: %', p_video_id;
    END IF;
    
    IF v_current_split != 'temp' THEN
        RAISE EXCEPTION 'Video not in temp split: %', v_current_split;
    END IF;
    
    -- Perform promotion
    PERFORM promote_video(p_video_id, p_label, p_user_id);
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error promoting video: %', SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
```

### Exercises

1. **Use existing procedures**:
   ```sql
   -- Get current stats
   SELECT * FROM get_dataset_stats();
   
   -- Check class balance
   SELECT label, SUM(count) as total
   FROM get_dataset_stats()
   WHERE split IN ('dataset_all', 'train')
   GROUP BY label;
   ```

2. **Test promotion workflow**:
   ```sql
   -- Insert test video
   INSERT INTO video (file_path, split) 
   VALUES ('videos/proc_test.mp4', 'temp')
   RETURNING video_id;
   
   -- Promote using stored procedure
   SELECT promote_video(
       '<video_id>'::UUID,
       'sad'::emotion_label,
       'test_user'
   );
   
   -- Verify promotion logged
   SELECT * FROM promotion_log 
   WHERE video_id = '<video_id>';
   
   -- Clean up
   DELETE FROM video WHERE file_path = 'videos/proc_test.mp4';
   ```

3. **Create a simple procedure**:
   ```sql
   -- Count videos by emotion
   CREATE OR REPLACE FUNCTION count_by_emotion(p_emotion emotion_label)
   RETURNS BIGINT AS $$
   DECLARE
       v_count BIGINT;
   BEGIN
       SELECT COUNT(*) INTO v_count
       FROM video
       WHERE label = p_emotion;
       RETURN v_count;
   END;
   $$ LANGUAGE plpgsql;
   
   -- Test it
   SELECT count_by_emotion('happy');
   SELECT count_by_emotion('sad');
   ```

### Checkpoint: Days 3-4
- [ ] Understand why stored procedures are useful
- [ ] Can call existing procedures
- [ ] Understand promote_video workflow
- [ ] Can write simple procedures

---

## Day 5: Practice & Review

### Comprehensive Exercise

Simulate a complete video workflow:

```sql
-- 1. Create a training run
INSERT INTO training_run (strategy, train_fraction, test_fraction, seed)
VALUES ('stratified', 0.7, 0.3, 42)
RETURNING run_id;

-- 2. Insert test videos
INSERT INTO video (file_path, split) VALUES
    ('videos/week2_test_001.mp4', 'temp'),
    ('videos/week2_test_002.mp4', 'temp'),
    ('videos/week2_test_003.mp4', 'temp');

-- 3. Promote videos with labels
UPDATE video SET split = 'dataset_all', label = 'happy'
WHERE file_path = 'videos/week2_test_001.mp4';

UPDATE video SET split = 'dataset_all', label = 'sad'
WHERE file_path = 'videos/week2_test_002.mp4';

UPDATE video SET split = 'dataset_all', label = 'happy'
WHERE file_path = 'videos/week2_test_003.mp4';

-- 4. Check dataset stats
SELECT * FROM get_dataset_stats();

-- 5. Sample for training (using the run_id from step 1)
INSERT INTO training_selection (run_id, video_id, target_split)
SELECT '<run_id>'::UUID, video_id, 
       CASE WHEN random() < 0.7 THEN 'train' ELSE 'test' END
FROM video
WHERE split = 'dataset_all' AND file_path LIKE 'videos/week2_test%';

-- 6. Verify selections
SELECT v.file_path, v.label, ts.target_split
FROM video v
JOIN training_selection ts ON v.video_id = ts.video_id
WHERE ts.run_id = '<run_id>';

-- 7. Clean up
DELETE FROM training_selection WHERE run_id = '<run_id>';
DELETE FROM training_run WHERE run_id = '<run_id>';
DELETE FROM video WHERE file_path LIKE 'videos/week2_test%';
```

### Knowledge Check

1. What are the 5 video splits and their label requirements?
2. Why does the `test` split have NULL labels?
3. What does `ON DELETE CASCADE` do for `training_selection`?
4. How do stored procedures ensure atomic operations?
5. What happens if you try to promote a video that's not in `temp`?

### Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Video lifecycle | __ |
| Split/label policy | __ |
| Table relationships | __ |
| Stored procedures | __ |
| Error handling in SQL | __ |

---

## Week 2 Deliverables

| Deliverable | Status |
|-------------|--------|
| Module 3 read | [ ] |
| Module 4 read | [ ] |
| All 12 tables understood | [ ] |
| Video lifecycle mastered | [ ] |
| Stored procedures used | [ ] |
| Comprehensive exercise complete | [ ] |

---

## Next Week

[Week 3: Python ORM & API Integration](WEEK_03_PYTHON_ORM.md) covers:
- SQLAlchemy ORM models
- Python database access
- FastAPI integration
