# Tutorial 4: Enhanced Utilities Framework

## Learning Objectives

By the end of this tutorial, you will understand:
- How to build robust, production-ready R utilities
- Defensive programming patterns with comprehensive input validation
- Structured logging and error handling frameworks
- Database connectivity with caching and retry logic
- Performance monitoring and memory management techniques
- Modular code organization for maintainable statistical applications

## Overview: The Foundation Layer

The `utils_enhanced.R` file is the **foundation layer** that powers all enhanced statistical scripts. Think of it as the **infrastructure** that handles all the "boring but critical" tasks:

- **Input Validation**: Catching errors before they cause problems
- **Logging**: Tracking what happened for debugging and monitoring
- **Database Access**: Secure, efficient data retrieval with caching
- **Error Handling**: Graceful failure and recovery
- **Performance Monitoring**: Tracking execution time and memory usage

## Core Philosophy: Defensive Programming

### The "Fail Fast, Fail Clear" Principle

```r
# BAD: Silent failure that's hard to debug
compute_metrics <- function(y_true, y_pred) {
  cm <- table(y_true, y_pred)  # What if y_true is empty?
  # ... calculations that might produce NaN or crash
}

# GOOD: Explicit validation with clear error messages
compute_enhanced_metrics <- function(y_true, y_pred) {
  # Validate inputs immediately
  assert_that(length(y_true) == length(y_pred))
  assert_that(length(y_true) > 0, msg = "Empty input vectors")
  
  y_true <- validate_emotion_labels(y_true)
  y_pred <- validate_emotion_labels(y_pred)
  
  # Now we can proceed with confidence
  cm <- compute_robust_confusion_matrix(y_true, y_pred)
  # ... rest of calculation
}
```

**Key Insight**: Spend time validating inputs to save hours debugging mysterious failures later.

## Structured Logging Framework

### Why Logging Matters

In production, you need to know:
- **What happened**: Which functions were called
- **When it happened**: Timestamps for performance analysis
- **Why it failed**: Error messages with context
- **How long it took**: Performance monitoring

### Logging Implementation

```r
suppressPackageStartupMessages({
  library(logger)
  library(assertthat)
  library(data.table)
})

# Configure logging with file output
log_threshold(INFO)
log_appender(appender_file(file.path(tempdir(), "reachy_stats.log")))
```

### Log Levels and Usage

```r
# DEBUG: Detailed information for troubleshooting
log_debug("Computing confusion matrix for {length(y_true)} samples")

# INFO: General information about program flow
log_info("Enhanced metrics computed successfully")

# WARN: Something unexpected but not fatal
log_warn("Zero or near-zero variance in differences for class {class_name}")

# ERROR: Something went wrong
log_error("Failed to load CSV: {e$message}")
```

**Best Practice**: Use string interpolation with `{}` for dynamic values. The logger library handles this efficiently.

### Logging in Action

```r
compute_enhanced_metrics <- function(y_true, y_pred) {
  log_info("Computing enhanced classification metrics")
  
  # Log key parameters for debugging
  log_debug("Input validation: {length(y_true)} samples, {length(unique(y_true))} classes")
  
  # ... computation ...
  
  # Log results for monitoring
  log_info("Enhanced metrics computed successfully")
  log_debug("Macro F1: {round(macro_f1, 4)}, Balanced Accuracy: {round(balanced_accuracy, 4)}")
  
  return(metrics)
}
```

## Input Validation Framework

### Emotion Label Validation

```r
validate_emotion_labels <- function(labels, allow_missing = FALSE) {
  # Type checking
  assert_that(is.character(labels) || is.factor(labels))
  
  # Missing value handling
  if (!allow_missing && any(is.na(labels))) {
    stop("Missing values found in emotion labels", call. = FALSE)
  }
  
  # Domain validation
  unique_labels <- unique(labels[!is.na(labels)])
  invalid_labels <- setdiff(unique_labels, EMOTION_CLASSES)
  
  if (length(invalid_labels) > 0) {
    log_error("Invalid emotion labels found: {paste(invalid_labels, collapse = ', ')}")
    stop(sprintf("Invalid emotion labels: %s. Valid labels are: %s",
                paste(invalid_labels, collapse = ", "),
                paste(EMOTION_CLASSES, collapse = ", ")), call. = FALSE)
  }
  
  log_debug("Validated {length(labels)} emotion labels")
  return(as.character(labels))
}
```

