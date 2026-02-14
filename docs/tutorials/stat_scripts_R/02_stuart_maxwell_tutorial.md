# Tutorial 2: Stuart-Maxwell Test for Model Comparison

## Learning Objectives

By the end of this tutorial, you will understand:
- How to compare prediction patterns between two models statistically
- The mathematical foundation of the Stuart-Maxwell test
- R programming patterns for contingency table analysis
- How to interpret effect sizes and marginal differences
- When and why to use this test in emotion classification

## Statistical Background

### What is the Stuart-Maxwell Test?

The Stuart-Maxwell test answers this critical question: **"Did fine-tuning systematically change how the model classifies emotions?"**

It's the **multi-class extension of McNemar's test**, designed for comparing two models on the same dataset. Think of it as detecting whether your model's "personality" changed after training.

### Real-World Scenario

```r
# Before fine-tuning: Base model predictions
base_predictions <- c("neutral", "happiness", "anger", "neutral", "sadness")

# After fine-tuning: Same samples, new predictions  
finetuned_predictions <- c("neutral", "surprise", "anger", "sadness", "sadness")

# Question: Did fine-tuning systematically shift prediction patterns?
# Stuart-Maxwell test provides the statistical answer
```

### Key Concepts

**Marginal Homogeneity**: Do both models predict each emotion class with the same frequency?

**Contingency Table**: Cross-tabulation showing agreement/disagreement patterns
```
              Fine-tuned Model
              A  H  N  S  Total
Base    A    [5  1  2  0]   8    ← Base predicted Anger 8 times
Model   H    [0  7  1  1]   9    ← Base predicted Happiness 9 times  
        N    [1  2 15  2]  20    ← Base predicted Neutral 20 times
        S    [0  0  1  6]   7    ← Base predicted Sadness 7 times
       Total  6 10 19  9   44
```

**Diagonal = Agreement**: Both models made same prediction
**Off-diagonal = Disagreement**: Models disagreed

## Script Structure and Imports

```r
#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)    # Command-line arguments
  library(jsonlite)    # JSON I/O
  library(ggplot2)     # Static plots
  library(plotly)      # Interactive visualizations
  library(viridis)     # Color palettes
  library(logger)      # Structured logging
  library(assertthat)  # Input validation
  library(MASS)        # Matrix operations (ginv for singular matrices)
  library(corrplot)    # Correlation visualization
})
```

**Why MASS library?** The Stuart-Maxwell test involves matrix inversion, which can fail if the covariance matrix is singular (non-invertible). `MASS::ginv()` provides a generalized inverse that handles these edge cases.

## Core Statistical Implementation

### Building the Contingency Table

```r
stuart_maxwell_enhanced <- function(base_labels, ft_labels, alpha = 0.05) {
  # Validate inputs first
  base_labels <- validate_emotion_labels(base_labels)
  ft_labels <- validate_emotion_labels(ft_labels)
  assert_that(length(base_labels) == length(ft_labels))
  
  n_samples <- length(base_labels)
  n_classes <- length(EMOTION_CLASSES)
  
  # Build contingency table
  contingency <- table(
    factor(base_labels, levels = EMOTION_CLASSES),
    factor(ft_labels, levels = EMOTION_CLASSES)
  )
  contingency_matrix <- as.matrix(contingency)
  
  return(contingency_matrix)
}
```

**Critical Detail**: Using `factor()` with explicit levels ensures the contingency table is always 8×8, even if some emotions are missing from the data.

### Computing Marginal Differences

```r
# Compute marginal differences d_i = n_{i.} - n_{.i}
row_marginals <- rowSums(contingency_matrix)  # How often base model predicted each class
col_marginals <- colSums(contingency_matrix)  # How often fine-tuned model predicted each class
marginal_diffs <- row_marginals - col_marginals
```

**Interpretation**:
- **Positive difference**: Base model predicted this emotion more often
- **Negative difference**: Fine-tuned model predicted this emotion more often
- **Zero difference**: Both models predicted this emotion equally often

### Example Calculation

```r
# Example contingency table (simplified to 3 emotions)
#           FT_Anger  FT_Happy  FT_Neutral
# Base_Anger    [5      1         2     ]  = 8 total
# Base_Happy    [1      6         2     ]  = 9 total  
# Base_Neutral  [0      2        15     ]  = 17 total
# Totals         6      9        19       = 34 total

row_marginals <- c(8, 9, 17)    # Base model predictions
col_marginals <- c(6, 9, 19)    # Fine-tuned model predictions
marginal_diffs <- c(2, 0, -2)   # Differences

# Interpretation:
# Anger: +2 → Base model predicted anger 2 times more than fine-tuned
# Happy: 0 → Both models predicted happiness equally
# Neutral: -2 → Fine-tuned model predicted neutral 2 times more than base
```

## Covariance Matrix Construction

