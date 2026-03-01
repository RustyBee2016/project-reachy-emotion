# Schema Reconciliation — Execution Report (2026-02-28)

## Overview

This report documents the execution of the schema reconciliation plan defined in
[10-SCHEMA-RECONCILIATION-PLAN-2026-02-28.md](./10-SCHEMA-RECONCILIATION-PLAN-2026-02-28.md).

All planned revisions (A/B/C) were implemented plus an additional constraint
reconciliation migration to close drift gaps discovered during live DB verification.

## Migration Chain (Applied)

| Revision | File | Purpose | Down From |
|----------|------|---------|-----------|
| `20260227_000004` | `composite_indexes.py` | Section 2 — missing indexes on `video`, `training_run`, `promotion_log`, `extracted_frame`, `training_selection` | `20260223_000003` |
| `20260227_000005` | `missing_orm_tables.py` | Section 3 — create `label_event`, `deployment_log`, `audit_log`, `obs_samples`, `reconcile_report` | `20260227_000004` |
| `20260227_000006` | `cleanup_view_trigger.py` | Section 4 — `run_link` adoption, `dataset_all` migration (R6), `updated_at` trigger (R7), statistics views (R9) | `20260227_000005` |
| `20260228_000007` | `constraint_reconciliation.py` | Constraint drift — `chk_video_split_label_policy`, `promotion_log` constraint tightening, `video.zfs_snapshot` ORM adoption | `20260227_000006` |
| `20260228_000008` | `training_run_constraints.py` | `training_run` CHECK constraints reconciliation | `20260228_000007` |

**Current Alembic head:** `20260228_000008`

## Section 2 (Constraints & Indexes) — Results

### Indexes Added (migration 000004)
- `ix_video_split` — `video(split)`
- `ix_video_label` — `video(label)`
- `ix_training_run_status` — `training_run(status)`
- `ix_training_run_created` — `training_run(created_at)`
- `ix_promotion_log_idempotency` — `promotion_log(idempotency_key)`

### Constraints Reconciled (migration 000007)
- **Dropped:** legacy `ck_video_split` (allowed only `temp, train, test`)
- **Added:** `chk_video_split_label_policy` with `purged` support and label enforcement
  - `split IN ('temp','test','purged') → label IS NULL`
  - `split = 'train' → label IS NOT NULL`
  - Applied with `NOT VALID` + `VALIDATE CONSTRAINT`
- **Replaced:** `promotion_log_from_split_check` → `chk_promotion_from_split` (4-value)
- **Replaced:** `promotion_log_to_split_check` → `chk_promotion_to_split` (4-value)
- **Replaced:** `promotion_log_intended_label_check` → `chk_promotion_intended_label` (3-class)

## Section 3 (Agent Tables) — Results

### Tables Created (migration 000005)
All 5 ORM-defined tables created with full constraints and indexes:

| Table | PK | Key Constraints/Indexes |
|-------|----|------------------------|
| `label_event` | `id` (Integer, autoincrement) | `chk_label_event_action`, `ix_label_event_video`, `ix_label_event_created`, `ix_label_event_idempotency` |
| `deployment_log` | `id` (Integer, autoincrement) | `chk_deployment_target_stage`, `chk_deployment_status` |
| `audit_log` | `id` (Integer, autoincrement) | `ix_audit_action`, `ix_audit_entity`, `ix_audit_timestamp` |
| `obs_samples` | `id` (Integer, autoincrement) | `ix_obs_ts`, `ix_obs_src_metric` |
| `reconcile_report` | `id` (Integer, autoincrement) | `ix_reconcile_run_at` |

## Section 4 (Legacy Object Alignment) — Results

### `video.zfs_snapshot` (migration 000007)
- `ADD COLUMN IF NOT EXISTS` — no-op on live DB where column already existed
- ORM `Video` model updated with `zfs_snapshot: Mapped[Optional[str]]`

### `run_link` (migration 000006)
- Full ORM model `RunLink` added to `models.py`
- Table created if missing; no destructive operations on existing lineage data
- Structural constraints and indexes applied

### Additional Work (migration 000006)
- `dataset_all` data migration: rows updated to valid splits
- `updated_at` trigger function (PostgreSQL only)
- Statistics views: `v_label_distribution`, `v_run_frame_stats` (PostgreSQL only)
- Legacy SQL files `002` and `003` formally deprecated with headers
- Test scripts updated to remove `dataset_all` references
- `BigInteger` → `Integer` for Phase 3 ORM model PKs (SQLite autoincrement fix)

## Rollback Notes

- **Indexes/constraints:** Can be dropped without data loss via `alembic downgrade`
- **Agent tables:** Downgrade scripts use `DROP TABLE IF EXISTS` — safe only if tables are empty
- **`zfs_snapshot` column:** Downgrade does not drop the column (non-destructive policy)
- **`run_link` table:** Downgrade does not drop populated tables

## Verification Commands

```bash
# Check current Alembic head
alembic -c apps/api/app/db/alembic.ini current

# Verify table existence
psql -U reachy_dev -d reachy_emotion -c "
  SELECT tablename FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY tablename;"

# Verify constraints
psql -U reachy_dev -d reachy_emotion -c "
  SELECT conname, conrelid::regclass
  FROM pg_constraint
  WHERE conname LIKE 'chk_%'
  ORDER BY conrelid::regclass, conname;"

# Verify indexes
psql -U reachy_dev -d reachy_emotion -c "
  SELECT indexname, tablename
  FROM pg_indexes
  WHERE schemaname = 'public'
    AND indexname LIKE 'ix_%'
  ORDER BY tablename, indexname;"
```

## Application-Level Fixes (Same Session)

In parallel with the schema reconciliation, 14 application-level fixes were
implemented as part of a promotion pipeline audit. See:
- **ADR:** `memory-bank/decisions/008-promotion-pipeline-audit-fixes.md`

Key changes: FileMover integration, idempotency enforcement, Prometheus metrics,
httpx lifecycle management, hardcoded path removal, `datetime.utcnow()` elimination.

## Sign-Off

- Schema plan: Fully executed (Sections 2, 3, 4 + constraint reconciliation)
- Documentation: `07-KNOWN-ISSUES.md`, `08-SETUP-GUIDE.md`, `09-LEGACY-SQL-USAGE-AUDIT.md` updated
- No data loss or destructive operations performed
- All migrations are idempotent-tolerant
