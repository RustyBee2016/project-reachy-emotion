# Week 6: Statistical Tests (Stuart-Maxwell & Paired t-Tests)

**Phase 1 Tutorial Series**  
**Duration**: ~6 hours  
**Prerequisites**: Week 5 complete

---

## Overview

This week covers:
- **Stats Module 2**: Stuart-Maxwell Test (3 hours)
- **Stats Module 3**: Per-class Paired t-Tests (3 hours)

### Weekly Goals
- [ ] Understand when to use Stuart-Maxwell test
- [ ] Run and interpret Stuart-Maxwell results
- [ ] Apply Benjamini-Hochberg correction
- [ ] Identify which emotion classes changed significantly

---

## Day 1-2: Stuart-Maxwell Test

### Study Materials

Read the complete tutorial:
```
stats/curriculum/TUTORIAL_02_STUART_MAXWELL.md
```

Script to study:
```
stats/scripts/02_stuart_maxwell_test.py
```

### Why Stuart-Maxwell?

**Question**: Did fine-tuning change the model's prediction patterns?

**Problem**: Comparing F1 scores alone doesn't tell the whole story. Two models could have identical F1 but make completely different predictions on individual samples.

**Solution**: Stuart-Maxwell test checks if the *pattern* of predictions changed, not just aggregate metrics.

### When to Use Stuart-Maxwell

| Scenario | Use Stuart-Maxwell? |
|----------|---------------------|
| Comparing base vs. fine-tuned model | ✅ Yes |
| Comparing two different architectures | ❌ No (use McNemar) |
| Evaluating a single model | ❌ No (use quality gates) |
| Paired predictions on same samples | ✅ Yes |

### The Contingency Table

Stuart-Maxwell uses a **contingency table** showing how predictions changed:

```
                    Fine-tuned Prediction
                 happy  sad  angry  neutral  ...
Base      happy   [40]    3     2      5     ...
Pred      sad       4   [35]    6      3     ...
          angry     2     5   [38]     4     ...
          neutral   3     4     3    [42]    ...
          ...

Diagonal = Both models agree
Off-diagonal = Models disagree
```

### Interpreting Results

**Null hypothesis**: Marginal distributions are the same (no systematic change)

**If p < 0.05**: Fine-tuning significantly changed prediction patterns
**If p ≥ 0.05**: No significant change detected

### Running the Script

```bash
# Demo mode
python stats/scripts/02_stuart_maxwell_test.py --demo

# With real data
python stats/scripts/02_stuart_maxwell_test.py --predictions results/paired_predictions.npz
```

### Demo Output

```
================================================================================
STUART-MAXWELL TEST RESULTS
================================================================================

Samples: 1000
Classes: 8

--- Contingency Table ---
[Matrix visualization]

--- Test Results ---
Chi-squared statistic: 23.45
Degrees of freedom: 7
P-value: 0.0014

--- Interpretation ---
✅ SIGNIFICANT (p < 0.05)
Fine-tuning significantly changed prediction patterns.

--- Marginal Differences ---
happy:    +3.2% (base: 12.5%, fine-tuned: 15.7%)
sad:      -1.8% (base: 11.2%, fine-tuned: 9.4%)
angry:    +0.5% (base: 13.1%, fine-tuned: 13.6%)
...

Agreement rate: 78.3%
```

### Exercises

1. **Run demo mode**:
   ```bash
   python stats/scripts/02_stuart_maxwell_test.py --demo
   ```

2. **Create paired predictions**:
   ```python
   import numpy as np
   
   n_samples = 500
   n_classes = 8
   
   # Base model predictions
   y_base = np.random.randint(0, n_classes, n_samples)
   
   # Fine-tuned model (slightly different)
   y_finetuned = y_base.copy()
   # Change 20% of predictions
   mask = np.random.random(n_samples) < 0.2
   y_finetuned[mask] = np.random.randint(0, n_classes, mask.sum())
   
   np.savez('stats/data/paired_predictions.npz',
            y_base=y_base, y_finetuned=y_finetuned)
   ```

3. **Run with paired data**:
   ```bash
   python stats/scripts/02_stuart_maxwell_test.py --predictions stats/data/paired_predictions.npz
   ```

### Checkpoint: Days 1-2
- [ ] Understand when to use Stuart-Maxwell
- [ ] Can build a contingency table
- [ ] Can interpret significant vs. non-significant results
- [ ] Ran script successfully

---

## Day 3-4: Per-class Paired t-Tests

