# Partial Methods Integration: Visual Summary

Quick reference guide with diagrams and decision trees.

---

## METHOD 1: MSE FOR VALENCE/AROUSAL REGRESSION

### Current Pipeline
```
Video → Face Detection → RGB Crop (224×224×3)
                              ↓
                        ResNet50 Backbone
                              ↓
                    Classification Head: FC(1024 → 2)
                              ↓
                    Output: [happy_logit, sad_logit]
                              ↓
                        Softmax → [0.95, 0.05]
                              ↓
                        Emotion: happy ✓
```

### Enhanced Pipeline with Multi-Task Learning
```
Video → Face Detection → RGB Crop (224×224×3)
                              ↓
                        ResNet50 Backbone (1024-D features)
                         /            \
                        /              \
        Emotion Head (FC)          VA Head (FC)
        1024 → 2 (logits)      1024 → 64 → 2 (tanh)
              ↓                        ↓
           CrossEntropy           MSE Loss
          [0.95, 0.05]      [valence, arousal]
              ↓                    ↓
           happy              [0.80, 0.65]
                                   ↓
                       valence=0.80 (positive)
                       arousal=0.65 (moderately intense)
```

### Loss Combination
```
L_total = L_emotion + λ × L_va

Where:
- L_emotion = CrossEntropyLoss(logits, label)
- L_va = MSELoss(pred_va, true_va)
- λ = 0.3 (weight balancing both objectives)
```

### Robot Response Decision Tree
```
emotion = "happy"
valence = 0.80       arousal = 0.65
      ↓                   ↓
    Positive           Moderate Intensity
      ↓                   ↓
  Use smile          Adjust gesture size
  gestures           and speech rate
      ↓
    EXECUTE:
    - Warm smile (not manic)
    - Medium hand gestures
    - Conversational pace
    - "I can see you're happy!"
```

---

## METHOD 2: CONFIDENCE INTERVALS

### Single Metric vs CI
```
OLD REPORTING:
Training Run 5: F1 = 0.8450
               (single point, no uncertainty)

NEW REPORTING (Bootstrap):
Training Run 5: F1 = 0.8450 [95% CI: 0.8210, 0.8680]
                      ↑            ↑            ↑
                   estimate    lower bound  upper bound
                   CI width = 0.047 (narrow = stable)

NEW REPORTING (k-Fold CV):
5-Fold CV Results:
  Fold 1: F1 = 0.843
  Fold 2: F1 = 0.831
  Fold 3: F1 = 0.858
  Fold 4: F1 = 0.849
  Fold 5: F1 = 0.853
  ────────────────────
  Mean ± Std: 0.8468 ± 0.0102
  95% CI: [0.8277, 0.8659]
```

### Bootstrap Procedure (Visual)
```
Original Validation Set
┌─────────────────────────────────────┐
│ [sample_0, sample_1, ..., sample_n] │
└─────────────────────────────────────┘
            ↓ Resample N=1000 times
    ┌───────┴───────┐
    ↓               ↓
Bootstrap 1:    Bootstrap 2:
[s_5, s_2,      [s_0, s_3,     ...   Bootstrap 1000:
 s_5, s_1, ...   s_2, s_4, ...]       [s_n, s_1, ...]
    ↓               ↓                      ↓
  F1=0.840       F1=0.843            F1=0.851
    ↓               ↓                      ↓
    └───────────────┴──────────────────────┘
                    ↓
            Collect 1000 F1 scores:
            [0.840, 0.843, ..., 0.851]
                    ↓
            Compute percentiles:
            2.5th percentile = 0.8210
            50th percentile  = 0.8450 (median)
            97.5th percentile = 0.8680
                    ↓
            Report: F1 = 0.8450 [95% CI: 0.8210, 0.8680]
```

### CI Width Interpretation
```
NARROW CI (width < 0.03)          WIDE CI (width > 0.06)
┌────────────────┐                ┌──────────────────────────┐
│ 0.840 ─ 0.855  │                │ 0.75 ─────────── 0.90    │
│ F1 = 0.8475    │                │ F1 = 0.8250              │
└────────────────┘                └──────────────────────────┘
        ↓                                  ↓
    STABLE model            Model is UNSTABLE
  Consistent performance    High variance → likely needs:
                            - More training data
                            - Better data quality
                            - Hyperparameter tuning
```

