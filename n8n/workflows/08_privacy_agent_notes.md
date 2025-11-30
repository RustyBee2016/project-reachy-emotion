# Agent 8 — Privacy / Retention Agent (Workflow `08_privacy_agent.json`)

Rusty, this note mirrors the privacy/retention workflow so you can recreate it in n8n. It starts with an alphabetical node inventory, then details each node's inputs, parameters (JSON snippets you can paste), and how the purge loop runs from both the nightly schedule and manual GDPR requests.

## Alphabetical inventory of nodes (workflow scope)
- HTTP: emit.purged
- Loop: batch.delete
- Postgres: audit.log
- Postgres: find.old_temp
- Postgres: mark.purged
- SSH: delete.file
- Schedule: daily 03:00
- Webhook: gdpr.deletion

---

## Node-by-node flow details
The workflow locates stale temp videos (or ones specified by a manual GDPR call), deletes them from disk in batches, marks the rows as `purged`, logs the action, emits a purge event, and loops until the batch source is exhausted.

### Schedule node
**Schedule: daily 03:00** — Nightly trigger that starts the purge cycle automatically. It injects an empty payload and passes control to the DB selector.

Parameters:
```json
{ "rule": { "interval": [{ "field": "cronExpression", "expression": "0 3 * * *" }] } }
```

### Webhook node
**Webhook: gdpr.deletion** — Manual POST hook (`/privacy/purge`) to force a purge run, typically when responding to GDPR/PII requests. The incoming request body is forwarded to the same DB query node as the schedule trigger.

Parameters:
```json
{ "httpMethod": "POST", "path": "privacy/purge", "responseMode": "responseNode" }
```

### Postgres nodes
**Postgres: find.old_temp** — Selects temp-split videos older than 14 days for deletion. It consumes whichever trigger fired (schedule or webhook) but ignores the payload; the result set becomes the batch input.

Parameters:
```json
{
  "operation": "executeQuery",
  "query": "SELECT video_id, file_path FROM video WHERE split='temp' AND created_at < NOW() - INTERVAL '14 days';"
}
```

**Postgres: mark.purged** — After a file is removed, updates the DB row to reflect the purge. It reads `video_id` from the loop item to run the update.

Parameters:
```json
{
  "operation": "executeQuery",
  "query": "UPDATE video SET split='purged', updated_at=NOW() WHERE video_id='{{$json.video_id}}'::uuid;"
}
```

**Postgres: audit.log** — Records each deletion in `audit_log` so you have an immutable trail (action, video_id, reason, timestamp). It receives the same loop item after the DB update.

Parameters:
```json
{ "operation": "insert", "table": "audit_log", "columns": "action, video_id, reason, timestamp" }
```

### Loop node
**Loop: batch.delete** — Splits the selected rows into batches of 50 and provides each item to the deletion path. After audit logging, the loop node re-enters itself to continue until no items remain.

Parameters:
```json
{ "batchSize": 50, "options": {} }
```

### SSH node
**SSH: delete.file** — Removes the video file from disk using the `file_path` field for each looped item. It receives one item at a time from the batch node.

Parameters:
```json
{ "command": "rm -f /videos/{{$json.file_path}}", "authentication": "password" }
```

### HTTP node
**HTTP: emit.purged** — Emits an event to Gateway after audit logging to signal how many items were purged. It uses the loop batch size for the `count` field so downstream services know the volume of the purge run.

Parameters:
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/privacy",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "event_type", "value": "=privacy.purged" },
      { "name": "count", "value": "={{$('split_batches').params.batchSize}}" }
    ]
  }
}
```

### Flow wiring (inputs between nodes)
- **Schedule daily 03:00** → Postgres find.old_temp.
- **Webhook gdpr.deletion** → Postgres find.old_temp (shares the same path as the schedule).
- **Postgres find.old_temp** → Loop batch.delete.
- **Loop batch.delete** → SSH delete.file → Postgres mark.purged → Postgres audit.log.
- **Postgres audit.log** → Loop batch.delete (to fetch next batch) **and** HTTP emit.purged (after each batch/record) to notify downstream systems.

This flow ensures stale or manually requested items are purged consistently: triggers gather candidates, batches iterate them, files are deleted, database state is updated, each action is audited, and a purge event is emitted for observability.
