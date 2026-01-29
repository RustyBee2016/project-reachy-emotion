# Tutorial 03: Per-Class Paired t-Tests with Benjamini-Hochberg Correction

**Module**: Phase 1 Statistical Analysis  
**Duration**: 3-4 hours  
**Difficulty**: Intermediate  
**Script**: `stats/scripts/03_perclass_paired_ttests.py`

---

## Table of Contents

1. [Introduction](#introduction)
2. [When to Use Per-Class Tests](#when-to-use-per-class-tests)
3. [Understanding Paired t-Tests](#understanding-paired-t-tests)
4. [The Multiple Comparison Problem](#the-multiple-comparison-problem)
5. [Benjamini-Hochberg Correction](#benjamini-hochberg-correction)
6. [Script Walkthrough](#script-walkthrough)
7. [Output Interpretation](#output-interpretation)
8. [Practice Exercises](#practice-exercises)

---

## Introduction

After the Stuart-Maxwell test tells you that fine-tuning changed prediction patterns, you need to answer the next question:

> **WHICH emotion classes improved or degraded?**

Per-class paired t-tests answer this by comparing F1 scores for each emotion class across cross-validation folds.

### The Analysis Pipeline

```
Stuart-Maxwell: "Something changed"
        │
        ▼
Per-class t-tests: "HERE'S what changed"
        │
        ├── Contempt improved (+0.08)
        ├── Disgust improved (+0.06)
        ├── Neutral improved (+0.04) ← Important for Phase 2!
        └── Happiness degraded (-0.02)
```

---

## When to Use Per-Class Tests

### Use Per-Class Tests When:
- ✅ Stuart-Maxwell test was **significant**
- ✅ You have **fold-level metrics** (F1 per fold per class)
- ✅ You want to know **which classes** changed

### Don't Use Per-Class Tests When:
- ❌ Stuart-Maxwell was not significant (nothing to diagnose)
- ❌ You only have aggregate metrics (no fold breakdown)
- ❌ You're comparing different test sets (use unpaired tests)

### In Your Project Workflow

```
┌─────────────────────────────────────────┐
│  Stuart-Maxwell Test: SIGNIFICANT       │
│  "Fine-tuning changed predictions"      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Per-Class Paired t-Tests               │◄── YOU ARE HERE
│  "Which classes changed?"               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Actionable Insights                    │
│  - Contempt improved: synthetic helped  │
│  - Neutral improved: Phase 2 ready      │
│  - Happiness degraded: investigate      │
└─────────────────────────────────────────┘
```

---

## Understanding Paired t-Tests

### Tier 1: Middle School Explanation

Let's say the Stuart-Maxwell test told you "these two robots sort photos differently." But now you want to know: **Which emotions did they disagree about?**

You run a mini-test for each emotion separately. "Did the robots differ on happy faces? What about sad? Angry?" Each emotion gets its own test.

**The "paired" part is important.** Imagine you gave both robots the same 5 quizzes (folds). For each quiz, you recorded how well each robot did on "happy" faces:

```
         Quiz 1   Quiz 2   Quiz 3   Quiz 4   Quiz 5
Robot A:   82%      79%      84%      81%      80%
Robot B:   85%      83%      86%      84%      82%
Difference: +3%     +4%      +2%      +3%      +2%
```

The paired t-test asks: "Is the average difference (+2.8%) big enough to be real, or could it be luck?"

Because we're comparing the **same quizzes**, we can see that Robot B consistently does a little better. If we had different quizzes for each robot, we couldn't tell if differences were due to the robots or the quizzes.

### Tier 2: College Freshman (CS) Explanation

A **paired t-test** compares the mean difference between two related groups. Since both models are evaluated on the same cross-validation folds, the observations are **paired** — fold 1's base model F1 and fold 1's fine-tuned F1 come from the exact same test samples.

```python
# For each emotion class:
differences = [ft_f1[fold] - base_f1[fold] for fold in range(k)]
mean_diff = np.mean(differences)
std_diff = np.std(differences, ddof=1)

# t-statistic
t_stat = mean_diff / (std_diff / np.sqrt(k))

# p-value (two-tailed)
p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=k-1))
```

**Why paired?** Pairing removes fold-to-fold variability. Some folds are harder than others (different test samples). By comparing the same fold across models, we isolate the model effect from the fold effect.

**Unpaired alternative:** If we used an unpaired test, we'd be comparing "base model on fold 1" vs "fine-tuned model on fold 3" — mixing model differences with fold differences.

### Tier 3: Graduate Data Science Explanation

For class $c$, let $F1_c^{(k, \text{base})}$ and $F1_c^{(k, \text{ft})}$ denote the F1 scores for fold $k$ under the base and fine-tuned models, respectively.

**Paired differences:**
$$D_c^{(k)} = F1_c^{(k, \text{ft})} - F1_c^{(k, \text{base})}$$

**Mean and standard deviation of differences:**
$$\bar{D}_c = \frac{1}{K} \sum_{k=1}^{K} D_c^{(k)}$$
$$s_{D_c} = \sqrt{\frac{1}{K-1} \sum_{k=1}^{K} (D_c^{(k)} - \bar{D}_c)^2}$$

**Paired t-statistic:**
$$t_c = \frac{\bar{D}_c}{s_{D_c} / \sqrt{K}}$$

Under $H_0: \mu_{D_c} = 0$, the statistic $t_c \sim t(K-1)$.

**Two-tailed p-value:**
$$p_c = 2 \cdot P(T > |t_c|) \text{ where } T \sim t(K-1)$$

**Assumptions:**
- Differences are approximately normally distributed (robust with K ≥ 10 by CLT)
- Observations within each fold are independent
- Folds are identically distributed

---

## The Multiple Comparison Problem

### Tier 1: Middle School Explanation

Here's a problem: You're running 8 tests (one per emotion). Even if there's NO real difference, sometimes you get a "yes" just by luck. It's like flipping coins — flip enough times and you'll get heads eventually.

If each test has a 5% chance of a false alarm, running 8 tests gives you about a **34% chance** of at least one false alarm!

```
1 test:  5% chance of false positive
8 tests: 34% chance of at least one false positive
```

That's way too high. We need a stricter grading rule.

### Tier 2: College Freshman (CS) Explanation

When you run multiple hypothesis tests, the probability of at least one false positive (Type I error) increases:

$$\text{FWER} = 1 - (1 - \alpha)^m$$

For $m = 8$ tests at $\alpha = 0.05$:
$$\text{FWER} = 1 - (0.95)^8 \approx 0.34$$

This is called the **Family-Wise Error Rate (FWER)** — the probability of making at least one false discovery across all tests.

**Options for correction:**

| Method | Controls | Strictness |
|--------|----------|------------|
| Bonferroni | FWER | Very strict (α/m per test) |
| Holm | FWER | Less strict than Bonferroni |
| Benjamini-Hochberg | FDR | Least strict, most power |

We use **Benjamini-Hochberg** because:
1. It's less conservative than Bonferroni (won't miss real effects)
2. It controls **False Discovery Rate (FDR)** — the expected proportion of false positives among rejected hypotheses
3. It's appropriate for exploratory analysis where some false discoveries are tolerable

### Tier 3: Graduate Data Science Explanation

The **False Discovery Rate (FDR)** is defined as:

$$\text{FDR} = \mathbb{E}\left[\frac{V}{R \vee 1}\right]$$

where:
- $V$ = number of false positives (incorrectly rejected null hypotheses)
- $R$ = total number of rejections
- $R \vee 1 = \max(R, 1)$ to avoid division by zero

FDR controls the **expected proportion** of false discoveries, not the probability of any false discovery (FWER).

**Comparison:**
- FWER = P(V ≥ 1) — probability of at least one false positive
- FDR = E[V/R] — expected fraction of false positives among rejections

FDR is less conservative because it allows some false positives as long as they're a small fraction of total discoveries. This is appropriate when:
- You're doing exploratory analysis
- False positives can be caught in follow-up validation
- Missing true effects (false negatives) is costly

---

## Benjamini-Hochberg Correction

### Tier 1: Middle School Explanation

The Benjamini-Hochberg correction is like a stricter grading rule that accounts for how many tests you ran.

**The procedure:**
1. Line up all your p-values from smallest to largest
2. The smallest p-value gets compared to a strict threshold
3. Each larger p-value gets compared to a slightly looser threshold
4. Find the cutoff point where p-values are too big

It's like grading on a curve, but the curve gets stricter the more tests you run.

### Tier 2: College Freshman (CS) Explanation

**Benjamini-Hochberg Procedure:**

1. **Sort p-values** from smallest to largest: $p_{(1)} \leq p_{(2)} \leq \cdots \leq p_{(m)}$

2. **Find the threshold**: For each rank $i$, compute the threshold $\frac{i}{m} \cdot \alpha$

3. **Find the cutoff**: Find the largest $k$ such that $p_{(k)} \leq \frac{k}{m} \cdot \alpha$

4. **Reject**: Reject all hypotheses with rank $\leq k$

**Example with 8 tests at α = 0.05:**

| Rank | Class | Raw p-value | Threshold (i/8 × 0.05) | Reject? |
|------|-------|-------------|------------------------|---------|
| 1 | contempt | 0.002 | 0.00625 | ✓ Yes |
| 2 | disgust | 0.008 | 0.01250 | ✓ Yes |
| 3 | neutral | 0.023 | 0.01875 | ✗ No (0.023 > 0.01875) |
| 4 | fear | 0.045 | 0.02500 | ✗ No |
| ... | ... | ... | ... | ... |

The cutoff is at rank 2, so we reject contempt and disgust only.

**Adjusted p-values** are computed so you can compare directly to α:
$$p_{\text{adj}(i)} = \min\left(p_{(i)} \cdot \frac{m}{i}, 1\right)$$

With monotonicity enforcement (adjusted p-values are non-decreasing).

### Tier 3: Graduate Data Science Explanation

The Benjamini-Hochberg procedure guarantees:

$$\text{FDR} \leq \frac{m_0}{m} \cdot \alpha \leq \alpha$$

where $m_0$ is the number of true null hypotheses.

**Adjusted p-values** allow direct comparison to α:

$$\tilde{p}_{(i)} = \min_{j \geq i} \left\{ \min\left( p_{(j)} \cdot \frac{m}{j}, 1 \right) \right\}$$

The inner minimum enforces monotonicity: if $p_{(i)} < p_{(j)}$ for $i < j$, then $\tilde{p}_{(i)} \leq \tilde{p}_{(j)}$.

**Properties:**
- Controls FDR at level α under independence or positive regression dependence (PRDS)
- More powerful than Bonferroni (rejects more true alternatives)
- Adjusted p-values can be interpreted as "the smallest FDR at which this hypothesis would be rejected"

**Implementation:**
```python
def benjamini_hochberg(p_values, alpha=0.05):
    m = len(p_values)
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]
    
    # Compute adjusted p-values
    adjusted = np.zeros(m)
    for i in range(m):
        adjusted[i] = sorted_p[i] * m / (i + 1)
    
    # Enforce monotonicity (backwards pass)
    for i in range(m - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
    
    # Cap at 1.0 and reorder
    adjusted = np.minimum(adjusted, 1.0)
    adjusted_original = np.zeros(m)
    adjusted_original[sorted_indices] = adjusted
    
    return adjusted_original, adjusted_original < alpha
```

---

## Script Walkthrough

### File Location
```
stats/scripts/03_perclass_paired_ttests.py
```

### Running the Script

**Demo mode (synthetic data):**
```bash
python stats/scripts/03_perclass_paired_ttests.py --demo
```

**Demo with no effect:**
```bash
python stats/scripts/03_perclass_paired_ttests.py --demo --effect-pattern none
```

**With real fold metrics:**
```bash
python stats/scripts/03_perclass_paired_ttests.py --metrics results/fold_metrics.json
```

### Input Data Format

The script expects a JSON file with fold-level F1 scores:

```json
{
  "base_metrics": {
    "anger": [0.82, 0.84, 0.81, 0.83, 0.80, ...],
    "contempt": [0.65, 0.68, 0.63, 0.67, 0.64, ...],
    ...
  },
  "finetuned_metrics": {
    "anger": [0.84, 0.86, 0.83, 0.85, 0.82, ...],
    "contempt": [0.73, 0.76, 0.71, 0.75, 0.72, ...],
    ...
  }
}
```

Each list contains K values (one per fold).

### Key Code Sections

#### 1. Paired t-Test Implementation (Lines 75-115)

```python
def paired_t_test(
    base_scores: np.ndarray,
    finetuned_scores: np.ndarray
) -> Tuple[float, float, float, float, float]:
    """
    Perform paired t-test for a single emotion class.
    
    t = d̄ / (s_d / √n)
    """
    differences = finetuned_scores - base_scores
    
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)  # Bessel's correction
    n = len(differences)
    
    # Compute t-statistic
    t_stat = mean_diff / (std_diff / np.sqrt(n))
    
    # Two-tailed p-value
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))
    
    return mean_diff, std_diff, t_stat, p_value, np.mean(base_scores), np.mean(finetuned_scores)
```

#### 2. Benjamini-Hochberg Correction (Lines 118-165)

```python
def benjamini_hochberg_correction(p_values: np.ndarray, alpha: float = 0.05):
    """
    Apply Benjamini-Hochberg procedure for multiple comparison correction.
    """
    m = len(p_values)
    sorted_indices = np.argsort(p_values)
    sorted_p_values = p_values[sorted_indices]
    
    # Compute adjusted p-values
    adjusted = np.zeros(m)
    for i in range(m):
        rank = i + 1
        adjusted[i] = sorted_p_values[i] * m / rank
    
    # Enforce monotonicity
    for i in range(m - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
    
    # Cap at 1.0 and reorder
    adjusted = np.minimum(adjusted, 1.0)
    adjusted_original_order = np.zeros(m)
    adjusted_original_order[sorted_indices] = adjusted
    
    significant = adjusted_original_order < alpha
    
    return adjusted_original_order, significant
```

#### 3. Main Analysis Function (Lines 168-230)

```python
def run_perclass_paired_ttests(
    base_metrics: Dict[str, List[float]],
    finetuned_metrics: Dict[str, List[float]],
    alpha: float = 0.05
) -> PairedTTestsResult:
    """
    Run paired t-tests for all emotion classes with BH correction.
    """
    # Run t-test for each class
    raw_p_values = []
    for cls in EMOTION_CLASSES:
        _, _, _, p_value, _, _ = paired_t_test(
            np.array(base_metrics[cls]),
            np.array(finetuned_metrics[cls])
        )
        raw_p_values.append(p_value)
    
    # Apply BH correction
    adjusted_p_values, significant_mask = benjamini_hochberg_correction(
        np.array(raw_p_values), alpha
    )
    
    # Build results...
```

---

## Output Interpretation

### Sample Output

```
======================================================================
PER-CLASS PAIRED T-TESTS: Fine-Tuning Effect Analysis
======================================================================

--- TEST OVERVIEW ---
Question: Which emotion classes changed significantly after fine-tuning?
Number of folds: 10
Number of classes tested: 8
Significance level (α): 0.05
Multiple comparison correction: Benjamini-Hochberg

--- SUMMARY ---
Significant changes: 3 / 8 classes
  - Improved: 3 classes
  - Degraded: 0 classes
  - Unchanged: 5 classes

Improved classes: contempt, disgust, neutral

--- DETAILED RESULTS ---
Class        Base F1    FT F1       Diff     t-stat       p-raw      p-adj     Sig?
------------------------------------------------------------------------------------------
contempt      0.6523    0.7312    +0.0789      4.234    0.002145   0.017160   YES ✓ ↑
disgust       0.7234    0.7856    +0.0622      3.567    0.006234   0.024936   YES ✓ ↑
neutral       0.8812    0.9156    +0.0344      2.891    0.017823   0.047528   YES ✓ ↑
fear          0.7823    0.8034    +0.0211      1.456    0.178234   0.356468   no
anger         0.8234    0.8389    +0.0155      1.123    0.289456   0.463130   no
sadness       0.8456    0.8534    +0.0078      0.567    0.583234   0.777645   no
surprise      0.7623    0.7712    +0.0089      0.612    0.554123   0.777645   no
happiness     0.9012    0.8923    -0.0089     -0.678    0.512345   0.777645   no

--- INTERPRETATION ---
Fine-tuning produced significant changes in 3 class(es):
  • contempt: improved by 12.1% (F1: 0.652 → 0.731)
  • disgust: improved by 8.6% (F1: 0.723 → 0.786)
  • neutral: improved by 3.9% (F1: 0.881 → 0.916)

→ IMPORTANT: Neutral class improved, strengthening Phase 2 baseline.
```

### How to Read This Output

1. **Summary**: 3 out of 8 classes showed significant changes after BH correction. All 3 were improvements.

2. **Detailed Results Table**:
   - **Base F1 / FT F1**: Mean F1 across folds for each model
   - **Diff**: Mean difference (positive = improvement)
   - **t-stat**: Test statistic (larger magnitude = stronger evidence)
   - **p-raw**: Uncorrected p-value
   - **p-adj**: BH-adjusted p-value (compare to α)
   - **Sig?**: Whether p-adj < α

3. **Interpretation**: 
   - Contempt improved most (+12.1%) — synthetic data helped this underrepresented class
   - Neutral improved (+3.9%) — important for Phase 2 baseline
   - Happiness slightly degraded but not significantly

### Decision Logic

```
IF significant improvements in target classes:
    → Fine-tuning succeeded for those classes
    → Consider generating more synthetic data for unchanged classes

IF significant degradation in any class:
    → Investigate synthetic data quality for that class
    → Consider class-specific fine-tuning strategies

IF neutral improved:
    → Phase 2 baseline is strengthened
    → Proceed with confidence to intensity modeling

IF neutral degraded:
    → WARNING: Phase 2 baseline may be compromised
    → Prioritize neutral class improvement before Phase 2
```

---

## Practice Exercises

### Exercise 1: Manual BH Correction

Given these raw p-values for 5 tests at α = 0.05:

| Test | Raw p-value |
|------|-------------|
| A | 0.012 |
| B | 0.045 |
| C | 0.003 |
| D | 0.089 |
| E | 0.021 |

Apply Benjamini-Hochberg correction and determine which tests are significant.

<details>
<summary>Solution</summary>

**Step 1: Sort by p-value**

| Rank | Test | Raw p | Threshold (i/5 × 0.05) |
|------|------|-------|------------------------|
| 1 | C | 0.003 | 0.010 |
| 2 | A | 0.012 | 0.020 |
| 3 | E | 0.021 | 0.030 |
| 4 | B | 0.045 | 0.040 |
| 5 | D | 0.089 | 0.050 |

**Step 2: Find cutoff**
- Rank 1: 0.003 ≤ 0.010 ✓
- Rank 2: 0.012 ≤ 0.020 ✓
- Rank 3: 0.021 ≤ 0.030 ✓
- Rank 4: 0.045 > 0.040 ✗ (STOP)

**Step 3: Reject ranks 1-3**
- Significant: C, A, E
- Not significant: B, D

**Adjusted p-values:**
- C: 0.003 × 5/1 = 0.015
- A: 0.012 × 5/2 = 0.030
- E: 0.021 × 5/3 = 0.035
- B: 0.045 × 5/4 = 0.056
- D: 0.089 × 5/5 = 0.089

</details>

### Exercise 2: Run the Demo

1. Run with mixed effects:
   ```bash
   python stats/scripts/03_perclass_paired_ttests.py --demo --effect-pattern mixed
   ```

2. Run with no effects:
   ```bash
   python stats/scripts/03_perclass_paired_ttests.py --demo --effect-pattern none
   ```

3. Compare:
   - How many classes are significant in each case?
   - What happens to the adjusted p-values when there's no effect?

### Exercise 3: Interpret Real-World Scenarios

**Scenario**: After fine-tuning, you get these results:

| Class | Base F1 | FT F1 | p-adj | Significant? |
|-------|---------|-------|-------|--------------|
| neutral | 0.85 | 0.82 | 0.032 | Yes |
| contempt | 0.60 | 0.72 | 0.008 | Yes |
| happiness | 0.92 | 0.91 | 0.456 | No |

What actions would you take?

<details>
<summary>Solution</summary>

**Analysis:**
1. **Neutral degraded significantly** (0.85 → 0.82, p = 0.032)
   - This is a WARNING for Phase 2
   - The baseline for intensity modeling is weaker

2. **Contempt improved significantly** (0.60 → 0.72, p = 0.008)
   - Synthetic data helped this underrepresented class
   - This is a positive outcome

3. **Happiness unchanged** (0.92 → 0.91, not significant)
   - No meaningful change
   - Already performing well

**Recommended Actions:**
1. **Do NOT proceed to Phase 2** until neutral is addressed
2. Investigate why neutral degraded:
   - Were synthetic neutral samples low quality?
   - Did fine-tuning cause neutral → other class confusion?
3. Consider class-weighted fine-tuning to protect neutral
4. Generate more high-quality synthetic neutral samples

</details>

### Exercise 4: Power Analysis

With K = 5 folds, you have limited statistical power. Calculate the minimum detectable effect size.

For a paired t-test with K = 5, α = 0.05, and 80% power, the minimum detectable effect size (Cohen's d) is approximately 1.4.

If your fold-to-fold standard deviation is 0.03, what's the minimum F1 difference you can reliably detect?

<details>
<summary>Solution</summary>

Cohen's d = mean_difference / std_difference

With d = 1.4 and std = 0.03:
mean_difference = d × std = 1.4 × 0.03 = 0.042

**You can reliably detect F1 differences of ≥ 0.042 (4.2 percentage points).**

Smaller differences may exist but won't reach significance with only 5 folds. Consider using K = 10 folds for better power.

</details>

---

## Key Takeaways

1. **Paired tests** are more powerful because they control for fold-to-fold variation
2. **Multiple comparison correction** is essential when testing multiple classes
3. **Benjamini-Hochberg** controls FDR, balancing power and false discovery risk
4. **Adjusted p-values** can be compared directly to α
5. **Neutral class results** are especially important for Phase 2

---

## Common Mistakes

### Mistake 1: Skipping Correction
❌ "I'll just use raw p-values"
✅ Always apply BH correction when testing multiple hypotheses

### Mistake 2: Using Unpaired Tests
❌ Using independent samples t-test on fold data
✅ Use paired t-test because the same folds are used for both models

### Mistake 3: Over-interpreting Non-Significant Results
❌ "Non-significant means no difference"
✅ Non-significant means we can't detect a difference — it might exist but be too small

### Mistake 4: Ignoring Effect Size
❌ Only reporting p-values
✅ Report both p-values and effect sizes (F1 differences)

---

## Summary: The Complete Analysis Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  1. QUALITY GATES (Script 01)                                   │
│     - Evaluate base model against thresholds                    │
│     - Must pass: Macro F1 ≥ 0.84, Balanced Acc ≥ 0.82,         │
│                  F1 Neutral ≥ 0.80                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. STUART-MAXWELL TEST (Script 02)                             │
│     - Compare base vs. fine-tuned prediction patterns           │
│     - Significant → proceed to per-class analysis               │
│     - Not significant → fine-tuning had no effect               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. PER-CLASS PAIRED T-TESTS (Script 03)                        │
│     - Identify which classes improved/degraded                  │
│     - Apply Benjamini-Hochberg correction                       │
│     - Pay special attention to neutral class                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. ACTIONABLE INSIGHTS                                         │
│     - Improved classes: synthetic data helped                   │
│     - Degraded classes: investigate and fix                     │
│     - Neutral status: determines Phase 2 readiness              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After completing this tutorial:
1. ✅ You can identify which emotion classes changed after fine-tuning
2. ✅ You understand the complete Phase 1 statistical analysis pipeline
3. ➡️ Apply these methods to your actual model comparison
4. ➡️ Use insights to guide synthetic data generation for the next iteration

---

**Questions?** Open an issue in the project repository with the `curriculum` tag.
