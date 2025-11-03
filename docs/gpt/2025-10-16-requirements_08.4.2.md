# Project Requirements — Reachy_Local_08.4.2

## 1. Project Overview
- **Project Name**: Reachy_Local_08.4.2
- **Version**: 0.08.4.2
- **Last Updated**: 2025-10-16
- **Project Type**: Robotics Control Software
- **Target Platform**: Reachy Mini Companion Robot — Jetson Xavier NX 16GB model
- **Primary Language**: Python 3.8+

### Version History
| Version | Date       | Author           | Changes Description                                                                                                                                           |
|--------:|------------|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1.0   | 2025-09-16 | Russell Bray     | Initial requirements draft                                                                                                                                    |
| 0.2.0   | 2025-09-16 | Cascade          | Added deployment gates, performance metrics, privacy controls, and acceptance criteria                                                                         |
| 0.8.3   | 2025-09-20 | Team             | Hybrid storage (PostgreSQL metadata + ext4 media via Nginx), DeepStream-only runtime, FastAPI gateway, checksum/dedup, promotion dry‑run, reconciler & metrics, tightened security |
| 0.08.3.2| 2025-09-20 | Team             | Integrated **Reachy_Storage.md** guidance: canonical FS layout, mini‑FastAPI endpoints, MLflow lineage, NAS redundancy, DB schema, ops playbooks, acceptance criteria |
| 0.08.3.3| 2025-10-06 | Team             | Pin TAO container/image version; document workspace mounts and envs; canonicalize storage root on Ubuntu 1; add explicit endpoint map; clarify EmotionNet schema; note Media Mover on Ubuntu 1 |
| 0.08.4.2| 2025-10-16 | Team             | Project renamed to Reachy_Local_08.4.2; updated README alignment; agentic AI system integration; enhanced privacy controls and deployment gates |
| 0.08.4.3| 2025-10-28 | Team             | Introduced `/videos/dataset_all/` staging, randomized train/test selection workflows, and updated promotion/manifest requirements |

### Project Description
Reachy‑Emotion‑Recognition is an open‑source robotic platform designed for human‑robot interaction and research. This project implements a privacy‑preserving emotion recognition system with a continuous improvement loop:

1. **Data Generation**: Web app for generating and classifying synthetic emotion videos.
2. **Model Training**: Fine‑tuning of EmotionNet models with rigorous validation.
3. **Deployment**: Containerized deployment to Reachy robots with staged rollout.
4. **Inference**: Real‑time emotion classification with strict performance SLAs.
5. **Feedback Loop**: Ongoing user‑based classifications improve future model iterations.

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

---

## 2. Project Scope

### 2.1 In Scope
- Generate and classify videos of people expressing emotions
- Python API used for emotion recognition
- Advanced AI/ML capabilities use generated videos for model fine‑tuning
- Safety features and privacy protection
- **Primary storage on local filesystem** (ext4 or ZFS) with canonical layout: `/videos/{temp,dataset_all,train,test,thumbs,manifests}`. Labeled clips persist in `dataset_all`; `train`/`test` are regenerated per fine-tuning run from that corpus.
- **mini‑FastAPI “media mover”** to list media, serve thumbnails (via Nginx), perform atomic promotions, and rebuild manifests
- **MLflow (file‑backed)** for experiment/run tracking (params, metrics, artifacts) tied to dataset hashes and optional ZFS snapshot tags
- **Synology NAS redundancy** via NFS/SMB mirroring of `/videos/*` and MLflow artifacts; SSD remains the hot path

### 2.2 Out of Scope
- Hardware specification and procurement details for Reachy Mini (covered elsewhere)
- Object‑store semantics (S3/MinIO/Supabase buckets) for this phase
- Using MLflow as a media server (tracking only; artifacts live on filesystem)

---

## 3. Stakeholders
| Role | Name | Contact | Responsibilities |
|------|------|---------|------------------|
| Product Owner | Russell Bray  | rustybee255@gmail.com | Project vision & development |
| Lead Developer | Russell Bray | rustybee255@gmail.com | Technical direction & implementation |
| ML/Computer Vision Engineer | Russell Bray | rustybee255@gmail.com | ML & CV components |
| End Users | Unknown | Unknown | Interaction with Reachy |

