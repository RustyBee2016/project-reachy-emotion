# Legacy SQL Usage Audit (001/002/003)

## Goal
Determine whether the legacy SQL scripts below are still used directly in database configuration:

- `alembic/versions/001_phase1_schema.sql` 
- `alembic/versions/002_stored_procedures.sql` 
- `alembic/versions/003_missing_tables.sql` 

## Result Summary
- **Runtime app migration path:** Uses Alembic Python migrations from `apps/api/app/db/alembic/versions/`.
- **Direct SQL file execution in app code/config scripts:** **Not found**.
- **Direct SQL file usage in docs and legacy tests:** **Found**.

## Evidence
1. Active app migration path is Alembic (Python revisions).
2. Repo-wide searches found no direct runtime automation invoking `001/002/003`.
3. Legacy setup docs and legacy DB tests still reference SQL script-based setup and SQL-defined functions.

## Operational Interpretation
You can state with confidence that the application runtime path does not directly execute `001/002/003`.

You cannot state that the repository has fully removed direct usage, because documentation and legacy test paths still reference and/or depend on behavior created by those scripts.

## Formal Deprecation (2026-02-27)

All three legacy SQL files now carry a `DEPRECATED` header:

| File | Status | Superseded By |
|------|--------|---------------|
| `001_phase1_schema.sql` | DEPRECATED (header added previously) | `202510280000_initial_schema.py` |
| `002_stored_procedures.sql` | DEPRECATED (header added 2026-02-27) | Python services; stored procedures reference deprecated `dataset_all` split |
| `003_missing_tables.sql` | DEPRECATED (header added 2026-02-27) | `20260227_000005_missing_orm_tables.py` |

All tables previously only created by `003_missing_tables.sql` are now managed by Alembic
migration `20260227_000005`. The `dataset_all` split referenced in `002_stored_procedures.sql`
has been removed from the active schema. Test scripts (`test_all_endpoints.sh`,
`manual_validation.sh`) were updated to remove `dataset_all` references.

The backup file `apps/web/api_client_BAK.py` (which contained `stage_to_dataset_all()`) was deleted.
