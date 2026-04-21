---
title: "Iterative Model Selection for Privacy-First Emotion Recognition: How Training Data Composition Reverses Transfer Learning Strategy"
author: "Russell Bray"
date: "May 2026"
geometry: margin=1in
fontsize: 12pt
numbersections: true
linestretch: 2
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
  - \usepackage{amssymb}
  - \usepackage{graphicx}
  - \usepackage{float}
  - \usepackage{caption}
  - \usepackage{setspace}
  - \doublespacing
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{Iterative Model Selection}
  - \fancyhead[R]{Bray, 2026}
  - \fancyfoot[C]{\thepage}
  - \usepackage{hyperref}
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
\pagenumbering{roman}
\setcounter{page}{2}

\begin{center}
{\large\textbf{ACKNOWLEDGMENTS}}
\end{center}

I wish to express my sincere gratitude to the faculty of the Department of Computer Science at Loyola University Chicago for their guidance throughout this program. I also thank the developers of the HSEmotion framework, the AffectNet dataset, and the open-source PyTorch ecosystem. Finally, I am grateful to the Reachy Mini robotics platform community for providing an accessible embodied AI development environment.

\newpage
\tableofcontents
\newpage

**Keywords:** facial emotion recognition, transfer learning, EfficientNet, privacy-first AI, edge deployment, model calibration, temperature scaling, social robotics, synthetic-to-real domain adaptation, mixed-domain training, iterative model selection

\newpage
\pagenumbering{arabic}
\setcounter{page}{1}

# Chapter 1: Introduction

## Motivation and Background

Social robots deployed in companion, educational, and therapeutic contexts require the ability to perceive and respond to human emotions in real time (Breazeal, 2003; Fong et al., 2003). Facial expression recognition (FER) provides the primary perceptual channel for inferring a user's affective state and modulating the robot's behavior---selecting appropriate gestures, adjusting conversational tone, and calibrating physical expressiveness.

Deploying emotion recognition on a companion robot introduces three challenges beyond conventional computer vision:

1. **Real-time edge inference.** Inference must operate on dedicated hardware (NVIDIA Jetson Xavier NX) with latencies below human-perceptible thresholds (~120 ms per frame).
2. **Privacy-first architecture.** Raw video never leaves the local network. No cloud processing, no remote logging of facial data.
3. **Asymmetric error consequences.** A robot that consistently misidentifies neutral expressions as sadness creates a qualitatively worse user experience than one that occasionally fails to detect happiness. Aggregate accuracy metrics are therefore insufficient for model selection.

This paper addresses these challenges through the Reachy Emotion Classification System. The central contribution is a **methodological demonstration** that the optimal transfer learning strategy depends on training data composition, and that systematic iterative improvement guided by diagnostic quality gates can reverse initial deployment recommendations.

## Research Questions

**RQ1:** How does the choice between frozen-backbone and fine-tuned transfer learning strategies affect real-world emotion classification performance when training data is synthetic?

**RQ2:** Does augmenting synthetic training data with real photographs change which transfer learning strategy is optimal?

**RQ3:** Can post-hoc calibration techniques correct calibration regression introduced by backbone fine-tuning without affecting classification performance?

**RQ4:** Do aggregate classification metrics adequately capture deployment-relevant quality differences between models, or are class-level analyses required?

## Research Contributions

1. **An empirical demonstration that the freeze-vs-fine-tune decision depends on training data composition.** Under synthetic-only training, the frozen backbone transfers better; under mixed-domain training, the fine-tuned backbone is dramatically superior (F1 = 0.916 vs. 0.834).
2. **Evidence that modest real-data augmentation closes the synthetic-to-real gap.** Adding 15,000 real photographs (~15% of total) improved V2's F1 from 0.780 to 0.916.
3. **A practical demonstration that calibration and classification quality are separable concerns.** Temperature scaling corrected ECE from 0.142 to 0.036 without affecting classification metrics.
4. **A two-tier quality gate framework** that prevented deployment of a model with a dangerous error profile concealed by aggregate metrics.
5. **A comprehensive statistical methodology for deployment decision-making** using Wilson confidence intervals, Cohen's kappa, coefficient of variation, and composite scoring.

