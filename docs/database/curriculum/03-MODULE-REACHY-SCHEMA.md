# Module 3: Reachy Schema Deep Dive

**Duration**: 4 hours
**Prerequisites**: Modules 1-2
**Goal**: Master the 9 ORM-managed tables in the Reachy database and understand their relationships

---

## Learning Objectives

By the end of this module, you will be able to:

1. Explain the purpose of each ORM-managed table in the database
2. Understand the video lifecycle from capture to training
3. Navigate relationships between tables using foreign keys
4. Write queries to answer business questions
5. Identify which table to use for each use case
6. Explain how the three source-of-truth files work together to define the schema

---

## Lesson 3.1: The Big Picture (45 minutes)

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

The database has **9 ORM-managed tables** organized into four functional groups.
These are the tables that the Python application creates, reads, and writes through
SQLAlchemy. Each one has a corresponding Python class in `models.py`.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   9 ORM-MANAGED REACHY TABLES                        │
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
│   OPERATIONS (4 tables)                                             │
│   ├── deployment_log     - Model deployments to Jetson              │
│   ├── audit_log          - GDPR/privacy compliance                  │
│   ├── obs_samples        - System metrics time-series               │
│   └── reconcile_report   - Filesystem/DB consistency                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

> **What about `user_session`, `generation_request`, and `emotion_event`?**
>
> These three tables exist in the legacy SQL files (`001_phase1_schema.sql`) but
> are **not** represented in the current SQLAlchemy models. They were designed for
> future features (web UI sessions, AI video generation, real-time Jetson streaming)
> that have not yet been implemented. If those features are built later, new ORM
> models and Alembic migrations will be created for them. For now, ignore them —
> they are not part of the active schema.

### Source of Truth: Three Files That Define the Schema

Understanding **where** the schema is defined is just as important as understanding
the tables themselves. The Reachy project uses three files that work together:

| File | Path | Role |
| ---- | ---- | ---- |
| **`models.py`** | `apps/api/app/db/models.py` | Defines the 9 Python classes that map to database tables. This is the **primary** source of truth — every column, constraint, index, and relationship is declared here. When you need to know what a table looks like, read this file first. |
| **`enums.py`** | `apps/api/app/db/enums.py` | Defines the three shared enum types (`SplitEnum`, `EmotionEnum`, `SelectionTargetEnum`) used across multiple tables. These are implemented as **CHECK constraints** (not native PostgreSQL ENUMs) for cross-database compatibility. |
| **`202510280000_initial_schema.py`** | `apps/api/app/db/alembic/versions/` | The Alembic migration that **creates** the tables in PostgreSQL. It translates the Python model definitions into actual `CREATE TABLE` DDL. When you run `alembic upgrade head`, this file executes. |

**How they work together:**

```
┌──────────────┐     imports      ┌──────────────┐
│  enums.py    │◀────────────────│  models.py   │
│              │                  │              │
│  SplitEnum   │                  │  Video       │
│  EmotionEnum │                  │  TrainingRun │
│  Selection   │                  │  ...7 more   │
│  TargetEnum  │                  │              │
└──────────────┘                  └──────┬───────┘
                                         │
                                         │ Alembic reads models.py
                                         │ to auto-generate migrations
                                         ▼
                              ┌────────────────────┐
                              │  202510280000_     │
                              │  initial_schema.py │
                              │                    │
                              │  upgrade():        │
                              │    CREATE TABLE... │
                              │    CREATE INDEX... │
                              │                    │
                              │  downgrade():      │
                              │    DROP TABLE...   │
                              └────────────────────┘
                                         │
                                         │ alembic upgrade head
                                         ▼
                              ┌────────────────────┐
                              │   PostgreSQL DB     │
                              │   (actual tables)   │
                              └────────────────────┘
```

**Why this matters for you as an implementer:**

- **To understand a table's structure** → read `models.py`
- **To understand allowed enum values** → read `enums.py`
- **To see exactly what SQL runs against the database** → read the Alembic migration
- **To add a new column or table** → modify `models.py` first, then generate a new Alembic migration

> ⚠️ **Important**: The legacy SQL files in `alembic/versions/` (`001_phase1_schema.sql`,
> `002_stored_procedures.sql`, `003_missing_tables.sql`) are **deprecated**. They were
> the original hand-written schema but have been superseded by the SQLAlchemy + Alembic
> approach. Do not use them to create or modify the database. They remain in the repo
> for historical reference only.

