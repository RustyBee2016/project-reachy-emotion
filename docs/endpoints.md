# API Endpoints — Reachy_Local_08.4.2

## Overview
Unified API route map for Reachy Local 08.4.2, covering backend (Ubuntu 1), gateway/web UI (Ubuntu 2), and Jetson inference nodes.  
Each endpoint aligns with an n8n AI Agent (1 – 10).

---

## Ubuntu 2 — Gateway / Web API (Port 8000)

**Base URL:** `https://10.0.4.140`  
**Dev URL:**  `http://10.0.4.140:8000`

### Core Routes
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/events/emotion` | Ingest live emotion events from Jetson. |
| `POST` | `/api/promote` | Proxy to Media Mover `/api/media/promote`. |
| `GET`  | `/health` | Liveness probe (`ok`). |
| `GET`  | `/ready` | Readiness probe (`ready`). |
| `GET`  | `/metrics` | Prometheus metrics (internal scrape). |
| `WS`   | `/ws/cues/{device_id}` | Real-time cues from server → Jetson. |

**Media Proxy Examples**
- `/api/videos/list` → Ubuntu 1 Media Mover  
- `/api/media/promote` → Ubuntu 1 Media Mover  
- `/api/llm/chat` → Ubuntu 1 LM Studio (port 1234)

---

## Ubuntu 1 — Backend / Media Mover API (Port 8081)

**Base URL:** `https://10.0.4.130/api`  
All routes reverse-proxied through Nginx (`/api/...`).

### Agent 1 — Ingest Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/media/ingest` | Upload or register new video. |
| `GET`  | `/api/media/videos/temp/{id}` | Retrieve metadata or ingest status. |
| `GET`  | `/api/media/healthz` | Health probe for service. |

### Agent 2 — Labeling Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/media/label/{video_id}` | Apply human label (`happy` / `sad`). |
| `GET`  | `/api/media/labels/summary` | Return per-class counts and ratio. |
| `POST` | `/api/media/relabel/{video_id}` | Modify or remove label. |

### Agent 3 — Promotion / Curation Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/media/promote` | Atomic move `temp → train/test`. |
| `GET`  | `/api/media/promotions/logs` | Retrieve promotion history. |

### Agent 4 — Reconciler / Audit Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/media/reconcile` | Trigger checksum + manifest rebuild. |
| `GET`  | `/api/media/reconcile/report` | Fetch latest audit summary. |

### Agent 5 — Training Orchestrator
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/train/start` | Launch TAO EmotionNet fine-tuning. |
| `GET`  | `/api/train/status/{run_id}` | Return MLflow run state / metrics. |
| `GET`  | `/api/train/runs` | List recent TAO runs. |

### Agent 6 — Evaluation Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/eval/run` | Execute validation on balanced test set. |
| `GET`  | `/api/eval/metrics/{run_id}` | Retrieve confusion matrix + accuracy. |

### Agent 7 — Deployment Agent
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/deploy/promote` | Approve and deploy engine (`shadow→canary→rollout`). |
| `GET`  | `/api/deploy/status` | Active engine version + latency + FPS. |
| `POST` | `/api/deploy/rollback` | Revert to previous engine. |

### Agent 8 — Privacy / Retention Agent
| Method | Route | Description |
|:--|:--|:--|
| `DELETE` | `/api/privacy/purge/temp` | Remove expired temp videos. |
| `POST`   | `/api/privacy/redact/{video_id}` | Manual purge / anonymize record. |
| `GET`    | `/api/privacy/logs` | Return purge / violation logs. |

### Agent 9 — Observability / Telemetry Agent
| Method | Route | Description |
|:--|:--|:--|
| `GET`  | `/api/obs/metrics` | Prometheus metrics export. |
| `GET`  | `/api/obs/snapshot` | Live agent status snapshot. |
| `POST` | `/api/obs/alert` | Manual or test alert trigger. |

### Agent 10 — Generation Balancer (Sub-Agent)
| Method | Route | Description |
|:--|:--|:--|
| `POST` | `/api/gen/request` | Request new synthetic videos with target emotion mix. |
| `GET`  | `/api/gen/stats` | Recent generation totals per class. |

---

## Ubuntu 1 — LM Studio API (Port 1234)
`POST /v1/chat/completions` — OpenAI-compatible endpoint used by Gateway `/api/llm/chat`.

---

## Ubuntu 2 — Streamlit Web UI (Port 8501)
Reverse-proxied at `https://10.0.4.140/`  
Provides upload, labeling, and training controls.  
Communicates only through Gateway API above.

---

## Jetson NX — DeepStream Runtime
- WebSocket: `/ws/cues/{device_id}` for real-time cues  
- Emits POST `/api/events/emotion` to Gateway

---

## Error Response Format
```json
{
  "schema_version": "v1",
  "error": "validation_error",
  "message": "Detailed message",
  "correlation_id": "uuid-here",
  "fields": ["/field/path"]
}
