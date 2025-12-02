# Module 5: Privacy Agent — TTL Enforcement, Batch Processing & Audit Logging

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~2 hours  
**Prerequisites**: Completed Modules 0-4

---

## Learning Objectives

By the end of this module, you will:
1. Implement **TTL (Time-To-Live) enforcement** for temporary data
2. Use the **Split In Batches** node for controlled bulk operations
3. Create **audit log entries** for compliance
4. Handle **GDPR-style purge requests** via webhook
5. Understand **soft delete patterns** (marking vs. deleting)

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **TTL enforcement** | SQL date comparison | Auto-cleanup old data |
| **Batch processing** | Split In Batches | Prevent system overload |
| **Soft delete** | split='purged' | Audit trail preservation |
| **Audit logging** | Postgres INSERT | Compliance requirements |
| **GDPR purge** | Manual webhook | User data deletion rights |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Schedule: daily 03:00 | n8n scheduler | ⬜ (native) |
| 2 | Webhook: gdpr.deletion | n8n webhook | ⬜ (native) |
| 3 | Postgres: find.old_temp | PostgreSQL query | ⬜ |
| 4 | Loop: batch.delete | Split In Batches | ⬜ (native) |
| 5 | SSH: delete.file | SSH to Ubuntu1 | ⬜ |
| 6 | Postgres: mark.purged | PostgreSQL UPDATE | ⬜ |
| 7 | Postgres: audit.log | PostgreSQL INSERT | ⬜ |
| 8 | HTTP: emit.purged | Gateway events API | ⬜ |

---

### Verification Procedures

#### Test 1: Find Old Temp Videos Query

```sql
-- Check for videos older than 14 days in temp
SELECT video_id, file_path, created_at
FROM video 
WHERE split='temp' 
  AND created_at < NOW() - INTERVAL '14 days';
```

**Status**: ⬜ → [ ] Complete

---

#### Test 2: Audit Log Table Exists

```sql
-- Check audit_log table structure
\d audit_log

-- If missing, create it:
CREATE TABLE IF NOT EXISTS audit_log (
  log_id BIGSERIAL PRIMARY KEY,
  action VARCHAR(50) NOT NULL,
  video_id VARCHAR(36),
  reason VARCHAR(255),
  actor VARCHAR(255),
  extra_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Status**: ⬜ → [ ] Complete

---

#### Test 3: SSH File Deletion

```bash
# Test rm command (with non-existent file - safe)
ssh rusty_admin@localhost 'rm -f /tmp/test_delete_nonexistent.mp4 && echo "OK"'
```

**Expected**: `OK` (no error even if file doesn't exist due to `-f` flag)

**Status**: ⬜ → [ ] Complete

---

## Part 1: Understanding Privacy & Retention

### Why Privacy Matters in ML

| Concern | Impact | Solution |
|---------|--------|----------|
| **Storage costs** | Temp files accumulate | Auto-purge after TTL |
| **GDPR compliance** | User deletion rights | Manual purge webhook |
| **Audit requirements** | Need deletion records | Audit log table |
| **Data minimization** | Keep only needed data | Soft delete pattern |

### The Soft Delete Pattern

Instead of permanently deleting:
1. Delete the **file** from filesystem
2. Keep the **database record** but mark as `split='purged'`
3. Log the action in **audit_log**

This preserves audit trail while removing actual data.

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PRIVACY AGENT FLOW                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Schedule: daily 03:00 ──┬──► Postgres: find.old_temp                   │
│                          │            │                                 │
│  Webhook: gdpr.deletion ─┘            ▼                                 │
│                               Loop: batch.delete (50 items)             │
│                                       │                                 │
│                                       ▼                                 │
│                               SSH: delete.file                          │
│                                       │                                 │
│                                       ▼                                 │
│                               Postgres: mark.purged                     │
│                                       │                                 │
│                                       ▼                                 │
│                               Postgres: audit.log                       │
│                                       │                                 │
│                           ┌───────────┴───────────┐                     │
│                           │                       │                     │
│                           ▼                       ▼                     │
│                   [More batches?]          HTTP: emit.purged            │
│                           │                                             │
│                           └──► Loop: batch.delete (next batch)          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 8 — Privacy Agent (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Schedule Trigger

**Node Name**: `Schedule: daily 03:00`

| Parameter | Value |
|-----------|-------|
| Trigger | `Cron` |
| Cron Expression | `0 3 * * *` |

**Why 03:00?** After reconciler (02:15), allows time for any fixes before purge.

---

### Step 3: Add GDPR Webhook

**Node Name**: `Webhook: gdpr.deletion`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `privacy/purge` |
| Response Mode | `Respond Using "Respond to Webhook" Node` |

**Expected Input**:
```json
{
  "video_ids": ["uuid1", "uuid2"],  // Optional: specific videos
  "reason": "gdpr_request",          // Optional
  "requestor": "user@example.com"    // Optional
}
```

---

### Step 4: Add Find Old Videos Query

**Node Name**: `Postgres: find.old_temp`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
SELECT video_id, file_path 
FROM video 
WHERE split='temp' 
  AND created_at < NOW() - INTERVAL '14 days';
```

**Retention Policy**:
| Split | Retention | Reason |
|-------|-----------|--------|
| `temp` | 14 days | Awaiting review |
| `train` | Indefinite | Active training data |
| `test` | Indefinite | Active test data |

---

### Step 5: Add Batch Processing

**Node Name**: `Loop: batch.delete`

