---
title: "Iterative Model Selection for Privacy-First Emotion Recognition"
author: "Russell Bray"
date: "May 2026"
geometry: margin=1in
fontsize: 12pt
linestretch: 2
---

\begin{titlepage}
\begin{center}
\vspace*{2cm}
{\Large\textbf{ITERATIVE MODEL SELECTION FOR PRIVACY-FIRST EMOTION RECOGNITION:}}\\[0.5cm]
{\Large\textbf{HOW TRAINING DATA COMPOSITION REVERSES TRANSFER LEARNING STRATEGY}}\\[3cm]
{\large A Research Paper}\\[0.5cm]
{\large Presented to the Faculty of the Graduate School}\\[0.3cm]
{\large Loyola University Chicago}\\[1.5cm]
{\large In Partial Fulfillment}\\[0.3cm]
{\large of the Requirements for the Degree of}\\[0.3cm]
{\large Master of Science in Computer Science}\\[3cm]
{\large by}\\[0.5cm]
{\large Russell Bray}\\[0.5cm]
{\large May 2026}\\
\end{center}
\end{titlepage}

\newpage

\begin{center}
{\large\textbf{ACKNOWLEDGMENTS}}
\end{center}

I wish to express my sincere gratitude to the faculty of the Department of Computer Science at Loyola University Chicago for their guidance throughout this program. The interdisciplinary nature of this work---spanning computer vision, machine learning, robotics, and human-computer interaction---reflects the breadth of training I received. I also thank the developers of the HSEmotion framework, the AffectNet dataset, and the open-source PyTorch ecosystem, without which this work would not have been possible. Finally, I am grateful to the Reachy Mini robotics platform community for providing an accessible embodied AI development environment.

\newpage
\tableofcontents
\newpage

**Keywords:** facial emotion recognition, transfer learning, EfficientNet, privacy-first AI, edge deployment, model calibration, temperature scaling, social robotics, synthetic-to-real domain adaptation, mixed-domain training, iterative model selection

\newpage

# Abstract

This paper presents an empirical study of iterative model selection for facial emotion recognition on a companion robot platform, demonstrating that the optimal transfer learning strategy---frozen backbone versus selective fine-tuning---depends critically on training data composition. Using an EfficientNet-B0 backbone pre-trained on VGGFace2 and AffectNet (HSEmotion), two model variants are developed for 3-class emotion classification (happy, sad, neutral) and evaluated across three iterative training regimes: synthetic-only, mixed-domain, and mixed-domain with post-hoc temperature scaling. Under synthetic-only training (86,519 AI-generated frames), the frozen-backbone variant (V1, F1 = 0.781) is preferred over the fine-tuned variant (V2, F1 = 0.780) due to V2's dangerous neutral-to-sad confusion pattern (35.1% error rate) despite near-identical aggregate metrics. However, augmenting the synthetic data with 15,000 real AffectNet photographs reverses the recommendation: V2's fine-tuned backbone adapts to the mixed distribution, achieving F1 = 0.916 (+17.4%) with neutral-to-sad confusion reduced to 5.7%, while V1's frozen backbone improves only to F1 = 0.834. Post-hoc temperature scaling (T = 0.59) corrects V2's calibration regression (ECE: 0.142 to 0.036) without affecting classification predictions. The final model passes all deployment quality gates---the only configuration to do so. A comprehensive statistical analysis using Wilson confidence intervals, Cohen's kappa, coefficient of variation, and composite scoring validates the selection. The system deploys on an NVIDIA Jetson Xavier NX via TensorRT within a privacy-first architecture where no raw video leaves the local network.

\newpage

# Introduction

## Motivation and Background

Social robots deployed in companion, educational, and therapeutic contexts require the ability to perceive and respond to human emotions in real time (Breazeal, 2003; Fong, Nourbakhsh, & Dautenhahn, 2003). Facial expression recognition (FER) provides the primary perceptual channel for inferring a user's affective state and modulating the robot's behavior---selecting appropriate gestures, adjusting conversational tone, and calibrating physical expressiveness. The proliferation of deep learning has transformed FER from a hand-crafted feature engineering problem into a transfer learning problem: pre-trained convolutional networks are fine-tuned on emotion datasets, typically achieving accuracy above 90% on benchmarks such as AffectNet (Mollahosseini, Hasani, & Mahoor, 2017). However, benchmark performance does not guarantee deployment readiness.

This investigation matters for several reasons. First, emotion-aware interaction is a prerequisite for companion robots to be perceived as socially competent; without it, the robot is reduced to a scripted device. Second, deploying machine learning models on edge hardware under strict privacy constraints is a growing real-world requirement that academic benchmarks rarely address. Third, the iterative process of discovering that data composition---not just model architecture---determines the optimal transfer learning strategy has broad implications for any practitioner choosing between freezing and fine-tuning a pre-trained backbone.

My interest in this project originated from the intersection of two passions: robotics and applied machine learning. The Reachy Mini platform offered a unique opportunity to bridge the gap between academic FER benchmarks and a tangible, physical system where misclassification has immediate behavioral consequences---the robot acts on its predictions by gesturing, speaking, and modulating its expressiveness in real time.

The beneficiaries of this work are threefold. Robot end-users benefit from more empathetic and contextually appropriate interactions. The Reachy R&D community benefits from a validated deployment pipeline and quality gate framework. The broader machine learning community benefits from empirical evidence that the freeze-vs-fine-tune decision depends on data composition.

Deploying emotion recognition on a companion robot introduces three challenges beyond conventional computer vision. First, **real-time edge inference** requires latencies below 120 ms per frame on dedicated hardware (NVIDIA Jetson Xavier NX). Second, a **privacy-first architecture** demands that raw video never leaves the local network. Third, **asymmetric error consequences** mean that a robot misidentifying neutral expressions as sadness creates a qualitatively worse experience than one that occasionally misses happiness. These challenges motivate a deployment methodology that goes beyond aggregate accuracy metrics.

The potential broader implications extend beyond robotics. Any application of transfer learning---medical imaging, autonomous driving, content moderation---faces the same freeze-vs-fine-tune decision. This study provides evidence that the answer depends on the compositional relationship between training data and the target domain. Furthermore, the demonstration that classification and calibration quality are separable concerns offers a practical methodology for any system where confidence scores drive downstream behavior.

## Problem Statement

This paper addresses the challenge of selecting and deploying an emotion classification model for a companion robot under constraints of real-time edge inference, strict privacy requirements, and asymmetric error consequences. The central question is: given two transfer learning strategies, how does training data composition affect which strategy is optimal, and can iterative refinement guided by diagnostic quality gates produce a deployment-ready model?

## Research Questions

**RQ1:** How does the choice between frozen-backbone and fine-tuned transfer learning strategies affect real-world emotion classification performance when training data is synthetic?

**RQ2:** Does augmenting synthetic training data with real photographs change which transfer learning strategy is optimal?

**RQ3:** Can post-hoc calibration techniques correct calibration regression introduced by backbone fine-tuning without affecting classification performance?

**RQ4:** Do aggregate classification metrics adequately capture deployment-relevant quality differences between models, or are class-level analyses required?

## Research Contributions

This work makes five contributions: (1) an empirical demonstration that the freeze-vs-fine-tune decision depends on training data composition; (2) evidence that modest real-data augmentation (~15%) closes the synthetic-to-real gap; (3) a practical demonstration that calibration and classification quality are separable concerns; (4) a two-tier quality gate framework that prevented deployment of a model with a dangerous error profile concealed by aggregate metrics; and (5) a comprehensive statistical methodology for deployment decision-making.

## Overview of the Paper

The remainder of this paper is organized as follows. The Method section describes the complete research platform, including hardware, software, data sources, model architecture, and the orchestration system. The Literature Review situates this work within transfer learning, facial emotion recognition, domain adaptation, calibration, and quality gate research, emphasizing how studies build upon one another and identifying the specific gaps this work addresses. The Results and Discussion section presents hypotheses, experimental findings across three iterative phases, comprehensive statistical analysis, and interpretation. Threats to the Validity examines internal, external, and construct validity. Future Work identifies remaining research directions. Reflections addresses lessons learned. The References section provides the complete bibliography, and Appendix A contains all source code used for statistical computation.

\newpage

# Method

This section describes the hardware, software, and data infrastructure, the overall plan of analysis, specialized tools, custom software developed, and unexpected challenges encountered.

## Overall Plan of Analysis

The investigation follows a three-phase iterative design. In Phase 1, two model variants are trained on synthetic data and evaluated on real photographs. In Phase 2, the training data is augmented with real photographs, and both variants are retrained. In Phase 3, post-hoc temperature scaling corrects any calibration regression. At each phase, a diagnostic quality gate framework evaluates deployment readiness, and the specific failures guide the next intervention.

## Hardware Infrastructure

| Node | Role | Hardware | IP |
|------|------|----------|----|
| Ubuntu 1 (Training) | GPU training, FastAPI, PostgreSQL 16, n8n, MLflow | NVIDIA GPU workstation | 10.0.4.130 |
| Ubuntu 2 (Web/UI) | Streamlit frontend, Nginx reverse proxy | General-purpose server | 10.0.4.140 |
| Jetson Xavier NX | Real-time inference, DeepStream + TensorRT | 384-core Volta GPU, 8 GB | 10.0.4.150 |

All processing occurs on-premise. No raw video data is transmitted externally (ADR-003, Privacy-First Architecture).

## Software Stack and Tools

- **Training framework:** Python 3.10, PyTorch 2.x with FP16, `timm`, HSEmotion (`emotiefflib`), scikit-learn
- **Experiment tracking:** MLflow (local instance)
- **Database:** PostgreSQL 16 (`reachy_emotion` database)
- **Web application:** Custom multi-page Streamlit (Dashboard and Compare pages)
- **API layer:** FastAPI (`/api/v1/media/`)
- **Orchestration:** n8n (10 cooperating agents)
- **Edge deployment:** ONNX -> TensorRT FP16 -> DeepStream
- **Statistical analysis:** R 4.x (`ggplot2`, `jsonlite`, `optparse`, `MASS`, `tidyr`); Python (`scipy.stats`, `numpy`)

