# Agent 3 — Promotion/Curation Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/03_promotion_agent.json`

## Related Scripts and Functionalities
- `apps/api/routers/media.py` -> dry-run and real promote at `POST /api/v1/media/promote`.
- `apps/api/app/routers/ingest.py` -> `POST /api/v1/ingest/manifest/rebuild`.
- `apps/api/routers/gateway.py` -> `POST /api/events/pipeline` event sink used in v3.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `HTTP: dryrun.promote` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
- `HTTP: real.promote` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
- `HTTP: rebuild.manifest` uses credential type `httpHeaderAuth` with display name `Media Mover Auth`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`
- `MEDIA_MOVER_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: request.promotion`
- Add node type: `Webhook`
- Rename node to: `Webhook: request.promotion`
- Why this node exists: Receive promotion request payload.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `promotion/v1` |
| `responseMode` | `responseNode` |
| `options` | `{}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Code: validate.request`

### Step 2 - `Code: validate.request`
- Add node type: `Code`
- Rename node to: `Code: validate.request`
- Why this node exists: Validate promotion payload and generate idempotency key.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Validate promotion request
const body = $json.body ?? $json;
const required = ['video_id', 'label'];

for (const field of required) {
  if (!body[field]) {
    throw new Error(`Missing required field: ${field}`);
  }
}

const allowedSplits = ['train', 'test'];
const target = body.target || body.dest_split || 'train';

if (!allowedSplits.includes(target)) {
  throw new Error(`Invalid target split: ${target}`);
}

// Generate stable idempotency key
const crypto = require('crypto');
const idem = body.idempotency_key || crypto.createHash('sha256')
  .update(`${body.video_id}|${target}|${body.label}`)
  .digest('hex').slice(0, 32);

return [{
  json: {
    video_id: body.video_id,
    label: body.label,
    target,
    idempotency_key: idem,
    correlation_id: body.correlation_id || `promo-${Date.now()}`,
    dry_run: true  // Start with dry-run
  }
}];
```

**Connection checklist for this node**
- Incoming: `Webhook: request.promotion` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: dryrun.promote`

### Step 3 - `HTTP: dryrun.promote`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: dryrun.promote`
- Why this node exists: Execute dry-run promotion plan.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "dest_split", "value": "={{$json.target}}"}, {"name": "label", "value": "={{$json.label}}"}, {"name": "dry_run", "value": "=true"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}]}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `Code: validate.request` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: summarize.plan`

### Step 4 - `Code: summarize.plan`
- Add node type: `Code`
- Rename node to: `Code: summarize.plan`
- Why this node exists: Build human-approval summary payload.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Summarize dry-run plan for approval
const plan = $json;
const req = $('Code: validate.request').first().json;

return [{
  json: {
    approval_request: {
      title: 'Video Promotion Request',
      video_id: req.video_id,
      label: req.label,
      target_split: req.target,
      plan_summary: {
        will_move: plan.moves || [],
        will_update_db: plan.will_update_db !== false,
        conflicts: plan.conflicts || [],
        dry_run_status: plan.status
      },
      correlation_id: req.correlation_id,
      idempotency_key: req.idempotency_key
    }
  }
}];
```

**Connection checklist for this node**
- Incoming: `HTTP: dryrun.promote` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Webhook: await.approval`

### Step 5 - `Webhook: await.approval`
- Add node type: `Webhook`
- Rename node to: `Webhook: await.approval`
- Why this node exists: Pause until human approval callback arrives.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `promotion/approve` |
| `responseMode` | `onReceived` |
| `options` | `{}` |

**Connection checklist for this node**
- Incoming: `Code: summarize.plan` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: approved?`

### Step 6 - `IF: approved?`
- Add node type: `If`
- Rename node to: `IF: approved?`
- Why this node exists: Branch approved vs rejected decision.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.approved}}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `Webhook: await.approval` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: real.promote`
- Outgoing: this node output branch `1` -> `Respond: rejected`

### Step 7 - `HTTP: real.promote`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: real.promote`
- Why this node exists: Execute real promotion after approval.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "dest_split", "value": "={{$json.target_split}}"}, {"name": "label", "value": "={{$json.label}}"}, {"name": "dry_run", "value": "=false"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}]}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `IF: approved?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: rebuild.manifest`

### Step 8 - `HTTP: rebuild.manifest`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: rebuild.manifest`
- Why this node exists: Rebuild manifests after state mutation.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/manifest/rebuild` |
| `authentication` | `genericCredentialType` |
| `genericAuthType` | `httpHeaderAuth` |
| `sendHeaders` | `True` |
| `headerParameters` | `{"parameters": [{"name": "X-Correlation-ID", "value": "={{$json.correlation_id}}"}]}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "splits", "value": "=[\"train\", \"test\"]"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}]}` |
| `method` | `POST` |

**Credential binding**
- `httpHeaderAuth` -> `Media Mover Auth`

**Connection checklist for this node**
- Incoming: `HTTP: real.promote` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.completed`

### Step 9 - `HTTP: emit.completed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.completed`
- Why this node exists: Emit promotion completion event to pipeline event endpoint.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=promotion.completed"}, {"name": "pipeline_id", "value": "={{$json.correlation_id}}"}, {"name": "video_id", "value": "={{$json.video_id}}"}, {"name": "dest_split", "value": "={{$json.target_split}}"}, {"name": "label", "value": "={{$json.label}}"}, {"name": "correlation_id", "value": "={{$json.correlation_id}}"}, {"name": "dataset_hash", "value": "={{$('HTTP: rebuild.manifest').first().json.dataset_hash \|\| ''}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `HTTP: rebuild.manifest` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Respond: success`

### Step 10 - `Respond: success`
- Add node type: `Respond to Webhook`
- Rename node to: `Respond: success`
- Why this node exists: Return final response to webhook caller.

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `={{ {
  "status": "success",
  "video_id": $json.video_id,
  "dest_split": $json.target_split,
  "dataset_hash": $json.dataset_hash,
  "correlation_id": $json.correlation_id
} }}` |

**Connection checklist for this node**
- Incoming: `HTTP: emit.completed` output branch `0` -> this node

### Step 11 - `Respond: rejected`
- Add node type: `Respond to Webhook`
- Rename node to: `Respond: rejected`
- Why this node exists: Implements one stage of the workflow execution path.

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `={{ {
  "status": "rejected",
  "message": "Promotion not approved",
  "correlation_id": $json.correlation_id
} }}` |
| `options` | `{"responseCode": 403}` |

**Connection checklist for this node**
- Incoming: `IF: approved?` output branch `1` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: request.promotion` branch `0` -> `Code: validate.request`
- `Code: validate.request` branch `0` -> `HTTP: dryrun.promote`
- `HTTP: dryrun.promote` branch `0` -> `Code: summarize.plan`
- `Code: summarize.plan` branch `0` -> `Webhook: await.approval`
- `Webhook: await.approval` branch `0` -> `IF: approved?`
- `IF: approved?` branch `0` -> `HTTP: real.promote`
- `IF: approved?` branch `1` -> `Respond: rejected`
- `HTTP: real.promote` branch `0` -> `HTTP: rebuild.manifest`
- `HTTP: rebuild.manifest` branch `0` -> `HTTP: emit.completed`
- `HTTP: emit.completed` branch `0` -> `Respond: success`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