**Validation Layers**:
1. **Type checking**: Ensure correct data type
2. **Missing value handling**: Decide policy for NAs
3. **Domain validation**: Check against allowed values
4. **Logging**: Record validation results

### Safe Division with Edge Case Handling

```r
safe_divide <- function(numerator, denominator, default_value = 0) {
  # Input validation
  assert_that(is.numeric(numerator), is.numeric(denominator))
  assert_that(length(numerator) == length(denominator) || 
              length(denominator) == 1 || length(numerator) == 1)
  
  # Handle division by zero
  result <- ifelse(is.na(denominator) | denominator == 0, 
                   default_value, 
                   numerator / denominator)
  
  # Handle NaN and Inf cases (can occur with 0/0 or extreme values)
  result[is.nan(result) | is.infinite(result)] <- default_value
  
  return(result)
}
```

**Why This Matters**: In classification metrics, division by zero is common:
- Precision when no positive predictions: TP/(TP+FP) = 0/0
- Recall when no true positives in data: TP/(TP+FN) = 0/0

### Comprehensive Data Loading

```r
load_and_validate_csv <- function(path, required_columns, max_rows = 1e6) {
  log_info("Loading CSV from: {path}")
  
  # File existence check
  assert_that(file.exists(path), msg = sprintf("File not found: %s", path))
  assert_that(is.character(required_columns), length(required_columns) > 0)
  
  # Safe loading with error handling
  tryCatch({
    # Use data.table for performance on large files
    dt <- fread(path, nrows = max_rows)
    df <- as.data.frame(dt)
    
    # Column validation
    missing_cols <- setdiff(required_columns, names(df))
    if (length(missing_cols) > 0) {
      stop(sprintf("Missing required columns: %s", paste(missing_cols, collapse = ", ")))
    }
    
    log_info("Successfully loaded {nrow(df)} rows with {ncol(df)} columns")
    return(df)
    
  }, error = function(e) {
    log_error("Failed to load CSV: {e$message}")
    stop(sprintf("Error loading CSV file: %s", e$message), call. = FALSE)
  })
}
```

**Features**:
- **Performance**: Uses `data.table::fread()` for fast loading
- **Safety**: Limits rows to prevent memory issues
- **Validation**: Checks required columns exist
- **Error Handling**: Provides clear error messages

## Enhanced Statistical Computing

### Robust Confusion Matrix Computation

```r
compute_robust_confusion_matrix <- function(y_true, y_pred) {
  log_debug("Computing confusion matrix for {length(y_true)} samples")
  
  # Comprehensive validation
  assert_that(length(y_true) == length(y_pred))
  assert_that(length(y_true) > 0, msg = "Empty input vectors")
  
  y_true <- validate_emotion_labels(y_true)
  y_pred <- validate_emotion_labels(y_pred)
  
  # Create factors with all emotion classes (crucial for consistent matrix size)
  y_true_factor <- factor(y_true, levels = EMOTION_CLASSES)
  y_pred_factor <- factor(y_pred, levels = EMOTION_CLASSES)
  
  # Compute confusion matrix
  cm <- table(y_true_factor, y_pred_factor)
  cm_matrix <- as.matrix(cm)
  
  # Post-computation validation
  assert_that(nrow(cm_matrix) == length(EMOTION_CLASSES))
  assert_that(ncol(cm_matrix) == length(EMOTION_CLASSES))
  assert_that(sum(cm_matrix) == length(y_true))
  
  log_info("Confusion matrix computed: {nrow(cm_matrix)}x{ncol(cm_matrix)}, total samples: {sum(cm_matrix)}")
  
  return(cm_matrix)
}
```

