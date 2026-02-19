# System Architecture — Project Reachy

## Topology Overview

```
          +---------------------------+                  +---------------------------+
          |        Jetson (Edge)      |                  |      Ubuntu 1 (Model)     |
          |---------------------------|                  |---------------------------|
Camera -->| DeepStream + TensorRT     |   Emotion JSON   | LM Studio (LLM)           |
 stream   | EfficientNet-B0 engine    |--------------->  | Media Mover API (8083)    |
          | Windowing + smoothing     |                  | Nginx media / thumbnails  |
          |                           |   Cue websocket  | PostgreSQL (metadata)     |
          | <------------------------ |<-----------------| Storage (/videos/*)       |
          +---------------------------+                  +---------------------------+
                       |                                            ^
                       |                                            |
                       v                                            |
                (metrics/logs)                                      |
          +---------------------------------------------------------+-------+
          |                      Ubuntu 2 (Gateway)                         |
          |-----------------------------------------------------------------|
          | Nginx reverse proxy (TLS)                                       |
          | FastAPI gateway (/api/events/emotion, /api/promote, /ws/cues)   |
          | Web UI (Streamlit)                                              |
          | n8n Orchestrator Triggers                                       |
          |-----------------------------------------------------------------|
          | Responsibilities:                                               |
          | 1. Receive Jetson emotion events & log to DB                    |
          | 2. Call LM Studio for empathetic responses                      |
          | 3. Fan-out cues to Jetson via WebSocket                         |
          | 4. Accept human curation -> Media Mover promotions              |
          | 5. Expose manifests, health, metrics                            |
          +-----------------------------------------------------------------+
```

## Data & Control Flows

1. **Inference Loop**
   - Jetson performs real-time inference and posts emotion events to Ubuntu 2 (`POST /api/events/emotion`).
   - Ubuntu 2 persists metadata, triggers LM Studio (Ubuntu 1) for contextual text, and streams cues back to Jetson (`/ws/cues/{device_id}`).

2. **Human-in-the-Loop Curation**
   - Web UI on Ubuntu 2 shows clips from `/videos/temp` (served via Ubuntu 1 Nginx).
   - Accepted clips trigger gateway `POST /api/promote` → Media Mover `POST /api/media/promote`, moving files `temp -> train/<label>` and updating PostgreSQL.

3. **Training & Evaluation**
   - Ubuntu 1 training jobs read `/videos/train/<label>`; dataset prep extracts run-specific frames (`train/<label>/<run_id>` and `train/<run_id>/<label>`).
   - Training/evaluation outputs metrics and new TensorRT engines stored on Ubuntu 1; deployment agent transfers engines back to Jetson.

4. **Observability & Governance**
   - All services emit structured logs with `correlation_id`.
   - Idempotency enforced on mutate endpoints; reconciler validates filesystem ↔ database state nightly.

## Key Technology Mapping

| Layer        | Stack / Tools                                         |
|--------------|-------------------------------------------------------|
| Edge         | NVIDIA Jetson Xavier NX, DeepStream 6.x, TensorRT 8.6 |
| Gateway      | FastAPI, Uvicorn, Nginx, Streamlit, n8n               |
| Model Host   | LM Studio (Llama 3.1), PostgreSQL 16, Media Mover     |
| Storage      | Ext4/ZFS under `/media/project_data/reachy_emotion/`  |
| ML Pipeline  | EfficientNet-B0 (HSEmotion), PyTorch fine-tuning      |
| Deployment   | TensorRT engines, SCP to Jetson, systemd services     |
| Security     | LAN-only, TLS/mTLS, JWT, Idempotency-Key headers      |

## Trust Boundaries

- **Jetson ↔ Ubuntu 2**: JSON events + WebSocket cues, no raw video leaves Jetson.
- **Ubuntu 2 ↔ Ubuntu 1**: Promotion API (+idempotent writes), LM Studio chat, manifest rebuilds.
- **Storage/DB**: Only Ubuntu 1 mutates `/videos/*` and PostgreSQL; Ubuntu 2 interacts through authenticated APIs.

## Operational Highlights

- Promotion pipeline enforces `happy|sad|neutral` labels and logs every move.
- Training runs reference manifests (JSONL) tied to dataset hashes for reproducibility.
- Observability agents watch latency, dataset balance, and promotion integrity.
