### Updates: 1.0  (3.19.26)

* Updated project components
  
  * Web app
    
    * Completed ML data pipeline
    
    * * Ingestion
      
      * Pre-processing
      
      * Promotion
      
      * Logging
    
    * Added model fine-tuning
    
    * Added model dashboards
      
      * Displays statistical results
      
      * Determines Gate A thresholds
      
      * Includes direct model comparisons
  
  * Workflow automation using ***n8n***
    
    * Completed first three agents
    
    * Confirmed functionalities
    
    * 100% availabe for production
  
  * Marketing Web app
    
    * Static version provides snapshots summarize key concepts
    
    * Key metrics reflect actual data pipelines
      
      

### File list - 3.19.26



Comprehensive inventory of file inventory available here:  **PROJECT_FILES_INVENTORY.md**



### Summary

#### Streamlit Web App (10 pages)

**Core Pages:**

* 00_Home.py — Dashboard with system status

* 01_Generate.py — Video generation (Luma/Runway)

* 02_Label.py — Human labeling with class balance

* 03_Train.py — Training launch with hyperparameters

* 04_Deploy.py — TensorRT deployment management

* 05_Video_Management.py — Video library browser

**Advanced ML Pages:**

* 06_Dashboard.py — Gate A metrics (F1, ECE, Brier, confusion matrices)

* 07_Fine_Tune.py — **Variant 2** with 25+ tuneable hyperparameters

* 08_Compare.py — Direct model comparison (Base vs Variant 1 vs Variant 2)

* 09_EQ_Calibration.py — EQ calibration metrics (ECE, Brier, MCE)

### FastAPI Gateway (11 routers)

**Key Routers:**

* ingest.py — Video ingestion with SHA256 deduplication (pull_video(), register_local_video())

* promote.py — Promotion with dry-run preview

* media_v1.py — Canonical promotion workflow

* training_control.py — Training subprocess spawning (`launch_training()`)

* gateway_upstream.py — Jetson emotion events

* websocket_cues.py — Real-time gesture cues

### ML Training Pipeline

**Core Scripts:**

* train_efficientnet.py — CLI entry point

* run_efficientnet_pipeline.py — End-to-end orchestrator

* prepare_dataset.py — DatasetPreparer class (10 frames/video extraction)

* gate_a_validator.py — Threshold validation

* mlflow_tracker.py — Experiment tracking

### n8n Workflows (✅ 100% PRODUCTION-READY)

**First Three Agents (Confirmed Functional):**

* 01_ingest_agent.json — Video ingestion with deduplication

* 02_labeling_agent.json — Human labeling with class balance

* 03_promotion_agent.json — Dry-run promotion with approval gate

**Remaining Agents (Validated):**

* 04_reconciler_agent.json — Filesystem ↔ DB drift detection

* 05_training_orchestrator_efficientnet.json — EfficientNet-B0 training with MLflow

* 06_evaluation_agent_efficientnet.json — Test evaluation with calibration

* 07_deployment_agent_efficientnet.json — ONNX → TensorRT + Jetson deployment

* 08_privacy_agent.json — TTL purging and GDPR compliance

* 09_observability_agent.json — Prometheus metrics

* 10_ml_pipeline_orchestrator.json — Master coordinator

### 

### React Website Location:

apps/web/dev/

### React Website Structure (✅ VALIDATED - STABLE & PRODUCTION-READY)

**Core Files:**

* package.json — React 18.3 + Vite 5.4 + TailwindCSS 3.4 dependencies with gh-pages deployment

* src/App.jsx — HashRouter with 7 routes, Layout wrapper, ScrollToTop utility

* src/main.jsx — React bootstrap entry point

**Pages (7):**

* HomePage.jsx — Landing with hero waveform, EQ gauge, feature showcase

* TechnologyPage.jsx — EfficientNet-B0, HSEmotion, DeepStream/TensorRT technical details

* ArchitecturePage.jsx — Three-node system, agent orchestration, deployment gates

* PrivacySafetyPage.jsx — Privacy-by-design, GDPR compliance, ethical guidelines

* UseCasesPage.jsx — Companion robotics, healthcare, education applications

* AboutPage.jsx — Project background and team

* ContactPage.jsx — Contact form
  
  

------



# Project Requirements — Reachy_EQ_PPE_Degree_Mini_01

## 1. Project Overview

- **Project Name**: Reachy_EQ_PPE_Degree_Mini_01
- **Version**: 0.09.2
- **Last Updated**: 2026-03-13
- **Project Type**: Robotics Control Software
- **Target Platform**: Reachy Mini Companion Robot — Jetson Xavier NX 16GB model
- **Primary Language**: Python 3.8+

### Version History

