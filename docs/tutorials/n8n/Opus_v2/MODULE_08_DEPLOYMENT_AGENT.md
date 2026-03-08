# MODULE 08 -- Deployment Agent (EfficientNet-B0)

**Duration:** ~4 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`
**Nodes to Wire:** 14
**Prerequisite:** MODULE 07 complete
**Outcome:** A deployment workflow that transfers ONNX models to the Jetson, converts to TensorRT, updates DeepStream, validates runtime performance (Gate B), and auto-rolls back on failure

---

## 8.1 What Does the Deployment Agent Do?

This agent deploys a trained and evaluated model to the edge device (Jetson Xavier NX). It's the most **operationally risky** agent because it modifies a running production system.

Steps:
1. Validates Gate A was passed
2. SCP the ONNX model from Ubuntu 1 → Jetson
3. Converts ONNX to TensorRT engine (FP16)
4. Updates DeepStream configuration
5. Restarts the emotion inference service
6. Waits 30 seconds for startup
7. Validates **Gate B** runtime thresholds (FPS, latency)
8. On Gate B failure: **automatic rollback** to previous engine

### Gate B Quality Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Service Active | Yes | `systemctl is-active reachy-emotion` returns "active" |
| FPS | >= 25 | Frames per second on the Jetson GPU |
| Latency P50 | <= 120ms | Median inference latency |

### New Concepts

- **Two SSH credentials** (Ubuntu 1 + Jetson)
- **SCP file transfer** via SSH node
- **TensorRT conversion** on edge device
- **Auto-rollback** on deployment failure
- **Gate B** (runtime performance gate)

---

## 8.2 Pre-Wiring Checklist

- [ ] **SSH to Jetson** works: `ssh jetson@10.0.4.150`
- [ ] **trtexec** is available on Jetson: `ssh jetson@10.0.4.150 "which trtexec"`
- [ ] **DeepStream** is installed on Jetson
- [ ] **reachy-emotion service** is configured: `ssh jetson@10.0.4.150 "systemctl status reachy-emotion"`
- [ ] **ONNX model** exists from a training run

---

## 8.3 Create the Workflow

1. Name: `Agent 7 -- Deployment Agent EfficientNet-B0 (Reachy 08.4.2)`
2. Tags: `agent`, `deployment`, `efficientnet`, `ml-v1`

---

## 8.4 Wire Node 1: webhook_deploy

1. Add a **Webhook** → rename to `webhook_deploy`

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `agent/deployment/efficientnet/start` |
| **Response Mode** | `On Received` |
| **Response Code** | `202` |

---

## 8.5 Wire Node 2: if_gate_passed

1. Add an **IF** node → rename to `if_gate_passed`

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.body.gate_a_passed }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

This is a safety gate -- we never deploy a model that didn't pass Gate A.

---

## 8.6 Wire Node 3: prepare_deploy

Connected to **true** output.

1. Add a **Code** node → rename to `prepare_deploy`
2. Code:

```javascript
const body = $('webhook_deploy').first().json.body;

const run_id = body.run_id;
const onnx_source = body.checkpoint_path ||
  `/media/rusty_admin/project_data/ml_models/efficientnet/${run_id}/best_model.onnx`;

const engine_path = '/opt/reachy/models/emotion_classifier.engine';
const backup_path = engine_path + '.bak';
const onnx_tmp = '/tmp/emotion_classifier.onnx';

return [{
  json: {
    run_id,
    onnx_source,
    onnx_tmp,
    engine_path,
    backup_path,
    deployment_stage: 'shadow',
    jetson_host: '10.0.4.150'
  }
}];
```

---

## 8.7 Wire Node 4: scp_onnx

This transfers the ONNX file from Ubuntu 1 to the Jetson.

1. Add an **SSH** node → rename to `scp_onnx`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Ubuntu1` |
| **Command** | *(see below)* |

```bash
scp {{ $json.onnx_source }} jetson@{{ $json.jetson_host }}:{{ $json.onnx_tmp }}
```

### Why SCP from Ubuntu 1?

