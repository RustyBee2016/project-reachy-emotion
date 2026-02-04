# R Statistical Scripts — Test Strategy (Simulated Data)

The R scripts under `stats/R_scripts/` share a common CLI surface and offer built-in synthetic data generators. The test suite in this folder exercises those entry points using simulated data only (No Postgres access needed).

## Test Scenarios

| Script | Test Mode | Purpose |
| --- | --- | --- |
| `01_quality_gate_metrics.R` | `--demo` | Verifies metrics + plots run end-to-end with synthetic predictions |
| `01_quality_gate_metrics.R` | `--predictions-csv` | Confirms CSV ingestion path works by pointing to generated sample predictions |
| `02_stuart_maxwell_test.R` | `--demo --effect-size medium` | Validates contingency + JSON outputs |
| `02_stuart_maxwell_test.R` | `--predictions-csv` | Ensures paired CSV ingestion works |
| `03_perclass_paired_ttests.R` | `--demo --effect-pattern mixed --n-folds 6` | Checks per-class pipeline using synthetic fold metrics |
| `03_perclass_paired_ttests.R` | `--metrics-csv` | Confirms fold-metric CSV ingestion |

## Test Harness

Each `test_*.R` file:

1. Generates a temporary working directory under `stats/results/test_runs_<timestamp>`.
2. Creates a lightweight CSV fixture (when needed) using the script’s own demo helpers.
3. Invokes the target script via `system2("Rscript", ...)` and asserts exit status 0.
4. Validates required outputs exist (JSON report, optional plots) and logs concise status.

This keeps the tests fast (<5s each) while covering every CLI path we rely on (demo and CSV). For database inputs, we rely on the shared ingestion helper being exercised indirectly through CSV (same schema) plus config parsing.

Run all tests from repo root:

```powershell
Rscript stats/R_scripts/R_tests/run_all_tests.R
```
