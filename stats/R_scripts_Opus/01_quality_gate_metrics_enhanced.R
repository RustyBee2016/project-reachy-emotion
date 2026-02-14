#!/usr/bin/env Rscript
#' Enhanced Quality Gate Metrics Analysis
#' 
#' Advanced implementation with robust statistical computing, comprehensive error handling,
#' and enhanced visualization capabilities for emotion classification model evaluation.
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

# Enhanced configuration
DEFAULT_RESULTS_DIR <- normalizePath(file.path(SCRIPT_DIR, "..", "results"), mustWork = FALSE)
DEFAULT_CACHE_DIR <- file.path(DEFAULT_RESULTS_DIR, "raw_inputs")

#' Print enhanced quality gate report with statistical insights
#' @param metrics Enhanced metrics from compute_enhanced_metrics
#' @param gate_eval Gate evaluation from evaluate_quality_gates_enhanced
#' @param model_name Model identifier
print_enhanced_report <- function(metrics, gate_eval, model_name = "model") {
  log_info("Generating enhanced quality gate report for model: {model_name}")
  
  cat(strrep("=", 80), "\n", sep = "")
  cat("ENHANCED QUALITY GATE METRICS REPORT:", model_name, "\n")
  cat(strrep("=", 80), "\n\n", sep = "")
  
  # Executive Summary
  cat("--- EXECUTIVE SUMMARY ---\n")
  cat(sprintf("Overall Status: %s\n", 
              if (gate_eval$overall_pass) "✅ PASS" else "❌ FAIL"))
  cat(sprintf("Gates Passed: %d/%d\n", gate_eval$summary$passed, gate_eval$summary$total))
  cat(sprintf("Sample Size: %,d\n", metrics$n_samples))
  cat(sprintf("Confidence Level: 95%%\n\n"))
  
  # Quality Gate Evaluation with Enhanced Details
  cat("--- QUALITY GATE EVALUATION ---\n")
  header <- sprintf("%-25s %10s %12s %10s %12s %10s\n", 
                   "Metric", "Value", "Threshold", "Status", "Margin", "Risk")
  cat(header)
  cat(strrep("-", 85), "\n", sep = "")
  
  for (gate_name in names(gate_eval$gates)) {
    gate <- gate_eval$gates[[gate_name]]
    status <- if (gate$passed) "PASS ✓" else "FAIL ✗"
    risk_level <- if (gate$margin > 0.05) "LOW" else if (gate$margin > 0) "MEDIUM" else "HIGH"
    
    cat(sprintf("%-25s %10.4f %12.2f %10s %+12.4f %10s\n",
                gate_name, gate$value, gate$threshold, status, gate$margin, risk_level))
  }
  
  # Critical Failures Alert
  if (length(gate_eval$critical_failures) > 0) {
    cat("\n⚠️  CRITICAL FAILURES DETECTED:\n")
    for (failure in gate_eval$critical_failures) {
      margin <- gate_eval$gates[[failure]]$margin
      cat(sprintf("   • %s: %.4f (%.4f below threshold)\n", failure, 
                 gate_eval$gates[[failure]]$value, abs(margin)))
    }
  }
  
  cat("\n--- STATISTICAL ANALYSIS ---\n")
  cat(sprintf("Accuracy: %.4f [%.4f, %.4f] (95%% CI)\n", 
             metrics$accuracy, 
             metrics$confidence_intervals$accuracy[1],
             metrics$confidence_intervals$accuracy[2]))
  cat(sprintf("Macro Precision: %.4f\n", metrics$macro_precision))
  cat(sprintf("Macro Recall: %.4f\n", metrics$macro_recall))
  
  # Class Distribution Analysis
  cat("\n--- CLASS DISTRIBUTION ANALYSIS ---\n")
  total_samples <- sum(metrics$class_distribution)
  cat(sprintf("%-15s %10s %12s %10s %12s\n", "Class", "Support", "Proportion", "F1", "Status"))
  cat(strrep("-", 70), "\n", sep = "")
  
  for (cls in EMOTION_CLASSES) {
    support <- metrics$class_distribution[cls]
    proportion <- support / total_samples
    f1_score <- metrics$per_class$f1[cls]
    
    # Determine class status
    status <- if (f1_score >= 0.8) "GOOD" else if (f1_score >= 0.6) "FAIR" else "POOR"
    if (cls == NEUTRAL_CLASS) status <- paste(status, "★")
    
    cat(sprintf("%-15s %10d %12.1f%% %10.4f %12s\n",
                cls, support, proportion * 100, f1_score, status))
  }
  
  # Performance Insights
  cat("\n--- PERFORMANCE INSIGHTS ---\n")
  
  # Best and worst performing classes
  f1_scores <- metrics$per_class$f1
  best_class <- names(f1_scores)[which.max(f1_scores)]
  worst_class <- names(f1_scores)[which.min(f1_scores)]
  
  cat(sprintf("Best Performing Class: %s (F1: %.4f)\n", best_class, f1_scores[best_class]))
  cat(sprintf("Worst Performing Class: %s (F1: %.4f)\n", worst_class, f1_scores[worst_class]))
  
  # Class imbalance assessment
  class_props <- metrics$class_distribution / sum(metrics$class_distribution)
  imbalance_ratio <- max(class_props) / min(class_props)
  cat(sprintf("Class Imbalance Ratio: %.2f:1 ", imbalance_ratio))
  if (imbalance_ratio > 10) {
    cat("(SEVERE IMBALANCE ⚠️)\n")
  } else if (imbalance_ratio > 3) {
    cat("(MODERATE IMBALANCE)\n")
  } else {
    cat("(BALANCED ✓)\n")
  }
  
  cat("\n--- RECOMMENDATIONS ---\n")
  if (!gate_eval$overall_pass) {
    cat("🔧 IMMEDIATE ACTIONS REQUIRED:\n")
    for (gate_name in names(gate_eval$gates)) {
      gate <- gate_eval$gates[[gate_name]]
      if (!gate$passed) {
        if (gate_name == "macro_f1") {
          cat("   • Improve overall classification: Consider data augmentation or model architecture changes\n")
        } else if (gate_name == "balanced_accuracy") {
          cat("   • Address class imbalance: Use class weighting or resampling techniques\n")
        } else if (gate_name == "f1_neutral") {
          cat("   • Critical: Neutral class performance affects Phase 2 baseline\n")
        }
      }
    }
  } else {
    cat("✅ All quality gates passed. Model ready for deployment.\n")
  }
  
  cat(strrep("=", 80), "\n", sep = "")
}

