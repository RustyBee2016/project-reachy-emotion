# Agent 4 — Reconciler / Audit Agent (Workflow `04_reconciler_agent.json`)

Rusty, this walkthrough details every node for the reconciler workflow. It starts with an alphabetical inventory, then describes each node's inputs, parameters, and how they connect. Dynamic parameters are shown as JSON so you can paste them directly into n8n.

## Alphabetical inventory of nodes (workflow scope)
- Code: diff.fs_db
- Code: parse.fs_scan
- Email: send.report
- IF: drift.found?
- Postgres: fetch.all_videos
- SSH: scan.filesystem
- Schedule: daily 02:15
- Set: config
- Webhook: manual.trigger

---

## Node-by-node flow details
The reconciler runs either on a daily schedule or via a manual webhook. It seeds base settings, scans the filesystem over SSH, fetches database records, diffs the two datasets, and sends a report email when drift is detected.

### Schedule node
**Schedule: daily 02:15** — Cron trigger that kicks off the daily reconciliation run and feeds into the configuration node.

Parameters:
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "15 2 * * *"
      }
    ]
  }
}
```

### Webhook node
**Webhook: manual.trigger** — Allows on-demand reconciliation via HTTP GET at `/reconciler/audit`. It forwards the request to the configuration node; response is controlled by downstream nodes.

Parameters:
```json
{
  "httpMethod": "GET",
  "path": "reconciler/audit",
  "responseMode": "onReceived",
  "options": {}
}
```

### Set node
**Set: config** — Establishes baseline settings shared by both triggers. Emits `root_dir` and `safe_fix` flags that downstream nodes can use.

Parameters:
```json
{
  "assignments": {
    "assignments": [
      { "id": "1", "name": "root_dir", "value": "/videos", "type": "string" },
      { "id": "2", "name": "safe_fix", "value": "=false", "type": "boolean" }
    ]
  }
}
```

### SSH node
**SSH: scan.filesystem** — Runs a `find` command over SSH to enumerate MP4 files across splits. Output is JSONL; each line has `file_path`, `size_bytes`, and `mtime`. Feeds the parser code node.

Parameters:
```json
{
  "command": "find /videos/{temp,train,test,dataset_all} -type f -name '*.mp4' -printf '{\\\"file_path\\\":\\\"%P\\\",\\\"size_bytes\\\":%s,\\\"mtime\\\":\\\"%TY-%Tm-%TdT%TH:%TM:%TSZ\\\"}\\\\n'",
  "authentication": "password"
}
```

### Code nodes
**Code: parse.fs_scan** — Parses the JSONL from the SSH node. For each file, it extracts path, size, mtime, and derives the split from the top-level folder. Malformed lines are skipped. Outputs one item per file for comparison.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Parse JSONL filesystem scan results\nconst output = $json.stdout || '';\nconst lines = output.split('\\n').filter(Boolean);\nconst items = [];\n\nfor (const line of lines) {\n  try {\n    const obj = JSON.parse(line);\n    const pathParts = obj.file_path.split('/');\n    const split = pathParts[0];\n    \n    items.push({\n      json: {\n        file_path: obj.file_path,\n        size_bytes: parseInt(obj.size_bytes, 10),\n        mtime: obj.mtime,\n        split,\n        source: 'fs'\n      }\n    });\n  } catch (e) {\n    // Skip malformed lines\n  }\n}\n\nreturn items;"
}
```

**Code: diff.fs_db** — Compares filesystem items to database rows from the Postgres node. Builds counts for totals, orphans (FS only), missing (DB only), and size/split mismatches. Emits a summary object plus detailed arrays for later reporting.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Diff filesystem vs database\nconst fsItems = $('parse_fs_scan').all();\nconst dbItems = $('db_fetch_all').all();\n\n// Build maps\nconst fsMap = new Map();\nfor (const item of fsItems) {\n  fsMap.set(item.json.file_path, item.json);\n}\n\nconst dbMap = new Map();\nfor (const item of dbItems) {\n  dbMap.set(item.json.file_path, item.json);\n}\n\n// Find differences\nconst orphans_fs = [];\nconst missing_fs = [];\nconst mismatches = [];\n\n// Orphans: in FS, not in DB\nfor (const [path, fsData] of fsMap) {\n  if (!dbMap.has(path)) {\n    orphans_fs.push({ file_path: path, ...fsData });\n  }\n}\n\n// Missing: in DB, not in FS\nfor (const [path, dbData] of dbMap) {\n  if (!fsMap.has(path)) {\n    missing_fs.push({ file_path: path, video_id: dbData.video_id });\n  } else {\n    // Check for mismatches\n    const fsData = fsMap.get(path);\n    if (fsData.size_bytes !== dbData.size_bytes || fsData.split !== dbData.split) {\n      mismatches.push({\n        file_path: path,\n        fs_size: fsData.size_bytes,\n        db_size: dbData.size_bytes,\n        fs_split: fsData.split,\n        db_split: dbData.split\n      });\n    }\n  }\n}\n\nreturn [{\n  json: {\n    summary: {\n      total_fs: fsMap.size,\n      total_db: dbMap.size,\n      orphans_count: orphans_fs.length,\n      missing_count: missing_fs.length,\n      mismatch_count: mismatches.length\n    },\n    orphans_fs,\n    missing_fs,\n    mismatches,\n    timestamp: new Date().toISOString()\n  }\n}];"
}
```

### Postgres node
**Postgres: fetch.all_videos** — Reads the `video` table (id, path, split, label, size, sha256, updated_at). Feeds the diff code node alongside filesystem items.

Parameters:
```json
{
  "operation": "executeQuery",
  "query": "SELECT\n  video_id,\n  file_path,\n  split,\n  label,\n  size_bytes,\n  sha256,\n  updated_at\nFROM video;",
  "options": {}
}
```

### IF node
**IF: drift.found?** — Checks whether any orphans, missing files, or mismatches exist. True branch triggers the email report; false branch ends the workflow quietly.

Parameters:
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.summary.orphans_count > 0 || $json.summary.missing_count > 0 || $json.summary.mismatch_count > 0}}"
      }
    ]
  }
}
```

### Email node
**Email: send.report** — Composes a plaintext summary email to Rusty when drift is detected. Includes counts and a timestamp from the diff node output. Downstream flow ends after sending.

Parameters:
```json
{
  "fromEmail": "noreply@reachy.local",
  "toEmail": "rustybee255@gmail.com",
  "subject": "=Reconciler Report: {{$json.summary.orphans_count}} orphans, {{$json.summary.missing_count}} missing",
  "emailType": "text",
  "message": "=Reconciler completed at {{$json.timestamp}}\n\nSummary:\n- FS files: {{$json.summary.total_fs}}\n- DB records: {{$json.summary.total_db}}\n- Orphans (FS only): {{$json.summary.orphans_count}}\n- Missing (DB only): {{$json.summary.missing_count}}\n- Mismatches: {{$json.summary.mismatch_count}}\n\nReview in database or n8n execution logs."
}
```

### Flow wiring (inputs between nodes)
- **Schedule** → Set config → SSH scan.filesystem → Code parse.fs_scan → Code diff.fs_db → IF drift.found? → Email send.report (when true).
- **Webhook** → Set config (shares path with schedule trigger and downstream nodes).
- **Set config** also fans out to Postgres fetch.all_videos, which feeds the diff.fs_db node alongside parsed filesystem data.

This layout ensures the reconciler can run automatically each morning or on demand, compare filesystem and database state, and notify you immediately when drift appears.
