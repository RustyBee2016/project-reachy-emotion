# Module 6: Training Orchestrator — Long-Running Processes, Polling & MLflow

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~5 hours  
**Prerequisites**: Completed Modules 0-5

---

## Learning Objectives

By the end of this module, you will:
1. Orchestrate **long-running SSH processes** (ML training)
2. Implement **polling loops** for async status checking
3. Integrate with **MLflow** for experiment tracking
4. Validate **Gate A requirements** (quality thresholds)
5. Handle **insufficient data** scenarios gracefully

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Long-running SSH** | Background process | Training takes hours |
| **Polling loop** | Wait → Check → IF → Loop | Monitor async processes |
| **MLflow integration** | HTTP to MLflow API | Experiment tracking |
| **Quality gates** | IF with thresholds | Prevent bad models |
| **Data validation** | Check before training | Ensure sufficient samples |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Webhook: training.start | n8n webhook | ⬜ (native) |
| 2 | Postgres: check.train_balance | PostgreSQL query | ⬜ |
| 3 | IF: sufficient_data? | n8n conditional | ⬜ (native) |
| 4 | HTTP: mlflow.create_run | MLflow REST API | ⬜ |
| 5 | Code: prepare.training | JavaScript | ⬜ (native) |
| 6 | SSH: start.training | SSH + Python script | ⬜ |
| 7 | Wait: 5min | n8n Wait | ⬜ (native) |
| 8 | SSH: check.status | SSH check for results.json | ⬜ |
| 9 | Code: parse.results | JavaScript | ⬜ (native) |
| 10 | IF: training.done? | n8n conditional | ⬜ (native) |
| 11 | IF: Gate_A.pass? | n8n conditional | ⬜ (native) |
| 12 | HTTP: mlflow.log_gate | MLflow REST API | ⬜ |
| 13-15 | HTTP: emit.* | Gateway events API | ⬜ |

---

### Verification Procedures

#### Test 1: Training Data Balance Query

```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train
FROM video;
```

**Requirement**: Both counts ≥ 50 for training to proceed.

**Status**: ⬜ → [ ] Complete

---

#### Test 2: MLflow Server (Optional)

```bash
curl http://10.0.4.130:5000/api/2.0/mlflow/experiments/list
```

**Expected**: JSON with experiments list. If MLflow not running, you can skip MLflow nodes.

**Status**: ⬜ → [ ] Complete (or N/A)

---

#### Test 3: Training Script Exists

```bash
ls -la /home/rusty_admin/projects/reachy_08.4.2/trainer/train_resnet50.py
```

**Status**: ⬜ → [ ] Complete

---

#### Test 4: Training Environment

```bash
# Verify Python environment
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
```

**Status**: ⬜ → [ ] Complete

---

## Part 1: Understanding ML Training Orchestration

### The Challenge

ML training is fundamentally different from typical API calls:
- Takes **hours**, not seconds
- Runs as a **background process**
- Produces **intermediate outputs** (checkpoints)
- Has **quality requirements** (Gate A)

### Polling Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    POLLING PATTERN FOR ASYNC OPS                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Start Process (SSH)                                                    │
│        │                                                                │
│        ▼                                                                │
│  ┌──► Wait: 5 minutes                                                   │
│  │        │                                                             │
│  │        ▼                                                             │
│  │   Check Status (SSH)                                                 │
│  │        │                                                             │
│  │        ▼                                                             │
│  │   IF: Done?                                                          │
│  │     │      │                                                         │
│  │  [No]    [Yes]                                                       │
│  │     │      │                                                         │
│  └─────┘      ▼                                                         │
│           Continue...                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Gate A Requirements

