# Comprehensive Overview: Project Reachy Emotion Recognition System

**A Three-Phase Approach to Privacy-Preserving Emotion Classification for Human-Robot Interaction**

---

## Abstract

This paper presents a comprehensive overview of Project Reachy, a multi-phase emotion recognition system designed for the Reachy Mini companion robot. The project implements a local-first, privacy-preserving pipeline that spans synthetic video generation, machine learning (ML) model fine-tuning, edge deployment, and empathetic human-robot interaction powered by large language models (LLMs). Organized into three distinct phases—(1) offline ML classification with a web application, (2) advanced emotional metrics including degree of emotion and Emotional Intelligence (EQ), and (3) robotics integration with gesture-based interaction—the system demonstrates a complete MLOps lifecycle from data curation to real-time inference. This paper describes the system architecture, data flow, agent-based orchestration, and quality gates that ensure reliable deployment of emotion classifiers to edge devices.

**Keywords:** emotion recognition, transfer learning, EfficientNet-B0, HSEmotion, human-robot interaction, MLOps, edge computing, privacy-preserving AI

---

## 1. Introduction

### 1.1 Motivation

Human-robot interaction (HRI) systems increasingly require the ability to perceive and respond to human emotional states. Emotion recognition enables robots to provide contextually appropriate responses, fostering more natural and empathetic interactions (Picard, 1997). However, deploying such systems raises significant privacy concerns, as continuous video capture of human faces constitutes sensitive biometric data.

Project Reachy addresses these challenges through a local-first architecture where raw video never leaves the edge device. The system processes emotion detection on-device using optimized neural networks, transmitting only derived metadata (emotion labels, confidence scores, timestamps) to upstream services. This approach aligns with privacy-by-design principles while enabling sophisticated emotional intelligence capabilities.

### 1.2 Project Objectives

The primary objectives of Project Reachy are:

1. **Data Generation & Curation**: Develop a web application for generating and classifying synthetic emotion videos using AI-powered video generation APIs.

2. **Model Fine-Tuning**: Fine-tune an EfficientNet-B0 classifier (HSEmotion `enet_b0_8_best_vgaf`) pre-trained on VGGFace2 + AffectNet for 3-class emotion classification (happy, sad, neutral).

3. **Edge Deployment**: Deploy optimized TensorRT models to the Reachy Mini robot's NVIDIA Jetson Xavier NX for real-time inference.

4. **Empathetic Interaction**: Integrate LLM-powered responses with physical robot gestures to create emotionally intelligent interactions.

5. **Continuous Improvement**: Establish a feedback loop where user-classified videos improve future model iterations.

### 1.3 Document Organization

This paper is organized as follows: Section 2 describes the three-phase development approach. Section 3 details the system architecture. Section 4 covers the MLOps pipeline. Section 5 discusses the agent-based orchestration system. Section 6 presents quality gates and deployment strategies. Section 7 concludes with future directions.

---

## 2. Three-Phase Development Approach

Project Reachy follows a phased development methodology, with each phase building upon the capabilities established in the previous phase.

### 2.1 Phase 1: Offline ML Classification (Capstone)

Phase 1 establishes the foundational infrastructure for emotion classification:

- **Web Application**: A Streamlit-based interface (`apps/web/landing_page.py`) enables users to upload existing videos or generate synthetic emotion videos using the Luma AI API.

- **Video Generation**: Integration with Luma AI's Ray-2 model generates 5-second emotion videos at 720p resolution based on text prompts (e.g., "a happy girl eating lunch").

- **Data Curation Pipeline**: Videos flow through a structured directory hierarchy (`/videos/temp/` → `/videos/dataset_all/` → `/videos/train/` and `/videos/test/`) with human-in-the-loop labeling.

- **3-Class Classification**: The initial model targets three emotion classes—happy, sad, and neutral—using an EfficientNet-B0 backbone (HSEmotion `enet_b0_8_best_vgaf`) fine-tuned with transfer learning. This architecture provides 3× latency improvement over ResNet-50 baselines.

- **Offline Validation**: Models must pass Gate A quality thresholds (macro F1 ≥ 0.84, balanced accuracy ≥ 0.85) before proceeding to deployment.

### 2.2 Phase 2: Degree/PPE/EQ Extensions

Phase 2 extends the classification system with nuanced emotional metrics:

- **Degree of Emotion**: Rather than discrete labels, the system outputs continuous confidence scores representing emotion intensity on a spectrum.

