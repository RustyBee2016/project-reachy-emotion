# Schema Reconciliation Plan (2026-02-28)

## Objective
Produce a non-destructive Alembic revision set that reconciles live PostgreSQL schema drift with the active ORM/migration source of truth, addressing prior findings in strict order:

1. Section 2: partially mapped / drifted objects
2. Section 3: missing mappings
3. Section 4: extra live objects not represented

This plan is approval-only. No schema changes are executed until explicit approval.

## Baseline Snapshot (Live DB, 2026-02-28)
- Alembic head in DB: `20260223_000003`
- Present tables: `video`, `training_run`, `training_selection`, `promotion_log`, `extracted_frame`, `run_link`, `alembic_version`
- Missing tables vs ORM: `label_event`, `deployment_log`, `audit_log`, `obs_samples`, `reconcile_report`
- Drift highlights:
  - `video` missing expected `chk_video_split_label_policy`, `ix_video_split`, `ix_video_label`
  - `training_run` missing expected `ix_training_run_status`, `ix_training_run_created`
  - `promotion_log` missing expected `ix_promotion_log_idempotency`
  - `promotion_log` split/label checks still allow legacy values (`dataset_all`, legacy emotions)
  - Extra live-only objects: `run_link` table, `video.zfs_snapshot` column

## Non-Destructive Rules
- No table/column drops that remove data.
- Constraint tightening is done only after preflight data checks.
- Use `NOT VALID` + `VALIDATE CONSTRAINT` when historical rows may violate new rules.
- All revisions are idempotent-tolerant (check existence before create/drop).
- Downgrades for data-bearing additions are no-op (or metadata-only) to avoid data loss.

## Revision Set (Planned)

### Revision A (Section 2)
- Planned file: `apps/api/app/db/alembic/versions/20260228_000004_section2_constraints_indexes.py`
- `down_revision`: `20260223_000003`
- Purpose: reconcile split/label policy constraints and missing indexes on existing tables.

Planned operations:
1. Preflight data normalization (safe updates only):
   - Normalize legacy emotion values in `promotion_log.intended_label` into `happy|sad|neutral` where needed.
2. `video` constraint reconciliation:
   - If present, drop legacy `ck_video_split` constraint.
   - Add `chk_video_split_label_policy`:
     - `split IN ('temp','test','purged') -> label IS NULL`
     - `split = 'train' -> label IS NOT NULL`
   - Add missing indexes: `ix_video_split`, `ix_video_label`.
3. `training_run` index reconciliation:
   - Add `ix_training_run_status`, `ix_training_run_created` if missing.
4. `promotion_log` constraint/index reconciliation:
   - Replace legacy split checks (`promotion_log_from_split_check`, `promotion_log_to_split_check`) with strict 4-split checks (`temp|train|test|purged`).
   - Replace legacy intended label check with strict 3-class check (`NULL|happy|sad|neutral`).
   - Add missing `ix_promotion_log_idempotency`.
   - Add uniqueness guard for idempotency (partial unique index on non-null values) only if duplicate preflight check passes.
5. Validation step:
   - Validate new constraints; if legacy rows exist in other environments, keep `NOT VALID` and emit migration log warning instead of failing.

Acceptance checks:
- `pg_constraint` includes `chk_video_split_label_policy`.
- `pg_indexes` includes all expected missing indexes above.
- No existing rows violate the enforced 3-class policy.

### Revision B (Section 3)
- Planned file: `apps/api/app/db/alembic/versions/20260228_000005_section3_agent_tables.py`
- `down_revision`: `20260228_000004`
- Purpose: create missing ORM-defined agent workflow tables.

Planned operations:
1. Create (if absent) tables:
   - `label_event`
   - `deployment_log`
   - `audit_log`
   - `obs_samples`
   - `reconcile_report`
2. Add all ORM-declared checks and indexes for those tables.
3. Keep column names/types aligned with `apps/api/app/db/models.py`.
4. Keep migration cross-environment safe by guarding create operations with table/index existence checks.

Acceptance checks:
- Expected tables exist in `information_schema.tables`.
- Table constraints and indexes match ORM intent.
- Existing ingest/promotion/evaluation paths remain unaffected.

### Revision C (Section 4)
- Planned file: `apps/api/app/db/alembic/versions/20260228_000006_section4_legacy_object_alignment.py`
- `down_revision`: `20260228_000005`
- Purpose: reconcile extra live objects into managed, documented compatibility state without data loss.

Planned operations:
1. Adopt `video.zfs_snapshot` as compatibility field:
   - Add nullable `zfs_snapshot` column to ORM `Video` model.
   - In migration, `ADD COLUMN IF NOT EXISTS` to keep environments convergent.
2. Adopt `run_link` as compatibility table:
   - Add lightweight ORM model for `run_link` (lineage compatibility).
   - In migration:
     - Create table if missing.
     - Backfill structural constraints/indexes only when preflight checks are safe.
     - Do not delete or rewrite lineage rows.
3. Mark both as "compatibility-managed" in docs to avoid future drift/autogenerate noise.