---

## Lesson 3.2: Core Data Tables (1 hour)

### The `video` Table - Central Registry

**Source**: `models.py` → class `Video` (lines 34-85)

This is the most important table. Every video clip has one row here.

The Python model defines the table like this:

```python
class Video(TimestampMixin, Base):
    __tablename__ = "video"

    video_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    split: Mapped[str] = mapped_column(SplitEnum, nullable=False, default="temp")
    label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

Which translates to this SQL when the Alembic migration runs:

```sql
CREATE TABLE video (
    video_id     VARCHAR(36) PRIMARY KEY,       -- UUID stored as string for portability
    file_path    VARCHAR(1024) NOT NULL,
    split        VARCHAR(10) NOT NULL DEFAULT 'temp',  -- CHECK constraint, not native ENUM
    label        VARCHAR(10),                          -- CHECK constraint, not native ENUM
    duration_sec FLOAT,
    fps          FLOAT,
    width        INTEGER,
    height       INTEGER,
    size_bytes   BIGINT NOT NULL,
    sha256       VARCHAR(64) NOT NULL,
    metadata     JSON,                          -- Note: column name is "metadata" in DB
    deleted_at   TIMESTAMPTZ,                   -- Soft deletes (GDPR)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),   -- From TimestampMixin
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()    -- From TimestampMixin
);
```

**Column Breakdown:**

| Column         | Python Type       | DB Type        | Purpose                   | Example                        |
| -------------- | ----------------- | -------------- | ------------------------- | ------------------------------ |
| `video_id`     | `String(36)`      | VARCHAR(36)    | UUID as string            | `"550e8400-e29b-41d4..."`      |
| `file_path`    | `String(1024)`    | VARCHAR(1024)  | Path to MP4 on disk       | `"videos/temp/001.mp4"`        |
| `split`        | `SplitEnum`       | VARCHAR + CHECK | Lifecycle stage          | `"temp"`, `"train"`, `"test"`  |
| `label`        | `EmotionEnum`     | VARCHAR + CHECK | Emotion classification   | `"happy"`, `"sad"`, `"neutral"`|
| `duration_sec` | `Float`           | FLOAT          | Video length in seconds   | `5.25`                         |
| `fps`          | `Float`           | FLOAT          | Frames per second         | `29.97`                        |
| `width`        | `int` (nullable)  | INTEGER        | Video width in pixels     | `1920`                         |
| `height`       | `int` (nullable)  | INTEGER        | Video height in pixels    | `1080`                         |
| `size_bytes`   | `BigInteger`      | BIGINT         | File size (required)      | `1024000`                      |
| `sha256`       | `String(64)`      | VARCHAR(64)    | File hash (required)      | `"a1b2c3d4..."`                |
| `extra_data`   | `JSON`            | JSON           | Flexible extra data       | `{"source": "jetson"}`         |
| `deleted_at`   | `DateTime(tz)`    | TIMESTAMPTZ    | Soft delete marker        | `NULL` or timestamp            |
| `created_at`   | via `TimestampMixin` | TIMESTAMPTZ | When row was created      | Auto-set by DB                 |
| `updated_at`   | via `TimestampMixin` | TIMESTAMPTZ | When row was last changed | Auto-updated by SQLAlchemy     |

> **Design decisions to understand:**
>
> - **`String(36)` for UUIDs** instead of PostgreSQL's native `UUID` type. This makes
>   the schema portable across databases (SQLite for testing, PostgreSQL for production).
> - **`SplitEnum` and `EmotionEnum` are CHECK constraints**, not native PostgreSQL ENUMs.
>   See `enums.py` — each enum is created with `native_enum=False, create_constraint=True`.
>   This means the DB column is a plain `VARCHAR` with a `CHECK` constraint that limits
>   the allowed values. This avoids the complexity of `ALTER TYPE` when adding new values.
> - **`extra_data` maps to a DB column named `"metadata"`**. The Python attribute is called
>   `extra_data` to avoid shadowing SQLAlchemy's internal `.metadata` attribute, but the
>   actual database column name is `metadata`.
> - **`TimestampMixin`** (from `base.py`) automatically adds `created_at` and `updated_at`
>   columns with `server_default=func.now()`. The `updated_at` column also has
>   `onupdate=func.now()` so SQLAlchemy refreshes it on every UPDATE.

**Key Constraints (from `models.py` `__table_args__`):**

```python
# Unique file: same hash + size = same file (deduplication)
UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size")

