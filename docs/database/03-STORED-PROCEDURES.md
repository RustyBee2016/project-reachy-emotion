# Stored Procedures Reference

This document describes the PostgreSQL stored procedures (functions) that implement core business logic for the Reachy Emotion Detection system.

**Source File**: `alembic/versions/002_stored_procedures.sql` (362 lines)

## What Are Stored Procedures?

Stored procedures are reusable code stored inside the database. They:
- Encapsulate complex business logic
- Run faster than multiple round-trip queries
- Ensure consistent behavior across all callers
- Can perform transactions atomically

## Trigger Functions

### touch_updated_at()

**Purpose**: Automatically updates the `updated_at` timestamp when a row is modified.

**Source**: `alembic/versions/002_stored_procedures.sql:10-18`

```sql
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Usage**: Applied to `video` and `training_run` tables via triggers.

```sql
-- Applied automatically on UPDATE
UPDATE video SET label = 'happy' WHERE video_id = 'abc-123';
-- updated_at is now set to current time
```

---

## Core Functions

### get_class_distribution()

**Purpose**: Returns count and statistics for each emotion class in a split.

**Source**: `alembic/versions/002_stored_procedures.sql:30-70`

**Signature**:
```sql
get_class_distribution(p_split video_split)
RETURNS TABLE (
    split video_split,
    label emotion_label,
    count BIGINT,
    percentage NUMERIC(5,2),
    avg_duration NUMERIC(10,2),
    total_size_mb NUMERIC(12,2)
)
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `p_split` | `video_split` | Which split to analyze (e.g., 'dataset_all') |

**Returns**: One row per emotion label with:
- `count`: Number of videos
- `percentage`: Percentage of total
- `avg_duration`: Average video length in seconds
- `total_size_mb`: Total storage in megabytes

**Example**:
```sql
SELECT * FROM get_class_distribution('dataset_all');
```

**Result**:
| split | label | count | percentage | avg_duration | total_size_mb |
|-------|-------|-------|------------|--------------|---------------|
| dataset_all | happy | 450 | 48.39 | 5.23 | 2,340.12 |
| dataset_all | sad | 480 | 51.61 | 5.18 | 2,501.45 |

**Use Case**: Check class balance before training.

---

### check_dataset_balance()

**Purpose**: Evaluates whether the dataset is ready for training based on sample count and class imbalance.

**Source**: `alembic/versions/002_stored_procedures.sql:80-150`

**Signature**:
```sql
check_dataset_balance(
    p_min_samples INTEGER DEFAULT 100,
    p_max_ratio NUMERIC DEFAULT 1.5
)
RETURNS TABLE (
    balanced BOOLEAN,
    total_samples BIGINT,
    min_class emotion_label,
    min_count BIGINT,
    max_class emotion_label,
    max_count BIGINT,
    imbalance_ratio NUMERIC(5,2),
    recommendation TEXT
)
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `p_min_samples` | `INTEGER` | 100 | Minimum samples per class required |
| `p_max_ratio` | `NUMERIC` | 1.5 | Maximum allowed imbalance ratio (max/min) |

**Returns**:
- `balanced`: TRUE if dataset passes all checks
- `total_samples`: Total videos in dataset_all
- `min_class`/`min_count`: Smallest class and its count
- `max_class`/`max_count`: Largest class and its count
- `imbalance_ratio`: max_count / min_count
- `recommendation`: Human-readable status message

**Example**:
```sql
SELECT * FROM check_dataset_balance(100, 1.5);
```

**Possible Results**:

1. **Empty Dataset**:
```
balanced: FALSE
recommendation: "Dataset is empty. Add labeled videos to dataset_all first."
```

2. **Insufficient Samples**:
```
balanced: FALSE
total_samples: 50
recommendation: "Need more samples. Minimum 100 per class, but 'happy' has only 25."
```

3. **Imbalanced Classes**:
```
balanced: FALSE
imbalance_ratio: 3.0
recommendation: "Class imbalance detected. 'happy' has 900 samples, 'sad' has 300. Ratio 3.0 exceeds max 1.5."
```

4. **Ready for Training**:
```
balanced: TRUE
recommendation: "Dataset is balanced and ready for training."
```

**Use Case**: Quality gate before starting a training run.

---

### promote_video_safe()

**Purpose**: Atomically promotes a video from one split to another with full validation and audit logging.

**Source**: `alembic/versions/002_stored_procedures.sql:160-260`

**Signature**:
```sql
promote_video_safe(
    p_video_id UUID,
    p_dest_split video_split,
    p_label emotion_label DEFAULT NULL,
    p_user_id VARCHAR(255) DEFAULT 'system',
    p_idempotency_key VARCHAR(64) DEFAULT NULL,
    p_dry_run BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    old_split video_split,
    new_split video_split,
    old_label emotion_label,
    new_label emotion_label
)
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `p_video_id` | `UUID` | Required | Video to promote |
| `p_dest_split` | `video_split` | Required | Target split |
| `p_label` | `emotion_label` | NULL | Label (required for dataset_all/train) |
| `p_user_id` | `VARCHAR` | 'system' | Who is making this change |
| `p_idempotency_key` | `VARCHAR(64)` | NULL | Prevents duplicate processing |
| `p_dry_run` | `BOOLEAN` | FALSE | If TRUE, validates but doesn't change |

