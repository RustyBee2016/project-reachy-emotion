#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)
  library(jsonlite)
  library(ggplot2)
  library(rlang)
  library(tidyr)
})

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
source(file.path(SCRIPT_DIR, "utils_data_ingest.R"))
DEFAULT_RESULTS_DIR <- normalizePath(file.path(SCRIPT_DIR, "..", "results"), mustWork = FALSE)
DEFAULT_CACHE_DIR <- file.path(DEFAULT_RESULTS_DIR, "raw_inputs")

EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)

ALPHA_DEFAULT <- 0.05

default_effects <- list(
  anger = 0.02,
  contempt = 0.08,
  disgust = 0.06,
  fear = 0.03,
  happiness = -0.02,
  neutral = 0.04,
  sadness = 0.01,
  surprise = 0.02
)

paired_t_test <- function(base_scores, ft_scores) {
  differences <- ft_scores - base_scores
  mean_diff <- mean(differences)
  std_diff <- sd(differences)
  n <- length(differences)
  if (n < 2) {
    return(list(
      mean_diff = mean_diff,
      std_diff = std_diff %||% 0,
      t_stat = 0,
      p_value = 1,
      mean_base = mean(base_scores),
      mean_ft = mean(ft_scores)
    ))
  }
  if (is.na(std_diff) || std_diff < 1e-10) {
    if (abs(mean_diff) < 1e-10) {
      return(list(
        mean_diff = mean_diff,
        std_diff = 0,
        t_stat = 0,
        p_value = 1,
        mean_base = mean(base_scores),
        mean_ft = mean(ft_scores)
      ))
    }
    t_stat <- sign(mean_diff) * 100
    return(list(
      mean_diff = mean_diff,
      std_diff = 0,
      t_stat = t_stat,
      p_value = 1e-10,
      mean_base = mean(base_scores),
      mean_ft = mean(ft_scores)
    ))
  }
  t_stat <- mean_diff / (std_diff / sqrt(n))
  p_value <- 2 * (1 - pt(abs(t_stat), df = n - 1))
  list(
    mean_diff = mean_diff,
    std_diff = std_diff,
    t_stat = t_stat,
    p_value = p_value,
    mean_base = mean(base_scores),
    mean_ft = mean(ft_scores)
  )
}

benjamini_hochberg <- function(p_values, alpha = ALPHA_DEFAULT) {
  m <- length(p_values)
  order_idx <- order(p_values)
  sorted_p <- p_values[order_idx]
  adjusted <- numeric(m)
  for (i in seq_len(m)) {
    adjusted[i] <- sorted_p[i] * m / i
  }
  for (i in seq(m - 1, 1)) {
    adjusted[i] <- min(adjusted[i], adjusted[i + 1])
  }
  adjusted <- pmin(adjusted, 1)
  adjusted_original <- numeric(m)
  adjusted_original[order_idx] <- adjusted
  list(
    adjusted = adjusted_original,
    significant = adjusted_original < alpha
  )
}

prepare_metrics_matrix <- function(df) {
  df$emotion_class <- factor(df$emotion_class, levels = EMOTION_CLASSES)
  split(df, df$emotion_class)
}

