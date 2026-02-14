TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% sys.frames()[[length(sys.frames())]]$ofile %||% ""), mustWork = FALSE)
if (is.na(TESTS_DIR) || TESTS_DIR == "") {
  TESTS_DIR <- getwd()
}
source(file.path(TESTS_DIR, "test_utils.R"))

run_quality_gate_metrics_tests <- function() {
  message("[TEST] 01_quality_gate_metrics.R — demo mode")
  demo_output <- create_output_dir("quality_gate_demo")
  run_rscript(
    "01_quality_gate_metrics.R",
    c("--demo", "--output", demo_output, "--plot")
  )
  assert_files_exist(c(
    file.path(demo_output, "demo_model_quality_gate_metrics.json"),
    file.path(demo_output, "demo_model_confusion_matrix.png"),
    file.path(demo_output, "demo_model_per_class_f1.png")
  ))

  message("[TEST] 01_quality_gate_metrics.R — CSV ingestion")
  csv_path <- file.path(demo_output, "sample_predictions.csv")
  write_predictions_csv(csv_path)
  csv_output <- create_output_dir("quality_gate_csv")
  run_rscript(
    "01_quality_gate_metrics.R",
    c(
      "--predictions-csv", csv_path,
      "--model-name", "csv_model",
      "--output", csv_output
    )
  )
  assert_files_exist(c(
    file.path(csv_output, "csv_model_quality_gate_metrics.json")
  ))

  message("[PASS] quality_gate_metrics tests completed\n")
}

if (sys.nframe() == 0) {
  run_quality_gate_metrics_tests()
}
