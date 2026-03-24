# Project Reachy — Files & Components Inventory

**Last Updated:** 2026-03-19  
**Purpose:** Comprehensive listing of React website, Streamlit web app, ML pipeline, and n8n workflow files with functional descriptions.

---

## 1. React Marketing Website

**Location:** `apps/web/dev/`  
**Framework:** React 18.3 + Vite 5.4 + TailwindCSS 3.4 + React Router 6.26  
**Deployment:** GitHub Pages via `gh-pages` package  
**Status:** ✅ **VALIDATED** — Structure is stable and production-ready

### 1.1 Core Configuration Files

- **`apps/web/dev/package.json`** — NPM dependencies (React, Vite, TailwindCSS, Lucide icons, gh-pages deployment).
- **`apps/web/dev/vite.config.js`** — Vite build configuration with React plugin.
- **`apps/web/dev/tailwind.config.js`** — TailwindCSS theme customization (3052 bytes of custom utilities and color schemes).
- **`apps/web/dev/postcss.config.js`** — PostCSS configuration for TailwindCSS processing.
- **`apps/web/dev/index.html`** — HTML entry point with meta tags and root div mount.

### 1.2 Application Entry & Routing

- **`apps/web/dev/src/main.jsx`** — React application bootstrap, renders `App` component into DOM.
- **`apps/web/dev/src/App.jsx`** — Main application component with HashRouter, route definitions, Layout wrapper, and ScrollToTop utility.
- **`apps/web/dev/src/index.css`** — Global CSS with TailwindCSS directives and custom styles.

### 1.3 Page Components

- **`apps/web/dev/src/pages/HomePage.jsx`** — Landing page with hero section, animated waveform visualization, feature showcase, EQ gauge demo, and CTA sections.
- **`apps/web/dev/src/pages/TechnologyPage.jsx`** — Technical deep-dive on EfficientNet-B0, HSEmotion pre-training, DeepStream/TensorRT pipeline, and Phase 2 Emotional Intelligence Layer.
- **`apps/web/dev/src/pages/ArchitecturePage.jsx`** — System architecture overview with three-node diagram, agent orchestration, data flow, and deployment gates.
- **`apps/web/dev/src/pages/PrivacySafetyPage.jsx`** — Privacy-by-design principles, GDPR compliance, local-first processing, and ethical guidelines.
- **`apps/web/dev/src/pages/UseCasesPage.jsx`** — Real-world applications (companion robotics, healthcare, education, retail).
- **`apps/web/dev/src/pages/AboutPage.jsx`** — Project background, team information, and research context.
- **`apps/web/dev/src/pages/ContactPage.jsx`** — Contact form and project links.

### 1.4 Reusable Components

- **`apps/web/dev/src/components/Navbar.jsx`** — Fixed navigation bar with scroll effects, mobile menu, gradient logo, and route links.
- **`apps/web/dev/src/components/Footer.jsx`** — Site footer with social links, copyright, and project metadata.
- **`apps/web/dev/src/components/LogoSVG.jsx`** — Project logo as SVG component with gradient styling.
- **`apps/web/dev/src/components/AnimatedBackground.jsx`** — Visual effects (GradientOrbs, GridOverlay, ParticleField, AnimatedBorderCard) for hero sections.
- **`apps/web/dev/src/components/EQGauge.jsx`** — Interactive emotional intelligence calibration gauge visualization.
- **`apps/web/dev/src/components/GestureModulationShowcase.jsx`** — Gesture expressiveness tier visualization (5-tier confidence-based modulation).

### 1.5 Custom Hooks

- **`apps/web/dev/src/hooks/useReveal.jsx`** — Intersection Observer hook for scroll-triggered animations and counter animations.

---

## 2. Streamlit Web Application

**Location:** `apps/web/pages/`  
**Framework:** Streamlit (Python)  
**Purpose:** Internal ML operations dashboard for video generation, labeling, training, deployment, and model evaluation.

### 2.1 Core Pages

