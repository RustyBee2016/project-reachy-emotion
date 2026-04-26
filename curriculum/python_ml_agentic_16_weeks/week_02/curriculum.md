# Week 02 — Data Modeling, Typing, and Validation

## Weekly Objective
Strengthen type hints, dataclasses, Pydantic schemas, and runtime validation strategy.

## Core Python Topics
- Type annotations (`typing`, `Protocol`, `TypedDict`)
- Pydantic model design and validation semantics
- Schema evolution strategies

## Codebase Review Targets
- Map schema contracts in `shared/contracts/schemas.py`.
- Inspect settings/config patterns in `apps/api/app/settings.py`.
- Compare schema usage in API and web clients.

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
- Refactor one internal data model with stricter typing and add tests.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
