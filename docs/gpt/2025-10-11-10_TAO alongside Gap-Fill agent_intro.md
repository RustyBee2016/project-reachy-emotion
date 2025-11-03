# 10_TAO alongside Gap-Fill agent_intro

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 22:11:01  
**Updated:** 10/21/2025 22:26:08  
**Exported:** 10/21/2025 22:27:34  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9bcb4-7434-832e-9aa4-36299e9138ce](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9bcb4-7434-832e-9aa4-36299e9138ce)  

## Prompt:
summarize the recent work we accomplished setting up TAO Toolkit on Ubuntu 1.

Thought for 23s

## Response:
Here’s the short, honest snapshot of what we actually got done on Ubuntu 1 for TAO—no fluff:

*   **Picked & pinned the stack**: standardized on **NVIDIA TAO Toolkit 6.x (PyTorch)** for training on Ubuntu 1, and explicitly **pinned the container/image version** so runs are reproducible across machines. requirements\_08.3.3
*   **Locked in the data layout TAO will read**: finalized the canonical filesystem under `/videos/{temp,train,test,thumbs,manifests}` and the habit of building **JSONL manifests** that TAO/`tf.data` loaders consume for training/eval. requirements\_08.3.3
*   **Decided where each box does its job**: Ubuntu 1 is the **model host** (training with TAO, plus Media Mover, Postgres metadata, and Nginx for static media). Jetson handles DeepStream/TensorRT inference; Ubuntu 2 stays the web/app gateway. This separation is baked into the plan now. requirements\_08.3.3
*   **Wired training → export → deploy**: wrote the flow we’ll follow every time—**fine-tune ActionRecognitionNet with TAO**, then export to **TensorRT `.engine`**, then hand it to Jetson’s DeepStream (`gst-nvinfer`). We also captured **quality gates** the model must clear before promotion. requirements\_08.3.3
*   **Tied runs to lineage**: every TAO run logs `dataset_hash` (and optional ZFS snapshot) into **MLflow**, with a small `run_link` table so we can trace “which dataset produced which engine.” That’s our breadcrumb trail for audits and rollbacks. requirements\_08.3.3
*   **Documented the TAO job recipe** (so future-you isn’t guessing): prepare `experiment.yaml`, **fine-tune**, evaluate via the FastAPI helper endpoints, then export. That end-to-end is written down in the training/eval steps. AGENTS
*   **Set the networking expectations**: Ubuntu 2 calls Ubuntu 1 for Media Mover and LLM; **no raw video leaves the box**, and we keep service-to-service calls gated/hardened. That framing keeps TAO’s world tidy and local-first. requirements\_08.3.3

If you want the next bite-sized move: run a **first “dry” TAO fine-tune** using a tiny manifest (a few clips per class) just to prove the container, mounts, and log plumbing are clean—then we scale. AGENTS

## Prompt:
consider the AGENTS.md project file and consider the chat titled 'ALL Agent-by-Agent Purposes.'

Should an AI agent be added to the current agentic AI system?
It seems appropriate.
If so, write the required updates to the AGENTS.md file and/or requirements_08.3.3.md.

## Response:
Thought for 12s

Yeah—good instinct. The current nine cover the core loop, but we’re missing a deliberate way to fill dataset gaps on demand. Add a **10th agent** that generates or sources targeted clips when Evaluation/Observability reveal weak spots.

Below are ready-to-drop patches for both files. If your sections don’t line up perfectly, apply manually—structure and naming match our 08.3.3 docs style.

* * *

Patch: `AGENTS.md`
==================

