# Research Paper: Reachy_Local_08.4.2 — A Local-First Agentic AI System for Emotion Classification, Curation, and Edge Deployment

**Authoring context:** internal technical paper for project stakeholders and engineering teams.

## Abstract
This paper presents Reachy_Local_08.4.2, a local-first agentic AI system that orchestrates video ingest, human-assisted labeling, controlled promotion, model training/evaluation, and edge deployment through a multi-agent n8n workflow architecture. The system targets three-class facial emotion classification (`happy`, `sad`, `neutral`) using EfficientNet-B0 fine-tuned from HSEmotion pretraining. The architecture emphasizes strict data governance, reproducibility, and operational safety via approval and metric gates (Gate A/B), idempotent mutation patterns, and audit-first eventing. We describe system design, control-flow semantics, endpoint contracts, failure handling, and deployment reliability mechanisms. We also provide implementation-level guidance on n8n node logic, Python backend interactions, and syntax pitfalls for maintainable evolution.

## 1. Introduction
Agentic pipelines for ML systems often fail at the interfaces between orchestration, backend services, and deployment runtime constraints. Reachy_Local_08.4.2 addresses this by combining:
- **n8n workflow-level control-flow** for deterministic orchestration.
- **FastAPI service contracts** for explicit side-effect semantics.
- **DB/filesystem auditability** for traceable state.
- **Edge deployment constraints** for real-world robotics operation.

The core challenge is not only model quality; it is maintaining **consistent state and safe progression** from raw videos to deployed inference engines.

## 2. System Objectives and Non-goals
### 2.1 Objectives
1. Classify short synthetic videos into `happy`, `sad`, `neutral`.
2. Keep data and inference local-first.
3. Support human-in-the-loop curation and approvals.
4. Maintain reproducible training/evaluation/deployment lifecycle.

### 2.2 Non-goals
- Audio emotion recognition.
- Cloud-dependent inference pipelines.
- Conversational/linguistic emotion synthesis.

## 3. Architecture
### 3.1 Layered architecture
1. **Orchestration Layer (n8n Agents 1–9):** branching, retries, approval gates, and event routing.
2. **Service Layer (FastAPI + Gateway + Media Mover):** ingest/promote/status/event APIs.
3. **State Layer (PostgreSQL + filesystem):** metadata, labels, manifests, audit records, media assets.
4. **Execution Layer (Trainer + Jetson):** EfficientNet fine-tuning/evaluation and TensorRT runtime deployment.

### 3.2 Why multi-agent decomposition works
Each agent has one narrow responsibility. This improves observability and fault isolation:
- If training fails, Agent 5 and its status/event chain are isolated from ingest logic.
- If a policy mismatch appears in promotion, Agent 3 can halt without impacting telemetry collection.

## 4. End-to-End Control Flow
### 4.1 Main path
`Ingest -> Labeling -> Promotion -> Training -> Evaluation -> Deployment`

### 4.2 Continuous supporting paths
`Reconciler`, `Privacy`, and `Observability` run on schedules/manual triggers to enforce integrity, compliance, and telemetry.

### 4.3 Gate semantics
- **Gate A:** quality/calibration threshold gate before export/advance.
- **Gate B:** runtime deployment gate (FPS/latency/memory) before rollout finalization.

### 4.4 Approval semantics
- Promotion and deployment workflows include explicit human approval branches (`approved` vs `rejected`).

## 5. Agent-by-Agent Technical Analysis
### 5.1 Agent 1 (Ingest)
**Logic:** webhook trigger -> header auth -> payload normalization -> ingest API call -> status branch -> event emit -> response.

**Control-flow insight:**
- Normalize input early to prevent downstream contract drift.
- Accept both `done` and `duplicate` as completion states.

**Syntax-level insight:**
In n8n `Code` nodes, normalize payload shape from alternate keys (`source_url`, `url`, nested asset path) before HTTP call.

### 5.2 Agent 2 (Labeling)
**Logic:** validate action + label -> fetch current state -> write label event -> branch by action (`label_only/promote/discard`) -> respond with class balance.

**Control-flow insight:**
- Label event persistence should happen before optional side effects to keep auditable history intact.

**Syntax-level insight:**
Ensure request body keys align with backend request schemas (e.g., `new_label` vs `label` when relabel contract requires it).

### 5.3 Agent 3 (Promotion)
**Logic:** validate request -> dry-run plan -> human approval wait -> execute real promotion on approval -> rebuild manifests -> emit completion event.

**Control-flow insight:**
Dry-run + approval forms a two-phase commit-like pattern for safer state mutation.

