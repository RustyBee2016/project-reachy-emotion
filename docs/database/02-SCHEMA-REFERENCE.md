# Database Schema Reference

This document provides a complete reference for all tables, columns, and constraints in the Reachy Emotion Detection database.

**Source File**: `alembic/versions/001_phase1_schema.sql` (lines 1-193)

## Custom Types (ENUMs)

### video_split

Defines the lifecycle stage of a video clip.

```sql
CREATE TYPE video_split AS ENUM (
    'temp',        -- Incoming videos from Jetson (unlabeled)
    'dataset_all', -- Labeled, curated corpus
    'train',       -- Selected for training
    'test',        -- Selected for testing
    'purged'       -- Deleted for privacy compliance
);
```

**Source**: `alembic/versions/001_phase1_schema.sql:13`

### emotion_label

The set of emotions that can be detected.

```sql
CREATE TYPE emotion_label AS ENUM (
    'neutral',
    'happy',
    'sad',
    'angry',
    'surprise',
    'fearful'
);
```

**Source**: `alembic/versions/001_phase1_schema.sql:19`

### training_status

Tracks the state of a training run.

```sql
CREATE TYPE training_status AS ENUM (
    'pending',     -- Waiting to start
    'sampling',    -- Selecting train/test videos
    'training',    -- TAO training in progress
    'evaluating',  -- Running validation
    'completed',   -- Success
    'failed',      -- Error occurred
    'cancelled'    -- User cancelled
);
```

**Source**: `alembic/versions/001_phase1_schema.sql:27`

---

## Core Tables (Phase 1)

### video

**Purpose**: Central registry of all video clips and their metadata.

**Source**: `alembic/versions/001_phase1_schema.sql:31-46`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `video_id` | `UUID` | `PRIMARY KEY`, `DEFAULT uuid_generate_v4()` | Unique identifier |
| `file_path` | `VARCHAR(500)` | `NOT NULL` | Relative path (e.g., `videos/temp/abc.mp4`) |
| `split` | `video_split` | `NOT NULL`, `DEFAULT 'temp'` | Current lifecycle stage |
| `label` | `emotion_label` | `NULLABLE` | Emotion classification |
| `sha256` | `CHAR(64)` | `NULLABLE` | File content hash |
| `duration_sec` | `NUMERIC(10,2)` | `NULLABLE` | Video length in seconds |
| `width` | `INTEGER` | `NULLABLE` | Video width in pixels |
| `height` | `INTEGER` | `NULLABLE` | Video height in pixels |
| `fps` | `NUMERIC(5,2)` | `NULLABLE` | Frames per second |
| `size_bytes` | `BIGINT` | `NULLABLE` | File size |
| `metadata` | `JSONB` | `DEFAULT '{}'` | Flexible additional data |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When added |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Last modification |
| `deleted_at` | `TIMESTAMPTZ` | `NULLABLE` | Soft delete timestamp |

**Indexes**:
```sql
CREATE INDEX idx_video_split ON video(split);
CREATE INDEX idx_video_label ON video(label);
CREATE INDEX idx_video_created ON video(created_at DESC);
CREATE INDEX idx_video_sha256 ON video(sha256);
CREATE UNIQUE INDEX uq_video_sha256_size ON video(sha256, size_bytes);
```

**Business Rule Constraint**:
```sql
-- NOTE: This constraint exists in Python models but is MISSING from SQL schema
-- Videos in 'temp', 'test', or 'purged' MUST NOT have labels
-- Videos in 'dataset_all' or 'train' MUST have labels
CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
)
```

**Triggers**:
- `trg_video_updated`: Auto-updates `updated_at` on any change

---

### training_run

**Purpose**: Tracks each model training attempt with configuration and results.

**Source**: `alembic/versions/001_phase1_schema.sql:56-80`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `run_id` | `UUID` | `PRIMARY KEY`, `DEFAULT uuid_generate_v4()` | Unique identifier |
| `strategy` | `VARCHAR(100)` | `NOT NULL` | Sampling strategy name |
| `train_fraction` | `NUMERIC(3,2)` | `NOT NULL`, `DEFAULT 0.7` | Training data percentage |
| `test_fraction` | `NUMERIC(3,2)` | `NOT NULL`, `DEFAULT 0.3` | Test data percentage |
| `seed` | `BIGINT` | `NULLABLE` | Random seed for reproducibility |
| `dataset_hash` | `CHAR(64)` | `NULLABLE` | SHA256 of all videos used |
| `status` | `training_status` | `DEFAULT 'pending'` | Current state |
| `mlflow_run_id` | `VARCHAR(255)` | `NULLABLE` | MLflow experiment link |
| `model_path` | `VARCHAR(500)` | `NULLABLE` | Path to trained .tlt model |
| `engine_path` | `VARCHAR(500)` | `NULLABLE` | Path to TensorRT .engine |
| `metrics` | `JSONB` | `DEFAULT '{}'` | F1, accuracy, precision, recall |
| `config` | `JSONB` | `DEFAULT '{}'` | Full training hyperparameters |
| `error_message` | `TEXT` | `NULLABLE` | Failure reason |
| `started_at` | `TIMESTAMPTZ` | `NULLABLE` | When training began |
| `completed_at` | `TIMESTAMPTZ` | `NULLABLE` | When training finished |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Row creation time |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Last modification |