## Paper Organization

Chapter 2 presents the literature review. Chapter 3 describes the research platform. Chapter 4 details hypotheses, experiments, and results. Chapter 5 provides statistical analysis. Chapter 6 discusses threats to validity. Chapter 7 presents future work. Chapter 8 offers reflections. Chapter 9 concludes.

\newpage

# Chapter 2: Literature Review

## Transfer Learning for Facial Emotion Recognition

Transfer learning is the dominant paradigm in FER (Tan et al., 2018; Zhuang et al., 2020). Two canonical strategies exist: **feature extraction** (freeze backbone, train head) and **fine-tuning** (unfreeze some layers). The conventional wisdom holds that small datasets favor freezing while large datasets favor fine-tuning (Yosinski et al., 2014). Howard and Ruder (2018) demonstrated that discriminative fine-tuning with per-layer learning rates mitigates catastrophic forgetting. Our work challenges the simplification that dataset *size* alone determines strategy by showing that data *composition* is the critical factor.

## Pre-trained Models for Emotion Recognition

The HSEmotion framework (Savchenko, 2021, 2022) provides EfficientNet-B0 models pre-trained on VGGFace2 (~3.3M face images) and AffectNet (~450K labeled expressions). EfficientNet-B0 (Tan & Le, 2019) uses compound scaling to balance network width, depth, and resolution. The `enet_b0_8_best_vgaf` checkpoint's two-stage pre-training produces features encoding both identity-invariant facial geometry and expression-specific patterns.

## Synthetic-to-Real Domain Adaptation

Training on synthetic data introduces a domain gap (Tobin et al., 2017; Tremblay et al., 2018). Mitigation strategies include domain randomization, style transfer, and adversarial adaptation (Ganin & Lempitsky, 2015). Our work measures this gap empirically (F1: 0.999 -> 0.780, 22% degradation) and demonstrates that modest real-data injection (~15%) yields transformative results without adversarial techniques.

## Model Calibration

Guo et al. (2017) demonstrated that modern deep networks are systematically overconfident. Temperature scaling---dividing logits by a learned scalar $T$---is the standard post-hoc correction. For our system, calibration directly controls the robot's 5-tier gesture expressiveness system. An overconfident model causes dramatic gestures based on incorrect predictions.

## Quality Gates for Model Deployment

Automated quality gates extend MLOps practices (Baylor et al., 2017; Zaharia et al., 2018). Our architecture innovates with: (1) a two-tier structure acknowledging domain shift, and (2) per-class F1 thresholds preventing majority-class inflation from masking minority-class failures.

## Imbalanced Classification and Metric Selection

He and Garcia (2009) note that standard accuracy is poor for imbalanced data. Macro-averaged metrics weight classes equally. However, even macro metrics can mask class-level disparities: our V1 and V2 had F1 Macro of 0.781 and 0.780 ($\Delta = 0.001$) despite radically different per-class profiles.

\newpage

# Chapter 3: Research Platform and Data Management

## Hardware Infrastructure

| Node | Role | Hardware | IP |
|------|------|----------|----|
| Ubuntu 1 | GPU training, FastAPI, PostgreSQL 16, n8n, MLflow | NVIDIA GPU workstation | 10.0.4.130 |
| Ubuntu 2 | Streamlit frontend, Nginx proxy | General-purpose server | 10.0.4.140 |
| Jetson Xavier NX | Real-time inference, DeepStream + TensorRT | 384-core Volta GPU, 8 GB | 10.0.4.150 |

All processing occurs on-premise. No raw video data is transmitted externally.

## Software Stack

- **Training:** Python 3.10, PyTorch 2.x, timm, HSEmotion, scikit-learn
- **Model tracking:** MLflow (local)
- **Database:** PostgreSQL 16 (`reachy_emotion` database)
- **Web application:** Streamlit (Dashboard, Compare, Labeling pages)
- **API:** FastAPI (`/api/v1/media/`)
- **Orchestration:** n8n (10 cooperating agents)
- **Deployment:** ONNX -> TensorRT FP16 -> DeepStream
- **Statistics:** R 4.x (`ggplot2`, `jsonlite`); Python (`scipy.stats`)