The codebase comprises approximately 15,000 lines of Python and 900 lines of R. I had to learn n8n workflow automation, DeepStream pipeline configuration, and TensorRT engine conversion---none of which were part of my prior experience.

## Data Sources

***Synthetic data.*** 11,911 AI-generated videos (Luma) yielded 86,519 face-cropped frames:

| Class | Videos | Train Frames | Val Frames |
|-------|--------|-------------|-----------|
| Happy | 3,589 | 26,723 | 8,908 |
| Sad | 5,015 | 35,227 | 11,742 |
| Neutral | 3,307 | 24,569 | 8,190 |
| **Total** | **11,911** | **86,519** | **28,840** |

***Real data.*** 15,000 AffectNet images (5,000/class) for training augmentation; 894 AffectNet images (435 happy, 160 sad, 299 neutral) for independent test evaluation. Test IDs are explicitly excluded from training to prevent leakage.

| Source | Happy | Sad | Neutral | Total |
|--------|-------|-----|---------|-------|
| Synthetic | 26,723 | 35,227 | 24,569 | 86,519 |
| Real AffectNet | 5,000 | 5,000 | 5,000 | 15,000 |
| **Combined** | **31,723** | **40,227** | **29,569** | **101,519** |

## Model Architecture

The EfficientNet-B0 backbone (Tan & Le, 2019) uses the HSEmotion checkpoint (`enet_b0_8_best_vgaf`) pre-trained on VGGFace2 then AffectNet. The 8-class head is replaced with Dropout(p) -> Linear(1280, 3).

| Property | V1 (Frozen) | V2 (Fine-Tuned) |
|----------|------------|-----------------|
| Backbone | Frozen | blocks.5, .6, conv\_head unfrozen |
| Trainable params | ~4,000 | ~500,000 |
| Training phases | Single | Two-phase (frozen -> unfreeze) |
| LR | 1e-4 | 3e-4 (head), 3e-5 (backbone) |
| Label smoothing | 0.15 | 0.10 |
| Dropout | 0.3 | 0.5 |

## Quality Gate Framework

| Metric | A-val (Synthetic) | A-deploy (Real-World) |
|--------|-------------------|----------------------|
| F1 Macro | >= 0.84 | >= 0.75 |
| Balanced Acc | >= 0.85 | >= 0.75 |
| Per-class F1 | >= 0.80 each | >= 0.70 each |
| ECE | <= 0.12 | <= 0.12 |
| Brier | --- | <= 0.16 |

## Evaluation Metrics

Classification: F1 Macro (primary), balanced accuracy, per-class F1, precision, recall, accuracy. Calibration: ECE (10 bins), Brier, MCE. Composite score: $S = 0.50 \times F1_{macro} + 0.20 \times bAcc + 0.15 \times \overline{F1}_{per\text{-}class} + 0.15 \times (1 - ECE)$.

## Orchestration

Although the full Reachy\_Local\_08.4.2 architecture defines 10 cooperating agents, Phase 1 intentionally implements only the first three agents (Ingest, Labeling, Promotion) in production-critical workflows. This is a deliberate *scope control* decision, not a capability gap.

### Why n8n and Agentic Orchestration

n8n provides a visual, event-driven control plane for agentic AI pipelines where each agent is a bounded workflow with explicit inputs, outputs, and retry policies. Architecturally, this creates a directed graph of responsibilities rather than a monolithic script. The practical benefits are:

1. **Deterministic control flow.** Each node in a workflow has explicit branching conditions (`if/else` logic) and failure edges, making execution traceable.
2. **Operational observability.** Every run produces timestamped execution logs tied to workflow IDs, which simplifies debugging across API, file-system, and database boundaries.
3. **Idempotent automation.** Promotion and labeling actions can enforce unique keys and transaction checks before writes, reducing duplicate side effects.
4. **Human-in-the-loop checkpoints.** n8n can pause on approval gates (e.g., dataset promotion), then resume with the same context once approved.

In software engineering terms, each agent behaves like a single-responsibility service: it consumes an event payload, validates preconditions, performs one bounded side effect, and emits a new event. This pattern improves maintainability for junior-to-senior collaboration because control flow is inspectable without stepping through a large asynchronous codebase.

### Phase 1 Agent Scope (1--3 only)

Phase 1 focuses on building a reliable data foundation for 3-class training (`happy`, `sad`, `neutral`). For that objective, only three agents are strictly required:

| Agent | Core Control Flow | Why Required in Phase 1 |
|------|-------------------|-------------------------|
| Ingest | receive clip -> hash -> metadata extract -> thumbnail -> DB record -> emit `ingest.completed` | Creates trustworthy, deduplicated records and provenance for all later steps |
| Labeling | present item -> enforce 3-class policy -> capture human decision -> update counters -> emit label event | Ensures semantic correctness of supervised targets and class-balance awareness |
| Promotion | validate approval + constraints -> move `temp` to `train/<label>` -> log promotion transaction | Converts labeled assets into train-ready filesystem state with auditability |

### Why Limiting to 3/10 Agents Is a Strong Phase 1 Strategy

Restricting Phase 1 to Agents 1--3 is beneficial for both research validity and engineering risk management:

- **Reduces confounding variables.** Early model experiments should fail or succeed based on data and training choices, not on downstream deployment or telemetry complexity.
- **Improves debugging locality.** When only ingest/label/promote are active, root-cause analysis stays close to data lineage. This directly enabled discovery of the face-cropping issue.
- **Builds a stable contract surface.** Later agents (Reconciler, Training, Evaluation, Deployment, Privacy, Observability, Gesture) depend on consistent schemas, paths, and event envelopes produced by the first three.
- **Supports incremental verification.** Phase 1 can validate correctness with concrete invariants: checksum uniqueness, split-label constraints, and promotion audit logs.
- **Controls operational overhead.** Activating all 10 agents prematurely increases failure modes, retry cascades, and maintenance load without improving the core Phase 1 research question.

Therefore, the phased rollout follows a sound agentic AI principle: establish high-integrity data ingress and curation before scaling to full lifecycle automation. In this project, limiting scope to Agents 1--3 made the experimental findings more interpretable and the system more reliable.

## Unexpected Challenges

The most significant challenge was discovering that initial poor test results (F1 ~ 0.43) were caused by missing face cropping, not model inadequacy. Enabling `face_crop=True` nearly doubled performance. A second challenge was calibration regression from mixed-domain fine-tuning (ECE: 0.096 -> 0.142), requiring implementation of temperature scaling. The third was debugging inter-workflow communication in the 10-agent n8n system.

\newpage

# Literature Review

The challenge of building a deployable emotion recognition system draws on several intersecting research areas. This section traces how each area has evolved and how studies relate to one another, building toward the gaps this work addresses.

## Transfer Learning: From Feature Extraction to Discriminative Fine-Tuning

Transfer learning has become the dominant paradigm in computer vision (Zhuang, Qi, Duan, Xi, Zhu, Zhu, Xiong, & He, 2020). The foundational work by Yosinski, Clune, Bengio, and Lipson (2014) demonstrated that features in deep networks transition from general (edge detectors) in early layers to task-specific in later layers. Their key finding---that freezing early layers and fine-tuning later layers outperforms training from scratch---established modern transfer learning methodology. However, they also identified "fragile co-adaptation" between layers, where selective unfreezing can break dependencies.

Building on Yosinski and colleagues' layer-wise specificity insight, Howard and Ruder (2018) introduced *discriminative fine-tuning* with per-layer learning rates. Rather than a binary freeze-or-fine-tune decision, their ULMFiT framework showed that gradual unfreezing with learning rate decay achieves superior transfer. This directly informs our Variant 2, which uses 3e-4 for the head but only 3e-5 for unfrozen backbone blocks. Where Howard and Ruder focused on NLP, this study applies their principles to vision-based emotion recognition.

Raghu, Zhang, Kleinberg, and Bengio (2019) examined transfer to domains with limited labeled data. Their "Transfusion" study found that transfer learning's primary benefit comes from feature reuse rather than improved optimization, suggesting that a frozen backbone (V1) should perform well when pre-training and target domains are similar. However, Raghu and colleagues did not address what happens when training data *composition* shifts---the central question of our study.

Tan, Sun, Kong, Zhang, Yang, and Liu (2018) formalized the taxonomy of transfer approaches and identified dataset size as the conventional factor determining the freeze-vs-fine-tune decision. Our work directly challenges this simplification: the training set grew by only 17% when real data was added, yet the optimal strategy reversed entirely. Data *composition*, not merely size, is the critical factor.

## Pre-Trained Models for Facial Emotion Recognition

Within FER, pre-trained models have evolved from general ImageNet backbones to face-specific architectures. AffectNet (Mollahosseini, Hasani, & Mahoor, 2017) provided ~450,000 annotated facial images---an order of magnitude larger than FER2013 (Goodfellow, Erhan, Carrier, Courville, Mirza, Hamber, Cukierski, Tang, Thaler, Lee, Zhou, Ramaiah, Belber, Chi, de la Torre, Boudev, Bai, & Escalera, 2013). AffectNet's scale enabled training deep models directly on expressions rather than relying on ImageNet pre-training. However, its internet-sourced collection introduces demographic biases.

Building on large-scale face datasets, Savchenko (2021, 2022) developed HSEmotion, which pre-trains EfficientNet-B0 in two stages: first on VGGFace2 (~3.3M faces) for identity-invariant recognition, then on AffectNet for 8-class emotion classification. This two-stage approach provides richer initialization than single-stage training because face recognition features encode geometric and structural properties invariant to identity---exactly what emotion recognition needs. However, Savchenko evaluated only on standard benchmarks, not in deployment contexts with synthetic-to-real domain shift.

