# Tutorial 06: Running the Full Analysis Pipeline

This tutorial covers how to use `run_analysis.py` to execute the complete Phase 1 statistical analysis, from data loading to report generation.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Run the analysis with demo data
2. Prepare and load custom data files
3. Understand command-line options
4. Export and interpret results

---

## Part 1: Quick Start with Demo Data

### From Python

```python
from stats.Opus4.5_stats.phase_1.run_analysis import generate_demo_data, run_analysis

# Generate demo data (matches research paper results)
data = generate_demo_data()

# Run the complete analysis
results = run_analysis(
    data,
    output_dir="demo_results/",
    show_plots=True,
    alpha=0.05
)
```

### From Command Line

```bash
# Run with demo data
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo --output demo_results/

# Run without showing plots
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo --output results/ --no-plots
```

---

## Part 2: Understanding Demo Data

### What `generate_demo_data()` Creates

```python
data = generate_demo_data()

# Let's examine it:
print(f"Samples: {len(data['y_true'])}")          # 500
print(f"Classes: {data['num_classes']}")           # 2
print(f"Class names: {data['class_names']}")       # ['happy', 'sad']
print(f"Model A: {data['model_a_name']}")          # ResNet-50
print(f"Model B: {data['model_b_name']}")          # EfficientNet-B0
```

### Why Demo Data?

Demo data serves two purposes:
1. **Verification**: Results should match the research paper
2. **Learning**: You can run the analysis without collecting real data

### The Random Seed

```python
def generate_demo_data():
    np.random.seed(42)  # Always produces same results
    ...
```

Using a fixed seed ensures reproducibility.

---

## Part 3: Preparing Custom Data

### Data Format (JSON)

Create a file `my_data.json`:

```json
{
    "y_true": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    "pred_a": [0, 1, 0, 1, 0, 0, 0, 1, 1, 1],
    "pred_b": [0, 0, 0, 1, 1, 1, 0, 1, 0, 1],
    "class_names": ["happy", "sad"],
    "num_classes": 2,
    "model_a_name": "My ResNet",
    "model_b_name": "My EfficientNet",
    "f1_folds_a": {
        "0": [0.87, 0.86, 0.88, 0.85, 0.87],
        "1": [0.84, 0.85, 0.86, 0.83, 0.85]
    },
    "f1_folds_b": {
        "0": [0.82, 0.81, 0.83, 0.80, 0.82],
        "1": [0.80, 0.81, 0.82, 0.79, 0.81]
    }
}
```

### Required vs. Optional Fields

| Field | Required? | Default if Missing |
|-------|-----------|-------------------|
| `y_true` | ✓ Yes | — |
| `pred_a` | ✓ Yes | — |
| `pred_b` | ✓ Yes | — |
| `class_names` | No | ["Class 0", "Class 1", ...] |
| `num_classes` | No | Inferred from unique y_true values |
| `model_a_name` | No | "Model A" |
| `model_b_name` | No | "Model B" |
| `f1_folds_a` | No | Skips paired tests |
| `f1_folds_b` | No | Skips paired tests |

### Loading Custom Data

```bash
# From command line
python -m stats.Opus4.5_stats.phase_1.run_analysis --data my_data.json --output results/
```

```python
# From Python
from stats.Opus4.5_stats.phase_1.run_analysis import load_data, run_analysis

data = load_data("my_data.json")
results = run_analysis(data, output_dir="results/")
```

---

## Part 4: Command-Line Options

### Full Usage

```bash
python -m stats.Opus4.5_stats.phase_1.run_analysis [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--demo` | | Use demo data |
| `--data PATH` | | Load data from JSON file |
| `--output DIR` | `-o` | Output directory for results |
| `--alpha FLOAT` | | Significance level (default: 0.05) |
| `--no-plots` | | Disable plot display |

### Examples

```bash
# Demo mode, save to results/
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo -o results/

# Custom data, stricter significance
python -m stats.Opus4.5_stats.phase_1.run_analysis --data exp1.json --alpha 0.01

# Run silently (no plots)
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo --no-plots -o batch_results/
```

---

## Part 5: Understanding the Output

### Console Output Structure

```
======================================================================
PHASE 1 STATISTICAL ANALYSIS
======================================================================
Model A: ResNet-50
Model B: EfficientNet-B0
Samples: 500
Classes: 2 (happy, sad)
Alpha: 0.05

======================================================================
SECTION 1: UNIVARIATE METRICS
======================================================================
[Metrics for each model...]

======================================================================
SECTION 2: MULTIVARIATE MODEL COMPARISON
======================================================================
[Stuart-Maxwell, McNemar, Kappa results...]

======================================================================
SECTION 3: PAIRED T-TESTS (Cross-Validation)
======================================================================
[Paired test results with BH correction...]

======================================================================
SECTION 4: VISUALIZATIONS
======================================================================
Generated 7 plots.

======================================================================
ANALYSIS SUMMARY
======================================================================
ResNet-50:
  Macro F1: 0.8650
  Balanced Accuracy: 0.8700
  Gate A: PASSED

EfficientNet-B0:
  Macro F1: 0.8350
  Balanced Accuracy: 0.8500
  Gate A: FAILED

Comparison:
  Stuart-Maxwell p-value: 0.3173 (not significant)
  Cohen's Kappa: 0.7200 (Substantial)
```

