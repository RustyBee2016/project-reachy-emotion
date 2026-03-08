# Reachy Emotion Detection System: Comprehensive System Description

## Executive Summary for Project Managers

**Project Name:** Reachy_Local_08.4.2 — Agentic AI Emotion Detection System
**Platform:** Reachy Mini Humanoid Robot (Pollen Robotics)
**Architecture:** Edge-first, privacy-preserving, locally hosted ML pipeline
**Scope:** End-to-end emotion classification — from video ingestion to real-time inference on a humanoid robot

### What It Does

The Reachy Emotion Detection System gives a humanoid robot the ability to recognize human emotions in real time. A camera on the robot captures video, a neural network classifies facial expressions (happy, sad, neutral, etc.), and the robot responds with appropriate gestures and speech. All processing happens on-premise — no cloud services, no data leaving the building.

### Business Value

- **Privacy by design**: No video or biometric data is transmitted externally. Only derived metadata (e.g., "happy at 92% confidence") flows between components
- **Autonomous operation**: 10 AI agents manage the entire ML lifecycle — data collection, labeling, training, evaluation, deployment, and monitoring — with minimal human intervention
- **Continuous improvement**: The system automatically retrains and redeploys improved models when sufficient new data accumulates, with quality gates preventing regressions
- **Production-grade reliability**: Error handling, dead-letter queues, automated rollback, and 24/7 observability ensure the system self-heals from failures

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Inference latency (p95) | <250 ms | Time from frame capture to emotion classification |
| Throughput | 30 FPS | Frames processed per second on Jetson |
| Model accuracy (2-class) | F1 >= 0.84 | Happy/sad binary classification |
| Model accuracy (6-class) | F1 >= 0.75 | Full emotion spectrum |
| System uptime | 99%+ | Automated restart and recovery |

### Timeline and Status

| Phase | Status | Deliverables |
|-------|--------|-------------|
| Phase 1: Foundation | Complete | Database schema, API client, WebSocket client, Streamlit UI (43 tests) |
| Phase 2: ML Pipeline | Complete | TAO training configs, dataset preparation, MLflow tracking, TensorRT export (62 tests) |
| Phase 3: Edge Deployment | Complete | DeepStream pipeline, Jetson client, system monitoring, systemd service (46 tests) |
| Phase 4: Orchestration | Complete | 10 n8n agent workflows, 111+ nodes wired, 13-module curriculum |
| Phase 5: Production Hardening | Planned | Monitoring dashboards, alerting, security hardening, documentation |

### Team Impact

- **1 developer** can operate the entire system once deployed
- **13-module curriculum** (40-50 hours) trains new team members from zero n8n experience to professional-level workflow development
- **151 automated tests** with 90%+ pass rate ensure confidence in changes

---

## System Architecture

### Three-Node Deployment

