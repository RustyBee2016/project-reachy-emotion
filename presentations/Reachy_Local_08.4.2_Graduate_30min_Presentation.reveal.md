---
title: "Reachy_Local_08.4.2 — Graduate-Level Technical Briefing"
author: "Russell Bray — Solutions Architect"
date: "2026-03-25"
theme: moon
transition: slide
slideNumber: true
controls: true
progress: true
history: true
center: true
---

# Reachy_Local_08.4.2 {data-background-color="#1a1a2e"}

## A Governed, Local-First Emotion Intelligence Platform

**Russell Bray** — Solutions Architect

Graduate-Level Technical Briefing · 30 Minutes

> "The outcome is not a trained model. The outcome is a deployable, auditable, privacy-first operational capability."

::: notes
PART I — EXECUTIVE FRAMING (00:00–06:00). Slide 1 of 15. Title & Outcome Statement. Pause after the thesis statement — everything that follows supports this claim.
:::

---

## Why the Business Should Care {data-background-color="#1a1a2e"}

### Four Levers

- **Engagement** — Emotion-aware interactions increase trust, even with non-human agents
- **Operational Risk** — Gate A/B/C bounds exposure to bad models reaching users
- **Compliance** — Local-first: no video leaves LAN, TTL purges, GDPR-aligned
- **Iteration Speed** — MLflow-tracked runs, n8n orchestration, hours not weeks

. . .

> **Managers:** Reduce AI deployment risk while maintaining velocity.
> **Technologists:** Build the operational envelope, not just the model.

::: notes
Slide 2 of 15 (02:00–04:00). Four business levers: engagement, operational risk, compliance, iteration speed. Emphasis on the operational envelope concept.
:::

---

## Case-Base Scope & Maturity {data-background-color="#1a1a2e"}

### Repository Footprint

| Category | Count | Purpose |
|---|---:|---|
| Total tracked files | 1,003 | Full system |
| Markdown & design docs | 408 | Requirements, ADRs, runbooks |
| Python implementation | 222 | Full-stack coverage |
| JSON artifacts | 50 | n8n workflows, configs, specs |
| Shell scripts | 24 | Automation & deployment |

### Python Distribution

`apps/api` (53) · `apps/web` (23) · `trainer` (21) · `apps/reachy` (8) · `stats/scripts` (5)

> **Cross-cutting system** — not a model with a wrapper.

::: notes
Slide 3 of 15 (04:00–06:00). Functional decomposition by directory reveals system boundaries. 222 Python files across 5 subsystems.
:::

---

# Part II: Architecture & Operations {data-background-color="#7B2FF7"}

Slides 4–6 · 06:00–13:30

---

## End-to-End Architecture {data-background-color="#1a1a2e"}

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

> Layers connected by **explicit event contracts**, not implicit coupling.

::: notes
Slide 4 of 15 (06:00–08:30). Walk through each layer: UI, gateway, data, ML, deployment, output, cross-cutting. Key: event-driven microservice architecture on LAN.
:::

---

## Agentic Operating Model (10+1) {data-background-color="#1a1a2e"}

| # | Agent | Role |
|---|---|---|
| 1 | **Ingest** | SHA-256, metadata, thumbnails → `temp/` |
| 2 | **Labeling** | 3-class policy, balance, `chk_split_label` |
| 3 | **Promotion** | Canonical promote endpoint, frame extraction |
| 4 | **Reconciler** | Checksum verify, orphan detect, manifest rebuild |
| 5 | **Training** | EfficientNet-B0, two-phase, MLflow, Gate A |
| 6 | **Evaluation** | F1, ECE, Brier, confusion matrix, Gate A |
| 7 | **Deployment** | ONNX → TensorRT → Jetson, Gate B, rollback |
| 8 | **Privacy** | TTL purges, access control |
| 9 | **Observability** | Prometheus, Grafana, error budgets |
| 10 | **Gesture** | WebSocket → Reachy Mini via gRPC |

> **Bounded autonomy** — cross-boundary actions require upstream events or human approval.

::: notes
Slide 5 of 15 (08:30–11:00). Actor-model variant. n8n as orchestration bus, not distributed broker. Reactor pattern in asyncio for gateway.
:::

---

## Quality Gates & Governance {data-background-color="#1a1a2e"}

### Gate A — Model Quality

| Metric | Threshold |
|---|---|
| Macro F1 | ≥ 0.84 |
| Balanced Accuracy | ≥ 0.85 |
| Per-class F1 | ≥ 0.75 (floor 0.70) |
| ECE | ≤ 0.08 |
| Brier | ≤ 0.16 |

