# Tutorial 02: Univariate Metrics

This tutorial covers the metrics used to evaluate a **single** model's performance. These are the building blocks for understanding how well a classifier works.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Understand confusion matrices and how to read them
2. Know the formulas for precision, recall, and F1 score
3. Understand macro F1 and balanced accuracy
4. Know how to use the `univariate.py` module

---

## Part 1: The Confusion Matrix

### What Is It?

A confusion matrix shows how predictions compare to ground truth. For a 2-class problem:

```
                    Predicted
                    Happy   Sad
Actual  Happy   [   TP      FN   ]
        Sad     [   FP      TN   ]
```

Wait—that's the binary view. Our code uses a more general form:

```
                    Predicted
                    Class 0   Class 1
Actual  Class 0  [   n00       n01   ]
        Class 1  [   n10       n11   ]
```

Where `n[i,j]` = count of samples with true label `i` predicted as `j`.

### Example

Given:
```python
y_true = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]  # 4 happy, 6 sad
y_pred = [0, 0, 0, 1, 1, 1, 1, 1, 0, 0]  # Model's guesses
```

The confusion matrix is:

```
                Predicted
                Happy(0)  Sad(1)
Actual Happy(0) [  3        1   ]   <- 3 correct, 1 wrong
       Sad(1)   [  2        4   ]   <- 2 wrong, 4 correct
```

### The Code

```python
from stats.Opus4.5_stats.phase_1 import compute_confusion_matrix
import numpy as np

y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0])

cm = compute_confusion_matrix(y_true, y_pred, num_classes=2)
print(cm)
```

Output:
```
[[3 1]
 [2 4]]
```

### Reading the Matrix

- **Diagonal** (top-left to bottom-right): Correct predictions
- **Off-diagonal**: Errors
- **Row sums**: Total samples per actual class
- **Column sums**: Total predictions per class

---

## Part 2: Precision, Recall, and F1

These metrics describe performance **per class**.

### Definitions

For class `k`:

| Metric | Formula | Intuition |
|--------|---------|-----------|
| **Precision** | TP / (TP + FP) | "Of all I predicted as k, how many were actually k?" |
| **Recall** | TP / (TP + FN) | "Of all actual k samples, how many did I find?" |
| **F1** | 2 × (P × R) / (P + R) | Harmonic mean of precision and recall |

### Visual Intuition

Think of a search engine:
- **Precision**: Of the results shown, how many are relevant?
- **Recall**: Of all relevant documents, how many did I find?

High precision = few false alarms
High recall = few missed cases

### Example Calculation

From our confusion matrix for **Class 0 (Happy)**:

```
TP = 3  (predicted happy, actually happy)
FP = 2  (predicted happy, actually sad)
FN = 1  (predicted sad, actually happy)
```

```python
precision_0 = 3 / (3 + 2)  # = 0.60
recall_0 = 3 / (3 + 1)     # = 0.75
f1_0 = 2 * (0.60 * 0.75) / (0.60 + 0.75)  # = 0.667
```

### The Code

```python
from stats.Opus4.5_stats.phase_1 import (
    compute_confusion_matrix,
    compute_precision,
    compute_recall,
    compute_f1
)

cm = compute_confusion_matrix(y_true, y_pred, num_classes=2)

# For class 0
prec_0 = compute_precision(cm, class_idx=0)
rec_0 = compute_recall(cm, class_idx=0)
f1_0 = compute_f1(prec_0, rec_0)

print(f"Class 0 - Precision: {prec_0:.3f}, Recall: {rec_0:.3f}, F1: {f1_0:.3f}")
```

Output:
```
Class 0 - Precision: 0.600, Recall: 0.750, F1: 0.667
```

### Computing All Classes at Once

```python
from stats.Opus4.5_stats.phase_1 import compute_per_class_metrics

precision, recall, f1, support = compute_per_class_metrics(cm)

print("Class | Precision | Recall | F1    | Support")
print("-" * 45)
for i in range(2):
    print(f"  {i}   |   {precision[i]:.3f}   | {recall[i]:.3f} | {f1[i]:.3f} |   {support[i]}")
```

