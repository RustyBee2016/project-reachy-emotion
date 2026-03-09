# PostgreSQL Node Reference — n8n v3 Codex Workflows

This document catalogs every PostgreSQL node across all v3 Codex n8n workflows, explaining **what** each node does, **why** it exists, and **exactly how** to wire and configure it.

All Postgres nodes use the credential `PostgreSQL - reachy_local` (credential type: `postgres`).

---

## Summary Table

| Workflow (Module) | Node Name | Operation | Purpose |
|---|---|---|---|
| 02 — Labeling Agent | `Postgres: fetch.video` | `executeQuery` (SELECT) | Read current video state before label mutation |
| 02 — Labeling Agent | `Postgres: apply.label` | `executeQuery` (INSERT+UPDATE) | Write label event + update video label |
| 02 — Labeling Agent | `Postgres: class.balance` | `executeQuery` (SELECT) | Compute per-class training counts for UI feedback |
| 04 — Reconciler Agent | `Postgres: fetch.all_videos` | `executeQuery` (SELECT) | Load full video inventory for FS/DB diff |
| 05 — Training Orchestrator | `Postgres: check.train_balance` | `executeQuery` (SELECT) | Count per-class train samples to gate training |
| 06 — Evaluation Agent | `Postgres: check.test_balance` | `executeQuery` (SELECT) | Count per-class test samples to gate evaluation |
| 08 — Privacy Agent | `Postgres: find.old_temp` | `executeQuery` (SELECT) | Select expired temp records for purge |
| 08 — Privacy Agent | `Postgres: mark.purged` | `executeQuery` (UPDATE) | Mark video row as purged after file deletion |
| 08 — Privacy Agent | `Postgres: audit.log` | `insert` | Insert purge action into audit_log table |
| 09 — Observability Agent | `Postgres: store.metrics` | `insert` | Persist telemetry samples to obs_samples table |

---

## Workflow-by-Workflow Detail

---

### Module 02 — Labeling Agent

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`

This workflow has **3 Postgres nodes** that together handle label persistence, audit trail, and class-balance reporting.

#### 1) `Postgres: fetch.video`

**Purpose:** Fetch the current DB state (split, label, file_path) for a video before applying any label mutation. Acts as a pre-read to verify the video exists.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query:**
```sql
SELECT v.video_id, v.split, v.label AS current_label, v.file_path
FROM video v
WHERE v.video_id = '{{$json.video_id}}'::uuid;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `Code: validate.payload` (branch 0) — receives the validated/normalized label submission payload containing `video_id`.
- **Output to:** `Postgres: apply.label` (branch 0) — passes the fetched video state downstream.

**Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

---

#### 2) `Postgres: apply.label`

**Purpose:** Apply the label update atomically — inserts a `label_event` audit record and updates `video.label` in a single CTE query. Uses idempotency key conflict handling to prevent duplicate label events.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query:**
```sql
WITH ins AS (
  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)
  VALUES (
    '{{$json.video_id}}'::uuid,
    '{{$json.label}}',
    '{{$json.action}}',
    '{{$json.rater_id}}',
    '{{$json.notes}}',
    '{{$json.idempotency_key}}'
  )
  ON CONFLICT (video_id, idempotency_key) DO NOTHING
  RETURNING event_id
)
UPDATE video
SET label = '{{$json.label}}',
    updated_at = NOW()
WHERE video_id = '{{$json.video_id}}'::uuid
RETURNING
  video_id,
  label,
  split,
  (SELECT event_id FROM ins) AS event_id;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `Postgres: fetch.video` (branch 0) — receives the validated payload data (the fetch result flows through but the SQL references `$json` fields set earlier by `Code: validate.payload`).
- **Output to:** `Switch: branch.action` (branch 0) — the switch routes to relabel/promote/discard/label-only paths.

**Schema bindings:**
- `LabelEvent` (`models.py:269`) — audit table
- `Video` (`models.py:41`) — label column update
- Constraint `chk_video_split_label_policy` (`models.py:95`) can reject invalid split/label combinations at the DB layer.

---

#### 3) `Postgres: class.balance`

**Purpose:** Compute per-class label counts across the training split. Returns `happy_count`, `sad_count`, `neutral_count`, and `total_train` for the webhook response body. The UI uses these counts to show class-balance status.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query:**
```sql
SELECT
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(CASE WHEN label = 'neutral' AND split = 'train' THEN 1 END) AS neutral_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring (convergence node — 3 inputs):**
- **Input from:** `Switch: branch.action` (branch 3, "discard" path) — skips relabel/promote, goes straight to balance.
- **Input from:** `HTTP: mm.relabel` (branch 0) — after relabel completes.
- **Input from:** `HTTP: mm.promote` (branch 0) — after promote completes.
- **Output to:** `Respond: success` (branch 0) — balance counts are included in the webhook response.

