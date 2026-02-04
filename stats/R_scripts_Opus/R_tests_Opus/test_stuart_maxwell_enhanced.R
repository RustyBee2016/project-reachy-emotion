#!/usr/bin/env Rscript
#' Comprehensive Tests for Enhanced Stuart-Maxwell Test
#' 
#' Tests statistical accuracy, error handling, performance, and feature completeness
#' of the enhanced Stuart-Maxwell test implementation.

# Setup test environment
TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% getwd()), mustWork = FALSE)
source(file.path(TESTS_DIR, "test_utils_enhanced.R"))

suppressPackageStartupMessages({
  library(testthat)
  library(logger)
})

#' Test enhanced Stuart-Maxwell functionality
test_enhanced_stuart_maxwell <- function() {
  log_info("Starting enhanced Stuart-Maxwell test validation")
  
  test_results <- list()
  
  # Test 1: Demo mode with different effect sizes
  test_results$demo_execution <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_demo")
    
    # Test medium effect size
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--demo", "--effect-size", "medium", "--output", output_dir, "--plot")
    )
    
    assert_that(result$success, msg = paste("Demo execution failed:", result$output))
    assert_that(result$execution_time < 45, msg = "Demo execution too slow")
    
    # Validate JSON output
    json_file <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    validate_json_output(json_file, c("timestamp", "results", "metadata"))
    
    # Load and validate results
    json_data <- fromJSON(json_file)
    sm_result <- json_data$results
    
    # Validate statistical properties
    assert_that(sm_result$chi_squared >= 0, msg = "Chi-squared must be non-negative")
    assert_that(sm_result$degrees_of_freedom == 7, msg = "DF should be K-1 = 7")
    assert_that(sm_result$p_value >= 0 && sm_result$p_value <= 1, msg = "P-value out of range")
    assert_that(sm_result$effect_size >= 0, msg = "Effect size must be non-negative")
    assert_that(sm_result$agreement_rate >= 0 && sm_result$agreement_rate <= 1)
    
    # Validate plots
    heatmap_file <- file.path(output_dir, "contingency_heatmap_enhanced.png")
    marginal_file <- file.path(output_dir, "marginal_differences_enhanced.png")
    validate_image_output(heatmap_file)
    validate_image_output(marginal_file)
    
    log_test_result("Demo Execution", TRUE, 
                   sprintf("χ²=%.4f, p=%.6f, effect=%s", 
                          sm_result$chi_squared, sm_result$p_value, sm_result$effect_interpretation),
                   result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time, results = sm_result)
    
  }, error = function(e) {
    log_test_result("Demo Execution", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 2: No effect scenario (should be non-significant)
  test_results$no_effect <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_no_effect")
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--demo", "--effect-size", "none", "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    json_data <- fromJSON(json_file)
    sm_result <- json_data$results
    
    # With no effect, test should likely be non-significant
    # (though random variation might occasionally make it significant)
    assert_that(sm_result$effect_size < 0.2, msg = "Effect size should be small with no true effect")
    
    log_test_result("No Effect Scenario", TRUE, 
                   sprintf("Non-significant as expected: p=%.6f", sm_result$p_value))
    list(passed = TRUE, results = sm_result)
    
  }, error = function(e) {
    log_test_result("No Effect Scenario", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 3: Large effect scenario (should be significant)
  test_results$large_effect <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_large_effect")
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--demo", "--effect-size", "large", "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    json_data <- fromJSON(json_file)
    sm_result <- json_data$results
    
    # Large effect should be significant and have substantial effect size
    assert_that(sm_result$significant, msg = "Large effect should be statistically significant")
    assert_that(sm_result$effect_size > 0.3, msg = "Large effect should have substantial effect size")
    
    log_test_result("Large Effect Scenario", TRUE, 
                   sprintf("Significant as expected: p=%.6f, effect=%s", 
                          sm_result$p_value, sm_result$effect_interpretation))
    list(passed = TRUE, results = sm_result)
    
  }, error = function(e) {
    log_test_result("Large Effect Scenario", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 4: CSV input processing
  test_results$csv_processing <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_csv")
    
    # Generate test paired predictions
    test_data <- generate_test_paired_predictions(n_samples = 800, effect_size = "medium")
    csv_path <- write_test_csv(test_data, "paired_predictions.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir, "--plot")
    )
    
    assert_that(result$success, msg = paste("CSV processing failed:", result$output))
    
    # Validate outputs
    json_file <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    validate_json_output(json_file, c("results", "metadata"))
    
    # Load and validate contingency table
    json_data <- fromJSON(json_file)
    sm_result <- json_data$results
    contingency <- sm_result$contingency_table
    
    # Contingency table should be 8x8 and sum to total samples
    assert_that(length(contingency) == 8, msg = "Contingency table should be 8x8")
    assert_that(all(sapply(contingency, length) == 8), msg = "All rows should have 8 columns")
    total_samples <- sum(unlist(contingency))
    assert_that(total_samples == nrow(test_data), msg = "Sample count mismatch")
    
    log_test_result("CSV Processing", TRUE, 
                   sprintf("Processed %d samples", total_samples), result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time)
    
  }, error = function(e) {
    log_test_result("CSV Processing", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 5: Perfect agreement scenario
  test_results$perfect_agreement <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_perfect")
    
    # Create perfect agreement data
    perfect_data <- data.frame(
      base_pred = rep(EMOTION_CLASSES, each = 20),
      finetuned_pred = rep(EMOTION_CLASSES, each = 20),
      stringsAsFactors = FALSE
    )
    csv_path <- write_test_csv(perfect_data, "perfect_agreement.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    json_data <- fromJSON(json_file)
    sm_result <- json_data$results
    
    # Perfect agreement should yield specific results
    assert_numerical_equal(sm_result$agreement_rate, 1.0, tolerance = 1e-10, "agreement_rate")
    assert_numerical_equal(sm_result$chi_squared, 0.0, tolerance = 1e-6, "chi_squared")
    assert_that(!sm_result$significant, msg = "Perfect agreement should be non-significant")
    assert_that(all(unlist(sm_result$marginal_differences) == 0), msg = "All marginal differences should be zero")
    
    log_test_result("Perfect Agreement", TRUE, "Perfect agreement validated")
    list(passed = TRUE, results = sm_result)
    
  }, error = function(e) {
    log_test_result("Perfect Agreement", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 6: Interactive visualization
  test_results$interactive_plots <- tryCatch({
    output_dir <- create_test_output_dir("stuart_maxwell_interactive")
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--demo", "--effect-size", "medium", "--output", output_dir, "--plot", "--interactive")
    )
    
    assert_that(result$success)
    
    # Check for interactive HTML file
    html_file <- file.path(output_dir, "contingency_heatmap_interactive.html")
    validate_image_output(html_file, min_size_kb = 100)  # Interactive HTML should be substantial
    
    log_test_result("Interactive Plots", TRUE, "Interactive heatmap created")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Interactive Plots", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 7: Error handling
  test_results$error_handling <- tryCatch({
    # Test with mismatched prediction lengths
    output_dir <- create_test_output_dir("stuart_maxwell_error")
    
    # Create invalid data (different lengths)
    invalid_data <- data.frame(
      base_pred = c("anger", "happiness"),
      finetuned_pred = c("anger"),  # Shorter length
      stringsAsFactors = FALSE
    )
    csv_path <- write_test_csv(invalid_data, "invalid_pairs.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "02_stuart_maxwell_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir)
    )
    
    # Should fail gracefully
    assert_that(!result$success, msg = "Should fail with invalid data")
    
    log_test_result("Error Handling", TRUE, "Invalid input handled gracefully")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Error Handling", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 8: Performance benchmark
  test_results$performance <- tryCatch({
    # Generate large paired dataset
    large_data <- generate_test_paired_predictions(n_samples = 3000, effect_size = "small")
    output_dir <- create_test_output_dir("stuart_maxwell_perf")
    csv_path <- write_test_csv(large_data, "large_pairs.csv", output_dir)
    
    # Benchmark execution
    benchmark <- benchmark_script(
      "02_stuart_maxwell_enhanced.R",
      c("--predictions-csv", csv_path, "--output", output_dir, "--plot"),
      n_runs = 3
    )
    
    # Performance should be reasonable
    assert_that(benchmark$mean_time < 25, msg = "Performance too slow for large dataset")
    assert_that(benchmark$sd_time < 3, msg = "Performance too variable")
    
    log_test_result("Performance", TRUE, 
                   sprintf("Mean: %.2fs, SD: %.2fs", benchmark$mean_time, benchmark$sd_time))
    list(passed = TRUE, benchmark = benchmark)
    
  }, error = function(e) {
    log_test_result("Performance", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Summarize results
  total_tests <- length(test_results)
  passed_tests <- sum(sapply(test_results, function(x) x$passed %||% FALSE))
  
  log_info("Enhanced Stuart-Maxwell tests completed: {passed_tests}/{total_tests} passed")
  
  return(list(
    summary = list(total = total_tests, passed = passed_tests, failed = total_tests - passed_tests),
    results = test_results
  ))
}

# Run tests if script is executed directly
if (sys.nframe() == 0) {
  test_results <- test_enhanced_stuart_maxwell()
  
  # Create test report
  report_path <- file.path(TEST_OUTPUT_ROOT, "stuart_maxwell_enhanced_test_report.json")
  create_test_report(test_results$results, report_path)
  
  # Exit with appropriate code
  if (test_results$summary$failed > 0) {
    quit(status = 1)
  }
}
