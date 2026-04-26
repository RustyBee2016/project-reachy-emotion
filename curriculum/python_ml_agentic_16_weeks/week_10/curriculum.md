# Week 10 — Agentic AI Foundations in the Repo

## Weekly Objective
Model event-driven agents, tool boundaries, and message contracts.

## Core Python Topics
- Agent boundaries and tool contracts
- Prompt-routing and response parsing
- State transition design

## Codebase Review Targets
- Trace orchestration in `apps/pipeline/emotion_llm_gesture.py`.
- Review LLM interfaces in `apps/llm/client.py` and prompts in `apps/llm/prompts/emotion_prompts.py`.
- Inspect gesture mapping in `apps/reachy/gestures/emotion_gesture_map.py`.

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
- Draw a sequence diagram: emotion event → LLM response → gesture cue execution.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
