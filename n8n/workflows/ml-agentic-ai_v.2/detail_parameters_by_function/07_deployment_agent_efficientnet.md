# Agent 7 — Deployment Agent EfficientNet-B0 (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-29

## Overview

The Deployment Agent promotes validated EfficientNet-B0 models from Ubuntu 1 to the Jetson Xavier NX edge device. It handles ONNX→TensorRT conversion, DeepStream configuration updates, service restarts, and Gate B validation (FPS ≥ 25, latency p50 ≤ 120ms). Automatic rollback is triggered if Gate B fails.

**Model:** `efficientnet-b0-hsemotion`  
**Target:** Jetson Xavier NX (10.0.4.150)

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: parse.verification | n8n-nodes-base.code | parse_verify |
| Code: prepare.deployment | n8n-nodes-base.code | prepare_deploy |
| HTTP: emit.rollback | n8n-nodes-base.httpRequest | emit_rollback |
| HTTP: emit.success | n8n-nodes-base.httpRequest | emit_success |
| IF: Gate_B.pass? | n8n-nodes-base.if | if_gate_b |
| IF: gate_a.passed? | n8n-nodes-base.if | if_gate_passed |
| SSH: convert.to_tensorrt | n8n-nodes-base.ssh | ssh_convert_trt |
| SSH: rollback | n8n-nodes-base.ssh | ssh_rollback |
| SSH: scp.onnx_to_jetson | n8n-nodes-base.ssh | scp_onnx |
| SSH: update.deepstream_config | n8n-nodes-base.ssh | ssh_update_config |
| SSH: verify.deployment | n8n-nodes-base.ssh | ssh_verify |
| Wait: 30s | n8n-nodes-base.wait | wait_startup |
| Webhook: deployment.start | n8n-nodes-base.webhook | webhook_deploy |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: deployment.start
    │
    ▼
IF: gate_a.passed?
    │
    └──► [True] ──► Code: prepare.deployment
                            │
                            ▼
                    SSH: scp.onnx_to_jetson (Ubuntu1 → Jetson)
                            │
                            ▼
                    SSH: convert.to_tensorrt (on Jetson)
                            │
                            ▼
                    SSH: update.deepstream_config (on Jetson)
                            │
                            ▼
                    Wait: 30s (service startup)
                            │
                            ▼
                    SSH: verify.deployment (on Jetson)
                            │
                            ▼
                    Code: parse.verification
                            │
                            ▼
                    IF: Gate_B.pass?
                            │
                            ├──► [True] ──► HTTP: emit.success
                            │
                            └──► [False] ──► SSH: rollback
                                                    │
                                                    ▼
                                            HTTP: emit.rollback
```

---

## Node Details

### 1. Webhook: deployment.start

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-600, 300]  
**Purpose:** Entry point for deployment requests.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests |
| `path` | `agent/deployment/efficientnet/start` | URL path |
| `responseMode` | `onReceived` | Respond immediately |
| `options.responseCode` | `202` | HTTP 202 Accepted |
| `webhookId` | `efficientnet-deploy-start` | Unique identifier |

#### Expected Input

```json
{
  "run_id": "efficientnet_b0_emotion_xxx",
  "gate_a_passed": true,
  "onnx_path": "/workspace/exports/xxx/model.onnx",
  "correlation_id": "string"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 2. IF: gate_a.passed?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [-400, 300]  
**Purpose:** Validates that Gate A passed before deployment.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.gate_a_passed}}` | Gate A result |
| `conditions.boolean[0].value2` | `true` | Expected pass |

#### Test Status: ✅ OPERATIONAL

---

### 3. Code: prepare.deployment

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-200, 200]  
**Purpose:** Prepares deployment paths and backup location.

#### JavaScript Code

```javascript
// Prepare deployment paths
const runId = $json.run_id;
const onnxPath = $json.onnx_path || 
  `/workspace/exports/${runId}/emotion_classifier_${runId}.onnx`;
const enginePath = `/opt/reachy/models/emotion_efficientnet.engine`;
const backupPath = `/opt/reachy/models/backup/emotion_efficientnet_b0_${Date.now()}.engine`;

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

#### Output Schema

```json
{
  "onnx_path": "/workspace/exports/xxx/emotion_classifier_xxx.onnx",
  "engine_path": "/opt/reachy/models/emotion_efficientnet.engine",
  "backup_path": "/opt/reachy/models/backup/emotion_efficientnet_b0_1701234567890.engine",
  "deployment_stage": "shadow"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 4. SSH: scp.onnx_to_jetson

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [0, 200]  
**Purpose:** Copies ONNX model from Ubuntu 1 to Jetson.

#### Command

```bash
scp {{$json.onnx_path}} jetson@10.0.4.150:/tmp/emotion_classifier.onnx
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `3` | SSH Ubuntu1 |

#### Test Status: ✅ OPERATIONAL

---

### 5. SSH: convert.to_tensorrt

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [200, 200]  
**Purpose:** Converts ONNX to TensorRT engine on Jetson.

#### Command

```bash
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

#### TensorRT Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `--fp16` | enabled | FP16 precision for speed |
| `--workspace` | 2048 MB | GPU workspace |
| `--minShapes` | 1x3x224x224 | Minimum batch size |
| `--optShapes` | 1x3x224x224 | Optimal batch size |
| `--maxShapes` | 8x3x224x224 | Maximum batch size |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `4` | SSH Jetson |

#### Test Status: ✅ OPERATIONAL

---

### 6. SSH: update.deepstream_config

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [400, 200]  
**Purpose:** Updates DeepStream config and restarts service.

#### Command

```bash
# Update DeepStream config to use new engine
sed -i 's|model-engine-file=.*|model-engine-file={{$json.engine_path}}|' \
  /opt/reachy/config/emotion_inference.txt

