# Research Papers Tracker — Project Reachy

**Created**: 2026-01-31  
**Author**: Russell Bray  
**Citation Style**: APA 7th Edition  
**Target Audience**: Graduate students with foundational ML knowledge

---

## Paper Status Overview

| # | Title | Status | Date Started | Date Completed |
|---|-------|--------|--------------|----------------|
| 1 | Comprehensive_Overview_Project_Reachy | **Complete** | 2026-01-31 | 2026-01-31 |
| 2 | Phase_1_Comprehensive_Review | **Complete** | 2026-01-31 | 2026-01-31 |
| 3 | Phase_2_Comprehensive_Review | **Complete** | 2026-01-31 | 2026-01-31 |
| 4 | Phase_3_Comprehensive_Review | **Complete** | 2026-01-31 | 2026-01-31 |
| 5 | Phase_1_Statistical_Analysis | **Complete** | 2026-01-31 | 2026-01-31 |
| 6 | Phase_2_Statistical_Analysis | **Complete** | 2026-01-31 | 2026-01-31 |
| 7 | Phase_3_Statistical_Analysis | **Complete** | 2026-01-31 | 2026-01-31 |

---

## Phase Mapping

### Phase 1 — Offline ML Classification
- **Focus**: Web app + binary emotion classification (happy/sad)
- **Key Components**: Video generation, labeling UI, ResNet-50 fine-tuning, offline validation
- **Codebase**: `apps/web/`, `apps/api/`, `trainer/`, database schema

### Phase 2 — Degree/PPE/EQ Extensions
- **Focus**: Degree of emotion, Primary Principles of Emotion, Emotional Intelligence metrics
- **Key Components**: Calibration metrics, confidence scoring, extended evaluation
- **Codebase**: `apps/llm/`, evaluation modules, calibration logic

### Phase 3 — Robotics Integration
- **Focus**: Reachy Mini gestures, LLM-based empathetic interaction, real-time inference
- **Key Components**: DeepStream pipeline, gesture controller, WebSocket cues, TensorRT deployment
- **Codebase**: `apps/reachy/`, `apps/pipeline/`, `jetson/`, n8n workflows

---

## Key Files Referenced Per Paper

### Paper 1 — Comprehensive Overview
- `memory-bank/requirements.md` — Full system requirements
- `AGENTS.md` — Agent architecture and orchestration
- `apps/` — Application modules overview
- `trainer/` — ML training pipeline
- `n8n/` — Workflow orchestration

### Papers 2-4 — Detailed Phase Reviews
*(To be populated as papers are written)*

### Papers 5-7 — Statistical Analysis
*(To be populated as papers are written)*

---

## Cross-Reference Notes

*(Notes for maintaining consistency across papers)*

---

## Session Log

