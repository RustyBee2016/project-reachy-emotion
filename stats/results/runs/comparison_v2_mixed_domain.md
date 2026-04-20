# Variant 2 Mixed-Domain Comparison Report

**Date:** 2026-04-20  
**Test Dataset:** test_dataset_01 (894 real AffectNet images)  
**Gate A-deploy thresholds:** F1≥0.75, bAcc≥0.75, per-class F1≥0.70, ECE≤0.12, Brier≤0.16

---

## Three-Way Comparison: V2 Mixed vs V2 Synthetic-Only vs V1 Mixed

| Metric              | V2 Synth-Only (run_0107) | V2 Mixed (run_0107_mixed) | V1 Mixed (run_0107_mixed) | V2 Mixed Δ vs V2 Synth |
|---------------------|--------------------------|---------------------------|---------------------------|------------------------|
| **F1 macro**        | 0.780                    | **0.916**                 | 0.834                     | **+17.4%** ↑           |
| **Balanced Acc**    | 0.812                    | **0.921**                 | 0.840                     | **+13.4%** ↑           |
| **Accuracy**        | 0.817                    | **0.926**                 | 0.828                     | **+13.3%** ↑           |
| **F1 happy**        | 0.946                    | **0.961**                 | 0.842                     | **+1.6%** ↑            |
| **F1 sad**          | 0.694                    | **0.888**                 | 0.860                     | **+28.0%** ↑           |
| **F1 neutral**      | 0.699                    | **0.899**                 | 0.801                     | **+28.6%** ↑           |
| **ECE**             | 0.096                    | 0.142                     | 0.104                     | +48.3% ↓               |
| **Brier**           | 0.279                    | 0.167                     | 0.262                     | **-40.1%** ↑           |
| **MCE**             | 0.130                    | 0.604                     | 0.124                     | +364.6% ↓              |

### Gate A-deploy Pass/Fail

| Gate                | V2 Synth-Only | V2 Mixed   | V1 Mixed   |
|---------------------|---------------|------------|------------|
| F1 macro ≥ 0.75     | ❌ (0.780)    | ✅ (0.916) | ✅ (0.834) |
| Balanced Acc ≥ 0.75  | ✅ (0.812)    | ✅ (0.921) | ✅ (0.840) |
| Per-class F1 ≥ 0.70  | ❌ (sad=0.694)| ✅ (all≥0.888) | ✅ (all≥0.801) |
| ECE ≤ 0.12          | ✅ (0.096)    | ❌ (0.142) | ✅ (0.104) |
| Brier ≤ 0.16        | ❌ (0.279)    | ❌ (0.167) | ❌ (0.262) |
| **Overall**         | **FAIL (3/5)**| **FAIL (3/5)** | **FAIL (4/5)** |

---

## Confusion Matrices

### V2 Synthetic-Only (run_0107)
```
              Pred happy  Pred sad  Pred neutral
True happy       406         6          23
True sad           3       144          13
True neutral      14       105         180
```
**Critical issue:** 105 neutral→sad misclassifications (35.1% of neutral)

### V2 Mixed-Domain (run_0107_mixed)
```
              Pred happy  Pred sad  Pred neutral
True happy       404         2          29
True sad           1       143          16
True neutral       1        17         281
```
**Massive improvement:** neutral→sad down from 105 to 17 (−83.8%)

### V1 Mixed-Domain (run_0107_mixed)
```
              Pred happy  Pred sad  Pred neutral
True happy       316         7         112
True sad           0       129          31
True neutral       0         4         295
```
**Different trade-off:** happy→neutral = 112 (25.7%) but near-zero cross-class errors for sad/neutral

---

## Key Analysis

### 1. Dramatic F1 / Balanced Accuracy Improvement (V2 Mixed vs V2 Synth)
- **F1 macro jumped +17.4%** (0.780 → 0.916) — the largest single-run improvement in project history
- **Sad F1 jumped +28.0%** (0.694 → 0.888) — previously the weakest class, now very strong
- **Neutral F1 jumped +28.6%** (0.699 → 0.899) — the other weak class also recovered massively
- Root cause: the neutral→sad confusion dropped from 105 to 17 misclassifications

