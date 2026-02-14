# Tutorial 01: Univariate Quality Gate Metrics

**Module**: Phase 1 Statistical Analysis  
**Duration**: 2-3 hours  
**Difficulty**: Beginner  
**Script**: `stats/scripts/01_quality_gate_metrics.py`

---

## Table of Contents

1. [Introduction](#introduction)
2. [The Three Quality Gate Metrics](#the-three-quality-gate-metrics)
3. [Metric 1: Macro F1 Score](#metric-1-macro-f1-score)
4. [Metric 2: Balanced Accuracy](#metric-2-balanced-accuracy)
5. [Metric 3: F1 Neutral](#metric-3-f1-neutral)
6. [Script Walkthrough](#script-walkthrough)
7. [Output Interpretation](#output-interpretation)
8. [Practice Exercises](#practice-exercises)

---

## Introduction

Before deploying an emotion recognition model, we need to verify it meets minimum performance standards. This tutorial teaches you how to evaluate a model using three key metrics that form our **quality gates**.

### Why Quality Gates?

Quality gates are pass/fail checkpoints that prevent underperforming models from reaching production. Our gates ensure:

| Gate | Metric | Threshold | Purpose |
|------|--------|-----------|---------|
| 1 | Macro F1 | ≥ 0.84 | Overall classification quality |
| 2 | Balanced Accuracy | ≥ 0.82 | Protection against class imbalance |
| 3 | F1 Neutral | ≥ 0.80 | Phase 2 baseline stability |

A model must pass **all three gates** to proceed.

---

## The Three Quality Gate Metrics

### Quick Summary

| Metric | What It Measures | Why It Matters |
|--------|------------------|----------------|
| Macro F1 | Average performance across all emotion classes | Ensures no class is ignored |
| Balanced Accuracy | Average recall across all classes | Catches models that exploit imbalance |
| F1 Neutral | Performance on neutral faces specifically | Protects Phase 2 baseline |

---

## Metric 1: Macro F1 Score

### Tier 1: Middle School Explanation

Imagine you're a teacher grading how well a robot recognizes different emotions — happy, sad, angry, and so on. The robot looks at photos and guesses what emotion each person is showing.

**Macro F1 is like giving the robot a report card.** But here's the fair part: even if there are way more happy photos than angry photos, each emotion counts equally on the report card. So the robot can't cheat by just getting really good at happy faces and ignoring the hard ones.

A score of 0.84 means the robot gets about 84% right, balanced across all emotions. That's like getting a B+ where every subject matters equally, even the ones with fewer homework problems.

### Tier 2: College Freshman (CS) Explanation

Macro F1 is an aggregate classification metric that treats all classes equally regardless of their frequency in the dataset.

For each emotion class, you compute an F1 score — the harmonic mean of precision (how many of your "happy" predictions were actually happy) and recall (how many actual happy samples you caught). Then you average these F1 scores across all classes without weighting by class size.

```python
# Conceptually:
macro_f1 = (1/K) * sum(f1_score_per_class)
```

This prevents a classifier from gaming the metric by excelling at majority classes while ignoring minority ones. In an imbalanced emotion dataset where 30% of samples are neutral but only 5% are contempt, macro F1 forces the model to perform well on contempt too.

### Tier 3: Graduate Data Science Explanation

Macro F1 is defined as the unweighted arithmetic mean of per-class F1 scores:

$$F1_{\text{macro}} = \frac{1}{K} \sum_{c=1}^{K} F1_c$$

where $K$ is the number of classes and $F1_c$ is the class-specific F1 score:

$$F1_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c} = \frac{2 \cdot TP_c}{2 \cdot TP_c + FP_c + FN_c}$$

**Key Properties:**
- Bounded in [0, 1], with 1 indicating perfect classification
- Sensitive to poor performance on minority classes (a single class with F1 = 0.4 substantially drags down the macro average)
- Assumes class importance is uniform — if certain misclassifications carry higher operational cost, weighted variants may be more appropriate

**For your quality gate of ≥0.84**, this threshold implies the model must achieve strong, balanced performance across all eight emotion classes, not merely aggregate accuracy dominated by high-frequency classes.

### Equations Summary

**Precision for class c:**
$$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}$$

**Recall for class c:**
$$\text{Recall}_c = \frac{TP_c}{TP_c + FN_c}$$

**F1 for class c:**
$$F1_c = \frac{2 \cdot TP_c}{2 \cdot TP_c + FP_c + FN_c}$$

**Macro F1:**
$$F1_{\text{macro}} = \frac{1}{K} \sum_{c=1}^{K} F1_c$$

---

## Metric 2: Balanced Accuracy

### Tier 1: Middle School Explanation

Let's say you have a robot sorting candies by color, but you have 100 red candies and only 10 blue candies. If the robot just guesses "red" every time, it gets 100 out of 110 right — that sounds great!

But that's not fair. The robot never actually learned to recognize blue.

**Balanced accuracy fixes this** by asking: "What percentage of red candies did you get right?" and "What percentage of blue candies did you get right?" Then it averages those two percentages. Now the robot can't cheat — it has to be good at both colors equally.

### Tier 2: College Freshman (CS) Explanation

Balanced accuracy compensates for class imbalance by averaging the recall (true positive rate) for each class.

Regular accuracy is just `(correct predictions) / (total predictions)`. But if 90% of your dataset is one class, a model that always predicts that class gets 90% accuracy while being completely useless for the minority class.

Balanced accuracy computes:

```python
balanced_acc = (1/K) * sum(recall_per_class)
# where recall = TP / (TP + FN) for each class
```

This is equivalent to asking: "If I gave you exactly 100 samples from each class, what percentage would you classify correctly?" It normalizes for class distribution, revealing whether the model actually learned discriminative features or just learned class frequencies.

### Tier 3: Graduate Data Science Explanation

Balanced accuracy is defined as the macro-averaged recall across classes:

$$\text{Balanced Accuracy} = \frac{1}{K} \sum_{c=1}^{K} \text{Recall}_c = \frac{1}{K} \sum_{c=1}^{K} \frac{TP_c}{TP_c + FN_c}$$

This metric is equivalent to accuracy computed under the assumption of uniform class priors, regardless of the empirical class distribution in the test set.

**Properties and interpretation:**
- For binary classification, balanced accuracy equals the average of sensitivity (true positive rate) and specificity (true negative rate): $\frac{1}{2}(TPR + TNR)$
- For multi-class problems, it generalizes to the mean per-class recall
- A random classifier achieves balanced accuracy of $\frac{1}{K}$ (0.125 for 8-class emotion recognition)
- Unlike macro F1, balanced accuracy only considers recall, not precision — it doesn't penalize false positives directly

**In your pipeline**, balanced accuracy serves as an imbalance-robust sanity check. A model could theoretically achieve macro F1 ≥ 0.84 while having severely imbalanced precision/recall tradeoffs per class. The balanced accuracy gate (≥0.82) ensures recall is consistently strong.

### Equation Summary

$$\text{Balanced Accuracy} = \frac{1}{K} \sum_{c=1}^{K} \frac{TP_c}{TP_c + FN_c}$$

---

## Metric 3: F1 Neutral

### Tier 1: Middle School Explanation

In your emotion-recognition robot, "neutral" is special — it's the face people make when they're not showing any particular emotion. Think of it as the **"zero" on a thermometer**.

If the robot can't recognize neutral faces correctly, it's like having a broken thermometer that doesn't know where zero is. Then all your other measurements are off!

**F1 for neutral is a report card just for neutral faces.** It checks two things: When the robot says "neutral," is it usually right? And when someone actually has a neutral face, does the robot catch it? The F1 score combines both into one number.

### Tier 2: College Freshman (CS) Explanation

F1 (Neutral) isolates the performance on the neutral class specifically, computed as the harmonic mean of precision and recall for neutral predictions only.

```python
precision_neutral = TP_neutral / (TP_neutral + FP_neutral)
recall_neutral = TP_neutral / (TP_neutral + FN_neutral)
f1_neutral = 2 * (precision_neutral * recall_neutral) / (precision_neutral + recall_neutral)
```

**Why single out neutral?** In this project, neutral serves as the baseline for Phase 2's emotion intensity modeling. If you're measuring "how angry" someone is, you need a reliable zero point. Poor neutral classification means:

- **False positives**: non-neutral faces contaminate your baseline training data
- **False negatives**: actual neutral faces get misclassified, so your model never sees clean examples of "zero intensity"

The F1 threshold (≥0.80) ensures both failure modes are controlled before proceeding to intensity modeling.

### Tier 3: Graduate Data Science Explanation

The class-specific F1 score for the neutral class is computed from the entries of the confusion matrix corresponding to the neutral class index (assumed to be $c=0$):

$$\text{Precision}_{\text{neutral}} = \frac{TP_0}{\sum_{j=0}^{K-1} n_{j,0}} = \frac{n_{0,0}}{\sum_{j} n_{j,0}}$$

$$\text{Recall}_{\text{neutral}} = \frac{TP_0}{\sum_{j=0}^{K-1} n_{0,j}} = \frac{n_{0,0}}{\sum_{j} n_{0,j}}$$

$$F1_{\text{neutral}} = \frac{2 \cdot \text{Precision}_{\text{neutral}} \cdot \text{Recall}_{\text{neutral}}}{\text{Precision}_{\text{neutral}} + \text{Recall}_{\text{neutral}}}$$

where $n_{i,j}$ denotes the confusion matrix entry for true class $i$ and predicted class $j$.

**The operational rationale** for a dedicated neutral gate stems from the project's two-phase architecture:

| Phase 1 Failure Mode | Phase 2 Consequence |
|---------------------|---------------------|
| Low neutral precision (high FP rate) | Emotion-intensity model trained on contaminated baseline |
| Low neutral recall (high FN rate) | Intensity model lacks sufficient zero-point references |

By requiring $F1_{\text{neutral}} \geq 0.80$, you enforce simultaneous constraints on both precision and recall, ensuring the neutral class serves as a stable, uncontaminated reference distribution for continuous intensity estimation in Phase 2.

---

## Script Walkthrough

### File Location
```
stats/scripts/01_quality_gate_metrics.py
```

### Running the Script

**Demo mode (synthetic data):**
```bash
python stats/scripts/01_quality_gate_metrics.py --demo
```

**With real predictions:**
```bash
python stats/scripts/01_quality_gate_metrics.py --predictions results/predictions.npz
```

### Key Code Sections

#### 1. Configuration (Lines 40-60)

```python
# Quality gate thresholds (from requirements.md)
QUALITY_GATES = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.82,
    "f1_neutral": 0.80,
}

# Emotion class labels (8-class HSEmotion)
EMOTION_CLASSES = [
    "anger", "contempt", "disgust", "fear",
    "happiness", "neutral", "sadness", "surprise",
]
```

This section defines the thresholds and class labels. If your project uses different thresholds or classes, modify here.

#### 2. Macro F1 Calculation (Lines 95-115)

```python
def compute_macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Macro F1 Score.
    
    Macro F1 is the unweighted mean of per-class F1 scores:
        F1_macro = (1/K) * Σ F1_c
    """
    return f1_score(y_true, y_pred, average='macro', zero_division=0)
```

Uses scikit-learn's `f1_score` with `average='macro'`. The `zero_division=0` parameter handles classes with no predictions gracefully.

#### 3. Balanced Accuracy Calculation (Lines 118-135)

```python
def compute_balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Balanced Accuracy.
    
    Balanced accuracy is the macro-averaged recall across classes:
        Balanced Accuracy = (1/K) * Σ Recall_c
    """
    return balanced_accuracy_score(y_true, y_pred)
```

Uses scikit-learn's built-in `balanced_accuracy_score`.

#### 4. F1 Neutral Calculation (Lines 138-160)

```python
def compute_f1_neutral(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute F1 Score for the Neutral class specifically.
    """
    # Get per-class F1 scores
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    return per_class_f1[NEUTRAL_INDEX]
```

Uses `average=None` to get per-class scores, then extracts the neutral class by index.

#### 5. Quality Gate Evaluation (Lines 185-200)

```python
def evaluate_quality_gates(
    macro_f1: float,
    balanced_accuracy: float,
    f1_neutral: float
) -> Tuple[Dict[str, bool], bool]:
    """Evaluate metrics against quality gate thresholds."""
    gates_passed = {
        "macro_f1": macro_f1 >= QUALITY_GATES["macro_f1"],
        "balanced_accuracy": balanced_accuracy >= QUALITY_GATES["balanced_accuracy"],
        "f1_neutral": f1_neutral >= QUALITY_GATES["f1_neutral"],
    }
    overall_pass = all(gates_passed.values())
    return gates_passed, overall_pass
```

Simple threshold comparison. Returns both individual gate results and overall pass/fail.

---

## Output Interpretation

### Sample Output

```
======================================================================
QUALITY GATE METRICS REPORT: Demo Model (Synthetic Data)
======================================================================

--- QUALITY GATE EVALUATION ---
Metric                        Value    Threshold     Status
------------------------------------------------------------
Macro F1                     0.8245         0.84     FAIL ✗
Balanced Accuracy            0.8312         0.82     PASS ✓
F1 (Neutral)                 0.8834         0.80     PASS ✓
------------------------------------------------------------
OVERALL                                              FAIL ✗

--- ADDITIONAL METRICS ---
Accuracy:         0.8450
Macro Precision:  0.8312
Macro Recall:     0.8245

--- PER-CLASS F1 SCORES ---
Class              F1    Precision      Recall
--------------------------------------------------
anger            0.8234     0.8156      0.8314
contempt         0.6523     0.6789      0.6278 ← Weak class
disgust          0.7456     0.7234      0.7692
fear             0.7823     0.7912      0.7736
happiness        0.9012     0.8956      0.9069
neutral          0.8834     0.8712      0.8959 ← Phase 2 baseline
sadness          0.8456     0.8523      0.8390
surprise         0.7623     0.7834      0.7423
```

### How to Read This Output

1. **Quality Gate Evaluation**: Shows each metric, its computed value, the threshold, and pass/fail status. The model must pass ALL gates.

2. **Additional Metrics**: Supplementary information. Accuracy is shown for reference but not used for gating.

3. **Per-Class F1 Scores**: Identifies weak classes. In this example, contempt (0.6523) is dragging down the macro F1. This tells you where to focus improvement efforts.

### Decision Logic

```
IF all gates pass:
    → Model is ready for deployment consideration
    → Proceed to compare with fine-tuned version (Stuart-Maxwell)
ELSE:
    → Identify failing gates
    → Examine per-class F1 to find weak classes
    → Improve model before proceeding
```

---

## Practice Exercises

### Exercise 1: Manual Calculation

Given the following confusion matrix for a 3-class problem (A, B, C):

```
              Predicted
              A    B    C
Actual  A    45    3    2
        B     5   38    7
        C     4    6   40
```

Calculate:
1. Precision for class A
2. Recall for class A
3. F1 for class A
4. Macro F1 (compute F1 for all classes first)

<details>
<summary>Solution</summary>

**Class A:**
- TP_A = 45
- FP_A = 5 + 4 = 9 (column A, not row A)
- FN_A = 3 + 2 = 5 (row A, not column A)
- Precision_A = 45 / (45 + 9) = 45/54 = 0.833
- Recall_A = 45 / (45 + 5) = 45/50 = 0.900
- F1_A = 2 * (0.833 * 0.900) / (0.833 + 0.900) = 0.865

**Class B:**
- TP_B = 38, FP_B = 3+6=9, FN_B = 5+7=12
- Precision_B = 38/47 = 0.809
- Recall_B = 38/50 = 0.760
- F1_B = 0.784

**Class C:**
- TP_C = 40, FP_C = 2+7=9, FN_C = 4+6=10
- Precision_C = 40/49 = 0.816
- Recall_C = 40/50 = 0.800
- F1_C = 0.808

**Macro F1 = (0.865 + 0.784 + 0.808) / 3 = 0.819**

</details>

### Exercise 2: Run the Demo

1. Run the demo script:
   ```bash
   python stats/scripts/01_quality_gate_metrics.py --demo
   ```

2. Answer these questions:
   - Which quality gates passed?
   - Which emotion class has the lowest F1?
   - What is the agreement rate (accuracy)?

### Exercise 3: Modify Thresholds

1. Open `01_quality_gate_metrics.py`
2. Change the `macro_f1` threshold from 0.84 to 0.80
3. Re-run the demo
4. Does the model now pass all gates?

### Exercise 4: Interpret a Confusion Matrix

From the demo output, examine the confusion matrix:
1. Which emotion is most commonly confused with another?
2. Is there a pattern to the misclassifications?
3. How would you improve the model based on this information?

---

## Key Takeaways

1. **Macro F1** treats all classes equally — use it when class balance matters
2. **Balanced Accuracy** protects against models that exploit imbalance
3. **F1 Neutral** is critical because neutral is your Phase 2 baseline
4. A model must pass **all three gates** to proceed
5. Per-class F1 scores help identify where to focus improvement efforts

---

## Next Steps

After completing this tutorial:
1. ✅ You can evaluate a single model against quality gates
2. ➡️ Proceed to [Tutorial 02: Stuart-Maxwell Test](TUTORIAL_02_STUART_MAXWELL.md) to learn how to compare two models

---

**Questions?** Open an issue in the project repository with the `curriculum` tag.