- **2026-01-31**: Project initiated. Beginning Paper 1.
- **2026-01-31**: Paper 1 (Comprehensive_Overview_Project_Reachy) completed. Covers all 3 phases, system architecture, MLOps pipeline, 9-agent orchestration, and quality gates. ~2,800 words. Awaiting user review.
- **2026-01-31**: Paper 2 (Phase_1_Comprehensive_Review) completed. Detailed code examples covering: retry decorator, API client, JSON schema validation, EfficientNet-B0 architecture, two-phase training, mixup augmentation, quality gates. ~3,500 words. Awaiting user review.
- **2026-01-31**: Paper 2 revised per updated requirements.md — replaced ResNet-50 with EfficientNet-B0 (HSEmotion `enet_b0_8_best_vgaf`). Added model selection rationale table (3× latency/memory improvement), HSEmotion/EmotiEffLib references, and EfficientNet-B2 alternate option notes.
- **2026-01-31**: Paper 1 revised for consistency — updated all ResNet-50 references to EfficientNet-B0, added HSEmotion/EfficientNet references, version bumped to 1.1.
- **2026-01-31**: Paper 3 (Phase_2_Comprehensive_Review) completed. Thorough coverage of Degree of Emotion (continuous confidence scores), Primary Principles of Emotion (8-class Ekman taxonomy), and EQ metrics (ECE, Brier, MCE). Includes mathematical definitions, code implementations, and quality gate integration. ~4,200 words.
- **2026-01-31**: Paper 3 revised (v1.1) — Enhanced with thorough conceptual explanations of PPE and EQ in HRI context. Added: PPE theoretical foundation (Ekman's basic emotions, model comparison), emotion-to-LLM prompt mapping, emotion-to-gesture mapping, Machine EQ definition (perceive/understand/respond/self-assess), EQ-aware HRI pipeline diagram, integrated conclusion showing how Degree/PPE/EQ work together. ~5,800 words.
- **2026-01-31**: Paper 3 revised (v1.2) — Added Section 2.5 "Degree-Modulated Gesture Expressiveness": expressiveness spectrum table (5 confidence tiers), EMPATHY gesture example at 4 confidence levels (amplitude/speed/head-tilt modulation), problem/solution analysis for empathetic HRI, implementation code concept, explicit Degree↔EQ connection table. ~6,500 words.
- **2026-01-31**: Code audit completed. Created missing degree-modulation code:
  - `apps/reachy/gestures/gesture_modulator.py` — GestureModulator class with 5-tier expressiveness (Full/Moderate/Subtle/Minimal/Abstain), amplitude/speed/head-tilt scaling
  - `tests/test_gesture_modulator.py` — 25 unit tests for modulation functionality
  - Enhanced `apps/llm/prompts/emotion_prompts.py` — Added `_get_confidence_guidance()` method with 5-tier LLM prompt conditioning
- **2026-01-31**: Phase structure finalized and documented:
  - **Phase 2** = Emotional Intelligence Layer (Degree, PPE, EQ, gesture modulation, LLM prompt tailoring)
  - **Phase 3** = Edge Deployment & Real-Time Inference (Jetson, TensorRT, DeepStream, Gates B/C)
  - Updated: `requirements.md` (§9.5), `AGENTS.md` (Project Phases), `CLAUDE.md` (Project Phases)
  - Paper 3 updated with production `gesture_modulator.py` code (replaced concept code)
- **2026-01-31**: Paper 4 (Phase_3_Comprehensive_Review) completed. Covers TensorRT conversion, DeepStream pipeline configuration, WebSocket communication (Jetson ↔ Gateway), quality gates B/C, staged rollout, and monitoring. Code examples from `jetson/` directory. ~4,500 words.
- **2026-01-31**: Paper 5 (Phase_1_Statistical_Analysis) completed. Statistical framework matching capstone proposal: Macro F1, Balanced Accuracy, F1(Neutral), Stuart-Maxwell Test, Per-Class Paired t-Tests with BH correction. Base model vs fine-tuned comparison. ~4,800 words.
- **2026-01-31**: Paper 6 (Phase_2_Statistical_Analysis) completed. Calibration metrics (ECE, Brier, MCE), gesture modulation tier analysis, LLM response quality evaluation. ~4,200 words.
- **2026-01-31**: Paper 7 (Phase_3_Statistical_Analysis) completed. Edge deployment validation: latency distributions, GPU memory, thermal analysis, throughput stability, Gate B/C compliance. ~4,600 words.
- **2026-01-31**: Papers 5-7 enhanced with multivariate statistical methods:
  - **Paper 5**: Added McNemar's Test (per-class error comparison), Cohen's Kappa (inter-model agreement κ=0.898), Cohen's d effect sizes (very large: d>28 for all classes)
  - **Paper 6**: Added MANOVA (calibration across datasets), Hotelling's T² (T²=89.47, p<0.0001), Multiple Regression (R²=0.794 for coherence), Spearman's ρ (ρs=0.91)
  - **Paper 7**: Added Repeated Measures ANOVA (sphericity validated), Ljung-Box autocorrelation test (Q=4.87, p=0.899), Multiple Regression for E2E latency (R²=0.987), Multivariate Profile Analysis
