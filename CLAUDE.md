# CLAUDE.md — Reachy_Local_08.4.2

> **Purpose**: Guide Claude Code (Desktop) when analyzing and working with this codebase.  
> **Project**: Reachy_Local_08.4.2 — Local-first emotion recognition for the Reachy Mini robot.  
> **Last Updated**: 2026-01-31

---

## Project Overview

Reachy_Local_08.4.2 is a **privacy-first, LAN-contained pipeline** for real-time emotion recognition on the Reachy Mini robot. The system uses:

- **EfficientNet-B0** — HSEmotion backbone (`enet_b0_8_best_vgaf`) pre-trained on VGGFace2 + AffectNet, fine-tuned for binary emotion classification (`happy` vs `sad`)
- **DeepStream + TensorRT** — Edge inference on Jetson Xavier NX
- **FastAPI + Nginx** — API gateway and media serving
- **LM Studio** — On-premise LLM (Llama-3.1-8B-Instruct) for empathetic dialogue
- **PostgreSQL** — Metadata storage (no raw video in DB)
- **n8n** — Agentic AI orchestration (10 cooperating agents)
- **MLflow** — Experiment tracking and model lineage

### Primary Objective
Emotion classification from short synthetic videos (2-class: `happy`, `sad`) using EfficientNet-B0 with human-in-the-loop labeling and dataset curation.

### Non-Goals
- Audio emotion recognition
- Cloud dependencies
- Linguistic or conversational emotion synthesis

---

## Project Phases

### Phase 1: Offline ML Classification System
Foundation infrastructure: web app, EfficientNet-B0 training pipeline, FastAPI gateway, MLflow tracking, Gate A validation.

**Key Components:**
- `apps/web/` — Streamlit UI for video upload/labeling
- `trainer/fer_finetune/` — Training pipeline with transfer learning
- `apps/api/` — FastAPI gateway

### Phase 2: Emotional Intelligence Layer
Response generation with degree-modulated behavior:

| Concept | Description | Key File |
|---------|-------------|----------|
| **Degree** | Confidence scores (0–1) for emotion intensity | `trainer/fer_finetune/evaluate.py` |
| **PPE** | 8-class Ekman taxonomy with emotion-to-response mapping | `apps/reachy/gestures/emotion_gesture_map.py` |
| **EQ** | Calibration metrics (ECE, Brier, MCE) for reliability | `trainer/fer_finetune/evaluate.py` |
| **Gesture Modulation** | 5-tier confidence-based expressiveness | `apps/reachy/gestures/gesture_modulator.py` |
| **LLM Prompt Tailoring** | Emotion-conditioned prompts with confidence guidance | `apps/llm/prompts/emotion_prompts.py` |

### Phase 3: Edge Deployment & Real-Time Inference
Jetson deployment: TensorRT conversion, DeepStream pipeline, real-time inference, Gates B & C validation, staged rollout.

**Key Components:**
- `jetson/` — DeepStream configs and WebSocket client
- `apps/pipeline/emotion_llm_gesture.py` — Full pipeline orchestration

---

## Architecture (3-Node Local Lab)

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Ubuntu 1          │    │   Ubuntu 2          │    │   Jetson Xavier NX  │
│   10.0.4.130        │    │   10.0.4.140        │    │   10.0.4.150        │
│                     │    │                     │    │                     │
│ • Media Mover :8081 │◄───│ • FastAPI :8000     │◄───│ • DeepStream        │
│ • PostgreSQL :5432  │    │ • Streamlit :8501   │    │ • TensorRT Engine   │
│ • LM Studio :1234   │    │ • Nginx :443        │    │ • WebSocket Client  │
│ • MLflow :5000      │    │                     │    │                     │
│ • TAO Training      │    │                     │    │                     │
│ • n8n :5678         │    │                     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### Data Flow
1. **Jetson** detects emotion → sends JSON event to Ubuntu 2 (no raw video egress)
2. **Ubuntu 2** updates DB, requests LLM inference from Ubuntu 1
3. **Ubuntu 1** returns tone-matched dialogue text
4. **User** curates videos via web UI → promotes `temp → dataset_all → train/test`
5. **Training** orchestrator triggers TAO fine-tuning when thresholds met
6. **Deployment** agent pushes validated `.engine` to Jetson

---

## Repository Structure

