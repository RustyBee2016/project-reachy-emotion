# Reachy_Local_08.4.2 — Graduate-Level Presentation Script (30 Minutes)

**Audience:** Business managers, technical leadership, graduate-level technologists
**Presenter:** Russell Bray (Solutions Architect)
**Date:** 2026-03-25
**Objective:** Comprehensive briefing combining business framing, architectural rationale, statistical evidence, operational governance, and technical depth.

**Format:** Slide-by-slide speaking script with timing cues, transitions, audience callouts, and presenter notes.

---

## Timing Overview

| Part | Slides | Time | Focus |
|---|---|---|---|
| I — Executive Framing | 1–3 | 00:00–06:00 | Mission, value, maturity evidence |
| II — Architecture & Operations | 4–6 | 06:00–13:30 | Pipeline, agents, governance |
| III — Evidence & Statistical Rigor | 7–8 | 13:30–18:00 | Metrics, paired tests, interpretation |
| IV — Demo & Technical Depth | 9–11 | 18:00–23:00 | Demo plan, API walkthrough, pipeline design |
| V — Risk, ROI & Competency | 12–15 | 23:00–30:00 | Risk analysis, ROI, architect proof, close |

---

# Part I — Executive Framing (Slides 1–3, 00:00–06:00)

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

The three-class emotion taxonomy — `happy`, `sad`, `neutral` — was chosen deliberately. It is narrow enough to be tractable with limited training data, broad enough to drive meaningful behavioral differentiation, and simple enough to explain to non-technical stakeholders.

**The outcome of this project is not a trained model. The outcome is a deployable, auditable, privacy-first operational capability** that can be placed into a real environment — a clinic lobby, a care facility, a research lab — and trusted to behave predictably."

### Presenter Note
Pause here. Make eye contact. This is the thesis statement. Everything that follows supports this claim.

### Transition
"Let me now frame why this matters for the business — and why the timing is right."

---

## Slide 2 (02:00–04:00) — Why the Business Should Care

### Script

"There are four business levers this platform addresses directly.

**First: engagement.** Emotion-aware interactions create qualitatively different user experiences. When a robot can detect that someone is distressed and modulate its response — softer gestures, empathetic language, reduced assertiveness — that is a UX differentiator in healthcare, education, and assisted living. The literature on affective computing consistently shows that perceived empathy increases trust and willingness to interact, even with non-human agents.

**Second: operational risk.** Every ML system carries deployment risk. The standard failure mode is: a model gets trained, someone copies it to production, and there is no gate, no rollback, and no audit trail. This platform inverts that pattern. Gate A enforces performance and calibration thresholds in code. Gate B validates latency and resource usage on the edge device. Gate C monitors post-deployment drift. If any gate fails, deployment halts automatically and the prior engine is restored.

**Third: compliance.** This is a local-first system by design. No video leaves the LAN. There is a TTL-based retention policy that auto-purges temporary media. Every promotion, every label, every deployment event is logged with timestamps and checksums. That posture maps directly onto GDPR data minimization principles. We do not have to retrofit compliance — it is baked into the architecture.

**Fourth: iteration speed.** The ML pipeline is fully reproducible. Each training run gets a unique run ID, a dataset hash, and all artifacts are tracked in MLflow. The n8n orchestration layer lets us rewire workflows without code changes. The time from 'new labeled data' to 'validated model candidate' is hours, not weeks.

Taken together: **reliability, observability, auditability, and speed**."

### Audience Callout
- **For managers:** This is about reducing the risk of AI deployment while maintaining iteration velocity.
- **For technologists:** This is about building the operational envelope around the model, not just the model itself.

### Transition
"Now let me show you the evidence that this system is mature — not just a concept."

---

## Slide 3 (04:00–06:00) — Case-Base Scope and Maturity Evidence

### Script

"One of the first things I do when evaluating a system's maturity is measure its footprint — not lines of code, but functional coverage across concerns.

The repository contains (excluding venvs and generated artifacts):

- **1,003 tracked files total.**
- **408 Markdown and design documents** — requirements, decision records, runbooks, session handoffs, curriculum materials.
- **222 Python implementation files** spanning the full stack.
- **50 JSON artifacts** — n8n workflow definitions, MLflow configs, gate threshold specs.
- **24 shell automation scripts** — service startup, SSL cert generation, test runners, deployment helpers.

Where those Python files live matters:

- **53 files in `apps/api`** — FastAPI backend: media operations, promotion routing, training triggers, health checks, WebSocket cues, observability.
- **21 files in `trainer`** — ML pipeline: EfficientNet-B0 fine-tuning, dataset preparation, frame extraction, gate validation.
- **23 files in `apps/web`** — Streamlit operator UI: labeling, curation, dashboards, promotion workflows.
- **8 files in `apps/reachy`** — gesture control, emotion-to-gesture mapping, cue handling, gesture modulator.
- **5 files in `stats/scripts`** — statistical validation: paired testing, calibration analysis, report generation.