| Version  | Date       | Author       | Changes Description                                                                                                                                                                            |
| --------:| ---------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1.0    | 2025-09-16 | Russell Bray | Initial requirements draft                                                                                                                                                                     |
| 0.2.0    | 2025-09-16 | Cascade      | Added deployment gates, performance metrics, privacy controls, and acceptance criteria                                                                                                         |
| 0.8.3    | 2025-09-20 | Team         | Hybrid storage (PostgreSQL metadata + ext4 media via Nginx), DeepStream-only runtime, FastAPI gateway, checksum/dedup, promotion dry‑run, reconciler & metrics, tightened security             |
| 0.08.3.2 | 2025-09-20 | Team         | Integrated **Reachy_Storage.md** guidance: canonical FS layout, mini‑FastAPI endpoints, MLflow lineage, NAS redundancy, DB schema, ops playbooks, acceptance criteria                          |
| 0.08.3.3 | 2025-10-06 | Team         | Pin TAO container/image version; document workspace mounts and envs; canonicalize storage root on Ubuntu 1; add explicit endpoint map; clarify EmotionNet schema; note Media Mover on Ubuntu 1 |
| 0.08.4.2 | 2025-10-16 | Team         | Project renamed to Reachy_Local_08.4.2; updated README alignment; agentic AI system integration; enhanced privacy controls and deployment gates                                                |
| 0.08.4.3 | 2025-10-28 | Team         | Introduced run-scoped dataset preparation workflows and updated promotion/manifest requirements                                                                                                |
| 0.09.0   | 2026-01-14 | Russell Bray | Renamed to Reachy_EQ_PPE_Degree_Mini_01; added emotion-degree telemetry (0–5), Reachy Mini Lite gesture orchestration, multi-task training updates, and refreshed documentation                |
| 0.09.1   | 2026-01-25 | Cascade      | Swapped backbone to EfficientNet-B0 (HSEmotion enet_b0_8_best_vgaf) for 3× latency/memory headroom on Jetson; documented EfficientNet-B2 trade-offs                                            |
| 0.09.2   | 2026-03-13 | Cascade      | Updated to reflect 10-agent system (added Agent 10: Reachy Gesture Agent); Phase 2 Emotional Intelligence Layer 95% complete; synchronized documentation                                       |

### Project Description

Reachy‑Emotion‑Recognition is an open‑source robotic platform designed for human‑robot interaction and research. This project implements a privacy‑preserving emotion perception + expression system with a continuous improvement loop:

1. **Data Generation**: Web app for generating and classifying synthetic emotion videos (labels + degree sliders).
2. **Model Training**: Multi-task fine-tuning of EfficientNet-B0 (HSEmotion enet_b0_8_best_vgaf pretrained on VGGFace2 + AffectNet) with categorical + scalar heads plus gesture-alignment summaries, tuned for Jetson latency/memory constraints.
3. **Deployment**: Containerized deployment to Reachy Mini Lite with staged rollout and cue planner integration.
4. **Inference**: Real‑time emotion classification + degree estimation with strict performance SLAs.
5. **Expression Loop**: Gesture planner pairs empathetic dialogue and Reachy gestures driven by emotion degree.
6. **Feedback Loop**: Ongoing user‑based classifications refine both labels and degree targets for future iterations.

The system prioritizes user privacy through on‑device processing, minimal data retention, and strict access controls. Performance is continuously monitored against quantifiable metrics for accuracy, latency, and resource utilization.

### Project Goals

1. Create a web app for generating and classifying videos of people expressing emotions.
2. Fine‑tune a classification model using videos created by the web app.
3. Deploy fine‑tuned models to the robot (Reachy).
4. Create client software for recognizing user emotions observed while interacting with Reachy.
5. Implement reliable emotion classification used to tailor LLM interaction.
6. LLM provides the user with emotional support based on the previously classified emotion.
7. Computer vision systems support integration by streaming video to the classification model on‑board Reachy.
8. Provide comprehensive documentation and examples.

### Success Metrics

- 95% emotion recognition accuracy within specified tolerances
- Sub‑100 ms response time for basic commands
- 99.9% system uptime during operation
- Comprehensive test coverage (>80%)
- Clear and accessible documentation
- Gateway API regression suite: **59/59 tests passing** (validated 2025-11-26)

---

## 2. Project Scope

### 2.1 In Scope

- Generate and classify videos of people expressing emotions
- Python API used for emotion recognition
- Advanced AI/ML capabilities use generated videos for model fine‑tuning
- Safety features and privacy protection
- **Primary storage on local filesystem** (ext4 or ZFS) with canonical layout: `/videos/{temp,train,test,thumbs,manifests}`. Labeled clips are promoted into `train/<label>` and run-specific frame datasets are generated for each fine-tuning run.
- **mini‑FastAPI “media mover”** to list media, serve thumbnails (via Nginx), perform atomic promotions, and rebuild manifests
- **MLflow (file‑backed)** for experiment/run tracking (params, metrics, artifacts) tied to dataset hashes and optional ZFS snapshot tags
- **Synology NAS redundancy** via NFS/SMB mirroring of `/videos/*` and MLflow artifacts; SSD remains the hot path

### 2.2 Out of Scope

- Hardware specification and procurement details for Reachy Mini (covered elsewhere)
- Object‑store semantics (S3/MinIO/Supabase buckets) for this phase
- Using MLflow as a media server (tracking only; artifacts live on filesystem)

---

## 3. Stakeholders

| Role                        | Name         | Contact               | Responsibilities                     |
| --------------------------- | ------------ | --------------------- | ------------------------------------ |
| Product Owner               | Russell Bray | rustybee255@gmail.com | Project vision & development         |
| Lead Developer              | Russell Bray | rustybee255@gmail.com | Technical direction & implementation |
| ML/Computer Vision Engineer | Russell Bray | rustybee255@gmail.com | ML & CV components                   |
| End Users                   | Unknown      | Unknown               | Interaction with Reachy              |

---

## 4. Architecture & Data Flow

**Hot Path (low‑latency):** Jetson/ingest → `/videos/temp` → human labeling in web UI → `POST /api/media/promote` (direct promote into `/videos/train/<label>`) → per-run frame extractor selects 10 random frames/video into `train/<label>/<run_id>` and consolidated `train/run/<run_id>/<label>` (with optional test mirrors under `test/<run_id>/<label>`) → run manifests → training/eval → gated deploy.