### Gate B — Runtime (Jetson)
FPS ≥ 25 · Latency p50 ≤ 120ms · GPU ≤ 2.5 GB

### Gate C — Post-Deployment
Confidence drift · Accuracy vs holdouts · User-outcome KPIs

### Structural: Correlation IDs · Idempotency · Deprecated shims · Priority stack · Backoff + breakers

::: notes
Slide 6 of 15 (11:00–13:30). ECE = equal-width binning, 10 bins. Brier decomposes into calibration + discrimination. Correlation IDs trace artifacts from promotion to telemetry.
:::

---

# Part III: Evidence & Statistical Rigor {data-background-color="#D4166A"}

Slides 7–8 · 13:30–18:00

---

## Model Performance Trendline {data-background-color="#1a1a2e"}

| Variant | Accuracy | Macro F1 | Bal. Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| **Base** | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| **Variant 1** | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| **Variant 2** | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

. . .

### Improvements (Base → Variant 2)

- **Accuracy:** +11.72 pp · **F1:** +11.78 pp · **Bal. Acc:** +12.05 pp
- **ECE:** −4.70 pp · **Brier:** −6.60 pp

### ✅ All Gate A Thresholds Cleared

::: notes
Slide 7 of 15 (13:30–16:00). ECE 0.065 means confidence trustworthy to ~6.5pp. Brier below 0.10 is excellent for 3-class.
:::

---

## Paired Tests & Statistical Rigor {data-background-color="#1a1a2e"}

### Three Complementary Tests

| Test | Measures | Result |
|---|---|---|
| **Paired t-test** | Mean per-sample accuracy diff | p < 0.001 |
| **McNemar's** | Discordant pair asymmetry | p < 0.001 |
| **Stuart-Maxwell** | 3-class marginal shift (paired) | p < 0.001 |

. . .

### Why Stuart-Maxwell?

- McNemar's is binary — loses inter-class shift info
- Stuart-Maxwell: full k×k confusion matrix, χ² with k−1 df
- Detects misclassification redistributions per-class F1 misses

### Calibration: Bootstrap CI
Variant 2 ECE **[0.055, 0.076]** vs Base **[0.098, 0.127]** — no overlap

::: notes
Slide 8 of 15 (16:00–18:00). Stuart-Maxwell is the standard for paired nominal data with >2 categories. Common in clinical trials.
:::

---

# Part IV: Demo & Technical Depth {data-background-color="#00B4D8"}

Slides 9–11 · 18:00–23:00

---

## Backend Demonstration Flow {data-background-color="#1a1a2e"}

### 7-Step End-to-End

1. **Ingest** — Upload → SHA-256 + metadata → `temp/` → PostgreSQL
2. **Label & Promote** — Assign `happy` → `POST /api/v1/media/promote` → `train/happy/`
3. **Class Balance** — Dashboard: 1:1:1 ratio, readiness indicator
4. **Train** — `train_efficientnet.py` → frozen 5 ep → unfreeze → MLflow
5. **Evaluate** — Test inference → Gate A → confusion matrix → pass/fail
6. **Deploy** — ONNX → SCP → TensorRT → DeepStream → Gate B (or rollback)
7. **Respond** — Camera → emotion → LLM → gesture → Reachy Mini (< 200ms)

> Every step produces a **logged, traceable event** with correlation ID.

::: notes
Slide 9 of 15 (18:00–20:00). If live: Streamlit on 10.0.4.140, Swagger on 10.0.4.130:8001/docs, Jetson on 10.0.4.150.
:::

---

## API Lifecycle: Promotion Routing {data-background-color="#1a1a2e"}

```
POST /api/v1/media/promote
Headers: X-Correlation-ID, Idempotency-Key
Body: { video_id, target_label, dry_run? }
```

| Phase | Action |
|---|---|
| **Validation** | 3-class policy, existence, status, `chk_split_label` |
| **Dry Run** | Preview source/target path, constraint violations |
| **Execution** | Atomic: move file + update PG + rebuild manifest |
| **Response** | New path, class counts, balance, correlation ID |
| **Error** | `PromotionValidationError` — constraint, expected, actual |
| **Legacy** | HTTP 410 + canonical URL + migration guide |

> **Fail-fast** · **Atomic transitions** · **Full traceability**

::: notes
Slide 10 of 15 (20:00–21:30). Dry-run from IaC (Terraform plan). Idempotency from Stripe API design.
:::

---

## Emotion → LLM → Gesture Pipeline {data-background-color="#1a1a2e"}

