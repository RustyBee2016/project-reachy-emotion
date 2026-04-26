# Week 08 — Evaluation, Calibration, and Quality Gates

## Weekly Objective
Operationalize metrics beyond accuracy: macro F1, ECE, Brier, balanced accuracy.

## Core Python Topics
- Metric design for imbalanced classes
- Calibration metrics and reliability
- Quality gate automation

## Codebase Review Targets
- Review `trainer/gate_a_validator.py` and calibration tests in `tests/test_calibration_metrics.py`.
- Inspect evaluation flow in `trainer/fer_finetune/evaluate.py`.
- Connect results persistence via `trainer/result_store.py`.

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
- Build a markdown playbook for pass/fail gate interpretation and response actions.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
