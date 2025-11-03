# Routes by AI agents_10-21-25

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/21/2025 22:46:11  
**Updated:** 10/21/2025 22:47:51  
**Exported:** 10/21/2025 22:49:35  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f84571-b85c-8331-ac28-c2a607cab806](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f84571-b85c-8331-ac28-c2a607cab806)  

## Response:
Here’s the up-to-date map of all **routes by AI agent (1–10)** for project **Reachy\_Local\_08.4.2**, combining what’s in `requirements_08.4.2.md`, `AGENTS_08.4.2.md`, and recent backend progress.  
Each route is the FastAPI endpoint or n8n webhook that corresponds to that agent’s function.

* * *

### **Agent 1 — Ingest Agent**

**Purpose:** receive and register new videos.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/media/ingest` | Upload or register new video (UI → backend). |
| `GET` | `/api/media/videos/temp/{id}` | Retrieve metadata or check ingest status. |
| `GET` | `/api/media/healthz` | Health probe for Media Mover service. |

* * *

### **Agent 2 — Labeling Agent**

**Purpose:** manage user-assisted emotion labeling.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/media/label/{video_id}` | Apply human label (`happy` / `sad`). |
| `GET` | `/api/media/labels/summary` | Return per-class counts and balance ratio. |
| `POST` | `/api/media/relabel/{video_id}` | Change or remove a label (admin-only). |

* * *

### **Agent 3 — Promotion / Curation Agent**

**Purpose:** controlled movement from `temp` → `train` or `test`.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/media/promote` | Promote accepted clip; updates DB + filesystem. |
| `GET` | `/api/media/promotions/logs` | View promotion history (curation audit). |

* * *

### **Agent 4 — Reconciler / Audit Agent**

**Purpose:** verify DB ↔ filesystem integrity.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/media/reconcile` | Trigger checksum + manifest rebuild. |
| `GET` | `/api/media/reconcile/report` | Fetch last audit summary. |

* * *

### **Agent 5 — Training Orchestrator**

**Purpose:** launch TAO fine-tuning jobs.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/train/start` | Kick off EmotionNet TAO job when dataset balanced. |
| `GET` | `/api/train/status/{run_id}` | Return MLflow run state and metrics. |
| `GET` | `/api/train/runs` | List recent TAO/MLflow runs. |

* * *

### **Agent 6 — Evaluation Agent**

**Purpose:** validate the trained model.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/eval/run` | Execute validation using balanced test set. |
| `GET` | `/api/eval/metrics/{run_id}` | Retrieve confusion matrix + accuracy. |

* * *

### **Agent 7 — Deployment Agent**

**Purpose:** export and push engine to Jetson.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/deploy/promote` | Approve and deploy engine (`shadow → canary → rollout`). |
| `GET` | `/api/deploy/status` | Report active engine version + latency + FPS. |
| `POST` | `/api/deploy/rollback` | Revert to previous engine on regression. |

* * *

### **Agent 8 — Privacy / Retention Agent**

**Purpose:** enforce TTLs and purge policy.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `DELETE` | `/api/privacy/purge/temp` | Remove expired temp videos. |
| `POST` | `/api/privacy/redact/{video_id}` | Manually purge or anonymize a record. |
| `GET` | `/api/privacy/logs` | Return purge / violation logs. |

* * *

### **Agent 9 — Observability / Telemetry Agent**

**Purpose:** collect and expose metrics.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/obs/metrics` | Prometheus-formatted metrics export. |
| `GET` | `/api/obs/snapshot` | Return live status of all agents. |
| `POST` | `/api/obs/alert` | Manual trigger or test alert. |

* * *

### **Agent 10 — Generation Balancer (Sub-Agent)**

**Purpose:** bias synthetic generation for class balance.  
**Routes:**

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/gen/request` | Request new synthetic videos with target emotion mix. |
| `GET` | `/api/gen/stats` | Return recent generation totals per class. |

* * *

**Summary view**

| Agent # | Endpoint Root | Core Function |
| --- | --- | --- |
| 1 | `/api/media/ingest` | Video ingest + metadata |
| 2 | `/api/media/label` | Human labeling |
| 3 | `/api/media/promote` | Promotion / curation |
| 4 | `/api/media/reconcile` | Audit / manifest rebuild |
| 5 | `/api/train` | TAO fine-tuning orchestration |
| 6 | `/api/eval` | Model evaluation |
| 7 | `/api/deploy` | Engine deployment |
| 8 | `/api/privacy` | Retention / purge |
| 9 | `/api/obs` | Telemetry / metrics |
| 10 | `/api/gen` | Synthetic generation balancer |

This list reflects the **current FastAPI + n8n integration plan** for Reachy\_Local\_08.4.2 and should serve as the reference when adding placeholder routes or testing inter-agent communication.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)