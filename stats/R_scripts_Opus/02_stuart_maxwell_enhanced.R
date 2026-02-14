#!/usr/bin/env Rscript
#' Enhanced Stuart-Maxwell Test for Model Comparison
#' 
#' Advanced implementation with robust statistical computing, comprehensive error handling,
#' and enhanced visualization for comparing prediction patterns between models.
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
  library(MASS)
  library(corrplot)
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

#' Enhanced Stuart-Maxwell test with comprehensive statistical analysis
#' @param base_labels Base model predictions
#' @param ft_labels Fine-tuned model predictions
#' @param alpha Significance level
#' @return Enhanced test results with additional statistics
stuart_maxwell_enhanced <- function(base_labels, ft_labels, alpha = ALPHA_DEFAULT) {
  log_info("Performing enhanced Stuart-Maxwell test")
  
  # Validate inputs
  base_labels <- validate_emotion_labels(base_labels)
  ft_labels <- validate_emotion_labels(ft_labels)
  assert_that(length(base_labels) == length(ft_labels))
  assert_that(length(base_labels) > 0)
  
  n_samples <- length(base_labels)
  n_classes <- length(EMOTION_CLASSES)
  
  # Build contingency table
  contingency <- table(
    factor(base_labels, levels = EMOTION_CLASSES),
    factor(ft_labels, levels = EMOTION_CLASSES)
  )
  contingency_matrix <- as.matrix(contingency)
  
  # Compute marginal differences
  row_marginals <- rowSums(contingency_matrix)
  col_marginals <- colSums(contingency_matrix)
  marginal_diffs <- row_marginals - col_marginals
  
  # Build covariance matrix (K-1 x K-1)
  V <- matrix(0, nrow = n_classes, ncol = n_classes)
  for (i in 1:n_classes) {
    for (j in 1:n_classes) {
      if (i == j) {
        V[i, i] <- row_marginals[i] + col_marginals[i] - 2 * contingency_matrix[i, i]
      } else {
        V[i, j] <- -(contingency_matrix[i, j] + contingency_matrix[j, i])
      }
    }
  }
  
  # Reduce to (K-1) x (K-1) for non-singularity
  V_reduced <- V[-n_classes, -n_classes, drop = FALSE]
  d_reduced <- marginal_diffs[-n_classes]
  
  # Compute test statistic with robust matrix inversion
  tryCatch({
    V_inv <- solve(V_reduced)
  }, error = function(e) {
    log_warn("Singular covariance matrix, using generalized inverse")
    V_inv <- MASS::ginv(V_reduced)
  })
  
  chi_squared <- as.numeric(t(d_reduced) %*% V_inv %*% d_reduced)
  df <- n_classes - 1
  p_value <- 1 - pchisq(chi_squared, df)
  significant <- p_value < alpha
  
  # Additional statistics
  n_agreements <- sum(diag(contingency_matrix))
  n_disagreements <- n_samples - n_agreements
  agreement_rate <- n_agreements / n_samples
  
  # Effect size (Cramer's V equivalent for Stuart-Maxwell)
  effect_size <- sqrt(chi_squared / (n_samples * (n_classes - 1)))
  
  # Per-class agreement rates
  class_agreements <- diag(contingency_matrix)
  class_totals <- rowSums(contingency_matrix)
  class_agreement_rates <- safe_divide(class_agreements, class_totals)
  
  # Confidence interval for overall agreement rate
  agreement_ci <- binom.test(n_agreements, n_samples)$conf.int
  
  result <- list(
    # Core test results
    chi_squared = chi_squared,
    degrees_of_freedom = df,
    p_value = p_value,
    significant = significant,
    alpha = alpha,
    
    # Effect size and interpretation
    effect_size = effect_size,
    effect_interpretation = case_when(
      effect_size < 0.1 ~ "negligible",
      effect_size < 0.3 ~ "small",
      effect_size < 0.5 ~ "medium",
      TRUE ~ "large"
    ),
    
    # Marginal analysis
    marginal_differences = setNames(as.numeric(marginal_diffs), EMOTION_CLASSES),
    marginal_differences_abs_sum = sum(abs(marginal_diffs)),
    
    # Agreement analysis
    contingency_table = contingency_matrix,
    n_samples = n_samples,
    n_agreements = n_agreements,
    n_disagreements = n_disagreements,
    agreement_rate = agreement_rate,
    agreement_ci = as.numeric(agreement_ci),
    
    # Per-class analysis
    class_agreement_rates = setNames(as.numeric(class_agreement_rates), EMOTION_CLASSES),
    class_marginal_shifts = setNames(as.numeric(marginal_diffs / class_totals), EMOTION_CLASSES),
    
    # Statistical diagnostics
    covariance_matrix_condition = kappa(V_reduced),
    residuals = as.numeric(d_reduced),
    
    # Sample composition
    base_class_distribution = setNames(as.numeric(row_marginals), EMOTION_CLASSES),
    ft_class_distribution = setNames(as.numeric(col_marginals), EMOTION_CLASSES)
  )
  
  log_info("Stuart-Maxwell test completed: χ²={round(chi_squared, 4)}, p={round(p_value, 6)}")
  return(result)
}

