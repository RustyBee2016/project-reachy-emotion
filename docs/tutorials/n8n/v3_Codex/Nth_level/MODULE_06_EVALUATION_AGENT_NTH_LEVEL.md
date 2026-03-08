# MODULE 06 — Evaluation Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/06_evaluation_agent_efficientnet.json`

## Runtime Goal
Gate evaluation by test-balance condition, run skip-train evaluation pipeline, log metrics, enforce Gate A, and publish completion/failure/blocked status.

## Node-to-Script Map

### 1) `Webhook: evaluation.start` (`Webhook`)
- **Workflow role:** evaluation run trigger.
- **Path/method:** `POST /webhook/agent/evaluation/efficientnet/start`.

### 2) `Postgres: check.test_balance` (`Postgres`)
- **Workflow role:** checks test split class counts.
- **SQL:** counts labels in `split='test'`.

### 3) `IF: test_set.balanced?` (`If`)
- **Workflow role:** pre-evaluation gate.
- **Expression:** `min(happy_test,sad_test,neutral_test) >= 20`.
- **Branches:**
- true -> run evaluation
- false -> blocked status path

### 4) `Code: prepare.evaluation` (`Code`)
- **Workflow role:** build command inputs.
- **Essential in-node logic:**
- derives run ID
- resolves checkpoint path fallback
- injects `gateway_base`, output dir, model placeholder

### 5) `SSH: run.evaluation` (`SSH`)
- **Workflow role:** runs evaluation using pipeline script in `--skip-train` mode.
- **Command target:** `python trainer/run_efficientnet_pipeline.py --skip-train ...`
- **Backend binding:** `run_efficientnet_pipeline.py:304` `main()`
- **Script-level behavior in skip-train mode:**
- `_emit_evaluation_started(...)` (`line 88`)
- loads checkpoint + validation data via `_collect_predictions(...)` (`line 195`)
- computes Gate A via `evaluate_predictions(...)` (`line 448`)
- writes artifacts (`predictions.npz`, `gate_a.json`)
- emits completion/failure status payloads to gateway training-status API
- **Post-command status fetch:** same node curls `/api/training/status/{run_id}` and `/latest`.

### 6) `Code: parse.results` (`Code`)
- **Workflow role:** parse status payload and derive gate breakdown.
- **Essential in-node logic:**
- reads `run_status.metrics` and `gate_a_gates`
- computes fallback gate booleans when explicit gates missing
- builds `gate_a` object with `passed`, `f1_macro`, `balanced_accuracy`, `ece`, `brier`

### 7) `HTTP: mlflow.log_metrics` (`HTTP Request`)
- **Workflow role:** logs evaluation metrics as MLflow batch metrics.

### 8) `IF: Gate_A.pass?` (`If`)
- **Workflow role:** pass/fail branch from parsed evaluation gate.

### 9) `HTTP: emit.completed` (`HTTP Request`)
- **Workflow role:** emits `evaluation.completed` pipeline event, including `ready_for_deployment`.
- **Backend binding:** `apps/api/routers/gateway.py:346` `post_pipeline_event(...)`.

### 10) `HTTP: emit.gate_failed` (`HTTP Request`)
- **Workflow role:** emits `evaluation.gate_failed` with gate details and serialized metrics.

### 11) `Code: prepare.blocked_status` (`Code`)
- **Workflow role:** constructs blocked payload when test-balance gate fails.
- **Fields added:** `blocked_reason`, min required per class, observed counts, `run_id`.

### 12) `HTTP: status.blocked` (`HTTP Request`)
- **Workflow role:** persists blocked status to training-status DB endpoint.
- **HTTP target:** `POST {{$json.gateway_base}}/api/training/status/{{$json.run_id}}`
- **Backend binding chain:**
- proxy in `apps/api/routers/gateway.py:377`
- persistence in `apps/api/app/routers/gateway_upstream.py:537` `update_training_status(...)`
- DB row in `TrainingRun` (`models.py:102`)

## How This Delivers Evaluation Functionality
1. Enforces minimum test-data threshold before compute-heavy evaluation.
2. Reuses end-to-end pipeline script with `--skip-train` for consistent artifacts/contract updates.
3. Converts persisted status snapshots into actionable gate decision in n8n.
4. Emits either deploy-ready completion or structured gate failure/blocked states.

## Critical Alignment Note
- DB policy (`Video` constraint `chk_video_split_label_policy`, `models.py:95`) enforces `label IS NULL` for `split='test'`.
- This workflow’s SQL gate counts labeled test rows; if policy is strictly followed, counts are zero and blocked path will dominate unless evaluation is sourced from manifest/frame metadata instead of `video.label`.