EfficientNet-B0 (Tan & Le, 2019) uses compound scaling to balance width, depth, and resolution, achieving high accuracy at low computational cost. With 5.3M parameters and ~40ms latency on the Jetson, it fits within our 120ms and 2.5 GB budgets with substantial headroom.

## Synthetic-to-Real Domain Adaptation

Training on synthetic data introduces a systematic domain gap. Tobin, Fong, Ray, Schneider, Sauber, and Goldberg (2017) were among the first to quantify this for deep learning, proposing *domain randomization*---randomizing visual attributes during training to force domain-invariant features. The strength is simplicity; the weakness is that it requires extensive randomization engineering.

Tremblay, Prakash, Acuna, Brober, Jampani, Anil, To, Cameracci, Boochoon, and Birchfield (2018) extended domain randomization by combining it with structured variation, improving upon Tobin and colleagues' results for object detection. The fundamental limitation remained: synthetic data encodes biases of the generation process.

Taking a different approach, Ganin and Lempitsky (2015) proposed *adversarial domain adaptation*, training a domain classifier while simultaneously training the feature extractor to fool it. Shrivastava, Pfister, Tuzel, Susskind, Wang, and Webb (2017) extended this to the generative setting. These methods are effective but complex.

Our approach is simpler: directly augmenting synthetic data with real photographs. Adding 15,000 real images (~15%) closed a 22% generalization gap to 8.3%, suggesting that for tasks where some real data is available, simple augmentation may outperform sophisticated techniques---particularly when the backbone already encodes real-world knowledge.

## Model Calibration: Confidence as a Functional Requirement

A model that closes the domain gap through fine-tuning may simultaneously *regress* in calibration. Guo, Pleiss, Sun, and Weinberger (2017) demonstrated that modern deep networks are systematically overconfident and proposed temperature scaling as the simplest correction. For our system, calibration directly controls the robot's 5-tier gesture expressiveness---a functional requirement absent from standard benchmarks.

## Quality Gates and MLOps

Baylor, Breck, Cheng, Fiedel, Foo, Haque, Haykal, Ispir, Jain, Koc, Koo, Lew, Mewald, Modi, Polyzotis, Ramesh, Roy, Whang, Wicke, Wilkiewicz, and Zhang (2017) introduced TFX, formalizing automated deployment validation. Zaharia, Chen, Davidson, Ghodsi, Hong, Konwinski, Murching, Nykodym, Ogilvie, Parkhe, Xie, and Zuber (2018) extended this with MLflow. Our gate architecture adds two innovations: a two-tier structure acknowledging domain shift, and per-class F1 thresholds preventing majority-class inflation from masking failures.

## Imbalanced Classification and Metric Selection

He and Garcia (2009) surveyed learning from imbalanced data, recommending class-balanced metrics. Our test set (48.7% happy, 17.9% sad, 33.4% neutral) makes macro metrics essential. However, even macro metrics can mask class-level disparities: our V1 and V2 had F1 Macro of 0.781 and 0.780 (Delta = 0.001) despite radically different per-class profiles---a limitation not emphasized in the binary-focused survey.

## Gaps Addressed by This Work

This literature reveals four gaps: (1) the freeze-vs-fine-tune decision is treated as a function of size, not composition; (2) domain adaptation research focuses on complex techniques rather than simple mixed-domain augmentation; (3) calibration research rarely considers behavioral consequences in embodied systems; (4) MLOps gates lack per-class decomposition. This study addresses each gap.

\newpage

# Results and Discussion

This section presents hypotheses, results across three iterative phases, statistical analysis, and interpretation. Hypotheses, data analysis, and discussion are integrated so each phase's findings motivate the next.

## Hypotheses

**H1 (Transfer Strategy x Data Composition).** The relative performance of frozen-backbone (V1) versus fine-tuned-backbone (V2) depends on training data composition. V1 will be preferred under synthetic-only training; V2 under mixed-domain.

**H2 (Mixed-Domain Improvement).** Augmenting synthetic data with ~15% real photographs will improve both variants, with V2 benefiting disproportionately.

**H3 (Calibration Separability).** Post-hoc temperature scaling will correct calibration regression without affecting classification metrics.

**H4 (Aggregate Metric Insufficiency).** Aggregate metrics will fail to distinguish models with substantially different per-class error profiles.

Given conventional wisdom that fine-tuned models outperform frozen ones on large datasets, I expected V2 to be uniformly superior. The finding that V1 was initially preferred---and that the preference reversed---was genuinely surprising.

## The Face Cropping Discovery

Before presenting the main results, a critical preprocessing finding must be reported. Prior to enabling face cropping (run\_0104), full-scene synthetic frames yielded F1 of approximately 0.43 for both variants:

| Configuration | V1 F1 | V2 F1 | Improvement |
|--------------|-------|-------|-------------|
| No face crop (run\_0104) | 0.430 | 0.439 | --- |
| Face crop (run\_0107) | 0.781 | 0.780 | +82% / +78% |

This single preprocessing flag produced the largest improvement of the entire project, reinforcing the data-centric AI perspective (Ng, 2021): data quality decisions can dominate model architecture decisions.

## Phase 1 Results: Synthetic-Only Training

***Aggregate metrics.*** Both variants were trained on 86,519 synthetic face-cropped frames and evaluated on the 894-image AffectNet test set.

| Metric | V1 (Frozen) | V2 (Fine-Tuned) | Delta |
|--------|------------|-----------------|-------|
| F1 Macro | **0.781** | 0.780 | +0.001 |
| Balanced Accuracy | 0.799 | **0.812** | -0.013 |
| Accuracy | 0.771 | **0.817** | -0.046 |
| ECE | 0.102 | **0.096** | +0.006 |
| Brier | 0.340 | **0.279** | +0.061 |

The near-identical F1 Macro (Delta = 0.001) conceals radically different per-class profiles, directly relevant to H4.

***Per-class analysis.*** Decomposing the aggregate reveals the hidden disparity:

| Metric | V1 | V2 | Consequence |
|--------|----|----|-------------|
| F1 Happy | 0.777 | **0.946** | V2 excels on majority class |
| F1 Sad | **0.822** | 0.694 | V2 fails Gate A (0.70) |
| F1 Neutral | **0.743** | 0.699 | V2 fails Gate A (0.70) |
| Per-class CV | **4.2%** | 15.1% | V2 has severe inequity |

V2's CV (15.1%) is 3.6x V1's (4.2%), indicating severe class-level disparity. V2's dominant error is neutral-to-sad confusion: 105 of 299 neutral faces (35.1%) misclassified as sad---behaviorally disruptive on the robot (offering empathy to someone at rest). V1's dominant error (happy-to-neutral: 147/435, 33.8%) is behaviorally benign (calm composure toward someone happy).

***Gate A-deploy compliance.*** V1 passes 5/7 gates; V2 passes 4/7 (failing per-class F1 on sad and neutral). **V1 is the Phase 1 deployment candidate.** This supports H1 for the synthetic-only case.

## Phase 2 Results: Mixed-Domain Training

Adding 15,000 real AffectNet photographs (5,000/class) produces a dramatic reversal:

| Metric | V1 Synth -> Mixed | V2 Synth -> Mixed |
|--------|-------------------|-------------------|
| F1 Macro | 0.781 -> 0.834 (+0.053) | 0.780 -> **0.916** (+0.136) |
| F1 Sad | 0.822 -> 0.860 | 0.694 -> **0.888** (+0.194) |
| F1 Neutral | 0.743 -> 0.801 | 0.699 -> **0.899** (+0.200) |
| Neutral -> Sad | --- | 35.1% -> 5.7% (--83.8%) |
| ECE | 0.102 -> 0.104 | 0.096 -> 0.142 (regression) |

V2's disproportionate improvement (+17.4% vs. +6.8%) directly supports H2. However, mixed-domain training introduces calibration regression: V2 mixed ECE = 0.142 exceeds the 0.12 threshold.

This reversal is the central finding. It demonstrates that the optimal strategy is not a static property of architecture or dataset size, but depends on the compositional relationship between training data and the target domain. When data was purely synthetic, V2's fine-tuned backbone adapted to synthetic-specific artifacts that did not transfer. When real photographs anchored the distribution, V2's additional capacity became an asset.

## Phase 3 Results: Temperature Scaling

Learned T = 0.59 (sharpening), consistent with label smoothing (0.10) applied during training.

| Metric | V2 Mixed | V2 Mixed+T | Delta |
|--------|---------|-----------|-------|
| F1 Macro | 0.916 | 0.916 | 0.000 |
| Balanced Acc | 0.921 | 0.921 | 0.000 |
| Per-class F1 | unchanged | unchanged | 0.000 |
| ECE | 0.142 | **0.036** | -0.106 |
| Brier | 0.167 | **0.128** | -0.039 |

Classification unchanged; calibration fixed. ECE dropped 75%, now 3x below the threshold. **H3 supported.**

## Final Gate A-deploy Compliance

| Config | F1 >= .75 | bAcc >= .75 | F1/cls >= .70 | ECE <= .12 | Brier <= .16 | Total |
|--------|-----------|-------------|---------------|------------|-------------|-------|
| V1 synth | PASS | PASS | PASS | PASS | FAIL | 5/7 |
| V2 synth | PASS | PASS | FAIL | PASS | FAIL | 4/7 |
| V1 mixed+T | PASS | PASS | PASS | PASS | FAIL | 6/7 |
| **V2 mixed+T** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** | **7/7** |

**V2 mixed+T is the only configuration passing all seven gates.**

## Composite Score Evolution

