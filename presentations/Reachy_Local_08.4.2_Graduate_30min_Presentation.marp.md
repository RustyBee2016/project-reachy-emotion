---
marp: true
theme: default
paginate: true
backgroundColor: #1a1a2e
color: #e0e0e0
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }
  h1 { color: #D4166A; }
  h2 { color: #7B2FF7; }
  h3 { color: #00B4D8; }
  strong { color: #D4166A; }
  table { font-size: 0.8em; }
  th { background-color: #7B2FF7; color: white; }
  td { border-color: #333; }
  code { background-color: #2a2a4e; color: #00B4D8; }
  a { color: #00B4D8; }
  blockquote { border-left: 4px solid #D4166A; padding-left: 1em; font-style: italic; }
---

<!-- _class: lead -->

# Reachy_Local_08.4.2
## A Governed, Local-First Emotion Intelligence Platform

**Russell Bray** — Solutions Architect
Graduate-Level Technical Briefing · 30 Minutes

> "The outcome is not a trained model. The outcome is a deployable, auditable, privacy-first operational capability."

<!--
PART I — EXECUTIVE FRAMING (00:00–06:00)
Slide 1 of 15 · Title & Outcome Statement
-->

---

# Why the Business Should Care

### Four Levers

- **Engagement** — Emotion-aware interactions increase trust and willingness to interact, even with non-human agents
- **Operational Risk** — Gate A/B/C structure bounds exposure to bad models reaching users
- **Compliance** — Local-first by design: no video leaves the LAN, TTL purges, GDPR-aligned data minimization
- **Iteration Speed** — MLflow-tracked runs, n8n orchestration, hours from new data to validated candidate

> **For managers:** Reduce AI deployment risk while maintaining iteration velocity.
> **For technologists:** Build the operational envelope around the model, not just the model itself.

<!--
Slide 2 of 15 · Why the Business Should Care (02:00–04:00)
-->

---

# Case-Base Scope & Maturity Evidence

### Repository Footprint (excl. venvs & generated artifacts)

| Category | Count | Purpose |
|---|---:|---|
| **Total tracked files** | 1,003 | Full system |
| **Markdown & design docs** | 408 | Requirements, ADRs, runbooks, curriculum |
| **Python implementation** | 222 | Full-stack coverage |
| **JSON artifacts** | 50 | n8n workflows, MLflow configs, gate specs |
| **Shell scripts** | 24 | Service startup, SSL, test runners |

### Python Distribution

- `apps/api` (53) · `apps/web` (23) · `trainer` (21) · `apps/reachy` (8) · `stats/scripts` (5)

> **Cross-cutting system** — not a model with a wrapper.

<!--
Slide 3 of 15 · Maturity Evidence (04:00–06:00)
-->

---

<!-- _class: lead -->

# Part II
## Architecture & Operations
Slides 4–6 · 06:00–13:30

---

# End-to-End Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Streamlit   │───▶│  FastAPI Gateway  │───▶│  PostgreSQL 16  │
│  (Ubuntu 2)  │    │   (Ubuntu 1)     │    │  + Filesystem   │
│  10.0.4.140  │    │   10.0.4.130     │    │   Manifests     │
└─────────────┘    └───────┬──────────┘    └─────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────────┐ ┌─────────┐ ┌──────────────┐
     │  ML Training  │ │  MLflow │ │ Jetson NX    │
     │  EfficientNet │ │ Tracking│ │ DeepStream   │
     │  B0 + HSEmo   │ │         │ │ + TensorRT   │
     └──────────────┘ └─────────┘ │ 10.0.4.150   │
                                   └──────┬───────┘
                                          ▼
                                  ┌──────────────┐
                                  │ LLM → Gesture │
                                  │ Reachy Mini   │
                                  └──────────────┘
```

> Layers connected by **explicit event contracts**, not implicit coupling.

<!--
Slide 4 of 15 · Architecture (06:00–08:30)
-->

---

# Agentic Operating Model (10+1 Agents)

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
| 9 | **Observability** | Prometheus, Grafana, error budgets (< 1%/wk) | `obs.snapshot` |
| 10 | **Gesture** | WebSocket cues → Reachy Mini via gRPC | gesture executed |

> Design principle: **Bounded autonomy** — cross-boundary actions require upstream events or human approval.

<!--
Slide 5 of 15 · Agents (08:30–11:00)
-->

---

# Quality Gates & Governance

### Gate A — Model Quality (before ONNX export)

| Metric | Threshold | Rationale |
|---|---|---|
| Macro F1 | ≥ 0.84 | Balanced quality across 3 classes |
| Balanced Accuracy | ≥ 0.85 | Guards against class-skew |
| Per-class F1 | ≥ 0.75 (floor 0.70) | No class below usability |
| ECE | ≤ 0.08 | Confidence trustworthiness |
| Brier | ≤ 0.16 | Calibration + discrimination |

### Gate B — Runtime (Jetson)
FPS ≥ 25 · Latency p50 ≤ 120ms · GPU ≤ 2.5 GB

### Gate C — Post-Deployment (continuous)
Confidence drift · Accuracy vs holdouts · User-outcome KPIs

### Structural Governance
Correlation IDs · Idempotency keys · Deprecated endpoint shims (HTTP 410) · Instruction priority stack · Exponential backoff + circuit breakers

<!--
Slide 6 of 15 · Gates & Governance (11:00–13:30)
-->

---

<!-- _class: lead -->

# Part III
## Evidence & Statistical Rigor
Slides 7–8 · 13:30–18:00

---

# Model Performance Trendline

| Variant | Accuracy | Macro F1 | Balanced Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| **Base** | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| **Variant 1** | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| **Variant 2** | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

### Key Improvements (Base → Variant 2)
- **Accuracy:** +11.72 pp · **Macro F1:** +11.78 pp · **Balanced Acc:** +12.05 pp
- **ECE:** −4.70 pp (confidence now trustworthy to ~6.5 pp)
- **Brier:** −6.60 pp (below 0.10 = excellent for 3-class)

### ✅ Variant 2 Clears All Gate A Thresholds
F1 0.93 ≥ 0.84 · Balanced Acc 0.93 ≥ 0.85 · ECE 0.065 ≤ 0.08 · Brier 0.092 ≤ 0.16

<!--
Slide 7 of 15 · Performance Trendline (13:30–16:00)
-->

---

# Paired Tests & Statistical Rigor

### Three Complementary Tests

| Test | What It Measures | Result |
|---|---|---|
| **Paired t-test** | Mean per-sample accuracy difference | p < 0.001 |
| **McNemar's test** | Discordant pair asymmetry (binary) | p < 0.001 |
| **Stuart-Maxwell** | 3-class marginal distribution shift (paired) | p < 0.001 |

### Why Stuart-Maxwell?
- McNemar's is binary — loses inter-class shift information
- Stuart-Maxwell operates on the full k×k confusion matrix
- Chi-squared with k−1 degrees of freedom
- Detects misclassification redistributions that per-class F1 misses

### Calibration Verification
Bootstrap (1000 resamples): Variant 2 ECE CI **[0.055, 0.076]** vs Base **[0.098, 0.127]** — no overlap.

<!--
Slide 8 of 15 · Statistical Rigor (16:00–18:00)
-->

---

<!-- _class: lead -->

# Part IV
## Demo & Technical Depth
Slides 9–11 · 18:00–23:00

---

# Backend Demonstration Flow

### 7-Step End-to-End Walkthrough

1. **Ingest** — Upload video → SHA-256 + metadata → `/videos/temp/` → PostgreSQL
2. **Label & Promote** — Assign `happy` → `POST /api/v1/media/promote` → `train/happy/`
3. **Class Balance** — Dashboard shows 1:1:1 ratio, training readiness indicator
4. **Train** — `trainer/train_efficientnet.py` → frozen 5 epochs → unfreeze blocks.5/6/conv_head → MLflow
5. **Evaluate** — Test-set inference → Gate A metrics → confusion matrix → pass/fail
6. **Deploy** — ONNX → SCP → TensorRT → DeepStream → Gate B validation (or rollback)
7. **Respond** — Camera → emotion + confidence → LLM prompt → gesture cue → Reachy Mini via gRPC

> **Full loop: detection to gesture in under 200ms**

### Audit Trail
Every step produces a logged, traceable event with correlation ID.

<!--
Slide 9 of 15 · Demo Plan (18:00–20:00)
-->

---

# API Lifecycle: Promotion Routing

### Request → Validate → Execute → Respond

```
POST /api/v1/media/promote
Headers: X-Correlation-ID, Idempotency-Key
Body: { video_id, target_label, dry_run? }
```

| Phase | Action |
|---|---|
| **Validation** | 3-class policy check, existence, status, `chk_split_label` constraint |
| **Dry Run** | Preview: source path, target path, constraint violations — no execution |
| **Execution** | Atomic: move file + update PostgreSQL + rebuild manifest |
| **Response** | New path, class counts, balance status, correlation ID |
| **Error** | `PromotionValidationError` with constraint name, expected, actual |
| **Legacy** | `/api/v1/promote/stage` → HTTP 410 + canonical URL + migration guide |

### Three Principles
**Fail-fast validation** · **Atomic state transitions** · **Full traceability**

<!--
Slide 10 of 15 · API Lifecycle (20:00–21:30)
-->

---

# Emotion → LLM → Gesture Pipeline

### Four Stages

| Stage | Component | Output |
|---|---|---|
| 1. **Detection** | DeepStream + TensorRT (Jetson) | Classification + confidence vector |
| 2. **Prompt Tailoring** | Confidence-based hedging | Graduated language (high/med/low) |
| 3. **LLM Response** | LM Studio (local) | Empathetic text + `[GESTURE]` keywords |
| 4. **Gesture Execution** | Reachy Mini via gRPC | Physical motor sequence |

### 5-Tier Gesture Modulation

| Tier | Confidence | Expressiveness | Example |
|---|---|---|---|
| 5 | 0.90–1.00 | Full | Bold wave, wide arm gestures |
| 4 | 0.75–0.90 | High | Standard wave, clear nod |
| 3 | 0.60–0.75 | Medium | Subtle nod, small gesture |
| 2 | 0.45–0.60 | Low | Minimal acknowledgment |
| 1 | 0.00–0.45 | Minimal | Attentive posture only |

> **Chain of Responsibility + Strategy pattern** — behavior proportional to certainty.

<!--
Slide 11 of 15 · Emotion Pipeline (21:30–23:00)
-->

---

<!-- _class: lead -->

# Part V
## Risk, ROI & Competency
Slides 12–15 · 23:00–30:00

---

# Risk Analysis & Mitigation

| # | Risk | Mitigation | Residual |
|---|---|---|---|
| 1 | **Model degradation** | Gate C drift detection, auto-retrain, instant rollback | Low |
| 2 | **Video exfiltration** | Local-first architecture, no outbound routes, TTL purges, firewall | Very Low |
| 3 | **Edge resource exhaustion** | Gate B hard limits, EfficientNet-B0 edge-optimized | Low |
| 4 | **Operator mislabeling** | 3-class simplicity, Reconciler anomaly detection, dry-run preview | Moderate |
| 5 | **n8n SPOF** | systemd auto-restart, stateless agents, PostgreSQL checkpoints | Moderate |

### Risk Posture
**Managed and measurable** — each risk has a named mitigation, and the gate structure provides automated enforcement rather than manual processes.

> **For managers:** Risk register maps to gate structure — automatically tested every cycle.
> **For technologists:** Stateless agent design = fast n8n recovery, no distributed state to rebuild.

<!--
Slide 12 of 15 · Risk Analysis (23:00–25:00)
-->

---

# ROI, Scaling & Vertical Extensibility

### Three Dimensions

| Dimension | Detail |
|---|---|
| **Development Velocity** | New agent: 2–4 hrs contract + 1–2 days impl (vs 1–2 wks monolithic). Open/Closed at system level. |
| **Cost Avoidance** | AWS equivalent ~$2–4K/mo vs on-prem ~$300–500/mo. Breakeven < 3 months. |
| **Vertical Extensibility** | Same pipeline pattern for any classification task. |

### Two Verticals Designed

- **CareFlow** — Healthcare companion ops. Patient engagement, HIPAA-adjacent privacy.
- **SecureFlow** — Cybersecurity ops. Threat detection, SOC 2-aligned governance.

### Scaling Path
- **Horizontal:** More Jetson nodes for multi-camera
- **Vertical:** EfficientNet-B0 → B2 (~2% accuracy, ~2x latency)
- **Organizational:** Version-controlled workflows — fork and adapt

<!--
Slide 13 of 15 · ROI & Scaling (25:00–27:00)
-->

---

# Competency Proof: Solutions Architect

### Seven Integrated Domains

| # | Domain | Evidence |
|---|---|---|
| 1 | **System Design** | 3 nodes, 4 languages, 6 tech domains, documented boundaries |
| 2 | **ML Engineering** | HSEmotion transfer learning, two-phase unfreezing, calibration metrics, auto gates |
| 3 | **API Design** | 11 routers, correlation IDs, idempotency, dry-run, deprecated shims, OpenAPI |
| 4 | **DevOps / MLOps** | MLflow, n8n, systemd, Alembic (12 tables), Prometheus/Grafana |
| 5 | **Edge Deployment** | ONNX → TensorRT → DeepStream → Jetson with real-time constraints |
| 6 | **Privacy & Governance** | Local-first, TTL, audit logging, GDPR alignment, gate controls |
| 7 | **Human-Robot Interaction** | Emotion→gesture mapping, confidence modulation, LLM empathy, gRPC execution |

> Each area is individually a specialty. Integrating them into a coherent, governed, deployable system defines a **solutions architect**.

<!--
Slide 14 of 15 · Competency Proof (27:00–29:00)
-->

---

<!-- _class: lead -->

# Summary & Commitments

### What You've Seen

1. **Governed, local-first emotion intelligence platform** — video in, empathetic robot behavior out
2. **Ten cooperating agents** with bounded autonomy and automated quality gates
3. **Statistical evidence** — paired t-tests, McNemar's, Stuart-Maxwell (all p < 0.001)
4. **Complete operational stack** — ingestion → training → edge deployment → gesture execution
5. **Enterprise-grade governance** — correlation IDs, idempotency, audit trails, three gates

### 30-Day Commitments
- Gate C monitoring dashboard operational
- Second-vertical prototype (CareFlow or SecureFlow)
- EfficientNet-B0 vs B2 benchmark on Jetson Xavier NX

### Thank You
Live demo · Code review · Domain adaptation discussion — I'm available for all three.

<!--
Slide 15 of 15 · Close (29:00–30:00)
-->
