# Agent 6 — Evaluation Agent EfficientNet-B0 (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-29

## Overview

The Evaluation Agent runs validation jobs on trained EfficientNet-B0 models. It checks for a balanced test set (≥20 samples per class), executes evaluation via SSH, computes comprehensive metrics including calibration (ECE, Brier), validates Gate A requirements, logs metrics to MLflow, and emits completion events.

**Model:** `efficientnet-b0-hsemotion`

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: parse.results | n8n-nodes-base.code | parse_results |
| Code: prepare.evaluation | n8n-nodes-base.code | prepare_eval |
| HTTP: emit.completed | n8n-nodes-base.httpRequest | emit_completed |
| HTTP: emit.gate_failed | n8n-nodes-base.httpRequest | emit_gate_failed |
| HTTP: mlflow.log_metrics | n8n-nodes-base.httpRequest | mlflow_log |
| IF: Gate_A.pass? | n8n-nodes-base.if | gate_a_check |
| IF: test_set.balanced? | n8n-nodes-base.if | if_balanced |
| Postgres: check.test_balance | n8n-nodes-base.postgres | db_check_balance |
| SSH: run.evaluation | n8n-nodes-base.ssh | ssh_run_eval |
| Webhook: evaluation.start | n8n-nodes-base.webhook | webhook_eval |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: evaluation.start
    │
    ▼
Postgres: check.test_balance
    │
    ▼
IF: test_set.balanced? (min 20/class)
    │
    └──► [True] ──► Code: prepare.evaluation
                            │
                            ▼
                    SSH: run.evaluation
                            │
                            ▼
                    Code: parse.results
                            │
                            ▼
                    HTTP: mlflow.log_metrics
                            │
                            ▼
                    IF: Gate_A.pass?
                            │
                            ├──► [True] ──► HTTP: emit.completed
                            │
                            └──► [False] ──► HTTP: emit.gate_failed