```
reachy_08.4.2/
├── CLAUDE.md                    # This file — Claude Code guidance
├── AGENTS.md                    # Agent roles, contracts, orchestration policy
├── README.md                    # Quick start and overview
├── pyproject.toml               # Python dependencies (hatch build system)
│
├── apps/                        # Main application code
│   ├── api/                     # FastAPI backend
│   │   ├── app/                 # Core application
│   │   │   ├── config.py        # Centralized configuration
│   │   │   ├── main.py          # FastAPI app factory
│   │   │   ├── routers/         # API route handlers
│   │   │   ├── schemas/         # Pydantic models
│   │   │   ├── services/        # Business logic
│   │   │   ├── repositories/    # Data access layer
│   │   │   └── db/              # Database models and migrations
│   │   └── .env.template        # Environment variable template
│   ├── gateway/                 # Gateway-specific code
│   └── web/                     # Streamlit web UI
│
├── trainer/                     # ML training pipeline
│   ├── train_emotionnet.py      # Training orchestrator (TAO 4.x)
│   ├── export_to_trt.py         # TensorRT export (TAO 5.3)
│   ├── prepare_dataset.py       # Dataset preparation
│   ├── mlflow_tracker.py        # MLflow integration
│   ├── validation.py            # Model validation
│   └── tao/                     # TAO configuration
│       ├── specs/               # Training specs (YAML)
│       │   ├── emotionnet_2cls.yaml   # 2-class config
│       │   └── emotionnet_6cls.yaml   # 6-class config
│       ├── docker-compose-tao.yml
│       └── setup_tao_env.sh
│
├── jetson/                      # Edge deployment
│   ├── deepstream/              # DeepStream pipeline configs
│   │   ├── emotion_pipeline.txt # Main pipeline config
│   │   ├── emotion_inference.txt
│   │   └── emotion_labels.txt
│   ├── emotion_client.py        # WebSocket client
│   ├── emotion_main.py          # Main entry point
│   ├── deepstream_wrapper.py    # DeepStream Python wrapper
│   ├── deploy.sh                # Deployment script
│   └── systemd/                 # Service files
│
├── n8n/                         # Agentic AI orchestration
│   ├── workflows/               # 9 agent workflow JSONs
│   │   ├── 01_ingest_agent.json
│   │   ├── 02_labeling_agent.json
│   │   ├── 03_promotion_agent.json
│   │   ├── 04_reconciler_agent.json
│   │   ├── 05_training_orchestrator.json
│   │   ├── 06_evaluation_agent.json
│   │   ├── 07_deployment_agent.json
│   │   ├── 08_privacy_agent.json
│   │   └── 09_observability_agent.json
│   └── README.md                # n8n deployment guide
│
├── memory-bank/                 # Project knowledge base
│   ├── index.md                 # Entry points to context
│   ├── requirements.md          # Comprehensive requirements (v0.08.4.2)
│   ├── decisions/               # Architecture Decision Records (ADRs)
│   └── templates/               # Memory note templates
│
├── docs/                        # Documentation
│   ├── endpoints.md             # API endpoint reference
│   └── gpt/                     # AI-generated implementation guides
│
├── tests/                       # Test suite (151+ tests)
│   ├── apps/                    # App-specific tests
│   └── test_*.py                # Integration and unit tests
│
├── shared/                      # Shared contracts and utilities
│   └── contracts/
│
├── src/                         # Legacy code (being migrated to apps/)
├── scripts/                     # Utility scripts
├── alembic/                     # Database migrations
└── systemd/                     # System service files
```

---

## Key Files to Read First

When starting work on this project, read these files in order:

1. **`memory-bank/requirements.md`** — Comprehensive requirements, architecture, API contracts
2. **`AGENTS.md`** — Agent roles, approval rules, orchestration policy
3. **`docs/endpoints.md`** — API endpoint reference
4. **`trainer/tao/specs/emotionnet_2cls.yaml`** — Training configuration
5. **`apps/api/app/config.py`** — Centralized configuration

---

## Technology Stack

### Core Dependencies
| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ (3.12 recommended) | Primary language |
| FastAPI | 0.110+ | API framework |
| Pydantic | 2.x | Data validation |
| SQLAlchemy | 2.0+ | ORM |
| PostgreSQL | 16+ | Metadata database |
| Uvicorn | 0.29+ | ASGI server |
| Nginx | 1.22+ | Reverse proxy |

### ML/AI Stack
| Component | Version | Purpose |
|-----------|---------|---------|
| TAO Toolkit | 4.x (train), 5.3 (export) | Model fine-tuning |
| TensorRT | 8.6+ | Inference optimization |
| DeepStream | 6.x | Video analytics pipeline |
| MLflow | 2.14+ | Experiment tracking |
| JetPack | 5.x | Jetson SDK |