run_perclass_tests <- function(df, alpha = ALPHA_DEFAULT) {
  df_list <- prepare_metrics_matrix(df)
  class_results <- list()
  p_values <- numeric(length(EMOTION_CLASSES))
  idx <- 1
  for (cls in EMOTION_CLASSES) {
    class_df <- df_list[[cls]]
    if (is.null(class_df)) {
      stop(sprintf("Missing metrics for class '%s'", cls), call. = FALSE)
    }
    stats <- paired_t_test(class_df$base_score, class_df$finetuned_score)
    class_results[[cls]] <- list(
      emotion_class = cls,
      mean_base = stats$mean_base,
      mean_finetuned = stats$mean_ft,
      mean_difference = stats$mean_diff,
      std_difference = stats$std_diff,
      t_statistic = stats$t_stat,
      p_value_raw = stats$p_value
    )
    p_values[idx] <- stats$p_value
    idx <- idx + 1
  }
  bh <- benjamini_hochberg(p_values, alpha)
  improved <- c()
  degraded <- c()
  final_results <- vector("list", length(EMOTION_CLASSES))
  for (i in seq_along(EMOTION_CLASSES)) {
    cls <- EMOTION_CLASSES[i]
    res <- class_results[[cls]]
    is_sig <- bh$significant[i]
    direction <- "unchanged"
    if (is_sig) {
      if (res$mean_difference > 0) {
        direction <- "improved"
        improved <- c(improved, cls)
      } else {
        direction <- "degraded"
        degraded <- c(degraded, cls)
      }
    }
    final_results[[i]] <- c(res,
      list(
        p_value_adjusted = bh$adjusted[i],
        significant = is_sig,
        direction = direction
      )
    )
  }
  list(
    class_results = final_results,
    n_folds = length(df$fold %||% unique(df$fold)),
    n_classes = length(EMOTION_CLASSES),
    alpha = alpha,
    correction_method = "Benjamini-Hochberg",
    n_significant = sum(bh$significant),
    n_improved = length(improved),
    n_degraded = length(degraded),
    n_unchanged = length(EMOTION_CLASSES) - sum(bh$significant),
    improved_classes = improved,
    degraded_classes = degraded
  )
}

print_report <- function(result) {
  cat(strrep("=", 70), "\n", sep = "")
  cat("PER-CLASS PAIRED T-TESTS: Fine-Tuning Effect Analysis\n")
  cat(strrep("=", 70), "\n\n", sep = "")
  cat("--- TEST OVERVIEW ---\n")
  cat(sprintf("Classes: %d\n", result$n_classes))
  cat(sprintf("Significance level (α): %.2f\n", result$alpha))
  cat(sprintf("Correction: %s\n", result$correction_method))
  cat("\n--- SUMMARY ---\n")
  cat(sprintf("Significant changes: %d\n", result$n_significant))
  cat(sprintf("  - Improved: %d\n", result$n_improved))
  cat(sprintf("  - Degraded: %d\n", result$n_degraded))
  cat(sprintf("  - Unchanged: %d\n", result$n_unchanged))
  if (length(result$improved_classes) > 0) {
    cat(sprintf("Improved classes: %s\n", paste(result$improved_classes, collapse = ", ")))
  }
  if (length(result$degraded_classes) > 0) {
    cat(sprintf("Degraded classes: %s\n", paste(result$degraded_classes, collapse = ", ")))
  }
  cat("\n--- DETAILED RESULTS ---\n")
  cat(sprintf("%-12s %10s %10s %10s %10s %12s %12s %8s\n",
    "Class", "Base F1", "FT F1", "Diff", "t-stat", "p-raw", "p-adj", "Sig"))
  cat(strrep("-", 94), "\n", sep = "")
  ordered <- result$class_results[order(sapply(result$class_results, function(x) x$p_value_adjusted))]
  for (res in ordered) {
    sig_marker <- if (res$significant) "YES" else "no"
    direction_marker <- if (res$significant && res$direction == "improved") "↑" else if (res$significant && res$direction == "degraded") "↓" else ""
    cat(sprintf("%-12s %10.4f %10.4f %10.4f %10.3f %12.6f %12.6f %4s %s\n",
      res$emotion_class,
      res$mean_base,
      res$mean_finetuned,
      res$mean_difference,
      res$t_statistic,
      res$p_value_raw,
      res$p_value_adjusted,
      sig_marker,
      direction_marker
    ))
  }
  cat(strrep("=", 70), "\n", sep = "")
}

save_report <- function(result, output_path) {
  payload <- list(
    test_name = "Per-Class Paired t-tests",
    description = "Paired t-tests per emotion class with Benjamini-Hochberg correction",
    results = result
  )
  write_json(payload, output_path, pretty = TRUE, auto_unbox = TRUE)
  message("Report saved to: ", output_path)
}

