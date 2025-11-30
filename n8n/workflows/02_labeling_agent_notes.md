# Agent 2 — Labeling Agent (Workflow `02_labeling_agent.json`)

Rusty, this mirrors the structure used for the ingest agent notes: a node inventory followed by per-node inputs and parameter JSON snippets. Dynamic parameters stay in JSON for easy import into n8n.

## Alphabetical inventory of nodes (workflow scope)
- Code: validate.payload
- HTTP: mm.promote
- HTTP: mm.relabel
- Postgres: apply.label
- Postgres: class.balance
- Postgres: fetch.video
- Respond: success
- Switch: branch.action
- Webhook: label.submitted

---

## Node-by-node flow details
The flow starts with the labeling webhook, validates inputs, fetches the video record, writes the label event, then branches based on the requested action (label-only, promote to train/test, or discard). All branches converge on class balance reporting before returning a response.

### Webhook node
**Webhook: label.submitted** — Receives UI POST requests containing `video_id`, `label`, `action`, optional `notes`, and `rater_id`. Forwards the body and headers to the validation code node.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "label",
  "responseMode": "responseNode",
  "options": {}
}
```

### Code node
**Code: validate.payload** — Validates the request, enforcing allowed labels (`happy`, `sad`, `angry`, `neutral`, `surprise`, `fearful`) and actions (`label_only`, `promote_train`, `promote_test`, `discard`). Normalizes casing, fills defaults (`action` defaults to `label_only`, `rater_id` defaults to `anonymous`), and generates `idempotency_key` plus `correlation_id` when missing. Emits a single normalized item for downstream nodes.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Validate and normalize label submission\nconst body = $json.body ?? $json;\nconst allowedLabels = new Set(['happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful']);\nconst allowedActions = new Set(['label_only', 'promote_train', 'promote_test', 'discard']);\n\nfunction uuidv4() {\n  return crypto.randomUUID ? crypto.randomUUID() : \n    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {\n      const r = (Math.random() * 16) | 0;\n      const v = c === 'x' ? r : (r & 0x3 | 0x8);\n      return v.toString(16);\n    });\n}\n\nconst video_id = body.video_id;\nconst label = (body.label || '').toLowerCase();\nconst action = body.action || 'label_only';\nconst rater_id = body.rater_id || 'anonymous';\nconst notes = body.notes || '';\nconst idempotency_key = body.idempotency_key || uuidv4();\n\nif (!video_id) throw new Error('video_id required');\nif (!allowedLabels.has(label)) throw new Error(`Invalid label: ${label}`);\nif (!allowedActions.has(action)) throw new Error(`Invalid action: ${action}`);\n\nreturn [{\n  json: {\n    video_id,\n    label,\n    action,\n    rater_id,\n    notes,\n    idempotency_key,\n    correlation_id: body.correlation_id || `label-${Date.now()}`\n  }\n}];"
}
```

### Postgres nodes
**Postgres: fetch.video** — Retrieves the target video row to confirm it exists and to capture current split/label before modification.

Query:
```json
{
  "operation": "executeQuery",
  "query": "SELECT v.video_id, v.split, v.label AS current_label, v.file_path\nFROM video v\nWHERE v.video_id = '{{$json.video_id}}'::uuid;",
  "options": {}
}
```

**Postgres: apply.label** — Writes a `label_event` with idempotency protection and updates the video’s `label` and `updated_at`. Returns the `event_id` (if inserted) plus the updated video metadata.

Query:
```json
{
  "operation": "executeQuery",
  "query": "WITH ins AS (\n  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)\n  VALUES (\n    '{{$json.video_id}}'::uuid,\n    '{{$json.label}}',\n    '{{$json.action}}',\n    '{{$json.rater_id}}',\n    '{{$json.notes}}',\n    '{{$json.idempotency_key}}'\n  )\n  ON CONFLICT (video_id, idempotency_key) DO NOTHING\n  RETURNING event_id\n)\nUPDATE video\nSET label = '{{$json.label}}',\n    updated_at = NOW()\nWHERE video_id = '{{$json.video_id}}'::uuid\nRETURNING \n  video_id, \n  label, \n  split,\n  (SELECT event_id FROM ins) AS event_id;",
  "options": {}
}
```

**Postgres: class.balance** — Aggregates training split counts for `happy` and `sad` to keep the UI informed about balance and totals.

Query:
```json
{
  "operation": "executeQuery",
  "query": "SELECT \n  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,\n  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,\n  COUNT(*) FILTER (WHERE split = 'train') AS total_train\nFROM video;",
  "options": {}
}
```

### Switch node
**Switch: branch.action** — Routes based on the requested `action` key from the validated payload:
- `label_only` → relabel only (no promotion)
- `promote_train` → promote to train split
- `promote_test` → promote to test split
- `discard` → skip Media Mover calls and go straight to balance reporting

Parameters:
```json
{
  "rules": {
    "values": [
      {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "label_only"}]}, "renameOutput": true, "outputKey": "label_only"},
      {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "promote_train"}]}, "renameOutput": true, "outputKey": "promote_train"},
      {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "promote_test"}]}, "renameOutput": true, "outputKey": "promote_test"},
      {"conditions": {"string": [{"value1": "={{$json.action}}", "value2": "discard"}]}, "renameOutput": true, "outputKey": "discard"}
    ]
  }
}
```

### HTTP Request nodes
**HTTP: mm.relabel** — For `label_only` branch: calls Media Mover’s relabel endpoint with idempotency and correlation headers, updating metadata without moving the file.

Parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]},
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {"name": "video_id", "value": "={{$json.video_id}}"},
      {"name": "label", "value": "={{$json.label}}"},
      {"name": "correlation_id", "value": "={{$json.correlation_id}}"}
    ]
  }
}
```

**HTTP: mm.promote** — For `promote_train`/`promote_test` branches: promotes the video to the requested split via Media Mover with idempotency and correlation metadata. Sets `dry_run` to `false` so the move is executed.

Parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {"parameters": [{"name": "Idempotency-Key", "value": "={{$json.idempotency_key}}"}]},
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {"name": "video_id", "value": "={{$json.video_id}}"},
      {"name": "dest_split", "value": "={{$json.action === 'promote_train' ? 'train' : 'test'}}"},
      {"name": "label", "value": "={{$json.label}}"},
      {"name": "correlation_id", "value": "={{$json.correlation_id}}"},
      {"name": "dry_run", "value": "=false"}
    ]
  }
}
```

### Respond node
**Respond: success** — Final webhook response aggregates the latest class balance alongside the video/action echoes and correlation id. Balance is considered “balanced” when happy vs sad counts differ by ≤ 5.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"success\",\n  \"video_id\": $json.video_id,\n  \"label\": $json.label,\n  \"action\": $json.action,\n  \"class_balance\": {\n    \"happy\": $json.happy_count,\n    \"sad\": $json.sad_count,\n    \"total_train\": $json.total_train,\n    \"balanced\": Math.abs($json.happy_count - $json.sad_count) <= 5\n  },\n  \"correlation_id\": $json.correlation_id\n} }}"
}
```

### Flow wiring
- Webhook → Code validate.payload → Postgres fetch.video → Postgres apply.label → Switch branch.action.
- `label_only` branch: Switch → HTTP mm.relabel → Postgres class.balance → Respond success.
- `promote_train`/`promote_test` branches: Switch → HTTP mm.promote → Postgres class.balance → Respond success.
- `discard` branch: Switch → Postgres class.balance → Respond success.