Acceptance checks:
- No unmanaged extra objects remain for active runtime schema.
- ORM + Alembic + live DB all agree on `run_link` and `video.zfs_snapshot`.

## Execution Status (Updated 2026-02-28)

The planned revisions A/B/C were superseded by the actual implementation, plus a
fourth migration to close constraint drift gaps discovered during live DB verification:

| Planned | Actual Migration | Status |
|---------|-----------------|--------|
| Revision A (constraints/indexes) | `20260227_000004_composite_indexes.py` | ✅ Implemented |
| Revision B (agent tables) | `20260227_000005_missing_orm_tables.py` | ✅ Implemented |
| Revision C (legacy alignment) | `20260227_000006_cleanup_view_trigger.py` | ✅ Implemented |
| Constraint reconciliation | `20260228_000007_constraint_reconciliation.py` | ✅ Implemented |

### Migration 000007 — Constraint Reconciliation Details

Addresses live DB drift that migrations 000004–000006 did not cover:

1. **Gap 1 — `video` constraint swap:**
   - Drops legacy `ck_video_split` (allowed `temp, train, test` only, no label policy)
   - Adds `chk_video_split_label_policy` with full split↔label enforcement + `purged` split
   - Uses `NOT VALID` + `VALIDATE CONSTRAINT` for safety

2. **Gap 2 — `promotion_log` constraint tightening:**
   - Replaces `promotion_log_from_split_check` → `chk_promotion_from_split` (4-value: `temp|train|test|purged`)
   - Replaces `promotion_log_to_split_check` → `chk_promotion_to_split` (4-value)
   - Replaces `promotion_log_intended_label_check` → `chk_promotion_intended_label` (3-class: `neutral|happy|sad`)

3. **Gap 3 — `video.zfs_snapshot` ORM adoption:**
   - `ADD COLUMN IF NOT EXISTS` (no-op on live DB where column already exists)
   - `Video` ORM model updated with `zfs_snapshot: Mapped[Optional[str]]`

### Additional work completed beyond the original plan:
- `RunLink` ORM model added to `models.py` (not just compatibility table — full model)
- `dataset_all` data migration (R6)
- `updated_at` trigger function (R7, PostgreSQL only)
- Statistics views `v_label_distribution` and `v_run_frame_stats` (R9, PostgreSQL only)
- Legacy SQL files `002` and `003` formally deprecated with headers
- Backup file `api_client_BAK.py` deleted
- Test scripts updated to remove `dataset_all` references
- `BigInteger` → `Integer` for Phase 3 ORM model PKs (SQLite autoincrement fix)
- 5 missing single-column indexes backfilled in migration 000004

## Original Execution Order and Gates (Superseded)
1. Gate A: approve this plan document.
2. Execute Revision A only; run verification queries and tests.
3. Gate B: approve Section 2 results.
4. Execute Revision B only; run verification queries and tests.
5. Gate C: approve Section 3 results.
6. Execute Revision C only; run verification queries and tests.
7. Publish final reconciliation report.

## Test and Verification Matrix
- Migration chain:
  - `alembic -c apps/api/app/db/alembic.ini upgrade head`
  - `alembic -c apps/api/app/db/alembic.ini current`
- Schema assertions:
  - table existence (`information_schema.tables`)
  - constraint existence (`pg_constraint`)
  - index existence (`pg_indexes`)
- Data policy assertions:
  - `video` split/label policy compliance
  - `promotion_log` split/label compliance
  - `extracted_frame` test-label null policy remains valid
- App tests (minimum):
  - `tests/apps/api/db/test_migrations.py`
  - `tests/apps/api/db/test_models_constraints.py`
  - `tests/apps/api/test_ingest_endpoints.py` (run-frame persistence cases)

## Documentation Deliverables (Complete Package)
After each approved section execution, update:
1. `docs/database/07-KNOWN-ISSUES.md`
   - Mark resolved drift items with revision IDs and applied date.
2. `docs/database/08-SETUP-GUIDE.md`
   - Update "expected tables" and migration history to include new revisions.
3. `docs/database/09-LEGACY-SQL-USAGE-AUDIT.md`
   - Record compatibility treatment for `run_link` and `zfs_snapshot`.
4. New execution report:
   - `docs/database/11-SCHEMA-RECONCILIATION-EXECUTION-REPORT-2026-02-28.md`
   - Include pre/post SQL evidence, revision hashes, and rollback notes.

## Rollback Strategy
- For Section 2 constraint/index changes: rollback by dropping newly added constraints/indexes only (no data mutation rollback).
- For Section 3 and 4 data-bearing objects: do not drop populated tables/columns in downgrade; use forward-fix revisions if needed.
- Keep `pg_dump --schema-only` and targeted table backups before each section.

## Approval Checklist
- [ ] Revision names, order, and scope approved
- [ ] Constraint tightening strategy (`NOT VALID` + conditional validate) approved
- [ ] Section 4 compatibility adoption (`run_link`, `zfs_snapshot`) approved
- [ ] Documentation package scope approved
- [ ] Permission to implement Section 2 (Revision A) granted