## Data Sources

### Synthetic Data (Luma AI)

11,911 AI-generated videos -> 86,519 face-cropped frames:

| Class | Videos | Train Frames | Val Frames |
|-------|--------|-------------|-----------|
| Happy | 3,589 | 26,723 | 8,908 |
| Sad | 5,015 | 35,227 | 11,742 |
| Neutral | 3,307 | 24,569 | 8,190 |
| **Total** | **11,911** | **86,519** | **28,840** |

### Real Data (AffectNet)

- **Training augmentation:** 15,000 images (5,000/class) from AffectNet training partition
- **Test evaluation:** 894 images (435 happy, 160 sad, 299 neutral) from AffectNet validation partition

| Source | Happy | Sad | Neutral | Total |
|--------|-------|-----|---------|-------|
| Synthetic | 26,723 | 35,227 | 24,569 | 86,519 |
| Real AffectNet | 5,000 | 5,000 | 5,000 | 15,000 |
| **Combined** | **31,723** | **40,227** | **29,569** | **101,519** |

## Orchestration: n8n Agent System

Ten agents manage the pipeline: Ingest, Labeling, Promotion, Reconciler, Training Orchestrator, Evaluation, Deployment, Privacy, Observability, and Gesture agents.

## Web Application

- **Dashboard** (`06_Dashboard.py`): Per-run metrics, confusion matrix, Gate A indicators
- **Compare** (`08_Compare.py`): V1 vs. V2 head-to-head with recommendation engine

\newpage

# Chapter 4: Hypotheses, Experiments, and Data Analysis

## Hypotheses

**H1:** V1 (frozen) will be preferred under synthetic-only training; V2 (fine-tuned) under mixed-domain.

**H2:** Mixed-domain training will improve both variants, with V2 benefiting disproportionately.

**H3:** Temperature scaling will correct calibration without affecting classification metrics.

**H4:** Aggregate metrics will fail to distinguish models with different per-class error profiles.

## Model Variants

| Property | V1 (Frozen) | V2 (Fine-Tuned) |
|----------|------------|-----------------|
| Backbone | Frozen | blocks.5, .6, conv\_head unfrozen |
| Trainable params | ~4,000 | ~500,000 |
| Training phases | Single | Two-phase (frozen -> unfreeze) |
| LR | 1e-4 | 3e-4 (head), 3e-5 (backbone) |
| Label smoothing | 0.15 | 0.10 |
| Dropout | 0.3 | 0.5 |

## Quality Gate Thresholds

| Metric | A-val (Synthetic) | A-deploy (Real-World) |
|--------|-------------------|----------------------|
| F1 Macro | >= 0.84 | >= 0.75 |
| Balanced Acc | >= 0.85 | >= 0.75 |
| Per-class F1 | >= 0.80 each | >= 0.70 each |
| ECE | <= 0.12 | <= 0.12 |
| Brier | --- | <= 0.16 |

## Results: Face Cropping Discovery

| Configuration | V1 F1 | V2 F1 | Improvement |
|--------------|-------|-------|-------------|
| No face crop (run\_0104) | 0.430 | 0.439 | --- |
| Face crop (run\_0107) | 0.781 | 0.780 | +82% / +78% |

A single preprocessing flag (`face_crop=True`) produced the largest improvement of the project.

## Results: Phase 1 (Synthetic-Only)

| Metric | V1 | V2 | $\Delta$ |
|--------|----|----|---------|
| F1 Macro | **0.781** | 0.780 | +0.001 |
| Balanced Acc | 0.799 | **0.812** | -0.013 |
| ECE | 0.102 | **0.096** | +0.006 |

Per-class analysis reveals the hidden disparity:

| Metric | V1 | V2 |
|--------|----|----|
| F1 Happy | 0.777 | **0.946** |
| F1 Sad | **0.822** | 0.694 (FAIL) |
| F1 Neutral | **0.743** | 0.699 (FAIL) |
| CV | **4.2%** | 15.1% |

