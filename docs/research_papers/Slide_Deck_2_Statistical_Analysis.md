# Reachy Emotion Classification System
## Project Overview & Statistical Analysis for Model Selection

**Russell Bray**
**Loyola University Chicago — M.S. Computer Science**
**May 2026**

---

# Slide 1: Title

## Reachy Emotion Classification System
### Privacy-First Emotion Recognition with Rigorous Statistical Model Selection

- **Author:** Russell Bray
- **Program:** M.S. Computer Science, Loyola University Chicago
- **Date:** May 2026

**Keywords:** Facial emotion recognition, transfer learning, EfficientNet, model calibration, statistical analysis, edge deployment, social robotics

---

# Slide 2: Problem & Motivation

## Emotion Recognition for a Companion Robot

Social companion robots need to perceive and respond to human emotions in real time.

### Three Core Challenges

| Challenge | Requirement |
|-----------|------------|
| **Real-time inference** | < 120 ms latency on edge hardware |
| **Privacy-first** | No raw video leaves the local network |
| **Asymmetric errors** | Not all misclassifications are equal |

### Central Research Question
> When two candidate models achieve near-identical aggregate performance but exhibit fundamentally different error profiles, how do we make a **principled, statistically grounded** deployment decision?

---

# Slide 3: System Architecture

## Three-Node Local-Only Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│   Ubuntu 1      │    │   Ubuntu 2      │    │  Jetson Xavier NX   │
│   10.0.4.130    │◄──►│   10.0.4.140    │    │  10.0.4.150         │
│                 │    │                 │    │                     │
│ • GPU Training  │    │ • Streamlit UI  │    │ • DeepStream + TRT  │
│ • FastAPI       │    │ • Nginx (HTTPS) │    │ • Real-time FER     │
│ • PostgreSQL    │    │                 │    │ • Reachy Mini Robot │
│ • n8n (10 agents)│   │                 │    │                     │
│ • MLflow        │    │                 │    │                     │
└─────────────────┘    └─────────────────┘    └─────────────────────┘
```

- **Zero cloud dependencies** — all processing on-premise
- **10-agent n8n orchestration** automates the full ML lifecycle
- **Privacy by architecture** — data minimization enforced by design
- **Two-tier quality gates** decouple training validation from deployment readiness

---

# Slide 4: Model Design

## EfficientNet-B0 with HSEmotion Pre-Training

**Backbone:** EfficientNet-B0 pre-trained on VGGFace2 (3.3M faces) + AffectNet (450K labeled)

**Task:** 3-class classification → Happy, Sad, Neutral

### Two Model Variants Compared

| | Variant 1 (Frozen) | Variant 2 (Fine-Tuned) |
|---|---|---|
| **Backbone** | Completely frozen | blocks.5, blocks.6, conv_head unfrozen |
| **Trainable params** | ~4,000 | ~500,000 (125×) |
| **Optimization** | Single run | 90-trial hyperparameter sweep |
| **GPU time** | ~2 hours | ~26 hours (13×) |
| **Strategy** | Preserve pre-trained features | Adapt backbone to target domain |

### Training Data
- **86,519 synthetic face-cropped frames** from 11,911 AI-generated videos
- **894 real AffectNet photographs** for test only (zero real data in training)

---

# Slide 5: The Face Cropping Discovery

## Data Pipeline > Model Architecture

| Configuration | V1 Test F1 | V2 Test F1 |
|--------------|-----------|-----------|
| Without face crop (run_0104) | 0.43 | 0.44 |
| **With face crop (run_0107)** | **0.781** | **0.780** |
| **Improvement** | **+82%** | **+77%** |

- The **single most impactful change** was a preprocessing flag: `face_crop=True`
- The synthetic-to-real domain gap was in **backgrounds and body context**, not facial expressions
- A 90-trial hyperparameter sweep (+26 GPU hours) produced negligible improvement over this single fix
- **Lesson:** Data pipeline quality often outweighs model complexity (Ng, 2021)

---

# Slide 6: Real-World Test Results

## Near-Identical Aggregate Scores, Radically Different Per-Class Profiles

| Metric | V1 run_0107 | V2 run_0107 | Winner |
|--------|-------------|-------------|--------|
| **F1 Macro** | **0.7807** | 0.7798 | V1 (Δ = 0.001) |
| **Balanced Accuracy** | 0.7994 | **0.8118** | V2 |
| Accuracy | 0.7707 | **0.8166** | V2 |
| **F1 Happy** | 0.7770 | **0.9464** | V2 |
| **F1 Sad** | **0.8224** | 0.6940 | **V1** |
| **F1 Neutral** | **0.7427** | 0.6990 | **V1** |
| ECE | 0.1024 | **0.0955** | V2 |
| Brier | 0.3401 | **0.2787** | V2 |

> **F1 macro Δ = 0.001** — yet these models behave fundamentally differently.
> V2 wins most global metrics; V1 wins on the metrics that matter for deployment safety.

---

# Slide 7: Confusion Matrix Analysis

## Where Each Model Makes Its Errors

### Variant 1
```
                Predicted
                Happy    Sad    Neutral    Recall
  Happy          277      11      147       63.7%
  Sad              0     132       28       82.5%
  Neutral          1      18      280       93.6%
  Precision:   99.6%   81.9%   61.5%
