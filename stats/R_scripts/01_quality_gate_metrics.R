#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)
  library(jsonlite)
  library(ggplot2)
  library(rlang)
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

QUALITY_GATES <- list(
  macro_f1 = 0.84,
  balanced_accuracy = 0.82,
  f1_neutral = 0.80
)

EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)

NEUTRAL_CLASS <- "neutral"

compute_confusion_matrix <- function(y_true, y_pred) {
  factor_true <- factor(y_true, levels = EMOTION_CLASSES)
  factor_pred <- factor(y_pred, levels = EMOTION_CLASSES)
  cm <- table(factor_true, factor_pred)
  as.matrix(cm)
}

safe_div <- function(num, denom) {
  ifelse(denom == 0, 0, num / denom)
}

compute_metrics <- function(y_true, y_pred) {
  cm <- compute_confusion_matrix(y_true, y_pred)
  tp <- diag(cm)
  fn <- rowSums(cm) - tp
  fp <- colSums(cm) - tp
  tn <- sum(cm) - (tp + fn + fp)

  precision <- safe_div(tp, tp + fp)
  recall <- safe_div(tp, tp + fn)
  f1 <- safe_div(2 * precision * recall, precision + recall)

  macro_f1 <- mean(f1)
  balanced_accuracy <- mean(recall)
  neutral_index <- match(NEUTRAL_CLASS, EMOTION_CLASSES)
  f1_neutral <- f1[neutral_index]

  accuracy <- safe_div(sum(tp), sum(cm))
  macro_precision <- mean(precision)
  macro_recall <- mean(recall)

  list(
    macro_f1 = macro_f1,
    balanced_accuracy = balanced_accuracy,
    f1_neutral = f1_neutral,
    accuracy = accuracy,
    macro_precision = macro_precision,
    macro_recall = macro_recall,
    per_class = list(
      precision = setNames(as.numeric(precision), EMOTION_CLASSES),
      recall = setNames(as.numeric(recall), EMOTION_CLASSES),
      f1 = setNames(as.numeric(f1), EMOTION_CLASSES)
    ),
    confusion_matrix = cm
  )
}

evaluate_gates <- function(metrics) {
  gates <- list(
    macro_f1 = metrics$macro_f1 >= QUALITY_GATES$macro_f1,
    balanced_accuracy = metrics$balanced_accuracy >= QUALITY_GATES$balanced_accuracy,
    f1_neutral = metrics$f1_neutral >= QUALITY_GATES$f1_neutral
  )
  list(gates = gates, overall = all(unlist(gates)))
}

print_report <- function(metrics, gate_eval, model_name = "model") {
  cat(strrep("=", 70), "\n", sep = "")
  cat("QUALITY GATE METRICS REPORT:", model_name, "\n")
  cat(strrep("=", 70), "\n\n", sep = "")

  cat("--- QUALITY GATE EVALUATION ---\n")
  header <- sprintf("%-25s %10s %12s %10s\n", "Metric", "Value", "Threshold", "Status")
  cat(header)
  cat(strrep("-", 60), "\n", sep = "")

  format_row <- function(name, value, threshold, pass) {
    status <- if (pass) "PASS ✓" else "FAIL ✗"
    sprintf("%-25s %10.4f %12.2f %10s\n", name, value, threshold, status)
  }

  cat(format_row("Macro F1", metrics$macro_f1, QUALITY_GATES$macro_f1, gate_eval$gates$macro_f1))
  cat(format_row("Balanced Accuracy", metrics$balanced_accuracy, QUALITY_GATES$balanced_accuracy, gate_eval$gates$balanced_accuracy))
  cat(format_row("F1 (Neutral)", metrics$f1_neutral, QUALITY_GATES$f1_neutral, gate_eval$gates$f1_neutral))
  cat(strrep("-", 60), "\n", sep = "")
  overall_status <- if (gate_eval$overall) "PASS ✓" else "FAIL ✗"
  cat(sprintf("%-25s %10s %12s %10s\n", "OVERALL", "", "", overall_status))

  cat("\n--- ADDITIONAL METRICS ---\n")
  cat(sprintf("Accuracy:         %.4f\n", metrics$accuracy))
  cat(sprintf("Macro Precision:  %.4f\n", metrics$macro_precision))
  cat(sprintf("Macro Recall:     %.4f\n", metrics$macro_recall))

  cat("\n--- PER-CLASS F1 SCORES ---\n")
  cat(sprintf("%-15s %10s %12s %10s\n", "Class", "F1", "Precision", "Recall"))
  cat(strrep("-", 55), "\n", sep = "")
  for (cls in EMOTION_CLASSES) {
    marker <- if (cls == NEUTRAL_CLASS) " ← Phase 2 baseline" else ""
    cat(sprintf(
      "%-15s %10.4f %12.4f %10.4f%s\n",
      cls,
      metrics$per_class$f1[[cls]],
      metrics$per_class$precision[[cls]],
      metrics$per_class$recall[[cls]],
      marker
    ))
  }

  cat("\n--- CONFUSION MATRIX ---\n")
  cat("(Rows: True labels, Columns: Predicted labels)\n\n")
  header <- sprintf("%10s", "")
  for (cls in EMOTION_CLASSES) {
    header <- paste0(header, sprintf("%6s", substr(cls, 1, 4)))
  }
  cat(header, "\n")
  for (i in seq_along(EMOTION_CLASSES)) {
    row_str <- sprintf("%-10s", substr(EMOTION_CLASSES[i], 1, 8))
    row_vals <- sprintf("%6d", metrics$confusion_matrix[i, ])
    cat(row_str, paste(row_vals, collapse = ""), "\n")
  }
  cat(strrep("=", 70), "\n", sep = "")
}

