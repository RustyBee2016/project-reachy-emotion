# Known Issues and Workarounds

This document lists critical issues in the database implementation that must be understood before deployment.

## Issue Summary

| # | Issue | Severity | Impact | Status |
|---|-------|----------|--------|--------|
| 1 | Emotion enum mismatch | 🔴 CRITICAL | Validation failures | Open |
| 2 | Split enum 'purged' mismatch | 🔴 CRITICAL | Order-dependent failures | Open |
| 3 | Check constraint inconsistency | 🔴 CRITICAL | Constraint violations | Open |
| 4 | Missing check constraint in SQL | 🔴 CRITICAL | Data integrity issues | Open |
| 5 | Missing SQLAlchemy models | 🔴 CRITICAL | ORM access impossible | Open |
| 6 | Video model missing columns | 🔴 CRITICAL | ORM incomplete | Open |
| 7 | TrainingRun model incomplete | 🔴 CRITICAL | MLflow broken | Open |
| 8 | UUID vs String type mismatch | 🔴 CRITICAL | Type incompatibility | Open |
| 9 | Enum type name mismatch | 🟡 MAJOR | Potential duplicates | Open |
| 10 | PromotionLog missing columns | 🟡 MAJOR | Idempotency broken | Open |
| 11 | TrainingSelection PK mismatch | 🟡 MAJOR | Migration conflicts | Open |
| 12 | Stratification logic bug | 🟠 MINOR | Imbalanced splits | Open |
| 13 | AuditLog ip_address type | 🟠 MINOR | Lost INET features | Open |

---

## 🔴 CRITICAL ISSUES

### Issue #1: Emotion Enum Mismatch

**Problem**: The emotion label enum has different values in SQL vs Python.

**Files Affected**:
- `alembic/versions/001_phase1_schema.sql:19` - Has 6 values including 'fearful'
- `apps/api/app/db/enums.py:21-31` - Has only 5 values, missing 'fearful'
- `apps/api/app/db/alembic/versions/202510280000_initial_schema.py:21-30` - Missing 'fearful'

**SQL Schema**:
```sql
CREATE TYPE emotion_label AS ENUM (
    'neutral', 'happy', 'sad', 'angry', 'surprise', 'fearful'
);
```

**Python Code**:
```python
EmotionEnum = Enum(
    "neutral", "happy", "sad", "angry", "surprise",
    # 'fearful' is MISSING!
    name=EMOTION_ENUM_NAME,
)
```

**Impact**:
- SQL files will work correctly (6 emotions)
- Python code will fail if you try to use `label='fearful'`
- Alembic migration creates enum with only 5 values
- SQLAlchemy validation rejects 'fearful' as invalid

**How It Fails**:
```python
video = Video(label="fearful", ...)
# sqlalchemy.exc.StatementError: Enum value 'fearful' is not valid
```

**Fix Required**:
```python
# In apps/api/app/db/enums.py
EmotionEnum = Enum(
    "neutral", "happy", "sad", "angry", "surprise", "fearful",  # Add 'fearful'
    name=EMOTION_ENUM_NAME,
)
```

---

### Issue #2: Split Enum 'purged' Mismatch

**Problem**: The 'purged' value exists in different places at different times.

**Files Affected**:
- `alembic/versions/001_phase1_schema.sql:13` - 4 values, NO 'purged'
- `alembic/versions/003_missing_tables.sql:142-156` - Adds 'purged' later
- `apps/api/app/db/enums.py:9-19` - Already includes 'purged'
- `apps/api/app/db/alembic/versions/202510280000_initial_schema.py:12-20` - Missing 'purged'

**Impact**:
- If you run SQL files out of order: failures
- If you use Python before running 003: 'purged' doesn't exist in DB
- If you use Alembic: 'purged' never gets created

**Order Dependency**:
```
Must run: 001 → 003 → Python code (CORRECT)
Will fail: 001 → Python code (MISSING 'purged')
Will fail: Alembic only (MISSING 'purged')
```

**Fix Required**:
Either add 'purged' to `001_phase1_schema.sql` OR add it to the Alembic migration.

---

### Issue #3: Check Constraint Inconsistency

**Problem**: The split/label policy constraint differs between files.

**Python models.py (lines 66-75)**:
```python
CheckConstraint(
    """
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
    """,
    name="chk_video_split_label_policy",
)
```

**Alembic migration (lines 66-74)**:
```python
sa.CheckConstraint(
    """
    (split IN ('temp', 'test') AND label IS NULL)  # 'purged' MISSING!
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
    """,
)
```

**SQL 001_phase1_schema.sql**: Constraint is completely MISSING!

