# MODULE 05 -- Privacy/Retention Agent

**Duration:** ~2 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/08_privacy_agent.json`
**Nodes to Wire:** 8
**Prerequisite:** MODULE 04 complete
**Outcome:** An automated data retention workflow that purges expired temp videos daily and supports on-demand GDPR deletion requests

---

## 5.1 What Does the Privacy Agent Do?

Data retention is critical for privacy compliance. The Privacy Agent:

1. Runs daily at 03:00 UTC (or on-demand via GDPR webhook)
2. Finds all `temp`-split videos older than 14 days
3. Processes deletions in batches of 50
4. For each video: deletes the file, marks the DB record as purged, writes an audit log
5. Emits a `privacy.purged` event when done

### New Concept: Batch Processing with Loop

This is the first workflow that uses the **Split In Batches** node. Instead of processing all items at once (which could overload the SSH connection), we process 50 at a time.

```
Find 200 old videos ──► Process 50 ──► Process 50 ──► Process 50 ──► Process 50 ──► Done
                         (batch 1)      (batch 2)      (batch 3)      (batch 4)
```

---

## 5.2 Pre-Wiring Checklist

- [ ] **SSH access** to Ubuntu 1 verified
- [ ] **PostgreSQL** `audit_log` table exists:
  ```bash
  psql -h localhost -U reachy_dev -d reachy_emotion -c "\d audit_log"
  ```
- [ ] Videos with `split='temp'` exist in the database (for testing)

---

## 5.3 Create the Workflow

1. Name: `Agent 8 -- Privacy/Retention Agent (Reachy 08.4.2)`
2. Tags: `agent`, `privacy`

---

## 5.4 Wire Node 1: schedule_daily

1. Add a **Schedule Trigger** → rename to `schedule_daily`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Cron Expression** | `0 3 * * *` |

Runs daily at 03:00 UTC -- 45 minutes after the Reconciler finishes.

---

## 5.5 Wire Node 2: webhook_gdpr

1. Add a **Webhook** → rename to `webhook_gdpr`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `privacy/purge` |
| **Response Mode** | `Using 'Respond to Webhook' Node` |

This allows manual GDPR deletion requests targeting specific videos.

---

## 5.6 Wire Node 3: db_find_old

1. Add a **Postgres** node → rename to `db_find_old`
2. **Connect both** `schedule_daily` and `webhook_gdpr` to this node
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
SELECT
  video_id,
  file_path,
  label,
  split,
  created_at
FROM video
WHERE split = 'temp'
  AND created_at < NOW() - INTERVAL '14 days'
ORDER BY created_at ASC;
```

### Retention Policy

- **`temp` split:** Auto-purged after 14 days. These are videos that were ingested but never promoted to train/test.
- **`train`/`test` splits:** Never auto-purged. These are curated dataset items.
- **`purged` split:** Already deleted. Excluded from this query.

---

## 5.7 Wire Node 4: split_batches

This is the first time we use **Split In Batches**. It processes items in groups.

### Step-by-Step

1. Add a **Split In Batches** node → rename to `split_batches`
2. Configure:

| Parameter | Value | Why |
|-----------|-------|-----|
| **Batch Size** | `50` | Process 50 deletions per batch to avoid overwhelming SSH |

### How Split In Batches Works

```
Input: [item1, item2, ... item200]

Batch 1: [item1 ... item50]   → process → loop back
Batch 2: [item51 ... item100] → process → loop back
Batch 3: [item101 ... item150] → process → loop back
Batch 4: [item151 ... item200] → process → done! → continue
```

The node has **two outputs**:
- **Output 1 (loop):** The current batch of items. Connect your processing nodes here.
- **Output 2 (done):** Fires when all batches are processed. Connect your "finished" node here.

---

## 5.8 Wire Node 5: ssh_delete_file

Connected to **Output 1** (loop) of `split_batches`.

### Step-by-Step