#' Create enhanced confusion matrix visualization
#' @param metrics Enhanced metrics object
#' @param output_path Optional output path for saving
#' @param interactive Whether to create interactive plot
create_enhanced_confusion_matrix <- function(metrics, output_path = NULL, interactive = FALSE) {
  log_info("Creating enhanced confusion matrix visualization")
  
  cm <- metrics$confusion_matrix
  
  # Convert to data frame for ggplot
  cm_df <- expand.grid(
    True = factor(EMOTION_CLASSES, levels = rev(EMOTION_CLASSES)),
    Predicted = factor(EMOTION_CLASSES, levels = EMOTION_CLASSES)
  )
  cm_df$Count <- as.vector(cm[nrow(cm):1, ])
  cm_df$Percentage <- cm_df$Count / sum(cm_df$Count) * 100
  
  # Create base plot
  p <- ggplot(cm_df, aes(x = Predicted, y = True, fill = Count)) +
    geom_tile(color = "white", size = 0.5) +
    geom_text(aes(label = sprintf("%d\n(%.1f%%)", Count, Percentage)), 
              color = ifelse(cm_df$Count > max(cm_df$Count) * 0.5, "white", "black"),
              size = 3) +
    scale_fill_viridis_c(name = "Count", option = "plasma") +
    labs(
      title = "Enhanced Confusion Matrix",
      subtitle = sprintf("Total Samples: %,d | Accuracy: %.3f", 
                        metrics$n_samples, metrics$accuracy),
      x = "Predicted Class",
      y = "True Class"
    ) +
    theme_minimal() +
    theme(
      axis.text.x = element_text(angle = 45, hjust = 1),
      plot.title = element_text(size = 14, face = "bold"),
      plot.subtitle = element_text(size = 12),
      legend.position = "right"
    )
  
  if (interactive) {
    p <- ggplotly(p, tooltip = c("x", "y", "fill", "text"))
  }
  
  if (!is.null(output_path)) {
    if (interactive) {
      htmlwidgets::saveWidget(p, output_path)
      log_info("Interactive confusion matrix saved to: {output_path}")
    } else {
      ggsave(output_path, p, width = 10, height = 8, dpi = 300)
      log_info("Confusion matrix saved to: {output_path}")
    }
  }
  
  return(p)
}