The ONNX model is stored on Ubuntu 1 (the training server). We SSH into Ubuntu 1 and use SCP to push the file to the Jetson. This avoids routing the file through n8n (which would be slow for large files).

---

## 8.8 Wire Node 5: ssh_convert_trt

This runs TensorRT conversion on the Jetson.

1. Add an **SSH** node → rename to `ssh_convert_trt`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `SSH Jetson` |
| **Command** | *(see below)* |

```bash
# Backup current engine
if [ -f {{ $('prepare_deploy').item.json.engine_path }} ]; then
  cp {{ $('prepare_deploy').item.json.engine_path }} {{ $('prepare_deploy').item.json.backup_path }}
  echo "Backed up existing engine"
fi

# Convert ONNX to TensorRT
trtexec \
  --onnx={{ $('prepare_deploy').item.json.onnx_tmp }} \
  --saveEngine={{ $('prepare_deploy').item.json.engine_path }} \
  --fp16 \
  --minShapes=input:1x3x224x224 \
  --optShapes=input:4x3x224x224 \
  --maxShapes=input:8x3x224x224 \
  2>&1 | tail -5

echo "TensorRT conversion complete"
```

### TensorRT Parameters Explained

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `--fp16` | FP16 precision | Half-precision for faster inference on Jetson |
| `--minShapes` | `1x3x224x224` | Minimum batch size = 1 |
| `--optShapes` | `4x3x224x224` | Optimal batch size = 4 |
| `--maxShapes` | `8x3x224x224` | Maximum batch size = 8 |

The `3x224x224` matches EfficientNet-B0's input: 3 color channels, 224x224 pixels.

### Backup First

We always backup the current engine before replacing it. If anything goes wrong, we can restore it.

---

## 8.9 Wire Node 6: ssh_update_config

1. Add an **SSH** node → rename to `ssh_update_config`
2. Credential: `SSH Jetson`
3. Command:

```bash
# Update DeepStream config to point to new engine
sed -i 's|model-engine-file=.*|model-engine-file={{ $('prepare_deploy').item.json.engine_path }}|' \
  /opt/reachy/config/deepstream_emotion.txt

# Restart the emotion inference service
sudo systemctl restart reachy-emotion

echo "Service restarted with new engine"
```

---

## 8.10 Wire Node 7: wait_startup

1. Add a **Wait** node → rename to `wait_startup`

| Parameter | Value |
|-----------|-------|
| **Amount** | `30` |
| **Unit** | `Seconds` |

The Jetson needs time to load the TensorRT engine into GPU memory and stabilize inference.

---

## 8.11 Wire Node 8: ssh_verify

1. Add an **SSH** node → rename to `ssh_verify`
2. Credential: `SSH Jetson`
3. Command:

```bash
# Check service is running
SERVICE_STATUS=$(systemctl is-active reachy-emotion)

# Read runtime metrics
METRICS=$(cat /opt/reachy/metrics/emotion_metrics.json 2>/dev/null || echo '{}')

echo "{\"service_status\": \"${SERVICE_STATUS}\", \"metrics\": ${METRICS}}"
```

---

## 8.12 Wire Node 9: parse_verify

1. Add a **Code** node → rename to `parse_verify`
2. Code:

```javascript
const stdout = $input.first().json.stdout || '{}';
let data;
try {
  data = JSON.parse(stdout);
} catch (e) {
  data = { service_status: 'unknown', metrics: {} };
}

const service_active = data.service_status === 'active';
const fps = parseFloat(data.metrics?.fps || 0);
const latency_p50 = parseFloat(data.metrics?.latency_p50_ms || 999);

const gate_b = {
  service_active,
  fps_pass: fps >= 25,
  latency_pass: latency_p50 <= 120,
  passed: service_active && fps >= 25 && latency_p50 <= 120
};

const deploy = $('prepare_deploy').first().json;

return [{
  json: {
    run_id: deploy.run_id,
    engine_path: deploy.engine_path,
    backup_path: deploy.backup_path,
    gate_b,
    fps,
    latency_p50,
    service_active
  }
}];
```

---

## 8.13 Wire Node 10: if_gate_b