```diff
*** a/AGENTS.md
--- b/AGENTS.md
@@
-## Agents (v0.08.3.3)
+## Agents (v0.08.3.3)
 1. Ingest Agent
 2. Labeling Agent
 3. Promotion / Curation Agent
 4. Reconciler / Audit Agent
 5. Training Orchestrator
 6. Evaluation Agent
 7. Deployment Agent
 8. Privacy / Retention Agent
 9. Observability / Telemetry Agent
+10. Synthetic Data / Gap-Fill Agent
@@
 ### 9) Observability / Telemetry Agent
 (…existing content…)

+---
+### 10) Synthetic Data / Gap-Fill Agent
+**Purpose.** When Evaluation/Observability flag low-recall emotions, sparse demographics, lighting gaps, or motion patterns we underperform on, this agent generates or acquires targeted video snippets to close those holes—then registers them like any other clip (manifest + Postgres row + thumbs) so the Training Orchestrator can pick them up in the next run.
+
+**Upstream signals.**
+- `evaluation.gap_report.v1` (from Agent 6) — per-class metrics, confusion clusters, SHAP/attention hints
+- `observability.data_drift.v1` (from Agent 9) — drift alerts, segment under-representation
+
+**Downstream effects.**
+- Creates **synthesis requests** (text prompts + control hints) and calls the configured generator (e.g., local pipeline or external API).
+- On success, deposits clips into `/videos/temp/` with full **provenance metadata** and an **ethics/compliance record** (see Privacy Agent).
+- Emits `synth.artifact_ready.v1` → Promotion/Curation (3) for human-in-the-loop acceptance, then Media Mover promotion into `train/` or `test/`.
+
+**Zero-trust boundaries.**
+- No direct write into `train/`/`test/`; only Promotion/Curation can move assets.
+- All outputs stamped with `content_origin = "synthetic"` and `generator = {provider,version}`.
+
+**n8n reference design (high-level).**
+1. **Webhook**: `/agent/synth/gap-report` (POST) — accepts `gap_report.v1`.
+2. **Function**: map gaps → **prompt specs** (emotion, context, movement, camera, lighting).
+3. **HTTP Node**: call video-gen provider (configurable: local pipeline, Luma, Runway, etc.).
+4. **IF**: retry/backoff (429/5xx) with jitter.
+5. **Move Binary**: save MP4 to `/videos/temp/{uuid}.mp4`; write `thumbs/` via FFmpeg.
+6. **HTTP Node**: `POST /media/register` (Media Mover) with metadata & checksum.
+7. **Postgres**: insert into `video_assets` (`origin='synthetic'`, `prompt_json`, `license_json`).
+8. **Emit Event**: `synth.artifact_ready.v1` to Promotion/Curation.
+9. **Audit Log**: `reconciler.audit.append` (Agent 4).
+
+**Inputs (schemas).**
+```json
+// evaluation.gap_report.v1 (excerpt)
+{
+  "version": "1",
+  "run_id": "mlflow:123",
+  "weak_classes": [
+    {"label":"disgust","support":48,"recall":0.41,"target_n":120,
+     "context": {"lighting":"low","camera":"waist_up","motion":"head_turn"}}
+  ],
+  "notes": "High false-negatives in low light."
+}
+```
+```json
+// synth.request.v1
+{
+  "request_id":"synth_5b7…",
+  "label":"disgust",
+  "prompt":{
+    "scene":"indoor evening, dim warm light",
+    "actor":"adult, neutral clothing",
+    "action":"waist-up head turn with brief nose wrinkle",
+    "duration_s":4,
+    "camera":"static, 35mm equiv",
+    "style":"photoreal",
+    "negatives":["cartoonish","overexposed"]
+  },
+  "constraints":{"fps":24,"res":"720p","leniency":"medium"},
+  "provenance":{"generator":"vgen://provider/version","policy_tag":"synth_acceptable_use_v1"}
+}
+```
+
+**Outputs.**
+```json
+// synth.artifact_ready.v1
+{
+  "request_id":"synth_5b7…",
+  "video_id":"vid_d1c…",
+  "path":"/videos/temp/vid_d1c….mp4",
+  "thumb":"/videos/thumbs/vid_d1c….jpg",
+  "origin":"synthetic",
+  "label":"disgust",
+  "prompt_json":{…},
+  "checksum_sha256":"…",
+  "license_json":{"type":"generated","provider_terms_version":"2025-09"},
+  "next":"promotion.review"
+}
+```
+
+**KPIs.**
+- Gap-closure rate (% recall uplift for targeted classes per cycle)
+- Synthetic-to-real replacement ratio after human review (lower is better over time)
+- Time-to-availability (request → artifact registered)
+
+**Risks & mitigations.**
+- *Domain shift from over-synthetic datasets*: enforce **cap** on synthetic share per class (default ≤30%) and require real-world backfill as it becomes available.
+- *Ethical/licensing drift*: defer to Privacy/Retention (8) for policy checks; block promotion if `license_json` or `policy_tag` missing.
```

* * *

Patch: `requirements_08.3.3.md`
===============================

