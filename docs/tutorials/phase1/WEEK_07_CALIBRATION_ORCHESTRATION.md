# Week 7: Calibration Metrics & Analysis Orchestration

**Phase 1 Tutorial Series**  
**Duration**: ~5 hours  
**Prerequisites**: Weeks 5-6 complete

---

## Overview

This week covers advanced statistical analysis topics:
- ECE and Brier score implementation
- Bootstrap confidence intervals
- Full analysis orchestrator script
- MLflow integration for stats logging

### Weekly Goals
- [ ] Understand and compute calibration metrics (ECE, Brier)
- [ ] Implement bootstrap confidence intervals
- [ ] Create orchestrator script for full analysis pipeline
- [ ] Integrate stats logging with MLflow

---

## Day 1: Calibration Metrics Deep Dive

### Why Calibration Matters

**Problem**: A model might be accurate but overconfident.

Example:
- Model predicts "happy" with 95% confidence
- But it's only correct 70% of the time when it says 95%
- This is **miscalibration**

**Why it matters for Reachy**:
- Confidence scores drive gesture intensity
- Overconfident wrong predictions → inappropriate robot responses
- Well-calibrated models enable better decision-making

### Expected Calibration Error (ECE)

**Intuition**: How well do confidence scores match actual accuracy?

**Calculation**:
1. Bin predictions by confidence (e.g., 0-10%, 10-20%, ...)
2. For each bin, compute:
   - Average confidence
   - Actual accuracy
3. ECE = weighted average of |confidence - accuracy| across bins

```python
def compute_ece(y_true, y_prob, n_bins=10):
    """
    Compute Expected Calibration Error.
    
    Args:
        y_true: True labels (n_samples,)
        y_prob: Predicted probabilities (n_samples, n_classes)
        n_bins: Number of confidence bins
    
    Returns:
        ECE value (lower is better)
    """
    # Get predicted class and confidence
    y_pred = np.argmax(y_prob, axis=1)
    confidences = np.max(y_prob, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    # Create bins
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        # Find samples in this bin
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            # Average confidence and accuracy in bin
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            
            # Weighted absolute difference
            ece += np.abs(avg_accuracy - avg_confidence) * prop_in_bin
    
    return ece
```

### Brier Score

**Intuition**: Mean squared error of probability predictions.

```python
def compute_brier(y_true, y_prob):
    """
    Compute Brier Score (multi-class).
    
    Args:
        y_true: True labels (n_samples,)
        y_prob: Predicted probabilities (n_samples, n_classes)
    
    Returns:
        Brier score (lower is better)
    """
    n_samples, n_classes = y_prob.shape
    
    # One-hot encode true labels
    y_true_onehot = np.zeros((n_samples, n_classes))
    y_true_onehot[np.arange(n_samples), y_true] = 1
    
    # Mean squared error
    brier = np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))
    
    return brier
```

### Gate A Calibration Thresholds

| Metric | Threshold | Interpretation |
|--------|-----------|----------------|
| ECE | ≤ 0.08 | Confidence within 8% of accuracy |
| Brier | ≤ 0.16 | Low probability prediction error |

### Exercises

1. **Compute ECE manually**:
   ```python
   import numpy as np
   
   # Sample data
   y_true = np.array([0, 1, 0, 1, 0])
   y_prob = np.array([
       [0.9, 0.1],  # Confident correct
       [0.3, 0.7],  # Less confident correct
       [0.8, 0.2],  # Confident correct
       [0.4, 0.6],  # Less confident correct
       [0.6, 0.4],  # Confident wrong!
   ])
   
   ece = compute_ece(y_true, y_prob, n_bins=5)
   print(f"ECE: {ece:.4f}")
   ```

2. **Visualize calibration**:
   ```python
   import matplotlib.pyplot as plt
   
   def plot_calibration(y_true, y_prob, n_bins=10):
       y_pred = np.argmax(y_prob, axis=1)
       confidences = np.max(y_prob, axis=1)
       accuracies = (y_pred == y_true).astype(float)
       
       bin_boundaries = np.linspace(0, 1, n_bins + 1)
       bin_centers = (bin_boundaries[:-1] + bin_boundaries[1:]) / 2
       
       bin_accuracies = []
       bin_confidences = []
       
       for i in range(n_bins):
           in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
           if in_bin.sum() > 0:
               bin_accuracies.append(accuracies[in_bin].mean())
               bin_confidences.append(confidences[in_bin].mean())
           else:
               bin_accuracies.append(0)
               bin_confidences.append(bin_centers[i])
       
       plt.figure(figsize=(8, 6))
       plt.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
       plt.bar(bin_centers, bin_accuracies, width=0.08, alpha=0.7, label='Model')
       plt.xlabel('Confidence')
       plt.ylabel('Accuracy')
       plt.title('Calibration Plot')
       plt.legend()
       plt.savefig('calibration_plot.png')
       plt.close()
   ```