**Impact**:
- Python expects 'purged' to work without label
- Alembic constraint doesn't allow 'purged'
- SQL has no constraint at all (allows any combination)

---

### Issue #4: Missing Check Constraint in SQL Schema

**Problem**: The split/label policy constraint doesn't exist in `001_phase1_schema.sql`.

**Where It Should Be** (but isn't):
```sql
-- In 001_phase1_schema.sql, after video table definition
ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
);
```

**Impact**:
- If using SQL files only: NO data validation
- Can insert invalid combinations like `split='dataset_all', label=NULL`
- Corrupts training data integrity

---

### Issue #5: Missing SQLAlchemy Models

**Problem**: Three SQL tables have no Python ORM models.

**Missing Models**:
| SQL Table | Location | Purpose |
|-----------|----------|---------|
| `user_session` | `001_phase1_schema.sql:118` | User activity tracking |
| `generation_request` | `001_phase1_schema.sql:136` | Synthetic video requests |
| `emotion_event` | `001_phase1_schema.sql:155` | Real-time detections |

**Impact**:
```python
from apps.api.app.db.models import UserSession
# ImportError: cannot import name 'UserSession'

# Must use raw SQL instead
await session.execute(text("SELECT * FROM user_session"))
```

**Fix Required**: Create SQLAlchemy model classes for each table.

---

### Issue #6: Video Model Missing Columns

**Problem**: The Python `Video` model is missing columns that exist in SQL.

**SQL Has**:
```sql
metadata JSONB DEFAULT '{}',
deleted_at TIMESTAMPTZ
```

**Python models.py MISSING**:
- `metadata` - For flexible additional data
- `deleted_at` - For GDPR soft deletes

**Impact**:
- Cannot store flexible metadata via ORM
- Cannot implement soft deletes for GDPR compliance
- Cannot track `deleted_at` timestamp

---

### Issue #7: TrainingRun Model Incomplete

**Problem**: The `TrainingRun` model is severely incomplete.

**SQL Has 15+ Columns Including**:
```sql
dataset_hash, mlflow_run_id, model_path, engine_path,
metrics JSONB, config JSONB, error_message,
started_at, completed_at
```

**Python Has Only 8 Columns**:
```python
run_id, strategy, train_fraction, test_fraction,
seed, status, created_at, updated_at
```

**Impact**:
- Cannot track MLflow run IDs via ORM
- Cannot store trained model paths
- Cannot store training metrics or config
- Cannot track error messages or timing

---

### Issue #8: UUID vs String Type Mismatch

**Problem**: SQL uses native `UUID` type, Python uses `String(36)`.

**SQL**:
```sql
video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4()
```

**Python**:
```python
video_id: Mapped[str] = mapped_column(String(36), primary_key=True)
```

**Impact**:
- Different storage format (binary vs text)
- Different indexing characteristics
- Potential comparison issues
- Type conversion overhead

**Recommendation**: Use SQLAlchemy's `PGUUID` type or keep `String(36)` consistently.

---

## 🟡 MAJOR ISSUES

### Issue #9: Enum Type Name Mismatch

**Problem**: Enum names differ between SQL and Python.

| SQL | Python | Alembic |
|-----|--------|---------|
| `video_split` | `video_split_enum` | `video_split_enum` |
| `emotion_label` | `emotion_enum` | `emotion_enum` |
| `training_status` | (not defined) | `training_selection_target_enum` |

**Mitigation**: Python uses `native_enum=False`, which creates CHECK constraints instead of native PostgreSQL ENUMs. This masks the naming issue but may create inconsistencies.

---

### Issue #10: PromotionLog Missing Columns

**Problem**: Idempotency columns missing from Python model.

**SQL Has**:
```sql
idempotency_key VARCHAR(64) UNIQUE,
correlation_id UUID
```

**Python models.py MISSING**: Both columns.

**Impact**:
- Cannot access idempotency key via ORM
- Retry-safe operations partially broken
- Must use stored procedure for idempotent operations

---

### Issue #11: TrainingSelection Primary Key Mismatch

**Problem**: SQL and Python use different primary keys.

**SQL**:
```sql
id BIGSERIAL PRIMARY KEY,
run_id UUID NOT NULL,
video_id UUID NOT NULL,
target_split video_split NOT NULL
```

**Python**:
```python
# Composite primary key (no `id` column)
run_id: Mapped[str] = mapped_column(..., primary_key=True)
video_id: Mapped[str] = mapped_column(..., primary_key=True)
target_split: Mapped[str] = mapped_column(..., primary_key=True)
```

**Impact**:
- Different foreign key behavior
- Potential migration conflicts
- Cannot reference by single ID

---

## 🟠 MINOR ISSUES

### Issue #12: Stratification Logic Bug

**Problem**: `create_training_run_with_sampling()` doesn't truly stratify.

**Location**: `alembic/versions/002_stored_procedures.sql:313-322`

**Current Logic**:
```sql
-- Orders by label, then applies random globally
ORDER BY label, random();
CASE WHEN random() < p_train_fraction THEN 'train' ELSE 'test' END
```

**True Stratification Would**:
- Apply train_fraction to EACH label separately
- Guarantee 70/30 split within happy, within sad, etc.

**Current Result**:
```
happy: 68% train, 32% test (varies)
sad:   72% train, 28% test (varies)
```

**Expected Result**:
```
happy: 70% train, 30% test (exact)
sad:   70% train, 30% test (exact)
```

**Workaround**: Use Python's `PromoteService._balanced_sample()` which does proper stratification.

---

### Issue #13: AuditLog ip_address Type

**Problem**: SQL uses `INET`, Python uses `String(45)`.

**SQL**:
```sql
ip_address INET
```

**Python**:
```python
ip_address: Mapped[str] = mapped_column(String(45))
```

**Impact**:
- Cannot use PostgreSQL INET operators
- Cannot do IP range queries like `WHERE ip_address << '192.168.0.0/16'`

---

## Deployment Scenarios

### Scenario A: Use SQL Files Only

```bash
psql -d reachy_local -f 001_phase1_schema.sql
psql -d reachy_local -f 002_stored_procedures.sql
psql -d reachy_local -f 003_missing_tables.sql
```

**Result**: ✅ SQL works, but:
- Missing check constraint (Issue #4)
- Python ORM will fail (Issues #1, #2, #5, #6, #7)

### Scenario B: Use Alembic Only

```bash
alembic upgrade head
```

**Result**: ❌ FAILS with:
- Missing 'purged' enum value (Issue #2)
- Missing 'fearful' enum value (Issue #1)
- Constraint mismatch (Issue #3)

### Scenario C: Mix SQL + Alembic

**Result**: ❌ WORST CASE
- Duplicate enum types with different names
- Conflicting constraints
- Unpredictable behavior

### Scenario D: Fix All Issues First

**Result**: ✅ RECOMMENDED
- Apply fixes before any deployment
- Use consistent approach (SQL OR Alembic, not both)

---

## Recommended Fix Priority

### Must Fix Before Deployment

| Priority | Issue | Estimated Time |
|----------|-------|----------------|
| 1 | Add 'fearful' to Python enums and Alembic | 15 min |
| 2 | Add 'purged' to SQL 001 or Alembic | 15 min |
| 3 | Make check constraint consistent everywhere | 30 min |
| 4 | Add check constraint to SQL 001 | 15 min |

### Fix Before Python API Works

| Priority | Issue | Estimated Time |
|----------|-------|----------------|
| 5 | Add missing Video columns (metadata, deleted_at) | 30 min |
| 6 | Add missing TrainingRun columns (9 columns) | 1 hour |
| 7 | Create missing models (UserSession, etc.) | 2 hours |
| 8 | Add PromotionLog missing columns | 30 min |

### Fix When Time Permits

| Priority | Issue | Estimated Time |
|----------|-------|----------------|
| 9 | Standardize enum type names | 1 hour |
| 10 | Fix UUID vs String(36) | 2 hours |
| 11 | Fix TrainingSelection PK | 1 hour |
| 12 | Fix stratification logic | 1 hour |
| 13 | Fix AuditLog INET type | 30 min |

**Total Estimated Fix Time**: 10-12 hours for an experienced developer

---

## Testing After Fixes

```python
# tests/test_issue_fixes.py
import pytest
from apps.api.app.db.models import Video
from apps.api.app.db.enums import EmotionEnum

def test_fearful_enum_exists():
    """Issue #1: Verify 'fearful' is in emotion enum."""
    assert "fearful" in [e.name for e in EmotionEnum.enums]

def test_video_can_have_fearful_label(session):
    """Issue #1: Verify Video can be labeled 'fearful'."""
    video = Video(
        file_path="test.mp4",
        split="dataset_all",
        label="fearful",  # Should not fail
        sha256="a" * 64,
        size_bytes=1000,
    )
    session.add(video)
    session.flush()  # Should not raise

def test_purged_split_exists():
    """Issue #2: Verify 'purged' is in split enum."""
    from apps.api.app.db.enums import SplitEnum
    assert "purged" in [e.name for e in SplitEnum.enums]
```

---

## Next Steps

1. Review this document with the team
2. Prioritize fixes based on deployment timeline
3. Create fix branches for each issue
4. Test thoroughly before merging
5. See [08-SETUP-GUIDE.md](08-SETUP-GUIDE.md) for setting up a test environment
