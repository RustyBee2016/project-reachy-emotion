# AGENTS — Reachy_Local_08.4.2

## Metadata
- **Project:** Reachy_Local_08.4.2  
- **Primary Objective:** Emotion classification from short synthetic videos (2-class: `happy`, `sad`) using the EmotionNet model.  
- **Secondary Objectives:** Local-first privacy, reproducible fine-tuning, human-in-the-loop labeling and dataset curation, low operational overhead.  
- **Non-goals:** Audio emotion recognition, cloud dependencies, linguistic or conversational emotion synthesis.  
- **Stakeholders:** Robot end-users, Reachy R&D team, and project maintainers.  

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
  PostgreSQL 16 cluster (local). Stores metadata, video URLs, hashes, and promotion logs.  
- **Storage:**  
  Local SSD under `/media/project_data/reachy_emotion/videos/` with subfolders:  
  `temp/`, `train/`, and `test/`.  
- **Networking:**  
  Static LAN IPs — Ubuntu 1 (10.0.4.130), Ubuntu 2 (10.0.4.140), Jetson (10.0.4.150).  
- **Model:**  
  NVIDIA TAO EmotionNet, fine-tuned for binary (`happy` vs `sad`) classification.

---

## Agent Overview
The Reachy_Local_08.4.2 system uses **nine cooperating agents**, each performing one narrow, auditable task in the video → label → train → evaluate → deploy loop.  
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
- Maintain training split integrity (`videos/train/`) by ensuring all accepted items carry a valid label (`happy` or `sad`).  
- Enforce the **no-label rule** for the `test` split.  
- Interface with the web UI to update per-class counts and 50/50 balance status.  
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
Trigger EmotionNet fine-tuning once dataset balance and size thresholds are met.

**Responsibilities:**  
- Launch TAO training using the pinned `emotion_train_2cls.yaml` spec.  
- Mount dataset paths from `/media/.../videos/train/` and generate checkpoints.  
- Record dataset hash, TAO container version, and metrics to MLflow.  
- Publish `training.completed` with links to artifacts and validation metrics.  

---

### Agent 6 — Evaluation Agent
**Purpose:**  
Run validation jobs once the test set is balanced.

**Updated Responsibilities:**  
- Confirm `min(happy_count, sad_count) ≥ TEST_MIN_PER_CLASS` before triggering TAO/DeepStream validation.  
- Reference test videos by file path only; never attach or infer labels internally.  
- Produce final confusion matrix and accuracy metrics using the *labeled validation split*, keeping `videos/test/` untouched for the final report.  

---

### Agent 7 — Deployment Agent
**Purpose:**  
Promote validated engines from `shadow → canary → rollout` with explicit approval gates.

**Responsibilities:**  
- Copy exported `.engine` to the Jetson NX at `/opt/reachy/models/emotion.engine`.  
- Update DeepStream pipeline configuration and restart service.  
- Verify live metrics: FPS ≥ 25, latency ≤ 100 ms.  
- Support rollback to prior engine on regression.  
- Record deployment metadata (`engine_version`, `fps`, `accuracy`, `timestamp`).  

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
Monitor class ratios and bias subsequent synthetic video generation to maintain a 50/50 balance between `happy` and `sad`.  
Acts as a lightweight helper to Labeling Agent + Promotion Agent when automated balancing is desired.

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
