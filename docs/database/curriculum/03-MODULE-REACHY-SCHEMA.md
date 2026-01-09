# Module 3: Reachy Schema Deep Dive

**Duration**: 4 hours
**Prerequisites**: Modules 1-2
**Goal**: Master all 12 tables in the Reachy database and understand their relationships

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain the purpose of each table in the database
2. Understand the video lifecycle from capture to training
3. Navigate relationships between tables
4. Write queries to answer business questions
5. Identify which table to use for each use case

---

## Lesson 3.1: The Big Picture (30 minutes)

### Database Purpose

The Reachy database tracks **metadata** about emotion recognition videos:

```
┌────────────────────────────────────────────────────────────────────────┐
│                    REACHY DATA FLOW                                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Jetson Camera ───▶ MP4 Files ───▶ PostgreSQL Metadata                │
│   (captures)        (on disk)       (in database)                      │
│                                                                         │
│   The database does NOT store video files!                             │
│   It stores paths, labels, sizes, hashes, etc.                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Table Categories

The 12 tables are organized into four functional groups:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        12 REACHY TABLES                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   CORE DATA (3 tables)                                              │
│   ├── video              - Video metadata registry                  │
│   ├── training_run       - ML training job tracking                 │
│   └── training_selection - Video-to-run assignments                 │
│                                                                      │
│   AUDIT & HISTORY (2 tables)                                        │
│   ├── promotion_log      - Video lifecycle changes                  │
│   └── label_event        - Human labeling decisions                 │
│                                                                      │
│   USER & EVENTS (3 tables)                                          │
│   ├── user_session       - Web UI user sessions                     │
│   ├── generation_request - AI video generation tracking             │
│   └── emotion_event      - Real-time emotion detections             │
│                                                                      │
│   OPERATIONS (4 tables)                                             │
│   ├── deployment_log     - Model deployments to Jetson              │
│   ├── audit_log          - GDPR/privacy compliance                  │
│   ├── obs_samples        - System metrics time-series               │
│   └── reconcile_report   - Filesystem/DB consistency                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Source Files Reference

| Group | SQL File | Lines |
|-------|----------|-------|
| Core Data | `alembic/versions/001_phase1_schema.sql` | 31-80 |
| Audit | `alembic/versions/001_phase1_schema.sql` | 81-117 |
| User & Events | `alembic/versions/001_phase1_schema.sql` | 118-175 |
| Operations | `alembic/versions/003_missing_tables.sql` | 1-297 |

---

## Lesson 3.2: Core Data Tables (1 hour)

### The `video` Table - Central Registry

**Source**: `001_phase1_schema.sql` lines 31-52

This is the most important table. Every video clip has one row here.

```sql
CREATE TABLE video (
    video_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path    VARCHAR(500) NOT NULL,
    split        video_split NOT NULL DEFAULT 'temp',
    label        emotion_label,
    sha256       CHAR(64),
    duration_sec NUMERIC(10,2),
    width        INTEGER,
    height       INTEGER,
    fps          NUMERIC(5,2),
    size_bytes   BIGINT,
    metadata     JSONB DEFAULT '{}'::JSONB,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now(),
    deleted_at   TIMESTAMPTZ  -- For soft deletes (GDPR)
);
```

**Column Breakdown:**

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| `video_id` | UUID | Unique identifier | `550e8400-e29b-41d4...` |
| `file_path` | VARCHAR(500) | Relative path to MP4 | `videos/temp/001.mp4` |
| `split` | ENUM | Lifecycle stage | `temp`, `dataset_all`, `train` |
| `label` | ENUM | Emotion classification | `happy`, `sad`, `angry` |
| `sha256` | CHAR(64) | File hash (deduplication) | `a1b2c3d4...` |
| `duration_sec` | NUMERIC | Video length | `5.25` |
| `width`, `height` | INTEGER | Video dimensions | `1920`, `1080` |
| `fps` | NUMERIC | Frames per second | `29.97` |
| `size_bytes` | BIGINT | File size | `1024000` |
| `metadata` | JSONB | Flexible extra data | `{"source": "jetson"}` |
| `created_at` | TIMESTAMPTZ | When added | `2025-01-05 14:30:00` |
| `updated_at` | TIMESTAMPTZ | Last modified | Auto-updated |
| `deleted_at` | TIMESTAMPTZ | Soft delete marker | NULL or timestamp |

**Key Constraints:**

```sql
-- Unique file (same hash + size = same file)
UNIQUE (sha256, size_bytes)

