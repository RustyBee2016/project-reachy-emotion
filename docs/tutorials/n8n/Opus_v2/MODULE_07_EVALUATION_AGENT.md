# MODULE 07 -- Evaluation Agent (EfficientNet-B0)

**Duration:** ~3 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`
**Nodes to Wire:** 12
**Prerequisite:** MODULE 06 complete
**Outcome:** A workflow that evaluates a trained model on the test set, logs metrics to MLflow, and enforces Gate A thresholds

---

## 7.1 What Does the Evaluation Agent Do?

After training completes (Module 06), the Evaluation Agent runs the trained model against the **test dataset** to validate its quality on unseen data:

1. Checks test set balance (>= 20 samples per class)
2. Runs evaluation via SSH with `--skip-train` flag
3. Parses metrics: F1, accuracy, ECE, Brier score
4. Logs all metrics to MLflow in a batch
5. Validates Gate A thresholds
6. Emits success or failure events

### Training vs. Evaluation

| Aspect | Training (Module 06) | Evaluation (Module 07) |
|--------|---------------------|----------------------|
| Dataset | `train` split | `test` split |
| Min samples | 50/class | 20/class |
| Duration | 15-60 minutes | 2-5 minutes |
| Output | Model weights (.onnx) | Metrics only |
| Script flag | (none) | `--skip-train` |
| Gate A | Same thresholds | Same thresholds |

---

## 7.2 Pre-Wiring Checklist

- [ ] **Test data:** >= 20 videos per class in `test` split
- [ ] **Trained model** checkpoint exists (from Module 06 training run)
- [ ] **MLflow** is running for metric logging

---

## 7.3 Create the Workflow

1. Name: `Agent 6 -- Evaluation Agent EfficientNet-B0 (Reachy 08.4.2)`
2. Tags: `agent`, `evaluation`, `efficientnet`, `ml-v1`

---

## 7.4 Wire Node 1: webhook_eval

1. Add a **Webhook** → rename to `webhook_eval`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `agent/evaluation/efficientnet/start` |
| **Response Mode** | `On Received` |
| **Response Code** | `200` |

---

## 7.5 Wire Node 2: db_check_balance

1. Add a **Postgres** node → rename to `db_check_balance`

```sql
SELECT
  COUNT(*) FILTER (WHERE label = 'happy') AS happy_test,
  COUNT(*) FILTER (WHERE label = 'sad') AS sad_test,
  COUNT(*) FILTER (WHERE label = 'neutral') AS neutral_test
FROM video
WHERE split = 'test';
```

---

## 7.6 Wire Node 3: if_balanced

1. Add an **IF** node → rename to `if_balanced`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ Math.min($json.happy_test, $json.sad_test, $json.neutral_test) }}` |
| **Operation** | `is greater than or equal to` |
| **Value 2** | `20` |

---

## 7.7 Wire Node 4: prepare_eval

Connected to **true** output of `if_balanced`.

1. Add a **Code** node → rename to `prepare_eval`
2. Code:

```javascript
const body = $('webhook_eval').first().json.body || {};

const run_id = body.run_id || 'eval-' + Date.now();
const checkpoint_path = body.checkpoint_path ||
  '/media/rusty_admin/project_data/ml_models/efficientnet/latest/best_model.onnx';
const output_dir = `/tmp/eval_${run_id}`;

return [{
  json: {
    run_id,
    checkpoint_path,
    output_dir,
    gateway_base: $env.GATEWAY_BASE_URL
  }
}];
```

---

## 7.8 Wire Node 5: ssh_run_eval

1. Add an **SSH** node → rename to `ssh_run_eval`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Ubuntu1` |
| **Command** | *(see below)* |

```bash
cd /home/rusty_admin/project-reachy-emotion && \
python trainer/run_efficientnet_pipeline.py \
  --skip-train \
  --checkpoint {{ $json.checkpoint_path }} \
  --run-id {{ $json.run_id }} \
  --output-dir {{ $json.output_dir }} \
  --gateway-base {{ $json.gateway_base }} && \
curl -s {{ $json.gateway_base }}/api/training/status/{{ $json.run_id }}
```

### Key Difference from Training

- **`--skip-train`** -- Skips the training step; only runs evaluation
- No `nohup` -- Evaluation is fast enough to run synchronously (2-5 minutes)
- The final `curl` fetches the evaluation results that the script posted to the Gateway

---

## 7.9 Wire Node 6: parse_results

1. Add a **Code** node → rename to `parse_results`
2. Code:

```javascript
const stdout = $input.first().json.stdout || '{}';

// The last line of stdout should be the JSON status from the curl command
const lines = stdout.trim().split('\n');
const statusLine = lines[lines.length - 1];
let status;

try {
  status = JSON.parse(statusLine);
} catch (e) {
  throw new Error('Failed to parse evaluation results: ' + statusLine);
}

const metrics = {
  f1_macro: parseFloat(status.metrics?.f1_macro || 0),
  balanced_accuracy: parseFloat(status.metrics?.balanced_accuracy || 0),
  ece: parseFloat(status.metrics?.ece || 1.0),
  brier: parseFloat(status.metrics?.brier || 1.0),
  accuracy: parseFloat(status.metrics?.accuracy || 0)
};