This distribution tells you this is a **cross-cutting system** — not a model with a wrapper. It spans data ops, ML ops, API design, edge deployment, and physical robotics. That breadth separates a research prototype from a deployable platform."

### Presenter Note
Functional decomposition by directory is a lightweight architecture recovery technique — it reveals actual system boundaries faster than reading documentation.

### Transition
"Now let me show you the architecture itself — in one picture."

---

# Part II — Architecture & Operations (Slides 4–6, 06:00–13:30)

---

## Slide 4 (06:00–08:30) — End-to-End Architecture

### Script

"Here is the complete system flow.

**Top layer: operators and the web UI.** Human operators interact through a Streamlit dashboard behind Nginx on Ubuntu 2 (10.0.4.140). They upload/review videos, assign labels, approve promotions, and monitor health. The UI communicates with the API on Ubuntu 1 (10.0.4.130).

**Middle layer: the FastAPI gateway.** The coordination spine. 11 routers handling media ingestion, metadata persistence to PostgreSQL, filesystem operations, promotion routing with correlation IDs, training triggers, and WebSocket-based cue delivery.

**Data layer: PostgreSQL plus filesystem manifests.** PostgreSQL 16 at `10.0.4.130:5432` stores metadata, promotion logs, checksums, and evaluation results. The filesystem stores video files in `temp/`, `train/<label>/`, `test/`, `thumbs/`, and `manifests/`. The Reconciler Agent keeps them synchronized.

**ML layer: the training orchestrator.** EfficientNet-B0 pre-trained on VGGFace2 + AffectNet (HSEmotion `enet_b0_8_best_vgaf`). Two-phase training: frozen backbone for 5 epochs, then selective unfreezing of blocks.5, blocks.6, and conv_head. Mixed precision (FP16), mixup augmentation, cosine LR with warmup. Every run tracked in MLflow with dataset hash.

**Deployment layer: ONNX to TensorRT.** On Gate A pass: export to ONNX, SCP to Jetson Xavier NX (10.0.4.150), convert to TensorRT with FP16 via `trtexec`, load into DeepStream. Gate B validates: FPS ≥ 25, latency p50 ≤ 120ms, GPU memory ≤ 2.5 GB.

**Output layer: emotion → LLM → gesture.** Detected emotions feed into confidence-tailored LLM prompts. LLM responses are parsed for gesture cues (`[WAVE]`, `[HUG]`, `[EMPATHY]`), mapped to physical gestures on Reachy Mini via gRPC. A 5-tier gesture modulator scales expressiveness based on confidence.

**Cross-cutting: observability and privacy.** Prometheus, Grafana, structured JSONL logging, TTL-based purges, access controls.

The key insight: **layers are connected by explicit event contracts, not implicit coupling**. Each agent emits typed events that downstream agents consume. That makes the system testable, auditable, and replaceable at any layer."

### Audience Callout
- **For managers:** Each box has a named owner, a defined contract, and a failure mode that does not cascade.
- **For technologists:** Event-driven microservice architecture adapted for ML ops on a LAN — no cloud, no message broker, just n8n orchestration and HTTP/WebSocket contracts.

### Transition
"Let me go deeper into the agent model."

---

## Slide 5 (08:30–11:00) — Agentic Operating Model (10+1 Agents)

### Script

"Ten cooperating agents plus an optional generation balancer. All orchestration in n8n on Ubuntu 1.

**Agent 1 — Ingest.** Receives videos, computes SHA-256, extracts metadata (duration, FPS, resolution), generates thumbnails, stores in `/videos/temp/`. Emits `ingest.completed`. The only entry point for new media — intentional audit chokepoint.

**Agent 2 — Labeling.** Manages human-assisted classification. Enforces 3-class policy. Stages labeled clips from `temp/` to `train/<label>/`. Maintains per-class counts and 1:1:1 balance. Enforces `chk_split_label` constraint. Logs every label with `intended_emotion`, timestamp, SHA-256.

**Agent 3 — Promotion / Curation.** Controls filesystem stage movement via canonical `POST /api/v1/media/promote`. Orchestrates per-run frame extraction and train/valid splitting via `DatasetPreparer`. Verifies `label IS NULL` for test outputs. Legacy endpoints are deprecated shims.

**Agent 4 — Reconciler / Audit.** Ensures filesystem-database consistency. Recomputes checksums, detects orphans/duplicates, rebuilds manifests. Emits reconciliation reports to Prometheus. The system's immune system.

**Agent 5 — Training Orchestrator.** Triggers EfficientNet-B0 fine-tuning when thresholds are met. Two-phase protocol, mixed precision, MLflow tracking, Gate A validation. Exports to ONNX on success.

**Agent 6 — Evaluation.** Runs test-set inference once `min(class_counts) ≥ TEST_MIN_PER_CLASS` (default: 20). Computes accuracy, F1 (macro + per-class), balanced accuracy, ECE, Brier. Generates confusion matrices. Emits Gate A pass/fail.

