#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)
  library(jsonlite)
  library(ggplot2)
  library(rlang)
  library(MASS)
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

encode_classes <- function(labels) {
  idx <- match(labels, EMOTION_CLASSES)
  if (any(is.na(idx))) {
    missing_levels <- unique(labels[is.na(idx)])
    stop(sprintf(
      "Encountered unknown emotion classes: %s",
      paste(missing_levels, collapse = ", ")
    ), call. = FALSE)
  }
  idx
}

build_contingency <- function(base_preds, ft_preds) {
  n_classes <- length(EMOTION_CLASSES)
  table <- matrix(0, nrow = n_classes, ncol = n_classes)
  for (i in seq_along(base_preds)) {
    table[base_preds[i], ft_preds[i]] <- table[base_preds[i], ft_preds[i]] + 1
  }
  table
}

compute_marginal_differences <- function(table) {
  rowSums(table) - colSums(table)
}

compute_covariance_matrix <- function(table) {
  K <- nrow(table)
  row_marginals <- rowSums(table)
  col_marginals <- colSums(table)
  V_full <- matrix(0, nrow = K, ncol = K)
  for (i in seq_len(K)) {
    for (j in seq_len(K)) {
      if (i == j) {
        V_full[i, i] <- row_marginals[i] + col_marginals[i] - 2 * table[i, i]
      } else {
        V_full[i, j] <- -(table[i, j] + table[j, i])
      }
    }
  }
  V_full[-K, -K, drop = FALSE]
}

stuart_maxwell_test <- function(base_labels, ft_labels, alpha = ALPHA_DEFAULT) {
  base_idx <- encode_classes(base_labels)
  ft_idx <- encode_classes(ft_labels)
  contingency <- build_contingency(base_idx, ft_idx)
  d_full <- compute_marginal_differences(contingency)
  d_reduced <- matrix(d_full[-length(d_full)], ncol = 1)
  V <- compute_covariance_matrix(contingency)
  V_inv <- tryCatch(solve(V), error = function(e) MASS::ginv(V))
  chi_sq <- as.numeric(t(d_reduced) %*% V_inv %*% d_reduced)
  df <- length(EMOTION_CLASSES) - 1
  p_value <- 1 - pchisq(chi_sq, df)
  list(
    chi_squared = chi_sq,
    degrees_of_freedom = df,
    p_value = p_value,
    significant = p_value < alpha,
    alpha = alpha,
    marginal_differences = setNames(as.numeric(d_full), EMOTION_CLASSES),
    contingency_table = contingency,
    n_samples = length(base_labels),
    n_agreements = sum(diag(contingency)),
    n_disagreements = length(base_labels) - sum(diag(contingency))
  )
}

print_report <- function(result) {
  cat(strrep("=", 70), "\n", sep = "")
  cat("STUART-MAXWELL TEST: Model Comparison\n")
  cat(strrep("=", 70), "\n\n", sep = "")
  cat("--- TEST OVERVIEW ---\n")
  agreement_rate <- result$n_agreements / result$n_samples
  cat(sprintf("Samples analyzed: %d\n", result$n_samples))
  cat(sprintf("Agreement rate: %.2f%% (%d samples)\n", agreement_rate * 100, result$n_agreements))
  cat(sprintf("Disagreement rate: %.2f%% (%d samples)\n", (1 - agreement_rate) * 100, result$n_disagreements))

  cat("\n--- TEST RESULTS ---\n")
  cat(sprintf("Chi-squared statistic: %.4f\n", result$chi_squared))
  cat(sprintf("Degrees of freedom: %d\n", result$degrees_of_freedom))
  cat(sprintf("P-value: %.6f\n", result$p_value))
  cat(sprintf("Significance level (α): %.2f\n", result$alpha))

  cat("\n--- INTERPRETATION ---\n")
  if (result$significant) {
    cat("Result: SIGNIFICANT\n")
    cat("→ Fine-tuning CHANGED the model's prediction patterns.\n")
    cat("→ Follow-up per-class t-tests are recommended.\n")
  } else {
    cat("Result: NOT SIGNIFICANT\n")
    cat("→ No systematic change in prediction patterns detected.\n")
  }

  cat("\n--- MARGINAL DIFFERENCES ---\n")
  cat("(Positive = base predicted more; Negative = fine-tuned predicted more)\n")
  cat(sprintf("%-15s %12s %18s\n", "Class", "Difference", "Direction"))
  cat(strrep("-", 50), "\n", sep = "")
  for (cls in EMOTION_CLASSES) {
    diff <- result$marginal_differences[[cls]]
    direction <- if (diff > 0) "← Base more" else if (diff < 0) "→ Fine-tuned more" else "No change"
    cat(sprintf("%-15s %12.0f %18s\n", cls, diff, direction))
  }

  cat("\n--- CONTINGENCY TABLE ---\n")
  header <- sprintf("%10s", "")
  for (cls in EMOTION_CLASSES) {
    header <- paste0(header, sprintf("%6s", substr(cls, 1, 4)))
  }
  cat(header, "\n")
  for (i in seq_along(EMOTION_CLASSES)) {
    row_vals <- sprintf("%6d", result$contingency_table[i, ])
    cat(sprintf("%-10s", substr(EMOTION_CLASSES[i], 1, 8)), paste(row_vals, collapse = ""), "\n")
  }
  cat(strrep("=", 70), "\n", sep = "")
}

