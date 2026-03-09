# MODULE 06 -- Training Orchestrator (EfficientNet-B0)

**Duration:** ~5 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`
**Nodes to Wire:** 15
**Prerequisite:** MODULE 05 complete
**Outcome:** A workflow that validates dataset balance, creates MLflow experiments, launches training via SSH, polls for completion, and enforces Gate A quality thresholds

---

## 6.1 What Does the Training Orchestrator Do?

This is the most complex agent so far. It manages the full lifecycle of an EfficientNet-B0 training run:

1. Validates that the training set has >= 50 samples per class
2. Creates an MLflow experiment run for tracking
3. Launches training on Ubuntu 1 via SSH (long-running process)
4. Polls training status every 5 minutes until completion
5. Parses results and validates Gate A thresholds
6. Logs gate results to MLflow
7. Emits training completion or failure events

### Gate A Quality Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Macro F1 | >= 0.84 | Average F1 across all 3 classes |
| Balanced Accuracy | >= 0.85 | Accuracy adjusted for class imbalance |
| ECE | <= 0.08 | Expected Calibration Error (lower is better) |
| Brier Score | <= 0.16 | Probability accuracy (lower is better) |

---

## 6.2 Pre-Wiring Checklist

- [ ] **Training data:** >= 50 videos per class (happy, sad, neutral) in `train` split
- [ ] **MLflow** running at `http://10.0.4.130:5000`:
  ```bash
  curl -s http://10.0.4.130:5000/api/2.0/mlflow/experiments/list | jq .
  ```
- [ ] **Training script** exists on Ubuntu 1:
  ```bash
  ssh rusty_admin@10.0.4.130 "ls trainer/run_efficientnet_pipeline.py"
  ```
- [ ] **Gateway** training status endpoint works:
  ```bash
  curl -s http://10.0.4.140:8000/api/training/status/test | jq .
  ```

---

## 6.3 Create the Workflow

1. Name: `Agent 5 -- Training Orchestrator EfficientNet-B0 (Reachy 08.4.2)`
2. Tags: `agent`, `training`, `efficientnet`, `ml-v1`

---

## 6.4 Wire Node 1: webhook_training

1. Add a **Webhook** → rename to `webhook_training`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `agent/training/efficientnet/start` |
| **Response Mode** | `On Received` |
| **Response Code** | `202` |

We return 202 immediately because training is a long-running process (minutes to hours).

---

## 6.5 Wire Node 2: db_check_balance

1. Add a **Postgres** node → rename to `db_check_balance`
2. Configure:

```sql
SELECT
  COUNT(*) FILTER (WHERE label = 'happy') AS happy_count,
  COUNT(*) FILTER (WHERE label = 'sad') AS sad_count,
  COUNT(*) FILTER (WHERE label = 'neutral') AS neutral_count
FROM video
WHERE split = 'train';
```

---

## 6.6 Wire Node 3: if_sufficient_data

1. Add an **IF** node → rename to `if_sufficient_data`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ Math.min($json.happy_count, $json.sad_count, $json.neutral_count) }}` |
| **Operation** | `is greater than or equal to` |
| **Value 2** | `50` |

### Why 50 Per Class?

EfficientNet-B0 is a pre-trained model (on VGGFace2 + AffectNet), so it needs relatively little fine-tuning data. However, 50 per class is the minimum for statistically meaningful training with 3-fold cross-validation.

---

## 6.7 Wire Node 4: mlflow_create_run

Connected to the **true** output of `if_sufficient_data`.

1. Add an **HTTP Request** node → rename to `mlflow_create_run`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MLFLOW_URL }}/api/2.0/mlflow/runs/create` |
| **Body Content Type** | `JSON` |

Body (raw JSON):

```json
{
  "experiment_id": "1",
  "tags": [
    {"key": "model", "value": "efficientnet-b0-hsemotion"},
    {"key": "dataset_hash", "value": "{{ $('db_check_balance').item.json.happy_count }}_{{ $('db_check_balance').item.json.sad_count }}_{{ $('db_check_balance').item.json.neutral_count }}"},
    {"key": "correlation_id", "value": "trn-{{ Date.now() }}"}
  ]
}
```

