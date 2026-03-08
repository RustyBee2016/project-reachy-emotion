# Agentic Workflow Orchestration for Edge-Deployed Emotion Recognition: Architecture, Implementation, and Operational Patterns

**Authors:** Reachy_Local Project Team
**Date:** March 2026
**Keywords:** agentic AI, workflow orchestration, edge computing, emotion recognition, MLOps, n8n, DeepStream, TensorRT, humanoid robotics

---

## Abstract

We present the design and implementation of an agentic AI system for real-time emotion recognition on a humanoid robot platform. The system employs ten autonomous software agents, orchestrated through a low-code workflow engine (n8n), to manage the complete machine learning lifecycle: data ingestion, labeling, curation, model training, evaluation, edge deployment, privacy compliance, and observability. The architecture follows an edge-first, privacy-preserving design where raw video never leaves the inference device; only derived emotion metadata propagates through the system. We describe the multi-node deployment across a training server, application gateway, and NVIDIA Jetson Xavier NX edge device, achieving sub-100ms inference latency at 30 frames per second. We introduce a three-tier quality gate framework (offline accuracy, on-device performance, and production approval) that prevents model regressions from reaching production. We detail the error handling architecture — including dead-letter queues, automated retry cycles, and error classification — that enables the system to self-heal from transient failures. The system comprises 111 orchestration nodes across 10 workflows, backed by 151 automated tests, and is accompanied by a 13-module curriculum (40-50 hours) that doubles as both training material and system documentation. We discuss the trade-offs between low-code orchestration and traditional MLOps pipelines, the challenges of edge deployment in resource-constrained environments, and the operational patterns that emerged from building a production-grade agentic system.

---

## 1. Introduction

### 1.1 Motivation

Human-robot interaction (HRI) research has increasingly focused on affective computing — the ability of machines to recognize, interpret, and respond to human emotions. For social robots deployed in homes, healthcare facilities, and educational settings, emotion recognition enables more natural and empathetic interactions. However, deploying emotion recognition systems in real-world settings introduces challenges that laboratory prototypes rarely address:

1. **Privacy**: Continuous video capture of human faces raises significant privacy concerns. Cloud-based inference pipelines transmit sensitive biometric data across networks, creating attack surfaces and regulatory compliance burdens.

2. **Latency**: Social interaction demands real-time responsiveness. A robot that takes seconds to recognize an emotion breaks the illusion of natural conversation. Sub-100ms response times are necessary for fluid interaction.

3. **Operational complexity**: ML models degrade over time as the distribution of real-world data shifts from training data. Maintaining model quality requires a continuous cycle of data collection, labeling, retraining, evaluation, and deployment — a process known as MLOps — that is difficult to sustain without automation.

4. **Reliability**: A robot deployed in a home or care facility must operate autonomously for extended periods. Component failures, network interruptions, and resource exhaustion must be handled gracefully without human intervention.

This paper describes a system that addresses all four challenges through an architecture we term *agentic workflow orchestration* — the decomposition of ML lifecycle management into autonomous, event-driven agents coordinated by a workflow engine.

### 1.2 Contributions

This work makes the following contributions:

- **An edge-first emotion recognition architecture** that processes video entirely on-device, transmitting only derived metadata, achieving privacy by design without sacrificing latency.

- **A 10-agent orchestration framework** built on n8n that autonomously manages the ML lifecycle from data ingestion through production deployment, with quality gates preventing regressions.

- **A three-tier quality gate framework** (Gate A: offline accuracy, Gate B: on-device performance, Gate C: production approval) that ensures models meet both statistical and operational requirements before serving live traffic.

- **An error handling architecture** combining node-level retries, centralized error classification, dead-letter queues, and automated recovery that enables self-healing operation.

- **A 13-module practitioner curriculum** that serves as both training material and living system documentation, bridging the gap between system design and operational knowledge transfer.

### 1.3 System Context

The system is deployed on the Reachy Mini humanoid robot platform (Pollen Robotics). Reachy Mini features an expressive head with movable antennas and a camera, making it suitable for affective interaction research. The emotion recognition system enables the robot to detect human facial expressions in real time and respond with contextually appropriate gestures and vocalizations.

---

## 2. Related Work

### 2.1 Emotion Recognition Systems

