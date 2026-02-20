# Tutorial 00: Overview and Setup

Welcome to the Phase 1 Statistical Analysis tutorial series! This guide will walk you through the statistical methods used to evaluate and compare emotion classification models.

---

## What You'll Learn

By completing these tutorials, you will understand:

1. **Univariate Metrics** — How to measure a single model's performance
2. **Multivariate Comparisons** — How to statistically compare two models
3. **Multiple Comparison Correction** — How to handle testing multiple hypotheses
4. **Visualization** — How to create publication-quality plots
5. **Testing** — How to verify your code works correctly

---

## Prerequisites

### Knowledge Requirements

- Basic Python programming (functions, classes, dictionaries)
- Familiarity with NumPy arrays
- Basic statistics (mean, standard deviation, hypothesis testing concepts)
- Understanding of classification problems (what is a prediction? what is ground truth?)

### Software Requirements

```bash
# Python 3.8 or higher
python --version

# Install required packages
pip install -r stats/Opus4.5_stats/phase_1/requirements.txt
```

### Required Packages

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | ≥1.21.0 | Numerical computations |
| scipy | ≥1.7.0 | Statistical functions |
| matplotlib | ≥3.5.0 | Plotting |
| seaborn | ≥0.11.0 | Enhanced visualizations |

---

## The Problem We're Solving

### Context: Emotion Classification

We're building a system that classifies human emotions from video. Our current setup:

- **Classes**: `happy` (0) and `sad` (1)
- **Models**: We're comparing two neural networks (e.g., ResNet-50 vs EfficientNet-B0)
- **Goal**: Determine which model performs better and whether the difference is statistically significant

### Why Statistics Matter

Imagine Model A has 87% accuracy and Model B has 85% accuracy. Questions arise:

1. Is Model A *really* better, or is this just random variation?
2. Is Model A better at *all* emotion classes, or just some?
3. How confident can we be in our conclusions?

**Statistical analysis answers these questions rigorously.**

---

## Package Structure Overview

```
stats/Opus4.5_stats/
├── __init__.py                 # Package root
├── phase_1/
│   ├── __init__.py             # Module exports (what you can import)
│   ├── univariate.py           # Per-model metrics
│   ├── multivariate.py         # Model comparison tests
│   ├── paired_tests.py         # Cross-validation comparisons
│   ├── visualization.py        # Plotting functions
│   ├── run_analysis.py         # Main analysis script
│   ├── requirements.txt        # Dependencies
│   └── tests/
│       └── test_phase1_stats.py  # Unit tests
└── tutorials/
    └── (you are here)
```

---

## Quick Start: Running the Demo

Before diving into the theory, let's see the analysis in action:

```python
# From the project root directory
from stats.Opus4.5_stats.phase_1.run_analysis import generate_demo_data, run_analysis

# Generate synthetic data matching research paper results
data = generate_demo_data()

# Run the complete analysis
results = run_analysis(data, output_dir="demo_results/", show_plots=True)
```

Or from the command line:

```bash
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo --output demo_results/
```

This will:
1. Compute metrics for both models
2. Run statistical comparison tests
3. Generate visualizations
4. Save results to JSON

---

## Understanding the Data Format

All analyses expect data in this format:

```python
data = {
    # Ground truth labels (what the correct answers are)
    "y_true": [0, 1, 0, 1, 0, ...],  # 0=happy, 1=sad
    
    # Model A's predictions
    "pred_a": [0, 1, 1, 1, 0, ...],  # Model A's guesses
    
    # Model B's predictions
    "pred_b": [0, 0, 0, 1, 0, ...],  # Model B's guesses
    
    # Class names for display
    "class_names": ["happy", "sad"],
    
    # Number of classes
    "num_classes": 2,
    
    # Model names for reports
    "model_a_name": "ResNet-50",
    "model_b_name": "EfficientNet-B0",
    
    # F1 scores from k-fold cross-validation (for paired tests)
    "f1_folds_a": {
        "0": [0.87, 0.86, 0.88, 0.85, 0.87],  # Class 0 F1 across 5 folds
        "1": [0.84, 0.85, 0.86, 0.83, 0.85]   # Class 1 F1 across 5 folds
    },
    "f1_folds_b": {
        "0": [0.85, 0.84, 0.86, 0.83, 0.85],
        "1": [0.82, 0.83, 0.84, 0.81, 0.83]
    }
}
```

### Key Concepts

| Term | Definition |
|------|------------|
| `y_true` | The correct labels (ground truth) |
| `y_pred` | What the model predicted |
| Fold | One split of data in cross-validation |
| Class | A category (happy=0, sad=1) |

---

## Gate A: Our Quality Threshold

Before deploying a model, it must pass **Gate A** validation:

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| Macro F1 | ≥ 0.84 | Average F1 across all classes |
| Balanced Accuracy | ≥ 0.85 | Average recall across all classes |
| Per-class F1 Floor | ≥ 0.75 | No class can have F1 below this |

If a model fails any threshold, it cannot be deployed.

---

## Tutorial Roadmap

| Tutorial | Topic | Time |
|----------|-------|------|
| 01 | Package Structure (`__init__.py` files) | 15 min |
| 02 | Univariate Metrics (`univariate.py`) | 45 min |
| 03 | Multivariate Tests (`multivariate.py`) | 60 min |
| 04 | Paired Tests (`paired_tests.py`) | 45 min |
| 05 | Visualization (`visualization.py`) | 30 min |
| 06 | Running Analysis (`run_analysis.py`) | 30 min |
| 07 | Testing (`test_phase1_stats.py`) | 30 min |

---

## Self-Check Questions

Before proceeding, make sure you can answer:

1. What are the two emotion classes in our system?
2. What does `y_true` contain?
3. What are the three Gate A thresholds?
4. Why do we need statistical tests instead of just comparing accuracy numbers?

---

## Next Steps

When you're ready, proceed to **Tutorial 01: Understanding Package Structure**.

---

## Comprehension Scale

After reading this tutorial, rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

*Please share your rating and any questions before moving on!*
