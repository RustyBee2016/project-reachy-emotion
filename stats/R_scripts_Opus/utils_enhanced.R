#!/usr/bin/env Rscript
#' Enhanced Statistical Utilities for Reachy Emotion Analysis
#' 
#' This module provides robust statistical computing, error handling, and 
#' data validation utilities for emotion classification analysis.
#' 
#' @author Reachy Emotion Team - Opus Enhancement
#' @version 2.0.0

suppressPackageStartupMessages({
  library(DBI)
  library(RPostgres)
  library(glue)
  library(yaml)
  library(jsonlite)
  library(logger)
  library(assertthat)
  library(data.table)
})

# Configure logging
log_threshold(INFO)
log_appender(appender_file(file.path(tempdir(), "reachy_stats.log")))

#' Emotion class constants
EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)

NEUTRAL_CLASS <- "neutral"
NEUTRAL_INDEX <- which(EMOTION_CLASSES == NEUTRAL_CLASS)

#' Quality gate thresholds
QUALITY_GATES <- list(
  macro_f1 = 0.84,
  balanced_accuracy = 0.82,
  f1_neutral = 0.80
)

#' Safe division with proper handling of edge cases
#' @param numerator Numeric vector of numerators
#' @param denominator Numeric vector of denominators
#' @param default_value Value to return when denominator is 0 or NA
#' @return Numeric vector of division results
safe_divide <- function(numerator, denominator, default_value = 0) {
  assert_that(is.numeric(numerator), is.numeric(denominator))
  assert_that(length(numerator) == length(denominator) || 
              length(denominator) == 1 || length(numerator) == 1)
  
  result <- ifelse(is.na(denominator) | denominator == 0, 
                   default_value, 
                   numerator / denominator)
  
  # Handle NaN and Inf cases
  result[is.nan(result) | is.infinite(result)] <- default_value
  return(result)
}

