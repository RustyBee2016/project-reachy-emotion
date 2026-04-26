# Week 05 — Testing Strategy: Unit, Integration, Contract

## Weekly Objective
Build confidence with pytest fixtures, mocks, and end-to-end validation strategy.

## Core Python Topics
- pytest fixture composition
- Mocking external systems
- Contract testing and regression prevention

## Codebase Review Targets
- Read fixture design in `tests/apps/api/conftest.py`.
- Review API coverage in `tests/apps/api/test_ingest_endpoints.py` and `tests/test_gateway_app.py`.
- Study pipeline contract checks in `tests/test_run_efficientnet_pipeline_contract.py`.

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
- Add one contract test for an error path and document expected payload.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
