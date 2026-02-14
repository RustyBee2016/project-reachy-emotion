# Tutorial 02: Stuart-Maxwell Test for Model Comparison

**Module**: Phase 1 Statistical Analysis  
**Duration**: 3-4 hours  
**Difficulty**: Intermediate  
**Script**: `stats/scripts/02_stuart_maxwell_test.py`

---

## Table of Contents

1. [Introduction](#introduction)
2. [When to Use Stuart-Maxwell](#when-to-use-stuart-maxwell)
3. [Understanding the Test](#understanding-the-test)
4. [The Mathematics](#the-mathematics)
5. [Script Walkthrough](#script-walkthrough)
6. [Output Interpretation](#output-interpretation)
7. [Practice Exercises](#practice-exercises)

---

## Introduction

After your base model passes quality gates, you fine-tune it with synthetic video data. Now you need to answer a critical question:

> **Did fine-tuning actually change how the model classifies emotions?**

The Stuart-Maxwell test answers this question by comparing the prediction patterns of two models on the same test samples.

### Why Not Just Compare F1 Scores?

You might think: "Just compare the macro F1 of both models." But this misses important information:

| Scenario | Base F1 | Fine-tuned F1 | Stuart-Maxwell |
|----------|---------|---------------|----------------|
| A | 0.85 | 0.85 | **Significant** |
| B | 0.85 | 0.87 | Not Significant |

In Scenario A, both models have the same F1, but they make **different predictions** on individual samples. The fine-tuned model corrects some errors but introduces new ones — a lateral shift.

In Scenario B, the fine-tuned model has higher F1, but the improvement is within random variation across folds — not a systematic change.

Stuart-Maxwell detects **systematic changes in prediction patterns**, not just aggregate accuracy differences.

---

## When to Use Stuart-Maxwell

### Use Stuart-Maxwell When:
- ✅ You have **two models** classifying the **same samples**
- ✅ Classification is **multi-class** (more than 2 classes)
- ✅ You want to know if predictions **changed systematically**

### Don't Use Stuart-Maxwell When:
- ❌ You're evaluating a single model (use quality gates instead)
- ❌ Classification is binary (use McNemar's test instead)
- ❌ Models were tested on different samples (use unpaired tests)

### In Your Project Workflow

```
┌─────────────────────────────────────────┐
│  Base model passes quality gates        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Fine-tune with synthetic video data    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Stuart-Maxwell Test                    │◄── YOU ARE HERE
│  "Did fine-tuning change anything?"     │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
   Significant         Not Significant
        │                   │
        ▼                   ▼
┌───────────────┐   ┌───────────────────┐
│ Per-class     │   │ Fine-tuning had   │
│ t-tests       │   │ no effect         │
└───────────────┘   └───────────────────┘
```

---

## Understanding the Test

### Tier 1: Middle School Explanation

Imagine you have two robots trying to sort photos into emotion buckets. You show them both the **exact same 1,000 photos** and write down what each robot guesses.

The Stuart-Maxwell test asks: **"Did the robots sort things differently?"** Not just "who got more right," but "did they disagree about which photos go where?"

It's like comparing two students' answers on a test — not their grades, but whether they picked different answers for the same questions. If they picked mostly the same answers, the test says "no real difference." If they disagreed a lot in a lopsided way, it says "these students think differently."

**Example:**
```
Photo 1: Robot A says "happy", Robot B says "happy"     → Agreement
Photo 2: Robot A says "sad",   Robot B says "neutral"   → Disagreement
Photo 3: Robot A says "angry", Robot B says "angry"     → Agreement
Photo 4: Robot A says "happy", Robot B says "sad"       → Disagreement
```

The test looks at ALL the disagreements and asks: "Is there a pattern here, or is it just random noise?"

### Tier 2: College Freshman (CS) Explanation

The Stuart-Maxwell test is a statistical hypothesis test for **paired categorical data**. Given two models classifying the same samples, it tests whether the **marginal distributions** of predictions differ.

You construct a **K×K contingency table** where entry (i, j) counts how many samples the base model predicted as class i and the fine-tuned model predicted as class j.

```
                        Fine-tuned Model Predicts:
                    Happy   Sad   Angry   Neutral   ...
                  ┌───────┬───────┬───────┬─────────┬─────
Base        Happy │  450  │   5   │   2   │   12    │
Model       Sad   │   3   │  180  │   8   │   15    │
Predicts:   Angry │   1   │  10   │  142  │    4    │
            Neutral│   8   │   7   │   3   │  310    │
                  └───────┴───────┴───────┴─────────┴─────
```

- **Diagonal entries** = agreements (both models predicted the same class)
- **Off-diagonal entries** = disagreements

The test examines whether **row marginals** (base model's class distribution) equal **column marginals** (fine-tuned model's class distribution).

**Key intuition:** It doesn't care about ground truth — it only asks whether the two models' prediction patterns match. A significant result means fine-tuning changed the model's behavior.

### Tier 3: Graduate Data Science Explanation

The Stuart-Maxwell test evaluates **marginal homogeneity** in a K×K contingency table of paired categorical observations.

For models A (base) and B (fine-tuned) predicting on the same n samples, construct the contingency matrix:

$$N = [n_{ij}] \quad \text{where } n_{ij} = \#\{x : \hat{y}_A(x) = i, \hat{y}_B(x) = j\}$$

Define **marginal differences**:

$$d_i = n_{i \cdot} - n_{\cdot i} = \sum_{j=1}^{K} n_{ij} - \sum_{j=1}^{K} n_{ji}$$

where:
- $n_{i \cdot}$ = row marginal (base model predicts class i)
- $n_{\cdot i}$ = column marginal (fine-tuned model predicts class i)

**Null hypothesis** $H_0$: Marginal homogeneity — $\mathbb{E}[d_i] = 0$ for all $i$

**Covariance matrix** of the reduced vector $\mathbf{d} = (d_1, \ldots, d_{K-1})^T$:

$$V_{ii} = n_{i \cdot} + n_{\cdot i} - 2n_{ii}$$
$$V_{ij} = -(n_{ij} + n_{ji}) \quad \text{for } i \neq j$$

**Test statistic**:

$$\chi^2_{SM} = \mathbf{d}^T \mathbf{V}^{-1} \mathbf{d} \sim \chi^2(K-1) \text{ under } H_0$$

**Properties:**
- Operates on all n samples directly (not fold-level aggregates), maximizing statistical power
- No distributional assumptions on features — purely a test on paired categorical outcomes
- Detects systematic shifts in prediction behavior, not accuracy differences per se
- Generalizes McNemar's test (binary case) to multi-class settings

---

## The Mathematics

### Step 1: Build the Contingency Table

For each sample, record what both models predicted:

| Sample | True Label | Base Pred | Fine-tuned Pred |
|--------|------------|-----------|-----------------|
| 1 | happy | happy | happy |
| 2 | sad | neutral | sad |
| 3 | angry | angry | fear |
| ... | ... | ... | ... |

Count how many samples fall into each (base_pred, ft_pred) combination:

```python
table = np.zeros((K, K), dtype=int)
for base_pred, ft_pred in zip(base_predictions, ft_predictions):
    table[base_pred, ft_pred] += 1
```

### Step 2: Compute Marginal Differences

For each class i:

$$d_i = \text{(row i sum)} - \text{(column i sum)}$$

- **Positive $d_i$**: Base model predicted class i more often
- **Negative $d_i$**: Fine-tuned model predicted class i more often
- **Zero $d_i$**: No change in frequency for class i

### Step 3: Compute Covariance Matrix

The covariance matrix captures how the marginal differences are related:

$$V_{ii} = n_{i \cdot} + n_{\cdot i} - 2n_{ii}$$

This is the variance of $d_i$, accounting for the diagonal (agreements).

$$V_{ij} = -(n_{ij} + n_{ji})$$

This is the covariance between $d_i$ and $d_j$, based on the off-diagonal disagreements.

### Step 4: Compute Test Statistic

$$\chi^2_{SM} = \mathbf{d}^T \mathbf{V}^{-1} \mathbf{d}$$

This is a quadratic form that measures how far the marginal differences are from zero, weighted by their covariance structure.

### Step 5: Compute P-value

Under the null hypothesis, $\chi^2_{SM}$ follows a chi-squared distribution with K-1 degrees of freedom:

$$p = 1 - F_{\chi^2}(\chi^2_{SM}; K-1)$$

If $p < \alpha$ (typically 0.05), reject the null hypothesis and conclude the models differ.

---

## Script Walkthrough

### File Location
```
stats/scripts/02_stuart_maxwell_test.py
```

### Running the Script

**Demo mode (synthetic data):**
```bash
python stats/scripts/02_stuart_maxwell_test.py --demo
```

**Demo with no effect (should be non-significant):**
```bash
python stats/scripts/02_stuart_maxwell_test.py --demo --effect-size none
```

**With real predictions:**
```bash
python stats/scripts/02_stuart_maxwell_test.py --predictions results/paired_predictions.npz
```

### Key Code Sections

#### 1. Building the Contingency Table (Lines 85-105)

```python
def build_contingency_table(
    base_preds: np.ndarray,
    finetuned_preds: np.ndarray,
    n_classes: int
) -> np.ndarray:
    """
    Build K×K contingency table from paired predictions.
    
    Entry (i, j) counts samples where:
    - Base model predicted class i
    - Fine-tuned model predicted class j
    """
    table = np.zeros((n_classes, n_classes), dtype=int)
    
    for base_pred, ft_pred in zip(base_preds, finetuned_preds):
        table[base_pred, ft_pred] += 1
    
    return table
```

#### 2. Computing Marginal Differences (Lines 108-130)

```python
def compute_marginal_differences(table: np.ndarray) -> np.ndarray:
    """
    Compute marginal differences d_i = n_{i.} - n_{.i}.
    
    A positive d_i means the base model predicted class i more often.
    A negative d_i means the fine-tuned model predicted class i more often.
    """
    row_marginals = table.sum(axis=1)  # n_{i.}
    col_marginals = table.sum(axis=0)  # n_{.i}
    return row_marginals - col_marginals
```

#### 3. Computing the Covariance Matrix (Lines 133-170)

```python
def compute_covariance_matrix(table: np.ndarray) -> np.ndarray:
    """
    Compute covariance matrix V for the marginal differences.
    
    V_{ii} = n_{i.} + n_{.i} - 2*n_{ii}
    V_{ij} = -(n_{ij} + n_{ji})  for i ≠ j
    """
    K = table.shape[0]
    row_marginals = table.sum(axis=1)
    col_marginals = table.sum(axis=0)
    
    V_full = np.zeros((K, K))
    
    for i in range(K):
        for j in range(K):
            if i == j:
                V_full[i, i] = row_marginals[i] + col_marginals[i] - 2 * table[i, i]
            else:
                V_full[i, j] = -(table[i, j] + table[j, i])
    
    # Drop last row and column for non-singularity
    V_reduced = V_full[:-1, :-1]
    
    return V_reduced
```

#### 4. The Main Test Function (Lines 173-240)

```python
def stuart_maxwell_test(
    base_preds: np.ndarray,
    finetuned_preds: np.ndarray,
    alpha: float = 0.05
) -> StuartMaxwellResult:
    """
    Perform Stuart-Maxwell test for marginal homogeneity.
    
    Test statistic: χ²_SM = d^T V^{-1} d
    Under H_0: χ²_SM ~ χ²(K-1)
    """
    # ... build table, compute d, V, chi-squared, p-value ...
```

---

## Output Interpretation

### Sample Output (Significant Result)

```
======================================================================
STUART-MAXWELL TEST: Model Comparison
======================================================================

--- TEST OVERVIEW ---
Question: Did fine-tuning systematically change prediction patterns?
Samples analyzed: 2000
Agreement rate: 78.45% (1569 samples)
Disagreement rate: 21.55% (431 samples)

--- TEST RESULTS ---
Chi-squared statistic: 24.5678
Degrees of freedom: 7
P-value: 0.000912
Significance level (α): 0.05

--- INTERPRETATION ---
Result: SIGNIFICANT
The p-value (0.000912) is less than α (0.05).
→ Fine-tuning CHANGED the model's prediction patterns.
→ Proceed to per-class analysis to understand WHERE changes occurred.

--- MARGINAL DIFFERENCES ---
(Positive = base model predicted more; Negative = fine-tuned predicted more)
Class           Difference       Direction
---------------------------------------------
anger                 +12       ← Base more
contempt              -45       → Fine-tuned more
disgust               -28       → Fine-tuned more
fear                   +8       ← Base more
happiness             +15       ← Base more
neutral               -22       → Fine-tuned more
sadness                +5       ← Base more
surprise              +55       ← Base more
```

### How to Read This Output

1. **Agreement Rate**: 78.45% of samples got the same prediction from both models. The remaining 21.55% are disagreements that drive the test.

2. **Chi-squared and P-value**: The test statistic (24.57) with 7 degrees of freedom yields p = 0.0009. Since p < 0.05, the result is significant.

3. **Interpretation**: Fine-tuning changed prediction patterns. The models behave differently.

4. **Marginal Differences**: Shows which classes shifted:
   - Contempt: -45 means fine-tuned model predicts contempt 45 more times than base
   - Surprise: +55 means base model predicts surprise 55 more times than fine-tuned

### Sample Output (Non-Significant Result)

```
--- INTERPRETATION ---
Result: NOT SIGNIFICANT
The p-value (0.546621) is greater than α (0.05).
→ No systematic change in prediction patterns detected.
→ Fine-tuning had no statistically detectable effect.
```

This means the disagreements between models are within random variation — no systematic shift occurred.

### Decision Logic

```
IF Stuart-Maxwell is significant:
    → Fine-tuning changed the model's behavior
    → Proceed to per-class t-tests to identify WHICH classes changed
    → Check if changes are improvements or degradations
ELSE:
    → Fine-tuning had no detectable effect
    → Consider: Was the synthetic data insufficient?
    → Consider: Was the fine-tuning too conservative?
```

---

## Practice Exercises

### Exercise 1: Build a Contingency Table

Given these paired predictions for 10 samples:

| Sample | Base | Fine-tuned |
|--------|------|------------|
| 1 | A | A |
| 2 | A | B |
| 3 | B | B |
| 4 | B | A |
| 5 | A | A |
| 6 | C | C |
| 7 | B | C |
| 8 | A | A |
| 9 | C | B |
| 10 | B | B |

Build the 3×3 contingency table.

<details>
<summary>Solution</summary>

```
              Fine-tuned
              A    B    C
Base    A  [  3    1    0  ]
        B  [  1    2    1  ]
        C  [  0    1    1  ]
```

- (A,A) = 3: Samples 1, 5, 8
- (A,B) = 1: Sample 2
- (B,A) = 1: Sample 4
- (B,B) = 2: Samples 3, 10
- (B,C) = 1: Sample 7
- (C,B) = 1: Sample 9
- (C,C) = 1: Sample 6

</details>

### Exercise 2: Compute Marginal Differences

Using the contingency table from Exercise 1, compute the marginal differences for each class.

<details>
<summary>Solution</summary>

**Row marginals (base model totals):**
- A: 3 + 1 + 0 = 4
- B: 1 + 2 + 1 = 4
- C: 0 + 1 + 1 = 2

**Column marginals (fine-tuned model totals):**
- A: 3 + 1 + 0 = 4
- B: 1 + 2 + 1 = 4
- C: 0 + 1 + 1 = 2

**Marginal differences:**
- d_A = 4 - 4 = 0
- d_B = 4 - 4 = 0
- d_C = 2 - 2 = 0

All differences are zero, suggesting no systematic shift (as expected with this small, balanced example).

</details>

### Exercise 3: Run the Demo

1. Run with medium effect:
   ```bash
   python stats/scripts/02_stuart_maxwell_test.py --demo --effect-size medium
   ```

2. Run with no effect:
   ```bash
   python stats/scripts/02_stuart_maxwell_test.py --demo --effect-size none
   ```

3. Compare the results:
   - What is the p-value in each case?
   - What is the agreement rate in each case?
   - Which marginal differences are largest?

### Exercise 4: Interpret Real-World Scenarios

For each scenario, predict whether Stuart-Maxwell would be significant:

**Scenario A**: Base model has 85% accuracy, fine-tuned has 85% accuracy, but they disagree on 30% of samples.

**Scenario B**: Base model has 80% accuracy, fine-tuned has 88% accuracy, and they agree on 95% of samples.

**Scenario C**: Both models have 90% accuracy and agree on 98% of samples.

<details>
<summary>Solution</summary>

**Scenario A**: Likely **SIGNIFICANT**. High disagreement rate (30%) with balanced accuracy suggests systematic differences in which samples each model gets right.

**Scenario B**: Likely **NOT SIGNIFICANT**. Despite the accuracy improvement, 95% agreement means the fine-tuned model mostly makes the same predictions. The 8% accuracy gain comes from correcting a small subset of errors.

**Scenario C**: Likely **NOT SIGNIFICANT**. 98% agreement with identical accuracy means almost no change in predictions.

</details>

---

## Key Takeaways

1. **Stuart-Maxwell tests prediction patterns**, not just accuracy
2. It requires **paired data** — both models must classify the same samples
3. A **significant result** means fine-tuning changed behavior; proceed to per-class tests
4. A **non-significant result** means no detectable effect; reconsider your approach
5. The **marginal differences** show which classes shifted most

---

## Common Mistakes

### Mistake 1: Using Unpaired Data
❌ Testing models on different test sets
✅ Both models must predict on the exact same samples

### Mistake 2: Confusing Significance with Improvement
❌ "Significant means the fine-tuned model is better"
✅ Significant only means the models behave differently — could be better or worse

### Mistake 3: Ignoring Non-Significant Results
❌ "Non-significant means the test failed"
✅ Non-significant is a valid finding — fine-tuning had no effect

---

## Next Steps

After completing this tutorial:
1. ✅ You can detect if fine-tuning changed prediction patterns
2. ➡️ Proceed to [Tutorial 03: Per-class Paired t-Tests](TUTORIAL_03_PAIRED_TTESTS.md) to identify which classes changed

---

**Questions?** Open an issue in the project repository with the `curriculum` tag.