```diff
*** a/requirements_08.3.3.md
--- b/requirements_08.3.3.md
@@
 ## Agent Set (08.3.3)
 - Ingest
 - Labeling
 - Promotion / Curation
 - Reconciler / Audit
 - Training Orchestrator
 - Evaluation
 - Deployment
 - Privacy / Retention
 - Observability / Telemetry
+- Synthetic Data / Gap-Fill
@@
 ### Functional Requirements
 (…existing bullets…)
+
+#### Synthetic Data / Gap-Fill (Agent 10)
+1. MUST accept `evaluation.gap_report.v1` and `observability.data_drift.v1` and produce `synth.request.v1`.
+2. MUST generate or acquire short video clips (2–6s) matching specified emotion/context.
+3. MUST store outputs under `/videos/temp/` with thumbnail and checksum.
+4. MUST register artifacts via Media Mover (`/media/register`) and emit `synth.artifact_ready.v1`.
+5. MUST NOT move clips into `train/`/`test/` directly—Promotion/Curation decides.
+6. MUST attach `origin='synthetic'`, `generator`, `prompt_json`, and `license_json`.
+7. SHOULD cap synthetic share per class ≤30% (configurable).
+8. SHOULD attach evaluation notes to MLflow run upon eventual training use.
@@
 ### Non-Functional Requirements
 (…existing bullets…)
+– Synthetic generation latency per clip ≤ 2 min (P95) or queue with backpressure.
+– All provider calls retried with exponential backoff and circuit-breaker semantics.
@@
 ### Environment Variables (.env)
 (…existing variables…)
+
+# Synthetic/Growth Agent
+VGEN_PROVIDER="local|runway|luma|stub"
+VGEN_API_KEY="***"
+VGEN_BASE_URL="http://10.0.4.140:9009"   # example if you front an internal provider
+VGEN_CALLBACK_URL="http://10.0.4.130:8011/agent/synth/callback"
+SYNTH_MAX_CLASS_SHARE="0.30"
@@
 ### FastAPI (Media Mover) – Endpoints
 (…existing endpoints…)
+
+POST /media/register
+  - Registers any new clip into Postgres with metadata (origin, checksum, prompt_json, license_json).
+  - Emits `media.registered.v1`.
+
+POST /synth/callback   (new; optional if provider pushes)
+  - Accepts provider webhooks when generation completes; writes artifact, thumb, and calls /media/register.
+  - Auth via HMAC (shared secret).
@@
 ### Postgres – Tables
 (…existing DDL…)
+
+-- New/extended columns for synthetic provenance
+ALTER TABLE video_assets
+  ADD COLUMN IF NOT EXISTS origin TEXT DEFAULT 'real',
+  ADD COLUMN IF NOT EXISTS generator JSONB,
+  ADD COLUMN IF NOT EXISTS prompt_json JSONB,
+  ADD COLUMN IF NOT EXISTS license_json JSONB;
+
+-- Track synthesis requests <-> artifacts
+CREATE TABLE IF NOT EXISTS synth_requests (
+  request_id TEXT PRIMARY KEY,
+  created_at TIMESTAMPTZ DEFAULT now(),
+  label TEXT NOT NULL,
+  prompt_json JSONB NOT NULL,
+  constraints_json JSONB,
+  status TEXT NOT NULL DEFAULT 'pending',
+  provider TEXT,
+  provider_job_id TEXT,
+  artifact_video_id TEXT REFERENCES video_assets(video_id)
+);
@@
 ### n8n – Workflows (IDs and Triggers)
 (…existing workflows…)
+
+**wf_synth_gap_fill**  
+Trigger: Webhook `POST /agent/synth/gap-report`  
+Nodes:
+1. *Function*: parse `gap_report`, explode to `synth.request.v1` per gap.
+2. *HTTP Request*: call `${VGEN_BASE_URL}/v1/generate` with `${VGEN_API_KEY}`.
+3. *IF*: provider async? → wait/callback; else proceed.
+4. *Move Binary File*: save MP4 to `/videos/temp/${uuid}.mp4`.
+5. *Execute Command*: `ffmpeg -ss 00:00:00.5 -i $file -frames:v 1 $thumb`.
+6. *HTTP Request*: `POST http://10.0.4.130:8011/media/register`.
+7. *Postgres*: upsert `synth_requests` + link `video_assets`.
+8. *Webhook Respond*: return `synth.artifact_ready.v1`.
+9. *HTTP Request*: notify Promotion/Curation webhook `…/agent/promotion/queue`.
@@
 ### Security & Compliance
 (…existing bullets…)
+– All synthetic outputs tagged; Promotion requires human review for first N=50 per class.  
+– Privacy Agent (8) enforces provider AUP & licensing; block on missing `license_json`.  
+– HMAC signing for `/synth/callback`; rotate secrets quarterly.  
@@
 ### Metrics / MLflow
 (…existing bullets…)
