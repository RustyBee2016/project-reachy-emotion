# n8n Agent Node Reference v3 (Agents 1-9)

Source workflows:
- `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`
- `n8n/workflows/ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`
- `n8n/workflows/ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`
- `n8n/workflows/ml-agentic-ai_v.2/08_privacy_agent.json`
- `n8n/workflows/ml-agentic-ai_v.2/09_observability_agent.json`

## Agent 1: Ingest Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: ingest.video` | `webhook` | Receives ingest POST requests on `video_gen_hook` and returns `202` immediately (`onReceived`) so ingestion can run asynchronously. |
| 2 | `IF: auth.check` | `if` | Validates `x-ingest-key` header against `INGEST_TOKEN` env; routes authorized vs unauthorized traffic. |
| 3 | `Code: normalize.payload` | `code` | Normalizes payload variants into one schema: extracts `source_url`, optional label/meta, injects `correlation_id` and `idempotency_key`. |
| 4 | `HTTP: media.pull` | `httpRequest` | Calls Media Mover pull endpoint to download/register video and begin ingest processing. |
| 5 | `Wait: 3s` | `wait` | Adds polling delay between status checks. |
| 6 | `HTTP: check.status` | `httpRequest` | Polls status URL returned by pull endpoint. |
| 7 | `IF: status.done?` | `if` | Branches by status: `done` proceeds to DB insert, otherwise loops to retry path. |
| 8 | `Postgres: insert.video` | `postgres` | Inserts metadata into `video` table (`temp` split, ffprobe stats, hash, size) with conflict guard on `(sha256, size_bytes)`. |
| 9 | `HTTP: emit.completed` | `httpRequest` | Emits `ingest.completed` event to gateway `/api/events/ingest`. |
| 10 | `Respond: success` | `respondToWebhook` | Returns success JSON response to caller. |
| 11 | `Respond: 401 Unauthorized` | `respondToWebhook` | Returns explicit unauthorized response if auth check fails. |
| 12 | `Code: increment.attempt` | `code` | Increments polling attempt count and fails if max attempts reached; loops back to `Wait: 3s`. |

## Agent 2: Labeling Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: label.submitted` | `webhook` | Receives labeling requests on `label`; waits for workflow completion (`responseNode`) before replying. |
| 2 | `Code: validate.payload` | `code` | Validates/normalizes `video_id`, label (`happy/sad/neutral`), action (`label_only/promote_train/promote_test/discard`), and idempotency metadata. |
| 3 | `Postgres: fetch.video` | `postgres` | Fetches current video state from DB (`split`, current label, file path). |
| 4 | `Postgres: apply.label` | `postgres` | Writes idempotent label event to `label_event`, updates `video.label`, returns updated row and event ID. |
| 5 | `Switch: branch.action` | `switch` | Routes per action: relabel-only, promote to train/test, or discard flow. |
| 6 | `HTTP: mm.relabel` | `httpRequest` | Calls Media Mover relabel endpoint to sync filesystem/service metadata with DB label update. |
| 7 | `HTTP: mm.promote` | `httpRequest` | Calls Media Mover promote endpoint for `promote_train` or `promote_test`. |
| 8 | `Postgres: class.balance` | `postgres` | Computes training class counts (`happy/sad/neutral`) and total to update UI balancing state. |
| 9 | `Respond: success` | `respondToWebhook` | Returns consolidated success payload to label caller. |

## Agent 3: Promotion / Curation Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: request.promotion` | `webhook` | Receives promotion request on `promotion/v1` and keeps response open (`responseNode`) for gated completion flow. |
| 2 | `Code: validate.request` | `code` | Validates required fields (`video_id`, `label`), resolves target split, generates stable idempotency key, and forces dry-run first. |
| 3 | `HTTP: dryrun.promote` | `httpRequest` | Executes dry-run promotion plan against Media Mover (no state mutation expected). |
| 4 | `Code: summarize.plan` | `code` | Builds human-readable approval payload summarizing move plan, conflicts, and DB effects. |
| 5 | `Webhook: await.approval` | `webhook` | Waits for separate approval webhook call on `promotion/approve` (human-in-the-loop gate). |
| 6 | `IF: approved?` | `if` | Branches approved vs rejected decisions. |
| 7 | `HTTP: real.promote` | `httpRequest` | Executes real promotion after approval using same idempotency context. |
| 8 | `HTTP: rebuild.manifest` | `httpRequest` | Triggers manifest rebuild for `train` and `test` splits after promotion. |
| 9 | `HTTP: emit.completed` | `httpRequest` | Emits promotion completion event to gateway. |
| 10 | `Respond: success` | `respondToWebhook` | Returns success response for approved/finished path. |
| 11 | `Respond: rejected` | `respondToWebhook` | Returns `403` response when approval denied. |

