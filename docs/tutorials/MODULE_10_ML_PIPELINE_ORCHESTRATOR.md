# Module 10: ML Pipeline Orchestrator — End-to-End Automation

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~5 hours  
**Prerequisites**: Completed Modules 0-9

---

## Learning Objectives

By the end of this module, you will:
1. Implement **workflow-to-workflow calls** (agent orchestration)
2. Build an **end-to-end ML pipeline** coordinator
3. Configure **auto-deploy mode** for fully automated pipelines
4. Manage **pipeline state** across multiple agents
5. Handle **pipeline blocking** when prerequisites aren't met

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Agent orchestration** | HTTP to n8n webhooks | Coordinate multiple workflows |
| **Pipeline state** | Data passed between calls | Track progress |
| **Auto-deploy mode** | Boolean flag | Full automation option |
| **Dataset readiness** | Pre-flight checks | Prevent failed runs |
| **Status polling** | Wait + HTTP loop | Monitor sub-workflows |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Webhook: pipeline.start | n8n webhook | ⬜ (native) |
| 2 | Code: init.pipeline | JavaScript | ⬜ (native) |
| 3 | Postgres: dataset.stats | PostgreSQL query | ⬜ |
| 4 | Code: check.dataset | JavaScript | ⬜ (native) |
| 5 | IF: dataset.ready? | n8n conditional | ⬜ (native) |
| 6 | HTTP: trigger.training | Agent 05 webhook | ⬜ |
| 7 | Wait: training | n8n Wait | ⬜ (native) |
| 8 | HTTP: check.training_status | Gateway status API | ⬜ |
| 9 | IF: training.done? | n8n conditional | ⬜ (native) |
| 10 | HTTP: trigger.evaluation | Agent 06 webhook | ⬜ |
| 11 | Wait: evaluation | n8n Wait | ⬜ (native) |
| 12 | IF: auto_deploy? | n8n conditional | ⬜ (native) |
| 13 | HTTP: trigger.deployment | Agent 07 webhook | ⬜ |
| 14-15 | HTTP: emit.* | Gateway events | ⬜ |

---

### Verification Procedures

#### Test 1: Agent Webhooks Available

Verify the agent webhooks from previous modules are registered:

```bash
# Training Agent
curl -X POST http://10.0.4.130:5678/webhook/agent/training/resnet50/start \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Evaluation Agent  
curl -X POST http://10.0.4.130:5678/webhook/agent/evaluation/resnet50/start \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Deployment Agent
curl -X POST http://10.0.4.130:5678/webhook/agent/deployment/resnet50/start \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

**Status**: ⬜ → [ ] Complete

---

#### Test 2: Dataset Statistics Query

```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test
FROM video;
```

**Status**: ⬜ → [ ] Complete

---

## Part 1: Understanding Pipeline Orchestration

### The Complete ML Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ML PIPELINE STAGES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. DATASET CHECK                                                       │
│     ├── Train: ≥50 per class (happy, sad)                               │
│     └── Test: ≥20 per class                                             │
│                                                                         │
│  2. TRAINING (Agent 05)                                                 │
│     ├── Fine-tune ResNet-50                                             │
│     ├── Gate A validation                                               │
│     └── Export ONNX                                                     │
│                                                                         │
│  3. EVALUATION (Agent 06)                                               │
│     ├── Run on test set                                                 │
│     ├── Compute metrics (F1, ECE, Brier)                                │
│     └── Gate A re-validation                                            │
│                                                                         │
│  4. DEPLOYMENT (Agent 07) [if auto_deploy or manual trigger]            │
│     ├── Transfer to Jetson                                              │
│     ├── TensorRT conversion                                             │
│     ├── Gate B validation                                               │
│     └── Rollback if needed                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why an Orchestrator?

Without orchestration:
- Manual trigger of each agent
- No coordination between stages
- No pipeline-level state tracking

With orchestration:
- Single trigger starts entire pipeline
- Automatic progression through stages
- Centralized state and error handling

### Workflow Architecture

```
webhook_start
       │
       ▼
init_pipeline (generate pipeline_id)
       │
       ▼
dataset_stats (query both splits)
       │
       ▼
check_dataset (validate counts)
       │
       ▼
if_dataset_ready
  │         │
[True]   [False]
  │         │
  │         └──► emit_blocked
  │
  ▼
trigger_training (Agent 05)
       │
       ▼
wait_training ◄─────────────┐
       │                    │
       ▼                    │
check_training_status       │
       │                    │
       ▼                    │
if_training_done ───────────┤
       │               [False]
    [True]
       │
       ▼
trigger_evaluation (Agent 06)
       │
       ▼
wait_evaluation
       │
       ▼
if_auto_deploy
  │         │
[True]   [False]
  │         │
  ▼         │
trigger_deployment (Agent 07)
  │         │
  └────┬────┘
       │
       ▼
