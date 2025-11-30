# Agent 4 — Reconciler/Audit Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Reconciler/Audit Agent ensures filesystem and database consistency. It runs daily at 02:15 or on-demand via webhook, scanning the filesystem for video files and comparing against database records. It detects orphaned files (in FS but not DB), missing files (in DB but not FS), and metadata mismatches, then sends email reports when drift is found.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: diff.fs_db | n8n-nodes-base.code | diff_fs_db |
| Code: parse.fs_scan | n8n-nodes-base.code | parse_fs_scan |
| Email: send.report | n8n-nodes-base.emailSend | email_report |
| IF: drift.found? | n8n-nodes-base.if | if_drift_found |
| Postgres: fetch.all_videos | n8n-nodes-base.postgres | db_fetch_all |
| Schedule: daily 02:15 | n8n-nodes-base.scheduleTrigger | schedule_trigger |
| Set: config | n8n-nodes-base.set | set_config |
| SSH: scan.filesystem | n8n-nodes-base.ssh | ssh_scan_fs |
| Webhook: manual.trigger | n8n-nodes-base.webhook | webhook_manual |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Schedule: daily 02:15 ──┬──► Set: config
                        │         │
Webhook: manual.trigger ┘         │
                                  ├──► SSH: scan.filesystem ──► Code: parse.fs_scan ──┐
                                  │                                                    │
                                  └──► Postgres: fetch.all_videos ────────────────────┤
                                                                                       │
                                                                                       ▼
                                                                            Code: diff.fs_db
                                                                                       │
                                                                                       ▼
                                                                            IF: drift.found?
                                                                                       │
                                                                        [True] ──► Email: send.report
```

---

## Node Details

### 1. Schedule: daily 02:15

**Type:** `n8n-nodes-base.scheduleTrigger` (v1.2)  
**Position:** [-600, 300]  
**Purpose:** Triggers daily reconciliation at 02:15 AM.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `rule.interval[0].field` | `cronExpression` | Use cron syntax |
| `rule.interval[0].expression` | `15 2 * * *` | Run at 02:15 daily |

#### Test Status: ✅ OPERATIONAL

---

### 2. Webhook: manual.trigger

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-600, 450]  
**Purpose:** Allows manual triggering of reconciliation via GET request.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `GET` | Accept GET requests |
| `path` | `reconciler/audit` | URL: `{N8N_HOST}/webhook/reconciler/audit` |
| `responseMode` | `onReceived` | Respond immediately |
| `webhookId` | `reconciler-manual` | Unique identifier |

#### Test Status: ✅ OPERATIONAL

---

### 3. Set: config

**Type:** `n8n-nodes-base.set` (v3.3)  
**Position:** [-400, 350]  
**Purpose:** Sets configuration variables for the reconciliation run.

#### Parameters

| Assignment | Value | Type | Purpose |
|------------|-------|------|---------|
| `root_dir` | `/videos` | string | Base directory for video files |
| `safe_fix` | `false` | boolean | Auto-fix mode (disabled) |

#### Test Status: ✅ OPERATIONAL

---

### 4. SSH: scan.filesystem

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [-200, 350]  
**Purpose:** Scans filesystem for all MP4 files and outputs JSONL metadata.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `authentication` | `password` | SSH password auth |

#### Command

```bash
find /videos/{temp,train,test,dataset_all} -type f -name '*.mp4' \
  -printf '{"file_path":"%P","size_bytes":%s,"mtime":"%TY-%Tm-%TdT%TH:%TM:%TSZ"}\n'
```

#### Output Format (JSONL)

```json
{"file_path":"temp/abc123.mp4","size_bytes":12345,"mtime":"2025-11-07T10:30:00Z"}
{"file_path":"train/def456.mp4","size_bytes":67890,"mtime":"2025-11-06T15:45:00Z"}
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Test Status: ✅ OPERATIONAL

---

### 5. Code: parse.fs_scan

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [0, 350]  
**Purpose:** Parses JSONL filesystem scan output into structured items.

#### JavaScript Code

```javascript
// Parse JSONL filesystem scan results
const output = $json.stdout || '';
const lines = output.split('\n').filter(Boolean);
const items = [];

for (const line of lines) {
  try {
    const obj = JSON.parse(line);
    const pathParts = obj.file_path.split('/');
    const split = pathParts[0];
    
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
    // Skip malformed lines
  }
}

return items;
```

#### Output Schema (per item)

