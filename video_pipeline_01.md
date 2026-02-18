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

### B. Human Labeling / Promotion

1. User labels clip as one of: `happy`, `sad`, `neutral`.
2. Current promotion path is direct classify+promote:
   - `POST /api/promote` (gateway compatibility path)
3. Service behavior (`/api/media/promote` compatibility route):
   - Validates UUID IDs and 3-class label
   - Moves file `temp/* -> train/<label>/*`
   - Updates DB split/label and writes promotion log

### C. Run-Specific Frame Extraction for Training

1. Orchestrator calls `DatasetPreparer.prepare_training_dataset(run_id=...)`.
2. For each source video in `train/{happy|sad|neutral}/*.mp4`, 10 random frames are extracted to:
   - `train/happy/<run_id>/`
   - `train/sad/<run_id>/`
   - `train/neutral/<run_id>/`
3. Frames are then consolidated to a single run dataset:
   - `train/<run_id>/<label>/*.jpg`
4. Run manifests are generated as:
   - `manifests/<run_id>_train.jsonl`

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

- Some docs still described an old staged-corpus policy after direct promote changes.
- Training docs needed explicit run-specific frame extraction paths.

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

## Gap 5: Label/Video Management pages used legacy promotion assumptions (fixed)

- Pages assumed direct promote behavior and had limited staging semantics.

Resolution applied:
- `apps/web/pages/02_Label.py` now promotes temp clips directly to `train/<label>`.
- `apps/web/pages/05_Video_Management.py` now batch-promotes temp clips directly to `train/<label>`.

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

## 6) Promotion + Frame Extraction Process Deep Dive

### Direct classify/promotion operation (`/api/promote`)

Inputs:
- `video_id` (UUID)
- `dest_split="train"`
- `label` (`happy|sad|neutral`)
- `dry_run`

Execution path:
1. Validate UUID and 3-class label.
2. Fetch `video` row for `split='temp'`.
3. Move filesystem object to `train/<label>/`.
4. Update `video` row (`split='train'`, label set, new path).
5. Insert `promotion_log` record.

Failure handling:
- File move errors trigger rollback/compensation handling and DB rollback.

### Run frame extraction operation (`DatasetPreparer.prepare_training_dataset`)

Inputs:
- `run_id` (e.g., `epoch_01`)
- `seed` (optional, deterministic fallback from run_id)

Execution path:
1. Scan source videos from `train/happy/*.mp4`, `train/sad/*.mp4`, `train/neutral/*.mp4`.
2. Randomly select 10 frames per source video.
3. Write frames into label/run folders:
   - `train/happy/<run_id>/`, `train/sad/<run_id>/`, `train/neutral/<run_id>/`
4. Build consolidated run dataset:
   - `train/<run_id>/<label>/*.jpg`
5. Emit run manifest:
   - `manifests/<run_id>_train.jsonl`
6. Compute run-specific `dataset_hash` from consolidated frame files.

---

## 7) Recommended Next Changes (Priority Order)

1. **P0: Keep a single schema migration path**
   - Operationally deprecate root SQL migration files.
   - Add explicit startup or CI check to confirm app Alembic head is applied.

2. **P0: Standardize docs + runbooks on direct promote + frame extraction flow**
   - Remove remaining legacy staged-corpus and sampling language where no longer true.
   - Make `train/<label>/<run_id>` and `train/<run_id>/<label>` conventions explicit.

3. **P1: Add integration tests for frame extraction reliability**
   - Cases: unreadable videos, low-frame videos, deterministic output with same seed, manifest integrity.

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
- `trainer/prepare_dataset.py`
- `trainer/fer_finetune/dataset.py`
- `tests/test_dataset_prep.py`
- `tests/test_dataset_preparation.py`
- `tests/test_training_pipeline.py`
- `README.md`
- `memory-bank/requirements.md`
- `video_pipeline_01.md` (this document)

---

## 9) Validation Summary

- Submit Classification now promotes directly to `train/<label>`.
- Fine-tuning prep now extracts 10 random frames per video into run-scoped label folders and consolidated run datasets.
- Training manifests are now frame-based (`<run_id>_train.jsonl`) and include source-video references.
- Database architecture remains viable; migration discipline and enum alignment are still recommended follow-ups.
