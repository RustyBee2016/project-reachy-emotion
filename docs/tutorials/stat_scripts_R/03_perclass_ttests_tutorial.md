# Tutorial 3: Per-Class Paired t-Tests with Multiple Comparison Correction

## Learning Objectives

By the end of this tutorial, you will understand:
- How to identify which specific emotion classes improved after fine-tuning
- The mathematics behind paired t-tests and why they're appropriate for fold-level data
- Multiple comparison corrections (Benjamini-Hochberg, Bonferroni, Holm)
- Effect size calculations and their practical interpretation
- R programming patterns for statistical diagnostics and robust analysis

## Statistical Background

### What are Per-Class Paired t-Tests?

After the Stuart-Maxwell test tells you that prediction patterns changed, per-class paired t-tests answer: **"WHICH specific emotion classes improved or degraded?"**

This is crucial for emotion classification because:
- Different emotions have different baseline difficulties
- Fine-tuning might help some emotions while hurting others
- You need to know if critical emotions (like neutral) improved

### The Paired Design

**Why "paired"?** Because we compare the same model evaluated on the same cross-validation folds:

```r
# Example: 5-fold cross-validation results
fold_data <- data.frame(
  fold = c(1, 2, 3, 4, 5),
  emotion_class = "anger",
  base_f1 = c(0.82, 0.85, 0.79, 0.83, 0.81),      # Base model F1 scores
  finetuned_f1 = c(0.87, 0.89, 0.84, 0.88, 0.86)  # Fine-tuned model F1 scores
)

# Each fold is a "pair" - same data, two different models
differences <- fold_data$finetuned_f1 - fold_data$base_f1
# [0.05, 0.04, 0.05, 0.05, 0.05] - consistently positive!
```

### Multiple Comparisons Problem

**The Problem**: Testing 8 emotion classes means 8 hypothesis tests. By chance alone, we expect 8 × 0.05 = 0.4 false positives at α = 0.05.

**The Solution**: Adjust p-values to control the False Discovery Rate (FDR) or Family-Wise Error Rate (FWER).

## Script Structure and Key Imports

```r
#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)    # Command-line arguments
  library(jsonlite)    # JSON I/O
  library(ggplot2)     # Static plotting
  library(plotly)      # Interactive visualizations
  library(viridis)     # Color palettes
  library(logger)      # Structured logging
  library(assertthat)  # Input validation
  library(tidyr)       # Data reshaping (pivot_longer, etc.)
  library(dplyr)       # Data manipulation
  library(broom)       # Tidy statistical output
  library(effsize)     # Effect size calculations
})
```

**Key Libraries**:
- **broom**: Converts statistical test results to tidy data frames
- **effsize**: Provides Cohen's d and other effect size measures
- **tidyr/dplyr**: Modern R data manipulation (part of tidyverse)

## Enhanced Paired t-Test Implementation

### Core Statistical Function

```r
enhanced_paired_t_test <- function(base_scores, ft_scores, class_name) {
  log_debug("Running enhanced paired t-test for class: {class_name}")
  
  # Validate inputs
  assert_that(is.numeric(base_scores), is.numeric(ft_scores))
  assert_that(length(base_scores) == length(ft_scores))
  assert_that(length(base_scores) >= 3, msg = "Need at least 3 paired observations")
  
  n <- length(base_scores)
  differences <- ft_scores - base_scores
  
  # Basic statistics
  mean_base <- mean(base_scores, na.rm = TRUE)
  mean_ft <- mean(ft_scores, na.rm = TRUE)
  mean_diff <- mean(differences, na.rm = TRUE)
  sd_diff <- sd(differences, na.rm = TRUE)
  se_diff <- sd_diff / sqrt(n)
  
  # Handle edge case: zero variance
  if (is.na(sd_diff) || sd_diff < 1e-10) {
    log_warn("Zero or near-zero variance in differences for class {class_name}")
    return(create_zero_variance_result(class_name, mean_base, mean_ft, mean_diff, n))
  }
  
  # Perform t-test
  t_stat <- mean_diff / se_diff
  df <- n - 1
  p_value <- 2 * pt(-abs(t_stat), df)  # Two-tailed test
  
  # Confidence interval for mean difference
  t_critical <- qt(0.975, df)
  ci_lower <- mean_diff - t_critical * se_diff
  ci_upper <- mean_diff + t_critical * se_diff
  
  # Effect size (Cohen's d for paired samples)
  cohens_d <- mean_diff / sd_diff
  
  return(list(
    class_name = class_name,
    n_folds = n,
    mean_base = mean_base,
    mean_finetuned = mean_ft,
    mean_difference = mean_diff,
    sd_difference = sd_diff,
    se_difference = se_diff,
    t_statistic = t_stat,
    p_value_raw = p_value,
    df = df,
    ci_lower = ci_lower,
    ci_upper = ci_upper,
    effect_size_cohens_d = cohens_d,
    effect_size_interpretation = interpret_cohens_d(cohens_d)
  ))
}
```

