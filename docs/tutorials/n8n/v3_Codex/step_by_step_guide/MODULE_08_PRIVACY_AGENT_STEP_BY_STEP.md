# Agent 8 — Privacy/Retention Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/08_privacy_agent.json`

## Related Scripts and Functionalities
- Retention query and purge state updates are handled by workflow SQL nodes against `video` + `audit_log`.
- Filesystem deletion is executed by SSH command in `SSH: delete.file`.
- Purge events are emitted to gateway pipeline endpoint (`POST /api/events/pipeline`).

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `Postgres: find.old_temp` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `SSH: delete.file` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
- `Postgres: mark.purged` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `Postgres: audit.log` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Schedule: daily 03:00`
- Add node type: `Schedule Trigger`
- Rename node to: `Schedule: daily 03:00`
- Why this node exists: Daily retention sweep trigger.

| UI Field | Value |
|---|---|
| `rule` | `{"interval": [{"field": "cronExpression", "expression": "0 3 * * *"}]}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Postgres: find.old_temp`

### Step 2 - `Webhook: gdpr.deletion`
- Add node type: `Webhook`
- Rename node to: `Webhook: gdpr.deletion`
- Why this node exists: Manual purge trigger endpoint.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `privacy/purge` |
| `responseMode` | `responseNode` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Postgres: find.old_temp`

### Step 3 - `Postgres: find.old_temp`
- Add node type: `Postgres`
- Rename node to: `Postgres: find.old_temp`
- Why this node exists: Select expired temp records for purge.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query**
```text
SELECT video_id, file_path FROM video WHERE split='temp' AND created_at < NOW() - INTERVAL '7 days';
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Schedule: daily 03:00` output branch `0` -> this node
- Incoming: `Webhook: gdpr.deletion` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Loop: batch.delete`

### Step 4 - `Loop: batch.delete`
- Add node type: `Split In Batches`
- Rename node to: `Loop: batch.delete`
- Why this node exists: Process purge operations in batches.

| UI Field | Value |
|---|---|
| `batchSize` | `50` |
| `options` | `{}` |

**Connection checklist for this node**
- Incoming: `Postgres: find.old_temp` output branch `0` -> this node
- Incoming: `Postgres: audit.log` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: delete.file`

### Step 5 - `SSH: delete.file`
- Add node type: `SSH`
- Rename node to: `SSH: delete.file`
- Why this node exists: Delete file from local storage.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
rm -f /videos/{{$json.file_path}}
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Loop: batch.delete` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: mark.purged`

### Step 6 - `Postgres: mark.purged`
- Add node type: `Postgres`
- Rename node to: `Postgres: mark.purged`
- Why this node exists: Mark DB row as purged.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query**
```text
UPDATE video SET split='purged', updated_at=NOW() WHERE video_id='{{$json.video_id}}'::uuid;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `SSH: delete.file` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: audit.log`

### Step 7 - `Postgres: audit.log`
- Add node type: `Postgres`
- Rename node to: `Postgres: audit.log`
- Why this node exists: Write purge action to audit log table.

| UI Field | Value |
|---|---|
| `operation` | `insert` |
| `table` | `audit_log` |
| `columns` | `action, video_id, reason, timestamp` |

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Postgres: mark.purged` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Loop: batch.delete`
- Outgoing: this node output branch `0` -> `HTTP: emit.purged`

### Step 8 - `HTTP: emit.purged`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.purged`
- Why this node exists: Emit purge event for observability.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=privacy.purged"}, {"name": "pipeline_id", "value": "=privacy-retention"}, {"name": "count", "value": "=1"}, {"name": "video_id", "value": "={{$json.video_id}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `Postgres: audit.log` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Schedule: daily 03:00` branch `0` -> `Postgres: find.old_temp`
- `Webhook: gdpr.deletion` branch `0` -> `Postgres: find.old_temp`
- `Postgres: find.old_temp` branch `0` -> `Loop: batch.delete`
- `Loop: batch.delete` branch `0` -> `SSH: delete.file`
- `SSH: delete.file` branch `0` -> `Postgres: mark.purged`
- `Postgres: mark.purged` branch `0` -> `Postgres: audit.log`
- `Postgres: audit.log` branch `0` -> `Loop: batch.delete`
- `Postgres: audit.log` branch `0` -> `HTTP: emit.purged`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