---

## 4. Architecture & Data Flow

**Hot Path (low‑latency):** Jetson/ingest → `/videos/temp` → human labeling in web UI → `POST /api/media/promote` (stage into `/videos/dataset_all`) → per-run sampling engine copies randomized subsets into `/videos/train` and `/videos/test` → rebuild manifests → training/eval → gated deploy.

**Serving:** Nginx serves `/thumbs/`; mini‑FastAPI exposes `list`, `thumb`, `promote`, `relabel`, `manifest/rebuild`.

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
  `GET /api/videos/list?split={temp|dataset_all|train|test}&limit=&offset=` returns `video_id, path, size, mtime`.
- **FR‑STOR‑002 — Stage to dataset**  
  `POST /api/media/promote {video_id, dest_split="dataset_all", label, dry_run?}` atomically moves accepted clips from `/videos/temp` into `/videos/dataset_all` while updating Postgres metadata and promotion logs.
- **FR‑STOR‑003 — Randomized train/test selection**  
  `POST /api/media/promote {run_id, dest_split="train"|"test", sample_strategy, sample_fraction, seed?, dry_run?}` copies clips from `/videos/dataset_all` into `/videos/train` and `/videos/test` for a specific training run, enforcing label policy (`train` labeled, `test` unlabeled) and returning selection manifests.
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
- **ML Framework (legacy)**: TensorFlow 2.14+ with CUDA 12 *(legacy compatibility; training uses TAO 6.x PyTorch)*
- **NVIDIA Framework Wheel**: 24.05
- **NVIDIA JetPack**: 5.x
- **Containerization**: Docker 20.10+ with NVIDIA Container Toolkit
- **Deep Learning (Training, Ubuntu 1)**: NVIDIA TAO Toolkit **6.x (PyTorch)**
- **Inference (Jetson)**: NVIDIA **DeepStream SDK 6.x** + **TensorRT 8.6+** (`gst-nvinfer`, `pyds`, GStreamer 1.22+)
- **API Gateway**: FastAPI **0.110+** (Pydantic v2), `orjson 3.10+`
- **ASGI Server**: Uvicorn **0.29+** (optionally under Gunicorn)
- **Reverse Proxy**: Nginx **1.22+** (range requests; strict MIME allow‑list)
- **Database (metadata)**: PostgreSQL **15+**, SQLAlchemy **2.0+**, `psycopg2-binary 2.9+`, Alembic **1.13+`
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
- ZFS checksums when using ZFS; snapshot before each fine‑tune
- Mutate endpoints require Bearer/JWT; strict `video_id` validation; forbid arbitrary paths
- Optional ZFS native encryption or LUKS on ext4 for at‑rest protection
- rsync exit codes monitored; SMART monitoring on NAS

---

## 7. Model Deployment & Quality Gates

### 7.1 Deployment Gates
**Gate A — Offline Validation (Pre‑robot)**
- Macro F1 (val): ≥ 0.84; per‑class floors ≥ 0.75; no class < 0.70
- Balanced accuracy: ≥ 0.85
- Calibration: ECE ≤ 0.08, Brier ≤ 0.16

**Gate B — Robot Shadow Mode**
- On‑device latency: p50 ≤ 120 ms, p95 ≤ 250 ms
- GPU memory ≤ 2.5 GB; Macro F1 ≥ 0.80; per‑class floors ≥ 0.72; no class < 0.68

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
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Model Drift | High | Medium | Monitoring + retraining pipeline |
| Privacy Concerns | High | Low | On‑device processing, data minimization |
| Hardware Limits | Medium | Medium | Optimization, quantization |
| Performance Bottlenecks | High | Medium | Profiling + targeted fixes |
| Data Quality Issues | High | Medium | Rigorous validation/cleaning |

---

## 10. Timeline and Milestones
| Milestone | Target Date | Owner | Status |
|-----------|-------------|-------|--------|
| Requirements Finalized | 2025-10-01 | Russell Bray | In Progress |
| Initial Prototype | 2025-12-31 | Russell Bray | Not Started |
| Beta Release | 2026-02-15 | Russell Bray | Not Started |
| Production Release | 2026-05-10 | Russell Bray | Not Started |

---

## 11. System Architecture Overview

### 11.1 Components
- **Ubuntu 1 — Model Host (heavy compute)**  
  LM Studio (Llama‑3.1‑8B‑Instruct), synthetic video clients, **Media Mover API** (base: `https://10.0.4.130/api/media`), PostgreSQL (metadata only), Nginx static media.

