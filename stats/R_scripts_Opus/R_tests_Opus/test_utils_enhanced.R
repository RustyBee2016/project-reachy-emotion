#!/usr/bin/env Rscript
#' Enhanced Test Utilities for R Statistical Scripts
#' 
#' Comprehensive testing framework with statistical validation, performance benchmarking,
#' and accuracy verification against reference implementations.
#' 
#' @author Reachy Emotion Team - Opus Testing
#' @version 2.0.0

suppressPackageStartupMessages({
  library(testthat)
  library(bench)
  library(logger)
  library(assertthat)
  library(jsonlite)
  library(data.table)
})

# Test configuration
TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% getwd()), mustWork = FALSE)
OPUS_SCRIPTS_DIR <- normalizePath(file.path(TESTS_DIR, ".."), mustWork = TRUE)
ORIGINAL_SCRIPTS_DIR <- normalizePath(file.path(TESTS_DIR, "..", "..", "R_scripts"), mustWork = TRUE)
RESULTS_DIR <- file.path(dirname(TESTS_DIR), "..", "results")
TEST_OUTPUT_ROOT <- file.path(RESULTS_DIR, "test_runs_opus")

# Ensure test output directory exists
if (!dir.exists(TEST_OUTPUT_ROOT)) {
  dir.create(TEST_OUTPUT_ROOT, recursive = TRUE, showWarnings = FALSE)
}

# Configure logging for tests
log_threshold(INFO)
log_appender(appender_file(file.path(TEST_OUTPUT_ROOT, "test_execution.log")))

#' Emotion classes for testing
EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)

#' Quality gate thresholds for validation
QUALITY_GATES <- list(
  macro_f1 = 0.84,
  balanced_accuracy = 0.82,
  f1_neutral = 0.80
)

#' Create timestamped test output directory
#' @param prefix Directory prefix
#' @return Full path to created directory
create_test_output_dir <- function(prefix = "test") {
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  dir_name <- sprintf("%s_%s_%04d", prefix, timestamp, sample(1000:9999, 1))
  dir_path <- file.path(TEST_OUTPUT_ROOT, dir_name)
  dir.create(dir_path, recursive = TRUE, showWarnings = FALSE)
  log_debug("Created test output directory: {dir_path}")
  return(dir_path)
}

#' Generate high-quality synthetic prediction data
#' @param n_samples Number of samples
#' @param accuracy_level Overall accuracy level (0-1)
#' @param class_imbalance Degree of class imbalance (0-1)
#' @param seed Random seed
#' @return Data frame with y_true and y_pred columns
generate_test_predictions <- function(n_samples = 1000, accuracy_level = 0.85, 
                                    class_imbalance = 0.2, seed = 12345) {
  set.seed(seed)
  log_debug("Generating test predictions: n={n_samples}, acc={accuracy_level}, imb={class_imbalance}")
  
  # Generate class weights based on imbalance
  if (class_imbalance == 0) {
    weights <- rep(1/length(EMOTION_CLASSES), length(EMOTION_CLASSES))
  } else {
    weights <- exp(-class_imbalance * seq_along(EMOTION_CLASSES))
    weights <- weights / sum(weights)
  }
  
  # Generate true labels
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = weights)
  
  # Generate predictions with realistic confusion patterns
  confusion_patterns <- list(
    anger = c("fear", "disgust", "contempt"),
    contempt = c("disgust", "anger", "neutral"),
    disgust = c("contempt", "anger", "fear"),
    fear = c("surprise", "anger", "sadness"),
    happiness = c("surprise", "neutral", "contempt"),
    neutral = c("sadness", "happiness", "contempt"),
    sadness = c("neutral", "fear", "anger"),
    surprise = c("fear", "happiness", "neutral")
  )
  
  y_pred <- character(n_samples)
  for (i in seq_len(n_samples)) {
    true_class <- y_true[i]
    if (runif(1) < accuracy_level) {
      y_pred[i] <- true_class
    } else {
      y_pred[i] <- sample(confusion_patterns[[true_class]], 1)
    }
  }
  
  data.frame(y_true = y_true, y_pred = y_pred, stringsAsFactors = FALSE)
}

