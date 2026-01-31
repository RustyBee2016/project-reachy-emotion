# Tutorial 04: Paired Tests and Multiple Comparison Correction

This tutorial covers statistical tests for comparing models using **cross-validation results**. Unlike Tutorial 03, which compared single predictions, here we compare F1 scores across multiple folds.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Understand paired t-tests and when to use them
2. Know how to calculate and interpret Cohen's d effect size
3. Understand the multiple comparison problem
4. Apply the Benjamini-Hochberg correction

---

## Why Paired Tests?

### The Problem with Single Test Sets

In Tutorial 03, we compared models on a single test set. But what if that test set happened to contain "easy" examples that favor one model?

**Solution**: Use **k-fold cross-validation** to get multiple performance measurements, then compare using a **paired test**.

### What is Cross-Validation?

```
Data: [████████████████████████████████████████]

Fold 1: [Test][  Training Data                  ]
Fold 2: [    ][Test][  Training Data            ]
Fold 3: [         ][Test][  Training Data       ]
Fold 4: [              ][Test][  Training Data  ]
Fold 5: [                   ][Test][ Training   ]
```

Each fold gives us one F1 score per model. With 5 folds, we get 5 paired measurements.

### Why "Paired"?

Each fold uses the **same test samples** for both models. This creates natural pairs:

| Fold | Model A F1 | Model B F1 | Same Test Data? |
|------|------------|------------|-----------------|
| 1 | 0.87 | 0.85 | ✓ Yes |
| 2 | 0.86 | 0.84 | ✓ Yes |
| 3 | 0.88 | 0.86 | ✓ Yes |
| 4 | 0.85 | 0.83 | ✓ Yes |
| 5 | 0.87 | 0.85 | ✓ Yes |

Because they're paired, we can use more powerful statistical tests.

---

## Part 1: The Paired t-Test

### What Does It Test?

The paired t-test asks: **Is the average difference between paired observations significantly different from zero?**

**Null Hypothesis (H₀)**: Mean difference = 0 (models are equivalent)
**Alternative (H₁)**: Mean difference ≠ 0 (one model is better)

### The Math

Given paired scores (A₁, B₁), (A₂, B₂), ..., (Aₙ, Bₙ):

1. Calculate differences: dᵢ = Aᵢ - Bᵢ
2. Calculate mean difference: d̄ = mean(d)
3. Calculate standard deviation: sᵈ = std(d)
4. Calculate t-statistic: t = d̄ / (sᵈ / √n)

### The Code

```python
from stats.Opus4.5_stats.phase_1 import paired_t_test
import numpy as np

# F1 scores from 5-fold CV
scores_a = np.array([0.87, 0.86, 0.88, 0.85, 0.87])
scores_b = np.array([0.85, 0.84, 0.86, 0.83, 0.85])

t_stat, p_value, mean_diff, std_diff = paired_t_test(scores_a, scores_b)

print(f"Paired t-Test Results:")
print(f"  Mean difference (A - B): {mean_diff:+.4f}")
print(f"  Std of differences: {std_diff:.4f}")
print(f"  t-statistic: {t_stat:.4f}")
print(f"  p-value: {p_value:.4f}")
```

### Example Output

```
Paired t-Test Results:
  Mean difference (A - B): +0.0200
  Std of differences: 0.0000
  t-statistic: inf
  p-value: 0.0000
```

**Note**: In this example, the difference is exactly 0.02 for every fold, so std=0 and t=∞. In real data, you'd see variation.

### Interpreting the Results

| p-value | Interpretation |
|---------|----------------|
| p < 0.05 | **Significant**: The difference is unlikely due to chance |
| p ≥ 0.05 | **Not significant**: Can't rule out that difference is random |

But wait—**p-values don't tell you the size of the effect!**

---

## Part 2: Cohen's d Effect Size

### What Is It?

Cohen's d measures how large the difference is in standardized units:

```
d = mean(differences) / std(differences)
```

It answers: "How many standard deviations apart are the models?"

### Interpretation Scale (Cohen, 1988)

| |d| | Interpretation |
|----|----------------|
| < 0.2 | **Negligible** — difference exists but is tiny |
| 0.2 - 0.5 | **Small** — noticeable with careful measurement |
| 0.5 - 0.8 | **Medium** — easily noticeable |
| ≥ 0.8 | **Large** — obvious difference |

### The Code

```python
from stats.Opus4.5_stats.phase_1 import cohens_d, interpret_cohens_d

d = cohens_d(scores_a, scores_b)
interpretation = interpret_cohens_d(d)

print(f"Cohen's d: {d:+.3f}")
print(f"Interpretation: {interpretation}")
```

### Example with Real Variance

```python
# More realistic data with variance
scores_a = np.array([0.87, 0.84, 0.89, 0.85, 0.88])
scores_b = np.array([0.82, 0.80, 0.85, 0.81, 0.84])

d = cohens_d(scores_a, scores_b)
print(f"Cohen's d: {d:+.3f}")  # e.g., +1.58
print(f"Interpretation: {interpret_cohens_d(d)}")  # Large (favoring A)
```