| Configuration | Composite | Gates | Status |
|--------------|-----------|-------|--------|
| V1 synthetic | 0.802 | 5/7 | Initial candidate |
| V2 synthetic | 0.805 | 4/7 | Rejected |
| V1 mixed+T | 0.857 | 6/7 | Improved |
| **V2 mixed+T** | **0.924** | **7/7** | **Final candidate** |

## Statistical Analysis

***Wilson score confidence intervals.*** Wilson 95% CIs on per-class recall (synthetic-only):

| Class | n | V1 Recall [95% CI] | V2 Recall [95% CI] | Overlap |
|-------|---|-------------------|-------------------|---------|
| Happy | 435 | 0.637 [0.591, 0.681] | 0.933 [0.906, 0.953] | **No** |
| Sad | 160 | 0.825 [0.759, 0.876] | 0.900 [0.844, 0.938] | Yes |
| Neutral | 299 | 0.936 [0.903, 0.959] | 0.602 [0.546, 0.656] | **No** |

Non-overlapping intervals for happy and neutral confirm genuine differences. **Supports H4.**

***Per-class F1 z-tests.*** Testing H0: F1\_k = 0.70 (deployment threshold):

| Class | V1 F1 | z | p | V2 F1 | z | p |
|-------|-------|---|---|-------|---|---|
| Happy | 0.777 | +3.85 | < .001 | 0.946 | +22.9 | < .001 |
| Sad | 0.822 | +4.07 | < .001 | 0.694 | -0.17 | .43 |
| Neutral | 0.743 | +1.71 | .044 | 0.699 | -0.04 | .48 |

V2's gate failures are genuine, not artifacts.

***Cohen's kappa.***

| Model | kappa | Interpretation |
|-------|-------|---------------|
| V1 synthetic | 0.645 | Substantial |
| V2 synthetic | 0.712 | Substantial |
| V2 mixed+T | **0.865** | Almost perfect |

V2 synthetic's higher kappa is inflated by majority-class (happy) performance.

***Coefficient of variation.***

| Model | F1 Happy | F1 Sad | F1 Neutral | CV |
|-------|---------|--------|-----------|-----|
| V1 synth | 0.777 | 0.822 | 0.743 | **4.2%** |
| V2 synth | 0.946 | 0.694 | 0.699 | **15.1%** |
| V2 mixed+T | 0.961 | 0.888 | 0.899 | **4.3%** |

Mixed-domain training resolved V2's inequity.

***Composite score decomposition.***

| Component | Weight | V1 Mixed+T | V2 Mixed+T |
|-----------|--------|-----------|-----------|
| F1 Macro | 0.50 | 0.417 | **0.458** |
| Balanced Acc | 0.20 | 0.168 | **0.184** |
| Mean per-class F1 | 0.15 | 0.125 | **0.137** |
| 1 -- ECE | 0.15 | 0.147 | 0.145 |
| **Composite** | **1.00** | **0.857** | **0.924** |

The 0.067-point gap is 22x the synthetic-only Delta of 0.003.

## The Global vs. Local Metric Paradox

The synthetic-only phase produced a paradox: global metrics favored V2 (accuracy 0.817, kappa 0.712), while local metrics favored V1 (CV 4.2%, gates 5/7). V2 excelled on happy (48.7% of test), inflating global metrics while masking minority-class failures. The per-class gate framework served as the circuit breaker. Mixed-domain training dissolved the paradox: V2 mixed+T achieves superiority on both global and local metrics.

## Summary of Hypothesis Testing

- **H1 supported:** V1 preferred synthetic (5/7 vs. 4/7); V2 preferred mixed (7/7 vs. 6/7).
- **H2 supported:** V2 gains +17.4% vs. V1's +6.8%.
- **H3 supported:** ECE drops 75% with zero classification change.
- **H4 supported:** F1 Macro Delta = 0.001 concealed recall differences of +29.6% and --33.4%.

\newpage

# Threats to the Validity

Every empirical study has limitations. This section identifies potential weaknesses that could affect the conclusions drawn above. If the findings depend on assumptions, those assumptions are stated explicitly.

## Internal Validity

***Test set reuse and researcher degrees of freedom.*** The same 894-image real test set is reused across phases. Even with phase-end evaluation discipline, repeated exposure can create unintentional leakage through decision coupling (e.g., selecting interventions based on patterns observed in prior test confusion matrices). This threat is partially mitigated by fixed gate thresholds defined before final comparison and by reporting all major pivots rather than only favorable ones. A stronger design for future replication would reserve a final *lockbox* test split that is never consulted until the end of the full three-phase program.

***Calibration split overlap.*** The temperature parameter $T$ is fitted on 30% of the real test pool and then reported on the remaining pool. Because temperature scaling has only one free parameter, overfitting risk is lower than multi-parameter recalibration methods; however, this still couples calibration model selection and final evaluation within the same source distribution. A fully independent calibration set (or nested cross-validation for calibration) would tighten causal claims about expected real-world confidence reliability.

***Pipeline intervention timing.*** Face cropping was activated after early poor results, then retained for all subsequent runs. This is methodologically correct as a preprocessing correction, but it means early and late experiments differ by more than one factor in the historical timeline of the project. The paper reports this explicitly and treats pre-crop results as diagnostic rather than as directly comparable ablations.

***Hyperparameter search asymmetry.*** V2 received broader optimization (90 trials) than V1. The asymmetry is defensible because V2 has a larger trainable space, but it can inflate observed V2 headroom. To reduce this threat, future studies should allocate a fixed optimization budget per effective trainable parameter, or at minimum run a modest V1 sweep to establish a fairer comparison baseline.

***Selection bias from iterative stopping.*** Iterative projects risk "stopping when results look good." In this work, progression criteria were constrained by predefined quality gates (A-val and A-deploy), which reduced ad-hoc stopping behavior. Nonetheless, because intervention order was not randomized, the sequence itself may have influenced interpretation.

## External Validity

***Single-source real benchmark.*** AffectNet is the sole real-data benchmark. Real deployment contexts for companion robots include camera placement effects, motion blur, household lighting shifts, and interpersonal distances not represented uniformly in curated internet images. Consequently, A-deploy pass on AffectNet should be treated as a *necessary but insufficient* proxy for field readiness.

***Static-image to video transfer gap.*** Evaluation uses static images, while deployment consumes frame streams with temporal smoothing and confidence modulation. Errors in onset/offset transitions, expression ambiguity across frames, and motion-induced blur are not directly measured in the current protocol.

***Population and context shift.*** AffectNet contains broad internet diversity but cannot guarantee balanced representation of the specific populations and interaction contexts expected in deployment (e.g., seated tabletop interaction with a child, adult caregiver, or elder). External validity is therefore bounded to environments reasonably similar to the combined synthetic + AffectNet distribution.

***Hardware and software portability.*** Reported edge performance targets are achieved on Jetson Xavier NX with a specific FP16 TensorRT/DeepStream pipeline. Latency and throughput conclusions may not transfer directly to other edge accelerators, camera sensors, or runtime stacks without re-optimization.

***Open demonstration bias (Hugging Face deployment).*** A public demonstration for portfolio/job-search purposes can differ from operational deployment if demo constraints favor stable, curated inputs. If Hugging Face Spaces deployment uses preprocessed or constrained sample streams, performance in that environment may overestimate unconstrained in-home interaction performance.

## Construct Validity

***Metric-to-risk alignment.*** Macro F1 treats classes equally, while deployment harm is asymmetric (neutral-to-sad errors are behaviorally costlier than some other confusions). Thus, the metric captures statistical balance but only partially captures interactional risk.

***Calibration estimator sensitivity.*** ECE with 10 fixed bins may be unstable with finite samples and class imbalance. Although the calibration trend is large and consistent with reliability diagrams, absolute ECE values should be interpreted as approximate, not exact physical risk.

***Composite score subjectivity.*** The weighted composite reflects practical deployment priorities but remains heuristic. Different stakeholders (research benchmark vs. human-robot interaction safety) might assign different weights and obtain different aggregate rankings, even when underlying per-metric ordering is similar.

***Label ontology simplification.*** The 3-class taxonomy operationalizes emotion into `happy/sad/neutral` for robustness and data sufficiency, but this simplification may compress semantically distinct states (e.g., fear vs. surprise) into neutral or misaligned categories. Construct validity is strong for coarse valence-like behavior, weaker for nuanced affect.

***Proxy target mismatch.*** The ultimate construct of interest is "socially appropriate robot response," yet evaluation targets image-level emotion classification/calibration. The current construct mapping assumes better FER metrics translate to better interaction quality, which should be tested directly with user studies.

\newpage

# Future Work

Several directions could strengthen and extend this research.

***Public reproducible deployment track (Hugging Face).*** A prioritized next step is releasing a reproducible public inference stack on Hugging Face (model card + Space demo + documented limitations). For career and portfolio value, this should include: (a) exact preprocessing parity with training (face crop, resize, normalization), (b) explicit confidence calibration display, (c) latency benchmarks under CPU and GPU modes, and (d) a transparent "not for clinical use" disclaimer. The scientific value is equally important: open deployment enables external replication and peer critique.

***Prospective lockbox evaluation.*** Create a never-touched lockbox dataset collected after model freeze, including challenging video clips from target deployment environments. This would provide a stronger estimate of true generalization and protect against iterative overfitting to known benchmarks.

***Scaled real-data curriculum.*** Extend mixed-domain training with staged real-data increments (e.g., 5k, 15k, 30k, 60k per class) to estimate diminishing returns. A formal sample-efficiency curve would quantify how much real data is required to reach each gate threshold with confidence intervals.

***Phase 2 expansion to 8-class PPE/EQ stack.*** Progress from 3-class to Ekman-8 classification and integrate confidence-driven policy mapping into gesture modulation and prompt conditioning. This transition should include class-merging fallback logic when confidence is low to avoid brittle over-specific behavior.

