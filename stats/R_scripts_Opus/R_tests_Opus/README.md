# Enhanced R Statistical Scripts — Comprehensive Test Suite

This directory contains comprehensive tests for the enhanced R statistical scripts in `stats/R_scripts_Opus/`. The test suite validates statistical accuracy, error handling, performance, and feature completeness against the original Python implementations.

## Test Architecture

### Test Categories

1. **Unit Tests** (`test_unit_*.R`)
   - Individual function testing with edge cases
   - Statistical accuracy validation
   - Error handling verification

2. **Integration Tests** (`test_integration_*.R`)
   - End-to-end workflow testing
   - CLI interface validation
   - File I/O and database connectivity

3. **Performance Tests** (`test_performance_*.R`)
   - Execution time benchmarks
   - Memory usage profiling
   - Scalability testing

4. **Accuracy Tests** (`test_accuracy_*.R`)
   - Cross-validation against Python implementations
   - Statistical equivalence testing
   - Numerical precision validation

### Test Data

- **Synthetic Data**: Generated with known statistical properties
- **Reference Data**: Validated datasets with expected outcomes
- **Edge Cases**: Boundary conditions and error scenarios
- **Performance Data**: Large-scale datasets for benchmarking

## Test Execution

### Run All Tests
```powershell
Rscript stats/R_scripts_Opus/R_tests_Opus/run_all_enhanced_tests.R
```

### Run Specific Test Categories
```powershell
# Unit tests only
Rscript stats/R_scripts_Opus/R_tests_Opus/run_unit_tests.R

# Performance benchmarks
Rscript stats/R_scripts_Opus/R_tests_Opus/run_performance_tests.R

# Accuracy validation
Rscript stats/R_scripts_Opus/R_tests_Opus/run_accuracy_tests.R
```

### Individual Script Tests
```powershell
# Quality gate metrics
Rscript stats/R_scripts_Opus/R_tests_Opus/test_quality_gate_enhanced.R

# Stuart-Maxwell test
Rscript stats/R_scripts_Opus/R_tests_Opus/test_stuart_maxwell_enhanced.R

# Per-class paired t-tests
Rscript stats/R_scripts_Opus/R_tests_Opus/test_perclass_enhanced.R
```

## Test Coverage

### Statistical Functions
- [x] Confusion matrix computation
- [x] Metric calculations (F1, precision, recall, balanced accuracy)
- [x] Quality gate evaluation
- [x] Stuart-Maxwell test implementation
- [x] Paired t-test with multiple comparison correction
- [x] Effect size calculations
- [x] Confidence interval estimation

### Error Handling
- [x] Input validation
- [x] Edge case handling
- [x] Graceful failure modes
- [x] Informative error messages

### Performance
- [x] Large dataset handling
- [x] Memory efficiency
- [x] Execution time benchmarks
- [x] Scalability testing

### Features
- [x] CLI interface completeness
- [x] Output format validation
- [x] Visualization generation
- [x] Interactive plot creation
- [x] Database connectivity
- [x] Configuration file parsing

## Quality Metrics

### Test Success Criteria
- **Statistical Accuracy**: ≤ 1e-10 difference from reference implementations
- **Performance**: ≤ 2x execution time of original R scripts
- **Memory**: ≤ 1.5x memory usage of original implementations
- **Coverage**: ≥ 95% function coverage
- **Error Handling**: 100% error scenario coverage

### Benchmarking Results
Results are automatically generated and stored in `stats/results/test_runs_opus/benchmarks/`

## Dependencies

### Required R Packages
```r
# Core testing
library(testthat)
library(bench)
library(profvis)

# Statistical validation
library(assertthat)
library(logger)

# Enhanced functionality
library(plotly)
library(viridis)
library(effsize)
library(broom)
```

### Installation
```r
install.packages(c(
  "testthat", "bench", "profvis", "assertthat", "logger",
  "plotly", "viridis", "effsize", "broom", "corrplot"
))
```

## Continuous Integration

Tests are designed to run in CI/CD environments with:
- Automated test execution
- Performance regression detection
- Statistical accuracy validation
- Coverage reporting
- Benchmark tracking

## Troubleshooting

### Common Issues
1. **Missing Dependencies**: Run package installation script
2. **Memory Limits**: Adjust test data sizes in configuration
3. **Timeout Issues**: Increase test timeout limits
4. **Platform Differences**: Check OS-specific test configurations

### Debug Mode
Set `LOG_LEVEL=DEBUG` environment variable for detailed test execution logs.

## Contributing

When adding new tests:
1. Follow naming convention: `test_[category]_[component].R`
2. Include comprehensive documentation
3. Add both positive and negative test cases
4. Update this README with new test coverage
5. Ensure tests run in < 30 seconds individually