### Understanding the Mathematics

**Paired t-Test Formula**:
```
t = d̄ / (s_d / √n)

where:
- d̄ = mean of differences (fine-tuned - base)
- s_d = standard deviation of differences  
- n = number of pairs (folds)
```

**Why this works**: The t-statistic measures how many standard errors the mean difference is from zero. Large |t| values indicate the difference is unlikely due to chance.

### Effect Size Interpretation

```r
interpret_cohens_d <- function(d) {
  case_when(
    abs(d) < 0.2 ~ "negligible",
    abs(d) < 0.5 ~ "small", 
    abs(d) < 0.8 ~ "medium",
    TRUE ~ "large"
  )
}
```

**Cohen's d Guidelines**:
- **0.2**: Small effect (noticeable to experts)
- **0.5**: Medium effect (visible to informed observers)  
- **0.8**: Large effect (obvious to anyone)

**Example**: If Cohen's d = 0.6 for anger classification, fine-tuning had a "medium" effect on anger detection performance.

## Multiple Comparison Corrections

### Benjamini-Hochberg Procedure (Recommended)

```r
enhanced_multiple_comparison_correction <- function(p_values, alpha = 0.05, method = "BH") {
  m <- length(p_values)
  
  if (method == "BH") {
    # Step 1: Order p-values from smallest to largest
    order_idx <- order(p_values)
    sorted_p <- p_values[order_idx]
    
    # Step 2: Apply BH correction
    adjusted <- numeric(m)
    for (i in seq_len(m)) {
      adjusted[i] <- sorted_p[i] * m / i
    }
    
    # Step 3: Enforce monotonicity (adjusted p-values can't decrease)
    for (i in seq(m - 1, 1)) {
      adjusted[i] <- min(adjusted[i], adjusted[i + 1])
    }
    
    # Step 4: Cap at 1.0 and reorder to original positions
    adjusted <- pmin(adjusted, 1.0)
    adjusted_original <- numeric(m)
    adjusted_original[order_idx] <- adjusted
    
    return(adjusted_original)
  }
  # ... other methods (Bonferroni, Holm)
}
```

### BH Procedure Step-by-Step Example

```r
# Example with 4 emotion classes
raw_p_values <- c(0.001, 0.025, 0.040, 0.080)  # anger, happiness, neutral, sadness
class_names <- c("anger", "happiness", "neutral", "sadness")

# Step 1: Order (already ordered in this example)
# Step 2: Apply correction
# i=1: 0.001 * 4/1 = 0.004
# i=2: 0.025 * 4/2 = 0.050  
# i=3: 0.040 * 4/3 = 0.053
# i=4: 0.080 * 4/4 = 0.080

# Step 3: Enforce monotonicity
# Work backwards: 0.080, min(0.053, 0.080) = 0.053, min(0.050, 0.053) = 0.050, min(0.004, 0.050) = 0.004
adjusted_p_values <- c(0.004, 0.050, 0.053, 0.080)

# Results at α = 0.05:
# anger: 0.004 < 0.05 → SIGNIFICANT
# happiness: 0.050 = 0.05 → BORDERLINE  
# neutral: 0.053 > 0.05 → NOT SIGNIFICANT
# sadness: 0.080 > 0.05 → NOT SIGNIFICANT
```

