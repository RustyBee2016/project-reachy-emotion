# Agent 5 — Training Orchestrator (Workflow `05_training_orchestrator.json`)

Rusty, this note walks through every node in the training orchestrator. It starts with an alphabetical inventory, then explains each node's inputs, parameters, and how the control loop works. Dynamic parameters are shown as JSON snippets so you can paste them into n8n.

## Alphabetical inventory of nodes (workflow scope)
- Code: parse.summary
- HTTP: emit.completed
- HTTP: mlflow.create_run
- IF: Gate_A.pass?
- IF: training.done?
- SSH: check.status
- SSH: tao.export_trt
- SSH: tao.start_training
- Wait: 5min
- Webhook: dataset.promoted

---

## Node-by-node flow details
The workflow listens for a dataset promotion event, registers a new MLflow run, starts TAO training, polls for completion, applies Gate A metric thresholds, exports a TensorRT engine, and emits a completion event.

### Webhook node
**Webhook: dataset.promoted** — External trigger (HTTP POST to `/agent/training/start`) that launches training. It passes the request payload (e.g., `dataset_hash`, `correlation_id`) directly to MLflow so tags can reference the dataset used for this run.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "agent/training/start",
  "responseMode": "onReceived",
  "options": { "responseCode": 202 }
}
```

### HTTP node
**HTTP: mlflow.create_run** — Uses the webhook payload to create a new MLflow run. The response carries `run.info.run_id`, which downstream nodes reuse to namespace experiment folders and checkpoints.

Dynamic parameters:
```json
{
  "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "experiment_id", "value": "={{$env.MLFLOW_EXPERIMENT_ID}}" },
      { "name": "tags", "value": "={{[{ key: 'dataset_hash', value: $json.dataset_hash }, { key: 'correlation_id', value: $json.correlation_id }]}}" }
    ]
  }
}
```

### SSH nodes
**SSH: tao.start_training** — Starts EmotionNet training on Ubuntu 1 using the MLflow `run_id` to create a unique experiment directory. It runs the job in the background and redirects logs to `train.log`. Input includes `run_id` from the MLflow response.

Parameters:
```json
{
  "command": "cd /workspace && nohup tao-launcher emotion_net train -e /workspace/specs/emotionnet_2cls.yaml -r /workspace/experiments/{{$json.run_id}} > /workspace/experiments/{{$json.run_id}}/train.log 2>&1 &",
  "authentication": "password"
}
```

**SSH: check.status** — Polls the experiment directory for `summary.json`. If the file exists, it outputs the JSON; otherwise it returns a placeholder `{"status": "running"}`. Input carries the same `run_id` so the command points at the correct experiment folder.

Parameters:
```json
{
  "command": "test -f /workspace/experiments/{{$json.run_id}}/summary.json && cat /workspace/experiments/{{$json.run_id}}/summary.json || echo '{\"status\": \"running\"}'",
  "authentication": "password"
}
```

**SSH: tao.export_trt** — After Gate A passes, exports the trained model to TensorRT FP16 engine format. It relies on `run_id` to reference the correct `model.etlt` output from training.

Parameters:
```json
{
  "command": "cd /workspace && tao-converter -k tlt_encode -d 3,224,224 -t fp16 -e /workspace/experiments/{{$json.run_id}}/emotionnet.engine /workspace/experiments/{{$json.run_id}}/model.etlt",
  "authentication": "password"
}
```

### Wait node
**Wait: 5min** — Adds a fixed five-minute delay between status checks to avoid hammering the filesystem while training runs. It receives the `run_id` and passes it through unchanged.

Parameters:
```json
{ "amount": 5, "unit": "minutes" }
```

### Code node
**Code: parse.summary** — Parses the stdout from `check.status`. If the job is still running, it preserves the incoming JSON and sets `status: "running"`. When `summary.json` is present, it returns the parsed metrics plus the original `run_id` so IF nodes can evaluate completion and Gate A thresholds.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "const result = JSON.parse($json.stdout || '{}');\nif (result.status === 'running') {\n  return [{ json: { ...items[0].json, status: 'running' } }];\n}\nreturn [{ json: { ...result, run_id: items[0].json.run_id } }];"
}
```

### IF nodes
**IF: training.done?** — Checks the parsed status for `completed`. True branch proceeds to Gate A metrics; false branch loops back to the wait node for another poll.

Parameters:
```json
{
  "conditions": {
    "string": [
      { "value1": "={{$json.status}}", "value2": "completed" }
    ]
  }
}
```

**IF: Gate_A.pass?** — Evaluates core metrics from `summary.json` to enforce minimum performance before exporting. Requires `macro_f1 ≥ 0.84`, `balanced_accuracy ≥ 0.85`, and `ece ≤ 0.08`.

Parameters:
```json
{
  "conditions": {
    "number": [
      { "value1": "={{$json.macro_f1}}", "operation": "largerEqual", "value2": 0.84 },
      { "value1": "={{$json.balanced_accuracy}}", "operation": "largerEqual", "value2": 0.85 },
      { "value1": "={{$json.ece}}", "operation": "smallerEqual", "value2": 0.08 }
    ]
  }
}
```

### HTTP node (emit event)
**HTTP: emit.completed** — Emits a `training.completed` event to the Gateway service once the engine export succeeds. Sends the `run_id`, `dataset_hash`, and engine path so downstream agents (evaluation and deployment) can pick up the artifact.

Dynamic parameters:
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/training",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "event_type", "value": "=training.completed" },
      { "name": "run_id", "value": "={{$json.run_id}}" },
      { "name": "dataset_hash", "value": "={{$json.dataset_hash}}" },
      { "name": "engine_path", "value": "=/workspace/experiments/{{$json.run_id}}/emotionnet.engine" }
    ]
  }
}
```

### Flow wiring (inputs between nodes)
- **Webhook dataset.promoted** → HTTP mlflow.create_run → SSH tao.start_training → Wait 5min → SSH check.status → Code parse.summary → IF training.done? (true to Gate_A.pass?, false loops back to Wait 5min).
- **Gate_A.pass?** (true) → SSH tao.export_trt → HTTP emit.completed.
- **Gate_A.pass?** (false) currently stops without export; the workflow ends after the metric check fails.

This layout lets you trigger training from the promotion event, track progress with timed polling, gate export on quality thresholds, and notify the rest of the system when a TensorRT engine is ready.