#' Create enhanced per-class performance visualization
#' @param metrics Enhanced metrics object
#' @param output_path Optional output path for saving
create_enhanced_performance_plot <- function(metrics, output_path = NULL) {
  log_info("Creating enhanced per-class performance visualization")
  
  # Prepare data
  perf_df <- data.frame(
    Class = rep(EMOTION_CLASSES, 3),
    Metric = rep(c("Precision", "Recall", "F1"), each = length(EMOTION_CLASSES)),
    Value = c(metrics$per_class$precision, 
              metrics$per_class$recall, 
              metrics$per_class$f1),
    Support = rep(metrics$per_class$support, 3),
    stringsAsFactors = FALSE
  )
  
  # Add quality indicators
  perf_df$Quality <- ifelse(perf_df$Value >= 0.8, "Excellent",
                           ifelse(perf_df$Value >= 0.6, "Good", "Needs Improvement"))
  perf_df$IsNeutral <- perf_df$Class == NEUTRAL_CLASS
  
  # Create plot
  p <- ggplot(perf_df, aes(x = reorder(Class, Value), y = Value, fill = Quality)) +
    geom_col(position = "dodge", alpha = 0.8) +
    geom_hline(yintercept = c(0.6, 0.8), linetype = "dashed", alpha = 0.5) +
    facet_wrap(~Metric, scales = "free_x") +
    scale_fill_manual(values = c("Excellent" = "#2E8B57", "Good" = "#FFD700", "Needs Improvement" = "#FF6347")) +
    labs(
      title = "Enhanced Per-Class Performance Analysis",
      subtitle = "Precision, Recall, and F1 Scores by Emotion Class",
      x = "Emotion Class",
      y = "Score",
      fill = "Performance Level"
    ) +
    theme_minimal() +
    theme(
      axis.text.x = element_text(angle = 45, hjust = 1),
      plot.title = element_text(size = 14, face = "bold"),
      strip.text = element_text(size = 12, face = "bold"),
      legend.position = "bottom"
    )
  
  # Highlight neutral class
  p <- p + geom_point(data = perf_df[perf_df$IsNeutral, ], 
                      aes(x = Class, y = Value), 
                      color = "red", size = 3, shape = 8)
  
  if (!is.null(output_path)) {
    ggsave(output_path, p, width = 12, height = 8, dpi = 300)
    log_info("Performance plot saved to: {output_path}")
  }
  
  return(p)
}

