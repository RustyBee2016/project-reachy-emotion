# MODULE 10 -- ML Pipeline Orchestrator

**Duration:** ~5 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`
**Nodes to Wire:** 15
**Prerequisite:** MODULES 06-08 complete (the orchestrator calls Agents 5, 6, and 7)
**Outcome:** An end-to-end orchestrator that validates dataset readiness, then triggers training, evaluation, and deployment agents in sequence

---

## 10.1 What Does the ML Pipeline Orchestrator Do?

This is the **meta-workflow** -- it orchestrates the other agents. Instead of manually triggering training → evaluation → deployment, the Orchestrator:

1. Validates dataset readiness (both train and test splits)
2. Triggers Agent 5 (Training Orchestrator) via HTTP
3. Polls training status every 10 minutes
4. On completion, triggers Agent 6 (Evaluation Agent)
5. Waits for evaluation
6. If `auto_deploy=true` AND Gate A passed → triggers Agent 7 (Deployment Agent)
7. Emits `pipeline.completed` event

### Workflow-to-Workflow Pattern

```
ML PIPELINE ORCHESTRATOR
        │
        ├──► Agent 5 (Training)    via POST /webhook/agent/training/efficientnet/start
        │         ⬇ (poll 10 min)
        ├──► Agent 6 (Evaluation)  via POST /webhook/agent/evaluation/efficientnet/start
        │         ⬇ (wait 5 min)
        └──► Agent 7 (Deployment)  via POST /webhook/agent/deployment/efficientnet/start
```

---

## 10.2 Pre-Wiring Checklist

- [ ] **Agent 5** (Training) is active and working
- [ ] **Agent 6** (Evaluation) is active and working
- [ ] **Agent 7** (Deployment) is active and working
- [ ] All three agents respond to their webhook endpoints
- [ ] **Dataset** has sufficient data in both train (>=50/class) and test (>=20/class) splits

---

## 10.3 Create the Workflow

1. Name: `ML Pipeline Orchestrator -- EfficientNet-B0 (Reachy 08.4.2)`
2. Tags: `orchestrator`, `ml-pipeline`, `efficientnet`, `ml-v1`

---

## 10.4 Wire Node 1: webhook_start

1. Add a **Webhook** → rename to `webhook_start`

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `ml/pipeline/start` |
| **Response Mode** | `On Received` |
| **Response Code** | `202` |

---

## 10.5 Wire Node 2: init_pipeline

1. Add a **Code** node → rename to `init_pipeline`
2. Code:

```javascript
const body = $input.first().json.body || {};

const pipeline_id = 'pipe-' + Date.now() + '-' +
  Math.random().toString(36).substr(2, 6);

return [{
  json: {
    pipeline_id,
    model: body.model || 'efficientnet-b0-hsemotion',
    config_path: body.config_path ||
      'trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml',
    auto_deploy: body.auto_deploy === true,
    stages: ['dataset_check', 'training', 'evaluation', 'deployment'],
    current_stage: 'dataset_check',
    started_at: new Date().toISOString(),
    correlation_id: 'orch-' + Date.now()
  }
}];
```

---

## 10.6 Wire Node 3: db_dataset_stats

1. Add a **Postgres** node → rename to `db_dataset_stats`
2. Query:

```sql
SELECT
  split,
  COUNT(*) FILTER (WHERE label = 'happy') AS happy,
  COUNT(*) FILTER (WHERE label = 'sad') AS sad,
  COUNT(*) FILTER (WHERE label = 'neutral') AS neutral,
  COUNT(*) AS total
FROM video
WHERE split IN ('train', 'test')
GROUP BY split
ORDER BY split;
```

This returns two rows: one for `test` and one for `train`.

---

## 10.7 Wire Node 4: check_dataset

1. Add a **Code** node → rename to `check_dataset`
2. Code:

```javascript
const rows = $input.all().map(i => i.json);

const train = rows.find(r => r.split === 'train') ||
  { happy: 0, sad: 0, neutral: 0, total: 0 };
const test = rows.find(r => r.split === 'test') ||
  { happy: 0, sad: 0, neutral: 0, total: 0 };

const trainMin = Math.min(train.happy, train.sad, train.neutral);
const testMin = Math.min(test.happy, test.sad, test.neutral);

const trainReady = trainMin >= 50;
const testReady = testMin >= 20;

