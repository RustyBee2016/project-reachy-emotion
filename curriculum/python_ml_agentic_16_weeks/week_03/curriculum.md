# Week 03 — Async Python and Concurrency

## Weekly Objective
Master async/await, task scheduling, cancellation, and backpressure basics.

## Core Python Topics
- `asyncio` primitives (Task, gather, timeout)
- Cancellation and error handling in async flows
- WebSocket event loop design

## Codebase Review Targets
- Analyze async handlers in `apps/api/routers/gateway.py`.
- Study WebSocket control flow in `apps/reachy/cue_handler.py` and `apps/web/websocket_client.py`.
- Inspect retry logic tests in `tests/test_api_client_retry.py`.

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
- Implement a small async producer-consumer pattern with timeout handling.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
