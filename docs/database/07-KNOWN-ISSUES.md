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
| 13 | AuditLog IP type mismatch | 🟠 MINOR | Lost IP queries | Open |

---

## 🔴 CRITICAL ISSUES

### Issue #1: Emotion Enum Mismatch

**Problem**: The `emotion_label` enum has 6 values in SQL but only 5 in Python.

**SQL** (`alembic/versions/001_phase1_schema.sql`, line 19):
```sql
CREATE TYPE emotion_label AS ENUM (
    'neutral', 'happy', 'sad', 'angry', 'surprise', 'fearful'
);
```

**Python** (`apps/api/app/db/enums.py`, lines 21-31):
```python
EmotionEnum = Enum(
    "neutral", "happy", "sad", "angry", "surprise",
    # Missing 'fearful'!
    name=EMOTION_ENUM_NAME,
)
```

**Impact**: Python code will reject 'fearful' as invalid.

**Fix**:
```python
EmotionEnum = Enum(
    "neutral", "happy", "sad", "angry", "surprise", "fearful",
    name=EMOTION_ENUM_NAME,
)
```

---

### Issue #2: Split Enum 'purged' Mismatch

**Problem**: The `video_split` enum is created with 4 values initially, but Python expects 5.

**SQL 001** (`alembic/versions/001_phase1_schema.sql`, line 13):
```sql
CREATE TYPE video_split AS ENUM ('temp', 'dataset_all', 'train', 'test');
-- 'purged' added later in 003_missing_tables.sql
```

**Python** (`apps/api/app/db/enums.py`, lines 9-19):
```python
SplitEnum = Enum(
    "temp", "dataset_all", "train", "test", "purged",  # Has 'purged'
    name=VIDEO_SPLIT_ENUM_NAME,
)
```

**Impact**: Order-dependent failures if SQL 003 not applied before Python runs.

**Fix Options**:
- A) Add 'purged' to SQL 001 initially
- B) Ensure SQL 003 runs before any Python code

---

### Issue #3: Check Constraint Inconsistency

**Problem**: The split/label policy constraint differs between files.

**models.py** (lines 66-75):
```python
CheckConstraint(
    """
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR (split IN ('dataset_all', 'train') AND label IS NOT NULL)
    """,
    name="chk_video_split_label_policy",
)
```

**Alembic** (`202510280000_initial_schema.py`, lines 66-74):
```python
sa.CheckConstraint(
    """
    (split IN ('temp', 'test') AND label IS NULL)  -- Missing 'purged'!
    OR (split IN ('dataset_all', 'train') AND label IS NOT NULL)
    """,
)
```

**Fix**: Add 'purged' to Alembic constraint.

---

### Issue #4: Missing Check Constraint in SQL

**Problem**: SQL schema files don't include the split/label policy constraint.

**Impact**: Database created with SQL files won't enforce business rules.

**Fix**: Add to `001_phase1_schema.sql`:
```sql
ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR (split IN ('dataset_all', 'train') AND label IS NOT NULL)
);
```

---

### Issue #5: Missing SQLAlchemy Models

**Problem**: Three tables exist in SQL but have no ORM models.

**Missing from `models.py`**:
- `user_session` (SQL line 118)
- `generation_request` (SQL line 136)
- `emotion_event` (SQL line 155)

**Impact**: Cannot access these tables via Python ORM.

**Fix**: Add model classes to `apps/api/app/db/models.py`.

---

### Issue #6: Video Model Missing Columns

**Problem**: Video model doesn't include all SQL columns.

**Missing**:
- `metadata JSONB`
- `deleted_at TIMESTAMPTZ`

**Impact**: Cannot use soft deletes or flexible metadata via ORM.

---

### Issue #7: TrainingRun Model Incomplete

**Problem**: TrainingRun model has only 6 columns but SQL has 15+.

**Missing columns**:
- `dataset_hash`
- `mlflow_run_id`
- `model_path`
- `engine_path`
- `metrics` (JSONB)
- `config` (JSONB)
- `error_message`
- `started_at`
- `completed_at`

**Impact**: MLflow integration and metrics storage broken.

---

### Issue #8: UUID vs String Type Mismatch

**Problem**: SQL uses native UUID type, but models use String(36).

**SQL**:
```sql
video_id UUID PRIMARY KEY
```

**Python**:
```python
video_id: Mapped[str] = mapped_column(String(36), primary_key=True)
```

**Impact**: Potential type conversion issues and performance differences.

---

## 🟡 MAJOR ISSUES

### Issue #9: Enum Type Name Mismatch

**Problem**: SQL and Python use different enum type names.

| SQL Name | Python Name |
|----------|-------------|
| `video_split` | `video_split_enum` |
| `emotion_label` | `emotion_enum` |

**Impact**: If both SQL and Alembic run, duplicate types created.

---

### Issue #10: PromotionLog Missing Columns

**Problem**: PromotionLog model missing idempotency columns.

**Missing**:
- `idempotency_key`
- `correlation_id`

**Impact**: Idempotency support broken via ORM.

---

### Issue #11: TrainingSelection PK Mismatch

**Problem**: Different primary key structures.

**SQL**: `id BIGSERIAL PRIMARY KEY`
**models.py**: Composite PK `(run_id, video_id, target_split)`

---

## 🟠 MINOR ISSUES

### Issue #12: Stratification Logic Bug

**Problem**: `create_training_run_with_sampling()` doesn't truly stratify.

**Current behavior**: Applies `random() < train_fraction` globally.
**Expected behavior**: Apply fraction within each label group.

**Impact**: Class imbalance in train/test splits.

---

### Issue #13: AuditLog IP Type Mismatch

**Problem**: SQL uses `INET`, Python uses `String(45)`.

**Impact**: Cannot use PostgreSQL INET operators for IP range queries.

---

## Recommended Fix Priority

### Must Fix Before Deployment
1. Issue #1 - Add 'fearful' to Python enums
2. Issue #2 - Synchronize 'purged' value
3. Issue #3 - Align check constraint
4. Issue #4 - Add constraint to SQL

### Fix Before Python ORM Works
5. Issue #5 - Create missing models
6. Issue #6 - Add missing Video columns
7. Issue #7 - Complete TrainingRun model

### Fix When Time Permits
8-13. Remaining issues

---

## Workarounds

### Using SQL While ORM is Broken

```python
# Direct SQL execution
from sqlalchemy import text

async with session.begin():
    result = await session.execute(
        text("SELECT * FROM user_session WHERE user_id = :uid"),
        {"uid": "alice@example.com"}
    )
    rows = result.fetchall()
```

### Checking Enum Values

```sql
-- Verify enum has all values
SELECT enum_range(NULL::emotion_label);
-- Should return: {neutral,happy,sad,angry,surprise,fearful}
```