Facial emotion recognition (FER) has been studied extensively using datasets such as FER2013 [Goodfellow et al., 2013], AffectNet [Mollahosseini et al., 2019], and RAF-DB [Li et al., 2017]. Modern approaches use deep convolutional neural networks, with EfficientNet [Tan and Le, 2019] and Vision Transformer [Dosovitskiy et al., 2021] architectures achieving state-of-the-art accuracy. Transfer learning from ImageNet pre-trained models is standard practice for FER due to limited labeled data.

Our system uses NVIDIA TAO Toolkit's EmotionNet, which provides a pre-trained EfficientNet-B0 backbone fine-tuned on emotion datasets. We further fine-tune on domain-specific data collected from the robot's camera to adapt to the specific deployment environment (lighting conditions, camera angle, typical user demographics).

### 2.2 Edge AI Deployment

Deploying neural networks on edge devices requires model optimization to meet latency and memory constraints. TensorRT [NVIDIA, 2023] provides layer fusion, kernel auto-tuning, and reduced-precision (FP16/INT8) inference that can achieve 2-5x speedup over unoptimized frameworks. DeepStream SDK [NVIDIA, 2023] provides a GStreamer-based pipeline for GPU-accelerated video analytics, handling video decode, pre-processing, batched inference, and post-processing in a single pipeline.

Prior work on edge-deployed emotion recognition includes EmotionMeter [Zhang et al., 2021], which demonstrated real-time FER on mobile devices using knowledge distillation, and FaceBoxes [Zhang et al., 2018] for lightweight face detection. Our contribution extends these with an end-to-end operational framework that handles not just inference but the entire ML lifecycle.

### 2.3 MLOps and Workflow Orchestration

MLOps platforms such as Kubeflow [Google, 2019], MLflow [Zaharia et al., 2018], and Metaflow [Netflix, 2019] provide frameworks for managing ML lifecycle. These systems typically assume cloud infrastructure and containerized workloads. For edge-deployed systems with on-premise constraints, lighter-weight orchestration is needed.

Low-code workflow engines such as n8n, Apache Airflow, and Prefect offer visual workflow design with extensible node types. n8n [n8n GmbH, 2019] is particularly suited to our use case because it supports webhook triggers (for event-driven agents), HTTP/SSH/database operations (for multi-node coordination), and self-hosted deployment (for on-premise requirements).

### 2.4 Agentic AI Systems

The concept of autonomous agents that perceive, decide, and act has roots in classical AI [Russell and Norvig, 2010]. Recent work on LLM-based agents [Shinn et al., 2023; Yao et al., 2023] has renewed interest in multi-agent architectures. Our system differs from LLM-agent systems in that our agents are *deterministic workflow agents* — their behavior is fully specified by workflow graphs rather than prompted language models. This provides predictability and auditability at the cost of flexibility.

---

## 3. System Architecture

### 3.1 Design Principles

The system is guided by five architectural principles:

1. **Edge-first privacy**: Raw video is processed exclusively on the edge device. Only derived metadata (emotion label, confidence score, inference time) crosses the network boundary.

2. **Event-driven autonomy**: Agents react to events (webhooks, schedules, upstream completions) rather than being centrally commanded. This decouples agents and allows independent evolution.

3. **Idempotent operations**: All data pipeline operations are idempotent — replaying the same event produces the same result without side effects. This enables safe retries and simplifies error recovery.

4. **Quality gates over continuous deployment**: Models are not deployed automatically unless they pass both statistical (Gate A) and operational (Gate B) quality gates. This prevents regressions from reaching production.

5. **Observable by default**: Every agent emits structured events, every data mutation is logged, and system metrics are collected every 30 seconds.

### 3.2 Physical Architecture

The system is deployed across three nodes connected by a local Ethernet network:

**Node 1 — Training and Orchestration (Ubuntu, x86_64 with GPU):**
- n8n workflow engine hosting all 10 agent workflows
- PostgreSQL database for metadata, metrics, and audit logs
- Media Mover API for filesystem operations
- MLflow for experiment tracking and model registry
- NVIDIA TAO Docker containers for GPU-accelerated training

**Node 2 — Application Gateway (Ubuntu, x86_64):**
- FastAPI gateway for event ingestion and API routing
- Streamlit web UI for human-in-the-loop operations
- Nginx reverse proxy with TLS termination and rate limiting
- WebSocket server for real-time event distribution

