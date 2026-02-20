# Tutorial 05: Visualization

This tutorial covers creating publication-quality plots for statistical analysis results. Good visualizations make your findings clear and compelling.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Create confusion matrix heatmaps
2. Plot F1 score comparisons between models
3. Visualize contingency tables and marginal differences
4. Create effect size plots
5. Understand the style fallback mechanism

---

## Part 1: Setting Up the Style

### The Challenge

Different versions of matplotlib have different style names:
- matplotlib ≥ 3.6: `'seaborn-v0_8-whitegrid'`
- matplotlib < 3.6: `'seaborn-whitegrid'`

### The Solution: Fallback Mechanism

```python
def set_style():
    """Set consistent plot style with version fallback."""
    style_options = [
        'seaborn-v0_8-whitegrid',  # matplotlib >= 3.6
        'seaborn-whitegrid',        # matplotlib < 3.6
        'ggplot',                   # fallback
    ]
    
    for style in style_options:
        try:
            plt.style.use(style)
            return
        except OSError:
            continue
```

This tries each style in order until one works.

### Why This Matters

Without this fallback, your code might crash on different systems:
```python
# Bad: might fail
plt.style.use('seaborn-v0_8-whitegrid')  # OSError on older matplotlib!

# Good: always works
set_style()  # Tries alternatives automatically
```

---

## Part 2: Confusion Matrix Heatmap

### What It Shows

A confusion matrix heatmap uses color intensity to show:
- **Diagonal**: Correct predictions (should be dark/high)
- **Off-diagonal**: Errors (should be light/low)

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_confusion_matrix
from stats.Opus4.5_stats.phase_1 import compute_all_univariate_metrics
import numpy as np

# Create sample data
y_true = np.array([0]*50 + [1]*50)
y_pred = y_true.copy()
y_pred[:5] = 1  # Add some errors
y_pred[50:55] = 0

results = compute_all_univariate_metrics(y_true, y_pred, 2, ["happy", "sad"])

# Create the plot
fig = plot_confusion_matrix(
    results,
    model_name="My Model",
    normalize=False,  # Show counts
    figsize=(8, 6),
    cmap="Blues",
    save_path="confusion_matrix.png"  # Optional: save to file
)
```

### Parameters Explained

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `results` | UnivariateResults from metrics computation | See above |
| `model_name` | Title for the plot | "ResNet-50" |
| `normalize` | Show percentages instead of counts | True/False |
| `figsize` | Figure size in inches (width, height) | (8, 6) |
| `cmap` | Color map name | "Blues", "Greens", "YlOrRd" |
| `save_path` | Path to save the image | "plots/cm.png" |

### Normalized vs. Raw Counts

```python
# Raw counts - shows actual numbers
plot_confusion_matrix(results, normalize=False)

# Output shows:
#     [[45  5]
#      [ 5 45]]

# Normalized - shows percentages
plot_confusion_matrix(results, normalize=True)

# Output shows:
#     [[90%  10%]
#      [10%  90%]]
```

**When to use which:**
- **Raw counts**: When sample size matters
- **Normalized**: When comparing datasets of different sizes

---

## Part 3: F1 Score Comparison

### What It Shows

A grouped bar chart comparing F1 scores between two models for each class.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_f1_comparison

fig = plot_f1_comparison(
    results_a,          # UnivariateResults for Model A
    results_b,          # UnivariateResults for Model B
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    figsize=(10, 6),
    save_path="f1_comparison.png"
)
```

### What You'll See

```
     F1 Score
  1.0 ┤
      │   ████
  0.9 ┤   ████  ████
      │   ████  ████   ████
  0.8 ┤   ████  ████   ████  ████
      │   ████  ████   ████  ████
  0.75┼---████--████---████--████--- F1 Floor (Gate A)
      │   ████  ████   ████  ████
  0.6 ┤   
      └────────────────────────────
          happy           sad
          
      ████ ResNet-50  ████ EfficientNet-B0
```

### Features

- **Red dashed line**: F1 floor threshold (0.75)
- **Value labels**: Exact F1 values on each bar
- **Legend**: Identifies which color is which model

---

## Part 4: Contingency Table Visualization

### What It Shows

A heatmap of the contingency table showing how models agree/disagree.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_contingency_table

fig = plot_contingency_table(
    contingency_table,
    class_names=["happy", "sad"],
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    figsize=(12, 6),
    save_path="contingency.png"
)
```

### Reading the Plot

```
                        Class
                    happy    sad