***Video-native modeling and evaluation.*** Move from frame-centric inference to temporal encoders or lightweight sequence aggregation (e.g., sliding-window logits with hysteresis), then evaluate on annotated clips capturing transitions, mixed affect, and brief expressions. This aligns evaluation with real robot perception.

***Fairness, robustness, and safety stress tests.*** Add subgroup analysis where metadata is ethically available, plus perturbation tests for occlusion, illumination, camera jitter, and compression artifacts. Track worst-group performance and calibrate per-group reliability where needed.

***Alternative adaptation methods.*** Compare mixed-domain augmentation against adversarial adaptation and self-training under equal compute budgets. The goal is not only best score, but best complexity-to-benefit ratio for maintainable local-first deployment.

***Human-centered outcome studies.*** Pair model metrics with user studies measuring perceived empathy, appropriateness of gesture intensity, and trust. This directly validates whether calibration improvements and confusion reductions translate to better lived interaction outcomes.

\newpage

# Reflections

## On the Research Process

This project evolved significantly from its initial conception. The original plan envisioned ResNet-50 trained on synthetic data with a single training pass. Each pivot was driven by empirical evidence: EfficientNet-B0 for edge efficiency, HSEmotion for expression-specific features, face cropping for domain alignment, mixed-domain training for closing the gap, and temperature scaling for calibration. The most important methodological lesson is that disciplined iteration beats attachment to an initial architecture. In practice, "model selection" became "system selection": data pipeline, orchestration reliability, calibration policy, and deployment constraints mattered as much as backbone choice.

## Most Rewarding Aspects

The most rewarding aspect was the moment when the mixed-domain results came in and the deployment recommendation reversed. Seeing empirical evidence overturn an assumption I held (that V1 would remain superior) was a powerful demonstration of data-driven decision making. A close second was the temperature scaling result: watching ECE drop from 0.142 to 0.036 with zero change to classification metrics was an elegant confirmation that calibration and classification are separable concerns.

Equally rewarding was building an end-to-end, auditable local-first pipeline that links model confidence to robot behavior. The project moved beyond "train a classifier" into a complete applied ML system with quality gates, reproducibility, and deployment accountability---the kind of work that translates directly to professional MLOps and robotics engineering practice.

## Most Challenging Aspects

The most challenging aspect was managing the complexity of the full-stack system. This project is not just a machine learning experiment---it includes a web application, a REST API, a PostgreSQL database, a 10-agent orchestration system, edge deployment with TensorRT, and statistical analysis in both R and Python. Debugging issues that span multiple layers (e.g., a face-cropping bug that manifests as poor model performance) required disciplined root-cause analysis. The face cropping discovery, in particular, consumed significant debugging time because the symptom (poor test F1) initially suggested a model problem, not a data pipeline problem.

## Lessons Learned

1. **Start with the data pipeline.** Face cropping yielded an 82% improvement---more than any model change. Data preprocessing decisions dominate architectural decisions.

2. **Define quality gates before evaluation.** Pre-defined criteria prevent post-hoc rationalization. Without per-class F1 gates, V2 synthetic would have appeared acceptable (F1 = 0.780, accuracy = 0.817).

3. **Measure per-class performance.** Aggregate metrics concealed a 35.1% neutral-to-sad error rate. Per-class analysis, coefficient of variation, and confusion matrix decomposition are essential for multi-class deployment.

4. **Consider error consequences.** Not all errors are equal. Happy-to-neutral (33%) is more tolerable than neutral-to-sad (35%) because the downstream robot behavior differs qualitatively.

5. **Treat calibration separately.** Classification and calibration are separable concerns. Temperature scaling fixed calibration without classification cost, simplifying the optimization pipeline.

6. **Revisit decisions as data evolves.** The optimal transfer learning strategy changed with data composition. Static decisions based on initial conditions would have locked in V1 permanently.

7. **Synthetic and real data are complements.** Even 15% real data was transformative. The two data sources address different aspects of the learning problem and should be treated as complementary.

8. **Iterate rather than optimize in one pass.** Three phases, each addressing the specific blocker identified by the previous phase, outperformed any single training configuration. The iterative methodology is itself a contribution.

9. **Design for explainability to future employers and collaborators.** Building clear run records, gate criteria, and decision logs made it possible to explain *why* each technical choice was made. This narrative traceability is as important for industry readiness as raw metric improvements.

10. **Treat public demos as scientific communication, not only presentation.** Preparing for Hugging Face deployment clarified assumptions, surfaced documentation gaps, and forced explicit communication of failure modes. A transparent demo can function as both portfolio artifact and reproducible research companion.

## Suggestions for Future Projects

For anyone undertaking a similar data science project, I offer four suggestions. First, invest heavily in data quality and preprocessing before touching model architecture; the face cropping lesson applies broadly. Second, define quantitative success criteria before evaluating results---it is far too easy to rationalize marginal performance after the fact. Third, plan for iteration: your first model will not be your last, and each failure teaches you something that a single optimization pass cannot. Fourth, if you plan a public deployment (e.g., Hugging Face), treat reproducibility, limitations, and ethical communication as first-class engineering deliverables rather than post-project documentation tasks.

## Professional and Deployment Reflection

Because this system is intended to be a centerpiece of my job search, the final phase includes an explicit translation from academic artifact to deployable portfolio evidence. The Hugging Face release will therefore emphasize: reproducible setup, model and dataset provenance, calibration transparency, failure-case examples, and measurable inference performance. My objective is not simply to show a high F1 score, but to demonstrate engineering maturity: I can design, validate, and ship a privacy-first embodied AI system with auditable decisions and clearly communicated trade-offs.

\newpage

# References

Baylor, D., Breck, E., Cheng, H.-T., Fiedel, N., Foo, C. Y., Haque, Z., Haykal, S., Ispir, M., Jain, V., Koc, L., Koo, C. Y., Lew, L., Mewald, C., Modi, A. N., Polyzotis, N., Ramesh, S., Roy, S., Whang, S. E., Wicke, M., Wilkiewicz, J., & Zhang, X. (2017). TFX: A TensorFlow-based production-scale machine learning platform. *Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 1387--1395).

Breazeal, C. (2003). Emotion and sociable humanoid robots. *International Journal of Human-Computer Studies*, 59(1--2), 119--155.

Fong, T., Nourbakhsh, I., & Dautenhahn, K. (2003). A survey of socially interactive robots. *Robotics and Autonomous Systems*, 42(3--4), 143--166.

Ganin, Y., & Lempitsky, V. (2015). Unsupervised domain adaptation by backpropagation. *Proceedings of the 32nd International Conference on Machine Learning* (pp. 1180--1189).

Goodfellow, I. J., Erhan, D., Carrier, P. L., Courville, A., Mirza, M., Hamber, B., Cukierski, W., Tang, Y., Thaler, D., Lee, D.-H., Zhou, Y., Ramaiah, C., Belber, F., Chi, C., de la Torre, F., Boudev, R., Bai, Y., & Escalera, S. (2013). Challenges in representation learning: A report on three machine learning contests. *International Conference on Neural Information Processing* (pp. 117--124).

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *Proceedings of the 34th International Conference on Machine Learning* (pp. 1321--1330).

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE Transactions on Knowledge and Data Engineering*, 21(9), 1263--1284.

Howard, J., & Ruder, S. (2018). Universal language model fine-tuning for text classification. *Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics* (pp. 328--339).

Mollahosseini, A., Hasani, B., & Mahoor, M. H. (2017). AffectNet: A database for facial expression, valence, and arousal computing in the wild. *IEEE Transactions on Affective Computing*, 10(1), 18--31.

Ng, A. (2021). Data-centric AI competition. *NeurIPS Datasets and Benchmarks Track*.

Raghu, M., Zhang, C., Kleinberg, J., & Bengio, S. (2019). Transfusion: Understanding transfer learning for medical imaging. *Advances in Neural Information Processing Systems 32* (pp. 3342--3352).

Savchenko, A. V. (2021). Facial expression and attributes recognition based on multi-task learning of lightweight neural networks. *IEEE 19th International Symposium on Intelligent Systems and Informatics* (pp. 119--124).

Savchenko, A. V. (2022). HSEmotion: High-speed emotion recognition library. *arXiv preprint arXiv:2202.10585*.

Shrivastava, A., Pfister, T., Tuzel, O., Susskind, J., Wang, W., & Webb, R. (2017). Learning from simulated and unsupervised images through adversarial training. *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 2107--2116).

Tan, C., Sun, F., Kong, T., Zhang, W., Yang, C., & Liu, C. (2018). A survey on deep transfer learning. *International Conference on Artificial Neural Networks* (pp. 270--279).

Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. *Proceedings of the 36th International Conference on Machine Learning* (pp. 6105--6114).

Tobin, J., Fong, R., Ray, A., Schneider, J., Sauber, W., & Goldberg, K. (2017). Domain randomization for transferring deep neural networks from simulation to the real world. *Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems* (pp. 23--30).

Tremblay, J., Prakash, A., Acuna, D., Brober, M., Jampani, V., Anil, C., To, T., Cameracci, E., Boochoon, S., & Birchfield, S. (2018). Training deep networks with synthetic data: Bridging the reality gap by domain randomization. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops* (pp. 969--977).

Yosinski, J., Clune, J., Bengio, Y., & Lipson, H. (2014). How transferable are features in deep neural networks? *Advances in Neural Information Processing Systems 27* (pp. 3320--3328).

Zaharia, M., Chen, A., Davidson, A., Ghodsi, A., Hong, S. A., Konwinski, A., Murching, S., Nykodym, T., Ogilvie, P., Parkhe, M., Xie, F., & Zuber, C. (2018). Accelerating the machine learning lifecycle with MLflow. *IEEE Data Engineering Bulletin*, 41(4), 39--45.

