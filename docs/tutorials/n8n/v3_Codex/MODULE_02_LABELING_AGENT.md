# Labeling Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`

## Objective
Validate user labels, update DB label state, route promote actions, and recompute class balance.

## Related Backend Scripts and Functionalities
- `apps/api/app/routers/gateway_upstream.py`: `POST /api/relabel` expects `new_label` and updates `video.label`.
- `apps/api/routers/media.py`: `POST /api/v1/media/promote` (and `/api/media/promote` alias) performs atomic promotion.
- `apps/api/app/db/models.py`: `video` and `label_event` tables updated by SQL nodes.

## What Changed vs Legacy Module
- Updated relabel payload key from `label` to `new_label` to match `RelabelRequest` contract.
- Moved promote endpoint from `/api/promote` to canonical `/api/v1/media/promote`.
- Aligned promote payload with 3-class policy by sending label only for `promote_train` path.
- Kept action fan-out (`label_only`, `promote_train`, `promote_test`, `discard`) with explicit routing via `Switch`.
- Set explicit HTTP method `POST` on outbound API calls.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: label.submitted` | `Webhook` | `Webhook` entrypoint for UI label submission. |
| `Code: validate.payload` | `Code` | `Code` node validates label/action/idempotency and normalizes payload. |
| `Postgres: fetch.video` | `Postgres` | `Postgres` node reads current video split/label state. |
| `Postgres: apply.label` | `Postgres` | `Postgres` node writes `label_event` + updates `video.label` idempotently. |
| `Switch: branch.action` | `Switch` | `Switch` node routes label-only vs promotion actions. |
| `HTTP: mm.relabel` | `HTTP Request` | `HTTP Request` node to `/api/relabel` for upstream metadata sync. |
| `HTTP: mm.promote` | `HTTP Request` | `HTTP Request` node to `/api/v1/media/promote` for train/test movement. |
| `Postgres: class.balance` | `Postgres` | `Postgres` aggregation for happy/sad/neutral training counts. |
| `Respond: success` | `Respond to Webhook` | `Respond to Webhook` node returning updated balance context. |

## How This Workflow Delivers Code-Level Functionality
1. Label payload validation protects downstream DB and promotion operations from invalid actions/labels.
2. SQL nodes persist label events and keep `video.label` synchronized for class-balance and promotion logic.
3. `HTTP: mm.relabel` matches upstream `RelabelRequest` (`new_label`) so router validation succeeds.
4. `HTTP: mm.promote` uses canonical `/api/v1/media/promote`, ensuring filesystem move + DB state updates are handled by Media Mover service code.
5. Final `class.balance` query enables UI to enforce 1:1:1 class tracking for happy/sad/neutral.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