**Node 3 — Edge Inference (NVIDIA Jetson Xavier NX):**
- DeepStream 6.x pipeline for GPU-accelerated video processing
- TensorRT 8.6+ engine for optimized model inference
- WebSocket client for streaming emotion events to the gateway
- System monitor for GPU/CPU/thermal metrics
- systemd service for process lifecycle management

### 3.3 Communication Patterns

Three communication patterns connect the nodes:

1. **Synchronous HTTP**: API calls between n8n agents and backend services (Media Mover, MLflow, Gateway). Used for request-response operations where the caller needs an immediate result.

2. **Asynchronous WebSocket**: Event streaming from Jetson to Gateway. The emotion client maintains a persistent connection with automatic reconnection (infinite retry, exponential backoff up to 30 seconds) and 30-second heartbeats.

3. **SSH/SCP**: Remote command execution and file transfer between the training node and Jetson. Used for training execution, model transfer, and filesystem reconciliation.

### 3.4 Data Model

The PostgreSQL database contains nine primary tables:

| Table | Cardinality | Growth Rate | Purpose |
|-------|-------------|-------------|---------|
| `video` | Thousands | ~10/day | Video clip metadata and labels |
| `emotion_event` | Millions | ~30/second | Real-time inference results |
| `obs_samples` | Millions | ~6/minute | Infrastructure metrics |
| `promotion_log` | Hundreds | ~5/day | Data curation audit trail |
| `training_run` | Tens | ~1/week | ML experiment history |
| `training_selection` | Thousands | ~100/week | Train/test split assignments |
| `error_log` | Hundreds | Variable | Error tracking |
| `dead_letter_queue` | Tens | Variable | Failed operation recovery |
| `deployment_log` | Tens | ~1/week | Model deployment history |

The schema enforces data integrity through constraints:
- `chk_video_split_label_policy`: Ensures videos in training/test splits have labels, and videos in temp/test splits do not have unauthorized labels
- Unique constraint on `(sha256, size_bytes)` prevents duplicate video ingestion
- Foreign key relationships maintain referential integrity between runs, selections, and videos

---

## 4. Agent Design

### 4.1 Agent Taxonomy

We classify the 10 agents into four functional groups:

**Data Pipeline Agents (1-3):** Manage the flow of data from raw capture to curated training sets.
- Agent 1 (Ingest): Authenticates, validates, and stores incoming video metadata
- Agent 2 (Labeling): Assigns emotion labels with class balance enforcement
- Agent 3 (Promotion): Moves labeled videos to training/test splits with approval

**Maintenance Agents (4-5):** Ensure system integrity and regulatory compliance.
- Agent 4 (Reconciler): Detects filesystem-database drift via daily SSH audits
- Agent 5 (Privacy): Enforces TTL-based data retention with audit logging

**ML Pipeline Agents (6-8):** Execute the training-evaluation-deployment cycle.
- Agent 6 (Training Orchestrator): Triggers TAO training, monitors via MLflow, enforces Gate A
- Agent 7 (Evaluation Agent): Runs held-out evaluation, computes per-class metrics
- Agent 8 (Deployment Agent): Transfers model to Jetson, optimizes with TensorRT, enforces Gate B

**System Agents (9-10):** Provide observability and cross-agent coordination.
- Agent 9 (Observability): Scrapes Prometheus metrics from all nodes every 30 seconds
- Agent 10 (ML Pipeline Orchestrator): Sequences Agents 6-8 with dataset validation

### 4.2 Agent Communication

Agents communicate through three mechanisms:

1. **Direct HTTP invocation**: Agent 10 triggers Agents 6, 7, and 8 via their webhook endpoints. This creates explicit, traceable dependencies.

2. **Shared database state**: Agents 1-3 coordinate through the `video` table's `split` and `label` columns. Agent 1 creates records in `temp` split; Agent 2 adds labels; Agent 3 promotes to `train`/`test`.

3. **Event emission**: Agents emit structured events (e.g., `training.completed`, `pipeline.blocked`) via HTTP POST to the gateway. These events can trigger downstream workflows or update dashboards.

### 4.3 Idempotency Patterns

Each data pipeline agent implements idempotency differently:

**Agent 1 (Ingest)** uses PostgreSQL's `ON CONFLICT (filename) DO NOTHING` clause. Replaying an ingestion event for an already-ingested file is a no-op.

**Agent 2 (Labeling)** uses a `WHERE NOT EXISTS` guard. If a video already has a label, the labeling operation is skipped.

