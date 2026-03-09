# Reachy_Local_08.4.2 Agentic AI System — Complete Summary

## 1) What the system is
Reachy_Local_08.4.2 is a **local-first, multi-agent MLOps system** orchestrated with n8n. It transforms incoming videos into curated datasets, trains and evaluates a 3-class emotion model (`happy`, `sad`, `neutral`), and deploys validated models to Jetson for real-time inference.

In simple terms, the system is a controlled pipeline:
1. Ingest videos safely.
2. Label and curate with human-in-the-loop approvals.
3. Train and evaluate with strict metric gates.
4. Deploy only when runtime constraints pass.
5. Continuously audit privacy, data integrity, and telemetry.

## 2) Core architecture
The architecture has four layers:
- **Orchestration layer (n8n):** Agent workflows 1–9.
- **Service/API layer (FastAPI + Gateway + Media Mover):** Endpoint contracts, event sinks, status interfaces.
- **State layer (PostgreSQL + local filesystem):** Metadata, label events, manifests, audit logs, media files.
- **Execution layer (Trainer + Jetson):** EfficientNet training/evaluation and TensorRT deployment.

## 3) Agent responsibilities (operational view)
- **Agent 1 Ingest:** Pulls media, computes hash/metadata/thumbnail, inserts records, emits ingest event.
- **Agent 2 Labeling:** Validates human label actions, writes label audit trail, optionally triggers promote/relabel.
- **Agent 3 Promotion:** Runs dry-run plan -> approval -> real promotion -> manifest rebuild -> event emission.
- **Agent 4 Reconciler:** Scans filesystem and DB to detect drift and report mismatches.
- **Agent 5 Training:** Verifies training data readiness, starts pipeline, tracks status, enforces Gate A metrics.
- **Agent 6 Evaluation:** Verifies test readiness, runs evaluation-only pipeline, computes gate metrics and outcomes.
- **Agent 7 Deployment:** Copies ONNX, builds TensorRT engine, updates DeepStream, verifies Gate B, rolls back if needed.
- **Agent 8 Privacy:** Applies TTL-based purge policy and records auditable purge events.
- **Agent 9 Observability:** Scrapes metrics, parses/stores telemetry, supports alerts/SLO tracking.

## 4) Control-flow and gates
### Control-flow
Main path: **Ingest -> Label -> Promote -> Train -> Evaluate -> Deploy**.
Support path: **Reconciler + Privacy + Observability** run continuously in parallel.

### Quality/Release gates
- **Gate A (model quality):** F1, balanced accuracy, and calibration limits determine if artifacts can progress.
- **Gate B (runtime quality):** FPS, latency, and memory limits determine whether deployment can continue or must rollback.

### Approval gates
- Promotion and deployment include explicit human approval checkpoints.

## 5) How scripts and workflow logic fit together
n8n nodes handle orchestration logic (branching, retries, routing), while Python/FastAPI services execute core business functions.

Typical control-flow structure inside an agent:
1. Trigger (`Webhook`/`Schedule`)
2. Normalize/validate (`Code`, `If`, `Switch`)
3. Execute side effect (`HTTP Request`, `Postgres`, `SSH`)
4. Gate decision (`If` on status/metrics/approval)
5. Emit outcome (`HTTP Request` events + response)

## 6) Data integrity and safety invariants
- Every mutating operation should carry correlation and idempotency context.
- Filesystem and DB updates must be traceable by event and audit log.
- Test split labeling policy must stay enforced (`label IS NULL` where required).
- Deployment must always include rollback path.
- Privacy purge must be explicit, recorded, and reversible only via re-ingestion.

## 7) Why this design is robust
- **Separation of concerns:** each agent does one narrow task.
- **Auditability:** event-driven records and DB logs make state transitions visible.
- **Fail-safe behavior:** gate failures and approval denials stop unsafe progression.
- **Local-first privacy:** no raw video leaves local infrastructure by default.

## 8) What Rusty should focus on when changing code
1. Confirm endpoint contracts before editing node expressions.
2. Keep node names stable if referenced from expressions.
3. Verify both success and failure branches (not just happy path).
4. Validate side effects: DB rows, filesystem changes, and emitted events.
5. Re-check Gate A/B definitions whenever training/deployment logic changes.
