---
title: "Promotion Pipeline Audit & Fixes"
date: 2026-02-28
status: implemented
category: audit
affects:
  - apps/api/routers/media.py
  - apps/api/routers/gateway.py
  - apps/api/app/main.py
  - apps/api/app/db/models.py
  - apps/api/app/routers/training_control.py
  - apps/api/app/routers/websocket_cues.py
  - apps/api/app/routers/ingest.py
  - apps/api/app/services/promote_service.py
  - apps/api/app/repositories/video_repository.py
  - trainer/prepare_dataset.py
  - src/media_mover/main.py
---

# ADR-008: Promotion Pipeline Audit & Fixes

## Context

A comprehensive line-by-line audit was conducted on the entire promotion pipeline:
media.py promote handler, PromoteService, FileMover, VideoRepository,
DatasetPreparer, training_control router, gateway proxy, and DB models.

The audit identified 17 issues across 4 severity levels.

## Fixes Implemented (2026-02-28)

### HIGH Priority

1. **FIX #10 — media.py now uses FileMover for atomic moves + Prometheus metrics.**
   The live promote endpoint previously used `shutil.move()` (non-atomic, no fsync)
   and had zero observability. Now uses `FileMover.stage_to_train()` for train
   promotions (atomic via `os.replace` + fsync) and emits
   `PROMOTION_OPERATION_COUNTER`, `PROMOTION_OPERATION_DURATION`, and
   `PROMOTION_FILESYSTEM_FAILURES` metrics.

2. **FIX #4 — Idempotency enforcement added to promote handler.**
   The handler now extracts `Idempotency-Key` from request headers, checks
   `PromotionLog` for an existing entry with that key, and returns a cached
   replay if found. New promotions store the key in the `PromotionLog` row.

3. **FIX #3 — File-before-commit trade-off documented + reconciler logging.**
   Added structured `media_mover_promote_pending` / `media_mover_promote_committed`
   log pairs that the Reconciler Agent (Agent 4) can use to detect incomplete
   promotions where the file was moved but the DB commit didn't complete.

4. **FIX #12 — DatasetPreparer guards against overwriting completed runs.**
   `_extract_run_frames()` now checks for `train_ds_` / `valid_ds_` subdirectories
   before `rmtree()`. If found, raises `ValueError` directing the caller to use
   `prune_run_artifacts()` first.

### MEDIUM Priority

5. **FIX #17 — Hardcoded paths removed from training_control.py.**
   `_DEFAULT_CHECKPOINT_DIR`, `_AFFECTNET_TEST_DATASET`, `_DATA_ROOT`, `_RUN_DIR`
   replaced with helper functions that derive paths from `AppConfig.videos_root`.

6. **FIX #15 — Centralized run_id generation.**
   `training_control._next_run_id()` now delegates to
   `DatasetPreparer.resolve_run_id(None)` to eliminate duplicate scanning logic.

7. **FIX #9 — httpx.AsyncClient lifecycle managed in app lifespan.**
   Module-level `client` in gateway.py replaced with `get_http_client(request)`
   that reads from `app.state.http_client`. Client is created/closed in
   `main.py` lifespan context manager.

### LOW Priority

8. **FIX #5 — All `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`.**
   Affected files: models.py (6 column defaults via `_utcnow()` helper),
   media.py, ingest.py, websocket_cues.py.

9. **FIX #6 — Filesystem glob limited to known video extensions.**
   `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` filter applied in media.py fallback lookup.

10. **FIX #8 — Legacy path detection uses exact `==` match.**
    Replaced fragile `endswith()` chain with `request.url.path == LEGACY_PROMOTE_PATH`.

11. **FIX #7 — Auto-registration logs warning for reconciler.**
    When a video file is found on disk but not in the DB, a `WARNING`-level
    structured log is emitted noting that ingest agent metadata extraction
    was bypassed.

12. **FIX #14 — Dataset hash trade-off documented in DatasetPreparer.**
    `calculate_dataset_hash()` docstring now explains the path+size vs content
    hashing speed/accuracy trade-off.

### INFO

13. **FIX #1,11 — Dead code annotated.**
    `PromoteService._balanced_sample()` and
    `VideoRepository.fetch_train_pool_for_sampling()` marked as dead code.

14. **FIX stub — src/media_mover/main.py marked as non-production.**
    Prominent docstring header added explaining this is a stub with incorrect
    destination path logic.

## Consequences

- Promotion operations are now atomic (fsync) and observable (Prometheus).
- Idempotent replays prevent duplicate promotions from gateway retries.
- Reconciler Agent can detect incomplete promotions via structured log pairs.
- Training control is portable across environments (no hardcoded paths).
- Python 3.12+ deprecation warnings eliminated.
- No schema migrations required (all changes are application-level).

## Risks

- `FileMover.stage_to_train()` expects source files under `temp/` prefix;
  promotions from other splits would need the test-split `os.replace` fallback.
- The lazy import of `DatasetPreparer` in `_next_run_id()` could fail if
  OpenCV is not installed (cv2 is a transitive dependency).