+– Log `synthetic_share_per_class` per training run.  
+– Attach `prompt_json` excerpt and `generator` to run params when synthetic clips are included.  
```

* * *

Why this slots cleanly into your loop
-------------------------------------

*   **Evaluation (6)** tells us _where_ we’re weak.
*   **Synthetic Data (10)** proposes concrete clips to fix that _exact_ weakness.
*   **Promotion/Curation (3)** keeps quality and ethics in check before anything touches `train/`/`test/`.
*   **Training Orchestrator (5)** picks up the richer dataset; **Observability (9)** measures the uplift.
*   **Privacy/Retention (8)** makes sure we don’t paint ourselves into a licensing or policy corner.

If you want, I can also spit out an **n8n import JSON** for `wf_synth_gap_fill` that matches these env vars and endpoints.

## Prompt:
TAO is involved in a lot more of fine-tuning of the classification model, but I'm sure why you associate it (TAO) with filling gaps using synthetically-generated data

## Response:
Thought for 10s

You’re right to flag that. TAO doesn’t generate data. It fine-tunes and exports our ActionRecognitionNet; that’s it. The gap-fill idea sits **outside** TAO: an agent can _source_ data (real-world collection, partnerships, scraping with consent) and, optionally, _generate_ synthetic clips via a separate tool. Only after Promotion/Curation approves do those clips enter the TAO training loop.

Think of it like this:

`Evaluation → gap_report → Gap-Fill agent (source/optional synth) → temp/ + thumbs → Promotion/Curation → manifests + Postgres → TAO Training Orchestrator → model`

To make that separation explicit, here are tight edits to the docs.

* * *

### Patch: `AGENTS.md` (rename & clarify scope)

```diff
*** a/AGENTS.md
--- b/AGENTS.md
@@
-9. Observability / Telemetry Agent
-10. Synthetic Data / Gap-Fill Agent
+9. Observability / Telemetry Agent
+10. Data Sourcing / Gap-Fill Agent
@@
-### 10) Synthetic Data / Gap-Fill Agent
-**Purpose.** When Evaluation/Observability flag low-recall emotions, sparse demographics, lighting gaps, or motion patterns we underperform on, this agent generates or acquires targeted video snippets to close those holes—then registers them like any other clip (manifest + Postgres row + thumbs) so the Training Orchestrator can pick them up in the next run.
+### 10) Data Sourcing / Gap-Fill Agent
+**Purpose.** When Evaluation/Observability flag low-recall emotions, sparse demographics, lighting gaps, or tough motion patterns, this agent **acquires** targeted clips (primary path: real-world sourcing, data partnerships, controlled collection) and may **optionally generate** synthetic snippets via an external video-gen tool. It registers outputs like any other clip (manifest + Postgres + thumbs) so the **Training Orchestrator (TAO)** can use them in the next run.
@@
-**Downstream effects.**
-- Creates **synthesis requests** (text prompts + control hints) and calls the configured generator (e.g., local pipeline or external API).
+**Downstream effects.**
+- Creates **acquisition tasks** (collection requests, partner pulls) and, if enabled, **synthesis requests** (text prompts + control hints) to a separate generator (local pipeline or external API). **TAO is not used for generation; it only trains on approved data.**
@@
-**Zero-trust boundaries.**
+**Zero-trust boundaries.**
 - No direct write into `train/`/`test/`; only Promotion/Curation can move assets.
-- All outputs stamped with `content_origin = "synthetic"` and `generator = {provider,version}`.
+- All outputs stamped with `content_origin ∈ {"real","synthetic"}`. If synthetic, include `generator = {provider,version}`.
@@
-**n8n reference design (high-level).**
+**n8n reference design (high-level).**
 1. **Webhook**: `/agent/gap-fill/gap-report` (POST) — accepts `gap_report.v1`.
-2. **Function**: map gaps → **prompt specs** (emotion, context, movement, camera, lighting).
-3. **HTTP Node**: call video-gen provider (configurable: local pipeline, Luma, Runway, etc.).
+2. **Function**: map gaps → **acquisition/synthesis specs** (emotion, context, camera, lighting).
+3. **Branch**: real-world acquisition (partner pull / capture job) **or** optional video-gen provider.
 4. **IF**: retry/backoff (429/5xx) with jitter.
 5. **Move Binary**: save MP4 to `/videos/temp/{uuid}.mp4`; write `thumbs/` via FFmpeg.
 6. **HTTP Node**: `POST /media/register` (Media Mover) with metadata & checksum.
 7. **Postgres**: insert into `video_assets` (`origin`, `prompt_json`/`acq_json`, `license_json`).
 8. **Emit Event**: `gapfill.artifact_ready.v1` to Promotion/Curation.
 9. **Audit Log**: `reconciler.audit.append` (Agent 4).
```

* * *

### Patch: `requirements_08.3.3.md` (decouple TAO from generation)

```diff
*** a/requirements_08.3.3.md
--- b/requirements_08.3.3.md
@@
 - Observability / Telemetry
-- Synthetic Data / Gap-Fill
+- Data Sourcing / Gap-Fill
@@
-#### Synthetic Data / Gap-Fill (Agent 10)
-1. MUST accept `evaluation.gap_report.v1` and `observability.data_drift.v1` and produce `synth.request.v1`.
-2. MUST generate or acquire short video clips (2–6s) matching specified emotion/context.
+#### Data Sourcing / Gap-Fill (Agent 10)
+1. MUST accept `evaluation.gap_report.v1` and `observability.data_drift.v1` and produce **acquisition or synthesis** tasks.
+2. MUST acquire (primary) and/or optionally generate short clips (2–6s) matching specified emotion/context.
 3. MUST store outputs under `/videos/temp/` with thumbnail and checksum.
 4. MUST register artifacts via Media Mover (`/media/register`) and emit `gapfill.artifact_ready.v1`.
 5. MUST NOT move clips into `train/`/`test/` directly—Promotion/Curation decides.