### Checkpoint: Day 1
- [ ] Understand ECE calculation
- [ ] Understand Brier score
- [ ] Can compute both metrics
- [ ] Know Gate A thresholds

---

## Day 2: Bootstrap Confidence Intervals

### Why Bootstrap?

**Problem**: A single metric value doesn't tell us how reliable it is.

**Solution**: Bootstrap resampling gives confidence intervals.

Example:
- Macro F1 = 0.85
- With bootstrap: Macro F1 = 0.85 [0.82, 0.88] (95% CI)

Now we know the metric is reliably between 0.82 and 0.88.

### Bootstrap Algorithm

```python
def bootstrap_metric(y_true, y_pred, metric_fn, n_bootstrap=1000, ci=0.95):
    """
    Compute bootstrap confidence interval for a metric.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        metric_fn: Function that computes the metric
        n_bootstrap: Number of bootstrap samples
        ci: Confidence interval (e.g., 0.95 for 95%)
    
    Returns:
        (point_estimate, lower_bound, upper_bound)
    """
    n_samples = len(y_true)
    bootstrap_values = []
    
    for _ in range(n_bootstrap):
        # Sample with replacement
        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        y_true_boot = y_true[indices]
        y_pred_boot = y_pred[indices]
        
        # Compute metric on bootstrap sample
        value = metric_fn(y_true_boot, y_pred_boot)
        bootstrap_values.append(value)
    
    bootstrap_values = np.array(bootstrap_values)
    
    # Point estimate (original data)
    point_estimate = metric_fn(y_true, y_pred)
    
    # Confidence interval (percentile method)
    alpha = 1 - ci
    lower = np.percentile(bootstrap_values, alpha / 2 * 100)
    upper = np.percentile(bootstrap_values, (1 - alpha / 2) * 100)
    
    return point_estimate, lower, upper
```

### Using Bootstrap for Quality Gates

```python
from sklearn.metrics import f1_score, balanced_accuracy_score

# Compute F1 with confidence interval
def macro_f1(y_true, y_pred):
    return f1_score(y_true, y_pred, average='macro')

f1, f1_lower, f1_upper = bootstrap_metric(y_true, y_pred, macro_f1)
print(f"Macro F1: {f1:.4f} [{f1_lower:.4f}, {f1_upper:.4f}]")

# Check if confidence interval excludes threshold
threshold = 0.84
if f1_lower >= threshold:
    print("✅ Confidently passes Gate A (lower bound above threshold)")
elif f1_upper < threshold:
    print("❌ Confidently fails Gate A (upper bound below threshold)")
else:
    print("⚠️ Uncertain (confidence interval spans threshold)")
```

### Exercises

1. **Compute bootstrap CI for Macro F1**:
   ```python
   import numpy as np
   from sklearn.metrics import f1_score
   
   # Generate sample data
   np.random.seed(42)
   y_true = np.random.randint(0, 8, 500)
   y_pred = y_true.copy()
   y_pred[np.random.random(500) < 0.15] = np.random.randint(0, 8, (np.random.random(500) < 0.15).sum())
   
   f1, lower, upper = bootstrap_metric(
       y_true, y_pred, 
       lambda yt, yp: f1_score(yt, yp, average='macro'),
       n_bootstrap=1000
   )
   
   print(f"Macro F1: {f1:.4f} [{lower:.4f}, {upper:.4f}]")
   ```

2. **Compare with and without bootstrap**:
   - Run quality gates with point estimates only
   - Run with bootstrap confidence intervals
   - How does interpretation change?

### Checkpoint: Day 2
- [ ] Understand bootstrap resampling
- [ ] Can compute confidence intervals
- [ ] Know how CIs affect gate decisions

---

## Day 3: Analysis Orchestrator Script

### Why an Orchestrator?

Running three scripts manually is error-prone. An orchestrator:
- Runs all analyses in correct order
- Passes data between scripts
- Generates unified report
- Logs to MLflow

### Orchestrator Implementation

Create `stats/scripts/run_full_analysis.py`:

```python
#!/usr/bin/env python3
"""
Full Statistical Analysis Orchestrator

Runs all Phase 1 statistical analyses in sequence:
1. Quality Gate Metrics
2. Stuart-Maxwell Test
3. Per-class Paired t-Tests

Generates unified report and logs to MLflow.
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

# Import analysis modules
from quality_gate_metrics import run_quality_gates, MetricsReport
from stuart_maxwell_test import run_stuart_maxwell, StuartMaxwellResult
from perclass_paired_ttests import run_paired_ttests, PairedTTestsResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FullAnalysisReport:
    """Complete analysis report."""
    timestamp: str
    model_name: str
    
    # Quality gates
    quality_gates: dict
    gates_passed: bool
    
    # Stuart-Maxwell (optional)
    stuart_maxwell: Optional[dict] = None
    pattern_changed: Optional[bool] = None
    
    # Per-class tests (optional)
    perclass_tests: Optional[dict] = None
    improved_classes: Optional[list] = None
    degraded_classes: Optional[list] = None
    
    # Summary
    phase1_ready: bool = False
    recommendations: list = None


def run_full_analysis(
    predictions_path: Path,
    paired_predictions_path: Optional[Path] = None,
    fold_metrics_path: Optional[Path] = None,
    model_name: str = "model",
    output_dir: Path = Path("stats/results"),
) -> FullAnalysisReport:
    """
    Run complete statistical analysis pipeline.
    
    Args:
        predictions_path: Path to single model predictions (.npz)
        paired_predictions_path: Path to paired predictions for Stuart-Maxwell
        fold_metrics_path: Path to fold metrics for per-class tests
        model_name: Name for reporting
        output_dir: Directory for output files
    
    Returns:
        FullAnalysisReport with all results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    recommendations = []
    
    logger.info("=" * 60)
    logger.info("FULL STATISTICAL ANALYSIS")
    logger.info("=" * 60)
    
    # Step 1: Quality Gates
    logger.info("\n--- Step 1: Quality Gate Metrics ---")
    qg_result = run_quality_gates(predictions_path)
    
    gates_passed = qg_result.overall_pass
    if not gates_passed:
        recommendations.append("Model does not pass quality gates. Improve before proceeding.")
    
    # Step 2: Stuart-Maxwell (if paired data available)
    sm_result = None
    pattern_changed = None
    
    if paired_predictions_path and paired_predictions_path.exists():
        logger.info("\n--- Step 2: Stuart-Maxwell Test ---")
        sm_result = run_stuart_maxwell(paired_predictions_path)
        pattern_changed = sm_result.significant
        
        if not pattern_changed:
            recommendations.append("Fine-tuning did not significantly change predictions.")
    
    # Step 3: Per-class Tests (if fold data available and Stuart-Maxwell significant)
    pc_result = None
    improved_classes = []
    degraded_classes = []
    
    if fold_metrics_path and fold_metrics_path.exists():
        if pattern_changed or pattern_changed is None:
            logger.info("\n--- Step 3: Per-class Paired t-Tests ---")
            pc_result = run_paired_ttests(fold_metrics_path)
            
            for class_result in pc_result.class_results:
                if class_result.significant:
                    if class_result.mean_difference > 0:
                        improved_classes.append(class_result.class_name)
                    else:
                        degraded_classes.append(class_result.class_name)
            
            if degraded_classes:
                recommendations.append(f"Classes degraded: {', '.join(degraded_classes)}")
    
    # Determine Phase 1 readiness
    phase1_ready = gates_passed and len(degraded_classes) == 0
    
    if phase1_ready:
        recommendations.append("✅ Model is ready for Phase 1 deployment consideration.")
    
    # Build report
    report = FullAnalysisReport(
        timestamp=datetime.now().isoformat(),
        model_name=model_name,
        quality_gates=qg_result.to_dict(),
        gates_passed=gates_passed,
        stuart_maxwell=sm_result.to_dict() if sm_result else None,
        pattern_changed=pattern_changed,
        perclass_tests=pc_result.to_dict() if pc_result else None,
        improved_classes=improved_classes,
        degraded_classes=degraded_classes,
        phase1_ready=phase1_ready,
        recommendations=recommendations,
    )
    
    # Save report
    report_path = output_dir / f"full_analysis_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(asdict(report), f, indent=2)
    
    logger.info(f"\nReport saved to: {report_path}")
    
    # Print summary
    print_summary(report)
    
    return report


def print_summary(report: FullAnalysisReport):
    """Print analysis summary."""
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    
    print(f"\nModel: {report.model_name}")
    print(f"Timestamp: {report.timestamp}")
    
    print(f"\nQuality Gates: {'✅ PASS' if report.gates_passed else '❌ FAIL'}")
    
    if report.pattern_changed is not None:
        print(f"Pattern Changed: {'✅ Yes' if report.pattern_changed else '❌ No'}")
    
    if report.improved_classes:
        print(f"Improved Classes: {', '.join(report.improved_classes)}")
    
    if report.degraded_classes:
        print(f"Degraded Classes: {', '.join(report.degraded_classes)}")
    
    print(f"\nPhase 1 Ready: {'✅ YES' if report.phase1_ready else '❌ NO'}")
    
    if report.recommendations:
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  • {rec}")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Full Statistical Analysis")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--paired", type=Path, default=None)
    parser.add_argument("--folds", type=Path, default=None)
    parser.add_argument("--model-name", type=str, default="model")
    parser.add_argument("--output-dir", type=Path, default=Path("stats/results"))
    
    args = parser.parse_args()
    
    run_full_analysis(
        args.predictions,
        args.paired,
        args.folds,
        args.model_name,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
```

