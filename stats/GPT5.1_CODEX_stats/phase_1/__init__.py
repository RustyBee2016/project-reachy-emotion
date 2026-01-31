"""
Phase 1 Statistical Analysis Package

Statistical framework for evaluating emotion recognition models trained with synthetic data.
Compares base EfficientNet-B0 model against fine-tuned variant.

Modules:
    - univariate: Gate A metrics (Macro F1, Balanced Accuracy, Per-class F1)
    - multivariate: Model comparison tests (Stuart-Maxwell, McNemar's, Cohen's Kappa)
    - paired_tests: Per-class paired t-tests with Benjamini-Hochberg correction
    - visualization: Plotting functions for results
    - run_analysis: Main script to execute full analysis pipeline
"""

from .univariate import (
    compute_confusion_matrix,
    compute_precision_recall,
    compute_per_class_f1,
    compute_macro_f1,
    compute_balanced_accuracy,
    validate_gate_a,
    UnivariateResults,
    GateAThresholds,
)

from .multivariate import (
    stuart_maxwell_test,
    mcnemar_test,
    cohens_kappa,
    build_contingency_table,
    StuartMaxwellResult,
    McNemarResult,
    KappaResult,
)

from .paired_tests import (
    paired_t_test,
    benjamini_hochberg_correction,
    compute_cohens_d,
    run_per_class_paired_tests,
    PairedTestResult,
)

__version__ = "1.0.0"
__author__ = "Russell Bray"