## Agent 4: Reconciler / Audit Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Schedule: daily 02:15` | `scheduleTrigger` | Runs automatic daily reconciliation cycle (cron expression `15 2 * * *`). |
| 2 | `Webhook: manual.trigger` | `webhook` | Provides on-demand reconciliation trigger at `reconciler/audit`. |
| 3 | `Set: config` | `set` | Defines runtime config fields such as root dir and safety flags. |
| 4 | `SSH: scan.filesystem` | `ssh` | Scans video tree and emits JSONL of file path, size, and mtime for `.mp4` files. |
| 5 | `Code: parse.fs_scan` | `code` | Parses SSH JSONL output into normalized n8n items annotated with inferred split. |
| 6 | `Postgres: fetch.all_videos` | `postgres` | Reads authoritative DB inventory for all videos. |
| 7 | `Code: diff.fs_db` | `code` | Computes orphans (FS-only), missing (DB-only), and metadata mismatches; produces reconciliation summary. |
| 8 | `IF: drift.found?` | `if` | Checks whether drift exists and gates alerting path. |
| 9 | `Email: send.report` | `emailSend` | Sends reconciliation report when drift is detected. |

## Agent 5: Training Orchestrator (EfficientNet)
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: training.start` | `webhook` | Receives training start request at `agent/training/efficientnet/start` and responds immediately with `202`. |
| 2 | `Postgres: check.train_balance` | `postgres` | Counts train samples per class (`happy/sad/neutral`) to enforce minimum data threshold. |
| 3 | `IF: sufficient_data?` | `if` | Requires minimum per-class train count (>= 50) before launch. |
| 4 | `HTTP: mlflow.create_run` | `httpRequest` | Creates MLflow run and sets run tags/metadata for training tracking. |
| 5 | `Code: prepare.training` | `code` | Generates run ID and prepares pipeline paths/config for EfficientNet 3-class run. |
| 6 | `SSH: start.training` | `ssh` | Launches training pipeline process in workspace and writes logs to run-specific output dir. |
| 7 | `Wait: 5min` | `wait` | Poll interval while job is running. |
| 8 | `SSH: check.status` | `ssh` | Pulls run status and latest status snapshots from gateway training status APIs. |
| 9 | `Code: parse.results` | `code` | Parses status snapshots, determines running/completed state, and extracts key metrics and Gate A data. |
| 10 | `IF: training.done?` | `if` | Loops until run state indicates completion. |
| 11 | `IF: Gate_A.pass?` | `if` | Branches on Gate A pass/fail outcome. |
| 12 | `HTTP: mlflow.log_gate` | `httpRequest` | Logs gate result metric to MLflow. |
| 13 | `HTTP: emit.completed` | `httpRequest` | Emits `training.completed` event to gateway. |
| 14 | `HTTP: emit.gate_failed` | `httpRequest` | Emits `training.gate_failed` event when Gate A fails. |
| 15 | `HTTP: emit.insufficient_data` | `httpRequest` | Emits insufficient-data event if minimum class counts are not met. |

## Agent 6: Evaluation Agent (EfficientNet)
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: evaluation.start` | `webhook` | Receives evaluation start request at `agent/evaluation/efficientnet/start`. |
| 2 | `Postgres: check.test_balance` | `postgres` | Counts test samples per class (`happy/sad/neutral`). |
| 3 | `IF: test_set.balanced?` | `if` | Requires minimum per-class test count (>= 20). |
| 4 | `Code: prepare.evaluation` | `code` | Builds evaluation run context (`run_id`, checkpoint path, output dir, gateway base). |
| 5 | `SSH: run.evaluation` | `ssh` | Runs pipeline in skip-train mode for evaluation and collects run status snapshots. |
| 6 | `Code: parse.results` | `code` | Parses run status payload, extracts metrics, computes Gate A criteria booleans, and pass/fail state. |
| 7 | `HTTP: mlflow.log_metrics` | `httpRequest` | Logs evaluation metrics batch to MLflow. |
| 8 | `IF: Gate_A.pass?` | `if` | Branches completed vs gate-failed evaluation outcomes. |
| 9 | `HTTP: emit.completed` | `httpRequest` | Emits `evaluation.completed` event payload. |
| 10 | `HTTP: emit.gate_failed` | `httpRequest` | Emits `evaluation.gate_failed` event payload. |
| 11 | `Code: prepare.blocked_status` | `code` | Prepares blocked status object when test-set threshold is not met. |
| 12 | `HTTP: status.blocked` | `httpRequest` | Persists blocked state to training status endpoint for visibility/UI feedback. |

