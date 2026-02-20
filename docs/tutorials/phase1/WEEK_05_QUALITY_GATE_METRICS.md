# Week 5: Quality Gate Metrics

**Phase 1 Tutorial Series**  
**Duration**: ~4 hours  
**Prerequisites**: Weeks 1-4 complete (database track)

---

## Overview

This week begins the **Statistical Analysis Track**, covering:
- **Stats Module 1**: Univariate Quality Gate Metrics

### Weekly Goals
- [ ] Understand Macro F1, Balanced Accuracy, F1 Neutral
- [ ] Run the quality gate metrics script
- [ ] Interpret confusion matrices
- [ ] Understand Gate A requirements

---

## Study Materials

### Primary Resource

Read the complete tutorial:
```
stats/curriculum/TUTORIAL_01_UNIVARIATE_METRICS.md
```

This tutorial has three explanation levels:
- **Tier 1**: Middle school (intuition)
- **Tier 2**: College freshman (formulas)
- **Tier 3**: Graduate (full derivations)

### Script to Study

```
stats/scripts/01_quality_gate_metrics.py
```

---

## Day 1: Understanding the Metrics

### Why These Metrics?

**Problem**: Simple accuracy is misleading with imbalanced classes.

Example: If 80% of videos are "happy", a model that always predicts "happy" gets 80% accuracy but is useless!

**Solution**: Use metrics that account for class imbalance:

| Metric | What It Measures | Why It Matters |
|--------|------------------|----------------|
| **Macro F1** | Average F1 across all classes | Treats all emotions equally |
| **Balanced Accuracy** | Average recall per class | Penalizes ignoring rare classes |
| **F1 Neutral** | F1 for neutral class specifically | Critical for Phase 2 baseline |

### Macro F1 Explained

**F1 for one class**:
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)

Where:
- Precision = TP / (TP + FP)  "Of predictions, how many correct?"
- Recall = TP / (TP + FN)     "Of actual, how many found?"
```

**Macro F1** = Average of F1 scores for all classes:
```
# For Phase 1 (3-class: happy, sad, neutral):
Macro F1 = (F1_happy + F1_sad + F1_neutral) / 3

# For full 8-class expansion:
Macro F1 = (F1_happy + F1_sad + F1_angry + ... + F1_surprise) / 8
```

### Balanced Accuracy Explained

```
Balanced Accuracy = Average of per-class recall

# For Phase 1 (3-class):
= (Recall_happy + Recall_sad + Recall_neutral) / 3

# For full 8-class:
= (Recall_happy + Recall_sad + ... + Recall_surprise) / 8
```

This ensures the model can't "cheat" by ignoring rare classes.

### Confusion Matrix

A confusion matrix shows predictions vs. actual labels:

```
                    Predicted
                 happy  sad  angry  ...
Actual  happy    [45]    3     2    ...   ← Row sums = actual counts
        sad        5   [38]    4    ...
        angry      2     3   [42]   ...
        ...
        
        ↑ Column sums = prediction counts
        [Diagonal] = correct predictions
```

**Reading the matrix**:
- **Diagonal**: Correct predictions (higher is better)
- **Off-diagonal**: Mistakes (lower is better)
- **Row**: Where actual class X was predicted
- **Column**: What was predicted as class X

### Checkpoint: Day 1
- [ ] Understand why accuracy alone is insufficient
- [ ] Know what Macro F1 measures
- [ ] Know what Balanced Accuracy measures
- [ ] Can read a confusion matrix

---

## Day 2: Gate A Requirements

### What is Gate A?

**Gate A** is the offline validation gate that models must pass before deployment consideration.

From `memory-bank/requirements.md`:

| Metric | Threshold | Script |
|--------|-----------|--------|
| Macro F1 | ≥ 0.84 | `01_quality_gate_metrics.py` |
| Balanced Accuracy | ≥ 0.85 | `01_quality_gate_metrics.py` |
| Per-class F1 | ≥ 0.75 (floor: 0.70) | `03_perclass_paired_ttests.py` |
| ECE | ≤ 0.08 | `01_quality_gate_metrics.py` |
| Brier Score | ≤ 0.16 | `01_quality_gate_metrics.py` |

### Understanding the Thresholds

**Why 0.84 for Macro F1?**
- Industry standard for emotion recognition is 0.70-0.85
- 0.84 ensures competitive performance
- Allows room for real-world degradation

**Why 0.85 for Balanced Accuracy?**
- Slightly higher than F1 to ensure no class is ignored
- Protects against class imbalance gaming

**Why track F1 Neutral specifically?**
- Neutral is the hardest class to classify
- Often confused with other emotions
- Critical baseline for Phase 2 improvements

### Calibration Metrics (ECE & Brier)

**ECE (Expected Calibration Error)**:
- Measures if confidence scores match actual accuracy
- Model says 80% confident → should be right 80% of the time
- Lower is better (≤ 0.08)

**Brier Score**:
- Mean squared error of probability predictions
- Lower is better (≤ 0.16)

### Checkpoint: Day 2
- [ ] Know all Gate A thresholds
- [ ] Understand why each metric matters
- [ ] Know what ECE and Brier measure

---

## Day 3: Running the Script

### Script Overview

```bash
# View script help
python stats/scripts/01_quality_gate_metrics.py --help