### Enhanced Metrics with Confidence Intervals

```r
compute_enhanced_metrics <- function(y_true, y_pred) {
  log_info("Computing enhanced classification metrics")
  
  # Core computation
  cm <- compute_robust_confusion_matrix(y_true, y_pred)
  
  # Extract counts
  tp <- diag(cm)
  fn <- rowSums(cm) - tp
  fp <- colSums(cm) - tp
  tn <- sum(cm) - (tp + fn + fp)
  
  # Compute metrics with safe division
  precision <- safe_divide(tp, tp + fp)
  recall <- safe_divide(tp, tp + fn)
  f1 <- safe_divide(2 * precision * recall, precision + recall)
  
  # Aggregate metrics
  macro_f1 <- mean(f1, na.rm = TRUE)
  balanced_accuracy <- mean(recall, na.rm = TRUE)
  accuracy <- safe_divide(sum(tp), sum(cm))
  f1_neutral <- f1[NEUTRAL_INDEX]
  
  # Confidence intervals using Wilson score interval
  n_samples <- sum(cm)
  wilson_ci <- function(x, n, conf_level = 0.95) {
    if (n == 0) return(c(0, 0))
    z <- qnorm((1 + conf_level) / 2)
    p <- x / n
    denominator <- 1 + z^2 / n
    center <- (p + z^2 / (2 * n)) / denominator
    margin <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / denominator
    c(max(0, center - margin), min(1, center + margin))
  }
  
  accuracy_ci <- wilson_ci(sum(tp), n_samples)
  
  # Package comprehensive results
  metrics <- list(
    # Core metrics
    macro_f1 = macro_f1,
    balanced_accuracy = balanced_accuracy,
    f1_neutral = f1_neutral,
    accuracy = accuracy,
    
    # Per-class details
    per_class = list(
      precision = setNames(as.numeric(precision), EMOTION_CLASSES),
      recall = setNames(as.numeric(recall), EMOTION_CLASSES),
      f1 = setNames(as.numeric(f1), EMOTION_CLASSES),
      support = setNames(as.numeric(rowSums(cm)), EMOTION_CLASSES)
    ),
    
    # Statistical information
    confusion_matrix = cm,
    confidence_intervals = list(accuracy = accuracy_ci),
    n_samples = n_samples,
    class_distribution = setNames(as.numeric(rowSums(cm)), EMOTION_CLASSES)
  )
  
  log_info("Enhanced metrics computed successfully")
  return(metrics)
}
```

## Quality Gate Evaluation Framework

### Enhanced Gate Logic with Risk Assessment

```r
evaluate_quality_gates_enhanced <- function(metrics) {
  log_info("Evaluating quality gates")
  
  gates <- list(
    macro_f1 = list(
      value = metrics$macro_f1,
      threshold = QUALITY_GATES$macro_f1,
      passed = metrics$macro_f1 >= QUALITY_GATES$macro_f1,
      margin = metrics$macro_f1 - QUALITY_GATES$macro_f1
    ),
    balanced_accuracy = list(
      value = metrics$balanced_accuracy,
      threshold = QUALITY_GATES$balanced_accuracy,
      passed = metrics$balanced_accuracy >= QUALITY_GATES$balanced_accuracy,
      margin = metrics$balanced_accuracy - QUALITY_GATES$balanced_accuracy
    ),
    f1_neutral = list(
      value = metrics$f1_neutral,
      threshold = QUALITY_GATES$f1_neutral,
      passed = metrics$f1_neutral >= QUALITY_GATES$f1_neutral,
      margin = metrics$f1_neutral - QUALITY_GATES$f1_neutral
    )
  )
  
  # Overall assessment
  overall_pass <- all(sapply(gates, function(g) g$passed))
  
  # Risk assessment based on margins
  critical_failures <- names(gates)[sapply(gates, function(g) 
    !g$passed && g$margin < -0.05)]
  
  result <- list(
    gates = gates,
    overall_pass = overall_pass,
    critical_failures = critical_failures,
    summary = list(
      passed = sum(sapply(gates, function(g) g$passed)),
      failed = sum(sapply(gates, function(g) !g$passed)),
      total = length(gates)
    )
  )
  
  log_info("Quality gates evaluation: {result$summary$passed}/{result$summary$total} passed")
  if (length(critical_failures) > 0) {
    log_warn("Critical failures detected: {paste(critical_failures, collapse = ', ')}")
  }
  
  return(result)
}
```