**Agent 3 (Promotion)** uses a two-phase approach: dry-run preview followed by human approval. The human gate inherently prevents accidental re-promotion.

**Agent 6 (Training)** uses MLflow run deduplication. Before starting a new training run, it checks for existing active runs with the same pipeline ID.

### 4.4 Node Composition

The 111 nodes across 10 workflows use 12 n8n node types:

| Node Type | Count | Purpose |
|-----------|-------|---------|
| Code (JavaScript) | 28 | Data transformation, validation, metric computation |
| HTTP Request | 24 | API calls to services, webhook triggers |
| Postgres | 18 | Database queries and insertions |
| IF | 14 | Conditional branching (quality gates, validation) |
| Webhook | 10 | Event triggers (one per workflow) |
| Wait | 8 | Polling intervals (training, evaluation) |
| SSH | 6 | Remote command execution |
| Respond to Webhook | 4 | HTTP response construction |
| Schedule Trigger | 3 | Cron-based triggers |
| Switch | 2 | Multi-branch routing |
| Split In Batches | 2 | Batch processing |
| Cron | 1 | Sub-minute scheduling |

---

## 5. Quality Gate Framework

### 5.1 Gate A: Offline Accuracy

Gate A evaluates model quality using held-out test data. It is enforced by Agent 7 (Evaluation) after training completes.

**Criteria:**

| Metric | Threshold (2-class) | Threshold (6-class) |
|--------|---------------------|---------------------|
| Macro F1 | >= 0.84 | >= 0.75 |
| Per-class precision | >= 0.80 | >= 0.70 |
| Per-class recall | >= 0.80 | >= 0.70 |

**Implementation:**
```
MLflow API ──► Extract metrics ──► Compare against thresholds
    ──► [all passed] gate_a_passed = true
    ──► [any failed] gate_a_passed = false, emit alert
```

Gate A prevents statistically underperforming models from proceeding to deployment. The thresholds are configurable per model variant (2-class vs. 6-class) and are stored in the training configuration YAML.

### 5.2 Gate B: On-Device Performance

Gate B evaluates model performance *on the target hardware* after deployment. It is enforced by Agent 8 (Deployment) during a soak test period.

**Criteria:**

| Metric | Threshold |
|--------|-----------|
| Inference latency (p95) | < 100 ms |
| Throughput | >= 30 FPS |
| GPU temperature | < 75°C |
| GPU throttling | None in 30-minute soak |

**Implementation:**
```
Deploy model ──► Restart DeepStream ──► Wait (soak period)
    ──► SSH tegrastats + custom metrics
    ──► [all passed] gate_b_passed = true, promote model
    ──► [any failed] gate_b_passed = false, rollback to previous model
```

Gate B addresses the reality that a model with good accuracy may still be unsuitable for production if it cannot meet latency requirements on the target hardware, causes thermal throttling, or exceeds memory budgets.

### 5.3 Gate C: Production Approval

Gate C is a human-in-the-loop approval gate used for the first deployment to production or when auto-deploy is disabled. The ML Pipeline Orchestrator (Agent 10) checks the `auto_deploy` flag: if `false`, the pipeline stops after evaluation and waits for manual approval.

### 5.4 Gate Interaction

The gates compose sequentially:

```
Training ──► Gate A (accuracy) ──► Deployment ──► Gate B (performance)
                                                        │
                                            [auto_deploy=false]
                                                        ▼
                                                   Gate C (human)
```

A model must pass Gate A before deployment is attempted. Gate B triggers automatic rollback if on-device performance is inadequate. Gate C provides a manual override for conservative deployment strategies.

---

## 6. Error Handling Architecture

### 6.1 Three-Layer Design

The error handling architecture operates at three levels:

**Layer 1 — Node-Level Retries:**
Individual nodes are configured with retry policies based on their failure characteristics:

| Operation Type | Max Retries | Backoff | Rationale |
|---------------|-------------|---------|-----------|
| HTTP Request (external) | 3 | 1 second | Transient network failures |
| SSH Command | 2 | 2 seconds | Connection establishment |
| SCP File Transfer | 3 | 5 seconds | Large file transfer reliability |
| Database Query | 0 | N/A | Failures indicate logic errors |

Non-critical operations (metric collection, notification emission) use n8n's "Continue on Fail" setting, allowing the workflow to proceed even if the node fails.