Zhuang, F., Qi, Z., Duan, K., Xi, D., Zhu, Y., Zhu, H., Xiong, H., & He, Q. (2020). A comprehensive survey on transfer learning. *Proceedings of the IEEE*, 109(1), 43--76.

\newpage

# Appendix A: Source Code for Statistical Computation

This appendix contains the complete source code for all scripts used to compute and validate the statistics reported in this paper.

## A.1 Temperature Scaling (`trainer/fer_finetune/temperature_scaling.py`)

```python
"""
Post-hoc Temperature Scaling for calibration improvement.

Temperature scaling learns a single scalar T on a held-out calibration set
that divides logits before softmax:  p = softmax(z / T).

- T > 1 softens predictions (reduces overconfidence)
- T < 1 sharpens predictions (increases confidence)
- T = 1 is the identity (no change)
"""

import json, logging, numpy as np, torch, torch.nn as nn
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class _TemperatureModel(nn.Module):
    """Learnable temperature parameter via log-parameterization (T > 0)."""

    def __init__(self, init_temp: float = 1.5) -> None:
        super().__init__()
        self.log_temperature = nn.Parameter(
            torch.tensor([float(np.log(init_temp))])
        )

    @property
    def temperature(self) -> torch.Tensor:
        return self.log_temperature.exp()

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature


def learn_temperature(
    logits: torch.Tensor, labels: torch.Tensor,
    *, lr: float = 0.01, max_iter: int = 200, tol: float = 1e-7,
) -> float:
    """Learn optimal T by minimizing NLL on calibration data via L-BFGS."""
    temp_model = _TemperatureModel(init_temp=1.5)
    if logits.is_cuda:
        temp_model = temp_model.cuda()

    nll_criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.LBFGS(
        temp_model.parameters(), lr=lr, max_iter=max_iter,
        tolerance_change=tol,
    )

    best_loss = float("inf")
    best_T = 1.5

    def _closure():
        nonlocal best_loss, best_T
        optimizer.zero_grad()
        scaled = temp_model(logits)
        loss = nll_criterion(scaled, labels)
        loss.backward()
        current_T = temp_model.temperature.item()
        if loss.item() < best_loss:
            best_loss = loss.item()
            best_T = current_T
        return loss

    optimizer.step(_closure)
    optimal_T = temp_model.temperature.item()

    if not (0.01 <= optimal_T <= 100.0):
        logger.warning(
            f"Learned T={optimal_T:.4f} outside [0.01, 100]. "
            f"Using best seen T={best_T:.4f}."
        )
        optimal_T = best_T

    logger.info(f"Learned temperature T = {optimal_T:.6f} (NLL={best_loss:.6f})")
    return optimal_T


def apply_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    """Apply temperature scaling and return calibrated probabilities."""
    scaled = logits / temperature
    exp_scaled = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))
    return exp_scaled / np.sum(exp_scaled, axis=1, keepdims=True)


def collect_logits(
    checkpoint_path, data_root, class_names, input_size,
    batch_size, num_workers, *, val_dir=None,
    val_dataset_type="emotion", ground_truth_manifest=None,
    run_id=None, frames_per_video=1,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run forward pass and collect raw logits, labels, and probabilities."""
    from trainer.fer_finetune.model_efficientnet import load_pretrained_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_pretrained_model(
        checkpoint_path, num_classes=len(class_names), device=device,
    )

    if ground_truth_manifest:
        from trainer.fer_finetune.dataset import EmotionDataset, get_val_transforms
        dataset = EmotionDataset(
            data_dir=data_root, split="",
            transform=get_val_transforms(input_size),
            class_names=class_names, frame_sampling="middle",
            frames_per_video=frames_per_video,
            manifest_path=ground_truth_manifest,
        )
        loader = DataLoader(
            dataset, batch_size=batch_size * 2, shuffle=False,
            num_workers=num_workers, pin_memory=True,
        )
    else:
        from trainer.fer_finetune.dataset import create_dataloaders
        _, loader = create_dataloaders(
            data_dir=data_root, batch_size=batch_size,
            num_workers=num_workers, input_size=input_size,
            class_names=class_names,
            frame_sampling_train="random", frame_sampling_val="middle",
            run_id=run_id, frames_per_video=frames_per_video,
            val_dir=val_dir, val_dataset_type=val_dataset_type,
        )

    all_logits, all_labels, all_probs = [], [], []
    model.eval()
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            logits = outputs["logits"] if isinstance(outputs, dict) else outputs
            probs = torch.softmax(logits, dim=1)
            all_logits.extend(logits.cpu().numpy())
            all_labels.extend(labels.cpu().numpy().tolist())
            all_probs.extend(probs.cpu().numpy())

    return (
        np.array(all_logits, dtype=np.float32),
        np.array(all_labels, dtype=np.int64),
        np.array(all_probs, dtype=np.float32),
    )


def calibrate_checkpoint(
    checkpoint_path, calibration_data_dir, class_names,
    input_size=224, batch_size=32, num_workers=0, *,
    val_dir=None, val_dataset_type="emotion",
    ground_truth_manifest=None, run_id=None,
    frames_per_video=1, output_path=None,
) -> Dict[str, Any]:
    """End-to-end: learn T on calibration set and save results."""
    logger.info(f"Collecting logits from {checkpoint_path}")
    logits, labels, probs_before = collect_logits(
        checkpoint_path=checkpoint_path, data_root=calibration_data_dir,
        class_names=class_names, input_size=input_size,
        batch_size=batch_size, num_workers=num_workers,
        val_dir=val_dir, val_dataset_type=val_dataset_type,
        ground_truth_manifest=ground_truth_manifest,
        run_id=run_id, frames_per_video=frames_per_video,
    )

    logits_t = torch.from_numpy(logits)
    labels_t = torch.from_numpy(labels)
    if torch.cuda.is_available():
        logits_t, labels_t = logits_t.cuda(), labels_t.cuda()

    temperature = learn_temperature(logits_t, labels_t)
    probs_after = apply_temperature(logits, temperature)

    from trainer.fer_finetune.evaluate import compute_calibration_metrics
    cal_before = compute_calibration_metrics(labels.tolist(), probs_before)
    cal_after = compute_calibration_metrics(labels.tolist(), probs_after)

    result = {
        "temperature": temperature, "samples": len(labels),
        "calibration_before": {
            "ece": cal_before.get("ece"),
            "brier": cal_before.get("brier"),
            "mce": cal_before.get("mce"),
        },
        "calibration_after": {
            "ece": cal_after.get("ece"),
            "brier": cal_after.get("brier"),
            "mce": cal_after.get("mce"),
        },
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        result["output_path"] = str(out)

    return result
```

## A.2 Composite Score Calculation (`apps/web/pages/08_Compare.py`)

```python
def _composite_score(payload):
    """Weighted aggregation for automated run selection.

    Formula: S = 0.50*F1_macro + 0.20*bAcc + 0.15*mean_perclass_F1
                 + 0.15*(1 - ECE)
    """
    m = payload.get("gate_a_metrics", {})
    f1_macro = float(m.get("f1_macro", 0.0))
    bal_acc = float(m.get("balanced_accuracy", 0.0))
    per_class = [float(m.get(f"f1_{c}", 0.0))
                 for c in ["happy", "sad", "neutral"]]
    per_class_mean = sum(per_class) / max(len(per_class), 1)
    ece = float(m.get("ece", 1.0))
    calibration = 1.0 - min(ece, 1.0)
    return (0.50 * f1_macro + 0.20 * bal_acc
            + 0.15 * per_class_mean + 0.15 * calibration)
```

## A.3 Gate A-deploy Thresholds (`trainer/fer_finetune/config.py`)

```python
GATE_A_DEPLOY_THRESHOLDS = {
    "f1_macro": (">=", 0.75),
    "balanced_accuracy": (">=", 0.75),
    "per_class_f1": (">=", 0.70),
    "ece": ("<=", 0.12),
}
```

## A.4 R Utility Functions (`stats/R_scripts/utils_data_ingest.R`)

```r
suppressPackageStartupMessages({
  library(DBI)
  library(RPostgres)
  library(glue)
  library(yaml)
  library(jsonlite)
})

`%||%` <- function(lhs, rhs) {
  if (is.null(lhs) || (is.character(lhs) && identical(lhs, ""))
      || (is.logical(lhs) && length(lhs) == 0)) {
    rhs
  } else {
    lhs
  }
}

compact_list <- function(x) {
  if (is.null(x) || length(x) == 0) return(list())
  x[!vapply(x, is.null, logical(1))]
}

merge_lists <- function(base, override) {
  if (is.null(base)) base <- list()
  if (is.null(override)) return(base)
  for (name in names(override)) {
    if (is.list(base[[name]]) && is.list(override[[name]])) {
      base[[name]] <- merge_lists(base[[name]], override[[name]])
    } else {
      base[[name]] <- override[[name]]
    }
  }
  base
}

read_yaml_config <- function(path) {
  if (is.null(path)) return(list())
  if (!file.exists(path)) stop(sprintf("Config not found: %s", path))
  yaml::read_yaml(path)
}

parse_params_json <- function(param_json) {
  if (is.null(param_json) || param_json == "") return(list())
  parsed <- jsonlite::fromJSON(param_json, simplifyVector = FALSE)
  if (!is.list(parsed)) stop("Query params must be a JSON object.")
  parsed
}

validate_connection <- function(conn_cfg) {
  required <- c("host", "dbname", "user")
  missing <- setdiff(required, names(conn_cfg))
  if (length(missing) > 0)
    stop(sprintf("Missing DB fields: %s", paste(missing, collapse = ", ")))
  invisible(conn_cfg)
}

run_parameterized_query <- function(conn_cfg, query_text, params = list()) {
  validate_connection(conn_cfg)
  if (is.null(query_text) || query_text == "")
    stop("SQL query text is required.")
  conn <- DBI::dbConnect(
    RPostgres::Postgres(),
    host = conn_cfg$host, port = conn_cfg$port %||% 5432,
    dbname = conn_cfg$dbname, user = conn_cfg$user,
    password = conn_cfg$password %||% ""
  )
  on.exit(DBI::dbDisconnect(conn), add = TRUE)
  sql_statement <- if (length(params) > 0) {
    glue::glue_data_sql(params, query_text, .con = conn)
  } else { DBI::SQL(query_text) }
  DBI::dbGetQuery(conn, sql_statement)
}

ensure_columns <- function(df, required_cols) {
  missing <- setdiff(required_cols, names(df))
  if (length(missing) > 0)
    stop(sprintf("Missing columns: %s", paste(missing, collapse = ", ")))
  df
}

cache_raw_inputs <- function(df, cache_dir, prefix = "analysis") {
  if (is.null(cache_dir) || cache_dir == "") return(NULL)
  if (!dir.exists(cache_dir))
    dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  path <- file.path(cache_dir, sprintf("%s_%s.csv", prefix, timestamp))
  write.csv(df, path, row.names = FALSE)
  message("Raw inputs cached to: ", path)
  path
}
```

