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
