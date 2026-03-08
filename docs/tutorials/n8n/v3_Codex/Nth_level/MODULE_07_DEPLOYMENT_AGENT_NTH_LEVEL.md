# MODULE 07 — Deployment Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/07_deployment_agent_efficientnet.json`

## Runtime Goal
Deploy ONNX to Jetson (TensorRT/DeepStream), verify Gate B runtime constraints, and rollback automatically on failure.

## Node-to-Script Map

### 1) `Webhook: deployment.start` (`Webhook`)
- **Workflow role:** deployment trigger.
- **Path/method:** `POST /webhook/agent/deployment/efficientnet/start`.

### 2) `IF: gate_a.passed?` (`If`)
- **Workflow role:** hard gate before deployment.
- **Expression:** `{{$json.gate_a_passed}} == true`.

### 3) `Code: prepare.deployment` (`Code`)
- **Workflow role:** prepares artifact paths and stage metadata.
- **Essential in-node logic:**
- derives ONNX path fallback from run id
- sets target engine path (`/opt/reachy/models/emotion_efficientnet.engine`)
- creates backup path with timestamp
- marks deployment stage as `shadow`

### 4) `SSH: scp.onnx_to_jetson` (`SSH`)
- **Workflow role:** transfers ONNX to Jetson temp path.
- **Command:** `scp {{$json.onnx_path}} jetson@10.0.4.150:/tmp/emotion_classifier.onnx`.

### 5) `SSH: convert.to_tensorrt` (`SSH`)
- **Workflow role:** backup existing engine + build TensorRT engine.
- **Command behavior:**
- if engine exists, copy to backup
- run `trtexec --onnx ... --saveEngine ... --fp16 ...`
- **Output artifact:** new `.engine` file at configured engine path.

### 6) `SSH: update.deepstream_config` (`SSH`)
- **Workflow role:** switch DeepStream model-engine-file and restart service.
- **Command behavior:** `sed -i ... emotion_inference.txt` then `systemctl restart reachy-emotion`.

### 7) `Wait: 30s` (`Wait`)
- **Workflow role:** warm-up delay before verification check.

### 8) `SSH: verify.deployment` (`SSH`)
- **Workflow role:** service and performance probe.
- **Command behavior:**
- checks `systemctl is-active reachy-emotion`
- reads last JSON line from `/var/log/reachy/emotion_metrics.json`

### 9) `Code: parse.verification` (`Code`)
- **Workflow role:** converts verification output to Gate B decision.
- **Essential in-node logic:**
- parses service active status + metrics JSON
- computes `gate_b` booleans:
- `service_active`
- `fps_ok` (>=25)
- `latency_ok` (`latency_p50_ms` <=120)
- sets `deployment_status` success/failed

### 10) `IF: Gate_B.pass?` (`If`)
- **Workflow role:** deployment success vs rollback branch.

### 11) `HTTP: emit.success` (`HTTP Request`)
- **Workflow role:** emits `deployment.completed` event.
- **HTTP target:** `POST {{$env.GATEWAY_BASE_URL}}/api/events/deployment`
- **Backend binding:** `apps/api/routers/gateway.py:331` `post_deployment_event(...)`.

### 12) `SSH: rollback` (`SSH`)
- **Workflow role:** restores previous engine and restarts service when Gate B fails.

### 13) `HTTP: emit.rollback` (`HTTP Request`)
- **Workflow role:** emits `deployment.rollback` event with metrics payload.

## How This Delivers Deployment Functionality
1. Blocks deployment unless upstream Gate A pass is explicit.
2. Copies ONNX, compiles TensorRT FP16 engine, updates DeepStream runtime.
3. Verifies runtime service + performance and enforces Gate B.
4. Rolls back engine automatically if Gate B fails.

## Script/Model Alignment Notes
- This workflow emits deployment events but does not call deployment status persistence endpoints (`apps/api/app/routers/gateway_upstream.py:617`), so `DeploymentLog` may remain underutilized unless another path writes it.
- AGENTS policy also mentions GPU memory gate; current `parse.verification` logic checks service/fps/latency only.
