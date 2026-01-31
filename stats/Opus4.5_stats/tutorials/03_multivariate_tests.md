# Tutorial 03: Multivariate Tests for Model Comparison

This tutorial covers statistical tests for comparing **two models**. While univariate metrics tell us how well each model performs, multivariate tests tell us if the *difference* between models is statistically significant.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Understand contingency tables for model comparison
2. Know when and how to use the Stuart-Maxwell test
3. Understand McNemar's test for per-class comparisons
4. Apply Cohen's Kappa to measure inter-model agreement

---

## Why Compare Models Statistically?

Imagine:
- Model A: 87% accuracy
- Model B: 85% accuracy

**Question**: Is Model A actually better, or could this 2% difference be due to random chance?

**Statistical tests answer this with a p-value** — the probability of seeing this difference (or larger) if the models were actually equivalent.

---

## Part 1: The Contingency Table

### Concept

A contingency table categorizes each sample based on how **both** models performed:

| Category | Description |
|----------|-------------|
| Both Correct | A ✓, B ✓ |
| A Correct Only | A ✓, B ✗ |
| B Correct Only | A ✗, B ✓ |
| Both Incorrect | A ✗, B ✗ |

This is computed **per class**.

### Visual Representation

```
For each class:
                       Model B
                    Correct   Wrong
Model A  Correct  [  n_both    b   ]
         Wrong    [    c    n_neither ]

Where:
- b = samples A got right but B got wrong ("discordant: A wins")
- c = samples A got wrong but B got right ("discordant: B wins")
```

### The Code

```python
from stats.Opus4.5_stats.phase_1 import build_contingency_table
import numpy as np

# Example data
y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
pred_a = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0])  # Model A
pred_b = np.array([0, 0, 1, 1, 1, 1, 1, 0, 0, 0])  # Model B

ct = build_contingency_table(y_true, pred_a, pred_b, num_classes=2)
print("Contingency Table (rows: both_correct, A_only, B_only, both_wrong):")
print(ct)
```

Output:
```
Contingency Table (rows: both_correct, A_only, B_only, both_wrong):
[[2 3]    <- Both correct (Class 0: 2, Class 1: 3)
 [1 1]    <- A correct, B wrong
 [0 1]    <- A wrong, B correct  
 [1 1]]   <- Both wrong
```

### Reading the Table

- **Row 0**: Both models got it right
- **Row 1**: Only Model A was right (b values)
- **Row 2**: Only Model B was right (c values)
- **Row 3**: Both models got it wrong

The key insight: **Rows 1 and 2 are the "discordant" pairs** — samples where models disagree. These drive the statistical tests!

---

## Part 2: Stuart-Maxwell Test

### What Does It Test?

The Stuart-Maxwell test checks **marginal homogeneity** — whether the overall distribution of predictions is the same for both models.

**Null Hypothesis (H₀)**: The marginal distributions are equal.
- Model A predicts class 0 the same number of times as Model B
- Model A predicts class 1 the same number of times as Model B

**Alternative (H₁)**: The distributions differ.

### When to Use It

Use Stuart-Maxwell when you want to know:
> "Do these models have different *patterns* of predictions?"

A significant result means one model is systematically biased toward certain classes compared to the other.

### The Math (Simplified)

1. Build an "agreement matrix" showing how often A predicts class i when B predicts class j
2. Compare row marginals (what A predicts) to column marginals (what B predicts)
3. Compute a chi-square statistic testing if the differences are significant

### The Code

```python
from stats.Opus4.5_stats.phase_1 import stuart_maxwell_test

result = stuart_maxwell_test(pred_a, pred_b, num_classes=2, alpha=0.05)

print(f"Stuart-Maxwell Test:")
print(f"  χ² statistic: {result.statistic:.4f}")
print(f"  p-value: {result.p_value:.4f}")
print(f"  Degrees of freedom: {result.df}")
print(f"  Significant: {result.significant}")
print(f"\nMarginal differences (A - B):")
for i, diff in enumerate(result.marginal_diff):
    print(f"  Class {i}: {diff:+d}")
```

### Interpreting Results

| p-value | Interpretation |
|---------|----------------|
| p < 0.05 | **Significant**: Models have different prediction patterns |
| p ≥ 0.05 | **Not significant**: No evidence of different patterns |

### Example Interpretation

```
Stuart-Maxwell Test:
  χ² statistic: 0.5000
  p-value: 0.4795
  Significant: False

Marginal differences (A - B):
  Class 0: +1
  Class 1: -1
```

