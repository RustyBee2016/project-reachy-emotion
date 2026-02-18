# Reachy_Local_08.4.2

Local-first, LAN-contained pipeline for real-time emotion recognition on the Reachy Mini robot, powered by an on-device EfficientNet-B0 classifier (TensorRT) and an on-prem LLM for empathetic dialogue. Synthetic video generation and human-in-the-loop curation feed a continuous fine-tuning loop.

- Target platform: `Reachy Mini (Jetson Xavier NX 16GB)`
- Primary language: `Python 3.12+`
- Core stack: DeepStream 6.x + TensorRT 8.6+ (Jetson), FastAPI + Nginx (Ubuntu 2), LM Studio (Ubuntu 1), PostgreSQL (metadata only)

## Recent Updates (2026-02)

- **Fine-tuning stack standardized on 3-class EfficientNet-B0 (HSEmotion)**
  - Training config: `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`
  - Pipeline target labels: `happy`, `sad`, `neutral`
- **Promotion flow now follows staged dataset policy**
  - Human labeling stages clips `temp -> dataset_all` via `POST /api/v1/promote/stage`
  - Train/test sets are built via per-run sampling (`POST /api/v1/promote/sample`)
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

**Phases Completed**: 3 of 5 (60%)  
**Tests Created**: 151  
**Test Pass Rate**: 137+ passing (90%+)

✅ **Phase 1**: Web UI & Foundation (43 tests)  
✅ **Phase 2**: ML Pipeline (62 tests)  
✅ **Phase 3**: Edge Deployment (46 tests)  
⏳ **Phase 4**: n8n Orchestration (Pending)  
⏳ **Phase 5**: Production Hardening (Pending)

**See**: `IMPLEMENTATION_STATUS.md` for detailed status  
**Quick Reference**: `QUICK_REFERENCE.md` for common commands

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
   - Create directories: `/videos/temp`, `/videos/dataset_all`, `/videos/train`, `/videos/test`, `/videos/thumbs`, `/videos/manifests`.
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

### Stage to Dataset Corpus — Ubuntu 2 → Ubuntu 1 (Media Mover)
```http
POST http://10.0.4.130:8083/api/v1/promote/stage HTTP/1.1
Content-Type: application/json
X-API-Version: v1
Idempotency-Key: <uuid>
```
```json
{ "video_ids": ["<video-uuid>"], "label": "sad", "dry_run": false }
```

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
reachy_08.3/
├── AGENTS.md
├── README.md
├── pyproject.toml            # src-layout for now; apps/* next PR to package
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
├── shared/
│   └── contracts/
│       └── schemas.py        # Placeholder for shared Pydantic/JSON Schemas
├── src/                      # Legacy location (will be migrated into apps/*)
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

## Development
- Style: black, isort, flake8, mypy
- Tests: pytest; target ≥ 80% coverage
- Commits: conventional commits recommended
- Branches: feature/*, fix/*, release/*

### Local Testing
- Unit tests for config/controller utils under `tests/`.
- Contract tests for APIs using `pytest + httpx`.
- Load test event ingestion with `k6` or `locust` (verify latency histograms).

## CI/CD (suggested)
- Pre-commit hooks for lint/format/type-check.
- GitHub Actions pipeline: build → test → SBOM → sign → publish container/image artifacts.
- Staged deploys: shadow → canary → rollout; evidence bundle must meet Gate A/B/C.

## Contributing
1. Open an issue describing the change and link to `memory-bank/requirements.md` sections affected.
2. Fork/branch and submit a PR with:
   - Tests and docs
   - API/OpenAPI updates (if interface change)
   - Signed-off-by trailer if required
   - Gates and privacy checks
   - Agent contracts (where applicable)

## Troubleshooting
- Emotion latency high: check GPU throttling, `inference_ms`, and queue depth on Ubuntu 2.
- No LLM replies: verify LM Studio at `http://10.0.4.130:1234` and Nginx routes.
- Promotion fails 409: confirm `Idempotency-Key` unique, target path exists, and Media Mover reachable at `http://10.0.4.130:8083`.

## License
TBD (add your preferred license).