### Exercises

1. **Run orchestrator with demo data**:
   ```bash
   # First generate demo data
   python stats/scripts/01_quality_gate_metrics.py --demo --save-predictions stats/data/demo_preds.npz
   
   # Run orchestrator
   python stats/scripts/run_full_analysis.py --predictions stats/data/demo_preds.npz --model-name demo
   ```

2. **Run with all three analyses**:
   ```bash
   python stats/scripts/run_full_analysis.py \
       --predictions stats/data/predictions.npz \
       --paired stats/data/paired_predictions.npz \
       --folds stats/data/fold_metrics.json \
       --model-name full_test
   ```

### Checkpoint: Day 3
- [ ] Understand orchestrator purpose
- [ ] Can run full analysis pipeline
- [ ] Understand the unified report

---

## Day 4: MLflow Integration

### Why MLflow?

MLflow provides:
- Experiment tracking
- Metric logging
- Artifact storage
- Model versioning

### MLflow Stats Logger

Create `stats/scripts/mlflow_stats_logger.py`:

```python
"""
MLflow integration for statistical analysis logging.
"""

import mlflow
from pathlib import Path
from typing import Dict, Any, Optional
import json


class StatsMLflowLogger:
    """Log statistical analysis results to MLflow."""
    
    def __init__(
        self,
        experiment_name: str = "reachy_emotion_stats",
        tracking_uri: str = "http://localhost:5000"
    ):
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
    
    def log_quality_gates(self, report: Dict[str, Any], run_name: str = None):
        """Log quality gate metrics to MLflow."""
        with mlflow.start_run(run_name=run_name or "quality_gates"):
            # Log metrics
            mlflow.log_metric("macro_f1", report["metrics"]["macro_f1"])
            mlflow.log_metric("balanced_accuracy", report["metrics"]["balanced_accuracy"])
            mlflow.log_metric("f1_neutral", report["metrics"]["f1_neutral"])
            
            if "ece" in report["metrics"]:
                mlflow.log_metric("ece", report["metrics"]["ece"])
            if "brier" in report["metrics"]:
                mlflow.log_metric("brier", report["metrics"]["brier"])
            
            # Log gate results
            for gate, passed in report["quality_gates"]["results"].items():
                mlflow.log_metric(f"gate_{gate}_passed", int(passed))
            
            mlflow.log_metric("overall_pass", int(report["quality_gates"]["overall_pass"]))
            
            # Log report as artifact
            report_path = Path("/tmp/quality_gate_report.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            mlflow.log_artifact(report_path)
    
    def log_stuart_maxwell(self, result: Dict[str, Any], run_name: str = None):
        """Log Stuart-Maxwell test results."""
        with mlflow.start_run(run_name=run_name or "stuart_maxwell"):
            mlflow.log_metric("chi_squared", result["chi_squared"])
            mlflow.log_metric("p_value", result["p_value"])
            mlflow.log_metric("significant", int(result["significant"]))
            mlflow.log_metric("agreement_rate", result["agreement_rate"])
    
    def log_perclass_tests(self, result: Dict[str, Any], run_name: str = None):
        """Log per-class t-test results."""
        with mlflow.start_run(run_name=run_name or "perclass_tests"):
            mlflow.log_metric("n_significant", result["n_significant"])
            mlflow.log_metric("n_improved", result["n_improved"])
            mlflow.log_metric("n_degraded", result["n_degraded"])
            
            # Log per-class metrics
            for class_result in result["class_results"]:
                class_name = class_result["class_name"]
                mlflow.log_metric(f"{class_name}_diff", class_result["mean_difference"])
                mlflow.log_metric(f"{class_name}_pval", class_result["p_value_adjusted"])
                mlflow.log_metric(f"{class_name}_sig", int(class_result["significant"]))
    
    def log_full_analysis(self, report: Dict[str, Any], run_name: str = None):
        """Log complete analysis to a single MLflow run."""
        with mlflow.start_run(run_name=run_name or "full_analysis"):
            # Quality gates
            if report.get("quality_gates"):
                qg = report["quality_gates"]
                mlflow.log_metric("macro_f1", qg["metrics"]["macro_f1"])
                mlflow.log_metric("balanced_accuracy", qg["metrics"]["balanced_accuracy"])
                mlflow.log_metric("gates_passed", int(report["gates_passed"]))
            
            # Stuart-Maxwell
            if report.get("stuart_maxwell"):
                sm = report["stuart_maxwell"]
                mlflow.log_metric("sm_p_value", sm["p_value"])
                mlflow.log_metric("pattern_changed", int(report["pattern_changed"]))
            
            # Per-class
            if report.get("perclass_tests"):
                pc = report["perclass_tests"]
                mlflow.log_metric("n_improved", pc["n_improved"])
                mlflow.log_metric("n_degraded", pc["n_degraded"])
            
            # Overall
            mlflow.log_metric("phase1_ready", int(report["phase1_ready"]))
            
            # Tags
            mlflow.set_tag("model_name", report["model_name"])
            mlflow.set_tag("timestamp", report["timestamp"])
            
            # Full report as artifact
            report_path = Path("/tmp/full_analysis_report.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            mlflow.log_artifact(report_path)
```

