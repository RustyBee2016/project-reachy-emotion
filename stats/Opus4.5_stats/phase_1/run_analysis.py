"""
Phase 1 Statistical Analysis Runner
====================================

Main script to run the complete Phase 1 statistical analysis pipeline.

Usage:
    # Run with demo data (reproduces research paper results)
    python run_analysis.py --demo
    
    # Run with custom data file
    python run_analysis.py --data path/to/data.json
    
    # Specify output directory
    python run_analysis.py --demo --output results/

Data Format (JSON):
    {
        "y_true": [0, 1, 0, ...],
        "pred_a": [0, 1, 1, ...],
        "pred_b": [0, 0, 0, ...],
        "class_names": ["happy", "sad"],
        "model_a_name": "ResNet-50",
        "model_b_name": "EfficientNet-B0",
        "f1_folds_a": {"0": [0.85, 0.86, ...], "1": [0.82, 0.83, ...]},
        "f1_folds_b": {"0": [0.87, 0.88, ...], "1": [0.84, 0.85, ...]}
    }
"""

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .univariate import (
    compute_all_univariate_metrics,
    validate_gate_a,
    print_univariate_report,
    UnivariateResults,
    GateAResult
)
from .multivariate import (
    build_contingency_table,
    stuart_maxwell_test,
    mcnemar_test_per_class,
    cohens_kappa,
    print_multivariate_report,
    StuartMaxwellResult,
    McNemarResult,
    KappaResult
)
from .paired_tests import (
    run_per_class_paired_tests,
    print_paired_tests_report,
    PairedTestResult
)
from .visualization import create_all_plots


# =============================================================================
# Demo Data Generator
# =============================================================================

def generate_demo_data() -> Dict[str, Any]:
    """
    Generate demo data that reproduces the research paper results.
    
    This function creates synthetic data matching the statistics reported
    in Phase_1_Statistical_Analysis.md for verification purposes.
    
    Returns:
        Dictionary with all data needed for analysis
    """
    np.random.seed(42)
    
    # Define class structure
    class_names = ["happy", "sad"]
    num_classes = 2
    n_samples = 500
    
    # Generate ground truth with slight imbalance (55% happy, 45% sad)
    y_true = np.array([0] * 275 + [1] * 225)
    np.random.shuffle(y_true)
    
    # Generate predictions for Model A (ResNet-50)
    # Target: ~87% accuracy, balanced performance
    pred_a = y_true.copy()
    error_indices_a = np.random.choice(n_samples, size=65, replace=False)
    for idx in error_indices_a:
        pred_a[idx] = 1 - pred_a[idx]
    
    # Generate predictions for Model B (EfficientNet-B0)
    # Target: ~85% accuracy, slightly lower
    pred_b = y_true.copy()
    error_indices_b = np.random.choice(n_samples, size=75, replace=False)
    for idx in error_indices_b:
        pred_b[idx] = 1 - pred_b[idx]
    
    # Generate k-fold F1 scores (5 folds)
    n_folds = 5
    
    # Model A fold scores (targeting macro F1 ~0.86)
    f1_folds_a = {
        0: np.array([0.87, 0.86, 0.88, 0.85, 0.87]),  # happy
        1: np.array([0.84, 0.85, 0.86, 0.83, 0.85])   # sad
    }
    
    # Model B fold scores (targeting macro F1 ~0.84)
    f1_folds_b = {
        0: np.array([0.85, 0.84, 0.86, 0.83, 0.85]),  # happy
        1: np.array([0.82, 0.83, 0.84, 0.81, 0.83])   # sad
    }
    
    return {
        "y_true": y_true.tolist(),
        "pred_a": pred_a.tolist(),
        "pred_b": pred_b.tolist(),
        "class_names": class_names,
        "num_classes": num_classes,
        "model_a_name": "ResNet-50",
        "model_b_name": "EfficientNet-B0",
        "f1_folds_a": {str(k): v.tolist() for k, v in f1_folds_a.items()},
        "f1_folds_b": {str(k): v.tolist() for k, v in f1_folds_b.items()}
    }


# =============================================================================
# Data Loading
# =============================================================================