emit_complete
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `ML Pipeline Orchestrator — ResNet-50 (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Pipeline Start Webhook

**Node Name**: `Webhook: pipeline.start`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `ml/pipeline/start` |
| Response Mode | `When Last Node Finishes` |
| Response Code | `202` |

**Expected Input**:
```json
{
  "config": "fer_finetune/specs/resnet50_emotion_2cls.yaml",
  "auto_deploy": false,
  "correlation_id": "optional-id"
}
```

---

### Step 3: Add Pipeline Initialization

**Node Name**: `Code: init.pipeline`

```javascript
// Initialize pipeline run
const timestamp = new Date().toISOString()
  .replace(/[-:T]/g, '')
  .slice(0, 14);
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
    correlation_id: $json.correlation_id || pipelineId,
    started_at: new Date().toISOString()
  }
}];
```

---

### Step 4: Add Dataset Statistics Query

**Node Name**: `Postgres: dataset.stats`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL**:
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train,
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test,
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test
FROM video;
```

---

### Step 5: Add Dataset Validation

**Node Name**: `Code: check.dataset`

```javascript
// Check dataset readiness
const stats = $json;
const pipeline = $('Code: init.pipeline').item.json;
const minTrainPerClass = 50;
const minTestPerClass = 20;

const trainReady = Math.min(stats.happy_train, stats.sad_train) >= minTrainPerClass;
const testReady = Math.min(stats.happy_test, stats.sad_test) >= minTestPerClass;

// Check balance (< 20% imbalance)
const trainImbalance = Math.abs(stats.happy_train - stats.sad_train) / 
                       Math.max(stats.happy_train, stats.sad_train);
const balanced = trainImbalance < 0.2;

return [{
  json: {
    ...pipeline,
    dataset_stats: stats,
    dataset_ready: trainReady && testReady,
    train_ready: trainReady,
    test_ready: testReady,
    balanced: balanced,
    current_stage: (trainReady && testReady) ? 'training' : 'blocked'
  }
}];
```

---

### Step 6: Add Dataset Ready Check

**Node Name**: `IF: dataset.ready?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.dataset_ready}}` |
| Operation | `Is True` |

---

### Step 7: Add Blocked Event

**Node Name**: `HTTP: emit.blocked`

Connect: IF dataset.ready? (False branch) → emit.blocked

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |

**Body**:
```json
{
  "event_type": "pipeline.blocked",
  "pipeline_id": "={{$json.pipeline_id}}",
  "reason": "Insufficient training data",
  "dataset_stats": "={{JSON.stringify($json.dataset_stats)}}",
  "requirements": {"train": 50, "test": 20}
}
```

---

### Step 8: Add Training Trigger

**Node Name**: `HTTP: trigger.training`

Connect: IF dataset.ready? (True branch) → trigger.training

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `http://localhost:5678/webhook/agent/training/resnet50/start` |

**Body**:
```json
{
  "pipeline_id": "={{$json.pipeline_id}}",
  "correlation_id": "={{$json.correlation_id}}",
  "config": "={{$json.config}}",
  "dataset_hash": "={{$json.dataset_stats.happy_train + '_' + $json.dataset_stats.sad_train}}"
}
```

**Note**: Using `localhost` because orchestrator runs on same n8n instance.

---

### Step 9: Add Training Wait

**Node Name**: `Wait: training`

| Parameter | Value |
|-----------|-------|
| Amount | `10` |
| Unit | `Minutes` |

---

### Step 10: Add Training Status Check

**Node Name**: `HTTP: check.training_status`

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/training/status/{{$json.pipeline_id}}` |

**⚠️ TBD**: This endpoint may need to be implemented. For testing, you can:
1. Implement the endpoint
2. Check for results.json via SSH
3. Use a mock response

---

### Step 11: Add Training Done Check

**Node Name**: `IF: training.done?`

| Parameter | Value |
|-----------|-------|
| Condition | String |
| Value 1 | `={{$json.status}}` |
| Operation | `Contains` |
| Value 2 | `completed` |

**Outputs**:
- True → trigger.evaluation
- False → Wait: training (loop back)

---

### Step 12: Add Evaluation Trigger

**Node Name**: `HTTP: trigger.evaluation`

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `http://localhost:5678/webhook/agent/evaluation/resnet50/start` |

**Body**:
```json
{
  "pipeline_id": "={{$json.pipeline_id}}",
  "run_id": "={{$json.run_id}}",
  "correlation_id": "={{$json.correlation_id}}"
}
```

---

### Step 13: Add Evaluation Wait

**Node Name**: `Wait: evaluation`

| Parameter | Value |
|-----------|-------|
| Amount | `5` |
| Unit | `Minutes` |

---

### Step 14: Add Auto-Deploy Check

**Node Name**: `IF: auto_deploy?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$('Code: init.pipeline').item.json.auto_deploy && $json.gate_a_passed}}` |
| Operation | `Is True` |

**Logic**: Auto-deploy ONLY if:
1. `auto_deploy: true` was requested
2. Gate A passed