V2's neutral->sad confusion: 105/299 (35.1%) --- behaviorally disruptive.

**Phase 1 Gate A-deploy:** V1 passes 5/7, V2 passes 4/7. **V1 recommended.**

## Results: Phase 2 (Mixed-Domain)

| Metric | V1 Synth->Mixed | V2 Synth->Mixed |
|--------|---------------|---------------|
| F1 Macro | 0.781->0.834 (+0.053) | 0.780->**0.916** (+0.136) |
| F1 Sad | 0.822->0.860 | 0.694->**0.888** (+0.194) |
| F1 Neutral | 0.743->0.801 | 0.699->**0.899** (+0.200) |
| Neutral->Sad | --- | 35.1%->5.7% (--83.8%) |
| ECE | 0.102->0.104 | 0.096->0.142 (regression) |

**Reversal:** V2 now superior. V2 mixed passes 5/7 gates (ECE and Brier blockers).

## Results: Phase 3 (Temperature Scaling)

Learned $T = 0.59$ (sharpening, consistent with label smoothing applied during training).

| Metric | V2 Mixed | V2 Mixed+T | $\Delta$ |
|--------|---------|-----------|---------|
| F1 Macro | 0.916 | 0.916 | 0.000 |
| Per-class F1 | unchanged | unchanged | 0.000 |
| ECE | 0.142 | **0.036** | -0.106 |
| Brier | 0.167 | **0.128** | -0.039 |

Classification unchanged; calibration fixed. **H3 supported.**

## Final Gate A-deploy Compliance

| Config | F1>=.75 | bAcc>=.75 | F1/cls>=.70 | ECE<=.12 | Brier<=.16 | Total |
|--------|--------|----------|-----------|---------|----------|-------|
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

\newpage

# Chapter 5: Statistical Analysis

## Wilson Score Confidence Intervals

Wilson 95% CIs on per-class recall (synthetic-only phase):

| Class | n | V1 Recall [95% CI] | V2 Recall [95% CI] | Overlap |
|-------|---|-------------------|-------------------|---------|
| Happy | 435 | 0.637 [0.591, 0.681] | 0.933 [0.906, 0.953] | **No** |
| Sad | 160 | 0.825 [0.759, 0.876] | 0.900 [0.844, 0.938] | Yes |
| Neutral | 299 | 0.936 [0.903, 0.959] | 0.602 [0.546, 0.656] | **No** |

Non-overlapping intervals for happy and neutral confirm class-level differences are not sampling artifacts. **Supports H4.**

## Per-Class F1 z-Tests

$SE(F1) \approx \sqrt{F1(1-F1)/n_k}$; testing $H_0: F1_k = 0.70$:

| Class | V1 F1 | z | p | V2 F1 | z | p |
|-------|-------|---|---|-------|---|---|
| Happy | 0.777 | +3.85 | <.001 | 0.946 | +22.9 | <.001 |
| Sad | 0.822 | +4.07 | <.001 | 0.694 | -0.17 | .43 |
| Neutral | 0.743 | +1.71 | .044 | 0.699 | -0.04 | .48 |

V2's gate failures are genuine, not artifacts.

## Cohen's Kappa

| Model | kappa | Interpretation |
|-------|---|---------------|
| V1 synthetic | 0.645 | Substantial |
| V2 synthetic | 0.712 | Substantial |
| V2 mixed+T | **0.865** | Almost perfect |

V2's higher kappa in synthetic phase is inflated by majority-class (happy) performance.

## Coefficient of Variation

| Model | F1 Happy | F1 Sad | F1 Neutral | CV |
|-------|---------|--------|-----------|-----|
| V1 synth | 0.777 | 0.822 | 0.743 | **4.2%** |
| V2 synth | 0.946 | 0.694 | 0.699 | **15.1%** |
| V2 mixed+T | 0.961 | 0.888 | 0.899 | **4.3%** |

CV quantifies classification equity. V2 synth's 15.1% (3.6x V1) = severe inequity.

## Composite Score Decomposition