plot_perclass_comparison <- function(result, output_path = NULL) {
  df <- data.frame(
    class = sapply(result$class_results, function(x) x$emotion_class),
    base = sapply(result$class_results, function(x) x$mean_base),
    ft = sapply(result$class_results, function(x) x$mean_finetuned),
    significant = sapply(result$class_results, function(x) x$significant)
  )
  df_long <- tidyr::pivot_longer(df, cols = c("base", "ft"), names_to = "model", values_to = "f1")
  plot <- ggplot(df_long, aes(x = class, y = f1, fill = model)) +
    geom_col(position = position_dodge(width = 0.7), width = 0.7) +
    geom_text(data = df[df$significant, ], aes(x = class, y = pmax(base, ft) + 0.02, label = "*"),
      inherit.aes = FALSE, size = 5, color = "red") +
    labs(title = "Per-Class F1 Comparison", x = "Emotion class", y = "F1 score") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 10, height = 5, dpi = 150)
    message("Per-class comparison chart saved to: ", output_path)
  }
}

plot_effect_sizes <- function(result, output_path = NULL) {
  df <- data.frame(
    class = sapply(result$class_results, function(x) x$emotion_class),
    diff = sapply(result$class_results, function(x) x$mean_difference),
    std = sapply(result$class_results, function(x) x$std_difference),
    significant = sapply(result$class_results, function(x) x$significant)
  )
  n <- length(unique(df$class))
  df$ci <- qt(0.975, df = n - 1) * df$std / sqrt(n)
  plot <- ggplot(df, aes(x = reorder(class, diff), y = diff, fill = diff > 0)) +
    geom_col(color = "black") +
    geom_errorbar(aes(ymin = diff - ci, ymax = diff + ci), width = 0.2) +
    scale_fill_manual(values = c("TRUE" = "#2ecc71", "FALSE" = "#e74c3c"), guide = "none") +
    labs(title = "Effect Sizes (F1 Difference)", x = "Emotion class", y = "ΔF1 (FT - Base)") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 10, height = 5, dpi = 150)
    message("Effect sizes chart saved to: ", output_path)
  }
}

