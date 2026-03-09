# Agent 6 — Evaluation Agent EfficientNet-B0 (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/06_evaluation_agent_efficientnet.json`

## Related Scripts and Functionalities
- `trainer/run_efficientnet_pipeline.py --skip-train` is launched by `SSH: run.evaluation`.
- Evaluation status is persisted via `POST /api/training/status/{run_id}`.
- Evaluation events are routed to implemented gateway endpoint `POST /api/events/pipeline`.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `Postgres: check.test_balance` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `SSH: run.evaluation` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`
- `MLFLOW_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: evaluation.start`
- Add node type: `Webhook`
- Rename node to: `Webhook: evaluation.start`
- Why this node exists: Trigger evaluation workflow run.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `agent/evaluation/efficientnet/start` |
| `responseMode` | `onReceived` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Postgres: check.test_balance`

### Step 2 - `Postgres: check.test_balance`
- Add node type: `Postgres`
- Rename node to: `Postgres: check.test_balance`
- Why this node exists: Check per-class test sample counts.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query**
```text
SELECT COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test, COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test FROM video;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Webhook: evaluation.start` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: test_set.balanced?`

### Step 3 - `IF: test_set.balanced?`
- Add node type: `If`
- Rename node to: `IF: test_set.balanced?`
- Why this node exists: Block run until test minima are met.

| UI Field | Value |
|---|---|
| `conditions` | `{"number": [{"value1": "={{Math.min($json.happy_test, $json.sad_test, $json.neutral_test)}}", "operation": "largerEqual", "value2": 20}]}` |

**Connection checklist for this node**
- Incoming: `Postgres: check.test_balance` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: prepare.evaluation`
- Outgoing: this node output branch `1` -> `Code: prepare.blocked_status`

### Step 4 - `Code: prepare.evaluation`
- Add node type: `Code`
- Rename node to: `Code: prepare.evaluation`
- Why this node exists: Prepare evaluation run context.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Prepare evaluation command using pipeline runner in skip-train mode
const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const runId = $json.run_id || `efficientnet_eval_${timestamp}`;
const checkpointPath = $json.checkpoint_path || `/workspace/checkpoints/efficientnet_b0_emotion/best_model.pth`;

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    checkpoint_path: checkpointPath,
    output_dir: `/workspace/experiments/${runId}`,
    gateway_base: $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000',
    model_placeholder: 'efficientnet-b0-hsemotion'
  }
}];
```

**Connection checklist for this node**
- Incoming: `IF: test_set.balanced?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: run.evaluation`

### Step 5 - `SSH: run.evaluation`
- Add node type: `SSH`
- Rename node to: `SSH: run.evaluation`
- Why this node exists: Launch evaluation-only runner.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
cd /workspace && mkdir -p {{$json.output_dir}} && source venv/bin/activate && python trainer/run_efficientnet_pipeline.py --skip-train --checkpoint {{$json.checkpoint_path}} --run-id {{$json.run_id}} --output-dir {{$json.output_dir}} --gateway-base {{$json.gateway_base}} --strict-contract-updates > {{$json.output_dir}}/evaluation.log 2>&1; RUN_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/{{$json.run_id}}); LATEST_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/latest); echo "{\"run_status\":$RUN_STATUS,\"latest_status\":$LATEST_STATUS}"
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Code: prepare.evaluation` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.results`

### Step 6 - `Code: parse.results`
- Add node type: `Code`
- Rename node to: `Code: parse.results`
- Why this node exists: Parse status payloads and gate metrics.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Parse persisted status snapshots (run-specific + latest)
const output = $json.stdout || '{}';
let payload;
try {
  payload = JSON.parse(output);
} catch (e) {
  payload = {error: 'Failed to parse status output', raw: output};
}

const runStatus = payload.run_status || {};
const latestStatus = payload.latest_status || {};
const metrics = runStatus.metrics?.gate_a_metrics || runStatus.metrics || {};
const gateGates = runStatus.metrics?.gate_a_gates || {};
const gateA = {
  f1_macro: gateGates.macro_f1 ?? ((metrics.f1_macro || 0) >= 0.84),
  balanced_accuracy: gateGates.balanced_accuracy ?? ((metrics.balanced_accuracy || 0) >= 0.85),
  ece: gateGates.ece ?? ((metrics.ece || 1) <= 0.08),
  brier: gateGates.brier ?? ((metrics.brier || 1) <= 0.16),
  passed: runStatus.metrics?.gate_a_passed ?? false
};

return [{
  json: {
    ...items[0].json,
    run_status: runStatus,
    latest_status: latestStatus,
    metrics,
    gate_a: gateA
  }
}];
```

