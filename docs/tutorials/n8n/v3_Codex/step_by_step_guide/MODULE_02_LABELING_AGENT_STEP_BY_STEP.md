# Agent 2 — Labeling Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`

## Related Scripts and Functionalities
- `apps/api/app/routers/gateway_upstream.py` -> `POST /api/relabel` (expects `video_id`, `new_label`).
- `apps/api/routers/media.py` -> `POST /api/v1/media/promote` (canonical promote operation).
- `video` + `label_event` tables are updated by workflow SQL nodes.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `Postgres: fetch.video` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `Postgres: apply.label` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `HTTP: mm.relabel` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
- `HTTP: mm.promote` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
- `Postgres: class.balance` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
3. Set required environment variables in n8n runtime/environment:
- `MEDIA_MOVER_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: label.submitted`
- Add node type: `Webhook`
- Rename node to: `Webhook: label.submitted`
- Why this node exists: Receive label or promote action from UI.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `label` |
| `responseMode` | `responseNode` |
| `options` | `{}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Code: validate.payload`

### Step 2 - `Code: validate.payload`
- Add node type: `Code`
- Rename node to: `Code: validate.payload`
- Why this node exists: Validate label/action and normalize metadata.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Validate and normalize label submission
const body = $json.body ?? $json;
const allowedLabels = new Set(['happy', 'sad', 'neutral']);
const allowedActions = new Set(['label_only', 'promote_train', 'promote_test', 'discard']);

function uuidv4() {
  return crypto.randomUUID ? crypto.randomUUID() : 
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
}

const video_id = body.video_id;
const label = (body.label || '').toLowerCase();
const action = body.action || 'label_only';
const rater_id = body.rater_id || 'anonymous';
const notes = body.notes || '';
const idempotency_key = body.idempotency_key || uuidv4();

if (!video_id) throw new Error('video_id required');
if (!allowedLabels.has(label)) throw new Error(`Invalid label: ${label}`);
if (!allowedActions.has(action)) throw new Error(`Invalid action: ${action}`);

return [{
  json: {
    video_id,
    label,
    action,
    rater_id,
    notes,
    idempotency_key,
    correlation_id: body.correlation_id || `label-${Date.now()}`
  }
}];
```

**Connection checklist for this node**
- Incoming: `Webhook: label.submitted` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: fetch.video`

### Step 3 - `Postgres: fetch.video`
- Add node type: `Postgres`
- Rename node to: `Postgres: fetch.video`
- Why this node exists: Fetch current DB state for selected video.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query**
```text
SELECT v.video_id, v.split, v.label AS current_label, v.file_path
FROM video v
WHERE v.video_id = '{{$json.video_id}}'::uuid;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Code: validate.payload` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: apply.label`

### Step 4 - `Postgres: apply.label`
- Add node type: `Postgres`
- Rename node to: `Postgres: apply.label`
- Why this node exists: Apply label update and write label event record.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query**
```text
WITH ins AS (
  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)
  VALUES (
    '{{$json.video_id}}'::uuid,
    '{{$json.label}}',
    '{{$json.action}}',
    '{{$json.rater_id}}',
    '{{$json.notes}}',
    '{{$json.idempotency_key}}'
  )
  ON CONFLICT (video_id, idempotency_key) DO NOTHING
  RETURNING event_id
)
UPDATE video
SET label = '{{$json.label}}',
    updated_at = NOW()
WHERE video_id = '{{$json.video_id}}'::uuid
RETURNING 
  video_id, 
  label, 
  split,
  (SELECT event_id FROM ins) AS event_id;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Postgres: fetch.video` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Switch: branch.action`

### Step 5 - `Switch: branch.action`
- Add node type: `Switch`
- Rename node to: `Switch: branch.action`
- Why this node exists: Route by action: label_only/promote/discard.

| UI Field | Value |
|---|---|
| `rules` | `{"values": [{"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "label_only"}]}, "renameOutput": true, "outputKey": "label_only"}, {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "promote_train"}]}, "renameOutput": true, "outputKey": "promote_train"}, {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "promote_test"}]}, "renameOutput": true, "outputKey": "promote_test"}, {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "discard"}]}, "renameOutput": true, "outputKey": "discard"}]}` |

**Connection checklist for this node**
- Incoming: `Postgres: apply.label` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: mm.relabel`
- Outgoing: this node output branch `1` -> `HTTP: mm.promote`
- Outgoing: this node output branch `2` -> `HTTP: mm.promote`
- Outgoing: this node output branch `3` -> `Postgres: class.balance`

### Step 6 - `HTTP: mm.relabel`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mm.relabel`
- Why this node exists: Sync relabel upstream through media API.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "schema_version", "value": "=v1"}, {"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "new_label", "value": "={{$json.label}}"}]}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `Switch: branch.action` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: class.balance`

### Step 7 - `HTTP: mm.promote`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mm.promote`
- Why this node exists: Promote to train/test via canonical promote endpoint.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "dest_split", "value": "={{$json.action === 'promote_train' ? 'train' : 'test'}}"}, {"name": "label", "value": "={{$json.action === 'promote_train' ? $json.label : null}}"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}, {"name": "dry_run", "value": "=false"}]}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `Switch: branch.action` output branch `1` -> this node
- Incoming: `Switch: branch.action` output branch `2` -> this node
- Outgoing: this node output branch `0` -> `Postgres: class.balance`

### Step 8 - `Postgres: class.balance`
- Add node type: `Postgres`
- Rename node to: `Postgres: class.balance`
- Why this node exists: Compute class-balance counters for UI feedback.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query**
```text
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(CASE WHEN label = 'neutral' AND split = 'train' THEN 1 END) AS neutral_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Switch: branch.action` output branch `3` -> this node
- Incoming: `HTTP: mm.relabel` output branch `0` -> this node
- Incoming: `HTTP: mm.promote` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Respond: success`

### Step 9 - `Respond: success`
- Add node type: `Respond to Webhook`
- Rename node to: `Respond: success`
- Why this node exists: Return final response to webhook caller.

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `={{ {
  "status": "success",
  "video_id": $json.video_id,
  "label": $json.label,
  "action": $json.action,
  "class_balance": {
    "happy": $json.happy_count,
    "sad": $json.sad_count,
    "neutral": $json.neutral_count,
    "total_train": $json.total_train,
    "balanced": Math.max($json.happy_count, $json.sad_count, $json.neutral_count) - Math.min($json.happy_count, $json.sad_count, $json.neutral_count) <= 10
  },
  "correlation_id": $json.correlation_id
} }}` |

**Connection checklist for this node**
- Incoming: `Postgres: class.balance` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: label.submitted` branch `0` -> `Code: validate.payload`
- `Code: validate.payload` branch `0` -> `Postgres: fetch.video`
- `Postgres: fetch.video` branch `0` -> `Postgres: apply.label`
- `Postgres: apply.label` branch `0` -> `Switch: branch.action`
- `Switch: branch.action` branch `0` -> `HTTP: mm.relabel`
- `Switch: branch.action` branch `1` -> `HTTP: mm.promote`
- `Switch: branch.action` branch `2` -> `HTTP: mm.promote`
- `Switch: branch.action` branch `3` -> `Postgres: class.balance`
- `HTTP: mm.relabel` branch `0` -> `Postgres: class.balance`
- `HTTP: mm.promote` branch `0` -> `Postgres: class.balance`
- `Postgres: class.balance` branch `0` -> `Respond: success`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