generate_demo_metrics <- function(n_folds = 10, effect_pattern = "mixed", seed = 42) {
  set.seed(seed)
  base_means <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(base_means) <- EMOTION_CLASSES
  effects <- switch(effect_pattern,
    none = setNames(rep(0, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_improve = setNames(rep(0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    all_degrade = setNames(rep(-0.05, length(EMOTION_CLASSES)), EMOTION_CLASSES),
    default_effects
  )
  fold_std <- 0.03
  records <- list()
  idx <- 1
  for (cls in EMOTION_CLASSES) {
    base_mean <- base_means[[cls]]
    ft_mean <- base_mean + effects[[cls]]
    fold_difficulty <- rnorm(n_folds, mean = 0, sd = fold_std / 2)
    base_scores <- base_mean + fold_difficulty + rnorm(n_folds, mean = 0, sd = fold_std / 2)
    ft_scores <- ft_mean + fold_difficulty + rnorm(n_folds, mean = 0, sd = fold_std / 2)
    base_scores <- pmin(pmax(base_scores, 0), 1)
    ft_scores <- pmin(pmax(ft_scores, 0), 1)
    for (fold in seq_len(n_folds)) {
      records[[idx]] <- data.frame(
        fold = fold,
        emotion_class = cls,
        base_score = base_scores[fold],
        finetuned_score = ft_scores[fold]
      )
      idx <- idx + 1
    }
  }
  do.call(rbind, records)
}

load_metrics_csv <- function(path) {
  df <- read.csv(path, stringsAsFactors = FALSE)
  required <- c("emotion_class", "base_score", "finetuned_score")
  ensure_columns(df, required)
  df
}

load_metrics_from_db <- function(args, cfg) {
  query_text <- args$`db-query` %||% cfg$query$text
  if (is.null(query_text) || query_text == "") {
    stop("Database query text is required when using DB ingestion.", call. = FALSE)
  }
  conn_override <- compact_list(list(
    host = args$`db-host`,
    port = if (!is.null(args$`db-port`)) as.integer(args$`db-port`) else NULL,
    dbname = args$`db-name`,
    user = args$`db-user`,
    password = args$`db-password`
  ))
  conn_cfg <- merge_lists(cfg$connection, conn_override)
  if (length(conn_cfg) == 0) {
    stop("Database connection parameters are required.", call. = FALSE)
  }
  params_cfg <- cfg$query$params %||% list()
  params_cli <- parse_params_json(args$`query-params`)
  query_params <- merge_lists(params_cfg, params_cli)
  df <- run_parameterized_query(conn_cfg, query_text, query_params)
  ensure_columns(df, c("emotion_class", "base_score", "finetuned_score"))
}

load_metrics_data <- function(args, cfg) {
  if (args$demo) {
    message("Generating synthetic fold metrics ...")
    return(list(df = generate_demo_metrics(n_folds = args$`n-folds`, effect_pattern = args$`effect-pattern`), source = "demo"))
  }
  if (!is.null(args$`metrics-csv`)) {
    message("Loading fold metrics from CSV: ", args$`metrics-csv`)
    return(list(df = load_metrics_csv(args$`metrics-csv`), source = "csv"))
  }
  message("Querying Postgres for fold metrics ...")
  df <- load_metrics_from_db(args, cfg)
  list(df = df, source = "database")
}

run_analysis <- function(df, alpha, output_dir = NULL, do_plot = FALSE) {
  result <- run_perclass_tests(df, alpha = alpha)
  print_report(result)
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    save_report(result, file.path(output_dir, "perclass_paired_ttests.json"))
    if (do_plot) {
      plot_perclass_comparison(result, file.path(output_dir, "perclass_comparison.png"))
      plot_effect_sizes(result, file.path(output_dir, "perclass_effect_sizes.png"))
    }
  } else if (do_plot) {
    plot_perclass_comparison(result)
    plot_effect_sizes(result)
  }
  invisible(result)
}

main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE, help = "Run with synthetic fold metrics"),
    make_option(c("--effect-pattern"), type = "character", default = "mixed", help = "Demo effect pattern (none, all_improve, all_degrade, mixed)"),
    make_option(c("--n-folds"), type = "integer", default = 10, help = "Number of folds for demo data"),
    make_option(c("--metrics-csv"), type = "character", default = NULL, help = "CSV containing emotion_class, base_score, finetuned_score"),
    make_option(c("--config"), type = "character", default = NULL, help = "YAML config for DB/query defaults"),
    make_option(c("--db-host"), type = "character", default = NULL, help = "Postgres host"),
    make_option(c("--db-port"), type = "integer", default = NULL, help = "Postgres port"),
    make_option(c("--db-name"), type = "character", default = NULL, help = "Database name"),
    make_option(c("--db-user"), type = "character", default = NULL, help = "Database user"),
    make_option(c("--db-password"), type = "character", default = NULL, help = "Database password"),
    make_option(c("--db-query"), type = "character", default = NULL, help = "SQL query returning per-fold metrics"),
    make_option(c("--query-params"), type = "character", default = NULL, help = "JSON object with templated query params"),
    make_option(c("--cache-dir"), type = "character", default = NULL, help = "Directory to cache raw query inputs"),
    make_option(c("--output"), type = "character", default = NULL, help = "Directory to save JSON/plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE, help = "Generate optional plots"),
    make_option(c("--alpha"), type = "double", default = ALPHA_DEFAULT, help = "Significance level" )
  )
  parser <- OptionParser(option_list = option_list)
  args <- parse_args(parser)
  cfg <- read_yaml_config(args$config)
  if (!args$demo && is.null(args$`metrics-csv`) && is.null(args$`db-query`) && is.null(cfg$query$text)) {
    print_help(parser)
    stop("Provide --demo, --metrics-csv, or database connection/query options.")
  }
  data_bundle <- load_metrics_data(args, cfg)
  cache_dir <- args$`cache-dir` %||% cfg$output$cache_dir %||% DEFAULT_CACHE_DIR
  if (identical(data_bundle$source, "database")) {
    cache_raw_inputs(data_bundle$df, cache_dir, prefix = "perclass_paired_ttests")
  }
  output_dir <- args$output %||% cfg$output$dir %||% DEFAULT_RESULTS_DIR
  run_analysis(data_bundle$df, alpha = args$alpha, output_dir = output_dir, do_plot = args$plot)
}

if (sys.nframe() == 0) {
  main()
}
