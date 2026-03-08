# Agent 5 — Training Orchestrator EfficientNet-B0 (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/05_training_orchestrator_efficientnet.json`

## Related Scripts and Functionalities
- `trainer/run_efficientnet_pipeline.py` is launched by `SSH: start.training`.
- `apps/api/routers/gateway.py` + `apps/api/app/routers/gateway_upstream.py` provide `/api/training/status/{id}` status contract.
- Gateway accepts training events at `POST /api/events/training`.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `Postgres: check.train_balance` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
- `SSH: start.training` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
- `SSH: check.status` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`
- `MLFLOW_EXPERIMENT_ID`
- `MLFLOW_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: training.start`
- Add node type: `Webhook`
- Rename node to: `Webhook: training.start`
- Why this node exists: Trigger training orchestrator execution.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `agent/training/efficientnet/start` |
| `responseMode` | `onReceived` |
| `options` | `{"responseCode": 202}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `Postgres: check.train_balance`

### Step 2 - `Postgres: check.train_balance`
- Add node type: `Postgres`
- Rename node to: `Postgres: check.train_balance`
- Why this node exists: Check per-class train sample counts.

| UI Field | Value |
|---|---|
| `operation` | `executeQuery` |

**SQL Query**
```text
SELECT COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train, COUNT(*) FILTER (WHERE label='neutral' AND split='train') AS neutral_train FROM video;
```

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Webhook: training.start` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: sufficient_data?`

### Step 3 - `IF: sufficient_data?`
- Add node type: `If`
- Rename node to: `IF: sufficient_data?`
- Why this node exists: Gate training if class minima are unmet.

| UI Field | Value |
|---|---|
| `conditions` | `{"number": [{"value1": "={{Math.min($json.happy_train, $json.sad_train, $json.neutral_train)}}", "operation": "largerEqual", "value2": 50}]}` |

**Connection checklist for this node**
- Incoming: `Postgres: check.train_balance` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: mlflow.create_run`
- Outgoing: this node output branch `1` -> `HTTP: emit.insufficient_data`

### Step 4 - `HTTP: mlflow.create_run`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mlflow.create_run`
- Why this node exists: Create MLflow run before launch.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "experiment_id", "value": "={{$env.MLFLOW_EXPERIMENT_ID}}"}, {"name": "tags", "value": "={{[{key: 'model', value: 'efficientnet-b0-hsemotion'}, {key: 'dataset_hash', value: $json.dataset_hash}, {key: 'correlation_id', value: $json.correlation_id}]}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: sufficient_data?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: prepare.training`

### Step 5 - `Code: prepare.training`
- Add node type: `Code`
- Rename node to: `Code: prepare.training`
- Why this node exists: Build run IDs and command inputs.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Generate run ID and prepare 3-class EfficientNet pipeline command
const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const runId = `efficientnet_b0_emotion_${timestamp}`;

return [{
  json: {
    ...items[0].json,
    run_id: runId,
    config_path: '/workspace/trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml',
    output_dir: `/workspace/experiments/${runId}`,
    model_placeholder: 'efficientnet-b0-hsemotion',
    model_storage_path: '/media/rusty_admin/project_data/ml_models/efficientnet_b0',
    gateway_base: $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000'
  }
}];
```

**Connection checklist for this node**
- Incoming: `HTTP: mlflow.create_run` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: start.training`

### Step 6 - `SSH: start.training`
- Add node type: `SSH`
- Rename node to: `SSH: start.training`
- Why this node exists: Launch training runner on worker host.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
cd /workspace && mkdir -p {{$json.output_dir}} && source venv/bin/activate && python trainer/run_efficientnet_pipeline.py --config {{$json.config_path}} --run-id {{$json.run_id}} --output-dir {{$json.output_dir}} --gateway-base {{$json.gateway_base}} --strict-contract-updates > {{$json.output_dir}}/pipeline.log 2>&1
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Code: prepare.training` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Wait: 5min`

### Step 7 - `Wait: 5min`
- Add node type: `Wait`
- Rename node to: `Wait: 5min`
- Why this node exists: Wait before polling status again.

| UI Field | Value |
|---|---|
| `amount` | `5` |
| `unit` | `minutes` |

**Connection checklist for this node**
- Incoming: `SSH: start.training` output branch `0` -> this node
- Incoming: `IF: training.done?` output branch `1` -> this node
- Outgoing: this node output branch `0` -> `SSH: check.status`

### Step 8 - `SSH: check.status`
- Add node type: `SSH`
- Rename node to: `SSH: check.status`
- Why this node exists: Fetch run status snapshots from API.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
RUN_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/{{$json.run_id}}); LATEST_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/latest); echo "{\"run_status\":$RUN_STATUS,\"latest_status\":$LATEST_STATUS}"
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Wait: 5min` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.results`

