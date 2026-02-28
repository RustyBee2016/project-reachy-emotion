# Module 8: Deployment Agent — Edge Deployment, TensorRT & Rollback

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~4 hours  
**Prerequisites**: Completed Modules 0-7

---

## Learning Objectives

By the end of this module, you will:
1. Transfer models between servers using **SCP**
2. Convert **ONNX to TensorRT** for edge optimization
3. Update **DeepStream configuration** files
4. Validate **Gate B requirements** (FPS, latency)
5. Implement **automatic rollback** on failure

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **SCP transfer** | SSH node with scp | Model deployment |
| **TensorRT conversion** | trtexec command | Edge optimization |
| **Config file updates** | sed command | Pipeline configuration |
| **Service restart** | systemctl | Apply changes |
| **Rollback pattern** | Backup + restore | Safety net |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Webhook: deployment.start | n8n webhook | ⬜ (native) |
| 2 | IF: gate_a.passed? | n8n conditional | ⬜ (native) |
| 3 | Code: prepare.deployment | JavaScript | ⬜ (native) |
| 4 | SSH: scp.onnx_to_jetson | SCP from Ubuntu1 | ⬜ |
| 5 | SSH: convert.to_tensorrt | trtexec on Jetson | ⬜ |
| 6 | SSH: update.deepstream_config | sed on Jetson | ⬜ |
| 7 | Wait: 30s | n8n Wait | ⬜ (native) |
| 8 | SSH: verify.deployment | systemctl on Jetson | ⬜ |
| 9 | Code: parse.verification | JavaScript | ⬜ (native) |
| 10 | IF: Gate_B.pass? | n8n conditional | ⬜ (native) |
| 11 | SSH: rollback | File restore on Jetson | ⬜ |
| 12-13 | HTTP: emit.* | Gateway events | ⬜ |

---

### Verification Procedures

#### Test 1: SSH to Jetson

```bash
# From Ubuntu1
ssh jetson@10.0.4.150 'echo "Jetson SSH OK"'
```

**⚠️ Note**: Jetson may not be available during development. You can:
1. Skip Jetson-related nodes
2. Mock with Ubuntu1 as target
3. Set "Continue On Fail" on Jetson nodes

**Status**: ⬜ → [ ] Complete (or N/A)

---

#### Test 2: TensorRT Available on Jetson

```bash
ssh jetson@10.0.4.150 'ls /usr/src/tensorrt/bin/trtexec'
```

**Status**: ⬜ → [ ] Complete (or N/A)

---

#### Test 3: DeepStream Config Path

```bash
ssh jetson@10.0.4.150 'ls /opt/reachy/config/emotion_inference.txt'
```

**Status**: ⬜ → [ ] Complete (or N/A)

---

## Part 1: Understanding Edge Deployment

### Deployment Pipeline

```
Ubuntu 1 (Training Server)          Jetson Xavier NX (Edge Device)
┌─────────────────────────┐        ┌─────────────────────────────┐
│                         │        │                             │
│  ONNX Model             │  SCP   │  /tmp/emotion_classifier.onnx│
│  /workspace/exports/... │ ─────► │                             │
│                         │        │         trtexec              │
└─────────────────────────┘        │            ▼                │
                                   │  TensorRT Engine            │
                                   │  /opt/reachy/models/        │
                                   │            ▼                │
                                   │  DeepStream Pipeline        │
                                   │  (reachy-emotion service)   │
                                   └─────────────────────────────┘
```

### Gate B Requirements

| Metric | Threshold | Why |
|--------|-----------|-----|
| Service Active | true | Basic health |
| FPS | ≥ 25 | Real-time requirement |
| Latency P50 | ≤ 120ms | Responsive interaction |
| GPU Memory | ≤ 2.5GB | Resource constraint |

### Rollback Strategy