// Check class imbalance (max - min) / max < 0.2
const trainMax = Math.max(train.happy, train.sad, train.neutral);
const balanced = trainMax > 0 ? (trainMax - trainMin) / trainMax < 0.2 : false;

const pipeline = $('init_pipeline').first().json;

// Compute dataset hash for tracking
const dataset_hash = `h${train.happy}s${train.sad}n${train.neutral}_` +
                     `h${test.happy}s${test.sad}n${test.neutral}`;

return [{
  json: {
    ...pipeline,
    train_stats: train,
    test_stats: test,
    trainReady,
    testReady,
    balanced,
    dataset_ready: trainReady && testReady,
    dataset_hash
  }
}];
```

---

## 10.8 Wire Node 5: if_dataset_ready

1. Add an **IF** node → rename to `if_dataset_ready`

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.dataset_ready }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 10.9 Wire Node 6: trigger_training

Connected to **true** output. This calls Agent 5's webhook.

1. Add an **HTTP Request** node → rename to `trigger_training`

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/webhook/agent/training/efficientnet/start` |

Body fields:

| Field | Value |
|-------|-------|
| `pipeline_id` | `{{ $json.pipeline_id }}` |
| `correlation_id` | `{{ $json.correlation_id }}` |
| `model` | `{{ $json.model }}` |
| `config_path` | `{{ $json.config_path }}` |
| `dataset_hash` | `{{ $json.dataset_hash }}` |

### URL Note

The URL uses the n8n host (not Gateway) because we're calling another n8n workflow's webhook. If n8n is at `http://10.0.4.130:5678`, the full URL would be:
```
http://10.0.4.130:5678/webhook/agent/training/efficientnet/start
```

You may need to set an `N8N_HOST` environment variable or hardcode the URL.

---

## 10.10 Wire Node 7: wait_training

1. Add a **Wait** node → rename to `wait_training`

| Parameter | Value |
|-----------|-------|
| **Amount** | `10` |
| **Unit** | `Minutes` |

Training takes 15-60 minutes. We poll every 10 minutes.

---

## 10.11 Wire Node 8: check_training

1. Add an **HTTP Request** node → rename to `check_training`

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/training/status/{{ $('init_pipeline').item.json.pipeline_id }}` |

---

## 10.12 Wire Node 9: if_training_done

1. Add an **IF** node → rename to `if_training_done`

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.status }}` |
| **Operation** | `contains` |
| **Value 2** | `completed` |

**False output** → loop back to `wait_training` (polling loop)

---

## 10.13 Wire Node 10: trigger_evaluation

Connected to **true** output of `if_training_done`.

1. Add an **HTTP Request** node → rename to `trigger_evaluation`

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `http://10.0.4.130:5678/webhook/agent/evaluation/efficientnet/start` |

Body fields:

| Field | Value |
|-------|-------|
| `pipeline_id` | `{{ $('init_pipeline').item.json.pipeline_id }}` |
| `run_id` | `{{ $json.run_id }}` |
| `checkpoint_path` | `{{ $json.checkpoint_path }}` |

---

## 10.14 Wire Node 11: wait_evaluation

1. Add a **Wait** node → rename to `wait_evaluation`

| Parameter | Value |
|-----------|-------|
| **Amount** | `5` |
| **Unit** | `Minutes` |

Evaluation is faster than training (2-5 minutes), so we wait 5 minutes.

---

## 10.15 Wire Node 12: if_auto_deploy

1. Add an **IF** node → rename to `if_auto_deploy`

This checks **two conditions**: auto_deploy is enabled AND Gate A passed.

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $('check_dataset').item.json.auto_deploy && $json.gate_a_passed }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 10.16 Wire Node 13: trigger_deployment

Connected to **true** output of `if_auto_deploy`.

1. Add an **HTTP Request** node → rename to `trigger_deployment`

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `http://10.0.4.130:5678/webhook/agent/deployment/efficientnet/start` |

Body fields:

| Field | Value |
|-------|-------|
| `pipeline_id` | `{{ $('init_pipeline').item.json.pipeline_id }}` |
| `run_id` | `{{ $json.run_id }}` |
| `checkpoint_path` | `{{ $json.checkpoint_path }}` |
| `gate_a_passed` | `true` |

---

## 10.17 Wire Node 14: emit_complete

**Both** `trigger_deployment` output AND `if_auto_deploy` **false** output connect here.