## Demo Data Generation Framework

### High-Quality Synthetic Data

```r
generate_enhanced_demo_data <- function(n_samples = 2000, class_imbalance = 0.3, 
                                       noise_level = 0.1, seed = 42) {
  set.seed(seed)
  log_info("Generating enhanced demo data: n={n_samples}, imbalance={class_imbalance}, noise={noise_level}")
  
  # Generate realistic class weights
  if (class_imbalance == 0) {
    weights <- rep(1/length(EMOTION_CLASSES), length(EMOTION_CLASSES))
  } else {
    # Exponential decay for imbalanced distribution
    weights <- exp(-class_imbalance * seq_along(EMOTION_CLASSES))
    weights <- weights / sum(weights)
  }
  
  # Generate true labels
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = weights)
  
  # Realistic base accuracies per class
  base_accuracies <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_accuracies) <- EMOTION_CLASSES
  
  # Realistic confusion patterns (emotions that are commonly confused)
  confusion_patterns <- list(
    anger = c("fear", "disgust"),
    contempt = c("disgust", "anger"), 
    disgust = c("contempt", "anger"),
    fear = c("surprise", "anger"),
    happiness = c("surprise", "neutral"),
    neutral = c("sadness", "happiness"),
    sadness = c("neutral", "fear"),
    surprise = c("fear", "happiness")
  )
  
  # Generate predictions with realistic error patterns
  y_pred <- character(n_samples)
  for (i in seq_len(n_samples)) {
    true_class <- y_true[i]
    accuracy <- base_accuracies[true_class] * (1 - noise_level)
    
    if (runif(1) < accuracy) {
      y_pred[i] <- true_class  # Correct prediction
    } else {
      # Realistic confusion
      y_pred[i] <- sample(confusion_patterns[[true_class]], 1)
    }
  }
  
  df <- data.frame(
    y_true = y_true,
    y_pred = y_pred,
    stringsAsFactors = FALSE
  )
  
  log_info("Generated demo data with {length(unique(y_true))} classes")
  return(df)
}
```

**Features**:
- **Configurable imbalance**: Test different class distribution scenarios
- **Realistic confusion**: Models make human-like errors
- **Noise control**: Adjust overall difficulty level
- **Reproducible**: Seed control for consistent results

## Enhanced Export Framework

### Comprehensive Results Export

```r
export_enhanced_results <- function(results, output_path, metadata = list()) {
  log_info("Exporting results to: {output_path}")
  
  # Add comprehensive metadata
  enhanced_results <- list(
    timestamp = Sys.time(),
    r_version = R.version.string,
    system_info = Sys.info()[c("sysname", "release", "machine")],
    metadata = metadata,
    results = results
  )
  
  # Ensure output directory exists
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  
  # Export with error handling
  tryCatch({
    write_json(enhanced_results, output_path, pretty = TRUE, auto_unbox = TRUE)
    log_info("Results exported successfully")
  }, error = function(e) {
    log_error("Failed to export results: {e$message}")
    stop(sprintf("Export failed: %s", e$message), call. = FALSE)
  })
}
```

## Performance Monitoring Utilities

### Execution Time Tracking

