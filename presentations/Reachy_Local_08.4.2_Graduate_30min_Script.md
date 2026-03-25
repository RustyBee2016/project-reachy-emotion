# Reachy_Local_08.4.2 — Graduate-Level Presentation Script (30 Minutes)

**Audience:** Business managers, technical leadership, graduate-level technologists  
**Presenter:** Rusty (Project Architect)  
**Date:** 2026-03-25  
**Objective:** Deliver a comprehensive briefing combining business framing, architectural rationale, statistical evidence, operational governance, and technical depth — at a level appropriate for graduate coursework, consulting engagements, or senior technical review.

**Format:** Slide-by-slide speaking script with timing cues, transitions, audience callouts, and presenter notes.

---

# 30-Minute Delivery Script (Timeboxed)

- **00:00–02:00** Slide 1: Mission, outcome, and framing
- **02:00–04:00** Slide 2: Business value and strategic alignment
- **04:00–06:00** Slide 3: Case-base scope and maturity evidence
- **06:00–08:30** Slide 4: End-to-end architecture walkthrough
- **08:30–11:00** Slide 5: Agentic operating model (deep dive)
- **11:00–13:30** Slide 6: Governance, quality gates, and compliance
- **13:30–16:00** Slide 7: Model performance trendline and interpretation
- **16:00–18:00** Slide 8: Statistical rigor and methodological depth
- **18:00–20:30** Slide 9: Backend demonstration plan
- **20:30–23:00** Slides 10–11: Technical control-flow walkthrough
- **23:00–25:00** Slide 12: Risk analysis and mitigation framework
- **25:00–27:00** Slide 13: ROI, program implications, and scaling
- **27:00–29:00** Slide 14: Competency proof (consultant/architect)
- **29:00–30:00** Slide 15: Close, ask, and commitments

---

# Part I — Executive Framing (Slides 1–3)

---

## Slide 1 (00:00–02:00) — Title & Outcome Statement

### Script

"Thank you for the time today. I want to set the framing clearly before we go into detail.

This project — Reachy_Local_08.4.2 — is a **local-first emotion intelligence platform** designed for Reachy Mini companion robots. It takes short video clips, classifies the emotional state of the person in the frame, and uses that classification to drive real-time empathetic behavior on a physical robot.

But that description undersells what we actually built. Let me reframe it.

This is not a model demo. This is not a Jupyter notebook with a confusion matrix. This is a **governed decision system** — a production-grade pipeline that includes:
- Explicit quality gates that must pass before any model is exported or deployed.
- Privacy controls that ensure no raw video ever leaves the local network.
- Staged deployment with rollback logic — shadow, canary, rollout — with human approval at each gate.
- Full audit lineage from the moment a video enters the system to the moment a robot raises its arm in response.

The three-class emotion taxonomy — `happy`, `sad`, `neutral` — was chosen deliberately. It's narrow enough to be tractable with limited training data, broad enough to drive meaningful behavioral differentiation, and simple enough to explain to non-technical stakeholders. That's an intentional design choice, not a limitation.

**The outcome of this project is not a trained model. The outcome is a deployable, auditable, privacy-first operational capability** that can be placed into a real environment — a clinic lobby, a care facility, a research lab — and trusted to behave predictably."

### Presenter Note
Pause here. Make eye contact. This is the thesis statement. Everything that follows supports this claim.

### Transition
"Let me now frame why this matters for the business — and why the timing is right."

---

## Slide 2 (02:00–04:00) — Why the Business Should Care

### Script

"There are four business levers this platform addresses directly.

**First: engagement.** Emotion-aware interactions create qualitatively different user experiences. When a robot can detect that someone is distressed and modulate its response — softer gestures, empathetic language, reduced assertiveness — that's not a novelty feature. That's a UX differentiator in healthcare, education, and assisted living. The literature on affective computing consistently shows that perceived empathy increases trust and willingness to interact, even with non-human agents.

**Second: operational risk.** Every ML system carries deployment risk. The standard failure mode is: a model gets trained, someone copies it to production, and there's no gate, no rollback, and no audit trail. This platform inverts that pattern. Gate A enforces performance and calibration thresholds in code. Gate B validates latency and resource usage on the edge device. Gate C monitors post-deployment drift. If any gate fails, deployment halts automatically and the prior engine is restored. For a business manager, that means your exposure to a bad model reaching users is bounded and measurable.

**Third: compliance.** This is a local-first system by design. No video leaves the LAN. There's a TTL-based retention policy that auto-purges temporary media. Every promotion, every label, every deployment event is logged with timestamps and checksums. That posture maps directly onto GDPR data minimization principles and institutional review requirements. We don't have to retrofit compliance — it's baked into the architecture.