The system runs on three physical machines in a local network:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOCAL NETWORK (10.0.4.x)                        │
│                                                                         │
│  ┌───────────────────────────────────┐                                  │
│  │  UBUNTU 1 (10.0.4.130)           │                                  │
│  │  "Training & Orchestration Node"  │                                  │
│  │                                   │                                  │
│  │  ┌─────────┐  ┌──────────────┐   │                                  │
│  │  │  n8n    │  │  PostgreSQL  │   │                                  │
│  │  │ :5678   │  │  :5432       │   │                                  │
│  │  │         │  │              │   │                                  │
│  │  │ 10 agent│  │ reachy_      │   │                                  │
│  │  │ wkflows │  │ emotion DB   │   │                                  │
│  │  └─────────┘  └──────────────┘   │                                  │
│  │  ┌─────────┐  ┌──────────────┐   │                                  │
│  │  │ Media   │  │   MLflow     │   │                                  │
│  │  │ Mover   │  │   :5000      │   │                                  │
│  │  │ :8083   │  │              │   │                                  │
│  │  └─────────┘  └──────────────┘   │                                  │
│  │  ┌─────────────────────────────┐ │                                  │
│  │  │ NVIDIA TAO 4.x (Docker)    │ │                                  │
│  │  │ GPU Training Environment    │ │                                  │
│  │  └─────────────────────────────┘ │                                  │
│  └───────────────────────────────────┘                                  │
│                    │                                                     │
│             HTTP / SSH / SCP                                             │
│                    │                                                     │
│  ┌───────────────────────────────────┐                                  │
│  │  UBUNTU 2 (10.0.4.140)           │                                  │
│  │  "Application Gateway"            │                                  │
│  │                                   │                                  │
│  │  ┌──────────────┐  ┌──────────┐  │                                  │
│  │  │ FastAPI      │  │ Streamlit│  │                                  │
│  │  │ Gateway      │  │ Web UI   │  │                                  │
│  │  │ :8000        │  │          │  │                                  │
│  │  └──────────────┘  └──────────┘  │                                  │
│  │  ┌──────────────────────────────┐│                                  │
│  │  │ Nginx (reverse proxy, TLS)  ││                                  │
│  │  └──────────────────────────────┘│                                  │
│  └───────────────────────────────────┘                                  │
│                    │                                                     │
│             WebSocket / HTTP                                             │
│                    │                                                     │
│  ┌───────────────────────────────────┐                                  │
│  │  JETSON XAVIER NX                │                                  │
│  │  "Edge Inference Node"            │                                  │
│  │                                   │                                  │
│  │  ┌──────────────┐  ┌──────────┐  │                                  │
│  │  │ DeepStream   │  │ Emotion  │  │                                  │
│  │  │ Pipeline     │─►│ Client   │──┼──► WebSocket to Gateway          │
│  │  │ (TensorRT)   │  │          │  │                                  │
│  │  └──────────────┘  └──────────┘  │                                  │
│  │  ┌──────────────────────────────┐│                                  │
│  │  │ systemd: reachy-emotion     ││                                  │
│  │  │ (auto-start, auto-restart)  ││                                  │
│  │  └──────────────────────────────┘│                                  │
│  └───────────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Camera ──► DeepStream ──► TensorRT ──► Emotion Event ──► WebSocket ──► Gateway
  (Jetson)   (video)      (inference)   {happy, 0.92}     (stream)     (Ubuntu 2)
                                                                          │
                                                                          ▼
                                                                     PostgreSQL
                                                                      (Ubuntu 1)
                                                                          │
                                              ┌───────────────────────────┤
                                              ▼                           ▼
                                         n8n Agents               Streamlit UI
                                      (orchestration)           (labeling, training,
                                              │                   deployment)
                                              ▼
                                        ML Pipeline
                                    (train → eval → deploy)
```

---

## The 10 Autonomous Agents

The system's intelligence is distributed across 10 autonomous agents, each implemented as an n8n workflow. Together they manage the complete ML lifecycle without manual intervention.

### Agent Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC ORCHESTRATION LAYER                      │
│                                                                         │
│  DATA PIPELINE                    ML PIPELINE                           │
│  ┌──────────┐  ┌──────────┐      ┌──────────┐  ┌──────────┐           │
│  │ Agent 1  │─►│ Agent 2  │      │ Agent 6  │─►│ Agent 7  │           │
│  │ Ingest   │  │ Labeling │      │ Training │  │ Eval     │           │
│  │ 12 nodes │  │ 9 nodes  │      │ 15 nodes │  │ 12 nodes │           │
│  └──────────┘  └────┬─────┘      └──────────┘  └────┬─────┘           │
│                      │                                │                  │
│                      ▼                                ▼                  │
│               ┌──────────┐                     ┌──────────┐             │
│               │ Agent 3  │                     │ Agent 8  │             │
│               │ Promote  │                     │ Deploy   │             │
│               │ 11 nodes │                     │ 14 nodes │             │
│               └──────────┘                     └──────────┘             │
│                                                                         │
│  MAINTENANCE                      ORCHESTRATION                         │
│  ┌──────────┐  ┌──────────┐      ┌──────────┐  ┌──────────┐           │
│  │ Agent 4  │  │ Agent 5  │      │ Agent 9  │  │ Agent 10 │           │
│  │ Reconcile│  │ Privacy  │      │ Observe  │  │ ML Orch  │           │
│  │ 9 nodes  │  │ 8 nodes  │      │ 6 nodes  │  │ 15 nodes │           │
│  └──────────┘  └──────────┘      └──────────┘  └──────────┘           │
│                                                                         │
│  Total: 111 nodes across 10 workflows                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent 1: Ingest Agent (12 nodes)

**Purpose:** Registers new video clips into the system with authentication, validation, and idempotent storage.

**Trigger:** HTTP webhook (`POST /ingest/video`)

**Flow:**
```
Webhook ──► Auth Check ──► Validate Payload ──► Fetch Media ──► Compute SHA256
    ──► DB Insert (ON CONFLICT) ──► Emit Event ──► Respond 201