**Agent 7 — Deployment.** Manages ONNX → TensorRT → Jetson pipeline. Backs up engines, converts FP16, updates DeepStream config, validates Gate B, supports automatic rollback.

**Agent 8 — Privacy / Retention.** Auto-purges temp media past TTL (7 days). Denies unauthorized video access. Emits `privacy.purged` and `privacy.violation`.

**Agent 9 — Observability.** Aggregates all agent metrics: queue depth, task latency, success rate, dataset balance, model drift. Publishes to Prometheus/Grafana. Alerts on error budget breach (< 1% weekly per agent).

**Agent 10 — Reachy Gesture.** Receives WebSocket cues, parses gesture keywords from LLM, maps emotions to gestures, executes on Reachy Mini via gRPC. Happy: CELEBRATE, WAVE, NOD. Sad: EMPATHY, HUG, LISTEN. Neutral: NOD, THINK. Supports simulation mode.

**Optional — Generation Balancer.** Monitors class ratios, biases synthetic generation for 1:1:1 balance.

Design principle: **bounded autonomy**. Each agent acts within scope; cross-boundary actions require upstream events or human approval."

### Presenter Note
This is a variant of the actor-model pattern. n8n acts as the orchestration bus rather than a distributed message broker — simplifies operations at the cost of horizontal scalability, appropriate for LAN-bound systems. The Reactor pattern in Python asyncio underpins the gateway's event loop.

### Transition
"Those agents operate under explicit governance. Let me show you the gate structure."

---

## Slide 6 (11:00–13:30) — Quality Gates and Governance

### Script

"Governance in this system is code, not a document.

**Gate A — Model Quality (before ONNX export):**
- Macro F1 ≥ 0.84 — balanced quality across all three classes.
- Balanced Accuracy ≥ 0.85 — guards against class-skewed performance.
- Per-class F1 ≥ 0.75 (hard floor 0.70).
- ECE ≤ 0.08 — ensures confidence scores are trustworthy. A model that says '90% happy' should be correct ~90% of the time at that confidence level. Downstream gesture modulation and LLM prompt hedging depend on this.
- Brier ≤ 0.16 — proper scoring rule penalizing both miscalibration and poor discrimination.

**Gate B — Runtime (Jetson, post-TensorRT):**
- FPS ≥ 25, latency p50 ≤ 120ms, GPU memory ≤ 2.5 GB.

**Gate C — Post-Deployment (continuous):**
- Confidence distribution drift, accuracy vs labeled holdouts, user-outcome KPIs.

**Structural governance:**
- **Correlation IDs:** `X-Correlation-ID` follows artifacts from promotion through training, evaluation, deployment, and telemetry.
- **Idempotency keys:** All write operations deduplicate safely.
- **Deprecated endpoints:** Legacy shims return HTTP 410 with canonical URL and migration guidance. Toggleable via config.
- **Instruction priority:** (1) Safety/privacy/compliance → (2) UI consistency → (3) Maintainer instructions. Fail closed on uncertainty.
- **Retry policy:** Exponential backoff with jitter, max 5 attempts. Circuit breakers on latency/error spikes. Dead-letter queue for human review.

This makes the system **enterprise-safe**. An auditor can trace any decision from input to output."

### Audience Callout
- **For managers:** Gates are automatic. No bypass without code changes, and code changes require version control.
- **For technologists:** ECE uses equal-width binning (10 bins). Brier decomposes into calibration + discrimination. Both are proper scoring rules.

### Transition
"Now let me show you the model performance evidence."

---

# Part III — Evidence & Statistical Rigor (Slides 7–8, 13:30–18:00)

---

## Slide 7 (13:30–16:00) — Model Performance Trendline

### Script

"Here is the Gate A dashboard showing three model variants in progression:

| Variant | Accuracy | Macro F1 | Balanced Acc | ECE | Brier |
|---|---:|---:|---:|---:|---:|
| Base | 0.8125 | 0.8120 | 0.8080 | 0.1120 | 0.1580 |
| Variant 1 | 0.9023 | 0.9017 | 0.8998 | 0.0894 | 0.1299 |
| Variant 2 | 0.9297 | 0.9298 | 0.9285 | 0.0650 | 0.0920 |

Let me interpret each column.

**Accuracy** improved by 11.72 percentage points from Base to Variant 2. Meaningful, but accuracy alone is insufficient for a 3-class problem where class balance matters.

**Macro F1** improved by 11.78 points. Macro F1 computes F1 per class then averages — a model excellent on `happy` but poor on `sad` gets penalized. That macro F1 tracks closely with accuracy confirms the improvement is balanced, not skewed.

**Balanced Accuracy** improved by 12.05 points. Average of per-class recall. At 0.9285, Variant 2 correctly identifies each emotion ~93% of the time, balanced across classes.

