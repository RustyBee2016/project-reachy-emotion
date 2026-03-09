# MODULE 04 -- Reconciler/Audit Agent

**Duration:** ~3 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`
**Nodes to Wire:** 9
**Prerequisite:** MODULE 03 complete
**Outcome:** A scheduled audit workflow that detects drift between the filesystem and database, running daily or on-demand

---

## 4.1 What Does the Reconciler Agent Do?

Over time, the filesystem and database can get out of sync. Files might be manually deleted, moved, or corrupted. The Reconciler Agent:

1. Scans all video files on disk via SSH
2. Fetches all video records from the database
3. Compares the two to find discrepancies:
   - **Orphans:** Files on disk but not in the database
   - **Missing:** Database records with no corresponding file
   - **Mismatches:** Records where size or split disagrees
4. Emails a report if any drift is found

### New Concepts in This Module

- **Schedule Trigger** (cron-based automation)
- **SSH node** (running commands on remote servers)
- **Parallel fan-out** (running two nodes simultaneously)
- **Send Email node**
- **Dual triggers** (both scheduled and manual)

---

## 4.2 Pre-Wiring Checklist

- [ ] **SSH access** to Ubuntu 1 works (test with `ssh rusty_admin@10.0.4.130`)
- [ ] **Videos exist** on disk under `/videos/` directory
- [ ] **SMTP** is configured for sending emails (or use a test email service)
- [ ] **PostgreSQL** has video records to compare against

---

## 4.3 Create the Workflow

1. Click **Add Workflow**
2. Name: `Agent 4 -- Reconciler/Audit Agent (Reachy 08.4.2)`
3. Tags: `agent`, `reconciler`, `phase4`

---

## 4.4 Wire Node 1: schedule_trigger

This is the first time we use a **Schedule Trigger**. It fires automatically on a cron schedule.

### Step-by-Step

1. Add a **Schedule Trigger** node → rename to `schedule_trigger`
2. Configure:

| Parameter | Value | Why |
|-----------|-------|-----|
| **Trigger at** | `Cron Expression` | Gives precise control over timing |
| **Cron Expression** | `15 2 * * *` | Runs daily at 02:15 UTC |

### Cron Expression Breakdown

```
15 2 * * *
│  │ │ │ │
│  │ │ │ └── Day of week (any)
│  │ │ └──── Month (any)
│  │ └────── Day of month (any)
│  └──────── Hour (2 AM UTC)
└─────────── Minute (15)
```

### Why 02:15?

- Runs during off-hours when system load is low
- 15 minutes past the hour to avoid coinciding with other scheduled tasks
- The Privacy Agent runs at 03:00 -- staggering prevents resource contention

---

## 4.5 Wire Node 2: webhook_manual

A second trigger for on-demand audits.

### Step-by-Step

1. Add a **Webhook** node → rename to `webhook_manual`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `GET` |
| **Path** | `reconciler/audit` |
| **Response Mode** | `On Received` |

### Dual Triggers

This workflow has **two triggers**: `schedule_trigger` and `webhook_manual`. Both connect to the same next node (`set_config`). n8n allows multiple triggers in one workflow -- whichever fires starts the execution.

---

## 4.6 Wire Node 3: set_config

### Step-by-Step

1. Add a **Set** node → rename to `set_config`
2. **Connect both triggers** to this node:
   - Draw a connection from `schedule_trigger` → `set_config`
   - Draw a connection from `webhook_manual` → `set_config`
3. Configure -- click "Add Value" twice:

| Field Name | Type | Value | Purpose |
|------------|------|-------|---------|
| `root_dir` | String | `/videos` | Base directory to scan for video files |
| `safe_fix` | Boolean | `false` | When false, report only. When true, auto-repair discrepancies |

---

## 4.7 Wire Node 4: ssh_scan_fs

This is the first time we use the **SSH node**. It runs commands on Ubuntu 1 remotely.

### Step-by-Step

1. Add an **SSH** node → rename to `ssh_scan_fs`
2. Connect `set_config` → `ssh_scan_fs`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Ubuntu1` |
| **Command** | *(see below)* |

