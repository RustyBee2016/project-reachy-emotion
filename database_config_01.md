# Database Configuration Deep Dive (Reachy_Local_08.4.2)

## 1) Purpose and Role of the Database

The PostgreSQL database is the system of record for:

- Video metadata and lifecycle state (`temp`, `dataset_all`, `train`, `test`, `purged`)
- Labeling state and policy enforcement
- Promotion/audit history
- Training/evaluation/deployment run metadata
- Agent telemetry and reconciliation records

In short: filesystem stores the actual media bytes; PostgreSQL stores all traceable state and relationships needed to run and audit the pipeline safely.

---

## 2) Configuration Source of Truth

## Runtime config (application)

Primary config is in:
- `apps/api/app/config.py`

Key DB setting:
- `REACHY_DATABASE_URL` (async SQLAlchemy URL)
- Default fallback in code:
  `postgresql+asyncpg://reachy_dev:tweetwd4959@localhost:5432/reachy_emotion`

Important related runtime settings in the same config:
- API port default: `8083`
- Videos root default: `/mnt/videos`
- Required storage subdirectories: `temp`, `dataset_all`, `train`, `test`, `thumbs`, `manifests`

Validation behavior in `AppConfig.validate()`:
- checks DB URL parseability
- validates ports
- validates/creates required storage directories

## Schema/migration source of truth

Active schema path:
- SQLAlchemy models: `apps/api/app/db/models.py`
- Alembic migration: `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`

Legacy SQL files under root `alembic/versions/*.sql` are historical references and should not be treated as the primary migration path.

---

## 3) Enumerations and Domain Constraints

Defined in `apps/api/app/db/enums.py`:

1. `SplitEnum`:
   - `temp`, `dataset_all`, `train`, `test`, `purged`

2. `EmotionEnum`:
   - `neutral`, `happy`, `sad`

3. `SelectionTargetEnum`:
   - `train`, `test`

These enums are configured as `native_enum=False` with check constraints, which keeps behavior explicit and portable.

---

## 4) Core Schema (Tables, Keys, Constraints)

## A) `video`

Purpose:
- Master table for each video and current lifecycle state.

Important columns:
- `video_id` (PK, UUID string)
- `file_path`
- `split`
- `label` (nullable depending on split)
- media metadata (`duration_sec`, `fps`, `width`, `height`, `size_bytes`, `sha256`)
- `metadata` JSON (`extra_data` in ORM)
- soft-delete marker `deleted_at`
- timestamps via mixin (`created_at`, `updated_at`)

Critical constraints:
1. Uniqueness: `uq_video_sha256_size` on (`sha256`, `size_bytes`)
2. Split-label policy: `chk_video_split_label_policy`
   - `temp/test/purged` => `label IS NULL`
   - `dataset_all/train` => `label IS NOT NULL`

Indexes:
- `ix_video_split`
- `ix_video_label`

This table is the center of the promotion state machine.

## B) `training_run`

Purpose:
- Tracks dataset sampling/training run metadata.

Important columns:
- `run_id` (PK)
- `strategy`
- `train_fraction`, `test_fraction`
- `status` (`pending/sampling/training/evaluating/completed/failed/cancelled`)
- `dataset_hash`, `mlflow_run_id`, model artifact paths, metrics/config JSON
- error and timestamps

Constraints:
- `chk_train_fraction_range`
- `chk_valid_fractions`
- `chk_training_status`

Indexes:
- `ix_training_run_status`
- `ix_training_run_created`

## C) `training_selection`

Purpose:
- Bridge table mapping videos selected into a run and target split.

Composite PK:
- (`run_id`, `video_id`, `target_split`)

FKs:
- `run_id -> training_run.run_id` (CASCADE)
- `video_id -> video.video_id` (CASCADE)

`target_split` enum values:
- `train`, `test`

## D) `promotion_log`

Purpose:
- Auditable record of staging/sampling/promotions.

Important columns:
- `promotion_id` (PK)
- `video_id` FK
- `from_split`, `to_split`
- `intended_label`
- `actor`, `success`, `dry_run`
- `idempotency_key` (unique)
- `correlation_id`, `error_message`, metadata JSON
- timestamps

Indexes:
- `ix_promotion_log_video_time`
- `ix_promotion_log_idempotency`

This table is crucial for idempotency, replay safety, and post-mortem analysis.

---

