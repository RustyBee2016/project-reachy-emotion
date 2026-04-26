# Week 04 — Architecture Patterns for Services

## Weekly Objective
Apply modular design, dependency inversion, and clean boundaries in Python services.

## Core Python Topics
- Layered architecture in Python
- Dependency injection and inversion
- Configuration boundaries and startup orchestration

## Codebase Review Targets
- Review dependency setup in `apps/api/app/deps.py`.
- Trace config boundaries in `apps/gateway/config.py` and `apps/api/app/config.py`.
- Inspect entrypoints (`apps/api/main.py`, `apps/gateway/main.py`).

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
- Produce a service-boundary diagram and propose one architecture improvement.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