#' Print enhanced Stuart-Maxwell report
#' @param result Enhanced test results
print_enhanced_stuart_maxwell_report <- function(result) {
  log_info("Generating enhanced Stuart-Maxwell report")
  
  cat(strrep("=", 80), "\n", sep = "")
  cat("ENHANCED STUART-MAXWELL TEST: Model Comparison Analysis\n")
  cat(strrep("=", 80), "\n\n", sep = "")
  
  # Executive Summary
  cat("--- EXECUTIVE SUMMARY ---\n")
  cat(sprintf("Test Result: %s\n", if (result$significant) "✅ SIGNIFICANT CHANGE" else "❌ NO SIGNIFICANT CHANGE"))
  cat(sprintf("Effect Size: %.4f (%s)\n", result$effect_size, result$effect_interpretation))
  cat(sprintf("Sample Size: %,d\n", result$n_samples))
  cat(sprintf("Overall Agreement: %.2f%% [%.2f%%, %.2f%%] (95%% CI)\n", 
             result$agreement_rate * 100, 
             result$agreement_ci[1] * 100, 
             result$agreement_ci[2] * 100))
  
  # Statistical Results
  cat("\n--- STATISTICAL RESULTS ---\n")
  cat(sprintf("Chi-squared statistic: %.6f\n", result$chi_squared))
  cat(sprintf("Degrees of freedom: %d\n", result$degrees_of_freedom))
  cat(sprintf("P-value: %.8f\n", result$p_value))
  cat(sprintf("Significance level (α): %.3f\n", result$alpha))
  cat(sprintf("Matrix condition number: %.2e\n", result$covariance_matrix_condition))
  
  # Interpretation with statistical context
  cat("\n--- DETAILED INTERPRETATION ---\n")
  if (result$significant) {
    cat("🔍 SIGNIFICANT PATTERN CHANGE DETECTED:\n")
    cat("   • Fine-tuning systematically altered prediction patterns\n")
    cat("   • Changes are statistically reliable (not due to chance)\n")
    cat(sprintf("   • Effect magnitude: %s (%.4f)\n", result$effect_interpretation, result$effect_size))
    cat("   • Recommendation: Proceed with per-class analysis\n")
  } else {
    cat("📊 NO SIGNIFICANT PATTERN CHANGE:\n")
    cat("   • Prediction patterns remained statistically stable\n")
    cat("   • Observed differences likely due to random variation\n")
    cat("   • Fine-tuning had minimal systematic impact\n")
  }
  
  # Marginal Analysis
  cat("\n--- MARGINAL DIFFERENCES ANALYSIS ---\n")
  cat("(Positive = base model predicted more; Negative = fine-tuned predicted more)\n")
  cat(sprintf("%-15s %12s %15s %12s %15s\n", 
             "Class", "Difference", "Rel. Change", "Agreement", "Shift Impact"))
  cat(strrep("-", 80), "\n", sep = "")
  
  for (cls in EMOTION_CLASSES) {
    diff <- result$marginal_differences[cls]
    rel_change <- result$class_marginal_shifts[cls] * 100
    agreement <- result$class_agreement_rates[cls] * 100
    
    impact <- if (abs(rel_change) > 10) "HIGH" else if (abs(rel_change) > 5) "MEDIUM" else "LOW"
    direction <- if (diff > 0) "← Base" else if (diff < 0) "→ FT" else "Stable"
    
    cat(sprintf("%-15s %+12.0f %+14.1f%% %11.1f%% %10s %s\n",
                cls, diff, rel_change, agreement, impact, direction))
  }
  
  # Agreement Analysis
  cat("\n--- AGREEMENT PATTERN ANALYSIS ---\n")
  best_agreement <- names(result$class_agreement_rates)[which.max(result$class_agreement_rates)]
  worst_agreement <- names(result$class_agreement_rates)[which.min(result$class_agreement_rates)]
  
  cat(sprintf("Highest Agreement: %s (%.1f%%)\n", 
             best_agreement, result$class_agreement_rates[best_agreement] * 100))
  cat(sprintf("Lowest Agreement: %s (%.1f%%)\n", 
             worst_agreement, result$class_agreement_rates[worst_agreement] * 100))
  
  # Model Comparison
  cat("\n--- MODEL DISTRIBUTION COMPARISON ---\n")
  cat(sprintf("%-15s %12s %12s %12s\n", "Class", "Base Count", "FT Count", "Net Change"))
  cat(strrep("-", 55), "\n", sep = "")
  
  for (cls in EMOTION_CLASSES) {
    base_count <- result$base_class_distribution[cls]
    ft_count <- result$ft_class_distribution[cls]
    net_change <- ft_count - base_count
    
    cat(sprintf("%-15s %12d %12d %+12d\n", cls, base_count, ft_count, net_change))
  }
  
  # Recommendations
  cat("\n--- RECOMMENDATIONS ---\n")
  if (result$significant) {
    if (result$effect_size > 0.3) {
      cat("🎯 STRONG EVIDENCE of systematic changes:\n")
      cat("   • Conduct per-class paired t-tests to identify specific improvements\n")
      cat("   • Analyze classes with largest marginal shifts\n")
      cat("   • Consider model ensemble if changes are beneficial\n")
    } else {
      cat("📈 MODERATE EVIDENCE of changes:\n")
      cat("   • Changes are statistically significant but modest in magnitude\n")
      cat("   • Focus on classes with poor agreement rates\n")
    }
  } else {
    cat("🔄 NO SYSTEMATIC CHANGES detected:\n")
    cat("   • Fine-tuning preserved existing prediction patterns\n")
    cat("   • Consider alternative training strategies if improvement was expected\n")
  }
  
  cat(strrep("=", 80), "\n", sep = "")
}