| Stage | Component | Output |
|---|---|---|
| 1 | DeepStream + TensorRT | Classification + confidence |
| 2 | Confidence hedging | Graduated LLM prompt |
| 3 | LM Studio (local) | Empathetic text + `[GESTURE]` |
| 4 | Reachy Mini (gRPC) | Physical motor sequence |

### 5-Tier Gesture Modulation

| Tier | Confidence | Expressiveness |
|---|---|---|
| 5 | 0.90–1.00 | Full — bold wave, wide arms |
| 4 | 0.75–0.90 | High — standard wave, nod |
| 3 | 0.60–0.75 | Medium — subtle nod |
| 2 | 0.45–0.60 | Low — minimal acknowledgment |
| 1 | 0.00–0.45 | Minimal — attentive posture |

> **Chain of Responsibility + Strategy** — behavior proportional to certainty.

::: notes
Slide 11 of 15 (21:30–23:00). Reactor pattern in asyncio. Priority queue for urgent emotional responses.
:::

---

# Part V: Risk, ROI & Competency {data-background-color="#1a1a2e"}

Slides 12–15 · 23:00–30:00

---

## Risk Analysis & Mitigation {data-background-color="#1a1a2e"}

| # | Risk | Mitigation | Residual |
|---|---|---|---|
| 1 | Model degradation | Gate C drift, auto-retrain, rollback | Low |
| 2 | Video exfiltration | Local-first, no outbound, TTL, firewall | Very Low |
| 3 | Edge exhaustion | Gate B limits, B0 edge-optimized | Low |
| 4 | Mislabeling | 3-class simplicity, Reconciler, dry-run | Moderate |
| 5 | n8n SPOF | systemd restart, stateless agents, PG checkpoints | Moderate |

> **Managed and measurable** — gate structure provides automated enforcement.

::: notes
Slide 12 of 15 (23:00–25:00). Risk register maps to gate structure. Stateless agents = fast recovery.
:::

---

## ROI & Vertical Extensibility {data-background-color="#1a1a2e"}

| Dimension | Detail |
|---|---|
| **Dev Velocity** | New agent: 2–4 hrs + 1–2 days (vs 1–2 wks monolithic) |
| **Cost Avoidance** | AWS ~$2–4K/mo vs on-prem ~$300–500/mo. Breakeven < 3 mo. |
| **Extensibility** | Same pattern for any classification task |

### Two Verticals

- **CareFlow** — Healthcare companion ops, HIPAA-adjacent
- **SecureFlow** — Cybersecurity ops, SOC 2-aligned

### Scaling

- **Horizontal:** More Jetson nodes · **Vertical:** B0 → B2
- **Organizational:** Version-controlled workflows — fork and adapt

::: notes
Slide 13 of 15 (25:00–27:00). CareFlow emerald #10B981, SecureFlow amber #F59E0B. Both share 5-node infra and 8-step pattern.
:::

---

## Competency Proof: Solutions Architect {data-background-color="#1a1a2e"}

| # | Domain | Evidence |
|---|---|---|
| 1 | **System Design** | 3 nodes, 4 languages, 6 domains |
| 2 | **ML Engineering** | HSEmotion transfer, two-phase, calibration, gates |
| 3 | **API Design** | 11 routers, correlation, idempotency, dry-run |
| 4 | **DevOps / MLOps** | MLflow, n8n, systemd, Alembic, Prometheus |
| 5 | **Edge Deployment** | ONNX → TRT → DeepStream → Jetson |
| 6 | **Privacy & Governance** | Local-first, TTL, GDPR, gate controls |
| 7 | **HRI** | Emotion→gesture, confidence modulation, gRPC |

> Integrating seven specialties into a coherent system defines a **solutions architect**.

::: notes
Slide 14 of 15 (27:00–29:00). Each domain implemented with production patterns, not prototypes.
:::

---

## Summary & Commitments {data-background-color="#1a1a2e"}

### What You've Seen

1. **Governed, local-first emotion intelligence** — video in, robot behavior out
2. **Ten agents** with bounded autonomy and automated gates
3. **Statistical evidence** — paired t-tests, McNemar's, Stuart-Maxwell
4. **Complete operational stack** — ingestion → deployment → gesture
5. **Enterprise governance** — correlation IDs, idempotency, three gates

### 30-Day Commitments

- Gate C monitoring dashboard operational
- Second-vertical prototype (CareFlow or SecureFlow)
- EfficientNet-B0 vs B2 benchmark on Jetson

### Thank You {data-background-color="#7B2FF7"}

Live demo · Code review · Domain adaptation — available for all three.

::: notes
Slide 15 of 15 (29:00–30:00). End at 30:00. If ahead, expand demo or stats. If behind, compress ROI.
:::