- **`apps/web/pages/00_Home.py`** — Dashboard home with system status, recent activity, and quick links (13,866 bytes).
- **`apps/web/pages/01_Generate.py`** — Video generation interface for Luma/Runway API integration (2,079 bytes).
- **`apps/web/pages/02_Label.py`** — Human-in-the-loop labeling interface with class balance tracking (4,886 bytes).
- **`apps/web/pages/03_Train.py`** — Training launch page for EfficientNet-B0 fine-tuning with hyperparameter controls (13,167 bytes).
- **`apps/web/pages/04_Deploy.py`** — Deployment management for TensorRT engine promotion to Jetson (1,438 bytes).
- **`apps/web/pages/05_Video_Management.py`** — Video library browser with promotion, deletion, and metadata editing (3,963 bytes).

### 2.2 Advanced ML Pages

- **`apps/web/pages/06_Dashboard.py`** — Run-level results dashboard displaying Gate A metrics (F1, ECE, Brier, confusion matrices) for training/validation/test runs (16,199 bytes).
- **`apps/web/pages/07_Fine_Tune.py`** — **Variant 2** fine-tuning page with 25+ tuneable hyperparameters, config overrides backend, AffectNet test button, and dataset overview (30,979 bytes).
- **`apps/web/pages/08_Compare.py`** — Direct model comparison tool for evaluating Base vs Variant 1 vs Variant 2 against fixed AffectNet test dataset (19,625 bytes).
- **`apps/web/pages/09_EQ_Calibration.py`** — Emotional Intelligence (EQ) calibration metrics dashboard with ECE, Brier, MCE visualizations (11,082 bytes).

---

## 3. FastAPI Gateway & Media Mover

**Location:** `apps/api/`  
**Framework:** FastAPI 0.110+ with Pydantic v2, SQLAlchemy 2.0+, PostgreSQL 16  
**Purpose:** RESTful API gateway for video ingestion, promotion, training control, and WebSocket cues.

### 3.1 Core Application Files

- **`apps/api/app/main.py`** — FastAPI application factory with router registration, CORS, middleware, and startup/shutdown hooks.
- **`apps/api/app/config.py`** — Application configuration with environment variable loading.
- **`apps/api/app/settings.py`** — Settings management with validation.
- **`apps/api/app/deps.py`** — Dependency injection providers for database sessions and services.

### 3.2 Database Layer

- **`apps/api/app/db/models.py`** — SQLAlchemy ORM models (Video, ExtractedFrame, LabelEvent, PromotionLog, TrainingRun, DeploymentLog, etc.).
- **`apps/api/app/db/enums.py`** — Database enums (EmotionLabel, Split, RunStatus, etc.).
- **`apps/api/app/db/session.py`** — Async database session factory and connection pooling.
- **`apps/api/app/db/base.py`** — SQLAlchemy declarative base.

### 3.3 API Routers (Endpoints)

- **`apps/api/app/routers/ingest.py`** — Video ingestion endpoints (`POST /api/v1/ingest/pull`, `/upload`, `/register`) supporting n8n Ingest Agent with SHA256 deduplication and ffprobe metadata extraction.
- **`apps/api/app/routers/promote.py`** — Promotion endpoints (`POST /api/v1/promote/stage`, `/sample`) with dry-run preview and atomic filesystem operations.
- **`apps/api/app/routers/media_v1.py`** — Media management endpoints (`GET /api/v1/media/list`, `POST /api/v1/media/promote`) for canonical promotion workflow.
- **`apps/api/app/routers/training_control.py`** — Training orchestration endpoint (`POST /api/v1/training/launch`) that spawns EfficientNet-B0 fine-tuning subprocess.
- **`apps/api/app/routers/gateway_upstream.py`** — Upstream gateway endpoints for Jetson emotion events and LLM inference routing.
- **`apps/api/app/routers/websocket_cues.py`** — WebSocket endpoint (`/ws/cues/{device_id}`) for real-time gesture cue delivery to Jetson.
- **`apps/api/app/routers/dialogue.py`** — LLM dialogue endpoints for empathetic response generation.
- **`apps/api/app/routers/health.py`** — Health check endpoints (`/healthz`, `/readyz`).
- **`apps/api/app/routers/metrics.py`** — Prometheus metrics endpoint (`/metrics`).
- **`apps/api/app/routers/observability.py`** — Observability endpoints for system telemetry.