# Business rule: label is required for dataset_all/train, forbidden for temp/test/purged
CheckConstraint(
    """
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
    """,
    name="chk_video_split_label_policy",
)

# Indexes for fast lookups
Index("ix_video_split", "split")
Index("ix_video_label", "label")
```

The `chk_video_split_label_policy` constraint is a critical business rule. It ensures
that videos in `temp`, `test`, or `purged` splits **cannot** have a label, while videos
in `dataset_all` or `train` **must** have one. In the current runtime workflow, labeled
videos are promoted directly from `temp` into `train/<label>` and frame datasets are
constructed per run (`train/<run_id>/<label>`), while `dataset_all` remains legacy
compatibility for older APIs/procedures.

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
WHERE split = 'train' AND deleted_at IS NULL
GROUP BY label;
```

### The `training_run` Table - ML Job Tracking

**Source**: `models.py` → class `TrainingRun` (lines 88-136)

Tracks each model training attempt:

```python
class TrainingRun(TimestampMixin, Base):
    __tablename__ = "training_run"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    train_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    test_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    seed: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    engine_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

> **Design decisions to understand:**
>
> - **`seed` is nullable** (`Optional[int]`). Not every training run uses a fixed seed.
>   The legacy SQL had `BIGINT NOT NULL`, which would reject unseeded runs.
> - **`status` uses a CHECK constraint** (not a native ENUM) to restrict values to:
>   `pending`, `sampling`, `training`, `evaluating`, `completed`, `failed`, `cancelled`.
> - **`train_fraction` and `test_fraction` are `Float`**, not `NUMERIC(3,2)`. Two CHECK
>   constraints enforce that `train_fraction` is between 0 and 1, and that the sum of
>   both fractions does not exceed 1.0.
> - **`metrics` and `config` are JSON columns** that store structured data (F1 scores,
>   hyperparameters) without needing dedicated columns for each value.

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

**Source**: `models.py` → class `TrainingSelection` (lines 139-158)

Junction table linking videos to training runs:

```python
class TrainingSelection(TimestampMixin, Base):
    __tablename__ = "training_selection"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_run.run_id", ondelete="CASCADE"), primary_key=True,
    )
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video.video_id", ondelete="CASCADE"), primary_key=True,
    )
    target_split: Mapped[str] = mapped_column(SelectionTargetEnum, primary_key=True)

    training_run: Mapped[TrainingRun] = relationship(back_populates="selections")
    video: Mapped[Video] = relationship(back_populates="selections")
```

> **Design decisions to understand:**
>
> - **Composite primary key** `(run_id, video_id, target_split)` — there is no
>   auto-increment `id` column. The combination of these three columns uniquely
>   identifies each row. This means the same video can appear in the same run
>   twice only if it has different `target_split` values (e.g., once as `train`
>   and once as `test` — though in practice this shouldn't happen).
> - **`SelectionTargetEnum`** restricts `target_split` to just `"train"` or `"test"`
>   (defined in `enums.py`). This is a smaller set than `SplitEnum` because
>   selection assignments only make sense for those two splits.
> - **`ON DELETE CASCADE`** on both foreign keys means that if a training run or
>   video is deleted, all related selection rows are automatically removed.

**Relationship Diagram:**

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│  training_run   │       │  training_selection │       │     video       │
│─────────────────│       │─────────────────────│       │─────────────────│
│ run_id (PK)     │───┐   │ run_id (PK, FK)     │   ┌───│ video_id (PK)   │
│ strategy        │   │   │ video_id (PK, FK)───│───┘   │ file_path       │
│ train_fraction  │   └──▶│ target_split (PK)   │       │ label           │
└─────────────────┘       └─────────────────────┘       └─────────────────┘

One run has MANY selections
One video can be in MANY runs
Composite PK: (run_id, video_id, target_split)
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

**Source**: `models.py` → class `PromotionLog` (lines 161-190)

Immutable audit trail of all video split changes:

```python
class PromotionLog(TimestampMixin, Base):
    __tablename__ = "promotion_log"

    promotion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video.video_id", ondelete="CASCADE"), nullable=False,
    )
    from_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    to_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    intended_label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict, nullable=True)
