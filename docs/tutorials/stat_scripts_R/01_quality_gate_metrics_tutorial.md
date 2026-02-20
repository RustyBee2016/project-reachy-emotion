# Tutorial 1: Quality Gate Metrics Analysis

## Learning Objectives

By the end of this tutorial, you will understand:
- How to calculate classification metrics (F1, precision, recall, balanced accuracy)
- The logic behind quality gate validation for emotion classification
- R programming patterns for robust statistical computing
- How to generate professional reports and visualizations

## Statistical Background

### What are Quality Gates?

Quality gates are **pass/fail thresholds** that determine if an emotion classification model is ready for deployment. Think of them as a **quality control checkpoint** before releasing a model to production.

For the Reachy emotion project, we have three critical metrics:

1. **Macro F1 ≥ 0.84**: Overall classification quality across all emotions
2. **Balanced Accuracy ≥ 0.82**: Protection against class imbalance bias  
3. **F1 Neutral ≥ 0.80**: Critical for Phase 2 baseline (neutral serves as reference point)

### Why These Specific Thresholds?

```r
# These thresholds come from project requirements
QUALITY_GATES <- list(
  macro_f1 = 0.84,           # High enough for reliable emotion detection
  balanced_accuracy = 0.82,  # Ensures all emotions are detected fairly
  f1_neutral = 0.80          # Neutral class is baseline for intensity modeling
)
```

**Real-world impact**: If F1 Neutral drops below 0.80, the robot might misinterpret neutral expressions as emotional, leading to inappropriate responses.

## Script Structure Overview

Let's examine the enhanced quality gate script structure:

```r
#!/usr/bin/env Rscript
# Shebang line - tells system this is an R script

# Load required libraries
suppressPackageStartupMessages({
  library(optparse)    # Command-line argument parsing
  library(jsonlite)    # JSON input/output
  library(ggplot2)     # Static plotting
  library(plotly)      # Interactive visualizations
  library(viridis)     # Color-blind friendly palettes
  library(logger)      # Structured logging
  library(assertthat)  # Input validation
})
```

**Key Pattern**: `suppressPackageStartupMessages()` prevents cluttered output when loading packages.

## Core Data Structures

### Emotion Classes Definition

```r
EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)
```

**Why this order?** It matches the HSEmotion model output indices. The order matters for confusion matrix calculations.

### Configuration Constants

```r
# Script directory detection (works in different execution contexts)
get_script_dir <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_flag <- "--file="
  file_idx <- grep(file_flag, cmd_args)
  if (length(file_idx) > 0) {
    return(dirname(normalizePath(sub(file_flag, "", cmd_args[file_idx]))))
  }
  # Fallback methods...
  getwd()
}
```

**Learning Point**: This function handles different ways R scripts can be executed (Rscript, source(), RStudio, etc.).

## Confusion Matrix Computation

### The Foundation of All Metrics

```r
compute_robust_confusion_matrix <- function(y_true, y_pred) {
  log_debug("Computing confusion matrix for {length(y_true)} samples")
  
  # Input validation - catch errors early!
  assert_that(length(y_true) == length(y_pred))
  assert_that(length(y_true) > 0, msg = "Empty input vectors")
  
  # Validate emotion labels
  y_true <- validate_emotion_labels(y_true)
  y_pred <- validate_emotion_labels(y_pred)
  
  # Create factors with ALL emotion classes (crucial!)
  y_true_factor <- factor(y_true, levels = EMOTION_CLASSES)
  y_pred_factor <- factor(y_pred, levels = EMOTION_CLASSES)
  
  # Compute confusion matrix
  cm <- table(y_true_factor, y_pred_factor)
  cm_matrix <- as.matrix(cm)
  
  return(cm_matrix)
}
```

### Why Use Factors with Levels?

**Problem**: If your test data doesn't contain all emotion classes, `table()` will create a smaller matrix.

```r
# BAD: Missing classes create wrong-sized matrix
y_true <- c("anger", "happiness", "anger")
y_pred <- c("anger", "anger", "happiness")
table(y_true, y_pred)  # Only 2x2 matrix!

# GOOD: Factors ensure 8x8 matrix always
y_true_factor <- factor(y_true, levels = EMOTION_CLASSES)
y_pred_factor <- factor(y_pred, levels = EMOTION_CLASSES)
table(y_true_factor, y_pred_factor)  # Always 8x8 matrix
```