**Interpretation**: Model A predicted "happy" one more time than Model B (and "sad" one less time), but this difference is not statistically significant (p=0.48). We cannot conclude the models have different prediction biases.

---

## Part 3: McNemar's Test (Per-Class)

### What Does It Test?

McNemar's test compares **error rates** between two models for a specific class.

**Null Hypothesis**: Both models have the same error rate for this class.

**Alternative**: One model has a different error rate.

### The Key: Discordant Pairs

Only samples where models disagree matter:
- **b**: Samples A got right but B got wrong
- **c**: Samples A got wrong but B got right

If b ≈ c, the models make different mistakes but at similar rates.
If b >> c, Model A is significantly better.
If c >> b, Model B is significantly better.

### The Formula

```
χ² = (|b - c| - 1)² / (b + c)
```

The "-1" is a continuity correction for small samples.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import mcnemar_test_per_class

results = mcnemar_test_per_class(
    ct, 
    class_names=["happy", "sad"],
    alpha=0.05
)

for r in results:
    print(f"\nClass: {r.class_name}")
    print(f"  b (A✓, B✗): {r.b}")
    print(f"  c (A✗, B✓): {r.c}")
    print(f"  χ² statistic: {r.statistic:.4f}")
    print(f"  p-value: {r.p_value:.4f}")
    print(f"  Significant: {r.significant}")
    print(f"  Winner: {r.winner if r.winner else 'None'}")
```

### Understanding the Output

```
Class: happy
  b (A✓, B✗): 1
  c (A✗, B✓): 0
  χ² statistic: 0.0000
  p-value: 1.0000
  Significant: False
  Winner: None

Class: sad
  b (A✓, B✗): 1
  c (A✗, B✓): 1
  χ² statistic: 0.0000
  p-value: 1.0000
  Significant: False
  Winner: None
```

**Interpretation**: For both classes, the models make similar numbers of unique errors. No statistically significant difference.

### Odds Ratio

The **odds ratio** quantifies how much better one model is:

```
Odds Ratio = b / c
```

| Odds Ratio | Interpretation |
|------------|----------------|
| OR > 1 | Model A makes fewer errors (A is better) |
| OR = 1 | Models are equivalent |
| OR < 1 | Model B makes fewer errors (B is better) |

---

## Part 4: Cohen's Kappa

### What Does It Measure?

Cohen's Kappa (κ) measures **agreement** between two raters (or models) beyond what would be expected by chance.

### The Formula

```
κ = (P_observed - P_expected) / (1 - P_expected)
```

Where:
- **P_observed**: Proportion of samples where both models give the same prediction
- **P_expected**: Proportion expected to agree by random chance

### Why Not Just Use Agreement Percentage?

Two models that both predict "happy" 90% of the time would agree frequently **by chance**. Kappa accounts for this.

### Interpretation Scale (Landis & Koch, 1977)

| Kappa | Interpretation |
|-------|----------------|
| < 0.00 | Poor (worse than chance) |
| 0.00 - 0.20 | Slight |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Substantial |
| 0.81 - 1.00 | Almost Perfect |

### The Code

```python
from stats.Opus4.5_stats.phase_1 import cohens_kappa

result = cohens_kappa(pred_a, pred_b, num_classes=2, alpha=0.05)

print(f"Cohen's Kappa:")
print(f"  κ = {result.kappa:.4f}")
print(f"  Standard Error: {result.std_error:.4f}")
print(f"  95% CI: [{result.ci_lower:.4f}, {result.ci_upper:.4f}]")
print(f"  p-value: {result.p_value:.4f}")
print(f"  Observed Agreement: {result.agreement_observed:.4f}")
print(f"  Expected Agreement: {result.agreement_expected:.4f}")
print(f"  Interpretation: {result.interpretation}")
```

### Example Output

```
Cohen's Kappa:
  κ = 0.5000
  Standard Error: 0.2236
  95% CI: [0.0618, 0.9382]
  p-value: 0.0253
  Observed Agreement: 0.7000
  Expected Agreement: 0.4000
  Interpretation: Moderate
```

**Interpretation**: 
- 70% of predictions agree (observed)
- 40% would agree by chance (expected)
- κ = 0.50 indicates **moderate** agreement beyond chance
- The models agree more than chance, but not perfectly

### Special Cases

```python
# Perfect agreement
kappa_perfect = cohens_kappa(pred_a, pred_a, num_classes=2)
print(f"Perfect agreement κ: {kappa_perfect.kappa}")  # 1.0