```bash
find /videos/temp /videos/train /videos/test /videos/dataset_all \
  -name '*.mp4' -type f \
  -printf '{"path":"%p","size":%s,"mtime":"%T@","split_dir":"%h"}\n' \
  2>/dev/null || true
```

### What This Command Does

- `find` locates all `.mp4` files under the four video directories
- `-printf` outputs each file as a JSON object (one per line = JSONL format)
- Fields: `path` (full path), `size` (bytes), `mtime` (modification time), `split_dir` (parent directory)
- `2>/dev/null || true` -- suppresses errors if a directory doesn't exist and ensures the command always succeeds

### SSH Node Details

The SSH node connects to `rusty_admin@10.0.4.130` using the credentials you set up in Module 00. The command runs on the remote server, and the stdout is returned as `$json.stdout` in the node's output.

---

## 4.8 Wire Node 5: parse_fs_scan

### Step-by-Step

1. Add a **Code** node → rename to `parse_fs_scan`
2. Code:

```javascript
const stdout = $input.first().json.stdout || '';
const lines = stdout.trim().split('\n').filter(line => line.length > 0);

const fsItems = lines.map(line => {
  try {
    const item = JSON.parse(line);
    // Extract split from the directory path
    // e.g., /videos/train/happy/video.mp4 → split = 'train'
    const pathParts = item.path.split('/');
    const splitIndex = pathParts.indexOf('videos') + 1;
    const split = pathParts[splitIndex] || 'unknown';

    return {
      json: {
        file_path: item.path,
        size_bytes: item.size,
        mtime: item.mtime,
        split: split
      }
    };
  } catch (e) {
    return null;
  }
}).filter(item => item !== null);

return fsItems;
```

---

## 4.9 Wire Node 6: db_fetch_all

This runs **in parallel** with `ssh_scan_fs`.

### Step-by-Step

1. Add a **Postgres** node → rename to `db_fetch_all`
2. **Connect `set_config` → `db_fetch_all`** (this creates a second output from set_config)
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
  split,
  label,
  size_bytes,
  sha256,
  updated_at
FROM video
WHERE split != 'purged'
ORDER BY file_path;
```

### Parallel Execution

Both `ssh_scan_fs` and `db_fetch_all` connect from `set_config`. In n8n, when a node has multiple outputs going to different nodes, those downstream nodes can execute in parallel. This speeds up the reconciliation since the SSH scan and DB query happen simultaneously.

---

## 4.10 Wire Node 7: diff_fs_db

This is the core logic -- comparing filesystem and database.

### Step-by-Step

1. Add a **Code** node → rename to `diff_fs_db`
2. **Connect both** `parse_fs_scan` and `db_fetch_all` to this node
3. Code:

```javascript
// Get filesystem items from parse_fs_scan
const fsItems = $('parse_fs_scan').all();
// Get database items from db_fetch_all
const dbItems = $('db_fetch_all').all();

// Build lookup maps
const fsMap = new Map();
fsItems.forEach(item => {
  fsMap.set(item.json.file_path, item.json);
});

const dbMap = new Map();
dbItems.forEach(item => {
  dbMap.set(item.json.file_path, item.json);
});

// Find discrepancies
const orphans_fs = [];  // On disk but not in DB
const missing_fs = [];  // In DB but not on disk
const mismatches = [];  // In both but disagree

// Check each filesystem file against DB
fsMap.forEach((fsItem, path) => {
  const dbItem = dbMap.get(path);
  if (!dbItem) {
    orphans_fs.push({ file_path: path, size_bytes: fsItem.size_bytes, split: fsItem.split });
  } else {
    // Check for mismatches
    const issues = [];
    if (fsItem.size_bytes !== dbItem.size_bytes) {
      issues.push(`size: fs=${fsItem.size_bytes} db=${dbItem.size_bytes}`);
    }
    if (fsItem.split !== dbItem.split) {
      issues.push(`split: fs=${fsItem.split} db=${dbItem.split}`);
    }
    if (issues.length > 0) {
      mismatches.push({ file_path: path, issues: issues.join('; ') });
    }
  }
});

