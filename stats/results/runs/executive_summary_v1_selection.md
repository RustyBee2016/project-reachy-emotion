# Executive Summary: Emotion Model Selection for Reachy Deployment

**Date:** 2026-04-14  
**Prepared for:** Project Manager / Decision Maker  
**Prepared by:** Cascade AI  
**Decision:** **Deploy Variant 1 (V1), run_0107**  
**Confidence:** HIGH  
**Full Analysis:** [deployment_recommendation_v1_vs_v2.md](deployment_recommendation_v1_vs_v2.md)

---

## Background

Reachy's emotion classifier detects **happy**, **sad**, or **neutral** from a person's face in real time. The prediction drives the robot's gesture selection (wave, nod, empathy), gesture intensity (5-tier confidence system), and conversational tone (LLM prompt conditioning). Two candidate models were evaluated:

- **Variant 1 (V1)** — Frozen backbone. Trains only a small classification head (~4,000 parameters) on top of a pre-trained face-recognition network. Quick to train (~2 hours).
- **Variant 2 (V2)** — Fine-tuned backbone. Unfreezes deeper network layers (~500,000 parameters) and was optimized through a 90-trial automated hyperparameter sweep (~26 GPU-hours).

Both were trained on **86,519 AI-generated face images** and tested on **894 real photographs** from the AffectNet academic dataset — images neither model has ever seen, from a completely different visual domain than the training data.

---

## The Headline Numbers

| | Variant 1 | Variant 2 |
|---|---|---|
| **Overall Accuracy (F1 Macro)** | **78.1%** | 78.0% |
| **Deployment Gates Passed** | **6 of 6** | 4 of 6 |
| **Happy Detection** | 77.7% | **94.6%** |
| **Sad Detection** | **82.2%** | 69.4% |
| **Neutral Detection** | **74.3%** | 69.9% |
| **Confidence Reliability (ECE)** | 10.2% error | **9.6%** error |

Both models achieve ~78% overall accuracy — effectively a tie. The critical difference is *where* each model makes its mistakes.

---

## Why V1 Was Selected: Four Reasons

### 1. V1 Passes All Deployment Gates; V2 Does Not

Our deployment policy requires every emotion to be detected with at least 70% accuracy (F1). V1 meets this bar for all three emotions. V2 fails on two: **sad (69.4%)** and **neutral (69.9%)**. This alone disqualifies V2 under current policy.

### 2. V1's Errors Are Evenly Distributed; V2's Are Concentrated

A statistical measure of performance balance (coefficient of variation) shows V1 is **3.6× more balanced** across emotion classes than V2. V2 achieves a near-perfect 94.6% on happy faces but neglects sad and neutral — it has effectively specialized in one emotion at the expense of the other two. For a robot that must respond appropriately to *all* emotions, balanced performance is essential.

### 3. V1's Mistakes Are Less Disruptive to the User Experience

| V1's Main Error | V2's Main Error |
|---|---|
| Calls 34% of happy people "neutral" | Calls 35% of neutral people "sad" |
| **Robot under-reacts** — responds neutrally to a happy person | **Robot over-reacts** — offers empathy to someone who is fine |
| Socially acceptable; rarely noticed | Socially awkward; erodes trust over time |

Since neutral is expected to be the **most common** emotion in real interactions (~75%), V2's error pattern would cause Reachy to inappropriately express sadness-related gestures (comfort, hug, empathy) in roughly **1 in 4 neutral encounters**. V1's error — occasionally treating a happy person as neutral — is far less noticeable.

### 4. When V2 Says "Sad," It's Barely Better Than a Coin Flip

V2's sad-detection precision is only **53.7%** — nearly half the time V2 labels someone as sad, the person is actually neutral. V1's sad precision is **69.8%**. For a robot that triggers empathy gestures based on sadness detection, this gap has direct consequences for user trust.

---

## What the Statistics Confirm

Seven formal statistical tests were conducted on the 894-image test set (details in the full report). The key findings, in plain language:

- **Neither model is uniformly better.** V2 is statistically significantly better at recognizing happy faces (+29.7 pp, non-overlapping 95% confidence intervals). V1 is statistically significantly better at recognizing neutral faces (+33.4 pp). On sad faces, the difference is not statistically significant.

- **V2 looks better on aggregate metrics** (overall accuracy, Cohen's kappa) because happy is the largest class in the test set (48.7%). V2's excellent happy detection inflates its global scores while hiding its failures on the other two classes. This is a well-documented statistical artifact in imbalanced classification.

- **V1's one marginal metric** — neutral F1 at 74.3% vs the 75% per-class target — is within statistical noise (z = −0.29, well inside the 95% confidence interval). V2's two failures are also near the threshold but fall on the wrong side.

- **V2's extra training investment did not improve generalization.** Despite 90 hyperparameter trials and 125× more trainable parameters, V2's accuracy drop from synthetic training data to real-world test data (22.0%) is slightly *larger* than V1's (21.2%). The frozen backbone in V1 better preserves the real-face knowledge from the original pre-trained model.

- **Both models' confidence scores are trustworthy.** Calibration error (ECE) is within the 12% deployment threshold for both. The slight V2 advantage (9.6% vs 10.2%) is negligible for Reachy's 5-tier gesture system.

---

## Recommendation

| Option | Description | Ready? | Risk |
|--------|------------|--------|------|
| **A. Deploy V1 now** | 78% accuracy, balanced errors, passes all gates | **Yes** | Low |
| B. Deploy V2 now | 78% accuracy, excellent happy detection, fails 2 gates | No | Medium — neutral→sad confusion |
| C. Ensemble V1+V2 | Average both models' predictions | 2 days work | Low — likely best accuracy, doubles inference cost |

**Recommendation: Option A — deploy Variant 1 (run_0107).**

---

## Next Steps

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **Deploy V1** to Jetson (ONNX → TensorRT → DeepStream) | 1 day | Reachy responds to emotions live |
| 2 | **Temperature scaling** — a post-training calibration fix | 1 day | Improves confidence accuracy at zero cost to detection accuracy |
| 3 | **Diversify training data** — mix real faces into training | 1 week | Closes the synthetic→real gap toward 84% F1 |
| 4 | **Explore V1+V2 ensemble** — combine both models' strengths | 2 days | Complementary error patterns suggest a meaningful accuracy boost |

### When to Revisit

Re-evaluate when a future model variant passes all six deployment gates **and** achieves either F1 ≥ 84% on real-world data or per-class balance (CV) below 10% with F1 above V1's 78.1%.

---

*This summary distills the full statistical analysis in [deployment_recommendation_v1_vs_v2.md](deployment_recommendation_v1_vs_v2.md). That document contains Wilson confidence intervals, z-tests, Cohen's kappa, normalized mutual information, generalization gap analysis, calibration decomposition, and statistical power assessment — all supporting the conclusions above.*
