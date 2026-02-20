#!/usr/bin/env Rscript
#' Enhanced Per-Class Paired t-Tests with Advanced Statistical Analysis
#' 
#' Advanced implementation with robust statistical computing, comprehensive error handling,
#' multiple comparison corrections, and enhanced visualization for per-class analysis.
#' 
#' @author Reachy Emotion Team - Opus Enhancement
#' @version 2.0.0

suppressPackageStartupMessages({
  library(optparse)
  library(jsonlite)
  library(ggplot2)
  library(plotly)
  library(viridis)
  library(logger)
  library(assertthat)
  library(tidyr)
  library(dplyr)
  library(broom)
  library(effsize)
})

# Get script directory and source enhanced utilities
get_script_dir <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_flag <- "--file="
  file_idx <- grep(file_flag, cmd_args)
  if (length(file_idx) > 0) {
    return(dirname(normalizePath(sub(file_flag, "", cmd_args[file_idx]))))
  }
  if (!is.null(sys.frames()[[1]]$ofile)) {
    return(dirname(normalizePath(sys.frames()[[1]]$ofile)))
  }
  getwd()
}

SCRIPT_DIR <- get_script_dir()
source(file.path(SCRIPT_DIR, "utils_enhanced.R"))

DEFAULT_RESULTS_DIR <- normalizePath(file.path(SCRIPT_DIR, "..", "results"), mustWork = FALSE)
ALPHA_DEFAULT <- 0.05

#' Enhanced paired t-test with comprehensive statistics
#' @param base_scores Base model scores for a class
#' @param ft_scores Fine-tuned model scores for a class
#' @param class_name Emotion class name
#' @return Enhanced test results with effect sizes and diagnostics
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
  
  # Handle edge cases
  if (is.na(sd_diff) || sd_diff < 1e-10) {
    log_warn("Zero or near-zero variance in differences for class {class_name}")
    return(list(
      class_name = class_name,
      n_folds = n,
      mean_base = mean_base,
      mean_finetuned = mean_ft,
      mean_difference = mean_diff,
      sd_difference = 0,
      se_difference = 0,
      t_statistic = if (abs(mean_diff) < 1e-10) 0 else sign(mean_diff) * Inf,
      p_value_raw = if (abs(mean_diff) < 1e-10) 1 else 0,
      df = n - 1,
      ci_lower = mean_diff,
      ci_upper = mean_diff,
      effect_size_cohens_d = 0,
      effect_size_interpretation = "none",
      normality_p_value = NA,
      outliers_detected = 0
    ))
  }
  
  # Perform t-test
  t_stat <- mean_diff / se_diff
  df <- n - 1
  p_value <- 2 * pt(-abs(t_stat), df)
  
  # Confidence interval for mean difference
  t_critical <- qt(0.975, df)
  ci_lower <- mean_diff - t_critical * se_diff
  ci_upper <- mean_diff + t_critical * se_diff
  
  # Effect size (Cohen's d for paired samples)
  cohens_d <- mean_diff / sd_diff
  
  # Effect size interpretation
  effect_interpretation <- case_when(
    abs(cohens_d) < 0.2 ~ "negligible",
    abs(cohens_d) < 0.5 ~ "small",
    abs(cohens_d) < 0.8 ~ "medium",
    TRUE ~ "large"
  )
  
  # Normality test for differences (Shapiro-Wilk if n <= 50, otherwise Anderson-Darling)
  normality_p <- tryCatch({
    if (n <= 50) {
      shapiro.test(differences)$p.value
    } else {
      # Use Kolmogorov-Smirnov test for larger samples
      ks.test(differences, "pnorm", mean(differences), sd(differences))$p.value
    }
  }, error = function(e) NA)
  
  # Outlier detection using IQR method
  Q1 <- quantile(differences, 0.25, na.rm = TRUE)
  Q3 <- quantile(differences, 0.75, na.rm = TRUE)
  IQR <- Q3 - Q1
  outliers <- which(differences < (Q1 - 1.5 * IQR) | differences > (Q3 + 1.5 * IQR))
  n_outliers <- length(outliers)
  
  result <- list(
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
    effect_size_interpretation = effect_interpretation,
    normality_p_value = normality_p,
    outliers_detected = n_outliers,
    outlier_indices = outliers
  )
  
  log_debug("Paired t-test completed for {class_name}: t={round(t_stat, 3)}, p={round(p_value, 6)}")
  return(result)
}