1. Add an **IF** node → rename to `if_gate_b`

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.gate_b.passed }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 8.14 Wire Node 11: emit_success

Connected to **true** output of `if_gate_b`.

1. Add an **HTTP Request** node → rename to `emit_success`

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `deployment.completed` |
| `run_id` | `{{ $json.run_id }}` |
| `engine_path` | `{{ $json.engine_path }}` |
| `fps` | `{{ $json.fps }}` |
| `latency_p50_ms` | `{{ $json.latency_p50 }}` |
| `stage` | `shadow` |

---

## 8.15 Wire Node 12: ssh_rollback

Connected to **false** output of `if_gate_b`.

1. Add an **SSH** node → rename to `ssh_rollback`
2. Credential: `SSH Jetson`
3. Command:

```bash
# Restore backup engine
if [ -f {{ $json.backup_path }} ]; then
  cp {{ $json.backup_path }} {{ $json.engine_path }}
  sudo systemctl restart reachy-emotion
  echo "Rolled back to previous engine"
else
  echo "ERROR: No backup engine found at {{ $json.backup_path }}"
fi
```

### Automatic Rollback

This is the safety net. If Gate B fails (service down, low FPS, high latency), the workflow automatically:
1. Restores the backup `.engine.bak` file
2. Restarts the service
3. The robot continues running with the previous model

---

## 8.16 Wire Node 13: emit_rollback

1. Add an **HTTP Request** node after `ssh_rollback` → rename to `emit_rollback`

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `deployment.rollback` |
| `run_id` | `{{ $json.run_id }}` |
| `reason` | `Gate B failed` |
| `gate_b_details` | `{{ JSON.stringify($('parse_verify').item.json.gate_b) }}` |

---

## 8.17 Wire Node 14: respond_failed

Connected to **false** output of `if_gate_passed` (node 2).

1. Add a **Respond to Webhook** → rename to `respond_failed`

| Parameter | Value |
|-----------|-------|
| **Response Code** | `412` |
| **Response Body** | `{"error": "Gate A not passed", "message": "Cannot deploy model that did not pass quality gates"}` |

---

## 8.18 Final Connection Map

```
webhook_deploy ──► if_gate_passed
                      │             │
                [false]            [true]
                   │                │
                   ▼                ▼
             respond_failed   prepare_deploy
                                    │
                                    ▼
                               scp_onnx
                                    │
                                    ▼
                            ssh_convert_trt
                                    │
                                    ▼
                          ssh_update_config
                                    │
                                    ▼
                             wait_startup
                                    │
                                    ▼
                             ssh_verify
                                    │
                                    ▼
                            parse_verify
                                    │
                                    ▼
                             if_gate_b
                            │          │
                      [pass]          [fail]
                         │               │
                         ▼               ▼
                    emit_success    ssh_rollback
                                        │
                                        ▼
                                  emit_rollback
```

---

## 8.19 Testing

### Test Deployment

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/agent/deployment/efficientnet/start \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "<run_id>",
    "checkpoint_path": "/path/to/best_model.onnx",
    "gate_a_passed": true
  }'
```

### Test Gate A Block

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/agent/deployment/efficientnet/start \
  -H "Content-Type: application/json" \
  -d '{"run_id": "test", "gate_a_passed": false}'
```

**Expected:** HTTP 412 Precondition Failed.

---

## 8.20 Key Concepts Learned

- **Two SSH credentials** in one workflow (Ubuntu 1 for SCP, Jetson for conversion/config)
- **SCP file transfer** between servers via SSH node
- **TensorRT conversion** with dynamic batch shapes
- **DeepStream configuration** updates via `sed`
- **Gate B validation** (runtime performance thresholds)
- **Automatic rollback** pattern for safe deployments
- **Safety-first design** -- Gate A check prevents unauthorized deployments

---

*Previous: [MODULE 07 -- Evaluation Agent](MODULE_07_EVALUATION_AGENT.md)*
*Next: [MODULE 09 -- Observability Agent](MODULE_09_OBSERVABILITY_AGENT.md)*