**ECE** dropped by 4.70 points — from 0.1120 to 0.0650. The critical metric. ECE bins predictions by confidence, computes the gap between average confidence and average accuracy in each bin, and takes a weighted average. An ECE of 0.065 means the model's confidence is trustworthy to within ~6.5 percentage points. For a gesture modulator that scales response intensity based on confidence, this determines whether robot behavior is appropriate or erratic.

**Brier score** dropped by 6.60 points — from 0.1580 to 0.0920. Brier combines discrimination (can the model tell classes apart?) with calibration (are probabilities accurate?). Below 0.10 is excellent for a 3-class problem.

Variant 2 clears all Gate A thresholds: F1 0.93 ≥ 0.84, balanced accuracy 0.93 ≥ 0.85, ECE 0.065 ≤ 0.08, Brier 0.092 ≤ 0.16.

The critical question: **are these improvements real, or sampling noise?**"

### Presenter Note
ECE uses equal-width binning with 10 bins (0.0–0.1, 0.1–0.2, ..., 0.9–1.0). For a 3-class problem, the multi-class extension uses maximum predicted probability per sample. Alternative: adaptive/equal-mass binning.

### Transition
"Let me walk you through the statistical methodology."

---

## Slide 8 (16:00–18:00) — Paired Tests and Statistical Rigor

### Script

"Three complementary tests determine whether differences are statistically significant.

**1. Paired t-test on per-sample accuracy.**
Each test sample produces a binary correct/incorrect outcome per variant. We compute the per-sample difference and test whether the mean difference is significantly different from zero. For Base vs Variant 2: mean improvement 11.72 points, p < 0.001. The paired design controls for sample-level difficulty, increasing statistical power.

**2. McNemar's test for marginal homogeneity.**
Examines discordant pairs: samples one variant got right and the other got wrong. If Variant 2 is genuinely better, significantly more samples have Variant 2 correct and Base wrong than the reverse. Chi-squared with continuity correction: p < 0.001.

**3. Stuart-Maxwell test for 3-class marginal shifts.**
The critical test for our setting. McNemar's is for binary outcomes; Stuart-Maxwell generalizes to multi-class. It tests whether the marginal distribution of predicted classes has changed between two models, accounting for paired structure. For 3 classes, it uses chi-squared with 2 degrees of freedom.

Stuart-Maxwell detects scenarios per-class F1 misses. A model could maintain the same macro F1 while shifting misclassifications from `happy→neutral` to `sad→neutral`. Stuart-Maxwell flags this redistribution even if aggregate metrics stay flat.

All three tests: Base vs Variant 2 yields p < 0.001. Improvements are not sampling artifacts.

**Calibration verification:** ECE confidence intervals (bootstrap, 1000 resamples) — Variant 2 [0.055, 0.076] does not overlap Base [0.098, 0.127], confirming robust calibration improvement."

### Presenter Note
Stuart-Maxwell is the multivariate generalization of McNemar's. For k classes: chi-squared with k-1 degrees of freedom. Tests H0: marginal row totals equal marginal column totals in the k×k confusion matrix of paired predictions. Standard in clinical trials comparing diagnostic classifications before/after intervention.

### Audience Callout
- **For managers:** All three tests confirm improvements are real and not due to chance.
- **For technologists:** Stuart-Maxwell is the correct test for paired multi-class comparisons. Binarized McNemar's loses class-specific shift information.

### Transition
"With evidence established, let me show you the system in action."

---

# Part IV — Demo & Technical Depth (Slides 9–11, 18:00–23:00)

---

## Slide 9 (18:00–20:00) — Backend Demonstration Plan

### Script

"Let me walk you through what a live demonstration looks like — whether run live or walked through recordings, the sequence is identical.

**Step 1: Ingest a video.**
A short synthetic video (3–5 seconds) is uploaded through the Streamlit UI. The Ingest Agent computes SHA-256, extracts metadata (duration, FPS, resolution), generates a thumbnail, stores the video in `/videos/temp/`, and writes the record to PostgreSQL. The UI updates with the new video and thumbnail.

**Step 2: Label and promote.**
The operator reviews the video, assigns `happy`, and clicks promote. `POST /api/v1/media/promote` moves the file from `temp/` to `train/happy/`, logs the event with timestamp and checksum, and updates per-class balance. The Labeling Agent enforces 3-class policy.

**Step 3: Observe class balance.**
The dashboard shows distribution across all three classes. The 1:1:1 balance indicator updates in real time. Training readiness turns green when sufficient balanced data is available.

**Step 4: Trigger training.**
Training launches via `trainer/train_efficientnet.py`. Two-phase protocol: frozen backbone 5 epochs, then unfreezing blocks.5, blocks.6, conv_head. MLflow tracks the run with unique ID and dataset hash.

**Step 5: Evaluate and validate Gate A.**
The Evaluation Agent runs test-set inference. The Dashboard (06_Dashboard.py) displays Gate A metrics: accuracy, F1, balanced accuracy, ECE, Brier, confusion matrix. Green checkmarks for each passing threshold.