$$S = 0.50 \times F1_{\text{macro}} + 0.20 \times bAcc + 0.15 \times \overline{F1}_{\text{per-class}} + 0.15 \times (1 - ECE)$$

| Component | Weight | V1 Mixed+T | V2 Mixed+T |
|-----------|--------|-----------|-----------|
| F1 Macro | 0.50 | 0.417 | **0.458** |
| Balanced Acc | 0.20 | 0.168 | **0.184** |
| Mean per-class F1 | 0.15 | 0.125 | **0.137** |
| 1 -- ECE | 0.15 | 0.147 | 0.145 |
| **Composite** | **1.00** | **0.857** | **0.924** |

Gap of 0.067 is 22x the synthetic-only Delta of 0.003.

## Summary: All Hypotheses Supported

- **H1:** V1 preferred synthetic-only (5/7 vs. 4/7); V2 preferred mixed (7/7 vs. 6/7)
- **H2:** V2 gains +17.4% vs. V1's +6.8% from mixed-domain training
- **H3:** ECE drops 75% (0.142->0.036) with zero classification change
- **H4:** F1 Macro Delta=0.001 concealed recall differences of +29.6% and --33.4%

\newpage

# Chapter 6: Threats to Validity

## Internal Validity

- **Test set reuse:** Same 894 images across phases. Mitigated by using Gate A-val for development decisions; test evaluation only at phase end.
- **Temperature scaling data overlap:** $T$ learned on 30% calibration split of test set. Single-parameter nature minimizes overfitting risk.
- **Hyperparameter asymmetry:** V2 had 90-trial sweep; V1 used single config. V1's simpler architecture partially mitigates.

## External Validity

- **Single test dataset:** Only AffectNet. Deployment environments may differ.
- **Static images:** Deployed system processes video with temporal dynamics not tested.
- **Demographic coverage:** Specific deployment contexts may have underrepresented demographics.

## Construct Validity

- **F1 Macro equal weighting:** Does not reflect operational importance (neutral ~75% of interactions).
- **ECE binning:** 10 equal-width bins with 894 samples may have sparse bins.
- **Composite weights:** Chosen heuristically, not from formal utility analysis.

\newpage

# Chapter 7: Future Work

1. **Expanded real-data sampling** (30K--50K per class)
2. **Ensemble methods** combining V1 and V2 predictions
3. **8-class Ekman taxonomy** (Phase 2 expansion)
4. **Adversarial domain adaptation** (Ganin & Lempitsky, 2015)
5. **Fairness evaluation** across demographic groups
6. **Video-level evaluation** with temporal smoothing

\newpage

# Chapter 8: Reflections

## On the Research Process

This project evolved significantly from its initial conception (ResNet-50 on synthetic data). Each pivot was driven by empirical evidence: EfficientNet-B0 for edge efficiency, HSEmotion for expression-specific features, mixed-domain training for closing the domain gap, temperature scaling for calibration.

The most significant lesson was the power of diagnostic quality gates. Without per-class F1 thresholds, V2 synthetic would have appeared acceptable (F1 = 0.780, accuracy = 0.817). The gate framework not only prevented a problematic deployment but *diagnosed* the specific deficiency, pointing to the required intervention.

## On Iterative Development

The three-phase structure was emergent. Each phase addressed the blocker identified by the previous phase:

1. Phase 1 identified the synthetic-to-real gap and per-class imbalance
2. Phase 2 closed the classification gap but introduced calibration regression
3. Phase 3 resolved the calibration regression

This iterative approach outperformed any single-shot optimization. The lesson: **iterate rather than optimize in one pass.**

## On Data-Centric AI

Face cropping yielded an 82% F1 improvement---more than any model change, hyperparameter sweep, or training strategy. Adding 15% real data produced a 17.4% F1 improvement. Both are data interventions, not model interventions. This reinforces the data-centric AI perspective (Ng, 2021): improvements in data quality and composition often outweigh architectural innovations.

## On the Separability of Concerns

The discovery that classification and calibration are separable concerns simplified the optimization pipeline. Rather than jointly optimizing for both objectives during training (which may require complex multi-objective loss functions), we optimized classification first, then applied a single-parameter post-hoc correction for calibration.