// Gate A sub-checks
const gate_a = {
  f1_pass: metrics.f1_macro >= 0.84,
  accuracy_pass: metrics.balanced_accuracy >= 0.85,
  ece_pass: metrics.ece <= 0.08,
  brier_pass: metrics.brier <= 0.16,
  passed: false
};
gate_a.passed = gate_a.f1_pass && gate_a.accuracy_pass &&
                gate_a.ece_pass && gate_a.brier_pass;

const run_id = $('prepare_eval').first().json.run_id;

return [{
  json: {
    run_id,
    status: 'completed',
    metrics,
    gate_a
  }
}];
```

---

## 7.10 Wire Node 7: mlflow_log

1. Add an **HTTP Request** node → rename to `mlflow_log`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MLFLOW_URL }}/api/2.0/mlflow/runs/log-batch` |

Body (raw JSON):

```json
{
  "run_id": "{{ $json.run_id }}",
  "metrics": [
    {"key": "eval_f1_macro", "value": {{ $json.metrics.f1_macro }}, "timestamp": {{ Date.now() }}},
    {"key": "eval_accuracy", "value": {{ $json.metrics.accuracy }}, "timestamp": {{ Date.now() }}},
    {"key": "eval_ece", "value": {{ $json.metrics.ece }}, "timestamp": {{ Date.now() }}},
    {"key": "eval_brier", "value": {{ $json.metrics.brier }}, "timestamp": {{ Date.now() }}},
    {"key": "eval_balanced_accuracy", "value": {{ $json.metrics.balanced_accuracy }}, "timestamp": {{ Date.now() }}}
  ]
}
```

### MLflow Batch Logging

Instead of 5 separate API calls (one per metric), we use the `log-batch` endpoint to log all 5 metrics in a single request. This is more efficient and atomic.

---

## 7.11 Wire Node 8: gate_a_check

1. Add an **IF** node → rename to `gate_a_check`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $('parse_results').item.json.gate_a.passed }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 7.12 Wire Node 9: emit_completed

Connected to **true** output of `gate_a_check`.

1. Add an **HTTP Request** node → rename to `emit_completed`

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `evaluation.completed` |
| `run_id` | `{{ $('parse_results').item.json.run_id }}` |
| `gate_a_passed` | `true` |
| `f1_macro` | `{{ $('parse_results').item.json.metrics.f1_macro }}` |
| `ece` | `{{ $('parse_results').item.json.metrics.ece }}` |
| `ready_for_deployment` | `true` |

---

## 7.13 Wire Node 10: emit_gate_failed

Connected to **false** output of `gate_a_check`.

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `evaluation.gate_failed` |
| `gate_a_details` | `{{ JSON.stringify($('parse_results').item.json.gate_a) }}` |
| `metrics` | `{{ JSON.stringify($('parse_results').item.json.metrics) }}` |

---

## 7.14 Wire Nodes 11-12: Blocked Path

Connected to the **false** output of `if_balanced` (from node 3).

### Node 11: prepare_blocked_status

1. Add a **Code** node → rename to `prepare_blocked_status`
2. Code:

```javascript
const balance = $('db_check_balance').first().json;
return [{
  json: {
    status: 'blocked',
    reason: 'Insufficient test data',
    happy_test: balance.happy_test,
    sad_test: balance.sad_test,
    neutral_test: balance.neutral_test,
    minimum_required: 20,
    run_id: $('webhook_eval').first().json.body?.run_id || 'unknown'
  }
}];
```

### Node 12: emit_blocked_status

1. Add an **HTTP Request** node → rename to `emit_blocked_status`
2. POST to `{{ $env.GATEWAY_BASE_URL }}/api/training/status/{{ $json.run_id }}`

---

## 7.15 Final Connection Map

```
webhook_eval ──► db_check_balance ──► if_balanced
                                          │
                   [unbalanced]           │    [balanced]
                        │                 │
                        ▼                 ▼
              prepare_blocked_status    prepare_eval
                        │                 │
                        ▼                 ▼
              emit_blocked_status      ssh_run_eval
                                          │
                                          ▼
                                     parse_results
                                          │
                                          ▼
                                      mlflow_log
                                          │
                                          ▼
                                     gate_a_check
                                    │           │
                              [pass]            [fail]
                                 │                │
                                 ▼                ▼
                          emit_completed    emit_gate_failed
```

---

## 7.16 Testing

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/agent/evaluation/efficientnet/start \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id from training>",
    "checkpoint_path": "/path/to/best_model.onnx"
  }'
```

---

## 7.17 Key Concepts Learned

- **Evaluation-only mode** using `--skip-train` flag
- **MLflow batch logging** for efficient multi-metric recording
- **Blocked status path** for insufficient data scenarios
- **Gate A re-validation** on unseen test data
- **Synchronous SSH** (no polling loop needed for fast operations)

---

*Previous: [MODULE 06 -- Training Orchestrator](MODULE_06_TRAINING_ORCHESTRATOR.md)*
*Next: [MODULE 08 -- Deployment Agent](MODULE_08_DEPLOYMENT_AGENT.md)*
