# 04_Develop Reconciler Agent

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:16:36  
**Updated:** 10/21/2025 22:04:40  
**Exported:** 10/21/2025 22:05:30  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9aff2-1ee0-832e-a208-bf27ac362df2](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9aff2-1ee0-832e-a208-bf27ac362df2)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 4: Reconciler / Audit Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

## Response:
Thought for 20s

You’re building the cop who walks the beat at night: finds drift between DB ↔ filesystem ↔ manifests, files tickets, and only fixes what it’s allowed to. Below is a practical, “drop into n8n” plan for Agent 4: Reconciler / Audit Agent—complete nodes, params, and two importable workflows (main + error workflow). I bias for DB-as-truth (per your reqs), no destructive actions by default, all edits behind human gates.

* * *

What this agent does (scope)
============================

**Nightly + on-demand** it will:

1.  **Scan FS** under `/videos/{temp,train,test,thumbs,manifests}` and compute facts: path, size, mtime, split, optional sha256.
2.  **Query DB** tables (`video`, `run_link`) for canonical metadata.
3.  **Compare**:
    *   Orphans on disk (no DB row)
    *   Missing-on-disk (DB row but file gone)
    *   Mismatch (size/split/label)
    *   Thumb/manifest gaps
4.  **Emit a report** (JSON + markdown summary), push metrics, and open a **curation ticket** (e.g., GitHub issue/Email/Slack—stubbed in the JSON to Email for now).
5.  **(Optional) Safe actions** behind a boolean: rebuild manifests; re-gen missing thumbs; set `split='missing'` in DB for files that disappeared; never delete media by default.

Observability: pushes counters and timings; on failure, routes to a dedicated **Error Workflow**.

* * *

n8n nodes you’ll use (and why)
==============================

*   **Schedule Trigger**: Cron-like timer for nightly run; respects timezone (see docs and timezone caveats). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/?utm_source=chatgpt.com)
*   **Webhook**: manual trigger with `?dry_run=1` (for ad-hoc audits).
*   **Postgres**: `SELECT` with parameterized queries; optional `UPDATE` for safe fixes. [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
*   **SSH** or **Execute Command**: list files and compute hashes/metadata on Ubuntu 1 over SSH (preferred), or inside n8n container via a custom image. [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
*   **Split In Batches** + **IF** + **Merge**: paginate big file lists safely and gate actions. [n8n Docs+2n8n+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com)
*   **Function / Function Item**: normalize records, diff DB vs FS, craft summaries.
*   **HTTP Request**: call Media Mover endpoints (manifest rebuild), or push metrics.
*   **Error Trigger** + **Error handling**: centralized failure flow + optional “Stop and Error” guardrails. [n8n Docs+2n8n+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)

* * *

Credentials you’ll define
=========================

*   **SSH** (Ubuntu 1): key-based auth for `rusty_admin@10.0.4.130`.
*   **Postgres** (Ubuntu 1): read/write role for metadata DB.
*   (Optional) **Email/Slack** for the audit report.

* * *

Data contracts (lightweight)
============================

Common shape the diff code expects:

```json
{
  "video_id": "uuid-or-null",
  "split": "temp|train|test",
  "file_path": "videos/train/abc123.mp4",  // relative path as in DB
  "size_bytes": 12345678,
  "sha256": "optional",
  "mtime": "2025-10-10T01:23:45Z",
  "label": "happy|null",
  "source": "fs|db"
}
```

* * *

Workflow 1: Reconciler / Audit (nightly + manual)
=================================================

**Trigger**

*   **Schedule Trigger**  
    Mode: _Every Day_  
    Time: 02:15 local (set `GENERIC_TIMEZONE=America/New_York` on self-host). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/?utm_source=chatgpt.com)
*   **Webhook** (GET `/reconciler/audit`): optional manual run; accepts `dry_run` query.

**Initialize**

*   **Set (constants)**:
    *   `root_dir=/videos`
    *   `splits=["temp","train","test"]`
    *   `thumb_dir=/videos/thumbs`
    *   `manifest_dir=/videos/manifests`
    *   `max_batch=500`
    *   `safe_fix=false` (set to true to enable non-destructive fixes)
    *   `ttl_days_temp=14`

**Enumerate filesystem (Ubuntu 1)**

*   **SSH** → _Execute a command_ (host 10.0.4.130) [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)  
    Command (single line for JSONL):
    ```bash
    find /videos/{temp,train,test} -type f -name '*.mp4' -printf '{"file_path":"%P","size_bytes":%s,"mtime":"%TY-%Tm-%TdT%TH:%TM:%TSZ"}\n'
    ```
    (If you also want hashes on changed files only, run a second batched command for candidates; full-hash every night isn’t necessary.)
*   **Move Binary Data** (if needed) → **Function**: parse JSONL to items, derive `split` from path (segment 2), add `source="fs"`.
*   **Split In Batches**: make it process in chunks of `{{$json.max_batch}}` for any follow-up per-file calls (e.g., sha256). Use the documented `noItemsLeft` pattern with an **IF** loop if you expand hashing later. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com)