**Constraints**:
```sql
CHECK (train_fraction >= 0 AND train_fraction <= 1)
CHECK (test_fraction >= 0 AND test_fraction <= 1)
CHECK (train_fraction + test_fraction <= 1.0)
```

**Triggers**:
- `trg_training_run_updated`: Auto-updates `updated_at` on change

---

### training_selection

**Purpose**: Many-to-many relationship linking videos to training runs.

**Source**: `alembic/versions/001_phase1_schema.sql:89-101`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `run_id` | `UUID` | `NOT NULL`, `FK → training_run` | Training run reference |
| `video_id` | `UUID` | `NOT NULL`, `FK → video` | Video reference |
| `target_split` | `video_split` | `NOT NULL` | 'train' or 'test' |
| `selected_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When selected |

**Indexes**:
```sql
CREATE INDEX idx_ts_run_id ON training_selection(run_id);
CREATE INDEX idx_ts_video_id ON training_selection(video_id);
CREATE UNIQUE INDEX uq_ts_run_video_split ON training_selection(run_id, video_id, target_split);
```

---

### promotion_log

**Purpose**: Append-only audit trail for all video split changes.

**Source**: `alembic/versions/001_phase1_schema.sql:104-118`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `video_id` | `UUID` | `NOT NULL` | Which video was promoted |
| `from_split` | `video_split` | `NOT NULL` | Source split |
| `to_split` | `video_split` | `NOT NULL` | Destination split |
| `label` | `emotion_label` | `NULLABLE` | Label assigned |
| `user_id` | `VARCHAR(255)` | `NULLABLE` | Who initiated promotion |
| `correlation_id` | `UUID` | `NULLABLE` | Groups related operations |
| `idempotency_key` | `VARCHAR(64)` | `UNIQUE` | Prevents duplicate processing |
| `dry_run` | `BOOLEAN` | `DEFAULT FALSE` | Was this a test run? |
| `success` | `BOOLEAN` | `DEFAULT TRUE` | Did it succeed? |
| `error_message` | `TEXT` | `NULLABLE` | Failure reason |
| `promoted_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When it happened |

**Indexes**:
```sql
CREATE INDEX idx_pl_video_id ON promotion_log(video_id);
CREATE INDEX idx_pl_promoted_at ON promotion_log(promoted_at DESC);
CREATE INDEX idx_pl_correlation ON promotion_log(correlation_id);
```

---

### user_session

**Purpose**: Tracks web UI user sessions for analytics.

**Source**: `alembic/versions/001_phase1_schema.sql:118-135`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | `UUID` | `PRIMARY KEY` | Unique session ID |
| `user_id` | `VARCHAR(255)` | `NOT NULL` | User identifier |
| `device_id` | `VARCHAR(255)` | `NULLABLE` | Browser/device fingerprint |
| `ip_address` | `INET` | `NULLABLE` | User's IP address |
| `user_agent` | `TEXT` | `NULLABLE` | Browser info |
| `started_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Session start |
| `last_activity_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Last interaction |
| `ended_at` | `TIMESTAMPTZ` | `NULLABLE` | Session end |
| `actions_count` | `INTEGER` | `DEFAULT 0` | Actions in session |
| `metadata` | `JSONB` | `DEFAULT '{}'` | Additional data |

---

### generation_request

**Purpose**: Tracks AI-generated synthetic video requests (Luma, Runway).

**Source**: `alembic/versions/001_phase1_schema.sql:136-154`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `request_id` | `UUID` | `PRIMARY KEY` | Unique request ID |
| `prompt` | `TEXT` | `NOT NULL` | Generation prompt |
| `emotion` | `emotion_label` | `NOT NULL` | Target emotion |
| `duration_sec` | `INTEGER` | `NULLABLE` | Requested length |
| `provider` | `VARCHAR(50)` | `NOT NULL` | luma/runway/midjourney |
| `status` | `VARCHAR(50)` | `DEFAULT 'pending'` | Current state |
| `video_id` | `UUID` | `NULLABLE`, `FK → video` | Resulting video |
| `api_response` | `JSONB` | `DEFAULT '{}'` | Full API response |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Request time |
| `completed_at` | `TIMESTAMPTZ` | `NULLABLE` | Completion time |
| `error_message` | `TEXT` | `NULLABLE` | Failure reason |

