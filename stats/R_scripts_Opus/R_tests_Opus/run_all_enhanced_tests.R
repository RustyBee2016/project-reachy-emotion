#!/usr/bin/env Rscript
#' Comprehensive Test Suite Runner for Enhanced R Statistical Scripts
#' 
#' Executes all test categories and generates comprehensive reports with
#' performance benchmarks and quality metrics.

# Setup test environment
TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% getwd()), mustWork = FALSE)
source(file.path(TESTS_DIR, "test_utils_enhanced.R"))

suppressPackageStartupMessages({
  library(logger)
  library(jsonlite)
})

#' Run all enhanced tests with comprehensive reporting
run_all_enhanced_tests <- function() {
  log_info("Starting comprehensive enhanced R scripts test suite")
  
  start_time <- Sys.time()
  all_results <- list()
  
  # Test 1: Enhanced Quality Gate Metrics
  log_info("=== Testing Enhanced Quality Gate Metrics ===")
  tryCatch({
    source(file.path(TESTS_DIR, "test_quality_gate_enhanced.R"))
    all_results$quality_gate <- test_enhanced_quality_gates()
  }, error = function(e) {
    log_error("Quality gate tests failed: {e$message}")
    all_results$quality_gate <- list(
      summary = list(total = 0, passed = 0, failed = 1),
      error = e$message
    )
  })
  
  # Test 2: Enhanced Stuart-Maxwell Test
  log_info("=== Testing Enhanced Stuart-Maxwell ===")
  tryCatch({
    source(file.path(TESTS_DIR, "test_stuart_maxwell_enhanced.R"))
    all_results$stuart_maxwell <- test_enhanced_stuart_maxwell()
  }, error = function(e) {
    log_error("Stuart-Maxwell tests failed: {e$message}")
    all_results$stuart_maxwell <- list(
      summary = list(total = 0, passed = 0, failed = 1),
      error = e$message
    )
  })
  
  # Test 3: Enhanced Per-Class Paired t-Tests
  log_info("=== Testing Enhanced Per-Class Paired t-Tests ===")
  tryCatch({
    source(file.path(TESTS_DIR, "test_perclass_enhanced.R"))
    all_results$perclass_ttests <- test_enhanced_perclass_ttests()
  }, error = function(e) {
    log_error("Per-class t-tests failed: {e$message}")
    all_results$perclass_ttests <- list(
      summary = list(total = 0, passed = 0, failed = 1),
      error = e$message
    )
  })
  
  # Calculate overall statistics
  total_time <- as.numeric(Sys.time() - start_time)
  
  overall_summary <- list(
    total_tests = sum(sapply(all_results, function(x) x$summary$total %||% 0)),
    passed_tests = sum(sapply(all_results, function(x) x$summary$passed %||% 0)),
    failed_tests = sum(sapply(all_results, function(x) x$summary$failed %||% 0)),
    execution_time = total_time,
    success_rate = 0
  )
  
  overall_summary$success_rate <- if (overall_summary$total_tests > 0) {
    overall_summary$passed_tests / overall_summary$total_tests
  } else {
    0
  }
  
  # Print comprehensive summary
  cat("\n", strrep("=", 80), "\n", sep = "")
  cat("COMPREHENSIVE ENHANCED R SCRIPTS TEST RESULTS\n")
  cat(strrep("=", 80), "\n\n", sep = "")
  
  cat("--- OVERALL SUMMARY ---\n")
  cat(sprintf("Total Tests: %d\n", overall_summary$total_tests))
  cat(sprintf("Passed: %d (%.1f%%)\n", overall_summary$passed_tests, overall_summary$success_rate * 100))
  cat(sprintf("Failed: %d\n", overall_summary$failed_tests))
  cat(sprintf("Total Execution Time: %.2f seconds\n", overall_summary$execution_time))
  
  # Individual test suite results
  cat("\n--- TEST SUITE BREAKDOWN ---\n")
  
  for (suite_name in names(all_results)) {
    suite_result <- all_results[[suite_name]]
    suite_title <- switch(suite_name,
      quality_gate = "Quality Gate Metrics",
      stuart_maxwell = "Stuart-Maxwell Test", 
      perclass_ttests = "Per-Class Paired t-Tests",
      suite_name
    )
    
    if ("error" %in% names(suite_result)) {
      cat(sprintf("%-30s: ERROR - %s\n", suite_title, suite_result$error))
    } else {
      summary <- suite_result$summary
      success_rate <- if (summary$total > 0) summary$passed / summary$total * 100 else 0
      cat(sprintf("%-30s: %d/%d passed (%.1f%%)\n", 
                 suite_title, summary$passed, summary$total, success_rate))
    }
  }
  
  # Performance analysis
  cat("\n--- PERFORMANCE ANALYSIS ---\n")
  performance_data <- list()
  
  for (suite_name in names(all_results)) {
    suite_result <- all_results[[suite_name]]
    if ("results" %in% names(suite_result)) {
      # Extract performance data from individual tests
      for (test_name in names(suite_result$results)) {
        test_result <- suite_result$results[[test_name]]
        if ("execution_time" %in% names(test_result)) {
          performance_data[[paste(suite_name, test_name, sep = "_")]] <- test_result$execution_time
        }
        if ("benchmark" %in% names(test_result)) {
          benchmark <- test_result$benchmark
          performance_data[[paste(suite_name, test_name, "benchmark", sep = "_")]] <- benchmark$mean_time
        }
      }
    }
  }
  
  if (length(performance_data) > 0) {
    avg_time <- mean(unlist(performance_data), na.rm = TRUE)
    max_time <- max(unlist(performance_data), na.rm = TRUE)
    cat(sprintf("Average Test Time: %.2f seconds\n", avg_time))
    cat(sprintf("Longest Test Time: %.2f seconds\n", max_time))
    
    # Identify slow tests
    slow_tests <- names(performance_data)[unlist(performance_data) > 10]
    if (length(slow_tests) > 0) {
      cat("Slow Tests (>10s):\n")
      for (test in slow_tests) {
        cat(sprintf("  • %s: %.2fs\n", test, performance_data[[test]]))
      }
    }
  }
  
  # Quality assessment
  cat("\n--- QUALITY ASSESSMENT ---\n")
  if (overall_summary$success_rate >= 0.95) {
    cat("✅ EXCELLENT: Test suite quality is excellent (≥95% pass rate)\n")
  } else if (overall_summary$success_rate >= 0.90) {
    cat("✅ GOOD: Test suite quality is good (≥90% pass rate)\n")
  } else if (overall_summary$success_rate >= 0.80) {
    cat("⚠️  ACCEPTABLE: Test suite quality is acceptable (≥80% pass rate)\n")
  } else {
    cat("❌ POOR: Test suite quality needs improvement (<80% pass rate)\n")
  }
  
  # Recommendations
  cat("\n--- RECOMMENDATIONS ---\n")
  if (overall_summary$failed_tests > 0) {
    cat("🔧 IMMEDIATE ACTIONS:\n")
    cat("   • Review failed test logs for specific issues\n")
    cat("   • Check enhanced script implementations for bugs\n")
    cat("   • Validate test data generation and expectations\n")
  }
  
  if (overall_summary$execution_time > 300) {  # 5 minutes
    cat("⚡ PERFORMANCE IMPROVEMENTS:\n")
    cat("   • Optimize slow-running tests and scripts\n")
    cat("   • Consider parallel test execution\n")
    cat("   • Review algorithm efficiency in enhanced implementations\n")
  }
  
  if (overall_summary$success_rate >= 0.95) {
    cat("🚀 DEPLOYMENT READY:\n")
    cat("   • Enhanced R scripts pass comprehensive validation\n")
    cat("   • Statistical accuracy and performance verified\n")
    cat("   • Ready for production deployment\n")
  }
  
  cat(strrep("=", 80), "\n", sep = "")
  
  # Generate comprehensive report
  comprehensive_report <- list(
    timestamp = Sys.time(),
    test_environment = list(
      r_version = R.version.string,
      system_info = Sys.info()[c("sysname", "release", "machine")],
      test_directory = TESTS_DIR
    ),
    overall_summary = overall_summary,
    suite_results = all_results,
    performance_data = performance_data,
    quality_assessment = list(
      grade = if (overall_summary$success_rate >= 0.95) "EXCELLENT" else
              if (overall_summary$success_rate >= 0.90) "GOOD" else
              if (overall_summary$success_rate >= 0.80) "ACCEPTABLE" else "POOR",
      pass_rate = overall_summary$success_rate,
      deployment_ready = overall_summary$success_rate >= 0.95 && overall_summary$failed_tests == 0
    )
  )
  
  # Save comprehensive report
  report_path <- file.path(TEST_OUTPUT_ROOT, "comprehensive_test_report.json")
  write_json(comprehensive_report, report_path, pretty = TRUE, auto_unbox = TRUE)
  log_info("Comprehensive test report saved: {report_path}")
  
  # Create summary CSV for easy analysis
  summary_csv_path <- file.path(TEST_OUTPUT_ROOT, "test_summary.csv")
  summary_df <- data.frame(
    test_suite = names(all_results),
    total_tests = sapply(all_results, function(x) x$summary$total %||% 0),
    passed_tests = sapply(all_results, function(x) x$summary$passed %||% 0),
    failed_tests = sapply(all_results, function(x) x$summary$failed %||% 0),
    success_rate = sapply(all_results, function(x) {
      s <- x$summary
      if (s$total > 0) s$passed / s$total else 0
    }),
    has_error = sapply(all_results, function(x) "error" %in% names(x)),
    stringsAsFactors = FALSE
  )
  write.csv(summary_df, summary_csv_path, row.names = FALSE)
  log_info("Test summary CSV saved: {summary_csv_path}")
  
  # Return results for programmatic use
  return(comprehensive_report)
}

# Execute if run directly
if (sys.nframe() == 0) {
  results <- run_all_enhanced_tests()
  
  # Exit with appropriate code
  if (results$overall_summary$failed_tests > 0) {
    quit(status = 1)
  } else {
    quit(status = 0)
  }
}