### Using the Logger

```python
from mlflow_stats_logger import StatsMLflowLogger

# Initialize logger
logger = StatsMLflowLogger(
    experiment_name="reachy_emotion_stats",
    tracking_uri="http://localhost:5000"
)

# After running analysis
report = run_full_analysis(...)

# Log to MLflow
logger.log_full_analysis(report, run_name=f"analysis_{model_name}")
```

### Exercises

1. **Start MLflow server**:
   ```bash
   mlflow server --host 0.0.0.0 --port 5000
   ```

2. **Log analysis results**:
   ```python
   # Run analysis and log
   from run_full_analysis import run_full_analysis
   from mlflow_stats_logger import StatsMLflowLogger
   
   report = run_full_analysis(Path("stats/data/predictions.npz"))
   
   logger = StatsMLflowLogger()
   logger.log_full_analysis(report, run_name="test_analysis")
   ```

3. **View in MLflow UI**:
   - Open http://localhost:5000
   - Find your experiment
   - Compare metrics across runs

### Checkpoint: Day 4
- [ ] Understand MLflow purpose
- [ ] Can log metrics to MLflow
- [ ] Can view results in MLflow UI

---

## Day 5: Integration & Review

### Complete Workflow

```bash
# 1. Generate/prepare prediction data
python trainer/train_efficientnet.py --evaluate --save-predictions

# 2. Run full analysis with MLflow logging
python stats/scripts/run_full_analysis.py \
    --predictions outputs/predictions.npz \
    --paired outputs/paired_predictions.npz \
    --folds outputs/fold_metrics.json \
    --model-name efficientnet_b0_v1 \
    --log-mlflow

# 3. View results
# - Check stats/results/ for JSON reports
# - Check MLflow UI for tracked metrics
```

### Knowledge Check

1. What does ECE measure and why is it important?
2. How does bootstrap give us confidence intervals?
3. What is the purpose of the orchestrator script?
4. Why log stats to MLflow?
5. What determines if a model is "Phase 1 ready"?

### Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| ECE calculation | __ |
| Brier score | __ |
| Bootstrap CIs | __ |
| Orchestrator workflow | __ |
| MLflow logging | __ |

---

## Week 7 Deliverables

| Deliverable | Status |
|-------------|--------|
| ECE/Brier understood | [ ] |
| Bootstrap CIs implemented | [ ] |
| Orchestrator script working | [ ] |
| MLflow integration working | [ ] |
| Full pipeline tested | [ ] |

---

## Next Week

[Week 8: Gate A Validation & Training Integration](WEEK_08_GATE_A_VALIDATION.md) covers:
- Integrating stats with training pipeline
- Post-training analysis automation
- Phase 1 completion checklist