---

### Step 15: Add Deployment Trigger

**Node Name**: `HTTP: trigger.deployment`

Connect: IF auto_deploy? (True branch) → trigger.deployment

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `http://localhost:5678/webhook/agent/deployment/resnet50/start` |

**Body**:
```json
{
  "pipeline_id": "={{$json.pipeline_id}}",
  "run_id": "={{$json.run_id}}",
  "gate_a_passed": "={{$json.gate_a_passed}}",
  "onnx_path": "={{$json.onnx_path}}",
  "correlation_id": "={{$json.correlation_id}}"
}
```

---

### Step 16: Add Pipeline Complete Event

**Node Name**: `HTTP: emit.complete`

Connect BOTH paths (with and without deployment) to this node.

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |

**Body**:
```json
{
  "event_type": "pipeline.completed",
  "pipeline_id": "={{$('Code: init.pipeline').item.json.pipeline_id}}",
  "model": "resnet50-affectnet-raf-db",
  "final_stage": "={{$json.current_stage || 'evaluation'}}",
  "gate_a_passed": "={{$json.gate_a_passed}}",
  "deployed": "={{$json.deployed || false}}",
  "duration_minutes": "={{Math.round((Date.now() - new Date($('Code: init.pipeline').item.json.started_at)) / 60000)}}"
}
```

---

## Part 3: Auto-Deploy Mode

### When to Use Auto-Deploy

| Mode | Use Case |
|------|----------|
| `auto_deploy: false` | Development, manual review |
| `auto_deploy: true` | Nightly builds, CI/CD integration |

### Auto-Deploy Flow

```
auto_deploy: true
       │
       ▼
Training completes
       │
       ▼
Evaluation completes
       │
       ▼
Gate A passed? ──[No]──► Stop (no deployment)
       │
    [Yes]
       │
       ▼
Trigger deployment automatically
       │
       ▼
Gate B passed? ──[No]──► Rollback
       │
    [Yes]
       │
       ▼
Pipeline complete (model deployed)
```

### Usage Examples

**Manual Mode (default)**:
```bash
curl -X POST http://10.0.4.130:5678/webhook/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "config": "fer_finetune/specs/resnet50_emotion_2cls.yaml"
  }'
```

**Auto-Deploy Mode**:
```bash
curl -X POST http://10.0.4.130:5678/webhook/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "auto_deploy": true,
    "correlation_id": "nightly-build-001"
  }'
```

---

## Part 4: Testing

### Test 1: Insufficient Data

Ensure you have < 50 samples per class, then trigger:

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected**: Pipeline blocks with `insufficient_data` event.

### Test 2: Full Pipeline (Mock)

For testing without actual training:
1. Set Wait nodes to 30 seconds instead of minutes
2. Create mock status responses
3. Observe agent triggers in execution history

### Test 3: Auto-Deploy Flag

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"auto_deploy": true}'
```

**Expected**: Deployment agent triggered after evaluation (if Gate A passes).

---

## Module 10 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Agent orchestration | HTTP to n8n webhooks |
| Pipeline state | Pass data between triggers |
| Auto-deploy mode | Boolean flag + Gate A check |
| Status polling | Wait → Check → IF → Loop |
| Blocked handling | Emit event, stop pipeline |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: pipeline.start | Webhook | Entry point |
| 2 | Code: init.pipeline | Code | Generate pipeline ID |
| 3 | Postgres: dataset.stats | Postgres | Get counts |
| 4 | Code: check.dataset | Code | Validate readiness |
| 5 | IF: dataset.ready? | IF | Gate dataset |
| 6 | HTTP: trigger.training | HTTP Request | Call Agent 05 |
| 7 | Wait: training | Wait | Polling interval |
| 8 | HTTP: check.training_status | HTTP Request | Poll status |
| 9 | IF: training.done? | IF | Completion check |
| 10 | HTTP: trigger.evaluation | HTTP Request | Call Agent 06 |
| 11 | Wait: evaluation | Wait | Processing time |
| 12 | IF: auto_deploy? | IF | Deployment decision |
| 13 | HTTP: trigger.deployment | HTTP Request | Call Agent 07 |
| 14-15 | HTTP: emit.* | HTTP Request | Events |

### Pipeline Flow Summary

```
Start → Check Dataset → [Ready?]
                          │
               [No] → Emit Blocked
               [Yes] → Training → [Done?]
                                    │
                         [No] → Wait → Poll
                         [Yes] → Evaluation → [Auto-Deploy & Gate A?]
                                                     │
                                      [No] → Complete (no deploy)
                                      [Yes] → Deployment → Complete
```

---

## Next Steps

Proceed to **Module 11: Error Handling & Recovery** where you'll learn:
- **Global error workflows**
- **Retry patterns** with exponential backoff
- **Dead letter queues** for failed tasks
- **Alerting on failures**

---

*Module 10 Complete — Proceed to Module 11: Error Handling & Recovery*