#' Create enhanced contingency heatmap with statistical annotations
#' @param result Enhanced test results
#' @param output_path Optional output path
#' @param interactive Whether to create interactive plot
create_enhanced_contingency_heatmap <- function(result, output_path = NULL, interactive = FALSE) {
  log_info("Creating enhanced contingency heatmap")
  
  # Prepare data
  cm <- result$contingency_table
  cm_df <- expand.grid(
    Base = factor(EMOTION_CLASSES, levels = rev(EMOTION_CLASSES)),
    FT = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES)
  )
  cm_df$Count <- as.vector(cm[nrow(cm):1, ])
  cm_df$Percentage <- cm_df$Count / sum(cm_df$Count) * 100
  cm_df$IsAgreement <- cm_df$Base == cm_df$FT
  
  # Create enhanced plot
  p <- ggplot(cm_df, aes(x = FT, y = Base, fill = Count)) +
    geom_tile(color = "white", size = 0.8) +
    geom_text(aes(label = sprintf("%d\n(%.1f%%)", Count, Percentage)), 
              color = ifelse(cm_df$Count > max(cm_df$Count) * 0.6, "white", "black"),
              size = 3, fontface = ifelse(cm_df$IsAgreement, "bold", "plain")) +
    scale_fill_viridis_c(name = "Count", option = "plasma", trans = "sqrt") +
    labs(
      title = "Enhanced Prediction Agreement Matrix",
      subtitle = sprintf("χ² = %.4f, p = %.6f | Agreement Rate: %.1f%% | Effect: %s", 
                        result$chi_squared, result$p_value, 
                        result$agreement_rate * 100, result$effect_interpretation),
      x = "Fine-tuned Model Predictions",
      y = "Base Model Predictions",
      caption = "Diagonal = Agreement | Off-diagonal = Disagreement | Bold = Perfect Agreement"
    ) +
    theme_minimal() +
    theme(
      axis.text.x = element_text(angle = 45, hjust = 1),
      plot.title = element_text(size = 14, face = "bold"),
      plot.subtitle = element_text(size = 11),
      plot.caption = element_text(size = 9, hjust = 0),
      legend.position = "right",
      panel.grid = element_blank()
    )
  
  # Add agreement rate annotations
  agreement_data <- data.frame(
    FT = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES),
    Base = factor(EMOTION_CLASSES, levels = rev(EMOTION_CLASSES)),
    Agreement = result$class_agreement_rates[rev(EMOTION_CLASSES)]
  )
  
  if (interactive) {
    p <- ggplotly(p, tooltip = c("x", "y", "fill", "text"))
  }
  
  if (!is.null(output_path)) {
    if (interactive) {
      htmlwidgets::saveWidget(p, output_path)
      log_info("Interactive contingency heatmap saved to: {output_path}")
    } else {
      ggsave(output_path, p, width = 12, height = 10, dpi = 300)
      log_info("Enhanced contingency heatmap saved to: {output_path}")
    }
  }
  
  return(p)
}