## Metric Calculations

### Safe Division Pattern

```r
safe_divide <- function(numerator, denominator, default_value = 0) {
  # Handle multiple edge cases
  result <- ifelse(is.na(denominator) | denominator == 0, 
                   default_value, 
                   numerator / denominator)
  
  # Handle NaN and Inf cases
  result[is.nan(result) | is.infinite(result)] <- default_value
  return(result)
}
```

**Why needed?** Division by zero crashes programs. In classification metrics:
- Precision = TP / (TP + FP) → undefined if no positive predictions
- Recall = TP / (TP + FN) → undefined if no true positives in data

### Computing Classification Metrics

```r
compute_enhanced_metrics <- function(y_true, y_pred) {
  # Get confusion matrix
  cm <- compute_robust_confusion_matrix(y_true, y_pred)
  
  # Extract basic counts from confusion matrix
  tp <- diag(cm)                    # True positives (diagonal elements)
  fn <- rowSums(cm) - tp           # False negatives (row sum - diagonal)
  fp <- colSums(cm) - tp           # False positives (col sum - diagonal)
  tn <- sum(cm) - (tp + fn + fp)   # True negatives (everything else)
  
  # Compute per-class metrics with safe division
  precision <- safe_divide(tp, tp + fp)
  recall <- safe_divide(tp, tp + fn)
  f1 <- safe_divide(2 * precision * recall, precision + recall)
  
  # Aggregate metrics
  macro_f1 <- mean(f1, na.rm = TRUE)
  balanced_accuracy <- mean(recall, na.rm = TRUE)  # Same as macro recall
  
  return(list(
    macro_f1 = macro_f1,
    balanced_accuracy = balanced_accuracy,
    f1_neutral = f1[NEUTRAL_INDEX],
    per_class = list(
      precision = setNames(precision, EMOTION_CLASSES),
      recall = setNames(recall, EMOTION_CLASSES),
      f1 = setNames(f1, EMOTION_CLASSES)
    ),
    confusion_matrix = cm
  ))
}
```

### Understanding the Math

**Confusion Matrix Layout**:
```
         Predicted
         A  H  N  S
True A  [5  1  0  0]  ← True Anger: 5 correct, 1 confused with Happiness
     H  [0  8  1  0]  ← True Happiness: 8 correct, 1 confused with Neutral  
     N  [0  2  15 1]  ← True Neutral: 15 correct, 2 confused with Happiness
     S  [1  0  0  7]  ← True Sadness: 7 correct, 1 confused with Anger
```

**For Anger class**:
- TP = 5 (correctly predicted anger)
- FN = 1 (anger predicted as happiness) 
- FP = 1 (sadness predicted as anger)
- Precision = 5/(5+1) = 0.833
- Recall = 5/(5+1) = 0.833
- F1 = 2×0.833×0.833/(0.833+0.833) = 0.833

## Quality Gate Evaluation

### Enhanced Gate Logic

```r
evaluate_quality_gates_enhanced <- function(metrics) {
  gates <- list(
    macro_f1 = list(
      value = metrics$macro_f1,
      threshold = QUALITY_GATES$macro_f1,
      passed = metrics$macro_f1 >= QUALITY_GATES$macro_f1,
      margin = metrics$macro_f1 - QUALITY_GATES$macro_f1  # How close to threshold
    ),
    # ... similar for other gates
  )
  
  # Overall pass status
  overall_pass <- all(sapply(gates, function(g) g$passed))
  
  # Identify critical failures (large negative margins)
  critical_failures <- names(gates)[sapply(gates, function(g) 
    !g$passed && g$margin < -0.05)]
  
  return(list(
    gates = gates,
    overall_pass = overall_pass,
    critical_failures = critical_failures
  ))
}
```

**Business Logic**: A "critical failure" is when a metric is >0.05 below threshold, indicating serious model problems.

## Enhanced Reporting

### Executive Summary Generation