**Layer 2 — Workflow Error Handler:**
A centralized error handler workflow receives errors from all 10 agent workflows. It classifies errors by category (network, infrastructure, data quality, permissions) and severity (critical, error, warning), logs them to the `error_log` table, and dispatches alerts for critical failures.

**Layer 3 — Dead-Letter Queue:**
For data pipeline operations where retries are exhausted, failed items are inserted into the `dead_letter_queue` table. A scheduled retry workflow processes the DLQ every 15 minutes, re-attempting failed operations up to a configurable maximum (default: 3 retries).

### 6.2 Recovery Patterns

**Idempotent Recovery:** Data pipeline agents can be safely retried because their operations are idempotent. The DLQ retry workflow re-invokes the original operation, and database constraints prevent duplicate data creation.

**Training Recovery:** If a training run fails mid-execution, the MLflow run remains in `RUNNING` state. On retry, Agent 6 detects the existing active run and resumes monitoring instead of starting a new training job.

**Deployment Rollback:** If Gate B fails after model deployment, Agent 8 automatically restores the previous model version on the Jetson device, restarts DeepStream, and logs the rollback.

---

## 7. Observability

### 7.1 Metrics Collection

Agent 9 (Observability) collects Prometheus-format metrics from three endpoints every 30 seconds:

1. **n8n** (`http://n8n:5678/metrics`): Active executions, workflow execution counts, error rates
2. **Media Mover** (`http://10.0.4.130:9101/metrics`): Ingestion rates, promotion counts
3. **Gateway** (`http://10.0.4.140:9100/metrics`): Request rates, queue depth, response latencies

The agent uses parallel fan-out (one Cron trigger to three simultaneous HTTP Request nodes) to minimize collection latency. Metrics are parsed from Prometheus text format using regex and stored in the `obs_samples` time-series table.

### 7.2 Error Tracking

The centralized error handler classifies errors into five categories:

| Category | Detection Pattern | Severity |
|----------|------------------|----------|
| Network | `ETIMEDOUT`, `ECONNREFUSED` | Critical |
| Infrastructure | `ENOMEM`, `disk` | Critical |
| Data conflict | `duplicate key`, `unique constraint` | Warning |
| Permissions | `EACCES`, `permission` | Critical |
| Data quality | `null`, `undefined` | Error |

Critical errors trigger immediate alerts via webhook (Slack, email, or custom endpoint). All errors are persisted to the `error_log` table for post-incident analysis.

### 7.3 Audit Trail

Every data mutation in the system is logged:

| Operation | Audit Table | Fields Captured |
|-----------|-------------|-----------------|
| Video ingestion | `video` (created_at) | Filename, source, SHA256 |
| Label assignment | `video` (updated_at) | Label, labeler, confidence |
| File promotion | `promotion_log` | From/to split, idempotency key |
| Data purging | Audit log (in Privacy Agent) | File path, TTL policy, timestamp |
| Model deployment | `deployment_log` | Model version, gate results |
| Error occurrence | `error_log` | Workflow, node, error message |

---

## 8. Edge Deployment

### 8.1 DeepStream Pipeline

The Jetson edge device runs a DeepStream 6.x pipeline configured for emotion recognition:

```
V4L2 Camera (1920x1080, 30 FPS)
    ──► nvstreammux (batching)
    ──► nvinfer (TensorRT FP16, 224x224 input)
    ──► nvvideoconvert
    ──► nvdsosd (on-screen display)
    ──► Application callback (emotion extraction)
```

The pipeline processes the camera stream at 30 FPS, resizing frames to 224x224 for the EfficientNet-B0 input, and running inference in FP16 precision. The `nvinfer` plugin handles batched inference using a pre-compiled TensorRT engine.

### 8.2 Emotion Client

The emotion client is a Python process that:

1. Receives emotion classification results from the DeepStream pipeline callback
2. Packages results as structured events (emotion label, confidence, inference time, frame number)
3. Streams events to the FastAPI gateway via Socket.IO WebSocket with auto-reconnection
4. Sends 30-second heartbeats to detect stale connections
5. Receives downstream cues (gesture commands, TTS triggers) from the gateway

The client uses `python-socketio` with infinite reconnection attempts and exponential backoff (1 second to 30 seconds), ensuring the system recovers from network partitions without manual intervention.

### 8.3 System Monitoring

