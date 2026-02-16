# Video Pipeline Review (Web App + Promotions)

Date: 2026-02-16
Reviewer: Codex (for Rusty)

## Scope

This review focuses on recent web-app and API changes affecting ingest, labeling, and promotion behavior across `temp → dataset_all/train/test`.

Recent commit series inspected:
- `d6f6539` (web app permissions + promotion fallback updates)
- `0c0a662` (comments in FastAPI app main)
- `5e05aed` (systemd configuration for FastAPI)

## Key Findings (Recent Changes)

1. **Web UI now has a safer promotion fallback path** in `apps/web/landing_page.py`:
   - Preferred path: `stage_to_dataset_all(video_id=UUID)`
   - Fallback path: legacy gateway promotion using filename clip identifier when UUID staging fails.

2. **Luma-generated videos are explicitly registered** via `register_local_video(...)` when ingest metadata is missing, reducing "unknown ID" promotion failures.

3. **Web API client resiliency improved**:
   - Retry decorator for transient failures.
   - TLS verification controls for local/self-signed setups.
   - Migration toward v1 endpoints (`/api/v1/media/list`, `/api/v1/ingest/register-local`, `/api/v1/promote/stage`).

4. **Policy/logic mismatch remains in orchestrator docs/workflow**:
   - Some n8n docs/workflows still describe 2-class logic (`happy/sad`) and older labels, while current DB + web flow are 3-class (`happy/sad/neutral`) with strict split-label policy.

## Pipeline Script Inventory

### A) Web UI scripts
- `apps/web/landing_page.py` — upload/generate/classify UI and promotion calls.
- `apps/web/api_client.py` — HTTP client for ingest/list/promote/stage/reject.
- `apps/web/pages/02_Label.py` — operator page for list + promote actions.

### B) API (FastAPI) scripts
- `apps/api/app/main.py` — router wiring, legacy endpoint toggle, startup services.
- `apps/api/app/routers/ingest.py` — pull/upload/register-local ingest endpoints.
- `apps/api/app/routers/media_v1.py` — v1 listing/metadata/thumbnail APIs.
- `apps/api/app/routers/promote.py` — v1 stage/sample/reset-manifest endpoints.
- `apps/api/app/services/promote_service.py` — core promotion/sampling orchestration.
- `apps/api/app/repositories/video_repository.py` — DB persistence and promotion logs.
- `apps/api/app/fs/media_mover.py` — atomic file move/copy + rollback.
- `apps/api/app/db/models.py` — split/label constraints and event log tables.

### C) Legacy compatibility scripts (still relevant to fallback behavior)
- `apps/api/routers/gateway.py` — `/api/promote` proxy enforcing API version + idempotency key.
- `apps/api/routers/media.py` — legacy `/api/media/promote` adapter and filesystem move path.

### D) n8n workflow scripts (agent layer)
- `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`

(plus their parameter docs in `detail_parameters_by_function/*.md`.)

## Control Flow Summary (How It Works End-to-End)

1. **Ingest**
   - Upload or generation creates a video in temp storage.
   - API stores metadata and hash; DB row uses `split='temp'`, `label=NULL`.

2. **Labeling / Classification**
   - Web UI gets/ensures `video_id`.
   - On submit, UI tries **staging to `dataset_all`** with explicit label.
   - If staging endpoint cannot be used, UI falls back to legacy promote path.

3. **Promotion / Sampling**
   - `stage_to_dataset_all` moves `temp/*` to `dataset_all/*`, writes label + promotion log.
   - `sample_split` copies from `dataset_all` to `train/{run_id}` or `test/{run_id}`.
   - Test samples are forced unlabeled (`label=NULL`), train remains labeled.

4. **Reconciliation / Training readiness**
   - Reconciler checks filesystem-vs-DB drift.
   - Orchestrator checks class readiness and triggers train/evaluate/deploy stages.

## Risks and Recommendations

1. **Legacy and v1 paths diverge**
   - Risk: behavior differences between `stage_to_dataset_all` and legacy `/api/media/promote`.
   - Recommendation: phase out legacy flow after hardening `register_local_video + stage` path.

2. **n8n docs/workflow label sets are stale in places**
   - Risk: operator confusion and incorrect assumptions (2-class vs 3-class).
   - Recommendation: align all `detail_parameters_by_function` docs and SQL examples with 3-class policy.

3. **Dual source of truth for listing (filesystem vs DB)**
   - Risk: race/drift visibility differences.
   - Recommendation: prioritize DB-backed listing for any operation requiring promotion eligibility.

4. **Fallback clip-id promotion can hide ID mapping issues**
   - Risk: accidental promotion with weak identifiers.
   - Recommendation: keep fallback temporary; enforce UUID-only promotions once ingest registration is stable.

