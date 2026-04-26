# Week 11 — Reliable Agentic Workflows

## Weekly Objective
Add idempotency, retries, fallbacks, and observability to agentic pipelines.

## Core Python Topics
- Idempotent workflow design
- Retry/backoff patterns
- Failure-mode analysis

## Codebase Review Targets
- Review API retry + resilience tests in `tests/test_api_client_v2.py` and `tests/test_gateway_proxy_unit.py`.
- Inspect status persistence patterns in `tests/apps/api/test_status_persistence.py`.
- Analyze guardrail utilities in shared modules.

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
- Implement and test one deterministic fallback path for an agentic step.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
