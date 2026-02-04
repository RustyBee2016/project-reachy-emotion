TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% sys.frames()[[length(sys.frames())]]$ofile %||% ""), mustWork = FALSE)
if (is.na(TESTS_DIR) || TESTS_DIR == "") {
  TESTS_DIR <- getwd()
}
source(file.path(TESTS_DIR, "test_utils.R"))

run_perclass_paired_ttests <- function() {
  message("[TEST] 03_perclass_paired_ttests.R — demo mode")
  demo_output <- create_output_dir("perclass_demo")
  run_rscript(
    "03_perclass_paired_ttests.R",
    c(
      "--demo",
      "--effect-pattern", "mixed",
      "--n-folds", "6",
      "--output", demo_output,
      "--plot"
    )
  )
  assert_files_exist(c(
    file.path(demo_output, "perclass_paired_ttests.json"),
    file.path(demo_output, "perclass_comparison.png"),
    file.path(demo_output, "perclass_effect_sizes.png")
  ))

  message("[TEST] 03_perclass_paired_ttests.R — CSV ingestion")
  csv_path <- file.path(demo_output, "fold_metrics.csv")
  write_fold_metrics_csv(csv_path, n_folds = 6)
  csv_output <- create_output_dir("perclass_csv")
  run_rscript(
    "03_perclass_paired_ttests.R",
    c(
      "--metrics-csv", csv_path,
      "--alpha", "0.05",
      "--output", csv_output
    )
  )
  assert_files_exist(c(
    file.path(csv_output, "perclass_paired_ttests.json")
  ))

  message("[PASS] perclass_paired_ttests tests completed\n")
}

if (sys.nframe() == 0) {
  run_perclass_paired_ttests()
}
