# MODULE 08 — Privacy / Retention Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/08_privacy_agent.json`

## Runtime Goal
Purge stale temp media (scheduled or manual), mark DB state, audit deletion, and emit privacy events.

## Node-to-Script Map

### 1) `Schedule: daily 03:00` (`Schedule Trigger`)
- **Workflow role:** automatic retention run trigger.
- **Cron expression:** `0 3 * * *`.

### 2) `Webhook: gdpr.deletion` (`Webhook`)
- **Workflow role:** manual purge trigger.
- **Path/method:** `POST /webhook/privacy/purge`.

### 3) `Postgres: find.old_temp` (`Postgres`)
- **Workflow role:** finds purge candidates.
- **SQL:** `video` rows where `split='temp'` and `created_at < now()-7 days`.
- **Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

### 4) `Loop: batch.delete` (`Split In Batches`)
- **Workflow role:** process rows in chunks of 50.
- **Control flow:** loops until all candidates consumed.

### 5) `SSH: delete.file` (`SSH`)
- **Workflow role:** physical file deletion.
- **Command:** `rm -f /videos/{{$json.file_path}}`.
- **Side effect:** filesystem mutation only; no DB update yet.

### 6) `Postgres: mark.purged` (`Postgres`)
- **Workflow role:** marks DB row as purged after delete.
- **SQL:** `UPDATE video SET split='purged', updated_at=NOW() ...`.
- **Constraint coupling:** aligns with `chk_video_split_label_policy` (`models.py:95`) where non-train rows must be unlabeled.

### 7) `Postgres: audit.log` (`Postgres`)
- **Workflow role:** inserts audit row per purge operation.
- **Table:** `audit_log`.
- **Schema binding:** `AuditLog` model (`models.py:344`).

### 8) `HTTP: emit.purged` (`HTTP Request`)
- **Workflow role:** emits `privacy.purged` pipeline event.
- **HTTP target:** `POST {{$env.GATEWAY_BASE_URL}}/api/events/pipeline`
- **Backend binding:** `apps/api/routers/gateway.py:346` `post_pipeline_event(...)`.

## How This Delivers Privacy Functionality
1. Enumerates stale temp assets via DB policy query.
2. Deletes files in bounded batches.
3. Marks records as purged and records audit metadata.
4. Emits privacy events for observability/traceability.

## Related Script Functions Not Directly Called by This Workflow
- `apps/api/app/routers/gateway_upstream.py:437` `redact_video(...)` provides API-level redact path (delete file + thumbnail + audit), but this workflow currently uses raw SSH + SQL path instead.

## Operational Caveat
- `SSH: delete.file` runs a direct `rm -f` on DB-derived path. Keep DB path hygiene strict; malformed `file_path` values can cause unintended deletions.
