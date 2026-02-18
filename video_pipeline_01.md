# Video Pipeline Analysis (2026-02-18)

## 1) Scope

This document summarizes the current end-to-end video pipeline and recent updates across:

- Fine-tuning tutorials (`docs/tutorials/fine_tuning/`)
- n8n orchestration (`n8n/workflows/` and update guide)
- Web application workflows (`apps/web/` and `docs/tutorials/webapp/`)
- Prior review (`docs/video_pipeline_review_2026-02-16.md`)

It also identifies code-level gaps, database readiness, and concrete recommendations.

---

## 2) Current End-to-End Pipeline (Observed)

### A. Ingest / Generation

1. User uploads or generates a clip in Streamlit (`apps/web/landing_page.py`).
2. Clip is expected to be persisted under `videos/temp/` and registered in DB (`video` table with `split='temp'`, `label=NULL`).
3. Ingest endpoints support:
   - `/api/v1/ingest/upload`
   - `/api/v1/ingest/register-local`
4. Metadata is captured (sha256, size, ffprobe fields), with thumbnail generation.

### B. Human Labeling / Staging

1. User labels clip as one of: `happy`, `sad`, `neutral`.
2. Preferred promotion path is v1 stage endpoint:
   - `POST /api/v1/promote/stage`
3. Service behavior (`PromoteService.stage_to_dataset_all`):
   - Validates UUID IDs and 3-class label
   - Moves file `temp/* -> dataset_all/*` atomically via file mover
   - Updates DB split/label and writes promotion log

### C. Sampling for Train/Test

1. Orchestrator calls `POST /api/v1/promote/sample` with `run_id`, `target_split`, `sample_fraction`.
2. Service copies files from `dataset_all` into `train/{run_id}/...` or `test/{run_id}/...`.
3. DB side records `training_selection` rows and promotion logs.

### D. Manifest / Training / Eval / Deploy

1. Manifest rebuild endpoint (`/api/v1/ingest/manifest/rebuild`) emits JSONL manifests from DB rows.
2. Training orchestrator workflow triggers EfficientNet-B0 fine-tuning with 3-class config.
3. Evaluation checks Gate A metrics.
4. Deployment workflow promotes to Jetson path with staged rollout gates.

---

## 3) Recent Updates Captured

## Fine-tuning updates

- Tutorials are now centered on EfficientNet-B0 HSEmotion and 3-class flow.
- Key references use `efficientnet_b0_emotion_3cls.yaml` and Gate A thresholds.

## n8n updates

- `05_training_orchestrator_efficientnet.json` and `06_evaluation_agent_efficientnet.json` are already neutral-aware.
- Gaps were found and fixed in:
  - `02_labeling_agent.json`
  - `10_ml_pipeline_orchestrator.json`

## Web app updates

- Landing page now attempts safer registration and UUID resolution before promotion.
- Legacy fallback remains but now blocks non-UUID promotion attempts.

## Prior review alignment

- Findings from `docs/video_pipeline_review_2026-02-16.md` are still valid regarding legacy/v1 drift and UUID mapping risks.

---

## 4) Gaps Identified (Logic + Code)

## Gap 1: Legacy/v1 endpoint drift in tooling and docs

- Some docs and pages still describe direct `temp -> train/test` promotion.
- Current policy is staged corpus first (`temp -> dataset_all`), then sampled train/test.

Impact:
- Operator confusion.
- Inconsistent behavior between screens and automated workflows.

## Gap 2: Labeling workflow in n8n used non-3-class allowance (fixed)

- Label validator allowed extra classes (`angry`, `surprise`, `fearful`).
- Class-balance output did not include `neutral`.

Impact:
- Policy drift vs current DB constraints and training assumptions.

Resolution applied:
- Restricted to `happy/sad/neutral` and neutral-aware class-balance in `02_labeling_agent.json`.

## Gap 3: Pipeline orchestrator dataset readiness was 2-class (fixed)

- Orchestrator queried only happy/sad stats.
- Readiness/balance and dataset hash ignored neutral.

Impact:
- False "ready" condition for underrepresented neutral class.

Resolution applied:
- Neutral-aware SQL and logic in `10_ml_pipeline_orchestrator.json`.

## Gap 4: Landing-page submit classification could report success on weak fallback IDs (fixed)

- Promotion fallback could run with non-UUID identifiers under some paths.

Impact:
- User sees success while data may not have been correctly staged.

Resolution applied:
- Stronger UUID resolution + register-local fallback, and explicit non-UUID fallback rejection in `apps/web/landing_page.py`.