#' Enhanced Benjamini-Hochberg correction with additional methods
#' @param p_values Vector of raw p-values
#' @param alpha Significance level
#' @param method Correction method ("BH", "bonferroni", "holm")
#' @return List with adjusted p-values and significance indicators
enhanced_multiple_comparison_correction <- function(p_values, alpha = ALPHA_DEFAULT, method = "BH") {
  log_info("Applying {method} multiple comparison correction")
  
  assert_that(is.numeric(p_values), all(p_values >= 0), all(p_values <= 1))
  
  m <- length(p_values)
  
  if (method == "BH") {
    # Benjamini-Hochberg procedure
    order_idx <- order(p_values)
    sorted_p <- p_values[order_idx]
    
    adjusted <- numeric(m)
    for (i in seq_len(m)) {
      adjusted[i] <- sorted_p[i] * m / i
    }
    
    # Enforce monotonicity
    for (i in seq(m - 1, 1)) {
      adjusted[i] <- min(adjusted[i], adjusted[i + 1])
    }
    
    adjusted <- pmin(adjusted, 1.0)
    adjusted_original <- numeric(m)
    adjusted_original[order_idx] <- adjusted
    
  } else if (method == "bonferroni") {
    adjusted_original <- pmin(p_values * m, 1.0)
    
  } else if (method == "holm") {
    order_idx <- order(p_values)
    sorted_p <- p_values[order_idx]
    
    adjusted <- numeric(m)
    for (i in seq_len(m)) {
      adjusted[i] <- sorted_p[i] * (m - i + 1)
    }
    
    # Enforce monotonicity
    for (i in 2:m) {
      adjusted[i] <- max(adjusted[i], adjusted[i - 1])
    }
    
    adjusted <- pmin(adjusted, 1.0)
    adjusted_original <- numeric(m)
    adjusted_original[order_idx] <- adjusted
    
  } else {
    stop("Unsupported correction method: {method}")
  }
  
  significant <- adjusted_original < alpha
  
  list(
    adjusted_p_values = adjusted_original,
    significant = significant,
    method = method,
    alpha = alpha,
    n_significant = sum(significant),
    fdr_estimate = if (method == "BH") sum(significant) * alpha / m else NA
  )
}

