# Ingest Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Objective
Receive ingest requests, normalize payloads, pull media into local storage, emit ingest lifecycle events, and return a deterministic webhook response.

## Related Backend Scripts and Functionalities
- `apps/api/app/routers/ingest.py`: `POST /api/v1/ingest/pull` (download/hash/ffprobe/thumbnail/DB insert).
- `apps/api/routers/gateway.py`: `POST /api/events/ingest` event sink used by this workflow.

## What Changed vs Legacy Module
- Replaced `/api/media/pull` with canonical `POST /api/v1/ingest/pull`.
- Removed obsolete polling chain (`Wait`, status polling loop, duplicate DB write).
- Removed workflow-level auth gate and unauthorized response branch for this local trusted environment.
- Added envelope fields on emitted events: `schema_version`, `source`, `issued_at`.
- Added retry settings to outbound HTTP nodes (`maxTries=5`).
- Switched Agent 1 HTTP node URLs to explicit absolute endpoints because runtime env allow-list blocks those `$env.*` variables.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: ingest.video` | `Webhook` | Ingest entrypoint (`video_gen_hook`). |
| `Code: normalize.payload` | `Code` | Canonicalizes source URL, 3-class label policy, correlation/idempotency metadata. |
| `HTTP: media.pull` | `HTTP Request` | Calls `POST /api/v1/ingest/pull` with ingest payload and tracing headers. |
| `IF: status.done?` | `If` | Allows only `done|duplicate` to emit event. |
| `HTTP: emit.completed` | `HTTP Request` | Posts ingest lifecycle event to `/api/events/ingest`. |
| `Respond: success` | `Respond to Webhook` | Returns final normalized status payload to caller. |

## How This Workflow Delivers Code-Level Functionality
1. Ingest trigger reaches `Webhook: ingest.video`.
2. `Code: normalize.payload` validates payload shape and normalizes metadata.
3. `HTTP: media.pull` calls `pull_video()` to download, hash, dedupe, thumbnail, and insert DB row.
4. `IF: status.done?` gates event emission to terminal ingest statuses.
5. `HTTP: emit.completed` emits an auditable gateway event envelope.
6. `Respond: success` returns status, `video_id`, and `correlation_id`.

## Notes
- This module reflects the current no-auth workflow policy for n8n orchestration inside the trusted local network.
- Legacy module files under `docs/tutorials/n8n/Opus_v2/` remain as historical references.