#' Generate synthetic paired predictions for Stuart-Maxwell testing
#' @param n_samples Number of samples
#' @param effect_size Effect size ("none", "small", "medium", "large")
#' @param seed Random seed
#' @return Data frame with base_pred and finetuned_pred columns
generate_test_paired_predictions <- function(n_samples = 1000, effect_size = "medium", seed = 12345) {
  set.seed(seed)
  log_debug("Generating paired predictions: n={n_samples}, effect={effect_size}")
  
  # Generate true labels
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE)
  
  # Base model accuracies
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
  names(ft_acc) <- EMOTION_CLASSES
  
  # Generate predictions
  base_pred <- character(n_samples)
  ft_pred <- character(n_samples)
  
  confusion_options <- list(
    anger = c("fear", "disgust"), contempt = c("disgust", "anger"),
    disgust = c("contempt", "anger"), fear = c("surprise", "anger"),
    happiness = c("surprise", "neutral"), neutral = c("sadness", "happiness"),
    sadness = c("neutral", "fear"), surprise = c("fear", "happiness")
  )
  
  for (i in seq_len(n_samples)) {
    true_class <- y_true[i]
    
    # Base prediction
    if (runif(1) < base_acc[true_class]) {
      base_pred[i] <- true_class
    } else {
      base_pred[i] <- sample(confusion_options[[true_class]], 1)
    }
    
    # Fine-tuned prediction
    if (runif(1) < ft_acc[true_class]) {
      ft_pred[i] <- true_class
    } else {
      ft_pred[i] <- sample(confusion_options[[true_class]], 1)
    }
  }
  
  data.frame(base_pred = base_pred, finetuned_pred = ft_pred, stringsAsFactors = FALSE)
}