```r
print_enhanced_report <- function(metrics, gate_eval, model_name = "model") {
  cat("--- EXECUTIVE SUMMARY ---\n")
  cat(sprintf("Overall Status: %s\n", 
              if (gate_eval$overall_pass) "✅ PASS" else "❌ FAIL"))
  
  # Risk assessment based on margins
  for (gate_name in names(gate_eval$gates)) {
    gate <- gate_eval$gates[[gate_name]]
    risk_level <- if (gate$margin > 0.05) "LOW" else 
                  if (gate$margin > 0) "MEDIUM" else "HIGH"
    
    cat(sprintf("%-25s %10.4f %12.2f %10s %+12.4f %10s\n",
                gate_name, gate$value, gate$threshold, 
                if (gate$passed) "PASS ✓" else "FAIL ✗", 
                gate$margin, risk_level))
  }
}
```

**Output Example**:
```
--- EXECUTIVE SUMMARY ---
Overall Status: ✅ PASS

Metric                    Value    Threshold     Status      Margin       Risk
macro_f1                 0.8567        0.84     PASS ✓     +0.0167        LOW
balanced_accuracy        0.8234        0.82     PASS ✓     +0.0034     MEDIUM
f1_neutral              0.8123        0.80     PASS ✓     +0.0123        LOW
```

## Visualization Creation

### Enhanced Confusion Matrix Heatmap

```r
create_enhanced_confusion_matrix <- function(metrics, output_path = NULL, interactive = FALSE) {
  cm <- metrics$confusion_matrix
  
  # Convert to long format for ggplot
  cm_df <- expand.grid(
    True = factor(EMOTION_CLASSES, levels = rev(EMOTION_CLASSES)),  # Reverse for proper display
    Predicted = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES)
  )
  cm_df$Count <- as.vector(cm[nrow(cm):1, ])  # Reverse rows
  cm_df$Percentage <- cm_df$Count / sum(cm_df$Count) * 100
  
  # Create plot
  p <- ggplot(cm_df, aes(x = Predicted, y = True, fill = Count)) +
    geom_tile(color = "white", size = 0.5) +
    geom_text(aes(label = sprintf("%d\n(%.1f%%)", Count, Percentage)), 
              color = ifelse(cm_df$Count > max(cm_df$Count) * 0.5, "white", "black"),
              size = 3) +
    scale_fill_viridis_c(name = "Count", option = "plasma") +
    theme_minimal()
  
  if (interactive) {
    p <- ggplotly(p)  # Convert to interactive plot
  }
  
  return(p)
}
```

**Design Choices**:
- **Viridis colors**: Color-blind friendly and perceptually uniform
- **White text on dark tiles**: Ensures readability
- **Percentage labels**: Shows relative frequency, not just counts

## Command Line Interface

### Argument Parsing with optparse

```r
main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE, 
                help = "Run with enhanced synthetic demo data"),
    make_option(c("--demo-imbalance"), type = "double", default = 0.3,
                help = "Class imbalance level for demo data (0-1)"),
    make_option(c("--predictions-csv"), type = "character", default = NULL,
                help = "CSV file with y_true,y_pred columns"),
    make_option(c("--output"), type = "character", default = NULL,
                help = "Directory to save enhanced results and plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE,
                help = "Generate enhanced visualizations")
  )
  
  parser <- OptionParser(option_list = option_list)
  args <- parse_args(parser)
  
  # Validation logic
  if (!args$demo && is.null(args$`predictions-csv`)) {
    print_help(parser)
    stop("Provide --demo or --predictions-csv option.")
  }
}
```

### Usage Examples

```bash
# Demo with balanced data
Rscript 01_quality_gate_metrics_enhanced.R --demo

# Demo with class imbalance and noise
Rscript 01_quality_gate_metrics_enhanced.R --demo --demo-imbalance 0.7 --demo-noise 0.2 --plot

# Real data analysis
Rscript 01_quality_gate_metrics_enhanced.R --predictions-csv results/model_predictions.csv --output results/gates --plot --interactive
```

## Practical Exercise

### Exercise 1: Understanding Metrics