### What Is MLflow?

MLflow is an ML experiment tracker. It records metrics, parameters, and artifacts for each training run. Creating a "run" gives us a `run_id` that we use to track this specific training session.

---

## 6.8 Wire Node 5: prepare_training

1. Add a **Code** node → rename to `prepare_training`
2. Code:

```javascript
const mlflowResponse = $input.first().json;
const run_id = mlflowResponse.run.info.run_id;

const config_path = 'trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml';
const output_dir = `/media/rusty_admin/project_data/ml_models/efficientnet/${run_id}`;
const model_storage_path = output_dir + '/best_model.onnx';

const balance = $('db_check_balance').first().json;

return [{
  json: {
    run_id,
    config_path,
    output_dir,
    model_storage_path,
    happy_count: balance.happy_count,
    sad_count: balance.sad_count,
    neutral_count: balance.neutral_count,
    gateway_base: $env.GATEWAY_BASE_URL,
    attempt: 0
  }
}];
```

---

## 6.9 Wire Node 6: ssh_start_training

1. Add an **SSH** node → rename to `ssh_start_training`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Ubuntu1` |
| **Command** | *(see below)* |

```bash
cd /home/rusty_admin/project-reachy-emotion && \
nohup python trainer/run_efficientnet_pipeline.py \
  --config {{ $json.config_path }} \
  --run-id {{ $json.run_id }} \
  --output-dir {{ $json.output_dir }} \
  --gateway-base {{ $json.gateway_base }} \
  --strict-contract-updates \
  > /tmp/training_{{ $json.run_id }}.log 2>&1 &
echo "Training started with run_id={{ $json.run_id }}"
```

### Key Points

- **`nohup ... &`** -- Runs the training in the background. The SSH command returns immediately, but training continues on the server.
- **`> /tmp/training_*.log 2>&1`** -- Redirects all output to a log file for debugging.
- **`--strict-contract-updates`** -- The training script posts status updates to the Gateway API, which we poll in the next steps.

---

## 6.10 Wire Node 7: wait_poll

1. Add a **Wait** node → rename to `wait_poll`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Amount** | `5` |
| **Unit** | `Minutes` |

Training typically takes 15-60 minutes depending on dataset size and GPU.

---

## 6.11 Wire Node 8: check_status

1. Add an **HTTP Request** node → rename to `check_status`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/training/status/{{ $('prepare_training').item.json.run_id }}` |

The training script reports its status to the Gateway, and we poll that endpoint.

---

## 6.12 Wire Node 9: parse_results

1. Add a **Code** node → rename to `parse_results`
2. Code:

```javascript
const status = $input.first().json;

const result = {
  run_id: $('prepare_training').first().json.run_id,
  status: status.status || 'unknown',
  metrics: {
    f1_macro: status.metrics?.f1_macro || 0,
    balanced_accuracy: status.metrics?.balanced_accuracy || 0,
    ece: status.metrics?.ece || 1.0,
    brier: status.metrics?.brier || 1.0
  },
  epochs_completed: status.epochs_completed || 0,
  error_message: status.error_message || null,
  onnx_path: status.onnx_path || null
};

// Gate A validation
result.gate_a = {
  f1_pass: result.metrics.f1_macro >= 0.84,
  accuracy_pass: result.metrics.balanced_accuracy >= 0.85,
  ece_pass: result.metrics.ece <= 0.08,
  brier_pass: result.metrics.brier <= 0.16,
  passed: false
};
result.gate_a.passed =
  result.gate_a.f1_pass &&
  result.gate_a.accuracy_pass &&
  result.gate_a.ece_pass &&
  result.gate_a.brier_pass;

return [{ json: result }];
```

---

## 6.13 Wire Node 10: if_done

1. Add an **IF** node → rename to `if_done`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.status }}` |
| **Operation** | `contains` |
| **Value 2** | `completed` |

**True output** → training is done → check Gate A
**False output** → training still running → loop back to `wait_poll`

### Connect the Polling Loop

Draw a connection from `if_done` **false output** → `wait_poll`. This creates the 5-minute polling loop.

---

## 6.14 Wire Node 11: gate_a_check

Connected to the **true** output of `if_done`.

1. Add an **IF** node → rename to `gate_a_check`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.gate_a.passed }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 6.15 Wire Node 12: mlflow_log_gate

Connected to the **true** output of `gate_a_check`.

1. Add an **HTTP Request** node → rename to `mlflow_log_gate`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MLFLOW_URL }}/api/2.0/mlflow/runs/log-metric` |