The **Split In Batches** node processes items in controlled chunks.

| Parameter | Value |
|-----------|-------|
| Batch Size | `50` |

**Why Batch?**
- Prevents timeout on large datasets
- Allows progress tracking
- Reduces memory usage
- Can be interrupted/resumed

**Behavior**:
1. Takes input items (e.g., 150 videos)
2. Outputs first 50
3. When loop returns, outputs next 50
4. Continues until all processed
5. Then proceeds to "done" output

---

### Step 6: Add File Deletion

**Node Name**: `SSH: delete.file`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command**:
```bash
rm -f /media/project_data/reachy_emotion/videos/{{$json.file_path}}
```

**Command Flags**:
| Flag | Purpose |
|------|---------|
| `-f` | Force — no error if file doesn't exist |

**Security Note**: The file_path comes from a trusted database query, not user input.

---

### Step 7: Add Soft Delete (Mark as Purged)

**Node Name**: `Postgres: mark.purged`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
UPDATE video 
SET split='purged', updated_at=NOW() 
WHERE video_id='{{$json.video_id}}'::uuid
RETURNING video_id, split;
```

**Split Transition**:
```
temp ──[purge]──► purged
```

The record remains in database with `split='purged'` for audit purposes.

---

### Step 8: Add Audit Log Entry

**Node Name**: `Postgres: audit.log`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
INSERT INTO audit_log (action, video_id, reason, extra_data)
VALUES (
  'purge',
  '{{$json.video_id}}',
  'ttl_expired',
  '{"file_path": "{{$json.file_path}}", "purged_at": "{{$now.toISO()}}"}'::jsonb
)
RETURNING log_id;
```

---

### Step 9: Connect the Loop

The Split In Batches node has **two outputs**:
1. **Loop** (top): Items to process in current batch
2. **Done** (bottom): Triggered when all batches complete

**Connections**:
```
find.old_temp → batch.delete
                     │
                     ├─► [Loop] → delete.file → mark.purged → audit.log ─┐
                     │                                                    │
                     │    ◄────────────────────────────────────────────────┘
                     │    (loops back for next batch)
                     │
                     └─► [Done] → emit.purged
```

To create the loop:
1. Connect audit.log output back to batch.delete input
2. Connect batch.delete "Done" output to emit.purged

---

### Step 10: Add Event Emission

**Node Name**: `HTTP: emit.purged`

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/privacy` |

**Body**:
```json
{
  "event_type": "privacy.purged",
  "count": "={{$('Postgres: find.old_temp').all().length}}",
  "timestamp": "={{$now.toISO()}}"
}
```

---

## Part 3: GDPR Enhancement

For GDPR requests, add a Code node after the webhook to handle specific video_ids:

**Node Name**: `Code: merge.sources`

```javascript
// Handle both scheduled and GDPR-triggered purges
const webhookData = $json.body || {};
const dbResults = $('Postgres: find.old_temp').all();

// If GDPR request with specific IDs, filter to those
if (webhookData.video_ids && webhookData.video_ids.length > 0) {
  const requestedIds = new Set(webhookData.video_ids);
  return dbResults.filter(item => requestedIds.has(item.json.video_id));
}

// Otherwise, use all expired videos from query
return dbResults;
```

---

## Part 4: Testing

### Test 1: Scheduled Purge (Simulation)

Since you may not have 14-day-old data, temporarily modify the query:

```sql
-- For testing: find videos older than 1 minute
SELECT video_id, file_path 
FROM video 
WHERE split='temp' 
  AND created_at < NOW() - INTERVAL '1 minute';
```

**Remember to revert after testing!**

### Test 2: GDPR Request

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/privacy/purge \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["specific-uuid-here"],
    "reason": "gdpr_request",
    "requestor": "user@example.com"
  }'
```

### Test 3: Verify Audit Trail

```sql
SELECT * FROM audit_log 
WHERE action = 'purge' 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## Module 5 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| TTL enforcement | `created_at < NOW() - INTERVAL '14 days'` |
| Batch processing | Split In Batches with loop-back |
| Soft delete | `split='purged'` instead of DELETE |
| Audit logging | INSERT into audit_log table |
| GDPR support | Manual webhook for specific videos |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Schedule: daily 03:00 | Schedule Trigger | Daily auto-purge |
| 2 | Webhook: gdpr.deletion | Webhook | Manual purge requests |
| 3 | Postgres: find.old_temp | Postgres | Find expired videos |
| 4 | Loop: batch.delete | Split In Batches | Controlled processing |
| 5 | SSH: delete.file | SSH | Remove from filesystem |
| 6 | Postgres: mark.purged | Postgres | Soft delete in DB |
| 7 | Postgres: audit.log | Postgres | Compliance logging |
| 8 | HTTP: emit.purged | HTTP Request | Event notification |

### Privacy Policy Compliance

| Requirement | Implementation |
|-------------|----------------|
| Local-first | All data on-premise |
| TTL enforcement | 14-day auto-purge |
| Audit trail | All purges logged |
| GDPR support | Manual webhook |
| Data minimization | Soft delete pattern |

---

## Next Steps

Proceed to **Module 6: Training Orchestrator** where you'll learn:
- **Long-running SSH processes** for ML training
- **Polling patterns** for async status checking
- **MLflow integration** for experiment tracking
- **Gate A validation** (quality thresholds)

---

*Module 5 Complete — Proceed to Module 6: Training Orchestrator*
