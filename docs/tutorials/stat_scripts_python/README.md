# Python Statistical Scripts Tutorials for Reachy Emotion Analysis

## Overview

This tutorial series teaches junior data scientists how to understand and use the Python statistical scripts for emotion classification analysis. Each tutorial combines line-by-line syntax explanation with statistical concepts and practical examples using scikit-learn and other Python data science libraries.

## Learning Path

### Prerequisites
- Basic Python syntax (functions, classes, data structures)
- Elementary statistics (mean, standard deviation, hypothesis testing)
- Familiarity with NumPy and pandas
- Understanding of confusion matrices and classification metrics

### Tutorial Sequence

1. **[Tutorial 1: Quality Gate Metrics](01_quality_gate_metrics_tutorial.md)**
   - Learn scikit-learn classification evaluation metrics
   - Understand confusion matrix calculations with sklearn
   - Master quality gate validation logic and dataclasses

2. **[Tutorial 2: Stuart-Maxwell Test](02_stuart_maxwell_tutorial.md)**
   - Compare prediction patterns between models using scipy
   - Understand contingency tables and marginal homogeneity testing
   - Learn NumPy matrix operations and statistical computing

3. **[Tutorial 3: Per-Class Paired t-Tests](03_perclass_ttests_tutorial.md)**
   - Identify specific class improvements using scipy.stats
   - Master multiple comparison corrections with statsmodels
   - Understand pandas data manipulation for statistical analysis

4. **[Tutorial 4: Statistical Workflow Integration](04_python_workflow_tutorial.md)**
   - Learn how to combine all three analyses
   - Understand the complete statistical pipeline
   - Master data flow between different analysis stages

## Emotion Classification Context

These scripts analyze the performance of emotion classification models that predict 8 emotion classes:
- **anger**, **contempt**, **disgust**, **fear**
- **happiness**, **neutral**, **sadness**, **surprise**

The analysis workflow follows this sequence:
1. **Quality Gates** → Validate overall model performance using sklearn metrics
2. **Stuart-Maxwell** → Detect systematic prediction changes using scipy
3. **Per-Class Tests** → Identify which emotions improved/degraded using statistical testing

## Key Statistical Concepts

### Quality Gate Metrics
- **Macro F1**: Average F1 across all classes using `sklearn.metrics.f1_score`
- **Balanced Accuracy**: Average recall across classes using `sklearn.metrics.balanced_accuracy_score`  
- **F1 Neutral**: F1 for neutral class specifically using `sklearn.metrics.classification_report`

### Statistical Tests
- **Stuart-Maxwell Test**: Chi-squared test for marginal homogeneity using `scipy.stats.chi2`
- **Paired t-Tests**: Compare means of related samples using `scipy.stats.ttest_rel`
- **Multiple Comparisons**: Control false discovery rate using `statsmodels.stats.multitest`

### Effect Sizes
- **Cohen's d**: Standardized difference between means
- **Cramer's V**: Effect size for categorical associations
- **Interpretation**: negligible (<0.2), small (0.2-0.5), medium (0.5-0.8), large (>0.8)

## Python Programming Patterns

### Common Constructs You'll Learn
```python
# Dataclasses for structured data
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class MetricsReport:
    macro_f1: float
    balanced_accuracy: float
    f1_neutral: float
    per_class_metrics: Dict[str, float]

# Type hints for better code documentation
def compute_metrics(y_true: List[str], y_pred: List[str]) -> MetricsReport:
    pass

# Context managers for resource handling
with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)

# List comprehensions for efficient data processing
f1_scores = [metrics[cls]['f1-score'] for cls in EMOTION_CLASSES]

# NumPy vectorized operations
differences = np.array(finetuned_scores) - np.array(base_scores)

# Pandas for data manipulation
df = pd.DataFrame({
    'emotion_class': classes,
    'base_f1': base_scores,
    'finetuned_f1': finetuned_scores
})
```

### Data Science Best Practices
- **Type Safety**: Use type hints and dataclasses
- **Reproducibility**: Use random seeds with numpy.random
- **Validation**: Check inputs with assertions and custom validators
- **Documentation**: Clear docstrings following Google/NumPy style
- **Error Handling**: Comprehensive try-catch with informative messages

## Running the Scripts