## 5) Agent/Operations Tables (Phase 3+)

## `label_event`
Audit table for human labeling actions.
- action constrained to: `label_only`, `promote_train`, `promote_test`, `discard`, `relabel`
- includes optional `idempotency_key` and `correlation_id`

## `deployment_log`
Tracks model deployment lifecycle (shadow/canary/rollout) and Gate B metrics.
- stage/status check constraints
- stores FPS/latency/GPU memory fields

## `audit_log`
General privacy/compliance operations log.
- action/entity/operator metadata
- timestamped with correlation support

## `obs_samples`
Time-series metric storage for observability.
- source + metric + numeric value + labels JSON

## `reconcile_report`
Filesystem/database reconciliation outcomes.
- drift counts, fix flags, details JSON, duration

---

## 6) ORM Relationships (How Tables Connect)

In `models.py`:

- `Video` has many:
  - `PromotionLog`
  - `TrainingSelection`
  - `LabelEvent`

- `TrainingRun` has many:
  - `TrainingSelection`

- `TrainingSelection` belongs to:
  - one `TrainingRun`
  - one `Video`

These relationships are configured with cascade rules to keep child records consistent when parent entities are deleted.

---

## 7) Data Flow Mapped to DB Writes

## Stage flow (`temp -> dataset_all`)

Triggered via promote service/repository:

1. fetch candidate videos by UUID
2. verify eligibility (`split='temp'`)
3. move file on disk
4. DB update on `video`:
   - set `split='dataset_all'`
   - set `label` to chosen class
   - update `file_path`
5. write `promotion_log`

## Sampling flow (`dataset_all -> train/test`)

1. fetch candidates from `dataset_all`
2. exclude already-selected IDs for same run/split
3. choose sample
4. update `video` split/path (+ label nulling for `test`)
5. insert `training_selection`
6. insert `promotion_log`

Special rule enforced in repository:
- when target split is `test`, resulting `video.label` is set to `NULL`.

---

## 8) Policy Enforcement Model

Policy is enforced in layers:

1. **Application/service validation**
   - checks IDs, labels, transitions

2. **Repository logic**
   - applies deterministic split/label update behavior

3. **Database constraints**
   - hard checks (e.g., split-label policy) prevent invalid terminal states even if app logic regresses

This layered approach is a strong design for safety and auditability.

---

## 9) Important Consistency Notes and Risks

## A) Enum drift risk

Current ORM enum (`EmotionEnum`) is 3-class (`neutral/happy/sad`), but the initial Alembic migration file includes additional legacy labels (`angry`, `surprise`, `fearful`) in `emotion_enum`.

Why this matters:
- environments built at different times/pathways can drift semantically
- workflows may accidentally accept labels not intended for current model

Recommendation:
- align migration enum with model enum (or add a corrective migration)
- enforce CI check for migration-head/schema consistency

## B) Migration-path ambiguity

Root SQL migration files and app Alembic path coexist.

Recommendation:
- document and enforce app Alembic path as the only supported deployment migration mechanism.

## C) Secrets hygiene

Default DB URL in code contains inline credentials fallback.

Recommendation:
- production should always inject `REACHY_DATABASE_URL` from secrets manager/env and avoid fallback credentials.

---

## 10) Practical Verification Checklist

When validating a deployment, confirm:

1. Connection
- app can connect via `REACHY_DATABASE_URL`

2. Schema presence
- core tables exist: `video`, `training_run`, `training_selection`, `promotion_log`
- operational tables exist: `label_event`, `deployment_log`, `audit_log`, `obs_samples`, `reconcile_report`

3. Constraint behavior
- inserting `split='temp'` with non-null label should fail
- inserting `split='dataset_all'` with null label should fail

4. Pipeline correctness
- stage writes update `video` + `promotion_log`
- sample writes update `video` + `training_selection` + `promotion_log`
- test split rows end with `label=NULL`

5. Idempotency observability
- duplicate `idempotency_key` should be prevented where unique constraints apply

---

## 11) Summary

The database configuration is well-structured for a staged media-promotion pipeline with strong auditability:

- clear lifecycle state modeling in `video`
- explicit training run and selection lineage
- robust promotion logging and idempotency hooks
- additional operations/agent telemetry tables

The main improvement area is not schema breadth, but **schema consistency governance**:

- align enum definitions across models and migrations
- enforce one migration source of truth
- harden secrets handling for production deployments.