-- Business rule: Label required for dataset_all/train
CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
)
```

---

> ⚠️ **Known Issue #3: Check Constraint Inconsistency**
>
> The split/label policy constraint differs between files:
>
> **models.py** includes `'purged'`:
> ```python
> CheckConstraint(
>     "(split IN ('temp', 'test', 'purged') AND label IS NULL) OR ..."
> )
> ```
>
> **Alembic migration** is missing `'purged'`:
> ```python
> CheckConstraint(
>     "(split IN ('temp', 'test') AND label IS NULL) OR ..."  # Missing 'purged'!
> )
> ```
>
> **Impact**: Alembic-created databases reject purged videos.
>
> **Fix**: Add `'purged'` to the Alembic constraint.
>
> See: `docs/database/07-KNOWN-ISSUES.md` for details.

---

> ⚠️ **Known Issue #4: Missing Check Constraint in SQL**
>
> The SQL schema files (`001_phase1_schema.sql`) don't include the split/label policy constraint.
>
> **Impact**: Databases created with SQL files won't enforce business rules.
>
> **Fix**: Add to `001_phase1_schema.sql`:
> ```sql
> ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy CHECK (
>     (split IN ('temp', 'test', 'purged') AND label IS NULL)
>     OR (split IN ('dataset_all', 'train') AND label IS NOT NULL)
> );
> ```
>
> See: `docs/database/07-KNOWN-ISSUES.md` for details.

---

**Common Queries:**

```sql
-- Count videos by split
SELECT split, COUNT(*) FROM video GROUP BY split;

-- Find duplicates
SELECT sha256, size_bytes, COUNT(*)
FROM video
GROUP BY sha256, size_bytes
HAVING COUNT(*) > 1;

