# MODULE 04 — Reconciler / Audit Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`

## Runtime Goal
Compare filesystem reality with DB records, detect drift (orphans/missing/mismatches), and notify operators.

## Node-to-Script Map

### 1) `Schedule: daily 02:15` (`Schedule Trigger`)
- **Workflow role:** automatic daily reconciliation trigger.
- **Cron expression:** `15 2 * * *`.

### 2) `Webhook: manual.trigger` (`Webhook`)
- **Workflow role:** on-demand reconciliation entry.
- **Path/method:** `GET /webhook/reconciler/audit`.

### 3) `Set: config` (`Set`)
- **Workflow role:** injects workflow constants.
- **Fields:** `root_dir=/videos`, `safe_fix=false`.
- **Note:** values are not consumed by downstream SQL directly; they are informational unless you extend code nodes.

### 4) `SSH: scan.filesystem` (`SSH`)
- **Workflow role:** enumerates media files from disk.
- **Command behavior:** `find /videos/{temp,train,test} ... -printf JSONL` for each `.mp4`.
- **Output:** line-delimited JSON records with `file_path`, `size_bytes`, `mtime`.

### 5) `Code: parse.fs_scan` (`Code`)
- **Workflow role:** transforms raw SSH stdout into n8n item stream.
- **Essential in-node logic:**
- splits stdout by newline
- JSON parses each line
- infers split from first path segment
- emits one item per file (`source='fs'`)
- skips malformed lines (non-fatal)

### 6) `Postgres: fetch.all_videos` (`Postgres`)
- **Workflow role:** loads DB canonical inventory.
- **SQL target:** `video` table (`video_id`, `file_path`, `split`, `label`, `size_bytes`, `sha256`, `updated_at`).
- **Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

### 7) `Code: diff.fs_db` (`Code`)
- **Workflow role:** computes drift sets.
- **Essential in-node logic:**
- builds map by `file_path` for FS and DB
- `orphans_fs`: exists in FS, missing in DB
- `missing_fs`: exists in DB, missing in FS
- `mismatches`: size/split disagreement
- outputs summary counts + detail arrays

### 8) `IF: drift.found?` (`If`)
- **Workflow role:** drift gate.
- **Expression:** any of `orphans_count`, `missing_count`, `mismatch_count` > 0.
- **Branching:** true path notifies by email.

### 9) `Email: send.report` (`Email Send`)
- **Workflow role:** sends drift report with summary counts and timestamp.

## How This Delivers Reconciliation Functionality
1. Triggered by schedule or manual endpoint.
2. Collects FS and DB inventories independently.
3. Diffs both sources to identify consistency drift.
4. Escalates anomalies via email.

## Script/Model Alignment Notes
- Promotion flow intentionally accepts temporary FS/DB divergence around commit boundary (`apps/api/routers/media.py:375-383`), making this reconciler essential.
- `ReconcileReport` model exists (`apps/api/app/db/models.py:392`) but this workflow currently does not persist report rows; it only emits email + n8n logs.