save_report <- function(metrics, gate_eval, output_path, model_name = "model") {
  per_class <- list(
    f1 = metrics$per_class$f1,
    precision = metrics$per_class$precision,
    recall = metrics$per_class$recall
  )
  data <- list(
    model_name = model_name,
    quality_gates = list(
      thresholds = QUALITY_GATES,
      results = gate_eval$gates,
      overall_pass = gate_eval$overall
    ),
    metrics = list(
      macro_f1 = metrics$macro_f1,
      balanced_accuracy = metrics$balanced_accuracy,
      f1_neutral = metrics$f1_neutral,
      accuracy = metrics$accuracy,
      macro_precision = metrics$macro_precision,
      macro_recall = metrics$macro_recall,
      per_class = per_class,
      confusion_matrix = metrics$confusion_matrix
    ),
    emotion_classes = EMOTION_CLASSES
  )
  write_json(data, output_path, pretty = TRUE, auto_unbox = TRUE)
  message("Report saved to: ", output_path)
}

plot_confusion_matrix <- function(metrics, output_path = NULL) {
  cm <- metrics$confusion_matrix
  df <- as.data.frame(as.table(cm))
  colnames(df) <- c("true", "pred", "n")
  plot <- ggplot(df, aes(pred, true, fill = n)) +
    geom_tile(color = "white") +
    geom_text(aes(label = n), color = "black", size = 3) +
    scale_fill_gradient(low = "#e0f3f8", high = "#08589e") +
    labs(title = "Confusion Matrix", x = "Predicted", y = "True") +
    theme_minimal()
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 8, height = 6, dpi = 150)
    message("Confusion matrix saved to: ", output_path)
  }
}

plot_per_class_f1 <- function(metrics, output_path = NULL) {
  df <- data.frame(
    class = EMOTION_CLASSES,
    f1 = as.numeric(metrics$per_class$f1)
  )
  df$is_neutral <- df$class == NEUTRAL_CLASS
  plot <- ggplot(df, aes(x = reorder(class, -f1), y = f1, fill = is_neutral)) +
    geom_col(color = "black") +
    geom_hline(yintercept = 0.80, linetype = "dashed", color = "red") +
    scale_fill_manual(values = c("TRUE" = "#1f78b4", "FALSE" = "#a6cee3"), guide = "none") +
    labs(title = "Per-Class F1 Scores", x = "Class", y = "F1 Score") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  if (is.null(output_path)) {
    print(plot)
  } else {
    ggsave(output_path, plot, width = 9, height = 5, dpi = 150)
    message("Per-class F1 chart saved to: ", output_path)
  }
}

generate_demo_data <- function(n_samples = 2000, seed = 42) {
  set.seed(seed)
  weights <- c(0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10)
  y_true <- sample(EMOTION_CLASSES, size = n_samples, replace = TRUE, prob = weights)
  class_acc <- c(0.82, 0.70, 0.75, 0.78, 0.90, 0.88, 0.84, 0.80)
  names(class_acc) <- EMOTION_CLASSES
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
  y_pred <- character(length = n_samples)
  for (i in seq_len(n_samples)) {
    cls <- y_true[i]
    if (runif(1) < class_acc[[cls]]) {
      y_pred[i] <- cls
    } else {
      y_pred[i] <- sample(confusion_map[[cls]], 1)
    }
  }
  data.frame(y_true = y_true, y_pred = y_pred)
}