// Check each DB record against filesystem
dbMap.forEach((dbItem, path) => {
  if (!fsMap.has(path)) {
    missing_fs.push({
      video_id: dbItem.video_id,
      file_path: path,
      split: dbItem.split,
      label: dbItem.label
    });
  }
});

return [{
  json: {
    fs_file_count: fsMap.size,
    db_record_count: dbMap.size,
    orphans_fs,
    missing_fs,
    mismatches,
    orphans_count: orphans_fs.length,
    missing_count: missing_fs.length,
    mismatch_count: mismatches.length,
    scan_timestamp: new Date().toISOString()
  }
}];
```

### Understanding the `$('NodeName').all()` Pattern

When this node receives inputs from two different nodes, you use `$('NodeName').all()` to explicitly reference which node's data you want. This is different from `$input.all()` which would only give you the last connected node's data.

---

## 4.11 Wire Node 8: if_drift_found

### Step-by-Step

1. Add an **IF** node → rename to `if_drift_found`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.orphans_count + $json.missing_count + $json.mismatch_count }}` |
| **Operation** | `is greater than` |
| **Value 2** | `0` |

If no drift is found, the workflow simply ends (no email needed).

---

## 4.12 Wire Node 9: email_report

Connected to the **true** output of `if_drift_found`.

### Step-by-Step

1. Add a **Send Email** node → rename to `email_report`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **To** | `rustybee255@gmail.com` |
| **Subject** | `Reachy Reconciler Report - {{ $json.scan_timestamp }}` |
| **Email Format** | `Text` |
| **Body** | *(see below)* |

```
REACHY RECONCILER AUDIT REPORT
================================
Scan Time: {{ $json.scan_timestamp }}

SUMMARY
-------
Filesystem Files: {{ $json.fs_file_count }}
Database Records: {{ $json.db_record_count }}

DISCREPANCIES
-------------
Orphan Files (on disk, not in DB): {{ $json.orphans_count }}
Missing Files (in DB, not on disk): {{ $json.missing_count }}
Mismatches (size/split differ):     {{ $json.mismatch_count }}

DETAILS
-------
{{ JSON.stringify($json.orphans_fs, null, 2) }}

{{ JSON.stringify($json.missing_fs, null, 2) }}

{{ JSON.stringify($json.mismatches, null, 2) }}
```

---

## 4.13 Final Connection Map

```
schedule_trigger ──┐
                   ├──► set_config ──┬──► ssh_scan_fs ──► parse_fs_scan ──┐
webhook_manual ────┘                │                                      │
                                    └──► db_fetch_all ─────────────────────┤
                                                                           ▼
                                                                      diff_fs_db
                                                                           │
                                                                           ▼
                                                                    if_drift_found
                                                                      │          │
                                                                [drift]     [no drift]
                                                                   │         (end)
                                                                   ▼
                                                              email_report
```

---

## 4.14 Testing

### Manual Trigger Test

```bash
curl http://10.0.4.130:5678/webhook-test/reconciler/audit
```

### Verify Parallel Execution

Watch the execution: both `ssh_scan_fs` and `db_fetch_all` should show as running simultaneously.

### Create a Test Discrepancy

1. Manually create a file that doesn't exist in the DB:
   ```bash
   ssh rusty_admin@10.0.4.130 "touch /videos/temp/orphan_test.mp4"
   ```
2. Run the reconciler -- it should detect the orphan
3. Clean up: `ssh rusty_admin@10.0.4.130 "rm /videos/temp/orphan_test.mp4"`

---

## 4.15 Key Concepts Learned

- **Schedule Trigger** with cron expressions for automated execution
- **Dual triggers** (scheduled + manual webhook) in one workflow
- **SSH node** for running remote commands
- **Parallel fan-out** from one node to multiple downstream nodes
- **`$('NodeName').all()`** pattern for accessing specific node outputs
- **Set node** for configuration values
- **Send Email** node for alerts
- **Map-based diffing** pattern for comparing two data sources

---

*Previous: [MODULE 03 -- Promotion Agent](MODULE_03_PROMOTION_AGENT.md)*
*Next: [MODULE 05 -- Privacy Agent](MODULE_05_PRIVACY_AGENT.md)*