### 3.4 Services & Business Logic

- **`apps/api/app/services/promote_service.py`** — Promotion service with transaction management, validation, and rollback support.
- **`apps/api/app/services/video_query_service.py`** — Video query service with filtering, pagination, and aggregation.
- **`apps/api/app/services/thumbnail_watcher.py`** — Background service monitoring thumbnail generation.

### 3.5 Filesystem Utilities

- **`apps/api/app/fs/media_mover.py`** — Atomic file operations for video promotion (`stage_to_train`, `copy_to_split`) with FileTransition tracking and rollback support.

### 3.6 Schemas (Pydantic Models)

- **`apps/api/app/schemas/video.py`** — Video request/response schemas.
- **`apps/api/app/schemas/promote.py`** — Promotion request/response schemas.
- **`apps/api/app/schemas/dialogue.py`** — LLM dialogue schemas.
- **`apps/api/app/schemas/responses.py`** — Standard API response wrappers.

### 3.7 Repositories

- **`apps/api/app/repositories/video_repository.py`** — Video database access layer with async SQLAlchemy queries.

### 3.8 Utilities

- **`apps/api/app/manifest.py`** — Manifest generation utilities for JSONL dataset manifests.
- **`apps/api/app/metrics.py`** — Prometheus metrics definitions.
- **`apps/api/app/metrics_registry.py`** — Metrics registry singleton.

---

## 4. ML Training Pipeline

**Location:** `trainer/`  
**Framework:** PyTorch 2.0+ with timm, albumentations, MLflow  
**Purpose:** EfficientNet-B0 fine-tuning, dataset preparation, evaluation, and TensorRT export.

### 4.1 Core Training Scripts

- **`trainer/train_efficientnet.py`** — CLI entry point for EfficientNet-B0 training with config file support.
- **`trainer/run_efficientnet_pipeline.py`** — End-to-end pipeline orchestrator (dataset prep → training → evaluation → export) called by web UI.

### 4.2 Fine-Tuning Module (`trainer/fer_finetune/`)

- **`trainer/fer_finetune/config.py`** — Training configuration dataclasses (TrainingConfig, ModelConfig, DataConfig) with YAML serialization.
- **`trainer/fer_finetune/model_efficientnet.py`** — EfficientNet-B0 model wrapper with HSEmotion weight loading and custom classification head.
- **`trainer/fer_finetune/dataset.py`** — PyTorch Dataset for video frame loading with albumentations augmentation pipeline.
- **`trainer/fer_finetune/train_efficientnet.py`** — Two-phase training loop (frozen backbone → selective unfreezing) with mixed precision and mixup.
- **`trainer/fer_finetune/evaluate.py`** — Evaluation script computing F1, balanced accuracy, ECE, Brier score, and confusion matrices.
- **`trainer/fer_finetune/export.py`** — ONNX export with TensorRT conversion utilities.

### 4.3 Dataset Preparation

- **`trainer/prepare_dataset.py`** — `DatasetPreparer` class for run-specific frame extraction (10 frames/video), face detection, manifest generation, and dataset hashing.
- **`trainer/split_run_dataset.py`** — Train/validation splitting utility (90/10 split) for run-scoped datasets.
- **`trainer/data_roots.py`** — Data path resolution utilities.

### 4.4 Validation & Tracking

- **`trainer/gate_a_validator.py`** — Gate A threshold validation (F1 ≥ 0.84, balanced accuracy ≥ 0.85, ECE ≤ 0.08, Brier ≤ 0.16).
- **`trainer/mlflow_tracker.py`** — MLflow experiment tracking with dataset hash logging, artifact upload, and metric recording.
- **`trainer/validation.py`** — Validation utilities for model checkpoints.

### 4.5 Legacy/Alternative Models

- **`trainer/train_resnet50.py`** — ResNet-50 training script (superseded by EfficientNet-B0, see ADR 006).
- **`trainer/train_emotionnet.py`** — NVIDIA TAO EmotionNet training script (deprecated, domain mismatch).