### Why Both p-value and Effect Size?

| Scenario | p-value | Cohen's d | Meaning |
|----------|---------|-----------|---------|
| Large sample, tiny difference | < 0.05 | 0.1 | Statistically significant but not practical |
| Small sample, large difference | > 0.05 | 1.2 | Not significant but potentially important |
| Large sample, large difference | < 0.05 | 1.0 | Both significant and practically important ✓ |

**Always report both!**

---

## Part 3: The Multiple Comparison Problem

### The Setup

We run paired t-tests for **each class**:
- Test 1: Is Model A better at "happy"?
- Test 2: Is Model A better at "sad"?

Each test has α = 0.05 chance of false positive (Type I error).

### The Problem

With 2 tests:
- Probability of at least one false positive = 1 - (1-0.05)² = 9.75%

With 8 classes (like Ekman emotions):
- Probability = 1 - (1-0.05)⁸ = 33.7%

**One-third chance of a false positive!** This is called the **family-wise error rate (FWER)**.

### Visual Illustration

```
Running 10 tests at α = 0.05:

True effects:     ●  ●  ○  ○  ○  ○  ○  ○  ○  ○
                  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓
Significant?      ✓  ✓  ✗  ✗  ✓  ✗  ✗  ✗  ✗  ✗
                  ↑  ↑        ↑
                  |  |        |
               Correct     FALSE POSITIVE!
```

---

## Part 4: Benjamini-Hochberg (BH) Correction

### What Is It?

The Benjamini-Hochberg procedure controls the **False Discovery Rate (FDR)** — the expected proportion of false positives among rejected hypotheses.

### How It Works

1. **Sort** p-values from smallest to largest
2. **Rank** them 1, 2, 3, ...
3. **Calculate threshold** for each: threshold_i = (rank_i / m) × α
4. **Find cutoff**: largest rank where p_i ≤ threshold_i
5. **Reject** all hypotheses with rank ≤ cutoff

### Example

Given p-values: [0.001, 0.01, 0.03, 0.04, 0.20] with α = 0.05

| Rank | p-value | Threshold = (rank/5) × 0.05 | p ≤ threshold? |
|------|---------|------------------------------|----------------|
| 1 | 0.001 | 0.010 | ✓ |
| 2 | 0.010 | 0.020 | ✓ |
| 3 | 0.030 | 0.030 | ✓ |
| 4 | 0.040 | 0.040 | ✓ |
| 5 | 0.200 | 0.050 | ✗ |

**Cutoff = Rank 4** → Reject hypotheses with ranks 1, 2, 3, 4.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import benjamini_hochberg_correction

p_values = [0.001, 0.01, 0.03, 0.04, 0.20]

significant = benjamini_hochberg_correction(p_values, alpha=0.05)

print("BH Correction Results:")
for i, (p, sig) in enumerate(zip(p_values, significant)):
    print(f"  Test {i+1}: p={p:.3f}, Significant after BH: {sig}")
```

Output:
```
BH Correction Results:
  Test 1: p=0.001, Significant after BH: True
  Test 2: p=0.010, Significant after BH: True
  Test 3: p=0.030, Significant after BH: True
  Test 4: p=0.040, Significant after BH: True
  Test 5: p=0.200, Significant after BH: False
```

### Why BH Instead of Bonferroni?

| Method | Controls | Adjusted α for 10 tests |
|--------|----------|-------------------------|
| **Bonferroni** | FWER | α/10 = 0.005 (very strict) |
| **Benjamini-Hochberg** | FDR | Adaptive (less strict) |

BH is preferred when:
- You have many tests
- Some false positives are acceptable
- You don't want to miss real effects

---

## Part 5: The Complete Pipeline

### Using `run_per_class_paired_tests`

This function does everything at once:

```python
from stats.Opus4.5_stats.phase_1 import run_per_class_paired_tests
import numpy as np

# F1 scores per class across 5 folds
f1_folds_a = {
    0: np.array([0.87, 0.86, 0.88, 0.85, 0.87]),  # happy
    1: np.array([0.84, 0.85, 0.86, 0.83, 0.85])   # sad
}

f1_folds_b = {
    0: np.array([0.85, 0.84, 0.86, 0.83, 0.85]),  # happy
    1: np.array([0.82, 0.83, 0.84, 0.81, 0.83])   # sad
}

results = run_per_class_paired_tests(
    f1_folds_a,
    f1_folds_b,
    class_names=["happy", "sad"],
    alpha=0.05,
    apply_bh_correction=True
)

for r in results:
    print(f"\nClass: {r.class_name}")
    print(f"  Mean diff: {r.mean_diff:+.4f}")
    print(f"  t-stat: {r.t_statistic:.3f}, p-value: {r.p_value:.4f}")
    print(f"  Cohen's d: {r.cohens_d:+.3f} ({r.effect_interpretation})")
    print(f"  Significant (raw): {r.significant_raw}")
    print(f"  Significant (BH corrected): {r.significant_corrected}")
