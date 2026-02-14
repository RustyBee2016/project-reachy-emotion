# Module 7: Evaluation Agent — Comprehensive Metrics & Calibration

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~3 hours  
**Prerequisites**: Completed Modules 0-6

---

## Learning Objectives

By the end of this module, you will:
1. Understand **evaluation metrics** for classification (F1, accuracy, calibration)
2. Execute **model inference** via SSH
3. Parse **comprehensive results** including confusion matrices
4. Log metrics to **MLflow** for tracking
5. Validate **Gate A** from evaluation perspective

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Calibration metrics** | ECE, Brier score | Model confidence quality |
| **Confusion matrix** | Multi-class breakdown | Per-class performance |
| **Batch metric logging** | MLflow log-batch | Efficient metric storage |
| **Evaluation vs Training** | Different thresholds | Generalization check |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Webhook: evaluation.start | n8n webhook | ⬜ (native) |
| 2 | Postgres: check.test_balance | PostgreSQL query | ⬜ |
| 3 | IF: test_set.balanced? | n8n conditional | ⬜ (native) |
| 4 | Code: prepare.evaluation | JavaScript | ⬜ (native) |
| 5 | SSH: run.evaluation | SSH + Python | ⬜ |
| 6 | Code: parse.results | JavaScript | ⬜ (native) |
| 7 | HTTP: mlflow.log_metrics | MLflow API | ⬜ |
| 8 | IF: Gate_A.pass? | n8n conditional | ⬜ (native) |
| 9-10 | HTTP: emit.* | Gateway events | ⬜ |

---

### Verification Procedures

#### Test 1: Test Data Balance Query

```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test,
  COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test
FROM video;
```

**Requirement**: All counts ≥ 20 for evaluation.

**Status**: ⬜ → [ ] Complete

---

#### Test 2: Evaluation Script

```bash
# Verify evaluation module exists
ls -la /home/rusty_admin/projects/reachy_08.4.2/trainer/fer_finetune/evaluate.py
```

**Status**: ⬜ → [ ] Complete

---

## Part 1: Understanding Model Evaluation

### Training vs Evaluation

| Aspect | Training | Evaluation |
|--------|----------|------------|
| **Dataset** | train split | test split |
| **Purpose** | Learn patterns | Verify generalization |
| **Metrics** | Loss, train accuracy | F1, ECE, Brier |
| **Frequency** | Once per experiment | After training completes |

### Gate A Metrics Explained

| Metric | What It Measures | Threshold | Formula |
|--------|-----------------|-----------|---------|
| **F1 Macro** | Balance of precision/recall | ≥ 0.84 | Harmonic mean across classes |
| **Balanced Accuracy** | Per-class accuracy average | ≥ 0.85 | Mean of per-class recalls |
| **ECE** | Calibration error | ≤ 0.08 | Expected Calibration Error |
| **Brier Score** | Probability accuracy | ≤ 0.16 | Mean squared prediction error |

### Workflow Architecture

```
Webhook: evaluation.start
       │
       ▼
Postgres: check.test_balance
       │
       ▼
IF: test_set.balanced? (min 20/class)
       │
    [True]
       │
       ▼
Code: prepare.evaluation
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
   │         │
[True]    [False]
   │         │
   ▼         ▼
emit.completed   emit.gate_failed
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 6 — Evaluation Agent EfficientNet-B0 (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Webhook Trigger

**Node Name**: `Webhook: evaluation.start`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `agent/evaluation/efficientnet/start` |
| Response Mode | `When Last Node Finishes` |

**Expected Input**:
```json
{
  "run_id": "efficientnet_b0_emotion_xxx",
  "checkpoint_path": "/path/to/best_model.pth",
  "correlation_id": "string",
  "mlflow_run_id": "string"
}
```

---

### Step 3: Add Test Balance Check

**Node Name**: `Postgres: check.test_balance`

**SQL**:
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test
FROM video;
```

---

### Step 4: Add Balance Validation

**Node Name**: `IF: test_set.balanced?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{Math.min($json.happy_test, $json.sad_test, $json.neutral_test)}}` |
| Operation | `Larger or Equal` |
| Value 2 | `20` |

---

### Step 5: Add Evaluation Preparation

**Node Name**: `Code: prepare.evaluation`

```javascript
// Prepare evaluation parameters
const runId = $json.run_id || 'latest';
const checkpointPath = $json.checkpoint_path || 
  `/home/rusty_admin/projects/reachy_08.4.2/experiments/${runId}/best_model.pth`;

return [{
  json: {
    ...$('Webhook: evaluation.start').item.json,
    run_id: runId,
    checkpoint_path: checkpointPath,
    model_placeholder: 'efficientnet-b0-hsemotion',
    test_data_path: '/media/project_data/reachy_emotion/videos/test',
    output_dir: `/home/rusty_admin/projects/reachy_08.4.2/experiments/${runId}`
  }
}];
```

---

### Step 6: Add Evaluation Execution

**Node Name**: `SSH: run.evaluation`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command**:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2 && \
source venv/bin/activate && \
python -c "
import json
from trainer.fer_finetune.model_efficientnet import load_pretrained_model
from trainer.fer_finetune.dataset import create_dataloaders
from trainer.fer_finetune.evaluate import evaluate_model