---

## 5. n8n Workflow Automation

**Location:** `n8n/workflows/`  
**Framework:** n8n (self-hosted workflow automation)  
**Purpose:** Ten-agent orchestration system for ML pipeline automation.

### 5.1 Documentation

- **`n8n/README.md`** — n8n setup guide, environment variables, and workflow import instructions (12,103 bytes).
- **`n8n/AGENT_SUMMARIES.md`** — Comprehensive summaries of all 9 agents with responsibilities, benefits, and workflow files (15,426 bytes).
- **`n8n/AGENTIC_SYSTEM_OVERVIEW.md`** — System architecture overview, agent interactions, and data flow diagrams (16,889 bytes).
- **`n8n/DELIVERY_SUMMARY.md`** — Project delivery status, completion metrics, and production readiness checklist (14,595 bytes).

### 5.2 Production Workflows (ml-agentic-ai_v.2/)

**Status:** ✅ **PRODUCTION-READY** — First three agents confirmed functional, remaining agents validated.

- **`n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`** — **Agent 1: Ingest Agent** — Video ingestion with SHA256 deduplication, ffprobe metadata extraction, and thumbnail generation.
- **`n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`** — **Agent 2: Labeling Agent** — Human labeling workflow with class balance enforcement and audit trail.
- **`n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`** — **Agent 3: Promotion/Curation Agent** — Dry-run promotion preview, human approval gate, atomic filesystem operations, and manifest rebuild.
- **`n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`** — **Agent 4: Reconciler/Audit Agent** — Daily filesystem ↔ database drift detection with email reports.
- **`n8n/workflows/ml-agentic-ai_v.2/05_training_orchestrator_efficientnet.json`** — **Agent 5: Training Orchestrator** — EfficientNet-B0 fine-tuning trigger with MLflow tracking and Gate A validation.
- **`n8n/workflows/ml-agentic-ai_v.2/06_evaluation_agent_efficientnet.json`** — **Agent 6: Evaluation Agent** — Test set evaluation with calibration metrics and confusion matrix generation.
- **`n8n/workflows/ml-agentic-ai_v.2/07_deployment_agent_efficientnet.json`** — **Agent 7: Deployment Agent** — ONNX → TensorRT conversion, Jetson deployment, and Gate B validation.
- **`n8n/workflows/ml-agentic-ai_v.2/08_privacy_agent.json`** — **Agent 8: Privacy/Retention Agent** — TTL-based purging and GDPR compliance enforcement.
- **`n8n/workflows/ml-agentic-ai_v.2/09_observability_agent.json`** — **Agent 9: Observability/Telemetry Agent** — Prometheus metrics aggregation and Grafana dashboard updates.
- **`n8n/workflows/ml-agentic-ai_v.2/10_ml_pipeline_orchestrator.json`** — **Agent 10: ML Pipeline Orchestrator** — Master workflow coordinating all agents with event-driven triggers.

### 5.3 Legacy Workflows

- **`n8n/workflows/ml-agentic-ai_v.1/`** — ResNet-50 workflows (4 files, superseded by v.2 EfficientNet-B0).
- **`n8n/workflows/initial workflows/`** — Prototype workflows (9 files, archived).

---

## 6. Key Functions & Capabilities

### 6.1 Ingestion & Pre-processing

- **`pull_video()` in `apps/api/app/routers/ingest.py`** — Downloads video from URL, computes SHA256, extracts metadata with ffprobe, generates thumbnail.
- **`register_local_video()` in `apps/api/app/routers/ingest.py`** — Registers pre-existing video on disk without download.
- **`DatasetPreparer.prepare_run_dataset()` in `trainer/prepare_dataset.py`** — Extracts 10 random frames per video with face detection, generates run-scoped manifests.

### 6.2 Promotion & Logging

- **`PromoteService.stage_to_train()` in `apps/api/app/services/promote_service.py`** — Atomic promotion from `temp/` to `train/<label>/` with transaction rollback support.
- **`FileMover.stage_to_train()` in `apps/api/app/fs/media_mover.py`** — Filesystem-level atomic move operation with idempotency.
- **`rebuild_manifest()` in `apps/api/app/manifest.py`** — Generates JSONL manifests with dataset hash for MLflow lineage.

