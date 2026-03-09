# Agent 7 — Deployment Agent EfficientNet-B0 (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/07_deployment_agent_efficientnet.json`

## Related Scripts and Functionalities
- Jetson deployment is executed via SSH (`scp`, `trtexec`, DeepStream config update, service restart).
- `apps/api/routers/gateway.py` receives deployment lifecycle events at `POST /api/events/deployment`.
- Gate B logic is computed in `Code: parse.verification` using service/metrics output.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `SSH: scp.onnx_to_jetson` uses credential type `sshPassword` with display name `SSH Ubuntu1`.
- `SSH: convert.to_tensorrt` uses credential type `sshPassword` with display name `SSH Jetson`.
- `SSH: update.deepstream_config` uses credential type `sshPassword` with display name `SSH Jetson`.
- `SSH: verify.deployment` uses credential type `sshPassword` with display name `SSH Jetson`.
- `SSH: rollback` uses credential type `sshPassword` with display name `SSH Jetson`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: deployment.start`
- Add node type: `Webhook`
- Rename node to: `Webhook: deployment.start`
- Why this node exists: Start deployment workflow.

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `agent/deployment/efficientnet/start` |
| `responseMode` | `onReceived` |
| `options` | `{"responseCode": 202}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `IF: gate_a.passed?`

### Step 2 - `IF: gate_a.passed?`
- Add node type: `If`
- Rename node to: `IF: gate_a.passed?`
- Why this node exists: Block deployment when gate A is false.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.gate_a_passed}}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `Webhook: deployment.start` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: prepare.deployment`

### Step 3 - `Code: prepare.deployment`
- Add node type: `Code`
- Rename node to: `Code: prepare.deployment`
- Why this node exists: Derive ONNX/engine/backup paths.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Prepare deployment paths
const runId = $json.run_id;
const onnxPath = $json.onnx_path || `/workspace/exports/${runId}/emotion_classifier_${runId}.onnx`;
const enginePath = `/opt/reachy/models/emotion_efficientnet.engine`;
const backupPath = `/opt/reachy/models/backup/emotion_efficientnet_${Date.now()}.engine`;

return [{
  json: {
    ...items[0].json,
    onnx_path: onnxPath,
    engine_path: enginePath,
    backup_path: backupPath,
    model_placeholder: 'efficientnet-b0-hsemotion',
    deployment_stage: 'shadow'
  }
}];
```

**Connection checklist for this node**
- Incoming: `IF: gate_a.passed?` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: scp.onnx_to_jetson`

### Step 4 - `SSH: scp.onnx_to_jetson`
- Add node type: `SSH`
- Rename node to: `SSH: scp.onnx_to_jetson`
- Why this node exists: Copy ONNX artifact to Jetson host.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
scp {{$json.onnx_path}} jetson@10.0.4.150:/tmp/emotion_classifier.onnx
```

**Credential binding**
- `sshPassword` -> `SSH Ubuntu1`

**Connection checklist for this node**
- Incoming: `Code: prepare.deployment` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: convert.to_tensorrt`

### Step 5 - `SSH: convert.to_tensorrt`
- Add node type: `SSH`
- Rename node to: `SSH: convert.to_tensorrt`
- Why this node exists: Convert ONNX to TensorRT engine.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
# Backup existing engine
if [ -f {{$json.engine_path}} ]; then
  mkdir -p /opt/reachy/models/backup
  cp {{$json.engine_path}} {{$json.backup_path}}
fi

# Convert ONNX to TensorRT
/usr/src/tensorrt/bin/trtexec \
  --onnx=/tmp/emotion_classifier.onnx \
  --saveEngine={{$json.engine_path}} \
  --fp16 \
  --workspace=2048 \
  --minShapes=input:1x3x224x224 \
  --optShapes=input:1x3x224x224 \
  --maxShapes=input:8x3x224x224
```

**Credential binding**
- `sshPassword` -> `SSH Jetson`

**Connection checklist for this node**
- Incoming: `SSH: scp.onnx_to_jetson` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: update.deepstream_config`

### Step 6 - `SSH: update.deepstream_config`
- Add node type: `SSH`
- Rename node to: `SSH: update.deepstream_config`
- Why this node exists: Point DeepStream to new engine and restart.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
# Update DeepStream config to use new engine
sed -i 's|model-engine-file=.*|model-engine-file={{$json.engine_path}}|' /opt/reachy/config/emotion_inference.txt

# Restart DeepStream service
sudo systemctl restart reachy-emotion
```

**Credential binding**
- `sshPassword` -> `SSH Jetson`

**Connection checklist for this node**
- Incoming: `SSH: convert.to_tensorrt` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Wait: 30s`

### Step 7 - `Wait: 30s`
- Add node type: `Wait`
- Rename node to: `Wait: 30s`
- Why this node exists: Allow service warm-up before verify step.

| UI Field | Value |
|---|---|
| `amount` | `30` |
| `unit` | `seconds` |

**Connection checklist for this node**
- Incoming: `SSH: update.deepstream_config` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `SSH: verify.deployment`

### Step 8 - `SSH: verify.deployment`
- Add node type: `SSH`
- Rename node to: `SSH: verify.deployment`
- Why this node exists: Read runtime service/metric outputs.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
# Check service status and get metrics
systemctl is-active reachy-emotion && \
cat /var/log/reachy/emotion_metrics.json | tail -1
```