save_report <- function(result, output_path) {
  payload <- list(
    test_name = "Stuart-Maxwell Test",
    description = "Test for marginal homogeneity across paired categorical predictions",
    hypothesis = list(
      null = "Models have identical marginal prediction distributions",
      alternative = "Models differ in marginal prediction distributions"
    ),
    results = list(
      chi_squared = result$chi_squared,
      degrees_of_freedom = result$degrees_of_freedom,
      p_value = result$p_value,
      significant = result$significant,
      alpha = result$alpha,
      marginal_differences = result$marginal_differences,
      contingency_table = result$contingency_table,
      emotion_classes = EMOTION_CLASSES,
      n_samples = result$n_samples,
      n_agreements = result$n_agreements,
      n_disagreements = result$n_disagreements
    )
  )
  write_json(payload, output_path, pretty = TRUE, auto_unbox = TRUE)
  message("Report saved to: ", output_path)
}

plot_contingency_heatmap <- function(result, output_path = NULL) {
  df <- as.data.frame(as.table(result$contingency_table))
  colnames(df) <- c("base", "finetuned", "count")
  df$base <- factor(df$base, labels = EMOTION_CLASSES)
  df$finetuned <- factor(df$finetuned, labels = EMOTION_CLASSES)
  plot <- ggplot(df, aes(finetuned, base, fill = count)) +
    geom_tile(color = "white") +
    geom_text(aes(label = count), size = 3) +
    scale_fill_gradient(low = "#fee0d2", high = "#de2d26") +
    labs(
      title = sprintf("Prediction Agreement Heatmap (agree: %.1f%%)", result$n_agreements / result$n_samples * 100),
      x = "Fine-tuned model",
      y = "Base model"
    ) +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 8, height = 6, dpi = 150)
    message("Contingency heatmap saved to: ", output_path)
  }
}

plot_marginal_differences <- function(result, output_path = NULL) {
  df <- data.frame(
    class = EMOTION_CLASSES,
    diff = as.numeric(result$marginal_differences)
  )
  plot <- ggplot(df, aes(x = reorder(class, diff), y = diff, fill = diff > 0)) +
    geom_col(color = "black") +
    scale_fill_manual(values = c("TRUE" = "#3182bd", "FALSE" = "#e6550d"), labels = c("Fine-tuned more", "Base more")) +
    labs(title = "Marginal Differences (Base - Fine-tuned)", x = "Class", y = "Difference") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "none")
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 9, height = 5, dpi = 150)
    message("Marginal differences chart saved to: ", output_path)
  }
}

generate_demo_data <- function(n_samples = 2000, seed = 42, effect_size = "medium") {
  set.seed(seed)
  class_weights <- c(0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10)
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = class_weights)
  base_acc <- c(0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80)
  if (effect_size == "none") {
    ft_acc <- base_acc
  } else if (effect_size == "small") {
    ft_acc <- c(0.83, 0.68, 0.74, 0.79, 0.89, 0.89, 0.85, 0.81)
  } else if (effect_size == "large") {
    ft_acc <- c(0.88, 0.82, 0.85, 0.86, 0.85, 0.93, 0.88, 0.87)
  } else {
    ft_acc <- c(0.84, 0.75, 0.80, 0.82, 0.88, 0.91, 0.86, 0.83)
  }
  confusion_map <- list(
    anger = c("fear", "disgust"),
    contempt = c("disgust", "anger"),
    disgust = c("contempt", "anger"),
    fear = c("surprise", "anger"),
    happiness = c("surprise", "neutral"),
    neutral = c("sadness", "happiness"),
    sadness = c("neutral", "fear"),
    surprise = c("fear", "happiness")
  )
  base_pred <- character(n_samples)
  ft_pred <- character(n_samples)
  for (i in seq_len(n_samples)) {
    cls <- y_true[i]
    if (runif(1) < base_acc[match(cls, EMOTION_CLASSES)]) {
      base_pred[i] <- cls
    } else {
      base_pred[i] <- sample(confusion_map[[cls]], 1)
    }
    if (runif(1) < ft_acc[match(cls, EMOTION_CLASSES)]) {
      ft_pred[i] <- cls
    } else {
      ft_pred[i] <- sample(confusion_map[[cls]], 1)
    }
  }
  data.frame(base_pred = base_pred, finetuned_pred = ft_pred, stringsAsFactors = FALSE)
}

