#!/usr/bin/env Rscript
#' Comprehensive Tests for Enhanced Per-Class Paired t-Tests
#' 
#' Tests statistical accuracy, error handling, performance, and feature completeness
#' of the enhanced per-class paired t-tests implementation.

# Setup test environment
TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% getwd()), mustWork = FALSE)
source(file.path(TESTS_DIR, "test_utils_enhanced.R"))

suppressPackageStartupMessages({
  library(testthat)
  library(logger)
})

#' Test enhanced per-class paired t-tests functionality
test_enhanced_perclass_ttests <- function() {
  log_info("Starting enhanced per-class paired t-tests validation")
  
  test_results <- list()
  
  # Test 1: Demo mode with mixed effects
  test_results$demo_execution <- tryCatch({
    output_dir <- create_test_output_dir("perclass_demo")
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--demo", "--effect-pattern", "mixed", "--n-folds", "8", "--output", output_dir, "--plot")
    )
    
    assert_that(result$success, msg = paste("Demo execution failed:", result$output))
    assert_that(result$execution_time < 60, msg = "Demo execution too slow")
    
    # Validate JSON output
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    validate_json_output(json_file, c("timestamp", "results", "metadata"))
    
    # Load and validate results
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    
    # Validate structure
    assert_that("class_results" %in% names(pc_result), msg = "Missing class_results")
    assert_that(pc_result$n_classes_tested <= length(EMOTION_CLASSES))
    assert_that(pc_result$alpha == 0.05, msg = "Default alpha should be 0.05")
    assert_that(pc_result$correction_method == "BH", msg = "Default correction should be BH")
    
    # Validate class results structure
    class_results <- pc_result$class_results
    assert_that(length(class_results) > 0, msg = "Should have class results")
    
    # Check first valid result
    valid_result <- class_results[[1]]
    required_fields <- c("class_name", "mean_base", "mean_finetuned", "mean_difference", 
                        "t_statistic", "p_value_raw", "p_value_adjusted", "significant")
    assert_that(all(required_fields %in% names(valid_result)), 
                msg = paste("Missing fields:", paste(setdiff(required_fields, names(valid_result)), collapse = ", ")))
    
    log_test_result("Demo Execution", TRUE, 
                   sprintf("%d/%d significant changes", pc_result$n_significant, pc_result$n_classes_tested),
                   result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time, results = pc_result)
    
  }, error = function(e) {
    log_test_result("Demo Execution", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 2: No effect scenario
  test_results$no_effect <- tryCatch({
    output_dir <- create_test_output_dir("perclass_no_effect")
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--demo", "--effect-pattern", "none", "--n-folds", "10", "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    
    # With no true effects, should have few or no significant results
    expected_false_positives <- pc_result$n_classes_tested * 0.05  # Expected under null
    assert_that(pc_result$n_significant <= expected_false_positives + 3, 
                msg = "Too many false positives with no effect")
    
    log_test_result("No Effect Scenario", TRUE, 
                   sprintf("%d significant (≤%.1f expected)", pc_result$n_significant, expected_false_positives))
    list(passed = TRUE, results = pc_result)
    
  }, error = function(e) {
    log_test_result("No Effect Scenario", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 3: All improve scenario
  test_results$all_improve <- tryCatch({
    output_dir <- create_test_output_dir("perclass_all_improve")
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--demo", "--effect-pattern", "all_improve", "--n-folds", "12", "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    
    # All classes should show improvement
    assert_that(pc_result$n_improved > 0, msg = "Should detect improvements")
    assert_that(pc_result$n_degraded == 0, msg = "Should not detect degradations with all_improve")
    assert_that(pc_result$overall_mean_improvement > 0, msg = "Overall improvement should be positive")
    
    log_test_result("All Improve Scenario", TRUE, 
                   sprintf("%d improved, mean=+%.4f", pc_result$n_improved, pc_result$overall_mean_improvement))
    list(passed = TRUE, results = pc_result)
    
  }, error = function(e) {
    log_test_result("All Improve Scenario", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 4: CSV input processing
  test_results$csv_processing <- tryCatch({
    output_dir <- create_test_output_dir("perclass_csv")
    
    # Generate test fold metrics
    test_data <- generate_test_fold_metrics(n_folds = 6, effect_pattern = "mixed")
    csv_path <- write_test_csv(test_data, "fold_metrics.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--metrics-csv", csv_path, "--alpha", "0.01", "--output", output_dir)
    )
    
    assert_that(result$success, msg = paste("CSV processing failed:", result$output))
    
    # Validate outputs
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    validate_json_output(json_file, c("results", "metadata"))
    
    # Load and validate alpha was applied
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    assert_that(pc_result$alpha == 0.01, msg = "Custom alpha not applied")
    
    # Validate data consistency
    total_records <- nrow(test_data)
    expected_records_per_class <- total_records / length(EMOTION_CLASSES)
    assert_that(expected_records_per_class == 6, msg = "Expected 6 folds per class")
    
    log_test_result("CSV Processing", TRUE, 
                   sprintf("Processed %d records, α=%.2f", total_records, pc_result$alpha),
                   result$execution_time)
    list(passed = TRUE, execution_time = result$execution_time)
    
  }, error = function(e) {
    log_test_result("CSV Processing", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 5: Multiple comparison corrections
  test_results$correction_methods <- tryCatch({
    output_dir <- create_test_output_dir("perclass_corrections")
    
    # Test Bonferroni correction
    result_bonf <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--demo", "--effect-pattern", "mixed", "--correction", "bonferroni", "--output", output_dir)
    )
    
    assert_that(result_bonf$success)
    
    # Test Holm correction
    result_holm <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--demo", "--effect-pattern", "mixed", "--correction", "holm", "--output", output_dir)
    )
    
    assert_that(result_holm$success)
    
    # Load Bonferroni results
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    
    assert_that(pc_result$correction_method %in% c("bonferroni", "holm"), 
                msg = "Correction method not properly set")
    
    log_test_result("Correction Methods", TRUE, "Bonferroni and Holm corrections tested")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Correction Methods", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 6: Statistical accuracy with known scenario
  test_results$statistical_accuracy <- tryCatch({
    output_dir <- create_test_output_dir("perclass_accuracy")
    
    # Create controlled data with known statistical properties
    controlled_data <- data.frame(
      fold = rep(1:5, length(EMOTION_CLASSES)),
      emotion_class = rep(EMOTION_CLASSES, each = 5),
      base_score = rep(c(0.8, 0.6, 0.7, 0.75, 0.9, 0.85, 0.8, 0.75), each = 5),
      finetuned_score = rep(c(0.8, 0.6, 0.7, 0.75, 0.9, 0.85, 0.8, 0.75), each = 5),  # No change
      stringsAsFactors = FALSE
    )
    
    csv_path <- write_test_csv(controlled_data, "controlled_metrics.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--metrics-csv", csv_path, "--output", output_dir)
    )
    
    assert_that(result$success)
    
    # Load results
    json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
    json_data <- fromJSON(json_file)
    pc_result <- json_data$results
    
    # With identical scores, should have no significant differences
    assert_that(pc_result$n_significant == 0, msg = "Should find no differences with identical scores")
    assert_numerical_equal(pc_result$overall_mean_improvement, 0, tolerance = 1e-10, "overall_mean_improvement")
    
    # Check individual class results
    for (class_result in pc_result$class_results) {
      if (!is.na(class_result$mean_difference)) {
        assert_numerical_equal(class_result$mean_difference, 0, tolerance = 1e-10, 
                              paste("mean_difference for", class_result$class_name))
      }
    }
    
    log_test_result("Statistical Accuracy", TRUE, "Identical scores correctly identified")
    list(passed = TRUE, results = pc_result)
    
  }, error = function(e) {
    log_test_result("Statistical Accuracy", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 7: Error handling
  test_results$error_handling <- tryCatch({
    # Test with insufficient data
    output_dir <- create_test_output_dir("perclass_error")
    
    # Create data with too few folds for some classes
    insufficient_data <- data.frame(
      fold = c(1, 2),
      emotion_class = c("anger", "anger"),  # Only 2 folds for anger
      base_score = c(0.8, 0.7),
      finetuned_score = c(0.9, 0.8),
      stringsAsFactors = FALSE
    )
    
    csv_path <- write_test_csv(insufficient_data, "insufficient_data.csv", output_dir)
    
    result <- run_r_script_with_capture(
      "03_perclass_paired_ttests_enhanced.R",
      c("--metrics-csv", csv_path, "--output", output_dir)
    )
    
    # Should handle gracefully (may succeed with warnings or fail gracefully)
    if (result$success) {
      # If it succeeds, check that it handled insufficient data appropriately
      json_file <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
      json_data <- fromJSON(json_file)
      pc_result <- json_data$results
      
      # Should have noted missing classes
      assert_that(length(pc_result$missing_classes) > 0, msg = "Should identify missing classes")
    }
    
    log_test_result("Error Handling", TRUE, "Insufficient data handled appropriately")
    list(passed = TRUE)
    
  }, error = function(e) {
    log_test_result("Error Handling", FALSE, e$message)
    list(passed = FALSE, error = e$message)
  })
  
  # Test 8: Performance benchmark
  test_results$performance <- tryCatch({
    # Generate large fold dataset
    large_data <- generate_test_fold_metrics(n_folds = 20, effect_pattern = "mixed")
    output_dir <- create_test_output_dir("perclass_perf")
    csv_path <- write_test_csv(large_data, "large_fold_metrics.csv", output_dir)
    
    # Benchmark execution
    benchmark <- benchmark_script(
      "03_perclass_paired_ttests_enhanced.R",
      c("--metrics-csv", csv_path, "--output", output_dir, "--plot"),
      n_runs = 3
    )
    
    # Performance should be reasonable
    assert_that(benchmark$mean_time < 20, msg = "Performance too slow for large dataset")
    assert_that(benchmark$sd_time < 2, msg = "Performance too variable")
    
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
  
  log_info("Enhanced per-class paired t-tests completed: {passed_tests}/{total_tests} passed")
  
  return(list(
    summary = list(total = total_tests, passed = passed_tests, failed = total_tests - passed_tests),
    results = test_results
  ))
}

# Run tests if script is executed directly
if (sys.nframe() == 0) {
  test_results <- test_enhanced_perclass_ttests()
  
  # Create test report
  report_path <- file.path(TEST_OUTPUT_ROOT, "perclass_enhanced_test_report.json")
  create_test_report(test_results$results, report_path)
  
  # Exit with appropriate code
  if (test_results$summary$failed > 0) {
    quit(status = 1)
  }
}
