# Privacy / Retention Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/08_privacy_agent.json`

## Objective
Apply retention policy to temp media, purge stale files, and maintain purge audit traces.

## Related Backend Scripts and Functionalities
- `apps/api/app/routers/gateway_upstream.py`: `/api/v1/privacy/redact/{video_id}` exists, but this workflow currently uses direct file + DB operations.
- `apps/api/routers/gateway.py`: Pipeline event endpoint `/api/events/pipeline` used for purge events.

## What Changed vs Legacy Module
- Retention TTL changed from 14 days to 7 days to align AGENTS default policy guidance.
- Privacy event endpoint remapped from missing `/api/events/privacy` to implemented `/api/events/pipeline`.
- Event payload now includes `pipeline_id=privacy-retention` and `video_id` for traceability.
- Kept batch deletion pattern (`Split In Batches`) to reduce filesystem/DB load spikes.
- Set explicit `POST` method for event node.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Schedule: daily 03:00` | `Schedule Trigger` | `Schedule Trigger` for recurring retention sweep. |
| `Webhook: gdpr.deletion` | `Webhook` | `Webhook` for manual purge trigger. |
| `Postgres: find.old_temp` | `Postgres` | `Postgres` query selecting expired temp records. |
| `Loop: batch.delete` | `Split In Batches` | `Split In Batches` node to process records in bounded chunks. |
| `SSH: delete.file` | `SSH` | `SSH` node deleting media file on disk. |
| `Postgres: mark.purged` | `Postgres` | `Postgres` update marking row as purged. |
| `Postgres: audit.log` | `Postgres` | `Postgres` insert into audit log table. |
| `HTTP: emit.purged` | `HTTP Request` | `HTTP Request` purge event to gateway pipeline endpoint. |

## How This Workflow Delivers Code-Level Functionality
1. Scheduled + manual triggers support both automated retention and operator-requested purges.
2. TTL query scopes purge candidates to stale temp media only.
3. Batch loop controls deletion throughput to avoid spikes in I/O and DB locking.
4. Purged-state updates and audit writes preserve evidence trail for compliance checks.
5. Pipeline event emission exposes purge operations to centralized observability channels.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
