# Reachy_Local_08.4.2

Local-first, LAN-contained pipeline for real-time emotion recognition on the Reachy Mini robot, powered by an on-device EfficientNet-B0 classifier (TensorRT) and an on-prem LLM for empathetic dialogue. Synthetic video generation and human-in-the-loop curation feed a continuous fine-tuning loop.

- Target platform: `Reachy Mini (Jetson Xavier NX 16GB)`
- Primary language: `Python 3.12+`
- Core stack: DeepStream 6.x + TensorRT 8.6+ (Jetson), FastAPI + Nginx (Ubuntu 2), LM Studio (Ubuntu 1), PostgreSQL (metadata only)

## Recent Updates (2026-02)

- **Fine-tuning stack standardized on 3-class EfficientNet-B0 (HSEmotion)**
  - Training config: `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`
  - Pipeline target labels: `happy`, `sad`, `neutral`
- **Promotion and fine-tuning flow updated for frame-first runs**
  - Human labeling promotes clips directly `temp -> train/<emotion>` via gateway/media promote endpoints
  - At fine-tune time, each run extracts 10 random frames per source video into:
    - `train/happy/<epoch_id>`, `train/sad/<epoch_id>`, train/neutral/<epoch_id>
  - A consolidated run dataset is created at` train/<epoch_id>` and used for training/manifests
- **Web app promotion reliability hardened**
  - Landing page classification now aggressively resolves/registers UUID-backed `video_id` before promotion
  - Non-UUID fallback promotions are blocked to prevent false-success UI paths
- **n8n workflow alignment updates**
  - `ml-agentic-ai_v.2/02_labeling_agent.json` now enforces 3-class labels and neutral-aware class-balance response
  - `ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json` now uses 3-class dataset checks and 3-class dataset hash
- **Database schema source-of-truth clarified**
  - Active schema: SQLAlchemy models + Alembic migration at `apps/api/app/db/alembic/versions/202510280000_initial_schema.py`
  - Root-level `alembic/versions/*.sql` files are legacy/deprecated references

## 📊 Implementation Status

**Phases Completed**: 2 of 5 (40%)  

✅ **Phase 1**: Web UI & Foundation (In process)  
✅ **Phase 2**: ML Pipeline (In process)  
⏳ **Phase 3**: Edge Deployment (Pending)  
⏳ **Phase 4**: n8n Orchestration (Pending)  
⏳ **Phase 5**: Production Hardening (Pending)



## Quick Start

This repo is organized for a 3-node local lab:

- `Ubuntu 1` — Model Host (LM Studio + Nginx + PostgreSQL + media storage)
- `Ubuntu 2` — App Gateway (Nginx reverse proxy + FastAPI orchestrator)
- `Jetson` — Reachy edge device (TensorRT engine + runtime loop)

> See `memory-bank/requirements.md` (§11–§17) for detailed architecture, ports, and policies.

### 1) Ubuntu 1 — Model Host

1. LM Studio (Meta-Llama-3.1-8B-Instruct):
   
   - Install LM Studio and run the HTTP server on port `1234`.
   
   - Verify endpoint:
     
     ```bash
     curl -s http://10.0.4.130:1234/v1/models | jq .
     ```

2. Media + Nginx + Media Mover:
   
   - Create directories: `/videos/temp`, `/videos/train`, `/videos/test`, `/videos/thumbs`, `/videos/manifests`.
   - Configure Nginx to serve `/videos/` at `http(s)://10.0.4.130/videos/...`.
   - Start the Media Mover API on port `8083` (see `memory-bank/requirements.md` §16).

3. PostgreSQL (metadata only):
   
   - Create DB and user; apply schema migrations (see `memory-bank/requirements.md` §15).

### 2) Ubuntu 2 — App Gateway

1. Python env:
   
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip
   pip install fastapi uvicorn gunicorn pydantic[dotenv] requests psycopg2-binary python-json-logger
   ```

2. Run FastAPI app (placeholder layout):
   
   ```bash
   # Example: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Nginx reverse proxy → FastAPI; allow-list upstreams to `10.0.4.130:1234`, `10.0.4.130:8083`, and `postgres:5432`.