load_predictions <- function(path) {
  df <- read.csv(path, stringsAsFactors = FALSE)
  if (!all(c("y_true", "y_pred") %in% names(df))) {
    abort("Prediction file must contain 'y_true' and 'y_pred' columns.")
  }
  df
}

load_from_database <- function(args, cfg) {
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
  ensure_columns(df, c("y_true", "y_pred"))
}

load_data_source <- function(args, cfg) {
  if (args$demo) {
    message("Generating synthetic demo data ...")
    return(list(df = generate_demo_data(), source = "demo"))
  }
  if (!is.null(args$`predictions-csv`)) {
    message("Loading predictions from CSV: ", args$`predictions-csv`)
    return(list(df = load_predictions(args$`predictions-csv`), source = "csv", path = args$`predictions-csv`))
  }
  message("Querying Postgres for predictions ...")
  df <- load_from_database(args, cfg)
  list(df = df, source = "database")
}

run_analysis <- function(df, model_name = "model", output_dir = NULL, do_plot = FALSE) {
  metrics <- compute_metrics(df$y_true, df$y_pred)
  gate_eval <- evaluate_gates(metrics)
  print_report(metrics, gate_eval, model_name)
  if (!is.null(output_dir)) {
    dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
    json_path <- file.path(output_dir, paste0(model_name, "_quality_gate_metrics.json"))
    save_report(metrics, gate_eval, json_path, model_name)
    if (do_plot) {
      plot_confusion_matrix(metrics, file.path(output_dir, paste0(model_name, "_confusion_matrix.png")))
      plot_per_class_f1(metrics, file.path(output_dir, paste0(model_name, "_per_class_f1.png")))
    }
  } else if (do_plot) {
    plot_confusion_matrix(metrics)
    plot_per_class_f1(metrics)
  }
  invisible(list(metrics = metrics, gate_eval = gate_eval))
}

main <- function() {
  option_list <- list(
    make_option(c("--demo"), action = "store_true", default = FALSE, help = "Run with synthetic demo data"),
    make_option(c("--predictions-csv"), type = "character", default = NULL, help = "CSV file with y_true,y_pred columns"),
    make_option(c("--config"), type = "character", default = NULL, help = "YAML config for DB/query defaults"),
    make_option(c("--db-host"), type = "character", default = NULL, help = "Postgres host"),
    make_option(c("--db-port"), type = "integer", default = NULL, help = "Postgres port"),
    make_option(c("--db-name"), type = "character", default = NULL, help = "Database name"),
    make_option(c("--db-user"), type = "character", default = NULL, help = "Database user"),
    make_option(c("--db-password"), type = "character", default = NULL, help = "Database password"),
    make_option(c("--db-query"), type = "character", default = NULL, help = "SQL query to fetch predictions"),
    make_option(c("--query-params"), type = "character", default = NULL, help = "JSON object with query parameters"),
    make_option(c("--cache-dir"), type = "character", default = NULL, help = "Directory to cache raw query inputs"),
    make_option(c("--output"), type = "character", default = NULL, help = "Directory to save JSON/plots"),
    make_option(c("--plot"), action = "store_true", default = FALSE, help = "Generate plots"),
    make_option(c("--model-name"), type = "character", default = "model", help = "Name of evaluated model")
  )
  parser <- OptionParser(option_list = option_list)
  args <- parse_args(parser)

  cfg <- read_yaml_config(args$config)

  if (!args$demo && is.null(args$`predictions-csv`) && is.null(args$`db-query`) && is.null(cfg$query$text)) {
    print_help(parser)
    stop("Provide --demo, --predictions-csv, or database connection/query options.")
  }

  data_bundle <- load_data_source(args, cfg)
  cache_dir <- args$`cache-dir` %||% cfg$output$cache_dir %||% DEFAULT_CACHE_DIR
  if (identical(data_bundle$source, "database")) {
    cache_raw_inputs(data_bundle$df, cache_dir, prefix = paste0(args$`model-name`, "_predictions"))
  }

  output_dir <- args$output %||% cfg$output$dir %||% DEFAULT_RESULTS_DIR
  run_analysis(
    data_bundle$df,
    model_name = if (data_bundle$source == "demo") "demo_model" else args$`model-name`,
    output_dir = output_dir,
    do_plot = args$plot
  )
}

if (sys.nframe() == 0) {
  main()
}