**Step 6: Deploy to Jetson.**
On Gate A pass: ONNX export → SCP to Jetson → TensorRT conversion → DeepStream load. Gate B validates FPS, latency, GPU memory. Rollback on failure.

**Step 7: End-to-end emotion response.**
Live camera on Jetson detects emotion. Classification + confidence flows to LLM → empathetic response with gesture cues → Gesture Agent executes on Reachy Mini via gRPC. Full loop: detection to gesture in under 200ms."

### Presenter Note
If live: Streamlit on Ubuntu 2 (10.0.4.140), FastAPI Swagger on Ubuntu 1 (10.0.4.130:8001/docs), Jetson dashboard on 10.0.4.150. The key is showing the audit trail — every action produces a logged event.

### Transition
"Now let me go under the hood — the API lifecycle."

---

## Slide 10 (20:00–21:30) — API Lifecycle and Promotion Routing

### Script

"The API layer is where governance meets implementation. Let me walk through promotion as a concrete example.

**Request arrives:** `POST /api/v1/media/promote` with JSON body: `video_id`, `target_label`, optional `dry_run: true`. Carries `X-Correlation-ID` and `Idempotency-Key` headers.

**Validation phase:** Router validates label against 3-class policy. Checks video exists, is in `temp/` status, has not been promoted. Verifies `chk_split_label` constraint. If `dry_run: true`, response previews the operation — source path, target path, constraint violations — without executing.

**Execution phase:** File moves from `temp/` to `train/<label>/`. PostgreSQL updated atomically: status, split, label fields set; promotion log created with correlation ID, timestamp, operator, checksum. Filesystem manifest rebuilt.

**Response:** Structured JSON with new file path, updated class counts, balance status, correlation ID. HTTP warning headers if deprecated parameters used.

**Error handling:** Constraint violations raise `PromotionValidationError` with structured body: constraint name, expected value, actual value. Logged; Observability Agent records failure metric.

**Legacy routing:** Deprecated `/api/v1/promote/stage` and `/api/v1/promote/sample` return HTTP 410 (Gone) with canonical endpoint URL and migration instructions. Toggleable via configuration.

Three principles demonstrated: **fail-fast validation**, **atomic state transitions**, **full traceability**."

### Presenter Note
Dry-run is borrowed from infrastructure-as-code (Terraform plan, Ansible check mode) — preview before commit reduces operational risk. Idempotency key pattern follows Stripe's API design.

### Transition
"Let me show you the emotion-to-gesture pipeline design."

---

## Slide 11 (21:30–23:00) — Emotion → LLM → Gesture Pipeline Design

### Script

"Four stages turning a model prediction into a physical robot gesture.

**Stage 1: Emotion detection (Jetson).**
DeepStream processes frames through TensorRT engine. Each frame produces classification + confidence vector (three probabilities summing to 1.0). Top-1 class and confidence emitted as structured event.

**Stage 2: Confidence-based prompt tailoring.**
Confidence score constructs LLM prompt with appropriate hedging:
- High (> 0.85): 'The person appears clearly happy.'
- Medium (0.60–0.85): 'The person may be feeling happy, though I am not entirely certain.'
- Low (< 0.60): 'I am detecting a possible emotional cue but cannot identify it with certainty.'
This prevents assertive claims about uncertain emotions.

**Stage 3: LLM response with gesture keywords.**
LLM (via LM Studio, local network) generates empathetic text with bracketed gesture keywords — `[WAVE]`, `[HUG]`, `[CELEBRATE]`. Fallback to emotion-to-gesture default map if LLM omits gesture.

**Stage 4: Gesture execution on Reachy Mini.**
Gesture Agent receives cue via WebSocket, looks up motor sequence from `emotion_gesture_map.py`, executes via gRPC through `gesture_controller.py`. The gesture modulator (`gesture_modulator.py`) scales expressiveness using 5 tiers:

| Tier | Confidence | Expressiveness | Example |
|---|---|---|---|
| 5 | 0.90–1.00 | Full | Bold wave, wide arm gestures |
| 4 | 0.75–0.90 | High | Standard wave, clear nod |
| 3 | 0.60–0.75 | Medium | Subtle nod, small gesture |
| 2 | 0.45–0.60 | Low | Minimal acknowledgment |
| 1 | 0.00–0.45 | Minimal | Attentive posture only |

Design patterns: **Chain of Responsibility** (each stage processes and passes downstream) combined with **Strategy** (gesture modulator selects behavior by confidence). The robot's behavior is proportional to certainty — users perceive this as appropriate restraint, not inconsistency.

Full pipeline: camera frame to robot gesture in under 200ms."

### Presenter Note
The Reactor pattern in Python asyncio underpins the gateway event loop — single-threaded multiplexing across all WebSocket connections and HTTP handlers (same pattern as Node.js/Nginx). Gesture queue uses priority handling: urgent emotional responses preempt queued neutral acknowledgments.