#' Generate synthetic fold-level metrics for per-class testing
#' @param n_folds Number of folds
#' @param effect_pattern Effect pattern type
#' @param seed Random seed
#' @return Data frame with fold metrics
generate_test_fold_metrics <- function(n_folds = 10, effect_pattern = "mixed", seed = 12345) {
  set.seed(seed)
  log_debug("Generating fold metrics: folds={n_folds}, pattern={effect_pattern}")
  
  # Base performance levels
  base_means <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_means) <- EMOTION_CLASSES
  
  # Effect patterns
  effects <- switch(effect_pattern,
    none = setNames(rep(0, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_improve = setNames(rep(0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    mixed = c(anger = 0.02, contempt = 0.08, disgust = 0.06, fear = 0.03,
              happiness = -0.02, neutral = 0.04, sadness = 0.01, surprise = 0.02)
  )
  
  # Generate correlated fold metrics
  fold_std <- 0.03
  records <- list()
  idx <- 1
  
  for (cls in EMOTION_CLASSES) {
    base_mean <- base_means[cls]
    ft_mean <- base_mean + effects[cls]
    
    # Add fold-to-fold correlation
    fold_effects <- rnorm(n_folds, 0, fold_std/2)
    base_scores <- pmax(0, pmin(1, base_mean + fold_effects + rnorm(n_folds, 0, fold_std/2)))
    ft_scores <- pmax(0, pmin(1, ft_mean + fold_effects + rnorm(n_folds, 0, fold_std/2)))
    
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
  
  do.call(rbind, records)
}

#' Write test data to CSV file
#' @param data Data frame to write
#' @param filename Output filename
#' @param output_dir Output directory
#' @return Full path to written file
write_test_csv <- function(data, filename, output_dir) {
  filepath <- file.path(output_dir, filename)
  write.csv(data, filepath, row.names = FALSE)
  log_debug("Wrote test CSV: {filepath}")
  return(filepath)
}

#' Run R script with arguments and capture output
#' @param script_name Script filename (without path)
#' @param args Command line arguments
#' @param script_dir Directory containing the script
#' @param timeout_seconds Maximum execution time
#' @return List with status, output, and timing information
run_r_script_with_capture <- function(script_name, args = character(), 
                                     script_dir = OPUS_SCRIPTS_DIR, 
                                     timeout_seconds = 300) {
  script_path <- file.path(script_dir, script_name)
  assert_that(file.exists(script_path), msg = sprintf("Script not found: %s", script_path))
  
  log_debug("Running R script: {script_name} with args: {paste(args, collapse = ' ')}")
  
  start_time <- Sys.time()
  
  # Run script with timeout
  result <- tryCatch({
    output <- system2("Rscript", c(script_path, args), 
                     stdout = TRUE, stderr = TRUE, timeout = timeout_seconds)
    status <- attr(output, "status") %||% 0
    
    list(
      status = status,
      output = output,
      success = status == 0,
      execution_time = as.numeric(Sys.time() - start_time),
      timeout = FALSE
    )
  }, error = function(e) {
    if (grepl("timeout", e$message, ignore.case = TRUE)) {
      list(status = 124, output = paste("Timeout after", timeout_seconds, "seconds"),
           success = FALSE, execution_time = timeout_seconds, timeout = TRUE)
    } else {
      list(status = 1, output = e$message, success = FALSE, 
           execution_time = as.numeric(Sys.time() - start_time), timeout = FALSE)
    }
  })
  
  log_debug("Script execution completed: status={result$status}, time={round(result$execution_time, 2)}s")
  return(result)
}

#' Validate JSON output file structure
#' @param json_path Path to JSON file
#' @param expected_fields Expected top-level fields
#' @return TRUE if valid, throws error otherwise
validate_json_output <- function(json_path, expected_fields) {
  assert_that(file.exists(json_path), msg = sprintf("JSON file not found: %s", json_path))
  
  tryCatch({
    data <- fromJSON(json_path)
    missing_fields <- setdiff(expected_fields, names(data))
    
    if (length(missing_fields) > 0) {
      stop(sprintf("Missing JSON fields: %s", paste(missing_fields, collapse = ", ")))
    }
    
    log_debug("JSON validation passed: {json_path}")
    return(TRUE)
  }, error = function(e) {
    log_error("JSON validation failed: {e$message}")
    stop(sprintf("Invalid JSON structure: %s", e$message), call. = FALSE)
  })
}

#' Validate image file was created and has reasonable size
#' @param image_path Path to image file
#' @param min_size_kb Minimum file size in KB
#' @return TRUE if valid, throws error otherwise
validate_image_output <- function(image_path, min_size_kb = 10) {
  assert_that(file.exists(image_path), msg = sprintf("Image file not found: %s", image_path))
  
  file_size_kb <- file.size(image_path) / 1024
  if (file_size_kb < min_size_kb) {
    stop(sprintf("Image file too small: %.1f KB < %d KB", file_size_kb, min_size_kb))
  }
  
  log_debug("Image validation passed: {image_path} ({round(file_size_kb, 1)} KB)")
  return(TRUE)
}

#' Compare numerical results with tolerance
#' @param actual Actual values
#' @param expected Expected values
#' @param tolerance Numerical tolerance
#' @param label Description for error messages
#' @return TRUE if within tolerance, throws error otherwise
assert_numerical_equal <- function(actual, expected, tolerance = 1e-6, label = "values") {
  if (length(actual) != length(expected)) {
    stop(sprintf("Length mismatch in %s: %d vs %d", label, length(actual), length(expected)))
  }
  
  max_diff <- max(abs(actual - expected), na.rm = TRUE)
  if (max_diff > tolerance) {
    stop(sprintf("Numerical difference in %s exceeds tolerance: %.2e > %.2e", 
                label, max_diff, tolerance))
  }
  
  log_debug("Numerical comparison passed: {label} (max diff: {sprintf('%.2e', max_diff)})")
  return(TRUE)
}

#' Benchmark script execution time
#' @param script_name Script to benchmark
#' @param args Script arguments
#' @param n_runs Number of benchmark runs
#' @return Benchmark results
benchmark_script <- function(script_name, args = character(), n_runs = 3) {
  log_info("Benchmarking {script_name} with {n_runs} runs")
  
  times <- numeric(n_runs)
  for (i in seq_len(n_runs)) {
    result <- run_r_script_with_capture(script_name, args)
    if (!result$success) {
      stop(sprintf("Benchmark run %d failed: %s", i, result$output))
    }
    times[i] <- result$execution_time
  }
  
  benchmark_result <- list(
    script = script_name,
    n_runs = n_runs,
    times = times,
    mean_time = mean(times),
    median_time = median(times),
    min_time = min(times),
    max_time = max(times),
    sd_time = sd(times)
  )
  
  log_info("Benchmark completed: mean={round(benchmark_result$mean_time, 2)}s, sd={round(benchmark_result$sd_time, 2)}s")
  return(benchmark_result)
}

#' Create comprehensive test report
#' @param test_results List of test results
#' @param output_path Path for report file
create_test_report <- function(test_results, output_path) {
  log_info("Creating comprehensive test report")
  
  report <- list(
    timestamp = Sys.time(),
    r_version = R.version.string,
    system_info = Sys.info()[c("sysname", "release", "machine")],
    test_summary = list(
      total_tests = length(test_results),
      passed = sum(sapply(test_results, function(x) x$passed %||% FALSE)),
      failed = sum(sapply(test_results, function(x) !(x$passed %||% FALSE))),
      execution_time_total = sum(sapply(test_results, function(x) x$execution_time %||% 0))
    ),
    test_results = test_results
  )
  
  write_json(report, output_path, pretty = TRUE, auto_unbox = TRUE)
  log_info("Test report saved: {output_path}")
  return(report)
}

#' Log test result with standardized format
#' @param test_name Test identifier
#' @param passed Whether test passed
#' @param message Additional message
#' @param execution_time Execution time in seconds
log_test_result <- function(test_name, passed, message = "", execution_time = NA) {
  status <- if (passed) "PASS ✓" else "FAIL ✗"
  time_str <- if (!is.na(execution_time)) sprintf(" (%.2fs)", execution_time) else ""
  
  if (passed) {
    log_info("[{status}] {test_name}{time_str} {message}")
  } else {
    log_error("[{status}] {test_name}{time_str} {message}")
  }
}

# Export key constants and functions for test scripts
TEST_CONSTANTS <- list(
  EMOTION_CLASSES = EMOTION_CLASSES,
  QUALITY_GATES = QUALITY_GATES,
  OPUS_SCRIPTS_DIR = OPUS_SCRIPTS_DIR,
  ORIGINAL_SCRIPTS_DIR = ORIGINAL_SCRIPTS_DIR,
  TEST_OUTPUT_ROOT = TEST_OUTPUT_ROOT
)
