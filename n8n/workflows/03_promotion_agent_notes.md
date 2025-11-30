# Agent 3 — Promotion / Curation Agent (Workflow `03_promotion_agent.json`)

Rusty, here's the node-by-node breakdown for the promotion workflow. As with the ingest and labeling notes, this starts with an alphabetical node inventory, then details each node's inputs plus key parameters. Dynamic parameters are shown as JSON for easy pasting into n8n.

## Alphabetical inventory of nodes (workflow scope)
- Code: summarize.plan
- Code: validate.request
- HTTP: dryrun.promote
- HTTP: emit.completed
- HTTP: real.promote
- HTTP: rebuild.manifest
- IF: approved?
- Respond: rejected
- Respond: success
- Webhook: await.approval
- Webhook: request.promotion

---

## Node-by-node flow details
The promotion webhook validates the request, runs a dry-run promotion via Media Mover, summarizes the plan, then blocks for an approval webhook. Approved requests perform the real promotion, rebuild manifests, and emit an event before responding. Rejected approvals end the flow with a 403 JSON response.

### Webhook node
**Webhook: request.promotion** — Entry point for promotion requests (`video_id`, `label`, optional `target`/`dest_split`, `correlation_id`, `idempotency_key`). Forwards body + headers to the validation code node. Response is deferred to the final respond node.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "promotion/v1",
  "responseMode": "responseNode",
  "options": {}
}
```

### Code nodes
**Code: validate.request** — Validates required fields (`video_id`, `label`), enforces allowed targets (`train`, `test`), and normalizes fields. Generates a deterministic idempotency key (SHA-256 hash of `video_id|target|label`) when absent, sets `correlation_id` if missing, and marks the request as `dry_run: true` for the first HTTP call.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Validate promotion request\nconst body = $json.body ?? $json;\nconst required = ['video_id', 'label'];\n\nfor (const field of required) {\n  if (!body[field]) {\n    throw new Error(`Missing required field: ${field}`);\n  }\n}\n\nconst allowedSplits = ['train', 'test'];\nconst target = body.target || body.dest_split || 'train';\n\nif (!allowedSplits.includes(target)) {\n  throw new Error(`Invalid target split: ${target}`);\n}\n\n// Generate stable idempotency key\nconst crypto = require('crypto');\nconst idem = body.idempotency_key || crypto.createHash('sha256')\n  .update(`${body.video_id}|${target}|${body.label}`)\n  .digest('hex').slice(0, 32);\n\nreturn [{\n  json: {\n    video_id: body.video_id,\n    label: body.label,\n    target,\n    idempotency_key: idem,\n    correlation_id: body.correlation_id || `promo-${Date.now()}`,\n    dry_run: true  // Start with dry-run\n  }\n}];"
}
```

**Code: summarize.plan** — Takes the Media Mover dry-run response and crafts a concise approval payload. It threads through the original request details (video, label, target) and surfaces the dry-run plan (moves, DB updates, conflicts, dry-run status) for the approver webhook.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Summarize dry-run plan for approval\nconst plan = $json;\n\nreturn [{\n  json: {\n    approval_request: {\n      title: 'Video Promotion Request',\n      video_id: $('validate_request').item.json.video_id,\n      label: $('validate_request').item.json.label,\n      target_split: $('validate_request').item.json.target,\n      plan_summary: {\n        will_move: plan.moves || [],\n        will_update_db: plan.will_update_db !== false,\n        conflicts: plan.conflicts || [],\n        dry_run_status: plan.status\n      },\n      correlation_id: $('validate_request').item.json.correlation_id,\n      idempotency_key: $('validate_request').item.json.idempotency_key\n    }\n  }\n}];"
}
```

### HTTP Request nodes
**HTTP: dryrun.promote** — Calls Media Mover with `dry_run: true` to preview the promotion. Sends idempotency and correlation headers; body includes `video_id`, desired `dest_split`, label, and `dry_run` flag. Output feeds the summarize.plan code node.

Dynamic parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Idempotency-Key", "value": "={{$json.idempotency_key}}" }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "video_id", "value": "={{$json.video_id}}" },
      { "name": "dest_split", "value": "={{$json.target}}" },
      { "name": "label", "value": "={{$json.label}}" },
      { "name": "dry_run", "value": "=true" },
      { "name": "correlation_id", "value": "={{$json.correlation_id}}" }
    ]
  }
}
```