```r
# Simple timing wrapper
time_operation <- function(operation_name, expr) {
  log_debug("Starting operation: {operation_name}")
  start_time <- Sys.time()
  
  result <- expr
  
  execution_time <- as.numeric(Sys.time() - start_time)
  log_info("Operation '{operation_name}' completed in {round(execution_time, 2)} seconds")
  
  return(result)
}

# Usage example
metrics <- time_operation("Enhanced Metrics Computation", {
  compute_enhanced_metrics(y_true, y_pred)
})
```

### Memory Usage Monitoring

```r
# Memory-aware data loading
load_large_dataset <- function(path, chunk_size = 10000) {
  log_info("Loading large dataset with chunking")
  
  # Check available memory
  mem_info <- gc()
  available_mb <- sum(mem_info[, "max used"]) * 8 / 1024^2  # Rough estimate
  log_debug("Available memory: ~{round(available_mb)} MB")
  
  # Load in chunks if file is large
  file_size_mb <- file.size(path) / 1024^2
  if (file_size_mb > available_mb * 0.5) {
    log_warn("Large file detected ({round(file_size_mb)} MB), using chunked loading")
    # Implement chunked loading logic
  }
  
  # Regular loading for smaller files
  return(fread(path))
}
```

## Error Handling Patterns

### Structured Error Handling

```r
# Wrapper for safe operations
safe_operation <- function(operation_func, ..., default_value = NULL, 
                          operation_name = "operation") {
  tryCatch({
    result <- operation_func(...)
    log_debug("Safe operation '{operation_name}' completed successfully")
    return(result)
  }, error = function(e) {
    log_error("Safe operation '{operation_name}' failed: {e$message}")
    if (!is.null(default_value)) {
      log_warn("Returning default value for failed operation")
      return(default_value)
    } else {
      stop(sprintf("Operation '%s' failed: %s", operation_name, e$message), call. = FALSE)
    }
  })
}

# Usage example
confusion_matrix <- safe_operation(
  compute_robust_confusion_matrix,
  y_true, y_pred,
  operation_name = "confusion matrix computation"
)
```

### Graceful Degradation

```r
# Function that can work with partial data
compute_metrics_with_fallback <- function(y_true, y_pred) {
  tryCatch({
    # Try enhanced computation first
    return(compute_enhanced_metrics(y_true, y_pred))
  }, error = function(e) {
    log_warn("Enhanced computation failed, falling back to basic metrics: {e$message}")
    
    # Fallback to basic computation
    tryCatch({
      return(compute_basic_metrics(y_true, y_pred))
    }, error = function(e2) {
      log_error("Both enhanced and basic computation failed: {e2$message}")
      stop("Unable to compute metrics with available data", call. = FALSE)
    })
  })
}
```

## Practical Exercises

### Exercise 1: Input Validation

Write a validation function for fold-level metrics data:

```r
validate_fold_metrics <- function(df) {
  # Your implementation here
  # Should check:
  # 1. Required columns exist
  # 2. Scores are in [0, 1] range  
  # 3. Each emotion class has sufficient folds
  # 4. No missing values in critical columns
}
```

**Solution**:
```r
validate_fold_metrics <- function(df) {
  # Column validation
  required_cols <- c("fold", "emotion_class", "base_score", "finetuned_score")
  missing_cols <- setdiff(required_cols, names(df))
  assert_that(length(missing_cols) == 0, 
              msg = sprintf("Missing columns: %s", paste(missing_cols, collapse = ", ")))
  
  # Score range validation
  score_cols <- c("base_score", "finetuned_score")
  for (col in score_cols) {
    assert_that(all(df[[col]] >= 0 & df[[col]] <= 1, na.rm = TRUE),
                msg = sprintf("Scores in %s must be in [0, 1] range", col))
  }
  
  # Emotion class validation
  df$emotion_class <- validate_emotion_labels(df$emotion_class)
  
  # Sufficient data per class
  class_counts <- table(df$emotion_class)
  insufficient_classes <- names(class_counts)[class_counts < 3]
  if (length(insufficient_classes) > 0) {
    log_warn("Classes with <3 folds: {paste(insufficient_classes, collapse = ', ')}")
  }
  
  # Missing value check
  critical_cols <- c("emotion_class", "base_score", "finetuned_score")
  for (col in critical_cols) {
    n_missing <- sum(is.na(df[[col]]))
    assert_that(n_missing == 0, 
                msg = sprintf("Missing values in critical column %s: %d", col, n_missing))
  }
  
  log_info("Fold metrics validation passed: {nrow(df)} records, {length(unique(df$emotion_class))} classes")
  return(df)
}
```