```json
{
  "file_path": "temp/abc123.mp4",
  "size_bytes": 12345,
  "mtime": "2025-11-07T10:30:00Z",
  "split": "temp",
  "source": "fs"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 6. Postgres: fetch.all_videos

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [200, 200]  
**Purpose:** Fetches all video records from database for comparison.

#### SQL Query

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

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 7. Code: diff.fs_db

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [400, 300]  
**Purpose:** Compares filesystem and database records to identify discrepancies.

#### JavaScript Code

```javascript
// Diff filesystem vs database
const fsItems = $('parse_fs_scan').all();
const dbItems = $('db_fetch_all').all();

// Build maps
const fsMap = new Map();
for (const item of fsItems) {
  fsMap.set(item.json.file_path, item.json);
}

const dbMap = new Map();
for (const item of dbItems) {
  dbMap.set(item.json.file_path, item.json);
}

// Find differences
const orphans_fs = [];
const missing_fs = [];
const mismatches = [];

// Orphans: in FS, not in DB
for (const [path, fsData] of fsMap) {
  if (!dbMap.has(path)) {
    orphans_fs.push({ file_path: path, ...fsData });
  }
}

// Missing: in DB, not in FS
for (const [path, dbData] of dbMap) {
  if (!fsMap.has(path)) {
    missing_fs.push({ file_path: path, video_id: dbData.video_id });
  } else {
    // Check for mismatches
    const fsData = fsMap.get(path);
    if (fsData.size_bytes !== dbData.size_bytes || fsData.split !== dbData.split) {
      mismatches.push({
        file_path: path,
        fs_size: fsData.size_bytes,
        db_size: dbData.size_bytes,
        fs_split: fsData.split,
        db_split: dbData.split
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

#### Output Schema

```json
{
  "summary": {
    "total_fs": 150,
    "total_db": 148,
    "orphans_count": 3,
    "missing_count": 1,
    "mismatch_count": 0
  },
  "orphans_fs": [{"file_path": "...", "size_bytes": 12345}],
  "missing_fs": [{"file_path": "...", "video_id": "uuid"}],
  "mismatches": [],
  "timestamp": "2025-11-07T02:15:30.000Z"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 8. IF: drift.found?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [600, 300]  
**Purpose:** Checks if any discrepancies were found.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.summary.orphans_count > 0 \|\| $json.summary.missing_count > 0 \|\| $json.summary.mismatch_count > 0}}` | Any drift detected |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Any count > 0 | Email: send.report |
| False | All counts = 0 | (workflow ends) |

#### Test Status: ✅ OPERATIONAL

---

### 9. Email: send.report

**Type:** `n8n-nodes-base.emailSend` (v2.1)  
**Position:** [800, 200]  
**Purpose:** Sends email report when drift is detected.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `fromEmail` | `noreply@reachy.local` | Sender address |
| `toEmail` | `rustybee255@gmail.com` | Recipient |
| `emailType` | `text` | Plain text email |

#### Subject Template

```
Reconciler Report: {{$json.summary.orphans_count}} orphans, {{$json.summary.missing_count}} missing
```

#### Message Template

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

#### Test Status: ⚠️ TBD (requires SMTP configuration)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| (none) | N/A | N/A |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Database connection |
| 3 | SSH Ubuntu1 | SSH Password | Filesystem access |

---

## Workflow Settings

```json
{
  "executionOrder": "v1",
  "saveManualExecutions": true
}
```

---

## Tags

- `agent`
- `reconciler`
- `phase4`

---

## Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `ReconcileReport` | 270-300 | Model for storing reconciliation reports |
| `Video` | 33-78 | Video model for comparison |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| SMTP Configuration | MEDIUM | Configure email credentials for alerts |
| Auto-fix Mode | LOW | Implement safe_fix=true logic to auto-repair |
| Store Report in DB | LOW | Insert ReconcileReport record |

---

## Connections Summary

```json
{
  "schedule_trigger": { "main": [["set_config"]] },
  "webhook_manual": { "main": [["set_config"]] },
  "set_config": { "main": [["ssh_scan_fs", "db_fetch_all"]] },
  "ssh_scan_fs": { "main": [["parse_fs_scan"]] },
  "parse_fs_scan": { "main": [["diff_fs_db"]] },
  "db_fetch_all": { "main": [["diff_fs_db"]] },
  "diff_fs_db": { "main": [["if_drift_found"]] },
  "if_drift_found": { "main": [["email_report"]] }
}
```