#' Create enhanced marginal differences visualization
#' @param result Enhanced test results
#' @param output_path Optional output path
create_enhanced_marginal_plot <- function(result, output_path = NULL) {
  log_info("Creating enhanced marginal differences visualization")
  
  # Prepare data
  marg_df <- data.frame(
    Class = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES),
    Difference = as.numeric(result$marginal_differences),
    RelativeChange = as.numeric(result$class_marginal_shifts) * 100,
    BaseCount = as.numeric(result$base_class_distribution),
    FTCount = as.numeric(result$ft_class_distribution),
    stringsAsFactors = FALSE
  )
  
  marg_df$Direction <- ifelse(marg_df$Difference > 0, "Base More", "FT More")
  marg_df$Impact <- ifelse(abs(marg_df$RelativeChange) > 10, "High", 
                          ifelse(abs(marg_df$RelativeChange) > 5, "Medium", "Low"))
  marg_df$IsNeutral <- marg_df$Class == NEUTRAL_CLASS
  
  # Create main plot
  p1 <- ggplot(marg_df, aes(x = reorder(Class, Difference), y = Difference, fill = Direction)) +
    geom_col(alpha = 0.8, color = "black", size = 0.3) +
    geom_hline(yintercept = 0, color = "black", size = 0.8) +
    geom_text(aes(label = sprintf("%.0f\n(%.1f%%)", Difference, RelativeChange)), 
              vjust = ifelse(marg_df$Difference > 0, -0.5, 1.5), size = 3) +
    scale_fill_manual(values = c("Base More" = "#3182bd", "FT More" = "#e6550d")) +
    labs(
      title = "Enhanced Marginal Differences Analysis",
      subtitle = sprintf("Total Absolute Change: %.0f | Significant: %s", 
                        result$marginal_differences_abs_sum,
                        ifelse(result$significant, "Yes", "No")),
      x = "Emotion Class",
      y = "Marginal Difference (Base - Fine-tuned)",
      fill = "Prediction Bias"
    ) +
    theme_minimal() +
    theme(
      axis.text.x = element_text(angle = 45, hjust = 1),
      plot.title = element_text(size = 14, face = "bold"),
      legend.position = "bottom"
    )
  
  # Highlight neutral class
  if (any(marg_df$IsNeutral)) {
    p1 <- p1 + geom_point(data = marg_df[marg_df$IsNeutral, ], 
                          aes(x = Class, y = Difference), 
                          color = "red", size = 4, shape = 8, inherit.aes = FALSE)
  }
  
  if (!is.null(output_path)) {
    ggsave(output_path, p1, width = 12, height = 8, dpi = 300)
    log_info("Enhanced marginal differences plot saved to: {output_path}")
  }
  
  return(p1)
}

