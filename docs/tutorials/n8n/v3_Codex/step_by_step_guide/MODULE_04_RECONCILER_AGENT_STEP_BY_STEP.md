# Agent 4 — Reconciler/Audit Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`

## Related Scripts and Functionalities
- `video` table is fetched by `Postgres: fetch.all_videos` for reconciliation baseline.
- Filesystem scan uses SSH command path rooted at `/videos/{temp,train,test}`.
- Alerting path uses n8n `Send Email` node for reconciliation reports.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `SSH: scan.filesystem` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
- `Postgres: fetch.all_videos` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
3. Set required environment variables in n8n runtime/environment:
- No `$env.*` variables detected in this workflow.

## Step 1: Add and Configure Nodes
### Step 1 - `Schedule: daily 02:15`
- Add node type: `Schedule Trigger`
- Rename node to: `Schedule: daily 02:15`
- Why this node exists: Nightly automatic reconciliation trigger.

| UI Field | Value |
|---|---|
| `rule` | `{"interval": [{"field": "cronExpression", "expression": "15 2 * * *"}]}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Set: config`

### Step 2 - `Webhook: manual.trigger`
- Add node type: `Webhook`
- Rename node to: `Webhook: manual.trigger`
- Why this node exists: Manual reconciliation trigger endpoint.

| UI Field | Value |
|---|---|
| `httpMethod` | `GET` |
| `path` | `reconciler/audit` |
| `responseMode` | `onReceived` |
| `options` | `{}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Set: config`

### Step 3 - `Set: config`
- Add node type: `Set (Edit Fields)`
- Rename node to: `Set: config`
- Why this node exists: Set static config values used downstream.

| UI Field | Value |
|---|---|
| `assignments` | `{"assignments": [{"id": "1", "name": "root_dir", "value": "/videos", "type": "string"}, {"id": "2", "name": "safe_fix", "value": "=false", "type": "boolean"}]}` |

**Connection checklist for this node**
- Incoming: `Schedule: daily 02:15` output branch `0` -> this node
- Incoming: `Webhook: manual.trigger` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: scan.filesystem`
- Outgoing: this node output branch `0` -> `Postgres: fetch.all_videos`

### Step 4 - `SSH: scan.filesystem`
- Add node type: `SSH`
- Rename node to: `SSH: scan.filesystem`
- Why this node exists: Scan media files from filesystem.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
find /videos/{temp,train,test} -type f -name '*.mp4' -printf '{"file_path":"%P","size_bytes":%s,"mtime":"%TY-%Tm-%TdT%TH:%TM:%TSZ"}\n'
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Set: config` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.fs_scan`

### Step 5 - `Code: parse.fs_scan`
- Add node type: `Code`
- Rename node to: `Code: parse.fs_scan`
- Why this node exists: Convert scan stdout JSONL into structured items.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
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

**Connection checklist for this node**
- Incoming: `SSH: scan.filesystem` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: diff.fs_db`

### Step 6 - `Postgres: fetch.all_videos`
- Add node type: `Postgres`
- Rename node to: `Postgres: fetch.all_videos`
- Why this node exists: Load full video inventory from DB.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query**
```text
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

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Set: config` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: diff.fs_db`

### Step 7 - `Code: diff.fs_db`
- Add node type: `Code`
- Rename node to: `Code: diff.fs_db`
- Why this node exists: Compute orphans/missing/mismatches summary.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Diff filesystem vs database
const fsItems = $('Code: parse.fs_scan').all();
const dbItems = $('Postgres: fetch.all_videos').all();

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

**Connection checklist for this node**
- Incoming: `Code: parse.fs_scan` output branch `0` -> this node
- Incoming: `Postgres: fetch.all_videos` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: drift.found?`

### Step 8 - `IF: drift.found?`
- Add node type: `If`
- Rename node to: `IF: drift.found?`
- Why this node exists: Only alert if drift summary is non-zero.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.summary.orphans_count > 0 \|\| $json.summary.missing_count > 0 \|\| $json.summary.mismatch_count > 0}}"}]}` |

**Connection checklist for this node**
- Incoming: `Code: diff.fs_db` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Email: send.report`

### Step 9 - `Email: send.report`
- Add node type: `Send Email`
- Rename node to: `Email: send.report`
- Why this node exists: Send reconciliation report email.

| UI Field | Value |
|---|---|
| `fromEmail` | `noreply@reachy.local` |
| `toEmail` | `rustybee255@gmail.com` |
| `subject` | `=Reconciler Report: {{$json.summary.orphans_count}} orphans, {{$json.summary.missing_count}} missing` |
| `emailType` | `text` |
| `message` | `=Reconciler completed at {{$json.timestamp}}

Summary:
- FS files: {{$json.summary.total_fs}}
- DB records: {{$json.summary.total_db}}
- Orphans (FS only): {{$json.summary.orphans_count}}
- Missing (DB only): {{$json.summary.missing_count}}
- Mismatches: {{$json.summary.mismatch_count}}

Review in database or n8n execution logs.` |

**Connection checklist for this node**
- Incoming: `IF: drift.found?` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Schedule: daily 02:15` branch `0` -> `Set: config`
- `Webhook: manual.trigger` branch `0` -> `Set: config`
- `Set: config` branch `0` -> `SSH: scan.filesystem`
- `Set: config` branch `0` -> `Postgres: fetch.all_videos`
- `SSH: scan.filesystem` branch `0` -> `Code: parse.fs_scan`
- `Code: parse.fs_scan` branch `0` -> `Code: diff.fs_db`
- `Postgres: fetch.all_videos` branch `0` -> `Code: diff.fs_db`
- `Code: diff.fs_db` branch `0` -> `IF: drift.found?`
- `IF: drift.found?` branch `0` -> `Email: send.report`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