#' Validate emotion class labels
#' @param labels Character vector of emotion labels
#' @param allow_missing Logical, whether to allow missing values
#' @return Validated labels or throws error
validate_emotion_labels <- function(labels, allow_missing = FALSE) {
  assert_that(is.character(labels) || is.factor(labels))
  
  if (!allow_missing && any(is.na(labels))) {
    stop("Missing values found in emotion labels", call. = FALSE)
  }
  
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

#' Compute robust confusion matrix with comprehensive validation
#' @param y_true True labels
#' @param y_pred Predicted labels
#' @return Confusion matrix as numeric matrix
compute_robust_confusion_matrix <- function(y_true, y_pred) {
  log_debug("Computing confusion matrix for {length(y_true)} samples")
  
  # Validate inputs
  assert_that(length(y_true) == length(y_pred))
  assert_that(length(y_true) > 0, msg = "Empty input vectors")
  
  y_true <- validate_emotion_labels(y_true)
  y_pred <- validate_emotion_labels(y_pred)
  
  # Create factors with all emotion classes to ensure complete matrix
  y_true_factor <- factor(y_true, levels = EMOTION_CLASSES)
  y_pred_factor <- factor(y_pred, levels = EMOTION_CLASSES)
  
  # Compute confusion matrix
  cm <- table(y_true_factor, y_pred_factor)
  cm_matrix <- as.matrix(cm)
  
  # Validate matrix properties
  assert_that(nrow(cm_matrix) == length(EMOTION_CLASSES))
  assert_that(ncol(cm_matrix) == length(EMOTION_CLASSES))
  assert_that(sum(cm_matrix) == length(y_true))
  
  log_info("Confusion matrix computed: {nrow(cm_matrix)}x{ncol(cm_matrix)}, total samples: {sum(cm_matrix)}")
  
  return(cm_matrix)
}

#' Compute comprehensive classification metrics with statistical rigor
#' @param y_true True labels
#' @param y_pred Predicted labels
#' @return List of metrics with confidence intervals where applicable
compute_enhanced_metrics <- function(y_true, y_pred) {
  log_info("Computing enhanced classification metrics")
  
  # Compute confusion matrix
  cm <- compute_robust_confusion_matrix(y_true, y_pred)
  
  # Extract basic counts
  tp <- diag(cm)
  fn <- rowSums(cm) - tp
  fp <- colSums(cm) - tp
  tn <- sum(cm) - (tp + fn + fp)
  
  # Compute per-class metrics with safe division
  precision <- safe_divide(tp, tp + fp)
  recall <- safe_divide(tp, tp + fn)
  f1 <- safe_divide(2 * precision * recall, precision + recall)
  
  # Compute aggregate metrics
  macro_f1 <- mean(f1, na.rm = TRUE)
  macro_precision <- mean(precision, na.rm = TRUE)
  macro_recall <- mean(recall, na.rm = TRUE)
  balanced_accuracy <- macro_recall  # Balanced accuracy = macro recall
  
  # Overall accuracy
  accuracy <- safe_divide(sum(tp), sum(cm))
  
  # Neutral class F1
  f1_neutral <- f1[NEUTRAL_INDEX]
  
  # Compute confidence intervals for key metrics (using bootstrap approximation)
  n_samples <- sum(cm)
  
  # Wilson score interval for proportions
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
  
  # Package results
  metrics <- list(
    # Core quality gate metrics
    macro_f1 = macro_f1,
    balanced_accuracy = balanced_accuracy,
    f1_neutral = f1_neutral,
    
    # Additional aggregate metrics
    accuracy = accuracy,
    macro_precision = macro_precision,
    macro_recall = macro_recall,
    
    # Per-class metrics
    per_class = list(
      precision = setNames(as.numeric(precision), EMOTION_CLASSES),
      recall = setNames(as.numeric(recall), EMOTION_CLASSES),
      f1 = setNames(as.numeric(f1), EMOTION_CLASSES),
      support = setNames(as.numeric(rowSums(cm)), EMOTION_CLASSES)
    ),
    
    # Confusion matrix
    confusion_matrix = cm,
    
    # Confidence intervals
    confidence_intervals = list(
      accuracy = accuracy_ci
    ),
    
    # Sample information
    n_samples = n_samples,
    class_distribution = setNames(as.numeric(rowSums(cm)), EMOTION_CLASSES)
  )
  
  log_info("Enhanced metrics computed successfully")
  log_debug("Macro F1: {round(macro_f1, 4)}, Balanced Accuracy: {round(balanced_accuracy, 4)}")
  
  return(metrics)
}

#' Evaluate quality gates with detailed reporting
#' @param metrics Metrics list from compute_enhanced_metrics
#' @return List with gate results and detailed analysis
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
  
  # Overall pass status
  overall_pass <- all(sapply(gates, function(g) g$passed))
  
  # Identify critical failures (large margins)
  critical_failures <- names(gates)[sapply(gates, function(g) !g$passed && g$margin < -0.05)]
  
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

#' Enhanced data loading with comprehensive validation
#' @param path File path to CSV
#' @param required_columns Required column names
#' @param max_rows Maximum number of rows to read (for safety)
#' @return Validated data frame
load_and_validate_csv <- function(path, required_columns, max_rows = 1e6) {
  log_info("Loading CSV from: {path}")
  
  assert_that(file.exists(path), msg = sprintf("File not found: %s", path))
  assert_that(is.character(required_columns), length(required_columns) > 0)
  
  # Read with data.table for performance
  tryCatch({
    dt <- fread(path, nrows = max_rows)
    df <- as.data.frame(dt)
    
    # Validate columns
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

#' Generate comprehensive synthetic data for testing
#' @param n_samples Number of samples to generate
#' @param class_imbalance Degree of class imbalance (0 = balanced, 1 = highly imbalanced)
#' @param noise_level Amount of label noise (0 = no noise, 1 = maximum noise)
#' @param seed Random seed for reproducibility
#' @return Data frame with true and predicted labels
generate_enhanced_demo_data <- function(n_samples = 2000, class_imbalance = 0.3, 
                                       noise_level = 0.1, seed = 42) {
  set.seed(seed)
  log_info("Generating enhanced demo data: n={n_samples}, imbalance={class_imbalance}, noise={noise_level}")
  
  # Generate class weights based on imbalance parameter
  if (class_imbalance == 0) {
    weights <- rep(1/length(EMOTION_CLASSES), length(EMOTION_CLASSES))
  } else {
    # Create imbalanced distribution
    weights <- exp(-class_imbalance * seq_along(EMOTION_CLASSES))
    weights <- weights / sum(weights)
  }
  
  # Generate true labels
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = weights)
  
  # Generate predictions with class-specific accuracies
  base_accuracies <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_accuracies) <- EMOTION_CLASSES
  
  # Confusion patterns for realistic errors
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
  
  y_pred <- character(n_samples)
  for (i in seq_len(n_samples)) {
    true_class <- y_true[i]
    accuracy <- base_accuracies[true_class] * (1 - noise_level)
    
    if (runif(1) < accuracy) {
      y_pred[i] <- true_class
    } else {
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

#' Export results with enhanced formatting and metadata
#' @param results Results object to export
#' @param output_path Output file path
#' @param metadata Additional metadata to include
export_enhanced_results <- function(results, output_path, metadata = list()) {
  log_info("Exporting results to: {output_path}")
  
  # Add timestamp and system information
  enhanced_results <- list(
    timestamp = Sys.time(),
    r_version = R.version.string,
    system_info = Sys.info()[c("sysname", "release", "machine")],
    metadata = metadata,
    results = results
  )
  
  # Ensure output directory exists
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  
  # Export with pretty formatting
  tryCatch({
    write_json(enhanced_results, output_path, pretty = TRUE, auto_unbox = TRUE)
    log_info("Results exported successfully")
  }, error = function(e) {
    log_error("Failed to export results: {e$message}")
    stop(sprintf("Export failed: %s", e$message), call. = FALSE)
  })
}