### 3) Jetson — Edge Runtime

- Install NVIDIA JetPack 5.x, TensorRT, and your TRT engine produced by TAO.
- Ensure the robot loop posts emotion events to Ubuntu 2 (see API below), never sending raw video.

## APIs (v1)

> Full API expectations live in `memory-bank/requirements.md` §13–§16 with versioning, error model, auth, and idempotency.

### Emotion Event — Jetson → Ubuntu 2

```http
POST /api/events/emotion HTTP/1.1
Host: ubuntu2
Content-Type: application/json
X-API-Version: v1
```

```json
{
  "schema_version": "v1",
  "device_id": "reachy-mini-01",
  "ts": "2025-09-16T20:11:33Z",
  "emotion": "happy",
  "confidence": 0.87,
  "inference_ms": 92,
  "window": { "fps": 30, "size_s": 1.2, "hop_s": 0.5 },
  "meta": { "model_version": "emotionnet-0.8.4-trt", "temp": 68.2 },
  "correlation_id": "<uuid>"
}
```

### Promote Classified Clip to Train — Ubuntu 2 → Ubuntu 1 (Media Mover/Gateway)

```http
POST http://10.0.4.140:8000/api/promote HTTP/1.1
Content-Type: application/json
X-API-Version: v1
Idempotency-Key: <uuid>
```

```json
{
  "video_id": "<video-uuid>",
  "dest_split": "train",
  "label": "sad",
  "dry_run": false,
  "correlation_id": "<uuid>"
}
```

### Run-Specific Frame Extraction (Fine-Tune Prep)

- Source videos: `train/<emotion>/*.mp4`
- Per-run extracted frames: `train/<emotion>/<epoch_id>/*.jpg` (10 random frames/video)
- Consolidated training set for run: `train/<epoch_id>/*.jpg`
- Run manifests: `manifests/<epoch_id>_train.jsonl`

### Error Payload (standard)

```json
{
  "schema_version": "v1",
  "error": "validation_error",
  "message": "confidence must be between 0 and 1",
  "correlation_id": "abc-123",
  "fields": ["confidence"]
}
```

## Performance & Quality Gates

- Deployment gates and runtime KPIs are defined in `memory-bank/requirements.md` §7.
- Key targets: latency p50/p95 ≤ 120/250 ms, macro F1 ≥ 0.80 in shadow/canary, no GPU throttling in 30-min soak.

## Privacy & Security

- Privacy-first, edge-first: no raw video leaves Jetson by default.
- Only derived data (timestamps, labels, confidences, anonymized session IDs) are persisted.
- See `memory-bank/requirements.md` §8 and §17 for mTLS/JWT, Nginx hardening, retention, and governance.

## Repository Layout (current)

```
reachy_08.4.2/
├── AGENTS.md
├── README.md
├── memory-bank/
│   └── requirements.md
├── apps/
│   ├── api/
│   │   ├── main.py           # FastAPI app
│   │   └── routers/
│   │       ├── gateway.py    # /health, /ready, /metrics, /api/events/emotion, /api/promote
│   │       └── media.py      # /api/media/promote
│   └── web/
│       └── landing_page.py   # Streamlit UI (placeholder)       
├── src/                       
│   ├── gateway/
│   ├── media_mover/
│   └── web_ui/
└── tests/
    └── test_gateway.py
```

## Agents (08.4.2)

This system uses ten cooperating agents (ingest, labeling, promotion/curation, reconciler/audit, training, evaluation, deployment, privacy/retention, observability, reachy-gesture). Orchestration via n8n on Ubuntu 1. See `AGENTS.md` for responsibilities, approval rules, and SLOs.

### Run (local dev)

API:

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Web UI (Streamlit):

```bash
streamlit run apps/web/landing_page.py
```

## Local Testing

- Unit tests for config/controller utils under `tests/`.
- Contract tests for APIs using `pytest + httpx`.
  
  

## License

MIT License.