### Quality Gate with CI
```
Gate A Check: Does F1 ≥ 0.84?

Case 1: F1 = 0.8450 [CI: 0.8410, 0.8490]
        Lower bound: 0.8410 ✓ passes
        Estimate:    0.8450 ✓ passes
        → PASS ✓

Case 2: F1 = 0.8450 [CI: 0.7950, 0.9050]
        Lower bound: 0.7950 ✗ fails (< 0.84)
        Estimate:    0.8450 ✓ passes
        CI width:    0.11 (very wide)
        → WARN ⚠️ (unstable, likely failure)

Case 3: F1 = 0.8200 [CI: 0.8150, 0.8250]
        Lower bound: 0.8150 ✗ fails
        Estimate:    0.8200 ✗ fails
        → FAIL ✗ (doesn't meet requirement)
```

---

## METHOD 3: PCK FOR LANDMARK-BASED INPUT

### Modality Comparison
```
┌────────────────────────────────────────────────────────────────┐
│ INPUT MODALITY COMPARISON                                      │
├─────────────────┬──────────────┬──────────────┬────────────────┤
│ Property        │ RGB Image    │ Landmarks    │ Hybrid         │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ Input Shape     │ 224×224×3    │ 68×2         │ Both           │
│                 │ 150,528 vals │ 136 vals     │                │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ Latency (ms)    │ 45           │ 8            │ 50             │
│ (Jetson Xavier) │              │              │                │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ F1 Score        │ 0.845        │ 0.810        │ 0.875          │
│ (Accuracy)      │              │ (-3%)        │ (+3%)          │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ Robustness to   │ ✓ Fair       │ ✓✓✓ Excellent│ ✓✓ Good        │
│ Lighting        │              │              │                │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ Robustness to   │ ✗ Sensitive  │ ✓✓ Good      │ ✓ Fair         │
│ Pose/Angle      │              │              │                │
├─────────────────┼──────────────┼──────────────┼────────────────┤
│ Compute Cost    │ High         │ Very Low     │ Medium         │
│ (on edge device)│              │              │                │
└─────────────────┴──────────────┴──────────────┴────────────────┘
```

### Landmark Detection Pipeline
```
Video Frame (1920×1080)
        ↓
[Face Detection]
        ↓
Cropped Face (224×224)
        ↓
[MediaPipe/dlib]
        ↓
68 Landmarks Detected
        ↓
[Normalize to [-1, 1]]
        ↓
Input: [68, 2] = 136 values
        ↓
ResNet50 Backbone (adapted for 136-D input)
        ↓
Emotion Classification
        ↓
Prediction: happy/sad
```

### PCK Metric Explanation
```
Definition: What % of landmarks are within threshold distance?

Ground Truth        Predicted           Distance
Landmarks          Landmarks
  ●eye_L             ●(close)              ✓ within threshold
  ●eye_R             ●(close)              ✓ within threshold
  ●nose              ●(far)                ✗ outside threshold
  ●mouth_L           ●(very far)           ✗ outside threshold
  ●mouth_R           ●(close)              ✓ within threshold

PCK = # correct / # total = 3/5 = 0.60 = 60%
```

### PCK Per-Region
```
┌──────────────────────────────────────────────────────┐
│ Critical Regions (must be ≥ 90% PCK):               │
│                                                      │
│ Left Eye   ████████░ 89% ⚠️ WARNING                 │
│ Right Eye  ██████████ 94% ✓                          │
│ Mouth      ███████░░ 85% ✗ FAIL                     │
│                                                      │
│ Why: Eyes convey attention, mouth conveys emotion   │
│      Poor detection → poor classification            │
└──────────────────────────────────────────────────────┘

Per-Region Breakdown (full):
  Jaw (0-16):          96% ✓
  Left Eyebrow (17-21): 92% ✓
  Right Eyebrow (22-26): 93% ✓
  Nose (27-36):        94% ✓
  Left Eye (36-42):    89% ⚠️ (borderline)
  Right Eye (42-48):   91% ✓
  Mouth (48-68):       85% ✗ (needs improvement)

Overall PCK = mean = 91.8% ✓
```