#' Run enhanced Stuart-Maxwell analysis
#' @param df Input data frame with base_pred and finetuned_pred columns
#' @param alpha Significance level
#' @param output_dir Output directory
#' @param create_plots Whether to generate plots
#' @param interactive Whether to create interactive plots
run_enhanced_stuart_maxwell <- function(df, alpha = ALPHA_DEFAULT, output_dir = NULL, 
                                       create_plots = FALSE, interactive = FALSE) {
  log_info("Starting enhanced Stuart-Maxwell analysis")
  
  # Validate input
  assert_that(is.data.frame(df))
  assert_that(all(c("base_pred", "finetuned_pred") %in% names(df)))
  assert_that(nrow(df) > 0)
  
  # Run enhanced test
  result <- stuart_maxwell_enhanced(df$base_pred, df$finetuned_pred, alpha)
  
  # Print report
  print_enhanced_stuart_maxwell_report(result)
  
  # Save results and create plots
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    
    # Export results
    results_path <- file.path(output_dir, "stuart_maxwell_enhanced_results.json")
    export_enhanced_results(
      result,
      results_path,
      metadata = list(analysis_type = "stuart_maxwell", alpha = alpha)
    )
    
    if (create_plots) {
      # Contingency heatmap
      heatmap_path <- file.path(output_dir, "contingency_heatmap_enhanced.png")
      create_enhanced_contingency_heatmap(result, heatmap_path, interactive = FALSE)
      
      # Interactive heatmap
      if (interactive) {
        heatmap_interactive_path <- file.path(output_dir, "contingency_heatmap_interactive.html")
        create_enhanced_contingency_heatmap(result, heatmap_interactive_path, interactive = TRUE)
      }
      
      # Marginal differences plot
      marginal_path <- file.path(output_dir, "marginal_differences_enhanced.png")
      create_enhanced_marginal_plot(result, marginal_path)
    }
  }
  
  log_info("Enhanced Stuart-Maxwell analysis completed")
  return(result)
}

