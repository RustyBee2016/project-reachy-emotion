# Agent 5 — Training Orchestrator EfficientNet-B0 (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-29

## Overview

The Training Orchestrator triggers EfficientNet-B0 emotion classifier fine-tuning using AffectNet+RAF-DB pretrained weights. It checks for sufficient training data (≥50 samples per class), creates MLflow runs for experiment tracking, executes training via SSH, polls for completion, validates Gate A requirements, and emits completion events.

**Model:** `efficientnet-b0-hsemotion`  
**Storage Path:** `/media/rusty_admin/project_data/ml_models/efficientnet`

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: parse.results | n8n-nodes-base.code | parse_results |
| Code: prepare.training | n8n-nodes-base.code | prepare_training |
| HTTP: emit.completed | n8n-nodes-base.httpRequest | emit_completed |
| HTTP: emit.gate_failed | n8n-nodes-base.httpRequest | emit_gate_failed |
| HTTP: emit.insufficient_data | n8n-nodes-base.httpRequest | emit_insufficient |
| HTTP: mlflow.create_run | n8n-nodes-base.httpRequest | mlflow_create_run |
| HTTP: mlflow.log_gate | n8n-nodes-base.httpRequest | mlflow_log_gate |
| IF: Gate_A.pass? | n8n-nodes-base.if | gate_a_check |
| IF: sufficient_data? | n8n-nodes-base.if | if_sufficient_data |
| IF: training.done? | n8n-nodes-base.if | if_done |
| Postgres: check.train_balance | n8n-nodes-base.postgres | db_check_balance |
| SSH: check.status | n8n-nodes-base.ssh | check_status |
| SSH: start.training | n8n-nodes-base.ssh | ssh_start_training |
| Wait: 5min | n8n-nodes-base.wait | wait_poll |
| Webhook: training.start | n8n-nodes-base.webhook | webhook_training |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: training.start
    │
    ▼
Postgres: check.train_balance
    │
    ▼
IF: sufficient_data? (min 50/class)
    │
    ├──► [True] ──► HTTP: mlflow.create_run
    │                        │
    │                        ▼
    │               Code: prepare.training
    │                        │
    │                        ▼
    │               SSH: start.training
    │                        │
    │                        ▼
    │               Wait: 5min ◄─────────────────┐
    │                        │                   │
    │                        ▼                   │
    │               SSH: check.status            │
    │                        │                   │
    │                        ▼                   │
    │               Code: parse.results          │
    │                        │                   │
    │                        ▼                   │
    │               IF: training.done? ──────────┤ [False - still running]
    │                        │                   │
    │                        ▼ [True]            │
    │               IF: Gate_A.pass?             │
    │                        │                   │
    │                        ├──► [True] ──► HTTP: mlflow.log_gate
    │                        │                        │
    │                        │                        ▼
    │                        │               HTTP: emit.completed
    │                        │
    │                        └──► [False] ──► HTTP: emit.gate_failed
    │
    └──► [False] ──► HTTP: emit.insufficient_data
```

---

## Node Details

### 1. Webhook: training.start

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-800, 300]  
**Purpose:** Entry point for training requests.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests |
| `path` | `agent/training/efficientnet/start` | URL path |
| `responseMode` | `onReceived` | Respond immediately |
| `options.responseCode` | `202` | HTTP 202 Accepted |
| `webhookId` | `efficientnet-training-start` | Unique identifier |

#### Test Status: ✅ OPERATIONAL

---

### 2. Postgres: check.train_balance

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [-600, 300]  
**Purpose:** Checks training data balance (happy vs sad counts).

#### SQL Query

```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train
FROM video;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 3. IF: sufficient_data?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [-400, 300]  
**Purpose:** Validates minimum training data requirement (≥50 per class).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.number[0].value1` | `={{Math.min($json.happy_train, $json.sad_train)}}` | Minimum class count |
| `conditions.number[0].operation` | `largerEqual` | ≥ comparison |
| `conditions.number[0].value2` | `50` | Minimum threshold |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | min(happy, sad) ≥ 50 | HTTP: mlflow.create_run |
| False | min(happy, sad) < 50 | HTTP: emit.insufficient_data |

#### Test Status: ✅ OPERATIONAL

---

### 4. HTTP: mlflow.create_run

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-200, 200]  
**Purpose:** Creates MLflow run for experiment tracking.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create` | MLflow API |
| `sendBody` | `true` | Include request body |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `experiment_id` | `={{$env.MLFLOW_EXPERIMENT_ID}}` | MLflow experiment |
| `tags` | Array of key-value pairs | Model, dataset_hash, correlation_id |