### The Mathematical Foundation

The Stuart-Maxwell test statistic follows a chi-squared distribution. The covariance matrix V captures the variance and covariance of marginal differences:

```r
# Build covariance matrix (K x K)
V <- matrix(0, nrow = n_classes, ncol = n_classes)
for (i in 1:n_classes) {
  for (j in 1:n_classes) {
    if (i == j) {
      # Diagonal: variance of marginal difference for class i
      V[i, i] <- row_marginals[i] + col_marginals[i] - 2 * contingency_matrix[i, i]
    } else {
      # Off-diagonal: covariance between classes i and j
      V[i, j] <- -(contingency_matrix[i, j] + contingency_matrix[j, i])
    }
  }
}
```

**Why this formula?** 
- **Diagonal elements**: Variance of d_i = Var(n_{i.} - n_{.i})
- **Off-diagonal elements**: Covariance between different marginal differences

### Handling Singular Matrices

```r
# Reduce to (K-1) x (K-1) for non-singularity
V_reduced <- V[-n_classes, -n_classes, drop = FALSE]
d_reduced <- marginal_diffs[-n_classes]

# Robust matrix inversion
tryCatch({
  V_inv <- solve(V_reduced)
}, error = function(e) {
  log_warn("Singular covariance matrix, using generalized inverse")
  V_inv <- MASS::ginv(V_reduced)
})
```

**Why remove last row/column?** The marginal differences sum to zero (constraint), making the full matrix singular. Removing one dimension makes it invertible.

## Test Statistic and P-Value

### Computing the Chi-Squared Statistic

```r
# Stuart-Maxwell test statistic
chi_squared <- as.numeric(t(d_reduced) %*% V_inv %*% d_reduced)
df <- n_classes - 1
p_value <- 1 - pchisq(chi_squared, df)
significant <- p_value < alpha
```

**Mathematical Form**: χ² = d'V⁻¹d where d is the vector of marginal differences and V⁻¹ is the inverse covariance matrix.

### Effect Size Calculation

```r
# Effect size (Cramer's V equivalent for Stuart-Maxwell)
effect_size <- sqrt(chi_squared / (n_samples * (n_classes - 1)))

effect_interpretation <- case_when(
  effect_size < 0.1 ~ "negligible",
  effect_size < 0.3 ~ "small", 
  effect_size < 0.5 ~ "medium",
  TRUE ~ "large"
)
```

**Effect Size Guidelines**:
- **< 0.1**: Negligible practical difference
- **0.1-0.3**: Small but potentially meaningful difference
- **0.3-0.5**: Medium difference worth investigating
- **> 0.5**: Large difference with clear practical implications

## Enhanced Analysis Features

### Agreement Rate Analysis

```r
# Overall agreement
n_agreements <- sum(diag(contingency_matrix))
n_disagreements <- n_samples - n_agreements
agreement_rate <- n_agreements / n_samples

# Per-class agreement rates
class_agreements <- diag(contingency_matrix)
class_totals <- rowSums(contingency_matrix)
class_agreement_rates <- safe_divide(class_agreements, class_totals)
```

**Business Value**: Agreement rate tells you how often the models make the same prediction. High agreement (>90%) suggests fine-tuning had minimal impact.

### Confidence Intervals for Agreement

```r
# Binomial confidence interval for overall agreement rate
agreement_ci <- binom.test(n_agreements, n_samples)$conf.int
```

This provides uncertainty bounds: "We're 95% confident the true agreement rate is between X% and Y%."

## Enhanced Reporting

### Executive Summary Generation

```r
print_enhanced_stuart_maxwell_report <- function(result) {
  cat("--- EXECUTIVE SUMMARY ---\n")
  cat(sprintf("Test Result: %s\n", 
              if (result$significant) "✅ SIGNIFICANT CHANGE" else "❌ NO SIGNIFICANT CHANGE"))
  cat(sprintf("Effect Size: %.4f (%s)\n", result$effect_size, result$effect_interpretation))
  cat(sprintf("Sample Size: %,d\n", result$n_samples))
  cat(sprintf("Overall Agreement: %.2f%% [%.2f%%, %.2f%%] (95%% CI)\n", 
             result$agreement_rate * 100, 
             result$agreement_ci[1] * 100, 
             result$agreement_ci[2] * 100))
}
```

### Detailed Marginal Analysis

```r
cat("\n--- MARGINAL DIFFERENCES ANALYSIS ---\n")
cat("(Positive = base model predicted more; Negative = fine-tuned predicted more)\n")

for (cls in EMOTION_CLASSES) {
  diff <- result$marginal_differences[cls]
  rel_change <- result$class_marginal_shifts[cls] * 100
  agreement <- result$class_agreement_rates[cls] * 100
  
  impact <- if (abs(rel_change) > 10) "HIGH" else 
           if (abs(rel_change) > 5) "MEDIUM" else "LOW"
  direction <- if (diff > 0) "← Base" else if (diff < 0) "→ FT" else "Stable"
  
  cat(sprintf("%-15s %+12.0f %+14.1f%% %11.1f%% %10s %s\n",
              cls, diff, rel_change, agreement, impact, direction))
}
```

