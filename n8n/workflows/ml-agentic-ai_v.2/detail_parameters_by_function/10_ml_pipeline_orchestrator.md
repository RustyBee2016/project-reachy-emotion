# ML Pipeline Orchestrator — ResNet-50 (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-29

## Overview

The ML Pipeline Orchestrator coordinates the entire ML pipeline from dataset preparation to deployment. It checks dataset readiness, triggers Training Agent (05), Evaluation Agent (06), and optionally Deployment Agent (07) in sequence. It supports auto-deploy mode for fully automated pipelines.

**Model:** `resnet50-affectnet-raf-db`  
**Storage Path:** `/media/rusty_admin/project_data/ml_models/resnet50`

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: check.dataset | n8n-nodes-base.code | check_dataset |
| Code: init.pipeline | n8n-nodes-base.code | init_pipeline |
| HTTP: check.training_status | n8n-nodes-base.httpRequest | check_training |
| HTTP: emit.blocked | n8n-nodes-base.httpRequest | emit_blocked |
| HTTP: emit.pipeline_complete | n8n-nodes-base.httpRequest | emit_complete |
| HTTP: trigger.deployment | n8n-nodes-base.httpRequest | trigger_deployment |
| HTTP: trigger.evaluation | n8n-nodes-base.httpRequest | trigger_evaluation |
| HTTP: trigger.training | n8n-nodes-base.httpRequest | trigger_training |
| IF: auto_deploy? | n8n-nodes-base.if | if_auto_deploy |
| IF: dataset.ready? | n8n-nodes-base.if | if_dataset_ready |
| IF: training.done? | n8n-nodes-base.if | if_training_done |
| Postgres: dataset.stats | n8n-nodes-base.postgres | db_dataset_stats |
| Wait: evaluation | n8n-nodes-base.wait | wait_evaluation |
| Wait: training | n8n-nodes-base.wait | wait_training |
| Webhook: pipeline.start | n8n-nodes-base.webhook | webhook_start |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: pipeline.start
    │
    ▼
Code: init.pipeline
    │
    ▼
Postgres: dataset.stats
    │
    ▼
Code: check.dataset
    │
    ▼
IF: dataset.ready?
    │
    ├──► [False] ──► HTTP: emit.blocked
    │
    └──► [True] ──► HTTP: trigger.training (Agent 05)
                            │
                            ▼
                    Wait: training (10 min)
                            │
                            ▼
                    HTTP: check.training_status
                            │
                            ▼
                    IF: training.done?
                            │
                            ├──► [False] ──► Wait: training (loop)
                            │
                            └──► [True] ──► HTTP: trigger.evaluation (Agent 06)
                                                    │
                                                    ▼
                                            Wait: evaluation (5 min)
                                                    │
                                                    ▼
                                            IF: auto_deploy?
                                                    │
                                                    ├──► [True & Gate A passed] ──► HTTP: trigger.deployment (Agent 07)
                                                    │                                       │
                                                    │                                       ▼
                                                    │                               HTTP: emit.pipeline_complete
                                                    │
                                                    └──► [False] ──► HTTP: emit.pipeline_complete
```

---

## Node Details

### 1. Webhook: pipeline.start

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-800, 300]  
**Purpose:** Entry point for ML pipeline execution.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests |
| `path` | `ml/pipeline/start` | URL path |
| `responseMode` | `onReceived` | Respond immediately |
| `options.responseCode` | `202` | HTTP 202 Accepted |
| `webhookId` | `ml-pipeline-start` | Unique identifier |

#### Expected Input

```json
{
  "config": "fer_finetune/specs/resnet50_emotion_2cls.yaml",  // Optional
  "auto_deploy": false,                                        // Optional
  "correlation_id": "string"                                   // Optional
}
```

#### Test Status: ✅ OPERATIONAL

---

### 2. Code: init.pipeline

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-600, 300]  
**Purpose:** Initializes pipeline run with unique ID and configuration.

#### JavaScript Code

```javascript
// Initialize pipeline run
const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const pipelineId = `ml_pipeline_${timestamp}`;

