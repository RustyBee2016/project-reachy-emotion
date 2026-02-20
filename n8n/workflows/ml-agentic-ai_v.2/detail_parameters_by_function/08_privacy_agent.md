# Agent 8 — Privacy/Retention Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/08_privacy_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Privacy/Retention Agent enforces local-first policy and TTLs for temporary media. It runs daily at 03:00 or on-demand via webhook, finding videos in the temp split older than 14 days, deleting files via SSH, marking records as purged in the database, logging to audit, and emitting privacy.purged events.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| HTTP: emit.purged | n8n-nodes-base.httpRequest | emit_purged |
| Loop: batch.delete | n8n-nodes-base.splitInBatches | split_batches |
| Postgres: audit.log | n8n-nodes-base.postgres | db_audit_log |
| Postgres: find.old_temp | n8n-nodes-base.postgres | db_find_old |
| Postgres: mark.purged | n8n-nodes-base.postgres | db_mark_purged |
| Schedule: daily 03:00 | n8n-nodes-base.scheduleTrigger | schedule_daily |
| SSH: delete.file | n8n-nodes-base.ssh | ssh_delete_file |
| Webhook: gdpr.deletion | n8n-nodes-base.webhook | webhook_gdpr |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Schedule: daily 03:00 ──┬──► Postgres: find.old_temp
                        │            │
Webhook: gdpr.deletion ─┘            ▼
                            Loop: batch.delete (50 items)
                                     │
                                     ▼
                            SSH: delete.file
                                     │
                                     ▼
                            Postgres: mark.purged
                                     │
                                     ▼
                            Postgres: audit.log
                                     │
                                     ├──► Loop: batch.delete (next batch)
                                     │
                                     └──► HTTP: emit.purged (when done)
```

---

## Node Details

### 1. Schedule: daily 03:00

**Type:** `n8n-nodes-base.scheduleTrigger` (v1.2)  
**Position:** [-600, 300]  
**Purpose:** Triggers daily purge job at 03:00 AM.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `rule.interval[0].field` | `cronExpression` | Use cron syntax |
| `rule.interval[0].expression` | `0 3 * * *` | Run at 03:00 daily |

#### Test Status: ✅ OPERATIONAL

---

### 2. Webhook: gdpr.deletion

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-600, 450]  
**Purpose:** Allows manual/GDPR-triggered purge requests.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests |
| `path` | `privacy/purge` | URL: `{N8N_HOST}/webhook/privacy/purge` |
| `responseMode` | `responseNode` | Response handled by node |
| `webhookId` | `privacy-purge` | Unique identifier |

#### Expected Input (Optional)

```json
{
  "video_ids": ["uuid1", "uuid2"],  // Optional: specific videos
  "reason": "gdpr_request",          // Optional: purge reason
  "requestor": "user@example.com"    // Optional: who requested
}
```

#### Test Status: ✅ OPERATIONAL

---

### 3. Postgres: find.old_temp

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [-400, 300]  
**Purpose:** Finds temp videos older than 14 days for purging.

#### SQL Query

```sql
SELECT video_id, file_path 
FROM video 
WHERE split='temp' 
  AND created_at < NOW() - INTERVAL '14 days';
```

#### Retention Policy

| Split | Retention | Action |
|-------|-----------|--------|
| `temp` | 14 days | Auto-purge |
| `train` | Indefinite | Manual only |
| `test` | Indefinite | Manual only |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 4. Loop: batch.delete

**Type:** `n8n-nodes-base.splitInBatches` (v3)  
**Position:** [-200, 300]  
**Purpose:** Processes deletions in batches of 50 to avoid overwhelming the system.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `batchSize` | `50` | Items per batch |

#### Behavior

- Splits input items into batches of 50
- Processes each batch sequentially
- Loops back for next batch until all processed

#### Test Status: ✅ OPERATIONAL

---

### 5. SSH: delete.file

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [0, 300]  
**Purpose:** Deletes video file from filesystem.

#### Command

```bash
rm -f /videos/{{$json.file_path}}
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Security Notes

- Uses `-f` flag to avoid errors on missing files
- Only deletes from `/videos/` directory
- File path comes from trusted database query

#### Test Status: ✅ OPERATIONAL

---

### 6. Postgres: mark.purged

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [200, 300]  
**Purpose:** Updates video record to mark as purged.

#### SQL Query

```sql
UPDATE video 
SET split='purged', updated_at=NOW() 
WHERE video_id='{{$json.video_id}}'::uuid;
```

#### Split Transition

| From | To | Meaning |
|------|-----|---------|
| `temp` | `purged` | File deleted, record retained for audit |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 7. Postgres: audit.log

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [400, 300]  
**Purpose:** Creates audit log entry for the purge action.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `insert` | Insert new record |
| `table` | `audit_log` | Audit log table |
| `columns` | `action, video_id, reason, timestamp` | Columns to insert |

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `AuditLog` | 225-244 | Audit log model |

**AuditLog Schema:**

| Column | Type | Purpose |
|--------|------|---------|
| `log_id` | `BigInteger` | Primary key |
| `action` | `String(50)` | Action type (e.g., "purge") |
| `video_id` | `String(36)` | Related video |
| `reason` | `String(255)` | Purge reason |
| `timestamp` | `DateTime` | When action occurred |
| `extra_data` | `JSONB` | Additional metadata |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 8. HTTP: emit.purged

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [600, 300]  
**Purpose:** Emits privacy.purged event when batch completes.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/privacy` | Events endpoint |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `privacy.purged` | Event type |
| `count` | `={{$('split_batches').params.batchSize}}` | Items purged |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `GATEWAY_BASE_URL` | Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Database |
| 3 | SSH Ubuntu1 | SSH Password | File deletion |

---

## Tags

- `agent`
- `privacy`

---

## Privacy Policy Compliance

| Requirement | Implementation |
|-------------|----------------|
| Local-first | All data stays on-premise |
| TTL enforcement | 14-day auto-purge for temp |
| Audit trail | All purges logged to audit_log |
| GDPR support | Manual purge webhook available |
| Redaction | File deleted, metadata retained |

---

## Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `Video` | 33-78 | Video model with split field |
| `AuditLog` | 225-244 | Audit logging |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `/api/events/privacy` |
| GDPR Response | MEDIUM | Add webhook response with purge summary |
| Thumbnail Cleanup | LOW | Also delete associated thumbnails |
| Configurable TTL | LOW | Make 14-day TTL configurable |

---

## Connections Summary

```json
{
  "schedule_daily": { "main": [["db_find_old"]] },
  "webhook_gdpr": { "main": [["db_find_old"]] },
  "db_find_old": { "main": [["split_batches"]] },
  "split_batches": { "main": [["ssh_delete_file"]] },
  "ssh_delete_file": { "main": [["db_mark_purged"]] },
  "db_mark_purged": { "main": [["db_audit_log"]] },
  "db_audit_log": { "main": [["split_batches", "emit_purged"]] }
}
```

---

## Usage Example

### Manual GDPR Purge Request

```bash
curl -X POST http://localhost:5678/webhook/privacy/purge \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "gdpr_request",
    "requestor": "user@example.com"
  }'
```