**Sample Output**:
```
--- MARGINAL DIFFERENCES ANALYSIS ---
Class           Difference    Rel. Change   Agreement      Impact Direction
anger                   +5          +8.3%       78.2%      MEDIUM ← Base
happiness               -3          -4.2%       85.7%         LOW → FT
neutral                 +2          +1.1%       91.5%         LOW Stable
```

## Advanced Visualizations

### Enhanced Contingency Heatmap

```r
create_enhanced_contingency_heatmap <- function(result, interactive = FALSE) {
  cm <- result$contingency_table
  
  # Convert to long format for ggplot
  cm_df <- expand.grid(
    Base = factor(EMOTION_CLASSES, levels = rev(EMOTION_CLASSES)),
    FT = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES)
  )
  cm_df$Count <- as.vector(cm[nrow(cm):1, ])
  cm_df$Percentage <- cm_df$Count / sum(cm_df$Count) * 100
  cm_df$IsAgreement <- cm_df$Base == cm_df$FT
  
  # Create enhanced plot with statistical annotations
  p <- ggplot(cm_df, aes(x = FT, y = Base, fill = Count)) +
    geom_tile(color = "white", size = 0.8) +
    geom_text(aes(label = sprintf("%d\n(%.1f%%)", Count, Percentage)), 
              color = ifelse(cm_df$Count > max(cm_df$Count) * 0.6, "white", "black"),
              size = 3, fontface = ifelse(cm_df$IsAgreement, "bold", "plain")) +
    scale_fill_viridis_c(name = "Count", option = "plasma", trans = "sqrt") +
    labs(
      title = "Enhanced Prediction Agreement Matrix",
      subtitle = sprintf("χ² = %.4f, p = %.6f | Agreement Rate: %.1f%% | Effect: %s", 
                        result$chi_squared, result$p_value, 
                        result$agreement_rate * 100, result$effect_interpretation),
      x = "Fine-tuned Model Predictions",
      y = "Base Model Predictions"
    )
  
  if (interactive) {
    p <- ggplotly(p, tooltip = c("x", "y", "fill", "text"))
  }
  
  return(p)
}
```

**Design Features**:
- **Square root transformation**: Makes small counts more visible
- **Bold diagonal text**: Highlights agreement cells
- **Statistical subtitle**: Shows key results at a glance
- **Interactive tooltips**: Hover for detailed information

### Marginal Differences Visualization

```r
create_enhanced_marginal_plot <- function(result) {
  # Prepare data
  marg_df <- data.frame(
    Class = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES),
    Difference = as.numeric(result$marginal_differences),
    RelativeChange = as.numeric(result$class_marginal_shifts) * 100,
    Direction = ifelse(result$marginal_differences > 0, "Base More", "FT More"),
    Impact = ifelse(abs(result$class_marginal_shifts * 100) > 10, "High", 
                   ifelse(abs(result$class_marginal_shifts * 100) > 5, "Medium", "Low"))
  )
  
  # Create plot
  p <- ggplot(marg_df, aes(x = reorder(Class, Difference), y = Difference, fill = Direction)) +
    geom_col(alpha = 0.8, color = "black", size = 0.3) +
    geom_hline(yintercept = 0, color = "black", size = 0.8) +
    geom_text(aes(label = sprintf("%.0f\n(%.1f%%)", Difference, RelativeChange)), 
              vjust = ifelse(marg_df$Difference > 0, -0.5, 1.5), size = 3) +
    scale_fill_manual(values = c("Base More" = "#3182bd", "FT More" = "#e6550d")) +
    labs(
      title = "Enhanced Marginal Differences Analysis",
      subtitle = sprintf("Total Absolute Change: %.0f | Significant: %s", 
                        result$marginal_differences_abs_sum,
                        ifelse(result$significant, "Yes", "No")),
      x = "Emotion Class",
      y = "Marginal Difference (Base - Fine-tuned)"
    )
  
  return(p)
}
```

## Demo Data Generation

### Realistic Paired Predictions