```

> **Design decisions to understand:**
>
> - **`promotion_id` is an auto-increment integer**, not a UUID. Promotion logs are
>   append-only audit records, so a simple sequential ID is sufficient and more
>   efficient for ordering.
> - **`intended_label`** (not `label`) — the column name clarifies that this is the
>   label the promoter *intended* to apply, which may differ from the video's current
>   label if the promotion failed.
> - **`actor`** (not `user_id`) — a shorter `String(120)` that identifies who or what
>   triggered the promotion (could be a username, an n8n workflow ID, or `"system"`).
> - **`dry_run`** flag allows testing promotions without actually moving files. When
>   `dry_run=True`, the log records what *would* happen without side effects.
> - **`extra_data`** (DB column `metadata`) stores any additional context as JSON.

**Key Concept: Idempotency**

The `idempotency_key` ensures the same operation can be safely retried:

```sql
-- First call: inserts successfully
INSERT INTO promotion_log (video_id, from_split, to_split, intended_label, idempotency_key)
VALUES ('abc', 'temp', 'dataset_all', 'happy', 'promo-001');

-- Second call with same key: fails (unique constraint violation)
-- No duplicate promotion occurs!
```

**Common Queries:**

```sql
-- Promotion history for a video
SELECT from_split, to_split, intended_label, actor, created_at
FROM promotion_log
WHERE video_id = 'abc-123-def'
ORDER BY created_at;

-- Who has been promoting today?
SELECT actor, COUNT(*) as promotions
FROM promotion_log
WHERE created_at > now() - INTERVAL '24 hours'
  AND success = TRUE
GROUP BY actor;

-- Failed promotions (for debugging)
SELECT video_id, from_split, to_split, error_message
FROM promotion_log
WHERE success = FALSE;
```

### The `label_event` Table - Human Labeling Decisions

**Source**: `models.py` → class `LabelEvent` (lines 198-230)

Audit log for all labeling actions performed by human raters:

```python
class LabelEvent(Base):
    """Audit log for labeling actions (Labeling Agent - Agent 2)."""
    __tablename__ = "label_event"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("video.video_id", ondelete="SET NULL"), nullable=True,
    )
    label: Mapped[str] = mapped_column(EmotionEnum, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    rater_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False,
    )
```

> **Design decisions to understand:**
>
> - **`LabelEvent` does NOT use `TimestampMixin`** — it has its own `created_at` but
>   no `updated_at`. Label events are immutable audit records: once written, they are
>   never modified. This is an intentional design choice.
> - **`video_id` uses `ON DELETE SET NULL`** (not `CASCADE`). If a video is deleted,
>   the label event record survives with `video_id = NULL`. This preserves the audit
>   trail even after the video is purged for privacy compliance.
> - **`label` is NOT NULL** — every label event must record which emotion was assigned.
> - **`action` is constrained by a CHECK** to one of five values (see table below).
> - **`rater_id`** (not `user_id`) — identifies the human who performed the labeling.

**Action Types (enforced by `chk_label_event_action`):**

| Action          | Description                      |
| --------------- | -------------------------------- |
| `label_only`    | Add label without changing split |
| `promote_train` | Label and move to training split |
| `promote_test`  | Move to test split (no label)    |
| `discard`       | Mark for deletion/purge          |
| `relabel`       | Change existing label            |

---

## Lesson 3.4: Legacy-Only Tables (15 minutes)

The legacy SQL file `001_phase1_schema.sql` defined three additional tables that are
**not part of the current ORM models**. They were designed for features that have not
yet been implemented. You will encounter them in the legacy SQL files but should not
expect to find corresponding Python classes in `models.py`.

| Legacy Table | Intended Purpose | Why It's Not in the ORM |
| ------------ | ---------------- | ----------------------- |
| `user_session` | Track web UI user sessions (login, activity, logout) | The web UI (Streamlit) manages its own session state. No database-backed sessions are needed yet. |
| `generation_request` | Track AI video generation requests (Luma, Runway API calls) | Video generation is handled externally. If integrated later, a new ORM model and migration will be created. |
| `emotion_event` | Store real-time emotion detections from Jetson (high-volume streaming data) | Real-time inference results are consumed by the gateway and LLM pipeline, not persisted to PostgreSQL. If persistence is needed later, a time-series database or partitioned table would be more appropriate. |

> **Why mention them at all?**
>
> You may see these tables referenced in older documentation, the legacy SQL files, or
> in the relationship diagram from the original design. Understanding that they exist
> but are intentionally excluded from the active schema prevents confusion when you
> encounter them. If any of these features are built in the future, the correct approach
> is to add new ORM model classes to `models.py` and generate a new Alembic migration —
> **not** to run the legacy SQL files.

---

## Lesson 3.5: Operations Tables (45 minutes)

These four tables support the operational agents (Deployment, Privacy, Observability,
Reconciler). Like `LabelEvent`, they do **not** use `TimestampMixin` — each manages
its own timestamp column because they are append-only records with no `updated_at`.

### The `deployment_log` Table - Model Deployments

**Source**: `models.py` → class `DeploymentLog` (lines 233-270)

Tracks TensorRT model deployments to Jetson (Agent 7):

```python
class DeploymentLog(Base):
    __tablename__ = "deployment_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    engine_path: Mapped[str] = mapped_column(String(500), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    rollback_from: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gate_b_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fps_measured: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    latency_p50_ms: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    latency_p95_ms: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    gpu_memory_gb: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