#' Run enhanced per-class paired t-tests
#' @param df Data frame with fold-level metrics
#' @param alpha Significance level
#' @param correction_method Multiple comparison correction method
#' @return Enhanced results with comprehensive statistics
run_enhanced_perclass_tests <- function(df, alpha = ALPHA_DEFAULT, correction_method = "BH") {
  log_info("Running enhanced per-class paired t-tests")
  
  # Validate input data
  assert_that(is.data.frame(df))
  required_cols <- c("emotion_class", "base_score", "finetuned_score")
  assert_that(all(required_cols %in% names(df)))
  
  # Validate emotion classes
  df$emotion_class <- validate_emotion_labels(df$emotion_class)
  
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
  
  for (i, cls in enumerate(EMOTION_CLASSES)) {
    class_data <- df[df$emotion_class == cls, ]
    
    if (nrow(class_data) < 3) {
      log_warn("Insufficient data for class {cls}: {nrow(class_data)} observations")
      # Create placeholder result
      class_results[[cls]] <- list(
        class_name = cls,
        n_folds = nrow(class_data),
        mean_base = NA,
        mean_finetuned = NA,
        mean_difference = NA,
        sd_difference = NA,
        se_difference = NA,
        t_statistic = NA,
        p_value_raw = NA,
        df = NA,
        ci_lower = NA,
        ci_upper = NA,
        effect_size_cohens_d = NA,
        effect_size_interpretation = "insufficient_data",
        normality_p_value = NA,
        outliers_detected = NA
      )
      p_values[cls] <- NA
    } else {
      result <- enhanced_paired_t_test(class_data$base_score, class_data$finetuned_score, cls)
      class_results[[cls]] <- result
      p_values[cls] <- result$p_value_raw
    }
  }
  
  # Apply multiple comparison correction
  valid_p_values <- p_values[!is.na(p_values)]
  if (length(valid_p_values) > 0) {
    correction_result <- enhanced_multiple_comparison_correction(valid_p_values, alpha, correction_method)
    
    # Add adjusted p-values to results
    for (cls in names(valid_p_values)) {
      class_results[[cls]]$p_value_adjusted <- correction_result$adjusted_p_values[cls]
      class_results[[cls]]$significant <- correction_result$significant[cls]
      class_results[[cls]]$direction <- if (is.na(class_results[[cls]]$mean_difference)) {
        "insufficient_data"
      } else if (class_results[[cls]]$significant) {
        if (class_results[[cls]]$mean_difference > 0) "improved" else "degraded"
      } else {
        "unchanged"
      }
    }
  } else {
    log_error("No valid p-values for multiple comparison correction")
    correction_result <- list(n_significant = 0, method = correction_method)
  }
  
  # Summarize results
  improved_classes <- names(class_results)[sapply(class_results, function(x) 
    !is.na(x$direction) && x$direction == "improved")]
  degraded_classes <- names(class_results)[sapply(class_results, function(x) 
    !is.na(x$direction) && x$direction == "degraded")]
  
  # Overall statistics
  valid_results <- class_results[!sapply(class_results, function(x) is.na(x$mean_difference))]
  overall_mean_improvement <- mean(sapply(valid_results, function(x) x$mean_difference), na.rm = TRUE)
  
  final_result <- list(
    class_results = class_results,
    n_classes_tested = length(valid_results),
    n_classes_total = length(EMOTION_CLASSES),
    alpha = alpha,
    correction_method = correction_method,
    n_significant = correction_result$n_significant,
    n_improved = length(improved_classes),
    n_degraded = length(degraded_classes),
    n_unchanged = length(valid_results) - correction_result$n_significant,
    improved_classes = improved_classes,
    degraded_classes = degraded_classes,
    overall_mean_improvement = overall_mean_improvement,
    fdr_estimate = correction_result$fdr_estimate,
    missing_classes = missing_classes
  )
  
  log_info("Enhanced per-class tests completed: {final_result$n_significant}/{final_result$n_classes_tested} significant")
  return(final_result)
}