**Fourth: iteration speed.** The ML pipeline is fully reproducible. Each training run gets a unique run ID, a dataset hash, and all artifacts are tracked in MLflow. The agent orchestration layer — built on n8n — lets us rewire workflows without code changes. That means the time from 'we have new labeled data' to 'we have a validated model candidate' is hours, not weeks.

Taken together, these four levers support what enterprise buyers actually care about: **reliability, observability, auditability, and speed**."

### Audience Callout
- **For managers:** This is about reducing the risk of AI deployment while maintaining iteration velocity.
- **For technologists:** This is about building the operational envelope around the model, not just the model itself.

### Transition
"Now let me show you the evidence that this system is mature — not just a concept."

---

## Slide 3 (04:00–06:00) — Case Base Scope Analyzed

### Script

"One of the first things I do when evaluating a system's maturity is measure its footprint. Not lines of code — that's a vanity metric — but functional coverage across concerns.

Here's what the repository contains, excluding virtual environments and generated artifacts:

- **1003 tracked files total.**
- **408 Markdown and design documents** — requirements, decision records, runbooks, session handoffs, curriculum materials. This is not a codebase that lives in someone's head. The design rationale is externalized and versioned.
- **222 Python implementation files** spanning the full stack.
- **50 JSON artifacts and configuration files** — n8n workflow definitions, MLflow configs, gate threshold specs.
- **24 shell automation scripts** — service startup, SSL cert generation, test runners, deployment helpers.

More importantly, let's look at where those Python files live:

- **53 files in `apps/api`** — the FastAPI backend handling media operations, promotion routing, training triggers, health checks, WebSocket cues, and observability endpoints.
- **21 files in `trainer`** — the ML training and evaluation pipeline, including the EfficientNet-B0 fine-tuning workflow, dataset preparation, frame extraction, and gate validation logic.
- **23 files in `apps/web`** — the Streamlit-based operator UI for labeling, curation, dashboard visualization, and promotion workflows.
- **8 files in `apps/reachy`** — gesture control, emotion-to-gesture mapping, cue handling, and the gesture modulator that scales expressiveness based on confidence.
- **5 files in `stats/scripts`** — statistical validation scripts for paired testing, calibration analysis, and report generation.

This distribution matters. It tells you this is a **cross-cutting system** — not a model with a wrapper. It spans data operations, ML operations, API design, edge deployment, and physical robotics. That breadth is what separates a research prototype from a deployable platform."

### Presenter Note
If presenting to a graduate audience, note that functional decomposition by directory is a lightweight architecture recovery technique — it reveals actual system boundaries faster than reading documentation.

### Transition
"Now let me show you the architecture itself — in one picture."

---

# Part II — Architecture and Operations (Slides 4–6)

---

## Slide 4 (06:00–08:30) — End-to-End Architecture in One Picture

### Script

"Here's the complete system flow. I'll walk through each layer.