### Why BH Over Bonferroni?

**Bonferroni**: Multiply each p-value by number of tests
- Very conservative (high Type II error rate)
- Controls Family-Wise Error Rate (FWER)

**Benjamini-Hochberg**: More sophisticated adjustment
- Less conservative (better power)
- Controls False Discovery Rate (FDR)
- Better for exploratory analysis

```r
# Comparison example
raw_p <- c(0.01, 0.02, 0.03, 0.04)

# Bonferroni: multiply by 4
bonf_adj <- raw_p * 4  # [0.04, 0.08, 0.12, 0.16]
# Only first test significant at α = 0.05

# BH: more nuanced
bh_adj <- c(0.04, 0.067, 0.08, 0.16)  # (simplified calculation)
# First two tests significant at α = 0.05
```

## Enhanced Data Processing

### Handling Missing Classes and Insufficient Data

```r
run_enhanced_perclass_tests <- function(df, alpha = 0.05, correction_method = "BH") {
  # Validate input data
  assert_that(is.data.frame(df))
  required_cols <- c("emotion_class", "base_score", "finetuned_score")
  assert_that(all(required_cols %in% names(df)))
  
  # Check for missing classes
  present_classes <- unique(df$emotion_class)
  missing_classes <- setdiff(EMOTION_CLASSES, present_classes)
  if (length(missing_classes) > 0) {
    log_warn("Missing data for classes: {paste(missing_classes, collapse = ', ')}")
  }
  
  # Run tests for each class
  class_results <- list()
  p_values <- numeric(length(EMOTION_CLASSES))
  names(p_values) <- EMOTION_CLASSES
  
  for (cls in EMOTION_CLASSES) {
    class_data <- df[df$emotion_class == cls, ]
    
    if (nrow(class_data) < 3) {
      log_warn("Insufficient data for class {cls}: {nrow(class_data)} observations")
      class_results[[cls]] <- create_insufficient_data_result(cls, nrow(class_data))
      p_values[cls] <- NA
    } else {
      result <- enhanced_paired_t_test(class_data$base_score, class_data$finetuned_score, cls)
      class_results[[cls]] <- result
      p_values[cls] <- result$p_value_raw
    }
  }
  
  # Apply multiple comparison correction to valid p-values
  valid_p_values <- p_values[!is.na(p_values)]
  if (length(valid_p_values) > 0) {
    correction_result <- enhanced_multiple_comparison_correction(valid_p_values, alpha, correction_method)
    
    # Add adjusted p-values and significance to results
    for (cls in names(valid_p_values)) {
      class_results[[cls]]$p_value_adjusted <- correction_result[cls]
      class_results[[cls]]$significant <- correction_result[cls] < alpha
      class_results[[cls]]$direction <- determine_direction(class_results[[cls]])
    }
  }
  
  return(summarize_results(class_results, correction_method, alpha))
}
```

### Direction Classification

```r
determine_direction <- function(result) {
  if (is.na(result$mean_difference)) {
    return("insufficient_data")
  } else if (result$significant) {
    if (result$mean_difference > 0) "improved" else "degraded"
  } else {
    "unchanged"
  }
}
```

## Statistical Diagnostics

### Normality Testing

```r
# Add to enhanced_paired_t_test function
normality_p <- tryCatch({
  if (n <= 50) {
    shapiro.test(differences)$p.value  # Shapiro-Wilk for small samples
  } else {
    # Kolmogorov-Smirnov for larger samples
    ks.test(differences, "pnorm", mean(differences), sd(differences))$p.value
  }
}, error = function(e) NA)
```

**Interpretation**: If normality_p < 0.05, the differences aren't normally distributed. The t-test is robust to mild violations, but severe violations might require non-parametric alternatives.

### Outlier Detection

```r
# IQR method for outlier detection
Q1 <- quantile(differences, 0.25, na.rm = TRUE)
Q3 <- quantile(differences, 0.75, na.rm = TRUE)
IQR <- Q3 - Q1
outliers <- which(differences < (Q1 - 1.5 * IQR) | differences > (Q3 + 1.5 * IQR))
n_outliers <- length(outliers)
```

