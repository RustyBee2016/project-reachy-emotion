# Evaluation Agent (EfficientNet) (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/06_evaluation_agent_efficientnet.json`

## Objective
Run evaluation-only jobs, compute Gate A metrics on test data, and publish evaluation status.

## Related Backend Scripts and Functionalities
- `trainer/run_efficientnet_pipeline.py`: Invoked with `--skip-train` for evaluation-only mode.
- `apps/api/routers/gateway.py`: `/api/training/status/{id}` and `/api/events/pipeline` used by v3 event flow.
- `apps/api/app/routers/gateway_upstream.py`: Stores status payload posted by blocked-status node.

## What Changed vs Legacy Module
- Evaluation completion/failure events moved from missing `/api/events/evaluation` to implemented `/api/events/pipeline`.
- Added `pipeline_id` mapping to event payloads so pipeline event sink has a stable key.
- Set explicit `POST` method for status-blocked and all outbound HTTP nodes.
- Kept test-balance gate (`>=20` per class) and gate metric extraction logic.
- Maintained MLflow metric logging via log-batch endpoint.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: evaluation.start` | `Webhook` | `Webhook` trigger for evaluation start. |
| `Postgres: check.test_balance` | `Postgres` | `Postgres` node checking per-class test counts. |
| `IF: test_set.balanced?` | `If` | `If` node gating execution on test readiness. |
| `Code: prepare.evaluation` | `Code` | `Code` node preparing run/checkpoint/output context. |
| `SSH: run.evaluation` | `SSH` | `SSH` node invoking pipeline runner in evaluation mode. |
| `Code: parse.results` | `Code` | `Code` parser computing gate metrics and pass state. |
| `HTTP: mlflow.log_metrics` | `HTTP Request` | `HTTP Request` to MLflow `runs/log-batch`. |
| `IF: Gate_A.pass?` | `If` | `If` node routing pass/fail event branch. |
| `HTTP: emit.completed` | `HTTP Request` | `HTTP Request` posting evaluation completion into pipeline events. |
| `HTTP: emit.gate_failed` | `HTTP Request` | `HTTP Request` posting evaluation failure into pipeline events. |
| `Code: prepare.blocked_status` | `Code` | `Code` node building blocked-status payload for insufficient test data. |
| `HTTP: status.blocked` | `HTTP Request` | `HTTP Request` writing blocked status to training status API. |

## How This Workflow Delivers Code-Level Functionality
1. Test-balance gate blocks evaluation when happy/sad/neutral test minima are unmet.
2. Evaluation run executes with `--skip-train`, reusing common runner and status-contract plumbing.
3. Metrics are logged to MLflow for traceable quality and calibration evidence.
4. Completion/failure events use pipeline endpoint so they are accepted by current gateway implementation.
5. Blocked status is persisted to training-status API for UI visibility and operator diagnostics.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