### Audience Callout
- **For managers:** The robot never overreacts to low-confidence predictions. Behavior is always proportional to certainty.
- **For technologists:** The 5-tier modulation is configurable per deployment. Clinical settings compress tiers 4–5 to reduce startle risk; education settings expand tiers 3–5 for expressiveness.

### Transition
"Now: risk, return, and architectural competency."

---

# Part V — Risk, ROI & Competency (Slides 12–15, 23:00–30:00)

---

## Slide 12 (23:00–25:00) — Risk Analysis and Mitigation

### Script

"Every system has risks. The question is whether you have identified them, quantified them, and built mitigations. Five primary risks:

**Risk 1: Model degradation in production.**
Threat: Classifier accuracy drops as user population or lighting conditions shift. Mitigation: Gate C continuously monitors confidence distributions and accuracy against labeled holdouts. Drift triggers retraining automatically. Prior engine retained for instant rollback. Residual risk: low.

**Risk 2: Privacy breach — video exfiltration.**
Threat: Raw video leaves the local network. Mitigation: Local-first architecture — no outbound video routes exist. Privacy Agent enforces TTL purges. All access logged. Firewall restricts egress. Residual risk: very low — requires deliberate architectural circumvention.

**Risk 3: Edge device resource exhaustion.**
Threat: TensorRT engine exceeds Jetson Xavier NX's GPU memory or compute, causing frame drops or thermal throttling. Mitigation: Gate B enforces hard limits (FPS ≥ 25, latency p50 ≤ 120ms, GPU ≤ 2.5 GB). EfficientNet-B0 chosen specifically for edge favorability. Residual risk: low.

**Risk 4: Operator error in labeling.**
Threat: Mislabeled training data degrades model quality. Mitigation: 3-class policy reduces ambiguity vs 7/8-class Ekman. Reconciler detects statistical anomalies in label distributions. Promotion includes dry-run preview. Human-in-the-loop mandatory. Residual risk: moderate — inherent in human labeling, mitigated by taxonomic simplicity.

**Risk 5: Single point of failure in n8n orchestration.**
Threat: n8n downtime stops agent coordination. Mitigation: systemd service with auto-restart. Agents are stateless — work-in-progress logged to PostgreSQL, restart resumes from last checkpoint. HA configuration available for mission-critical deployments. Residual risk: moderate for single-node.

Overall posture: **managed and measurable**. Each risk has a named mitigation, and the gate structure provides automated enforcement."

### Audience Callout
- **For managers:** The risk register maps to the gate structure. Risks are automatically tested every deployment cycle.
- **For technologists:** Stateless agent design means n8n recovery is fast — no distributed transaction state to rebuild.

### Transition
"Let me translate this into return on investment."

---

## Slide 13 (25:00–27:00) — ROI, Program Implications, and Scaling

### Script

"ROI measured across three dimensions.

**Dimension 1: Development velocity.**
Agentic architecture with n8n means new workflows compose without code changes. Adding a new agent: define contract, wire into n8n. Existing agents untouched. Open/Closed Principle at the system level. Time to add a new agent: 2–4 hours contract definition, 1–2 days implementation — versus 1–2 weeks in a monolithic pipeline.

**Dimension 2: Operational cost avoidance.**
Local-first eliminates cloud compute and storage costs. Comparable AWS pipeline (SageMaker + Lambda + S3): ~$2,000–4,000/month. On-premise cost: hardware amortization of three nodes, ~$300–500/month including power and networking. Breakeven under 3 months.

**Dimension 3: Vertical extensibility.**
The pipeline pattern — ingest, label, train, evaluate, deploy, monitor — applies to any classification task. Two verticals already designed:

- **CareFlow** — healthcare companion operations. Same emotion pipeline drives patient engagement in clinical lobbies, assisted living, rehabilitation. Privacy-first posture critical for HIPAA-adjacent environments.
- **SecureFlow** — cybersecurity operations. Classification pipeline adapted for threat detection on visual feeds. Governance model (gates, audit trails, rollback) maps to SOC 2 compliance.

These demonstrate the platform is a **reusable operational pattern** — different domains, different models, same governance and monitoring infrastructure.

**Scaling path:**
- **Horizontal:** More Jetson nodes for multi-camera. Gateway already supports multiple upstream connections.
- **Vertical:** EfficientNet-B0 → B2 for ~2% higher accuracy at ~2x latency. Gate B thresholds adjusted accordingly.
- **Organizational:** n8n workflows, agent contracts, gate specs all version-controlled. Second team can fork and adapt without starting from scratch."