**Serving:** Nginx serves `/thumbs/`; the Ubuntu 2 FastAPI gateway exposes `/api/videos/*`, `/api/v1/promote/*`, `/health`, `/metrics`, and WebSockets for cues, while the Ubuntu 1 Media Mover (`https://10.0.4.130/api/media`) handles filesystem mutations.

**Training:** `tf.data` / TAO / DeepStream pipelines read `/videos/manifests/*.jsonl` or class folders.

**Tracking:** MLflow logs params/metrics/artifacts plus `dataset_hash` and optional ZFS `@snapshot`.

**Redundancy:** rsync (or Synology Drive) mirrors `/videos/*` and MLflow artifacts to NAS; restore playbook documented.

---

## 5. Functional Requirements

### 5.1 Core Features

1. **FR‑001 — Video Generation & User Classification**  
   Web app calls video generation APIs to create emotion clips; user classifies or discards.
2. **FR‑002 — Model Fine‑Tuning**  
   Classified videos fine‑tune EmotionNet; begin fine‑tuning after threshold is met.
3. **FR‑003 — Client Software on Reachy**  
   Improved models are redeployed in a continual loop when accuracy thresholds are surpassed.
4. **FR‑004 — On‑Device Real‑Time Emotion Recognition**  
   Fine‑tuned model classifies emotion; LLM is notified for confirmation.
5. **FR‑005 — Customized LLM Interaction**  
   LLM adapts responses based on predicted emotion.

### 5.2 Storage & Media API

- **FR‑STOR‑001 — Media listing**  
  `GET /api/videos/list?split={temp|train|test}&limit=&offset=` returns `video_id, path, size, mtime`.
- **FR‑STOR‑002 — Promote labeled clip to train**  
  `POST /api/media/promote {video_id, dest_split="train", label, dry_run?}` atomically moves accepted clips from `/videos/temp` into `/videos/train/<label>/` while updating Postgres metadata and promotion logs.
- **FR‑STOR‑003 — Run-specific frame extraction dataset**  
  Fine-tuning prep extracts **10 random frames per source video** from `/videos/train/<label>/*.mp4` into `/videos/train/<label>/<run_id>/`, then consolidates into `/videos/train/run/<run_id>/<label>/`. Test-ready mirrors follow `/videos/test/<run_id>/<label>/` when test datasets are generated. Run manifests enumerate the consolidated frame paths for training.
- **FR‑STOR‑004 — Thumbnails**  
  `GET /api/videos/{id}/thumb` returns file/redirect; thumbnails pre‑generated at `/videos/thumbs/{video_id}.jpg`.
- **FR‑STOR‑005 — Manifest rebuild**  
  `POST /api/manifest/rebuild` emits JSONL manifests under `/videos/manifests/` (tagged by `run_id` when applicable) and returns `dataset_hash`.

### 5.3 Experiment Tracking

- **FR‑TRACK‑001 — MLflow lineage**  
  Each run logs `dataset_hash`, optional `zfs_snapshot`, metrics (accuracy/F1, latency p50/p95, calibration), confusion matrix, and artifacts (logs, TRT/ONNX).

### 5.4 Redundancy & Backup

- **FR‑BACKUP‑001 — NAS mirror**  
  Nightly sync of `/videos/*` and `/mlruns` to Synology NAS; quarterly restore test.

---

## 6. Technical Specifications

### 6.1 Hardware Requirements

- **Robot**: Reachy Mini on NVIDIA Jetson Xavier NX 16GB
- **Camera**: RGB camera ≥30 FPS at 1080p
- **Memory**: 16 GB RAM
- **Storage**: 32 GB eMMC + 2 TB SSD

### 6.2 Software Dependencies

- **OS**: Ubuntu 20.04 LTS with ROS 2 Foxy
- **Python**: 3.8+
- **ML Framework**: PyTorch 2.0+ with CUDA 12 for EfficientNet-B0 fine-tuning
- **ML Libraries**: `timm 0.9+` (pretrained models), `albumentations 1.3+` (augmentation), `scikit-learn 1.3+` (metrics)
- **NVIDIA Framework Wheel**: 24.05
- **NVIDIA JetPack**: 5.x
- **Containerization**: Docker 20.10+ with NVIDIA Container Toolkit
- **Deep Learning (Training, Ubuntu 1)**: PyTorch + timm + `emotiefflib` for EfficientNet-B0 fine-tuning; NVIDIA TAO Toolkit **6.x** (legacy compatibility)
- **Model**: EfficientNet-B0 (`enet_b0_8_best_vgaf`) pre-trained on VGGFace2 + AffectNet (video-optimized emotion backbone)
- **Model Storage**: `/media/rusty_admin/project_data/ml_models/efficientnet_b0`
  - Alternate checkpoint: EfficientNet-B2 (`enet_b2_8`) available for future benchmarking when Jetson constraints are relaxed
