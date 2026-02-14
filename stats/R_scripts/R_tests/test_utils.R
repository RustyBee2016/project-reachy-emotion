if (!exists("TESTS_DIR")) {
  stop("TESTS_DIR must be defined before sourcing test_utils.R", call. = FALSE)
}

suppressPackageStartupMessages({
  library(jsonlite)
})

EMOTION_CLASSES <- c(
  "anger", "contempt", "disgust", "fear",
  "happiness", "neutral", "sadness", "surprise"
)

REPO_ROOT <- normalizePath(file.path(TESTS_DIR, "..", "..", ".."), mustWork = TRUE)
SCRIPTS_DIR <- file.path(REPO_ROOT, "stats", "R_scripts")
RESULTS_DIR <- file.path(REPO_ROOT, "stats", "results")
TEST_OUTPUT_ROOT <- file.path(RESULTS_DIR, "test_runs")
if (!dir.exists(TEST_OUTPUT_ROOT)) {
  dir.create(TEST_OUTPUT_ROOT, recursive = TRUE, showWarnings = FALSE)
}

timestamp_tag <- function(prefix) {
  paste0(prefix, "_", format(Sys.time(), "%Y%m%d_%H%M%S"), "_", sprintf("%04d", sample(0:9999, 1)))
}

create_output_dir <- function(prefix) {
  dir_path <- file.path(TEST_OUTPUT_ROOT, timestamp_tag(prefix))
  dir.create(dir_path, recursive = TRUE, showWarnings = FALSE)
  dir_path
}

write_predictions_csv <- function(path, n = 400, accuracy = 0.8) {
  set.seed(42)
  weights <- c(0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10)
  y_true <- sample(EMOTION_CLASSES, size = n, replace = TRUE, prob = weights)
  y_pred <- y_true
  n_noise <- round((1 - accuracy) * n)
  if (n_noise > 0) {
    idx <- sample(seq_len(n), n_noise)
    y_pred[idx] <- sample(EMOTION_CLASSES, n_noise, replace = TRUE)
  }
  data <- data.frame(y_true = y_true, y_pred = y_pred)
  write.csv(data, path, row.names = FALSE)
  path
}

write_paired_predictions_csv <- function(path, n = 1000, base_acc = 0.82, ft_acc = 0.88) {
  set.seed(43)
  y_true <- sample(EMOTION_CLASSES, size = n, replace = TRUE)
  base_pred <- y_true
  ft_pred <- y_true
  base_noise <- sample(seq_len(n), round((1 - base_acc) * n))
  ft_noise <- sample(seq_len(n), round((1 - ft_acc) * n))
  base_pred[base_noise] <- sample(EMOTION_CLASSES, length(base_noise), replace = TRUE)
  ft_pred[ft_noise] <- sample(EMOTION_CLASSES, length(ft_noise), replace = TRUE)
  df <- data.frame(base_pred = base_pred, finetuned_pred = ft_pred)
  write.csv(df, path, row.names = FALSE)
  path
}

write_fold_metrics_csv <- function(path, n_folds = 6) {
  set.seed(44)
  records <- list()
  idx <- 1
  for (cls in EMOTION_CLASSES) {
    base_mean <- runif(1, 0.65, 0.90)
    ft_mean <- pmin(1, pmax(0, base_mean + runif(1, -0.03, 0.08)))
    base_scores <- pmin(pmax(rnorm(n_folds, base_mean, 0.03), 0), 1)
    ft_scores <- pmin(pmax(rnorm(n_folds, ft_mean, 0.03), 0), 1)
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
  df <- do.call(rbind, records)
  write.csv(df, path, row.names = FALSE)
  path
}

run_rscript <- function(script_name, args = character()) {
  script_path <- normalizePath(file.path(SCRIPTS_DIR, script_name), mustWork = TRUE)
  output <- system2("Rscript", c(script_path, args), stdout = TRUE, stderr = TRUE)
  status <- attr(output, "status")
  if (is.null(status)) {
    status <- 0
  }
  if (status != 0) {
    stop(sprintf("Command failed (script: %s)\nOutput:\n%s", script_name, paste(output, collapse = "\n")), call. = FALSE)
  }
  invisible(output)
}

assert_files_exist <- function(paths) {
  missing <- paths[!file.exists(paths)]
  if (length(missing) > 0) {
    stop(sprintf("Expected output files missing: %s", paste(missing, collapse = ", " )), call. = FALSE)
  }
  TRUE
}
