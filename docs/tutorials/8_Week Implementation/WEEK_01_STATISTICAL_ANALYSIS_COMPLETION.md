# Week 1 Tutorial: Statistical Analysis Completion

**Project**: Reachy Emotion Recognition  
**Duration**: 5 days  
**Prerequisites**: Python environment with `stats/requirements-stats.txt` installed

---

## Overview

This week focuses on completing the statistical analysis toolkit by adding calibration metrics, creating an orchestrator script, and integrating with MLflow for experiment tracking.

### Weekly Goals
- [ ] Add ECE/Brier calibration metrics to quality gates script
- [ ] Create `run_full_analysis.py` orchestrator
- [ ] Integrate stats scripts with MLflow logging
- [ ] Add bootstrap confidence intervals

---

## Day 1: Add Calibration Metrics (ECE & Brier Score)

Gate A requires **ECE ≤ 0.08** and **Brier ≤ 0.16**. These metrics measure how well-calibrated the model's confidence scores are.

### Step 1.1: Understand Calibration Metrics

**Expected Calibration Error (ECE):**
- Measures the difference between predicted confidence and actual accuracy
- Bins predictions by confidence, computes accuracy per bin, then weighted average of |accuracy - confidence|

**Brier Score:**
- Mean squared error between predicted probabilities and one-hot encoded true labels
- Lower is better; perfect calibration = 0

### Step 1.2: Add Calibration Functions to Quality Gates Script

Open `stats/scripts/01_quality_gate_metrics.py` and add the following functions after the existing metric functions:

```python
def compute_ece(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    ECE measures the difference between predicted confidence and actual accuracy.
    
    ECE = Σ (|B_m| / n) * |acc(B_m) - conf(B_m)|
    
    where B_m is the set of samples in bin m.
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_proba: Predicted probabilities (shape: [n_samples, n_classes])
        n_bins: Number of bins for calibration (default: 10)
    
    Returns:
        ECE score in range [0, 1]
    """
    # Get predicted class and confidence
    y_pred = np.argmax(y_proba, axis=1)
    confidences = np.max(y_proba, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    # Create bins
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        # Find samples in this bin
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            ece += prop_in_bin * abs(avg_accuracy - avg_confidence)
    
    return float(ece)


def compute_brier_score(
    y_true: np.ndarray,
    y_proba: np.ndarray
) -> float:
    """
    Compute Brier Score (multi-class).
    
    Brier Score = (1/n) * Σ Σ (p_ij - y_ij)²
    
    where p_ij is predicted probability for sample i, class j
    and y_ij is 1 if true class is j, else 0.
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_proba: Predicted probabilities (shape: [n_samples, n_classes])
    
    Returns:
        Brier score (lower is better)
    """
    n_samples = len(y_true)
    n_classes = y_proba.shape[1]
    
    # One-hot encode true labels
    y_true_onehot = np.zeros((n_samples, n_classes))
    y_true_onehot[np.arange(n_samples), y_true] = 1
    
    # Compute Brier score
    brier = np.mean(np.sum((y_proba - y_true_onehot) ** 2, axis=1))
    
    return float(brier)
```

### Step 1.3: Update Quality Gates Configuration

Add calibration thresholds to the `QUALITY_GATES` dictionary:

```python
QUALITY_GATES = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.82,
    "f1_neutral": 0.80,
    "ece": 0.08,      # Gate A: ECE ≤ 0.08
    "brier": 0.16,    # Gate A: Brier ≤ 0.16
}
```

### Step 1.4: Update MetricsReport Dataclass

Add calibration fields to the `MetricsReport` dataclass:

```python
@dataclass
class MetricsReport:
    # ... existing fields ...
    
    # Calibration metrics (optional, require probabilities)
    ece: Optional[float] = None
    brier_score: Optional[float] = None
```

### Step 1.5: Update compute_all_metrics Function

Modify the function to accept optional probability predictions:

```python
def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None  # Add this parameter
) -> MetricsReport:
    # ... existing code ...
    
    # Compute calibration metrics if probabilities provided
    ece = None
    brier = None
    if y_proba is not None:
        ece = compute_ece(y_true, y_proba)
        brier = compute_brier_score(y_true, y_proba)
    
    # Update gates_passed to include calibration
    if ece is not None:
        gates_passed["ece"] = ece <= QUALITY_GATES["ece"]
    if brier is not None:
        gates_passed["brier"] = brier <= QUALITY_GATES["brier"]
    
    # ... return MetricsReport with new fields ...
```

### Step 1.6: Update Demo Mode

Modify `generate_demo_predictions()` to also generate probability scores:

```python
def generate_demo_predictions(
    n_samples: int = 2000,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic predictions with probabilities."""
    np.random.seed(seed)
    
    # ... existing code for y_true, y_pred ...
    
    # Generate probability scores
    n_classes = len(EMOTION_CLASSES)
    y_proba = np.random.dirichlet(np.ones(n_classes) * 2, size=n_samples)
    
    # Adjust probabilities to be somewhat calibrated
    for i in range(n_samples):
        if y_true[i] == y_pred[i]:
            # Boost confidence for correct predictions
            y_proba[i, y_pred[i]] += 0.3
        y_proba[i] /= y_proba[i].sum()  # Renormalize
    
    return y_true, y_pred, y_proba
```

### Step 1.7: Test Calibration Metrics

Run the updated demo:

```bash
python stats/scripts/01_quality_gate_metrics.py --demo
```

Verify the output includes ECE and Brier score in the quality gate evaluation.

### Checkpoint: Day 1 Complete
- [ ] ECE function implemented and tested
- [ ] Brier score function implemented and tested
- [ ] Quality gates updated with calibration thresholds
- [ ] Demo mode generates probability scores

---

## Day 2: Create Orchestrator Script

Create a single entry point that runs all three statistical analyses in sequence.

### Step 2.1: Create the Orchestrator Script

Create `stats/scripts/run_full_analysis.py`:

```python
#!/usr/bin/env python3
"""
Full Statistical Analysis Pipeline Orchestrator
================================================

Runs all Phase 1 statistical analyses in sequence:
1. Quality Gate Metrics (single model evaluation)
2. Stuart-Maxwell Test (model comparison)
3. Per-class Paired t-Tests (class-level changes)

Usage:
    # Demo mode
    python run_full_analysis.py --demo
    
    # With real data
    python run_full_analysis.py \
        --predictions results/predictions.npz \
        --paired-predictions results/paired_predictions.npz \
        --fold-metrics results/fold_metrics.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from quality_gate_metrics import (
    compute_all_metrics as compute_quality_gates,
    print_report as print_quality_report,
    save_report as save_quality_report,
    generate_demo_predictions,
)
from stuart_maxwell_test import (
    stuart_maxwell_test,
    print_report as print_sm_report,
    save_report as save_sm_report,
    generate_demo_paired_predictions,
)
from perclass_paired_ttests import (
    run_perclass_paired_ttests,
    print_report as print_ttest_report,
    save_report as save_ttest_report,
    generate_demo_fold_metrics,
)


def run_full_analysis(
    predictions_path: Optional[Path] = None,
    paired_predictions_path: Optional[Path] = None,
    fold_metrics_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    demo: bool = False,
) -> Dict[str, Any]:
    """
    Run complete statistical analysis pipeline.
    
    Args:
        predictions_path: Path to single model predictions (.npz)
        paired_predictions_path: Path to paired predictions (.npz)
        fold_metrics_path: Path to fold-level metrics (.json)
        output_dir: Output directory for results
        demo: Run in demo mode with synthetic data
    
    Returns:
        Dictionary with all analysis results
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "mode": "demo" if demo else "production",
        "analyses": {},
    }
    
    output_dir = output_dir or Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 70)
    print("FULL STATISTICAL ANALYSIS PIPELINE")
    print("=" * 70)
    
    # =========================================================================
    # Analysis 1: Quality Gate Metrics
    # =========================================================================
    print("\n" + "-" * 70)
    print("ANALYSIS 1: Quality Gate Metrics")
    print("-" * 70)
    
    if demo:
        y_true, y_pred, y_proba = generate_demo_predictions()
    else:
        data = np.load(predictions_path)
        y_true, y_pred = data['y_true'], data['y_pred']
        y_proba = data.get('y_proba', None)
    
    quality_report = compute_quality_gates(y_true, y_pred, y_proba)
    print_quality_report(quality_report)
    save_quality_report(quality_report, output_dir / "quality_gate_metrics.json")
    
    results["analyses"]["quality_gates"] = {
        "overall_pass": quality_report.overall_pass,
        "macro_f1": quality_report.macro_f1,
        "balanced_accuracy": quality_report.balanced_accuracy,
        "f1_neutral": quality_report.f1_neutral,
        "ece": quality_report.ece,
        "brier": quality_report.brier_score,
    }
    
    # =========================================================================
    # Analysis 2: Stuart-Maxwell Test
    # =========================================================================
    print("\n" + "-" * 70)
    print("ANALYSIS 2: Stuart-Maxwell Test (Model Comparison)")
    print("-" * 70)
    
    if demo:
        base_preds, ft_preds = generate_demo_paired_predictions()
    else:
        data = np.load(paired_predictions_path)
        base_preds, ft_preds = data['base_preds'], data['finetuned_preds']
    
    sm_result = stuart_maxwell_test(base_preds, ft_preds)
    print_sm_report(sm_result)
    save_sm_report(sm_result, output_dir / "stuart_maxwell_results.json")
    
    results["analyses"]["stuart_maxwell"] = {
        "significant": sm_result.significant,
        "p_value": sm_result.p_value,
        "chi_squared": sm_result.chi_squared,
        "agreement_rate": sm_result.agreement_rate,
    }
    
    # =========================================================================
    # Analysis 3: Per-class Paired t-Tests
    # =========================================================================
    print("\n" + "-" * 70)
    print("ANALYSIS 3: Per-class Paired t-Tests")
    print("-" * 70)
    
    if demo:
        base_metrics, ft_metrics = generate_demo_fold_metrics()
    else:
        with open(fold_metrics_path, 'r') as f:
            data = json.load(f)
        base_metrics = data['base_metrics']
        ft_metrics = data['finetuned_metrics']
    
    ttest_result = run_perclass_paired_ttests(base_metrics, ft_metrics)
    print_ttest_report(ttest_result)
    save_ttest_report(ttest_result, output_dir / "perclass_ttests_results.json")
    
    results["analyses"]["perclass_ttests"] = {
        "n_significant": ttest_result.n_significant,
        "n_improved": ttest_result.n_improved,
        "n_degraded": ttest_result.n_degraded,
        "improved_classes": ttest_result.improved_classes,
        "degraded_classes": ttest_result.degraded_classes,
    }
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    
    print(f"\n1. Quality Gates: {'PASS' if quality_report.overall_pass else 'FAIL'}")
    print(f"   - Macro F1: {quality_report.macro_f1:.4f} (threshold: 0.84)")
    print(f"   - Balanced Accuracy: {quality_report.balanced_accuracy:.4f} (threshold: 0.82)")
    
    print(f"\n2. Stuart-Maxwell: {'SIGNIFICANT' if sm_result.significant else 'NOT SIGNIFICANT'}")
    print(f"   - p-value: {sm_result.p_value:.6f}")
    print(f"   - Agreement rate: {sm_result.agreement_rate:.2%}")
    
    print(f"\n3. Per-class Changes: {ttest_result.n_significant}/{ttest_result.n_classes} significant")
    if ttest_result.improved_classes:
        print(f"   - Improved: {', '.join(ttest_result.improved_classes)}")
    if ttest_result.degraded_classes:
        print(f"   - Degraded: {', '.join(ttest_result.degraded_classes)}")
    
    # Save combined results
    with open(output_dir / "full_analysis_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nAll results saved to: {output_dir}")
    print("=" * 70)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run full Phase 1 statistical analysis pipeline"
    )
    parser.add_argument("--demo", action="store_true", help="Run with synthetic data")
    parser.add_argument("--predictions", type=Path, help="Single model predictions (.npz)")
    parser.add_argument("--paired-predictions", type=Path, help="Paired predictions (.npz)")
    parser.add_argument("--fold-metrics", type=Path, help="Fold-level metrics (.json)")
    parser.add_argument("--output", type=Path, help="Output directory")
    
    args = parser.parse_args()
    
    if args.demo:
        run_full_analysis(demo=True, output_dir=args.output)
    elif args.predictions and args.paired_predictions and args.fold_metrics:
        run_full_analysis(
            predictions_path=args.predictions,
            paired_predictions_path=args.paired_predictions,
            fold_metrics_path=args.fold_metrics,
            output_dir=args.output,
        )
    else:
        parser.print_help()
        print("\nError: Provide --demo or all three data paths")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 2.2: Test the Orchestrator

```bash
python stats/scripts/run_full_analysis.py --demo
```

### Checkpoint: Day 2 Complete
- [ ] Orchestrator script created
- [ ] Demo mode runs all three analyses
- [ ] Combined results saved to JSON

---

## Day 3: MLflow Integration

Integrate statistical analysis with MLflow for experiment tracking.

### Step 3.1: Create MLflow Stats Logger

Create `stats/scripts/mlflow_stats_logger.py`:

```python
"""
MLflow integration for statistical analysis results.

Logs quality gate metrics, model comparison results, and per-class
changes to MLflow experiments for tracking across training runs.
"""

