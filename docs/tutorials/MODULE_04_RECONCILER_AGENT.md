# Module 4: Reconciler Agent — Scheduled Triggers, SSH & Parallel Execution

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~3 hours  
**Prerequisites**: Completed Modules 0-3

---

## Learning Objectives

By the end of this module, you will:
1. Use **Schedule Trigger** nodes with cron expressions
2. Execute **SSH commands** for remote filesystem operations
3. Implement **parallel execution** (multiple nodes from one trigger)
4. Parse **JSONL output** from shell commands
5. Configure **Email Send** nodes for alerting
6. Use the **Set** node for configuration variables

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Scheduled triggers** | Schedule Trigger | Automated recurring tasks |
| **Cron expressions** | `15 2 * * *` | Precise scheduling control |
| **SSH operations** | SSH node | Remote command execution |
| **Parallel paths** | Multiple outputs | Concurrent operations |
| **JSONL parsing** | Code node | Handle streaming output |
| **Configuration node** | Set node | Centralize settings |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Schedule: daily 02:15 | n8n scheduler | ⬜ (native) |
| 2 | Webhook: manual.trigger | n8n webhook server | ⬜ (native) |
| 3 | Set: config | n8n Set node | ⬜ (native) |
| 4 | SSH: scan.filesystem | SSH to Ubuntu1 | ⬜ |
| 5 | Code: parse.fs_scan | JavaScript runtime | ⬜ (native) |
| 6 | Postgres: fetch.all_videos | PostgreSQL database | ⬜ |
| 7 | Code: diff.fs_db | JavaScript runtime | ⬜ (native) |
| 8 | IF: drift.found? | n8n conditional | ⬜ (native) |
| 9 | Email: send.report | SMTP server | ⬜ |

---

### Verification Procedures

#### Test 1: SSH Connection to Ubuntu1

```bash
# From Ubuntu1, test SSH locally
ssh rusty_admin@localhost 'echo "SSH works"'
```

**Status**: ⬜ → [ ] Complete

---

#### Test 2: Filesystem Scan Command

```bash
# Test the find command that generates JSONL
find /media/project_data/reachy_emotion/videos/{temp,train,test} \
  -type f -name '*.mp4' \
  -printf '{"file_path":"%P","size_bytes":%s,"mtime":"%TY-%Tm-%TdT%TH:%TM:%TS"}\n' \
  | head -5
```

**Expected Output** (JSONL):
```json
{"file_path":"temp/abc123.mp4","size_bytes":12345,"mtime":"2025-11-07T10:30:00"}
{"file_path":"train/def456.mp4","size_bytes":67890,"mtime":"2025-11-06T15:45:00"}
```

**Status**: ⬜ → [ ] Complete

---

#### Test 3: PostgreSQL Video Query

```sql
SELECT video_id, file_path, split, label, size_bytes
FROM video
LIMIT 5;
```

**Status**: ⬜ → [ ] Complete

---

#### Test 4: SMTP Configuration (Optional)

If you want email alerts, verify SMTP settings. Otherwise, you can skip the email node during testing.

**Status**: ⬜ → [ ] Complete (or N/A)

---

## Part 1: Understanding the Reconciler

### What Does the Reconciler Do?

The Reconciler ensures **filesystem ↔ database consistency**. Over time, drift can occur:

| Problem | Description | Impact |
|---------|-------------|--------|
| **Orphan files** | Files in FS, not in DB | Wasted storage, training confusion |
| **Missing files** | In DB, not in FS | Broken references, training failures |
| **Mismatches** | Different metadata | Incorrect training data |

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RECONCILER AGENT FLOW                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Schedule: daily 02:15 ──┬──► Set: config                               │
│                          │         │                                    │
│  Webhook: manual.trigger ┘         │                                    │
│                                    │                                    │
│                    ┌───────────────┴───────────────┐                    │
│                    │      PARALLEL EXECUTION       │                    │
│                    ▼                               ▼                    │
│        SSH: scan.filesystem           Postgres: fetch.all_videos        │
│                    │                               │                    │
│                    ▼                               │                    │
│        Code: parse.fs_scan                         │                    │
│                    │                               │                    │
│                    └───────────────┬───────────────┘                    │
│                                    │                                    │
│                                    ▼                                    │
│                            Code: diff.fs_db                             │
│                                    │                                    │
│                                    ▼                                    │
│                            IF: drift.found?                             │
│                                    │                                    │
│                            [True]  │                                    │
│                                    ▼                                    │
│                            Email: send.report                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Pattern: Parallel Execution