### Output Files

When you specify `--output`:

```
results/
├── results.json          # All metrics in machine-readable format
└── plots/
    ├── confusion_matrix_resnet-50.png
    ├── confusion_matrix_efficientnet-b0.png
    ├── f1_comparison.png
    ├── contingency_table.png
    ├── marginal_differences.png
    ├── effect_sizes.png
    └── mcnemar_results.png
```

---

## Part 6: The Results JSON

### Structure

```json
{
    "timestamp": "2025-01-31T12:00:00.000000",
    "univariate": {
        "model_a": {
            "confusion_matrix": [[45, 5], [5, 45]],
            "precision": {"0": 0.9, "1": 0.9},
            "recall": {"0": 0.9, "1": 0.9},
            "f1": {"0": 0.9, "1": 0.9},
            "macro_f1": 0.9,
            "balanced_accuracy": 0.9
        },
        "model_b": { ... }
    },
    "gate_a": {
        "model_a": {"passed": true, "failures": []},
        "model_b": {"passed": false, "failures": ["Macro F1 0.8350 < 0.84"]}
    },
    "stuart_maxwell": {
        "statistic": 1.0,
        "p_value": 0.3173,
        "significant": false
    },
    "mcnemar": [
        {"class_name": "happy", "p_value": 0.25, "winner": null},
        {"class_name": "sad", "p_value": 0.50, "winner": null}
    ],
    "cohens_kappa": {
        "kappa": 0.72,
        "interpretation": "Substantial"
    },
    "paired_tests": [
        {"class_name": "happy", "cohens_d": 0.85, "significant_corrected": true},
        {"class_name": "sad", "cohens_d": 0.92, "significant_corrected": true}
    ]
}
```

### Reading Results Programmatically

```python
import json

with open("results/results.json", "r") as f:
    results = json.load(f)

# Check if Model A passed Gate A
if results["gate_a"]["model_a"]["passed"]:
    print("Model A is ready for deployment!")
else:
    print("Model A failed Gate A:")
    for failure in results["gate_a"]["model_a"]["failures"]:
        print(f"  - {failure}")

# Get macro F1 difference
f1_a = results["univariate"]["model_a"]["macro_f1"]
f1_b = results["univariate"]["model_b"]["macro_f1"]
print(f"F1 difference: {f1_a - f1_b:+.4f}")
```

---

## Part 7: Programmatic Access to Results

### The Return Value

`run_analysis()` returns a dictionary:

```python
results = run_analysis(data, ...)

# Access individual components:
univariate_a = results["results_a"]        # UnivariateResults
univariate_b = results["results_b"]        # UnivariateResults
gate_a = results["gate_a_result_a"]        # GateAResult
contingency = results["contingency_table"]  # np.ndarray
stuart = results["stuart_maxwell_result"]   # StuartMaxwellResult
mcnemar = results["mcnemar_results"]        # List[McNemarResult]
kappa = results["kappa_result"]             # KappaResult
paired = results["paired_results"]          # List[PairedTestResult]
figures = results["figures"]                # Dict[str, Figure]
```

### Example: Extract Key Findings

```python
results = run_analysis(data, output_dir="results/", show_plots=False)

# Summary statistics
print("=== Key Findings ===")
print(f"Model A Macro F1: {results['results_a'].macro_f1:.4f}")
print(f"Model B Macro F1: {results['results_b'].macro_f1:.4f}")
print(f"Model A Gate A: {'PASS' if results['gate_a_result_a'].passed else 'FAIL'}")
print(f"Model B Gate A: {'PASS' if results['gate_a_result_b'].passed else 'FAIL'}")

# Statistical comparison
sm = results['stuart_maxwell_result']
print(f"\nStuart-Maxwell: χ²={sm.statistic:.2f}, p={sm.p_value:.4f}")

kappa = results['kappa_result']
print(f"Cohen's Kappa: κ={kappa.kappa:.3f} ({kappa.interpretation})")

# Per-class winners
for r in results['mcnemar_results']:
    if r.significant:
        print(f"  {r.class_name}: {r.winner} significantly better")
```

---

## Part 8: Error Handling

### Common Errors and Solutions

#### Missing Data File
```
FileNotFoundError: Data file not found: missing.json
```
**Solution**: Check the file path.

#### Missing Required Fields
```
ValueError: Missing required field: y_true
```
**Solution**: Ensure your JSON has `y_true`, `pred_a`, and `pred_b`.

#### Mismatched Array Lengths
```
ValueError: Array lengths must match. Got y_true=100, pred_a=99
```
**Solution**: Ensure all arrays have the same length.

### Robust Usage Pattern

```python
try:
    data = load_data("my_data.json")
    results = run_analysis(data, output_dir="results/")
except FileNotFoundError as e:
    print(f"Data file not found: {e}")
except ValueError as e:
    print(f"Invalid data format: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Part 9: Batch Processing

### Running Multiple Analyses

```python
import os
from stats.Opus4.5_stats.phase_1.run_analysis import load_data, run_analysis