### 5.4 Agent 4 (Reconciler)
**Logic:** scheduled/manual trigger -> scan filesystem -> fetch DB inventory -> diff sets -> produce mismatch report -> alert.

**Control-flow insight:**
Drift detection should classify at least: FS-only, DB-only, and metadata mismatches.

### 5.5 Agent 5 (Training Orchestrator)
**Logic:** request trigger -> verify class-balance thresholds -> launch trainer runtime -> poll status -> evaluate Gate A -> emit outcome event.

**Control-flow insight:**
Data readiness should block runs early; do not spend GPU cycles when class minimums are unmet.

### 5.6 Agent 6 (Evaluation)
**Logic:** verify test balance -> run evaluation mode -> persist metrics -> evaluate gate -> emit completed/failed/blocked status.

**Control-flow insight:**
Evaluation should reference test file paths without mutating labels.

### 5.7 Agent 7 (Deployment)
**Logic:** receive candidate -> copy ONNX to Jetson -> build TensorRT engine -> update runtime config/service -> verify Gate B -> rollback on fail.

**Control-flow insight:**
Rollback is a first-class branch and must be tested like a happy path.

### 5.8 Agent 8 (Privacy)
**Logic:** schedule/manual trigger -> query stale temp media -> delete files -> update DB as purged -> write audit -> emit event.

**Control-flow insight:**
Privacy policies are only credible when deletion + metadata updates are coupled and logged.

### 5.9 Agent 9 (Observability)
**Logic:** scrape metrics endpoints -> parse values -> normalize -> store samples -> alert branch.

**Control-flow insight:**
Parser logic should tolerate partial endpoint failures and still persist available metrics.

## 6. Script-Level Understanding for Python/ML Engineers
This section is tailored for Rusty-level implementation review.

### 6.1 Orchestration vs execution
- **n8n** is the control plane (when/if/where).
- **Python/FastAPI/trainer scripts** are the execution plane (how side effects are performed).

### 6.2 Typical script interaction chain
1. n8n node constructs JSON payload and headers.
2. HTTP/SSH node calls backend endpoint or runtime command.
3. Backend script performs I/O (DB/filesystem/model runtime).
4. n8n receives status and branches with `If/Switch` logic.
5. n8n emits event and response.

### 6.3 Pseudocode mapping (control-flow)
```python
# High-level conceptual pseudocode
if not authorized(request.headers):
    return unauthorized_response()

payload = normalize_payload(request.body)
result = call_ingest_endpoint(payload)

if result.status in {"done", "duplicate"}:
    emit_event("ingest.completed", result)

return success_response(result)
```

The key insight is that **branching lives in n8n**, while **side effects live in scripts/endpoints**.

## 7. Reliability, Safety, and Compliance
### 7.1 Reliability mechanisms
- Exponential backoff with bounded retries.
- Idempotency keys on mutating calls.
- Explicit success/failure/reject branches.
- Scheduled reconciliation and telemetry collection.

### 7.2 Safety/compliance mechanisms
- Local-only handling of sensitive media.
- Structured audit trail for promotions and purges.
- Human approvals for irreversible progression points.

## 8. Failure Modes and Mitigations
1. **Endpoint contract drift** -> Mitigation: endpoint alignment docs + schema-level checks.
2. **Node reference breakage after rename** -> Mitigation: enforce stable node naming and review expression references.
3. **Silent runtime regressions** -> Mitigation: Gate A/B + telemetry + rollback branch validation.
4. **Data drift/inconsistency** -> Mitigation: periodic reconciler with manifest rebuild and alerts.

## 9. Discussion
The architecture balances ML quality and operational governance. In robotics contexts, deployment reliability is as important as model performance. Reachy_Local_08.4.2 addresses this by encoding policy and runtime constraints directly into orchestrated control flow.

## 10. Limitations and Future Work
- Extend formal verification of workflow contracts (auto schema diff checks).
- Add richer calibration/uncertainty dashboards for Gate A diagnostics.
- Expand canary analysis automation for Gate B/C progression.
- Integrate gesture-agent pathway into the same governance envelope for full end-to-end emotional interaction lifecycle.

## 11. Conclusion
Reachy_Local_08.4.2 demonstrates a practical pattern for trustworthy agentic MLOps: explicit orchestration, auditable state, gate-driven progression, and reversible deployment. This combination allows fast iteration without sacrificing privacy, traceability, or operational safety.

## Appendix A: Suggested review checklist for engineers
1. Validate endpoint contract and request field names before changing workflow nodes.
2. Confirm all branches exist (success, failure, rejection, blocked).
3. Verify idempotency/correlation propagation.
4. Confirm DB/filesystem side effects are observable and auditable.
5. Re-run gate logic checks after any training/deployment changes.
