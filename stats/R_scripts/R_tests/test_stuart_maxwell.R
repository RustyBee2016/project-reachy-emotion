TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% sys.frames()[[length(sys.frames())]]$ofile %||% ""), mustWork = FALSE)
if (is.na(TESTS_DIR) || TESTS_DIR == "") {
  TESTS_DIR <- getwd()
}
source(file.path(TESTS_DIR, "test_utils.R"))

run_stuart_maxwell_tests <- function() {
  message("[TEST] 02_stuart_maxwell_test.R — demo mode")
  demo_output <- create_output_dir("stuart_demo")
  run_rscript(
    "02_stuart_maxwell_test.R",
    c("--demo", "--effect-size", "medium", "--output", demo_output, "--plot")
  )
  assert_files_exist(c(
    file.path(demo_output, "stuart_maxwell_results.json"),
    file.path(demo_output, "contingency_heatmap.png"),
    file.path(demo_output, "marginal_differences.png")
  ))

  message("[TEST] 02_stuart_maxwell_test.R — CSV ingestion")
  csv_path <- file.path(demo_output, "paired_predictions.csv")
  write_paired_predictions_csv(csv_path)
  csv_output <- create_output_dir("stuart_csv")
  run_rscript(
    "02_stuart_maxwell_test.R",
    c(
      "--predictions-csv", csv_path,
      "--output", csv_output
    )
  )
  assert_files_exist(c(
    file.path(csv_output, "stuart_maxwell_results.json")
  ))

  message("[PASS] stuart_maxwell tests completed\n")
}

if (sys.nframe() == 0) {
  run_stuart_maxwell_tests()
}