- **Inference (Jetson)**: NVIDIA **DeepStream SDK 6.x** + **TensorRT 8.6+** (`gst-nvinfer`, `pyds`, GStreamer 1.22+)
- **API Gateway**: FastAPI **0.110+** (Pydantic v2), `orjson 3.10+`
- **ASGI Server**: Uvicorn **0.29+** (optionally under Gunicorn)
- **Reverse Proxy**: Nginx **1.22+** (range requests; strict MIME allow‑list)
- **Database (metadata)**: PostgreSQL **16+**, SQLAlchemy **2.0+**, `psycopg2-binary 2.9+`, Alembic **1.13+**
- **Media Tools**: FFmpeg **6+** (ffprobe on ingest); optional OpenCV **4.8+** (thumbs)
- **Auth/Security**: `PyJWT 2.8+`, `cryptography 42+`
- **Observability**: `prometheus-client 0.20+`, Uvicorn access logs
- **Testing**: `pytest 8+`, `httpx 0.27+`, optional `locust`
- **Optional Infra**: Redis **7+** (rate‑limit/queues)
- **Filesystem (optional)**: ZFS utilities (`zpool`, `zfs`)

### 6.3 Performance Targets

- Nginx thumbnail fetch median **< 30 ms** on LAN
- Manifest rebuild for up to **10k clips** **< 2 minutes** on NVMe SSD
- Training I/O sustains NVMe read throughput (**≥ 1 GB/s** sequential where feasible)

### 6.4 Reliability & Security

- ZFS checksums when using ZFS; snapshot before each fine-tune
- Mutate endpoints require Bearer/JWT; strict `video_id` validation; forbid arbitrary paths
- Optional ZFS native encryption or LUKS on ext4 for at-rest protection
- rsync exit codes monitored; SMART monitoring on NAS

### 6.5 n8n Orchestration Environment

- **Container orchestration**: n8n runs via Docker Compose alongside PostgreSQL. Expose ports `5678/tcp` (n8n UI/API), `5432/tcp` (Postgres), and ensure Media Mover (`8083/tcp`), FastAPI gateway (`8000/tcp`), MLflow (`5000/tcp`), and SSH (`22/tcp`) are reachable from the n8n container network.
- **Environment variables**: Maintain the following keys in the n8n `.env` file (secrets stored outside source control). These power workflow authentication, host discovery, and feature toggles. *Default metadata DB connection: `DB_HOST=10.0.4.130`, `DB_PORT=5432`, `DB_NAME=reachy_emotion`, `DB_USER=reachy_dev` (credentials managed via Vault).*
  - n8n core: `N8N_BASIC_AUTH_ACTIVE`, `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, `N8N_METRICS`, `GENERIC_TIMEZONE`, `N8N_API_URL`, `N8N_API_KEY`, `N8N_HOST`, `WEBHOOK_URL`, `N8N_USER`, `N8N_PASSWORD`.
  - Media Mover & ingest: `MEDIA_MOVER_BASE_URL`, `MEDIA_MOVER_TOKEN`, `INGEST_TOKEN`, `MEDIA_MOVER_ENABLED`.
  - Gateway & UI: `GATEWAY_BASE_URL`, `GATEWAY_ADMIN_TOKEN`, `GATEWAY_WS_TOKEN`.
  - Databases: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
  - MLflow: `MLFLOW_URL`, `MLFLOW_EXPERIMENT_ID`, `MLFLOW_API_TOKEN`.
  - SSH access: Ubuntu host (`SSH_UBUNTU1_HOST`, `SSH_UBUNTU1_PORT`, `SSH_UBUNTU1_USER`, `SSH_UBUNTU1_PASS`, `SSH_UBUNTU1_KEY_PATH`, `SSH_UBUNTU1_KEY_PASSPHRASE`); Jetson host (`SSH_JETSON_HOST`, `SSH_JETSON_PORT`, `SSH_JETSON_USER`, `SSH_JETSON_PASS`, `SSH_JETSON_KEY_PATH`, `SSH_JETSON_KEY_PASSPHRASE`).
  - Observability & alerts: `PROMETHEUS_N8N_URL`, `PROMETHEUS_MEDIA_MOVER_URL`, `PROMETHEUS_GATEWAY_URL`, `SLACK_WEBHOOK_URL`, `ALERT_EMAIL_SMTP_HOST`, `ALERT_EMAIL_SMTP_PORT`, `ALERT_EMAIL_SMTP_USER`, `ALERT_EMAIL_SMTP_PASS`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO`.
  - Privacy & lifecycle: `TTL_DAYS_TEMP`, `GDPR_MANUAL_APPROVER_EMAIL`, `PURGE_DRY_RUN`.
  - Feature toggles: `SSH_ACTIONS_ENABLED`, `TRAINING_ENABLED`, `EVALUATION_ENABLED`, `DEPLOYMENT_ENABLED`.
  - LLM integrations: `CLAUDE_API_KEY`, `LLM_STUDIO_BASE_URL`, `LLM_STUDIO_API_KEY`.