### Presenter Note
CareFlow (emerald #10B981) and SecureFlow (amber #F59E0B) documented in `apps/web/dev/`. Both share the 5-node infrastructure and 8-step universal pattern.

### Transition
"Let me close with what this demonstrates about architectural competency."

---

## Slide 14 (27:00–29:00) — Competency Proof: Solutions Architect Evidence

### Script

"I want to be explicit about what this project demonstrates.

**1. System design.** Distributed system spanning three physical nodes, four languages (Python, SQL, JavaScript, YAML/JSON), six technology domains (ML, API, database, edge computing, robotics, observability). Documented architecture, clean boundaries, bounded failure modes.

**2. ML engineering.** Not just training — selecting appropriate pre-trained backbone (EfficientNet-B0, HSEmotion), implementing transfer learning with two-phase unfreezing, choosing proper evaluation metrics (including calibration metrics most practitioners ignore), building automated quality gates.

**3. API design.** Eleven FastAPI routers with versioned endpoints, correlation IDs, idempotency keys, dry-run support, structured errors, deprecated endpoint management, OpenAPI docs. An operational control plane, not a CRUD API.

**4. DevOps and MLOps.** MLflow for experiment tracking, n8n for orchestration, systemd for services, Alembic for migrations (12 tables through `20260228_000008`), Prometheus/Grafana for observability.

**5. Edge deployment.** ONNX export, TensorRT conversion, DeepStream configuration, Jetson Xavier NX resource management. The part most ML engineers never touch — getting a model from training server to physical device with real-time constraints.

**6. Privacy and governance engineering.** Local-first architecture, TTL retention, structured audit logging, GDPR-aligned data minimization, gate-based deployment controls. The part most system engineers never touch — building compliance into architecture, not bolting it on.

**7. Human-robot interaction.** Emotion-to-gesture mapping, confidence-based modulation, LLM prompt engineering for empathy, physical gesture execution via gRPC. Crosses from software engineering into interaction design.

Each area is individually a specialty. Integrating them into a coherent, governed, deployable system defines a **solutions architect** — someone who builds the system that connects components, not just the components themselves."

### Audience Callout
- **For managers:** Evidence of cross-functional delivery, not just individual component expertise.
- **For technologists:** Each domain implemented with production patterns, not prototypes.

### Transition
"Let me close with commitments and next steps."

---

## Slide 15 (29:00–30:00) — Close, Ask, and Commitments

### Script

"To summarize:

1. A **governed, local-first emotion intelligence platform** — video in, empathetic robot behavior out.
2. **Ten cooperating agents** with bounded autonomy, explicit contracts, automated quality gates.
3. **Statistical evidence** validated by paired t-tests, McNemar's test, and Stuart-Maxwell test.
4. A **complete operational stack** — ingestion through training through edge deployment through gesture execution.
5. **Enterprise-grade governance** — correlation IDs, idempotency, audit trails, three deployment gates.

**My ask:**

For adoption evaluation — I am available to run a live demo, walk through specific code paths, or discuss domain adaptation (CareFlow, SecureFlow, or new vertical).

For competency evaluation — the full repository is available for code review. Happy to deep-dive on any subsystem: ML pipeline, API layer, deployment pipeline, or gesture modulation.

**30-day commitments:**
- Gate C monitoring dashboard operational.
- Second-vertical prototype (CareFlow or SecureFlow) with domain-specific model.
- Performance benchmark: EfficientNet-B0 vs B2 on Jetson Xavier NX.

Thank you. I am happy to take questions."

### Presenter Note
End at exactly 30:00. If ahead, expand the demo (Slide 9) or statistical methodology (Slide 8). If behind, compress ROI (Slide 13) — the key message is vertical extensibility, statable in one sentence.

---

# Appendix — Extended Q&A (8 Questions)

---

## Q1: Why use ECE and Brier score instead of just accuracy and F1?

**Answer:** Accuracy and F1 measure discrimination — can the model tell classes apart? They say nothing about whether confidence scores are meaningful. In our system, confidence directly drives behavior: the gesture modulator scales expressiveness, and the LLM prompt hedges language based on confidence. If the model says "90% happy" but is only correct 60% of the time at that confidence level, the robot behaves inappropriately.

ECE measures this gap directly — partitions predictions into confidence bins, computes the difference between average confidence and average accuracy per bin, takes a weighted average. Well-calibrated: ECE near 0.

Brier score is a proper scoring rule — incentive-compatible (cannot game by reporting false confidences) and decomposable into calibration + discrimination components. Defined as mean squared error between predicted probability vectors and one-hot true labels.

Together, ECE and Brier ensure probabilities are trustworthy, not just top-1 predictions.

---

## Q2: Why EfficientNet-B0 instead of a larger model?

**Answer:** Must run real-time on Jetson Xavier NX: ≤ 2.5 GB GPU, ≥ 25 FPS. EfficientNet-B0 achieves this with headroom — ~5.3M parameters, ~0.39 GFLOPs. HSEmotion weights (`enet_b0_8_best_vgaf`) pre-trained on VGGFace2 + AffectNet — exactly our domain.

EfficientNet-B2 offers ~2% higher accuracy at ~2x latency, pushing close to Gate B limits. The B0/B2 tradeoff is a documented 30-day benchmark commitment.

Two-phase training (frozen 5 epochs, then selective unfreezing) works because HSEmotion weights already encode rich facial features — we only adapt the classification head and fine-tune final blocks for our 3-class taxonomy.

---

## Q3: What happens when a request hits a deprecated endpoint?

**Answer:** Deprecated endpoints (`/api/v1/promote/stage`, `/api/v1/promote/sample`) are retained as shims — not silently removed. They return:
- HTTP 410 (Gone)
- Structured JSON: `error_code`, `message`, `canonical_endpoint`, `migration_guide`
- HTTP `Deprecation` warning header with date

Shims raise `PromotionValidationError` internally. Toggleable via configuration for backward compatibility during migration periods. This approach follows API versioning best practices — clients get actionable error messages, not silent failures.

---

## Q4: How does the Stuart-Maxwell test differ from running McNemar's per class?

**Answer:** McNemar's test is binary — correct/incorrect. Running it per class binarizes each class separately, losing inter-class shift information. A model could shift misclassifications from `happy→neutral` to `sad→neutral` without changing per-class McNemar's results.

Stuart-Maxwell operates on the full k×k confusion matrix of paired predictions. For k classes, it produces a chi-squared statistic with k-1 degrees of freedom, testing whether marginal row totals equal marginal column totals. It detects distributional shifts that per-class tests miss.

It is the standard test for paired nominal data with more than two categories — commonly used in clinical trials comparing diagnostic classifications before/after intervention, or in linguistics for comparing categorization systems.

---

## Q5: How does the system handle class imbalance during training?

**Answer:** Multiple mechanisms:
1. **1:1:1 balance enforcement** — the Labeling Agent tracks per-class counts and displays balance status. The Generation Balancer biases synthetic video creation toward underrepresented classes.
2. **Dataset preparation** — `DatasetPreparer` creates run-scoped datasets with configurable train/val splits (90/10). Frame extraction produces 10 frames per video, maintaining class balance at the frame level.
3. **Training augmentation** — mixup augmentation (linear interpolation between training pairs) provides implicit regularization against class-specific overfitting.
4. **Metric selection** — macro F1 and balanced accuracy are the primary metrics, both of which penalize class-skewed performance. Per-class F1 floors (≥ 0.75, hard 0.70) ensure no class falls below usability.

---

## Q6: What is the rollback procedure if Gate B fails?

**Answer:** Automated rollback:
1. Gate B validation runs on Jetson after TensorRT conversion.
2. On failure (FPS < 25, latency > 120ms, or GPU > 2.5 GB), the Deployment Agent halts.
3. The prior engine backup (created before deployment) is restored to `/opt/reachy/models/emotion_efficientnet.engine`.
4. DeepStream configuration reverts to the prior `emotion_inference.txt`.
5. DeepStream service is restarted.
6. Rollback event logged with failure metrics, prior engine version, and timestamp.
7. Alert emitted to Observability Agent and human maintainer.

The entire rollback completes in under 60 seconds. The system never enters a state where no valid engine is loaded.

---

## Q7: How does correlation ID tracing work end-to-end?

**Answer:** The `X-Correlation-ID` is generated (or resolved from the incoming request) at the first API call — typically the promotion request. It follows the artifact through:
1. **Promotion** — logged with the video's move from `temp/` to `train/<label>/`.
2. **Training** — the dataset hash and correlation IDs of constituent videos are recorded in MLflow.
3. **Evaluation** — test results reference the model's training correlation ID.
4. **Deployment** — the engine metadata records the model's correlation ID.
5. **Telemetry** — Prometheus metrics and Grafana dashboards can filter by correlation ID.

This means any deployed engine can be traced back through evaluation, training, dataset composition, and individual video promotions. An auditor can reconstruct the complete provenance chain for any model in production.

The `correlation_id` is part of the mandatory message envelope (alongside `schema_version`, `issued_at`, and `source`) as defined in the Orchestration Policy.

---

## Q8: What would it take to add a fourth emotion class?

**Answer:** Adding a class (e.g., `angry`) requires changes at five layers:
1. **Database** — update the `chk_split_label` constraint to include `angry`. Add Alembic migration.
2. **Labeling Agent** — extend 3-class policy to 4-class. Update UI label options and balance tracking to 1:1:1:1.
3. **Training** — update `efficientnet_b0_emotion_3cls.yaml` to 4-class output. Retrain with balanced data. Gate A thresholds may need adjustment (F1 ≥ 0.80 might be more realistic for 4 classes).
4. **Gesture mapping** — add `angry` to `emotion_gesture_map.py` with appropriate gestures (e.g., CALM, ACKNOWLEDGE, GENTLE_NOD). Angry gestures should de-escalate, not mirror the emotion.
5. **LLM prompting** — add confidence-hedged prompt templates for `angry` detection.

Estimated effort: 1–2 days for implementation, 1–2 weeks for data collection and retraining. The architecture supports this — the agent contracts and gate structure do not assume a fixed number of classes. The constraint is data availability, not architecture.

---

*End of Graduate-Level 30-Minute Presentation Script*