#' Generate enhanced demo data for Stuart-Maxwell test
#' @param n_samples Number of samples
#' @param effect_size Effect size category
#' @param seed Random seed
generate_enhanced_demo_pairs <- function(n_samples = 2000, effect_size = "medium", seed = 42) {
  set.seed(seed)
  log_info("Generating enhanced demo paired predictions: n={n_samples}, effect={effect_size}")
  
  # Generate base predictions with realistic class distribution
  class_weights <- c(0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10)
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = class_weights)
  
  # Base model accuracies
  base_acc <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_acc) <- EMOTION_CLASSES
  
  # Fine-tuned accuracies based on effect size
  if (effect_size == "none") {
    ft_acc <- base_acc
  } else if (effect_size == "small") {
    ft_acc <- pmin(0.95, base_acc + c(0.01, 0.03, 0.02, 0.01, -0.01, 0.01, 0.01, 0.01))
  } else if (effect_size == "large") {
    ft_acc <- pmin(0.95, base_acc + c(0.06, 0.17, 0.13, 0.08, -0.05, 0.05, 0.04, 0.07))
  } else { # medium
    ft_acc <- pmin(0.95, base_acc + c(0.02, 0.10, 0.08, 0.04, -0.02, 0.03, 0.02, 0.03))
  }
  names(ft_acc) <- EMOTION_CLASSES
  
  # Confusion patterns
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
  
  # Generate predictions
  base_pred <- character(n_samples)
  ft_pred <- character(n_samples)
  
  for (i in seq_len(n_samples)) {
    true_class <- y_true[i]
    
    # Base model prediction
    if (runif(1) < base_acc[true_class]) {
      base_pred[i] <- true_class
    } else {
      base_pred[i] <- sample(confusion_patterns[[true_class]], 1)
    }
    
    # Fine-tuned model prediction
    if (runif(1) < ft_acc[true_class]) {
      ft_pred[i] <- true_class
    } else {
      ft_pred[i] <- sample(confusion_patterns[[true_class]], 1)
    }
  }
  
  df <- data.frame(
    base_pred = base_pred,
    finetuned_pred = ft_pred,
    y_true = y_true,
    stringsAsFactors = FALSE
  )
  
  log_info("Generated enhanced demo pairs with realistic confusion patterns")
  return(df)
}

#' Main function with enhanced CLI
main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE,
                help = "Run with enhanced synthetic demo data"),
    make_option(c("--effect-size"), type = "character", default = "medium",
                help = "Demo effect size (none, small, medium, large)"),
    make_option(c("--predictions-csv"), type = "character", default = NULL,
                help = "CSV with base_pred, finetuned_pred columns"),
    make_option(c("--output"), type = "character", default = NULL,
                help = "Directory to save enhanced results and plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE,
                help = "Generate enhanced visualizations"),
    make_option(c("--interactive"), action = "store_true", default = FALSE,
                help = "Create interactive plots"),
    make_option(c("--alpha"), type = "double", default = ALPHA_DEFAULT,
                help = "Significance level"),
    make_option(c("--log-level"), type = "character", default = "INFO",
                help = "Logging level (DEBUG, INFO, WARN, ERROR)")
  )
  
  parser <- OptionParser(option_list = option_list,
                        description = "Enhanced Stuart-Maxwell Test v2.0")
  args <- parse_args(parser)
  
  # Configure logging
  log_threshold(args$`log-level`)
  
  # Validate arguments
  if (!args$demo && is.null(args$`predictions-csv`)) {
    print_help(parser)
    stop("Provide --demo or --predictions-csv option.")
  }
  
  # Load or generate data
  if (args$demo) {
    df <- generate_enhanced_demo_pairs(effect_size = args$`effect-size`)
  } else {
    df <- load_and_validate_csv(args$`predictions-csv`, c("base_pred", "finetuned_pred"))
  }
  
  # Set output directory
  output_dir <- args$output %||% DEFAULT_RESULTS_DIR
  
  # Run enhanced analysis
  tryCatch({
    run_enhanced_stuart_maxwell(
      df = df,
      alpha = args$alpha,
      output_dir = output_dir,
      create_plots = args$plot,
      interactive = args$interactive
    )
  }, error = function(e) {
    log_error("Enhanced Stuart-Maxwell analysis failed: {e$message}")
    stop(sprintf("Analysis failed: %s", e$message), call. = FALSE)
  })
  
  log_info("Enhanced Stuart-Maxwell analysis completed successfully")
}

# Execute main function if script is run directly
if (sys.nframe() == 0) {
  main()
}
