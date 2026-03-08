# n8n Agent Node Reference -- Reachy Emotion Recognition System

**Version:** 08.4.2 (EfficientNet-B0 / 3-Class)
**Last Updated:** 2026-03-07
**Model:** EfficientNet-B0 (HSEmotion pre-trained)
**Emotion Classes:** `happy`, `sad`, `neutral`

> This document provides a comprehensive reference of every node used by each of
> the nine n8n agents and the ML Pipeline Orchestrator. For step-by-step wiring
> instructions, see the individual MODULE tutorials.

---

## Table of Contents

1. [Agent 1 -- Ingest Agent](#agent-1----ingest-agent)
2. [Agent 2 -- Labeling Agent](#agent-2----labeling-agent)
3. [Agent 3 -- Promotion/Curation Agent](#agent-3----promotioncuration-agent)
4. [Agent 4 -- Reconciler/Audit Agent](#agent-4----reconcileraudit-agent)
5. [Agent 5 -- Training Orchestrator (EfficientNet-B0)](#agent-5----training-orchestrator-efficientnet-b0)
6. [Agent 6 -- Evaluation Agent (EfficientNet-B0)](#agent-6----evaluation-agent-efficientnet-b0)
7. [Agent 7 -- Deployment Agent (EfficientNet-B0)](#agent-7----deployment-agent-efficientnet-b0)
8. [Agent 8 -- Privacy/Retention Agent](#agent-8----privacyretention-agent)
9. [Agent 9 -- Observability/Telemetry Agent](#agent-9----observabilitytelemetry-agent)
10. [ML Pipeline Orchestrator](#ml-pipeline-orchestrator)
11. [Node Type Summary](#node-type-summary)
12. [Credentials Reference](#credentials-reference)
13. [Environment Variables](#environment-variables)
14. [Architecture Patterns](#architecture-patterns)

---

## Agent 1 -- Ingest Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`
**Purpose:** Entry point for all video ingestion. Receives video URLs, downloads via Media Mover, stores metadata in PostgreSQL, and emits completion events.
**Tutorial:** [MODULE_01_INGEST_AGENT.md](MODULE_01_INGEST_AGENT.md)

### Node Inventory (12 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_trigger` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST requests at path `/video_gen_hook`. Returns HTTP 202 Accepted. Entry point for all video ingestion requests. |
| 2 | `auth_check` | **IF** (`n8n-nodes-base.if`) | Validates the `X-INGEST-KEY` header against the `INGEST_TOKEN` environment variable. Routes to `respond_401` on failure. |
| 3 | `respond_401` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 401 Unauthorized JSON response when authentication fails. |
| 4 | `normalize_payload` | **Code** (`n8n-nodes-base.code`) | JavaScript node that normalizes the incoming video payload. Extracts `source_url`, `label`, and `metadata` fields. Generates a correlation ID for tracing. |
| 5 | `media_pull` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Media Mover API (`{{MEDIA_MOVER_BASE_URL}}/api/v1/ingest/pull`) to download the video from the source URL. Returns a job ID for polling. |
| 6 | `wait_poll` | **Wait** (`n8n-nodes-base.wait`) | Pauses execution for 3 seconds before polling the Media Mover status endpoint. Part of the async polling loop. |
| 7 | `check_status` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET to Media Mover status endpoint to check if the download job has completed. Returns status field (`pending`, `processing`, `done`, `failed`). |
| 8 | `is_done` | **IF** (`n8n-nodes-base.if`) | Evaluates whether `status === "done"`. Routes to `db_insert` on success, or back to `increment_attempt` for retry. |
| 9 | `increment_attempt` | **Code** (`n8n-nodes-base.code`) | Increments the polling attempt counter. If attempts exceed 20 (max retries), raises an error to abort the workflow. Otherwise loops back to `wait_poll`. |
| 10 | `db_insert` | **Postgres** (`n8n-nodes-base.postgres`) | Inserts the video record into the `video` table with ffprobe metadata (duration, fps, width, height, size_bytes, sha256). Uses SHA256 for deduplication (`ON CONFLICT DO NOTHING`). |
| 11 | `emit_event` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway API (`{{GATEWAY_BASE_URL}}/api/events/ingest`) to emit an `ingest.completed` event with video_id and metadata. |
| 12 | `respond_success` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 200 JSON response with `{status: "ingested", video_id, file_path}`. |

### Data Flow

```
webhook_trigger
  │
  ├──[auth fails]──► auth_check ──► respond_401
  │
  └──[auth passes]──► normalize_payload ──► media_pull ──► wait_poll
                                                              │
                                              ┌───────────────┘
                                              ▼
                                         check_status ──► is_done
                                              ▲               │
                                              │    [not done]  │
                                              └── increment_attempt
                                                        │
                                                   [done] │
                                                        ▼
                                                   db_insert ──► emit_event ──► respond_success
```

### Key Configuration

- **Authentication:** Header `X-INGEST-KEY` matched against `$env.INGEST_TOKEN`
- **Polling:** Max 20 attempts x 3s = 60s timeout
- **Dedup:** SHA256 checksum with `ON CONFLICT DO NOTHING`
- **Credentials:** PostgreSQL (`reachy_local`), Media Mover Auth (HTTP Header)

---

## Agent 2 -- Labeling Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
**Purpose:** Processes human label submissions. Validates labels, records label events, routes to appropriate action (label-only, promote to train/test, or discard), and reports class balance.
**Tutorial:** [MODULE_02_LABELING_AGENT.md](MODULE_02_LABELING_AGENT.md)

### Node Inventory (9 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_label` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST label submission requests. Expects JSON body with `video_id`, `label`, `action`, and optional `rater_id`. |
| 2 | `validate_payload` | **Code** (`n8n-nodes-base.code`) | Validates that `label` is one of the allowed 3-class values (`happy`, `sad`, `neutral`). Validates `action` is one of: `label_only`, `promote_train`, `promote_test`, `discard`. Returns HTTP 400 on validation failure. |
| 3 | `db_fetch_video` | **Postgres** (`n8n-nodes-base.postgres`) | Retrieves the current video record by `video_id` to verify it exists and check current split/label state. |
| 4 | `db_apply_label` | **Postgres** (`n8n-nodes-base.postgres`) | Executes a CTE (Common Table Expression) that atomically: (1) inserts a `label_event` record, and (2) updates the `video.label` field. Idempotent via `ON CONFLICT (idempotency_key) DO NOTHING`. |
| 5 | `branch_action` | **Switch** (`n8n-nodes-base.switch`) | Routes to different paths based on the `action` field: `label_only` (skip promotion), `promote_train` (move to train split), `promote_test` (move to test split), `discard` (mark for removal). |
| 6 | `mm_relabel` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Media Mover relabel endpoint to rename the file into the correct label directory structure. Used for `label_only` action. |
| 7 | `mm_promote` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Media Mover promote endpoint to move the file from temp to `train/<label>` or `test/<label>`. Used for `promote_train` and `promote_test` actions. |
| 8 | `db_class_balance` | **Postgres** (`n8n-nodes-base.postgres`) | Queries class balance across the 3 emotion classes: counts of happy, sad, and neutral in the training split. Reports balance ratio and whether `max - min <= 10` threshold is met. |
| 9 | `respond_success` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 200 JSON with label confirmation and current class balance statistics. |

### Data Flow

```
webhook_label ──► validate_payload ──► db_fetch_video ──► db_apply_label ──► branch_action
                                                                                  │
                                              ┌──────────────┬──────────────┬─────┘
                                              ▼              ▼              ▼
                                        [label_only]   [promote_train]  [promote_test]
                                              │         [promote_test]
                                              ▼              ▼
                                         mm_relabel     mm_promote
                                              │              │
                                              └──────┬───────┘
                                                     ▼
                                              db_class_balance ──► respond_success
```

### Key Configuration

- **Allowed Labels:** `happy`, `sad`, `neutral` (3-class only -- 6-class labels are deprecated since Feb 2026)
- **Allowed Actions:** `label_only`, `promote_train`, `promote_test`, `discard`
- **Balance Threshold:** `max(class_count) - min(class_count) <= 10`
- **Idempotency:** CTE with `ON CONFLICT (idempotency_key) DO NOTHING`
- **Credentials:** PostgreSQL (`reachy_local`), Media Mover Auth (HTTP Header)

> **IMPORTANT UPDATE (Feb 2026):** The labeling agent now enforces strict 3-class
> labels. The original 6-class labels (`angry`, `surprise`, `fearful`, `neutral`,
> `happy`, `sad`) were migrated to 3 classes via database migration
> `20260214_000001_emotion_3class_migration.py`.

---

## Agent 3 -- Promotion/Curation Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`
**Purpose:** Implements a two-phase approval pattern for promoting videos between dataset splits. Supports dry-run preview, human-in-the-loop approval, and manifest rebuilding.
**Tutorial:** [MODULE_03_PROMOTION_AGENT.md](MODULE_03_PROMOTION_AGENT.md)

### Node Inventory (11 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_promotion` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST promotion requests with `video_id`, `label`, and `target` (train/test) fields. |
| 2 | `validate_request` | **Code** (`n8n-nodes-base.code`) | Validates required fields (`video_id`, `label`, `target`). Generates a stable SHA256-based `idempotency_key` from `video_id + label + target` to prevent duplicate promotions. |
| 3 | `http_dryrun` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway promotion endpoint with `dry_run=true`. Returns a preview of what the promotion would do without making any changes. Includes from_split, to_split, file operations. |
| 4 | `summarize_plan` | **Code** (`n8n-nodes-base.code`) | Formats the dry-run results into a human-readable summary showing: source file, destination path, label, and estimated disk usage. |
| 5 | `webhook_approval` | **Webhook** (`n8n-nodes-base.webhook`) | Second webhook that blocks execution until a human approves or rejects the promotion. Expects POST with `{approved: true/false}`. This creates a human-in-the-loop gate. |
| 6 | `if_approved` | **IF** (`n8n-nodes-base.if`) | Evaluates `approved === true`. Routes to `http_real_promote` on approval, or `respond_rejected` on rejection. |
| 7 | `http_real_promote` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway promotion endpoint with `dry_run=false`. Executes the actual file move and database update. Uses the same idempotency key as the dry-run. |
| 8 | `http_rebuild_manifest` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway manifest rebuild endpoint (`/api/v1/ingest/manifest/rebuild`). Regenerates JSONL manifest files for train and test splits after promotion. |
| 9 | `emit_completed` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway events endpoint to emit a `promotion.completed` event with video_id, label, and target split. |
| 10 | `respond_success` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 200 JSON response confirming successful promotion with details. |
| 11 | `respond_rejected` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 403 Forbidden response when the promotion is rejected by the human approver. |

### Data Flow

```
webhook_promotion ──► validate_request ──► http_dryrun ──► summarize_plan
                                                                │
                                                                ▼
                                                        webhook_approval ──► if_approved
                                                                                │
                                                        ┌───────────────────────┤
                                                        ▼                       ▼
                                                  [approved]              [rejected]
                                                        │                       │
                                                        ▼                       ▼
                                                http_real_promote       respond_rejected
                                                        │
                                                        ▼
                                              http_rebuild_manifest
                                                        │
                                                        ▼
                                                  emit_completed ──► respond_success
```

### Key Configuration

- **Two-Phase Pattern:** Dry-run first, then human approval, then execute
- **Idempotency:** SHA256 of `video_id + label + target` prevents duplicate operations
- **Manifest Format:** JSONL (line-delimited JSON) -- `{"path": "...", "label": "..."}`
- **Credentials:** Media Mover Auth (HTTP Header)

> **NOTE:** The legacy `/api/v1/promote/stage` endpoint is deprecated. Use
> `/api/v1/media/promote` with `dest_split='train'` instead. The deprecated
> endpoint returns a `Warning: 299` header.

---

## Agent 4 -- Reconciler/Audit Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`
**Purpose:** Detects drift between the filesystem and database. Runs on a daily schedule or manually. Scans all video files via SSH, compares against PostgreSQL records, and emails a discrepancy report.
**Tutorial:** [MODULE_04_RECONCILER_AGENT.md](MODULE_04_RECONCILER_AGENT.md)

### Node Inventory (9 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `schedule_trigger` | **Schedule Trigger** (`n8n-nodes-base.scheduleTrigger`) | Fires daily at 02:15 UTC using cron expression `15 2 * * *`. Initiates the reconciliation scan. |
| 2 | `webhook_manual` | **Webhook** (`n8n-nodes-base.webhook`) | Manual trigger endpoint for on-demand reconciliation. Allows operators to run the audit outside the schedule. |
| 3 | `set_config` | **Set** (`n8n-nodes-base.set`) | Configures runtime parameters: `root_dir=/videos` (scan root) and `safe_fix=false` (read-only mode). Set `safe_fix=true` to enable auto-repair. |
| 4 | `ssh_scan_fs` | **SSH** (`n8n-nodes-base.ssh`) | Executes a `find` command on Ubuntu 1 to locate all `.mp4` files under `/videos/`. Outputs JSONL with `{path, size, mtime, split_dir}` for each file. |
| 5 | `parse_fs_scan` | **Code** (`n8n-nodes-base.code`) | Parses the JSONL output from the SSH scan into n8n items. Extracts the split directory (temp/train/test) from the file path. |
| 6 | `db_fetch_all` | **Postgres** (`n8n-nodes-base.postgres`) | Fetches all video records from the `video` table (excluding `split='purged'`). Returns `video_id`, `file_path`, `split`, `size_bytes`. |
| 7 | `diff_fs_db` | **Code** (`n8n-nodes-base.code`) | Compares filesystem items against database records. Categorizes discrepancies into: **orphans** (file exists on disk but not in DB), **missing** (DB record exists but file not on disk), **mismatches** (split or size differs). |
| 8 | `if_drift_found` | **IF** (`n8n-nodes-base.if`) | Evaluates whether any discrepancies were found (`orphans.length + missing.length + mismatches.length > 0`). Skips the email if no drift exists. |
| 9 | `email_report` | **Send Email** (`n8n-nodes-base.emailSend`) | Sends a reconciliation report email to `rustybee255@gmail.com` with a summary of orphans, missing files, and mismatches. Includes timestamps and recommended actions. |

### Data Flow

```
schedule_trigger ──┐
                   ├──► set_config ──► ssh_scan_fs ──► parse_fs_scan ──┐
webhook_manual ────┘                                                    │
                                       db_fetch_all ───────────────────┤
                                                                       ▼
                                                                  diff_fs_db
                                                                       │
                                                                       ▼
                                                                 if_drift_found
                                                                       │
                                                              [drift found]
                                                                       │
                                                                       ▼
                                                                 email_report
```

### Key Configuration

- **Schedule:** Daily at 02:15 UTC (`15 2 * * *`)
- **Scan Root:** `/videos/` on Ubuntu 1
- **Safe Fix Mode:** `false` by default (read-only). Set to `true` for auto-repair.
- **Parallel Execution:** `ssh_scan_fs` and `db_fetch_all` run concurrently using `$('NodeName').all()` pattern
- **Credentials:** SSH Ubuntu1 (`ssh_ubuntu1`), PostgreSQL (`reachy_local`), SMTP

---

## Agent 5 -- Training Orchestrator (EfficientNet-B0)

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`
**Purpose:** Launches and monitors EfficientNet-B0 training runs. Validates dataset balance, creates MLflow experiments, polls training status, and enforces Gate A quality thresholds.
**Tutorial:** [MODULE_06_TRAINING_ORCHESTRATOR.md](MODULE_06_TRAINING_ORCHESTRATOR.md)

### Node Inventory (15 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_training` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST `training.start` requests. Expects `{model, config_path, auto_deploy}`. |
| 2 | `db_check_balance` | **Postgres** (`n8n-nodes-base.postgres`) | Queries training set balance across 3 classes: `SELECT label, COUNT(*) FROM video WHERE split='train' GROUP BY label`. Validates `min(happy, sad, neutral) >= 50`. |
| 3 | `if_sufficient_data` | **IF** (`n8n-nodes-base.if`) | Checks whether minimum data threshold is met (50 samples per class for training). Routes to `emit_insufficient` if data is inadequate. |
| 4 | `mlflow_create_run` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to MLflow API (`/api/2.0/mlflow/runs/create`) to create a new experiment run. Tags with `model=efficientnet-b0-hsemotion`, `experiment=reachy_emotion`. Returns `run_id`. |
| 5 | `prepare_training` | **Code** (`n8n-nodes-base.code`) | Generates the training configuration: run_id, config path (`trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`), output directory, model storage path (`/media/rusty_admin/project_data/ml_models/efficientnet`). |
| 6 | `ssh_start_training` | **SSH** (`n8n-nodes-base.ssh`) | Launches training on Ubuntu 1 via SSH: `nohup python trainer/run_efficientnet_pipeline.py --config <config_path> --run-id <run_id> --gateway-base <gateway_url> &`. Uses `nohup` for long-running process survival. |
| 7 | `wait_poll` | **Wait** (`n8n-nodes-base.wait`) | Pauses for 5 minutes before polling training status. Part of the polling loop for the long-running training process. |
| 8 | `check_status` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET to Gateway API (`/api/training/status/{{run_id}}`) to check training progress. Returns `{status, metrics, error_message}`. |
| 9 | `parse_results` | **Code** (`n8n-nodes-base.code`) | Parses the training status response. Extracts metrics (`f1_macro`, `balanced_accuracy`, `ece`, `brier`), checks for completion or failure, and prepares Gate A validation data. |
| 10 | `if_done` | **IF** (`n8n-nodes-base.if`) | Checks if training status is `completed` or `failed`. If still running, loops back to `wait_poll`. |
| 11 | `gate_a_check` | **IF** (`n8n-nodes-base.if`) | Validates Gate A quality thresholds: `f1_macro >= 0.84 AND balanced_accuracy >= 0.85 AND ece <= 0.08 AND brier <= 0.16`. |
| 12 | `mlflow_log_gate` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to MLflow API to log `gate_a_passed=true` metric for the current run. |
| 13 | `emit_completed` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `training.completed` event with run_id, metrics, and gate_a_passed status. |
| 14 | `emit_gate_failed` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `training.gate_failed` event when Gate A thresholds are not met. Includes the failing metrics for diagnosis. |
| 15 | `emit_insufficient` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `training.insufficient_data` event when fewer than 50 samples per class exist in the training set. |

### Data Flow

```
webhook_training ──► db_check_balance ──► if_sufficient_data
                                                │
                              [insufficient]    │   [sufficient]
                                   │            │
                                   ▼            ▼
                           emit_insufficient   mlflow_create_run ──► prepare_training
                                                                          │
                                                                          ▼
                                                                 ssh_start_training
                                                                          │
                                               ┌──────────────────────────┘
                                               ▼
                                          wait_poll ──► check_status ──► parse_results ──► if_done
                                               ▲                                              │
                                               │              [still running]                  │
                                               └──────────────────────────────────────────────┘
                                                              [completed]                      │
                                                                                               ▼
                                                                                         gate_a_check
                                                                                               │
                                                                         ┌─────────────────────┤
                                                                         ▼                     ▼
                                                                   [gate passed]          [gate failed]
                                                                         │                     │
                                                                         ▼                     ▼
                                                                 mlflow_log_gate       emit_gate_failed
                                                                         │
                                                                         ▼
                                                                   emit_completed
```

### Key Configuration

- **Model:** EfficientNet-B0 (HSEmotion pre-trained on VGGFace2 + AffectNet)
- **Config:** `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`
- **Min Data:** 50 samples per class (happy, sad, neutral) in training set
- **Gate A Thresholds:**
  - Macro F1 >= 0.84
  - Balanced Accuracy >= 0.85
  - ECE (Expected Calibration Error) <= 0.08
  - Brier Score <= 0.16
- **Polling:** 5-minute intervals
- **Credentials:** SSH Ubuntu1 (`ssh_ubuntu1`), PostgreSQL (`reachy_local`)

> **CODEBASE UPDATE:** The training pipeline now uses
> `trainer/run_efficientnet_pipeline.py` which reports status to the Gateway via
> `POST /api/training/status/{run_id}`. The n8n workflow can poll this endpoint
> instead of reading `results.json` via SSH (though both patterns are supported).

---

## Agent 6 -- Evaluation Agent (EfficientNet-B0)

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`
**Purpose:** Evaluates a trained EfficientNet-B0 model on the test dataset. Validates test set balance, runs inference, computes calibration metrics (ECE, Brier), logs to MLflow, and enforces Gate A.
**Tutorial:** [MODULE_07_EVALUATION_AGENT.md](MODULE_07_EVALUATION_AGENT.md)

### Node Inventory (13 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_eval` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST `evaluation.start` requests. Expects `{run_id, checkpoint_path, model}`. |
| 2 | `db_check_balance` | **Postgres** (`n8n-nodes-base.postgres`) | Queries test set balance: `SELECT label, COUNT(*) FROM video WHERE split='test' GROUP BY label`. Validates `min(happy, sad, neutral) >= 20`. |
| 3 | `if_balanced` | **IF** (`n8n-nodes-base.if`) | Checks whether minimum test data threshold is met (20 samples per class). Routes to blocked status path if insufficient. |
| 4 | `prepare_eval` | **Code** (`n8n-nodes-base.code`) | Configures the evaluation run: sets checkpoint path, output directory, and `--skip-train` flag to run evaluation only (no training). |
| 5 | `ssh_run_eval` | **SSH** (`n8n-nodes-base.ssh`) | Executes evaluation on Ubuntu 1: `python trainer/run_efficientnet_pipeline.py --skip-train --checkpoint <path> --run-id <run_id>`. Runs the model against the test dataset. |
| 6 | `parse_results` | **Code** (`n8n-nodes-base.code`) | Parses evaluation output. Extracts 5 key metrics: `f1_macro`, `balanced_accuracy`, `ece`, `brier`, `accuracy`. Validates all Gate A thresholds. |
| 7 | `mlflow_log` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to MLflow batch logging API (`/api/2.0/mlflow/runs/log-batch`). Logs 5 metrics: `eval_f1_macro`, `eval_accuracy`, `eval_ece`, `eval_brier`, `eval_balanced_accuracy`. |
| 8 | `gate_a_check` | **IF** (`n8n-nodes-base.if`) | Validates Gate A thresholds (same as training): `f1_macro >= 0.84 AND balanced_accuracy >= 0.85 AND ece <= 0.08 AND brier <= 0.16`. |
| 9 | `emit_completed` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `evaluation.completed` event with run_id, all metrics, and gate_a_passed status. |
| 10 | `emit_gate_failed` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `evaluation.gate_failed` event with failing metric details. |
| 11 | `prepare_blocked_status` | **Code** (`n8n-nodes-base.code`) | Prepares a detailed blocked status payload when the test set has insufficient data. Includes per-class counts and minimum requirements. |
| 12 | `emit_blocked_status` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `evaluation.blocked` status with detailed metrics about why the evaluation cannot proceed. |
| 13 | `respond_blocked` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 422 response when test set balance requirements are not met. |

### Data Flow

```
webhook_eval ──► db_check_balance ──► if_balanced
                                           │
                         [unbalanced]       │        [balanced]
                              │             │
                              ▼             ▼
                   prepare_blocked_status  prepare_eval ──► ssh_run_eval ──► parse_results
                              │                                                    │
                              ▼                                                    ▼
                    emit_blocked_status                                     mlflow_log ──► gate_a_check
                              │                                                                │
                              ▼                                           ┌────────────────────┤
                       respond_blocked                                    ▼                    ▼
                                                                   [gate passed]         [gate failed]
                                                                         │                    │
                                                                         ▼                    ▼
                                                                  emit_completed       emit_gate_failed
```

### Key Configuration

- **Model:** EfficientNet-B0 with `--skip-train` flag
- **Min Test Data:** 20 samples per class (happy, sad, neutral)
- **Gate A Thresholds:** Same as Agent 5
- **Metrics Logged to MLflow:** `eval_f1_macro`, `eval_accuracy`, `eval_ece`, `eval_brier`, `eval_balanced_accuracy`
- **Credentials:** SSH Ubuntu1, PostgreSQL (`reachy_local`)

> **CODEBASE UPDATE:** The evaluation agent now supports a blocked status path
> (`prepare_blocked_status` + `emit_blocked_status`) that was added in the v.2
> workflow. This provides the Gateway with detailed information about why an
> evaluation was blocked, improving observability.

---

## Agent 7 -- Deployment Agent (EfficientNet-B0)

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`
**Purpose:** Deploys a trained and evaluated EfficientNet-B0 model to the Jetson Xavier NX. Handles ONNX transfer, TensorRT conversion, DeepStream configuration, and Gate B runtime validation with automatic rollback.
**Tutorial:** [MODULE_08_DEPLOYMENT_AGENT.md](MODULE_08_DEPLOYMENT_AGENT.md)

### Node Inventory (14 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_deploy` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST `deployment.start` requests. Expects `{run_id, checkpoint_path, gate_a_passed, target_stage}`. |
| 2 | `if_gate_passed` | **IF** (`n8n-nodes-base.if`) | Validates that Gate A was passed (`gate_a_passed === true`). Blocks deployment if the model did not pass quality gates. |
| 3 | `prepare_deploy` | **Code** (`n8n-nodes-base.code`) | Configures deployment paths: ONNX source path on Ubuntu 1, engine destination on Jetson (`/opt/reachy/models/emotion_classifier.engine`), backup path for rollback. |
| 4 | `scp_onnx` | **SSH** (`n8n-nodes-base.ssh`) | Transfers the ONNX model from Ubuntu 1 to Jetson via SCP: `scp /path/to/model.onnx jetson@10.0.4.150:/tmp/emotion_classifier.onnx`. |
| 5 | `ssh_convert_trt` | **SSH** (`n8n-nodes-base.ssh`) | Converts ONNX to TensorRT engine on Jetson: `trtexec --onnx=/tmp/emotion_classifier.onnx --saveEngine=/opt/reachy/models/emotion_classifier.engine --fp16 --minShapes=input:1x3x224x224 --optShapes=input:4x3x224x224 --maxShapes=input:8x3x224x224`. |
| 6 | `ssh_update_config` | **SSH** (`n8n-nodes-base.ssh`) | Updates DeepStream configuration on Jetson using `sed` to point to the new engine file. Restarts the emotion inference service: `systemctl restart reachy-emotion`. |
| 7 | `wait_startup` | **Wait** (`n8n-nodes-base.wait`) | Pauses for 30 seconds to allow the DeepStream service to fully start and stabilize before running verification. |
| 8 | `ssh_verify` | **SSH** (`n8n-nodes-base.ssh`) | Checks service status (`systemctl is-active reachy-emotion`) and reads runtime metrics from `emotion_metrics.json` (fps, latency_p50_ms, latency_p95_ms, gpu_memory_mb). |
| 9 | `parse_verify` | **Code** (`n8n-nodes-base.code`) | Parses the verification output. Validates Gate B requirements: service is active, FPS >= 25, latency P50 <= 120ms. Determines pass/fail status. |
| 10 | `if_gate_b` | **IF** (`n8n-nodes-base.if`) | Evaluates Gate B results. Routes to `emit_success` on pass, or `ssh_rollback` on failure. |
| 11 | `emit_success` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `deployment.completed` event with run_id, engine path, and Gate B metrics. |
| 12 | `ssh_rollback` | **SSH** (`n8n-nodes-base.ssh`) | Restores the backup engine: copies the previous `.engine.bak` file back and restarts the service. Ensures the robot remains operational. |
| 13 | `emit_rollback` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `deployment.rollback` event with the failing Gate B metrics for diagnosis. |
| 14 | `respond_failed` | **Respond to Webhook** (`n8n-nodes-base.respondToWebhook`) | Returns HTTP 412 Precondition Failed when Gate A was not passed. |

### Data Flow

```
webhook_deploy ──► if_gate_passed
                        │
        [gate not passed]│          [gate passed]
               │         │
               ▼         ▼
        respond_failed  prepare_deploy ──► scp_onnx ──► ssh_convert_trt ──► ssh_update_config
                                                                                    │
                                                                                    ▼
                                                                              wait_startup
                                                                                    │
                                                                                    ▼
                                                                              ssh_verify ──► parse_verify ──► if_gate_b
                                                                                                                 │
                                                                                         ┌───────────────────────┤
                                                                                         ▼                       ▼
                                                                                   [Gate B pass]           [Gate B fail]
                                                                                         │                       │
                                                                                         ▼                       ▼
                                                                                    emit_success           ssh_rollback
                                                                                                                 │
                                                                                                                 ▼
                                                                                                           emit_rollback
```

### Key Configuration

- **Target:** Jetson Xavier NX at `10.0.4.150`
- **TensorRT:** FP16 precision, dynamic batch 1-8
- **Input Shape:** `input:Nx3x224x224` (EfficientNet-B0)
- **Gate B Thresholds:**
  - Service must be active
  - FPS >= 25
  - Latency P50 <= 120ms
  - GPU Memory <= 2.5GB (optional)
- **Rollback:** Automatic on Gate B failure -- restores `.engine.bak`
- **Deployment Stages:** Shadow, Canary, Rollout (canary/rollout TBD)
- **Credentials:** SSH Ubuntu1, SSH Jetson (`ssh_jetson`)

---

## Agent 8 -- Privacy/Retention Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/08_privacy_agent.json`
**Purpose:** Enforces data retention policies. Automatically purges temporary videos older than 14 days. Supports GDPR deletion requests. Maintains a full audit trail.
**Tutorial:** [MODULE_05_PRIVACY_AGENT.md](MODULE_05_PRIVACY_AGENT.md)

### Node Inventory (8 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `schedule_daily` | **Schedule Trigger** (`n8n-nodes-base.scheduleTrigger`) | Fires daily at 03:00 UTC. Initiates the retention sweep for expired temporary videos. |
| 2 | `webhook_gdpr` | **Webhook** (`n8n-nodes-base.webhook`) | Manual GDPR deletion trigger. Accepts POST with `{video_id}` to purge a specific video on demand regardless of age. |
| 3 | `db_find_old` | **Postgres** (`n8n-nodes-base.postgres`) | Queries for temp-split videos older than 14 days: `SELECT * FROM video WHERE split='temp' AND created_at < NOW() - INTERVAL '14 days'`. |
| 4 | `split_batches` | **Split In Batches** (`n8n-nodes-base.splitInBatches`) | Processes deletions in batches of 50 items to prevent resource exhaustion. The loop processes each batch sequentially. |
| 5 | `ssh_delete_file` | **SSH** (`n8n-nodes-base.ssh`) | Removes the video file from disk: `rm -f /videos/{{$json.file_path}}`. Executes on Ubuntu 1 where videos are stored. |
| 6 | `db_mark_purged` | **Postgres** (`n8n-nodes-base.postgres`) | Updates the video record: `UPDATE video SET split='purged', deleted_at=NOW() WHERE video_id='...'`. Soft delete preserves metadata while marking as purged. |
| 7 | `db_audit_log` | **Postgres** (`n8n-nodes-base.postgres`) | Inserts an audit trail record: `INSERT INTO audit_log (action, entity_type, entity_id, details, created_at)`. Ensures GDPR compliance with deletion records. |
| 8 | `emit_purged` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `privacy.purged` event with count of purged videos and batch details. |

### Data Flow

```
schedule_daily ──┐
                 ├──► db_find_old ──► split_batches
webhook_gdpr ────┘                        │
                                          ▼
                                    ┌─── Loop ───┐
                                    │             │
                                    ▼             │
                              ssh_delete_file     │
                                    │             │
                                    ▼             │
                              db_mark_purged      │
                                    │             │
                                    ▼             │
                               db_audit_log       │
                                    │             │
                                    └─────────────┘
                                          │
                                     [loop done]
                                          │
                                          ▼
                                     emit_purged
```

### Key Configuration

- **Schedule:** Daily at 03:00 UTC
- **Retention Policy:**
  - `temp` split: 14 days auto-purge
  - `train`/`test` splits: Indefinite (never auto-purged)
- **Batch Size:** 50 items per batch
- **Soft Delete:** File removed from disk, but metadata retained with `split='purged'`
- **Audit Trail:** Every deletion is logged in `audit_log` table
- **GDPR:** Manual webhook for targeted deletions
- **Credentials:** SSH Ubuntu1, PostgreSQL (`reachy_local`)

---

## Agent 9 -- Observability/Telemetry Agent

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/09_observability_agent.json`
**Purpose:** Collects Prometheus-format metrics from all three infrastructure nodes (n8n, Media Mover, Gateway) every 30 seconds and stores them in PostgreSQL for dashboarding and alerting.
**Tutorial:** [MODULE_09_OBSERVABILITY_AGENT.md](MODULE_09_OBSERVABILITY_AGENT.md)

### Node Inventory (6 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `cron_metrics` | **Cron** (`n8n-nodes-base.cron`) | Fires every 30 seconds. High-frequency trigger for near-real-time metrics collection. |
| 2 | `fetch_n8n_metrics` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET `http://n8n:5678/metrics` -- fetches Prometheus-format metrics from the n8n instance. Collects `n8n_active_executions`, `n8n_workflow_executions_total`. |
| 3 | `fetch_mm_metrics` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET `http://10.0.4.130:9101/metrics` -- fetches Prometheus-format metrics from Media Mover. Collects `media_mover_promote_total`, `media_mover_ingest_total`. |
| 4 | `fetch_gw_metrics` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET `http://10.0.4.140:9100/metrics` -- fetches Prometheus-format metrics from Gateway. Collects `gateway_queue_depth`, `gateway_request_duration_seconds`. |
| 5 | `parse_metrics` | **Code** (`n8n-nodes-base.code`) | Parses the three Prometheus text responses using regex. Extracts key metrics: `n8n_active_executions`, `media_mover_promote_total`, `gateway_queue_depth`. Converts to structured JSON items. |
| 6 | `db_store_metrics` | **Postgres** (`n8n-nodes-base.postgres`) | Inserts metric samples into the `obs_samples` table: `INSERT INTO obs_samples (ts, src, metric, value)`. Stores timestamped data for time-series queries. |

### Data Flow

```
cron_metrics ──┬──► fetch_n8n_metrics ──┐
               │                         │
               ├──► fetch_mm_metrics  ───┤──► parse_metrics ──► db_store_metrics
               │                         │
               └──► fetch_gw_metrics ───┘
```

### Key Configuration

- **Frequency:** Every 30 seconds
- **Sources (parallel HTTP):**
  - n8n: `http://n8n:5678/metrics`
  - Media Mover: `http://10.0.4.130:9101/metrics`
  - Gateway: `http://10.0.4.140:9100/metrics`
- **Storage:** `obs_samples` table with columns `(sample_id, ts, src, metric, value)`
- **SLOs (Service Level Objectives):**
  - Planner Actions P50 <= 2s
  - Planner Actions P95 <= 5s
  - Error Budget < 1% weekly
- **Parallel Execution:** All three HTTP requests fire concurrently
- **Credentials:** PostgreSQL (`reachy_local`)

---

## ML Pipeline Orchestrator

**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`
**Purpose:** Coordinates the entire ML pipeline end-to-end. Validates dataset readiness, triggers training (Agent 5), evaluation (Agent 6), and deployment (Agent 7) in sequence. Supports auto-deploy mode.
**Tutorial:** [MODULE_10_ML_PIPELINE_ORCHESTRATOR.md](MODULE_10_ML_PIPELINE_ORCHESTRATOR.md)

### Node Inventory (15 nodes)

| # | Node Name | n8n Node Type | Function |
|---|-----------|---------------|----------|
| 1 | `webhook_start` | **Webhook** (`n8n-nodes-base.webhook`) | Receives POST `pipeline.start` requests. Expects `{model, config_path, auto_deploy}`. |
| 2 | `init_pipeline` | **Code** (`n8n-nodes-base.code`) | Generates a unique `pipeline_id`. Sets model (`efficientnet-b0-hsemotion`), config path, pipeline stages, and auto_deploy flag. |
| 3 | `db_dataset_stats` | **Postgres** (`n8n-nodes-base.postgres`) | Queries comprehensive dataset statistics: counts per class (happy, sad, neutral) for both train and test splits. |
| 4 | `check_dataset` | **Code** (`n8n-nodes-base.code`) | Validates dataset readiness: `min(train_happy, train_sad, train_neutral) >= 50` and `min(test_happy, test_sad, test_neutral) >= 20`. Also checks class imbalance ratio (`< 20%`). |
| 5 | `if_dataset_ready` | **IF** (`n8n-nodes-base.if`) | Routes based on dataset readiness. If insufficient, emits blocked event. |
| 6 | `trigger_training` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Agent 5's webhook to start the training orchestrator. Passes model, config_path, and run metadata. |
| 7 | `wait_training` | **Wait** (`n8n-nodes-base.wait`) | Pauses for 10 minutes to allow training to complete before polling status. |
| 8 | `check_training` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | GET to Gateway to poll training status. Checks for `completed`, `failed`, or `gate_failed` status. |
| 9 | `if_training_done` | **IF** (`n8n-nodes-base.if`) | Evaluates training completion. Loops back to `wait_training` if still running. Proceeds to evaluation if completed. |
| 10 | `trigger_evaluation` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Agent 6's webhook to start the evaluation agent. Passes run_id and checkpoint path from training output. |
| 11 | `wait_evaluation` | **Wait** (`n8n-nodes-base.wait`) | Pauses for 5 minutes to allow evaluation to complete. |
| 12 | `if_auto_deploy` | **IF** (`n8n-nodes-base.if`) | Checks both conditions: `auto_deploy === true AND gate_a_passed === true`. Only proceeds to deployment if both are met. |
| 13 | `trigger_deployment` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Agent 7's webhook to start deployment. Passes run_id, checkpoint path, and gate_a_passed status. |
| 14 | `emit_complete` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `pipeline.completed` event with pipeline_id, total duration, and stage results. |
| 15 | `emit_blocked` | **HTTP Request** (`n8n-nodes-base.httpRequest`) | POST to Gateway to emit `pipeline.blocked` event when dataset requirements are not met. |

### Data Flow

```
webhook_start ──► init_pipeline ──► db_dataset_stats ──► check_dataset ──► if_dataset_ready
                                                                                │
                                                          [not ready]           │    [ready]
                                                               │                │
                                                               ▼                ▼
                                                         emit_blocked     trigger_training
                                                                                │
                                                                                ▼
                                                                          wait_training
                                                                                │
                                                              ┌─────────────────┘
                                                              ▼
                                                         check_training ──► if_training_done
                                                              ▲                     │
                                                              │    [still running]  │
                                                              └─────────────────────┘
                                                                   [done]           │
                                                                                    ▼
                                                                          trigger_evaluation
                                                                                    │
                                                                                    ▼
                                                                            wait_evaluation
                                                                                    │
                                                                                    ▼
                                                                            if_auto_deploy
                                                                                    │
                                                                  ┌─────────────────┤
                                                                  ▼                 ▼
                                                           [auto deploy]      [manual/gate fail]
                                                                  │                 │
                                                                  ▼                 │
                                                         trigger_deployment         │
                                                                  │                 │
                                                                  └────────┬────────┘
                                                                           ▼
                                                                     emit_complete
```

### Key Configuration

- **Pipeline Stages:** `dataset_check` -> `training` -> `evaluation` -> `deployment`
- **Dataset Requirements:**
  - Training: >= 50 samples per class (happy, sad, neutral)
  - Test: >= 20 samples per class
  - Class imbalance: < 20%
- **Auto-Deploy:** Optional flag. When enabled and Gate A passes, deployment is triggered automatically.
- **Polling Intervals:** Training 10 min, Evaluation 5 min
- **Credentials:** PostgreSQL (`reachy_local`)

---

## Node Type Summary

Summary of all n8n node types used across the nine agents and orchestrator:

| Node Type | n8n Internal Type | Count | Used In Agents |
|-----------|-------------------|-------|----------------|
| **Webhook** | `n8n-nodes-base.webhook` | 13 | All agents |
| **HTTP Request** | `n8n-nodes-base.httpRequest` | 22 | 1, 2, 3, 5, 6, 7, 9, 10 |
| **Code** (JavaScript) | `n8n-nodes-base.code` | 15 | 1, 2, 3, 4, 5, 6, 7, 9, 10 |
| **Postgres** | `n8n-nodes-base.postgres` | 14 | 1, 2, 4, 5, 6, 8, 9, 10 |
| **IF** | `n8n-nodes-base.if` | 13 | 1, 3, 4, 5, 6, 7, 10 |
| **SSH** | `n8n-nodes-base.ssh` | 10 | 4, 5, 6, 7, 8 |
| **Wait** | `n8n-nodes-base.wait` | 5 | 1, 5, 7, 10 |
| **Respond to Webhook** | `n8n-nodes-base.respondToWebhook` | 7 | 1, 2, 3, 6, 7 |
| **Schedule Trigger** | `n8n-nodes-base.scheduleTrigger` | 2 | 4, 8 |
| **Switch** | `n8n-nodes-base.switch` | 1 | 2 |
| **Set** | `n8n-nodes-base.set` | 1 | 4 |
| **Split In Batches** | `n8n-nodes-base.splitInBatches` | 1 | 8 |
| **Send Email** | `n8n-nodes-base.emailSend` | 1 | 4 |
| **Cron** | `n8n-nodes-base.cron` | 1 | 9 |

### Total Nodes Per Agent

| Agent | Name | Nodes |
|-------|------|-------|
| Agent 1 | Ingest Agent | 12 |
| Agent 2 | Labeling Agent | 9 |
| Agent 3 | Promotion/Curation Agent | 11 |
| Agent 4 | Reconciler/Audit Agent | 9 |
| Agent 5 | Training Orchestrator | 15 |
| Agent 6 | Evaluation Agent | 13 |
| Agent 7 | Deployment Agent | 14 |
| Agent 8 | Privacy/Retention Agent | 8 |
| Agent 9 | Observability/Telemetry Agent | 6 |
| Orchestrator | ML Pipeline Orchestrator | 15 |
| **Total** | | **112** |

---

## Credentials Reference

| Credential Name | Type | Used By | Configuration |
|-----------------|------|---------|---------------|
| `reachy_local` | PostgreSQL | Agents 1, 2, 4, 5, 6, 8, 9, 10 | Host: `localhost:5432`, DB: `reachy_emotion`, User: `reachy_dev` |
| Media Mover Auth | HTTP Header Auth | Agents 1, 2, 3 | Header: `Authorization`, Value from env var |
| `ssh_ubuntu1` | SSH | Agents 4, 5, 6, 7, 8 | Host: `10.0.4.130`, User: `rusty_admin` |
| `ssh_jetson` | SSH | Agent 7 | Host: `10.0.4.150`, User: `jetson` |
| SMTP | Email | Agent 4 | Configured for reconciliation alerts |

---

## Environment Variables

| Variable | Value | Used By |
|----------|-------|---------|
| `INGEST_TOKEN` | `tkn3848` | Agent 1 (auth check) |
| `MEDIA_MOVER_BASE_URL` | `http://10.0.4.130:8083` | Agents 1, 2, 3 |
| `GATEWAY_BASE_URL` | `http://10.0.4.140:8000` | All agents (event emission) |
| `MLFLOW_TRACKING_URI` | `http://10.0.4.130:5000` | Agents 5, 6 |
| `REACHY_VIDEOS_ROOT` | `/mnt/videos` | Agents 4, 8 |
| `REACHY_DATABASE_URL` | `postgresql+asyncpg://reachy_dev:...@localhost:5432/reachy_emotion` | All Postgres nodes |
| `REACHY_API_PORT` | `8083` | API configuration |

---

## Architecture Patterns

### Pattern 1: Webhook Authentication
Used in Agent 1. Validates inbound requests using a shared secret header.

```
Webhook ──► IF (header matches env var)
                  │
         [fail]   │   [pass]
           │      │
           ▼      ▼
        Respond  Continue...
        401
```

### Pattern 2: Async Polling Loop
Used in Agents 1, 5, 10. Polls an external process until completion.

```
Start Process ──► Wait N seconds ──► Check Status ──► IF Done?
                        ▲                                 │
                        │              [not done]         │
                        └── Increment Attempt ────────────┘
                                                [done]    │
                                                          ▼
                                                     Continue...
```

### Pattern 3: Two-Phase Approval (Dry-Run)
Used in Agent 3. Human-in-the-loop gate with preview.

```
Dry-Run Request ──► Summarize Plan ──► Await Approval Webhook
                                              │
                                    [approved] │ [rejected]
                                         │     │
                                         ▼     ▼
                                     Execute  Respond 403
```

### Pattern 4: Quality Gate Validation
Used in Agents 5, 6, 7. Enforces metric thresholds before proceeding.

```
Parse Metrics ──► IF (all thresholds met?)
                        │
               [pass]   │   [fail]
                 │      │
                 ▼      ▼
            Continue   Emit Gate Failed / Rollback
```

### Pattern 5: Batch Processing Loop
Used in Agent 8. Processes items in configurable batch sizes.

```
Fetch Items ──► Split In Batches
                      │
                 ┌── Loop ──┐
                 │          │
                 ▼          │
           Process Item     │
                 │          │
                 └──────────┘
                      │
                 [loop done]
                      │
                      ▼
                 Continue...
```

### Pattern 6: Parallel HTTP Collection
Used in Agent 9. Fetches from multiple sources simultaneously.

```
Cron Trigger ──┬──► HTTP Source A ──┐
               │                    │
               ├──► HTTP Source B ──┤──► Code (merge & parse) ──► Store
               │                    │
               └──► HTTP Source C ──┘
```

### Pattern 7: Agent Orchestration (Workflow-to-Workflow)
Used in ML Pipeline Orchestrator. Triggers downstream agents via HTTP.

```
Orchestrator Webhook ──► Validate ──► Trigger Agent N ──► Wait ──► Poll Status ──► Trigger Agent N+1 ...
```

---

## n8n Official Documentation References

For detailed node configuration, refer to the official n8n documentation:

- [Webhook Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
- [HTTP Request Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httpRequest/)
- [Code Node](https://docs.n8n.io/code/)
- [IF Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/)
- [Switch Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.switch/)
- [Postgres Node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/)
- [SSH Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/)
- [Wait Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/)
- [Split In Batches Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitInBatches/)
- [Schedule Trigger Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduleTrigger/)
- [Send Email Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.emailSend/)
- [Node Types Overview](https://docs.n8n.io/integrations/builtin/node-types/)
- [n8n Templates](https://n8n.io/workflows/)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-07 | Created comprehensive node reference for all 9 agents + orchestrator |
| 2026-02-14 | 3-class migration: 6 emotion labels consolidated to `happy`, `sad`, `neutral` |
| 2025-11-29 | v.2 workflows: EfficientNet-B0 replaced ResNet-50/TAO |
| 2025-11-07 | Initial v.2 workflow definitions |
