# Week 06 — Data Pipelines and Reproducibility

## Weekly Objective
Design deterministic data preparation, hashing, manifests, and traceability.

## Core Python Topics
- Deterministic data transformations
- Manifest/hash lineage
- File-system to metadata consistency

## Codebase Review Targets
- Trace dataset prep in `trainer/prepare_dataset.py`.
- Inspect split orchestration in `trainer/split_run_dataset.py`.
- Review root/data policies in `trainer/data_roots.py`.

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
- Create a reproducibility checklist tied to dataset hash + manifest outputs.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