**Business Value**: Outliers might indicate specific folds where fine-tuning had unusual effects. Worth investigating these cases.

## Enhanced Reporting

### Comprehensive Results Table

```r
print_enhanced_perclass_report <- function(result) {
  cat("--- DETAILED STATISTICAL RESULTS ---\n")
  header <- sprintf("%-12s %8s %8s %8s %8s %10s %10s %12s %8s %10s\n",
                   "Class", "N", "Base", "FT", "Diff", "t-stat", "p-raw", "p-adj", "Sig", "Effect")
  cat(header)
  cat(strrep("-", 110), "\n", sep = "")
  
  # Sort by adjusted p-value for easier interpretation
  valid_results <- result$class_results[!sapply(result$class_results, function(x) is.na(x$p_value_raw))]
  sorted_results <- valid_results[order(sapply(valid_results, function(x) x$p_value_adjusted %||% 1))]
  
  for (res in sorted_results) {
    sig_marker <- if (!is.na(res$significant) && res$significant) "YES ✓" else "no"
    direction_marker <- case_when(
      res$direction == "improved" ~ "↑",
      res$direction == "degraded" ~ "↓", 
      TRUE ~ ""
    )
    
    cat(sprintf("%-12s %8d %8.4f %8.4f %+8.4f %10.3f %10.6f %12.6f %4s %s %8s %s\n",
                res$class_name, res$n_folds, res$mean_base, res$mean_finetuned,
                res$mean_difference, res$t_statistic, res$p_value_raw, res$p_value_adjusted,
                sig_marker, direction_marker, res$effect_size_interpretation,
                if (res$class_name == NEUTRAL_CLASS) "★" else ""))
  }
}
```

**Sample Output**:
```
--- DETAILED STATISTICAL RESULTS ---
Class        N     Base       FT     Diff     t-stat     p-raw        p-adj   Sig   Effect
contempt    10   0.6500   0.7700   +0.1200      4.123   0.002841     0.011364  YES ↑   medium
anger       10   0.8200   0.8400   +0.0200      2.236   0.051847     0.103694   no     small
neutral     10   0.8800   0.9400   +0.0600      3.674   0.005129     0.013677  YES ↑   medium ★
```

### Effect Size Analysis

```r
cat("\n--- EFFECT SIZE ANALYSIS ---\n")
effect_sizes <- sapply(result$class_results, function(x) x$effect_size_cohens_d)
effect_sizes <- effect_sizes[!is.na(effect_sizes)]

if (length(effect_sizes) > 0) {
  cat(sprintf("Mean Effect Size (Cohen's d): %.3f\n", mean(effect_sizes)))
  cat(sprintf("Effect Size Range: [%.3f, %.3f]\n", min(effect_sizes), max(effect_sizes)))
  
  # Effect size distribution
  effect_counts <- table(sapply(result$class_results, function(x) x$effect_size_interpretation))
  for (effect in names(effect_counts)) {
    if (effect != "insufficient_data") {
      cat(sprintf("  %s: %d classes\n", stringr::str_to_title(effect), effect_counts[effect]))
    }
  }
}
```

## Demo Data Generation

### Realistic Fold-Level Metrics