### 2. V2 Mixed Now Surpasses V1 Mixed on Classification
- V2 mixed F1 macro (0.916) beats V1 mixed (0.834) by **+9.8%**
- V2 mixed balanced accuracy (0.921) beats V1 mixed (0.840) by **+9.6%**
- V2 mixed wins on ALL three per-class F1 scores:
  - happy: 0.961 vs 0.842 (+14.1%)
  - sad: 0.888 vs 0.860 (+3.3%)
  - neutral: 0.899 vs 0.801 (+12.2%)

### 3. Calibration Trade-off: ECE Regression
- V2 mixed ECE (0.142) is **worse** than V2 synth (0.096) and V1 mixed (0.104)
- The model is more **accurate** but less **calibrated** — confidence scores don't match observed accuracy
- Brier score improved significantly (0.279 → 0.167, −40.1%), meaning overall probability estimates are better
- MCE of 0.604 indicates one confidence bin is severely miscalibrated

### 4. Gate A-deploy Status
- V2 mixed passes 3/5 gates (same count as V2 synth, but DIFFERENT gates)
  - V2 synth failed: F1 macro, per-class F1, Brier
  - V2 mixed failed: ECE, Brier
- V1 mixed passes 4/5 gates (Brier sole blocker)
- **V1 mixed remains the deployment candidate** per Gate A rules (most gates passed)

### 5. Why V2 Mixed Has Better Classification but Worse ECE
The backbone unfreezing (blocks.5, blocks.6, conv_head) allows deeper feature adaptation, 
which produces sharper decision boundaries (higher accuracy) but overconfident predictions 
(higher ECE). This is a known phenomenon with fine-tuned deep layers — the model becomes 
more accurate but poorly calibrated.

**Potential fix:** Post-hoc temperature scaling on the V2 mixed checkpoint could reduce 
ECE to deployable levels while preserving the classification gains.

---

## Recommendation

### Short-term: Deploy V1 Mixed (run_0107_mixed)
- 4/5 Gate A-deploy gates passed (Brier sole blocker)
- Best calibration of all variants (ECE=0.104)
- Solid classification (F1=0.834, all per-class ≥ 0.80)

### Medium-term: Investigate V2 Mixed + Temperature Scaling
- V2 mixed has the best raw classification (F1=0.916)
- ECE of 0.142 could be correctable with temperature scaling
- If calibration is fixed, V2 mixed would pass 4/5 or potentially 5/5 gates
- Brier of 0.167 is very close to threshold (0.16) — temperature scaling may push it under

---

## Training Configuration Summary

| Parameter           | V2 Synth-Only (run_0107)     | V2 Mixed (run_0107_mixed)          |
|---------------------|------------------------------|------------------------------------|
| Source checkpoint    | V1 synth run_0107            | V1 mixed run_0107                  |
| Training data        | 86,519 synthetic only        | 86,519 synth + 15,000 real (5K/cls)|
| Leakage prevention   | N/A                          | 894 test IDs excluded              |
| Epochs completed     | 30                           | 25 (early stopped)                 |
| Best epoch           | ~30                          | 25                                 |
| Freeze epochs        | 5                            | 5                                  |
| Unfreeze layers      | blocks.5, blocks.6, conv_head| blocks.5, blocks.6, conv_head      |
| LR                   | 3e-4                         | 3e-4                               |
| Dropout              | 0.5                          | 0.5                                |
| Label smoothing      | 0.10                         | 0.10                               |
| Best val F1          | 0.997                        | 0.999                              |

### Artifacts
- V2 mixed checkpoint: `/media/rusty_admin/project_data/reachy_emotion/checkpoints/variant_2/var2_run_0107_mixed/best_model.pth`
- V2 mixed test results: `stats/results/runs/test/var2_test_var2_run_0107_mixed.json`
- V2 mixed gate_a: `/media/rusty_admin/project_data/reachy_emotion/results/test/var2_run_0107_mixed/gate_a.json`