> **Design decisions to understand:**
>
> - **Auto-increment `id`** (not UUID) — deployment logs are sequential records.
> - **`target_stage`** is constrained by `chk_deployment_stage` to: `shadow`, `canary`, `rollout`.
> - **`status`** is constrained by `chk_deployment_status` to: `pending`, `deploying`,
>   `success`, `failed`, `rolled_back`.
> - **Gate B metrics** (`fps_measured`, `latency_p50_ms`, etc.) use `Numeric` for
>   precise decimal storage. `gate_b_passed` is a boolean summary.
> - **`rollback_from`** records the previous engine path when a rollback occurs.
> - **No foreign key to `training_run`** — the deployment links to the training run
>   via `mlflow_run_id` instead, keeping the tables loosely coupled.

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

**Source**: `models.py` → class `AuditLog` (lines 273-297)

GDPR audit trail for data access and deletion (Agent 8):

```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="video")
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

> **Design decisions to understand:**
>
> - **`entity_type` + `entity_id`** is a polymorphic pattern — the audit log can
>   track actions on any entity type (video, user, model) without needing a separate
>   foreign key for each. `entity_type` defaults to `"video"`.
> - **`operator`** (not `user_id`) — identifies who performed the action. Could be
>   a human, an n8n workflow, or `"system"` for automated purges.
> - **`ip_address` is `String(45)`** — long enough for IPv6 addresses (max 45 chars).
> - **`extra_data`** (DB column `metadata`) uses `JSONB` (not plain `JSON`) for
>   indexed, queryable storage of additional audit details.

### The `obs_samples` Table - System Metrics

**Source**: `models.py` → class `ObsSample` (lines 300-318)

Time-series metrics for system monitoring (Agent 9):

```python
class ObsSample(Base):
    __tablename__ = "obs_samples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    src: Mapped[str] = mapped_column(String(100), nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