```

---

## Node Details

### 1. Webhook: evaluation.start

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-600, 300]  
**Purpose:** Entry point for evaluation requests.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests |
| `path` | `agent/evaluation/efficientnet/start` | URL path |
| `responseMode` | `onReceived` | Respond immediately |
| `webhookId` | `efficientnet-eval-start` | Unique identifier |

#### Expected Input

```json
{
  "run_id": "efficientnet_b0_emotion_xxx",
  "checkpoint_path": "/workspace/checkpoints/efficientnet_b0_emotion/best_model.pth",
  "correlation_id": "string",
  "mlflow_run_id": "string"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 2. Postgres: check.test_balance

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [-400, 300]  
**Purpose:** Checks test data balance (happy, sad, neutral counts).

#### SQL Query

```sql
SELECT
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test,
  COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test
FROM video;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 3. IF: test_set.balanced?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [-200, 300]  
**Purpose:** Validates minimum test data requirement (≥20 per class).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.number[0].value1` | `={{Math.min($json.happy_test, $json.sad_test, $json.neutral_test)}}` | Minimum class count |
| `conditions.number[0].operation` | `largerEqual` | ≥ comparison |
| `conditions.number[0].value2` | `20` | Minimum threshold |

#### Test Status: ✅ OPERATIONAL

---

### 4. Code: prepare.evaluation

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [0, 200]  
**Purpose:** Prepares evaluation command parameters.

#### JavaScript Code

```javascript
// Prepare evaluation command
const runId = $json.run_id || 'latest';
const checkpointPath = $json.checkpoint_path || 
  `/workspace/checkpoints/efficientnet_b0_emotion/best_model.pth`;

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    checkpoint_path: checkpointPath,
    model_placeholder: 'efficientnet-b0-hsemotion'
  }
}];
```

#### Test Status: ✅ OPERATIONAL

---

### 5. SSH: run.evaluation

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [200, 200]  
**Purpose:** Executes model evaluation on Ubuntu 1.

#### Command

```bash
cd /workspace && source venv/bin/activate && python -c "
from trainer.fer_finetune.model import load_pretrained_model
from trainer.fer_finetune.dataset import create_dataloaders
from trainer.fer_finetune.evaluate import evaluate_model, generate_report
import json

model = load_pretrained_model('{{$json.checkpoint_path}}', num_classes=3)
_, val_loader = create_dataloaders('/media/project_data/reachy_emotion/videos', batch_size=32)
results = evaluate_model(model, val_loader, class_names=['happy', 'sad', 'neutral'])
report = generate_report(results, '/workspace/experiments/{{$json.run_id}}/eval_report.txt')
print(json.dumps(results))
"
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Related Code

**File:** `trainer/fer_finetune/evaluate.py`

| Function | Purpose |
|----------|---------|
| `evaluate_model()` | Run inference, compute metrics |
| `generate_report()` | Create evaluation report |

**File:** `trainer/fer_finetune/model.py`

| Function | Purpose |
|----------|---------|
| `load_pretrained_model()` | Load checkpoint |

#### Test Status: ✅ OPERATIONAL

---

### 6. Code: parse.results

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [400, 200]  
**Purpose:** Parses evaluation results and validates Gate A.

#### JavaScript Code

```javascript
// Parse evaluation results
const output = $json.stdout || '{}';
let results;
try {
  results = JSON.parse(output);
} catch (e) {
  results = {error: 'Failed to parse evaluation output', raw: output};
}

// Check Gate A requirements
const gateA = {
  f1_macro: results.f1_macro >= 0.84,
  balanced_accuracy: results.balanced_accuracy >= 0.85,
  ece: results.ece <= 0.08,
  brier: results.brier <= 0.16,
  passed: false
};
gateA.passed = gateA.f1_macro && gateA.balanced_accuracy && gateA.ece && gateA.brier;

return [{
  json: {
    ...items[0].json,
    metrics: results,
    gate_a: gateA
  }
}];
```

#### Gate A Requirements

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `f1_macro` | ≥ 0.84 | Macro F1 score |
| `balanced_accuracy` | ≥ 0.85 | Balanced accuracy |
| `ece` | ≤ 0.08 | Expected Calibration Error |
| `brier` | ≤ 0.16 | Brier score |

#### Output Schema

```json
{
  "metrics": {
    "accuracy": 0.89,
    "f1_macro": 0.87,
    "f1_happy": 0.88,
    "f1_sad": 0.86,
    "balanced_accuracy": 0.88,
    "ece": 0.05,
    "brier": 0.12,
    "confusion_matrix": [[45, 5], [4, 46]]
  },
  "gate_a": {
    "f1_macro": true,
    "balanced_accuracy": true,
    "ece": true,
    "brier": true,
    "passed": true
  }
}
```

#### Test Status: ✅ OPERATIONAL

---

### 7. HTTP: mlflow.log_metrics

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [600, 200]  
**Purpose:** Logs evaluation metrics to MLflow.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-batch` | MLflow batch API |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `run_id` | `={{$json.mlflow_run_id}}` | MLflow run |
| `metrics` | Array of metrics | F1, accuracy, ECE, Brier, balanced_accuracy |

#### Metrics Logged

- `eval_f1_macro`
- `eval_accuracy`
- `eval_ece`
- `eval_brier`
- `eval_balanced_accuracy`

#### Test Status: ⚠️ TBD (requires MLflow server)

---

### 8. IF: Gate_A.pass?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [800, 200]  
**Purpose:** Routes based on Gate A validation result.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.gate_a.passed}}` | Gate A result |
| `conditions.boolean[0].value2` | `true` | Expected pass |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Gate A passed | HTTP: emit.completed |
| False | Gate A failed | HTTP: emit.gate_failed |

#### Test Status: ✅ OPERATIONAL

---

### 9. HTTP: emit.completed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1000, 100]  
**Purpose:** Emits evaluation.completed event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `evaluation.completed` | Event type |
| `run_id` | `={{$json.run_id}}` | Run ID |
| `model` | `efficientnet-b0-hsemotion` | Model |
| `gate_a_passed` | `={{$json.gate_a.passed}}` | Gate result |
| `f1_macro` | `={{$json.metrics.f1_macro}}` | F1 score |
| `ece` | `={{$json.metrics.ece}}` | ECE |
| `ready_for_deployment` | `={{$json.gate_a.passed}}` | Deploy flag |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

### 10. HTTP: emit.gate_failed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1000, 300]  
**Purpose:** Emits evaluation.gate_failed event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `evaluation.gate_failed` | Event type |
| `run_id` | `={{$json.run_id}}` | Run ID |
| `model` | `efficientnet-b0-hsemotion` | Model |
| `gate_a_details` | `={{JSON.stringify($json.gate_a)}}` | Gate details |
| `metrics` | `={{JSON.stringify($json.metrics)}}` | All metrics |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `MLFLOW_URL` | MLflow tracking server | `http://10.0.4.130:5000` |
| `GATEWAY_BASE_URL` | Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Database |
| 3 | SSH Ubuntu1 | SSH Password | Evaluation server |

---

## Tags

- `agent`
- `evaluation`
- `efficientnet`
- `ml-v1`

---

## Related Code Files

| File | Purpose |
|------|---------|
| `trainer/fer_finetune/evaluate.py` | Evaluation logic |
| `trainer/fer_finetune/model.py` | Model loading |
| `trainer/fer_finetune/dataset.py` | Data loading |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `/api/events/evaluation` |
| MLflow Integration | HIGH | Configure MLflow server |
| Insufficient Data Handler | MEDIUM | Add branch for test set too small |

---

## Connections Summary

```json
{
  "webhook_eval": { "main": [["db_check_balance"]] },
  "db_check_balance": { "main": [["if_balanced"]] },
  "if_balanced": { "main": [["prepare_eval"]] },
  "prepare_eval": { "main": [["ssh_run_eval"]] },
  "ssh_run_eval": { "main": [["parse_results"]] },
  "parse_results": { "main": [["mlflow_log"]] },
  "mlflow_log": { "main": [["gate_a_check"]] },
  "gate_a_check": { "main": [["emit_completed"], ["emit_gate_failed"]] }
}
```