data_files = ["exp1.json", "exp2.json", "exp3.json"]

for data_file in data_files:
    exp_name = os.path.splitext(data_file)[0]
    
    print(f"\n{'='*50}")
    print(f"Processing: {exp_name}")
    print(f"{'='*50}")
    
    data = load_data(data_file)
    results = run_analysis(
        data,
        output_dir=f"results/{exp_name}/",
        show_plots=False  # Don't display when batch processing
    )
    
    # Quick summary
    print(f"  Model A F1: {results['results_a'].macro_f1:.4f}")
    print(f"  Model B F1: {results['results_b'].macro_f1:.4f}")
```

---

## Part 10: Integration with CI/CD

### Creating an Automated Test

```python
# tests/test_analysis_integration.py

import os
import json
from stats.Opus4.5_stats.phase_1.run_analysis import generate_demo_data, run_analysis

def test_demo_analysis_completes():
    """Test that demo analysis runs without errors."""
    data = generate_demo_data()
    results = run_analysis(data, show_plots=False)
    
    assert "results_a" in results
    assert "results_b" in results
    assert results["results_a"].macro_f1 > 0.5

def test_results_export():
    """Test that results can be exported to JSON."""
    import tempfile
    
    data = generate_demo_data()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        results = run_analysis(data, output_dir=tmpdir, show_plots=False)
        
        # Check JSON was created
        json_path = os.path.join(tmpdir, "results.json")
        assert os.path.exists(json_path)
        
        # Check it's valid JSON
        with open(json_path) as f:
            exported = json.load(f)
        
        assert "univariate" in exported
        assert "gate_a" in exported
```

---

## Complete Workflow Example

```python
"""
Complete Phase 1 Analysis Workflow
==================================

This script demonstrates the full analysis pipeline.
"""

import numpy as np
import json
from stats.Opus4.5_stats.phase_1.run_analysis import run_analysis

# Step 1: Prepare your data
# (In practice, this comes from your ML pipeline)
data = {
    "y_true": [0]*100 + [1]*100,
    "pred_a": [0]*95 + [1]*5 + [0]*10 + [1]*90,   # Model A: ~92.5% acc
    "pred_b": [0]*90 + [1]*10 + [0]*15 + [1]*85,  # Model B: ~87.5% acc
    "class_names": ["happy", "sad"],
    "num_classes": 2,
    "model_a_name": "ResNet-50 (ours)",
    "model_b_name": "Baseline CNN",
    "f1_folds_a": {
        "0": [0.92, 0.91, 0.93, 0.90, 0.92],
        "1": [0.91, 0.90, 0.92, 0.89, 0.91]
    },
    "f1_folds_b": {
        "0": [0.87, 0.86, 0.88, 0.85, 0.87],
        "1": [0.85, 0.84, 0.86, 0.83, 0.85]
    }
}

# Step 2: Run the analysis
print("Running Phase 1 Statistical Analysis...")
results = run_analysis(
    data,
    output_dir="experiment_results/",
    show_plots=True,
    alpha=0.05
)

# Step 3: Extract key findings
print("\n" + "="*60)
print("KEY FINDINGS")
print("="*60)

# Gate A results
for name, gate in [("Model A", results["gate_a_result_a"]), 
                   ("Model B", results["gate_a_result_b"])]:
    status = "✓ PASSED" if gate.passed else "✗ FAILED"
    print(f"\n{name} Gate A: {status}")
    if not gate.passed:
        for f in gate.failures:
            print(f"  - {f}")

# Best model determination
kappa = results["kappa_result"]
sm = results["stuart_maxwell_result"]

print(f"\nModel Agreement: κ={kappa.kappa:.3f} ({kappa.interpretation})")
print(f"Distribution Shift: p={sm.p_value:.4f} ({'significant' if sm.significant else 'not significant'})")

# Recommendation
if results["gate_a_result_a"].passed and not results["gate_a_result_b"].passed:
    print("\nRECOMMENDATION: Deploy Model A (meets Gate A, baseline does not)")
elif results["gate_a_result_a"].passed and results["gate_a_result_b"].passed:
    if results["results_a"].macro_f1 > results["results_b"].macro_f1:
        print("\nRECOMMENDATION: Deploy Model A (higher F1)")
    else:
        print("\nRECOMMENDATION: Deploy Model B (higher F1)")
else:
    print("\nRECOMMENDATION: Neither model meets Gate A requirements")
```

---

## Summary

| Task | Method |
|------|--------|
| Run with demo data | `--demo` flag or `generate_demo_data()` |
| Run with custom data | `--data file.json` or `load_data()` |
| Save results | `--output DIR` or `output_dir=` parameter |
| Disable plots | `--no-plots` or `show_plots=False` |
| Change significance | `--alpha 0.01` or `alpha=` parameter |

---

## Self-Check Questions

1. What's the minimum data required to run the analysis?
2. Where are results saved when you specify `--output`?
3. How do you run batch analyses on multiple experiments?
4. What happens if `f1_folds` data is missing?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 07: Testing Your Code**.