```

> **Design decisions to understand:**
>
> - **Minimal columns by design** — this table is optimized for high-volume inserts.
>   The `src` + `metric` pair identifies what is being measured, `value` is the
>   measurement, and `labels` holds any additional tags as JSONB.
> - **`Numeric(15, 4)`** for `value` — supports very large numbers (up to 10^11)
>   with 4 decimal places of precision.
> - **Indexed on `(ts)` and `(src, metric)`** for efficient time-range and
>   source-filtered queries.

**Example Data:**

| ts                  | src     | metric             | value | labels                      |
| ------------------- | ------- | ------------------ | ----- | --------------------------- |
| 2025-01-05 14:30:00 | jetson  | gpu_temp_c         | 67.2  | `{"device": "reachy-mini"}` |
| 2025-01-05 14:30:01 | gateway | request_latency_ms | 45.3  | `{"endpoint": "/videos"}`   |

### The `reconcile_report` Table - Consistency Checks

**Source**: `models.py` → class `ReconcileReport` (lines 321-348)

Results of filesystem/database reconciliation (Agent 4):

```python
class ReconcileReport(Base):
    __tablename__ = "reconcile_report"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    orphan_count: Mapped[int] = mapped_column(default=0, nullable=False)
    missing_count: Mapped[int] = mapped_column(default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(default=0, nullable=False)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

> **Design decisions to understand:**
>
> - **`trigger_type`** is constrained by `chk_reconcile_trigger` to: `scheduled`,
>   `manual`, `webhook`. This tells you *why* the reconciliation ran.
> - **Three count columns** (`orphan_count`, `missing_count`, `mismatch_count`)
>   give a quick summary without needing to parse the `details` JSONB.
>   - **Orphan**: file exists on disk but has no DB record
>   - **Missing**: DB record exists but file is gone from disk
>   - **Mismatch**: file exists but hash/size doesn't match the DB record
> - **`drift_detected`** is a boolean summary — `True` if any count > 0.
> - **`auto_fixed`** indicates whether the reconciler automatically corrected
>   the drift (e.g., by removing orphan DB records).
> - **`duration_ms`** tracks how long the reconciliation took, useful for
>   monitoring performance as the dataset grows.

---

## Lesson 3.6: Complete Relationship Diagram (30 minutes)

The diagram below shows all 9 ORM-managed tables and their relationships.
Tables connected by arrows have foreign key relationships. Tables in the
"Standalone" section have no foreign keys — they are independent records.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     REACHY DATABASE RELATIONSHIPS (9 ORM Tables)                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│                              ┌─────────────────┐                                    │
│                              │  training_run   │                                    │
│                              │─────────────────│                                    │
│                              │ run_id (PK)     │                                    │
│                              │ strategy        │                                    │
│                              │ status          │                                    │
│                              │ metrics (JSON)  │                                    │
│                              └────────┬────────┘                                    │
│                                       │                                              │
│                                       │ 1:M                                          │
│                                       ▼                                              │
│ ┌─────────────────┐         ┌─────────────────────┐                                 │
│ │ promotion_log   │         │ training_selection  │                                 │
│ │─────────────────│         │─────────────────────│                                 │
│ │ promotion_id(PK)│         │ run_id (PK, FK)     │                                 │
│ │ video_id (FK)───│────┐    │ video_id (PK, FK)───│──┐                              │
│ │ from_split      │    │    │ target_split (PK)   │  │                              │
│ │ intended_label  │    │    └─────────────────────┘  │                              │
│ │ actor           │    │                             │                              │
│ │ idempotency_key │    │                             │                              │
│ └─────────────────┘    │                             │                              │
│                        │    ┌─────────────────┐      │                              │
│ ┌─────────────────┐    │    │     video       │◀─────┘                              │
│ │  label_event    │    └───▶│─────────────────│                                     │
│ │─────────────────│         │ video_id (PK)   │                                     │
│ │ event_id (PK)   │         │ file_path       │                                     │
│ │ video_id (FK)───│────────▶│ split           │                                     │
│ │ label           │         │ label           │                                     │
│ │ action          │         │ sha256          │                                     │
│ │ rater_id        │         │ size_bytes      │                                     │
│ └─────────────────┘         └─────────────────┘                                     │
│   (ON DELETE SET NULL)        ▲  ▲  ▲                                               │
│                               │  │  │  (all ON DELETE CASCADE except label_event)    │
│                                                                                      │
│   STANDALONE TABLES (no foreign keys):                                              │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐│
│   │ deployment_log  │  │   audit_log     │  │   obs_samples   │  │reconcile_report││
│   │─────────────────│  │─────────────────│  │─────────────────│  │────────────────││
│   │ id (PK)         │  │ id (PK)         │  │ id (PK)         │  │ id (PK)        ││
│   │ engine_path     │  │ action          │  │ ts              │  │ run_at         ││
│   │ target_stage    │  │ entity_type     │  │ src             │  │ trigger_type   ││
│   │ gate_b_passed   │  │ entity_id       │  │ metric          │  │ drift_detected ││
│   │ mlflow_run_id   │  │ operator        │  │ value           │  │ orphan_count   ││
│   └─────────────────┘  └─────────────────┘  └─────────────────┘  └────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Key relationships to remember:**

- **`video`** is the central table — three other tables reference it via foreign keys:
  `training_selection`, `promotion_log`, and `label_event`.
- **`training_run` → `training_selection` → `video`** is the training data pipeline.
  A run selects many videos; a video can be in many runs (many-to-many via junction table).
- **`promotion_log`** and **`label_event`** are audit tables that reference `video`
  but serve different purposes: promotions track *split changes*, label events track
  *labeling actions*.
- **`label_event`** uses `ON DELETE SET NULL` so audit records survive video deletion.
  All other FK relationships use `ON DELETE CASCADE`.
- The four **standalone tables** have no foreign keys. They are independent operational
  records that can be queried without joining to other tables.

---

## Knowledge Check

1. Which table stores the actual video file contents?

2. What is the purpose of the `idempotency_key` in `promotion_log`?

3. If you need to find all videos labeled "happy" that were used in training, which tables do you query?

4. What happens to `training_selection` records when a `training_run` is deleted?

5. Which table would you query to check if the Jetson is meeting performance requirements?

6. Name the three source-of-truth files and explain the role of each.

7. Why does `label_event` use `ON DELETE SET NULL` instead of `ON DELETE CASCADE`?

<details>
<summary>Click to see answers</summary>

1. **None!** The database stores metadata only. Video files are on the filesystem.

2. To prevent duplicate promotions. If the same `idempotency_key` is used twice, the second insert fails due to the unique constraint.

3. `video` and `training_selection`. Join them to find videos with `label='happy'` that appear in `training_selection`.

4. They are deleted automatically due to `ON DELETE CASCADE` on the foreign key.

5. `deployment_log` — check `fps_measured`, `latency_p50_ms`, `latency_p95_ms`, and `gate_b_passed`.

6. **`models.py`** defines the 9 Python classes (primary source of truth for table structure). **`enums.py`** defines the three shared enum types as CHECK constraints. **`202510280000_initial_schema.py`** is the Alembic migration that creates the actual tables in PostgreSQL.

7. So that audit records survive video deletion. If a video is purged for privacy compliance, the `label_event` rows remain (with `video_id = NULL`) to preserve the audit trail.

</details>

---

## Hands-On Exercise 3

### Setup: Load Sample Data

```sql
-- Insert test videos (note: sha256 and size_bytes are required NOT NULL columns)
INSERT INTO video (video_id, file_path, split, label, size_bytes, sha256, duration_sec) VALUES
    ('aaaaaaaa-0001-0001-0001-000000000001', 'videos/train/happy/happy_001.mp4', 'train', 'happy', 1024000, 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', 5.0),
    ('aaaaaaaa-0001-0001-0001-000000000002', 'videos/train/happy/happy_002.mp4', 'train', 'happy', 1048576, 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3', 6.2),
    ('aaaaaaaa-0001-0001-0001-000000000003', 'videos/train/sad/sad_001.mp4', 'train', 'sad', 2097152, 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', 4.5),
    ('aaaaaaaa-0001-0001-0001-000000000004', 'videos/train/sad/sad_002.mp4', 'train', 'sad', 1500000, 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5', 5.8),
    ('aaaaaaaa-0001-0001-0001-000000000005', 'videos/temp/unlabeled_001.mp4', 'temp', NULL, 500000, 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6', 3.0);

-- Create a training run (seed is nullable in the current schema)
INSERT INTO training_run (run_id, strategy, train_fraction, test_fraction, seed, status)
VALUES ('bbbbbbbb-0001-0001-0001-000000000001', 'balanced_random', 0.70, 0.30, 42, 'completed');

-- Link videos to run using the composite PK (run_id, video_id, target_split)
INSERT INTO training_selection (run_id, video_id, target_split)
SELECT 'bbbbbbbb-0001-0001-0001-000000000001', video_id,
       CASE WHEN random() < 0.7 THEN 'train' ELSE 'test' END
FROM video
WHERE split = 'train';
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
   WHERE split = 'train';
   ```

4. **List videos in your training run with their labels:**
   
   ```sql
   SELECT v.file_path, v.label, ts.target_split
   FROM training_selection ts
   JOIN video v ON ts.video_id = v.video_id
   WHERE ts.run_id = 'bbbbbbbb-0001-0001-0001-000000000001';
   ```

5. **Check train/test distribution:**
   
   ```sql
   SELECT target_split, COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
   FROM training_selection
   WHERE run_id = 'bbbbbbbb-0001-0001-0001-000000000001'
   GROUP BY target_split;
   ```

---

## Summary

In this module, you learned:

- ✅ The purpose of all 9 ORM-managed tables in the Reachy database
- ✅ How the three source-of-truth files (`models.py`, `enums.py`, Alembic migration) work together
- ✅ The current video lifecycle: temp → train/<label> → run-specific frame datasets → purged
- ✅ How tables relate through foreign keys (CASCADE vs SET NULL)
- ✅ Which table to query for different use cases
- ✅ Why 3 legacy tables exist but are not part of the active schema
- ✅ Key design decisions: String UUIDs, CHECK-constraint enums, composite PKs, TimestampMixin

**Next**: [Module 4: Stored Procedures & Business Logic](./04-MODULE-STORED-PROCEDURES.md)