```

**Key Patterns:**
- Bearer token authentication
- Idempotent ingestion via `ON CONFLICT (filename)` SQL clause
- SHA256 checksumming for deduplication
- Polling loop with configurable timeout for media availability
- Event emission to downstream agents

### Agent 2: Labeling Agent (9 nodes)

**Purpose:** Manages emotion label assignment to videos with class balance enforcement.

**Trigger:** HTTP webhook (`POST /label/video`)

**Flow:**
```
Webhook ──► Validate Label ──► CTE Query (class counts) ──► Switch (balance check)
    ──► [balanced] Apply Label ──► Respond 200
    ──► [imbalanced] Reject ──► Respond 409
```

**Key Patterns:**
- Common Table Expression (CTE) for real-time class distribution
- Switch node for multi-branch routing
- Three valid labels: happy, sad, neutral
- Class imbalance detection with configurable threshold

### Agent 3: Promotion Agent (11 nodes)

**Purpose:** Controls the movement of labeled videos from temporary storage to training/test splits using a two-phase approval workflow.

**Trigger:** HTTP webhook (`POST /promote/video`)

**Flow:**
```
Webhook ──► Dry-Run Check ──► [dry_run=true] Preview ──► Respond
                             ──► [dry_run=false] Human Approval Gate
                             ──► SCP to Target Split ──► DB Update ──► Respond
```

**Key Patterns:**
- Two-phase commit: dry-run preview, then actual promotion
- Human-in-the-loop approval gate
- Atomic file move via SCP + database update
- Rollback on partial failure

### Agent 4: Reconciler Agent (9 nodes)

**Purpose:** Detects and reports drift between filesystem state and database records.

**Trigger:** Scheduled (daily)

**Flow:**
```
Schedule ──► SSH List Jetson Files ──► DB Query All Records
    ──► Diff (files vs DB) ──► [drift detected] Email Report
                             ──► [no drift] Log "all clear"
```

**Key Patterns:**
- SSH remote command execution
- Set difference computation (files on disk vs. database records)
- Email alerting for drift detection
- Split In Batches for large file lists

### Agent 5: Privacy/Retention Agent (8 nodes)

**Purpose:** Enforces data retention policies (GDPR-style TTL) by automatically purging expired records.

**Trigger:** Scheduled (daily)

**Flow:**
```
Schedule ──► DB Query Expired ──► Split In Batches ──► Delete File
    ──► DB Mark Purged ──► Audit Log Insert ──► Summary Report
```

**Key Patterns:**
- TTL-based automatic data purging
- Batch processing with configurable batch size
- Audit trail for compliance (every deletion logged)
- Safe deletion: database mark before file removal

### Agent 6: Training Orchestrator (15 nodes)

**Purpose:** Manages the complete training lifecycle — from triggering NVIDIA TAO training to quality gate evaluation.

**Trigger:** HTTP webhook (`POST /agent/training/efficientnet/start`)

**Flow:**
```
Webhook ──► Init Run ──► SSH Start Training ──► Wait 10 min ──► Check MLflow
    ──► [running] Loop Back to Wait
    ──► [completed] Extract Metrics ──► Gate A Check (F1 >= 0.84)
    ──► [passed] Emit training.completed
    ──► [failed] Emit training.gate_failed
