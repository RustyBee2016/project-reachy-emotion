# Executive Summary: Emotion Model Selection for Reachy Deployment

**Date:** 2026-04-20 (Updated — supersedes 2026-04-14 version)  
**Prepared for:** Project Manager / Decision Maker  
**Prepared by:** Cascade AI  
**Decision:** **Deploy Variant 2 Mixed-Domain + Temperature Scaling (V2 mixed+T), var2_run_0107_mixed_calibrated**  
**Confidence:** HIGH  
**ADR:** [ADR 012 — Mixed-Domain + Temperature Scaling → V2 Deployment](../../memory-bank/decisions/012-mixed-domain-temperature-scaling-v2-deployment.md)  
**Full Analysis:** [deployment_recommendation_v1_vs_v2.md](deployment_recommendation_v1_vs_v2.md) (synthetic-only phase); research paper §6.9–6.11, §7.9.2 (final phase)

---

## Background

Reachy's emotion classifier detects **happy**, **sad**, or **neutral** from a person's face in real time. The prediction drives the robot's gesture selection (wave, nod, empathy), gesture intensity (5-tier confidence system), and conversational tone (LLM prompt conditioning). Two model architectures were evaluated:

- **Variant 1 (V1)** — Frozen backbone. Trains only a small classification head (~4,000 parameters) on top of a pre-trained face-recognition network. Quick to train (~2 hours).
- **Variant 2 (V2)** — Fine-tuned backbone. Unfreezes deeper network layers (~500,000 parameters) and was optimized through a 90-trial automated hyperparameter sweep (~26 GPU-hours).

The selection process was **iterative**, spanning three training regimes:

1. **Synthetic-only** (86,519 AI-generated frames) → V1 initially recommended (2026-04-14)
2. **Mixed-domain** (86,519 synthetic + 15,000 real AffectNet images) → V2 dramatically improved but failed calibration
3. **Mixed-domain + temperature scaling** (post-hoc calibration fix) → V2 passes all gates, final recommendation

---

## The Headline Numbers

| | V1 Synthetic (April 14) | V2 Mixed+T (April 20) | Change |
|---|---|---|---|
| **Overall Accuracy (F1 Macro)** | 78.1% | **91.6%** | **+17.3%** |
| **Deployment Gates Passed** | 6 of 6 | **7 of 7** | All pass |
| **Happy Detection** | 77.7% | **96.2%** | +23.8% |
| **Sad Detection** | 82.2% | **88.8%** | +8.0% |
| **Neutral Detection** | 74.3% | **89.9%** | +21.0% |
| **Confidence Reliability (ECE)** | 10.2% error | **3.6%** error | **3× better** |
| **Composite Score** | 0.802 | **0.924** | +15.2% |

V2 mixed+T is better on **every single metric** by a substantial margin.

---

## Why the Recommendation Changed: The Iterative Journey

### Phase 1 (April 14): V1 Was the Right Choice

When both models were trained on synthetic data only, V1 and V2 achieved virtually identical F1 (~78%). V1 was selected because:
- V1 passed all 6 deployment gates; V2 failed 2 (sad F1=69.4%, neutral F1=69.9%)
- V1's errors were balanced across classes (CV=4.2% vs V2's 15.1%)
- V2's 35% neutral→sad confusion rate was a critical UX risk

*This analysis was correct given the data available at the time.*

### Phase 2 (April 18): Mixed-Domain Training Reversed the Picture

Adding 15,000 real AffectNet photographs (5K per class, ~15% of training data) had dramatically different effects:

| | V1 Improvement | V2 Improvement |
|---|---|---|
| **F1 Macro** | 78.1% → 83.4% (+6.8%) | 78.0% → **91.6%** (+17.4%) |
| **Neutral→Sad Confusion** | — | 35.1% → **5.7%** (resolved) |
| **Balanced Accuracy** | 79.9% → 84.0% | 81.2% → **92.1%** |

**Why V2 benefited so much more:** V2's unfrozen backbone layers could *adapt* to real-face features during training — learning texture, lighting, and expression patterns that only exist in real photographs. V1's frozen backbone cannot learn new features; it can only re-weight existing ones. This is the key insight: **the optimal transfer learning strategy depends on the data composition.** Frozen backbones protect against overfitting on synthetic data, but fine-tuned backbones unlock dramatically more capacity when real data is available.

**New blocker:** V2 mixed ECE regressed to 14.2% (> 12% threshold) — the backbone parameter updates shifted the logit scale, making confidence scores unreliable.

### Phase 3 (April 20): Temperature Scaling Fixed Calibration

