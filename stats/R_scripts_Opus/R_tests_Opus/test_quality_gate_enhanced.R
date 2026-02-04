#!/usr/bin/env Rscript
#' Comprehensive Tests for Enhanced Quality Gate Metrics
#' 
#' Tests statistical accuracy, error handling, performance, and feature completeness
#' of the enhanced quality gate metrics implementation.

# Setup test environment
TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% getwd()), mustWork = FALSE)
source(file.path(TESTS_DIR, "test_utils_enhanced.R"))

suppressPackageStartupMessages({
  library(testthat)
  library(logger)
})

#' Test enhanced quality gate metrics functionality
test_enhanced_quality_gates <- function() {
  log_info("Starting enhanced quality gate metrics tests")
  
  test_results <- list()
  
  # Test 1: Demo mode execution
  test_results$demo_execution <- tryCatch({
    output_dir <- create_test_output_dir("quality_gate_demo")
    
    result <- run_r_script_with_capture(
      "01_quality_gate_metrics_enhanced.R",
      c("--demo", "--output", output_dir, "--plot", "--log-level", "INFO")
    )
    
    # Validate execution
    assert_that(result$success, msg = paste("Demo execution failed:", result$output))
    assert_that(result$execution_time < 60, msg = "Demo execution too slow")
    
    # Validate outputs
    json_file <- file.path(output_dir, "enhanced_demo_model_enhanced_quality_gates.json")
    validate_json_output(json_file, c("timestamp", "results", "metadata"))
    
    # Validate plots
    cm_file <- file.path(output_dir, "enhanced_demo_model_confusion_matrix_enhanced.png")
    perf_file <- file.path(output_dir, "enhanced_demo_model_performance_enhanced.png")
    validate_image_output(cm_file)
    validate_image_output(perf_file)
    
    log_test_result("Demo Execution", TRUE, "All outputs generated", result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time)
    
  }, error = function(e) {
    log_test_result("Demo Execution", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 2: CSV input processing
  test_results$csv_processing <- tryCatch({
    output_dir <- create_test_output_dir("quality_gate_csv")
    
    # Generate test data
    test_data <- generate_test_predictions(n_samples = 500, accuracy_level = 0.87)
    csv_path <- write_test_csv(test_data, "test_predictions.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "01_quality_gate_metrics_enhanced.R",
      c("--predictions-csv", csv_path, "--model-name", "test_model", 
        "--output", output_dir, "--plot")
    )
    
    assert_that(result$success, msg = paste("CSV processing failed:", result$output))
    
    # Validate JSON output structure
    json_file <- file.path(output_dir, "test_model_enhanced_quality_gates.json")
    validate_json_output(json_file, c("results", "metadata"))
    
    # Load and validate metrics
    json_data <- fromJSON(json_file)
    metrics <- json_data$results$metrics
    
    # Validate metric ranges
    assert_that(metrics$macro_f1 >= 0 && metrics$macro_f1 <= 1)
    assert_that(metrics$balanced_accuracy >= 0 && metrics$balanced_accuracy <= 1)
    assert_that(metrics$f1_neutral >= 0 && metrics$f1_neutral <= 1)
    assert_that(metrics$accuracy >= 0 && metrics$accuracy <= 1)
    
    log_test_result("CSV Processing", TRUE, "Metrics validated", result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time, metrics = metrics)
    
  }, error = function(e) {
    log_test_result("CSV Processing", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 3: Statistical accuracy validation
  test_results$statistical_accuracy <- tryCatch({
    # Create perfect prediction scenario
    perfect_data <- data.frame(
      y_true = rep(EMOTION_CLASSES, each = 10),
      y_pred = rep(EMOTION_CLASSES, each = 10),
      stringsAsFactors = FALSE
    )
    
    output_dir <- create_test_output_dir("quality_gate_perfect")
    csv_path <- write_test_csv(perfect_data, "perfect_predictions.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "01_quality_gate_metrics_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results and validate perfect scores
    json_file <- file.path(output_dir, "model_enhanced_quality_gates.json")
    json_data <- fromJSON(json_file)
    metrics <- json_data$results$metrics
    
    # Perfect predictions should yield perfect metrics
    assert_numerical_equal(metrics$macro_f1, 1.0, tolerance = 1e-10, "macro_f1")
    assert_numerical_equal(metrics$balanced_accuracy, 1.0, tolerance = 1e-10, "balanced_accuracy")
    assert_numerical_equal(metrics$f1_neutral, 1.0, tolerance = 1e-10, "f1_neutral")
    assert_numerical_equal(metrics$accuracy, 1.0, tolerance = 1e-10, "accuracy")
    
    # All quality gates should pass
    gates <- json_data$results$gate_evaluation$gates
    assert_that(all(sapply(gates, function(g) g$passed)))
    
    log_test_result("Statistical Accuracy", TRUE, "Perfect predictions validated")
    list(passed = TRUE, metrics = metrics)
    
  }, error = function(e) {
    log_test_result("Statistical Accuracy", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 4: Error handling
  test_results$error_handling <- tryCatch({
    # Test with invalid CSV
    output_dir <- create_test_output_dir("quality_gate_error")
    invalid_csv <- file.path(output_dir, "invalid.csv")
    writeLines("invalid,data\n1,2", invalid_csv)
    
    result <- run_r_script_with_capture(
      "01_quality_gate_metrics_enhanced.R",
      c("--predictions-csv", invalid_csv, "--output", output_dir)
    )
    
    # Should fail gracefully
    assert_that(!result$success, msg = "Should fail with invalid CSV")
    assert_that(result$status != 0, msg = "Should return non-zero exit code")
    
    log_test_result("Error Handling", TRUE, "Invalid input handled gracefully")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Error Handling", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 5: Performance benchmark
  test_results$performance <- tryCatch({
    # Generate large dataset
    large_data <- generate_test_predictions(n_samples = 5000, accuracy_level = 0.85)
    output_dir <- create_test_output_dir("quality_gate_perf")
    csv_path <- write_test_csv(large_data, "large_predictions.csv", output_dir)
    
    # Benchmark execution
    benchmark <- benchmark_script(
      "01_quality_gate_metrics_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir, "--plot"),
      n_runs = 3
    )
    
    # Performance should be reasonable
    assert_that(benchmark$mean_time < 30, msg = "Performance too slow for large dataset")
    assert_that(benchmark$sd_time < 5, msg = "Performance too variable")
    
    log_test_result("Performance", TRUE, 
                   sprintf("Mean: %.2fs, SD: %.2fs", benchmark$mean_time, benchmark$sd_time))
    list(passed = TRUE, benchmark = benchmark)
    
  }, error = function(e) {
    log_test_result("Performance", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 6: Interactive plots
  test_results$interactive_plots <- tryCatch({
    output_dir <- create_test_output_dir("quality_gate_interactive")
    
    result <- run_r_script_with_capture(
      "01_quality_gate_metrics_enhanced.R",
      c("--demo", "--output", output_dir, "--plot", "--interactive")
    )
    
    assert_that(result$success)
    
    # Check for interactive HTML file
    html_file <- file.path(output_dir, "enhanced_demo_model_confusion_matrix_interactive.html")
    validate_image_output(html_file, min_size_kb = 50)  # HTML files should be larger
    
    log_test_result("Interactive Plots", TRUE, "HTML visualization created")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Interactive Plots", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Summarize results
  total_tests <- length(test_results)
  passed_tests <- sum(sapply(test_results, function(x) x$passed %||% FALSE))
  
  log_info("Enhanced quality gate tests completed: {passed_tests}/{total_tests} passed")
  
  return(list(
    summary = list(total = total_tests, passed = passed_tests, failed = total_tests - passed_tests),
    results = test_results
  ))
}

# Run tests if script is executed directly
if (sys.nframe() == 0) {
  test_results <- test_enhanced_quality_gates()
  
  # Create test report
  report_path <- file.path(TEST_OUTPUT_ROOT, "quality_gate_enhanced_test_report.json")
  create_test_report(test_results$results, report_path)
  
  # Exit with appropriate code
  if (test_results$summary$failed > 0) {
    quit(status = 1)
  }
}