- **Compose alignment**: Docker Compose expects the `.env` to define `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `N8N_USER`, `N8N_PASSWORD`, `N8N_HOST`, and `WEBHOOK_URL` so that container environment interpolation resolves correctly.
  
  

### 6.6 Model Selection Rationale — EfficientNet Family (2.30.26)

* **Why EfficientNet-B0 now:** Provides ~3× latency (≈40 ms vs 120 ms budget) and 3× memory headroom compared to the prior ResNet-50 export while maintaining target accuracy through compound scaling and HSEmotion pre-training. The extra thermal/memory margin protects gesture workloads and future cue-planning features on Jetson Xavier NX.

* **EfficientNet-B2 trade-off:** HSEmotion’s `enet_b2_8` offers higher accuracy in unconstrained settings but is expected to exceed Jetson latency and memory limits (≤120 ms, ≤2.5 GB). Requirements now mandate a benchmark/validation cycle before any promotion to B2, and Gate B metrics must be re-established if constraints change.

* **Sources:** HSEmotion / EmotiEffLib (`pip install emotiefflib`) for video-optimized EfficientNet-B0/B2 weights, plus timm fallbacks when custom checkpoints are unavailable. Google’s canonical EfficientNet repo is considered legacy for this stack.
  
  

---

## 7. Model Deployment & Quality Gates

### 7.1 Deployment Gates

**Gate A — Offline Validation (Pre-robot)**

- Macro F1 (val): ≥ 0.84; per‑class floors ≥ 0.75; no class < 0.70
- Balanced accuracy: ≥ 0.85
- Calibration: ECE ≤ 0.08, Brier ≤ 0.16

EfficientNet-B0 is the reference backbone for these gates; any alternative (e.g., EfficientNet-B2) must demonstrate equal or better metrics **and** prove latency/memory compliance before the gates are updated.

**Gate B — Robot Shadow Mode**

- On‑device latency: p50 ≤ 120 ms, p95 ≤ 250 ms
- GPU memory ≤ 2.5 GB; Macro F1 ≥ 0.80; per‑class floors ≥ 0.72; no class < 0.68

EfficientNet-B0’s 3× latency/memory cushion (≈40 ms p50 inference, ~0.8 GB GPU footprint) supplies the thermal headroom needed for gesture planners and future multimodal features. Make sure this margin remains ≥2× after TensorRT optimization before clearing Gate B.

**Gate C — Limited User Rollout**

- User‑visible latency ≤ 300 ms end‑to‑end; abstention ≤ 20%; complaints < 1% of sessions

### 7.2 Performance Requirements

- Input: 30 FPS camera stream
- Decision window: 1.0–1.5 s sliding; hop 0.5 s
- Update cadence: new estimate every 500 ms
- Latency: p50 ≤ 120 ms, p95 ≤ 250 ms
- Sustained throughput: ≥ 20 decisions/sec

---

## 8. Compliance & Ethics

### 8.1 Ethical Guidelines

- No demographic bias in training
- Clear statements of capabilities/limitations
- User consent for data collection; opt‑out available

### 8.2 Regulatory Compliance

- GDPR, COPPA, WCAG 2.1

### 8.3 Data Governance

- Data retention policies; right to be forgotten; DSAR process

---

## 9. Risks and Mitigations

| Risk                    | Impact | Likelihood | Mitigation                              |
| ----------------------- | ------ | ---------- | --------------------------------------- |
| Model Drift             | High   | Medium     | Monitoring + retraining pipeline        |
| Privacy Concerns        | High   | Low        | On‑device processing, data minimization |
| Hardware Limits         | Medium | Medium     | Optimization, quantization              |
| Performance Bottlenecks | High   | Medium     | Profiling + targeted fixes              |
| Data Quality Issues     | High   | Medium     | Rigorous validation/cleaning            |

---

## 9.5 Project Phases

The project is organized into three sequential phases, each building on the previous:

### Phase 1: Offline ML Classification System

**Scope:** Foundation infrastructure and model training pipeline

- Web application for video generation, upload, and emotion labeling
- EfficientNet-B0 fine-tuning pipeline with transfer learning
- FastAPI gateway and Media Mover services
- Database schema and MLflow experiment tracking
- Quality Gate A validation (F1 ≥ 0.84, ECE ≤ 0.08)

**Key Files:** `apps/web/`, `trainer/fer_finetune/`, `apps/api/`

### Phase 2: Emotional Intelligence Layer

**Scope:** Degree, PPE, EQ metrics + response generation

- **Degree of Emotion**: Continuous confidence scores (0–1) from softmax
- **Primary Principles of Emotion (PPE)**: 8-class Ekman taxonomy mapping
- **Emotional Intelligence (EQ)**: Calibration metrics (ECE, Brier, MCE)
- **Gesture Modulation**: Confidence-tiered gesture expressiveness (5 tiers)
- **LLM Prompt Tailoring**: Emotion-conditioned prompts with confidence guidance

**Key Files:** 

- `apps/reachy/gestures/gesture_modulator.py` — Degree-modulated gestures
- `apps/llm/prompts/emotion_prompts.py` — Emotion-conditioned LLM prompts
- `apps/reachy/gestures/emotion_gesture_map.py` — PPE gesture mapping
- `trainer/fer_finetune/evaluate.py` — EQ calibration metrics

### Phase 3: Edge Deployment & Real-Time Inference

**Scope:** Jetson deployment and production optimization

- TensorRT engine conversion (ONNX → .engine)
- DeepStream pipeline configuration
- Real-time inference on Jetson Xavier NX
- WebSocket communication (Jetson ↔ Ubuntu 2)
- Quality Gates B & C validation (latency, memory, user satisfaction)
- Shadow → Canary → Rollout deployment stages

**Key Files:** `jetson/`, `apps/pipeline/emotion_llm_gesture.py`

---

## 10. Timeline and Milestones

| Milestone              | Target Date | Owner        | Status      |
| ---------------------- | ----------- | ------------ | ----------- |
| Requirements Finalized | 2025-10-01  | Russell Bray | In Progress |
| Initial Prototype      | 2025-12-31  | Russell Bray | Not Started |
| Beta Release           | 2026-02-15  | Russell Bray | Not Started |
| Production Release     | 2026-05-10  | Russell Bray | Not Started |

---

## 11. System Architecture Overview

### 11.1 Components

- **Ubuntu 1 — Model Host (heavy compute)**  
  LM Studio (Llama-3.1-8B-Instruct), synthetic video clients, **Media Mover API** (base: `https://10.0.4.130/api/media`), PostgreSQL (metadata only), Nginx static media, EfficientNet-B0 dual-head training/export pipeline.

