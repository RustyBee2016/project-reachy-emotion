# Deployment Agent (EfficientNet) (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/07_deployment_agent_efficientnet.json`

## Objective
Deploy validated ONNX exports to Jetson as TensorRT engines with Gate B validation and rollback support.

## Related Backend Scripts and Functionalities
- `n8n/workflows/ml-agentic-ai_v.3/07_deployment_agent_efficientnet.json`: Contains SCP/TensorRT/DeepStream operational commands.
- `apps/api/routers/gateway.py`: Receives deployment events on `/api/events/deployment`.

## What Changed vs Legacy Module
- Updated engine path constants from `emotion_resnet50.engine` to `emotion_efficientnet.engine` to match project model target.
- Updated backup naming to `emotion_efficientnet_*` for consistent rollback artifacts.
- Kept Gate B checks (`fps`, `latency_p50_ms`, service active) unchanged.
- Kept rollback branch wired to backup restoration command and rollback event emission.
- Set explicit `POST` methods for deployment event HTTP nodes.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: deployment.start` | `Webhook` | `Webhook` entrypoint for deployment requests. |
| `IF: gate_a.passed?` | `If` | `If` gate preventing deployment before Gate A success. |
| `Code: prepare.deployment` | `Code` | `Code` node assembling ONNX/engine/backup path variables. |
| `SSH: scp.onnx_to_jetson` | `SSH` | `SSH` node copying ONNX artifact to Jetson. |
| `SSH: convert.to_tensorrt` | `SSH` | `SSH` node converting ONNX to TensorRT FP16 engine. |
| `SSH: update.deepstream_config` | `SSH` | `SSH` node patching DeepStream config and restarting service. |
| `Wait: 30s` | `Wait` | `Wait` warm-up interval before verification. |
| `SSH: verify.deployment` | `SSH` | `SSH` node checking service health and runtime metrics. |
| `Code: parse.verification` | `Code` | `Code` node evaluating Gate B pass/fail booleans. |
| `IF: Gate_B.pass?` | `If` | `If` success vs rollback branch. |
| `HTTP: emit.success` | `HTTP Request` | `HTTP Request` deployment success event. |
| `SSH: rollback` | `SSH` | `SSH` rollback command to restore previous engine. |
| `HTTP: emit.rollback` | `HTTP Request` | `HTTP Request` rollback event. |

## How This Workflow Delivers Code-Level Functionality
1. Gate A prerequisite prevents unvalidated models from reaching Jetson deployment stages.
2. SCP + TensorRT conversion chain materializes deployable engine from ONNX export on target hardware.
3. DeepStream config update switches runtime inference to the new engine artifact.
4. Verification parser enforces Gate B runtime thresholds before rollout continuation.
5. Rollback branch restores prior engine automatically when Gate B fails.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