### Step 9 - `Code: parse.results`
- Add node type: `Code`
- Rename node to: `Code: parse.results`
- Why this node exists: Parse status payloads and gate metrics.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
const payload = JSON.parse($json.stdout || '{}');
const runStatus = payload.run_status || {};
const latestStatus = payload.latest_status || {};
const metrics = runStatus.metrics || {};
const gateResults = metrics.gate_a_gates || {};

if (runStatus.status === 'training' || runStatus.status === 'evaluating' || runStatus.status === 'pending' || runStatus.status === 'sampling') {
  return [{json: {...items[0].json, status: 'running', run_status: runStatus, latest_status: latestStatus}}];
}

return [{
  json: {
    ...items[0].json,
    status: runStatus.status || 'unknown',
    best_metric: metrics.best_metric ?? metrics.f1_macro ?? null,
    epochs_completed: metrics.epochs_completed ?? null,
    gate_results: {
      ...gateResults,
      gate_a: metrics.gate_a_passed ?? false
    },
    run_status: runStatus,
    latest_status: latestStatus
  }
}];
```

**Connection checklist for this node**
- Incoming: `SSH: check.status` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: training.done?`

### Step 10 - `IF: training.done?`
- Add node type: `If`
- Rename node to: `IF: training.done?`
- Why this node exists: Loop until status indicates completion.

| UI Field | Value |
|---|---|
| `conditions` | `{"string": [{"value1": "={{$json.status}}", "operation": "contains", "value2": "completed"}]}` |

**Connection checklist for this node**
- Incoming: `Code: parse.results` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: Gate_A.pass?`
- Outgoing: this node output branch `1` -> `Wait: 5min`

### Step 11 - `IF: Gate_A.pass?`
- Add node type: `If`
- Rename node to: `IF: Gate_A.pass?`
- Why this node exists: Branch gate pass/fail outputs.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.gate_results.gate_a}}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `IF: training.done?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: mlflow.log_gate`
- Outgoing: this node output branch `1` -> `HTTP: emit.gate_failed`

### Step 12 - `HTTP: mlflow.log_gate`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mlflow.log_gate`
- Why this node exists: Write gate pass metric to MLflow.

| UI Field | Value |
|---|---|
| `url` | `={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-metric` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "run_id", "value": "={{$json.mlflow_run_id}}"}, {"name": "key", "value": "=gate_a_passed"}, {"name": "value", "value": "={{$json.gate_results.gate_a ? 1 : 0}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: Gate_A.pass?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.completed`

### Step 13 - `HTTP: emit.completed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.completed`
- Why this node exists: Emit training completion event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/training` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=training.completed"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "model", "value": "=efficientnet-b0-hsemotion"}, {"name": "gate_a_passed", "value": "={{$json.gate_results.gate_a}}"}, {"name": "onnx_path", "value": "={{$json.export?.onnx \|\| ''}}"}, {"name": "best_f1", "value": "={{$json.best_metric}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `HTTP: mlflow.log_gate` output branch `0` -> this node

### Step 14 - `HTTP: emit.gate_failed`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.gate_failed`
- Why this node exists: Emit training gate-failed event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/training` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=training.gate_failed"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "model", "value": "=efficientnet-b0-hsemotion"}, {"name": "best_f1", "value": "={{$json.best_metric}}"}, {"name": "message", "value": "=Gate A requirements not met. Need more training data or hyperparameter tuning."}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: Gate_A.pass?` output branch `1` -> this node

### Step 15 - `HTTP: emit.insufficient_data`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.insufficient_data`
- Why this node exists: Emit insufficient data event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/training` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=training.insufficient_data"}, {"name": "happy_count", "value": "={{$json.happy_train}}"}, {"name": "sad_count", "value": "={{$json.sad_train}}"}, {"name": "neutral_count", "value": "={{$json.neutral_train}}"}, {"name": "message", "value": "=Insufficient training data. Need at least 50 samples per class (happy/sad/neutral)."}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: sufficient_data?` output branch `1` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: training.start` branch `0` -> `Postgres: check.train_balance`
- `Postgres: check.train_balance` branch `0` -> `IF: sufficient_data?`
- `IF: sufficient_data?` branch `0` -> `HTTP: mlflow.create_run`
- `IF: sufficient_data?` branch `1` -> `HTTP: emit.insufficient_data`
- `HTTP: mlflow.create_run` branch `0` -> `Code: prepare.training`
- `Code: prepare.training` branch `0` -> `SSH: start.training`
- `SSH: start.training` branch `0` -> `Wait: 5min`
- `Wait: 5min` branch `0` -> `SSH: check.status`
- `SSH: check.status` branch `0` -> `Code: parse.results`
- `Code: parse.results` branch `0` -> `IF: training.done?`
- `IF: training.done?` branch `0` -> `IF: Gate_A.pass?`
- `IF: training.done?` branch `1` -> `Wait: 5min`
- `IF: Gate_A.pass?` branch `0` -> `HTTP: mlflow.log_gate`
- `IF: Gate_A.pass?` branch `1` -> `HTTP: emit.gate_failed`
- `HTTP: mlflow.log_gate` branch `0` -> `HTTP: emit.completed`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