- **Primary Principles of Emotion (PPE)**: The architecture supports expansion to eight emotion classes (neutral, happy, sad, anger, fear, disgust, surprise, contempt) aligned with established emotion taxonomies.

- **Emotional Intelligence (EQ) Metrics**: Calibration metrics including Expected Calibration Error (ECE ≤ 0.08) and Brier score (≤ 0.16) ensure the model's confidence scores are well-calibrated and reliable for downstream decision-making.

- **Enhanced Evaluation**: The evaluation pipeline computes per-class F1 scores with minimum floors (≥ 0.75) to prevent class imbalance issues.

### 2.3 Phase 3: Robotics Integration

Phase 3 completes the system with real-time robotics capabilities:

- **DeepStream Pipeline**: NVIDIA DeepStream SDK 6.x processes camera streams at 30 FPS on the Jetson Xavier NX, running TensorRT-optimized inference.

- **Gesture System**: A comprehensive gesture library maps detected emotions to physical robot movements (wave, nod, thumbs up, empathy gestures) via the Reachy SDK.

- **LLM Integration**: LM Studio running Llama-3.1-8B-Instruct generates context-aware, empathetic responses based on detected emotions.

- **Real-Time Pipeline**: The `EmotionLLMGesturePipeline` orchestrates the flow from emotion detection → LLM response generation → gesture keyword parsing → robot actuation.

---

## 3. System Architecture

### 3.1 Network Topology

Project Reachy operates on a three-node local area network:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Project Reachy Network Topology                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Ubuntu 1 (10.0.4.130) — Model Host                                │
│  ├── LM Studio (Llama-3.1-8B) ................ :1234               │
│  ├── Media Mover API ......................... :8083               │
│  ├── PostgreSQL 16 ........................... :5432               │
│  ├── n8n Orchestration ....................... :5678               │
│  ├── MLflow Tracking ......................... :5000               │
│  └── Nginx Static Media ...................... :80/:443            │
│                                                                     │
│  Ubuntu 2 (10.0.4.140) — App Gateway                               │
│  ├── FastAPI Gateway ......................... :8000               │
│  ├── Streamlit Web UI ........................ :8501               │
│  └── Nginx Reverse Proxy ..................... :443                │
│                                                                     │
│  Jetson Xavier NX (10.0.4.150) — Edge Runtime                      │
│  ├── DeepStream 6.x + TensorRT                                     │
│  ├── Emotion Classification Engine                                 │
│  └── WebSocket Client → Ubuntu 2                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

**Ubuntu 1 — Model Host (Heavy Compute)**

Ubuntu 1 serves as the computational backbone:

- Hosts the LLM inference server (LM Studio) for generating empathetic responses
- Runs the Media Mover API for filesystem operations (video promotion, thumbnail generation, manifest rebuilding)
- Maintains the PostgreSQL database storing video metadata, labels, and promotion logs
- Executes PyTorch training jobs for model fine-tuning
- Operates n8n for workflow orchestration across all nine agents

**Ubuntu 2 — App Gateway (Ingress/Orchestrator)**

Ubuntu 2 manages external communication:

- Receives emotion events from Jetson via JSON over HTTPS
- Routes LLM inference requests to Ubuntu 1
- Serves the Streamlit web interface for video generation and labeling
- Exposes WebSocket endpoints for real-time cue delivery to Jetson
- Proxies media requests to Ubuntu 1's Nginx server

**Jetson Xavier NX — Edge Runtime**

The Jetson handles real-time inference:

- Captures 30 FPS camera stream
- Runs DeepStream pipeline with TensorRT-optimized emotion classifier
- Emits JSON emotion events (never raw video) to Ubuntu 2
- Receives gesture/TTS cues via WebSocket
- Controls Reachy Mini robot via the Reachy SDK

### 3.3 Design Principles

The architecture adheres to three core principles:

1. **Local-First Processing**: All raw video processing occurs on-device. No video frames traverse the network; only derived metadata is transmitted.

2. **Separation of Concerns**: Each node has distinct responsibilities—edge inference, API orchestration, and heavy computation are cleanly separated.

3. **Privacy by Design**: The system enforces strict data governance with configurable retention policies, GDPR-compliant deletion workflows, and audit logging.

---

## 4. MLOps Pipeline

### 4.1 Data Flow Overview