| Metric | Threshold | Description |
|--------|-----------|-------------|
| F1 (macro) | ≥ 0.84 | Balance between precision/recall |
| Balanced Accuracy | ≥ 0.85 | Accuracy adjusted for class imbalance |
| ECE | ≤ 0.08 | Expected Calibration Error |
| Brier Score | ≤ 0.16 | Calibration quality |

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 5 — Training Orchestrator ResNet-50 (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Webhook Trigger

**Node Name**: `Webhook: training.start`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `agent/training/resnet50/start` |
| Response Mode | `When Last Node Finishes` |
| Response Code | `202` |

**202 Accepted**: Indicates request received, processing asynchronously.

---

### Step 3: Add Data Balance Check

**Node Name**: `Postgres: check.train_balance`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train
FROM video;
```

---

### Step 4: Add Data Sufficiency Check

**Node Name**: `IF: sufficient_data?`

| Parameter | Value |
|-----------|-------|
| Condition | Number |
| Value 1 | `={{Math.min($json.happy_train, $json.sad_train)}}` |
| Operation | `Larger or Equal` |
| Value 2 | `50` |

**Outputs**:
- **True**: Proceed to training
- **False**: Emit insufficient data event

---

### Step 5: Add MLflow Run Creation (Optional)

**Node Name**: `HTTP: mlflow.create_run`

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create` |

**Body**:
```json
{
  "experiment_id": "={{$env.MLFLOW_EXPERIMENT_ID}}",
  "tags": [
    {"key": "model", "value": "resnet50-affectnet-raf-db"},
    {"key": "trigger", "value": "n8n"}
  ]
}
```

**If MLflow not available**: Set "Continue On Fail" = true, or replace with a Code node that generates a local run ID.

---

### Step 6: Add Training Preparation

**Node Name**: `Code: prepare.training`

```javascript
// Generate run ID and prepare training configuration
const timestamp = new Date().toISOString()
  .replace(/[-:T]/g, '')
  .slice(0, 14);
const runId = `resnet50_emotion_${timestamp}`;

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    config_path: '/home/rusty_admin/projects/reachy_08.4.2/trainer/fer_finetune/specs/resnet50_emotion_2cls.yaml',
    model_placeholder: 'resnet50-affectnet-raf-db',
    model_storage_path: '/media/rusty_admin/project_data/ml_models/resnet50',
    experiments_dir: '/home/rusty_admin/projects/reachy_08.4.2/experiments'
  }
}];
```

---

### Step 7: Add Training Start (SSH)

**Node Name**: `SSH: start.training`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command**:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2 && \
source venv/bin/activate && \
mkdir -p {{$json.experiments_dir}}/{{$json.run_id}} && \
nohup python trainer/train_resnet50.py \
  --config {{$json.config_path}} \
  --run-id {{$json.run_id}} \
  > {{$json.experiments_dir}}/{{$json.run_id}}/train.log 2>&1 &
echo "Training started: {{$json.run_id}}"
```

**Key Elements**:
| Element | Purpose |
|---------|---------|
| `nohup` | Don't terminate when SSH disconnects |
| `&` | Run in background |
| `> ... 2>&1` | Redirect stdout and stderr to log |

---

### Step 8: Add Polling Wait

**Node Name**: `Wait: 5min`

| Parameter | Value |
|-----------|-------|
| Amount | `5` |
| Unit | `Minutes` |

**Why 5 minutes?** Balance between responsiveness and resource usage. Training typically takes 1-2 hours.

---

### Step 9: Add Status Check

**Node Name**: `SSH: check.status`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command**:
```bash
if [ -f {{$json.experiments_dir}}/{{$json.run_id}}/results.json ]; then
  cat {{$json.experiments_dir}}/{{$json.run_id}}/results.json
else
  echo '{"status": "running"}'
fi
```

**Logic**: If `results.json` exists, training is complete; otherwise still running.

---

### Step 10: Add Results Parser

**Node Name**: `Code: parse.results`

```javascript
// Parse training results
const stdout = $json.stdout || '{}';
let result;

try {
  result = JSON.parse(stdout);
} catch (e) {
  result = { status: 'error', message: 'Failed to parse output' };
}

if (result.status === 'running') {
  return [{
    json: {
      ...$('Code: prepare.training').item.json,
      status: 'running'
    }
  }];
}

// Training complete - parse results
return [{
  json: {
    ...$('Code: prepare.training').item.json,
    status: result.status || 'completed',
    best_metric: result.best_metric || result.f1_macro,
    epochs_completed: result.epochs_completed,
    gate_results: {
      gate_a: result.f1_macro >= 0.84 && 
              result.balanced_accuracy >= 0.85 &&
              result.ece <= 0.08,
      f1_macro: result.f1_macro,
      balanced_accuracy: result.balanced_accuracy,
      ece: result.ece,
      brier: result.brier
    },
    export: result.export || null
  }
}];
```

---

### Step 11: Add Done Check

**Node Name**: `IF: training.done?`

| Parameter | Value |
|-----------|-------|
| Condition | String |
| Value 1 | `={{$json.status}}` |
| Operation | `Contains` |
| Value 2 | `completed` |

**Outputs**:
- **True**: Proceed to Gate A check
- **False**: Loop back to Wait (polling)

**Create the Loop**:
1. Connect IF (False) → Wait: 5min
2. This creates: Wait → Check → Parse → IF → (back to Wait)

---

### Step 12: Add Gate A Check

**Node Name**: `IF: Gate_A.pass?`

| Parameter | Value |
|-----------|-------|
| Condition | Boolean |
| Value 1 | `={{$json.gate_results.gate_a}}` |
| Operation | `Is True` |

---

### Step 13: Add Event Emissions

**Node Name**: `HTTP: emit.completed` (Gate A passed)

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/training` |

**Body**:
```json
{
  "event_type": "training.completed",
  "run_id": "={{$json.run_id}}",
  "model": "resnet50-affectnet-raf-db",
  "gate_a_passed": true,
  "f1_macro": "={{$json.gate_results.f1_macro}}",
  "onnx_path": "={{$json.export?.onnx || ''}}"
}
```

**Node Name**: `HTTP: emit.gate_failed` (Gate A failed)

**Body**:
```json
{
  "event_type": "training.gate_failed",
  "run_id": "={{$json.run_id}}",
  "model": "resnet50-affectnet-raf-db",
  "gate_a_passed": false,
  "message": "Gate A requirements not met"
}
```

**Node Name**: `HTTP: emit.insufficient_data` (Not enough training data)

Connect from: IF: sufficient_data? (False branch)

**Body**:
```json
{
  "event_type": "training.insufficient_data",
  "happy_count": "={{$json.happy_train}}",
  "sad_count": "={{$json.sad_train}}",
  "required": 50,
  "message": "Need at least 50 samples per class"
}
```

---

## Part 3: Complete Connection Map

```
webhook_training
       │
       ▼
db_check_balance
       │
       ▼
if_sufficient_data
  │           │
[True]     [False]
  │           │
  ▼           ▼
mlflow_create_run   emit_insufficient
  │
  ▼
prepare_training
  │
  ▼
ssh_start_training
  │
  ▼
wait_poll ◄─────────────────────┐
  │                             │
  ▼                             │
check_status                    │
  │                             │
  ▼                             │
parse_results                   │
  │                             │
  ▼                             │
if_done ────────────────────────┤
  │                        [False]
[True]
  │
  ▼
gate_a_check
  │         │
[True]   [False]
  │         │
  ▼         ▼
mlflow_log_gate   emit_gate_failed
  │
  ▼
emit_completed
```

---

## Part 4: Testing

### Test 1: Insufficient Data Scenario

First, ensure you have < 50 samples per class:

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/agent/training/resnet50/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected**: Event emitted with "insufficient_data"

### Test 2: Training Start (Mock)

Create a mock results.json to simulate completed training:

```bash
mkdir -p /home/rusty_admin/projects/reachy_08.4.2/experiments/test_run
echo '{
  "status": "completed",
  "f1_macro": 0.87,
  "balanced_accuracy": 0.88,
  "ece": 0.05,
  "brier": 0.12,
  "epochs_completed": 30
}' > /home/rusty_admin/projects/reachy_08.4.2/experiments/test_run/results.json
```

Then modify the Code: prepare.training to use `run_id: "test_run"` for testing.

---

## Module 6 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Long-running SSH | `nohup ... &` with log redirect |
| Polling loop | Wait → Check → IF → Loop |
| MLflow integration | REST API calls |
| Quality gates | IF with metric thresholds |
| Data validation | Check counts before start |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: training.start | Webhook | Entry point |
| 2 | Postgres: check.train_balance | Postgres | Data validation |
| 3 | IF: sufficient_data? | IF | Minimum data check |
| 4 | HTTP: mlflow.create_run | HTTP Request | Create experiment |
| 5 | Code: prepare.training | Code | Setup run config |
| 6 | SSH: start.training | SSH | Launch training |
| 7 | Wait: 5min | Wait | Polling interval |
| 8 | SSH: check.status | SSH | Check results |
| 9 | Code: parse.results | Code | Parse JSON output |
| 10 | IF: training.done? | IF | Completion check |
| 11 | IF: Gate_A.pass? | IF | Quality gate |
| 12-15 | HTTP: emit.* | HTTP Request | Event emissions |

---

## Next Steps

Proceed to **Module 7: Evaluation Agent** where you'll learn:
- **Comprehensive metrics** computation (F1, ECE, Brier)
- **Confusion matrix** generation
- **Report generation** for human review
- **Gate A re-validation** post-evaluation

---

*Module 6 Complete — Proceed to Module 7: Evaluation Agent*
