# Known Issues — Resolution Status

This document tracks the 13 database schema discrepancies that were identified during the
transition from legacy SQL files to the SQLAlchemy/Alembic-managed schema. Most issues have
been **resolved** as part of the v08.4.2 schema reconfiguration.

> **Background:** The project originally defined the database schema in raw SQL files
> (`001_phase1_schema.sql`, `002_stored_procedures.sql`, `003_missing_tables.sql`) and
> simultaneously in Python via SQLAlchemy models + Alembic migrations. This "dual definition"
> caused drift between the two sources. The resolution was to establish **SQLAlchemy + Alembic
> as the single authoritative path** and deprecate the legacy SQL files.
>
> **Authoritative source files:**
> - `apps/api/app/db/models.py` — Table definitions
> - `apps/api/app/db/enums.py` — Enum definitions
> - `apps/api/app/db/base.py` — Base class and TimestampMixin
> - `apps/api/app/db/alembic/versions/202510280000_initial_schema.py` — Migration

## Issue Summary

| # | Issue | Original Severity | Status | Resolution |
|---|-------|-------------------|--------|------------|
| 1 | Emotion enum mismatch | 🔴 CRITICAL | ✅ Resolved | `enums.py` now includes `fearful` |
| 2 | Split enum 'purged' mismatch | 🔴 CRITICAL | ✅ Resolved | `enums.py` and Alembic migration both include `purged` |
| 3 | Check constraint inconsistency | 🔴 CRITICAL | ✅ Resolved | Alembic migration now includes `purged` in constraint |
| 4 | Missing check constraint in SQL | 🔴 CRITICAL | ✅ Resolved (architecture) | Constraint in Alembic migration; SQL file deprecated |
| 5 | Missing SQLAlchemy models | 🔴 CRITICAL | ✅ Resolved | All ORM models now have Alembic migrations (20260227_000005) |
| 6 | Video model missing columns | 🔴 CRITICAL | ✅ Resolved | `extra_data` and `deleted_at` now present |
| 7 | TrainingRun model incomplete | 🔴 CRITICAL | ✅ Resolved | All 15+ columns now present |
| 8 | UUID vs String type mismatch | 🔴 CRITICAL | ✅ Resolved (by design) | `String(36)` used intentionally for SQLite test compatibility |
| 9 | Enum type name mismatch | 🟡 MAJOR | ✅ Resolved | Unified names; legacy SQL deprecated |
| 10 | PromotionLog missing columns | 🟡 MAJOR | ✅ Resolved | `idempotency_key` and `correlation_id` now present |
| 11 | TrainingSelection PK mismatch | 🟡 MAJOR | ✅ Resolved | Composite PK in both `models.py` and Alembic |
| 12 | Stratification logic bug | 🟠 MINOR | 🟠 Open (legacy path) | Bug in legacy SQL; Python services use correct logic |
| 13 | AuditLog IP type mismatch | 🟠 MINOR | ✅ Resolved (by design) | `String(45)` used intentionally for cross-DB compatibility |

---

## ✅ RESOLVED ISSUES

### Issue #1: Emotion Enum Mismatch — RESOLVED

**Original problem**: `EmotionEnum` in Python had only 5 values, missing `fearful`.

**Resolution**: `apps/api/app/db/enums.py` (lines 21-31) now includes all 6 values:

```python
EmotionEnum = Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    "fearful",
    name=EMOTION_ENUM_NAME,
    create_constraint=True,
    native_enum=False,
    validate_strings=True,
)
```

**Verified in**: `apps/api/app/db/enums.py` line 27.

---

### Issue #2: Split Enum 'purged' Mismatch — RESOLVED

**Original problem**: Legacy SQL 001 created `video_split` with only 4 values; `purged` was
added later in SQL 003, causing order-dependent failures.

**Resolution**: Both `enums.py` and the Alembic migration include `purged` from the start:

- `apps/api/app/db/enums.py` line 14: `"purged"` included in `SplitEnum`
- `apps/api/app/db/alembic/versions/202510280000_initial_schema.py` line 17: `"purged"` included in split enum

The legacy SQL files are deprecated and no longer used for schema creation.

---

### Issue #3: Check Constraint Inconsistency — RESOLVED