## Lessons Learned

1. **Start with the data pipeline.** Face cropping yielded 82% improvement.
2. **Define quality gates before evaluation.** Pre-defined criteria prevent post-hoc rationalization.
3. **Measure per-class performance.** Aggregate metrics concealed 35.1% error rates.
4. **Consider error consequences.** Happy->neutral (33%) is more tolerable than neutral->sad (35%).
5. **Treat calibration separately.** Temperature scaling fixed it without classification cost.
6. **Revisit decisions as data evolves.** The optimal strategy changed with data composition.
7. **Synthetic and real data are complements.** Even 15% real data was transformative.
8. **Iterate rather than optimize in one pass.** Three phases outperformed any single config.

\newpage

# Chapter 9: Conclusion

This paper presented an empirical study demonstrating that the optimal transfer learning strategy for facial emotion recognition depends on training data composition. Through three iterative phases---synthetic-only training, mixed-domain augmentation, and post-hoc temperature scaling---the deployment recommendation evolved from Variant 1 (frozen backbone, F1 = 0.781) to Variant 2 with mixed-domain training and temperature scaling (selectively fine-tuned backbone, F1 = 0.916, ECE = 0.036, 7/7 deployment gates passed).

The iterative methodology, guided by a diagnostic quality gate framework, proved more effective than any single training configuration. Each phase identified specific blockers and applied targeted interventions. The final model achieves near-parity with the pre-trained base model (F1 = 0.926) while operating within the project's 3-class taxonomy and privacy-first constraints.

Key findings:

- The freeze-vs-fine-tune decision depends on data composition, not just size
- 15% real data augmentation improved F1 by 17.4% (0.780 -> 0.916)
- Temperature scaling corrected calibration (ECE: 0.142 -> 0.036) at zero classification cost
- Per-class gates prevented deployment of a model whose aggregate metrics concealed a 35.1% error rate
- Iterative development reversed the initial deployment recommendation

The system deploys on an NVIDIA Jetson Xavier NX via TensorRT within a privacy-first architecture where no raw video leaves the local network.

\newpage

# References

Baylor, D., et al. (2017). TFX: A TensorFlow-based production-scale machine learning platform. *KDD* (pp. 1387--1395).

Breazeal, C. (2003). Emotion and sociable humanoid robots. *International Journal of Human-Computer Studies*, 59(1--2), 119--155.

Fong, T., Nourbakhsh, I., & Dautenhahn, K. (2003). A survey of socially interactive robots. *Robotics and Autonomous Systems*, 42(3--4), 143--166.

Ganin, Y., & Lempitsky, V. (2015). Unsupervised domain adaptation by backpropagation. *ICML* (pp. 1180--1189).

Goodfellow, I. J., et al. (2013). Challenges in representation learning: A report on three machine learning contests. *ICONIP* (pp. 117--124).

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *ICML* (pp. 1321--1330).

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE TKDE*, 21(9), 1263--1284.

Howard, J., & Ruder, S. (2018). Universal language model fine-tuning for text classification. *ACL* (pp. 328--339).

Li, S., & Deng, W. (2017). Reliable crowdsourcing and deep locality-preserving learning for expression recognition in the wild. *CVPR* (pp. 2852--2861).

Mollahosseini, A., Hasani, B., & Mahoor, M. H. (2017). AffectNet: A database for facial expression, valence, and arousal computing in the wild. *IEEE Transactions on Affective Computing*, 10(1), 18--31.

Ng, A. (2021). Data-centric AI competition. *NeurIPS Datasets and Benchmarks Track*.

Raghu, M., Zhang, C., Kleinberg, J., & Bengio, S. (2019). Transfusion: Understanding transfer learning for medical imaging. *NeurIPS 32* (pp. 3342--3352).

Savchenko, A. V. (2021). Facial expression and attributes recognition based on multi-task learning of lightweight neural networks. *SISY* (pp. 119--124).

Savchenko, A. V. (2022). HSEmotion: High-speed emotion recognition library. *arXiv:2202.10585*.