```r
generate_enhanced_demo_pairs <- function(n_samples = 2000, effect_size = "medium", seed = 42) {
  set.seed(seed)
  
  # Generate realistic class distribution
  class_weights <- c(0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10)
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = class_weights)
  
  # Base model accuracies (realistic values)
  base_acc <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_acc) <- EMOTION_CLASSES
  
  # Fine-tuned accuracies based on effect size
  effect_multipliers <- switch(effect_size,
    none = rep(0, length(EMOTION_CLASSES)),
    small = c(0.01, 0.03, 0.02, 0.01, -0.01, 0.01, 0.01, 0.01),
    medium = c(0.02, 0.10, 0.08, 0.04, -0.02, 0.03, 0.02, 0.03),
    large = c(0.06, 0.17, 0.13, 0.08, -0.05, 0.05, 0.04, 0.07)
  )
  
  ft_acc <- pmin(0.95, base_acc + effect_multipliers)
  
  # Generate predictions with realistic confusion patterns
  confusion_options <- list(
    anger = c("fear", "disgust"), 
    contempt = c("disgust", "anger"),
    # ... etc for all emotions
  )
  
  # Implementation details for generating correlated predictions...
}
```

**Key Features**:
- **Realistic class distribution**: Reflects actual emotion frequency in datasets
- **Correlated errors**: Models make similar mistakes (more realistic than independent errors)
- **Configurable effect sizes**: Test different scenarios

## Command Line Interface

### Usage Examples

```bash
# Demo with different effect sizes
Rscript 02_stuart_maxwell_enhanced.R --demo --effect-size none     # Should be non-significant
Rscript 02_stuart_maxwell_enhanced.R --demo --effect-size small    # Might be significant
Rscript 02_stuart_maxwell_enhanced.R --demo --effect-size large    # Should be significant

# Real data analysis
Rscript 02_stuart_maxwell_enhanced.R --predictions-csv model_comparison.csv --output results --plot --interactive

# Custom significance level
Rscript 02_stuart_maxwell_enhanced.R --demo --alpha 0.01 --plot
```

## Practical Exercises

### Exercise 1: Manual Calculation

Given this 3×3 contingency table:
```
           FT_A  FT_H  FT_N
Base_A      [4    1    0]   = 5
Base_H      [1    3    1]   = 5  
Base_N      [0    1    4]   = 5
Totals       5    5    5    = 15
```

Calculate:
1. Marginal differences for each class
2. Overall agreement rate
3. Per-class agreement rates

**Solution**:
```r
# Marginal differences
row_marginals <- c(5, 5, 5)  # Base predictions
col_marginals <- c(5, 5, 5)  # Fine-tuned predictions
marginal_diffs <- c(0, 0, 0) # No systematic shifts

# Overall agreement rate
agreements <- 4 + 3 + 4  # Diagonal sum
agreement_rate <- 11/15  # 73.3%

# Per-class agreement rates
class_agreements <- c(4/5, 3/5, 4/5)  # 80%, 60%, 80%
```

### Exercise 2: Effect Size Interpretation

If χ² = 12.5, n = 200, K = 8:
1. Calculate effect size
2. Interpret the magnitude
3. What does this mean practically?

**Solution**:
```r
effect_size <- sqrt(12.5 / (200 * 7))  # 0.095
# Interpretation: Negligible effect (< 0.1)
# Practical meaning: Models are very similar, differences likely due to random variation
```

## Common Pitfalls and Solutions

### 1. Unequal Sample Sizes

**Problem**: Comparing models on different datasets
```r
# WRONG: Different sample sizes
base_preds <- c("anger", "happiness")      # n = 2
ft_preds <- c("anger", "happiness", "neutral")  # n = 3
```

**Solution**: Ensure paired predictions
```r
# CORRECT: Same samples for both models
assert_that(length(base_preds) == length(ft_preds))
```

### 2. Missing Emotion Classes

**Problem**: Some emotions not present in comparison data
```r
# Creates smaller contingency table
table(base_preds, ft_preds)  # Might be 6×6 instead of 8×8
```

**Solution**: Use factor levels
```r
table(factor(base_preds, levels = EMOTION_CLASSES),
      factor(ft_preds, levels = EMOTION_CLASSES))  # Always 8×8
```

### 3. Misinterpreting Non-Significance

**Problem**: "Non-significant means models are identical"
**Correct Interpretation**: "Insufficient evidence of systematic differences"

Non-significance could mean:
- Models truly similar
- Sample size too small to detect differences
- Effect size too small to matter practically

## Key Takeaways

1. **Stuart-Maxwell tests systematic changes**: Not just overall accuracy, but prediction patterns
2. **Effect size matters**: Statistical significance ≠ practical importance
3. **Agreement rate provides context**: High agreement suggests minimal impact from fine-tuning
4. **Marginal differences show direction**: Which emotions shifted and by how much
5. **Visualization aids interpretation**: Heatmaps reveal confusion patterns

## Next Steps

- **Tutorial 3**: Learn per-class paired t-tests to identify specific improvements
- **Practice**: Run with different effect sizes and interpret results
- **Real Analysis**: Compare your own model versions

The Stuart-Maxwell test is your tool for detecting whether fine-tuning fundamentally changed your model's behavior. Master it to make informed decisions about model updates!