return [{
  json: {
    pipeline_id: pipelineId,
    model: 'resnet50-affectnet-raf-db',
    model_storage_path: '/media/rusty_admin/project_data/ml_models/resnet50',
    stages: ['dataset_check', 'training', 'evaluation', 'deployment'],
    current_stage: 'dataset_check',
    config: $json.config || 'fer_finetune/specs/resnet50_emotion_2cls.yaml',
    auto_deploy: $json.auto_deploy || false,
    correlation_id: $json.correlation_id || pipelineId
  }
}];
```

#### Output Schema

```json
{
  "pipeline_id": "ml_pipeline_20251129150000",
  "model": "resnet50-affectnet-raf-db",
  "model_storage_path": "/media/rusty_admin/project_data/ml_models/resnet50",
  "stages": ["dataset_check", "training", "evaluation", "deployment"],
  "current_stage": "dataset_check",
  "config": "fer_finetune/specs/resnet50_emotion_2cls.yaml",
  "auto_deploy": false,
  "correlation_id": "ml_pipeline_20251129150000"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 3. Postgres: dataset.stats

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [-400, 300]  
**Purpose:** Fetches dataset statistics for both train and test splits.

#### SQL Query

```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test
FROM video;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

### 4. Code: check.dataset

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-200, 300]  
**Purpose:** Validates dataset readiness against minimum requirements.

#### JavaScript Code

```javascript
// Check dataset readiness
const stats = items[0].json;
const minTrainPerClass = 50;
const minTestPerClass = 20;

const trainReady = Math.min(stats.happy_train, stats.sad_train) >= minTrainPerClass;
const testReady = Math.min(stats.happy_test, stats.sad_test) >= minTestPerClass;
const balanced = Math.abs(stats.happy_train - stats.sad_train) / 
                 Math.max(stats.happy_train, stats.sad_train) < 0.2;

return [{
  json: {
    ...items[0].json,
    dataset_stats: stats,
    dataset_ready: trainReady && testReady,
    train_ready: trainReady,
    test_ready: testReady,
    balanced: balanced,
    current_stage: trainReady ? 'training' : 'dataset_check'
  }
}];
```

#### Dataset Requirements

| Split | Minimum per Class | Balance Threshold |
|-------|-------------------|-------------------|
| train | 50 | < 20% imbalance |
| test | 20 | N/A |

#### Output Schema

```json
{
  "dataset_stats": {
    "happy_train": 55,
    "sad_train": 52,
    "happy_test": 22,
    "sad_test": 21
  },
  "dataset_ready": true,
  "train_ready": true,
  "test_ready": true,
  "balanced": true,
  "current_stage": "training"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 5. IF: dataset.ready?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [0, 300]  
**Purpose:** Routes based on dataset readiness.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.dataset_ready}}` | Readiness flag |
| `conditions.boolean[0].value2` | `true` | Expected value |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Dataset ready | HTTP: trigger.training |
| False | Dataset not ready | HTTP: emit.blocked |

#### Test Status: ✅ OPERATIONAL

---

### 6. HTTP: trigger.training

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [200, 200]  
**Purpose:** Triggers Training Orchestrator (Agent 05).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.N8N_HOST}}/webhook/agent/training/resnet50/start` | Training webhook |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `pipeline_id` | `={{$json.pipeline_id}}` | Pipeline ID |
| `correlation_id` | `={{$json.correlation_id}}` | Correlation ID |
| `config` | `={{$json.config}}` | Training config |
| `dataset_hash` | `={{$json.dataset_stats.happy_train + '_' + $json.dataset_stats.sad_train}}` | Dataset version |

#### Test Status: ✅ OPERATIONAL

---

### 7. Wait: training

**Type:** `n8n-nodes-base.wait` (v1.1)  
**Position:** [400, 200]  
**Purpose:** Waits for training to progress.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `amount` | `10` | Wait duration |
| `unit` | `minutes` | Time unit |

#### Test Status: ✅ OPERATIONAL

---

### 8. HTTP: check.training_status

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [600, 200]  
**Purpose:** Checks training status via Gateway API.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/training/status/{{$json.pipeline_id}}` | Status endpoint |
| `method` | `GET` | HTTP GET |

#### Expected Response

```json
{
  "status": "completed",
  "run_id": "resnet50_emotion_xxx",
  "gate_a_passed": true,
  "onnx_path": "/workspace/exports/xxx/model.onnx"
}
```

#### Test Status: ⚠️ TBD (requires status endpoint)

---

### 9. IF: training.done?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [800, 200]  
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
| True | Training completed | HTTP: trigger.evaluation |
| False | Still running | Wait: training (loop) |

#### Test Status: ✅ OPERATIONAL

---

### 10. HTTP: trigger.evaluation

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1000, 100]  
**Purpose:** Triggers Evaluation Agent (Agent 06).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.N8N_HOST}}/webhook/agent/evaluation/resnet50/start` | Evaluation webhook |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `pipeline_id` | `={{$json.pipeline_id}}` | Pipeline ID |
| `run_id` | `={{$json.run_id}}` | Training run ID |
| `correlation_id` | `={{$json.correlation_id}}` | Correlation ID |

#### Test Status: ✅ OPERATIONAL

---

### 11. Wait: evaluation

**Type:** `n8n-nodes-base.wait` (v1.1)  
**Position:** [1200, 100]  
**Purpose:** Waits for evaluation to complete.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `amount` | `5` | Wait duration |
| `unit` | `minutes` | Time unit |

#### Test Status: ✅ OPERATIONAL

---

