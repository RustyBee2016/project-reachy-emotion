# Promotion / Curation Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/03_promotion_agent.json`

## Objective
Run dry-run promotion plans with human approval, execute real promotion, and rebuild manifests.

## Related Backend Scripts and Functionalities
- `apps/api/routers/media.py`: `POST /api/v1/media/promote` handles dry-run and real promote execution.
- `apps/api/app/routers/ingest.py`: `POST /api/v1/ingest/manifest/rebuild` rebuilds train/test manifests.
- `apps/api/routers/gateway.py`: `POST /api/events/pipeline` is used for promotion completion event in v3 flow.

## What Changed vs Legacy Module
- Promote URLs switched from `/api/promote` to canonical `/api/v1/media/promote` (dry-run and real).
- Manifest rebuild URL standardized to `/api/v1/ingest/manifest/rebuild`.
- Promotion completion event remapped from missing `/api/events/promotion` to implemented `/api/events/pipeline`.
- Fixed `Code: summarize.plan` node references to use actual node names instead of stale identifiers.
- Set all outbound HTTP nodes to explicit `POST`.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: request.promotion` | `Webhook` | `Webhook` for promotion request intake (`promotion/v1`). |
| `Code: validate.request` | `Code` | `Code` validation for video/label/target and deterministic idempotency key generation. |
| `HTTP: dryrun.promote` | `HTTP Request` | `HTTP Request` dry-run call to Media Mover promote API. |
| `Code: summarize.plan` | `Code` | `Code` node producing human-readable approval payload. |
| `Webhook: await.approval` | `Webhook` | Second `Webhook` pause point for human approval (`promotion/approve`). |
| `IF: approved?` | `If` | `If` node branching approval vs rejection. |
| `HTTP: real.promote` | `HTTP Request` | `HTTP Request` executing real promotion after approval. |
| `HTTP: rebuild.manifest` | `HTTP Request` | `HTTP Request` that triggers manifest rebuild for train/test. |
| `HTTP: emit.completed` | `HTTP Request` | `HTTP Request` logging completion event through gateway pipeline channel. |
| `Respond: success` | `Respond to Webhook` | `Respond to Webhook` success path. |
| `Respond: rejected` | `Respond to Webhook` | `Respond to Webhook` rejection path (403). |

## How This Workflow Delivers Code-Level Functionality
1. Dry-run promote call executes validation path before any filesystem mutation, supporting safe human review.
2. Approval webhook creates an explicit human gate before executing real promotion.
3. Manifest rebuild call updates downstream training/evaluation dataset views after promotion changes.
4. Completion event uses implemented `/api/events/pipeline` endpoint to avoid lost events from non-existent routes.
5. Deterministic idempotency key generation keeps retries safe across n8n/API boundaries.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