1. Add an **HTTP Request** node → rename to `emit_complete`

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `pipeline.completed` |
| `pipeline_id` | `{{ $('init_pipeline').item.json.pipeline_id }}` |
| `model` | `{{ $('init_pipeline').item.json.model }}` |
| `auto_deployed` | `{{ $('check_dataset').item.json.auto_deploy }}` |
| `duration_sec` | `{{ Math.floor((Date.now() - new Date($('init_pipeline').item.json.started_at).getTime()) / 1000) }}` |

---

## 10.18 Wire Node 15: emit_blocked

Connected to **false** output of `if_dataset_ready` (node 5).

1. Add an **HTTP Request** node → rename to `emit_blocked`

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `pipeline.blocked` |
| `pipeline_id` | `{{ $('init_pipeline').item.json.pipeline_id }}` |
| `reason` | `Insufficient training data` |
| `train_stats` | `{{ JSON.stringify($('check_dataset').item.json.train_stats) }}` |
| `test_stats` | `{{ JSON.stringify($('check_dataset').item.json.test_stats) }}` |

---

## 10.19 Final Connection Map

```
webhook_start ──► init_pipeline ──► db_dataset_stats ──► check_dataset ──► if_dataset_ready
                                                                                │
                                                         [not ready]           │    [ready]
                                                              │                │
                                                              ▼                ▼
                                                        emit_blocked     trigger_training
                                                                               │
                                                                               ▼
                                                              ┌────── wait_training ◄──┐
                                                              │            │            │
                                                              │            ▼            │
                                                              │      check_training     │
                                                              │            │            │
                                                              │            ▼            │
                                                              │    if_training_done     │
                                                              │    [true]    [false]────┘
                                                              │       │
                                                              │       ▼
                                                              │  trigger_evaluation
                                                              │       │
                                                              │       ▼
                                                              │  wait_evaluation
                                                              │       │
                                                              │       ▼
                                                              │  if_auto_deploy
                                                              │  [true]     [false]
                                                              │    │            │
                                                              │    ▼            │
                                                              │ trigger_       │
                                                              │ deployment     │
                                                              │    │           │
                                                              │    └─────┬─────┘
                                                              │          ▼
                                                              │    emit_complete
                                                              └───────────────────
```

---

## 10.20 Testing

### Full Pipeline Test

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "model": "efficientnet-b0-hsemotion",
    "auto_deploy": false
  }'
```

### Auto-Deploy Test

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "model": "efficientnet-b0-hsemotion",
    "auto_deploy": true
  }'
```

### Insufficient Data Test

Ensure < 50 training samples per class, then trigger. Should immediately emit `pipeline.blocked`.

---

## 10.21 Key Concepts Learned

- **Workflow-to-Workflow orchestration** via HTTP webhooks
- **Multi-stage pipeline** with sequential agent triggers
- **Dual polling loops** (training 10 min, evaluation 5 min)
- **Conditional deployment** based on `auto_deploy` flag AND Gate A pass
- **Pipeline tracking** with `pipeline_id` for correlation across agents
- **Dataset validation** for both train and test splits simultaneously
- **Duration tracking** by computing elapsed time from start

---

## 10.22 Congratulations!

You've now wired all 10 workflows in the Reachy agentic AI system:

| Module | Agent | Nodes | Pattern |
|--------|-------|-------|---------|
| 01 | Ingest | 12 | Webhook → Auth → Poll → DB → Event |
| 02 | Labeling | 9 | Webhook → Validate → CTE → Switch → Balance |
| 03 | Promotion | 11 | Two-Phase Approval (Dry-Run + Human Gate) |
| 04 | Reconciler | 9 | Schedule → SSH + DB → Diff → Email |
| 05 | Privacy | 8 | Schedule → Batch Loop → Audit Log |
| 06 | Training | 15 | SSH + MLflow + Poll Loop + Gate A |
| 07 | Evaluation | 12 | SSH + MLflow Batch + Gate A |
| 08 | Deployment | 14 | SCP + TensorRT + Gate B + Rollback |
| 09 | Observability | 6 | Cron → Parallel HTTP → Parse → Store |
| 10 | Orchestrator | 15 | Multi-Agent Sequential Trigger |
| **Total** | | **111** | |

---

*Previous: [MODULE 09 -- Observability Agent](MODULE_09_OBSERVABILITY_AGENT.md)*
*Back to: [Curriculum Index](../CURRICULUM_INDEX.md)*
