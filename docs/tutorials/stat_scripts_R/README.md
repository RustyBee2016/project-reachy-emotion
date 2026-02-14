# R Statistical Scripts Tutorials for Reachy Emotion Analysis

## Overview

This tutorial series teaches junior data scientists how to understand and use the enhanced R statistical scripts for emotion classification analysis. Each tutorial combines line-by-line syntax explanation with statistical concepts and practical examples.

## Learning Path

### Prerequisites
- Basic R syntax (variables, functions, data frames)
- Elementary statistics (mean, standard deviation, hypothesis testing)
- Understanding of confusion matrices and classification metrics

### Tutorial Sequence

1. **[Tutorial 1: Quality Gate Metrics](01_quality_gate_metrics_tutorial.md)**
   - Learn classification evaluation metrics
   - Understand confusion matrix calculations
   - Master quality gate validation logic

2. **[Tutorial 2: Stuart-Maxwell Test](02_stuart_maxwell_tutorial.md)**
   - Compare prediction patterns between models
   - Understand contingency tables and marginal homogeneity
   - Learn effect size interpretation

3. **[Tutorial 3: Per-Class Paired t-Tests](03_perclass_ttests_tutorial.md)**
   - Identify specific class improvements after fine-tuning
   - Master multiple comparison corrections
   - Understand effect sizes and statistical power

4. **[Tutorial 4: Shared Utilities](04_utils_enhanced_tutorial.md)**
   - Learn robust error handling patterns
   - Understand logging and validation frameworks
   - Master database connectivity and caching

## Emotion Classification Context

These scripts analyze the performance of emotion classification models that predict 8 emotion classes:
- **anger**, **contempt**, **disgust**, **fear**
- **happiness**, **neutral**, **sadness**, **surprise**

The analysis workflow follows this sequence:
1. **Quality Gates** → Validate overall model performance
2. **Stuart-Maxwell** → Detect systematic prediction changes
3. **Per-Class Tests** → Identify which emotions improved/degraded

## Key Statistical Concepts

### Quality Gate Metrics
- **Macro F1**: Average F1 across all classes (≥0.84 required)
- **Balanced Accuracy**: Average recall across classes (≥0.82 required)  
- **F1 Neutral**: F1 for neutral class specifically (≥0.80 required)

### Statistical Tests
- **Stuart-Maxwell Test**: Chi-squared test for marginal homogeneity
- **Paired t-Tests**: Compare means of related samples (fold-level metrics)
- **Multiple Comparisons**: Control false discovery rate when testing multiple classes

### Effect Sizes
- **Cohen's d**: Standardized difference between means
- **Cramer's V**: Effect size for categorical associations
- **Interpretation**: negligible (<0.2), small (0.2-0.5), medium (0.5-0.8), large (>0.8)

## R Programming Patterns

### Common Constructs You'll Learn
```r
# Defensive programming with assertions
assert_that(is.numeric(x), msg = "x must be numeric")

# Safe division avoiding divide-by-zero
safe_divide <- function(num, denom, default = 0) {
  ifelse(denom == 0, default, num / denom)
}

# Structured error handling
tryCatch({
  risky_operation()
}, error = function(e) {
  log_error("Operation failed: {e$message}")
  return(default_value)
})

# Vectorized operations (R's strength)
f1_scores <- 2 * precision * recall / (precision + recall)

# Named lists for organized data
results <- list(
  metrics = computed_metrics,
  gates = gate_results,
  timestamp = Sys.time()
)
```

### Data Science Best Practices
- **Reproducibility**: Use seeds for random operations
- **Validation**: Check inputs before processing
- **Logging**: Track operations for debugging
- **Caching**: Store intermediate results
- **Documentation**: Clear function descriptions

## Running the Scripts

### Basic Usage
```bash
# Quality gate analysis with demo data
Rscript 01_quality_gate_metrics_enhanced.R --demo --plot

# Stuart-Maxwell test with medium effect
Rscript 02_stuart_maxwell_enhanced.R --demo --effect-size medium --plot

# Per-class analysis with mixed effects
Rscript 03_perclass_paired_ttests_enhanced.R --demo --effect-pattern mixed --plot
```

### Production Usage
```bash
# Real data analysis
Rscript 01_quality_gate_metrics_enhanced.R --predictions-csv results/predictions.csv --output results/quality_gates

# Compare two models
Rscript 02_stuart_maxwell_enhanced.R --predictions-csv results/model_comparison.csv --output results/stuart_maxwell

# Analyze fold-level improvements
Rscript 03_perclass_paired_ttests_enhanced.R --metrics-csv results/fold_metrics.csv --correction BH --output results/perclass
```

## Learning Objectives

By completing these tutorials, you will:

1. **Understand Statistical Concepts**
   - Classification metrics and their interpretation
   - Hypothesis testing and p-value interpretation
   - Effect sizes and practical significance
   - Multiple comparison corrections

2. **Master R Programming**
   - Defensive programming with input validation
   - Error handling and logging patterns
   - Vectorized operations for performance
   - Modular code organization

3. **Apply to Real Projects**
   - Evaluate emotion classification models
   - Compare model performance statistically
   - Generate publication-ready reports
   - Create interactive visualizations

## Getting Help

- **Syntax Questions**: Check R documentation with `?function_name`
- **Statistical Concepts**: Refer to the theory sections in each tutorial
- **Debugging**: Enable debug logging with `--log-level DEBUG`
- **Examples**: All tutorials include working code examples

Start with Tutorial 1 to begin your journey into statistical analysis with R!