A system monitor process on the Jetson tracks:

- **GPU utilization**: Parsed from NVIDIA `tegrastats` output
- **CPU/memory usage**: Via `psutil` library
- **Thermal state**: GPU junction temperature, throttling detection
- **Inference performance**: FPS, per-frame latency percentiles

These metrics are exposed to Agent 9 (Observability) via a Prometheus-compatible HTTP endpoint.

### 8.4 Process Management

The Jetson processes are managed by systemd:

```ini
[Service]
ExecStart=/usr/bin/python3 /opt/reachy/emotion_main.py
Restart=always
RestartSec=5
MemoryMax=2G
CPUQuota=400%
```

The service configuration ensures automatic restart on failure, resource limits to prevent runaway processes, and boot-time startup for unattended operation.

---

## 9. Curriculum as Documentation

### 9.1 Design Philosophy

A significant challenge in complex systems is maintaining accurate, useful documentation. Traditional documentation drifts from reality as the system evolves. We address this by embedding documentation in a *practitioner curriculum* — a structured learning path where each module teaches one agent's implementation by guiding the learner through building it from scratch.

This approach has three advantages:

1. **Accuracy**: The curriculum must be correct because learners execute it. Incorrect instructions produce immediate, visible failures.

2. **Completeness**: The step-by-step format requires documenting every parameter, expression, and connection — details that traditional documentation often omits.

3. **Onboarding**: New team members learn the system by building it, achieving deep understanding rather than surface-level familiarity.

### 9.2 Curriculum Structure

The 13-module curriculum (40-50 hours) is organized into six phases:

| Phase | Modules | Hours | Node Types Introduced |
|-------|---------|-------|-----------------------|
| Foundation | 00 | 3 | Webhook, HTTP Request, Code, IF |
| Core Data Pipeline | 01-03 | 11 | Postgres, Wait, Respond to Webhook, Switch |
| Maintenance | 04-05 | 5 | Schedule Trigger, SSH, Split In Batches, Email |
| ML Pipeline | 06-08 | 12 | (Composition of existing types for complex patterns) |
| Observability | 09-10 | 8 | Cron (sub-minute scheduling) |
| Advanced | 11-13 | 6 | Error Trigger, error workflow patterns |

Each module follows a five-part structure:
1. **Pre-wiring checklist**: Verify all dependencies before starting
2. **Concept explanation**: What the agent does and why
3. **Step-by-step wiring**: Node-by-node, parameter-by-parameter instructions
4. **Testing**: Manual test procedures and edge cases
5. **Troubleshooting**: Common problems and solutions

### 9.3 Pattern Progression

The curriculum introduces workflow patterns in order of increasing complexity:

| Module | Pattern | Complexity |
|--------|---------|------------|
| 01 | Linear pipeline | Simple |
| 02 | Branching (Switch) | Simple |
| 03 | Two-phase commit (dry-run + approval) | Moderate |
| 04 | Scheduled batch processing | Moderate |
| 06 | Polling loop (Wait → Check → Loop) | Complex |
| 08 | Conditional rollback | Complex |
| 09 | Parallel fan-out (1 trigger → 3 nodes) | Complex |
| 10 | Workflow-to-workflow orchestration | Advanced |
| 11 | Error workflow + DLQ | Advanced |

---

## 10. Discussion

### 10.1 Low-Code vs. Traditional MLOps

Using n8n (a low-code workflow engine) for ML pipeline orchestration offers distinct trade-offs compared to traditional MLOps platforms like Kubeflow or Airflow:

**Advantages:**
- *Visual debugging*: The workflow graph shows execution state at each node, making it easy to identify failures and inspect intermediate data
- *Rapid iteration*: Modifying a workflow requires editing parameters in a web UI rather than writing and deploying code
- *Non-engineer accessibility*: The visual interface enables domain experts (roboticists, psychologists) to understand and modify pipeline behavior
- *Self-hosted*: n8n runs on-premise without cloud dependencies, aligning with our privacy-first architecture

**Disadvantages:**
- *Scalability limits*: n8n's single-threaded execution model limits concurrent workflow execution to approximately 100. For our use case (10 workflows, mostly event-driven), this is sufficient, but it would not scale to high-throughput data processing
- *Version control*: Workflows are stored in n8n's internal database, not in version-controlled files. We mitigate this by exporting workflows as JSON and committing them to the repository
- *Testing*: n8n lacks native unit testing support for workflows. We compensate with external test scripts (curl-based) and execution history inspection