import mlflow
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class StatsMLflowLogger:
    """Log statistical analysis results to MLflow."""
    
    def __init__(
        self,
        tracking_uri: str = "file:///mlruns",
        experiment_name: str = "reachy_emotion_stats"
    ):
        """
        Initialize MLflow logger.
        
        Args:
            tracking_uri: MLflow tracking URI
            experiment_name: Experiment name for stats runs
        """
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self.experiment_name = experiment_name
    
    def log_quality_gates(
        self,
        report: Dict[str, Any],
        run_id: Optional[str] = None,
        model_name: str = "unknown"
    ) -> str:
        """
        Log quality gate metrics to MLflow.
        
        Args:
            report: Quality gate report dictionary
            run_id: Optional existing run ID to log to
            model_name: Model name for tagging
        
        Returns:
            MLflow run ID
        """
        with mlflow.start_run(run_id=run_id) as run:
            # Log parameters
            mlflow.log_param("model_name", model_name)
            mlflow.log_param("analysis_type", "quality_gates")
            
            # Log metrics
            mlflow.log_metric("macro_f1", report.get("macro_f1", 0))
            mlflow.log_metric("balanced_accuracy", report.get("balanced_accuracy", 0))
            mlflow.log_metric("f1_neutral", report.get("f1_neutral", 0))
            mlflow.log_metric("accuracy", report.get("accuracy", 0))
            
            if report.get("ece") is not None:
                mlflow.log_metric("ece", report["ece"])
            if report.get("brier_score") is not None:
                mlflow.log_metric("brier_score", report["brier_score"])
            
            # Log gate pass/fail as metrics (1 = pass, 0 = fail)
            gates = report.get("gates_passed", {})
            for gate_name, passed in gates.items():
                mlflow.log_metric(f"gate_{gate_name}_pass", 1 if passed else 0)
            
            mlflow.log_metric("overall_pass", 1 if report.get("overall_pass") else 0)
            
            # Log per-class F1 scores
            for cls, f1 in report.get("per_class_f1", {}).items():
                mlflow.log_metric(f"f1_{cls}", f1)
            
            # Log tags
            mlflow.set_tag("analysis", "quality_gates")
            mlflow.set_tag("overall_result", "PASS" if report.get("overall_pass") else "FAIL")
            
            return run.info.run_id
    
    def log_stuart_maxwell(
        self,
        result: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> str:
        """
        Log Stuart-Maxwell test results to MLflow.
        
        Args:
            result: Stuart-Maxwell result dictionary
            run_id: Optional existing run ID to log to
        
        Returns:
            MLflow run ID
        """
        with mlflow.start_run(run_id=run_id) as run:
            mlflow.log_param("analysis_type", "stuart_maxwell")
            
            mlflow.log_metric("chi_squared", result.get("chi_squared", 0))
            mlflow.log_metric("p_value", result.get("p_value", 1))
            mlflow.log_metric("agreement_rate", result.get("agreement_rate", 0))
            mlflow.log_metric("significant", 1 if result.get("significant") else 0)
            
            # Log marginal differences
            for cls, diff in result.get("marginal_differences", {}).items():
                mlflow.log_metric(f"marginal_diff_{cls}", diff)
            
            mlflow.set_tag("analysis", "stuart_maxwell")
            mlflow.set_tag("result", "SIGNIFICANT" if result.get("significant") else "NOT_SIGNIFICANT")
            
            return run.info.run_id
    
    def log_perclass_ttests(
        self,
        result: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> str:
        """
        Log per-class t-test results to MLflow.
        
        Args:
            result: Per-class t-test result dictionary
            run_id: Optional existing run ID to log to
        
        Returns:
            MLflow run ID
        """
        with mlflow.start_run(run_id=run_id) as run:
            mlflow.log_param("analysis_type", "perclass_ttests")
            mlflow.log_param("correction_method", result.get("correction_method", "BH"))
            
            mlflow.log_metric("n_significant", result.get("n_significant", 0))
            mlflow.log_metric("n_improved", result.get("n_improved", 0))
            mlflow.log_metric("n_degraded", result.get("n_degraded", 0))
            
            # Log per-class results
            for cls_result in result.get("class_results", []):
                cls = cls_result.get("emotion_class", "unknown")
                mlflow.log_metric(f"diff_{cls}", cls_result.get("mean_difference", 0))
                mlflow.log_metric(f"pval_adj_{cls}", cls_result.get("p_value_adjusted", 1))
                mlflow.log_metric(f"sig_{cls}", 1 if cls_result.get("significant") else 0)
            
            mlflow.set_tag("analysis", "perclass_ttests")
            mlflow.set_tag("improved_classes", ",".join(result.get("improved_classes", [])))
            mlflow.set_tag("degraded_classes", ",".join(result.get("degraded_classes", [])))
            
            return run.info.run_id
    
    def log_full_analysis(
        self,
        results: Dict[str, Any],
        artifacts_dir: Optional[Path] = None
    ) -> str:
        """
        Log complete analysis results to a single MLflow run.
        
        Args:
            results: Combined results from run_full_analysis
            artifacts_dir: Directory containing result files to log as artifacts
        
        Returns:
            MLflow run ID
        """
        with mlflow.start_run() as run:
            mlflow.log_param("analysis_type", "full_pipeline")
            mlflow.log_param("mode", results.get("mode", "unknown"))
            
            analyses = results.get("analyses", {})
            
            # Quality gates
            qg = analyses.get("quality_gates", {})
            mlflow.log_metric("macro_f1", qg.get("macro_f1", 0))
            mlflow.log_metric("balanced_accuracy", qg.get("balanced_accuracy", 0))
            mlflow.log_metric("overall_pass", 1 if qg.get("overall_pass") else 0)
            
            # Stuart-Maxwell
            sm = analyses.get("stuart_maxwell", {})
            mlflow.log_metric("sm_p_value", sm.get("p_value", 1))
            mlflow.log_metric("sm_significant", 1 if sm.get("significant") else 0)
            
            # Per-class t-tests
            tt = analyses.get("perclass_ttests", {})
            mlflow.log_metric("n_improved", tt.get("n_improved", 0))
            mlflow.log_metric("n_degraded", tt.get("n_degraded", 0))
            
            # Log artifacts
            if artifacts_dir and artifacts_dir.exists():
                for f in artifacts_dir.glob("*.json"):
                    mlflow.log_artifact(str(f))
                for f in artifacts_dir.glob("*.png"):
                    mlflow.log_artifact(str(f))
            
            mlflow.set_tag("analysis", "full_pipeline")
            
            return run.info.run_id
```

### Step 3.2: Update Orchestrator to Use MLflow

Add MLflow logging to `run_full_analysis.py`:

```python
# At the end of run_full_analysis function:

# Log to MLflow if available
try:
    from mlflow_stats_logger import StatsMLflowLogger
    
    logger = StatsMLflowLogger()
    mlflow_run_id = logger.log_full_analysis(results, output_dir)
    print(f"\nMLflow run ID: {mlflow_run_id}")
    results["mlflow_run_id"] = mlflow_run_id
except ImportError:
    print("\nMLflow not available, skipping experiment logging")
except Exception as e:
    print(f"\nMLflow logging failed: {e}")
```

### Step 3.3: Test MLflow Integration

```bash
# Ensure MLflow is installed
pip install mlflow

# Run analysis with MLflow logging
python stats/scripts/run_full_analysis.py --demo

# View results in MLflow UI
mlflow ui --port 5001
```

### Checkpoint: Day 3 Complete
- [ ] MLflow stats logger created
- [ ] Orchestrator logs to MLflow
- [ ] Results visible in MLflow UI

---

## Day 4: Bootstrap Confidence Intervals

Add bootstrap confidence intervals for more robust uncertainty quantification.

### Step 4.1: Create Bootstrap Utilities

Create `stats/scripts/bootstrap_utils.py`:

```python
"""
Bootstrap confidence interval utilities for statistical analysis.

Provides non-parametric confidence intervals for metrics using
bootstrap resampling.
"""

import numpy as np
from typing import Callable, Tuple, List, Dict, Any
from dataclasses import dataclass


@dataclass
class BootstrapResult:
    """Result of bootstrap confidence interval estimation."""
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int
    bootstrap_distribution: List[float]


def bootstrap_ci(
    data: np.ndarray,
    statistic_fn: Callable[[np.ndarray], float],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42
) -> BootstrapResult:
    """
    Compute bootstrap confidence interval for a statistic.
    
    Args:
        data: Input data array
        statistic_fn: Function that computes the statistic from data
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (e.g., 0.95 for 95% CI)
        seed: Random seed for reproducibility
    
    Returns:
        BootstrapResult with point estimate and confidence interval
    """
    np.random.seed(seed)
    n = len(data)
    
    # Point estimate
    point_estimate = statistic_fn(data)
    
    # Bootstrap resampling
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        # Sample with replacement
        indices = np.random.randint(0, n, size=n)
        bootstrap_sample = data[indices]
        bootstrap_stats.append(statistic_fn(bootstrap_sample))
    
    bootstrap_stats = np.array(bootstrap_stats)
    
    # Percentile method for CI
    alpha = 1 - confidence_level
    ci_lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return BootstrapResult(
        point_estimate=float(point_estimate),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        confidence_level=confidence_level,
        n_bootstrap=n_bootstrap,
        bootstrap_distribution=bootstrap_stats.tolist(),
    )


def bootstrap_metric_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42
) -> BootstrapResult:
    """
    Compute bootstrap CI for a classification metric.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        metric_fn: Function(y_true, y_pred) -> float
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level
        seed: Random seed
    
    Returns:
        BootstrapResult with point estimate and CI
    """
    np.random.seed(seed)
    n = len(y_true)
    
    # Point estimate
    point_estimate = metric_fn(y_true, y_pred)
    
    # Bootstrap resampling
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        indices = np.random.randint(0, n, size=n)
        y_true_boot = y_true[indices]
        y_pred_boot = y_pred[indices]
        bootstrap_stats.append(metric_fn(y_true_boot, y_pred_boot))
    
    bootstrap_stats = np.array(bootstrap_stats)
    
    alpha = 1 - confidence_level
    ci_lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return BootstrapResult(
        point_estimate=float(point_estimate),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        confidence_level=confidence_level,
        n_bootstrap=n_bootstrap,
        bootstrap_distribution=bootstrap_stats.tolist(),
    )


def compute_all_metrics_with_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95
) -> Dict[str, BootstrapResult]:
    """
    Compute all quality gate metrics with bootstrap CIs.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level
    
    Returns:
        Dictionary mapping metric name to BootstrapResult
    """
    from sklearn.metrics import f1_score, balanced_accuracy_score
    
    results = {}
    
    # Macro F1
    results["macro_f1"] = bootstrap_metric_ci(
        y_true, y_pred,
        lambda yt, yp: f1_score(yt, yp, average='macro', zero_division=0),
        n_bootstrap, confidence_level
    )
    
    # Balanced Accuracy
    results["balanced_accuracy"] = bootstrap_metric_ci(
        y_true, y_pred,
        balanced_accuracy_score,
        n_bootstrap, confidence_level
    )
    
    # F1 Neutral (assuming neutral is class index 5)
    NEUTRAL_INDEX = 5
    def f1_neutral(yt, yp):
        f1s = f1_score(yt, yp, average=None, zero_division=0)
        return f1s[NEUTRAL_INDEX] if len(f1s) > NEUTRAL_INDEX else 0.0
    
    results["f1_neutral"] = bootstrap_metric_ci(
        y_true, y_pred,
        f1_neutral,
        n_bootstrap, confidence_level
    )
    
    return results