Body:

```json
{
  "run_id": "{{ $json.run_id }}",
  "key": "gate_a_passed",
  "value": 1.0,
  "timestamp": {{ Date.now() }}
}
```

---

## 6.16 Wire Node 13: emit_completed

1. Add an **HTTP Request** node → rename to `emit_completed`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/events/training` |

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `training.completed` |
| `run_id` | `{{ $json.run_id }}` |
| `model` | `efficientnet-b0-hsemotion` |
| `gate_a_passed` | `{{ $json.gate_a.passed }}` |
| `f1_macro` | `{{ $json.metrics.f1_macro }}` |
| `onnx_path` | `{{ $json.onnx_path }}` |

---

## 6.17 Wire Node 14: emit_gate_failed

Connected to the **false** output of `gate_a_check`.

1. Add an **HTTP Request** node → rename to `emit_gate_failed`
2. Configure similarly to `emit_completed` but with:

| Field | Value |
|-------|-------|
| `event_type` | `training.gate_failed` |
| `gate_a_details` | `{{ JSON.stringify($json.gate_a) }}` |

---

## 6.18 Wire Node 15: emit_insufficient

Connected to the **false** output of `if_sufficient_data` (back at node 3).

1. Add an **HTTP Request** node → rename to `emit_insufficient`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/events/training` |

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `training.insufficient_data` |
| `happy_count` | `{{ $('db_check_balance').item.json.happy_count }}` |
| `sad_count` | `{{ $('db_check_balance').item.json.sad_count }}` |
| `neutral_count` | `{{ $('db_check_balance').item.json.neutral_count }}` |
| `minimum_required` | `50` |

---

## 6.19 Final Connection Map

```
webhook_training ──► db_check_balance ──► if_sufficient_data
                                                │
                             [insufficient]     │    [sufficient]
                                  │             │
                                  ▼             ▼
                          emit_insufficient    mlflow_create_run
                                                │
                                                ▼
                                          prepare_training
                                                │
                                                ▼
                                         ssh_start_training
                                                │
                                                ▼
                              ┌──────── wait_poll ◄──────────┐
                              │            │                  │
                              │            ▼                  │
                              │       check_status            │
                              │            │                  │
                              │            ▼                  │
                              │       parse_results           │
                              │            │                  │
                              │            ▼                  │
                              │         if_done               │
                              │      [true]   [false]─────────┘
                              │         │
                              │         ▼
                              │     gate_a_check
                              │    [true]    [false]
                              │      │          │
                              │      ▼          ▼
                              │ mlflow_log   emit_gate_failed
                              │   _gate
                              │      │
                              │      ▼
                              │ emit_completed
                              └──────────────────
```

---

## 6.20 Testing

### Test with Sufficient Data

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/agent/training/efficientnet/start \
  -H "Content-Type: application/json" \
  -d '{"model": "efficientnet-b0-hsemotion", "auto_deploy": false}'
```

### Test with Insufficient Data

If you have fewer than 50 samples per class, the workflow should immediately emit `training.insufficient_data`.

### Monitor Training Progress

Watch the execution in n8n -- you'll see the polling loop cycle every 5 minutes.

---

## 6.21 Key Concepts Learned

- **Long-running process management** via SSH with `nohup`
- **5-minute polling loop** (Wait + HTTP + IF + loop back)
- **MLflow integration** for experiment tracking
- **Gate A validation** with 4 quality thresholds
- **Multiple exit paths** (insufficient data, gate pass, gate fail)
- **Cross-node references** spanning many steps deep

---

*Previous: [MODULE 05 -- Privacy Agent](MODULE_05_PRIVACY_AGENT.md)*
*Next: [MODULE 07 -- Evaluation Agent](MODULE_07_EVALUATION_AGENT.md)*