### Orchestration
| Component | Version | Purpose |
|-----------|---------|---------|
| n8n | Latest | Workflow automation |
| Docker | 20.10+ | Containerization |

---

## EfficientNet-B0 Model Details

### Architecture
- **Base**: EfficientNet-B0 (HSEmotion `enet_b0_8_best_vgaf`)
- **Pre-training**: VGGFace2 + AffectNet (emotion-optimized)
- **Input**: 224×224×3 RGB images
- **Output**: Emotion class probabilities + optional valence/arousal
- **Project Classes**: 2 (happy, sad) — fine-tuned for binary classification
- **Expandable to**: 8-class Ekman taxonomy (Phase 2 PPE)

### Training Configuration (`efficientnet_emotion_2cls.yaml`)
```yaml
model:
  arch: "efficientnet_b0"
  input_shape: [224, 224, 3]
  num_classes: 2
  pretrained_weights: "hsemotion"  # enet_b0_8_best_vgaf
  freeze_blocks: ["conv_stem", "blocks.0", "blocks.1"]
  dropout_rate: 0.3

training:
  batch_size: 32
  num_epochs: 50
  optimizer: "adamw"
  learning_rate: 0.001
  lr_schedule:
    type: "cosine"
    warmup_epochs: 5
  early_stopping:
    patience: 10
    metric: "val_f1_macro"
  
  # Two-phase training
  freeze_epochs: 5      # Train head only
  unfreeze_layers: ["blocks.5", "blocks.6", "classifier"]
```

### Model Selection Rationale
| Metric | EfficientNet-B0 | ResNet-50 (prior) |
|--------|-----------------|-------------------|
| Inference Latency | ~40 ms | ~120 ms |
| GPU Memory | ~0.8 GB | ~2.4 GB |
| Thermal Headroom | 3× margin | Near limit |

EfficientNet-B0 provides **3× latency and memory headroom** on Jetson Xavier NX while maintaining accuracy through HSEmotion pre-training.

### Quality Gates
| Gate | Metric | Threshold |
|------|--------|-----------|
| Gate A (Offline) | Macro F1 | ≥ 0.84 |
| Gate A | Per-class F1 | ≥ 0.75 |
| Gate A | Balanced Accuracy | ≥ 0.85 |
| Gate B (Shadow) | Latency p50 | ≤ 120 ms |
| Gate B | Latency p95 | ≤ 250 ms |
| Gate B | GPU Memory | ≤ 2.5 GB |
| Gate B | Macro F1 | ≥ 0.80 |

---

## Common Commands

### Development
```bash
# Install dependencies
pip install -e ".[dev,web,trainer]"

# Run API server (Ubuntu 2)
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run Streamlit UI
streamlit run apps/web/landing_page.py

# Run tests
pytest tests/ -v

# Lint and format
ruff check . --fix
ruff format .
```

### Training Pipeline
```bash
# Prepare dataset
python trainer/prepare_dataset.py --dataset /videos/dataset_all --output /videos/train

# Train model (TAO 4.x container)
python trainer/train_emotionnet.py \
  --config trainer/tao/specs/emotionnet_2cls.yaml \
  --dataset /videos \
  --output /workspace/experiments \
  --mlflow-experiment emotionnet

# Export to TensorRT (TAO 5.3 container)
python trainer/export_to_trt.py \
  --model /workspace/experiments/emotionnet_2cls \
  --output /workspace/engines \
  --name emotionnet \
  --precision fp16
```

### Deployment (Jetson)
```bash
# Deploy to Jetson
./jetson/deploy.sh

# Check service status
sudo systemctl status reachy-emotion

# View logs
sudo journalctl -u reachy-emotion -f
```

---

## API Endpoints Quick Reference

### Gateway (Ubuntu 2 — Port 8000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/events/emotion` | Receive emotion events from Jetson |
| GET | `/api/videos/list` | List videos by split |
| PATCH | `/api/videos/{id}/label` | Update video label |
| POST | `/api/v1/promote/stage` | Promote temp → dataset_all |
| POST | `/api/v1/promote/sample` | Sample train/test splits |
| GET | `/health` | Liveness probe |
| GET | `/metrics` | Prometheus metrics |
| WS | `/ws/cues/{device_id}` | Real-time cues to Jetson |

### Media Mover (Ubuntu 1 — Port 8081)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/media/promote` | Atomic file move |
| POST | `/api/media/ingest` | Register new video |
| POST | `/api/manifest/rebuild` | Rebuild manifests |
| GET | `/api/media/healthz` | Health check |

---

## Database Schema (Key Tables)

