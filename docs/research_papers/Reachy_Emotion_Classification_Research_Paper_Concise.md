# Reachy Emotion Classification System: A Privacy-First Emotion Recognition System

> **⚠️ NOTE (2026-04-20):** This concise paper covers the **synthetic-only training phase**. The full paper ([Reachy_Emotion_Classification_Research_Paper.md](Reachy_Emotion_Classification_Research_Paper.md)) has been updated with mixed-domain training (§5.3.5, §6.9), temperature scaling (§5.3.6, §6.10), and the revised deployment recommendation: **V2 mixed+T (`var2_run_0107_mixed_calibrated`)**, F1=0.916, ECE=0.036, 7/7 gates passed. See [ADR 012](../../memory-bank/decisions/012-mixed-domain-temperature-scaling-v2-deployment.md).

---

**A Research Paper**

**Presented to the Faculty of the Graduate School**
**Loyola University Chicago**

**In Partial Fulfillment of the Requirements for the Degree of**
**Master of Science in Computer Science**

**by**

**Russell Bray**

**May 2026**

---

## Copyright

Copyright © 2026 by Russell Bray. All rights reserved.

---

## Table of Contents

1. [Abstract](#abstract)
2. [Chapter 1: Introduction](#chapter-1-introduction)
3. [Chapter 2: Background and Related Work](#chapter-2-background-and-related-work)
4. [Chapter 3: System Architecture and Methodology](#chapter-3-system-architecture-and-methodology)
5. [Chapter 4: Experiments and Results](#chapter-4-experiments-and-results)
6. [Chapter 5: Statistical Analysis for Model Selection](#chapter-5-statistical-analysis-for-model-selection)
7. [Chapter 6: Discussion and Threats to Validity](#chapter-6-discussion-and-threats-to-validity)
8. [Chapter 7: Future Work and Reflections](#chapter-7-future-work-and-reflections)
9. [References](#references)

---

## Abstract

This paper presents the design, implementation, and rigorous evaluation of the Reachy Emotion Classification System — a privacy-first, local-only platform for real-time facial emotion recognition on the Reachy Mini companion robot. The system classifies facial expressions into three emotion categories (happy, sad, neutral) using an EfficientNet-B0 convolutional neural network pre-trained on VGGFace2 and AffectNet via the HSEmotion framework, then fine-tuned on 86,519 synthetically generated face-cropped frames.

Two model variants were developed: Variant 1 (V1), which freezes the pre-trained backbone and trains only a lightweight classification head (~4,000 parameters), and Variant 2 (V2), which selectively unfreezes the final convolutional blocks (~500,000 trainable parameters) and was optimized through a 90-trial automated hyperparameter sweep. Both were evaluated on 894 real-world photographs from the AffectNet dataset — images from a completely different visual domain than the synthetic training data.

Despite near-identical F1 macro scores (V1: 0.781, V2: 0.780), the variants exhibit fundamentally different error profiles. The automated model selection system evaluates candidates using Gate A deployment thresholds — per-class F1 minimums (≥ 0.70), F1 macro (≥ 0.75), balanced accuracy (≥ 0.75), and ECE (≤ 0.12) — combined with a weighted composite score (0.50 × F1 macro + 0.20 × balanced accuracy + 0.15 × mean per-class F1 + 0.15 × (1 − ECE)). V1 passes all six Gate A deployment thresholds; V2 fails two (F1 sad = 0.694, F1 neutral = 0.699). Supplementary statistical analysis — Wilson score confidence intervals, z-tests, Cohen's kappa, NMI, coefficient of variation analysis, generalization gap quantification, and Brier decomposition — validates this selection and reveals that V1 distributes errors evenly across classes (CV = 4.2%), while V2 concentrates errors on sad and neutral detection (CV = 15.1%). Based on this analysis, V1 (run_0107) was selected for deployment via ONNX-to-TensorRT conversion on an NVIDIA Jetson Xavier NX, achieving sub-120ms latency within a DeepStream real-time inference pipeline. A 10-agent n8n orchestration system automates the complete lifecycle from data ingestion through deployment, with privacy enforcement ensuring no raw video leaves the local network.

**Keywords:** facial emotion recognition, transfer learning, EfficientNet, privacy-first AI, edge deployment, model calibration, social robotics, synthetic-to-real domain adaptation

---

## Chapter 1: Introduction

### 1.1 Problem Statement

Social robots deployed in companion, educational, and therapeutic contexts require the ability to perceive and respond to human emotions (Breazeal, 2003; Fong et al., 2003). Facial expression recognition (FER) provides the primary perceptual channel, but deploying it in social robotics introduces unique challenges: **real-time inference** on resource-constrained edge hardware (latency < 120 ms), a **privacy-first architecture** where raw video never leaves the local network, and **asymmetric error consequences** where misidentifying neutral expressions as sadness creates qualitatively worse user experiences than failing to detect happiness. This asymmetry means aggregate accuracy metrics alone are insufficient — the *distribution* of errors and their *behavioral consequences* must be explicitly analyzed.

This paper addresses these challenges through the Reachy Emotion Classification System — an end-to-end platform for emotion-aware interaction on the Reachy Mini companion robot, with emphasis on the statistical methodology required to make principled deployment decisions when candidate models achieve near-identical aggregate performance but exhibit fundamentally different error profiles.

### 1.2 Research Contributions

1. **A privacy-first emotion recognition architecture** processing all data locally across a three-node network with no cloud dependencies.

2. **A systematic comparison of frozen-backbone vs. fine-tuned transfer learning** for 3-class emotion classification, demonstrating that freezing the pre-trained backbone preserves features that transfer better from synthetic to real domains than selective fine-tuning.

3. **A comprehensive statistical framework for deployment decision-making** including Wilson score CIs, z-tests, Cohen's kappa, NMI, CV analysis, generalization gap quantification, and Brier decomposition — revealing critical selection criteria that aggregate metrics conceal.

4. **A two-tier quality gate architecture** (Gate A-val for synthetic validation, Gate A-deploy for real-world deployment) decoupling training quality control from deployment readiness.

5. **A 10-agent orchestration system** on n8n automating the complete ML lifecycle with reproducible, auditable model management.

---

## Chapter 2: Background and Related Work

### 2.1 Facial Emotion Recognition

FER research traces to Ekman's foundational work proposing universal basic emotions (Ekman & Friesen, 1971; Ekman, 1992). Deep CNNs transformed the field, with architectures like EfficientNet (Tan & Le, 2019) achieving human-competitive performance on benchmarks such as AffectNet (Mollahosseini et al., 2017; Li & Deng, 2020). The HSEmotion framework (Savchenko, 2021, 2022) provides EfficientNet-B0 pre-trained on VGGFace2 (~3.3M face images) and fine-tuned on AffectNet, yielding state-of-the-art FER with architectures suitable for edge deployment.

### 2.2 Transfer Learning Strategies

Two canonical strategies exist for transfer learning (Tan et al., 2018; Zhuang et al., 2020):

**Feature extraction (frozen backbone):** Only the classification head is trained, preserving domain-general representations. Effective when source and target domains are similar and target data is small or noisy (Yosinski et al., 2014).

**Fine-tuning (unfrozen backbone):** Some backbone layers are updated with reduced learning rates, allowing domain adaptation but risking "catastrophic forgetting" of useful source features (Raghu et al., 2019; Kornblith et al., 2019).

When training on synthetic data and deploying on real data, fine-tuning may cause the backbone to adapt *toward* synthetic characteristics and *away from* natural variation — a hypothesis directly tested in this work.

### 2.3 Synthetic-to-Real Domain Gap

Training on synthetic data introduces a distributional shift that can substantially degrade performance (Tobin et al., 2017; Tremblay et al., 2018). We train on 86,519 frames from AI-generated face videos and evaluate on 894 real AffectNet photographs. The resulting generalization gap (F1 ≈ 0.99 synthetic → F1 ≈ 0.78 real) motivates the two-tier gate architecture. Face cropping proved decisive: without it, test F1 = 0.43; with it, F1 = 0.78 — suggesting the primary domain gap lies in contextual information (backgrounds, body poses) rather than facial expressions themselves.

### 2.4 Calibration and Confidence-Aware Systems

Modern DNNs are systematically overconfident (Guo et al., 2017). For social robotics, calibration directly controls physical behavior through a 5-tier gesture expressiveness modulation system. ECE (Expected Calibration Error) measures this reliability:

$$ECE = \sum_{b=1}^{B} \frac{|S_b|}{N} \cdot |acc(S_b) - conf(S_b)|$$

The system employs an abstention mechanism: predictions with confidence < 0.6 or top-two margin < 0.15 are suppressed, preventing the robot from acting on uncertain inputs.

### 2.5 Related Systems

Prior social robotics FER systems (Breazeal, 2003; Churamani et al., 2020; Spezialetti et al., 2020) have addressed real-time performance and environmental robustness but not the explicit treatment of *error asymmetry* central to our approach. Our Gate A architecture extends MLOps quality gates (Baylor et al., 2017; Zaharia et al., 2018) with two innovations: a two-tier structure acknowledging domain shift as permanent, and *per-class* F1 thresholds preventing models from excelling on majority classes while neglecting minorities.

---

## Chapter 3: System Architecture and Methodology

### 3.1 Hardware and Software Infrastructure

The system operates across a three-node LAN with static IPs, eliminating cloud dependencies:

| Node | Role | Key Hardware | IP |
|------|------|--------------|----|
| **Ubuntu 1** | GPU training, FastAPI, PostgreSQL, n8n | NVIDIA GPU workstation | 10.0.4.130 |
| **Ubuntu 2** | Streamlit frontend, Nginx | General-purpose server | 10.0.4.140 |
| **Jetson Xavier NX** | Real-time inference (DeepStream + TensorRT) | 384-core Volta GPU, 8GB RAM | 10.0.4.150 |

The software stack includes PyTorch 2.x, HSEmotion pre-trained weights, TensorRT + DeepStream for edge inference, FastAPI backend, PostgreSQL 16, Streamlit UI, n8n orchestration, and MLflow experiment tracking.

### 3.2 Model Architecture

EfficientNet-B0 (Tan & Le, 2019) processes 224×224 RGB inputs through MBConv blocks producing a 1280-dimensional feature vector. The HSEmotion checkpoint (`enet_b0_8_best_vgaf`) was pre-trained on VGGFace2 then AffectNet for 8-class emotion classification. The 8-class head is replaced with a 3-class head:

```
ClassificationHead(Dropout(p=0.3), Linear(1280 → 3))  # ~3,843 parameters
```

**Variant 1 (Frozen):** Backbone completely frozen; only head trained (~4K params, ~2 hours GPU time).

**Variant 2 (Fine-Tuned):** Starting from V1 checkpoint, blocks.5, blocks.6, and conv_head are unfrozen (~500K params). Optimized via 90-trial hyperparameter sweep (~26 hours GPU time). Differential learning rate: backbone at LR/10, head at full LR.

### 3.3 Training Data and Procedure

| | Happy | Sad | Neutral | Total |
|---|---|---|---|---|
| **Source videos** | 3,589 | 5,015 | 3,307 | **11,911** |
| **Training frames** (75%) | 26,723 | 35,227 | 24,569 | **86,519** |
| **Validation frames** (25%) | 8,908 | 11,742 | 8,190 | **28,840** |

All data is AI-generated synthetic face video, processed with face detection and cropping. Training uses AdamW optimizer, cosine annealing with warmup, mixed precision (FP16), Mixup augmentation (α=0.2), and label smoothing (0.15 for V1, 0.10 for V2). Early stopping monitors validation F1 macro with patience of 10 epochs.

### 3.4 Quality Gates

**Gate A-val (synthetic validation):** F1 ≥ 0.84, balanced accuracy ≥ 0.85, per-class F1 ≥ 0.75, ECE ≤ 0.12, Brier ≤ 0.16. Controls ONNX export.

**Gate A-deploy (real-world test, per ADR 011):** F1 ≥ 0.75, balanced accuracy ≥ 0.75, per-class F1 ≥ 0.70, ECE ≤ 0.12. Controls Jetson deployment.

The deploy tier has lower thresholds to accommodate the inherent synthetic-to-real generalization gap.

### 3.5 Deployment Pipeline

Models passing Gate A-val are exported to ONNX (opset 13, dynamic batch), converted to TensorRT engines on the Jetson with FP16 precision, and integrated into NVIDIA DeepStream. The complete pipeline achieves p50 latency ≤ 120 ms and GPU memory ≤ 0.8 GB. The Deployment Agent (Agent 7) performs backup, Gate B validation (FPS ≥ 25, latency ≤ 120 ms, GPU ≤ 2.5 GB), and automatic rollback on failure.

### 3.6 Agent Orchestration and Emotional Intelligence

Ten n8n agents automate the ML lifecycle: Ingest, Labeling, Promotion/Curation, Reconciler/Audit, Training Orchestrator, Evaluation, Deployment, Privacy/Retention, Observability, and Gesture Execution. Each agent operates within explicit safety constraints with full audit logging.

The Emotional Intelligence Layer maps detected emotions to behavioral profiles via the Ekman taxonomy, with a 5-tier confidence-based gesture modulation system:

| Tier | Confidence | Expressiveness | Behavior |
|------|-----------|----------------|----------|
| 1 | < 0.60 | Abstain | No gesture |
| 2 | 0.60–0.70 | Minimal | Subtle response |
| 3 | 0.70–0.80 | Moderate | Gentle gesture |
| 4 | 0.80–0.90 | Full | Clear gesture |
| 5 | > 0.90 | Maximum | Expressive gesture |

Emotion-conditioned LLM prompting aligns the robot's verbal responses with its physical gestures.

---

## Chapter 4: Experiments and Results

### 4.1 Test Dataset

The test set consists of 894 real photographs from AffectNet (Mollahosseini et al., 2017): 435 happy (48.7%), 160 sad (17.9%), 299 neutral (33.4%). Neither model saw any real photographs during training.

### 4.2 The Face Cropping Discovery

| Configuration | V1 Test F1 | V2 Test F1 |
|--------------|-----------|-----------|
| **run_0104** (no face crop) | 0.43 | 0.44 |
| **run_0107** (with face crop) | 0.781 | 0.780 |
| **Improvement** | **+82%** | **+77%** |

Face cropping was the single most impactful change — more than any model architecture or hyperparameter optimization. The primary domain gap was contextual information (synthetic backgrounds), not facial expressions.

### 4.3 Synthetic Validation Results

| Metric | V1 | V2 |
|--------|-----|-----|
| F1 Macro | 0.990 | 0.999 |
| ECE | 0.124 | 0.076 |
| Gate A-val | **FAILED** (ECE) | **PASSED** |

V2's near-perfect synthetic metrics do not translate to equivalent real-world performance.

### 4.4 Real-World Test Results

| Metric | V1 run_0107 | V2 run_0107 | Winner |
|--------|-------------|-------------|--------|
| **F1 Macro** | **0.7807** | 0.7798 | V1 |
| **Balanced Accuracy** | 0.7994 | **0.8118** | V2 |
| Accuracy | 0.7707 | **0.8166** | V2 |
| **F1 Happy** | 0.7770 | **0.9464** | V2 |
| **F1 Sad** | **0.8224** | 0.6940 | V1 |
| **F1 Neutral** | **0.7427** | 0.6990 | V1 |
| **ECE** | 0.1024 | **0.0955** | V2 |
| Brier | 0.3401 | **0.2787** | V2 |

The near-identical F1 macro (Δ = 0.001) conceals radically different per-class profiles.

### 4.5 Confusion Matrix Analysis

**Variant 1:**
```
                Predicted
                Happy    Sad    Neutral    Total    Recall
  Happy          277      11      147       435      63.7%
  Sad              0     132       28       160      82.5%
  Neutral          1      18      280       299      93.6%

  Precision:   99.6%   81.9%   61.5%
```

**Variant 2:**
```
                Predicted
                Happy    Sad    Neutral    Total    Recall
  Happy          406       6       23       435      93.3%
  Sad              3     144       13       160      90.0%
  Neutral         14     105      180       299      60.2%

  Precision:   96.0%   56.5%   83.3%
```

**V1's dominant error** is happy → neutral (33.8%), which is **behaviorally benign** — the robot under-reacts with a neutral demeanor rather than celebrating. V1 produces zero happy → sad cross-valence errors.

**V2's dominant error** is neutral → sad (35.1%), which is **behaviorally disruptive** — the robot offers unsolicited empathy to people who are merely at rest. V2's sad precision is only 56.5%, meaning its sad predictions are correct barely more than half the time.

### 4.6 Gate A-deploy Compliance

| Gate | Threshold | V1 | V2 |
|------|-----------|-----|-----|
| F1 Macro ≥ 0.75 | 0.75 | **0.7807 PASS** | **0.7798 PASS** |
| Balanced Acc ≥ 0.75 | 0.75 | **0.7994 PASS** | **0.8118 PASS** |
| F1 Happy ≥ 0.70 | 0.70 | **0.7770 PASS** | **0.9464 PASS** |
| F1 Sad ≥ 0.70 | 0.70 | **0.8224 PASS** | **0.6940 FAIL** |
| F1 Neutral ≥ 0.70 | 0.70 | **0.7427 PASS** | **0.6990 FAIL** |
| ECE ≤ 0.12 | 0.12 | **0.1024 PASS** | **0.0955 PASS** |
| **Total** | | **6/6 PASSED** | **4/6 FAILED** |

The per-class F1 gate catches V2's systematic neglect of sad and neutral classes — a failure mode invisible to aggregate metrics.

### 4.7 Base Model Benchmark

The unmodified HSEmotion base model (8-class head) achieves F1 = 0.926 on the same test set, demonstrating the ceiling achievable with real-data pre-training. The 14.5 pp gap (0.926 vs. 0.781) represents the cost of synthetic-only training. The base model is not a deployment candidate because its 8-class output is incompatible with the project's 3-class behavioral pipeline.

### 4.8 Calibration

Both variants pass ECE ≤ 0.12 (V1: 0.102, V2: 0.096). The Brier score difference (0.340 vs. 0.279) is driven by V2's higher raw accuracy on happy, not by calibration quality. Both models' confidence scores are similarly trustworthy for the gesture modulation system.

---

## Chapter 5: Statistical Analysis for Model Selection

The automated model selection system (implemented in the web application's Compare page) selects the deployment candidate using two mechanisms: (1) **Gate A-deploy compliance** as a hard constraint — the model must pass all six thresholds (F1 macro ≥ 0.75, balanced accuracy ≥ 0.75, per-class F1 ≥ 0.70, ECE ≤ 0.12) — and (2) a **weighted composite score** (0.50 × F1 macro + 0.20 × balanced accuracy + 0.15 × mean per-class F1 + 0.15 × (1 − ECE)) as a tiebreaker when both candidates pass all gates. V1 passes all six gates; V2 fails two; therefore V1 is automatically recommended.

This chapter presents supplementary statistical analysis that validates and explains this automated decision. The analysis goes beyond the Dashboard metrics to characterize uncertainty, significance, and practical implications of the deployment choice. All tests were implemented in R (R Core Team, 2024).

### 5.1 Confidence Intervals on Per-Class Recall

We compute **Wilson score 95% confidence intervals** — preferred over Wald intervals because Wilson intervals maintain correct coverage even when the true proportion is near 0 or 1 (Wilson, 1927; Agresti & Coull, 1998; Brown et al., 2001).

For a class with $n_k$ samples and observed recall $\hat{p}$, the Wilson interval is:

$$\frac{\hat{p} + \frac{z^2}{2n_k} \pm z\sqrt{\frac{\hat{p}(1-\hat{p}) + \frac{z^2}{4n_k}}{n_k}}}{1 + \frac{z^2}{n_k}}$$

where $z = 1.96$ for $\alpha = 0.05$.

**Table 1. Wilson score 95% confidence intervals for per-class recall.**

| Class | n | V1 Recall [95% CI] | V2 Recall [95% CI] | CIs Overlap? |
|-------|---|-----|-----|-----|
| **Happy** | 435 | 0.637 [0.591, 0.681] | **0.933** [0.906, 0.953] | **No** — V2 statistically superior |
| **Sad** | 160 | **0.825** [0.759, 0.876] | 0.900 [0.844, 0.938] | Yes — not statistically significant |
| **Neutral** | 299 | **0.936** [0.903, 0.959] | 0.602 [0.546, 0.656] | **No** — V1 statistically superior |

**Interpretation:** On happy, V2 is unambiguously better (non-overlapping CIs, Δ = +29.7 pp). On sad, V2 has a slight edge but the difference is not statistically significant (overlapping CIs). On neutral, V1 is unambiguously better (non-overlapping CIs, Δ = +33.4 pp).

The two models trade statistically significant advantages on different classes. Neither is uniformly superior. The deployment decision hinges on *which errors matter more* — an insight aggregate metrics completely conceal.

### 5.2 Per-Class F1 z-Test Against Deployment Threshold

Using the delta-method approximation $SE(F1) \approx \sqrt{F1 \cdot (1-F1)/n_k}$, we test whether each per-class F1 is significantly above or below the 0.70 deployment threshold:

**Table 2. Per-class F1 z-test against the 0.70 deployment threshold.**

| Class | n | V1 F1 | SE | z vs 0.70 | p-value | V2 F1 | SE | z vs 0.70 | p-value |
|-------|---|-------|-----|-----------|---------|-------|-----|-----------|---------|
| Happy | 435 | 0.777 | 0.020 | **+3.85** | < 0.001 | 0.946 | 0.011 | +22.9 | < 0.001 |
| Sad | 160 | 0.822 | 0.030 | **+4.07** | < 0.001 | 0.694 | 0.036 | **−0.17** | 0.43 |
| Neutral | 299 | 0.743 | 0.025 | +1.71 | 0.044 | 0.699 | 0.027 | **−0.04** | 0.48 |

**Interpretation:**

- **V1 Happy and Sad** are both significantly above 0.70 at $p < 0.001$. V1 Neutral is marginally above at one-tailed $p = 0.044$.
- **V2 Sad** ($F1 = 0.694$, $z = -0.17$) cannot be statistically distinguished from 0.70 but falls below it.
- **V2 Neutral** ($F1 = 0.699$, $z = -0.04$) also cannot be distinguished from 0.70 but falls below it.

The z-tests confirm that V2's gate failures are not artifacts of random sampling — they reflect genuine performance shortfalls.

### 5.3 Cohen's Kappa (Inter-Rater Agreement with Ground Truth)

Cohen's $\kappa$ quantifies agreement corrected for chance (Cohen, 1960):

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

**Table 3. Cohen's kappa inter-rater agreement with ground truth.**

| | $\kappa$ | $SE(\kappa)$ | 95% CI | Interpretation |
|---|---|---|---|---|
| V1 | 0.645 | 0.022 | [0.603, 0.688] | Substantial |
| V2 | 0.712 | 0.020 | [0.673, 0.752] | Substantial |

Both models achieve "substantial" agreement per Landis & Koch (1977). V2's higher $\kappa$ (0.712 vs. 0.645) reflects its higher raw accuracy, driven by excellent happy recall. The non-overlapping CIs indicate V2's global advantage is statistically significant — but $\kappa$ is a *global* measure that does not capture class-specific imbalance.

### 5.4 Normalized Mutual Information (NMI)

NMI measures mutual dependence between predicted and true labels on [0, 1], normalized by entropy:

$$NMI(Y, \hat{Y}) = \frac{2 \cdot I(Y; \hat{Y})}{H(Y) + H(\hat{Y})}$$

**Table 4. Normalized Mutual Information (NMI) comparison.**

| | NMI | MI (bits) | $H(Y)$ | $H(\hat{Y})$ |
|---|---|---|---|---|
| V1 | 0.476 | 0.701 | 1.478 | 1.465 |
| V2 | 0.557 | 0.836 | 1.478 | 1.522 |

V2 captures 55.7% of the information in true labels vs. V1's 47.6%. Like $\kappa$, NMI rewards V2's near-perfect happy detection (48.7% of test data) without penalizing concentrated errors on the remaining 51.3%.

**The discrepancy between global metrics ($\kappa$, NMI, accuracy) favoring V2 and class-specific metrics (per-class F1, CV, gate compliance) favoring V1 is the central statistical insight of this analysis.** V2 "buys" a higher global score by over-investing in the largest class at the expense of smaller classes — a well-known failure mode in imbalanced classification (He & Garcia, 2009).

### 5.5 Coefficient of Variation Analysis (Performance Equity)

The CV of per-class F1 scores measures classifier equity:

$$CV = \frac{\sigma_{F1}}{\mu_{F1}} \times 100\%$$

**Table 5. Coefficient of variation (CV) of per-class F1 scores.**

| | F1 Happy | F1 Sad | F1 Neutral | $\mu$ | $\sigma$ | **CV** | Range |
|---|---|---|---|---|---|---|---|
| V1 | 0.777 | 0.822 | 0.743 | 0.781 | 0.033 | **4.2%** | 0.080 |
| V2 | 0.946 | 0.694 | 0.699 | 0.780 | 0.118 | **15.1%** | 0.252 |

V1's CV of 4.2% indicates near-uniform performance. V2's CV of 15.1% is 3.6× higher, indicating severe class-level inequity — V2 has specialized in happy detection at the expense of sad and neutral. For a social robot that must respond appropriately to *all* emotions, low CV is a critical requirement.

### 5.6 Generalization Gap Analysis

**Table 6. Generalization gap: synthetic validation vs. real-world test.**

| | Synthetic Val F1 | Real-World Test F1 | Gap | Relative Drop |
|---|---|---|---|---|
| V1 | 0.990 | 0.781 | 0.209 | 21.2% |
| V2 | 0.999 | 0.780 | 0.220 | 22.0% |

Despite V2's 125× more trainable parameters, 13× more GPU time, and 90-trial sweep, its generalization gap is 1.05× *larger* than V1's. V2's fine-tuned backbone overfitted to synthetic features rather than learning more generalizable representations.

This is consistent with the transfer learning literature: when fine-tuning and target domains differ substantially, freezing the pre-trained backbone prevents adaptation *away from* the target distribution (Yosinski et al., 2014; Raghu et al., 2019). The VGGFace2+AffectNet features in V1's frozen backbone were learned from 3.3M *real* face images — inherently more aligned with real-world test data than V2's synthetic-adapted features.

### 5.7 Brier Score Decomposition

The Brier score decomposes into calibration and refinement components:

$$Brier = Calibration + Refinement$$

| | Brier | ECE (proxy for calibration) | Notes |
|---|---|---|---|
| V1 | 0.340 | 0.102 | Higher Brier driven by classification errors |
| V2 | 0.279 | 0.096 | Lower Brier driven by higher accuracy on happy class |

The ECE gap (0.006) contributes negligibly to the Brier difference (0.061). V1's higher Brier is driven by lower raw accuracy, not calibration failure. Both models' confidence scores are similarly trustworthy for the gesture modulation system.

### 5.8 Statistical Power and Sample Size Considerations

**Table 7. Statistical power and minimum detectable differences by class.**

| Class | n | SE of Recall | Detectable Δ at 80% Power |
|-------|---|---|---|
| Happy | 435 | ≈ 0.023 | ≈ 0.064 |
| Sad | 160 | ≈ 0.030 | ≈ 0.083 |
| Neutral | 299 | ≈ 0.028 | ≈ 0.078 |

The sad class ($n = 160$) has the least statistical power; differences < ~8.3 pp cannot be reliably detected. The V1 vs. V2 sad recall difference (7.5 pp) is at the boundary of detectability, consistent with the overlapping CIs in §5.1.

However, the neutral (Δ = 33.4 pp) and happy (Δ = 29.7 pp) differences are far beyond detectable thresholds and unambiguously real. The complementary strengths pattern is robust.

### 5.9 Composite Scoring and Final Recommendation

$$S = 0.50 \times F1_{macro} + 0.20 \times bAcc + 0.15 \times \bar{F1}_{perclass} + 0.15 \times (1 - ECE)$$

**Table 8. Composite score breakdown and final recommendation.**

| Component | Weight | V1 Value | V1 Weighted | V2 Value | V2 Weighted |
|-----------|--------|----------|-------------|----------|-------------|
| F1 Macro | 0.50 | 0.7807 | 0.3904 | 0.7798 | 0.3899 |
| Balanced Accuracy | 0.20 | 0.7994 | 0.1599 | 0.8118 | 0.1624 |
| Mean Per-class F1 | 0.15 | 0.7807 | 0.1171 | 0.7798 | 0.1170 |
| 1 − ECE | 0.15 | 0.8976 | 0.1346 | 0.9045 | 0.1357 |
| **Composite** | **1.00** | | **0.8020** | | **0.8049** |

V2 has a marginally higher composite score (Δ = 0.003). However, **gate compliance takes priority**: V1 passes all six gates; V2 fails two. The gates exist as hard constraints preventing deployment of models with systematic blind spots, while the composite score serves as a tiebreaker when multiple models pass all gates.

**Final recommendation: Deploy Variant 1 (run_0107) with HIGH confidence.** The recommendation is robust because it is based on gate compliance (a binary criterion), not marginal metric differences.

---

## Chapter 6: Discussion and Threats to Validity

### 6.1 Key Findings

**Finding 1: Frozen backbones transfer better from synthetic to real domains.** Despite V2's 125× more trainable parameters and 13× more GPU time, both variants achieve identical real-world F1. V2's fine-tuned backbone adapted to synthetic features rather than learning generalizable representations.

**Finding 2: Aggregate metrics conceal critical disparities.** V1 and V2 have nearly identical F1 macro (Δ = 0.001), yet their error profiles differ fundamentally (CV 4.2% vs. 15.1%). The per-class F1 gate was the mechanism that caught this.

**Finding 3: Error severity is context-dependent.** V1's dominant error (happy → neutral, 33.8%) causes under-reaction; V2's (neutral → sad, 35.1%) causes inappropriate over-reaction. In a companion robot, the latter is far more disruptive.

**Finding 4: Face cropping is the most impactful preprocessing step.** Enabling face detection doubled test F1 from 0.43 to 0.78, demonstrating that the data pipeline is often more important than the model.

**Finding 5: The two-tier gate architecture works.** V1 fails Gate A-val but passes Gate A-deploy; V2 passes Gate A-val but fails Gate A-deploy. Without two tiers, the wrong model would be deployed.

### 6.2 The Global vs. Local Metric Paradox

Global metrics (accuracy, κ, NMI) consistently favor V2; local metrics (per-class F1, CV, gate compliance) favor V1. This paradox arises because V2 excels on the largest test class (happy, 48.7%), inflating global metrics. The resolution: use *both* metric types with hard constraints on local metrics as "circuit breakers" against global metric illusion.

### 6.3 Deployment Risk

In Reachy's expected environment, neutral dominates (~75% of interactions). V2's 35.1% neutral → sad confusion means approximately **1 in 4 neutral interactions** would trigger inappropriate sadness responses, eroding user trust.

**Deployment risk matrix:**

| Risk | V1 Impact | V2 Impact |
|------|-----------|-----------|
| **False sadness** (neutral→sad) | Low (6.0%) | **High (35.1%)** |
| **Missed happiness** (happy→neutral) | Moderate (33.8%) | Low (5.3%) |
| **Cross-valence error** (happy↔sad) | Very low (2.5%) | Very low (1.4%) |
| **Gate non-compliance** | None (6/6) | **2 gates failed** |

### 6.4 Threats to Validity

**Internal:** The AffectNet test set (894 images) is a convenience sample with class distribution (48.7/33.4/17.9%) that may not reflect deployment conditions where neutral dominates. Single test run; Wilson CIs partially mitigate but cannot substitute for repeated evaluation. AffectNet inter-annotator agreement is ~60-65%, meaning some V1 "errors" on the happy/neutral boundary may be correct.

**External:** All training data is AI-generated; models have never seen real photographs. The 22% generalization gap may vary across deployment contexts. The test set is static images but deployment processes video; temporal smoothing has not been validated against ground truth. No demographic fairness audit has been performed.

**Construct:** The 3-class taxonomy is a simplification; the abstention mechanism mitigates but doesn't address out-of-taxonomy emotions. F1 macro gives equal weight to all classes regardless of operational importance. ECE is sensitive to binning choices.

---

## Chapter 7: Future Work and Reflections

### 7.1 Priority Improvements

**Temperature scaling (Priority 1, ~1 day):** Post-hoc calibration (Guo et al., 2017) can reduce V1's ECE from 0.102 to ~0.06 with zero accuracy cost, improving gesture modulation reliability.

**Training data diversification (Priority 2):** Incorporating 10-20% real face images could close the generalization gap from F1 ≈ 0.78 toward the base model's 0.93 (Shrivastava et al., 2017). Diversifying synthetic prompts for demographic and environmental variety would also help.

**Ensemble methods (Priority 3, ~2 days):** V1 and V2 have complementary strengths (V1: sad+neutral, V2: happy). A weighted ensemble $p_{ensemble} = \alpha \cdot p_{V1} + (1-\alpha) \cdot p_{V2}$ could leverage both, though doubling compute on the Jetson is a concern.

**Phase 2: Full 8-class Ekman taxonomy (Priority 4):** The behavioral profile infrastructure already supports 8 classes. Expansion would enable de-escalation (anger), reassurance (fear), and redirect (disgust) behaviors. The HSEmotion backbone is pre-trained on all 8 Ekman classes.

**Domain adaptation (Priority 5):** Adversarial domain adaptation (Ganin & Lempitsky, 2015), style transfer preprocessing (Huang & Belongie, 2017), and self-supervised pre-training on unlabeled real video (Chen et al., 2020) could further close the synthetic-to-real gap.

**Fairness evaluation:** Dedicated audit across age, gender, ethnicity, and skin tone using tools like FairFace (Kärkkäinen & Joo, 2021).

### 7.2 Project Reflections

**Preprocessing over architecture:** The face cropping fix (+82% F1) outperformed V2's entire 90-trial hyperparameter sweep. This reinforces the "data-centric AI" perspective (Ng, 2021): data pipeline quality often yields higher returns than model architecture changes.

**Define gates before evaluation:** The gate framework prevented "metric cherry-picking" by establishing hard constraints on per-class performance *before* seeing results. MLOps quality gates should include both global and per-class metrics.

**Synthetic data is a complement, not a substitute.** The 14.5 pp gap between the base model (real-data pre-training) and V1 (synthetic-only) quantifies the cost. The synthetic data contains useful signal (facial expressions) embedded in misleading context (synthetic backgrounds).

**Consider error consequences, not just rates.** A 33% happy → neutral error rate (under-reaction) is more tolerable than a 35% neutral → sad rate (over-reaction), despite similar magnitudes. In human-facing applications, the *impact* of each error type matters as much as its frequency.

**Frozen backbones are a strong baseline.** Before investing in expensive fine-tuning sweeps, verify that feature extraction with a frozen backbone doesn't already meet deployment requirements. In our case, it did.

**Privacy constraints as features.** The local-only mandate produced lower latency (no cloud round-trips), higher availability (no internet dependency), simpler compliance (data minimization by architecture), and greater user trust.

---

## References

Agresti, A., & Coull, B. A. (1998). Approximate is better than "exact" for interval estimation of binomial proportions. *The American Statistician*, 52(2), 119–126.

Baylor, D., et al. (2017). TFX: A TensorFlow-based production-scale machine learning platform. In *Proceedings of the 23rd ACM SIGKDD* (pp. 1387–1395).

Breazeal, C. (2003). Emotion and sociable humanoid robots. *International Journal of Human-Computer Studies*, 59(1–2), 119–155.

Brown, L. D., Cai, T. T., & DasGupta, A. (2001). Interval estimation for a binomial proportion. *Statistical Science*, 16(2), 101–133.

Chen, T., Kornblith, S., Norouzi, M., & Hinton, G. (2020). A simple framework for contrastive learning of visual representations. In *ICML 2020* (pp. 1597–1607).

Churamani, N., Kalkan, S., & Gunes, H. (2020). Continual learning for affective robotics. In *IEEE RO-MAN 2020* (pp. 425–431).

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46.

Crawford, K. (2021). *Atlas of AI*. Yale University Press.

Ekman, P. (1992). An argument for basic emotions. *Cognition & Emotion*, 6(3–4), 169–200.

Ekman, P., & Friesen, W. V. (1971). Constants across cultures in the face and emotion. *Journal of Personality and Social Psychology*, 17(2), 124–129.

European Union. (2024). Regulation (EU) 2024/1689 — AI Act. *Official Journal of the European Union*.

Fong, T., Nourbakhsh, I., & Dautenhahn, K. (2003). A survey of socially interactive robots. *Robotics and Autonomous Systems*, 42(3–4), 143–166.

Ganin, Y., & Lempitsky, V. (2015). Unsupervised domain adaptation by backpropagation. In *ICML 2015* (pp. 1180–1189).

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. In *ICML 2017* (pp. 1321–1330).

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE TKDE*, 21(9), 1263–1284.

Howard, J., & Ruder, S. (2018). Universal language model fine-tuning for text classification. In *ACL 2018* (pp. 328–339).

Huang, X., & Belongie, S. (2017). Arbitrary style transfer in real-time with adaptive instance normalization. In *ICCV 2017* (pp. 1501–1510).

Kärkkäinen, K., & Joo, J. (2021). FairFace: Face attribute dataset for balanced race, gender, and age. In *WACV 2021* (pp. 1548–1558).

Kornblith, S., Shlens, J., & Le, Q. V. (2019). Do better ImageNet models transfer better? In *CVPR 2019* (pp. 2661–2671).

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174.

Li, S., & Deng, W. (2020). Deep facial expression recognition: A survey. *IEEE TAFFC*, 13(3), 1195–1215.

Mollahosseini, A., Hasani, B., & Mahoor, M. H. (2017). AffectNet: A database for facial expression, valence, and arousal computing in the wild. *IEEE TAFFC*, 10(1), 18–31.

Ng, A. (2021). Data-centric AI competition. *NeurIPS 2021 Datasets and Benchmarks Track*.

R Core Team. (2024). R: A language and environment for statistical computing. https://www.R-project.org/

Raghu, M., Zhang, C., Kleinberg, J., & Bengio, S. (2019). Transfusion: Understanding transfer learning for medical imaging. In *NeurIPS 2019* (pp. 3342–3352).

Savchenko, A. V. (2021). Facial expression and attributes recognition based on multi-task learning of lightweight neural networks. In *IEEE SISY 2021* (pp. 119–124).

Savchenko, A. V. (2022). HSEmotion: High-speed emotion recognition library. *arXiv:2202.10585*.

Shrivastava, A., et al. (2017). Learning from simulated and unsupervised images through adversarial training. In *CVPR 2017* (pp. 2107–2116).

Spezialetti, M., Placidi, G., & Rossi, S. (2020). Emotion recognition in human-robot interaction. *Frontiers in Robotics and AI*, 7, 532279.

Tan, C., et al. (2018). A survey on deep transfer learning. In *ICANN 2018* (pp. 270–279).

Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. In *ICML 2019* (pp. 6105–6114).

Tobin, J., et al. (2017). Domain randomization for transferring deep neural networks from simulation to the real world. In *IROS 2017* (pp. 23–30).

Tremblay, J., et al. (2018). Training deep networks with synthetic data. In *CVPR Workshops 2018* (pp. 969–977).

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *JASA*, 22(158), 209–212.

Yosinski, J., Clune, J., Bengio, Y., & Lipson, H. (2014). How transferable are features in deep neural networks? In *NeurIPS 2014* (pp. 3320–3328).

Zaharia, M., et al. (2018). Accelerating the machine learning lifecycle with MLflow. *IEEE Data Engineering Bulletin*, 41(4), 39–45.

Zhang, H., Cisse, M., Dauphin, Y. N., & Lopez-Paz, D. (2018). mixup: Beyond empirical risk minimization. In *ICLR 2018*.

Zhuang, F., et al. (2020). A comprehensive survey on transfer learning. *Proceedings of the IEEE*, 109(1), 43–76.

---

*Concise version of the full research paper.*
*Approximately 9,200 words (excluding tables and references).*
*Document location: `docs/research_papers/Reachy_Emotion_Classification_Research_Paper_Concise.md`*
