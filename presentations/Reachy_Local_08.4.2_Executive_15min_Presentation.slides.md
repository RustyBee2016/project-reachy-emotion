# Reachy_Local_08.4.2 — Executive & Technical Briefing (15 minutes)

Format: Google Slides import outline (one slide per H2). Paste into Slides via File → Import Slides (or use any Markdown→Slides tool).

---

## Slide 1 — Title & Outcome Statement

### What this project is
- A **local-first emotion intelligence platform** for Reachy Mini robots.
- Converts short video clips into operational insight and real-time empathetic robot behavior.
- Built around a governed 3-class emotion model (`happy`, `sad`, `neutral`) with auditable promotion, evaluation, and deployment flow.

### Executive takeaway
- This is not a model demo; it is a **production-ready decision system** with quality gates, privacy controls, and staged deployment.

---

## Slide 2 — Why the Business Should Care

### Core business outcomes
1. **Better user engagement** through emotion-aware interactions.
2. **Lower operational risk** via explicit Gate A/B controls and rollback paths.
3. **Compliance readiness** through local-only data handling and retention enforcement.
4. **Faster iteration** through n8n-based agent orchestration and reproducible ML pipelines.

### Strategic fit
- Supports enterprise requirements for reliability, observability, and auditable change management.

---

## Slide 3 — Case Base Scope Analyzed

### Repository-wide scope (excluding virtual environment artifacts)
- **Total tracked files analyzed:** 1003
- **Markdown/design/process docs:** 408
- **Python implementation files:** 222
- **JSON artifacts/configuration:** 50
- **Shell automation scripts:** 24

### Functional coverage discovered
- API/backend services (`apps/api`): **53 Python files**
- ML training/evaluation (`trainer`): **21 Python files**
- Web/UI workflows (`apps/web`): **23 Python files**
- Gesture/robot control (`apps/reachy`): **8 Python files**
- Statistical validation scripts (`stats/scripts`): **5 Python files**

---

## Slide 4 — End-to-End Architecture in One Picture

```text
[Web UI / Operators]
       |
       v
[FastAPI Media + Gateway Layer] <--> [PostgreSQL + Filesystem Manifests]
       |
       +--> [Promotion/Curation + Reconciler + Audit]
       |
       +--> [Training Orchestrator (EfficientNet-B0 + MLflow + Gate A)]
       |
       +--> [Deployment Agent (ONNX -> TensorRT -> Jetson)]
       |
       +--> [Observability + Privacy/Retention]
       |
       v
[Emotion -> LLM -> Gesture Pipeline] --> [Reachy Mini]
```

### Why it matters
- Cross-domain integration: data ops + ML ops + edge deployment + embodied AI.

---

## Slide 5 — Agentic Operating Model (10+1 Agents)

### Orchestrated responsibilities
- Ingest, labeling, promotion, reconciliation, training, evaluation, deployment, privacy, telemetry, and gesture execution.
- Optional generation balancer enforces class equilibrium (1:1:1).

### Business assurance pattern
- Narrow responsibility per agent + explicit event contracts = lower incident blast radius and clearer ownership.

---

## Slide 6 — Quality Gates and Governance

### Gate A thresholds enforced in code
- Macro F1 >= 0.84
- Balanced Accuracy >= 0.85
- Per-class F1 >= 0.75 and floor >= 0.70
- ECE <= 0.08
- Brier <= 0.16

### Governance implementation highlights
- Correlation IDs on promotion routes for traceability.
- Deprecated endpoints retained with warning headers for controlled migration.
- Legacy support is explicitly toggleable in app configuration lifecycle.

---

## Slide 7 — Statistical Evidence: Model Trend Across Variants

### Gate A dashboard run progression

| Variant | Accuracy | Macro F1 | Balanced Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| Base | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| Variant 1 | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| Variant 2 | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

### Net improvement (Base -> Variant 2)
- Accuracy: **+11.72 points**
- Macro F1: **+11.78 points**
- Balanced Accuracy: **+12.05 points**
- ECE: **-4.70 points** (better calibration)
- Brier: **-6.60 points** (better probabilistic quality)

---

## Slide 8 — Statistical Depth Beyond a Single Score

### Paired statistical testing (demo study artifacts)
- **Per-class paired t-tests:** 8/8 classes significant after BH correction.
- **Directionality:** 7 improved, 1 degraded (`happiness`) indicating nuanced change, not blind uplift.

### Multivariate paired analysis
- **Stuart-Maxwell p = 0.148** (not significant at alpha=0.05).
- Interpretation: global marginal distribution shifts are controlled while class-level improvements can still be meaningful.

---

## Slide 9 — Backend Demonstration Plan (Live/Recorded)

### Demo flow (4 minutes inside the 15)
1. **Promote** validated samples using canonical endpoint (`POST /api/v1/media/promote`).
2. **Trigger training** with EfficientNet pipeline and observe run ID/artifact lifecycle.
3. **Review Gate A JSON** output in `stats/results`.
4. **Show dashboard comparison** between base and tuned variants.
5. **Trigger emotion->LLM->gesture event** and show response + gesture cue handling.

### Demo success criteria
- One traceable correlation path from ingestion to evaluation to robot action.

---

## Slide 10 — Technical Walkthrough for Rusty (Control Flow)

