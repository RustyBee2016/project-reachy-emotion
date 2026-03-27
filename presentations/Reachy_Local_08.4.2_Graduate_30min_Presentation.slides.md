# Reachy_Local_08.4.2 — Graduate-Level Technical Briefing

**Import Instructions for Google Slides:**
1. Copy this entire markdown file
2. In Google Slides, go to File → Import slides
3. Use the "By URL" tab if hosted, or paste into a compatible converter
4. Each H2 header (##) becomes a new slide

**Alternate Method:**
Use a markdown-to-slides converter like [MarkShow](https://markshow.app/) or [Slides](https://slides.com/) that supports markdown import, then export to Google Slides format.

---

## Reachy_Local_08.4.2

### A Governed, Local-First Emotion Intelligence Platform

**Russell Bray** — Solutions Architect

Graduate-Level Technical Briefing · 30 Minutes

> "The outcome is not a trained model. The outcome is a deployable, auditable, privacy-first operational capability."

**Slide 1 of 15**

---

## Why the Business Should Care

### Four Levers

- **Engagement** — Emotion-aware interactions increase trust and willingness to interact, even with non-human agents
- **Operational Risk** — Gate A/B/C structure bounds exposure to bad models reaching users
- **Compliance** — Local-first by design: no video leaves the LAN, TTL purges, GDPR-aligned data minimization
- **Iteration Speed** — MLflow-tracked runs, n8n orchestration, hours from new data to validated candidate

**For managers:** Reduce AI deployment risk while maintaining iteration velocity.

**For technologists:** Build the operational envelope around the model, not just the model itself.

**Slide 2 of 15**

---

## Case-Base Scope & Maturity Evidence

### Repository Footprint (excluding venvs & generated artifacts)

| Category | Count | Purpose |
|---|---:|---|
| **Total tracked files** | 1,003 | Full system |
| **Markdown & design docs** | 408 | Requirements, ADRs, runbooks, curriculum |
| **Python implementation** | 222 | Full-stack coverage |
| **JSON artifacts** | 50 | n8n workflows, MLflow configs, gate specs |
| **Shell scripts** | 24 | Service startup, SSL, test runners |

### Python Distribution

**apps/api** (53 files) · **apps/web** (23 files) · **trainer** (21 files) · **apps/reachy** (8 files) · **stats/scripts** (5 files)

**Cross-cutting system** — not a model with a wrapper.

**Slide 3 of 15**

---

## PART II: Architecture & Operations

Slides 4–6 · 06:00–13:30

---

## End-to-End Architecture

```
Streamlit (Ubuntu 2)  ──▶  FastAPI Gateway (Ubuntu 1)  ──▶  PostgreSQL 16
   10.0.4.140                  10.0.4.130                   + Filesystem
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ML Training          MLflow      Jetson Xavier NX
            EfficientNet-B0     Tracking      DeepStream + TRT
            + HSEmotion                        10.0.4.150
                                                    │
                                                    ▼
                                            LLM → Gesture
                                            Reachy Mini (gRPC)
```

**Key Insight:** Layers connected by **explicit event contracts**, not implicit coupling.

**11 FastAPI routers** handling media ingestion, metadata persistence, promotion routing, training triggers, WebSocket cues, and observability endpoints.

**Slide 4 of 15**

---

## Agentic Operating Model (10+1 Agents)

| # | Agent | Role | Key Event |
|---|---|---|---|
| 1 | **Ingest** | SHA-256, metadata, thumbnails → `/videos/temp/` | `ingest.completed` |
| 2 | **Labeling** | 3-class policy, balance tracking, `chk_split_label` | label logged |
| 3 | **Promotion** | `POST /api/v1/media/promote`, frame extraction | promotion logged |
| 4 | **Reconciler** | Checksum verification, orphan detection, manifest rebuild | `reconcile.report` |
| 5 | **Training** | EfficientNet-B0, two-phase, MLflow, Gate A | `training.completed` |
| 6 | **Evaluation** | F1, ECE, Brier, confusion matrix, Gate A pass/fail | eval report |
| 7 | **Deployment** | ONNX → TensorRT → Jetson, Gate B, rollback | deploy logged |
| 8 | **Privacy** | TTL purges, access control | `privacy.purged` |
| 9 | **Observability** | Prometheus, Grafana, error budgets (< 1%/week) | `obs.snapshot` |
| 10 | **Gesture** | WebSocket cues → Reachy Mini via gRPC | gesture executed |

**Design Principle:** Bounded autonomy — cross-boundary actions require upstream events or human approval.

**Slide 5 of 15**

---

## Quality Gates & Governance

### Gate A — Model Quality (before ONNX export)

| Metric | Threshold | Rationale |
|---|---|---|
| Macro F1 | ≥ 0.84 | Balanced quality across 3 classes |
| Balanced Accuracy | ≥ 0.85 | Guards against class-skew |
| Per-class F1 | ≥ 0.75 (floor 0.70) | No class below usability |
| **ECE** | **≤ 0.08** | **Confidence trustworthiness** |
| **Brier** | **≤ 0.16** | **Calibration + discrimination** |

### Gate B — Runtime Performance (Jetson)
**FPS ≥ 25** · **Latency p50 ≤ 120ms** · **GPU memory ≤ 2.5 GB**

### Gate C — Post-Deployment (continuous)
Confidence distribution drift · Accuracy vs labeled holdouts · User-outcome KPIs

### Structural Governance
- Correlation IDs trace artifacts from promotion → training → deployment → telemetry
- Idempotency keys deduplicate operations
- Deprecated endpoints return HTTP 410 + migration guidance
- Exponential backoff with jitter + circuit breakers

**Slide 6 of 15**

---

## PART III: Evidence & Statistical Rigor

Slides 7–8 · 13:30–18:00

---

## Model Performance Trendline

| Variant | Accuracy | Macro F1 | Balanced Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| **Base** | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| **Variant 1** | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| **Variant 2** | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

### Key Improvements (Base → Variant 2)

- **Accuracy:** +11.72 percentage points
- **Macro F1:** +11.78 percentage points
- **Balanced Accuracy:** +12.05 percentage points
- **ECE:** −4.70 pp (confidence now trustworthy to ~6.5 percentage points)
- **Brier:** −6.60 pp (below 0.10 = excellent for 3-class)

### ✅ Variant 2 Clears All Gate A Thresholds

F1 0.93 ≥ 0.84 · Balanced Acc 0.93 ≥ 0.85 · ECE 0.065 ≤ 0.08 · Brier 0.092 ≤ 0.16

**Slide 7 of 15**

---

## Paired Tests & Statistical Rigor

### Three Complementary Tests

| Test | What It Measures | Result |
|---|---|---|
| **Paired t-test** | Mean per-sample accuracy difference | **p < 0.001** |
| **McNemar's test** | Discordant pair asymmetry (binary) | **p < 0.001** |
| **Stuart-Maxwell** | 3-class marginal distribution shift (paired) | **p < 0.001** |

### Why Stuart-Maxwell?

- McNemar's test is binary — loses inter-class shift information
- Stuart-Maxwell operates on the full **k×k confusion matrix** of paired predictions
- Chi-squared statistic with **k−1 degrees of freedom**
- Detects misclassification redistributions that per-class F1 comparisons miss

### Calibration Verification

Bootstrap (1000 resamples): Variant 2 ECE CI **[0.055, 0.076]** vs Base **[0.098, 0.127]** — **no overlap**

**All three tests confirm improvements are real, not sampling artifacts.**

**Slide 8 of 15**

---

## PART IV: Demo & Technical Depth

Slides 9–11 · 18:00–23:00

---

## Backend Demonstration Flow

### 7-Step End-to-End Walkthrough

1. **Ingest** — Upload video → SHA-256 + metadata → `/videos/temp/` → PostgreSQL
2. **Label & Promote** — Assign `happy` → `POST /api/v1/media/promote` → `train/happy/`
3. **Class Balance** — Dashboard shows 1:1:1 ratio, training readiness indicator updates
4. **Train** — `trainer/train_efficientnet.py` → frozen 5 epochs → unfreeze blocks.5/6/conv_head → MLflow tracking
5. **Evaluate** — Test-set inference → Gate A metrics → confusion matrix → pass/fail status
6. **Deploy** — ONNX export → SCP to Jetson → TensorRT conversion → DeepStream load → Gate B validation (or automatic rollback)
7. **Respond** — Live camera → emotion + confidence → LLM prompt → gesture cue → Reachy Mini via gRPC

**Full loop: detection to gesture in under 200 milliseconds**

### Audit Trail
Every step produces a **logged, traceable event** with correlation ID.

**Slide 9 of 15**

---

## API Lifecycle: Promotion Routing

### Request → Validate → Execute → Respond

```
POST /api/v1/media/promote
Headers: X-Correlation-ID, Idempotency-Key
Body: { video_id, target_label, dry_run? }
```

| Phase | Action |
|---|---|
| **Validation** | 3-class policy check, video existence, status verification, `chk_split_label` constraint |
| **Dry Run** | Preview operation: source path, target path, constraint violations — **no execution** |
| **Execution** | **Atomic:** move file + update PostgreSQL + rebuild manifest |
| **Response** | New file path, updated class counts, balance status, correlation ID |
| **Error Handling** | `PromotionValidationError` with structured body: constraint name, expected value, actual value |
| **Legacy Routing** | Deprecated endpoints → HTTP 410 (Gone) + canonical URL + migration guide |

### Three Principles Demonstrated
**Fail-fast validation** · **Atomic state transitions** · **Full traceability**

**Slide 10 of 15**

---

## Emotion → LLM → Gesture Pipeline Design

### Four Stages Turning Model Prediction into Physical Robot Gesture

| Stage | Component | Output |
|---|---|---|
| **1. Detection** | DeepStream + TensorRT (Jetson) | Classification + confidence vector (3 probabilities) |
| **2. Prompt Tailoring** | Confidence-based hedging | Graduated LLM language (high/medium/low certainty) |
| **3. LLM Response** | LM Studio (local network) | Empathetic text + `[GESTURE]` keywords |
| **4. Gesture Execution** | Reachy Mini via gRPC | Physical motor sequence from `emotion_gesture_map.py` |

### 5-Tier Gesture Modulation

| Tier | Confidence Range | Expressiveness | Example |
|---|---|---|---|
| 5 | 0.90–1.00 | Full | Bold wave, wide arm gestures |
| 4 | 0.75–0.90 | High | Standard wave, clear nod |
| 3 | 0.60–0.75 | Medium | Subtle nod, small gesture |
| 2 | 0.45–0.60 | Low | Minimal acknowledgment |
| 1 | 0.00–0.45 | Minimal | Attentive posture only |

**Design Patterns:** Chain of Responsibility + Strategy pattern
**Robot behavior is proportional to model certainty** — perceived as appropriate restraint, not inconsistency.

**Slide 11 of 15**

---

## PART V: Risk, ROI & Competency

Slides 12–15 · 23:00–30:00

---

## Risk Analysis & Mitigation

| # | Risk | Mitigation | Residual |
|---|---|---|---|
| 1 | **Model degradation in production** | Gate C drift detection, auto-retrain trigger, instant rollback | **Low** |
| 2 | **Privacy breach — video exfiltration** | Local-first architecture, no outbound routes, TTL purges, firewall | **Very Low** |
| 3 | **Edge device resource exhaustion** | Gate B hard limits, EfficientNet-B0 edge-optimized | **Low** |
| 4 | **Operator error in labeling** | 3-class policy simplicity, Reconciler anomaly detection, dry-run preview | **Moderate** |
| 5 | **n8n single point of failure** | systemd auto-restart, stateless agents, PostgreSQL checkpoints | **Moderate** |

### Overall Risk Posture
**Managed and measurable** — each risk has a named mitigation, and the gate structure provides **automated enforcement** rather than relying on manual processes.

**For managers:** Risk register maps directly to the gate structure — risks are automatically tested every deployment cycle.

**For technologists:** Stateless agent design means n8n recovery is fast — no distributed transaction state to rebuild.

**Slide 12 of 15**

---

## ROI, Program Implications & Scaling

### Three Dimensions

| Dimension | Detail |
|---|---|
| **Development Velocity** | New agent: 2–4 hours contract definition + 1–2 days implementation (vs 1–2 weeks monolithic) |
| **Operational Cost Avoidance** | AWS equivalent ~$2,000–4,000/month vs on-premise ~$300–500/month. **Breakeven < 3 months** |
| **Vertical Extensibility** | Same pipeline pattern applies to **any classification task** |

### Two Enterprise Verticals Already Designed

- **CareFlow** — Healthcare companion operations. Patient engagement in clinical lobbies, assisted living, rehabilitation. Privacy-first posture critical for HIPAA-adjacent environments.
- **SecureFlow** — Cybersecurity operations. Classification pipeline adapted for threat detection on visual feeds. Governance model (gates, audit trails, rollback) maps to SOC 2 compliance requirements.

### Scaling Path

- **Horizontal:** Add more Jetson nodes for multi-camera deployments
- **Vertical:** Upgrade EfficientNet-B0 → B2 for ~2% higher accuracy at ~2x latency
- **Organizational:** Version-controlled n8n workflows, agent contracts, gate specs — second team can fork and adapt

**Slide 13 of 15**

---

## Competency Proof: Solutions Architect Evidence

### Seven Integrated Domains

| # | Domain | Evidence |
|---|---|---|
| 1 | **System Design** | Distributed system: 3 nodes, 4 languages, 6 technology domains, documented boundaries |
| 2 | **ML Engineering** | HSEmotion transfer learning, two-phase unfreezing, calibration metrics, automated gates |
| 3 | **API Design** | 11 FastAPI routers, correlation IDs, idempotency, dry-run, deprecated shims, OpenAPI |
| 4 | **DevOps / MLOps** | MLflow, n8n orchestration, systemd services, Alembic migrations (12 tables), Prometheus/Grafana |
| 5 | **Edge Deployment** | ONNX → TensorRT → DeepStream → Jetson Xavier NX with real-time performance constraints |
| 6 | **Privacy & Governance** | Local-first architecture, TTL retention, structured audit logging, GDPR alignment, gate controls |
| 7 | **Human-Robot Interaction** | Emotion→gesture mapping, confidence-based modulation, LLM empathy prompting, gRPC execution |

**Each area is individually a specialty.**

**Integrating them into a coherent, governed, deployable system defines a solutions architect** — someone who builds the system that connects components, not just the components themselves.

**Slide 14 of 15**

---

## Summary & Commitments

### What You've Seen Today

1. A **governed, local-first emotion intelligence platform** — video in, empathetic robot behavior out
2. **Ten cooperating agents** with bounded autonomy, explicit contracts, and automated quality gates
3. **Statistical evidence** validated by paired t-tests, McNemar's test, and Stuart-Maxwell test (all p < 0.001)
4. A **complete operational stack** — ingestion through training through edge deployment through gesture execution
5. **Enterprise-grade governance** — correlation IDs, idempotency, audit trails, three deployment gates

### My Ask

**For adoption evaluation** — Available to run live demo on hardware, walk through specific code paths, or discuss adaptation for your domain (CareFlow, SecureFlow, or new vertical)

**For competency evaluation** — Full repository available for code review. Happy to deep-dive on any subsystem: ML pipeline, API layer, deployment pipeline, or gesture modulation system

### 30-Day Commitments

- Gate C monitoring dashboard operational
- Second-vertical prototype (CareFlow or SecureFlow) with domain-specific model
- Performance benchmark report: EfficientNet-B0 vs B2 on Jetson Xavier NX

**Thank you. I am happy to take questions.**

**Slide 15 of 15**

---

## Appendix: Extended Q&A

**Not included in main presentation — reference material**

See full script document for detailed answers to:
1. Why use ECE and Brier score instead of just accuracy and F1?
2. Why EfficientNet-B0 instead of a larger model?
3. What happens when a request hits a deprecated endpoint?
4. How does the Stuart-Maxwell test differ from running McNemar's per class?
5. How does the system handle class imbalance during training?
6. What is the rollback procedure if Gate B fails?
7. How does correlation ID tracing work end-to-end?
8. What would it take to add a fourth emotion class?

---

*End of Google Slides Import Format*