#### Related Code

- **MLflow API:** Standard MLflow REST API
- **Environment:** `MLFLOW_URL`, `MLFLOW_EXPERIMENT_ID`

#### Test Status: ⚠️ TBD (requires MLflow server)

---

### 5. Code: prepare.training

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [0, 200]  
**Purpose:** Generates run ID and prepares training configuration.

#### JavaScript Code

```javascript
// Generate run ID and prepare training command
const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const runId = `efficientnet_b0_emotion_${timestamp}`;

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    config_path: '/workspace/trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml',
    model_placeholder: 'efficientnet-b0-hsemotion',
    model_storage_path: '/media/rusty_admin/project_data/ml_models/efficientnet'
  }
}];
```

#### Output Schema

```json
{
  "run_id": "efficientnet_b0_emotion_20251129143000",
  "config_path": "/workspace/trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml",
  "model_placeholder": "efficientnet-b0-hsemotion",
  "model_storage_path": "/media/rusty_admin/project_data/ml_models/efficientnet"
}
```

#### Related Code

**File:** `trainer/train_efficientnet.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `main()` | 1-204 | Training entry point |

**File:** `trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml`

| Purpose |
|---------|
| Training configuration (epochs, LR, batch size, etc.) |

#### Test Status: ✅ OPERATIONAL

---

### 6. SSH: start.training

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [200, 200]  
**Purpose:** Starts training process on Ubuntu 1 via SSH.

#### Command

```bash
cd /workspace && source venv/bin/activate && \
python trainer/train_efficientnet.py \
  --config {{$json.config_path}} \
  --run-id {{$json.run_id}} \
  > /workspace/experiments/{{$json.run_id}}/train.log 2>&1
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Related Code

**File:** `trainer/train_efficientnet.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `main()` | 150-204 | Argument parsing, training execution |

**File:** `trainer/fer_finetune/train.py`

| Class | Purpose |
|-------|---------|
| `Trainer` | Training loop, checkpointing, metrics |

#### Test Status: ✅ OPERATIONAL

---

### 7. Wait: 5min

**Type:** `n8n-nodes-base.wait` (v1.1)  
**Position:** [400, 200]  
**Purpose:** Polling interval between status checks.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `amount` | `5` | Wait duration |
| `unit` | `minutes` | Time unit |

#### Test Status: ✅ OPERATIONAL

---

### 8. SSH: check.status

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [600, 200]  
**Purpose:** Checks if training has completed by looking for results.json.

#### Command

```bash
test -f /workspace/experiments/{{$json.run_id}}/results.json && \
cat /workspace/experiments/{{$json.run_id}}/results.json || \
echo '{"status": "running"}'
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Test Status: ✅ OPERATIONAL

---

### 9. Code: parse.results

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [800, 200]  
**Purpose:** Parses training results from JSON output.

#### JavaScript Code

```javascript
const result = JSON.parse($json.stdout || '{}');
if (result.status === 'running') {
  return [{json: {...items[0].json, status: 'running'}}];
}

// Parse training results
return [{
  json: {
    ...items[0].json,
    status: result.status,
    best_metric: result.best_metric,
    epochs_completed: result.epochs_completed,
    gate_results: result.gate_results || {},
    export: result.export || null
  }
}];
```

#### Expected Results Schema

```json
{
  "status": "completed_gate_passed",
  "best_metric": 0.87,
  "epochs_completed": 30,
  "gate_results": {
    "gate_a": true,
    "f1_macro": 0.87,
    "balanced_accuracy": 0.88,
    "ece": 0.06
  },
  "export": {
    "onnx": "/workspace/exports/efficientnet_b0_emotion_xxx/model.onnx"
  }
}
```

#### Test Status: ✅ OPERATIONAL

---

### 10. IF: training.done?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [1000, 200]  
**Purpose:** Checks if training has completed.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.string[0].value1` | `={{$json.status}}` | Status field |
| `conditions.string[0].operation` | `contains` | Partial match |
| `conditions.string[0].value2` | `completed` | Expected value |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | status contains "completed" | IF: Gate_A.pass? |
| False | status = "running" | Wait: 5min (loop back) |

#### Test Status: ✅ OPERATIONAL

---

### 11. IF: Gate_A.pass?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [1200, 100]  
**Purpose:** Validates Gate A requirements.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.gate_results.gate_a}}` | Gate A result |
| `conditions.boolean[0].value2` | `true` | Expected pass |

