# Reachy Agentic AI System — High-Level Brief for Project Manager (Rusty)

## Purpose of this document
This brief summarizes the **`docs/tutorials/n8n`** folder at an executive level so you can quickly understand what exists, why it exists, and how it supports delivery of Reachy_Local_08.4.2.

## What this folder contains (in plain language)
The folder is the "program guide" for the n8n-based agentic system. It includes:
- A curriculum index and tutorial plan explaining how the workflow system is taught and onboarded.
- Legacy modules (`MODULE_00` to `MODULE_13`) that still explain core design patterns.
- A **v3 orientation set** (`V3_TUTORIAL_INDEX`, `V3_AGENT_NODE_REFERENCE`, `V3_ENDPOINT_ALIGNMENT`) that points to the current production-aligned architecture.
- A `v3_Codex` curriculum that is the practical, code-aligned learning path for Agents 1–9.

## Business-level architecture summary
At this level, the system is a staged pipeline with governance checkpoints:
1. **Data intake and curation** (Ingest, Labeling, Promotion)
2. **Data integrity and policy maintenance** (Reconciler, Privacy)
3. **Model lifecycle execution** (Training, Evaluation, Deployment)
4. **Operational visibility** (Observability)

This gives you a local-first, auditable flow from new video to deployed model update.

## Why the docs are structured this way
The top-level tutorials balance two needs:
- **Management alignment:** clear ownership by agent role and gate outcomes.
- **Execution alignment:** direct mapping from docs to workflow JSON and backend endpoints.

In short: PMs can monitor milestones and risks without reading every node expression.

## What changed in the v3 direction (important for planning)
The v3 guidance emphasizes:
- Canonical endpoints (for example, promotion and ingest endpoint alignment).
- Removal of stale workflow behavior (for example, outdated polling patterns).
- Stronger consistency between workflow JSON behavior and active backend code.

Project impact:
- Fewer ambiguous contracts between n8n and FastAPI services.
- Better reliability for approvals, promotion flows, and status/event paths.
- Clearer change management via changelog-driven updates.

## PM checklist you can run every sprint
- Confirm each agent has a current workflow JSON and tutorial reference.
- Confirm endpoint alignment notes are up to date before release freeze.
- Confirm gate criteria ownership:
  - Gate A: training/evaluation thresholds
  - Gate B: deployment runtime thresholds
- Confirm privacy retention and audit event paths are still policy compliant.
- Confirm observability metrics are being collected and stored.

## Recommended reading order for non-engineering stakeholders
1. `V3_TUTORIAL_INDEX.md`
2. `V3_ENDPOINT_ALIGNMENT.md`
3. `v3_Codex/CURRICULUM_INDEX.md`
4. `v3_Codex/WORKFLOW_JSON_CHANGELOG.md`

This sequence gives strategy first, technical deltas second.

## One-sentence executive takeaway
The `docs/tutorials/n8n` folder provides a full governance + implementation map for a local-first, multi-agent ML operations system, with v3 docs serving as the active source of truth for rollout decisions.