## A.5 Quality Gate Metrics (`stats/R_scripts/01_quality_gate_metrics.R`)

```r
#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(optparse); library(jsonlite); library(ggplot2); library(rlang)
})

SCRIPT_DIR <- get_script_dir()
source(file.path(SCRIPT_DIR, "utils_data_ingest.R"))
DEFAULT_RESULTS_DIR <- normalizePath(
  file.path(SCRIPT_DIR, "..", "results"), mustWork = FALSE)

QUALITY_GATES <- list(
  macro_f1 = 0.84, balanced_accuracy = 0.82, f1_neutral = 0.80
)
EMOTION_CLASSES <- c(
  "anger","contempt","disgust","fear",
  "happiness","neutral","sadness","surprise"
)
NEUTRAL_CLASS <- "neutral"

compute_confusion_matrix <- function(y_true, y_pred) {
  factor_true <- factor(y_true, levels = EMOTION_CLASSES)
  factor_pred <- factor(y_pred, levels = EMOTION_CLASSES)
  as.matrix(table(factor_true, factor_pred))
}

safe_div <- function(num, denom) ifelse(denom == 0, 0, num / denom)

compute_metrics <- function(y_true, y_pred) {
  cm <- compute_confusion_matrix(y_true, y_pred)
  tp <- diag(cm); fn <- rowSums(cm) - tp
  fp <- colSums(cm) - tp; tn <- sum(cm) - (tp + fn + fp)
  precision <- safe_div(tp, tp + fp)
  recall <- safe_div(tp, tp + fn)
  f1 <- safe_div(2 * precision * recall, precision + recall)
  neutral_index <- match(NEUTRAL_CLASS, EMOTION_CLASSES)
  list(
    macro_f1 = mean(f1), balanced_accuracy = mean(recall),
    f1_neutral = f1[neutral_index], accuracy = safe_div(sum(tp), sum(cm)),
    macro_precision = mean(precision), macro_recall = mean(recall),
    per_class = list(
      precision = setNames(as.numeric(precision), EMOTION_CLASSES),
      recall = setNames(as.numeric(recall), EMOTION_CLASSES),
      f1 = setNames(as.numeric(f1), EMOTION_CLASSES)
    ),
    confusion_matrix = cm
  )
}

evaluate_gates <- function(metrics) {
  gates <- list(
    macro_f1 = metrics$macro_f1 >= QUALITY_GATES$macro_f1,
    balanced_accuracy = metrics$balanced_accuracy >= QUALITY_GATES$balanced_accuracy,
    f1_neutral = metrics$f1_neutral >= QUALITY_GATES$f1_neutral
  )
  list(gates = gates, overall = all(unlist(gates)))
}

print_report <- function(metrics, gate_eval, model_name = "model") {
  cat(strrep("=", 70), "\n")
  cat("QUALITY GATE METRICS REPORT:", model_name, "\n")
  cat(strrep("=", 70), "\n\n")
  cat("--- QUALITY GATE EVALUATION ---\n")
  format_row <- function(name, value, threshold, pass) {
    status <- if (pass) "PASS" else "FAIL"
    sprintf("%-25s %10.4f %12.2f %10s\n", name, value, threshold, status)
  }
  cat(format_row("Macro F1", metrics$macro_f1,
      QUALITY_GATES$macro_f1, gate_eval$gates$macro_f1))
  cat(format_row("Balanced Accuracy", metrics$balanced_accuracy,
      QUALITY_GATES$balanced_accuracy, gate_eval$gates$balanced_accuracy))
  cat(format_row("F1 (Neutral)", metrics$f1_neutral,
      QUALITY_GATES$f1_neutral, gate_eval$gates$f1_neutral))
  cat(sprintf("Accuracy: %.4f\n", metrics$accuracy))
  cat(sprintf("Macro Precision: %.4f\n", metrics$macro_precision))
  cat(sprintf("Macro Recall: %.4f\n", metrics$macro_recall))
}

save_report <- function(metrics, gate_eval, output_path, model_name = "model") {
  data <- list(
    model_name = model_name,
    quality_gates = list(
      thresholds = QUALITY_GATES,
      results = gate_eval$gates, overall_pass = gate_eval$overall),
    metrics = list(
      macro_f1 = metrics$macro_f1,
      balanced_accuracy = metrics$balanced_accuracy,
      f1_neutral = metrics$f1_neutral, accuracy = metrics$accuracy,
      macro_precision = metrics$macro_precision,
      macro_recall = metrics$macro_recall,
      per_class = metrics$per_class,
      confusion_matrix = metrics$confusion_matrix),
    emotion_classes = EMOTION_CLASSES
  )
  write_json(data, output_path, pretty = TRUE, auto_unbox = TRUE)
}

plot_confusion_matrix <- function(metrics, output_path = NULL) {
  cm <- metrics$confusion_matrix
  df <- as.data.frame(as.table(cm))
  colnames(df) <- c("true", "pred", "n")
  plot <- ggplot(df, aes(pred, true, fill = n)) +
    geom_tile(color = "white") +
    geom_text(aes(label = n), color = "black", size = 3) +
    scale_fill_gradient(low = "#e0f3f8", high = "#08589e") +
    labs(title = "Confusion Matrix", x = "Predicted", y = "True") +
    theme_minimal()
  if (!is.null(output_path)) ggsave(output_path, plot, width=8, height=6)
  else print(plot)
}

plot_per_class_f1 <- function(metrics, output_path = NULL) {
  df <- data.frame(class = EMOTION_CLASSES,
                   f1 = as.numeric(metrics$per_class$f1))
  df$is_neutral <- df$class == NEUTRAL_CLASS
  plot <- ggplot(df, aes(x = reorder(class, -f1), y = f1, fill = is_neutral)) +
    geom_col(color = "black") +
    geom_hline(yintercept = 0.80, linetype = "dashed", color = "red") +
    scale_fill_manual(values = c("TRUE"="#1f78b4","FALSE"="#a6cee3"),
                      guide = "none") +
    labs(title = "Per-Class F1 Scores", x = "Class", y = "F1 Score") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  if (!is.null(output_path)) ggsave(output_path, plot, width=9, height=5)
  else print(plot)
}

run_analysis <- function(df, model_name = "model",
                         output_dir = NULL, do_plot = FALSE) {
  metrics <- compute_metrics(df$y_true, df$y_pred)
  gate_eval <- evaluate_gates(metrics)
  print_report(metrics, gate_eval, model_name)
  if (!is.null(output_dir)) {
    dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
    json_path <- file.path(output_dir,
                           paste0(model_name, "_quality_gate_metrics.json"))
    save_report(metrics, gate_eval, json_path, model_name)
    if (do_plot) {
      plot_confusion_matrix(metrics,
        file.path(output_dir, paste0(model_name, "_confusion_matrix.png")))
      plot_per_class_f1(metrics,
        file.path(output_dir, paste0(model_name, "_per_class_f1.png")))
    }
  }
  invisible(list(metrics = metrics, gate_eval = gate_eval))
}
```

## A.6 Stuart-Maxwell Test (`stats/R_scripts/02_stuart_maxwell_test.R`)