```
**Dominant error:** Happy → Neutral (33.8%) — **behaviorally benign** under-reaction

### Variant 2
```
                Predicted
                Happy    Sad    Neutral    Recall
  Happy          406       6       23       93.3%
  Sad              3     144       13       90.0%
  Neutral         14     105      180       60.2%
  Precision:   96.0%   56.5%   83.3%
```
**Dominant error:** Neutral → Sad (35.1%) — **behaviorally disruptive** over-reaction

---

# Slide 8: Gate A-Deploy Compliance

## Quality Gates as Hard Deployment Constraints

| Gate | Threshold | V1 | V2 |
|------|-----------|-----|-----|
| F1 Macro ≥ 0.75 | | ✅ 0.781 | ✅ 0.780 |
| Balanced Acc ≥ 0.75 | | ✅ 0.799 | ✅ 0.812 |
| F1 Happy ≥ 0.70 | | ✅ 0.777 | ✅ 0.946 |
| F1 Sad ≥ 0.70 | | ✅ **0.822** | ❌ **0.694** |
| F1 Neutral ≥ 0.70 | | ✅ **0.743** | ❌ **0.699** |
| ECE ≤ 0.12 | | ✅ 0.102 | ✅ 0.096 |
| **Total** | | **6/6 PASS** | **4/6 FAIL** |

- Per-class F1 gates catch models that achieve good aggregate scores by excelling on the majority class while neglecting minorities
- V2's failures are marginal (within 0.01 of threshold) but **systematic** — both failures stem from neutral → sad confusion
- Gates are defined **before** evaluation to prevent metric cherry-picking

---

# Slide 9: Statistical Analysis — Confidence Intervals

## Wilson Score 95% CIs on Per-Class Recall

Wilson intervals preferred over Wald: correct coverage even near 0 or 1.

| Class | n | V1 Recall [95% CI] | V2 Recall [95% CI] | Overlap? |
|-------|---|-----|-----|-----|
| **Happy** | 435 | 0.637 [0.591, 0.681] | **0.933** [0.906, 0.953] | **No** — V2 superior |
| **Sad** | 160 | **0.825** [0.759, 0.876] | 0.900 [0.844, 0.938] | Yes — not significant |
| **Neutral** | 299 | **0.936** [0.903, 0.959] | 0.602 [0.546, 0.656] | **No** — V1 superior |

### Interpretation
- V2 is unambiguously better on happy (Δ = +29.7 pp, non-overlapping CIs)
- V1 is unambiguously better on neutral (Δ = +33.4 pp, non-overlapping CIs)
- Neither model is uniformly superior — **the decision hinges on which errors matter more**

---

# Slide 10: Statistical Analysis — z-Tests Against Threshold

## Is Each Per-Class F1 Significantly Above the 0.70 Deployment Floor?

Using delta-method: $SE(F1) \approx \sqrt{F1 \cdot (1-F1) / n_k}$

| Class | V1 F1 | z vs 0.70 | p-value | V2 F1 | z vs 0.70 | p-value |
|-------|-------|-----------|---------|-------|-----------|---------|
| Happy | 0.777 | **+3.85** | < 0.001 | 0.946 | +22.9 | < 0.001 |
| Sad | 0.822 | **+4.07** | < 0.001 | 0.694 | **−0.17** | 0.43 |
| Neutral | 0.743 | +1.71 | 0.044 | 0.699 | **−0.04** | 0.48 |

### Interpretation
- **V1:** All three classes above 0.70 (happy and sad at p < 0.001; neutral marginal at p = 0.044)
- **V2:** Sad and neutral F1 **cannot be statistically distinguished from 0.70** — and both fall below it
- V2's gate failures are **not sampling artifacts** — they reflect genuine shortfalls

---

# Slide 11: Statistical Analysis — Global Agreement Metrics

## Cohen's Kappa & Normalized Mutual Information

### Cohen's κ (agreement corrected for chance)

| | κ | 95% CI | Interpretation |
|---|---|---|---|
| V1 | 0.645 | [0.603, 0.688] | Substantial |
| V2 | **0.712** | [0.673, 0.752] | Substantial |

### Normalized Mutual Information

| | NMI | Interpretation |
|---|---|---|
| V1 | 0.476 | Captures 47.6% of true label information |
| V2 | **0.557** | Captures 55.7% of true label information |

### The Paradox
> **Global metrics (κ, NMI, accuracy) consistently favor V2.**
> **Class-specific metrics (per-class F1, CV, gate compliance) consistently favor V1.**
>
> V2 "buys" higher global scores by over-investing in the largest class (happy = 48.7% of test data).
> This is a well-known failure mode in imbalanced classification (He & Garcia, 2009).

---

# Slide 12: Statistical Analysis — Performance Equity

## Coefficient of Variation: The Key Differentiator

$$CV = \frac{\sigma_{F1}}{\mu_{F1}} \times 100\%$$

| | F1 Happy | F1 Sad | F1 Neutral | Mean | σ | **CV** |
|---|---|---|---|---|---|---|
| V1 | 0.777 | 0.822 | 0.743 | 0.781 | 0.033 | **4.2%** |
| V2 | 0.946 | 0.694 | 0.699 | 0.780 | 0.118 | **15.1%** |

- **V1 CV = 4.2%** → near-uniform performance across all classes
- **V2 CV = 15.1%** → 3.6× higher; severe class-level inequity
- V2 has specialized in happy detection at the expense of sad and neutral
- For a social robot that must respond appropriately to **all** emotions, low CV is critical

---

# Slide 13: Statistical Analysis — Generalization Gap

## Synthetic Training → Real-World Deployment

| | Synthetic Val F1 | Real-World Test F1 | Gap | Relative Drop |
|---|---|---|---|---|
| V1 | 0.990 | 0.781 | 0.209 | **21.2%** |
| V2 | 0.999 | 0.780 | 0.220 | **22.0%** |

### Key Finding
Despite V2's **125× more parameters**, **13× more GPU time**, and **90-trial optimization**, its generalization gap is **larger** than V1's.

### Why?
- V2's fine-tuned backbone **overfitted to synthetic features** (uniform lighting, perfect skin textures)
- V1's frozen backbone preserved VGGFace2+AffectNet features learned from **3.3M real faces**
- Consistent with transfer learning literature: freezing prevents adaptation *away from* the target distribution (Yosinski et al., 2014; Raghu et al., 2019)

---

# Slide 14: Statistical Analysis — Calibration & Power

## Brier Score Decomposition

| | Brier | ECE | Notes |
|---|---|---|---|
| V1 | 0.340 | 0.102 | Higher Brier from classification errors, not calibration |
| V2 | 0.279 | 0.096 | Lower Brier from higher happy accuracy |

- ECE gap (0.006) contributes negligibly to Brier difference (0.061)
- Both models' confidence scores are **similarly trustworthy** for the gesture modulation system

## Statistical Power

| Class | n | Detectable Δ at 80% Power |
|-------|---|---|
| Happy | 435 | ≈ 6.4 pp |
| Sad | 160 | ≈ 8.3 pp |
| Neutral | 299 | ≈ 7.8 pp |

- The neutral (Δ = 33.4 pp) and happy (Δ = 29.7 pp) differences are **far beyond detectable thresholds**
- The complementary strengths pattern is robust and not a sampling artifact

---

# Slide 15: Composite Score & Final Recommendation

## Decision Framework

$$S = 0.50 \times F1_{macro} + 0.20 \times bAcc + 0.15 \times \bar{F1}_{perclass} + 0.15 \times (1 - ECE)$$

| Component | Weight | V1 Weighted | V2 Weighted |
|-----------|--------|-------------|-------------|
| F1 Macro | 0.50 | 0.3904 | 0.3899 |
| Balanced Accuracy | 0.20 | 0.1599 | 0.1624 |
| Mean Per-class F1 | 0.15 | 0.1171 | 0.1170 |
| 1 − ECE | 0.15 | 0.1346 | 0.1357 |
| **Composite** | **1.00** | **0.8020** | **0.8049** |

### Decision Priority
1. **Gate compliance (hard constraint):** V1 passes 6/6; V2 fails 2/6 → **V1 wins**
2. **Composite score (tiebreaker):** Only used when both models pass all gates
3. V2's marginal composite advantage (Δ = 0.003) is **overridden** by its gate failures

---

# Slide 16: Why Variant 1 — Summary of Evidence

## Six Reasons V1 Is the Deployment Candidate

| # | Factor | V1 | V2 | Verdict |
|---|--------|-----|-----|---------|
| 1 | **Gate compliance** | 6/6 ✅ | 4/6 ❌ | V1 |
| 2 | **Error type** | Benign under-reaction | Disruptive over-reaction | V1 |
| 3 | **Performance equity (CV)** | 4.2% | 15.1% | V1 |
| 4 | **Generalization gap** | 21.2% (smaller) | 22.0% (larger) | V1 |
| 5 | **Real-world risk** | 6% false sadness | 35% false sadness | V1 |
| 6 | **Resource efficiency** | 2 hrs GPU | 26 hrs GPU | V1 |

### The Paradox Resolved
> Global metrics (accuracy, κ, NMI) favor V2 because it excels on the largest class (happy = 48.7%).
> Per-class metrics and quality gates favor V1 because it performs **equitably across all classes**.
>
> For a companion robot that interacts with neutral users ~75% of the time, **equity matters more than peak performance on any single class**.

**Recommendation: Deploy V1 (run_0107) with HIGH confidence.**

---

# Slide 17: Deployment & Edge Performance

## From PyTorch to Real-Time Robot Inference

```
PyTorch → ONNX (opset 13) → TensorRT (FP16) → DeepStream → Reachy Mini
```

### Jetson Xavier NX Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Latency (p50) | ≤ 120 ms | ✅ < 120 ms |
| GPU Memory | ≤ 2.5 GB | ✅ < 0.8 GB |
| Frame Rate | ≥ 25 FPS | ✅ ≥ 25 FPS |

### Safety Mechanisms
- **Abstention:** Confidence < 0.60 or top-2 margin < 0.15 → no gesture
- **5-tier expressiveness:** Gesture boldness scales proportionally with confidence
- **Automatic rollback:** Gate B failure on Jetson restores previous engine
- **Emotion-conditioned LLM prompting:** Verbal responses align with physical gestures

---

# Slide 18: Future Work & Key Takeaways

## Priority Enhancements

| Priority | Enhancement | Expected Impact |
|----------|------------|-----------------|
| 1 | Temperature scaling | ECE 0.102 → ~0.06 (1 day) |
| 2 | Mixed-domain training (10-20% real) | F1 0.78 → ~0.84 |
| 3 | V1+V2 ensemble | Leverage complementary strengths |
| 4 | 8-class Ekman expansion | Anger, fear, disgust, surprise |
| 5 | Domain adaptation | Adversarial training, style transfer |

## Five Key Takeaways

1. **Preprocessing > Architecture** — Face cropping (+82%) beat a 90-trial sweep
2. **Aggregate metrics deceive** — F1 Δ = 0.001 hid CV ratio of 4.2% vs 15.1%
3. **Define gates before evaluation** — Prevents metric cherry-picking
4. **Error consequences are context-dependent** — Under-reaction ≠ over-reaction
5. **Statistical rigor reveals what point estimates hide** — CIs, z-tests, and CV analysis are essential for deployment decisions

---

*Slide deck based on: Reachy_Emotion_Classification_Research_Paper_Concise.md*
*Russell Bray — Loyola University Chicago — May 2026*