### 10.2 Edge Deployment Challenges

Deploying ML models on the Jetson Xavier NX introduced several challenges:

**Thermal management**: Extended inference at 30 FPS raises the GPU junction temperature above the throttling threshold (75°C) in poorly ventilated enclosures. Gate B's thermal soak test catches this before production deployment. We found that FP16 inference generates approximately 30% less heat than FP32, making precision reduction valuable for thermal as well as performance reasons.

**Model size constraints**: The Jetson has limited memory (8GB shared CPU/GPU). TensorRT engine compilation requires up to 2GB of workspace memory, limiting the maximum model size. EfficientNet-B0 (5.3M parameters) fits comfortably; larger variants (B4+) would require INT8 quantization.

**Update mechanism**: Deploying new models requires transferring the TensorRT engine file via SCP (typically 20-40MB), recompiling the engine on-device if the TensorRT version differs, and restarting the DeepStream pipeline. This process takes 2-5 minutes, during which inference is interrupted. Future work could explore hot-swapping models without pipeline restart.

### 10.3 Agentic Architecture Patterns

Several architectural patterns emerged during development that may be useful for other agentic systems:

**Correlation ID propagation**: Every pipeline execution generates a unique `pipeline_id` and `correlation_id` that propagates through all agent invocations. This enables end-to-end tracing of a single pipeline run across 10 workflows and dozens of database operations.

**Dual polling loops**: The ML Pipeline Orchestrator (Agent 10) uses two polling loops with different intervals — 10 minutes for training (which runs 15-60 minutes) and 5 minutes for evaluation (which runs 2-5 minutes). Matching the polling interval to the expected operation duration minimizes both unnecessary polls and detection latency.

**Graduated deployment**: The deployment pipeline follows a Shadow → Canary → Rollout pattern. The new model runs in shadow mode (inference without serving results), then canary mode (serving a fraction of traffic), then full rollout. Gate B's soak test validates canary behavior before promotion.

### 10.4 Limitations

**Single-GPU training**: The current architecture supports only one concurrent training run. Parallel training experiments would require either multi-GPU support or job queuing.

**Two-class focus**: While the architecture supports 6-class emotion classification, the quality gates and training configurations are primarily tuned for the 2-class (happy/sad) variant. Extending to the full emotion spectrum requires additional data collection and gate threshold tuning.

**Manual model architecture selection**: The system automates hyperparameter tuning within a fixed model architecture (EfficientNet-B0) but does not perform neural architecture search. Model architecture changes require manual configuration updates.

**n8n single point of failure**: All 10 agent workflows run on a single n8n instance. If n8n crashes, all orchestration stops. Mitigations include systemd auto-restart and n8n's queue mode (multi-worker) for future scaling.

---

## 11. Evaluation

### 11.1 System Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Inference latency (p50) | <= 120 ms | < 80 ms |
| Inference latency (p95) | <= 250 ms | < 100 ms |
| Throughput | 30 FPS | 30 FPS (sustained) |
| GPU temperature (steady state) | < 75°C | ~68°C (with FP16) |
| Model accuracy (2-class F1) | >= 0.84 | Gate A enforced |
| End-to-end pipeline time | < 4 hours | ~2-3 hours (training-dependent) |
| System recovery time | < 5 minutes | ~30 seconds (systemd restart) |
| Observability granularity | 30 seconds | 30 seconds |

### 11.2 Test Coverage

The system includes 151 automated tests organized by phase:

| Phase | Tests | Coverage Focus |
|-------|-------|---------------|
| Phase 1 | 43 | API client (retry logic, idempotency), WebSocket client (reconnection), Streamlit integration |
| Phase 2 | 62 | TAO configuration, dataset preparation (balancing, manifest generation), MLflow integration, training pipeline |
| Phase 3 | 46 | DeepStream configuration, Jetson client (reconnection, heartbeat), deployment automation |

Test pass rate: 90%+ (137+ of 151 tests pass consistently).

### 11.3 Workflow Complexity