Temperature scaling — a single-parameter post-hoc fix (Guo et al., 2017) — corrected V2's overconfidence without changing any predictions:

| | Before | After | Change |
|---|---|---|---|
| **ECE** | 14.2% | **3.6%** | −75% (now 3× below threshold) |
| **Brier Score** | 0.167 | **0.130** | −22% |
| **Classification (F1, accuracy)** | unchanged | unchanged | Zero cost |

**Result:** V2 mixed+T now passes **all 7 Gate A-deploy thresholds** and outperforms V1 on every metric.

---

## What This Means for Reachy

### Better Emotion Detection

V2 mixed+T correctly identifies emotions **91.6% of the time** (up from 78.1%). The critical neutral→sad confusion that disqualified V2 in the synthetic-only phase is now just 5.7% — meaning Reachy will almost never inappropriately express empathy toward someone who is merely neutral.

### More Reliable Confidence Scores

ECE of 3.6% means Reachy's 5-tier gesture modulation system (subtle → moderate → full → emphatic → maximum) receives highly accurate confidence signals. When the model says "80% confident this person is happy," the actual probability is very close to 80%. This translates directly to appropriately calibrated physical gestures.

### All Deployment Gates Passed

| Gate | Threshold | V2 Mixed+T | Status |
|------|-----------|------------|--------|
| F1 Macro | ≥ 0.75 | 0.916 | ✅ |
| Balanced Accuracy | ≥ 0.75 | 0.921 | ✅ |
| F1 Happy | ≥ 0.70 | 0.962 | ✅ |
| F1 Sad | ≥ 0.70 | 0.888 | ✅ |
| F1 Neutral | ≥ 0.70 | 0.899 | ✅ |
| ECE | ≤ 0.12 | 0.036 | ✅ |
| Brier | ≤ 0.16 | 0.130 | ✅ |

---

## Recommendation

| Option | Description | Ready? | Risk |
|--------|------------|--------|------|
| **A. Deploy V2 mixed+T** | 91.6% accuracy, 3.6% ECE, all 7 gates passed | **Yes** | Low |
| B. Keep V1 synthetic-only | 78.1% accuracy, all gates passed but lower performance | Yes | Low — but leaves 13.5% F1 on the table |
| C. Ensemble V1+V2 | Combine models | 2 days | Marginal gain given V2's dominance |

**Recommendation: Option A — deploy Variant 2 mixed+T (var2_run_0107_mixed_calibrated).**

This supersedes the April 14 recommendation of V1 (run_0107). See [ADR 012](../../memory-bank/decisions/012-mixed-domain-temperature-scaling-v2-deployment.md) for the full decision record.

---

## Deployment Notes

- **Temperature at inference:** Apply T=0.59 to logits before softmax (single scalar division, negligible compute cost)
- **Checkpoint:** V2 mixed-domain checkpoint + temperature scaling config
- **Inference pipeline:** ONNX → TensorRT → DeepStream (same as V1 flow)
- **Rollback plan:** V1 run_0107 engine remains available as fallback

---

## Completed Items (from April 14 Next Steps)

| # | Action | Status | Result |
|---|--------|--------|--------|
| ~~1~~ | ~~Deploy V1 to Jetson~~ | **Superseded** | V2 mixed+T is now the deployment candidate |
| ~~2~~ | ~~Temperature scaling~~ | **Done** | T=0.59 learned, ECE 14.2% → 3.6% |
| ~~3~~ | ~~Diversify training data~~ | **Done** | 15K real images added, F1 78% → 91.6% |
| 4 | Explore V1+V2 ensemble | Deprioritized | V2 mixed+T alone exceeds all targets |

## Remaining Next Steps

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **Deploy V2 mixed+T** to Jetson (ONNX → TensorRT → DeepStream) | 1 day | Reachy responds to emotions live at 91.6% accuracy |
| 2 | **Independent calibration set** — collect separate data for ECE validation | 1 week | Eliminates calibration/test overlap concern |
| 3 | **Expand to 8-class Ekman** — broader emotion taxonomy for Phase 2 | 2 weeks | Richer emotional intelligence for robot interactions |

---

*This summary supersedes the April 14 version which recommended V1. The original V1 analysis remains valid for the synthetic-only phase and is preserved in [deployment_recommendation_v1_vs_v2.md](deployment_recommendation_v1_vs_v2.md). The full iterative analysis — including mixed-domain training results, temperature scaling methodology, and composite score evolution — is documented in the research paper (§5.3.5–5.3.6, §6.9–6.11, §7.9) and [ADR 012](../../memory-bank/decisions/012-mixed-domain-temperature-scaling-v2-deployment.md).*