**Validation Rules**:
1. Video must exist
2. Video cannot be already in destination split
3. Label is REQUIRED when promoting to `dataset_all` or `train`
4. Label must be NULL when promoting to `temp`, `test`, or `purged`
5. If idempotency key exists, returns success without re-processing

**Example - Normal Promotion**:
```sql
SELECT * FROM promote_video_safe(
    p_video_id := 'abc-123-def-456',
    p_dest_split := 'dataset_all',
    p_label := 'happy',
    p_user_id := 'alice@example.com'
);
```

**Result**:
```
success: TRUE
message: "Video promoted successfully"
old_split: temp
new_split: dataset_all
old_label: NULL
new_label: happy
```

**Example - Idempotent Replay**:
```sql
-- First call
SELECT * FROM promote_video_safe(
    p_video_id := 'abc-123',
    p_dest_split := 'dataset_all',
    p_label := 'happy',
    p_idempotency_key := 'promo-2025-01-05-001'
);
-- success: TRUE, message: "Video promoted successfully"

-- Second call with same idempotency key
SELECT * FROM promote_video_safe(
    p_video_id := 'abc-123',
    p_dest_split := 'dataset_all',
    p_label := 'happy',
    p_idempotency_key := 'promo-2025-01-05-001'
);
-- success: TRUE, message: "Idempotent: operation already completed"
```

**Example - Dry Run**:
```sql
SELECT * FROM promote_video_safe(
    p_video_id := 'abc-123',
    p_dest_split := 'dataset_all',
    p_label := 'happy',
    p_dry_run := TRUE
);
-- success: TRUE, message: "Dry run: promotion would succeed"
-- Video is NOT actually changed
```

**Error Cases**:
```sql
-- Missing label
SELECT * FROM promote_video_safe('abc-123', 'dataset_all', NULL);
-- success: FALSE, message: "Label required when promoting to dataset_all"

-- Video not found
SELECT * FROM promote_video_safe('nonexistent-id', 'dataset_all', 'happy');
-- success: FALSE, message: "Video not found"

-- Already in target split
SELECT * FROM promote_video_safe('abc-123', 'dataset_all', 'happy');
-- (when video is already in dataset_all)
-- success: FALSE, message: "Video already in dataset_all split"
```

**Side Effects**:
- Updates `video.split` and `video.label`
- Inserts row into `promotion_log` for audit trail

---

### create_training_run_with_sampling()

**Purpose**: Creates a new training run and automatically samples videos into train/test splits.

**Source**: `alembic/versions/002_stored_procedures.sql:270-362`

**Signature**:
```sql
create_training_run_with_sampling(
    p_strategy VARCHAR(100),
    p_train_fraction NUMERIC(3,2),
    p_seed BIGINT DEFAULT NULL
)
RETURNS UUID
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `p_strategy` | `VARCHAR(100)` | Required | Sampling strategy name |
| `p_train_fraction` | `NUMERIC(3,2)` | Required | Fraction for training (0.0-1.0) |
| `p_seed` | `BIGINT` | NULL | Random seed for reproducibility |

**Returns**: `UUID` of the created training run.

**What It Does**:
1. Creates a new `training_run` record
2. Calculates SHA256 hash of all videos in `dataset_all` (for reproducibility)
3. Sets a reproducible random seed
4. Samples videos from `dataset_all` into train/test splits
5. Creates `training_selection` records for each selected video
6. Returns the new run_id

**Example**:
```sql
SELECT create_training_run_with_sampling(
    p_strategy := 'balanced_random',
    p_train_fraction := 0.7,
    p_seed := 42
);
-- Returns: 'e7b8c9d0-1234-5678-abcd-ef0123456789'
```

**Verify the Results**:
```sql
-- Check the training run
SELECT * FROM training_run WHERE run_id = 'e7b8c9d0-...';