Both correct        [45]    [42]    <- Good: both right
ResNet ✓, Eff ✗     [ 3]    [ 4]    <- ResNet better
ResNet ✗, Eff ✓     [ 1]    [ 2]    <- EfficientNet better
Both incorrect      [ 1]    [ 2]    <- Bad: both wrong
```

The rows show:
1. Agreement (both correct) — ideally high
2. Model A wins — A got it right when B didn't
3. Model B wins — B got it right when A didn't
4. Agreement (both wrong) — ideally low

---

## Part 5: Marginal Differences Plot

### What It Shows

Two panels from the Stuart-Maxwell test:
1. **Left**: How many times each model predicted each class
2. **Right**: The difference (Model A - Model B)

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_marginal_differences

fig = plot_marginal_differences(
    stuart_maxwell_result,
    class_names=["happy", "sad"],
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    figsize=(10, 6),
    save_path="marginal_diff.png"
)
```

### Interpretation

```
Panel 1: Marginal Counts          Panel 2: Differences
                                  
Count │   ████                    Diff │    ██
 52   │   ████  ████               +3  │    ██ (green)
 51   │   ████  ████                0  ├────────────
 50   │   ████  ████               -3  │        ██ (red)
 49   │   ████  ████  ████              │  
      └───────────────────              └──────────────
          happy    sad                   happy    sad
          
      ████ ResNet  ████ Eff        Green = A predicts more
                                   Red = B predicts more
```

---

## Part 6: Effect Size Plot (Cohen's d)

### What It Shows

A horizontal bar chart showing Cohen's d effect size for each class.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_cohens_d_effect_sizes

fig = plot_cohens_d_effect_sizes(
    paired_results,      # List of PairedTestResult
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    figsize=(10, 6),
    save_path="effect_sizes.png"
)
```

### Reading the Plot

```
            ← Favors B    0    Favors A →
            
sad      ████████████████|███████             d = +0.65
                         |
happy    █████████████████████████████████    d = +1.20
                         |
         |      |        |        |      |
        -0.8   -0.5      0       0.5    0.8
        Large  Medium         Medium  Large
```

- **Green bars**: Significant after BH correction
- **Gray bars**: Not significant
- **Vertical lines**: Effect size thresholds (0.2, 0.5, 0.8)

---

## Part 7: McNemar Results Plot

### What It Shows

A bar chart showing discordant pairs (b and c values) from McNemar's test.

### The Code

```python
from stats.Opus4.5_stats.phase_1 import plot_mcnemar_results

fig = plot_mcnemar_results(
    mcnemar_results,
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    figsize=(10, 6),
    save_path="mcnemar.png"
)
```

### Interpretation

```
Count │            *         <- * indicates significant
  10  │   
   8  │        ████
   6  │   ████ ████
   4  │   ████ ████  ████
   2  │   ████ ████  ████ ████
      └────────────────────────
            happy        sad
            
      ████ ResNet ✓, Eff ✗ (b)
      ████ ResNet ✗, Eff ✓ (c)
```

If b >> c, Model A is significantly better for that class.

---

## Part 8: Creating All Plots at Once

### Using `create_all_plots`

```python
from stats.Opus4.5_stats.phase_1 import create_all_plots

figures = create_all_plots(
    results_a=results_a,
    results_b=results_b,
    contingency_table=ct,
    stuart_maxwell_result=stuart_maxwell_result,
    mcnemar_results=mcnemar_results,
    paired_results=paired_results,
    model_a_name="ResNet-50",
    model_b_name="EfficientNet-B0",
    output_dir="results/plots/",  # Save all plots here
    show_plots=True               # Display interactively
)

# Returns a dictionary of figure objects
print(f"Generated {len(figures)} plots:")
for name in figures:
    print(f"  - {name}")
```

### Output Structure

```
results/plots/
├── confusion_matrix_resnet-50.png
├── confusion_matrix_efficientnet-b0.png
├── f1_comparison.png
├── contingency_table.png
├── marginal_differences.png
├── effect_sizes.png
└── mcnemar_results.png
```

---

## Part 9: Customizing Plots

### Changing Colors

```python
# Different colormaps for confusion matrix
plot_confusion_matrix(results, cmap="Greens")   # Green shades
plot_confusion_matrix(results, cmap="YlOrRd")   # Yellow-Orange-Red
plot_confusion_matrix(results, cmap="viridis")  # Perceptually uniform
```

### Adjusting Figure Size

```python
# Wider plot for many classes
plot_f1_comparison(results_a, results_b, figsize=(14, 6))

