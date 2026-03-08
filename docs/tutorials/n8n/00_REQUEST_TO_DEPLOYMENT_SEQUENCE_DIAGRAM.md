# Reachy 08.4.2 — Request-to-Deployment Sequence Diagram (Single Page)

This page gives Rusty (and delivery stakeholders) one end-to-end view of how a video request moves through the n8n agentic system to model deployment.

## End-to-end sequence (Agent 1 -> Agent 9)

```mermaid
sequenceDiagram
    autonumber
    participant UI as Web UI / Caller
    participant A1 as Agent 1 Ingest (n8n)
    participant MM as Media Mover API
    participant FS as Local Storage
    participant DB as PostgreSQL
    participant GW as Gateway API
    participant A2 as Agent 2 Labeling (n8n)
    participant A3 as Agent 3 Promotion (n8n)
    participant A4 as Agent 4 Reconciler (n8n)
    participant A5 as Agent 5 Training (n8n)
    participant TR as Trainer Runtime (PyTorch)
    participant A6 as Agent 6 Evaluation (n8n)
    participant A7 as Agent 7 Deployment (n8n)
    participant JN as Jetson / DeepStream
    participant A8 as Agent 8 Privacy (n8n)
    participant A9 as Agent 9 Observability (n8n)

    UI->>A1: POST ingest webhook (source_url + metadata)
    A1->>MM: POST /api/v1/ingest/pull (Idempotency-Key, Correlation-ID)
    MM->>FS: Save video in temp + generate thumbnail
    MM->>DB: Insert video row + media metadata + checksum
    MM-->>A1: status=done|duplicate + video_id
    A1->>GW: POST /api/events/ingest
    A1-->>UI: Respond success / duplicate

    UI->>A2: Submit label + action
    A2->>DB: Validate/apply label event + update video state
    alt action == promote_train or promote_test
        A2->>MM: POST /api/v1/media/promote
    end
    A2-->>UI: Return label status + class balance

    UI->>A3: Request promotion
    A3->>MM: Dry-run promote plan
    A3-->>UI: Await human approval decision
    alt approved
        A3->>MM: Real promote execution
        A3->>MM: Rebuild manifests
        A3->>GW: POST /api/events/pipeline
        A3-->>UI: Promotion completed
    else rejected
        A3-->>UI: 403 promotion rejected
    end

    par scheduled/manual maintenance
        A4->>FS: Scan temp/train/test tree
        A4->>DB: Fetch canonical inventory
        A4->>GW: Emit reconcile report / alerts
    and retention
        A8->>DB: Query stale temp candidates (TTL policy)
        A8->>FS: Delete expired files
        A8->>DB: Mark purged + audit logs
        A8->>GW: Emit privacy events
    and telemetry
        A9->>GW: Scrape /metrics
        A9->>MM: Scrape /metrics
        A9->>DB: Store normalized obs_samples
    end

    UI->>A5: Request training start
    A5->>DB: Check train balance thresholds
    alt train data ready
        A5->>TR: Launch EfficientNet training pipeline (SSH)
        TR->>DB: Persist run status + metrics references
        A5->>GW: training.completed or training.failed
    else blocked
        A5-->>UI: blocked (insufficient balanced data)
    end

    UI->>A6: Request evaluation
    A6->>DB: Check test balance thresholds
    alt test data ready
        A6->>TR: Run evaluation pipeline (skip-train mode)
        TR->>DB: Persist evaluation metrics + gate values
        A6->>GW: evaluation.completed / gate_failed
    else blocked
        A6-->>UI: blocked (insufficient test samples)
    end

    UI->>A7: Approve deployment candidate
    A7->>JN: SCP ONNX + build TensorRT engine + restart DeepStream
    A7->>JN: Verify Gate B (fps/latency/memory)
    alt Gate B pass
        A7->>GW: deployment.completed
    else Gate B fail
        A7->>JN: Rollback prior engine
        A7->>GW: deployment.rolled_back
    end
```

## How to read this diagram (control-flow focus)
- **Linear data path:** Ingest -> Labeling -> Promotion -> Training/Evaluation -> Deployment.
- **Policy/ops side paths:** Reconciler, Privacy, and Observability run alongside the main path to keep state clean, compliant, and measurable.
- **Approval gates:** Promotion and deployment include explicit human decision points.
- **Metric gates:** Gate A (training/eval quality) and Gate B (runtime performance) decide if the system can progress safely.

## Key engineering invariants shown by the sequence
1. All mutating operations carry idempotency/correlation context.
2. Filesystem + DB state changes are paired with event emission for auditability.
3. Deployment is reversible by design (rollback branch is first-class, not an afterthought).
4. Maintenance/telemetry agents are continuous controls, not optional extras.