```

### The `PairedTestResult` Dataclass

```python
@dataclass
class PairedTestResult:
    class_idx: int              # 0, 1, ...
    class_name: str             # "happy", "sad"
    mean_diff: float            # Mean(A - B)
    std_diff: float             # Std of differences
    t_statistic: float          # t-test statistic
    p_value: float              # Raw p-value
    cohens_d: float             # Effect size
    effect_interpretation: str  # "Large (favoring A)"
    significant_raw: bool       # p < alpha (before correction)
    significant_corrected: bool # After BH correction
    alpha: float                # Significance level
    rank: int                   # Rank for BH procedure
```

**Note on Mutability**: The `significant_corrected` and `rank` fields are set *after* the object is created. This two-phase design is documented in the code because BH correction requires seeing all p-values first.

---

## Part 6: Printing Reports

```python
from stats.Opus4.5_stats.phase_1 import print_paired_tests_report

print_paired_tests_report(results, "Model A", "Model B")
```

Output:
```
================================================================================
PAIRED T-TESTS (Per-Class F1): Model A vs Model B
================================================================================

Class        Mean Δ    Std Δ         t    p-value       d               Effect    Sig (BH)
-----------------------------------------------------------------------------------------------
happy        +0.0200   0.0000      inf     0.0000    +inf       Large (favoring A)       Yes*
sad          +0.0200   0.0000      inf     0.0000    +inf       Large (favoring A)       Yes*
-----------------------------------------------------------------------------------------------
* Significant after Benjamini-Hochberg correction

Summary:
  Significant (raw):       2/2
  Significant (corrected): 2/2
```

---

## Part 7: Practical Considerations

### Minimum Number of Folds

```python
# This will raise an error:
try:
    paired_t_test(np.array([0.85]), np.array([0.80]))
except ValueError as e:
    print(f"Error: {e}")
# Error: Need at least 2 folds for paired comparison
```

**Rule**: You need at least 2 folds, but 5+ is recommended for reliable results.

### Handling Zero Variance

If the difference is exactly the same across all folds:

```python
scores_a = np.array([0.85, 0.85, 0.85, 0.85, 0.85])
scores_b = np.array([0.80, 0.80, 0.80, 0.80, 0.80])

# Difference is always 0.05, std = 0
t_stat, p_value, mean_diff, std_diff = paired_t_test(scores_a, scores_b)
# t_stat = inf (or -inf), p_value = 0.0
```

This is an edge case indicating extremely consistent results.

### When Results Conflict

What if:
- Paired t-test says "significant" (p < 0.05)
- Cohen's d says "negligible" (|d| < 0.2)

**Interpretation**: The difference is real but tiny. Statistically detectable due to large sample size, but not practically meaningful.

---

## Decision Flowchart

```
Have CV fold scores for both models?
              │
              ▼
     ┌────────────────────┐
     │ Run paired t-test  │
     │ for each class     │
     └─────────┬──────────┘
               │
               ▼
     ┌────────────────────┐
     │ Calculate Cohen's d│
     │ for effect size    │
     └─────────┬──────────┘
               │
               ▼
     ┌────────────────────┐
     │ Multiple classes?  │
     └─────────┬──────────┘
               │
        Yes    │    No
        ▼      │    ▼
   Apply BH    │  Report raw
   correction  │  p-value
        │      │
        └──────┴──────┐
                      ▼
          ┌────────────────────┐
          │ Report: p-value,   │
          │ Cohen's d, and     │
          │ BH-corrected sig.  │
          └────────────────────┘
```

---

## Complete Example

```python
import numpy as np
from stats.Opus4.5_stats.phase_1 import (
    run_per_class_paired_tests,
    print_paired_tests_report
)

# Simulate 5-fold CV results for 2 models
np.random.seed(42)

# Model A: Generally better
f1_folds_a = {
    0: 0.85 + np.random.normal(0, 0.02, 5),  # happy
    1: 0.83 + np.random.normal(0, 0.02, 5)   # sad
}

# Model B: Generally worse
f1_folds_b = {
    0: 0.82 + np.random.normal(0, 0.02, 5),  # happy
    1: 0.80 + np.random.normal(0, 0.02, 5)   # sad
}

# Run analysis
results = run_per_class_paired_tests(
    f1_folds_a, f1_folds_b,
    class_names=["happy", "sad"]
)

# Print report
print_paired_tests_report(results, "Model A", "Model B")
```

---

## Summary

| Concept | Purpose |
|---------|---------|
| **Paired t-test** | Test if mean difference ≠ 0 |
| **Cohen's d** | Measure effect size (small/medium/large) |
| **BH correction** | Control false discovery rate for multiple tests |
| **Raw significance** | p < α before any correction |
| **Corrected significance** | p significant after BH adjustment |

---

## Self-Check Questions

1. Why do we use a "paired" t-test instead of a regular t-test?
2. What's the difference between p-value and effect size?
3. Why do we need BH correction when testing multiple classes?
4. What does Cohen's d = 0.8 mean in practical terms?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 05: Visualization**.
