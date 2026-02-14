"""
Phase 1 Statistical Analysis - Main Runner

Executes the complete Phase 1 statistical analysis pipeline:
1. Univariate metrics (Gate A validation)
2. Stuart-Maxwell test (overall distributional shift)
3. McNemar's tests (per-class error rate comparison)
4. Cohen's Kappa (inter-model agreement)
5. Paired t-tests with Benjamini-Hochberg correction
6. Visualization generation

Usage:
    python -m stats.opus.phase_1.run_analysis --data-path /path/to/predictions.json
    
Or programmatically:
    from stats.opus.phase_1.run_analysis import run_full_analysis
    results = run_full_analysis(y_true, base_preds, ft_preds, fold_scores, class_names)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import numpy as np

from .univariate import (
    compute_all_univariate_metrics,
    print_univariate_report,
    UnivariateResults,
    GateAThresholds,
)
from .multivariate import (
    build_contingency_table,
    stuart_maxwell_test,
    run_all_mcnemar_tests,
    cohens_kappa,
    print_multivariate_report,
    StuartMaxwellResult,
    McNemarResult,
    KappaResult,
)
from .paired_tests import (
    run_per_class_paired_tests,
    print_paired_tests_report,
    PairedTestResult,
)
from .visualization import create_all_plots


@dataclass
class Phase1AnalysisResults:
    """Complete results from Phase 1 statistical analysis."""
    # Univariate
    base_univariate: UnivariateResults
    ft_univariate: UnivariateResults
    
    # Multivariate
    stuart_maxwell: StuartMaxwellResult
    mcnemar_tests: List[McNemarResult]
    cohens_kappa: KappaResult
    
    # Paired tests
    paired_t_tests: List[PairedTestResult]
    
    # Metadata
    class_names: List[str]
    n_samples: int
    n_folds: int
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to serializable dictionary."""
        return {
            'base_univariate': {
                'macro_f1': self.base_univariate.macro_f1,
                'balanced_accuracy': self.base_univariate.balanced_accuracy,
                'per_class_f1': self.base_univariate.per_class_f1,
                'gate_a_passed': self.base_univariate.gate_a_passed,
            },
            'ft_univariate': {
                'macro_f1': self.ft_univariate.macro_f1,
                'balanced_accuracy': self.ft_univariate.balanced_accuracy,
                'per_class_f1': self.ft_univariate.per_class_f1,
                'gate_a_passed': self.ft_univariate.gate_a_passed,
            },
            'stuart_maxwell': {
                'chi2': self.stuart_maxwell.chi2_statistic,
                'df': self.stuart_maxwell.degrees_of_freedom,
                'p_value': self.stuart_maxwell.p_value,
                'reject_null': self.stuart_maxwell.reject_null,
                'marginal_differences': self.stuart_maxwell.marginal_differences,
            },
            'mcnemar_tests': [
                {
                    'class': r.class_name,
                    'n12': r.n_base_correct_ft_incorrect,
                    'n21': r.n_base_incorrect_ft_correct,
                    'chi2': r.chi2_statistic,
                    'p_value': r.p_value,
                    'net_improvement': r.net_improvement,
                    'reject_null': r.reject_null,
                }
                for r in self.mcnemar_tests
            ],
            'cohens_kappa': {
                'kappa': self.cohens_kappa.kappa,
                'observed_agreement': self.cohens_kappa.observed_agreement,
                'expected_agreement': self.cohens_kappa.expected_agreement,
                'ci_lower': self.cohens_kappa.ci_lower,
                'ci_upper': self.cohens_kappa.ci_upper,
                'interpretation': self.cohens_kappa.interpretation,
            },
            'paired_t_tests': [
                {
                    'class': r.class_name,
                    'mean_diff': r.mean_difference,
                    't_statistic': r.t_statistic,
                    'p_value': r.p_value,
                    'p_value_adjusted': r.p_value_adjusted,
                    'cohens_d': r.cohens_d,
                    'effect_size': r.effect_size_interpretation,
                    'reject_null_adjusted': r.reject_null_adjusted,
                }
                for r in self.paired_t_tests
            ],
            'metadata': {
                'class_names': self.class_names,
                'n_samples': self.n_samples,
                'n_folds': self.n_folds,
                'timestamp': self.timestamp,
            }
        }