-- Recent uploads
SELECT file_path, created_at
FROM video
WHERE created_at > now() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Dataset class distribution
SELECT label, COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM video
WHERE split = 'dataset_all' AND deleted_at IS NULL
GROUP BY label;
```

### The `training_run` Table - ML Job Tracking

**Source**: `001_phase1_schema.sql` lines 59-67

Tracks each model training attempt:

```sql
CREATE TABLE training_run (
    run_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy       VARCHAR(100) NOT NULL,      -- 'balanced_random', 'stratified'
    train_fraction NUMERIC(3,2) NOT NULL,      -- 0.70 = 70% train
    test_fraction  NUMERIC(3,2) NOT NULL,      -- 0.30 = 30% test
    seed           BIGINT NOT NULL,            -- For reproducibility
    dataset_hash   CHAR(64),                   -- Hash of all videos used
    status         training_status NOT NULL DEFAULT 'pending',
    mlflow_run_id  VARCHAR(255),               -- Link to MLflow
    model_path     VARCHAR(500),               -- Path to .tlt model
    engine_path    VARCHAR(500),               -- Path to TensorRT .engine
    metrics        JSONB,                      -- F1, accuracy, etc.
    config         JSONB,                      -- Hyperparameters
    error_message  TEXT,                       -- If failed
    started_at     TIMESTAMPTZ,
    completed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- Constraint: fractions can't exceed 100%
CHECK (train_fraction + test_fraction <= 1.0)
```

**Status Lifecycle:**

```
pending ──▶ sampling ──▶ training ──▶ evaluating ──▶ completed
    │           │            │             │
    │           ▼            ▼             ▼
    └─────────────────── failed ◀─────────┘
                           │
                           ▼
                       cancelled
```

**Metrics Example:**

```json
{
    "accuracy": 0.87,
    "f1_score": 0.85,
    "precision": 0.86,
    "recall": 0.84,
    "confusion_matrix": [[85, 15], [12, 88]]
}
```

**Common Queries:**

```sql
-- Recent training runs
SELECT run_id, strategy, status, created_at
FROM training_run
ORDER BY created_at DESC
LIMIT 10;

-- Completed runs with best accuracy
SELECT run_id, strategy, metrics->>'accuracy' as accuracy
FROM training_run
WHERE status = 'completed' AND metrics IS NOT NULL
ORDER BY (metrics->>'accuracy')::NUMERIC DESC;

-- Failed runs with errors
SELECT run_id, error_message
FROM training_run
WHERE status = 'failed';
```

### The `training_selection` Table - Video Assignments

**Source**: `001_phase1_schema.sql` lines 69-80

Junction table linking videos to training runs:

```sql
CREATE TABLE training_selection (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES training_run(run_id) ON DELETE CASCADE,
    video_id     UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
    target_split video_split NOT NULL,  -- 'train' or 'test'
    selected_at  TIMESTAMPTZ DEFAULT now()
);
```

---

> ⚠️ **Known Issue #11: TrainingSelection PK Mismatch**
>
> SQL and Python models define different primary key structures:
>
> **SQL**: `id BIGSERIAL PRIMARY KEY` (single auto-increment column)
>
> **models.py**: Composite PK `(run_id, video_id, target_split)`
>
> **Impact**: Migration conflicts if both approaches are used.
>
> **Fix**: Align on one approach. Recommend keeping SQL's `BIGSERIAL` for simplicity.
>
> See: `docs/database/07-KNOWN-ISSUES.md` for details.

---

**Relationship Diagram:**

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│  training_run   │       │  training_selection │       │     video       │
│─────────────────│       │─────────────────────│       │─────────────────│
│ run_id (PK)     │───┐   │ id (PK)             │   ┌───│ video_id (PK)   │
│ strategy        │   │   │ run_id (FK)         │───┘   │ file_path       │
│ train_fraction  │   └──▶│ video_id (FK)       │       │ label           │
└─────────────────┘       │ target_split        │       └─────────────────┘
                          └─────────────────────┘

One run has MANY selections
One video can be in MANY runs
```

**Common Queries:**

```sql
-- Videos in a specific run
SELECT v.file_path, v.label, ts.target_split
FROM training_selection ts
JOIN video v ON ts.video_id = v.video_id
WHERE ts.run_id = 'abc-123-def'
ORDER BY ts.target_split, v.label;

-- Train/test distribution for a run
SELECT target_split, COUNT(*) as count
FROM training_selection
WHERE run_id = 'abc-123-def'
GROUP BY target_split;

-- Which runs used a specific video?
SELECT tr.run_id, tr.strategy, tr.status
FROM training_selection ts
JOIN training_run tr ON ts.run_id = tr.run_id
WHERE ts.video_id = 'xyz-789-ghi';
```

---

## Lesson 3.3: Audit & History Tables (45 minutes)

### The `promotion_log` Table - Video Lifecycle Changes

**Source**: `001_phase1_schema.sql` lines 81-103

Immutable audit trail of all video split changes:

```sql
CREATE TABLE promotion_log (
    id              BIGSERIAL PRIMARY KEY,
    video_id        UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
    from_split      video_split NOT NULL,
    to_split        video_split NOT NULL,
    label           emotion_label,
    user_id         VARCHAR(255),           -- Who initiated
    correlation_id  UUID,                   -- Groups related operations
    idempotency_key VARCHAR(64) UNIQUE,     -- Prevents duplicates
    dry_run         BOOLEAN DEFAULT FALSE,
    success         BOOLEAN NOT NULL,
    error_message   TEXT,
    promoted_at     TIMESTAMPTZ DEFAULT now()
);
```

**Key Concept: Idempotency**

The `idempotency_key` ensures the same operation can be safely retried:

```sql
-- First call: inserts successfully
INSERT INTO promotion_log (video_id, from_split, to_split, label, idempotency_key)
VALUES ('abc', 'temp', 'dataset_all', 'happy', 'promo-001');

-- Second call with same key: fails silently (unique violation)
-- No duplicate promotion occurs!
```

**Common Queries:**

```sql
-- Promotion history for a video
SELECT from_split, to_split, label, user_id, promoted_at
FROM promotion_log
WHERE video_id = 'abc-123-def'
ORDER BY promoted_at;

-- Who has been labeling today?
SELECT user_id, COUNT(*) as promotions
FROM promotion_log
WHERE promoted_at > now() - INTERVAL '24 hours'
  AND success = TRUE
GROUP BY user_id;

-- Failed promotions (for debugging)
SELECT video_id, from_split, to_split, error_message
FROM promotion_log
WHERE success = FALSE;
```

### The `label_event` Table - Human Labeling Decisions

**Source**: `003_missing_tables.sql` lines 1-30

Detailed tracking of labeling actions:

```sql
CREATE TABLE label_event (
    event_id        BIGSERIAL PRIMARY KEY,
    video_id        UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
    action          VARCHAR(50) NOT NULL,   -- 'label_only', 'promote_train', 'discard'
    label           emotion_label,
    source_split    video_split,
    target_split    video_split,
    user_id         VARCHAR(255),
    session_id      UUID,
    confidence      NUMERIC(5,4),           -- 0.0000 to 1.0000
    notes           TEXT,
    idempotency_key VARCHAR(64) UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

**Action Types:**

| Action | Description |
|--------|-------------|
| `label_only` | Add label without changing split |
| `promote_train` | Label and move to training split |
| `promote_test` | Label and move to test split |
| `discard` | Mark for deletion/purge |
| `relabel` | Change existing label |

---

## Lesson 3.4: User & Event Tables (45 minutes)

### The `user_session` Table - Web UI Sessions

**Source**: `001_phase1_schema.sql` lines 118-133

Tracks user activity in the labeling web interface:

```sql
CREATE TABLE user_session (
    session_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          VARCHAR(255) NOT NULL,
    device_id        VARCHAR(255),
    ip_address       INET,                   -- PostgreSQL IP type
    user_agent       TEXT,
    started_at       TIMESTAMPTZ DEFAULT now(),
    last_activity_at TIMESTAMPTZ DEFAULT now(),
    ended_at         TIMESTAMPTZ,
    actions_count    INTEGER DEFAULT 0,
    metadata         JSONB DEFAULT '{}'
);
```

**Common Queries:**

```sql
-- Active sessions
SELECT user_id, started_at, actions_count
FROM user_session
WHERE ended_at IS NULL
  AND last_activity_at > now() - INTERVAL '30 minutes';

-- User activity stats
SELECT user_id, COUNT(*) as sessions, SUM(actions_count) as total_actions
FROM user_session
GROUP BY user_id
ORDER BY total_actions DESC;
```

### The `generation_request` Table - AI Video Generation

**Source**: `001_phase1_schema.sql` lines 136-152

Tracks synthetic video generation requests (Luma, Runway):

```sql
CREATE TABLE generation_request (
    request_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt        TEXT NOT NULL,            -- "Person smiling"
    emotion       emotion_label NOT NULL,   -- Target emotion
    duration_sec  INTEGER DEFAULT 5,
    provider      VARCHAR(50) NOT NULL,     -- 'luma', 'runway'
    status        VARCHAR(50) DEFAULT 'pending',
    video_id      UUID REFERENCES video(video_id),  -- Result, if any
    api_response  JSONB,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    completed_at  TIMESTAMPTZ
);
```

### The `emotion_event` Table - Real-time Detections

**Source**: `001_phase1_schema.sql` lines 155-175

High-volume streaming data from Jetson edge devices:

```sql
CREATE TABLE emotion_event (
    event_id      BIGSERIAL PRIMARY KEY,
    device_id     VARCHAR(255) NOT NULL,
    emotion       emotion_label NOT NULL,
    confidence    NUMERIC(5,4) NOT NULL,    -- 0.0000 to 1.0000
    inference_ms  NUMERIC(8,2),             -- Inference time
    frame_number  BIGINT,
    timestamp     TIMESTAMPTZ NOT NULL,
    metadata      JSONB
);

-- Constraint: valid confidence
CHECK (confidence >= 0 AND confidence <= 1)
```

**Important**: This table grows FAST. Consider:
- Partitioning by month
- Archival policy
- Aggregation views

**Common Queries:**

```sql
-- Recent detections
SELECT emotion, confidence, timestamp
FROM emotion_event
WHERE timestamp > now() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 100;

-- Emotion distribution over time
SELECT
    date_trunc('hour', timestamp) as hour,
    emotion,
    COUNT(*) as count
FROM emotion_event
WHERE timestamp > now() - INTERVAL '24 hours'
GROUP BY hour, emotion
ORDER BY hour;

-- Average confidence by emotion
SELECT emotion, ROUND(AVG(confidence)::NUMERIC, 4) as avg_confidence
FROM emotion_event
GROUP BY emotion;
```

---

## Lesson 3.5: Operations Tables (45 minutes)

### The `deployment_log` Table - Model Deployments

**Source**: `003_missing_tables.sql` lines 32-75

Tracks TensorRT model deployments to Jetson:

```sql
CREATE TABLE deployment_log (
    deployment_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID REFERENCES training_run(run_id),
    device_id       VARCHAR(255) NOT NULL,
    engine_path     VARCHAR(500) NOT NULL,
    deploy_stage    VARCHAR(50) NOT NULL DEFAULT 'shadow',

    -- Gate B Performance Metrics
    fps_measured    NUMERIC(10,2),
    latency_p50_ms  NUMERIC(10,2),
    latency_p95_ms  NUMERIC(10,2),
    gpu_memory_gb   NUMERIC(5,2),
    gate_b_passed   BOOLEAN,

    status          VARCHAR(50) DEFAULT 'pending',
    deployed_by     VARCHAR(255),
    deployed_at     TIMESTAMPTZ DEFAULT now(),
    rolled_back_at  TIMESTAMPTZ,
    notes           TEXT
);
```

**Deployment Stages:**

```
shadow ───▶ canary ───▶ rollout
(testing)   (limited)   (production)
```

**Gate B Requirements:**
- FPS ≥ 25
- P50 latency ≤ 120ms
- P95 latency ≤ 250ms
- GPU memory ≤ 2.5GB

### The `audit_log` Table - Privacy Compliance

**Source**: `003_missing_tables.sql` lines 77-105

GDPR audit trail for data access and deletion:

```sql
CREATE TABLE audit_log (
    audit_id     BIGSERIAL PRIMARY KEY,
    action       VARCHAR(50) NOT NULL,      -- 'purge', 'access', 'export'
    resource     VARCHAR(100) NOT NULL,     -- 'video', 'user_session'
    resource_id  VARCHAR(255),
    user_id      VARCHAR(255),
    ip_address   VARCHAR(45),
    reason       TEXT,
    details      JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);
```

**Action Types:**

| Action | Description |
|--------|-------------|
| `purge` | Data deleted (right to be forgotten) |
| `access` | Data accessed (subject access request) |
| `export` | Data exported |
| `delete` | Logical deletion |
| `anonymize` | Personal data removed |

### The `obs_samples` Table - System Metrics

**Source**: `003_missing_tables.sql` lines 107-130

Time-series metrics for system monitoring:

```sql
CREATE TABLE obs_samples (
    id      BIGSERIAL PRIMARY KEY,
    ts      TIMESTAMPTZ NOT NULL,
    src     VARCHAR(100),           -- 'n8n', 'jetson', 'gateway'
    metric  VARCHAR(100),           -- 'gpu_temp', 'request_latency'
    value   NUMERIC(15,4),
    labels  JSONB                   -- Additional tags
);
```

**Example Data:**

| ts | src | metric | value | labels |
|----|-----|--------|-------|--------|
| 2025-01-05 14:30:00 | jetson | gpu_temp_c | 67.2 | `{"device": "reachy-mini"}` |
| 2025-01-05 14:30:01 | gateway | request_latency_ms | 45.3 | `{"endpoint": "/videos"}` |

### The `reconcile_report` Table - Consistency Checks

**Source**: `003_missing_tables.sql` lines 132-160

Results of filesystem/database reconciliation:

```sql
CREATE TABLE reconcile_report (
    report_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_at          TIMESTAMPTZ DEFAULT now(),
    root_path       VARCHAR(500) NOT NULL,

    -- Counts
    files_scanned   INTEGER,
    db_records      INTEGER,
    orphan_files    INTEGER,       -- On disk but not in DB
    missing_files   INTEGER,       -- In DB but not on disk
    mismatches      INTEGER,       -- Hash/size doesn't match

    -- Details
    orphan_list     JSONB,
    missing_list    JSONB,
    mismatch_list   JSONB,

    status          VARCHAR(50),
    error_message   TEXT
);
```

---

## Lesson 3.6: Complete Relationship Diagram (30 minutes)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              REACHY DATABASE RELATIONSHIPS                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│                              ┌─────────────────┐                                    │
│                              │  training_run   │                                    │
│                              │─────────────────│                                    │
│                              │ run_id (PK)     │◀─────────────────┐                │
│                              │ strategy        │                  │                │
│                              │ metrics         │                  │                │
│                              └────────┬────────┘                  │                │
│                                       │                           │                │
│                                       │ 1:M                       │                │
│                                       ▼                           │                │
│ ┌─────────────────┐         ┌─────────────────────┐      ┌─────────────────┐       │
│ │ promotion_log   │         │ training_selection  │      │ deployment_log  │       │
│ │─────────────────│         │─────────────────────│      │─────────────────│       │
│ │ video_id (FK)───│────┐    │ run_id (FK)         │      │ run_id (FK)─────│───────┘
│ │ from_split      │    │    │ video_id (FK)───────│──┐   │ device_id       │
│ │ to_split        │    │    │ target_split        │  │   │ gate_b_passed   │
│ └─────────────────┘    │    └─────────────────────┘  │   └─────────────────┘
│                        │                             │
│ ┌─────────────────┐    │    ┌─────────────────┐     │
│ │  label_event    │    │    │     video       │◀────┘
│ │─────────────────│    └───▶│─────────────────│
│ │ video_id (FK)───│────────▶│ video_id (PK)   │◀────┐
│ │ action          │         │ file_path       │     │
│ │ label           │         │ split           │     │
│ └─────────────────┘         │ label           │     │
│                             └────────┬────────┘     │
│                                      │              │
│                                      │ 1:1         │
│                                      ▼              │
│                             ┌─────────────────┐     │
│                             │generation_request│    │
│                             │─────────────────│     │
│                             │ video_id (FK)───│─────┘
│                             │ prompt          │
│                             │ provider        │
│                             └─────────────────┘
│                                                                                      │
│   STANDALONE TABLES (no FKs):                                                       │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│   │  user_session   │  │  emotion_event  │  │   audit_log     │  │   obs_samples   ││
│   │─────────────────│  │─────────────────│  │─────────────────│  │─────────────────││
│   │ session_id      │  │ event_id        │  │ audit_id        │  │ id              ││
│   │ user_id         │  │ device_id       │  │ action          │  │ ts              ││
│   │ ip_address      │  │ emotion         │  │ resource_id     │  │ metric          ││
│   └─────────────────┘  │ confidence      │  └─────────────────┘  │ value           ││
│                        └─────────────────┘                       └─────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Check

1. Which table stores the actual video file contents?

2. What is the purpose of the `idempotency_key` in `promotion_log`?

3. If you need to find all videos labeled "happy" that were used in training, which tables do you query?

4. What happens to `training_selection` records when a `training_run` is deleted?

5. Which table would you query to check if the Jetson is meeting performance requirements?

<details>
<summary>Click to see answers</summary>

1. **None!** The database stores metadata only. Video files are on the filesystem.

2. To prevent duplicate promotions. If the same idempotency_key is used twice, the second insert fails silently.

3. `video` and `training_selection`. Join them to find videos with label='happy' that appear in training_selection.

4. They are deleted automatically due to `ON DELETE CASCADE` on the foreign key.

5. `deployment_log` - check the `fps_measured`, `latency_p50_ms`, `latency_p95_ms`, and `gate_b_passed` columns.

</details>

---

## Hands-On Exercise 3

### Setup: Load Sample Data

```sql
-- Insert test videos
INSERT INTO video (file_path, split, label, size_bytes, duration_sec) VALUES
    ('videos/dataset/happy_001.mp4', 'dataset_all', 'happy', 1024000, 5.0),
    ('videos/dataset/happy_002.mp4', 'dataset_all', 'happy', 1048576, 6.2),
    ('videos/dataset/sad_001.mp4', 'dataset_all', 'sad', 2097152, 4.5),
    ('videos/dataset/sad_002.mp4', 'dataset_all', 'sad', 1500000, 5.8),
    ('videos/temp/unlabeled_001.mp4', 'temp', NULL, 500000, 3.0);

-- Create a training run
INSERT INTO training_run (strategy, train_fraction, test_fraction, seed, status)
VALUES ('balanced_random', 0.70, 0.30, 42, 'completed')
RETURNING run_id;
-- Note the returned run_id

-- Link videos to run (replace 'RUN_ID' with actual UUID)
INSERT INTO training_selection (run_id, video_id, target_split)
SELECT 'RUN_ID', video_id,
       CASE WHEN random() < 0.7 THEN 'train' ELSE 'test' END
FROM video
WHERE split = 'dataset_all';
```

### Tasks

1. **Count videos by split and label:**
```sql
SELECT split, label, COUNT(*)
FROM video
GROUP BY split, label
ORDER BY split, label;
```

2. **Find the largest video:**
```sql
SELECT file_path, size_bytes,
       pg_size_pretty(size_bytes::BIGINT) as human_size
FROM video
ORDER BY size_bytes DESC
LIMIT 1;
```

3. **Calculate total training corpus size:**
```sql
SELECT
    COUNT(*) as video_count,
    SUM(size_bytes) as total_bytes,
    pg_size_pretty(SUM(size_bytes)::BIGINT) as total_size
FROM video
WHERE split = 'dataset_all';
```

4. **List videos in your training run with their labels:**
```sql
SELECT v.file_path, v.label, ts.target_split
FROM training_selection ts
JOIN video v ON ts.video_id = v.video_id
WHERE ts.run_id = 'RUN_ID';
```

5. **Check train/test distribution:**
```sql
SELECT target_split, COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM training_selection
WHERE run_id = 'RUN_ID'
GROUP BY target_split;
```

---

## Summary

In this module, you learned:

- ✅ The purpose of all 12 tables in the Reachy database
- ✅ The video lifecycle: temp → dataset_all → train/test → purged
- ✅ How tables relate through foreign keys
- ✅ Which table to query for different use cases
- ✅ How to write complex queries across multiple tables

**Next**: [Module 4: Stored Procedures & Business Logic](./04-MODULE-STORED-PROCEDURES.md)