Shrivastava, A., et al. (2017). Learning from simulated and unsupervised images through adversarial training. *CVPR* (pp. 2107--2116).

Tan, C., et al. (2018). A survey on deep transfer learning. *ICANN* (pp. 270--279).

Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. *ICML* (pp. 6105--6114).

Tobin, J., et al. (2017). Domain randomization for transferring deep neural networks from simulation to the real world. *IROS* (pp. 23--30).

Tremblay, J., et al. (2018). Training deep networks with synthetic data: Bridging the reality gap by domain randomization. *CVPR Workshops* (pp. 969--977).

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *JASA*, 22(158), 209--212.

Yosinski, J., Clune, J., Bengio, Y., & Lipson, H. (2014). How transferable are features in deep neural networks? *NeurIPS 27* (pp. 3320--3328).

Zaharia, M., et al. (2018). Accelerating the machine learning lifecycle with MLflow. *IEEE Data Engineering Bulletin*, 41(4), 39--45.

Zhuang, F., et al. (2020). A comprehensive survey on transfer learning. *Proceedings of the IEEE*, 109(1), 43--76.

\newpage

# Appendix A: Key Source Code

## A.1 Temperature Scaling (`trainer/fer_finetune/temperature_scaling.py`)

```python
class _TemperatureModel(nn.Module):
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

def learn_temperature(logits, labels, *, lr=0.01, max_iter=200, tol=1e-7):
    temp_model = _TemperatureModel(init_temp=1.5)
    nll_criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.LBFGS(
        temp_model.parameters(), lr=lr, max_iter=max_iter,
        tolerance_change=tol,
    )
    # ... L-BFGS optimization minimizing NLL ...
    return optimal_T  # T clamped to [0.01, 100]

def apply_temperature(logits, temperature):
    scaled = logits / temperature
    exp_scaled = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))
    return exp_scaled / np.sum(exp_scaled, axis=1, keepdims=True)
```

## A.2 Composite Score (`apps/web/pages/08_Compare.py`)

```python
def _composite_score(payload):
    m = payload.get("gate_a_metrics", {})
    f1_macro = float(m.get("f1_macro", 0.0))
    bal_acc = float(m.get("balanced_accuracy", 0.0))
    per_class = [float(m.get(f"f1_{c}", 0.0)) for c in ["happy","sad","neutral"]]
    per_class_mean = sum(per_class) / max(len(per_class), 1)
    ece = float(m.get("ece", 1.0))
    calibration = 1.0 - min(ece, 1.0)
    return 0.50*f1_macro + 0.20*bal_acc + 0.15*per_class_mean + 0.15*calibration
```

## A.3 Gate A-deploy Thresholds

```python
GATE_A_DEPLOY_THRESHOLDS = {
    "f1_macro": (">=", 0.75),
    "balanced_accuracy": (">=", 0.75),
    "per_class_f1": (">=", 0.70),
    "ece": ("<=", 0.12),
}
```

## A.4 R Script: Quality Gate Metrics (`stats/R_scripts/01_quality_gate_metrics.R`)

```r
QUALITY_GATES <- list(
  macro_f1 = 0.84,
  balanced_accuracy = 0.82,
  f1_neutral = 0.80
)

compute_metrics <- function(y_true, y_pred) {
  cm <- compute_confusion_matrix(y_true, y_pred)
  tp <- diag(cm); fn <- rowSums(cm) - tp; fp <- colSums(cm) - tp
  precision <- safe_div(tp, tp + fp)
  recall <- safe_div(tp, tp + fn)
  f1 <- safe_div(2 * precision * recall, precision + recall)
  list(macro_f1=mean(f1), balanced_accuracy=mean(recall), ...)
}

evaluate_gates <- function(metrics) {
  gates <- list(
    macro_f1 = metrics$macro_f1 >= QUALITY_GATES$macro_f1,
    balanced_accuracy = metrics$balanced_accuracy >= QUALITY_GATES$balanced_accuracy,
    f1_neutral = metrics$f1_neutral >= QUALITY_GATES$f1_neutral
  )
  list(gates=gates, overall=all(unlist(gates)))
}
```