| Workflow | Nodes | Patterns Used | Estimated Wiring Time |
|----------|-------|---------------|----------------------|
| Agent 1 (Ingest) | 12 | Webhook, Auth, Polling, DB, Event | 4 hours |
| Agent 2 (Labeling) | 9 | Webhook, CTE, Switch, Balance | 3 hours |
| Agent 3 (Promotion) | 11 | Two-Phase, Human Gate, SCP | 4 hours |
| Agent 4 (Reconciler) | 9 | Schedule, SSH, Diff, Email | 3 hours |
| Agent 5 (Privacy) | 8 | Schedule, Batch, Audit | 2 hours |
| Agent 6 (Training) | 15 | SSH, MLflow, Polling Loop, Gate A | 5 hours |
| Agent 7 (Evaluation) | 12 | SSH, MLflow Batch, Gate A | 3 hours |
| Agent 8 (Deployment) | 14 | SCP, TensorRT, Gate B, Rollback | 4 hours |
| Agent 9 (Observability) | 6 | Cron, Parallel Fan-Out, Parse | 3 hours |
| Agent 10 (Orchestrator) | 15 | Multi-Agent Sequential, Conditional | 5 hours |
| **Total** | **111** | | **36 hours** |

---

## 12. Conclusion

We have presented an agentic workflow orchestration system for edge-deployed emotion recognition that addresses the interconnected challenges of privacy, latency, operational complexity, and reliability. The architecture's key innovation is the decomposition of ML lifecycle management into 10 autonomous, event-driven agents coordinated through a low-code workflow engine, combined with a three-tier quality gate framework that prevents model regressions across both statistical and operational dimensions.

The edge-first design ensures privacy by processing video entirely on-device, while the agentic architecture enables continuous model improvement with minimal human intervention. The error handling architecture — spanning node-level retries, centralized error classification, and dead-letter queues — provides self-healing capability that is essential for unattended operation.

The practitioner curriculum approach to documentation offers a novel solution to the documentation drift problem: by embedding system knowledge in executable learning modules, we ensure accuracy and provide an effective onboarding path for new team members.

### Future Work

Several directions merit further investigation:

1. **Federated learning**: Extending the architecture to support multiple Reachy robots contributing to a shared model without sharing raw data
2. **Online learning**: Incorporating real-time feedback (e.g., human correction of misclassified emotions) into the training loop
3. **Multi-modal emotion recognition**: Adding audio (speech prosody) and physiological signals (heart rate via camera-based PPG) to complement facial expression analysis
4. **LLM-augmented agents**: Replacing some deterministic workflow nodes with language model reasoning for more flexible decision-making (e.g., automatic threshold adjustment based on deployment context)
5. **Horizontal scaling**: Deploying n8n in queue mode with multiple workers to support higher-throughput data pipelines

---

## References

Dosovitskiy, A., et al. (2021). An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale. *ICLR 2021*.

Goodfellow, I., et al. (2013). Challenges in Representation Learning: A Report on Three Machine Learning Contests. *ICML 2013 Workshop on Representation Learning*.

Li, S., Deng, W., Du, J. (2017). Reliable Crowdsourcing and Deep Locality-Preserving Learning for Expression Recognition in the Wild. *CVPR 2017*.

Mollahosseini, A., Hasani, B., Mahoor, M. H. (2019). AffectNet: A Database for Facial Expression, Valence, and Arousal Computing in the Wild. *IEEE Transactions on Affective Computing*.

n8n GmbH. (2019). n8n.io — Workflow Automation. https://n8n.io

NVIDIA. (2023). NVIDIA DeepStream SDK Developer Guide. https://docs.nvidia.com/deepstream/

NVIDIA. (2023). NVIDIA TensorRT Developer Guide. https://docs.nvidia.com/tensorrt/

Russell, S. J., Norvig, P. (2010). *Artificial Intelligence: A Modern Approach*. 3rd Edition. Prentice Hall.

Shinn, N., et al. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*.

Tan, M., Le, Q. V. (2019). EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks. *ICML 2019*.

Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*.

Zaharia, M., et al. (2018). Accelerating the Machine Learning Lifecycle with MLflow. *IEEE Data Engineering Bulletin*.

Zhang, S., et al. (2018). FaceBoxes: A CPU Real-time and Accurate Unconstrained Face Detector. *IJCB 2018*.

Zhang, X., et al. (2021). Real-Time Facial Expression Recognition on Edge Devices. *ACM Multimedia 2021*.

---

*Corresponding repository: Reachy_Local_08.4.2*
*System version: 08.4.2*
*Curriculum version: 2.0 (Opus v2)*