**Connection checklist for this node**
- Incoming: `SSH: run.evaluation` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: mlflow.log_metrics`

### Step 7 - `HTTP: mlflow.log_metrics`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mlflow.log_metrics`
- Why this node exists: Log evaluation metrics to MLflow.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-batch` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "run_id", "value": "={{$json.mlflow_run_id}}"}, {"name": "metrics", "value": "={{[{key: 'eval_f1_macro', value: $json.metrics.f1_macro}, {key: 'eval_accuracy', value: $json.metrics.accuracy}, {key: 'eval_ece', value: $json.metrics.ece}, {key: 'eval_brier', value: $json.metrics.brier}, {key: 'eval_balanced_accuracy', value: $json.metrics.balanced_accuracy}]}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `Code: parse.results` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: Gate_A.pass?`

### Step 8 - `IF: Gate_A.pass?`
- Add node type: `If`
- Rename node to: `IF: Gate_A.pass?`
- Why this node exists: Branch gate pass/fail outputs.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.gate_a.passed}}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `HTTP: mlflow.log_metrics` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.completed`
- Outgoing: this node output branch `1` -> `HTTP: emit.gate_failed`

### Step 9 - `HTTP: emit.completed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.completed`
- Why this node exists: Emit evaluation completion event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=evaluation.completed"}, {"name": "pipeline_id", "value": "={{$json.run_id}}"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "model", "value": "=efficientnet-b0-hsemotion"}, {"name": "gate_a_passed", "value": "={{$json.gate_a.passed}}"}, {"name": "f1_macro", "value": "={{$json.metrics.f1_macro}}"}, {"name": "ece", "value": "={{$json.metrics.ece}}"}, {"name": "ready_for_deployment", "value": "={{$json.gate_a.passed}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: Gate_A.pass?` output branch `0` -> this node

### Step 10 - `HTTP: emit.gate_failed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.gate_failed`
- Why this node exists: Emit evaluation gate-failed event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/pipeline` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=evaluation.gate_failed"}, {"name": "pipeline_id", "value": "={{$json.run_id}}"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "model", "value": "=efficientnet-b0-hsemotion"}, {"name": "gate_a_details", "value": "={{JSON.stringify($json.gate_a)}}"}, {"name": "metrics", "value": "={{JSON.stringify($json.metrics)}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: Gate_A.pass?` output branch `1` -> this node

### Step 11 - `Code: prepare.blocked_status`
- Add node type: `Code`
- Rename node to: `Code: prepare.blocked_status`
- Why this node exists: Prepare blocked-status payload.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const runId = $json.run_id || `efficientnet_eval_blocked_${timestamp}`;
const gatewayBase = $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000';
const happy = Number($json.happy_test || 0);
const sad = Number($json.sad_test || 0);
const neutral = Number($json.neutral_test || 0);

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    gateway_base: gatewayBase,
    min_required_per_class: 20,
    happy_test: happy,
    sad_test: sad,
    neutral_test: neutral,
    min_count: Math.min(happy, sad, neutral),
    blocked_reason: 'insufficient_test_data'
  }
}];
```

**Connection checklist for this node**
- Incoming: `IF: test_set.balanced?` output branch `1` -> this node
- Outgoing: this node output branch `0` -> `HTTP: status.blocked`

### Step 12 - `HTTP: status.blocked`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: status.blocked`
- Why this node exists: Persist blocked status via status API.

| UI Field | Value |
|---|---|
| `url` | `={{$json.gateway_base}}/api/training/status/{{$json.run_id}}` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "schema_version", "value": "=v1"}, {"name": "event_type", "value": "=evaluation.blocked_insufficient_test_data"}, {"name": "source", "value": "=agent6.evaluation_agent"}, {"name": "correlation_id", "value": "={{$json.run_id}}"}, {"name": "status", "value": "=blocked"}, {"name": "metrics", "value": "={{JSON.stringify({blocked_reason: $json.blocked_reason, min_required_per_class: $json.min_required_per_class, counts: {happy: $json.happy_test, sad: $json.sad_test, neutral: $json.neutral_test}, min_count: $json.min_count})}}"}, {"name": "error_message", "value": "=Evaluation blocked: insufficient balanced test samples for happy/sad/neutral (minimum 20 per class)."}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `Code: prepare.blocked_status` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: evaluation.start` branch `0` -> `Postgres: check.test_balance`
- `Postgres: check.test_balance` branch `0` -> `IF: test_set.balanced?`
- `IF: test_set.balanced?` branch `0` -> `Code: prepare.evaluation`
- `IF: test_set.balanced?` branch `1` -> `Code: prepare.blocked_status`
- `Code: prepare.evaluation` branch `0` -> `SSH: run.evaluation`
- `SSH: run.evaluation` branch `0` -> `Code: parse.results`
- `Code: parse.results` branch `0` -> `HTTP: mlflow.log_metrics`
- `HTTP: mlflow.log_metrics` branch `0` -> `IF: Gate_A.pass?`
- `IF: Gate_A.pass?` branch `0` -> `HTTP: emit.completed`
- `IF: Gate_A.pass?` branch `1` -> `HTTP: emit.gate_failed`
- `Code: prepare.blocked_status` branch `0` -> `HTTP: status.blocked`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