**HTTP: real.promote** — Executes the approved promotion (`dry_run: false`) using the approver's payload. Uses idempotency header and sends `video_id`, `dest_split`, `label`, and `correlation_id`. Success flows into manifest rebuild.

Dynamic parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Idempotency-Key", "value": "={{$json.idempotency_key}}" }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "video_id", "value": "={{$json.video_id}}" },
      { "name": "dest_split", "value": "={{$json.target_split}}" },
      { "name": "label", "value": "={{$json.label}}" },
      { "name": "dry_run", "value": "=false" },
      { "name": "correlation_id", "value": "={{$json.correlation_id}}" }
    ]
  }
}
```

**HTTP: rebuild.manifest** — Triggers Media Mover to rebuild both `train` and `test` manifests after a successful promotion. Sends `X-Correlation-ID` header and a JSON body listing the splits. Output provides `dataset_hash` for the event emitter.

Dynamic parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/manifest/rebuild",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "X-Correlation-ID", "value": "={{$json.correlation_id}}" }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "splits", "value": "=[\"train\", \"test\"]" }
    ]
  }
}
```

**HTTP: emit.completed** — Notifies the Gateway service of a completed promotion. Uses the rebuilt manifest hash plus promotion details.

Dynamic parameters:
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/promotion",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "event_type", "value": "=promotion.completed" },
      { "name": "video_id", "value": "={{$json.video_id}}" },
      { "name": "dest_split", "value": "={{$json.target_split}}" },
      { "name": "label", "value": "={{$json.label}}" },
      { "name": "correlation_id", "value": "={{$json.correlation_id}}" },
      { "name": "dataset_hash", "value": "={{$('http_rebuild_manifest').item.json.dataset_hash}}" }
    ]
  }
}
```

### Approval gate
**Webhook: await.approval** — Waits for a POST approval decision (expects a boolean `approved` plus passthrough correlation/idempotency fields). Feeds directly into the IF node.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "promotion/approve",
  "responseMode": "onReceived",
  "options": {}
}
```

**IF: approved?** — Routes based on the approver payload. `approved: true` continues to the real promotion; `approved: false` returns a rejection response.

Dynamic parameters:
```json
{
  "conditions": {
    "boolean": [
      { "value1": "={{$json.approved}}", "value2": true }
    ]
  }
}
```

### Respond nodes
**Respond: success** — Final JSON response to the original promotion request, returning status, video ID, destination split, manifest hash, and correlation ID after the event is emitted.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"success\",\n  \"video_id\": $json.video_id,\n  \"dest_split\": $json.target_split,\n  \"dataset_hash\": $json.dataset_hash,\n  \"correlation_id\": $json.correlation_id\n} }}"
}
```

**Respond: rejected** — Response for denied approvals; returns a 403 status with a rejection message and correlation ID.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"rejected\",\n  \"message\": \"Promotion not approved\",\n  \"correlation_id\": $json.correlation_id\n} }}",
  "options": { "responseCode": 403 }
}
```

### Flow wiring (inputs between nodes)
- Webhook `request.promotion` → Code `validate.request` → HTTP `dryrun.promote` → Code `summarize.plan` → Webhook `await.approval` → IF `approved?`.
- IF `approved?` (true) → HTTP `real.promote` → HTTP `rebuild.manifest` → HTTP `emit.completed` → Respond `success`.
- IF `approved?` (false) → Respond `rejected`.