model = load_pretrained_model('{{$json.checkpoint_path}}', num_classes=3)
_, test_loader = create_dataloaders('{{$json.test_data_path}}', batch_size=32)
results = evaluate_model(model, test_loader, class_names=['happy', 'sad', 'neutral'])
print(json.dumps(results))
"
```

**Output Example**:
```json
{
  "accuracy": 0.89,
  "f1_macro": 0.87,
  "f1_happy": 0.88,
  "f1_sad": 0.86,
  "balanced_accuracy": 0.88,
  "ece": 0.05,
  "brier": 0.12,
  "confusion_matrix": [[45, 5], [4, 46]]
}
```

---

### Step 7: Add Results Parser with Gate A Check

**Node Name**: `Code: parse.results`

```javascript
// Parse evaluation results and check Gate A
const stdout = $json.stdout || '{}';
let results;

try {
  results = JSON.parse(stdout);
} catch (e) {
  return [{
    json: {
      ...items[0].json,
      error: 'Failed to parse evaluation output',
      raw_output: stdout
    }
  }];
}

// Gate A thresholds
const gateA = {
  f1_macro: results.f1_macro >= 0.84,
  balanced_accuracy: results.balanced_accuracy >= 0.85,
  ece: results.ece <= 0.08,
  brier: results.brier <= 0.16,
  passed: false
};

// All must pass
gateA.passed = gateA.f1_macro && 
               gateA.balanced_accuracy && 
               gateA.ece && 
               gateA.brier;

return [{
  json: {
    ...$('Code: prepare.evaluation').item.json,
    metrics: results,
    gate_a: gateA,
    ready_for_deployment: gateA.passed
  }
}];
```

---

### Step 8: Add MLflow Metric Logging

**Node Name**: `HTTP: mlflow.log_metrics`

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-batch` |

**Body**:
```json
{
  "run_id": "={{$json.mlflow_run_id}}",
  "metrics": [
    {"key": "eval_f1_macro", "value": "={{$json.metrics.f1_macro}}", "timestamp": "={{Date.now()}}"},
    {"key": "eval_accuracy", "value": "={{$json.metrics.accuracy}}", "timestamp": "={{Date.now()}}"},
    {"key": "eval_ece", "value": "={{$json.metrics.ece}}", "timestamp": "={{Date.now()}}"},
    {"key": "eval_brier", "value": "={{$json.metrics.brier}}", "timestamp": "={{Date.now()}}"},
    {"key": "eval_balanced_accuracy", "value": "={{$json.metrics.balanced_accuracy}}", "timestamp": "={{Date.now()}}"},
    {"key": "gate_a_passed", "value": "={{$json.gate_a.passed ? 1 : 0}}", "timestamp": "={{Date.now()}}"}
  ]
}
```

---

### Step 9: Add Gate A Decision

**Node Name**: `IF: Gate_A.pass?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.gate_a.passed}}` |
| Operation | `Is True` |

---

### Step 10: Add Event Emissions

**Node Name**: `HTTP: emit.completed`

```json
{
  "event_type": "evaluation.completed",
  "run_id": "={{$json.run_id}}",
  "model": "efficientnet-b0-hsemotion",
  "gate_a_passed": "={{$json.gate_a.passed}}",
  "f1_macro": "={{$json.metrics.f1_macro}}",
  "ece": "={{$json.metrics.ece}}",
  "ready_for_deployment": "={{$json.ready_for_deployment}}"
}
```

**Node Name**: `HTTP: emit.gate_failed`

```json
{
  "event_type": "evaluation.gate_failed",
  "run_id": "={{$json.run_id}}",
  "model": "efficientnet-b0-hsemotion",
  "gate_a_details": "={{JSON.stringify($json.gate_a)}}",
  "metrics": "={{JSON.stringify($json.metrics)}}"
}
```

---

## Part 3: Understanding Calibration Metrics

### Expected Calibration Error (ECE)

ECE measures how well the model's confidence matches actual accuracy:
- If model says 80% confident → should be correct ~80% of the time
- Lower is better (≤ 0.08 is our threshold)

### Brier Score

Brier score measures probability accuracy:
- Mean squared error between predicted probability and actual outcome
- Range: 0 (perfect) to 1 (worst)
- Lower is better (≤ 0.16 is our threshold)

### Why Calibration Matters

For emotion recognition on a robot:
- Uncertain predictions should be flagged
- Over-confident wrong predictions are dangerous
- Well-calibrated models enable better decision-making

---

## Module 7 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Evaluation metrics | F1, accuracy, ECE, Brier |
| Python evaluation | SSH with inline script |
| Gate A validation | Threshold checks in Code node |
| MLflow logging | Batch metric API |
| Calibration | ECE ≤ 0.08, Brier ≤ 0.16 |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: evaluation.start | Webhook | Entry point |
| 2 | Postgres: check.test_balance | Postgres | Test set validation |
| 3 | IF: test_set.balanced? | IF | Minimum samples check |
| 4 | Code: prepare.evaluation | Code | Setup parameters |
| 5 | SSH: run.evaluation | SSH | Execute evaluation |
| 6 | Code: parse.results | Code | Parse + Gate A check |
| 7 | HTTP: mlflow.log_metrics | HTTP Request | Log to MLflow |
| 8 | IF: Gate_A.pass? | IF | Quality gate |
| 9-10 | HTTP: emit.* | HTTP Request | Event emissions |

---

## Next Steps

Proceed to **Module 8: Deployment Agent** where you'll learn:
- **SCP file transfer** between servers
- **TensorRT conversion** for edge deployment
- **DeepStream configuration** updates
- **Gate B validation** (FPS, latency)
- **Automatic rollback** on failure

---

*Module 7 Complete — Proceed to Module 8: Deployment Agent*