**Original problem**: The `chk_video_split_label_policy` constraint in the Alembic migration
was missing `purged` in the NULL-label group.

**Resolution**: The Alembic migration (`202510280000_initial_schema.py`, lines 69-77) now
includes `purged`:

```python
sa.CheckConstraint(
    """
    (
        split IN ('temp', 'test', 'purged') AND label IS NULL
    ) OR (
        split IN ('dataset_all', 'train') AND label IS NOT NULL
    )
    """,
    name="chk_video_split_label_policy",
)
```

This matches `models.py` (lines 73-82) exactly.

---

### Issue #4: Missing Check Constraint in SQL — RESOLVED (Architecture)

**Original problem**: The legacy SQL schema files did not include the `chk_video_split_label_policy`
constraint.

**Resolution**: The constraint exists in both `models.py` and the Alembic migration. Since
the legacy SQL files are deprecated and no longer used for schema creation, this issue is
resolved by architecture. The SQL files are retained for historical reference only.

---

### Issue #5: Missing SQLAlchemy Models — BY DESIGN

**Original problem**: Three tables defined in `001_phase1_schema.sql` had no ORM models:
`user_session`, `generation_request`, `emotion_event`.

**Resolution**: This is now an **intentional architectural decision**. These three tables:
- Were part of the original SQL schema for features that are not yet implemented in the app runtime
- Are **not** needed by any current Python service or API endpoint
- Were intentionally excluded from `models.py` and the Alembic migration chain

If these tables are needed in the future, they should be added to `models.py` and a new
Alembic migration generated. For now, the 9 tables in `models.py` represent the complete
operational schema.

---

### Issue #6: Video Model Missing Columns — RESOLVED

**Original problem**: The `Video` model was missing `metadata` and `deleted_at` columns.

**Resolution**: Both columns are now present in `apps/api/app/db/models.py`:

- `extra_data` (mapped to column name `metadata`): line 51-53
  ```python
  extra_data: Mapped[Optional[dict]] = mapped_column(
      "metadata", JSON, default=dict, nullable=True
  )
  ```
- `deleted_at`: lines 54-56
  ```python
  deleted_at: Mapped[Optional[datetime]] = mapped_column(
      DateTime(timezone=True), nullable=True
  )
  ```

---

### Issue #7: TrainingRun Model Incomplete — RESOLVED

**Original problem**: The `TrainingRun` model had only 6 columns but needed 15+.

**Resolution**: `apps/api/app/db/models.py` (lines 88-136) now includes all columns:
`run_id`, `strategy`, `train_fraction`, `test_fraction`, `seed`, `dataset_hash`,
`mlflow_run_id`, `model_path`, `engine_path`, `metrics` (JSON), `config` (JSON),
`error_message`, `status`, `started_at`, `completed_at`, plus `created_at`/`updated_at`
from `TimestampMixin`.

---

### Issue #8: UUID vs String Type Mismatch — RESOLVED (By Design)

**Original problem**: SQL used native `UUID` type, but Python models used `String(36)`.

**Resolution**: `String(36)` is used **intentionally** for cross-database compatibility.
The project runs tests against SQLite (which has no native UUID type). Using `String(36)`
allows the same models to work with both PostgreSQL (production) and SQLite (testing)
without conditional type switching.

**Trade-off**: Slightly less efficient than native UUID in PostgreSQL, but eliminates
test/production schema divergence.

---

### Issue #9: Enum Type Name Mismatch — RESOLVED

**Original problem**: Legacy SQL used `video_split` and `emotion_label` as enum type names,
while Python/Alembic used `video_split_enum` and `emotion_enum`.

**Resolution**: The authoritative names are now:
- `video_split_enum` (defined in `enums.py` line 15)
- `emotion_enum` (defined in `enums.py` line 28)
- `training_selection_target_enum` (defined in `enums.py` line 38)

The legacy SQL files with the old names (`video_split`, `emotion_label`) are deprecated.
Since only one path (Alembic) is used for schema creation, there is no risk of duplicate
enum types.

---

### Issue #10: PromotionLog Missing Columns — RESOLVED

**Original problem**: `PromotionLog` model was missing `idempotency_key` and `correlation_id`.

**Resolution**: Both columns are now present in `apps/api/app/db/models.py`:

- `idempotency_key`: line 175-177
  ```python
  idempotency_key: Mapped[Optional[str]] = mapped_column(
      String(64), unique=True, nullable=True
  )
  ```
- `correlation_id`: line 178
  ```python
  correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
  ```

---

### Issue #11: TrainingSelection PK Mismatch — RESOLVED

**Original problem**: SQL used `id BIGSERIAL PRIMARY KEY` while `models.py` used a composite
primary key `(run_id, video_id, target_split)`.

**Resolution**: Both `models.py` (lines 139-158) and the Alembic migration (lines 135-162)
now use the composite primary key `(run_id, video_id, target_split)`. The legacy SQL
`BIGSERIAL` approach is deprecated.

---

## 🟠 OPEN ISSUES

### Issue #12: Stratification Logic Bug — OPEN (Legacy Path)

**Problem**: The `create_training_run_with_sampling()` stored procedure in
`002_stored_procedures.sql` applies `random() < train_fraction` globally across all videos
instead of stratifying per label group.

**Impact**: Potential class imbalance in train/test splits, especially with small or
imbalanced datasets.

**Current status**: This bug exists in the **legacy SQL stored procedure** only. The
application runtime uses Python services for training run creation, which implement correct
stratified sampling. The stored procedure remains available for manual/ad-hoc use but
carries this known limitation.

**Workaround**: Use the Python service layer for training run creation, or apply the
per-label stratification fix described in Module 04 of the curriculum.

---

### Issue #13: AuditLog IP Type Mismatch — RESOLVED (By Design)

**Original problem**: SQL used `INET` type for IP addresses, but the model uses `String(45)`.

**Resolution**: `String(45)` is used **intentionally** for cross-database compatibility
(same rationale as Issue #8). The string is long enough to hold IPv6 addresses. While this
means PostgreSQL-specific `INET` operators (e.g., subnet containment `<<`) are not available
via the ORM, IP filtering can be done with string operations or raw SQL when needed.

---

## Resolution Architecture

The root cause of all 13 issues was the **dual-definition problem**: the database schema
was defined in two places (raw SQL files and Python/Alembic) that drifted apart over time.

The resolution established a single authoritative path:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHORITATIVE PATH                           │
│                                                                 │
│  enums.py ──▶ models.py ──▶ alembic/env.py ──▶ migration.py   │
│                                                                 │
│  Python defines ──▶ Alembic versions ──▶ PostgreSQL executes   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    DEPRECATED PATH                              │
│                                                                 │
│  001_phase1_schema.sql    ──┐                                   │
│  002_stored_procedures.sql ──├──▶ Retained for reference only  │
│  003_missing_tables.sql   ──┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- **`native_enum=False`**: Enums are enforced via CHECK constraints, not native PostgreSQL
  ENUM types. This avoids the `ALTER TYPE ... ADD VALUE` migration complexity.
- **`String(36)` for UUIDs**: Cross-database compatibility with SQLite for testing.
- **`String(45)` for IPs**: Cross-database compatibility; INET-specific queries use raw SQL.
- **3 legacy-only tables excluded**: `user_session`, `generation_request`, `emotion_event`
  are not needed by the current app runtime and were intentionally omitted from the ORM.

---

## Remaining Action Items

| Item | Description | Priority | Status |
|------|-------------|----------|--------|
| Generate migration for tables 5–9 | `label_event`, `deployment_log`, `audit_log`, `obs_samples`, `reconcile_report` + `run_link` | High | ✅ Done — migration `20260227_000005` |
| Composite indexes for stats queries | `(split, label)` on video, `(run_id, label)` on extracted_frame | High | ✅ Done — migration `20260227_000004` |
| Deprecate `dataset_all` split | Migrate legacy rows, update test scripts, deprecate SQL files | High | ✅ Done — migration `20260227_000006` |
| Add `updated_at` trigger | DB-level trigger on `video` and `training_run` (PG only) | Medium | ✅ Done — migration `20260227_000006` |
| Statistics views | `v_label_distribution` and `v_run_frame_stats` (PG only) | Medium | ✅ Done — migration `20260227_000006` |
| Fix stratification bug (Issue #12) | Update `002_stored_procedures.sql` to use per-label sampling, or document that the Python service is the recommended path | Low | Open (legacy SQL file now deprecated) |