# Run in demo mode (synthetic data)
python stats/scripts/01_quality_gate_metrics.py --demo

# Run with real predictions
python stats/scripts/01_quality_gate_metrics.py --predictions results/predictions.npz
```

### Demo Mode Output

```bash
cd d:\projects\reachy_emotion
python stats/scripts/01_quality_gate_metrics.py --demo
```

Expected output:
```
================================================================================
QUALITY GATE METRICS REPORT
================================================================================

Model: demo_model
Samples: 1000
Classes: ['anger', 'contempt', 'disgust', 'fear', 'happiness', 'neutral', 'sadness', 'surprise']

--- Core Metrics ---
Macro F1:           0.8523
Balanced Accuracy:  0.8612
F1 Neutral:         0.8234

--- Calibration Metrics ---
ECE:                0.0654
Brier Score:        0.1423

--- Quality Gates ---
✅ Macro F1 >= 0.84:           PASS (0.8523)
✅ Balanced Accuracy >= 0.85:  PASS (0.8612)
✅ ECE <= 0.08:                PASS (0.0654)
✅ Brier <= 0.16:              PASS (0.1423)

OVERALL: PASS ✅

--- Confusion Matrix ---
[Confusion matrix visualization]

Report saved to: stats/results/quality_gate_report.json
```

### Understanding the Output

1. **Core Metrics**: The main classification metrics
2. **Calibration Metrics**: How well-calibrated the probabilities are
3. **Quality Gates**: Pass/fail for each threshold
4. **Confusion Matrix**: Visual breakdown of predictions

### Input Format

The script expects predictions in `.npz` format:

```python
import numpy as np

# Create predictions file
np.savez(
    'predictions.npz',
    y_true=np.array([0, 1, 2, ...]),      # True labels (integers)
    y_pred=np.array([0, 1, 1, ...]),      # Predicted labels (integers)
    y_prob=np.array([[0.9, 0.1, ...], ...])  # Probability for each class
)
```

### Exercises

1. **Run demo mode**:
   ```bash
   python stats/scripts/01_quality_gate_metrics.py --demo
   ```

2. **Examine the output JSON**:
   ```bash
   cat stats/results/quality_gate_report.json | python -m json.tool
   ```

3. **Create synthetic predictions**:
   ```python
   import numpy as np
   
   # Create test data
   n_samples = 500
   n_classes = 8
   
   y_true = np.random.randint(0, n_classes, n_samples)
   
   # Make predictions mostly correct (80% accuracy)
   y_pred = y_true.copy()
   mask = np.random.random(n_samples) < 0.2
   y_pred[mask] = np.random.randint(0, n_classes, mask.sum())
   
   # Create probability matrix
   y_prob = np.zeros((n_samples, n_classes))
   for i in range(n_samples):
       y_prob[i, y_pred[i]] = 0.7 + np.random.random() * 0.2
       remaining = 1 - y_prob[i, y_pred[i]]
       other_probs = np.random.random(n_classes - 1)
       other_probs = other_probs / other_probs.sum() * remaining
       j = 0
       for c in range(n_classes):
           if c != y_pred[i]:
               y_prob[i, c] = other_probs[j]
               j += 1
   
   # Save
   np.savez('stats/data/test_predictions.npz', 
            y_true=y_true, y_pred=y_pred, y_prob=y_prob)
   
   print("Saved test predictions")
   ```

4. **Run with your predictions**:
   ```bash
   python stats/scripts/01_quality_gate_metrics.py --predictions stats/data/test_predictions.npz
   ```

### Checkpoint: Day 3
- [ ] Can run script in demo mode
- [ ] Understand the output format
- [ ] Can create prediction files
- [ ] Can run with custom predictions

---

## Day 4: Interpreting Results

### Reading the Confusion Matrix

Example confusion matrix for 3 classes:

```
              Predicted
           happy  sad  angry
