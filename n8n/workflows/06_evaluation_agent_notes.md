# Agent 6 — Evaluation Agent (Workflow `06_evaluation_agent.json`)

Rusty, this guide documents the evaluation workflow end to end so you can mirror it in n8n. It starts with an alphabetical node inventory, then explains each node's inputs, key parameters (with JSON you can paste), and how the control flow enforces the balanced-test-set requirement before running DeepStream inference and logging metrics.

## Alphabetical inventory of nodes (workflow scope)
- Code: parse.results
- HTTP: emit.completed
- HTTP: mlflow.log_metrics
- IF: test_set.balanced?
- Postgres: check.test_balance
- SSH: run.inference
- Webhook: evaluation.start

---

## Node-by-node flow details
The workflow listens for an evaluation trigger, verifies the test split is balanced, runs DeepStream inference on the Jetson, parses the console output into metrics, logs accuracy to MLflow, and emits an evaluation completion event.

### Webhook node
**Webhook: evaluation.start** — External POST hook (`/agent/evaluation/start`) that kicks off evaluation. The incoming payload is forwarded downstream so later nodes (e.g., MLflow logging) can reuse fields like `run_id` or `correlation_id` if provided by the caller.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "agent/evaluation/start",
  "responseMode": "onReceived"
}
```

### Postgres node
**Postgres: check.test_balance** — Counts happy vs sad items in the `test` split to ensure evaluation only runs when both classes have sufficient coverage.

Parameters (query):
```json
{
  "operation": "executeQuery",
  "query": "SELECT COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test FROM video;"
}
```

### IF node
**IF: test_set.balanced?** — Enforces a minimum of 20 items per class in the test split. It takes the counts from the Postgres node and uses `Math.min(happy_test, sad_test)` to gate the run. False branch halts; true branch proceeds to the Jetson inference step.

Parameters:
```json
{
  "conditions": {
    "number": [
      { "value1": "={{Math.min($json.happy_test, $json.sad_test)}}", "operation": "largerEqual", "value2": 20 }
    ]
  }
}
```

### SSH node
**SSH: run.inference** — Executes DeepStream on the Jetson using the evaluation config. Input context (e.g., `run_id`, correlation_id) from the webhook is passed through implicitly so downstream logging can access it.

Parameters:
```json
{
  "command": "deepstream-app -c /opt/reachy/config/emotion_inference.txt",
  "authentication": "password"
}
```

### Code node
**Code: parse.results** — Parses DeepStream stdout to extract predicted emotions and confidence scores. It scans each line for the pattern `emotion:<label> conf:<score>`, collects matches, and outputs an array plus a total count. You can extend this to compute accuracy by comparing against labeled data if available.

Dynamic parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Parse DeepStream output and compute metrics\nconst output = $json.stdout || '';\nconst predictions = [];\n// Simple parser - in production use structured JSON from DeepStream\nconst lines = output.split('\\n');\nfor (const line of lines) {\n  if (line.includes('emotion:')) {\n    const match = line.match(/emotion:(\\w+) conf:(\\d\\.\\d+)/);\n    if (match) predictions.push({emotion: match[1], conf: parseFloat(match[2])});\n  }\n}\nreturn [{json: {predictions, total: predictions.length}}];"
}
```

### HTTP nodes
**HTTP: mlflow.log_metrics** — Logs evaluation metrics to MLflow. It expects `run_id` (typically supplied in the webhook payload) and an `accuracy` field produced upstream. If you add accuracy computation to the code node, keep the key name `accuracy` to match this request.

Dynamic parameters:
```json
{
  "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-metric",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "run_id", "value": "={{$json.run_id}}" },
      { "name": "key", "value": "=test_accuracy" },
      { "name": "value", "value": "={{$json.accuracy}}" }
    ]
  }
}
```

**HTTP: emit.completed** — Emits `evaluation.completed` to the Gateway service so downstream agents (e.g., deployment) know validation finished. It forwards any `run_id` in the current item so the event can be correlated with training outputs.

Dynamic parameters:
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/evaluation",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "event_type", "value": "=evaluation.completed" },
      { "name": "run_id", "value": "={{$json.run_id}}" }
    ]
  }
}
```

### Flow wiring (inputs between nodes)
- **Webhook evaluation.start** → Postgres check.test_balance → IF test_set.balanced? (true branch continues; false halts).
- **IF true branch** → SSH run.inference → Code parse.results → HTTP mlflow.log_metrics → HTTP emit.completed.

This sequence makes sure evaluation runs only when the test split is balanced, executes inference on the Jetson, parses the console output, logs metrics to MLflow using the provided run context, and emits a completion event for the rest of the system.
