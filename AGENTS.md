# AGENTS — Reachy_Local_08.4.2

## Metadata
- **Project:** Reachy_Local_08.4.2  
- **Primary Objective:** Emotion classification from short synthetic videos (3-class: `happy`, `sad`, `neutral`) using EfficientNet-B0 pre-trained on VGGFace2 + AffectNet (HSEmotion).  
- **Secondary Objectives:** Local-first privacy, reproducible fine-tuning, human-in-the-loop labeling and dataset curation, low operational overhead.  
- **Non-goals:** Audio emotion recognition, cloud dependencies, linguistic or conversational emotion synthesis.  
- **Stakeholders:** Robot end-users, Reachy R&D team, and project maintainers.

---

## Project Phases

### Phase 1: Offline ML Classification System
Foundation infrastructure: web app, EfficientNet-B0 training pipeline, FastAPI gateway, MLflow tracking, Gate A validation.

### Phase 2: Emotional Intelligence Layer
- **Degree**: Confidence scores (0–1) for emotion intensity
- **PPE**: 8-class Ekman taxonomy with emotion-to-response mapping
- **EQ**: Calibration metrics (ECE, Brier, MCE) for reliability
- **Gesture Modulation**: 5-tier confidence-based expressiveness (`gesture_modulator.py`)
- **LLM Prompt Tailoring**: Emotion-conditioned prompts with confidence guidance

### Phase 3: Edge Deployment & Real-Time Inference
Jetson deployment: TensorRT conversion, DeepStream pipeline, real-time inference, Gates B & C validation, staged rollout.  

---

## Instruction Priority Stack
1. Follow safety, privacy, and compliance policies defined in this AGENTS file and `requirements_08.4.2.md`.  
2. Maintain consistency with `UI_Requirements.md` (latest version).  
3. Obey maintainer instructions from the web UI or direct commands.  
4. On uncertainty: fail closed, ask ≤ 2 concise clarifications, confirm any file-modifying or destructive actions.

Conflicts between automation and policy defer to the human project owner (Russ).

---

## Environment Overview
- **Training Node (Ubuntu 1):**  
  NVIDIA GPU workstation running TAO Toolkit 4.x for EmotionNet fine-tuning.  
  Handles FastAPI-based Media Mover service (base: `https://10.0.4.130/api/media`) and Postgres database.
- **Web/UI Node (Ubuntu 2):**  
  Streamlit frontend behind Nginx, interacts with FastAPI and Postgres.  
- **Robot Node (Jetson Xavier NX):**  
  Runs DeepStream + TensorRT engine for live inference.
- **Database:**  
  PostgreSQL 16 cluster (local) at `10.0.4.130:5432` using the `reachy_dev` role against the `reachy_emotion` database. Stores metadata, video URLs, hashes, and promotion logs.  
- **Storage:**  
  Local SSD under `/media/project_data/reachy_emotion/videos/` with subfolders:  
  `temp/`, `train/`, and `test/`.  
- **Networking:**  
  Static LAN IPs — Ubuntu 1 (10.0.4.130), Ubuntu 2 (10.0.4.140), Jetson (10.0.4.150).  
- **Model:**  
  EfficientNet-B0 pre-trained on VGGFace2 + AffectNet (HSEmotion `enet_b0_8_best_vgaf`), fine-tuned for 3-class (`happy`, `sad`, `neutral`) classification.  
  Model placeholder: `efficientnet-b0-hsemotion`  
  Storage path: `/media/rusty_admin/project_data/ml_models/efficientnet_b0`

---

## Agent Overview
The Reachy_Local_08.4.2 system uses **ten cooperating agents**, each performing one narrow, auditable task in the video → label → train → evaluate → deploy loop.  
All orchestration occurs in **n8n** running on Ubuntu 1.

---

### Agent 1 — Ingest Agent
**Purpose:**  
Receive new videos (uploads or generated) and register them in the system.

**Responsibilities:**  
- Compute `sha256` checksum and store video in `/videos/temp/`.  
- Extract and persist metadata (`duration`, `fps`, `resolution`) in Postgres.  
- Generate a thumbnail (JPG) and store under `/thumbs/`.  
- Emit an `ingest.completed` event with the new record ID, checksum, and paths.  

**Notes:**  
Initiated by the web UI or generation workflow. Operates in local-only mode; no cloud upload permitted.

---

### Agent 2 — Labeling Agent
**Purpose:**  
Manage user-assisted classification and dataset promotion.

**Updated Responsibilities (v08.4.2):**
- Maintain training split integrity (`videos/train/`) by ensuring all accepted items carry a valid label (`happy`, `sad`, or `neutral`).  
- Enforce the **no-label rule** for the `test` split.  
- Interface with the web UI to update per-class counts and 1:1:1 balance status (happy, sad, neutral).  
- Coordinate with the Database API to apply the `chk_split_label` constraint and maintain per-split quotas.  
- Log each promotion event (`temp → train` or `temp → test`) with `intended_emotion`, timestamp, and `sha256`.  

