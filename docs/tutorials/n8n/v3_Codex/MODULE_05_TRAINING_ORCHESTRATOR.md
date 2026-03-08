# Training Orchestrator (EfficientNet) (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/05_training_orchestrator_efficientnet.json`

## Objective
Launch and monitor EfficientNet-B0 training runs, enforce Gate A preconditions, and emit training events.

## Related Backend Scripts and Functionalities
- `trainer/run_efficientnet_pipeline.py`: Training pipeline runner invoked via SSH command.
- `apps/api/routers/gateway.py`: `/api/training/status/{id}` proxy and `/api/events/training` event sink.
- `apps/api/app/routers/gateway_upstream.py`: Persists training status snapshots consumed by polling nodes.

## What Changed vs Legacy Module
- Explicitly set HTTP methods (`POST`) for MLflow and gateway event nodes for deterministic behavior.
- Kept train-balance gate (`>=50` per class) to align 3-class data readiness requirement.
- Retained status polling loop against `/api/training/status/{run_id}` and `/latest`.
- Preserved event emissions for `completed`, `gate_failed`, and `insufficient_data`.
- No endpoint path changes were required in this workflow.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Webhook: training.start` | `Webhook` | `Webhook` start trigger for training agent. |
| `Postgres: check.train_balance` | `Postgres` | `Postgres` node verifying happy/sad/neutral training counts. |
| `IF: sufficient_data?` | `If` | `If` data-readiness gate. |
| `HTTP: mlflow.create_run` | `HTTP Request` | `HTTP Request` creating MLflow run context. |
| `Code: prepare.training` | `Code` | `Code` node generating run ID, config path, output path, and gateway base. |
| `SSH: start.training` | `SSH` | `SSH` node launching trainer pipeline process. |
| `Wait: 5min` | `Wait` | `Wait` polling interval. |
| `SSH: check.status` | `SSH` | `SSH` node fetching persisted status snapshots. |
| `Code: parse.results` | `Code` | `Code` parser for training status and gate metrics. |
| `IF: training.done?` | `If` | `If` loop/exit decision for polling cycle. |
| `IF: Gate_A.pass?` | `If` | `If` gate on Gate A pass/fail outcome. |
| `HTTP: mlflow.log_gate` | `HTTP Request` | `HTTP Request` metric log for Gate A result. |
| `HTTP: emit.completed` | `HTTP Request` | `HTTP Request` completion event to gateway. |
| `HTTP: emit.gate_failed` | `HTTP Request` | `HTTP Request` failure event to gateway. |
| `HTTP: emit.insufficient_data` | `HTTP Request` | `HTTP Request` blocked event when data threshold not met. |

## How This Workflow Delivers Code-Level Functionality
1. Data sufficiency gate ensures training only starts when class counts satisfy minimum constraints.
2. Training launch command runs project trainer script with run-specific output paths and strict contract updates.
3. Poll loop reads persisted status contracts from gateway/media APIs rather than parsing raw process state.
4. Gate A branch controls whether training run is marked promotable for downstream deployment.
5. Event emissions feed orchestration and observability pipelines with run outcomes.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
