# Database Curriculum Rewrite — Task Checklist

**Goal**: Rewrite all tutorial files so they reference the actual source-of-truth files  
(`models.py`, `enums.py`, `202510280000_initial_schema.py`) instead of the deprecated  
legacy SQL files (`001_phase1_schema.sql`, `002_stored_procedures.sql`, `003_missing_tables.sql`).

**Audience**: Junior engineers implementing the database. They must understand the  
reasoning and logic behind the redesigned schema.

---

## Phase 1: Heavy Rewrites

- [x] **1. Rewrite `03-MODULE-REACHY-SCHEMA.md`**
  - [x] 1a. Change "12 tables" → 9 ORM-managed tables (explain 3 legacy-only tables)
  - [x] 1b. Replace Source Files Reference table (point to `models.py`, `enums.py`, migration)
  - [x] 1c. Add "Source of Truth" explainer section (how models.py, enums.py, and migration work together)
  - [x] 1d. Rewrite `video` table section from `models.py` (correct types: `String(36)`, `Float`, `SplitEnum`, etc.)
  - [x] 1e. Remove Known Issue #3 and #4 callouts (resolved by Alembic-only path)
  - [x] 1f. Rewrite `training_run` table section from `models.py`
  - [x] 1g. Rewrite `training_selection` table section from `models.py` (composite PK, no BIGSERIAL)
  - [x] 1h. Remove Known Issue #11 callout (resolved by composite PK in models.py)
  - [x] 1i. Rewrite `promotion_log` table section from `models.py`
  - [x] 1j. Rewrite `label_event` table section from `models.py`
  - [x] 1k. Rewrite User & Events section — clarify `user_session`, `generation_request`, `emotion_event` are legacy-only
  - [x] 1l. Rewrite Operations tables (`deployment_log`, `audit_log`, `obs_samples`, `reconcile_report`) from `models.py`
  - [x] 1m. Update relationship diagram to reflect 9 ORM tables
  - [x] 1n. Update Knowledge Check, Hands-On Exercise, and Summary sections

## Phase 2: Moderate Rewrites

- [x] **2. Rewrite `01-MODULE-DATABASE-FUNDAMENTALS.md`**
  - [x] 2a. Replace `001_phase1_schema.sql` source references with `models.py` / migration
  - [x] 2b. Rewrite `CREATE TABLE video` example to match actual schema
  - [x] 2c. Update `training_selection` and constraint examples

- [x] **3. Rewrite `02-MODULE-POSTGRESQL-ESSENTIALS.md`**
  - [x] 3a. Replace `psql -f 001_phase1_schema.sql` with Alembic migration approach
  - [x] 3b. ENUM section already correct (no changes needed)
  - [x] 3c. Update JSONB, NUMERIC, and index references to point to `models.py` / migration

- [x] **4. Rewrite `05-MODULE-SQLALCHEMY-ORM.md`**
  - [x] 4a. Fix `TrainingRun.seed` nullability (`nullable=True`, not `False`)
  - [x] 4b. Tighten "Legacy-Only Tables" section

## Phase 3: Minor Rewrites

- [x] **5. Rewrite `08-MODULE-TROUBLESHOOTING.md`**
  - [x] 5a. Change "12 tables" → 9 ORM-managed tables
  - [x] 5b. Update enum troubleshooting to reflect CHECK constraints (not native ENUMs)

- [x] **6. Rewrite `09-HANDS-ON-EXERCISES.md`**
  - [x] 6a. Fix Lab 2 exercise 2.1 (`enum_range` → CHECK constraint catalog query)
  - [x] 6b. Fix Lab 1 and Lab 2 setup INSERTs (missing required `sha256` and `video_id` columns)

## Phase 4: No Changes Needed (Verified)

- [x] `00-CURRICULUM-OVERVIEW.md` — already references correct source files
- [x] `04-MODULE-STORED-PROCEDURES.md` — already has legacy-path architecture note
- [x] `06-MODULE-API-INTEGRATION.md` — already references Python source files
- [x] `07-MODULE-MIGRATIONS-DEVOPS.md` — already Alembic-focused