### 12. IF: auto_deploy?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [1400, 100]  
**Purpose:** Checks if auto-deploy is enabled and Gate A passed.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.auto_deploy && $json.gate_a_passed}}` | Combined condition |
| `conditions.boolean[0].value2` | `true` | Expected value |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Auto-deploy enabled & Gate A passed | HTTP: trigger.deployment |
| False | Manual deploy or Gate A failed | HTTP: emit.pipeline_complete |

#### Test Status: ✅ OPERATIONAL

---

### 13. HTTP: trigger.deployment

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1600, 0]  
**Purpose:** Triggers Deployment Agent (Agent 07).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.N8N_HOST}}/webhook/agent/deployment/resnet50/start` | Deployment webhook |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `pipeline_id` | `={{$json.pipeline_id}}` | Pipeline ID |
| `run_id` | `={{$json.run_id}}` | Training run ID |
| `gate_a_passed` | `={{$json.gate_a_passed}}` | Gate A result |
| `onnx_path` | `={{$json.onnx_path}}` | ONNX model path |
| `correlation_id` | `={{$json.correlation_id}}` | Correlation ID |

#### Test Status: ✅ OPERATIONAL

---

### 14. HTTP: emit.pipeline_complete

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1800, 100]  
**Purpose:** Emits pipeline.completed event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `pipeline.completed` | Event type |
| `pipeline_id` | `={{$json.pipeline_id}}` | Pipeline ID |
| `model` | `resnet50-affectnet-raf-db` | Model |
| `final_stage` | `={{$json.current_stage}}` | Last stage |
| `gate_a_passed` | `={{$json.gate_a_passed}}` | Gate A result |
| `deployed` | `={{$json.deployed \|\| false}}` | Deployment status |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

### 15. HTTP: emit.blocked

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [200, 400]  
**Purpose:** Emits pipeline.blocked event when dataset insufficient.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `pipeline.blocked` | Event type |
| `pipeline_id` | `={{$json.pipeline_id}}` | Pipeline ID |
| `reason` | `Insufficient training data` | Block reason |
| `dataset_stats` | `={{JSON.stringify($json.dataset_stats)}}` | Current stats |
| `required` | `{train: 50/class, test: 20/class}` | Requirements |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `N8N_HOST` | n8n webhook base URL | `http://localhost:5678` |
| `GATEWAY_BASE_URL` | Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Dataset stats |

---

## Tags

- `orchestrator`
- `ml-pipeline`
- `resnet50`
- `ml-v1`

---

## Pipeline Stages

| Stage | Agent | Description |
|-------|-------|-------------|
| `dataset_check` | Orchestrator | Validate dataset readiness |
| `training` | Agent 05 | Fine-tune ResNet-50 |
| `evaluation` | Agent 06 | Evaluate model, Gate A |
| `deployment` | Agent 07 | Deploy to Jetson, Gate B |

---

## Auto-Deploy Mode

When `auto_deploy: true`:
1. Pipeline runs without human intervention
2. Deployment triggers automatically if Gate A passes
3. Rollback automatic if Gate B fails

When `auto_deploy: false` (default):
1. Pipeline stops after evaluation
2. Human reviews Gate A results
3. Manual trigger for deployment

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Training Status API | HIGH | Implement `/api/training/status/{id}` |
| Events Endpoint | HIGH | Implement `/api/events/pipeline` |
| Evaluation Status Check | MEDIUM | Add evaluation status polling |
| Retry Logic | MEDIUM | Add retry on agent failures |
| Notifications | LOW | Add Slack/email notifications |

---

## Connections Summary

```json
{
  "webhook_start": { "main": [["init_pipeline"]] },
  "init_pipeline": { "main": [["db_dataset_stats"]] },
  "db_dataset_stats": { "main": [["check_dataset"]] },
  "check_dataset": { "main": [["if_dataset_ready"]] },
  "if_dataset_ready": { "main": [["trigger_training"], ["emit_blocked"]] },
  "trigger_training": { "main": [["wait_training"]] },
  "wait_training": { "main": [["check_training"]] },
  "check_training": { "main": [["if_training_done"]] },
  "if_training_done": { "main": [["trigger_evaluation"], ["wait_training"]] },
  "trigger_evaluation": { "main": [["wait_evaluation"]] },
  "wait_evaluation": { "main": [["if_auto_deploy"]] },
  "if_auto_deploy": { "main": [["trigger_deployment"], ["emit_complete"]] },
  "trigger_deployment": { "main": [["emit_complete"]] }
}
```

---

## Usage Example

### Start Pipeline (Manual Deploy)

```bash
curl -X POST http://localhost:5678/webhook/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "config": "fer_finetune/specs/resnet50_emotion_2cls.yaml",
    "auto_deploy": false
  }'
```

### Start Pipeline (Auto Deploy)

```bash
curl -X POST http://localhost:5678/webhook/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "auto_deploy": true,
    "correlation_id": "nightly-build-001"
  }'
```

### Expected Response

```json
{
  "status": "accepted",
  "pipeline_id": "ml_pipeline_20251129150000",
  "message": "Pipeline started"
}
```