### A) API boot lifecycle (`apps/api/app/main.py`)
1. Load env + config.
2. Create shared `httpx.AsyncClient`.
3. Start thumbnail watcher background service.
4. Register current routers (health, media_v1, promote, ingest, training, observability, websocket cues, etc.).
5. Optionally include legacy router compatibility.
6. On shutdown: close HTTP client + stop watcher.

### B) Promotion router behavior (`apps/api/app/routers/promote.py`)
- Each request resolves/creates `X-Correlation-ID`.
- Calls service methods (`stage_to_train`, `sample_split`, `reset_manifest`).
- Uses structured exception handling to return 422/409/400 with correlation-aware detail payloads.

---

## Slide 11 — Technical Walkthrough for Rusty (Pipeline Syntax + Logic)

### Emotion->LLM->Gesture orchestrator (`apps/pipeline/emotion_llm_gesture.py`)
- Uses dataclasses (`PipelineConfig`, `EmotionEvent`, `PipelineResult`) for typed state payloads.
- Uses Enum (`PipelineState`) for explicit finite-state control.
- Initializes composable collaborators:
  - LLM client (real or mock)
  - Gesture controller + mapper + modulator
  - Confidence handler + temporal smoother
- Uses bounded `asyncio.Queue` to prevent unbounded load.
- Uses callbacks for decoupled downstream handling (response and gesture events).

### Why this is architecturally strong
- Clear separation of concerns and safe async boundaries for real-time robotics workflows.

---

## Slide 12 — Risk, Controls, and Residual Gaps

### Key strengths
- Local-first privacy posture.
- Explicit gate checks before export/deploy.
- Rollback-aware deployment design.
- Auditable event-driven operations.

### Residual risks to track
- Calibration instability in tiny-sample gate artifacts.
- Potential drift between synthetic and real-world interactions.
- Operational maturity of canary/rollout criteria in prolonged field usage.

### Proposed mitigations
- Increase balanced real-world validation set.
- Add weekly drift report and confidence bucket alarms.
- Add post-deployment user-outcome KPIs (engagement, de-escalation rates).

---

## Slide 13 — ROI and Program-Level Implications

### Value realization levers
- **Faster release cycles:** reusable pipeline and run-scoped artifacts.
- **Lower incident cost:** deterministic gates + rollback path.
- **Higher trust:** transparent metrics + quality controls.
- **Team productivity:** one system supports researchers, ops, and product teams.

### Program recommendation
- Continue to controlled canary with explicit success metrics per business segment.

---

## Slide 14 — Why This Demonstrates Mid-Level Consultant / Solutions Architect Skill

### Competency mapping
1. **Business translation:** Converts emotion ML into decision-ready KPIs and risk frameworks.
2. **Systems architecture:** Connects UI, API, data, ML training, observability, and edge deployment.
3. **Governance design:** Enforces privacy, retention, quality gates, and compatibility migration.
4. **Technical depth:** Implements asynchronous orchestration, model evaluation logic, and deployment pathways.
5. **Change management:** Uses deprecation shims, reproducible runs, and operational dashboards for stakeholder alignment.

### Executive summary statement
- Rusty demonstrates the profile of a **mid-level consultant/solutions architect** by combining technical implementation with governance, operational design, and measurable business outcomes.

---

## Slide 15 — Close & Ask

### Decision requested
- Approve next-phase canary rollout plan with KPI guardrails.

### Immediate next 30 days
- Expand test balance coverage.
- Formalize Gate B/C reporting dashboards.
- Run two executive demos: one technical deep-dive, one business-value narrative.

---

## Appendix A — 15-Minute Delivery Script (Timeboxed)

- **00:00-01:00** Slide 1: mission and outcome
- **01:00-02:00** Slide 2: why business value now
- **02:00-03:00** Slide 3: case-base evidence of maturity
- **03:00-04:00** Slide 4: architecture overview
- **04:00-05:00** Slide 5: agent responsibilities
- **05:00-06:00** Slide 6: governance and quality gates
- **06:00-07:30** Slide 7: hard metrics and trendline
- **07:30-08:30** Slide 8: statistical rigor
- **08:30-09:30** Slide 9: demo plan and success criteria
- **09:30-11:30** Slides 10-11: technical control flow walkthrough for Rusty
- **11:30-12:30** Slide 12: risk and mitigation
- **12:30-13:30** Slide 13: ROI implications
- **13:30-14:30** Slide 14: competency proof (consultant/architect)
- **14:30-15:00** Slide 15: ask and commitments

---

## Appendix B — Presenter Notes for Technical Q&A

### Q1: Why both macro F1 and calibration metrics?
- Macro F1 ensures class-balanced predictive quality.
- ECE/Brier ensure confidence scores are trustworthy for downstream behavior modulation.

### Q2: Why keep deprecated endpoints?
- Controlled migration avoids breaking external automations while steering traffic to canonical endpoints.

### Q3: Why queue-based async orchestration in the gesture pipeline?
- Real-time streams can burst; bounded queues and callbacks protect responsiveness and avoid uncontrolled backpressure.

### Q4: What proves this is enterprise-ready vs a notebook project?
- Reproducible run IDs, gate artifacts, migration strategy, and role-separated services show production system discipline.