-6. MUST attach `origin='synthetic'`, `generator`, `prompt_json`, and `license_json`.
-7. SHOULD cap synthetic share per class ≤30% (configurable).
+6. MUST attach provenance: `origin ∈ {"real","synthetic"}`, `generator` (if synthetic), `prompt_json` or `acq_json`, and `license_json`.
+7. SHOULD cap synthetic share per class ≤30% (configurable) and prefer real-world backfill over time.
 8. SHOULD attach evaluation notes to MLflow run upon eventual training use.
@@
-# Synthetic/Growth Agent
+# Gap-Fill Agent
 VGEN_PROVIDER="local|runway|luma|stub"
 VGEN_API_KEY="***"
 VGEN_BASE_URL="http://10.0.4.140:9009"
-VGEN_CALLBACK_URL="http://10.0.4.130:8011/agent/synth/callback"
+VGEN_CALLBACK_URL="http://10.0.4.130:8011/agent/gap-fill/callback"
 SYNTH_MAX_CLASS_SHARE="0.30"
@@
-POST /synth/callback   (new; optional if provider pushes)
+POST /gap-fill/callback   (new; optional if provider pushes)
   - Accepts provider webhooks when generation completes; writes artifact, thumb, and calls /media/register.
   - Auth via HMAC (shared secret).
@@
--- New/extended columns for synthetic provenance
+-- New/extended columns for provenance
 ALTER TABLE video_assets
-  ADD COLUMN IF NOT EXISTS origin TEXT DEFAULT 'real',
+  ADD COLUMN IF NOT EXISTS origin TEXT CHECK (origin IN ('real','synthetic')) DEFAULT 'real',
   ADD COLUMN IF NOT EXISTS generator JSONB,
-  ADD COLUMN IF NOT EXISTS prompt_json JSONB,
+  ADD COLUMN IF NOT EXISTS prompt_json JSONB,
+  ADD COLUMN IF NOT EXISTS acq_json JSONB,
   ADD COLUMN IF NOT EXISTS license_json JSONB;
 