- **Ubuntu 2 — App Gateway (ingress/orchestrator)**  
  Nginx reverse proxy + FastAPI app; receives Jetson JSON events; writes metadata; routes LLM calls; promotes videos via Media Mover; exposes `/healthz`, `/metrics`, `/ws/cues/{device_id}`.

- **Jetson (Reachy edge device)**  
  DeepStream + TensorRT (`gst‑nvinfer`) loading EmotionNet `.engine`; emits JSON (no raw video); consumes cues over WebSocket.

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
6. User curates → DB updated; clip promoted `temp → dataset_all` via Media Mover (label enforcement occurs here).
7. Training orchestrator requests a balanced sample → Media Mover copies randomized subsets from `dataset_all` into `train/` and `test/`, tagging selections with `run_id` and respecting configured fractions (e.g., 70%/30%) and label policy (`test` unlabeled).
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
Validation: `emotion ∈ {happy, sad}`, `0 ≤ confidence ≤ 1`.

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

### 13.4 Media Mover (Ubuntu 2 → Ubuntu 1)
`POST http://10.0.4.140/api/media/promote` → `{ clip, target, label, correlation_id, dry_run }`

### 13.5 WebSocket Cues (Ubuntu 2 → Jetson)
Server → client: `{ type: "tts|gesture", text, gesture_id, correlation_id, expires_at }`; client → server ack by `correlation_id`.

### 13.6 Error Model & Retries
- Standard error: `{ error, message, correlation_id, fields? }`
- Retry: backoff + jitter on 5xx/network; no retry on 4xx
- Idempotency: `Idempotency-Key` required on writes

### 13.7 AuthN/AuthZ & Transport
- mTLS or short‑lived JWTs for service calls; strict CORS; TLS 1.3; Nginx hardening

---

## 14. Data Storage & Curation Workflow
- **Directories on Ubuntu 1**: `/videos/temp/`, `/videos/dataset_all/`, `/videos/train/`, `/videos/test/`, `/videos/thumbs/`, `/videos/manifests/`
- **Path convention**: DB keeps **relative** `storage_path` (e.g., `videos/dataset_all/abc123.mp4`); `split` now includes `temp`, `dataset_all`, `train`, `test`.
- **On‑ingest**: compute `sha256`, `size_bytes`; `ffprobe` metadata; generate `thumbs/{stem}.jpg`.
- **Staging**: accepted clips move `temp → dataset_all`; labels validated and promotion log appended during the move.
- **Run sampling**: per training run, the promotion service copies randomized subsets from `dataset_all` into `train/` and `test/`, attaching a `run_id`. `train` copies retain labels; `test` copies enforce `label IS NULL` in DB.
- **Dedup**: unique index on `(sha256, size_bytes)` applies across all splits.
- **Dry‑run**: supported for both staging and sampling operations to preview counts and collisions.
- **Idempotency**: enforced via `Idempotency-Key` on writes.
- **Integrity & audits**: nightly reconciler verifies `dataset_all` plus active run splits; manifests include `run_id` metadata.
- **Retention**: `temp/` TTL 7–14 days; `train/` and `test/` can be pruned per run after artifacts are sealed; `dataset_all/` retains the canonical labeled corpus.

---