- **Ubuntu 2 — App Gateway (ingress/orchestrator)**  
  Nginx reverse proxy + FastAPI app; receives Jetson JSON events; writes metadata; routes LLM calls; promotes videos via Media Mover; exposes `/healthz`, `/metrics`, `/ws/cues/{device_id}`.

- **Jetson (Reachy edge device)**  
  DeepStream + TensorRT (`gst-nvinfer`) loading EfficientNet-B0 EmotionNet `.engine`; emits JSON (no raw video); consumes cues over WebSocket.

### 11.2 Design Principles

- Local‑first; no raw video egress by default
- Separation of concerns across Jetson / Ubuntu 1 / Ubuntu 2
- Media served via Nginx to bypass app layers for efficiency

---

## 12. End‑to‑End Data Flow

1. Jetson detects emotion → Ubuntu 2 JSON (emotion, confidence, context).
2. Ubuntu 2 updates DB and requests LLM inference from Ubuntu 1.
3. Ubuntu 1 returns tone‑matched text.
4. Ubuntu 2 enqueues cue; Jetson receives via WebSocket and acknowledges.
5. Browser shows emotion, confidence, LLM text, video URL, thumbnail.
6. User curates → DB updated; clip promoted `temp → train/<label>` via Media Mover (label enforcement occurs here).
7. Training orchestrator prepares run-specific frame datasets by extracting 10 random frames/video into `train/<label>/<run_id>` and consolidated `train/run/<run_id>/<label>` (plus `test/<run_id>/<label>` for test-ready outputs).
8. TAO retraining; new TRT engine versioned/signed; packaged for DeepStream `nvinfer`.

---

## 13. APIs & Event Schemas

### 13.1 Jetson → Ubuntu 2: Emotion Event

```json
{
  "device_id": "reachy-mini-01",
  "ts": "2025-09-16T20:11:33Z",
  "emotion": "happy",
  "confidence": 0.87,
  "inference_ms": 92,
  "window": { "fps": 30, "size_s": 1.2, "hop_s": 0.5 },
  "meta": { "model_version": "emotionnet-0.8.4-trt", "temp": 68.2 }
}
```

Validation: `emotion ∈ {happy, sad, neutral}`, `0 ≤ confidence ≤ 1`.

### 13.2 Ubuntu 2 → Ubuntu 1: LLM Chat (LM Studio)

Endpoint: `POST http://10.0.4.140:1234/v1/chat/completions` (messages array with system+user prompts).

### 13.3 Ubuntu 2 → Browser: UI Payload

```json
{
  "emotion": "sad",
  "confidence": 0.82,
  "llm_text": "…",
  "video_url": "/videos/temp/clip_00123.mp4",
  "thumb_url": "/thumbs/clip_00123.jpg"
}
```

### 13.4 FastAPI Gateway (Ubuntu 2)

- `GET https://10.0.4.140/api/videos/list` — filter/paginate/lists
- `GET https://10.0.4.140/api/videos/{video_id}` — metadata lookup
- `PATCH https://10.0.4.140/api/videos/{video_id}/label` — label updates (422 on validation)
- `POST https://10.0.4.140/api/promote` — promote clips from `temp` → `train/<label>`
- `POST https://10.0.4.140/api/manifest/rebuild` — rebuild manifests per run
- `POST https://10.0.4.140/api/v1/promote/reset-manifest` — rebuild manifests per run

### 13.5 Media Mover (Ubuntu 2 → Ubuntu 1)

`POST http://10.0.4.140/api/media/promote` → `{ clip, target, label, correlation_id, dry_run }`

### 13.6 WebSocket Cues (Ubuntu 2 → Jetson)

Server → client: `{ type: "tts|gesture", text, gesture_id, correlation_id, expires_at }`; client → server ack by `correlation_id`.

### 13.7 Error Model & Retries

- Standard error: `{ error, message, correlation_id, fields? }`
- Retry: backoff + jitter on 5xx/network; no retry on 4xx
- Idempotency: `Idempotency-Key` required on writes

### 13.8 AuthN/AuthZ & Transport

- mTLS or short‑lived JWTs for service calls; strict CORS; TLS 1.3; Nginx hardening

---

## 14. Data Storage & Curation Workflow

- **Directories on Ubuntu 1**: `/videos/temp/`, `/videos/train/`, `/videos/test/`, `/videos/thumbs/`, `/videos/manifests/`
- **Path convention**: DB keeps **relative** `storage_path` (e.g., `videos/train/happy/abc123.mp4`); `split` includes `temp`, `train`, `test`.
- **On‑ingest**: compute `sha256`, `size_bytes`; `ffprobe` metadata; generate `thumbs/{stem}.jpg`.
- **Promotion**: accepted clips move `temp → train/<label>`; labels validated and promotion log appended during the move.
- **Run frame extraction**: per training run, dataset prep extracts 10 random frames per source video into `train/<label>/<run_id>/` and builds consolidated training frames in `train/run/<run_id>/<label>/`.
- **Run manifests**: each run writes `manifests/<run_id>_train.jsonl` with frame paths and source-video metadata.
- **Dedup**: unique index on `(sha256, size_bytes)` applies across all splits.
- **Dry‑run**: supported for both staging and sampling operations to preview counts and collisions.
- **Idempotency**: enforced via `Idempotency-Key` on writes.
- **Integrity & audits**: nightly reconciler verifies `train/` labeled sources plus active run-frame directories; manifests include `run_id` and `source_video` metadata.
- **Retention**: `temp/` TTL 7–14 days; `train/<run_id>/` and `train/<label>/<run_id>/` can be pruned per run after artifacts are sealed.