The end-to-end data flow follows this sequence:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Project Reachy Data Flow                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. VIDEO GENERATION/UPLOAD                                        │
│     User uploads video OR generates via Luma AI                    │
│     ↓                                                               │
│  2. INGEST (Agent 1)                                               │
│     Compute SHA256, extract metadata, generate thumbnail           │
│     Store in /videos/temp/, insert DB record                       │
│     ↓                                                               │
│  3. LABELING (Agent 2)                                             │
│     User classifies emotion in web UI                              │
│     Update label in database                                       │
│     ↓                                                               │
│  4. PROMOTION (Agent 3)                                            │
│     Dry-run preview → Human approval → Atomic move                 │
│     temp/ → dataset_all/ (staging corpus)                          │
│     ↓                                                               │
│  5. SAMPLING (Training Orchestrator)                               │
│     Randomized selection: dataset_all/ → train/ + test/            │
│     Enforce 50/50 class balance, test set remains unlabeled        │
│     ↓                                                               │
│  6. TRAINING (Agent 5)                                             │
│     Fine-tune EfficientNet-B0 with frozen backbone → selective unfreeze │
│     Log to MLflow, validate Gate A                                 │
│     ↓                                                               │
│  7. EXPORT                                                         │
│     PyTorch → ONNX → TensorRT engine (FP16)                       │
│     ↓                                                               │
│  8. DEPLOYMENT (Agent 7)                                           │
│     Shadow → Canary (10%) → Full Rollout                          │
│     Validate Gate B (latency, GPU memory)                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Storage Architecture

The storage system uses a hybrid approach combining filesystem storage with database metadata:

**Filesystem Layout (Ubuntu 1)**:
```
/media/project_data/reachy_emotion/videos/
├── temp/           # Newly ingested, unclassified videos
├── dataset_all/    # Accepted, labeled videos (canonical corpus)
├── train/          # Per-run training subset (labeled)
├── test/           # Per-run test subset (unlabeled in DB)
├── thumbs/         # Generated thumbnails (JPG)
└── manifests/      # JSONL manifests per training run
```

**Database Schema (PostgreSQL)**:
- `video` table: Stores `video_id`, `file_path`, `split`, `label`, `duration_sec`, `fps`, `sha256`, `created_at`
- `training_run` table: Tracks run parameters, sampling strategy, train/test fractions
- `training_selection` table: Links videos to specific training runs

### 4.3 Model Architecture

The classification model uses an EfficientNet-B0 backbone with transfer learning:

- **Pre-trained Weights**: HSEmotion `enet_b0_8_best_vgaf` (VGGFace2 + AffectNet)
- **Source**: EmotiEffLib (`pip install emotiefflib`)
- **Input Size**: 224×224 RGB images
- **Output**: 3 classes (happy/sad/neutral) or 8 classes (multi-class expansion)
- **Performance**: ~40 ms inference latency (p50), ~0.8 GB GPU memory—providing 3× headroom vs. ResNet-50
- **Training Strategy**: Two-phase approach
  - Phase 1 (epochs 1-5): Frozen backbone, train classification head only
  - Phase 2 (epochs 6+): Selective unfreezing for domain adaptation

**Training Configuration Highlights**:
- Learning rate: 1e-4 with cosine annealing and 3-epoch warmup
- Regularization: Label smoothing (0.1), dropout (0.3), mixup augmentation
- Mixed precision: FP16 for faster training
- Early stopping: Patience of 10 epochs monitoring `val_f1_macro`

### 4.4 Experiment Tracking

MLflow tracks all training experiments with:

- **Parameters**: All hyperparameters from `TrainingConfig`
- **Metrics**: Accuracy, F1 (macro and per-class), balanced accuracy, ECE, Brier score
- **Artifacts**: Best model checkpoint, ONNX export, TensorRT engine, confusion matrices
- **Lineage**: `dataset_hash` linking model to exact training data, optional ZFS snapshot reference

---

## 5. Agent-Based Orchestration

### 5.1 Nine-Agent Architecture

Project Reachy employs nine cooperating agents orchestrated via n8n workflows:

| Agent | Purpose | Key Responsibility |
|-------|---------|-------------------|
| **1. Ingest** | Video registration | Hash computation, metadata extraction, thumbnail generation |
| **2. Labeling** | Classification management | User label updates, class balance enforcement |
| **3. Promotion** | Dataset curation | Atomic moves with dry-run, manifest rebuilding |
| **4. Reconciler** | Consistency auditing | Filesystem ↔ database drift detection |
| **5. Training** | Model fine-tuning | TAO/PyTorch training, MLflow logging, Gate A validation |
| **6. Evaluation** | Test validation | Confusion matrix, calibration metrics, Gate B validation |
| **7. Deployment** | Model rollout | Shadow → canary → rollout with approval gates |
| **8. Privacy** | Data retention | TTL enforcement, GDPR deletion, audit logging |
| **9. Observability** | System monitoring | Metrics aggregation, SLA breach alerting |

### 5.2 Event-Driven Communication

Agents communicate via webhook triggers and emit structured events:

- `ingest.completed`: New video registered with `video_id`, `sha256`, paths
- `label.completed`: Label updated with promotion action
- `promotion.completed`: Video moved to target split
- `training.completed`: Model trained with metrics and artifact paths
- `evaluation.completed`: Gate B decision with detailed metrics
- `deployment.completed`: Engine deployed to target stage
- `privacy.purged`: Videos purged with count and reason

### 5.3 Idempotency and Error Handling

All mutating operations enforce idempotency:

- **Idempotency Keys**: SHA256-based keys prevent duplicate operations
- **Correlation IDs**: Track requests across agent boundaries
- **Retry Policy**: Exponential backoff with jitter, max 5 attempts for transient errors
- **Dead Letter Queue**: Failed operations beyond retries require human review

---

## 6. Quality Gates and Deployment

### 6.1 Gate A — Offline Validation

Before any model leaves the training environment:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Macro F1 | ≥ 0.84 | Overall classification quality |
| Per-class F1 | ≥ 0.75 (floor) | Prevent class collapse |
| Balanced Accuracy | ≥ 0.85 | Handle class imbalance |
| ECE | ≤ 0.08 | Confidence calibration |
| Brier Score | ≤ 0.16 | Probabilistic accuracy |

### 6.2 Gate B — Robot Shadow Mode

On-device validation before user exposure:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Latency p50 | ≤ 120 ms | Responsive interaction |
| Latency p95 | ≤ 250 ms | Tail latency control |
| GPU Memory | ≤ 2.5 GB | Leave headroom for other tasks |
| Macro F1 | ≥ 0.80 | On-device accuracy |

### 6.3 Gate C — Limited User Rollout

Production validation with real users:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| End-to-end Latency | ≤ 300 ms | User-perceived responsiveness |
| Abstention Rate | ≤ 20% | Model confidence |
| User Complaints | < 1% of sessions | User satisfaction |

### 6.4 Staged Deployment

Deployment follows a progressive rollout:

1. **Shadow Mode**: Engine deployed to Jetson shadow slot, no traffic routing
2. **Canary (10%)**: Route 10% of traffic, monitor for 30 minutes
3. **Full Rollout**: Complete traffic switch after human approval

Rollback is automated if Gate B metrics degrade during any stage.

---

## 7. Phase 3: Real-Time Interaction Pipeline

### 7.1 Emotion-LLM-Gesture Pipeline

The `EmotionLLMGesturePipeline` class orchestrates the complete interaction loop:

```
┌─────────────────────────────────────────────────────────────────────┐
│               Emotion-LLM-Gesture Pipeline Flow                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Jetson Camera → DeepStream → TensorRT Inference                   │
│         │                                                           │
│         ↓                                                           │
│  EmotionEvent { emotion: "sad", confidence: 0.87, ... }            │
│         │                                                           │
│         ↓ (WebSocket)                                               │
│  Ubuntu 2 Gateway → EmotionLLMGesturePipeline                      │
│         │                                                           │
│         ↓                                                           │
│  LLM Client → LM Studio (Llama-3.1-8B)                             │
│         │                                                           │
│         ↓                                                           │
│  LLMResponse { text: "...", gesture_keywords: ["EMPATHY", "NOD"] } │
│         │                                                           │
│         ↓                                                           │
│  GestureController → Reachy SDK → Physical Robot                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Gesture Mapping

Emotions map to appropriate gesture types:

| Emotion | Default Gestures |
|---------|-----------------|
| Happy | CELEBRATE, EXCITED, THUMBS_UP, WAVE, NOD |
| Sad | EMPATHY, COMFORT, HUG, SAD_ACK, LISTEN |
| Neutral | NOD, LISTEN, WAVE, THINK |

The LLM can override defaults by embedding gesture keywords in responses (e.g., `[WAVE]`, `[HUG]`).

### 7.3 WebSocket Communication

The Jetson client (`emotion_client.py`) maintains a persistent WebSocket connection:

- **Outbound**: Emotion events streamed to gateway
- **Inbound**: Gesture and TTS cues received for robot actuation
- **Reliability**: Auto-reconnection with exponential backoff
- **Heartbeat**: 30-second keep-alive to detect connection loss

---

## 8. Security and Privacy

### 8.1 Data Protection

- **No Raw Video Egress**: DeepStream processes frames locally; only metadata crosses the network
- **Encryption**: TLS 1.3 for all network traffic; optional ZFS native encryption at rest
- **Token Rotation**: JWT tokens and API keys rotate every ≤90 days via HashiCorp Vault
- **Audit Trail**: All operations logged with correlation IDs to PostgreSQL audit tables

### 8.2 Access Control

- **mTLS/JWT**: Service-to-service authentication
- **Role-Based Access**: Least-privilege database roles (`reachy_dev` scoped to metadata schema)
- **Network Segmentation**: Firewall rules enforce LAN-only access; no Jetson↔Ubuntu 1 direct video streaming

### 8.3 Compliance

- **GDPR**: Right-to-be-forgotten supported via Privacy Agent purge workflows
- **Data Minimization**: Only essential metadata retained; configurable TTLs (default 7-14 days for temp/)
- **Consent**: User opt-out available for data collection

---

## 9. Conclusion and Future Directions

Project Reachy demonstrates a complete, privacy-preserving emotion recognition pipeline from data generation through real-time robotic interaction. The three-phase approach enables incremental capability development while maintaining production-quality standards through rigorous quality gates.

### 9.1 Key Contributions

1. **Local-First Architecture**: Proves feasibility of sophisticated emotion AI without cloud dependencies
2. **Agent-Based MLOps**: Nine cooperating agents provide auditable, idempotent operations
3. **Human-in-the-Loop**: User classifications directly improve model quality through continuous fine-tuning
4. **Integrated HRI**: Seamless pipeline from perception to empathetic robot response

### 9.2 Future Work

- **Multi-Modal Fusion**: Integrate audio emotion recognition alongside visual cues
- **Federated Learning**: Enable cross-device model improvement without centralizing data
- **Advanced Calibration**: Implement temperature scaling and focal loss for improved confidence estimates
- **Extended Emotion Taxonomy**: Expand to 8-class classification with valence/arousal dimensions

---

## References

Goodfellow, I., Bengio, Y., & Courville, A. (2016). *Deep learning*. MIT Press.

Li, S., & Deng, W. (2020). Deep facial expression recognition: A survey. *IEEE Transactions on Affective Computing*, 13(3), 1195-1215.

Savchenko, A. V. (2021). Facial expression and attributes recognition based on multi-task learning of lightweight neural networks. In *Proceedings of the IEEE International Symposium on Intelligent Systems and Informatics* (pp. 119-124). https://github.com/HSE-asavchenko/face-emotion-recognition

Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. In *Proceedings of the International Conference on Machine Learning* (pp. 6105-6114).

Mollahosseini, A., Hasani, B., & Mahoor, M. H. (2019). AffectNet: A database for facial expression, valence, and arousal computing in the wild. *IEEE Transactions on Affective Computing*, 10(1), 18-31.

NVIDIA Corporation. (2023). *DeepStream SDK developer guide* (Version 6.3). https://docs.nvidia.com/metropolis/deepstream/dev-guide/

Picard, R. W. (1997). *Affective computing*. MIT Press.

Russakovsky, O., Deng, J., Su, H., Krause, J., Satheesh, S., Ma, S., ... & Fei-Fei, L. (2015). ImageNet large scale visual recognition challenge. *International Journal of Computer Vision*, 115(3), 211-252.

---

**Document Information**

| Field | Value |
|-------|-------|
| Paper Number | 1 of 7 |
| Title | Comprehensive Overview: Project Reachy |
| Version | 1.1 |
| Date | January 31, 2026 |
| Author | Russell Bray |
| Project | Reachy_Local_08.4.2 |

---

*This paper is part of a seven-paper series documenting Project Reachy. Subsequent papers provide detailed phase reviews (Papers 2-4) and statistical analyses (Papers 5-7).*