Given this confusion matrix for 3 emotions:
```
         Predicted
         A  H  N
True A  [8  1  1]  
     H  [2  7  1]  
     N  [0  2  8]  
```

Calculate by hand:
1. Precision for each class
2. Recall for each class  
3. F1 for each class
4. Macro F1

**Solution**:
```r
# Anger: TP=8, FP=2, FN=2
precision_A <- 8/(8+2)  # 0.8
recall_A <- 8/(8+2)     # 0.8  
f1_A <- 2*0.8*0.8/(0.8+0.8)  # 0.8

# Happiness: TP=7, FP=3, FN=3  
precision_H <- 7/(7+3)  # 0.7
recall_H <- 7/(7+3)     # 0.7
f1_H <- 0.7

# Neutral: TP=8, FP=2, FN=2
precision_N <- 8/(8+2)  # 0.8
recall_N <- 8/(8+2)     # 0.8
f1_N <- 0.8

# Macro F1
macro_f1 <- (0.8 + 0.7 + 0.8) / 3  # 0.767
```

### Exercise 2: Quality Gate Analysis

If macro_f1 = 0.767, balanced_accuracy = 0.767, f1_neutral = 0.8:
1. Which gates pass/fail?
2. What's the risk level for each?
3. What recommendations would you make?

**Solution**:
```r
# Gate evaluation
macro_f1_pass <- 0.767 >= 0.84        # FALSE (margin: -0.073)
balanced_acc_pass <- 0.767 >= 0.82    # FALSE (margin: -0.053)  
f1_neutral_pass <- 0.8 >= 0.80        # TRUE (margin: 0.0)

# Risk levels
# macro_f1: HIGH risk (margin < -0.05)
# balanced_accuracy: HIGH risk (margin < -0.05)
# f1_neutral: MEDIUM risk (margin = 0, just barely passing)

# Recommendations:
# 1. Critical: Address overall classification quality (macro F1)
# 2. Critical: Handle class imbalance (balanced accuracy)  
# 3. Monitor: Neutral class performance is borderline
```

## Common Pitfalls and Solutions

### 1. Missing Emotion Classes in Test Data

**Problem**: Test set doesn't contain all 8 emotions
```r
# This creates a 6x6 matrix instead of 8x8
y_true <- c("anger", "happiness", "neutral")  # Missing 5 emotions
cm_wrong <- table(y_true, y_pred)
```

**Solution**: Always use factor levels
```r
y_true_factor <- factor(y_true, levels = EMOTION_CLASSES)
y_pred_factor <- factor(y_pred, levels = EMOTION_CLASSES)
cm_correct <- table(y_true_factor, y_pred_factor)  # Always 8x8
```

### 2. Division by Zero in Metrics

**Problem**: No predictions for a class leads to 0/0
```r
# If no predictions for "contempt", precision is undefined
precision_contempt <- tp_contempt / (tp_contempt + fp_contempt)  # 0/0 = NaN
```

**Solution**: Use safe division
```r
precision_contempt <- safe_divide(tp_contempt, tp_contempt + fp_contempt, default = 0)
```

### 3. Incorrect Neutral Class Index

**Problem**: Hardcoding neutral index
```r
f1_neutral <- f1_scores[6]  # Assumes neutral is 6th, but what if order changes?
```

**Solution**: Use programmatic lookup
```r
NEUTRAL_INDEX <- which(EMOTION_CLASSES == "neutral")
f1_neutral <- f1_scores[NEUTRAL_INDEX]
```

## Key Takeaways

1. **Input Validation is Critical**: Always validate inputs before processing
2. **Handle Edge Cases**: Use safe division and proper factor levels
3. **Structured Logging**: Log operations for debugging and monitoring
4. **Modular Design**: Separate concerns (computation, validation, reporting)
5. **Professional Output**: Generate reports that stakeholders can understand

## Next Steps

- **Tutorial 2**: Learn how to compare models using the Stuart-Maxwell test
- **Practice**: Run the script with different demo parameters
- **Real Data**: Try analyzing your own classification results

The quality gate script is your first checkpoint in the statistical analysis pipeline. Master it, and you'll have a solid foundation for the more advanced analyses that follow!