### Decision Tree: Should You Use Landmarks?
```
                    Is this for edge deployment?
                            ↓
                    ┌───────┴───────┐
                   Yes              No
                    ↓                ↓
            Is latency critical?    Use RGB
            (< 20ms needed?)            ↓
                    ↓              High accuracy
                    ┌───────┬───────┐ (F1 ~0.85)
                   Yes     No
                    ↓       ↓
            Is robustness  Use RGB
            to lighting    (simpler)
            needed?            ↓
                    ↓      Medium
            ┌───────┴───────┐ accuracy
           Yes      No       (F1 ~0.85)
            ↓        ↓
        USE       Use Hybrid
        LANDMARKS (RGB + Landmarks)
            ↓            ↓
        Landmarks    Best accuracy
        Only         (F1 ~0.87)
            ↓        BUT: 2x latency
        ✓ 8ms      of landmarks
        ✓ Robust
        ⚠️ 3% F1 drop
```

---

## Implementation Priority Matrix

### Effort vs Impact
```
HIGH IMPACT │
            │  CI ⭐⭐⭐
            │  (low effort)
            │
            │           MSE/VA ⭐⭐⭐
            │           (medium effort)
            │
            │
MEDIUM      │
IMPACT      │           PCK ⭐⭐
            │           (high effort)
            │
LOW IMPACT  │
            └─────────────────────────────────
              LOW        MEDIUM     HIGH
              EFFORT     EFFORT     EFFORT
```

### Timeline Recommendation
```
Week 1: Confidence Intervals
        Day 1-2: Implement bootstrap CI
        Day 3-4: k-fold CV integration
        Day 5: Testing & documentation

Week 2-3: MSE/Valence-Arousal
        Day 1-2: Dataset extension (VA labels)
        Day 3: Multi-task loss & training
        Day 4: Evaluation metrics
        Day 5: Gate extension & testing

Week 4-5: PCK/Landmarks (optional)
        Day 1-2: Landmark detector
        Day 2-3: Dataset loader
        Day 4: PCK metric & comparison
        Day 5: Benchmarking

TOTAL: ~6-10 days for complete implementation
```

---

## Success Criteria by Method

### MSE/Valence-Arousal Success
```
✅ Can predict valence ∈ [-1, 1] with MSE ≤ 0.06
✅ Can predict arousal ∈ [0, 1] with MSE ≤ 0.04
✅ Robot gestures adjust based on arousal level
✅ Gate A extended: valence_rmse ≤ 0.25, arousal_rmse ≤ 0.20
✅ MLflow logs 8+ new metrics per training run
```

### Confidence Intervals Success
```
✅ All metrics reported with 95% CI
✅ Bootstrap width < 0.03 for stable runs
✅ k-fold CV implemented (5 splits)
✅ Gate A considers CI lower bound
✅ Wide CI automatically triggers data quality warning
✅ Historical trend shows narrowing CIs over time
```

### PCK/Landmarks Success
```
✅ Landmark detector achieves PCK > 0.85
✅ Eye region PCK > 0.90
✅ Mouth region PCK > 0.90
✅ Landmark-based F1 ≥ 0.80 (within 3% of RGB)
✅ Latency p95 < 15ms (vs 45ms for RGB)
✅ Robust to ±30° head rotation
```

---

## Quick Decision Guide

**Choose METHOD 1 (MSE) if you want:**
- Nuanced robot interaction (scale gestures by intensity)
- Richer emotional representation
- Minor code changes (architecture ready)

**Choose METHOD 2 (CI) if you want:**
- Better stakeholder communication
- Early detection of data quality issues
- Quick observability win
- No architectural changes

**Choose METHOD 3 (PCK) if you want:**
- 5x faster edge inference
- Robustness to lighting/pose
- Can tolerate 3% F1 drop
- Resource-constrained deployment

---

**Document Version**: 1.0
**Last Updated**: 2026-01-22