## Gap 5: Label/Video Management pages used legacy promotion assumptions (partially fixed)

- Pages assumed direct promote behavior and had limited staging semantics.

Resolution applied:
- `apps/web/pages/02_Label.py` now stages temp clips to dataset_all.
- `apps/web/pages/05_Video_Management.py` now stages temp clips and skips non-UUID IDs safely.

## Gap 6: Database migration split-brain (legacy SQL vs Alembic)

- Root `alembic/versions/*.sql` are legacy and contain stale enum values / schema variants.
- Active app migration is `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`.

Impact:
- Risk of deploying divergent schemas depending on operator path.

Recommendation:
- Enforce a single migration path (app Alembic only), and clearly mark root SQL as archival.

---

## 5) Database Configuration Assessment

## What is configured correctly

- SQLAlchemy models encode core policy constraints:
  - split-label policy via `chk_video_split_label_policy`
  - uniqueness on `(sha256, size_bytes)`
- Core tables exist in code model for:
  - `video`, `training_run`, `training_selection`, `promotion_log`
  - plus audit/agent tables (`label_event`, `deployment_log`, etc.)
- App config points to PostgreSQL via async URL and wires session dependencies.

## Risks / caveats

1. **Enum drift risk**:
   - App enum in `apps/api/app/db/enums.py` is 3-class.
   - Initial Alembic migration includes legacy 6-class emotion enum values.

2. **Migration source ambiguity**:
   - Root SQL files may be run accidentally and do not represent current authoritative path.

3. **Credentials hygiene**:
   - Default DB URL in app config includes inline credential placeholder; production should rely on environment-only secret injection.

Conclusion:
- The database model design is broadly adequate for pipeline behavior, but migration discipline and enum alignment should be tightened to avoid environment drift.

---

## 6) Promotion Process Deep Dive

### Stage operation (`/api/v1/promote/stage`)

Inputs:
- `video_ids` (UUID list)
- `label` (happy/sad/neutral)
- `dry_run`

Execution path:
1. Validate UUID list and label.
2. Fetch matching `video` rows.
3. Accept only rows with `split='temp'`.
4. Move filesystem object to `dataset_all` atomically.
5. Update `video` row (`split='dataset_all'`, label set, new path).
6. Insert `promotion_log` record.
7. Schedule manifest rebuild.

Failure handling:
- File move errors trigger rollback of moved files and DB transaction rollback.

### Sample operation (`/api/v1/promote/sample`)

Inputs:
- `run_id`, `target_split` (train/test), `sample_fraction`, `strategy`, optional `seed`, `dry_run`

Execution path:
1. Validate request fields.
2. Load dataset_all candidates excluding already-selected run/split IDs.
3. Balanced random sample across labels.
4. Copy files into run-scoped train/test destinations.
5. Persist training selections and promotion logs.
6. Schedule manifest rebuild.

Policy behavior:
- `target_split='test'` rows are persisted with `label=NULL`.

---

## 7) Recommended Next Changes (Priority Order)

1. **P0: Keep a single schema migration path**
   - Operationally deprecate root SQL migration files.
   - Add explicit startup or CI check to confirm app Alembic head is applied.

2. **P0: Standardize all web pages on staged flow**
   - Remove remaining direct `temp -> train/test` UX language.
   - Make stage + sample intent explicit in operator interfaces.

3. **P1: Add integration tests for promotion reliability**
   - Cases: missing UUID, register-local fallback, stage dry-run/execute, sample dry-run/execute.

4. **P1: Audit docs for stale ports and endpoint aliases**
   - Ensure all references use current API base/ports and v1 endpoints first.

5. **P2: Consider stronger runtime guardrails**
   - Reject non-UUID promotions centrally at API gateway compatibility endpoints.
   - Add telemetry counters for fallback usage to monitor retirement progress.

---

## 8) Files Updated in This Pass

- `apps/web/landing_page.py`
- `apps/web/pages/02_Label.py`
- `apps/web/pages/05_Video_Management.py`
- `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`
- `README.md`
- `AGENTS.md`
- `video_pipeline_01.md` (this document)

---

## 9) Validation Summary

- Submit Classification reliability issue on landing page has been addressed with stronger UUID resolution + registration fallback.
- Similar promotion-path issues were addressed in Label and Video Management pages.
- n8n orchestration drift from 2-class to 3-class has been corrected in key workflows.
- Database architecture is fundamentally viable, but migration source-of-truth and enum consistency need tighter operational controls.