def run_full_analysis(
    y_true: np.ndarray,
    base_preds: np.ndarray,
    ft_preds: np.ndarray,
    base_fold_scores: Dict[str, List[float]],
    ft_fold_scores: Dict[str, List[float]],
    class_names: List[str],
    thresholds: Optional[GateAThresholds] = None,
    alpha: float = 0.05,
) -> Phase1AnalysisResults:
    """
    Run complete Phase 1 statistical analysis.
    
    Args:
        y_true: Ground truth labels (n_samples,)
        base_preds: Base model predictions (n_samples,)
        ft_preds: Fine-tuned model predictions (n_samples,)
        base_fold_scores: Per-class F1 scores per fold for base model
        ft_fold_scores: Per-class F1 scores per fold for fine-tuned model
        class_names: List of class names
        thresholds: Gate A thresholds (uses defaults if None)
        alpha: Significance level for hypothesis tests
        
    Returns:
        Phase1AnalysisResults with all computed statistics
    """
    n_samples = len(y_true)
    n_folds = len(list(base_fold_scores.values())[0])
    num_classes = len(class_names)
    
    # 1. Univariate metrics
    base_univariate = compute_all_univariate_metrics(
        y_true, base_preds, class_names, thresholds
    )
    ft_univariate = compute_all_univariate_metrics(
        y_true, ft_preds, class_names, thresholds
    )
    
    # 2. Build contingency table for multivariate tests
    contingency = build_contingency_table(base_preds, ft_preds, num_classes)
    
    # 3. Stuart-Maxwell test
    sm_result = stuart_maxwell_test(contingency, class_names, alpha)
    
    # 4. McNemar's tests
    mcnemar_results = run_all_mcnemar_tests(
        y_true, base_preds, ft_preds, class_names, alpha
    )
    
    # 5. Cohen's Kappa
    kappa_result = cohens_kappa(contingency)
    
    # 6. Paired t-tests with BH correction
    paired_results = run_per_class_paired_tests(
        base_fold_scores, ft_fold_scores, class_names, alpha
    )
    
    return Phase1AnalysisResults(
        base_univariate=base_univariate,
        ft_univariate=ft_univariate,
        stuart_maxwell=sm_result,
        mcnemar_tests=mcnemar_results,
        cohens_kappa=kappa_result,
        paired_t_tests=paired_results,
        class_names=class_names,
        n_samples=n_samples,
        n_folds=n_folds,
        timestamp=datetime.now().isoformat(),
    )


def print_full_report(results: Phase1AnalysisResults) -> str:
    """
    Generate complete formatted report.
    
    Args:
        results: Phase1AnalysisResults object
        
    Returns:
        Complete report string
    """
    sections = [
        "=" * 80,
        "PHASE 1 STATISTICAL ANALYSIS - COMPLETE REPORT",
        f"Generated: {results.timestamp}",
        f"Samples: {results.n_samples}  |  Classes: {len(results.class_names)}  |  Folds: {results.n_folds}",
        "=" * 80,
        "",
        "SECTION A: BASE MODEL EVALUATION",
        print_univariate_report(results.base_univariate),
        "",
        "SECTION B: FINE-TUNED MODEL EVALUATION", 
        print_univariate_report(results.ft_univariate),
        "",
        "SECTION C: MODEL COMPARISON",
        print_multivariate_report(
            results.stuart_maxwell,
            results.mcnemar_tests,
            results.cohens_kappa,
            results.class_names
        ),
        "",
        "SECTION D: PER-CLASS SIGNIFICANCE TESTING",
        print_paired_tests_report(results.paired_t_tests),
        "",
        "=" * 80,
        "SUMMARY",
        "=" * 80,
    ]
    
    # Summary statistics
    base_pass = "PASS" if results.base_univariate.gate_a_passed else "FAIL"
    ft_pass = "PASS" if results.ft_univariate.gate_a_passed else "FAIL"
    
    improvement = results.ft_univariate.macro_f1 - results.base_univariate.macro_f1
    pct_improvement = improvement / results.base_univariate.macro_f1 * 100
    
    sections.extend([
        f"Base Model Gate A:      {base_pass}",
        f"Fine-Tuned Model Gate A: {ft_pass}",
        "",
        f"Macro F1 Improvement:   {improvement:+.4f} ({pct_improvement:+.1f}%)",
        f"Stuart-Maxwell p-value: {results.stuart_maxwell.p_value:.6f}",
        f"Cohen's Kappa:          {results.cohens_kappa.kappa:.4f} ({results.cohens_kappa.interpretation})",
        "",
        "Per-Class Improvements (all significant after BH correction):" if all(
            r.reject_null_adjusted for r in results.paired_t_tests
        ) else "Per-Class Results:",
    ])
    
    for r in results.paired_t_tests:
        sig = "✓" if r.reject_null_adjusted else "✗"
        sections.append(f"  {r.class_name}: ΔF1 = {r.mean_difference:+.4f}, d = {r.cohens_d:.2f} {sig}")
    
    sections.extend(["", "=" * 80])
    
    return "\n".join(sections)