---

### emotion_event

**Purpose**: Real-time emotion detections from Jetson edge devices (streaming telemetry).

**Source**: `alembic/versions/001_phase1_schema.sql:155-170`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `event_id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `device_id` | `VARCHAR(255)` | `NOT NULL` | Which Jetson device |
| `emotion` | `emotion_label` | `NOT NULL` | Detected emotion |
| `confidence` | `NUMERIC(5,4)` | `NOT NULL` | 0.0-1.0 confidence |
| `inference_ms` | `NUMERIC(8,2)` | `NULLABLE` | Inference latency |
| `frame_number` | `BIGINT` | `NULLABLE` | Video frame number |
| `timestamp` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | Detection time |
| `metadata` | `JSONB` | `DEFAULT '{}'` | Additional data |

**Constraints**:
```sql
CHECK (confidence >= 0 AND confidence <= 1)
```

**Indexes**:
```sql
CREATE INDEX idx_ee_device ON emotion_event(device_id);
CREATE INDEX idx_ee_timestamp ON emotion_event(timestamp DESC);
CREATE INDEX idx_ee_emotion ON emotion_event(emotion);
```

**Performance Note**: This table will grow very large (millions of rows). Consider monthly partitioning for production.

---

## Agent Support Tables (Phase 3)

**Source**: `alembic/versions/003_missing_tables.sql`

### label_event

**Purpose**: Detailed audit trail for all labeling actions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `video_id` | `UUID` | `NOT NULL`, `FK → video` | Which video |
| `action` | `VARCHAR(50)` | `NOT NULL` | label_only/promote_train/promote_test/discard/relabel |
| `label` | `emotion_label` | `NULLABLE` | Assigned label |
| `user_id` | `VARCHAR(255)` | `NOT NULL` | Who performed action |
| `correlation_id` | `UUID` | `NULLABLE` | Groups related operations |
| `idempotency_key` | `VARCHAR(64)` | `UNIQUE` | Prevents duplicates |
| `confidence` | `NUMERIC(5,4)` | `NULLABLE` | Labeler confidence |
| `notes` | `TEXT` | `NULLABLE` | Labeler notes |
| `dry_run` | `BOOLEAN` | `DEFAULT FALSE` | Was this a test? |
| `success` | `BOOLEAN` | `DEFAULT TRUE` | Did it succeed? |
| `error_message` | `TEXT` | `NULLABLE` | Failure reason |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When it happened |

---

### deployment_log

**Purpose**: Tracks TensorRT model deployments to Jetson devices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `run_id` | `UUID` | `NOT NULL`, `FK → training_run` | Source training run |
| `device_id` | `VARCHAR(255)` | `NOT NULL` | Target Jetson device |
| `engine_path` | `VARCHAR(500)` | `NOT NULL` | TensorRT engine path |
| `stage` | `VARCHAR(50)` | `NOT NULL` | shadow/canary/rollout |
| `fps_measured` | `NUMERIC(6,2)` | `NULLABLE` | Frames per second |
| `latency_p50_ms` | `NUMERIC(8,2)` | `NULLABLE` | 50th percentile latency |
| `latency_p95_ms` | `NUMERIC(8,2)` | `NULLABLE` | 95th percentile latency |
| `gpu_memory_gb` | `NUMERIC(4,2)` | `NULLABLE` | GPU memory usage |
| `gate_b_passed` | `BOOLEAN` | `NULLABLE` | Performance gate passed? |
| `deployed_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When deployed |
| `promoted_at` | `TIMESTAMPTZ` | `NULLABLE` | When promoted to next stage |
| `rolled_back_at` | `TIMESTAMPTZ` | `NULLABLE` | When rolled back |
| `error_message` | `TEXT` | `NULLABLE` | Failure reason |

**Gate B Requirements** (performance thresholds):
- FPS ≥ 25
- P50 Latency ≤ 120ms
- P95 Latency ≤ 250ms
- GPU Memory ≤ 2.5GB

---

### audit_log

**Purpose**: Privacy/GDPR compliance audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `action` | `VARCHAR(50)` | `NOT NULL` | purge/access/export/delete/anonymize |
| `entity_type` | `VARCHAR(50)` | `NOT NULL` | video/user_session/emotion_event |
| `entity_id` | `VARCHAR(255)` | `NOT NULL` | ID of affected entity |
| `user_id` | `VARCHAR(255)` | `NOT NULL` | Who performed action |
| `ip_address` | `INET` | `NULLABLE` | Request IP |
| `reason` | `TEXT` | `NULLABLE` | Why action was taken |
| `metadata` | `JSONB` | `DEFAULT '{}'` | Additional context |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When it happened |