### Basic Usage
```bash
# Quality gate analysis with demo data
python 01_quality_gate_metrics.py --demo --plot

# Stuart-Maxwell test with demo data
python 02_stuart_maxwell_test.py --demo --effect-size medium --plot

# Per-class analysis with demo data
python 03_perclass_paired_ttests.py --demo --effect-pattern mixed --plot
```

### Production Usage
```bash
# Real data analysis
python 01_quality_gate_metrics.py --predictions-csv results/predictions.csv --output results/quality_gates

# Compare two models
python 02_stuart_maxwell_test.py --predictions-csv results/model_comparison.csv --output results/stuart_maxwell

# Analyze fold-level improvements
python 03_perclass_paired_ttests.py --metrics-csv results/fold_metrics.csv --correction BH --output results/perclass
```

## Learning Objectives

By completing these tutorials, you will:

1. **Master Python Data Science Stack**
   - scikit-learn for machine learning metrics
   - scipy for statistical testing and computations
   - NumPy for numerical computing and array operations
   - pandas for data manipulation and analysis
   - matplotlib/seaborn for data visualization

2. **Understand Statistical Concepts**
   - Classification metrics and their interpretation
   - Hypothesis testing and p-value interpretation
   - Effect sizes and practical significance
   - Multiple comparison corrections

3. **Apply Modern Python Practices**
   - Type hints and dataclasses for code clarity
   - Argparse for command-line interfaces
   - Pathlib for file system operations
   - F-strings for string formatting
   - Context managers for resource handling

4. **Build Production-Ready Code**
   - Comprehensive error handling and validation
   - Structured logging and debugging
   - Modular code organization
   - Unit testing patterns

## Key Python Libraries

### Core Dependencies
```python
import numpy as np                    # Numerical computing
import pandas as pd                   # Data manipulation
import matplotlib.pyplot as plt       # Basic plotting
import seaborn as sns                # Statistical visualization
from sklearn import metrics          # ML evaluation metrics
from scipy import stats              # Statistical functions
import argparse                      # Command-line parsing
import json                          # JSON handling
from pathlib import Path             # File system operations
from dataclasses import dataclass    # Structured data
from typing import List, Dict, Optional  # Type hints
```

### Statistical Computing
```python
# Classification metrics
from sklearn.metrics import (
    confusion_matrix, classification_report,
    f1_score, balanced_accuracy_score,
    precision_recall_fscore_support
)

# Statistical tests
from scipy.stats import (
    chi2, ttest_rel, shapiro,
    normaltest, jarque_bera
)

# Multiple comparisons
from statsmodels.stats.multitest import multipletests
```

## Getting Help

- **Syntax Questions**: Check Python documentation with `help(function_name)`
- **Statistical Concepts**: Refer to the theory sections in each tutorial
- **Library Usage**: Consult scikit-learn and scipy documentation
- **Debugging**: Use Python's built-in `pdb` debugger or IDE debugging tools
- **Examples**: All tutorials include working code examples with sample data

## Comparison with R Implementation

| Aspect | Python Implementation | R Implementation |
|--------|----------------------|------------------|
| **Metrics Calculation** | scikit-learn (robust, tested) | Manual implementation |
| **Statistical Tests** | scipy.stats (comprehensive) | Base R stats |
| **Data Handling** | pandas (powerful, flexible) | data.frame (simpler) |
| **Visualization** | matplotlib/seaborn | ggplot2/plotly |
| **Type Safety** | Type hints + dataclasses | Dynamic typing |
| **Error Handling** | try/except with logging | tryCatch with logging |
| **Performance** | NumPy vectorization | R vectorization |
| **Ecosystem** | Rich ML/stats ecosystem | Strong statistical focus |

## Tutorial Structure

Each tutorial follows this consistent structure:

1. **Learning Objectives** - What you'll master
2. **Statistical Background** - Theory and motivation
3. **Code Structure** - Imports, classes, and organization
4. **Core Implementation** - Line-by-line explanation
5. **Advanced Features** - Enhanced functionality
6. **Practical Exercises** - Hands-on practice
7. **Common Pitfalls** - What to avoid
8. **Key Takeaways** - Summary and next steps

Start with Tutorial 1 to begin your journey into statistical analysis with Python!