#### Gate A Requirements (from requirements.md)

| Metric | Threshold |
|--------|-----------|
| F1 (macro) | ≥ 0.84 |
| Balanced Accuracy | ≥ 0.85 |
| ECE | ≤ 0.12 |
| Brier Score | ≤ 0.16 |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Gate A passed | HTTP: mlflow.log_gate |
| False | Gate A failed | HTTP: emit.gate_failed |

#### Test Status: ✅ OPERATIONAL

---

### 12. HTTP: mlflow.log_gate

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1400, 0]  
**Purpose:** Logs Gate A result to MLflow.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-metric` | MLflow API |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `run_id` | `={{$json.mlflow_run_id}}` | MLflow run |
| `key` | `gate_a_passed` | Metric name |
| `value` | `={{$json.gate_results.gate_a ? 1 : 0}}` | 1 or 0 |

#### Test Status: ⚠️ TBD (requires MLflow server)

---

### 13. HTTP: emit.completed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1600, 0]  
**Purpose:** Emits training.completed event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `training.completed` | Event type |
| `run_id` | `={{$json.run_id}}` | Training run ID |
| `model` | `efficientnet-b0-hsemotion` | Model identifier |
| `gate_a_passed` | `={{$json.gate_results.gate_a}}` | Gate result |
| `onnx_path` | `={{$json.export?.onnx \|\| ''}}` | Export path |
| `best_f1` | `={{$json.best_metric}}` | Best F1 score |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

### 14. HTTP: emit.gate_failed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1400, 200]  
**Purpose:** Emits training.gate_failed event when Gate A fails.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `training.gate_failed` | Event type |
| `run_id` | `={{$json.run_id}}` | Training run ID |
| `model` | `efficientnet-b0-hsemotion` | Model identifier |
| `best_f1` | `={{$json.best_metric}}` | Best F1 achieved |
| `message` | Gate A requirements not met | Error message |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

### 15. HTTP: emit.insufficient_data

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-200, 400]  
**Purpose:** Emits event when training data is insufficient.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `training.insufficient_data` | Event type |
| `happy_count` | `={{$json.happy_train}}` | Happy samples |
| `sad_count` | `={{$json.sad_train}}` | Sad samples |
| `message` | Need at least 50 samples per class | Error message |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `MLFLOW_URL` | MLflow tracking server | `http://10.0.4.130:5000` |
| `MLFLOW_EXPERIMENT_ID` | Experiment ID | `1` |
| `GATEWAY_BASE_URL` | Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Database |
| 3 | SSH Ubuntu1 | SSH Password | Training server |

---

## Tags

- `agent`
- `training`
- `efficientnet`
- `ml-v1`

---

## Related Code Files

| File | Purpose |
|------|---------|
| `trainer/train_efficientnet.py` | Main training script |
| `trainer/fer_finetune/train.py` | Trainer class |
| `trainer/fer_finetune/model.py` | Model architecture |
| `trainer/fer_finetune/dataset.py` | Data loading |
| `trainer/fer_finetune/evaluate.py` | Evaluation metrics |
| `trainer/fer_finetune/export.py` | ONNX export |
| `trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml` | Config |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `/api/events/training` |
| MLflow Integration | HIGH | Configure MLflow server |
| Training Status API | MEDIUM | Implement status polling endpoint |

---

## Connections Summary

```json
{
  "webhook_training": { "main": [["db_check_balance"]] },
  "db_check_balance": { "main": [["if_sufficient_data"]] },
  "if_sufficient_data": { "main": [["mlflow_create_run"], ["emit_insufficient"]] },
  "mlflow_create_run": { "main": [["prepare_training"]] },
  "prepare_training": { "main": [["ssh_start_training"]] },
  "ssh_start_training": { "main": [["wait_poll"]] },
  "wait_poll": { "main": [["check_status"]] },
  "check_status": { "main": [["parse_results"]] },
  "parse_results": { "main": [["if_done"]] },
  "if_done": { "main": [["gate_a_check"], ["wait_poll"]] },
  "gate_a_check": { "main": [["mlflow_log_gate"], ["emit_gate_failed"]] },
  "mlflow_log_gate": { "main": [["emit_completed"]] }
}
```