Output:
```
Class | Precision | Recall | F1    | Support
---------------------------------------------
  0   |   0.600   | 0.750 | 0.667 |   4
  1   |   0.800   | 0.667 | 0.727 |   6
```

**Support** = number of actual samples in each class.

---

## Part 3: Macro F1 Score

### What Is It?

**Macro F1** is the unweighted average of per-class F1 scores:

```
Macro F1 = (F1_class0 + F1_class1 + ... + F1_classK) / K
```

### Why Use It?

Macro F1 treats all classes equally, regardless of class size. This is important when:
- Classes are imbalanced (e.g., 90% happy, 10% sad)
- All classes matter equally for your application

### Example

```python
from stats.Opus4.5_stats.phase_1 import compute_macro_f1

# From our example: F1_0 = 0.667, F1_1 = 0.727
macro_f1 = compute_macro_f1(f1)
print(f"Macro F1: {macro_f1:.3f}")
```

Output:
```
Macro F1: 0.697
```

Calculation: (0.667 + 0.727) / 2 = 0.697

---

## Part 4: Balanced Accuracy

### What Is It?

**Balanced Accuracy** is the average recall across all classes:

```
Balanced Accuracy = (Recall_0 + Recall_1 + ... + Recall_K) / K
```

### Why Use It?

Regular accuracy can be misleading with imbalanced data:

| Dataset | Model Strategy | Accuracy | Balanced Accuracy |
|---------|---------------|----------|-------------------|
| 95% happy, 5% sad | Always predict "happy" | 95% | 50% |

Balanced accuracy exposes this problem!

### Example

```python
from stats.Opus4.5_stats.phase_1 import compute_balanced_accuracy

balanced_acc = compute_balanced_accuracy(cm)
print(f"Balanced Accuracy: {balanced_acc:.3f}")
```

Output:
```
Balanced Accuracy: 0.708
```

Calculation: (0.75 + 0.667) / 2 = 0.708

---

## Part 5: Input Validation

Our code validates inputs to prevent errors. This is a **defensive programming** practice.

### What Gets Validated?

```python
def _validate_arrays(y_true, y_pred, name="input"):
    """Validate that prediction arrays are valid."""
    if y_true is None or y_pred is None:
        raise ValueError(f"{name}: Arrays cannot be None")
    
    if len(y_true) == 0 or len(y_pred) == 0:
        raise ValueError(f"{name}: Arrays cannot be empty")
    
    if len(y_true) != len(y_pred):
        raise ValueError(f"{name}: Array lengths must match")
```

### Why This Matters

Without validation, you might get cryptic errors:

```python
# Without validation - confusing error
cm = compute_confusion_matrix(None, [0, 1], 2)
# TypeError: 'NoneType' object is not iterable

# With validation - clear error
cm = compute_confusion_matrix(None, [0, 1], 2)
# ValueError: compute_confusion_matrix: Arrays cannot be None
```

### Try It

```python
# These should all raise clear errors:
try:
    compute_confusion_matrix([], [], 2)
except ValueError as e:
    print(f"Caught: {e}")

try:
    compute_confusion_matrix([0, 1], [0], 2)
except ValueError as e:
    print(f"Caught: {e}")
```

---

## Part 6: The Complete Pipeline

### Using `compute_all_univariate_metrics`

This function computes everything at once:

```python
from stats.Opus4.5_stats.phase_1 import compute_all_univariate_metrics

results = compute_all_univariate_metrics(
    y_true=y_true,
    y_pred=y_pred,
    num_classes=2,
    class_names=["happy", "sad"]
)

print(f"Confusion Matrix:\n{results.confusion_matrix}")
print(f"\nPer-class F1: {results.f1}")
print(f"Macro F1: {results.macro_f1:.4f}")
print(f"Balanced Accuracy: {results.balanced_accuracy:.4f}")
```

### The `UnivariateResults` Dataclass

Results are returned in a structured dataclass:

```python
@dataclass
class UnivariateResults:
    confusion_matrix: np.ndarray    # Shape: (num_classes, num_classes)
    precision: Dict[int, float]     # {0: 0.60, 1: 0.80}
    recall: Dict[int, float]        # {0: 0.75, 1: 0.67}
    f1: Dict[int, float]            # {0: 0.667, 1: 0.727}
    macro_f1: float                 # 0.697
    balanced_accuracy: float        # 0.708
    support: Dict[int, int]         # {0: 4, 1: 6}
    class_names: List[str]          # ["happy", "sad"]
```

This makes it easy to access any metric you need.

---

## Part 7: Gate A Validation

### What Is Gate A?

Gate A is our **quality threshold** before deploying a model:

| Metric | Threshold |
|--------|-----------|
| Macro F1 | ≥ 0.84 |
| Balanced Accuracy | ≥ 0.85 |
| Per-class F1 Floor | ≥ 0.75 |

### Using `validate_gate_a`

```python
from stats.Opus4.5_stats.phase_1 import validate_gate_a

gate_result = validate_gate_a(results)

print(f"Gate A Passed: {gate_result.passed}")
if not gate_result.passed:
    print("Failures:")
    for failure in gate_result.failures:
        print(f"  - {failure}")
```

Output (for our example):
```
Gate A Passed: False
Failures:
  - Macro F1 0.6970 < 0.84
  - Balanced Accuracy 0.7083 < 0.85
  - happy F1 0.6667 < 0.75
```

### Custom Thresholds

You can adjust thresholds if needed:

```python
gate_result = validate_gate_a(
    results,
    macro_f1_threshold=0.60,
    balanced_acc_threshold=0.60,
    f1_floor_threshold=0.50
)
print(f"Gate A Passed (relaxed): {gate_result.passed}")
```

---

## Part 8: Printing Reports

### Using `print_univariate_report`

```python
from stats.Opus4.5_stats.phase_1 import print_univariate_report

print_univariate_report(results, model_name="My Model", gate_a_result=gate_result)
```

Output:
```
============================================================
UNIVARIATE METRICS: My Model
============================================================

Confusion Matrix:
[[3 1]
 [2 4]]

Per-Class Metrics:
Class              Precision     Recall         F1    Support
-------------------------------------------------------
happy                 0.6000     0.7500     0.6667          4
sad                   0.8000     0.6667     0.7273          6
-------------------------------------------------------

Macro F1:          0.6970
Balanced Accuracy: 0.7083

============================================================
GATE A VALIDATION: FAILED ✗
============================================================
...
```

---

## Hands-On Exercise

### Task: Evaluate a "Perfect" Model

1. Create predictions that match ground truth exactly
2. Compute all metrics
3. Verify Gate A passes

```python
import numpy as np
from stats.Opus4.5_stats.phase_1 import (
    compute_all_univariate_metrics,
    validate_gate_a,
    print_univariate_report
)

# Create data
y_true = np.array([0]*50 + [1]*50)  # 50 happy, 50 sad
y_pred = y_true.copy()  # Perfect predictions!

# TODO: Compute metrics and validate
# Your code here...
```

### Expected Results

- All F1 scores = 1.0
- Macro F1 = 1.0
- Balanced Accuracy = 1.0
- Gate A: PASSED

---

## Summary

| Function | Purpose |
|----------|---------|
| `compute_confusion_matrix` | Build the confusion matrix |
| `compute_precision` | Precision for one class |
| `compute_recall` | Recall for one class |
| `compute_f1` | F1 from precision and recall |
| `compute_per_class_metrics` | All metrics for all classes |
| `compute_macro_f1` | Average F1 across classes |
| `compute_balanced_accuracy` | Average recall across classes |
| `compute_all_univariate_metrics` | Everything in one call |
| `validate_gate_a` | Check against thresholds |
| `print_univariate_report` | Pretty-print results |

---

## Self-Check Questions

1. What does precision measure? Recall?
2. Why is F1 the *harmonic* mean, not the arithmetic mean?
3. Why do we use balanced accuracy instead of regular accuracy?
4. What are the three Gate A thresholds?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions  
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 03: Multivariate Tests**.