```

**Key Patterns:**
- SSH command execution for remote GPU training
- Polling loop with 10-minute intervals
- MLflow API integration for metric extraction
- Quality Gate A: minimum F1 score threshold
- Correlation IDs for cross-workflow tracking

### Agent 7: Evaluation Agent (12 nodes)

**Purpose:** Runs model evaluation on held-out test data and validates quality gates.

**Trigger:** HTTP webhook (`POST /agent/evaluation/efficientnet/start`)

**Flow:**
```
Webhook ──► SSH Run Evaluation ──► Wait 5 min ──► Fetch MLflow Metrics
    ──► Compute Gate A (precision, recall, F1) ──► DB Store Results
    ──► Emit evaluation.completed
```

**Key Patterns:**
- Batch metric extraction from MLflow
- Multi-metric Gate A evaluation (precision, recall, F1, per-class)
- Structured evaluation report generation

### Agent 8: Deployment Agent (14 nodes)

**Purpose:** Deploys validated models to the Jetson edge device with TensorRT optimization, canary verification, and automated rollback.

**Trigger:** HTTP webhook (`POST /agent/deployment/efficientnet/start`)

**Flow:**
```
Webhook ──► SCP Model to Jetson ──► SSH TensorRT Convert
    ──► SSH Restart DeepStream ──► Wait (soak test)
    ──► Gate B Check (latency, FPS, thermal)
    ──► [passed] Promote to Active ──► Emit deployment.completed
    ──► [failed] Rollback to Previous Model
```

**Key Patterns:**
- SCP large file transfer (model artifacts)
- TensorRT FP16 optimization on-device
- Gate B: on-device performance validation (latency < 100ms, 30 FPS, GPU < 75°C)
- Automated rollback on Gate B failure
- Shadow → Canary → Rollout deployment strategy

### Agent 9: Observability Agent (6 nodes)

**Purpose:** Collects system metrics from all infrastructure nodes every 30 seconds.

**Trigger:** Cron (every 30 seconds)

**Flow:**
```
Cron ──┬──► Fetch n8n Metrics ────────┐
       ├──► Fetch Media Mover Metrics ─┼──► Parse Prometheus ──► DB Store
       └──► Fetch Gateway Metrics ─────┘
```

**Key Patterns:**
- Parallel fan-out: one trigger to three simultaneous HTTP requests
- Prometheus text format parsing with regex
- Time-series data storage in PostgreSQL
- Sub-minute scheduling via Cron node

### Agent 10: ML Pipeline Orchestrator (15 nodes)

**Purpose:** End-to-end meta-workflow that coordinates Agents 6, 7, and 8 in sequence.

**Trigger:** HTTP webhook (`POST /ml/pipeline/start`)

**Flow:**
```
Webhook ──► Init Pipeline ──► Check Dataset Readiness
    ──► [insufficient data] Emit pipeline.blocked
    ──► [ready] Trigger Training (Agent 6) ──► Poll Status (10 min loop)
    ──► [training done] Trigger Evaluation (Agent 7) ──► Wait 5 min
    ──► [auto_deploy && gate_a_passed] Trigger Deployment (Agent 8)
    ──► Emit pipeline.completed