```r
generate_enhanced_demo_metrics <- function(n_folds = 10, effect_pattern = "mixed", seed = 42) {
  set.seed(seed)
  
  # Base performance levels (realistic for emotion classification)
  base_means <- c(
    anger = 0.82, contempt = 0.65, disgust = 0.72, fear = 0.78,
    happiness = 0.90, neutral = 0.88, sadness = 0.84, surprise = 0.80
  )
  
  # Effect patterns for different scenarios
  effects <- switch(effect_pattern,
    none = setNames(rep(0, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_improve = setNames(rep(0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    mixed = c(anger = 0.02, contempt = 0.08, disgust = 0.06, fear = 0.03,
              happiness = -0.02, neutral = 0.04, sadness = 0.01, surprise = 0.02),
    realistic = c(anger = 0.015, contempt = 0.12, disgust = 0.08, fear = 0.025,
                  happiness = -0.015, neutral = 0.06, sadness = 0.02, surprise = 0.03)
  )
  
  # Generate correlated fold-level metrics (more realistic than independent)
  fold_std <- 0.03
  correlation <- 0.3  # Moderate correlation between base and fine-tuned performance
  
  records <- list()
  idx <- 1
  
  for (cls in EMOTION_CLASSES) {
    base_mean <- base_means[cls]
    ft_mean <- base_mean + effects[cls]
    
    # Generate correlated random effects using multivariate normal
    fold_effects <- MASS::mvrnorm(n_folds, mu = c(0, 0), 
                                  Sigma = matrix(c(1, correlation, correlation, 1), 2, 2))
    fold_effects <- fold_effects * fold_std
    
    # Ensure scores stay in [0, 1] range
    base_scores <- pmax(0, pmin(1, base_mean + fold_effects[, 1]))
    ft_scores <- pmax(0, pmin(1, ft_mean + fold_effects[, 2]))
    
    for (fold in seq_len(n_folds)) {
      records[[idx]] <- data.frame(
        fold = fold,
        emotion_class = cls,
        base_score = base_scores[fold],
        finetuned_score = ft_scores[fold],
        stringsAsFactors = FALSE
      )
      idx <- idx + 1
    }
  }
  
  return(do.call(rbind, records))
}
```

**Key Features**:
- **Correlated performance**: Base and fine-tuned scores are correlated (realistic)
- **Bounded scores**: Ensures F1 scores stay in [0, 1] range
- **Configurable patterns**: Test different improvement scenarios

## Command Line Interface

### Usage Examples

```bash
# Demo with different effect patterns
Rscript 03_perclass_paired_ttests_enhanced.R --demo --effect-pattern none        # No improvements
Rscript 03_perclass_paired_ttests_enhanced.R --demo --effect-pattern all_improve # All classes improve
Rscript 03_perclass_paired_ttests_enhanced.R --demo --effect-pattern mixed       # Realistic mixed effects

# Different correction methods
Rscript 03_perclass_paired_ttests_enhanced.R --demo --correction BH         # Benjamini-Hochberg (default)
Rscript 03_perclass_paired_ttests_enhanced.R --demo --correction bonferroni # Conservative
Rscript 03_perclass_paired_ttests_enhanced.R --demo --correction holm       # Holm's method

# Real data analysis
Rscript 03_perclass_paired_ttests_enhanced.R --metrics-csv fold_results.csv --alpha 0.01 --output results

# More folds for higher power
Rscript 03_perclass_paired_ttests_enhanced.R --demo --n-folds 20 --effect-pattern realistic
```

## Practical Exercises

### Exercise 1: Manual t-Test Calculation

Given fold-level F1 scores for anger:
```
Base:       [0.82, 0.85, 0.79, 0.83, 0.81]
Fine-tuned: [0.87, 0.89, 0.84, 0.88, 0.86]
```

Calculate by hand:
1. Mean difference
2. Standard error of differences  
3. t-statistic
4. Degrees of freedom

**Solution**:
```r
base <- c(0.82, 0.85, 0.79, 0.83, 0.81)
ft <- c(0.87, 0.89, 0.84, 0.88, 0.86)
differences <- ft - base  # [0.05, 0.04, 0.05, 0.05, 0.05]

# 1. Mean difference
mean_diff <- mean(differences)  # 0.048

# 2. Standard error
sd_diff <- sd(differences)      # 0.00447
se_diff <- sd_diff / sqrt(5)    # 0.002

# 3. t-statistic  
t_stat <- mean_diff / se_diff   # 24.0

# 4. Degrees of freedom
df <- 5 - 1                     # 4
```

### Exercise 2: Multiple Comparisons

With raw p-values: [0.001, 0.020, 0.035, 0.060, 0.080, 0.120, 0.200, 0.500]

Apply Benjamini-Hochberg correction at α = 0.05:
1. Which tests are significant?
2. What's the estimated FDR?

