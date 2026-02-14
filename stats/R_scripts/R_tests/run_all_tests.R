TESTS_DIR <- normalizePath(dirname(sys.frame(1)$ofile %||% sys.frames()[[length(sys.frames())]]$ofile %||% "."), mustWork = FALSE)
if (is.na(TESTS_DIR) || TESTS_DIR == "") {
  TESTS_DIR <- getwd()
}

source(file.path(TESTS_DIR, "test_quality_gate_metrics.R"))
source(file.path(TESTS_DIR, "test_stuart_maxwell.R"))
source(file.path(TESTS_DIR, "test_perclass_paired_ttests.R"))

run_all_tests <- function() {
  message("Running simulated-data R script tests...\n")
  run_quality_gate_metrics_tests()
  run_stuart_maxwell_tests()
  run_perclass_paired_ttests()
  message("All R script tests passed. Outputs under stats/results/test_runs/\n")
}

if (sys.nframe() == 0) {
  run_all_tests()
}
