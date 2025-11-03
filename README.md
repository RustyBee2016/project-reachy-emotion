# Reachy_Local_08.4.2

Local-first, LAN-contained pipeline for real-time emotion recognition on the Reachy Mini robot, powered by an on-device EmotionNet classifier (TensorRT) and an on-prem LLM for empathetic dialogue. Synthetic video generation and human-in-the-loop curation feed a continuous fine-tuning loop.

- Target platform: `Reachy Mini (Jetson Xavier NX 16GB)`
- Primary language: `Python 3.8+`
- Core stack: DeepStream 6.x + TensorRT 8.6+ (Jetson), FastAPI + Nginx (Ubuntu 2), LM Studio (Ubuntu 1), PostgreSQL (metadata only)

## Quick Start

This repo is organized for a 3-node local lab:
- `Ubuntu 1` — Model Host (LM Studio + Nginx + PostgreSQL + media storage)
- `Ubuntu 2` — App Gateway (Nginx reverse proxy + FastAPI orchestrator)
- `Jetson` — Reachy edge device (TensorRT engine + runtime loop)

> See `memory-bank/requirements_08.4.2.md` (§11–§17) for detailed architecture, ports, and policies.

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
   - Start the Media Mover API on port `8081` (see `memory-bank/requirements_08.4.2.md` §16).
3. PostgreSQL (metadata only):
   - Create DB and user; apply schema migrations (see `memory-bank/requirements_08.4.2.md` §15).

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
3. Nginx reverse proxy → FastAPI; allow-list upstreams to `10.0.4.130:1234`, `10.0.4.130:8081`, and `postgres:5432`.

### 3) Jetson — Edge Runtime
- Install NVIDIA JetPack 5.x, TensorRT, and your TRT engine produced by TAO.
- Ensure the robot loop posts emotion events to Ubuntu 2 (see API below), never sending raw video.

## APIs (v1)

> Full API expectations live in `memory-bank/requirements_08.4.2.md` §13–§16 with versioning, error model, auth, and idempotency.

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

### Promotion — Ubuntu 2 → Ubuntu 1 (Media Mover)
```http
POST http://10.0.4.130:8081/api/media/promote HTTP/1.1
Content-Type: application/json
X-API-Version: v1
Idempotency-Key: <uuid>
```
```json
{ "clip": "clip_00123.mp4", "target": "train", "label": "sad", "dry_run": false }
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
- Deployment gates and runtime KPIs are defined in `memory-bank/requirements_08.4.2.md` §7.
- Key targets: latency p50/p95 ≤ 120/250 ms, macro F1 ≥ 0.80 in shadow/canary, no GPU throttling in 30-min soak.

## Privacy & Security
- Privacy-first, edge-first: no raw video leaves Jetson by default.
- Only derived data (timestamps, labels, confidences, anonymized session IDs) are persisted.
- See `memory-bank/requirements_08.4.2.md` §8 and §17 for mTLS/JWT, Nginx hardening, retention, and governance.

## Repository Layout (current)
```
reachy_08.3/
├── AGENTS_08.4.2.md
├── README.md
├── pyproject.toml            # src-layout for now; apps/* next PR to package
├── memory-bank/
│   └── requirements_08.4.2.md
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
This system uses nine cooperating agents (ingest, labeling, promotion/curation, reconciler/audit, training, evaluation, deployment, privacy/retention, observability). Orchestration via n8n on Ubuntu 1. See `AGENTS_08.4.2.md` for responsibilities, approval rules, and SLOs.

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
1. Open an issue describing the change and link to `memory-bank/requirements_08.4.2.md` sections affected.
2. Fork/branch and submit a PR with:
   - Tests and docs
   - API/OpenAPI updates (if interface change)
   - Signed-off-by trailer if required
   - Gates and privacy checks
   - Agent contracts (where applicable)

## Troubleshooting
- Emotion latency high: check GPU throttling, `inference_ms`, and queue depth on Ubuntu 2.
- No LLM replies: verify LM Studio at `http://10.0.4.130:1234` and Nginx routes.
- Promotion fails 409: confirm `Idempotency-Key` unique, target path exists, and Media Mover reachable at `http://10.0.4.130:8081`.

## License
TBD (add your preferred license).