load_predictions_csv <- function(path) {
  df <- read.csv(path, stringsAsFactors = FALSE)
  required <- c("base_pred", "finetuned_pred")
  ensure_columns(df, required)
}

load_from_database_pairs <- function(args, cfg) {
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
  ensure_columns(df, c("base_pred", "finetuned_pred"))
}

load_prediction_pairs <- function(args, cfg) {
  if (args$demo) {
    message("Generating synthetic demo data ...")
    return(list(df = generate_demo_data(effect_size = args$`effect-size`), source = "demo"))
  }
  if (!is.null(args$`predictions-csv`)) {
    message("Loading paired predictions from CSV: ", args$`predictions-csv`)
    return(list(df = load_predictions_csv(args$`predictions-csv`), source = "csv"))
  }
  message("Querying Postgres for paired predictions ...")
  df <- load_from_database_pairs(args, cfg)
  list(df = df, source = "database")
}

run_analysis <- function(df, alpha, output_dir = NULL, do_plot = FALSE) {
  result <- stuart_maxwell_test(df$base_pred, df$finetuned_pred, alpha = alpha)
  print_report(result)
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    save_report(result, file.path(output_dir, "stuart_maxwell_results.json"))
    if (do_plot) {
      plot_contingency_heatmap(result, file.path(output_dir, "contingency_heatmap.png"))
      plot_marginal_differences(result, file.path(output_dir, "marginal_differences.png"))
    }
  } else if (do_plot) {
    plot_contingency_heatmap(result)
    plot_marginal_differences(result)
  }
  invisible(result)
}

main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE, help = "Run with synthetic demo data"),
    make_option(c("--effect-size"), type = "character", default = "medium", help = "Demo effect size (none, small, medium, large)"),
    make_option(c("--predictions-csv"), type = "character", default = NULL, help = "CSV with base_pred, finetuned_pred columns"),
    make_option(c("--config"), type = "character", default = NULL, help = "YAML config for DB/query defaults"),
    make_option(c("--db-host"), type = "character", default = NULL, help = "Postgres host"),
    make_option(c("--db-port"), type = "integer", default = NULL, help = "Postgres port"),
    make_option(c("--db-name"), type = "character", default = NULL, help = "Database name"),
    make_option(c("--db-user"), type = "character", default = NULL, help = "Database user"),
    make_option(c("--db-password"), type = "character", default = NULL, help = "Database password"),
    make_option(c("--db-query"), type = "character", default = NULL, help = "SQL query returning base_pred and finetuned_pred"),
    make_option(c("--query-params"), type = "character", default = NULL, help = "JSON object with templated query params"),
    make_option(c("--cache-dir"), type = "character", default = NULL, help = "Directory to cache raw query inputs"),
    make_option(c("--output"), type = "character", default = NULL, help = "Directory to save JSON/plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE, help = "Generate visualization plots"),
    make_option(c("--alpha"), type = "double", default = ALPHA_DEFAULT, help = "Significance level" )
  )
  parser <- OptionParser(option_list = option_list)
  args <- parse_args(parser)
  if (!args$demo && is.null(args$`predictions-csv`) && is.null(args$`db-query`)) {
    cfg_tmp <- read_yaml_config(args$config)
    if (is.null(cfg_tmp$query$text)) {
      print_help(parser)
      stop("Provide --demo, --predictions-csv, or database connection/query options.")
    }
  }
  cfg <- read_yaml_config(args$config)
  data_bundle <- load_prediction_pairs(args, cfg)
  cache_dir <- args$`cache-dir` %||% cfg$output$cache_dir %||% DEFAULT_CACHE_DIR
  if (identical(data_bundle$source, "database")) {
    cache_raw_inputs(data_bundle$df, cache_dir, prefix = "stuart_maxwell_pairs")
  }
  output_dir <- args$output %||% cfg$output$dir %||% DEFAULT_RESULTS_DIR
  run_analysis(data_bundle$df, alpha = args$alpha, output_dir = output_dir, do_plot = args$plot)
}

if (sys.nframe() == 0) {
  main()
}