### 6.3 Fine-Tuning

- **`train_efficientnet_two_phase()` in `trainer/fer_finetune/train_efficientnet.py`** — Two-phase training: frozen backbone (epochs 1-5) → selective unfreezing (blocks.5, blocks.6, conv_head).
- **`load_hsemotion_weights()` in `trainer/fer_finetune/model_efficientnet.py`** — Loads HSEmotion `enet_b0_8_best_vgaf` pre-trained weights.
- **`launch_training()` in `apps/api/app/routers/training_control.py`** — Spawns training subprocess with config overrides from web UI.

### 6.4 Model Dashboards & Gate A

- **`validate_gate_a()` in `trainer/gate_a_validator.py`** — Validates F1 ≥ 0.84, balanced accuracy ≥ 0.85, ECE ≤ 0.08, Brier ≤ 0.16.
- **`compute_calibration_metrics()` in `trainer/fer_finetune/evaluate.py`** — Computes ECE (Expected Calibration Error), Brier score, MCE (Maximum Calibration Error).
- **`render_dashboard()` in `apps/web/pages/06_Dashboard.py`** — Displays confusion matrices, per-class F1, calibration curves, and Gate A pass/fail status.

### 6.5 Model Comparison

- **`compare_models()` in `apps/web/pages/08_Compare.py`** — Side-by-side comparison of Base, Variant 1, Variant 2 against fixed AffectNet test dataset with statistical significance tests.

---

## 7. React Website Validation Summary

### Structure Assessment: ✅ **STABLE & PRODUCTION-READY**

**Strengths:**

- Modern React 18 + Vite 5 stack with fast HMR and optimized builds
- Responsive design with TailwindCSS 3.4 and mobile-first approach
- HashRouter for GitHub Pages compatibility (no server-side routing required)
- Modular component architecture with reusable UI elements
- Smooth scroll animations with Intersection Observer
- Lucide React icons for consistent iconography
- Automated deployment via `gh-pages` package

**Architecture Validation:**

- ✅ Clear separation of pages, components, and hooks
- ✅ Centralized routing in `App.jsx` with Layout wrapper
- ✅ Consistent styling with gradient theme and dark background
- ✅ Accessibility considerations (semantic HTML, ARIA labels)
- ✅ Performance optimizations (lazy loading, code splitting via Vite)

**Deployment Pipeline:**

- Build: `npm run build` → Vite bundles to `dist/`
- Deploy: `npm run deploy` → `gh-pages` pushes to GitHub Pages
- Preview: `npm run preview` → Local preview of production build

**No Critical Issues Detected** — Website structure is ready for production deployment.

---

## 8. Project Status Summary

### Web App (Streamlit)

- ✅ Fine-tuning page (07_Fine_Tune.py) with 25+ hyperparameters
- ✅ ML data pipeline complete (ingestion, pre-processing, promotion, logging)
- ✅ Model dashboards (06_Dashboard.py, 08_Compare.py, 09_EQ_Calibration.py)
- ✅ Gate A threshold validation with statistical displays

### Workflow Automation (n8n)

- ✅ **Agent 1 (Ingest):** Confirmed functional, production-ready
- ✅ **Agent 2 (Labeling):** Confirmed functional, production-ready
- ✅ **Agent 3 (Promotion):** Confirmed functional, production-ready
-  Agents 4-10: part of Phases 2 & 3 (not included in capstone project)

### ML Pipeline

- ✅ EfficientNet-B0 fine-tuning with HSEmotion weights
- ✅ Per-run frame extraction (10 frames/video)
- ✅ MLflow lineage tracking with dataset hashes
- ✅ Gate A validation (F1, ECE, Brier, balanced accuracy)

---

**Maintained by:** Russell Bray (rustybee255@gmail.com)  
**Project Version:** 0.09.2 (Reachy_EQ_PPE_Degree_Mini_01)  
**Last Validated:** 2026-03-19