**Query DB**

*   **Postgres** → _Execute Query_ (read) [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
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
    (Store as items with `source="db"`; ensure you return **relative** paths like `videos/train/abc123.mp4` to match FS.)

**Normalize & Diff**

*   **Function** node “diff\_db\_fs”:
    *   Build two maps keyed by `file_path`.
    *   **Orphans (FS-only)**: in FS map, not in DB map.
    *   **Missing on disk (DB-only)**: in DB map, not in FS map.
    *   **Mismatches**: same path, but `size_bytes` or `split` or `label` differs.
    *   **Thumb gaps**: for each item, ensure `/videos/thumbs/{stem}.jpg` exists; produce “missing\_thumb” set.
    *   **Manifest gaps**: ensure a current manifest file exists (you can keep it simple: request Media Mover to rebuild per run).
    Emit four arrays: `orphans_fs`, `missing_fs`, `mismatches`, `thumb_gaps`.

**Decide actions (non-destructive by default)**

*   **IF (safe\_fix == true)**:
    *   **Mismatches (split drift)** → **Postgres** _Execute Query (write)_ to update `split` to the FS-observed split **only** if it’s a benign move (e.g., `temp→train/test` should be policy-gated; leave as report unless you explicitly allow).
    *   **Missing on disk** → set `split='missing'` or append to an `audit_missing` table; **don’t delete DB rows**.
    *   **Thumb gaps** → **HTTP Request** to Media Mover thumb (or your internal “thumb rebuild” endpoint) to regenerate; otherwise enqueue a job.
    *   **Manifest** → **HTTP Request** `POST /api/manifest/rebuild` (idempotent) to refresh JSONL; capture returned `dataset_hash`.
*   **ELSE** (default): skip writes, only report + metrics.

**Metrics**

*   **Function** builds counters: `count_orphans`, `count_missing`, `count_mismatch`, `count_thumb_gaps`, `duration_ms`.
*   **HTTP Request** (optional) → push to Pushgateway or hit a tiny internal `/metrics/inc` endpoint. (If you use Prometheus scraping only, skip push and instead expose counts via your Media Mover; the agent can also POST to a FastAPI _/audit_ endpoint you add.)

**Report**

*   **Function** → craft markdown summary + attach JSON details.
*   **Email (or Slack)** node → send to on-call.
*   **Set** → small JSON “audit\_result” envelope with `correlation_id`, timestamps, and the arrays.

**Finish**

*   **IF** (`count_orphans + count_missing + count_mismatch + count_thumb_gaps > 0`) → set workflow to **success with findings**; otherwise soft green.

**Failure path**

*   Any node with “Continue On Fail = false” bubbles to the **Error Workflow** via n8n’s **Error Trigger** (configured below). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)

* * *

Workflow 2: Error workflow (centralized)
========================================

Create a second workflow with a single **Error Trigger** node. On run:

*   **Error Trigger** → captures failing workflow id, error, last node, JSON. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)
*   **Function** → reduce noisy stacks, attach `correlation_id`.
*   **Email/Slack** → notify with link to execution and a 10-line summary.
*   (Optional) **Postgres** → insert into an `audit_failures` table (timestamp, node, message, retryable flag).

* * *

Importable n8n JSON (main workflow)
===================================

> **Note:** This is a lean, self-contained starter. It assumes you’ve created **SSH** and **Postgres** credentials in n8n named `ubuntu1_ssh` and `ubuntu1_pg`. The “HTTP Request” nodes for Media Mover/metrics are present but disabled by default—flip them on when those endpoints are ready. Batch hashing and tickets are stubbed for later.

