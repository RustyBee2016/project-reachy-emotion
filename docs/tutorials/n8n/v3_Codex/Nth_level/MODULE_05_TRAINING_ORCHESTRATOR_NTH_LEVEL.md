# MODULE 05 — Training Orchestrator (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/05_training_orchestrator_efficientnet.json`

## Runtime Goal
Gate training by balanced data thresholds, launch EfficientNet pipeline, poll persisted status, enforce Gate A, and emit outcome events.

## Node-to-Script Map

### 1) `Webhook: training.start` (`Webhook`)
- **Workflow role:** training run trigger.
- **Path/method:** `POST /webhook/agent/training/efficientnet/start`.

### 2) `Postgres: check.train_balance` (`Postgres`)
- **Workflow role:** preflight class counts in `train` split.
- **SQL:** counts `happy/sad/neutral` where `split='train'`.

### 3) `IF: sufficient_data?` (`If`)
- **Workflow role:** minimum data gate.
- **Expression:** `min(happy_train, sad_train, neutral_train) >= 50`.
- **Branches:**
- true -> run training
- false -> emit insufficient-data event

### 4) `HTTP: mlflow.create_run` (`HTTP Request`)
- **Workflow role:** initializes MLflow run context.
- **HTTP target:** `POST {{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create`
- **Payload:** experiment ID and tags (`model`, `dataset_hash`, `correlation_id`).

### 5) `Code: prepare.training` (`Code`)
- **Workflow role:** generate runtime command parameters.
- **Essential in-node logic:**
- creates deterministic timestamped `run_id`
- injects config path `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`
- sets output/model paths and gateway base URL
- **Spec binding:** `efficientnet_b0_emotion_3cls.yaml` defines 3-class model, two-phase training, Gate A/B thresholds.

### 6) `SSH: start.training` (`SSH`)
- **Workflow role:** launches end-to-end pipeline script.
- **Command target:** `python trainer/run_efficientnet_pipeline.py ... --strict-contract-updates`
- **Backend binding:** `trainer/run_efficientnet_pipeline.py:304` `main()`
- **Essential script-level behavior:**
- emits `training.started` via `_emit_training_started(...)` (`line 67`)
- trains via `EfficientNetTrainer.train(...)`
- emits `evaluation.started` and later completion/failure status payloads to gateway status API
- computes predictions + Gate A report via `evaluate_predictions(...)` (`gate_a_validator.py:42`)
- exports ONNX if Gate A passes

### 7) `Wait: 5min` (`Wait`)
- **Workflow role:** polling interval throttle.

### 8) `SSH: check.status` (`SSH`)
- **Workflow role:** fetches run-specific + latest status snapshots.
- **Command behavior:** `curl .../api/training/status/{run_id}` and `/latest`.
- **Backend binding path:**
- gateway proxy: `apps/api/routers/gateway.py:365,377`
- persisted endpoint: `apps/api/app/routers/gateway_upstream.py:498,536`
- DB model: `TrainingRun` (`models.py:102`)

### 9) `Code: parse.results` (`Code`)
- **Workflow role:** normalize status payload to gate-ready object.
- **Essential in-node logic:**
- parses SSH JSON envelope
- if status in `{training,evaluating,pending,sampling}` returns `status='running'`
- otherwise extracts metrics, epochs, gate flags (`gate_a`)

### 10) `IF: training.done?` (`If`)
- **Workflow role:** loop control.
- **Expression:** status contains `completed`.
- **Branches:**
- true -> Gate A check
- false -> back to `Wait: 5min` (poll loop)

### 11) `IF: Gate_A.pass?` (`If`)
- **Workflow role:** quality gate branch.
- **Expression:** `{{$json.gate_results.gate_a}} == true`.
- **Gate source:** from persisted training metrics emitted by pipeline script.

### 12) `HTTP: mlflow.log_gate` (`HTTP Request`)
- **Workflow role:** writes final gate metric (`gate_a_passed` as 0/1) to MLflow.

### 13) `HTTP: emit.completed` (`HTTP Request`)
- **Workflow role:** emit `training.completed` to gateway event endpoint.
- **Backend binding:** `apps/api/routers/gateway.py:315` `post_training_event(...)`.

### 14) `HTTP: emit.gate_failed` (`HTTP Request`)
- **Workflow role:** emit `training.gate_failed` with explanatory message.

### 15) `HTTP: emit.insufficient_data` (`HTTP Request`)
- **Workflow role:** emit `training.insufficient_data` when gate 3 fails.

## Essential Functions Behind the Training Flow
- `trainer/fer_finetune/train_efficientnet.py`
- `EfficientNetTrainer.__init__`: freezes backbone initially (`line 84`)
- `_check_phase_transition`: unfreezes `blocks.6`, `blocks.5`, `conv_head` after configured epoch (`line 374+`)
- `_create_scheduler`: warmup + cosine scheduler (`line 146+`)
- mixed precision with `autocast` + `GradScaler` (`line 111`, `278+`)
- `_check_quality_gates`: F1/balanced-accuracy/ECE/Brier Gate A checks (`line 408+`)
- `trainer/gate_a_validator.py`
- `GateAThresholds` (`line 25`) and `evaluate_predictions(...)` (`line 42`)

## How This Delivers Training Functionality
1. Prevents underpowered training runs with data-balance precheck.
2. Launches scripted ML pipeline with contract status updates.
3. Polls DB-backed status API until completion.
4. Enforces Gate A and routes pass/fail outcomes to event sinks + MLflow.