Notice that **SSH** and **Postgres** run in parallel after Set:config. This is achieved by:
1. Connecting Set:config to SSH node
2. Connecting Set:config to Postgres node (same source, two destinations)

Both paths execute concurrently, then merge at diff.fs_db.

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 4 — Reconciler Agent (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Schedule Trigger

**Node Name**: `Schedule: daily 02:15`

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| Trigger | `Cron` | Use cron expression |
| Cron Expression | `15 2 * * *` | At 02:15 every day |

**Cron Expression Breakdown**:
```
┌───────────── minute (0 - 59)
│ ┌─────────── hour (0 - 23)
│ │ ┌───────── day of month (1 - 31)
│ │ │ ┌─────── month (1 - 12)
│ │ │ │ ┌───── day of week (0 - 6, Sunday = 0)
│ │ │ │ │
15 2 * * *   = At 02:15 every day
```

**Why 02:15?**
- Low system load time
- After midnight (system cleanup)
- Before morning work begins
- Offset from common times (00:00, 01:00) to avoid conflicts

---

### Step 3: Add Manual Trigger Webhook

**Node Name**: `Webhook: manual.trigger`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `GET` |
| Path | `reconciler/audit` |
| Response Mode | `When Last Node Finishes` |

**Purpose**: Allow on-demand reconciliation without waiting for schedule.

---

### Step 4: Add Configuration Node

**Node Name**: `Set: config`

The **Set node** defines variables used throughout the workflow.

| Parameter | Value |
|-----------|-------|
| Mode | `Manual Mapping` |

**Fields to Add**:
| Field Name | Value | Type |
|------------|-------|------|
| `root_dir` | `/media/project_data/reachy_emotion/videos` | String |
| `safe_fix` | `false` | Boolean |
| `run_id` | `={{$now.format('yyyyMMdd_HHmmss')}}` | String |

**Connect Both Triggers**:
- Schedule → Set:config
- Webhook → Set:config

---

### Step 5: Add SSH Filesystem Scan

**Node Name**: `SSH: scan.filesystem`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command** (single line):
```bash
find {{$json.root_dir}}/{temp,train,test} -type f -name '*.mp4' -printf '{"file_path":"%P","size_bytes":%s,"mtime":"%TY-%Tm-%TdT%TH:%TM:%TS"}\n'
```

**Command Breakdown**:
| Part | Purpose |
|------|---------|
| `find ... -type f` | Find files only |
| `-name '*.mp4'` | Match MP4 files |
| `-printf '...'` | Output as JSON |
| `%P` | Filename relative to search path |
| `%s` | Size in bytes |
| `%T...` | Modification time |

---

### Step 6: Add JSONL Parser

**Node Name**: `Code: parse.fs_scan`

```javascript
// Parse JSONL filesystem scan results
const output = $json.stdout || '';
const lines = output.split('\n').filter(Boolean);
const items = [];

for (const line of lines) {
  try {
    const obj = JSON.parse(line);
    const pathParts = obj.file_path.split('/');
    const split = pathParts[0];  // First part is split name (temp/train/test)
    
    items.push({
      json: {
        file_path: obj.file_path,
        size_bytes: parseInt(obj.size_bytes, 10),
        mtime: obj.mtime,
        split,
        source: 'fs'
      }
    });
  } catch (e) {
    // Skip malformed lines (e.g., empty or error messages)
    console.log('Skipped line:', line);
  }
}

// Return all items as separate n8n items
return items;
```

**Key Pattern**: JSONL → n8n Items
- SSH outputs one JSON object per line
- We parse each line into an n8n item
- Each item can be processed independently

---

### Step 7: Add PostgreSQL Query (Parallel Path)

**Node Name**: `Postgres: fetch.all_videos`

**Connect from**: Set:config (same source as SSH — creates parallel execution)

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
SELECT
  video_id,
  file_path,
  split,
  label,
  size_bytes,
  sha256,
  updated_at
FROM video;
```

---

### Step 8: Add Diff Logic

**Node Name**: `Code: diff.fs_db`

**Connect from**: 
- parse.fs_scan → diff.fs_db
- fetch.all_videos → diff.fs_db

This node receives items from BOTH parallel paths and compares them:

```javascript
// Diff filesystem vs database
// Access items from both input nodes
const fsItems = $('Code: parse.fs_scan').all();
const dbItems = $('Postgres: fetch.all_videos').all();

// Build maps for comparison
const fsMap = new Map();
for (const item of fsItems) {
  fsMap.set(item.json.file_path, item.json);
}

const dbMap = new Map();
for (const item of dbItems) {
  dbMap.set(item.json.file_path, item.json);
}

// Find differences
const orphans_fs = [];   // In FS, not in DB
const missing_fs = [];   // In DB, not in FS
const mismatches = [];   // Different metadata

// Check FS against DB
for (const [path, fsData] of fsMap) {
  if (!dbMap.has(path)) {
    orphans_fs.push({ file_path: path, ...fsData });
  }
}

// Check DB against FS
for (const [path, dbData] of dbMap) {
  if (!fsMap.has(path)) {
    missing_fs.push({ file_path: path, video_id: dbData.video_id });
  } else {
    // Check for metadata mismatches
    const fsData = fsMap.get(path);
    if (fsData.size_bytes !== dbData.size_bytes) {
      mismatches.push({
        file_path: path,
        fs_size: fsData.size_bytes,
        db_size: dbData.size_bytes
      });
    }
  }
}

return [{
  json: {
    summary: {
      total_fs: fsMap.size,
      total_db: dbMap.size,
      orphans_count: orphans_fs.length,
      missing_count: missing_fs.length,
      mismatch_count: mismatches.length
    },
    orphans_fs,
    missing_fs,
    mismatches,
    timestamp: new Date().toISOString()
  }
}];
```

**Key Pattern**: Multi-Input Merge
```javascript
$('NodeName').all()  // Get ALL items from a specific node
```

---

### Step 9: Add Drift Detection

**Node Name**: `IF: drift.found?`

| Parameter | Value |
|-----------|-------|
| Condition | Expression |
| Value 1 | `={{$json.summary.orphans_count > 0 || $json.summary.missing_count > 0 || $json.summary.mismatch_count > 0}}` |
| Operation | `is true` |

---

### Step 10: Add Email Alert (Optional)

**Node Name**: `Email: send.report`

Connect: IF (True branch) → Email

| Parameter | Value |
|-----------|-------|
| From Email | `noreply@reachy.local` |
| To Email | `rustybee255@gmail.com` |
| Subject | `Reconciler: {{$json.summary.orphans_count}} orphans, {{$json.summary.missing_count}} missing` |
| Email Type | `Text` |

**Message**:
```
Reconciler completed at {{$json.timestamp}}

Summary:
- FS files: {{$json.summary.total_fs}}
- DB records: {{$json.summary.total_db}}
- Orphans (FS only): {{$json.summary.orphans_count}}
- Missing (DB only): {{$json.summary.missing_count}}
- Mismatches: {{$json.summary.mismatch_count}}

Review in database or n8n execution logs.
```

**⚠️ SMTP Required**: Configure SMTP credentials in n8n. If not available, you can:
1. Skip this node
2. Replace with HTTP Request to a logging endpoint
3. Use a Slack/Discord webhook instead

---

## Part 3: Testing

### Test 1: Manual Trigger

```bash
curl http://10.0.4.130:5678/webhook-test/reconciler/audit
```

**Expected**: Workflow executes, diff is computed, email sent if drift found.

### Test 2: Create Artificial Drift

```bash
# Create orphan file (in FS, not in DB)
touch /media/project_data/reachy_emotion/videos/temp/orphan_test.mp4

# Run reconciler
curl http://10.0.4.130:5678/webhook-test/reconciler/audit

# Clean up
rm /media/project_data/reachy_emotion/videos/temp/orphan_test.mp4
```

**Expected**: `orphans_count: 1` in results

---

## Module 4 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Scheduled triggers | Cron expression `15 2 * * *` |
| SSH commands | `find` with `-printf` for JSONL |
| Parallel execution | Multiple connections from one node |
| JSONL parsing | Split, parse each line |
| Multi-input merge | `$('NodeName').all()` |
| Configuration node | Set node for centralized config |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Schedule: daily 02:15 | Schedule Trigger | Automated daily run |
| 2 | Webhook: manual.trigger | Webhook | On-demand execution |
| 3 | Set: config | Set | Configuration variables |
| 4 | SSH: scan.filesystem | SSH | Get FS file list |
| 5 | Code: parse.fs_scan | Code | Parse JSONL output |
| 6 | Postgres: fetch.all_videos | Postgres | Get DB records |
| 7 | Code: diff.fs_db | Code | Compare FS ↔ DB |
| 8 | IF: drift.found? | IF | Check for issues |
| 9 | Email: send.report | Email Send | Alert on drift |

---

## Next Steps

Proceed to **Module 5: Privacy Agent** where you'll learn:
- **TTL enforcement** for temporary data
- **Batch processing** with Split In Batches node
- **Audit logging** for compliance
- **GDPR purge** patterns

---

*Module 4 Complete — Proceed to Module 5: Privacy Agent*