## Agent 7: Deployment Agent (EfficientNet)
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Webhook: deployment.start` | `webhook` | Receives deployment requests at `agent/deployment/efficientnet/start` and returns `202`. |
| 2 | `IF: gate_a.passed?` | `if` | Prevents deployment when upstream Gate A failed. |
| 3 | `Code: prepare.deployment` | `code` | Resolves ONNX/engine/backup paths and deployment metadata for rollout stage. |
| 4 | `SSH: scp.onnx_to_jetson` | `ssh` | Transfers ONNX artifact to Jetson temp path via SCP. |
| 5 | `SSH: convert.to_tensorrt` | `ssh` | Backs up current engine and converts ONNX to TensorRT engine (`trtexec --fp16`). |
| 6 | `SSH: update.deepstream_config` | `ssh` | Rewrites DeepStream model-engine path and restarts `reachy-emotion` service. |
| 7 | `Wait: 30s` | `wait` | Allows service warm-up before verification. |
| 8 | `SSH: verify.deployment` | `ssh` | Checks service active state and reads latest runtime metrics from log JSON. |
| 9 | `Code: parse.verification` | `code` | Parses verification output and computes Gate B checks (service, fps, latency). |
| 10 | `IF: Gate_B.pass?` | `if` | Branches success vs rollback path based on Gate B result. |
| 11 | `HTTP: emit.success` | `httpRequest` | Emits deployment completion event. |
| 12 | `SSH: rollback` | `ssh` | Restores backup engine and restarts service when Gate B fails. |
| 13 | `HTTP: emit.rollback` | `httpRequest` | Emits rollback event payload. |

## Agent 8: Privacy / Retention Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Schedule: daily 03:00` | `scheduleTrigger` | Runs automatic privacy purge cycle daily at 03:00. |
| 2 | `Webhook: gdpr.deletion` | `webhook` | Accepts manual purge trigger requests at `privacy/purge`. |
| 3 | `Postgres: find.old_temp` | `postgres` | Finds old temp-split records exceeding TTL window. |
| 4 | `Loop: batch.delete` | `splitInBatches` | Iterates records in batches (`50`) to limit per-run delete pressure. |
| 5 | `SSH: delete.file` | `ssh` | Deletes underlying file from videos storage path. |
| 6 | `Postgres: mark.purged` | `postgres` | Marks video rows as `purged` and updates timestamp. |
| 7 | `Postgres: audit.log` | `postgres` | Inserts purge action records into audit log table. |
| 8 | `HTTP: emit.purged` | `httpRequest` | Emits privacy purge event to gateway for observability/audit trail. |

## Agent 9: Observability / Telemetry Agent
| # | Node | Type | Functionality |
|---|---|---|---|
| 1 | `Cron: every 30s` | `cron` | Triggers telemetry scraping cadence every 30 seconds. |
| 2 | `HTTP: n8n.metrics` | `httpRequest` | Pulls Prometheus metrics from n8n instance. |
| 3 | `HTTP: mediamover.metrics` | `httpRequest` | Pulls Prometheus metrics from Media Mover metrics endpoint. |
| 4 | `HTTP: gateway.metrics` | `httpRequest` | Pulls Prometheus metrics from Gateway metrics endpoint. |
| 5 | `Code: parse.metrics` | `code` | Extracts specific metrics by regex (`active_executions`, `promote_total`, `queue_depth`) into normalized records. |
| 6 | `Postgres: store.metrics` | `postgres` | Inserts telemetry samples into `obs_samples` table. |

## Cross-agent node patterns
- Human gate pattern: Agent 3 uses dual webhooks (`request` + `approval`) for explicit approval checkpoints.
- Async polling pattern: Agents 1 and 5 combine `Wait` + status checks + loop branch.
- Reliability pattern: Most write flows carry `correlation_id` and idempotency keys in node payloads.
- Batch safety pattern: Agent 8 uses `Split In Batches` before file deletion and DB mutation.
- Status-contract pattern: Agents 5 and 6 persist/read run status via `/api/training/status/{id}`.