1. **Before deployment**: Backup existing engine
2. **After deployment**: Check Gate B
3. **If Gate B fails**: Restore backup, restart service
4. **Emit event**: Notify of rollback

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 7 — Deployment Agent EfficientNet-B0 (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add Webhook Trigger

**Node Name**: `Webhook: deployment.start`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `agent/deployment/efficientnet/start` |
| Response Mode | `When Last Node Finishes` |
| Response Code | `202` |

**Expected Input**:
```json
{
  "run_id": "efficientnet_b0_emotion_xxx",
  "gate_a_passed": true,
  "onnx_path": "/workspace/exports/xxx/model.onnx",
  "correlation_id": "string"
}
```

---

### Step 3: Add Gate A Validation

**Node Name**: `IF: gate_a.passed?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.gate_a_passed}}` |
| Operation | `Is True` |

**Why check again?** Defense in depth — ensure only validated models deploy.

---

### Step 4: Add Deployment Preparation

**Node Name**: `Code: prepare.deployment`

```javascript
// Prepare deployment paths
const runId = $json.run_id;
const onnxPath = $json.onnx_path || 
  `/home/rusty_admin/projects/reachy_08.4.2/experiments/${runId}/model.onnx`;

const timestamp = Date.now();
const enginePath = '/opt/reachy/models/emotion_efficientnet.engine';
const backupPath = `/opt/reachy/models/backup/emotion_efficientnet_${timestamp}.engine`;

return [{
  json: {
    ...$json,
    onnx_path: onnxPath,
    engine_path: enginePath,
    backup_path: backupPath,
    config_path: '/opt/reachy/config/emotion_inference.txt',
    model_placeholder: 'efficientnet-b0-hsemotion',
    deployment_stage: 'shadow',
    jetson_host: '10.0.4.150',
    jetson_user: 'jetson'
  }
}];
```

---

### Step 5: Add SCP Transfer

**Node Name**: `SSH: scp.onnx_to_jetson`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Ubuntu1` |

**Command**:
```bash
scp {{$json.onnx_path}} {{$json.jetson_user}}@{{$json.jetson_host}}:/tmp/emotion_classifier.onnx
```

**Note**: This executes FROM Ubuntu1, pushing TO Jetson.

---

### Step 6: Add TensorRT Conversion

**Node Name**: `SSH: convert.to_tensorrt`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Jetson` |

**Command**:
```bash
# Backup existing engine if present
if [ -f {{$json.engine_path}} ]; then
  mkdir -p /opt/reachy/models/backup
  cp {{$json.engine_path}} {{$json.backup_path}}
  echo "Backup created: {{$json.backup_path}}"
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

echo "Conversion complete"
```

**TensorRT Parameters Explained**:
| Parameter | Purpose |
|-----------|---------|
| `--fp16` | Use FP16 precision (2x faster, minimal accuracy loss) |
| `--workspace=2048` | 2GB GPU memory for optimization |
| `--minShapes` | Minimum input batch size |
| `--optShapes` | Optimal (most common) batch size |
| `--maxShapes` | Maximum batch size |

---

### Step 7: Add Config Update

**Node Name**: `SSH: update.deepstream_config`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Jetson` |

**Command**:
```bash
# Update DeepStream config to use new engine
sed -i 's|model-engine-file=.*|model-engine-file={{$json.engine_path}}|' {{$json.config_path}}

# Restart DeepStream service
sudo systemctl restart reachy-emotion

echo "Service restarted"
```

---

### Step 8: Add Startup Wait

**Node Name**: `Wait: 30s`

| Parameter | Value |
|-----------|-------|
| Amount | `30` |
| Unit | `Seconds` |

**Why 30 seconds?** DeepStream needs time to:
1. Load TensorRT engine
2. Initialize CUDA context
3. Start processing pipeline

---

### Step 9: Add Deployment Verification

**Node Name**: `SSH: verify.deployment`

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Jetson` |

**Command**:
```bash
# Check service status
SERVICE_STATUS=$(systemctl is-active reachy-emotion)

# Get latest metrics
if [ "$SERVICE_STATUS" = "active" ]; then
  METRICS=$(cat /var/log/reachy/emotion_metrics.json | tail -1)
else
  METRICS='{"fps": 0, "latency_p50_ms": 999, "error": "service not active"}'
fi

echo "$SERVICE_STATUS"
echo "$METRICS"
```

---

### Step 10: Add Verification Parser

**Node Name**: `Code: parse.verification`

```javascript
// Parse verification results
const output = $json.stdout || '';
const lines = output.trim().split('\n');
const serviceActive = lines[0] === 'active';

let metrics = {};
try {
  metrics = JSON.parse(lines[1] || '{}');
} catch (e) {
  metrics = { fps: 0, latency_p50_ms: 999, error: 'parse failed' };
}

// Check Gate B requirements
const gateB = {
  service_active: serviceActive,
  fps_ok: metrics.fps >= 25,
  latency_ok: metrics.latency_p50_ms <= 120,
  gpu_mem_ok: (metrics.gpu_mem_mb || 0) <= 2500,
  passed: false
};

gateB.passed = gateB.service_active && 
               gateB.fps_ok && 
               gateB.latency_ok;

return [{
  json: {
    ...$('Code: prepare.deployment').item.json,
    service_active: serviceActive,
    metrics: metrics,
    gate_b: gateB,
    deployment_status: gateB.passed ? 'success' : 'failed'
  }
}];
```

---

### Step 11: Add Gate B Decision

**Node Name**: `IF: Gate_B.pass?`

| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.gate_b.passed}}` |
| Operation | `Is True` |

---

### Step 12: Add Rollback (Gate B Failed)

**Node Name**: `SSH: rollback`

Connect: IF Gate_B.pass? (False branch) → rollback

| Parameter | Value |
|-----------|-------|
| Credential | `SSH Jetson` |

**Command**:
```bash
# Rollback to previous engine
if [ -f {{$json.backup_path}} ]; then
  cp {{$json.backup_path}} {{$json.engine_path}}
  sudo systemctl restart reachy-emotion
  echo "Rollback complete"