## 15. Database Schema (Metadata)
```sql
CREATE TABLE video (
  video_id       UUID PRIMARY KEY,
  file_path      TEXT NOT NULL, -- relative path under videos/
  split          TEXT CHECK (split IN ('temp','dataset_all','train','test')) NOT NULL,
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

## 16. API Contract (mini‑FastAPI)
- Base: `GET /api/media` → returns service status and version. Base URL: `https://10.0.4.130/api/media`
- `GET /api/videos/list?split={temp|dataset_all|train|test}&limit=&offset=` → list items (paged)
- `GET /api/videos/{video_id}` → size, mtime, split
- `GET /api/videos/{video_id}/thumb` → file/redirect `/thumbs/{video_id}.jpg`
- `POST /api/media/promote` (auth)
  - **Stage mode**: `{ video_id, dest_split="dataset_all", label, dry_run?, correlation_id?, idempotency_key? }`
  - **Sample mode**: `{ run_id, dest_split="train"|"test", sample_strategy?, sample_fraction?, seed?, dry_run?, include_labels? }` (service copies from `dataset_all`, enforces label policy, emits selection manifests)
  - Compatibility alias: `POST /api/promote` (kept for existing clients)
- `POST /api/media/train/reset` (auth, optional) → prune or archive existing `train/` and `test/` selections for a given `run_id`
- `POST /api/relabel` (auth) → update label
- `POST /api/manifest/rebuild` (auth) → regenerate JSONL manifests + return `dataset_hash`

All mutate endpoints require Bearer/JWT.

---

## 17. Networking, Ports, and Security
- **Ingress**: Jetson → Ubuntu 2 only (HTTPS `:443`, WebSocket `/ws/cues/*`)
- **Ubuntu 2 → Ubuntu 1**: LM Studio `:1234`, Media Mover `:8081` (base `https://10.0.4.130/api/media`), PostgreSQL `:5432`, Nginx media `:80/:443`, Redis `:6379` (optional)
- **Prometheus**: internal `/metrics` (media‑mover `:9101`, gateway `:9100`)
- **Prohibitions**: no Jetson↔Ubuntu 1 video streaming; DeepStream not exposed outside Jetson
- **Edge auth**: mTLS/JWT; tokens ≤15 min; Vault‑managed keys; rotate ≤90 days
- **Reverse proxy hardening**: range requests, strict MIME, gzip text only, cache controls, request limits, CORS allow‑list
- **API hardening**: timeouts, retries, JSON logs, correlation IDs, idempotency keys; `/healthz` & `/metrics` internal only
- **DB access**: least privilege roles; TLS if feasible; IP restrict
- **Secrets**: no secrets in images; env‑only; short‑lived tokens
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

## 20. Agentic AI System (08.3)
- Agents register contracts (name/version/role, inputs/outputs schemas, tools, authority, limits, security, observability, ownership)
- Storage‑aware: agents reference **relative** media paths + `sha256`, never embed raw media
- Roles include Ingest, Labeling, Promotion/Curation, Reconciler/Audit, Training Orchestrator, Evaluation, Deployment, Privacy/Retention, Observability

---

## 21. Model Packaging & Serving on Jetson
- DeepStream `gst‑nvinfer` loads TensorRT `.engine` for EmotionNet
- Preferred precision FP16; optional INT8 with calibration set
- Minimal DeepStream container; include `nvinfer` configs and engine paths
- **No Triton** on Jetson for v0.8.3 (revisit later)

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
- Media‑mover exposes **list**, **thumb**, **promote**, **relabel**, **manifest rebuild** with auth and atomic moves
- MLflow runs contain **dataset_hash** and (if ZFS) **snapshot_ref** with artifacts visible in UI
- NAS sync passes nightly; quarterly restore verified
- Nginx thumbnail latency and manifest rebuild times meet targets in §6.3

---

*Document Version Control*

| Version  | Date       | Author | Changes |
|---------:|------------|--------|---------|
| 0.08.3.2 | 2025-09-20 | Team   | Integrated hybrid storage, mini‑FastAPI endpoints, MLflow linkage, NAS redundancy, DB schema, ops playbooks, acceptance criteria |
| 0.8.3    | 2025-09-20 | Team   | Hybrid storage, DeepStream runtime, gateway hardening, reconciler & metrics |
| 0.2.0    | 2025-09-16 | Cascade| Added comprehensive technical specifications, quality gates, and compliance |
| 0.1.0    | 2025-09-16 | System | Initial draft |

