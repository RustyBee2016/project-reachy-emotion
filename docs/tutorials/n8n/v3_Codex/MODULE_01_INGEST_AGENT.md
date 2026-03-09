# Ingest Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Objective
Receive ingest requests, normalize payloads, pull media into local storage, and emit ingest lifecycle events.

## Related Backend Scripts and Functionalities
- `apps/api/app/routers/ingest.py`: `POST /api/v1/ingest/pull` (pull/download + ffprobe + thumbnail + DB insert).
- `apps/api/routers/gateway.py`: `POST /api/events/ingest` event sink used by this workflow.

## What Changed vs Legacy Module
- Replaced `/api/media/pull` with canonical `POST /api/v1/ingest/pull` to match active Media Mover routers.
- Removed obsolete polling chain (`Wait`, `HTTP: check.status`, retry loop). Ingest pull is synchronous and already returns `status=done|duplicate`.
- Removed duplicate DB write (`Postgres: insert.video`) because `pull_video()` already persists to `video` table.
- Updated success criteria to accept both `done` and `duplicate` statuses.
- Added explicit HTTP method configuration (`POST`) for outbound requests.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: ingest.video` | `Webhook` | n8n `Webhook` trigger for ingest start (`video_gen_hook`). |
| `IF: auth.check` | `If` | n8n `If` gate validating `x-ingest-key` header against `INGEST_TOKEN`. |
| `Code: normalize.payload` | `Code` | n8n `Code` node that canonicalizes source URL and correlation/idempotency metadata. |
| `HTTP: media.pull` | `HTTP Request` | n8n `HTTP Request` node calling `POST /api/v1/ingest/pull` with `source_url`, `correlation_id`, and optional emotion metadata. |
| `IF: status.done?` | `If` | n8n `If` node validating response status belongs to `done|duplicate`. |
| `HTTP: emit.completed` | `HTTP Request` | n8n `HTTP Request` node posting ingest event payload to gateway `/api/events/ingest`. |
| `Respond: success` | `Respond to Webhook` | n8n `Respond to Webhook` node returning final normalized status to caller. |
| `Respond: 401 Unauthorized` | `Respond to Webhook` | n8n `Respond to Webhook` node for auth rejection path. |

## How This Workflow Delivers Code-Level Functionality
1. Ingest trigger arrives at `Webhook: ingest.video` and is validated by `If` auth gate.
2. `Code: normalize.payload` standardizes payload variants so downstream API contract is stable.
3. `HTTP: media.pull` calls `pull_video()` in `apps/api/app/routers/ingest.py`, which performs download, hash, metadata extraction, thumbnail generation, and DB insert.
4. The workflow only emits completion events when status is `done` or `duplicate`, matching pull endpoint outcomes.
5. Gateway receives ingest event through `apps/api/routers/gateway.py` (`/api/events/ingest`) for audit/observability.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