# Complete disagreement
pred_opposite = 1 - pred_a
kappa_opposite = cohens_kappa(pred_a, pred_opposite, num_classes=2)
print(f"Perfect disagreement κ: {kappa_opposite.kappa}")  # Negative
```

---

## Part 5: Implementation Note on McNemar's Test

In the code, you'll see this comment:

```python
"""
Implementation Note on McNemar's Test:
--------------------------------------
This module implements McNemar's test manually rather than using 
scipy.stats.mcnemar for the following reasons:
    1. Educational clarity: Makes the test logic transparent
    2. Per-class extension: We need per-class McNemar tests, not just binary
    3. Consistent CI calculation: We compute exact binomial CIs
    4. Integration: Reuses our build_contingency_table function
"""
```

**Why does this matter?**

- `scipy.stats.mcnemar` exists but only works for binary outcomes
- We needed per-class tests for multi-class classification
- Understanding the implementation helps you debug and extend it

---

## Part 6: Printing Reports

### Using `print_multivariate_report`

```python
from stats.Opus4.5_stats.phase_1 import print_multivariate_report

# After running all tests...
print_multivariate_report(
    stuart_maxwell=stuart_maxwell_result,
    mcnemar_results=mcnemar_results,
    kappa_result=kappa_result,
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0"
)
```

This produces a formatted report showing all comparison results.

---

## Part 7: Complete Example

Let's put it all together:

```python
import numpy as np
from stats.Opus4.5_stats.phase_1 import (
    build_contingency_table,
    stuart_maxwell_test,
    mcnemar_test_per_class,
    cohens_kappa,
    print_multivariate_report
)

# Generate example data
np.random.seed(42)
n_samples = 100

y_true = np.array([0]*50 + [1]*50)
np.random.shuffle(y_true)

# Model A: 90% accuracy
pred_a = y_true.copy()
errors_a = np.random.choice(n_samples, size=10, replace=False)
for i in errors_a:
    pred_a[i] = 1 - pred_a[i]

# Model B: 85% accuracy  
pred_b = y_true.copy()
errors_b = np.random.choice(n_samples, size=15, replace=False)
for i in errors_b:
    pred_b[i] = 1 - pred_b[i]

# Run all tests
ct = build_contingency_table(y_true, pred_a, pred_b, num_classes=2)
stuart_result = stuart_maxwell_test(pred_a, pred_b, num_classes=2)
mcnemar_results = mcnemar_test_per_class(ct, ["happy", "sad"])
kappa_result = cohens_kappa(pred_a, pred_b, num_classes=2)

# Print report
print_multivariate_report(
    stuart_result, mcnemar_results, kappa_result,
    "Model A (90%)", "Model B (85%)"
)
```

---

## Decision Flowchart

```
Want to compare two models?
           │
           ▼
    ┌──────────────────┐
    │ Build contingency│
    │     table        │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │ Q: Do models have different      │
    │    overall prediction patterns?  │
    └────────┬─────────────────────────┘
             │
             ▼
        Stuart-Maxwell Test
             │
             ▼
    ┌──────────────────────────────────┐
    │ Q: For class X specifically,     │
    │    is one model better?          │
    └────────┬─────────────────────────┘
             │
             ▼
        McNemar's Test (per class)
             │
             ▼
    ┌──────────────────────────────────┐
    │ Q: How much do models agree      │
    │    in their predictions?         │
    └────────┬─────────────────────────┘
             │
             ▼
        Cohen's Kappa
```

---

## Common Mistakes to Avoid

### Mistake 1: Confusing Significance with Importance

A significant p-value (p < 0.05) means the difference is *unlikely to be due to chance*. It doesn't mean the difference is *large* or *practically important*.

**Solution**: Always report effect sizes (like odds ratios) alongside p-values.

### Mistake 2: Ignoring Sample Size

With large samples, even tiny differences become "significant." With small samples, even large differences may not be detected.

**Solution**: Consider power analysis and confidence intervals.

### Mistake 3: Testing on Training Data

If you compare models on data they were trained on, results are meaningless.

**Solution**: Always use a held-out test set or cross-validation.

---

## Summary

| Test | Question Answered | Key Statistic |
|------|-------------------|---------------|
| **Stuart-Maxwell** | Do models have different prediction patterns? | χ², p-value |
| **McNemar's** | Is one model better for class X? | χ², odds ratio |
| **Cohen's Kappa** | How much do models agree? | κ (0-1 scale) |

---

## Self-Check Questions

1. What are "discordant pairs" in McNemar's test?
2. When would you use Stuart-Maxwell vs. McNemar's test?
3. What does κ = 0.6 mean in Cohen's Kappa?
4. Why do we use the contingency table instead of just comparing accuracies?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 04: Paired Tests and Multiple Comparison Correction**.