```sql
-- Video metadata
CREATE TABLE video (
  video_id       UUID PRIMARY KEY,
  file_path      TEXT NOT NULL,
  split          TEXT CHECK (split IN ('temp','dataset_all','train','test')),
  label          TEXT,
  sha256         TEXT,
  size_bytes     BIGINT,
  created_at     TIMESTAMPTZ DEFAULT now()
);

-- MLflow run linkage
CREATE TABLE run_link (
  mlflow_run_id  TEXT PRIMARY KEY,
  dataset_hash   TEXT NOT NULL,
  snapshot_ref   TEXT,
  created_at     TIMESTAMPTZ DEFAULT now()
);
```

**Connection**: `postgresql://reachy_dev:***@10.0.4.130:5432/reachy_emotion`

---

## Nine Cooperating Agents (n8n)

| # | Agent | Purpose |
|---|-------|---------|
| 1 | Ingest | Receive videos, compute SHA256, extract metadata |
| 2 | Labeling | Human-in-the-loop classification |
| 3 | Promotion | Controlled movement between splits |
| 4 | Reconciler | Filesystem ↔ DB consistency |
| 5 | Training | TAO fine-tuning orchestration |
| 6 | Evaluation | Test set validation |
| 7 | Deployment | Shadow → Canary → Rollout |
| 8 | Privacy | TTL enforcement, GDPR compliance |
| 9 | Observability | Metrics aggregation, SLA monitoring |

---

## Storage Layout (Ubuntu 1)

```
/media/project_data/reachy_emotion/videos/
├── temp/           # Incoming videos (TTL: 7-14 days)
├── dataset_all/    # Accepted labeled corpus
├── train/          # Training split (per run)
├── test/           # Test split (per run, unlabeled)
├── thumbs/         # Generated thumbnails
└── manifests/      # JSONL manifests
```

---

## Privacy & Security Principles

1. **Local-first**: No raw video leaves the local network
2. **Edge inference**: Jetson sends only JSON events (emotion, confidence, timestamp)
3. **Minimal PII**: Only faces retained; full purge support mandatory
4. **mTLS/JWT**: Service-to-service authentication
5. **Secrets via Vault**: No hardcoded credentials

---

## Testing Strategy

- **Unit tests**: `pytest tests/` (151+ tests, 90%+ pass rate)
- **Integration tests**: `test_integration_full.py`, `test_e2e_complete.py`
- **API contract tests**: `test_api_client.py`, `test_v1_endpoints.py`
- **ML pipeline tests**: `test_training_pipeline.py`, `test_tao_setup.py`
- **Edge tests**: `test_jetson_client.py`, `test_deepstream_config.py`

Run all tests:
```bash
pytest tests/ -v --tb=short
```

---

## Coding Conventions

- **Style**: Black, isort, ruff
- **Type hints**: Required (pyright strict mode)
- **Docstrings**: Google style
- **Commits**: Conventional commits recommended
- **Branches**: `feature/*`, `fix/*`, `release/*`

---

## Environment Variables

Key variables (see `apps/api/.env.template` for full list):

```bash
# Database
DB_HOST=10.0.4.130
DB_PORT=5432
DB_NAME=reachy_emotion
DB_USER=reachy_dev

# Services
MEDIA_MOVER_BASE_URL=http://10.0.4.130:8081/api
GATEWAY_BASE_URL=http://10.0.4.140:8000
MLFLOW_URL=http://10.0.4.130:5000

# LLM
LLM_STUDIO_BASE_URL=http://10.0.4.130:1234

# Jetson
GATEWAY_URL=http://10.0.4.140:8000
DEVICE_ID=reachy-mini-01
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| High emotion latency | Check GPU throttling, `inference_ms`, queue depth |
| No LLM replies | Verify LM Studio at `http://10.0.4.130:1234` |
| Promotion fails 409 | Ensure unique `Idempotency-Key`, target path exists |
| Training timeout | Check TAO container logs, GPU memory |
| DeepStream crash | Verify engine file exists, check `nvinfer` config |

---

## References

- **NVIDIA TAO Toolkit**: https://developer.nvidia.com/tao-toolkit
- **DeepStream SDK**: https://developer.nvidia.com/deepstream-sdk
- **EmotionNet Model Card**: See user-provided context in this session
- **n8n Documentation**: https://docs.n8n.io
- **FastAPI**: https://fastapi.tiangolo.com

---

## Contact

**Maintainer**: Russell Bray (rustybee255@gmail.com)  
**Project Owner**: Russell Bray (Russ)

---

*This file should be updated when significant architectural changes occur.*