**Credential binding**
- `sshPassword` -> `SSH Jetson`

**Connection checklist for this node**
- Incoming: `Wait: 30s` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.verification`

### Step 9 - `Code: parse.verification`
- Add node type: `Code`
- Rename node to: `Code: parse.verification`
- Why this node exists: Compute Gate B booleans from metrics.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
// Parse verification results
const output = $json.stdout || '';
const lines = output.trim().split('\n');
const serviceActive = lines[0] === 'active';

let metrics = {};
try {
  metrics = JSON.parse(lines[1] || '{}');
} catch (e) {
  metrics = {fps: 0, latency_ms: 999};
}

// Check Gate B requirements
const gateB = {
  service_active: serviceActive,
  fps_ok: metrics.fps >= 25,
  latency_ok: metrics.latency_p50_ms <= 120,
  passed: serviceActive && metrics.fps >= 25 && metrics.latency_p50_ms <= 120
};

return [{
  json: {
    ...items[0].json,
    service_active: serviceActive,
    metrics: metrics,
    gate_b: gateB,
    deployment_status: gateB.passed ? 'success' : 'failed'
  }
}];
```

**Connection checklist for this node**
- Incoming: `SSH: verify.deployment` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `IF: Gate_B.pass?`

### Step 10 - `IF: Gate_B.pass?`
- Add node type: `If`
- Rename node to: `IF: Gate_B.pass?`
- Why this node exists: Branch success path vs rollback path.

| UI Field | Value |
|---|---|
| `conditions` | `{"boolean": [{"value1": "={{$json.gate_b.passed}}", "value2": true}]}` |

**Connection checklist for this node**
- Incoming: `Code: parse.verification` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.success`
- Outgoing: this node output branch `1` -> `SSH: rollback`

### Step 11 - `HTTP: emit.success`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.success`
- Why this node exists: Emit deployment completion event.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/deployment` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=deployment.completed"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "model", "value": "=efficientnet-b0-hsemotion"}, {"name": "engine_path", "value": "={{$json.engine_path}}"}, {"name": "fps", "value": "={{$json.metrics.fps}}"}, {"name": "latency_p50_ms", "value": "={{$json.metrics.latency_p50_ms}}"}, {"name": "deployment_stage", "value": "=shadow"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `IF: Gate_B.pass?` output branch `0` -> this node

### Step 12 - `SSH: rollback`
- Add node type: `SSH`
- Rename node to: `SSH: rollback`
- Why this node exists: Restore previous engine on failure.

| UI Field | Value |
|---|---|
| `authentication` | `password` |

**SSH Command**
```text
# Rollback to previous engine
if [ -f {{$json.backup_path}} ]; then
  cp {{$json.backup_path}} {{$json.engine_path}}
  sudo systemctl restart reachy-emotion
fi
```

**Credential binding**
- `sshPassword` -> `SSH Jetson`

**Connection checklist for this node**
- Incoming: `IF: Gate_B.pass?` output branch `1` -> this node
- Outgoing: this node output branch `0` -> `HTTP: emit.rollback`

### Step 13 - `HTTP: emit.rollback`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: emit.rollback`
- Why this node exists: Emit rollback event payload.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/deployment` |
| `sendBody` | `True` |
| `bodyParameters` | `{"parameters": [{"name": "event_type", "value": "=deployment.rollback"}, {"name": "run_id", "value": "={{$json.run_id}}"}, {"name": "reason", "value": "=Gate B failed - performance requirements not met"}, {"name": "metrics", "value": "={{JSON.stringify($json.metrics)}}"}]}` |
| `method` | `POST` |

**Connection checklist for this node**
- Incoming: `SSH: rollback` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Webhook: deployment.start` branch `0` -> `IF: gate_a.passed?`
- `IF: gate_a.passed?` branch `0` -> `Code: prepare.deployment`
- `Code: prepare.deployment` branch `0` -> `SSH: scp.onnx_to_jetson`
- `SSH: scp.onnx_to_jetson` branch `0` -> `SSH: convert.to_tensorrt`
- `SSH: convert.to_tensorrt` branch `0` -> `SSH: update.deepstream_config`
- `SSH: update.deepstream_config` branch `0` -> `Wait: 30s`
- `Wait: 30s` branch `0` -> `SSH: verify.deployment`
- `SSH: verify.deployment` branch `0` -> `Code: parse.verification`
- `Code: parse.verification` branch `0` -> `IF: Gate_B.pass?`
- `IF: Gate_B.pass?` branch `0` -> `HTTP: emit.success`
- `IF: Gate_B.pass?` branch `1` -> `SSH: rollback`
- `SSH: rollback` branch `0` -> `HTTP: emit.rollback`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