# Square plot
plot_confusion_matrix(results, figsize=(8, 8))
```

### Saving in Different Formats

```python
# PNG (default, good for web)
fig.savefig("plot.png", dpi=150)

# PDF (good for publications)
fig.savefig("plot.pdf")

# SVG (scalable, good for presentations)
fig.savefig("plot.svg")
```

### High-Resolution for Publications

```python
fig.savefig("plot.png", dpi=300, bbox_inches='tight')
```

---

## Part 10: Handling Missing Seaborn

The code handles missing seaborn gracefully:

```python
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

# In plotting functions:
if HAS_SEABORN:
    sns.heatmap(...)  # Pretty seaborn heatmap
else:
    ax.imshow(...)    # Basic matplotlib fallback
```

If seaborn isn't installed, plots still work but look simpler.

---

## Complete Example

```python
import numpy as np
from stats.Opus4.5_stats.phase_1 import (
    compute_all_univariate_metrics,
    build_contingency_table,
    stuart_maxwell_test,
    mcnemar_test_per_class,
    cohens_kappa,
    run_per_class_paired_tests,
    create_all_plots
)

# Generate data
np.random.seed(42)
y_true = np.array([0]*100 + [1]*100)
np.random.shuffle(y_true)

pred_a = y_true.copy()
pred_a[np.random.choice(200, 15, replace=False)] = 1 - pred_a[np.random.choice(200, 15, replace=False)]

pred_b = y_true.copy()
pred_b[np.random.choice(200, 25, replace=False)] = 1 - pred_b[np.random.choice(200, 25, replace=False)]

# Compute all statistics
results_a = compute_all_univariate_metrics(y_true, pred_a, 2, ["happy", "sad"])
results_b = compute_all_univariate_metrics(y_true, pred_b, 2, ["happy", "sad"])
ct = build_contingency_table(y_true, pred_a, pred_b, 2)
sm_result = stuart_maxwell_test(pred_a, pred_b, 2)
mcnemar = mcnemar_test_per_class(ct, ["happy", "sad"])

# Paired tests (need fold data)
f1_a = {0: np.array([0.87, 0.86, 0.88, 0.85, 0.87]),
        1: np.array([0.84, 0.85, 0.86, 0.83, 0.85])}
f1_b = {0: np.array([0.82, 0.81, 0.83, 0.80, 0.82]),
        1: np.array([0.80, 0.81, 0.82, 0.79, 0.81])}
paired = run_per_class_paired_tests(f1_a, f1_b, ["happy", "sad"])

# Create all plots
figures = create_all_plots(
    results_a, results_b, ct, sm_result, mcnemar, paired,
    "Model A", "Model B",
    output_dir="my_results/plots/",
    show_plots=False  # Don't display, just save
)

print(f"Saved {len(figures)} plots to my_results/plots/")
```

---

## Tips for Publication-Quality Figures

### 1. Use Consistent Sizing

```python
# Standard sizes for different contexts
SINGLE_COLUMN = (3.5, 3)    # Journal single column
DOUBLE_COLUMN = (7, 4)      # Journal double column  
PRESENTATION = (10, 6)      # PowerPoint slides
```

### 2. Font Sizes

```python
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
})
```

### 3. Color Accessibility

Use colorblind-friendly palettes:
```python
# Good options:
cmap = "viridis"    # Perceptually uniform
cmap = "cividis"    # Colorblind-safe
```

---

## Summary

| Function | Creates |
|----------|---------|
| `plot_confusion_matrix` | Heatmap of confusion matrix |
| `plot_f1_comparison` | Grouped bar chart of F1 scores |
| `plot_contingency_table` | Heatmap of agreement/disagreement |
| `plot_marginal_differences` | Stuart-Maxwell visualization |
| `plot_cohens_d_effect_sizes` | Horizontal bar chart of effect sizes |
| `plot_mcnemar_results` | Bar chart of discordant pairs |
| `create_all_plots` | All of the above in one call |

---

## Self-Check Questions

1. When should you use normalized vs. raw confusion matrix?
2. What do the b and c values represent in the McNemar plot?
3. Why does the code have a style fallback mechanism?
4. How would you save a high-resolution figure for a journal?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 06: Running the Full Analysis Pipeline**.