---

## 15. Database Schema (Metadata)

```sql
CREATE TABLE video (
  video_id       UUID PRIMARY KEY,
  file_path      TEXT NOT NULL, -- relative path under videos/
  split          TEXT CHECK (split IN ('temp','train','test')) NOT NULL,
  label          TEXT,
  duration_sec   NUMERIC,
  fps            NUMERIC,
  width          INT,
  height         INT,
  size_bytes     BIGINT,
  sha256         TEXT,
  zfs_snapshot   TEXT,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_video_sha ON video(sha256, size_bytes);

CREATE TABLE run_link (
  mlflow_run_id  TEXT PRIMARY KEY,
  dataset_hash   TEXT NOT NULL,
  snapshot_ref   TEXT,
  created_at     TIMESTAMPTZ DEFAULT now()
);
```

**Policy:** DB is the source of truth for labels/splits; manifests are derived.

**Connection Defaults:** `host=10.0.4.130`, `port=5432`, `database=reachy_emotion`, `user=reachy_dev`, password via Vault secret. Application overrides use `DB_URL=postgresql+asyncpg://reachy_dev:***@10.0.4.130:5432/reachy_emotion`.

CREATE TABLE training_run (
  run_id         UUID PRIMARY KEY,
  created_at     TIMESTAMPTZ DEFAULT now(),
  strategy       TEXT NOT NULL,
  train_fraction NUMERIC NOT NULL,
  test_fraction  NUMERIC NOT NULL,
  seed           BIGINT,
  status         TEXT DEFAULT 'pending'
);

CREATE TABLE training_selection (
  run_id       UUID REFERENCES training_run(run_id) ON DELETE CASCADE,
  video_id     UUID REFERENCES video(video_id),
  target_split TEXT CHECK (target_split IN ('train','test')),
  PRIMARY KEY (run_id, video_id, target_split)
);

---

## 16. API Contracts

### 16.1 FastAPI Gateway (Ubuntu 2)

- Base: `https://10.0.4.140/api`
- `/videos/list`: supports `split`, `limit`, `offset`, `label`, `order_by`, `order`
- `/videos/{video_id}`: returns metadata + derived file status (404 if file missing)
- `/videos/{video_id}/label`: PATCH body `{ "new_label": "happy" }`; enforces label policy
- `/v1/promote/stage`: `{ video_ids: [], label, dry_run?, correlation_id?, idempotency_key? }`
- `/v1/promote/sample`: `{ run_id, target_split, sample_fraction, strategy, dry_run?, seed? }`
- `/v1/promote/reset-manifest`: resets manifests and clears cached selections for `run_id`
- `/metrics` & `/health`: internal monitoring endpoints

### 16.2 Media Mover API (Ubuntu 1)

- Base: `https://10.0.4.130/api/media`
- `GET /api/media`: service status/version
- `POST /api/media/promote`: filesystem move/copy operations mirroring gateway requests
- `POST /api/media/train/reset`: prune/archive selections for given `run_id`
- `POST /api/relabel`: update label directly in metadata store (protected)
- `POST /api/manifest/rebuild`: regenerate manifests + return `dataset_hash`

All mutate endpoints require Bearer/JWT creds issued via Vault. Gateway requests include `Idempotency-Key`; Media Mover enforces the same correlation ID for audit trails.

---

## 17. Networking, Ports, and Security

- **Ingress**: Jetson → Ubuntu 2 only (HTTPS `:443`, WebSocket `/ws/cues/*`)
- **Ubuntu 2 → Ubuntu 1**: LM Studio `:1234`, Media Mover `:8083` (base `https://10.0.4.130/api/media`), PostgreSQL `:5432`, Nginx media `:80/:443`, Redis `:6379` (optional)
- **Prometheus**: internal `/metrics` (media-mover `:9101`, gateway `:9100`); FastAPI gateway exposes `/metrics` guarded behind Nginx allow-list.
- **Prohibitions**: no Jetson↔Ubuntu 1 video streaming; DeepStream not exposed outside Jetson
- **Edge auth**: mTLS/JWT; tokens ≤15 min; Vault‑managed keys; rotate ≤90 days
- **Reverse proxy hardening**: range requests, strict MIME, gzip text only, cache controls, request limits, CORS allow-list, `/api/v1/promote/*` limited to LAN subnets
- **API hardening**: timeouts, retries, JSON logs, correlation IDs, idempotency keys; `/healthz` & `/metrics` internal only
- **DB access**: least privilege roles; TLS if feasible; IP restrict. Default metadata credentials: `reachy_dev@10.0.4.130:5432/reachy_emotion` (managed via Vault, rotated ≤90 days).
- **Secrets**: no secrets in images; env-only; short-lived tokens; DB credentials use `reachy_dev` role scoped to metadata schema
- **Firewall**: default‑deny; allow known subnets/ports

---

## 18. Observability & Operations