### Study Materials

Read the complete tutorial:
```
stats/curriculum/TUTORIAL_03_PAIRED_TTESTS.md
```

Script to study:
```
stats/scripts/03_perclass_paired_ttests.py
```

### Why Per-class Tests?

**Question**: Which specific emotion classes improved or degraded?

Stuart-Maxwell tells us *if* something changed, but not *what* changed. Per-class t-tests identify the specific classes that improved or degraded.

### Paired vs. Unpaired Tests

| Test Type | When to Use | Example |
|-----------|-------------|---------|
| **Paired** | Same samples, different models | Base vs. fine-tuned on same videos |
| **Unpaired** | Different samples | Model A on dataset 1 vs. Model B on dataset 2 |

We use **paired** because we compare the same videos across models.

### The Multiple Comparison Problem

**Problem**: Running 8 tests (one per class) at α=0.05 gives:
```
P(at least one false positive) = 1 - (0.95)^8 = 34%
```

**Solution**: Benjamini-Hochberg (BH) correction controls the False Discovery Rate (FDR).

### Benjamini-Hochberg Procedure

1. Sort p-values from smallest to largest
2. For each p-value at rank i, compute threshold: `(i/m) × α`
3. Find largest p-value ≤ its threshold
4. All p-values up to that one are significant

**Example**:
```
Rank  Class      Raw p    Threshold (i/8 × 0.05)  Significant?
1     neutral    0.001    0.00625                 ✅ Yes
2     fear       0.008    0.01250                 ✅ Yes
3     anger      0.023    0.01875                 ❌ No (0.023 > 0.01875)
4     happy      0.045    0.02500                 ❌ No
...
```

### Running the Script

```bash
# Demo mode
python stats/scripts/03_perclass_paired_ttests.py --demo

# With real data
python stats/scripts/03_perclass_paired_ttests.py --metrics results/fold_metrics.json
```

### Demo Output

```
================================================================================
PER-CLASS PAIRED T-TESTS WITH BENJAMINI-HOCHBERG CORRECTION
================================================================================

Alpha: 0.05
Number of classes: 8
Number of folds: 5

--- Results by Class ---

Class: anger
  Base F1:      0.823 ± 0.032
  Fine-tuned:   0.845 ± 0.028
  Difference:   +0.022
  t-statistic:  2.34
  p-value (raw): 0.078
  p-value (adj): 0.156
  Significant:  ❌ No

Class: neutral
  Base F1:      0.756 ± 0.041
  Fine-tuned:   0.812 ± 0.035
  Difference:   +0.056
  t-statistic:  4.12
  p-value (raw): 0.003
  p-value (adj): 0.024
  Significant:  ✅ Yes (IMPROVED)

...

--- Summary ---
Significant improvements: 2 (neutral, fear)
Significant degradations: 0
No significant change: 6
```

### Input Format

The script expects fold-level metrics:

```json
{
  "folds": [
    {
      "fold_id": 0,
      "base_metrics": {
        "anger": {"f1": 0.82},
        "neutral": {"f1": 0.75},
        ...
      },
      "finetuned_metrics": {
        "anger": {"f1": 0.84},
        "neutral": {"f1": 0.81},
        ...
      }
    },
    ...
  ]
}
```

### Exercises

1. **Run demo mode**:
   ```bash
   python stats/scripts/03_perclass_paired_ttests.py --demo
   ```

2. **Create fold metrics**:
   ```python
   import json
   import numpy as np
   
   classes = ['anger', 'contempt', 'disgust', 'fear', 
              'happiness', 'neutral', 'sadness', 'surprise']
   
   folds = []
   for fold_id in range(5):
       base_metrics = {}
       finetuned_metrics = {}
       
       for cls in classes:
           # Base model F1 (around 0.80)
           base_f1 = 0.80 + np.random.normal(0, 0.03)
           
           # Fine-tuned (slightly better for some classes)
           improvement = np.random.normal(0.02, 0.02)
           finetuned_f1 = base_f1 + improvement
           
           base_metrics[cls] = {"f1": float(np.clip(base_f1, 0, 1))}
           finetuned_metrics[cls] = {"f1": float(np.clip(finetuned_f1, 0, 1))}
       
       folds.append({
           "fold_id": fold_id,
           "base_metrics": base_metrics,
           "finetuned_metrics": finetuned_metrics
       })
   
   with open('stats/data/fold_metrics.json', 'w') as f:
       json.dump({"folds": folds}, f, indent=2)
   
   print("Saved fold metrics")
   ```