---

### Module 04 — Reconciler/Audit Agent

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`

This workflow has **1 Postgres node** that loads the DB-side inventory for comparison against the filesystem.

#### 1) `Postgres: fetch.all_videos`

**Purpose:** Load the complete video inventory from the database. This result set is compared against an SSH filesystem scan to detect drift (orphans, missing files, size/split mismatches).

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |
| `options` | `{}` |

**SQL Query:**
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

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring (parallel execution):**
- **Input from:** `Set: config` (branch 0) — runs in **parallel** with `SSH: scan.filesystem`, which also receives from `Set: config` branch 0.
- **Output to:** `Code: diff.fs_db` (branch 0) — the diff Code node references this node's output via `$('Postgres: fetch.all_videos').all()` to build the DB-side map.

**Important:** This node and `SSH: scan.filesystem` both feed into `Code: diff.fs_db` as parallel inputs. The Code node uses n8n's `$('node_name').all()` syntax to access both datasets.

**Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

---

### Module 05 — Training Orchestrator

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/05_training_orchestrator_efficientnet.json`

This workflow has **1 Postgres node** that serves as a data-balance preflight check.

#### 1) `Postgres: check.train_balance`

**Purpose:** Count per-class sample sizes in the training split (`happy`, `sad`, `neutral`). The downstream `IF: sufficient_data?` node requires a minimum of 50 samples per class before allowing training to proceed.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query:**
```sql
SELECT
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='neutral' AND split='train') AS neutral_train
FROM video;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `Webhook: training.start` (branch 0) — this is the very first processing node after the webhook trigger.
- **Output to:** `IF: sufficient_data?` (branch 0) — the IF node evaluates `Math.min($json.happy_train, $json.sad_train, $json.neutral_train) >= 50`. If true, training proceeds; if false, an `insufficient_data` event is emitted.

---

### Module 06 — Evaluation Agent

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/06_evaluation_agent_efficientnet.json`

This workflow has **1 Postgres node** that serves as a test-data balance gate.

#### 1) `Postgres: check.test_balance`

**Purpose:** Count per-class sample sizes in the test split. The downstream `IF: test_set.balanced?` node requires a minimum of 20 samples per class before allowing evaluation to proceed.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query:**
```sql
SELECT
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test,
  COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test
FROM video;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `Webhook: evaluation.start` (branch 0) — first processing node after the webhook.
- **Output to:** `IF: test_set.balanced?` (branch 0) — evaluates `Math.min($json.happy_test, $json.sad_test, $json.neutral_test) >= 20`. True proceeds to evaluation; false routes to a blocked-status path.

**Critical alignment note:** The DB policy constraint `chk_video_split_label_policy` (`models.py:95`) enforces `label IS NULL` for `split='test'`. If this policy is strictly followed, this query will return zeros and the blocked path will always trigger unless test labels are tracked separately.

---

### Module 08 — Privacy/Retention Agent

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/08_privacy_agent.json`

This workflow has **3 Postgres nodes** forming a find → mark → audit chain for data purging.

#### 1) `Postgres: find.old_temp`

**Purpose:** Select video records eligible for purge — rows in the `temp` split that are older than 7 days.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query:**
```sql
SELECT video_id, file_path
FROM video
WHERE split='temp' AND created_at < NOW() - INTERVAL '7 days';
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring (2 inputs — convergence node):**
- **Input from:** `Schedule: daily 03:00` (branch 0) — automatic daily trigger at 3 AM.
- **Input from:** `Webhook: gdpr.deletion` (branch 0) — manual GDPR purge trigger (`POST /webhook/privacy/purge`).
- **Output to:** `Loop: batch.delete` (branch 0) — feeds candidate rows into a batch loop (50 items per batch).

**Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

---

#### 2) `Postgres: mark.purged`

**Purpose:** After a file is physically deleted via SSH, update the video's DB row to set `split='purged'` and refresh `updated_at`. This ensures the DB reflects reality.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query:**
```sql
UPDATE video
SET split='purged', updated_at=NOW()
WHERE video_id='{{$json.video_id}}'::uuid;
```

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `SSH: delete.file` (branch 0) — executes after the physical file deletion (`rm -f /videos/{{$json.file_path}}`).
- **Output to:** `Postgres: audit.log` (branch 0) — passes the video_id to the audit logger.

**Constraint coupling:** Aligns with `chk_video_split_label_policy` (`models.py:95`) — non-train rows must be unlabeled.

---

#### 3) `Postgres: audit.log`

**Purpose:** Insert an audit record for each purge operation into the `audit_log` table for compliance and traceability.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `insert` |
| `table` | `audit_log` |
| `columns` | `action, video_id, reason, timestamp` |

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring (1 input, 2 outputs):**
- **Input from:** `Postgres: mark.purged` (branch 0).
- **Output to:** `Loop: batch.delete` (branch 0) — loops back for the next batch item.
- **Output to:** `HTTP: emit.purged` (branch 0) — emits a `privacy.purged` event to the gateway pipeline endpoint.

**Note:** This is the only Postgres node in the v3 workflows that uses the n8n `insert` operation mode (with `table` and `columns` fields) rather than `executeQuery`. The incoming item's JSON fields (`action`, `video_id`, `reason`, `timestamp`) are mapped to columns automatically by n8n.

**Schema binding:** `AuditLog` model (`models.py:344`).

---

### Module 09 — Observability/Telemetry Agent

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/09_observability_agent.json`