```

### Step 4.2: Add CI Option to Quality Gates Script

Update `01_quality_gate_metrics.py` to optionally compute bootstrap CIs:

```python
# Add to argument parser:
parser.add_argument(
    "--bootstrap",
    action="store_true",
    help="Compute bootstrap confidence intervals"
)
parser.add_argument(
    "--n-bootstrap",
    type=int,
    default=1000,
    help="Number of bootstrap samples (default: 1000)"
)

# In main analysis:
if args.bootstrap:
    from bootstrap_utils import compute_all_metrics_with_ci
    
    ci_results = compute_all_metrics_with_ci(
        y_true, y_pred,
        n_bootstrap=args.n_bootstrap
    )
    
    print("\n--- BOOTSTRAP CONFIDENCE INTERVALS (95%) ---")
    for metric, result in ci_results.items():
        print(f"{metric}: {result.point_estimate:.4f} "
              f"[{result.ci_lower:.4f}, {result.ci_upper:.4f}]")
```

### Step 4.3: Test Bootstrap CIs

```bash
python stats/scripts/01_quality_gate_metrics.py --demo --bootstrap
```

### Checkpoint: Day 4 Complete
- [ ] Bootstrap utilities created
- [ ] Quality gates script supports --bootstrap flag
- [ ] CIs computed and displayed

---

## Day 5: Documentation & Testing

Finalize Week 1 deliverables with documentation and testing.

### Step 5.1: Update Curriculum Index

Add new content to `stats/curriculum/CURRICULUM_INDEX.md`:

```markdown
### Advanced Topics