1. Add an **SSH** node → rename to `ssh_delete_file`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Ubuntu1` |
| **Command** | `rm -f /videos/{{ $json.file_path }}` |

### Safety: `rm -f`

The `-f` flag means "force" -- don't error if the file doesn't exist. This is safe because:
- We're only deleting files identified by the database query
- If the file was already deleted (e.g., by the Reconciler), the command succeeds silently
- The path comes from the database, not user input

---

## 5.9 Wire Node 6: db_mark_purged

### Step-by-Step

1. Add a **Postgres** node → rename to `db_mark_purged`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
UPDATE video
SET
  split = 'purged',
  deleted_at = NOW(),
  updated_at = NOW()
WHERE video_id = '{{ $json.video_id }}';
```

### Soft Delete

We don't delete the database record -- we set `split='purged'`. This preserves metadata (who uploaded it, when it was labeled) while marking the file as deleted. This is important for audit compliance.

---

## 5.10 Wire Node 7: db_audit_log

### Step-by-Step

1. Add a **Postgres** node → rename to `db_audit_log`
2. Configure:

```sql
INSERT INTO audit_log (
  action,
  entity_type,
  entity_id,
  details,
  created_at
)
VALUES (
  'purge',
  'video',
  '{{ $json.video_id }}',
  '{"reason": "retention_policy", "file_path": "{{ $json.file_path }}", "original_split": "temp", "age_days": 14}',
  NOW()
);
```

### Why Audit Logs?

GDPR compliance requires a record of all data deletions. The audit log captures:
- **What** was deleted (video_id, file_path)
- **Why** it was deleted (retention_policy or gdpr_request)
- **When** it was deleted (timestamp)

### Connect the Loop

After `db_audit_log`, connect its output **back to `split_batches`**. This creates the batch processing loop:

`split_batches` (output 1) → `ssh_delete_file` → `db_mark_purged` → `db_audit_log` → `split_batches` (input)

When the current batch is done, Split In Batches automatically grabs the next batch.

---

## 5.11 Wire Node 8: emit_purged

Connected to **Output 2** (done) of `split_batches`.

### Step-by-Step

1. Add an **HTTP Request** node → rename to `emit_purged`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/events/privacy` |

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `privacy.purged` |
| `purged_count` | `{{ $('db_find_old').all().length }}` |
| `timestamp` | `{{ $now.toISO() }}` |

---

## 5.12 Final Connection Map

```
schedule_daily ──┐
                 ├──► db_find_old ──► split_batches
webhook_gdpr ────┘                       │        │
                                    [batch]    [done]
                                       │          │
                                       ▼          ▼
                                 ssh_delete_file  emit_purged
                                       │
                                       ▼
                                 db_mark_purged
                                       │
                                       ▼
                                  db_audit_log
                                       │
                                       └──► split_batches (loop back)
```

---

## 5.13 Testing

### Test with a Fake Old Video

1. Insert a test video with a creation date > 14 days ago:
   ```sql
   INSERT INTO video (file_path, label, split, created_at)
   VALUES ('temp/test_purge.mp4', 'happy', 'temp', NOW() - INTERVAL '15 days');
   ```
2. Create the test file on disk:
   ```bash
   ssh rusty_admin@10.0.4.130 "touch /videos/temp/test_purge.mp4"
   ```
3. Trigger the workflow manually:
   ```bash
   curl -X POST http://10.0.4.130:5678/webhook-test/privacy/purge
   ```
4. Verify:
   - File is deleted from disk
   - Video record has `split='purged'`
   - Audit log entry exists

---

## 5.14 Key Concepts Learned

- **Split In Batches** node for batch processing with a loop
- **Batch loop wiring** -- connecting output back to the batch node's input
- **Soft delete pattern** -- marking records as purged instead of deleting them
- **Audit logging** -- maintaining compliance records for data deletions
- **GDPR support** -- manual webhook for targeted deletion requests
- **Staggered scheduling** -- spacing cron jobs to avoid resource contention

---

*Previous: [MODULE 04 -- Reconciler Agent](MODULE_04_RECONCILER_AGENT.md)*
*Next: [MODULE 06 -- Training Orchestrator](MODULE_06_TRAINING_ORCHESTRATOR.md)*