else
  echo "No backup available"
fi
```

---

### Step 13: Add Event Emissions

**Node Name**: `HTTP: emit.success`

Connect: IF Gate_B.pass? (True branch) → emit.success

```json
{
  "event_type": "deployment.completed",
  "run_id": "={{$json.run_id}}",
  "model": "efficientnet-b0-hsemotion",
  "engine_path": "={{$json.engine_path}}",
  "fps": "={{$json.metrics.fps}}",
  "latency_p50_ms": "={{$json.metrics.latency_p50_ms}}",
  "deployment_stage": "shadow"
}
```

**Node Name**: `HTTP: emit.rollback`

Connect: rollback → emit.rollback

```json
{
  "event_type": "deployment.rollback",
  "run_id": "={{$json.run_id}}",
  "reason": "Gate B failed - performance requirements not met",
  "metrics": "={{JSON.stringify($json.metrics)}}",
  "gate_b": "={{JSON.stringify($json.gate_b)}}"
}
```

---

## Part 3: Connection Summary

```
webhook_deploy
       │
       ▼
if_gate_a_passed ──[False]──► (end - no deployment)
       │
    [True]
       │
       ▼
prepare_deploy
       │
       ▼
scp_onnx
       │
       ▼
convert_trt
       │
       ▼
update_config
       │
       ▼
wait_30s
       │
       ▼
verify_deploy
       │
       ▼
parse_verify
       │
       ▼
if_gate_b
  │         │
[True]   [False]
  │         │
  ▼         ▼
emit_success   rollback
               │
               ▼
            emit_rollback
```

---

## Part 4: Testing Without Jetson

If Jetson is unavailable, you can mock the deployment:

### Mock Deployment on Ubuntu1

1. Create mock directories:
```bash
mkdir -p /tmp/mock_jetson/opt/reachy/{models,config}
echo '{"fps": 30, "latency_p50_ms": 80, "gpu_mem_mb": 2000}' > /tmp/mock_metrics.json
```

2. Modify SSH commands to use local paths instead of Jetson SSH

3. Set "Continue On Fail" on Jetson SSH nodes

---

## Module 8 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| SCP transfer | `scp source user@host:dest` |
| TensorRT conversion | `trtexec --onnx --saveEngine` |
| Config updates | `sed -i 's|old|new|'` |
| Service management | `systemctl restart` |
| Rollback | Backup → Try → Restore if fail |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: deployment.start | Webhook | Entry point |
| 2 | IF: gate_a.passed? | IF | Pre-deployment check |
| 3 | Code: prepare.deployment | Code | Setup paths |
| 4 | SSH: scp.onnx_to_jetson | SSH | Transfer model |
| 5 | SSH: convert.to_tensorrt | SSH | Edge optimization |
| 6 | SSH: update.deepstream_config | SSH | Config + restart |
| 7 | Wait: 30s | Wait | Startup time |
| 8 | SSH: verify.deployment | SSH | Health check |
| 9 | Code: parse.verification | Code | Parse + Gate B |
| 10 | IF: Gate_B.pass? | IF | Performance gate |
| 11 | SSH: rollback | SSH | Restore backup |
| 12-13 | HTTP: emit.* | HTTP Request | Events |

---

## Next Steps

Proceed to **Module 9: Observability Agent** where you'll learn:
- **High-frequency polling** (30-second intervals)
- **Prometheus metrics parsing**
- **Multi-source aggregation**
- **Time-series storage**

---

*Module 8 Complete — Proceed to Module 9: Observability Agent*