#### Calibration Metrics
- [ECE and Brier Score Guide](TUTORIAL_04_CALIBRATION_METRICS.md)
- Understanding model confidence calibration
- Gate A calibration requirements

#### Bootstrap Confidence Intervals
- [Bootstrap CI Tutorial](TUTORIAL_05_BOOTSTRAP_CI.md)
- Non-parametric uncertainty quantification
- When to use bootstrap vs. parametric CIs
```

### Step 5.2: Run Full Test Suite

```bash
# Test all scripts
python stats/scripts/01_quality_gate_metrics.py --demo
python stats/scripts/02_stuart_maxwell_test.py --demo
python stats/scripts/03_perclass_paired_ttests.py --demo
python stats/scripts/run_full_analysis.py --demo

# Verify outputs
ls stats/results/
```

### Step 5.3: Update Task Checklist

Mark Week 1 items as complete in `stats/task_checklist.md`.

### Checkpoint: Day 5 Complete
- [ ] All scripts tested
- [ ] Documentation updated
- [ ] Task checklist updated

---

## Week 1 Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| ECE/Brier calibration metrics | ✅ | `01_quality_gate_metrics.py` |
| Orchestrator script | ✅ | `run_full_analysis.py` |
| MLflow integration | ✅ | `mlflow_stats_logger.py` |
| Bootstrap CIs | ✅ | `bootstrap_utils.py` |
| Updated documentation | ✅ | `curriculum/` |

---

## Next Steps

Proceed to [Week 2: Training Pipeline Integration](WEEK_02_TRAINING_PIPELINE_INTEGRATION.md).
