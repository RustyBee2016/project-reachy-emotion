# Week 09 — Experiment Tracking and MLflow Ops

## Weekly Objective
Learn experiment lineage, artifact management, and comparative analysis.

## Core Python Topics
- Experiment metadata design
- Artifact/version traceability
- Run comparison methodology

## Codebase Review Targets
- Read `trainer/mlflow_tracker.py` and `tests/test_mlflow_integration.py`.
- Review run comparison utilities in `trainer/compare_finetune_runs.py`.
- Inspect pipeline run metadata in `trainer/save_run_artifacts.py`.

## Hands-On Build Tasks
1. **Read & Explain:** Produce a detailed logic + control-flow walkthrough for one selected module.
2. **Modify:** Implement one scoped code improvement aligned to this week’s objective.
3. **Validate:** Add or update tests proving correctness.
4. **Reflect:** Write a short engineering note on tradeoffs and architecture impact.

## Checkpoints (end of week)
- Can Rusty explain each important function in plain English and pseudocode?
- Can Rusty justify chosen control flow and data structures?
- Can Rusty map syntax-level details to system-level behavior?
- Are tests and documentation updated with the change?

## Deliverable
- Instrument one additional metric logging point in training/evaluation flow.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