```json
{
  "name": "Agent 4 — Reconciler / Audit (Reachy_Local_08.3.3)",
  "nodes": [
    {
      "id": "schedule",
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [200, 200],
      "parameters": {
        "triggerTimes": {
          "item": [
            {
              "hour": 2,
              "minute": 15
            }
          ]
        }
      }
    },
    {
      "id": "webhook",
      "name": "Webhook (Manual Audit)",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [200, 380],
      "parameters": {
        "path": "reconciler/audit",
        "httpMethod": "GET",
        "responseMode": "onReceived"
      }
    },
    {
      "id": "init",
      "name": "Set Constants",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [420, 280],
      "parameters": {
        "values": {
          "string": [
            { "name": "root_dir", "value": "/videos" },
            { "name": "thumb_dir", "value": "/videos/thumbs" },
            { "name": "manifest_dir", "value": "/videos/manifests" }
          ],
          "json": [
            { "name": "splits", "value": ["temp", "train", "test"] }
          ],
          "number": [
            { "name": "max_batch", "value": 500 },
            { "name": "ttl_days_temp", "value": 14 }
          ],
          "boolean": [
            { "name": "safe_fix", "value": false }
          ]
        },
        "options": { "dotNotation": true }
      }
    },
    {
      "id": "ssh_list",
      "name": "SSH — List MP4s",
      "type": "n8n-nodes-base.ssh",
      "typeVersion": 1,
      "position": [660, 200],
      "credentials": { "ssh": { "id": "__REPLACE_WITH_ID__", "name": "ubuntu1_ssh" } },
      "parameters": {
        "command": "find /videos/{temp,train,test} -type f -name '*.mp4' -printf '{\"file_path\":\"%P\",\"size_bytes\":%s,\"mtime\":\"%TY-%Tm-%TdT%TH:%TM:%TSZ\"}\\n'"
      }
    },
    {
      "id": "parse_fs",
      "name": "Function — Parse FS JSONL",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [880, 200],
      "parameters": {
        "functionCode": "const lines = $json.data ? $json.data.split('\\n') : ($item(0).json.data || '').split('\\n');\nconst items = [];\nfor (const line of lines) {\n  if (!line.trim()) continue;\n  const obj = JSON.parse(line);\n  const parts = obj.file_path.split('/');\n  obj.split = parts[1];\n  obj.source = 'fs';\n  items.push(obj);\n}\nreturn items.map(v => ({json: v}));"
      }
    },
    {
      "id": "pg_select",
      "name": "Postgres — Load DB Rows",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 1,
      "position": [660, 380],
      "credentials": { "postgres": { "id": "__REPLACE_WITH_ID__", "name": "ubuntu1_pg" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT video_id, file_path, split, label, size_bytes, sha256, updated_at FROM video;"
      }
    },
    {
      "id": "tag_db",
      "name": "Function — Tag DB Items",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [880, 380],
      "parameters": {
        "functionCode": "return items.map(i => ({json: {...i.json, source: 'db'}}));"
      }
    },
    {
      "id": "merge_inputs",
      "name": "Merge FS+DB (Pass-through)",
      "type": "n8n-nodes-base.merge",
      "typeVersion": 2,
      "position": [1100, 300],
      "parameters": { "mode": "passThrough" }
    },
    {
      "id": "diff",
      "name": "Function — Diff DB vs FS",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [1320, 300],
      "parameters": {
        "functionCode": "const fs = []; const db = [];\nfor (const it of items) (it.json.source==='fs'?fs:db).push(it.json);\nconst mapFs = new Map(fs.map(x=>[x.file_path,x]));\nconst mapDb = new Map(db.map(x=>[x.file_path,x]));\nconst orphans_fs = []; const missing_fs = []; const mismatches = []; const thumb_gaps = [];\nfor (const [k,v] of mapFs){ if(!mapDb.has(k)) orphans_fs.push(v); }\nfor (const [k,v] of mapDb){ if(!mapFs.has(k)) missing_fs.push(v); else {\n  const f = mapFs.get(k);\n  if ((v.size_bytes && f.size_bytes && Number(v.size_bytes)!==Number(f.size_bytes)) || (v.split && f.split && v.split!==f.split)) {\n    mismatches.push({db:v, fs:f});\n  }\n  const stem = k.replace(/^.*\\//,'').replace(/\\.mp4$/,'');\n  const thumb = `videos/thumbs/${stem}.jpg`;\n  // naive gap flag; real existence can come from an SSH test in a later iteration\n  if (thumb && !mapFs.has(thumb)) thumb_gaps.push({file_path: thumb, from: k});\n}}\nreturn [{json:{orphans_fs, missing_fs, mismatches, thumb_gaps}}];"
      }
    },
    {
      "id": "metrics",
      "name": "Function — Build Metrics",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [1540, 300],
      "parameters": {
        "functionCode": "const d = $json;\nconst counts = {\n  count_orphans: d.orphans_fs.length,\n  count_missing: d.missing_fs.length,\n  count_mismatch: d.mismatches.length,\n  count_thumb_gaps: d.thumb_gaps.length,\n};\nreturn [{json: {...d, ...counts, correlation_id: Date.now().toString() }}];"
      }
    },
    {
      "id": "report_md",
      "name": "Function — Markdown Summary",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [1760, 300],
      "parameters": {
        "functionCode": "const c = $json;\nconst lines = [];\nlines.push(`# Reconciler Audit — ${new Date().toISOString()}`);\nlines.push(`- Orphans on disk: **${c.count_orphans}**`);\nlines.push(`- Missing on disk (DB rows): **${c.count_missing}**`);\nlines.push(`- Mismatches: **${c.count_mismatch}**`);\nlines.push(`- Thumb gaps: **${c.count_thumb_gaps}**`);\nreturn [{json: { summary_md: lines.join('\\n'), details: c }}];"
      }
    },
    {
      "id": "email",
      "name": "Email — Send Audit",
      "type": "n8n-nodes-base.emailSend",
      "typeVersion": 2,
      "position": [1980, 300],
      "parameters": {
        "fromEmail": "reconciler@local",
        "toEmail": "rustybee255@gmail.com",
        "subject": "Reconciler Audit Report",
        "text": "{{$json.summary_md}}"
      }
    },
    {
      "id": "gate_fix",
      "name": "IF — safe_fix?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [1540, 480],
      "parameters": {
        "conditions": { "boolean": [ { "value1": "={{$json.safe_fix || $items(\"init\")[0].json.safe_fix}}" } ] }
      }
    },
    {
      "id": "manifest",
      "name": "HTTP — Rebuild Manifests (disabled)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [1760, 560],
      "disabled": true,
      "parameters": {
        "url": "http://10.0.4.130:8081/api/manifest/rebuild",
        "method": "POST",
        "jsonParameters": true,
        "options": { "timeout": 600000 }
      }
    },
    {
      "id": "pg_mark_missing",
      "name": "Postgres — Mark Missing (disabled)",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 1,
      "position": [1760, 480],
      "disabled": true,
      "credentials": { "postgres": { "id": "__REPLACE_WITH_ID__", "name": "ubuntu1_pg" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "UPDATE video SET split = 'missing', updated_at = now() WHERE file_path = ANY(:paths)",
        "additionalFields": {
          "queryParams": "={\"paths\": $json.details.missing_fs.map(x=>x.file_path)}"
        }
      }
    }
  ],
  "connections": {
    "schedule": { "main": [ [ { "node": "init", "type": "main", "index": 0 } ] ] },
    "webhook": { "main": [ [ { "node": "init", "type": "main", "index": 0 } ] ] },
    "init": { "main": [ [ { "node": "ssh_list", "type": "main", "index": 0 }, { "node": "pg_select", "type": "main", "index": 0 } ] ] },
    "ssh_list": { "main": [ [ { "node": "parse_fs", "type": "main", "index": 0 } ] ] },
    "parse_fs": { "main": [ [ { "node": "merge_inputs", "type": "main", "index": 0 } ] ] },
    "pg_select": { "main": [ [ { "node": "tag_db", "type": "main", "index": 0 } ] ] },
    "tag_db": { "main": [ [ { "node": "merge_inputs", "type": "main", "index": 1 } ] ] },
    "merge_inputs": { "main": [ [ { "node": "diff", "type": "main", "index": 0 } ] ] },
    "diff": { "main": [ [ { "node": "metrics", "type": "main", "index": 0 } ] ] },
    "metrics": { "main": [ [ { "node": "report_md", "type": "main", "index": 0 }, { "node": "gate_fix", "type": "main", "index": 0 } ] ] },
    "report_md": { "main": [ [ { "node": "email", "type": "main", "index": 0 } ] ] },
    "gate_fix": { "main": [ [ { "node": "pg_mark_missing", "type": "main", "index": 0 }, { "node": "manifest", "type": "main", "index": 0 } ] ] }
  },
  "pinData": {},
  "settings": {
    "timezone": "America/New_York",
    "errorWorkflow": "Agent 4 — Error Workflow"
  },
  "versionId": "0.1.0-reconciler"
}
```

* * *

Importable n8n JSON (error workflow)
====================================

```json
{
  "name": "Agent 4 — Error Workflow",
  "nodes": [
    {
      "id": "err",
      "name": "Error Trigger",
      "type": "n8n-nodes-base.errorTrigger",
      "typeVersion": 1,
      "position": [300, 300]
    },
    {
      "id": "shape",
      "name": "Function — Shape Error",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [540, 300],
      "parameters": {
        "functionCode": "const e = $json;\nconst msg = `Workflow ${e.workflow.name} failed at node ${e.execution.lastNodeExecuted}\\nReason: ${e.execution.error.message}`;\nreturn [{json:{subject:`Reconciler Failure: ${e.workflow.name}`, text: msg}}];"
      }
    },
    {
      "id": "alert",
      "name": "Email — Oncall",
      "type": "n8n-nodes-base.emailSend",
      "typeVersion": 2,
      "position": [780, 300],
      "parameters": {
        "fromEmail": "reconciler@local",
        "toEmail": "rustybee255@gmail.com",
        "subject": "={{$json.subject}}",
        "text": "={{$json.text}}"
      }
    }
  ],
  "connections": {
    "err": { "main": [ [ { "node": "shape", "type": "main", "index": 0 } ] ] },
    "shape": { "main": [ [ { "node": "alert", "type": "main", "index": 0 } ] ] }
  },
  "settings": {},
  "versionId": "0.1.0-reconciler-error"
}
```

* * *

How it aligns with your specs
=============================

*   **Nightly reconciler with Prometheus counters** → covered; prefer scrape over push, but HTTP push is stubbed. (Reqs §14: integrity & audits; §18 observability.) requirements\_08.3.3
*   **DB is the source of truth**; manifests derived and rebuilt on demand. (Reqs §14, §16) requirements\_08.3.3
*   **Idempotent ops** (manifest rebuild); **append-only promotion log** remains untouched here; agent only reports unless `safe_fix=true`. (Reqs §16 + §24) requirements\_08.3.3

* * *

Setup notes & small gotchas
===========================

*   **Timezone**: set `GENERIC_TIMEZONE=America/New_York` for predictable Schedule runs. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/common-issues/?utm_source=chatgpt.com)
*   **SSH vs Execute Command**: SSH is simplest. If you must run shell inside the n8n container, extend the image to include any needed tools (e.g., `findutils`, `coreutils`, `curl`) per Execute Command docs. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/?utm_source=chatgpt.com)
*   **Batching**: keep `max_batch` high for listing; if you add hashing, use **Split In Batches** with the `noItemsLeft` pattern to avoid long-running executions. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com)
*   **Error routing**: wire the main workflow’s **errorWorkflow** setting to “Agent 4 — Error Workflow” so every failure lands there. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)

* * *

“Turn it up later” (optional enhancements)
==========================================

*   **Thumb check by SSH**: actually `test -f /videos/thumbs/{stem}.jpg` in a batched SSH node to avoid false positives.
*   **Ticketing**: add GitHub Issues node for actionable tickets per group (orphans/missing/mismatch).
*   **Safe auto-fixes**: allow only `split='missing'` writes, never promotions; everything else remains a report.
*   **PGVector**: if you later keep file-level embeddings for search, n8n’s PGVector node exists—just not required here. [n8n Docs](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.vectorstorepgvector/?utm_source=chatgpt.com)
*   **Postgres Trigger**: you can also attach a second workflow using **Postgres Trigger** on `video` updates to immediately re-check a single path. [n8n Docs](https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.postgrestrigger/?utm_source=chatgpt.com)

* * *

If you want, I can flip `safe_fix=true` and wire **exact** SQL updates you’re comfortable with (e.g., only mark `split='missing'` for DB rows older than 24h that vanished). Or we keep it read-only and let the report drive manual curation. Your call.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)