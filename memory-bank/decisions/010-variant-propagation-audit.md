---
title: Variant Propagation Audit — End-to-End Model Variant Tracking
kind: decision
owners: [RussellBray]
related: [apps/web/api_client.py, apps/api/app/routers/training_control.py, trainer/run_efficientnet_pipeline.py, apps/web/pages/06_Dashboard.py]
created: 2026-03-06
updated: 2026-03-06
status: active
---

# Variant Propagation Audit — End-to-End Model Variant Tracking

## Context

After introducing `variant` as an explicit launch parameter (variant_1 for Train page,
variant_2 for Fine-Tune page), a full codebase audit was performed to identify gaps
in variant propagation across the UI → API → runner → dashboard → observability chain.

## Gaps Found and Fixed

### GAP 1 (High): `TrainingLaunchResponse` missing `variant` field
**File:** `apps/api/app/routers/training_control.py`
**Fix:** Added `variant: str` to `TrainingLaunchResponse` and included it in the
response construction. Callers now get confirmation of which variant was launched.

### GAP 2 (High): Variant 1 placeholders missing `model_variant` field
**File:** `apps/web/pages/06_Dashboard.py`
**Fix:** Changed bare alias assignments (`VARIANT_1_*_RESULTS = *_PLACEHOLDER`)
to explicit spread dicts with `"model_variant": "variant_1"` added, matching Variant 2
placeholders for consistency.

### GAP 3 (Medium): Dashboard `_render_run_dashboard` didn't display variant
**File:** `apps/web/pages/06_Dashboard.py`
**Fix:** Added `model_variant` display in the run header line next to run ID.

### GAP 4 (Medium): Contract payloads (`_emit_*`) missing variant context
**File:** `trainer/run_efficientnet_pipeline.py`
**Fix:** Added `variant` and `run_type` parameters (with backward-compatible defaults)
to all four `_emit_*` functions. Propagated `args.variant` and `args.run_type` to all
7 call sites in `main()`. Observability layer (Agent 9) can now distinguish variants.

### GAP 5 (Medium): Log filename collision across variants
**File:** `apps/api/app/routers/training_control.py`
**Fix:** Changed log filename from `{run_id}_{mode}.log` to `{variant}_{run_id}_{mode}.log`.
Updated `get_training_log()` in `api_client.py` to match.

### GAP 6 (Low): Dashboard placeholder confusion matrices were 2x2 (binary)
**File:** `apps/web/pages/06_Dashboard.py`
**Fix:** Updated all three placeholders to 3×3 matrices and added `f1_class_2`/`f1_neutral`
metrics, matching the 3-class model (happy, sad, neutral).

## Tests Added

- `test_emit_contract_payloads_include_variant_context` — Verifies all `_emit_*`
  functions propagate variant and run_type into payloads.
- Existing `test_emit_training_completed_posts_gate_a_metrics` — Extended with
  assertions for `variant` and `run_type` fields in metrics.
- All 9 tests pass.

## Consequences

- Variant is now tracked at every layer: API response, DB metadata, log filenames,
  contract events, artifact paths, and dashboard display.
- Backward compatible: all new parameters have defaults (`variant_1`, `training`).
- No pre-existing tests were broken.

## Related

- `memory-bank/decisions/009-fine-tune-webpage-variant2.md` — Initial variant support
- `AGENTS.md` — Agent 5/6/9 contracts

---

**Last Updated**: 2026-03-06
**Owner**: Russell Bray