```

**Key Patterns:**
- Workflow-to-workflow orchestration via HTTP webhooks
- Dataset readiness validation (min 50 train / 20 test per class)
- Multi-stage sequential pipeline with conditional deployment
- Pipeline ID tracking for cross-agent correlation
- Duration tracking and completion events

---

## Cross-Cutting Concerns

### Error Handling (Module 11)

Three-layer error architecture:

1. **Node-level**: Retry on fail (3 attempts with 1s backoff) for network operations
2. **Workflow-level**: Global error handler workflow with error classification (network, infrastructure, data quality, permissions) and severity-based alerting
3. **System-level**: Dead-letter queue for failed items with automated 15-minute retry cycles

### Quality Gates

| Gate | Location | Criteria | Action on Failure |
|------|----------|----------|-------------------|
| **Gate A** | After Training/Evaluation | F1 >= 0.84 (2-class), F1 >= 0.75 (6-class) | Block deployment, alert |
| **Gate B** | After Deployment (soak test) | Latency < 100ms p95, 30 FPS, GPU < 75°C | Automatic rollback |
| **Gate C** | Production approval | Human sign-off | Hold in staging |

### Idempotency

All data pipeline agents are idempotent:
- Ingest: `ON CONFLICT (filename)` prevents duplicate records
- Labeling: `WHERE NOT EXISTS` guards against duplicate label assignment
- Promotion: Dry-run + human gate prevents accidental re-promotion
- Training: MLflow run deduplication by experiment + pipeline ID

### Observability

- **Metrics**: Prometheus-format metrics from n8n, Media Mover, and Gateway scraped every 30 seconds
- **Error tracking**: Centralized error_log table with severity classification
- **Audit trail**: All data mutations (ingestion, labeling, promotion, purging) are logged
- **Performance tracking**: Per-node execution timing in n8n execution history

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Orchestration** | n8n | 1.120+ | Workflow automation, agent coordination |
| **Database** | PostgreSQL | 16+ | Metadata, metrics, audit logs |
| **ORM** | SQLAlchemy | 2.x | Async database access |
| **Migration** | Alembic | -- | Schema versioning |
| **API** | FastAPI | -- | Gateway, event ingestion |
| **Web UI** | Streamlit | -- | Labeling, training, deployment interface |
| **ML Training** | NVIDIA TAO | 4.x | Transfer learning for EmotionNet |
| **Experiment Tracking** | MLflow | -- | Training metrics, model registry |
| **Inference** | TensorRT | 8.6+ | Optimized model execution |
| **Video Pipeline** | DeepStream | 6.x | GPU-accelerated video processing |
| **Edge Hardware** | Jetson Xavier NX | JetPack 5.x | On-device inference |
| **Process Management** | systemd | -- | Service lifecycle on Jetson |
| **Reverse Proxy** | Nginx | -- | TLS termination, rate limiting |
| **Language** | Python | 3.10+ | All application code |

---

## Database Schema (Key Tables)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `video` | Video clip metadata | id, filename, label, split, sha256, duration_sec |
| `promotion_log` | File movement audit | video_id, from_split, to_split, idempotency_key |
| `training_run` | ML training runs | run_id, status, strategy, seed |
| `training_selection` | Train/test split assignments | run_id, video_id, target |
| `emotion_event` | Real-time detections | device_id, emotion, confidence, inference_ms |
| `obs_samples` | Time-series metrics | ts, src, metric, value |
| `error_log` | Error tracking | severity, category, workflow_name, error_message |
| `dead_letter_queue` | Failed operation recovery | source_workflow, payload, retry_count, status |
| `deployment_log` | Model deployment history | model_version, gate_b_passed, deployment_target |

---

## Curriculum Structure

The system includes a 13-module training curriculum (40-50 hours) that teaches n8n workflow development through building the actual production system:

| Phase | Modules | Hours | Focus |
|-------|---------|-------|-------|
| Foundation | 00 | 3 | n8n fundamentals |
| Core Data Pipeline | 01-03 | 11 | Webhooks, auth, DB, idempotency |
| Maintenance | 04-05 | 5 | Scheduling, SSH, compliance |
| ML Pipeline | 06-08 | 12 | Training, evaluation, deployment |
| Observability | 09-10 | 8 | Metrics, multi-agent orchestration |
| Advanced | 11-13 | 6 | Error handling, testing, production ops |

Each module follows a consistent structure: pre-wiring checklist, concept explanation, step-by-step wiring (node-by-node, parameter-by-parameter), testing procedures, and troubleshooting guides.