```
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

**Top layer: operators and the web UI.** Human operators interact through a Streamlit dashboard behind Nginx. They upload or review videos, assign labels, approve promotions, and monitor system health. The UI is on Ubuntu 2 (10.0.4.140) and communicates with the API on Ubuntu 1 (10.0.4.130).

**Middle layer: the FastAPI gateway.** This is the coordination spine. It handles media ingestion, metadata persistence to PostgreSQL, filesystem operations, promotion routing with correlation IDs, training triggers, and WebSocket-based cue delivery. It also serves health, observability, and legacy compatibility endpoints.

**Data layer: PostgreSQL + filesystem manifests.** PostgreSQL stores metadata, promotion logs, checksums, and evaluation results. The filesystem stores actual video files in a structured hierarchy — `temp/`, `train/<label>/`, `test/`, `thumbs/`, and `manifests/`. Reconciliation ensures these two sources of truth stay synchronized.

**ML layer: the training orchestrator.** When dataset balance and size thresholds are met, training kicks off using EfficientNet-B0 pre-trained on VGGFace2 + AffectNet via the HSEmotion library. Training uses a two-phase approach: frozen backbone for five epochs, then selective unfreezing of the final blocks. Mixed precision, mixup augmentation, and cosine learning rate scheduling are all configured. Every run is tracked in MLflow with a dataset hash for reproducibility.

**Deployment layer: ONNX to TensorRT.** Once Gate A passes, the model is exported to ONNX, transferred to the Jetson Xavier NX (10.0.4.150) via SCP, converted to a TensorRT engine with FP16 precision, and loaded into the DeepStream inference pipeline. Gate B validates runtime performance — FPS ≥ 25, latency p50 ≤ 120ms, GPU memory ≤ 2.5 GB.

**Output layer: emotion → LLM → gesture.** Detected emotions feed into an LLM prompt tailored with confidence scores. The LLM response is parsed for gesture cues, which are mapped to physical gestures on Reachy Mini via gRPC. A 5-tier gesture modulator scales expressiveness based on the model's confidence — high confidence produces bold gestures; low confidence produces subtle acknowledgments.

**Cross-cutting concerns: observability and privacy.** Prometheus metrics, Grafana dashboards, structured JSONL logging, and a privacy agent that enforces TTL-based purges and access controls.

The key architectural insight is that **these layers are connected by explicit event contracts, not implicit coupling**. Each agent emits typed events that downstream agents consume. That's what makes the system testable, auditable, and replaceable at any layer."

### Audience Callout
- **For managers:** Each box in this diagram has a named owner (an agent), a defined contract, and a failure mode that doesn't cascade.
- **For technologists:** This is an event-driven microservice architecture adapted for ML operations on a LAN — no cloud, no message broker, just n8n orchestration and HTTP/WebSocket contracts.

### Transition
"Let me go deeper into the agent model that powers this."

---

## Slide 5 (08:30–11:00) — Agentic Operating Model (10+1 Agents)

### Script

"The system is operated by ten cooperating agents plus an optional generation balancer. All orchestration runs in n8n on Ubuntu 1. Let me walk through each agent's role and why the boundaries are drawn where they are.

**Agent 1 — Ingest Agent.** Receives new videos, computes SHA-256 checksums, extracts metadata (duration, FPS, resolution), generates thumbnails, and stores everything in `/videos/temp/`. Emits `ingest.completed`. This agent is the only entry point for new media — that's an intentional chokepoint for auditability.

**Agent 2 — Labeling Agent.** Manages human-assisted classification. Enforces the 3-class policy. Stages labeled clips from `temp/` to `train/<label>/`. Maintains per-class counts and balance status. Coordinates with the database to enforce the `chk_split_label` constraint. Every label event is logged with timestamp and checksum.

**Agent 3 — Promotion / Curation Agent.** Controls movement between filesystem stages using the canonical `POST /api/v1/media/promote` endpoint. Orchestrates per-run frame extraction and train/valid splitting via `DatasetPreparer`. Verifies the `label IS NULL` policy for test outputs. This agent owns the data supply chain.

**Agent 4 — Reconciler / Audit Agent.** Ensures filesystem and database consistency. Recomputes checksums, detects orphans and duplicates, and rebuilds manifests when drift is found. Emits reconciliation reports to Prometheus. This is the system's immune system.

**Agent 5 — Training Orchestrator.** Triggers EfficientNet-B0 fine-tuning when balance and size thresholds are met. Manages the two-phase training protocol, mixed precision, MLflow tracking, and Gate A validation. Exports to ONNX on success.

**Agent 6 — Evaluation Agent.** Runs inference on the test set, computes accuracy, F1 (macro + per-class), balanced accuracy, ECE, and Brier score. Generates confusion matrices and evaluation reports. Validates Gate A requirements and emits pass/fail.

**Agent 7 — Deployment Agent.** Manages the ONNX → TensorRT → Jetson pipeline. Backs up existing engines, converts with FP16, updates DeepStream configuration, validates Gate B (FPS, latency, GPU memory), and supports automatic rollback on failure.

**Agent 8 — Privacy / Retention Agent.** Auto-purges temporary media past TTL. Denies unauthorized access to raw video. Logs all purge events. This agent enforces the local-first privacy guarantee.

**Agent 9 — Observability / Telemetry Agent.** Aggregates metrics from all agents: queue depth, task latency, success rate, dataset balance, model drift. Publishes to Prometheus and Grafana. Raises alerts when error budgets are exceeded.

**Agent 10 — Reachy Gesture Agent.** Receives gesture cues via WebSocket, parses gesture keywords from LLM responses, maps emotions to default gestures, and executes sequences on Reachy Mini via gRPC. Supports simulation mode for testing without the physical robot.

**Optional — Generation Balancer.** Monitors per-class ratios and biases synthetic video generation to maintain 1:1:1 balance. Acts as a lightweight helper to Agents 2 and 3.

The design principle here is **bounded autonomy**: each agent can act within its scope without permission, but any action that crosses a boundary — promotion, deployment, purge — requires either an explicit event from an upstream agent or human approval. This is the same pattern used in enterprise service mesh design, adapted for ML operations."

### Presenter Note
Graduate audiences will recognize this as a variant of the microkernel or actor-model pattern. The key distinction from a standard microservice architecture is that **n8n acts as the orchestration bus** rather than a distributed message broker, which simplifies operations at the cost of horizontal scalability — an appropriate tradeoff for a LAN-bound system.

### Transition
"Those agents operate under explicit governance rules. Let me show you the gate structure."

---

## Slide 6 (11:00–13:30) — Quality Gates and Governance

### Script

"Governance in this system is not a policy document. It's code.

**Gate A — Model Quality (enforced before ONNX export):**
- Macro F1 ≥ 0.84 — ensures balanced predictive quality across all three classes. We use macro F1 rather than accuracy because accuracy can be inflated by class imbalance.
- Balanced Accuracy ≥ 0.85 — a secondary guard against class-skewed performance.
- Per-class F1 ≥ 0.75, with a hard floor of 0.70 — prevents any single class from falling below a usable threshold.
- ECE ≤ 0.08 — Expected Calibration Error. This ensures the model's confidence scores are trustworthy. A model that says '90% happy' should be correct about 90% of the time when it says that. This matters because downstream behavior — gesture intensity, LLM prompt modulation — depends on confidence being meaningful, not just high.
- Brier ≤ 0.16 — a proper scoring rule that penalizes both miscalibration and poor discrimination. It's the mean squared error between predicted probabilities and actual outcomes.

**Gate B — Runtime Performance (enforced on Jetson after TensorRT conversion):**
- FPS ≥ 25 — real-time responsiveness for human interaction.
- Latency p50 ≤ 120ms — the median inference latency must stay under human perception thresholds.
- GPU memory ≤ 2.5 GB — respects the Jetson Xavier NX's shared memory architecture.

**Gate C — Post-Deployment Monitoring (continuous):**
- Drift detection, confidence distribution monitoring, and user-outcome KPIs.

Beyond the gates, there are structural governance mechanisms:

- **Correlation IDs.** Every promotion request receives or resolves an `X-Correlation-ID` header. That ID follows the artifact through training, evaluation, deployment, and telemetry. You can trace any model engine back to the exact promotion event, dataset hash, and training run that produced it.

- **Deprecated endpoint management.** Legacy endpoints like `/api/v1/promote/stage` are retained as shims that return structured error responses with migration guidance. They're not silently removed — they're explicitly deprecated with warning headers and configurable toggle support. This is controlled migration, not breaking change.

- **Instruction priority stack.** When there's a conflict between automation and policy, the system follows a defined priority: safety/privacy/compliance first, then consistency with UI requirements, then maintainer instructions. On uncertainty, agents fail closed and escalate to the human owner.

This governance model is what makes the system **enterprise-safe**. You can hand this to an auditor and they can trace any decision from input to output."

### Audience Callout
- **For managers:** Gates are automatic. No one can bypass them without changing code, and code changes require version control.
- **For technologists:** ECE and Brier are proper scoring rules — they penalize miscalibration in ways that accuracy and F1 cannot. If you're building human-facing AI, calibration is non-negotiable.

### Transition
"Now let me show you the model performance evidence."

---

# Part III — Evidence and Statistical Rigor (Slides 7–8)

---

## Slide 7 (13:30–16:00) — Statistical Evidence: Model Trend Across Variants

### Script

"Here's the Gate A dashboard showing three model variants in progression:

| Variant | Accuracy | Macro F1 | Balanced Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| Base | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| Variant 1 | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| Variant 2 | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

Let me interpret each column.

**Accuracy** improved by 11.72 points from Base to Variant 2. That's a meaningful jump, but accuracy alone is insufficient for a 3-class problem where class balance matters. That's why we also track macro F1 and balanced accuracy.

**Macro F1** improved by 11.78 points. Macro F1 computes F1 per class and then averages — so a model that's excellent on `happy` but poor on `sad` will be penalized. The fact that macro F1 tracks closely with accuracy tells us the improvement is balanced across classes, not skewed.

**Balanced Accuracy** improved by 12.05 points. This is the average of per-class recall. At 0.9285, Variant 2 correctly identifies each emotion class roughly 93% of the time, balanced across classes.

**ECE** dropped by 4.70 points — from 0.1120 to 0.0650. This is the critical one for our application. ECE bins predictions by confidence, computes the gap between average confidence and average accuracy in each bin, and takes a weighted average. An ECE of 0.065 means the model's confidence is trustworthy to within about 6.5 percentage points. For a gesture modulator that scales response intensity based on confidence, this is the metric that determines whether the robot's behavior is appropriate or erratic.

**Brier score** dropped by 6.60 points — from 0.1580 to 0.0920. The Brier score is a proper scoring rule that combines discrimination (can the model tell classes apart?) with calibration (are the probabilities accurate?). A Brier score below 0.10 is excellent for a 3-class problem.

Now, the critical question a graduate-level reviewer should ask: **are these improvements real, or are they artifacts of sampling noise?** That's what the next slide addresses."

### Presenter Note
If the audience includes statisticians, emphasize that ECE is computed with 10 equal-width bins and that Brier is the multiclass extension (mean of per-class Brier scores). Mention that both are decomposable into calibration and resolution components if pressed.

### Transition
"Let me show you the statistical validation."

---

## Slide 8 (16:00–18:00) — Statistical Depth Beyond a Single Score

### Script

"We didn't just compare summary metrics. We ran formal statistical tests to validate the improvement profile.

**Per-class paired t-tests.** For each of the 8 emotion classes in the original HSEmotion taxonomy, we ran paired t-tests comparing Base vs Variant 2 performance. After applying Benjamini-Hochberg correction for multiple comparisons, **all 8 tests were significant.** This means the improvement is not concentrated in one or two classes — it's systemic.

But here's the nuance: **7 classes improved, and 1 degraded.** The `happiness` class showed a small but statistically significant decrease. This is actually a sign of healthy model development — it means we're not blindly inflating all scores. The model redistributed some of its capacity, and the tradeoff was favorable overall. A reviewer who sees uniform improvement across every metric should be suspicious. A reviewer who sees a nuanced improvement profile with one known tradeoff should be reassured.

**Multivariate paired analysis — Stuart-Maxwell test.** This tests whether the overall pattern of class assignments shifted in a way that's statistically significant at the marginal level. The result: **p = 0.148**, which is not significant at alpha = 0.05.

The interpretation: the global distribution of predictions is stable — the model isn't systematically shifting its class preferences — even though individual classes show significant improvement. This is exactly the profile you want: **class-level improvements without uncontrolled distributional shift.**

For graduate-level context: the Stuart-Maxwell test is the multivariate extension of McNemar's test. It evaluates marginal homogeneity in a square contingency table. A non-significant result tells us that the marginal distributions (total predicted counts per class) are comparable between models, which means we're not seeing a model that 'learned to predict happy more often' — we're seeing a model that 'learned to predict all classes more accurately.'

This combination — significant per-class improvement with non-significant marginal shift — is the gold standard for demonstrating controlled model improvement."

### Audience Callout
- **For managers:** The improvement is real, tested, and the tradeoffs are known and documented.
- **For technologists:** BH correction controls the false discovery rate. Stuart-Maxwell tests marginal homogeneity. Together, they provide a rigorous validation profile.

### Transition
"Now let me show you how we'd demonstrate this system live."

---

# Part IV — Demonstration and Technical Depth (Slides 9–11)

---

## Slide 9 (18:00–20:30) — Backend Demonstration Plan

### Script

"If we were running this as a live demo, here's the exact path we'd trace:

**Step 1: Promote validated samples.** We'd use the canonical endpoint: `POST /api/v1/media/promote`. The request includes a video ID, an emotion label, and receives a correlation ID in the response. That promotion event is logged in PostgreSQL with the SHA-256 checksum, the target directory, and a timestamp.

**Step 2: Trigger training.** Once the dataset meets balance and size thresholds — a minimum number of samples per class with 1:1:1 ratio — the Training Orchestrator launches. We'd observe the run ID appear in MLflow, the training logs streaming with per-epoch loss and metrics, and the two-phase progression: frozen backbone epochs followed by selective unfreezing.

**Step 3: Review Gate A output.** After training completes, the evaluation agent runs automatically. The Gate A JSON output in `stats/results/` contains every metric, the pass/fail verdict, per-class breakdowns, and the confusion matrix. We'd open this artifact and verify the thresholds.

**Step 4: Dashboard comparison.** The operator dashboard shows a side-by-side view of base vs tuned variant metrics — accuracy, F1, calibration curves. This is where a business stakeholder sees the improvement in visual form.

**Step 5: Trigger the emotion→LLM→gesture chain.** We'd send a simulated emotion event — say, `sad` with confidence 0.87 — into the pipeline. The LLM receives an emotion-conditioned prompt with the confidence score. It generates a response that includes gesture cues like `[EMPATHY]` or `[COMFORT]`. The gesture agent parses those cues, maps them to physical movements, and the modulator scales intensity based on the 0.87 confidence — tier 4 out of 5, so nearly full expressiveness.

**Demo success criterion:** one traceable correlation path from video ingestion to robot action. Not a curated happy path — a real, auditable chain."

### Transition
"For the technical reviewers, let me walk through two specific code architectures."

---

## Slide 10 (20:30–21:45) — Technical Walkthrough: API Control Flow

### Script

"Let's look at how the API actually boots and how promotion routing works.

**API boot lifecycle** — `apps/api/app/main.py`:

1. Load environment variables and configuration. This includes database URLs, filesystem paths, feature flags for legacy compatibility, and port bindings.
2. Create a shared `httpx.AsyncClient` — this is the outbound HTTP client used for inter-service communication. It's shared to manage connection pooling and lifecycle.
3. Start the thumbnail watcher as a background service. This watches `/videos/temp/` for new files and generates thumbnails asynchronously.
4. Register routers: health check, media v1 operations, promotion, ingest, training triggers, observability, WebSocket cue delivery, and optionally, legacy compatibility routers.
5. On shutdown: close the HTTP client, stop the watcher, and release database connections.

This lifecycle pattern — explicit initialization, shared resources, graceful shutdown — is standard for production FastAPI applications but often missing from research prototypes. It matters because leaked connections, zombie processes, and unclean shutdowns are the top three operational issues in deployed Python services.

**Promotion router** — `apps/api/app/routers/promote.py`:

Each incoming request resolves or creates an `X-Correlation-ID` header. If the client sends one, it's preserved; otherwise, a UUID is generated. That ID is passed to every downstream service call.

The router calls service methods — `stage_to_train`, `sample_split`, `reset_manifest` — and wraps them in structured exception handling. A validation error returns 422 with a correlation-aware detail payload. A conflict (e.g., duplicate promotion) returns 409. A bad request returns 400. Every error response includes the correlation ID so operators can trace failures through logs.

This is defensive API design. It assumes callers will make mistakes, and it provides enough context for those mistakes to be diagnosed without SSH access."

### Transition
"Now the real-time pipeline — the most architecturally interesting part."

---

## Slide 11 (21:45–23:00) — Technical Walkthrough: Emotion→LLM→Gesture Pipeline

### Script

"The orchestration module at `apps/pipeline/emotion_llm_gesture.py` is where emotion classification becomes physical robot behavior. Let me walk through the design decisions.

**Typed state payloads.** The pipeline uses Python dataclasses — `PipelineConfig`, `EmotionEvent`, `PipelineResult` — for all internal state. This means every object passing through the pipeline has a defined schema, is serializable, and is self-documenting. No dictionaries with magic keys.

**Finite-state control.** A `PipelineState` enum defines the valid states: `IDLE`, `PROCESSING`, `AWAITING_LLM`, `GESTURE_PENDING`, `COMPLETE`, `ERROR`. State transitions are explicit — you can draw the state machine on a whiteboard. This prevents the most common bug in async pipelines: acting on stale or inconsistent state.

**Composable collaborators.** The pipeline initializes:
- An LLM client (real or mock — so you can test without an LLM server)
- A gesture controller (Reachy SDK interface via gRPC)
- A gesture mapper (emotion → gesture mapping)
- A gesture modulator (confidence → expressiveness scaling)
- A confidence handler and temporal smoother

Each collaborator is injected, not hard-coded. That's dependency inversion — the pipeline doesn't know or care whether it's talking to a real robot or a simulation.

**Bounded async queue.** The pipeline accepts emotion events via a `asyncio.Queue` with a bounded size. If events arrive faster than they can be processed, the oldest are dropped rather than allowing unbounded memory growth. This is critical for a real-time system — you'd rather miss an emotion event than crash the pipeline with backpressure.

**Decoupled callbacks.** Downstream handling — sending the LLM response to the UI, triggering the gesture — is done via callbacks, not direct calls. This means the pipeline core doesn't need to know what happens after it produces a result. You can add logging, metrics, or additional handlers without modifying the pipeline.

This is **safe, testable, production-grade async design** for real-time robotics. It's the kind of architecture that survives first contact with reality — dropped connections, slow LLMs, robot hardware failures — without cascading."

### Presenter Note
If the audience includes software architects, note that this pattern is essentially the Reactor pattern with typed channels. It's the same approach used in ROS2 node design, adapted for Python asyncio.

### Transition
"Now let's talk about what could go wrong."

---

# Part V — Risk, ROI, and Competency (Slides 12–15)

---

## Slide 12 (23:00–25:00) — Risk Analysis and Mitigation

### Script

"Every responsible system presentation should include a candid risk assessment. Here's ours.

**Key strengths to anchor on:**
- Local-first privacy posture eliminates an entire category of data exposure risk.
- Explicit gate checks prevent undertrained or miscalibrated models from reaching production.
- Rollback-aware deployment means a bad engine can be reverted in seconds.
- Event-driven audit trail means every decision is traceable.

**Residual risk 1: Calibration instability on small datasets.**
Gate A requires ECE ≤ 0.08, but calibration metrics are known to be noisy on small test sets. With 20 samples per class, the ECE estimate has high variance. The risk is that a model passes Gate A on one evaluation but would fail on a slightly different sample.

*Mitigation:* Increase the minimum test set size. Add bootstrap confidence intervals to Gate A reporting. Consider reporting a 95% CI for ECE rather than a point estimate.

**Residual risk 2: Synthetic vs real-world domain drift.**
The current training data includes synthetic videos generated by external APIs. Synthetic faces may have different texture, lighting, and motion characteristics than real-world interactions. A model that performs well on synthetic data may underperform on natural interactions.

*Mitigation:* Establish a real-world validation corpus. Run Gate A separately on synthetic and real-world subsets. Track drift metrics post-deployment using confidence distribution monitoring.

**Residual risk 3: Canary/rollout success criteria.**
Gate C — post-deployment monitoring — is specified but not yet fully operationalized. The criteria for progressing from canary to full rollout need sharper definition.

*Mitigation:* Define explicit canary graduation criteria: minimum observation period, maximum drift threshold, minimum interaction count. Implement automated rollback triggers based on confidence bucket anomalies.

The purpose of presenting risks is not to undermine confidence — it's to demonstrate **intellectual honesty and operational maturity.** A system with known risks and documented mitigations is safer than a system whose risks are unknown."

### Transition
"Given those risks, here's the ROI case."

---

## Slide 13 (25:00–27:00) — ROI and Program Implications

### Script

"Let me connect the technical architecture to program-level value.

**Faster release cycles.** The reproducible pipeline — dataset hashing, MLflow tracking, run-scoped artifacts — means that any training run can be reproduced, compared, and promoted without manual bookkeeping. The time from new data to validated model candidate is measured in hours. For a program manager, that means your team spends less time on configuration archaeology and more time on actual model improvement.

**Lower incident cost.** Gate A + Gate B + automatic rollback means the blast radius of a bad model is bounded. If a newly deployed engine degrades performance, the deployment agent reverts to the prior engine automatically. No pager, no war room, no manual intervention. The cost of a bad deployment drops from 'engineer-hours of firefighting' to 'one logged rollback event.'

**Higher trust with stakeholders.** Transparent metrics, audit trails, and governance mechanisms make the system legible to non-technical stakeholders. An executive can ask 'why did the robot behave that way?' and get a traceable answer: this emotion was detected with this confidence, this LLM prompt was sent, this gesture was executed. That traceability builds institutional trust.

**Team productivity.** The system is designed so that a single person — or a small team — can operate the full pipeline. Researchers focus on model architecture. Operators focus on data curation. Product teams focus on user experience. The platform handles the operational glue.

**Scaling path.** The architecture is LAN-bound today, but the agent contracts are protocol-independent. Moving to MQTT, gRPC, or a cloud-based orchestrator would require changing the transport layer, not the agent logic. The vertical adaptations we've already demonstrated — CareFlow for healthcare, SecureFlow for cybersecurity — prove that the same core platform serves different operational domains with different workflow logic, policy models, and operator dashboards.

**Program recommendation:** proceed to controlled canary rollout with explicit KPI guardrails. Define success criteria for canary graduation. Run parallel executive and technical demos to build buy-in across stakeholder groups."

### Transition
"Let me close by mapping all of this to a specific professional competency claim."

---

## Slide 14 (27:00–29:00) — Competency Proof: Consultant / Solutions Architect

### Script

"This project was designed, built, and operated by one person. Let me map what was demonstrated to the competency profile of a mid-level consultant or solutions architect.

**1. Business translation.** The ability to take a technical capability — emotion classification — and frame it as a decision-ready operational tool with KPIs, risk frameworks, and business levers. This is the core skill of consulting: translating technical possibility into business language.

**2. Systems architecture.** The ability to connect disparate concerns — UI, API, data pipeline, ML training, edge deployment, physical robotics — into a coherent, auditable system. This isn't about being an expert in each layer. It's about understanding the interfaces between layers and designing contracts that make the system maintainable.

**3. Governance design.** The ability to build compliance, privacy, quality gates, and migration strategies into the architecture — not as an afterthought, but as a first-class concern. Gate A, correlation IDs, deprecated endpoint management, TTL retention, and the instruction priority stack are all governance artifacts.

**4. Technical depth.** The ability to implement — not just design — asynchronous orchestration, model evaluation logic, calibration analysis, and deployment pathways. The code is not delegated; it's authored with production patterns (dependency injection, bounded queues, typed state, graceful shutdown).

**5. Change management.** The ability to manage system evolution without breaking existing consumers. Deprecation shims, reproducible run IDs, versioned artifacts, and operational dashboards all serve this purpose. A system that can't evolve safely is a system that will eventually be replaced rather than improved.

**6. Vertical adaptation.** The ability to take a horizontal platform and adapt it to specific market verticals — CareFlow for healthcare operations, SecureFlow for cybersecurity — with distinct workflow logic, policy models, and operator interfaces while preserving the shared architectural core.

Taken together, these six competencies map directly to what enterprise clients expect from a solutions architect: **someone who can translate business needs into governed, scalable, maintainable technical systems.**"

### Transition
"Final slide. The ask."

---

## Slide 15 (29:00–30:00) — Close & Ask

### Script

"Here's the decision I'm requesting:

**Approve the next-phase canary rollout plan with KPI guardrails.**

Specifically, in the next 30 days:

1. **Expand balanced test coverage.** Increase the minimum per-class count for Gate A evaluation. Add bootstrap confidence intervals to calibration metrics. Begin collecting real-world interaction clips to complement the synthetic training set.

2. **Formalize Gate B/C reporting dashboards.** Operationalize runtime performance monitoring on the Jetson. Define canary graduation criteria with explicit thresholds and observation periods.

3. **Run two executive demos.** One technical deep-dive for engineering leadership. One business-value narrative for program owners and stakeholders.

If we align on this plan, we move from validated prototype to operational deployment with full governance, known risks, and measurable success criteria.

Thank you. I'm happy to take questions."

---

# Appendix A — Extended Q&A Preparation

## Q1: Why both macro F1 and calibration metrics?
Macro F1 ensures class-balanced predictive quality — it catches models that sacrifice one class for another. ECE and Brier ensure the probability outputs are trustworthy for downstream decision-making. A model with high F1 but poor calibration would produce confident but wrong gesture modulation — the robot would act boldly when it should be uncertain.

## Q2: Why EfficientNet-B0 specifically?
EfficientNet-B0 offers the best accuracy-per-FLOP at the small end of the efficiency frontier. The HSEmotion pre-training on VGGFace2 + AffectNet provides face-specific features that transfer well to emotion classification. The B0 variant fits within the Jetson Xavier NX's memory and compute constraints while maintaining Gate A-passing accuracy.

## Q3: Why keep deprecated endpoints?
Controlled migration is a governance principle. Removing endpoints silently breaks external consumers (n8n workflows, UI clients, test scripts). Retaining them as shims with warning headers and structured error responses gives consumers time to migrate while providing clear guidance on the canonical replacement.

## Q4: Why queue-based async orchestration?
Real-time emotion events can burst — multiple frames may be classified in rapid succession. A bounded queue prevents unbounded memory growth and backpressure cascades. Callbacks decouple the pipeline from downstream consumers, making it testable in isolation. This is the standard pattern for real-time stream processing in resource-constrained environments.

## Q5: How does the gesture modulator work?
The modulator maps model confidence (0.0–1.0) to a 5-tier expressiveness scale. Tier 1 (confidence < 0.3): minimal acknowledgment. Tier 5 (confidence > 0.9): full expressive gesture. This prevents the robot from performing bold gestures when the model is uncertain, which would feel uncanny or inappropriate to the user.

## Q6: What happens if Gate A fails?
The model is not exported. No ONNX file is produced. The training run is logged in MLflow with a `GATE_A_FAIL` status, including the specific metrics that fell below threshold. The operator is notified via the dashboard. The prior model remains in production. This is the core safety mechanism.

## Q7: How do you handle the lack of a cloud infrastructure?
By design. Local-first is a feature, not a limitation. It eliminates cloud dependency, egress costs, latency variability, and data privacy concerns. The agent contracts are transport-agnostic — if a future deployment requires cloud orchestration, the agents can be re-wired to MQTT or gRPC without changing their internal logic.

## Q8: What's the difference between CareFlow and SecureFlow?
Same core platform. Different workflow logic (arrival detection vs anomaly detection), different policy models (empathy-first vs least-privilege), different operator dashboards, and different escalation chains. The architecture supports this because vertical-specific behavior is configured in the workflow layer (n8n), not hard-coded in the agent logic.