**Solution**:
```r
raw_p <- c(0.001, 0.020, 0.035, 0.060, 0.080, 0.120, 0.200, 0.500)
m <- length(raw_p)  # 8 tests

# Apply BH correction
bh_adjusted <- numeric(m)
for (i in 1:m) {
  bh_adjusted[i] <- raw_p[i] * m / i
}
# [0.008, 0.080, 0.093, 0.120, 0.128, 0.160, 0.229, 0.500]

# Enforce monotonicity (work backwards)
for (i in (m-1):1) {
  bh_adjusted[i] <- min(bh_adjusted[i], bh_adjusted[i+1])
}
# [0.008, 0.080, 0.093, 0.120, 0.128, 0.160, 0.229, 0.500]

# Significant tests at α = 0.05
significant <- bh_adjusted < 0.05  # Only first test significant
n_significant <- sum(significant)  # 1

# Estimated FDR
fdr_estimate <- n_significant * 0.05 / m  # 0.00625 (0.625%)
```

### Exercise 3: Effect Size Interpretation

If Cohen's d = 0.75 for neutral class improvement:
1. How do you interpret this effect size?
2. What does this mean for the Reachy robot?
3. Is this practically significant?

**Solution**:
```r
cohens_d <- 0.75
# 1. Interpretation: "medium" to "large" effect (between 0.5 and 0.8)
# 2. Robot impact: Substantial improvement in neutral detection
#    - Better baseline for emotion intensity modeling
#    - Reduced false emotional responses to neutral expressions
# 3. Practical significance: Yes, this is a meaningful improvement
#    - Effect size > 0.5 is generally considered practically important
#    - For neutral class, this could significantly improve user experience
```

## Common Pitfalls and Solutions

### 1. Insufficient Folds

**Problem**: Too few cross-validation folds reduce statistical power
```r
# Only 3 folds - very low power to detect differences
fold_data <- data.frame(
  fold = 1:3,
  base_score = c(0.8, 0.82, 0.81),
  finetuned_score = c(0.85, 0.87, 0.86)
)
```

**Solution**: Use at least 5-10 folds for adequate power
```r
# Better: 10 folds provide reasonable power
n_folds <- 10  # Recommended minimum
```

### 2. Ignoring Multiple Comparisons

**Problem**: Testing 8 emotions without correction inflates Type I error
```r
# WRONG: Use raw p-values for multiple tests
significant_classes <- names(raw_p_values)[raw_p_values < 0.05]
```

**Solution**: Always apply multiple comparison correction
```r
# CORRECT: Adjust p-values first
adjusted_p <- p.adjust(raw_p_values, method = "BH")
significant_classes <- names(adjusted_p)[adjusted_p < 0.05]
```

### 3. Misinterpreting Effect Sizes

**Problem**: "Statistically significant" ≠ "practically important"
```r
# Large sample might make tiny differences "significant"
# Cohen's d = 0.05 (negligible) but p < 0.001
```

**Solution**: Always report and interpret effect sizes
```r
if (result$significant && abs(result$effect_size_cohens_d) < 0.2) {
  cat("Statistically significant but negligible effect size\n")
}
```

### 4. Assuming Normality

**Problem**: t-test assumes normally distributed differences
```r
# Check normality assumption
shapiro.test(differences)  # p < 0.05 suggests non-normality
```

**Solution**: Check assumptions and use alternatives if needed
```r
if (normality_p < 0.05 && n_outliers > 0) {
  log_warn("Normality assumption violated - consider robust alternatives")
  # Could use Wilcoxon signed-rank test as alternative
}
```

## Key Takeaways

1. **Paired design is crucial**: Same folds for both models ensure valid comparisons
2. **Multiple comparisons matter**: Always adjust p-values when testing multiple classes
3. **Effect sizes provide context**: Statistical significance without practical importance is misleading
4. **Check assumptions**: Normality and outliers can affect t-test validity
5. **BH correction is often optimal**: Better power than Bonferroni while controlling FDR

## Next Steps

- **Tutorial 4**: Learn the shared utilities that power all these analyses
- **Practice**: Run with your own fold-level metrics
- **Integration**: Combine with Stuart-Maxwell results for complete analysis

Per-class paired t-tests are your precision tool for identifying exactly which emotions benefited from fine-tuning. Master this technique to make data-driven decisions about model improvements!