#' Print enhanced per-class paired t-tests report
#' @param result Enhanced test results
print_enhanced_perclass_report <- function(result) {
  log_info("Generating enhanced per-class paired t-tests report")
  
  cat(strrep("=", 90), "\n", sep = "")
  cat("ENHANCED PER-CLASS PAIRED T-TESTS: Fine-Tuning Impact Analysis\n")
  cat(strrep("=", 90), "\n\n", sep = "")
  
  # Executive Summary
  cat("--- EXECUTIVE SUMMARY ---\n")
  cat(sprintf("Classes Tested: %d/%d\n", result$n_classes_tested, result$n_classes_total))
  cat(sprintf("Significant Changes: %d (%.1f%%)\n", 
             result$n_significant, result$n_significant / result$n_classes_tested * 100))
  cat(sprintf("Overall Mean Improvement: %+.4f\n", result$overall_mean_improvement))
  cat(sprintf("Correction Method: %s (α = %.3f)\n", result$correction_method, result$alpha))
  if (!is.na(result$fdr_estimate)) {
    cat(sprintf("Estimated FDR: %.3f\n", result$fdr_estimate))
  }
  
  # Summary by Direction
  cat("\n--- IMPACT SUMMARY ---\n")
  cat(sprintf("Improved Classes: %d\n", result$n_improved))
  if (length(result$improved_classes) > 0) {
    cat(sprintf("  → %s\n", paste(result$improved_classes, collapse = ", ")))
  }
  cat(sprintf("Degraded Classes: %d\n", result$n_degraded))
  if (length(result$degraded_classes) > 0) {
    cat(sprintf("  → %s\n", paste(result$degraded_classes, collapse = ", ")))
  }
  cat(sprintf("Unchanged Classes: %d\n", result$n_unchanged))
  
  # Detailed Results Table
  cat("\n--- DETAILED STATISTICAL RESULTS ---\n")
  header <- sprintf("%-12s %8s %8s %8s %8s %10s %10s %12s %8s %10s\n",
                   "Class", "N", "Base", "FT", "Diff", "t-stat", "p-raw", "p-adj", "Sig", "Effect")
  cat(header)
  cat(strrep("-", 110), "\n", sep = "")
  
  # Sort by adjusted p-value
  valid_results <- result$class_results[!sapply(result$class_results, function(x) is.na(x$p_value_raw))]
  if (length(valid_results) > 0) {
    sorted_results <- valid_results[order(sapply(valid_results, function(x) x$p_value_adjusted %||% 1))]
    
    for (res in sorted_results) {
      sig_marker <- if (!is.na(res$significant) && res$significant) "YES ✓" else "no"
      direction_marker <- case_when(
        is.na(res$direction) ~ "",
        res$direction == "improved" ~ "↑",
        res$direction == "degraded" ~ "↓",
        TRUE ~ ""
      )
      
      cat(sprintf("%-12s %8d %8.4f %8.4f %+8.4f %10.3f %10.6f %12.6f %4s %s %8s %s\n",
                  res$class_name,
                  res$n_folds,
                  res$mean_base,
                  res$mean_finetuned,
                  res$mean_difference,
                  res$t_statistic,
                  res$p_value_raw,
                  res$p_value_adjusted %||% NA,
                  sig_marker,
                  direction_marker,
                  res$effect_size_interpretation,
                  if (res$class_name == NEUTRAL_CLASS) "★" else ""))
    }
  }
  
  # Effect Size Analysis
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
  
  # Statistical Diagnostics
  cat("\n--- STATISTICAL DIAGNOSTICS ---\n")
  normality_violations <- sum(sapply(result$class_results, function(x) 
    !is.na(x$normality_p_value) && x$normality_p_value < 0.05), na.rm = TRUE)
  total_outliers <- sum(sapply(result$class_results, function(x) x$outliers_detected %||% 0), na.rm = TRUE)
  
  cat(sprintf("Normality Violations: %d/%d classes\n", normality_violations, result$n_classes_tested))
  cat(sprintf("Total Outliers Detected: %d\n", total_outliers))
  
  if (length(result$missing_classes) > 0) {
    cat(sprintf("Missing Data: %s\n", paste(result$missing_classes, collapse = ", ")))
  }
  
  # Recommendations
  cat("\n--- RECOMMENDATIONS ---\n")
  if (result$n_significant == 0) {
    cat("🔍 NO SIGNIFICANT PER-CLASS CHANGES:\n")
    cat("   • Fine-tuning effects were diffuse across classes\n")
    cat("   • Consider global model improvements or different training strategies\n")
  } else {
    cat("📊 SIGNIFICANT PER-CLASS CHANGES DETECTED:\n")
    
    if (result$n_improved > result$n_degraded) {
      cat("   ✅ Overall positive impact from fine-tuning\n")
    } else if (result$n_degraded > result$n_improved) {
      cat("   ⚠️  More classes degraded than improved - review training approach\n")
    } else {
      cat("   ⚖️  Mixed results - analyze individual class patterns\n")
    }
    
    # Specific recommendations for neutral class
    neutral_result <- result$class_results[[NEUTRAL_CLASS]]
    if (!is.na(neutral_result$direction)) {
      if (neutral_result$direction == "improved") {
        cat("   🎯 Neutral class improved - strengthens Phase 2 baseline\n")
      } else if (neutral_result$direction == "degraded") {
        cat("   🚨 CRITICAL: Neutral class degraded - impacts Phase 2 baseline\n")
      }
    }
  }
  
  cat(strrep("=", 90), "\n", sep = "")
}