def load_data(filepath: str) -> Dict[str, Any]:
    """
    Load analysis data from JSON file.
    
    Args:
        filepath: Path to JSON data file
        
    Returns:
        Dictionary with analysis data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required fields are missing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    required_fields = ['y_true', 'pred_a', 'pred_b']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Set defaults
    if 'class_names' not in data:
        num_classes = len(set(data['y_true']))
        data['class_names'] = [f"Class {i}" for i in range(num_classes)]
    
    if 'num_classes' not in data:
        data['num_classes'] = len(data['class_names'])
    
    if 'model_a_name' not in data:
        data['model_a_name'] = "Model A"
    
    if 'model_b_name' not in data:
        data['model_b_name'] = "Model B"
    
    return data


# =============================================================================
# Results Export
# =============================================================================

def export_results(
    results_a: UnivariateResults,
    results_b: UnivariateResults,
    gate_a_result_a: GateAResult,
    gate_a_result_b: GateAResult,
    stuart_maxwell_result: StuartMaxwellResult,
    mcnemar_results: List[McNemarResult],
    kappa_result: KappaResult,
    paired_results: List[PairedTestResult],
    output_path: str
) -> None:
    """
    Export all results to JSON file.
    
    Args:
        results_a: Univariate results for model A
        results_b: Univariate results for model B
        gate_a_result_a: Gate A validation for model A
        gate_a_result_b: Gate A validation for model B
        stuart_maxwell_result: Stuart-Maxwell test result
        mcnemar_results: List of McNemar results
        kappa_result: Cohen's Kappa result
        paired_results: List of paired test results
        output_path: Path to save JSON
    """
    def make_serializable(obj):
        """Convert numpy types to Python types."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        return obj
    
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "univariate": {
            "model_a": {
                "confusion_matrix": make_serializable(results_a.confusion_matrix),
                "precision": make_serializable(results_a.precision),
                "recall": make_serializable(results_a.recall),
                "f1": make_serializable(results_a.f1),
                "macro_f1": results_a.macro_f1,
                "balanced_accuracy": results_a.balanced_accuracy,
                "support": make_serializable(results_a.support)
            },
            "model_b": {
                "confusion_matrix": make_serializable(results_b.confusion_matrix),
                "precision": make_serializable(results_b.precision),
                "recall": make_serializable(results_b.recall),
                "f1": make_serializable(results_b.f1),
                "macro_f1": results_b.macro_f1,
                "balanced_accuracy": results_b.balanced_accuracy,
                "support": make_serializable(results_b.support)
            }
        },
        "gate_a": {
            "model_a": {
                "passed": gate_a_result_a.passed,
                "macro_f1": gate_a_result_a.macro_f1,
                "balanced_accuracy": gate_a_result_a.balanced_accuracy,
                "failures": gate_a_result_a.failures
            },
            "model_b": {
                "passed": gate_a_result_b.passed,
                "macro_f1": gate_a_result_b.macro_f1,
                "balanced_accuracy": gate_a_result_b.balanced_accuracy,
                "failures": gate_a_result_b.failures
            }
        },
        "stuart_maxwell": {
            "statistic": stuart_maxwell_result.statistic,
            "p_value": stuart_maxwell_result.p_value,
            "df": stuart_maxwell_result.df,
            "significant": stuart_maxwell_result.significant,
            "marginal_diff": make_serializable(stuart_maxwell_result.marginal_diff)
        },
        "mcnemar": [
            {
                "class_name": r.class_name,
                "b": r.b,
                "c": r.c,
                "statistic": r.statistic,
                "p_value": r.p_value,
                "odds_ratio": r.odds_ratio if not np.isinf(r.odds_ratio) else "inf",
                "significant": r.significant,
                "winner": r.winner
            }
            for r in mcnemar_results
        ],
        "cohens_kappa": {
            "kappa": kappa_result.kappa,
            "std_error": kappa_result.std_error,
            "ci_lower": kappa_result.ci_lower,
            "ci_upper": kappa_result.ci_upper,
            "p_value": kappa_result.p_value,
            "interpretation": kappa_result.interpretation
        },
        "paired_tests": [
            {
                "class_name": r.class_name,
                "mean_diff": r.mean_diff,
                "std_diff": r.std_diff,
                "t_statistic": r.t_statistic,
                "p_value": r.p_value,
                "cohens_d": r.cohens_d,
                "effect_interpretation": r.effect_interpretation,
                "significant_raw": r.significant_raw,
                "significant_corrected": r.significant_corrected
            }
            for r in paired_results
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\nResults exported to: {output_path}")


# =============================================================================
# Main Analysis Pipeline
# =============================================================================

def run_analysis(
    data: Dict[str, Any],
    output_dir: Optional[str] = None,
    show_plots: bool = True,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Run the complete Phase 1 statistical analysis.
    
    Args:
        data: Dictionary containing all analysis data
        output_dir: Optional directory to save results and plots
        show_plots: Whether to display plots
        alpha: Significance level (default 0.05)
        
    Returns:
        Dictionary containing all analysis results
    """
    # Extract data
    y_true = np.array(data['y_true'])
    pred_a = np.array(data['pred_a'])
    pred_b = np.array(data['pred_b'])
    class_names = data['class_names']
    num_classes = data['num_classes']
    model_a_name = data['model_a_name']
    model_b_name = data['model_b_name']
    
    print("=" * 70)
    print("PHASE 1 STATISTICAL ANALYSIS")
    print("=" * 70)
    print(f"Model A: {model_a_name}")
    print(f"Model B: {model_b_name}")
    print(f"Samples: {len(y_true)}")
    print(f"Classes: {num_classes} ({', '.join(class_names)})")
    print(f"Alpha: {alpha}")
    
    # ----- Univariate Metrics -----
    print("\n" + "=" * 70)
    print("SECTION 1: UNIVARIATE METRICS")
    print("=" * 70)
    
    results_a = compute_all_univariate_metrics(y_true, pred_a, num_classes, class_names)
    results_b = compute_all_univariate_metrics(y_true, pred_b, num_classes, class_names)
    
    gate_a_result_a = validate_gate_a(results_a)
    gate_a_result_b = validate_gate_a(results_b)
    
    print_univariate_report(results_a, model_a_name, gate_a_result_a)
    print_univariate_report(results_b, model_b_name, gate_a_result_b)
    
    # ----- Multivariate Comparison -----
    print("\n" + "=" * 70)
    print("SECTION 2: MULTIVARIATE MODEL COMPARISON")
    print("=" * 70)
    
    contingency_table = build_contingency_table(y_true, pred_a, pred_b, num_classes)
    stuart_maxwell_result = stuart_maxwell_test(pred_a, pred_b, num_classes, alpha)
    mcnemar_results = mcnemar_test_per_class(contingency_table, class_names, alpha)
    kappa_result = cohens_kappa(pred_a, pred_b, num_classes, alpha)
    
    print_multivariate_report(stuart_maxwell_result, mcnemar_results, kappa_result,
                              model_a_name, model_b_name)
    
    # ----- Paired Tests -----
    print("\n" + "=" * 70)
    print("SECTION 3: PAIRED T-TESTS (Cross-Validation)")
    print("=" * 70)
    
    if 'f1_folds_a' in data and 'f1_folds_b' in data:
        f1_folds_a = {int(k): np.array(v) for k, v in data['f1_folds_a'].items()}
        f1_folds_b = {int(k): np.array(v) for k, v in data['f1_folds_b'].items()}
        
        paired_results = run_per_class_paired_tests(
            f1_folds_a, f1_folds_b, class_names, alpha
        )
        print_paired_tests_report(paired_results, model_a_name, model_b_name)
    else:
        print("\nNo fold data provided. Skipping paired t-tests.")
        paired_results = []
    
    # ----- Create Output Directory -----
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
        # Export results
        export_results(
            results_a, results_b,
            gate_a_result_a, gate_a_result_b,
            stuart_maxwell_result, mcnemar_results, kappa_result,
            paired_results,
            os.path.join(output_dir, "results.json")
        )
    
    # ----- Visualizations -----
    print("\n" + "=" * 70)
    print("SECTION 4: VISUALIZATIONS")
    print("=" * 70)
    
    if paired_results:
        figures = create_all_plots(
            results_a, results_b,
            contingency_table,
            stuart_maxwell_result,
            mcnemar_results,
            paired_results,
            model_a_name, model_b_name,
            output_dir=os.path.join(output_dir, "plots") if output_dir else None,
            show_plots=show_plots
        )
        print(f"\nGenerated {len(figures)} plots.")
    else:
        print("\nSkipping visualizations (no paired test results).")
        figures = {}
    
    # ----- Summary -----
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\n{model_a_name}:")
    print(f"  Macro F1: {results_a.macro_f1:.4f}")
    print(f"  Balanced Accuracy: {results_a.balanced_accuracy:.4f}")
    print(f"  Gate A: {'PASSED' if gate_a_result_a.passed else 'FAILED'}")
    
    print(f"\n{model_b_name}:")
    print(f"  Macro F1: {results_b.macro_f1:.4f}")
    print(f"  Balanced Accuracy: {results_b.balanced_accuracy:.4f}")
    print(f"  Gate A: {'PASSED' if gate_a_result_b.passed else 'FAILED'}")
    
    print(f"\nComparison:")
    print(f"  Stuart-Maxwell p-value: {stuart_maxwell_result.p_value:.4f} "
          f"({'significant' if stuart_maxwell_result.significant else 'not significant'})")
    print(f"  Cohen's Kappa: {kappa_result.kappa:.4f} ({kappa_result.interpretation})")
    
    return {
        "results_a": results_a,
        "results_b": results_b,
        "gate_a_result_a": gate_a_result_a,
        "gate_a_result_b": gate_a_result_b,
        "contingency_table": contingency_table,
        "stuart_maxwell_result": stuart_maxwell_result,
        "mcnemar_results": mcnemar_results,
        "kappa_result": kappa_result,
        "paired_results": paired_results,
        "figures": figures
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Command-line interface for Phase 1 analysis."""
    parser = argparse.ArgumentParser(
        description="Phase 1 Statistical Analysis for Emotion Classification",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--demo', action='store_true',
        help='Run with demo data (reproduces research paper results)'
    )
    parser.add_argument(
        '--data', type=str, default=None,
        help='Path to JSON data file'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output directory for results and plots'
    )
    parser.add_argument(
        '--alpha', type=float, default=0.05,
        help='Significance level (default: 0.05)'
    )
    parser.add_argument(
        '--no-plots', action='store_true',
        help='Disable plot display'
    )
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.demo:
        print("Running with demo data...")
        data = generate_demo_data()
    elif args.data:
        print(f"Loading data from: {args.data}")
        data = load_data(args.data)
    else:
        print("Error: Must specify --demo or --data")
        parser.print_help()
        return 1
    
    # Run analysis
    run_analysis(
        data,
        output_dir=args.output,
        show_plots=not args.no_plots,
        alpha=args.alpha
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
