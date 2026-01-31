# Tutorial 01: Understanding Package Structure

This tutorial explains how Python packages work and how our statistical analysis code is organized.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Understand what `__init__.py` files do
2. Know how to import functions from the package
3. Understand the difference between a module and a package

---

## What is a Python Package?

A **package** is a directory containing Python files and a special `__init__.py` file. It lets you organize related code into a logical hierarchy.

```
stats/Opus4.5_stats/          <- Package (has __init__.py)
├── __init__.py               <- Makes this directory a package
└── phase_1/                  <- Sub-package
    ├── __init__.py           <- Makes phase_1 a sub-package
    ├── univariate.py         <- Module (a single .py file)
    ├── multivariate.py       <- Module
    └── ...
```

### Key Terms

| Term | Definition | Example |
|------|------------|---------|
| **Module** | A single `.py` file | `univariate.py` |
| **Package** | A directory with `__init__.py` | `phase_1/` |
| **Sub-package** | A package inside another package | `phase_1` inside `Opus4.5_stats` |

---

## The Root `__init__.py`

**File**: `stats/Opus4.5_stats/__init__.py`

```python
"""
Opus4.5 Statistical Analysis Package
=====================================

Statistical analysis tools for emotion classification model evaluation.
"""

__version__ = "0.1.0"
__author__ = "Reachy R&D Team"

from . import phase_1
```

### What This Does

1. **Docstring**: Describes the package (shows in help/documentation)
2. **`__version__`**: Tracks the package version
3. **`__author__`**: Documents who wrote it
4. **`from . import phase_1`**: Makes `phase_1` accessible when you import the package

### The Dot (`.`) Notation

- `.` means "current package"
- `..` means "parent package"
- `from . import phase_1` means "import phase_1 from this same directory"

---

## The `phase_1/__init__.py` File

This file is more complex—it controls what you can import from `phase_1`.

**File**: `stats/Opus4.5_stats/phase_1/__init__.py`

```python
"""
Phase 1 Statistical Analysis Module
====================================

Implements the statistical framework for Phase 1 emotion classification evaluation.
"""

# Import from univariate.py
from .univariate import (
    compute_confusion_matrix,
    compute_precision,
    compute_recall,
    compute_f1,
    compute_per_class_metrics,
    compute_macro_f1,
    compute_balanced_accuracy,
    validate_gate_a,
    UnivariateResults,
    GateAResult,
    print_univariate_report,
)

# Import from multivariate.py
from .multivariate import (
    build_contingency_table,
    stuart_maxwell_test,
    mcnemar_test_per_class,
    cohens_kappa,
    StuartMaxwellResult,
    McNemarResult,
    KappaResult,
    print_multivariate_report,
)

# ... more imports ...

__all__ = [
    "compute_confusion_matrix",
    "compute_precision",
    # ... list of all public names ...
]
```

### Why Do This?

**Without** this `__init__.py`, you'd have to write:
```python
from stats.Opus4.5_stats.phase_1.univariate import compute_confusion_matrix
```

**With** this `__init__.py`, you can write:
```python
from stats.Opus4.5_stats.phase_1 import compute_confusion_matrix
```

Much cleaner!

### The `__all__` Variable

`__all__` defines what gets exported when someone writes:
```python
from stats.Opus4.5_stats.phase_1 import *
```

Only names listed in `__all__` will be imported. This prevents accidentally exposing internal helper functions.

---

## How to Import from the Package

### Method 1: Import Specific Functions

```python
from stats.Opus4.5_stats.phase_1 import (
    compute_confusion_matrix,
    compute_macro_f1,
    stuart_maxwell_test
)

# Use directly
cm = compute_confusion_matrix(y_true, y_pred, 2)
```

**Best for**: When you know exactly what functions you need.

### Method 2: Import the Module

```python
from stats.Opus4.5_stats import phase_1

# Access via module
cm = phase_1.compute_confusion_matrix(y_true, y_pred, 2)
macro_f1 = phase_1.compute_macro_f1(f1_scores)
```

**Best for**: When you want to make clear where functions come from.

### Method 3: Import Submodules Directly

```python
from stats.Opus4.5_stats.phase_1 import univariate, multivariate

# Access via submodule
cm = univariate.compute_confusion_matrix(y_true, y_pred, 2)
kappa = multivariate.cohens_kappa(pred_a, pred_b, 2)
```

**Best for**: When you want maximum clarity about which module provides each function.

---

## Practical Exercise

Let's practice importing and using the package.

### Step 1: Verify Installation

```python
# Open a Python interpreter or Jupyter notebook
import sys
sys.path.insert(0, "d:/projects/reachy_emotion")  # Adjust path as needed

# Try importing
from stats.Opus4.5_stats import phase_1
print(f"Package version: {phase_1.__doc__[:50]}...")
```

### Step 2: List Available Functions

```python
# See what's available
print("Available functions and classes:")
for name in dir(phase_1):
    if not name.startswith('_'):
        print(f"  - {name}")
```

### Step 3: Get Help on a Function

```python
# Get documentation for a function
help(phase_1.compute_confusion_matrix)
```

Expected output:
```
compute_confusion_matrix(y_true, y_pred, num_classes)
    Compute confusion matrix from predictions.
    
    Args:
        y_true: Ground truth labels (0-indexed)
        y_pred: Predicted labels (0-indexed)
        num_classes: Number of classes
    ...
```

---

## Common Import Errors and Solutions

### Error 1: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'stats'
```

**Solution**: Add the project root to your Python path:
```python
import sys
sys.path.insert(0, "/path/to/reachy_emotion")
```

Or set the `PYTHONPATH` environment variable.

### Error 2: ImportError

```
ImportError: cannot import name 'some_function' from 'phase_1'
```

**Solution**: The function isn't exported in `__init__.py`. Either:
1. Add it to `__init__.py`, or
2. Import directly from the module:
   ```python
   from stats.Opus4.5_stats.phase_1.univariate import some_function
   ```

### Error 3: Circular Import

```
ImportError: cannot import name 'X' from partially initialized module
```

**Solution**: This happens when module A imports from B while B imports from A. Our package avoids this by having `__init__.py` import from modules, but modules don't import from `__init__.py`.

---

## Summary

| Concept | Purpose |
|---------|---------|
| `__init__.py` | Makes a directory a Python package |
| `from . import X` | Import from the same package |
| `__all__` | Controls `from package import *` behavior |
| Docstrings | Document the package/module |

---

## Self-Check Questions

1. What makes a directory a Python package?
2. What does `from .univariate import compute_f1` mean?
3. Why do we list functions in `__init__.py`?
4. What is `__all__` used for?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Next Steps

When ready, proceed to **Tutorial 02: Univariate Metrics**.