### Agent 3 — Promotion / Curation Agent
**Purpose:**  
Oversee controlled movement of media between filesystem stages.

**Updated Responsibilities:**
- Allow promotion to `videos/test/` only through the Labeling Agent interface after user acceptance.  
- Verify `label IS NULL` for all test items.  
- Prevent class imbalance by checking counters before each move.  
- Update the Postgres `split` field transactionally with the filesystem move via Media Mover (`POST /api/media/promote`, alias supported at `POST /api/promote`).  
- Notify the UI of the updated ratio and readiness status (via WebSocket or polling).  

---

### Agent 4 — Reconciler / Audit Agent
**Purpose:**  
Ensure filesystem and database consistency.

**Responsibilities:**  
- Recompute checksums for changed files and compare against DB entries.  
- Detect orphaned, duplicate, or missing files.  
- Rebuild manifests (`train_manifest.json`, `test_manifest.json`) when drift is found.  
- Emit `reconcile.report` to Prometheus/Grafana dashboards with summary counts.  

---

### Agent 5 — Training Orchestrator
**Purpose:**  
Trigger EfficientNet-B0 emotion classifier fine-tuning once dataset balance and size thresholds are met.

**Updated Responsibilities (v08.4.2 ML):**
- Launch PyTorch training using `trainer/train_efficientnet.py` with config `fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`.  
- Implement two-phase training: frozen backbone (epochs 1-5) → selective unfreezing (blocks.5, blocks.6, conv_head).  
- Apply HSEmotion pre-trained weights (`enet_b0_8_best_vgaf` from VGGFace2 + AffectNet).  
- Use mixed precision (FP16), mixup augmentation, and cosine LR schedule with warmup.  
- Mount dataset paths from `/media/project_data/reachy_emotion/videos/train/` and generate checkpoints.  
- Record dataset hash, model version, and metrics (F1, ECE, Brier) to MLflow.  
- Validate Gate A requirements before export: F1 ≥ 0.84, balanced accuracy ≥ 0.85, ECE ≤ 0.08.  
- Export to ONNX on success; publish `training.completed` with artifacts and metrics.

**n8n Workflow:** `ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`  

---

### Agent 6 — Evaluation Agent
**Purpose:**  
Run validation jobs once the test set is balanced.

**Updated Responsibilities (v08.4.2 ML):**  
- Confirm `min(happy_count, sad_count, neutral_count) ≥ TEST_MIN_PER_CLASS` (default: 20) before triggering evaluation.  
- Load trained EfficientNet-B0 checkpoint and run inference on test set.  
- Compute comprehensive metrics: accuracy, F1 (macro + per-class), balanced accuracy.  
- Compute calibration metrics: ECE (Expected Calibration Error), Brier score.  
- Validate Gate A requirements and emit pass/fail status.  
- Generate evaluation report with confusion matrix.  
- Reference test videos by file path only; never attach or infer labels internally.

**n8n Workflow:** `ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`  

---

### Agent 7 — Deployment Agent
**Purpose:**  
Promote validated engines from `shadow → canary → rollout` with explicit approval gates.

**Updated Responsibilities (v08.4.2 ML):**  
- Transfer ONNX model to Jetson via SCP.  
- Convert ONNX → TensorRT engine on Jetson using `trtexec` with FP16 precision.  
- Backup existing engine before deployment.  
- Copy exported `.engine` to the Jetson NX at `/opt/reachy/models/emotion_efficientnet.engine`.  
- Update DeepStream pipeline configuration (`emotion_inference.txt`) and restart service.  
- Verify Gate B requirements: FPS ≥ 25, latency p50 ≤ 120 ms, GPU memory ≤ 2.5 GB.  
- Support automatic rollback to prior engine on Gate B failure.  
- Record deployment metadata (`engine_version`, `model`, `fps`, `latency`, `timestamp`).

**n8n Workflow:** `ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`  

---

### Agent 8 — Privacy / Retention Agent
**Purpose:**  
Enforce local-first policy, TTLs for temporary media, and purge/redaction procedures.

**Responsibilities:**  
- Auto-purge videos in `/videos/temp/` older than the configured TTL (e.g. 7 days).  
- Deny access to raw videos unless explicitly authorized by policy.  
- Support manual purge requests from UI and confirm deletion logs in Postgres.  
- Emit `privacy.purged` and `privacy.violation` events for auditing.  

---

### Agent 9 — Observability / Telemetry Agent
**Purpose:**  
Aggregate system metrics and raise alerts when thresholds are breached.