- Structured logs: latency histograms, fps, GPU mem/temp, per‑class counts, abstain counts
- Dashboards: latency p50/p95, macro/per‑class F1, drift (KL), flicker rate, SLA breaches
- Alerts: WebSocket churn, NAS sync failures, manifest rebuild errors, dataset sampling anomalies (e.g., insufficient clips, labeled entries in `test`).

---

## 19. Emotion Taxonomy & Operating Points

- Labels: `happy`, `sad`, `angry`, `neutral`, `surprise`, `fearful`

---

## 20. Agentic AI System (08.4.2)

The system uses **ten cooperating agents**, each performing one narrow, auditable task. All orchestration occurs in **n8n** running on Ubuntu 1.

### Agent Roster:

1. **Ingest Agent** — Receive new videos (uploads or generated) and register them in the system
2. **Labeling Agent** — Manage user-assisted classification and dataset promotion (3-class: happy, sad, neutral)
3. **Promotion/Curation Agent** — Oversee controlled movement of media between filesystem stages
4. **Reconciler/Audit Agent** — Ensure filesystem and database consistency
5. **Training Orchestrator** — Trigger EfficientNet-B0 emotion classifier fine-tuning once dataset balance and size thresholds are met
6. **Evaluation Agent** — Run validation jobs once the test set is balanced
7. **Deployment Agent** — Promote validated engines from shadow → canary → rollout with explicit approval gates
8. **Privacy/Retention Agent** — Enforce local-first policy, TTLs for temporary media, and purge/redaction procedures
9. **Observability/Telemetry Agent** — Aggregate system metrics and raise alerts when thresholds are breached
10. **Reachy Gesture Agent** — Execute physical gestures on the Reachy Mini robot based on emotion context and LLM response cues

### Agent Contracts:

- Agents register contracts (name/version/role, inputs/outputs schemas, tools, authority, limits, security, observability, ownership)
- Storage‑aware: agents reference **relative** media paths + `sha256`, never embed raw media
- See `AGENTS.md` for detailed responsibilities, approval rules, and SLOs

---

## 21. Model Packaging & Serving on Jetson

- DeepStream `gst‑nvinfer` loads TensorRT `.engine` for EmotionNet
- Preferred precision FP16; optional INT8 with calibration set
- Minimal DeepStream container; include `nvinfer` configs and engine paths
- **No Triton** on Jetson for v0.8.3 (revisit later)

---

### Changelog

- [2025-10-28 21:37:00] - Added staged dataset preparation workflows, randomized train/test selection requirements, API/schema updates, and monitoring expectations.
- [2025-11-26 03:55:00] - Documented `/api/v1/promote/*` gateway endpoints, refreshed DB credentials (`reachy_dev`), noted full gateway test pass, and aligned observability/networking details.
- [2026-02-18 11:50:00] - Updated architecture to direct `temp -> train/<label>` promotion and run-specific frame extraction (10 frames/video) into `train/<label>/<run_id>` with consolidated `train/<run_id>/<label>` datasets and frame-based manifests.
- [2026-02-19 10:58:00] - Updated consolidated run dataset conventions to `train/run/<run_id>/<label>` and `test/<run_id>/<label>` while preserving run-scoped extraction under `train/<label>/<run_id>`.
- [2026-03-13 02:45:00] - Added Agent 10 (Reachy Gesture Agent) to agentic system; updated Phase 2 status to 95% complete; synchronized all documentation to reflect 10-agent architecture.

---

## 22. Secrets & Registry

- Secrets: HashiCorp Vault issues & rotates certs, JWT keys, DB creds, LM Studio/Luma creds (≤90 days)
- Container registry: GHCR with cosign signatures

---

## 23. Operations Playbooks

- **Promote Flow**: request → atomic move → DB update → manifest rebuild → optional ZFS snapshot
- **Rollback**: stop writers → `zfs rollback` → rebuild manifests → re‑evaluate
- **Backup/Restore**: nightly rsync to NAS; quarterly restore test with hash verification
- **Integrity**: nightly `sha256` recompute for changed files; compare to DB

---

## 24. Acceptance Criteria

- **Gateway+Media Mover expose** `list`, `thumb`, direct `promote` (`temp -> train/<label>`), `relabel`, and manifest rebuild endpoints with auth and atomic moves
- **Training prep outputs run-specific frame datasets** in `train/<label>/<run_id>` and consolidated `train/run/<run_id>/<label>` (and optional `test/<run_id>/<label>`) with exactly 10 sampled frames per source video when sufficient frames exist
- MLflow runs contain **dataset_hash** and (if ZFS) **snapshot_ref** with artifacts visible in UI
- NAS sync passes nightly; quarterly restore verified
- Nginx thumbnail latency and manifest rebuild times meet targets in §6.3
- FastAPI gateway regression suite (59 tests) remains green before promoting config changes

---

*Document Version Control*

| Version  | Date       | Author  | Changes                                                                                                                          |
| --------:| ---------- | ------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 0.08.3.2 | 2025-09-20 | Team    | Integrated hybrid storage, mini‑FastAPI endpoints, MLflow linkage, NAS redundancy, DB schema, ops playbooks, acceptance criteria |
| 0.8.3    | 2025-09-20 | Team    | Hybrid storage, DeepStream runtime, gateway hardening, reconciler & metrics                                                      |
| 0.2.0    | 2025-09-16 | Cascade | Added comprehensive technical specifications, quality gates, and compliance                                                      |
| 0.1.0    | 2025-09-16 | System  | Initial draft                                                                                                                    |