3. **Run with fold data**:
   ```bash
   python stats/scripts/03_perclass_paired_ttests.py --metrics stats/data/fold_metrics.json
   ```

4. **Interpret results**:
   - Which classes improved significantly?
   - Which degraded?
   - What's the adjusted p-value for neutral?

### Checkpoint: Days 3-4
- [ ] Understand paired vs. unpaired tests
- [ ] Know why BH correction is needed
- [ ] Can interpret adjusted p-values
- [ ] Ran script successfully

---

## Day 5: Integration & Review

### Connecting the Three Scripts

The analysis workflow:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STATISTICAL ANALYSIS WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: Quality Gates (Script 01)                                  │
│  ─────────────────────────────────                                  │
│  Question: Does the model meet minimum standards?                   │
│  Input: Single model predictions                                    │
│  Output: Pass/fail for Macro F1, Balanced Acc, ECE, Brier          │
│                                                                      │
│          │                                                           │
│          ▼                                                           │
│                                                                      │
│  Step 2: Stuart-Maxwell (Script 02)                                 │
│  ──────────────────────────────────                                 │
│  Question: Did fine-tuning change prediction patterns?              │
│  Input: Paired predictions (base vs. fine-tuned)                    │
│  Output: Significant or not significant                             │
│                                                                      │
│          │                                                           │
│          ▼ (if significant)                                         │
│                                                                      │
│  Step 3: Per-class t-Tests (Script 03)                              │
│  ─────────────────────────────────────                              │
│  Question: Which classes improved or degraded?                      │
│  Input: Fold-level metrics for each class                           │
│  Output: List of significantly changed classes                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision Tree

```
                    ┌─────────────────────────────┐
                    │  Run Quality Gates (01)     │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │  Pass All Gates?            │
                    └─────────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │ NO                │                   │ YES
              ▼                   │                   ▼
    ┌─────────────────┐           │         ┌─────────────────┐
    │ Improve Model   │           │         │ Run Stuart-     │
    │ Before Proceed  │           │         │ Maxwell (02)    │
    └─────────────────┘           │         └────────┬────────┘
                                  │                  │
                                  │    ┌─────────────┼─────────────┐
                                  │    │ NOT SIG     │             │ SIGNIFICANT
                                  │    ▼             │             ▼
                                  │  ┌───────────┐   │   ┌───────────────────┐
                                  │  │ No Effect │   │   │ Run Per-class     │
                                  │  │ Detected  │   │   │ t-Tests (03)      │
                                  │  └───────────┘   │   └─────────┬─────────┘
                                  │                  │             │
                                  │                  │             ▼
                                  │                  │   ┌───────────────────┐
                                  │                  │   │ Identify Changed  │
                                  │                  │   │ Classes           │
                                  │                  │   └───────────────────┘
                                  └──────────────────┘
```

### Comprehensive Exercise

Run the complete analysis pipeline:

```bash
# Step 1: Quality Gates
python stats/scripts/01_quality_gate_metrics.py --demo

# Step 2: Stuart-Maxwell (if Step 1 passes)
python stats/scripts/02_stuart_maxwell_test.py --demo

# Step 3: Per-class t-Tests (if Step 2 is significant)
python stats/scripts/03_perclass_paired_ttests.py --demo
```

### Knowledge Check

1. What does Stuart-Maxwell test that quality gates don't?
2. Why do we need Benjamini-Hochberg correction?
3. If Stuart-Maxwell is significant but no individual classes are, what does that mean?
4. What's the difference between raw and adjusted p-values?
5. When would you use unpaired instead of paired t-tests?

### Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Stuart-Maxwell purpose | __ |
| Contingency table | __ |
| Paired t-tests | __ |
| Multiple comparison problem | __ |
| Benjamini-Hochberg | __ |
| Interpreting adjusted p-values | __ |

---

## Week 6 Deliverables

| Deliverable | Status |
|-------------|--------|
| Tutorial 02 read | [ ] |
| Tutorial 03 read | [ ] |
| Script 02 run | [ ] |
| Script 03 run | [ ] |
| Complete pipeline run | [ ] |
| Knowledge check passed | [ ] |

---

## Next Week

[Week 7: Calibration & Orchestration](WEEK_07_CALIBRATION_ORCHESTRATION.md) covers:
- ECE and Brier score implementation
- Bootstrap confidence intervals
- Full analysis orchestrator script
- MLflow integration for stats logging