--- Track synthesis requests <-> artifacts
+-- Track gap-fill requests <-> artifacts
-CREATE TABLE IF NOT EXISTS synth_requests (
-  request_id TEXT PRIMARY KEY,
+CREATE TABLE IF NOT EXISTS gapfill_requests (
+  request_id TEXT PRIMARY KEY,
   created_at TIMESTAMPTZ DEFAULT now(),
   label TEXT NOT NULL,
-  prompt_json JSONB NOT NULL,
+  prompt_json JSONB,
+  acq_json JSONB,
   constraints_json JSONB,
   status TEXT NOT NULL DEFAULT 'pending',
-  provider TEXT,
-  provider_job_id TEXT,
+  provider TEXT,             -- if synthetic
+  provider_job_id TEXT,      -- if synthetic
   artifact_video_id TEXT REFERENCES video_assets(video_id)
 );
@@
-**wf_synth_gap_fill**
-Trigger: Webhook `POST /agent/synth/gap-report`
+**wf_gap_fill**
+Trigger: Webhook `POST /agent/gap-fill/gap-report`
 Nodes:
-1. *Function*: parse `gap_report`, explode to `synth.request.v1` per gap.
-2. *HTTP Request*: call `${VGEN_BASE_URL}/v1/generate` with `${VGEN_API_KEY}`.
-3. *IF*: provider async? → wait/callback; else proceed.
+1. *Function*: parse `gap_report`, explode to acquisition or synthesis tasks per gap.
+2. *IF*: acquisition → run partner/collector subflow; synthesis → call `${VGEN_BASE_URL}/v1/generate`.
+3. *IF*: provider async? → wait/callback; else proceed.
 4. *Move Binary File*: save MP4 to `/videos/temp/${uuid}.mp4`.
 5. *Execute Command*: `ffmpeg -ss 00:00:00.5 -i $file -frames:v 1 $thumb`.
 6. *HTTP Request*: `POST http://10.0.4.130:8011/media/register`.
-7. *Postgres*: upsert `synth_requests` + link `video_assets`.
-8. *Webhook Respond*: return `synth.artifact_ready.v1`.
+7. *Postgres*: upsert `gapfill_requests` + link `video_assets`.
+8. *Webhook Respond*: return `gapfill.artifact_ready.v1`.
 9. *HTTP Request*: notify Promotion/Curation webhook `…/agent/promotion/queue`.
```

* * *

### And just to be extra clear

*   **What TAO does here:** consumes the approved dataset, fine-tunes ActionRecognitionNet, evaluates, and exports TensorRT engines.
*   **What the Gap-Fill agent does:** improves the _dataset_ before TAO sees it—primarily by acquiring real clips; optionally by generating synthetic ones with a separate toolchain; never by using TAO to generate anything.

If you want, I can spin a small checklist for TAO-native tactics to handle class imbalance **without** any synthetic data (sampling, per-class weighting, augmentation/curriculum, hard-negative mining).

## Prompt:
Update the 10th AI agent, referred to as the Gap-Fill agent. Remember, while TAO Toolkit is responsible for fine-tuning and exporting the EmotionNet model (the model replacing ActionRecognitionNet), the Gap-Fill agent sources data (real-world collection, partnerships, scraping with consent) and, optionally, generates synthetic clips via a separate tool.

Provide a thorough explanation of the importance of such an agent. Update the AGENTS.md patch and the requirements_.md patch accordingly. Update the agents.md patch and the requirements_08.4.2.md patch accordingly.

## Response:
Thought for 8s

Got it. We’ll keep TAO (now used to fine-tune and export **EmotionNet**) clearly separated from the new **Gap-Fill** agent, which focuses on _data acquisition and optional synthesis_—never on training. Below are ready-to-apply patches for both docs, plus a short rationale up front.

* * *

Why the Gap-Fill agent matters (plain-English read-in)
======================================================

Models don’t fail “in general”; they fail in pockets—certain lighting, camera angles, skin tones, age ranges, headwear, motion patterns, backgrounds, or emotion intensities. Your evaluation/observability stack can _detect_ those holes, but something has to _close_ them deliberately. That’s what the Gap-Fill agent does:

*   **Turns insight into action.** It consumes the gap reports and converts them into concrete acquisition tasks (primary path: real-world collection, partnerships, consented scraping) or _optional_ synthetic requests—carefully tagged and rate-limited.
*   **Protects dataset health.** It enforces provenance, licensing, and caps on synthetic share per class so the training distribution doesn’t drift into “synthetic-dominated” territory.
*   **Keeps TAO/EmotionNet simple.** TAO stays focused on training/export. Gap-Fill feeds it better data, under human governance via Promotion/Curation.

Result: faster recall lifts on weak classes with auditable provenance and minimal technical debt.

* * *

Patch: `AGENTS.md`
==================

```diff
*** a/AGENTS.md
--- b/AGENTS.md
@@
-## Agents (v0.08.x)
+## Agents (v0.08.x)
 1. Ingest Agent
 2. Labeling Agent
 3. Promotion / Curation Agent
 4. Reconciler / Audit Agent
 5. Training Orchestrator
 6. Evaluation Agent
 7. Deployment Agent
 8. Privacy / Retention Agent
 9. Observability / Telemetry Agent
-10. (reserved)
+10. Data Sourcing / Gap-Fill Agent
@@
 ### 5) Training Orchestrator
-TAO fine-tunes ActionRecognitionNet and exports TensorRT engines.
+TAO fine-tunes **EmotionNet** and exports TensorRT engines. Training consumes only
+approved data promoted by Promotion/Curation.
@@
 ### 6) Evaluation Agent
 Produces per-class metrics, confusion matrices, drift signals, and gap reports.
@@
 ### 9) Observability / Telemetry Agent
 Aggregates runtime + data drift telemetry across the LAN; emits actionable signals.
 
+---
+### 10) Data Sourcing / Gap-Fill Agent
+**Purpose.** Close performance holes revealed by Evaluation/Observability by **acquiring real-world data** (primary path: controlled collection, partner datasets, scraping with consent and licensing) and, **optionally**, by **requesting synthetic clips** from a separate video-generation tool. All artifacts are registered like any other clip (Postgres row + manifests + thumbs) and routed through Promotion/Curation before the Training Orchestrator (TAO → EmotionNet) sees them.
+
+**Why it matters.**
+- Converts gap insights into targeted assets (lighting, viewpoint, motion, demographic strata).
+- Speeds recall uplift with small, surgical additions instead of blunt dataset growth.
+- Enforces provenance, licensing, and synthetic caps to prevent distribution drift.
+
+**Scope.**
+- Input: `evaluation.gap_report.v1`, `observability.data_drift.v1`.
+- Output: new **temp** clips (`/videos/temp/*.mp4`), thumbs, and `gapfill.artifact_ready.v1` events.
+- Registration via Media Mover (`POST /media/register`) with checksums and provenance.
+- Optional synthetic generation uses a **separate** provider; **TAO is not involved in generation**.
+
+**Non-goals.**
+- No direct writes to `train/` or `test/`.
+- No model training/export—handled by TAO/EmotionNet via Training Orchestrator.
+
+**Zero-trust boundaries.**
+- All artifacts tagged: `origin ∈ {"real","synthetic"}`; if synthetic, include `generator = {provider, version}`.
+- Enforce `SYNTH_MAX_CLASS_SHARE` (default ≤30%) per label over any training window.
+- Block promotion if `license_json` or required consent flags are missing.
+
+**Reference flow (n8n, high level).**
+1. **Webhook** `/agent/gap-fill/gap-report` → validate signature.
+2. **Function**: explode gaps → task specs (emotion, scene, lighting, camera, motion, demographics).
+3. **Branch A (Acquire)**: partner pull / controlled capture / consented scrape.
+4. **Branch B (Optional Synthesize)**: call configured generator (local service or external API).
+5. **Write**: save MP4 under `/videos/temp/{uuid}.mp4`; create thumb via ffmpeg.
+6. **HTTP**: `POST /media/register` with metadata (origin, checksum, prompt/acq JSON, license JSON).
+7. **Postgres**: upsert `gapfill_requests` and link to `video_assets`.
+8. **Emit**: `gapfill.artifact_ready.v1` to Promotion/Curation queue.
+9. **Audit**: append to Reconciler/Audit logs.
+
+**Inputs (schemas).**
+```json
+// evaluation.gap_report.v1 (excerpt)
+{
+  "version": "1",
+  "run_id": "mlflow:9f2a",
+  "weak_classes": [
+    {
+      "label":"sad",
+      "support":72,
+      "recall":0.62,
+      "target_n":100,
+      "context":{"lighting":"low","camera":"profile","motion":"head_turn"}
+    }
+  ],
+  "notes":"Profile + low light underperforming."
+}
+```
+```json
+// gapfill.task.v1 (internal)
+{
+  "task_id":"gap_0e8d",
+  "label":"sad",
+  "strategy":"acquire|synthesize",
+  "spec":{
+    "scene":"indoor, dim warm",
+    "camera":"profile",
+    "motion":"head_turn",
+    "duration_s":4
+  },
+  "provenance_plan":{"origin":"real|synthetic","policy_tag":"ds_v1"}
+}
+```
+
+**Outputs.**
+```json
+// gapfill.artifact_ready.v1
+{
+  "task_id":"gap_0e8d",
+  "video_id":"vid_5c1b",
+  "path":"/videos/temp/vid_5c1b.mp4",
+  "thumb":"/thumbs/vid_5c1b.jpg",
+  "origin":"real",
+  "label":"sad",
+  "acq_json":{ "source":"partner_xyz","capture_id":"cap_77" },
+  "checksum_sha256":"…",
+  "license_json":{"agreement_id":"L-2025-014","terms_version":"2025-09"},
+  "next":"promotion.review"
+}
+```
+
+**KPIs.**
+- Recall uplift on targeted labels within N training cycles.
+- % of artifacts promoted (pass human review + policy).
+- Synthetic share per class over sliding window (should trend down as real data accrues).
```

* * *

Patch: `requirements_08.4.2.md`
===============================

```diff
*** a/requirements_08.4.2.md
--- b/requirements_08.4.2.md
@@
-## Models and Training
-- ActionRecognitionNet fine-tuning via TAO; export to TensorRT.
+## Models and Training
+- **EmotionNet** fine-tuning via TAO; export to TensorRT. TAO is used only for training/evaluation/export; it does not generate data.
@@
-## Agent Set (08.4.2)
+## Agent Set (08.4.2)
 - Ingest
 - Labeling
 - Promotion / Curation
 - Reconciler / Audit
 - Training Orchestrator
 - Evaluation
 - Deployment
 - Privacy / Retention
 - Observability / Telemetry
+- Data Sourcing / Gap-Fill
@@
-### Functional Requirements
+### Functional Requirements
 (existing bullets remain)
 
+#### Data Sourcing / Gap-Fill (Agent 10)
+1. MUST accept `evaluation.gap_report.v1` and `observability.data_drift.v1` and produce **acquisition or synthesis** tasks per weak class/segment.
+2. MUST prioritize **real-world acquisition** (controlled capture, partner pulls, consented scraping) and may **optionally** request synthetic clips from a separate generator.
+3. MUST save artifacts to `/videos/temp/` and generate a thumbnail (ffmpeg) within the same transaction scope.
+4. MUST register artifacts via Media Mover `POST /media/register` with fields: `origin ∈ {"real","synthetic"}`, `checksum_sha256`, `prompt_json` or `acq_json`, `license_json`, and `generator` (if synthetic).
+5. MUST emit `gapfill.artifact_ready.v1` to Promotion/Curation and SHALL NOT write to `train/`/`test/` directly.
+6. MUST enforce a configurable cap `SYNTH_MAX_CLASS_SHARE` (default 0.30) per label across any training window; violations block promotion.
+7. SHOULD attach an MLflow tag on the next training run noting `synthetic_share_per_class` and a short excerpt of `prompt_json`/`acq_json` used.
+8. SHOULD support retries with exponential backoff and circuit-breaker behavior for external providers.
@@
 ### Non-Functional Requirements
 (existing bullets remain)
+– Provenance: every artifact must be traceable to source with immutable checksum.  
+– Compliance: assets without `license_json` or consent flags are rejected.  
+– Latency: P95 end-to-end acquisition/registration ≤ 2 minutes for local/partner pulls (synthesis may exceed and is queued).  
+– Observability: emit structured logs/events for each task state (`queued`, `in_progress`, `registered`, `rejected`).  
@@
 ### Environment Variables (.env)
 (existing variables remain)
+
+# Gap-Fill Agent (acquisition + optional synthesis)
+GAPFILL_WEBHOOK_SECRET="change-me"
+SYNTH_MAX_CLASS_SHARE="0.30"
+VGEN_PROVIDER="local|runway|luma|stub"
+VGEN_BASE_URL="http://10.0.4.140:9009"
+VGEN_API_KEY="***"
+VGEN_CALLBACK_URL="http://10.0.4.130:8011/agent/gap-fill/callback"
@@
 ### FastAPI (Media Mover) – Endpoints
 (existing endpoints remain)
+
+POST /media/register
+  - Registers a new clip (temp) with metadata and checksum; returns `video_id` + URL(s).
+  - Validates `origin`, `license_json`, and optional `generator` block.
+
+POST /agent/gap-fill/callback    (optional, if synthesis provider pushes)
+  - HMAC-signed callback; writes artifact to `/videos/temp/`, makes thumb, calls `/media/register`, links `gapfill_requests`.
@@
 ### Postgres – Tables / DDL
 (existing DDL remains)
+
+-- Provenance extensions
+ALTER TABLE video_assets
+  ADD COLUMN IF NOT EXISTS origin TEXT CHECK (origin IN ('real','synthetic')) DEFAULT 'real',
+  ADD COLUMN IF NOT EXISTS generator JSONB,      -- if synthetic: {provider, version, job_id?}
+  ADD COLUMN IF NOT EXISTS prompt_json JSONB,    -- if synthetic
+  ADD COLUMN IF NOT EXISTS acq_json JSONB,       -- if acquired (source, capture_id, partner, etc.)
+  ADD COLUMN IF NOT EXISTS license_json JSONB;   -- consent/license details
+
+-- Track gap-fill requests and link to eventual artifact
+CREATE TABLE IF NOT EXISTS gapfill_requests (
+  request_id TEXT PRIMARY KEY,
+  created_at TIMESTAMPTZ DEFAULT now(),
+  label TEXT NOT NULL,
+  strategy TEXT CHECK (strategy IN ('acquire','synthesize')) NOT NULL,
+  prompt_json JSONB,
+  acq_json JSONB,
+  constraints_json JSONB,
+  status TEXT NOT NULL DEFAULT 'pending',
+  provider TEXT,             -- if synthetic
+  provider_job_id TEXT,      -- if synthetic
+  artifact_video_id TEXT REFERENCES video_assets(video_id)
+);
+
+-- Optional: class-level synthetic share guardrail (materialized view or trigger logic defined in DB section)
+-- (Implementation detail left to DB scripts; requirement enforced at Promotion/Curation boundary.)
@@
 ### n8n – Workflows (IDs and Triggers)
 (existing workflows remain)
+
+**wf_gap_fill**  
+Trigger: Webhook `POST /agent/gap-fill/gap-report` (HMAC required)  
+Nodes (high-level):
+1. *Function*: parse gap_report; explode to tasks (acquire or synthesize).
+2. *IF acquire*: partner API / collector / consented scrape → fetch asset(s).
+3. *IF synthesize*: HTTP `${VGEN_BASE_URL}/v1/generate` with `${VGEN_API_KEY}`; optionally await `${VGEN_CALLBACK_URL}`.
+4. *Move Binary File*: write `/videos/temp/${uuid}.mp4`.
+5. *Execute Command*: `ffmpeg -ss 00:00:00.5 -i $file -frames:v 1 $thumb`.
+6. *HTTP*: `POST http://10.0.4.130:8011/media/register` with provenance JSON.
+7. *Postgres*: upsert `gapfill_requests` + link `video_assets`.
+8. *Webhook Respond*: return `gapfill.artifact_ready.v1`.
+9. *HTTP*: notify Promotion/Curation (`/agent/promotion/queue`).
@@
 ### Security & Compliance
 (existing bullets remain)
+– Enforce `origin` + `license_json` presence; block otherwise.  
+– HMAC signatures on `/agent/gap-fill/gap-report` and `/agent/gap-fill/callback`; secrets rotated quarterly.  
+– Synthetic cap per class enforced at promotion time; dashboard shows rolling 30-day share.  
@@
 ### Metrics / MLflow
 (existing bullets remain)
+– Log `synthetic_share_per_class` and `gapfill_contribution` (count per label) as run tags on EmotionNet training cycles.  
+– Track recall uplift for targeted labels across successive runs; attribute uplift to Gap-Fill where applicable.  
```

* * *

If you want, I can also generate a minimal SQL migration file and an n8n import JSON matching these names and env vars so you can drop them in without hand-editing.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)