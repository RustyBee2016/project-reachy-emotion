"""
Phase 1 Statistical Analysis Module
====================================

Implements the statistical framework for Phase 1 emotion classification evaluation.

This module provides:
    - Univariate metrics (Macro F1, Balanced Accuracy, Per-class metrics)
    - Multivariate comparison tests (Stuart-Maxwell, McNemar's, Cohen's Kappa)
    - Paired statistical tests with multiple comparison correction
    - Visualization functions for analysis results

Gate A Validation Thresholds:
    - Macro F1 >= 0.84
    - Balanced Accuracy >= 0.85
    - Per-class F1 floor >= 0.75
"""

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

from .paired_tests import (
    paired_t_test,
    cohens_d,
    interpret_cohens_d,
    benjamini_hochberg_correction,
    run_per_class_paired_tests,
    PairedTestResult,
    print_paired_tests_report,
)

from .visualization import (
    plot_confusion_matrix,
    plot_f1_comparison,
    plot_contingency_table,
    plot_marginal_differences,
    plot_cohens_d_effect_sizes,
    plot_mcnemar_results,
    create_all_plots,
)

__all__ = [
    # Univariate
    "compute_confusion_matrix",
    "compute_precision",
    "compute_recall",
    "compute_f1",
    "compute_per_class_metrics",
    "compute_macro_f1",
    "compute_balanced_accuracy",
    "validate_gate_a",
    "UnivariateResults",
    "GateAResult",
    "print_univariate_report",
    # Multivariate
    "build_contingency_table",
    "stuart_maxwell_test",
    "mcnemar_test_per_class",
    "cohens_kappa",
    "StuartMaxwellResult",
    "McNemarResult",
    "KappaResult",
    "print_multivariate_report",
    # Paired Tests
    "paired_t_test",
    "cohens_d",
    "interpret_cohens_d",
    "benjamini_hochberg_correction",
    "run_per_class_paired_tests",
    "PairedTestResult",
    "print_paired_tests_report",
    # Visualization
    "plot_confusion_matrix",
    "plot_f1_comparison",
    "plot_contingency_table",
    "plot_marginal_differences",
    "plot_cohens_d_effect_sizes",
    "plot_mcnemar_results",
    "create_all_plots",
]
