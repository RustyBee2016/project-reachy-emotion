# Agent 1 — Ingest Agent (Workflow `01_ingest_agent.json`)

Rusty, this walkthrough mirrors the prior agent notes: alphabetical node inventory first, then per-node inputs and parameter JSON you can paste back into n8n. It explains the control flow so you can rebuild or audit the webhook → Media Mover pull → polling loop → DB insert → event emission sequence without guessing.

## Alphabetical inventory of nodes (workflow scope)
- Code: increment.attempt
- Code: normalize.payload
- HTTP: check.status
- HTTP: emit.completed
- HTTP: media.pull
- IF: auth.check
- IF: status.done?
- Postgres: insert.video
- Respond: 401 Unauthorized
- Respond: success
- Wait: 3s
- Webhook: ingest.video

---

## Node-by-node flow details
The workflow authenticates inbound webhook calls, normalizes payloads, submits a Media Mover pull job, polls the status URL until completion, inserts the new video row in Postgres, emits an ingest event to Gateway, and replies to the caller.

### Webhook node
**Webhook: ingest.video** — Entry point that receives the HTTP POST from the UI or generator. It forwards the full request (body + headers) to the auth check.

Parameters:
```json
{ "httpMethod": "POST", "path": "video_gen_hook", "responseMode": "onReceived", "options": { "responseCode": 202 } }
```

### IF nodes
**IF: auth.check** — Consumes the webhook item. It compares the `x-ingest-key` header against the `INGEST_TOKEN` environment variable; true continues to normalization, false returns 401.

Dynamic condition JSON:
```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{$json.headers['x-ingest-key']}}",
        "operation": "equals",
        "value2": "={{$env.INGEST_TOKEN}}"
      }
    ]
  }
}
```

**IF: status.done?** — Reads the latest Media Mover status payload and checks whether `status` equals `"done"`. True proceeds to DB insert; false loops through the increment + wait path to poll again.

Parameters:
```json
{ "conditions": { "string": [{ "value1": "={{$json.status}}", "operation": "equals", "value2": "done" }] } }
```

### Code nodes
**Code: normalize.payload** — Takes the authorized webhook JSON and normalizes multiple possible shapes into one payload (source URL, optional label, metadata, correlation/idempotency keys, timestamp). Throws if the source URL is missing.

Parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Normalize incoming payload from various sources\nconst body = $json.body ?? $json;\nconst sourceUrl = body.source_url ?? body.url ?? body.asset?.url ?? body.data?.asset?.url;\n\nif (!sourceUrl) {\n  throw new Error('Missing source_url in request body');\n}\n\nconst label = body.label ?? body.emotion ?? null;\nconst meta = body.meta ?? { \n  generator: body.generator ?? body.source ?? 'unknown' \n};\nconst correlationId = $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`;\nconst idempotencyKey = $json.headers?.['idempotency-key'] ?? `idem-${Date.now()}`;\n\nreturn [\n  {\n    json: {\n      source_url: sourceUrl,\n      label,\n      meta,\n      correlation_id: correlationId,\n      idempotency_key: idempotencyKey,\n      timestamp: new Date().toISOString()\n    }\n  }\n];"
}
```

**Code: increment.attempt** — Runs when the status check isn’t done. It bumps the `attempt` counter (default starting at 1) and loops the item back to the wait node unless the cap (20) is reached, in which case it throws to stop the workflow.

Parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Loop back to wait if not done yet\nconst maxAttempts = 20;\nconst currentAttempt = $json.attempt ?? 1;\n\nif (currentAttempt >= maxAttempts) {\n  throw new Error('Max polling attempts reached');\n}\n\nreturn [{\n  json: {\n    ...items[0].json,\n    attempt: currentAttempt + 1\n  }\n}];"
}
```

### HTTP Request nodes
**HTTP: media.pull** — Submits a pull job to Media Mover with idempotency and correlation headers. Body includes source URL, optional label, and flags to compute thumbnail and ffprobe metadata. It expects `status_url` plus file/hash metadata in the response.

Parameters:
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Idempotency-Key", "value": "={{$json.idempotency_key}}" },
      { "name": "X-Correlation-ID", "value": "={{$json.correlation_id}}" }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "source_url", "value": "={{$json.source_url}}" },
      { "name": "label", "value": "={{$json.label}}" },
      { "name": "correlation_id", "value": "={{$json.correlation_id}}" },
      { "name": "compute_thumb", "value": "=true" },
      { "name": "ffprobe", "value": "=true" },
      { "name": "dest_split", "value": "=temp" }
    ]
  },
  "options": { "timeout": 120000 }
}
```

**HTTP: check.status** — Polls the Media Mover `status_url` to see when the pull job completes. Uses the same header auth credential. The response feeds the status IF node.

Parameters:
```json
{ "url": "={{$json.status_url}}", "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "options": {} }
```

**HTTP: emit.completed** — After the DB insert succeeds, it posts an `ingest.completed` event to Gateway with identifiers and paths so downstream agents can react.

Parameters:
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/ingest",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "event_type", "value": "=ingest.completed" },
      { "name": "video_id", "value": "={{$json.video_id}}" },
      { "name": "correlation_id", "value": "={{$json.correlation_id}}" },
      { "name": "file_path", "value": "={{$json.file_path}}" },
      { "name": "sha256", "value": "={{$json.sha256}}" }
    ]
  }
}
```

### Wait node
**Wait: 3s** — Simple delay to give Media Mover time to enqueue/process before the first poll. Receives the Media Mover response item and passes it onward to the status check.

Parameters:
```json
{ "amount": 3, "unit": "seconds" }
```

### Postgres node
**Postgres: insert.video** — Inserts the completed ingest record into the `video` table, populating split `temp`, label, dimensions, duration, size, and checksum. Uses `ON CONFLICT (sha256, size_bytes) DO NOTHING` for idempotency and returns `video_id`.

Parameters:
```json
{
  "operation": "executeQuery",
  "query": "INSERT INTO video (video_id, file_path, split, label, duration_sec, fps, width, height, size_bytes, sha256, created_at, updated_at)\nVALUES (\n  '{{$json.video_id}}',\n  '{{$json.file_path}}',\n  'temp',\n  '{{$json.label}}',\n  {{$json.ffprobe.duration}},\n  {{$json.ffprobe.fps}},\n  {{$json.ffprobe.width}},\n  {{$json.ffprobe.height}},\n  {{$json.size_bytes}},\n  '{{$json.sha256}}',\n  NOW(),\n  NOW()\n)\nON CONFLICT (sha256, size_bytes) DO NOTHING\nRETURNING video_id;",
  "options": {}
}
```

### Respond nodes
**Respond: success** — Final webhook reply on the happy path. Sends JSON with status, video_id, and correlation_id back to the caller.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\"status\": \"success\", \"video_id\": $json.video_id, \"correlation_id\": $json.correlation_id} }}"
}
```

**Respond: 401 Unauthorized** — Runs on the failed auth branch and returns a structured JSON error with HTTP 401.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\"error\": \"unauthorized\", \"message\": \"Invalid or missing X-INGEST-KEY header\"} }}",
  "options": { "responseCode": 401 }
}
```

### Flow wiring (inputs between nodes)
- **Webhook ingest.video** → **IF auth.check** (true goes right; false goes to Respond 401).
- **auth.check (true)** → **Code normalize.payload** → **HTTP media.pull** → **Wait 3s** → **HTTP check.status** → **IF status.done?**.
- **status.done? (true)** → **Postgres insert.video** → **HTTP emit.completed** → **Respond success**.
- **status.done? (false)** → **Code increment.attempt** → loop back to **Wait 3s** for another poll.

This mirrors the production ingest path: authenticate, normalize the payload, submit the pull, poll until `done`, write the record, emit the event, and answer the caller. The increment + wait loop bounds polling to 20 tries to avoid runaway executions.