#' Run enhanced analysis with comprehensive reporting
#' @param df Input data frame with y_true and y_pred columns
#' @param model_name Model identifier
#' @param output_dir Output directory for results
#' @param create_plots Whether to generate visualizations
#' @param interactive Whether to create interactive plots
run_enhanced_analysis <- function(df, model_name = "model", output_dir = NULL, 
                                 create_plots = FALSE, interactive = FALSE) {
  log_info("Starting enhanced quality gate analysis for model: {model_name}")
  
  # Validate input data
  assert_that(is.data.frame(df))
  assert_that(all(c("y_true", "y_pred") %in% names(df)))
  assert_that(nrow(df) > 0)
  
  # Compute enhanced metrics
  metrics <- compute_enhanced_metrics(df$y_true, df$y_pred)
  
  # Evaluate quality gates
  gate_eval <- evaluate_quality_gates_enhanced(metrics)
  
  # Print enhanced report
  print_enhanced_report(metrics, gate_eval, model_name)
  
  # Save results if output directory specified
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    
    # Export enhanced results
    results_path <- file.path(output_dir, paste0(model_name, "_enhanced_quality_gates.json"))
    export_enhanced_results(
      list(metrics = metrics, gate_evaluation = gate_eval),
      results_path,
      metadata = list(model_name = model_name, analysis_type = "quality_gates")
    )
    
    # Create visualizations
    if (create_plots) {
      # Confusion matrix
      cm_path <- file.path(output_dir, paste0(model_name, "_confusion_matrix_enhanced.png"))
      create_enhanced_confusion_matrix(metrics, cm_path, interactive = FALSE)
      
      # Interactive confusion matrix
      if (interactive) {
        cm_interactive_path <- file.path(output_dir, paste0(model_name, "_confusion_matrix_interactive.html"))
        create_enhanced_confusion_matrix(metrics, cm_interactive_path, interactive = TRUE)
      }
      
      # Performance plot
      perf_path <- file.path(output_dir, paste0(model_name, "_performance_enhanced.png"))
      create_enhanced_performance_plot(metrics, perf_path)
    }
  }
  
  log_info("Enhanced analysis completed successfully")
  return(list(metrics = metrics, gate_evaluation = gate_eval))
}

#' Main function with enhanced CLI
main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE, 
                help = "Run with enhanced synthetic demo data"),
    make_option(c("--demo-imbalance"), type = "double", default = 0.3,
                help = "Class imbalance level for demo data (0-1)"),
    make_option(c("--demo-noise"), type = "double", default = 0.1,
                help = "Label noise level for demo data (0-1)"),
    make_option(c("--predictions-csv"), type = "character", default = NULL,
                help = "CSV file with y_true,y_pred columns"),
    make_option(c("--output"), type = "character", default = NULL,
                help = "Directory to save enhanced results and plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE,
                help = "Generate enhanced visualizations"),
    make_option(c("--interactive"), action = "store_true", default = FALSE,
                help = "Create interactive plots (requires plotly)"),
    make_option(c("--model-name"), type = "character", default = "model",
                help = "Name of evaluated model"),
    make_option(c("--log-level"), type = "character", default = "INFO",
                help = "Logging level (DEBUG, INFO, WARN, ERROR)")
  )
  
  parser <- OptionParser(option_list = option_list,
                        description = "Enhanced Quality Gate Metrics Analysis v2.0")
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
    log_info("Generating enhanced demo data with imbalance={args$`demo-imbalance`}, noise={args$`demo-noise`}")
    df <- generate_enhanced_demo_data(
      n_samples = 2000,
      class_imbalance = args$`demo-imbalance`,
      noise_level = args$`demo-noise`
    )
    model_name <- "enhanced_demo_model"
  } else {
    df <- load_and_validate_csv(args$`predictions-csv`, c("y_true", "y_pred"))
    model_name <- args$`model-name`
  }
  
  # Set output directory
  output_dir <- args$output %||% DEFAULT_RESULTS_DIR
  
  # Run enhanced analysis
  tryCatch({
    run_enhanced_analysis(
      df = df,
      model_name = model_name,
      output_dir = output_dir,
      create_plots = args$plot,
      interactive = args$interactive
    )
  }, error = function(e) {
    log_error("Analysis failed: {e$message}")
    stop(sprintf("Enhanced analysis failed: %s", e$message), call. = FALSE)
  })
  
  log_info("Enhanced quality gate analysis completed successfully")
}

# Execute main function if script is run directly
if (sys.nframe() == 0) {
  main()
}