This workflow has **1 Postgres node** that acts as the telemetry data sink.

#### 1) `Postgres: store.metrics`

**Purpose:** Insert parsed Prometheus metric samples into the `obs_samples` table, creating a historical time-series for dashboarding and alert queries.

**Configuration:**

| UI Field | Value |
|---|---|
| `operation` | `insert` |
| `table` | `obs_samples` |
| `columns` | `ts, src, metric, value` |

**Credential:** `postgres` → `PostgreSQL - reachy_local`

**Wiring:**
- **Input from:** `Code: parse.metrics` (branch 0) — receives normalized metric items, each with fields `ts` (ISO timestamp), `src` (service name: `n8n`, `media_mover`, or `gateway`), `metric` (metric name), and `value` (numeric value).
- **Output to:** None — this is a terminal/sink node.

**Schema binding:** `ObsSample` model (`apps/api/app/db/models.py:371`).

**Metrics alignment note:** The upstream `Code: parse.metrics` node expects specific Prometheus metric names (`media_mover_promote_total`, `gateway_queue_depth`) that must match what the services actually export. If metric names differ in the codebase, inserts will have null values and be filtered out.

---

## Common Configuration Patterns

### Credential Setup
All Postgres nodes share the same credential configuration:
- **Credential type:** `postgres`
- **Display name:** `PostgreSQL - reachy_local`
- This credential must be created in n8n **before** wiring any workflow.

### Operation Modes Used
1. **`executeQuery`** — Used by 8 of 10 nodes. Allows raw SQL with n8n expression templating (`{{$json.field}}`). Used for SELECT, UPDATE, and CTE (INSERT+UPDATE) queries.
2. **`insert`** — Used by 2 nodes (`Postgres: audit.log`, `Postgres: store.metrics`). Uses n8n's built-in column mapping where `table` and `columns` are specified in the UI, and incoming JSON fields are auto-mapped to column names.

### Expression Templating
SQL queries use n8n's `{{$json.field}}` syntax to inject values from upstream node output. For UUID fields, the pattern `'{{$json.video_id}}'::uuid` is used for PostgreSQL type casting.

---

## Workflow Wiring Diagrams (Postgres Node Context)

### Module 02 — Labeling Agent
```
Webhook → Code:validate → Postgres:fetch.video → Postgres:apply.label → Switch:branch.action
                                                                              ├─ HTTP:mm.relabel ──┐
                                                                              ├─ HTTP:mm.promote ──┤
                                                                              └─ (discard) ────────┤
                                                                                                    ▼
                                                                                        Postgres:class.balance → Respond
```

### Module 04 — Reconciler Agent
```
Schedule/Webhook → Set:config ─┬─ SSH:scan.filesystem → Code:parse.fs_scan ─┐
                               └─ Postgres:fetch.all_videos ─────────────────┤
                                                                              ▼
                                                                    Code:diff.fs_db → IF → Email
```

### Module 05 — Training Orchestrator
```
Webhook → Postgres:check.train_balance → IF:sufficient_data? → (training pipeline...)
                                              └─ HTTP:emit.insufficient_data
```

### Module 06 — Evaluation Agent
```
Webhook → Postgres:check.test_balance → IF:test_set.balanced? → (evaluation pipeline...)
                                              └─ Code:prepare.blocked_status → HTTP:status.blocked
```

### Module 08 — Privacy Agent
```
Schedule/Webhook → Postgres:find.old_temp → Loop:batch.delete → SSH:delete.file
                                                    ▲                    │
                                                    │                    ▼
                                            Postgres:audit.log ← Postgres:mark.purged
                                                    │
                                                    ▼
                                            HTTP:emit.purged
```

### Module 09 — Observability Agent
```
Cron ─┬─ HTTP:n8n.metrics ──────────┐
      ├─ HTTP:mediamover.metrics ────┤
      └─ HTTP:gateway.metrics ───────┤
                                     ▼
                           Code:parse.metrics → Postgres:store.metrics
```