Actual
happy       45     3     2     → 45/(45+3+2) = 90% recall for happy
sad          5    38     7     → 38/(5+38+7) = 76% recall for sad
angry        2     4    44     → 44/(2+4+44) = 88% recall for angry
             ↓
           45/(45+5+2) = 87% precision for happy
```

**Common patterns to look for**:

1. **Diagonal dominance**: Good! Most predictions correct
2. **Off-diagonal clusters**: Confusion between specific classes
3. **Empty rows/columns**: Model ignoring some classes
4. **Asymmetric confusion**: A→B more common than B→A

### Identifying Problem Classes

```python
# From the confusion matrix, identify:
# 1. Classes with low recall (row sum vs diagonal)
# 2. Classes with low precision (column sum vs diagonal)
# 3. Pairs with high confusion (large off-diagonal values)
```

### What to Do When Gates Fail

| Failure | Likely Cause | Action |
|---------|--------------|--------|
| Low Macro F1 | Poor overall performance | More training data, better model |
| Low Balanced Acc | Ignoring rare classes | Class weighting, oversampling |
| Low F1 Neutral | Neutral confusion | More neutral examples |
| High ECE | Overconfident predictions | Temperature scaling |
| High Brier | Poor probability estimates | Calibration training |

### Exercises

1. **Analyze a confusion matrix**:
   - Which classes have highest recall?
   - Which classes are most confused?
   - Is there asymmetric confusion?

2. **Simulate a failing model**:
   ```python
   # Create biased predictions (always predict class 0)
   y_true = np.random.randint(0, 8, 500)
   y_pred = np.zeros(500, dtype=int)  # Always predict class 0
   
   # This should fail Balanced Accuracy gate
   ```

3. **Compare two models**:
   - Run script on two different prediction files
   - Compare metrics side by side
   - Identify which model is better and why

### Checkpoint: Day 4
- [ ] Can interpret confusion matrices
- [ ] Know how to identify problem classes
- [ ] Understand what to do when gates fail

---

## Day 5: Practice & Review

### Comprehensive Exercise

Complete workflow:

1. **Generate predictions** (or use existing)
2. **Run quality gate script**
3. **Analyze the confusion matrix**
4. **Identify any failing gates**
5. **Document findings**

### Knowledge Check

Answer these questions:

1. Why is Macro F1 preferred over accuracy for imbalanced data?
2. What does Balanced Accuracy protect against?
3. If ECE is high, what does that mean about the model?
4. How do you read a confusion matrix to find the most confused class pair?
5. What are the Gate A thresholds for Macro F1 and Balanced Accuracy?

### Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Macro F1 calculation | __ |
| Balanced Accuracy | __ |
| Confusion matrix reading | __ |
| Gate A requirements | __ |
| ECE and Brier | __ |
| Running the script | __ |

---

## Week 5 Deliverables

| Deliverable | Status |
|-------------|--------|
| Tutorial 01 read | [ ] |
| Script 01 run in demo mode | [ ] |
| Custom predictions created | [ ] |
| Confusion matrix analyzed | [ ] |
| Knowledge check passed | [ ] |

---

## Next Week

[Week 6: Statistical Tests](WEEK_06_STATISTICAL_TESTS.md) covers:
- Stuart-Maxwell test for model comparison
- Per-class paired t-tests with Benjamini-Hochberg correction
- Identifying which classes improved or degraded