# Restart DeepStream service
sudo systemctl restart reachy-emotion
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `4` | SSH Jetson |

#### Related Files

| File | Purpose |
|------|---------|
| `/opt/reachy/config/emotion_inference.txt` | DeepStream pipeline config |
| `reachy-emotion.service` | Systemd service |

#### Test Status: ✅ OPERATIONAL

---

### 7. Wait: 30s

**Type:** `n8n-nodes-base.wait` (v1.1)  
**Position:** [600, 200]  
**Purpose:** Allows service to start and stabilize.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `amount` | `30` | Wait duration |
| `unit` | `seconds` | Time unit |

#### Test Status: ✅ OPERATIONAL

---

### 8. SSH: verify.deployment

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [800, 200]  
**Purpose:** Verifies service status and collects metrics.

#### Command

```bash
# Check service status and get metrics
systemctl is-active reachy-emotion && \
cat /var/log/reachy/emotion_metrics.json | tail -1
```

#### Expected Output

```
active
{"fps": 28.5, "latency_p50_ms": 95, "latency_p99_ms": 145, "gpu_mem_mb": 2100}
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `4` | SSH Jetson |

#### Test Status: ✅ OPERATIONAL

---

### 9. Code: parse.verification

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [1000, 200]  
**Purpose:** Parses verification results and validates Gate B.

#### JavaScript Code

```javascript
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

#### Gate B Requirements

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `service_active` | true | Service running |
| `fps` | ≥ 25 | Frames per second |
| `latency_p50_ms` | ≤ 120 | P50 latency in ms |
| `gpu_mem_mb` | ≤ 2500 | GPU memory (implicit) |

#### Output Schema

```json
{
  "service_active": true,
  "metrics": {
    "fps": 28.5,
    "latency_p50_ms": 95,
    "latency_p99_ms": 145,
    "gpu_mem_mb": 2100
  },
  "gate_b": {
    "service_active": true,
    "fps_ok": true,
    "latency_ok": true,
    "passed": true
  },
  "deployment_status": "success"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 10. IF: Gate_B.pass?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [1200, 200]  
**Purpose:** Routes based on Gate B validation.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.gate_b.passed}}` | Gate B result |
| `conditions.boolean[0].value2` | `true` | Expected pass |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True | Gate B passed | HTTP: emit.success |
| False | Gate B failed | SSH: rollback |

#### Test Status: ✅ OPERATIONAL

---

### 11. HTTP: emit.success

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1400, 100]  
**Purpose:** Emits deployment.completed event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `deployment.completed` | Event type |
| `run_id` | `={{$json.run_id}}` | Run ID |
| `model` | `efficientnet-b0-hsemotion` | Model |
| `engine_path` | `={{$json.engine_path}}` | Engine location |
| `fps` | `={{$json.metrics.fps}}` | Achieved FPS |
| `latency_p50_ms` | `={{$json.metrics.latency_p50_ms}}` | Achieved latency |
| `deployment_stage` | `shadow` | Deployment stage |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

### 12. SSH: rollback

**Type:** `n8n-nodes-base.ssh` (v1)  
**Position:** [1400, 300]  
**Purpose:** Rolls back to previous engine on Gate B failure.

#### Command

```bash
# Rollback to previous engine
if [ -f {{$json.backup_path}} ]; then
  cp {{$json.backup_path}} {{$json.engine_path}}
  sudo systemctl restart reachy-emotion
fi
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `sshPassword` | `4` | SSH Jetson |

#### Test Status: ✅ OPERATIONAL

---

### 13. HTTP: emit.rollback

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1600, 300]  
**Purpose:** Emits deployment.rollback event.

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `deployment.rollback` | Event type |
| `run_id` | `={{$json.run_id}}` | Run ID |
| `reason` | Gate B failed - performance requirements not met | Reason |
| `metrics` | `={{JSON.stringify($json.metrics)}}` | Failed metrics |

#### Test Status: ⚠️ TBD (requires events endpoint)

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `GATEWAY_BASE_URL` | Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 3 | SSH Ubuntu1 | SSH Password | Source server |
| 4 | SSH Jetson | SSH Password | Target device |

---

## Tags

- `agent`
- `deployment`
- `efficientnet`
- `ml-v1`

---

## Deployment Stages

| Stage | Description | Approval |
|-------|-------------|----------|
| `shadow` | Initial deployment, monitoring only | Automatic |
| `canary` | Limited traffic (future) | Manual |
| `rollout` | Full production (future) | Manual |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `/api/events/deployment` |
| Canary Stage | MEDIUM | Implement canary deployment logic |
| Rollout Stage | MEDIUM | Implement full rollout with approval |
| GPU Memory Check | LOW | Add GPU memory to Gate B |

---

## Connections Summary

```json
{
  "webhook_deploy": { "main": [["if_gate_passed"]] },
  "if_gate_passed": { "main": [["prepare_deploy"]] },
  "prepare_deploy": { "main": [["scp_onnx"]] },
  "scp_onnx": { "main": [["ssh_convert_trt"]] },
  "ssh_convert_trt": { "main": [["ssh_update_config"]] },
  "ssh_update_config": { "main": [["wait_startup"]] },
  "wait_startup": { "main": [["ssh_verify"]] },
  "ssh_verify": { "main": [["parse_verify"]] },
  "parse_verify": { "main": [["if_gate_b"]] },
  "if_gate_b": { "main": [["emit_success"], ["ssh_rollback"]] },
  "ssh_rollback": { "main": [["emit_rollback"]] }
}
```
