# Agent 1 — Ingest Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Related Scripts and Functionalities
- `apps/api/app/routers/ingest.py` -> `POST /api/v1/ingest/pull` (download/hash/ffprobe/thumbnail/DB insert).
- `apps/api/routers/gateway.py` -> `POST /api/events/ingest` (ingest event intake).

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `HTTP: media.pull` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`
- `INGEST_TOKEN`
- `MEDIA_MOVER_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: ingest.video`
- Add node type: `Webhook`
- Rename node to: `Webhook: ingest.video`
- Why this node exists: Receive ingest request from generation/upload callers.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `video_gen_hook` |
| `responseMode` | `onReceived` |
| `options` | `{"responseCode": 202}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `IF: auth.check`

### Step 2 - `IF: auth.check`
- Add node type: `If`
- Rename node to: `IF: auth.check`
- Why this node exists: Authorize request using ingest token header check.

| UI Field | Value |
|---|---|
| `conditions` | `{"string": [{"value1": "={{$json.headers['x-ingest-key']}}", "operation": "equals", "value2": "={{$env.INGEST_TOKEN}}"}]}` |

**Connection checklist for this node**
- Incoming: `Webhook: ingest.video` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: normalize.payload`
- Outgoing: this node output branch `1` -> `Respond: 401 Unauthorized`

### Step 3 - `Code: normalize.payload`
- Add node type: `Code`
- Rename node to: `Code: normalize.payload`
- Why this node exists: Normalize request payload to canonical contract.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Normalize incoming payload from various sources
const body = $json.body ?? $json;
const sourceUrl = body.source_url ?? body.url ?? body.asset?.url ?? body.data?.asset?.url;

if (!sourceUrl) {
  throw new Error('Missing source_url in request body');
}

const label = body.label ?? body.emotion ?? null;
const meta = body.meta ?? { 
  generator: body.generator ?? body.source ?? 'unknown' 
};
const correlationId = $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`;
const idempotencyKey = $json.headers?.['idempotency-key'] ?? `idem-${Date.now()}`;

return [
  {
    json: {
      source_url: sourceUrl,
      label,
      meta,
      correlation_id: correlationId,
      idempotency_key: idempotencyKey,
      timestamp: new Date().toISOString()
    }
  }
];
```

**Connection checklist for this node**
- Incoming: `IF: auth.check` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: media.pull`

### Step 4 - `HTTP: media.pull`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: media.pull`
- Why this node exists: Call media ingest endpoint to download/register video.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/pull` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}, {"name": "X-Correlation-ID", "value": "={{$json.correlation_id}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "source_url", "value": "={{$json.source_url}}"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}, {"name": "intended_emotion", "value": "={{$json.label}}"}, {"name": "generator", "value": "={{$json.meta?.generator \|\| 'unknown'}}"}, {"name": "prompt", "value": "={{$json.meta?.prompt \|\| ''}}"}]}` |
| `options` | `{"timeout": 120000}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `Code: normalize.payload` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: status.done?`

### Step 5 - `IF: status.done?`
- Add node type: `If`
- Rename node to: `IF: status.done?`
- Why this node exists: Allow only done/duplicate statuses to continue.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{ ['done','duplicate'].includes($json.status) }}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `HTTP: media.pull` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.completed`
- Outgoing: this node output branch `1` -> `Respond: success`

### Step 6 - `HTTP: emit.completed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.completed`
- Why this node exists: Emit ingest lifecycle event to gateway ingest endpoint.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/ingest` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "={{$json.status === 'duplicate' ? 'ingest.duplicate' : 'ingest.completed'}}"}, {"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}, {"name": "file_path", "value": "={{$json.file_path}}"}, {"name": "sha256", "value": "={{$json.sha256}}"}, {"name": "duplicate", "value": "={{$json.duplicate \|\| false}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: status.done?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Respond: success`

### Step 7 - `Respond: success`
- Add node type: `Respond to Webhook`
- Rename node to: `Respond: success`
- Why this node exists: Return final response to webhook caller.

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `={{ {"status": $json.status \|\| 'unknown', "video_id": $json.video_id \|\| null, "correlation_id": $json.correlation_id \|\| null, "duplicate": $json.duplicate \|\| false} }}` |

**Connection checklist for this node**
- Incoming: `IF: status.done?` output branch `1` -> this node
- Incoming: `HTTP: emit.completed` output branch `0` -> this node

### Step 8 - `Respond: 401 Unauthorized`
- Add node type: `Respond to Webhook`
- Rename node to: `Respond: 401 Unauthorized`
- Why this node exists: Return unauthorized response when token fails.

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `={{ {"error": "unauthorized", "message": "Invalid or missing X-INGEST-KEY header"} }}` |
| `options` | `{"responseCode": 401}` |

**Connection checklist for this node**
- Incoming: `IF: auth.check` output branch `1` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: ingest.video` branch `0` -> `IF: auth.check`
- `IF: auth.check` branch `0` -> `Code: normalize.payload`
- `IF: auth.check` branch `1` -> `Respond: 401 Unauthorized`
- `Code: normalize.payload` branch `0` -> `HTTP: media.pull`
- `HTTP: media.pull` branch `0` -> `IF: status.done?`
- `IF: status.done?` branch `0` -> `HTTP: emit.completed`
- `IF: status.done?` branch `1` -> `Respond: success`
- `HTTP: emit.completed` branch `0` -> `Respond: success`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
