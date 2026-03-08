# Reachy Agentic AI System — Mid-Level Guide for Agentic AI Team Lead

## Purpose of this document
This guide summarizes the **step-by-step wiring tutorials** (located in `docs/tutorials/n8n/v3_Codex/step_by_step_guide`) for technical leadership.

It is written for planning implementation quality, cross-agent consistency, and delivery risk management.

## What the step-by-step folder is optimized for
Each module is a reproducible wiring recipe for one workflow (Agents 1–9). Every guide includes:
- Required environment variables and credentials
- Exact n8n node types and node names
- Field-level configuration tables
- Connection checklists (source node -> target node)
- Smoke-test procedures after wiring

This makes it ideal for team leads managing multiple contributors.

## Mid-level control-flow model across all agents
Even though each agent is different, most workflows follow this reusable pattern:
1. **Trigger node** (`Webhook` or `Schedule/Cron`)
2. **Validation/normalization stage** (`Code`, `If`, `Switch`, `Set`)
3. **External action stage** (`HTTP Request`, `Postgres`, `SSH`)
4. **Decision gate** (`If` based on status, thresholds, or approvals)
5. **Event emission and response** (`HTTP Request` + `Respond to Webhook`/email)

As a team lead, this standardized control flow is the main reason onboarding is faster and regressions are easier to isolate.

## Module-level delivery focus
- **Agent 1 (Ingest):** Secure intake, payload normalization, ingest call, completion signaling.
- **Agent 2 (Labeling):** Human label validation + DB write + optional promote/relabel actions.
- **Agent 3 (Promotion):** Dry-run planning, human approval gate, real promotion, manifest rebuild.
- **Agent 4 (Reconciler):** Scheduled/manual drift detection between filesystem and DB.
- **Agent 5 (Training):** Data readiness checks, remote pipeline launch, status polling, Gate A pass/fail.
- **Agent 6 (Evaluation):** Test-balance checks, evaluation run, metric persistence, gate signaling.
- **Agent 7 (Deployment):** Jetson deploy actions, Gate B verification, rollback path.
- **Agent 8 (Privacy):** TTL-based candidate identification, deletion workflow, audit events.
- **Agent 9 (Observability):** Metrics scrape, parse, normalize, persistence, alert branch.

## Team lead governance checklist
Use this checklist during review:
- Node names in workflow exactly match names referenced by expressions in `Code` nodes.
- All outbound `HTTP Request` nodes set explicit method (`GET`/`POST`)—no implicit defaults.
- Idempotency and correlation IDs are passed through ingest/promotion/training paths.
- Approval-gated flows (especially promotion/deployment) have explicit reject branches.
- Post-change smoke tests are documented and reproducible.

## Delivery risks this folder helps prevent
- Broken node references after node rename in n8n canvas.
- Contract drift between workflow body fields and backend request models.
- Silent failures from implicit method defaults or missing environment variables.
- Incomplete branch handling (success path works, rejection/error path forgotten).

## Practical operating model for your team
- Assign one owner per module.
- Require "connection checklist" sign-off before merge.
- Add a short post-activation verification artifact (status payload screenshot/log snippet).
- Track endpoint contract changes in changelog before workflow export/import cycles.

## One-sentence team-lead takeaway
The step-by-step guides are operational blueprints: they standardize node wiring, make QA repeatable, and reduce integration drift across the nine-agent n8n system.