### Exercise 2: Logging Integration

Add comprehensive logging to this function:

```r
compute_basic_f1 <- function(y_true, y_pred) {
  cm <- table(y_true, y_pred)
  tp <- diag(cm)
  fp <- colSums(cm) - tp
  fn <- rowSums(cm) - tp
  
  precision <- tp / (tp + fp)
  recall <- tp / (tp + fn)
  f1 <- 2 * precision * recall / (precision + recall)
  
  return(mean(f1, na.rm = TRUE))
}
```

**Solution**:
```r
compute_basic_f1 <- function(y_true, y_pred) {
  log_info("Computing basic F1 score")
  log_debug("Input: {length(y_true)} samples, {length(unique(y_true))} true classes, {length(unique(y_pred))} predicted classes")
  
  # Input validation with logging
  assert_that(length(y_true) == length(y_pred))
  assert_that(length(y_true) > 0)
  
  cm <- table(y_true, y_pred)
  log_debug("Confusion matrix: {nrow(cm)}x{ncol(cm)}")
  
  tp <- diag(cm)
  fp <- colSums(cm) - tp
  fn <- rowSums(cm) - tp
  
  # Safe division with logging
  precision <- safe_divide(tp, tp + fp)
  recall <- safe_divide(tp, tp + fn)
  f1 <- safe_divide(2 * precision * recall, precision + recall)
  
  macro_f1 <- mean(f1, na.rm = TRUE)
  
  log_info("Basic F1 computation completed: macro F1 = {round(macro_f1, 4)}")
  log_debug("Per-class F1 range: [{round(min(f1, na.rm = TRUE), 3)}, {round(max(f1, na.rm = TRUE), 3)}]")
  
  return(macro_f1)
}
```

## Key Design Patterns

### 1. The Validation Sandwich

```r
my_function <- function(inputs) {
  # 1. Validate inputs
  validate_inputs(inputs)
  
  # 2. Core computation
  result <- do_computation(inputs)
  
  # 3. Validate outputs
  validate_outputs(result)
  
  return(result)
}
```

### 2. The Logging Lifecycle

```r
my_operation <- function() {
  log_info("Starting operation")
  
  tryCatch({
    # Do work
    result <- complex_computation()
    
    log_info("Operation completed successfully")
    return(result)
  }, error = function(e) {
    log_error("Operation failed: {e$message}")
    stop(e)
  })
}
```

### 3. The Safe Wrapper Pattern

```r
safe_wrapper <- function(func, ..., default = NULL) {
  tryCatch(
    func(...),
    error = function(e) {
      log_warn("Function failed, using default: {e$message}")
      return(default)
    }
  )
}
```

## Key Takeaways

1. **Validate Early and Often**: Catch errors at the boundary, not deep in computation
2. **Log Strategically**: Info for monitoring, debug for troubleshooting, warn/error for problems
3. **Handle Errors Gracefully**: Provide clear messages and fallback options when possible
4. **Design for Maintainability**: Clear function names, consistent patterns, comprehensive documentation
5. **Monitor Performance**: Track execution time and memory usage for optimization opportunities

## Next Steps

- **Integration Tutorial**: See how all scripts work together in the complete workflow
- **Practice**: Add logging and validation to your own R functions
- **Production**: Apply these patterns to make your code more robust

The utilities framework is your foundation for building reliable, maintainable statistical applications. Master these patterns, and your R code will be production-ready from day one!