def generate_demo_data() -> Dict[str, Any]:
    """
    Generate demo data matching the research paper results.
    
    Returns:
        Dict with y_true, base_preds, ft_preds, and fold scores
    """
    np.random.seed(42)
    
    class_names = ["happy", "sad", "neutral"]
    n_per_class = 3000
    n_total = n_per_class * 3
    
    # Ground truth: balanced classes
    y_true = np.array([0] * n_per_class + [1] * n_per_class + [2] * n_per_class)
    
    # Base model confusion matrix (from paper Section 5.1)
    base_cm = np.array([
        [2436, 198, 366],   # Happy
        [171, 2082, 747],   # Sad
        [249, 408, 2343],   # Neutral
    ])
    
    # Fine-tuned confusion matrix (from paper Section 5.2)
    ft_cm = np.array([
        [2769, 63, 168],    # Happy
        [57, 2541, 402],    # Sad
        [87, 192, 2721],    # Neutral
    ])
    
    # Generate predictions matching confusion matrices
    def cm_to_preds(cm, n_per_class):
        preds = []
        for true_class in range(3):
            for pred_class in range(3):
                preds.extend([pred_class] * cm[true_class, pred_class])
        return np.array(preds)
    
    base_preds = cm_to_preds(base_cm, n_per_class)
    ft_preds = cm_to_preds(ft_cm, n_per_class)
    
    # Fold scores (from paper Section 4.5.1)
    base_fold_scores = {
        "happy": [0.808, 0.815, 0.810, 0.817, 0.811],
        "sad": [0.701, 0.688, 0.697, 0.692, 0.693],
        "neutral": [0.776, 0.784, 0.779, 0.786, 0.781],
    }
    
    ft_fold_scores = {
        "happy": [0.919, 0.927, 0.921, 0.925, 0.922],
        "sad": [0.851, 0.842, 0.849, 0.844, 0.848],
        "neutral": [0.897, 0.908, 0.901, 0.905, 0.899],
    }
    
    return {
        'y_true': y_true,
        'base_preds': base_preds,
        'ft_preds': ft_preds,
        'base_fold_scores': base_fold_scores,
        'ft_fold_scores': ft_fold_scores,
        'class_names': class_names,
    }


def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Phase 1 Statistical Analysis for Emotion Recognition"
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        help="Path to JSON file with predictions and fold scores"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("stats/results"),
        help="Directory for output files"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data from the research paper"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level for hypothesis tests"
    )
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.demo:
        print("Running with demo data from research paper...")
        data = generate_demo_data()
    elif args.data_path:
        with open(args.data_path) as f:
            data = json.load(f)
        # Convert lists to numpy arrays
        data['y_true'] = np.array(data['y_true'])
        data['base_preds'] = np.array(data['base_preds'])
        data['ft_preds'] = np.array(data['ft_preds'])
    else:
        parser.error("Either --data-path or --demo is required")
    
    # Run analysis
    results = run_full_analysis(
        y_true=data['y_true'],
        base_preds=data['base_preds'],
        ft_preds=data['ft_preds'],
        base_fold_scores=data['base_fold_scores'],
        ft_fold_scores=data['ft_fold_scores'],
        class_names=data['class_names'],
        alpha=args.alpha,
    )
    
    # Print report
    report = print_full_report(results)
    print(report)
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON results
    json_path = output_dir / "phase1_results.json"
    with open(json_path, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)
    print(f"\nResults saved to: {json_path}")
    
    # Save report
    report_path = output_dir / "phase1_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Generate plots
    try:
        plot_paths = create_all_plots(
            results.base_univariate,
            results.ft_univariate,
            results.stuart_maxwell,
            results.mcnemar_tests,
            results.paired_t_tests,
            output_dir,
            prefix="phase1"
        )
        print(f"Plots saved to: {output_dir}")
        for name, path in plot_paths.items():
            print(f"  - {name}: {path.name}")
    except ImportError as e:
        print(f"Warning: Could not generate plots (missing dependency): {e}")
    
    return results


if __name__ == "__main__":
    main()