**Responsibilities:**  
- Collect metrics from all agents: queue depth, task latency, success rate, manifest rebuild time, dataset balance, model drift, etc.  
- Publish to Prometheus and visualize through Grafana dashboards.  
- Emit `obs.snapshot` and notify maintainers when error budgets are exceeded.  

---

### Optional Sub-Agent — Generation Balancer
**Purpose:**  
Monitor class ratios and bias subsequent synthetic video generation to maintain 1:1:1 balance across `happy`, `sad`, and `neutral`.  
Acts as a lightweight helper to Labeling Agent + Promotion Agent when automated balancing is desired.

---

### Agent 10 — Reachy Gesture Agent
**Purpose:**  
Execute physical gestures on the Reachy Mini robot based on emotion context and LLM response cues.

**Responsibilities:**
- Receive gesture cues from the gateway via WebSocket (`cue` events).
- Parse gesture keywords from LLM responses (e.g., `[WAVE]`, `[HUG]`, `[EMPATHY]`).
- Map detected emotions to appropriate default gestures when LLM doesn't specify.
- Execute gesture sequences on Reachy Mini via the Reachy SDK (gRPC).
- Maintain gesture queue with priority handling.
- Support simulation mode for testing without physical robot.
- Report gesture execution metrics to Observability Agent.

**Gesture Types:**
- **Happy emotions:** CELEBRATE, EXCITED, THUMBS_UP, WAVE, NOD
- **Sad emotions:** EMPATHY, COMFORT, HUG, SAD_ACK, LISTEN
- **Neutral:** NOD, LISTEN, WAVE, THINK

**Integration Points:**
- `apps/reachy/gestures/gesture_controller.py` — Reachy SDK interface
- `apps/reachy/gestures/emotion_gesture_map.py` — Emotion-to-gesture mapping
- `apps/reachy/cue_handler.py` — WebSocket cue routing
- `apps/pipeline/emotion_llm_gesture.py` — Full pipeline orchestration

**Requirements:**
- Python 3.12+ (Reachy SDK requirement)
- Reachy Mini robot online at configured gRPC address, or simulation mode enabled

---

## Safety / Privacy / Compliance
- All inference and training occur on-premise. No raw video leaves the local network.  
- Synthetic videos generated by external APIs must be labeled and logged with metadata (`generator`, `version`, `prompt`).  
- Only minimal PII (faces) is retained; full purge support is mandatory.  
- Logging is structured JSONL rotated regularly; includes `accuracy@val`, `latency_ms`, `fps`, `engine_version`.  
- Follow OpenAI and NVIDIA TAO usage policies; maintain local-only data flows.  

---

## Orchestration Policy
- **Retries:** Exponential backoff with jitter; `max_attempts = 5` for transient errors.  
- **Idempotency:** All write operations (promotion, delete, train) must include `Idempotency-Key`.  
  - Promotion calls use Media Mover at base `https://10.0.4.130/api/media` (`POST /api/media/promote`; compatibility alias `POST /api/promote`).
- **Circuit Breakers:** Trip on high latency or error spikes to protect upstreams (e.g. LM Studio).  
- **Queue Discipline:** Default FIFO per agent; limit concurrency per agent role.  
- **Dead Letter Queue:** Failed tasks beyond retries require human review.  
- **Message Envelope:** Every message includes `schema_version`, `correlation_id`, `issued_at`, and `source`.  

---

## Approval Rules
- **Dataset Promotions:** Require human confirmation (`temp → train/test`).  
- **Model Deployments:** Require two-stage approval (`shadow → canary`, `canary → rollout`).  
- **Privacy Policy Changes:** Require explicit owner consent.  

Evidence must reference Gate A/B/C records defined in `requirements_08.4.2.md`.

---

## Observability SLOs
- Planner Actions: P50 ≤ 2 s, P95 ≤ 5 s  
- Executor Actions: Meet per-agent SLAs; emit `task_latency`, `success_rate`, `queue_depth`  
- Error Budget: < 1 % weekly per agent  
- Trace Propagation: Maintain `correlation_id` across Ubuntu 2 → Ubuntu 1 → Jetson  

---

## Runbooks (Minimum)
- **Promotion Rejected:** Check Labeling Agent logs; resolve constraint or approval mismatch.  
- **Low FPS / High Latency:** Inspect DeepStream + Jetson thermals; fallback to FP16 precision.  
- **Dataset Drift:** Run Reconciler Agent manually to rebuild manifests and counters.  
- **Privacy Violation:** Trigger purge; confirm redaction and Postgres cleanup.  

---

Maintain alignment between **Agents_08.4.2.md**, **requirements_08.4.2.md**, and **MODEL_SPEC.md**.  
Any conflict must be resolved before next training or deployment cycle.