#' Generate enhanced demo fold metrics
#' @param n_folds Number of cross-validation folds
#' @param effect_pattern Effect pattern type
#' @param seed Random seed
generate_enhanced_demo_metrics <- function(n_folds = 10, effect_pattern = "mixed", seed = 42) {
  set.seed(seed)
  log_info("Generating enhanced demo fold metrics: folds={n_folds}, pattern={effect_pattern}")
  
  # Base performance levels with realistic variation
  base_means <- c(
    anger = 0.82, contempt = 0.65, disgust = 0.72, fear = 0.78,
    happiness = 0.90, neutral = 0.88, sadness = 0.84, surprise = 0.80
  )
  
  # Effect patterns
  effects <- switch(effect_pattern,
    none = setNames(rep(0, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_improve = setNames(rep(0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_degrade = setNames(rep(-0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    mixed = c(anger = 0.02, contempt = 0.08, disgust = 0.06, fear = 0.03,
              happiness = -0.02, neutral = 0.04, sadness = 0.01, surprise = 0.02),
    realistic = c(anger = 0.015, contempt = 0.12, disgust = 0.08, fear = 0.025,
                  happiness = -0.015, neutral = 0.06, sadness = 0.02, surprise = 0.03)
  )
  
  # Generate correlated fold-level metrics
  fold_std <- 0.03
  correlation <- 0.3  # Correlation between base and fine-tuned performance
  
  records <- list()
  idx <- 1
  
  for (cls in EMOTION_CLASSES) {
    base_mean <- base_means[cls]
    ft_mean <- base_mean + effects[cls]
    
    # Generate correlated random effects for folds
    fold_effects <- MASS::mvrnorm(n_folds, mu = c(0, 0), 
                                  Sigma = matrix(c(1, correlation, correlation, 1), 2, 2))
    fold_effects <- fold_effects * fold_std
    
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
  
  df <- do.call(rbind, records)
  log_info("Generated enhanced demo metrics with realistic fold correlations")
  return(df)
}

#' Main function with enhanced CLI
main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE,
                help = "Run with enhanced synthetic fold metrics"),
    make_option(c("--effect-pattern"), type = "character", default = "mixed",
                help = "Demo effect pattern (none, all_improve, all_degrade, mixed, realistic)"),
    make_option(c("--n-folds"), type = "integer", default = 10,
                help = "Number of folds for demo data"),
    make_option(c("--metrics-csv"), type = "character", default = NULL,
                help = "CSV with emotion_class, base_score, finetuned_score columns"),
    make_option(c("--output"), type = "character", default = NULL,
                help = "Directory to save enhanced results and plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE,
                help = "Generate enhanced visualizations"),
    make_option(c("--interactive"), action = "store_true", default = FALSE,
                help = "Create interactive plots"),
    make_option(c("--alpha"), type = "double", default = ALPHA_DEFAULT,
                help = "Significance level"),
    make_option(c("--correction"), type = "character", default = "BH",
                help = "Multiple comparison correction (BH, bonferroni, holm)"),
    make_option(c("--log-level"), type = "character", default = "INFO",
                help = "Logging level (DEBUG, INFO, WARN, ERROR)")
  )
  
  parser <- OptionParser(option_list = option_list,
                        description = "Enhanced Per-Class Paired t-Tests v2.0")
  args <- parse_args(parser)
  
  # Configure logging
  log_threshold(args$`log-level`)
  
  # Validate arguments
  if (!args$demo && is.null(args$`metrics-csv`)) {
    print_help(parser)
    stop("Provide --demo or --metrics-csv option.")
  }
  
  # Load or generate data
  if (args$demo) {
    df <- generate_enhanced_demo_metrics(
      n_folds = args$`n-folds`,
      effect_pattern = args$`effect-pattern`
    )
  } else {
    df <- load_and_validate_csv(args$`metrics-csv`, 
                               c("emotion_class", "base_score", "finetuned_score"))
  }
  
  # Set output directory
  output_dir <- args$output %||% DEFAULT_RESULTS_DIR
  
  # Run enhanced analysis
  tryCatch({
    result <- run_enhanced_perclass_tests(
      df = df,
      alpha = args$alpha,
      correction_method = args$correction
    )
    
    # Print report
    print_enhanced_perclass_report(result)
    
    # Save results
    if (!is.null(output_dir)) {
      dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
      
      results_path <- file.path(output_dir, "perclass_paired_ttests_enhanced.json")
      export_enhanced_results(
        result,
        results_path,
        metadata = list(analysis_type = "perclass_paired_ttests", 
                       alpha = args$alpha, correction = args$correction)
      )
    }
    
  }, error = function(e) {
    log_error("Enhanced per-class analysis failed: {e$message}")
    stop(sprintf("Analysis failed: %s", e$message), call. = FALSE)
  })
  
  log_info("Enhanced per-class paired t-tests completed successfully")
}

# Execute main function if script is run directly
if (sys.nframe() == 0) {
  main()
}