```r
#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(optparse); library(jsonlite); library(ggplot2)
  library(rlang); library(MASS)
})

SCRIPT_DIR <- get_script_dir()
source(file.path(SCRIPT_DIR, "utils_data_ingest.R"))
EMOTION_CLASSES <- c(
  "anger","contempt","disgust","fear",
  "happiness","neutral","sadness","surprise"
)
ALPHA_DEFAULT <- 0.05

encode_classes <- function(labels) {
  idx <- match(labels, EMOTION_CLASSES)
  if (any(is.na(idx)))
    stop(sprintf("Unknown classes: %s",
         paste(unique(labels[is.na(idx)]), collapse=", ")))
  idx
}

build_contingency <- function(base_preds, ft_preds) {
  n_classes <- length(EMOTION_CLASSES)
  table <- matrix(0, nrow = n_classes, ncol = n_classes)
  for (i in seq_along(base_preds))
    table[base_preds[i], ft_preds[i]] <- table[base_preds[i], ft_preds[i]] + 1
  table
}

compute_marginal_differences <- function(table) rowSums(table) - colSums(table)

compute_covariance_matrix <- function(table) {
  K <- nrow(table)
  row_m <- rowSums(table); col_m <- colSums(table)
  V_full <- matrix(0, nrow = K, ncol = K)
  for (i in seq_len(K)) for (j in seq_len(K)) {
    if (i == j) V_full[i,i] <- row_m[i] + col_m[i] - 2*table[i,i]
    else V_full[i,j] <- -(table[i,j] + table[j,i])
  }
  V_full[-K, -K, drop = FALSE]
}

stuart_maxwell_test <- function(base_labels, ft_labels,
                                alpha = ALPHA_DEFAULT) {
  base_idx <- encode_classes(base_labels)
  ft_idx <- encode_classes(ft_labels)
  contingency <- build_contingency(base_idx, ft_idx)
  d_full <- compute_marginal_differences(contingency)
  d_reduced <- matrix(d_full[-length(d_full)], ncol = 1)
  V <- compute_covariance_matrix(contingency)
  V_inv <- tryCatch(solve(V), error = function(e) MASS::ginv(V))
  chi_sq <- as.numeric(t(d_reduced) %*% V_inv %*% d_reduced)
  df <- length(EMOTION_CLASSES) - 1
  p_value <- 1 - pchisq(chi_sq, df)
  list(
    chi_squared = chi_sq, degrees_of_freedom = df,
    p_value = p_value, significant = p_value < alpha,
    alpha = alpha,
    marginal_differences = setNames(as.numeric(d_full), EMOTION_CLASSES),
    contingency_table = contingency,
    n_samples = length(base_labels),
    n_agreements = sum(diag(contingency)),
    n_disagreements = length(base_labels) - sum(diag(contingency))
  )
}

print_report <- function(result) {
  cat(strrep("=", 70), "\n")
  cat("STUART-MAXWELL TEST: Model Comparison\n")
  cat(strrep("=", 70), "\n\n")
  agreement_rate <- result$n_agreements / result$n_samples
  cat(sprintf("Samples: %d\n", result$n_samples))
  cat(sprintf("Agreement: %.2f%%\n", agreement_rate * 100))
  cat(sprintf("Chi-squared: %.4f\n", result$chi_squared))
  cat(sprintf("df: %d\n", result$degrees_of_freedom))
  cat(sprintf("p-value: %.6f\n", result$p_value))
  if (result$significant) {
    cat("Result: SIGNIFICANT - prediction patterns changed.\n")
  } else {
    cat("Result: NOT SIGNIFICANT\n")
  }
  cat("\nMarginal Differences (Base - Fine-tuned):\n")
  for (cls in EMOTION_CLASSES) {
    diff <- result$marginal_differences[[cls]]
    dir <- if (diff > 0) "Base more" else if (diff < 0) "FT more"
           else "No change"
    cat(sprintf("  %-15s %6.0f  %s\n", cls, diff, dir))
  }
}

save_report <- function(result, output_path) {
  payload <- list(
    test_name = "Stuart-Maxwell Test",
    description = "Marginal homogeneity test for paired categorical predictions",
    results = list(
      chi_squared = result$chi_squared,
      degrees_of_freedom = result$degrees_of_freedom,
      p_value = result$p_value, significant = result$significant,
      alpha = result$alpha,
      marginal_differences = result$marginal_differences,
      contingency_table = result$contingency_table,
      n_samples = result$n_samples, n_agreements = result$n_agreements,
      n_disagreements = result$n_disagreements
    )
  )
  write_json(payload, output_path, pretty = TRUE, auto_unbox = TRUE)
}

run_analysis <- function(df, alpha, output_dir = NULL, do_plot = FALSE) {
  result <- stuart_maxwell_test(df$base_pred, df$finetuned_pred,
                                alpha = alpha)
  print_report(result)
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    save_report(result, file.path(output_dir,
                                  "stuart_maxwell_results.json"))
  }
  invisible(result)
}
```

## A.7 Per-Class Paired t-Tests (`stats/R_scripts/03_perclass_paired_ttests.R`)

```r
#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(optparse); library(jsonlite); library(ggplot2)
  library(rlang); library(tidyr)
})

SCRIPT_DIR <- get_script_dir()
source(file.path(SCRIPT_DIR, "utils_data_ingest.R"))
EMOTION_CLASSES <- c(
  "anger","contempt","disgust","fear",
  "happiness","neutral","sadness","surprise"
)
ALPHA_DEFAULT <- 0.05

paired_t_test <- function(base_scores, ft_scores) {
  differences <- ft_scores - base_scores
  mean_diff <- mean(differences)
  std_diff <- sd(differences)
  n <- length(differences)
  if (n < 2) return(list(mean_diff=mean_diff, std_diff=0,
                         t_stat=0, p_value=1,
                         mean_base=mean(base_scores),
                         mean_ft=mean(ft_scores)))
  if (is.na(std_diff) || std_diff < 1e-10) {
    if (abs(mean_diff) < 1e-10)
      return(list(mean_diff=mean_diff, std_diff=0,
                  t_stat=0, p_value=1,
                  mean_base=mean(base_scores),
                  mean_ft=mean(ft_scores)))
    t_stat <- sign(mean_diff) * 100
    return(list(mean_diff=mean_diff, std_diff=0,
                t_stat=t_stat, p_value=1e-10,
                mean_base=mean(base_scores),
                mean_ft=mean(ft_scores)))
  }
  t_stat <- mean_diff / (std_diff / sqrt(n))
  p_value <- 2 * (1 - pt(abs(t_stat), df = n - 1))
  list(mean_diff=mean_diff, std_diff=std_diff,
       t_stat=t_stat, p_value=p_value,
       mean_base=mean(base_scores), mean_ft=mean(ft_scores))
}

benjamini_hochberg <- function(p_values, alpha = ALPHA_DEFAULT) {
  m <- length(p_values)
  order_idx <- order(p_values)
  sorted_p <- p_values[order_idx]
  adjusted <- numeric(m)
  for (i in seq_len(m)) adjusted[i] <- sorted_p[i] * m / i
  for (i in seq(m-1, 1)) adjusted[i] <- min(adjusted[i], adjusted[i+1])
  adjusted <- pmin(adjusted, 1)
  adjusted_original <- numeric(m)
  adjusted_original[order_idx] <- adjusted
  list(adjusted = adjusted_original, significant = adjusted_original < alpha)
}

run_perclass_tests <- function(df, alpha = ALPHA_DEFAULT) {
  df_list <- split(df, factor(df$emotion_class, levels = EMOTION_CLASSES))
  class_results <- list(); p_values <- numeric(length(EMOTION_CLASSES))
  for (i in seq_along(EMOTION_CLASSES)) {
    cls <- EMOTION_CLASSES[i]
    class_df <- df_list[[cls]]
    if (is.null(class_df)) stop(sprintf("Missing class '%s'", cls))
    stats <- paired_t_test(class_df$base_score, class_df$finetuned_score)
    class_results[[cls]] <- list(
      emotion_class = cls, mean_base = stats$mean_base,
      mean_finetuned = stats$mean_ft, mean_difference = stats$mean_diff,
      std_difference = stats$std_diff,
      t_statistic = stats$t_stat, p_value_raw = stats$p_value)
    p_values[i] <- stats$p_value
  }
  bh <- benjamini_hochberg(p_values, alpha)
  improved <- c(); degraded <- c()
  final_results <- vector("list", length(EMOTION_CLASSES))
  for (i in seq_along(EMOTION_CLASSES)) {
    cls <- EMOTION_CLASSES[i]; res <- class_results[[cls]]
    is_sig <- bh$significant[i]
    direction <- "unchanged"
    if (is_sig) {
      if (res$mean_difference > 0) {
        direction <- "improved"; improved <- c(improved, cls)
      } else {
        direction <- "degraded"; degraded <- c(degraded, cls)
      }
    }
    final_results[[i]] <- c(res, list(
      p_value_adjusted = bh$adjusted[i],
      significant = is_sig, direction = direction))
  }
  list(
    class_results = final_results,
    n_classes = length(EMOTION_CLASSES), alpha = alpha,
    correction_method = "Benjamini-Hochberg",
    n_significant = sum(bh$significant),
    n_improved = length(improved), n_degraded = length(degraded),
    n_unchanged = length(EMOTION_CLASSES) - sum(bh$significant),
    improved_classes = improved, degraded_classes = degraded
  )
}

print_report <- function(result) {
  cat(strrep("=", 70), "\n")
  cat("PER-CLASS PAIRED T-TESTS: Fine-Tuning Effect Analysis\n")
  cat(strrep("=", 70), "\n\n")
  cat(sprintf("Classes: %d\n", result$n_classes))
  cat(sprintf("Alpha: %.2f\n", result$alpha))
  cat(sprintf("Correction: %s\n", result$correction_method))
  cat(sprintf("Significant: %d (Improved: %d, Degraded: %d)\n",
      result$n_significant, result$n_improved, result$n_degraded))
  cat("\nDetailed Results:\n")
  cat(sprintf("%-12s %8s %8s %8s %8s %10s %10s %5s\n",
      "Class","Base","FT","Diff","t-stat","p-raw","p-adj","Sig"))
  cat(strrep("-", 80), "\n")
  ordered <- result$class_results[
    order(sapply(result$class_results, function(x) x$p_value_adjusted))]
  for (res in ordered) {
    sig <- if (res$significant) "YES" else "no"
    cat(sprintf("%-12s %8.4f %8.4f %8.4f %8.3f %10.6f %10.6f %5s\n",
        res$emotion_class, res$mean_base, res$mean_finetuned,
        res$mean_difference, res$t_statistic,
        res$p_value_raw, res$p_value_adjusted, sig))
  }
}

save_report <- function(result, output_path) {
  payload <- list(
    test_name = "Per-Class Paired t-tests",
    description = "Paired t-tests with Benjamini-Hochberg correction",
    results = result
  )
  write_json(payload, output_path, pretty = TRUE, auto_unbox = TRUE)
}

run_analysis <- function(df, alpha, output_dir = NULL, do_plot = FALSE) {
  result <- run_perclass_tests(df, alpha = alpha)
  print_report(result)
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    save_report(result, file.path(output_dir,
                                  "perclass_paired_ttests.json"))
  }
  invisible(result)
}
```