-- Check split distribution
SELECT target_split, COUNT(*) as count
FROM training_selection
WHERE run_id = 'e7b8c9d0-...'
GROUP BY target_split;
-- Result:
-- target_split | count
-- train        | 700
-- test         | 300
```

**Important Note - Stratification Bug**:

The current implementation claims to perform stratified sampling but has a logic issue. True stratification should maintain the same train/test ratio within each emotion class. The current implementation orders by label then random, but applies the split decision globally.

**Current Behavior** (may vary by class):
```
happy: 68% train, 32% test  (should be 70/30)
sad:   72% train, 28% test  (should be 70/30)
```

See [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for details and workarounds.

---

### get_training_run_details()

**Purpose**: Retrieves comprehensive information about a training run including selection counts.

**Source**: `alembic/versions/002_stored_procedures.sql` (later section)

**Signature**:
```sql
get_training_run_details(p_run_id UUID)
RETURNS TABLE (
    run_id UUID,
    strategy VARCHAR(100),
    train_fraction NUMERIC(3,2),
    test_fraction NUMERIC(3,2),
    seed BIGINT,
    status training_status,
    dataset_hash CHAR(64),
    train_count BIGINT,
    test_count BIGINT,
    created_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
)
```

**Example**:
```sql
SELECT * FROM get_training_run_details('e7b8c9d0-...');
```

**Result**:
| Column | Value |
|--------|-------|
| run_id | e7b8c9d0-... |
| strategy | balanced_random |
| train_fraction | 0.70 |
| test_fraction | 0.30 |
| seed | 42 |
| status | pending |
| dataset_hash | abc123... |
| train_count | 700 |
| test_count | 300 |

---

## Function Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROMOTION WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User Labels Video                                           │
│     │                                                           │
│     ▼                                                           │
│  promote_video_safe(video_id, 'dataset_all', 'happy')          │
│     │                                                           │
│     ├─── Validates video exists                                 │
│     ├─── Checks idempotency key                                 │
│     ├─── Validates label requirement                            │
│     │                                                           │
│     ▼                                                           │
│  [UPDATE video SET split='dataset_all', label='happy']         │
│  [INSERT INTO promotion_log ...]                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    TRAINING WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Check Dataset Readiness                                     │
│     │                                                           │
│     ▼                                                           │
│  check_dataset_balance(100, 1.5)                               │
│     │                                                           │
│     ├─── balanced: TRUE? ─── Continue                          │
│     └─── balanced: FALSE? ── Stop, show recommendation         │
│                                                                  │
│  2. View Class Distribution (optional)                          │
│     │                                                           │
│     ▼                                                           │
│  get_class_distribution('dataset_all')                         │
│                                                                  │
│  3. Create Training Run                                         │
│     │                                                           │
│     ▼                                                           │
│  create_training_run_with_sampling('balanced_random', 0.7, 42) │
│     │                                                           │
│     ├─── Creates training_run record                           │
│     ├─── Calculates dataset_hash                                │
│     ├─── Samples videos into train/test                        │
│     └─── Returns run_id                                         │
│                                                                  │
│  4. Verify Run Details                                          │
│     │                                                           │
│     ▼                                                           │
│  get_training_run_details(run_id)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Stored Procedures

Tests are located in `tests/test_database_schema.py`.

```python
# Example test from tests/test_database_schema.py:157-164
def test_check_dataset_balance_empty(self, db_cursor):
    """Test balance check with empty dataset."""
    db_cursor.execute("SELECT * FROM check_dataset_balance(100, 1.5)")
    result = db_cursor.fetchone()

    assert result['balanced'] is False
    assert result['total_samples'] == 0
    assert 'empty' in result['recommendation'].lower()
```

Run tests with:
```bash
pytest tests/test_database_schema.py -v
```

## Next Steps

- See [04-PYTHON-ORM-MODELS.md](04-PYTHON-ORM-MODELS.md) for how Python code interacts with the database
- See [05-API-INTEGRATION.md](05-API-INTEGRATION.md) for API endpoints that use these functions