---

### obs_samples

**Purpose**: Time-series observability metrics from all system components.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `ts` | `TIMESTAMPTZ` | `NOT NULL` | Metric timestamp |
| `src` | `VARCHAR(100)` | `NOT NULL` | Source (n8n/media_mover/gateway/jetson) |
| `metric` | `VARCHAR(100)` | `NOT NULL` | Metric name |
| `value` | `NUMERIC(15,4)` | `NOT NULL` | Metric value |
| `labels` | `JSONB` | `DEFAULT '{}'` | Additional tags |

**Example Data**:
```
ts                  | src     | metric          | value | labels
2025-01-05 14:30:00 | jetson  | gpu_temp_c      | 67.2  | {"device": "reachy-mini"}
2025-01-05 14:30:01 | gateway | request_latency | 45.3  | {"endpoint": "/videos"}
```

---

### reconcile_report

**Purpose**: Results of filesystem/database consistency checks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `BIGSERIAL` | `PRIMARY KEY` | Auto-incrementing ID |
| `run_at` | `TIMESTAMPTZ` | `DEFAULT CURRENT_TIMESTAMP` | When check ran |
| `orphan_count` | `INTEGER` | `NOT NULL` | Files on disk not in DB |
| `missing_count` | `INTEGER` | `NOT NULL` | DB rows without files |
| `mismatch_count` | `INTEGER` | `NOT NULL` | Size/hash mismatches |
| `orphan_paths` | `JSONB` | `DEFAULT '[]'` | List of orphan file paths |
| `missing_ids` | `JSONB` | `DEFAULT '[]'` | List of missing video IDs |
| `mismatch_details` | `JSONB` | `DEFAULT '[]'` | Mismatch information |
| `auto_fixed` | `INTEGER` | `DEFAULT 0` | How many auto-repaired |
| `duration_sec` | `NUMERIC(10,2)` | `NULLABLE` | How long check took |

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE ENTITIES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                    ┌──────────────────┐               │
│  │    video     │◄──────────────────┤ training_selection│               │
│  ├──────────────┤     1:N            ├──────────────────┤               │
│  │ video_id (PK)│                    │ run_id (FK)      │───────┐       │
│  │ file_path    │                    │ video_id (FK)    │       │       │
│  │ split        │                    │ target_split     │       │       │
│  │ label        │                    └──────────────────┘       │       │
│  └──────────────┘                                               │       │
│         │                                                       ▼       │
│         │ 1:N                                          ┌────────────────┐
│         │                                              │ training_run   │
│         ▼                                              ├────────────────┤
│  ┌──────────────┐                                      │ run_id (PK)    │
│  │promotion_log │                                      │ strategy       │
│  ├──────────────┤                                      │ status         │
│  │ video_id (FK)│                                      │ metrics (JSON) │
│  │ from_split   │                                      └────────────────┘
│  │ to_split     │                                              │
│  │ label        │                                              │ 1:N
│  └──────────────┘                                              ▼
│         │                                              ┌────────────────┐
│         │ 1:N                                          │ deployment_log │
│         ▼                                              ├────────────────┤
│  ┌──────────────┐                                      │ run_id (FK)    │
│  │ label_event  │                                      │ device_id      │
│  ├──────────────┤                                      │ stage          │
│  │ video_id (FK)│                                      └────────────────┘
│  │ action       │
│  │ user_id      │
│  └──────────────┘
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                         STANDALONE ENTITIES                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ user_session │  │emotion_event │  │  audit_log   │  │ obs_samples  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐                             │
│  │generation_request│  │reconcile_report  │                             │
│  └──────────────────┘  └──────────────────┘                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Index Summary

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| video | idx_video_split | split | Filter by lifecycle stage |
| video | idx_video_label | label | Filter by emotion |
| video | idx_video_created | created_at DESC | Time-based queries |
| video | uq_video_sha256_size | sha256, size_bytes | Deduplication |
| training_selection | idx_ts_run_id | run_id | Find videos in a run |
| training_selection | idx_ts_video_id | video_id | Find runs using a video |
| promotion_log | idx_pl_video_id | video_id | Video audit history |
| promotion_log | idx_pl_promoted_at | promoted_at DESC | Recent promotions |
| emotion_event | idx_ee_timestamp | timestamp DESC | Time-series queries |
| emotion_event | idx_ee_device | device_id | Per-device filtering |

## Next Steps

- See [03-STORED-PROCEDURES.md](03-STORED-PROCEDURES.md) for business logic functions
- See [04-PYTHON-ORM-MODELS.md](04-PYTHON-ORM-MODELS.md) for SQLAlchemy models
