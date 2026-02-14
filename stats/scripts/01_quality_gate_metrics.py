"""
Script 1: Univariate Quality Gate Metrics
=========================================

Purpose:
    Evaluate emotion classification model performance against quality gate thresholds.
    This script computes the three key metrics required for Phase 1 pass/fail decisions:
    
    1. Macro F1 Score (≥ 0.84) - Overall classification quality
    2. Balanced Accuracy (≥ 0.82) - Class imbalance protection  
    3. F1 Neutral (≥ 0.80) - Phase 2 baseline stability

Usage:
    # With real predictions
    python 01_quality_gate_metrics.py --predictions results/predictions.npz
    
    # Demo mode with synthetic data
    python 01_quality_gate_metrics.py --demo

Output:
    - Console summary with pass/fail status
    - JSON file with detailed metrics
    - Confusion matrix visualization (optional)

Author: Reachy Emotion Team
Version: 1.0.0
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_QUALITY_GATES = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "f1_neutral": 0.75,
}

DEFAULT_EMOTION_CLASSES = ["happy", "sad", "neutral"]

QUALITY_GATES = dict(DEFAULT_QUALITY_GATES)
EMOTION_CLASSES = list(DEFAULT_EMOTION_CLASSES)
NEUTRAL_INDEX = EMOTION_CLASSES.index("neutral")


def _configure_runtime(classes: Optional[List[str]] = None, quality_gates: Optional[Dict[str, float]] = None) -> None:
    """Configure runtime class labels and quality gate thresholds."""
    global EMOTION_CLASSES, NEUTRAL_INDEX, QUALITY_GATES

    if classes:
        normalized = [str(x).strip().lower() for x in classes if str(x).strip()]
        if len(normalized) < 2:
            raise ValueError("At least 2 emotion classes are required")
        EMOTION_CLASSES = normalized

    if "neutral" not in EMOTION_CLASSES:
        raise ValueError("Emotion classes must include 'neutral' for f1_neutral gate")
    NEUTRAL_INDEX = EMOTION_CLASSES.index("neutral")

    QUALITY_GATES = dict(DEFAULT_QUALITY_GATES)
    if quality_gates:
        QUALITY_GATES.update({k: float(v) for k, v in quality_gates.items()})


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class QualityGateResult:
    """Result of a single quality gate evaluation."""
    metric_name: str
    value: float
    threshold: float
    passed: bool
    
    def __str__(self) -> str:
        status = "PASS ✓" if self.passed else "FAIL ✗"
        return f"{self.metric_name}: {self.value:.4f} (threshold: {self.threshold}) [{status}]"


@dataclass
class MetricsReport:
    """Complete metrics report for a model evaluation."""
    # Quality gate metrics
    macro_f1: float
    balanced_accuracy: float
    f1_neutral: float
    
    # Additional metrics
    accuracy: float
    macro_precision: float
    macro_recall: float
    
    # Per-class metrics
    per_class_f1: Dict[str, float]
    per_class_precision: Dict[str, float]
    per_class_recall: Dict[str, float]
    
    # Quality gate results
    gates_passed: Dict[str, bool]
    overall_pass: bool
    
    # Confusion matrix
    confusion_matrix: List[List[int]]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Ensure booleans are native Python bool for JSON serialization
        data["gates_passed"] = {k: bool(v) for k, v in self.gates_passed.items()}
        data["overall_pass"] = bool(self.overall_pass)
        return data


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================

def compute_macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Macro F1 Score.
    
    Macro F1 is the unweighted mean of per-class F1 scores:
    
        F1_macro = (1/K) * Σ F1_c
    
    where K is the number of classes and F1_c is the F1 score for class c.
    
    This metric treats all classes equally regardless of their frequency,
    making it appropriate for imbalanced datasets.
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_pred: Predicted labels (shape: [n_samples])
    
    Returns:
        Macro F1 score in range [0, 1]
    """
    return f1_score(y_true, y_pred, average='macro', zero_division=0)


def compute_balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Balanced Accuracy.
    
    Balanced accuracy is the macro-averaged recall across classes:
    
        Balanced Accuracy = (1/K) * Σ Recall_c
    
    where Recall_c = TP_c / (TP_c + FN_c) for class c.
    
    This is equivalent to accuracy computed under uniform class priors,
    protecting against classifiers that exploit class imbalance.
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_pred: Predicted labels (shape: [n_samples])
    
    Returns:
        Balanced accuracy in range [0, 1]
    """
    return balanced_accuracy_score(y_true, y_pred)


def compute_f1_neutral(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute F1 Score for the Neutral class specifically.
    
    F1_neutral = 2 * (Precision_neutral * Recall_neutral) / (Precision_neutral + Recall_neutral)
    
    where:
        Precision_neutral = TP_neutral / (TP_neutral + FP_neutral)
        Recall_neutral = TP_neutral / (TP_neutral + FN_neutral)
    
    This metric is critical because neutral serves as the baseline for
    Phase 2 degree-of-emotion modeling. Poor neutral discrimination
    propagates systematic errors into intensity measurements.
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_pred: Predicted labels (shape: [n_samples])
    
    Returns:
        F1 score for neutral class in range [0, 1]
    """
    # Get per-class F1 scores
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    return per_class_f1[NEUTRAL_INDEX]


def compute_per_class_metrics(
    y_true: np.ndarray, 
    y_pred: np.ndarray
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    """
    Compute precision, recall, and F1 for each emotion class.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
    
    Returns:
        Tuple of (per_class_f1, per_class_precision, per_class_recall) dicts
    """
    f1_scores = f1_score(y_true, y_pred, average=None, zero_division=0)
    precision_scores = precision_score(y_true, y_pred, average=None, zero_division=0)
    recall_scores = recall_score(y_true, y_pred, average=None, zero_division=0)
    
    per_class_f1 = {cls: float(f1_scores[i]) for i, cls in enumerate(EMOTION_CLASSES)}
    per_class_precision = {cls: float(precision_scores[i]) for i, cls in enumerate(EMOTION_CLASSES)}
    per_class_recall = {cls: float(recall_scores[i]) for i, cls in enumerate(EMOTION_CLASSES)}
    
    return per_class_f1, per_class_precision, per_class_recall


def evaluate_quality_gates(
    macro_f1: float,
    balanced_accuracy: float,
    f1_neutral: float
) -> Tuple[Dict[str, bool], bool]:
    """
    Evaluate metrics against quality gate thresholds.
    
    Args:
        macro_f1: Computed macro F1 score
        balanced_accuracy: Computed balanced accuracy
        f1_neutral: Computed F1 for neutral class
    
    Returns:
        Tuple of (gates_passed dict, overall_pass bool)
    """
    gates_passed = {
        "macro_f1": macro_f1 >= QUALITY_GATES["macro_f1"],
        "balanced_accuracy": balanced_accuracy >= QUALITY_GATES["balanced_accuracy"],
        "f1_neutral": f1_neutral >= QUALITY_GATES["f1_neutral"],
    }
    overall_pass = all(gates_passed.values())
    return gates_passed, overall_pass


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> MetricsReport:
    """
    Compute all metrics and evaluate quality gates.
    
    This is the main entry point for model evaluation. It computes:
    - Quality gate metrics (Macro F1, Balanced Accuracy, F1 Neutral)
    - Additional aggregate metrics (Accuracy, Macro Precision, Macro Recall)
    - Per-class metrics for all emotion classes
    - Confusion matrix
    - Quality gate pass/fail status
    
    Args:
        y_true: Ground truth labels (shape: [n_samples])
        y_pred: Predicted labels (shape: [n_samples])
    
    Returns:
        MetricsReport containing all computed metrics and gate results
    """
    # Quality gate metrics
    macro_f1 = compute_macro_f1(y_true, y_pred)
    balanced_acc = compute_balanced_accuracy(y_true, y_pred)
    f1_neutral = compute_f1_neutral(y_true, y_pred)
    
    # Additional metrics
    accuracy = accuracy_score(y_true, y_pred)
    macro_precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
    macro_recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
    
    # Per-class metrics
    per_class_f1, per_class_precision, per_class_recall = compute_per_class_metrics(y_true, y_pred)
    
    # Quality gates
    gates_passed, overall_pass = evaluate_quality_gates(macro_f1, balanced_acc, f1_neutral)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    
    return MetricsReport(
        macro_f1=macro_f1,
        balanced_accuracy=balanced_acc,
        f1_neutral=f1_neutral,
        accuracy=accuracy,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        per_class_f1=per_class_f1,
        per_class_precision=per_class_precision,
        per_class_recall=per_class_recall,
        gates_passed=gates_passed,
        overall_pass=overall_pass,
        confusion_matrix=cm.tolist(),
    )


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_report(report: MetricsReport, model_name: str = "Model") -> None:
    """Print formatted metrics report to console."""
    
    print("\n" + "=" * 70)
    print(f"QUALITY GATE METRICS REPORT: {model_name}")
    print("=" * 70)
    
    # Quality Gate Results
    print("\n--- QUALITY GATE EVALUATION ---")
    print(f"{'Metric':<25} {'Value':>10} {'Threshold':>12} {'Status':>10}")
    print("-" * 60)
    
    gate_metrics = [
        ("Macro F1", report.macro_f1, QUALITY_GATES["macro_f1"], report.gates_passed["macro_f1"]),
        ("Balanced Accuracy", report.balanced_accuracy, QUALITY_GATES["balanced_accuracy"], report.gates_passed["balanced_accuracy"]),
        ("F1 (Neutral)", report.f1_neutral, QUALITY_GATES["f1_neutral"], report.gates_passed["f1_neutral"]),
    ]
    
    for name, value, threshold, passed in gate_metrics:
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"{name:<25} {value:>10.4f} {threshold:>12.2f} {status:>10}")
    
    print("-" * 60)
    overall_status = "PASS ✓" if report.overall_pass else "FAIL ✗"
    print(f"{'OVERALL':<25} {'':<10} {'':<12} {overall_status:>10}")
    
    # Additional Metrics
    print("\n--- ADDITIONAL METRICS ---")
    print(f"Accuracy:         {report.accuracy:.4f}")
    print(f"Macro Precision:  {report.macro_precision:.4f}")
    print(f"Macro Recall:     {report.macro_recall:.4f}")
    
    # Per-Class F1 Scores
    print("\n--- PER-CLASS F1 SCORES ---")
    print(f"{'Class':<15} {'F1':>10} {'Precision':>12} {'Recall':>10}")
    print("-" * 50)
    
    for cls in EMOTION_CLASSES:
        f1 = report.per_class_f1[cls]
        prec = report.per_class_precision[cls]
        rec = report.per_class_recall[cls]
        # Highlight neutral class
        marker = " ← Phase 2 baseline" if cls == "neutral" else ""
        print(f"{cls:<15} {f1:>10.4f} {prec:>12.4f} {rec:>10.4f}{marker}")
    
    # Confusion Matrix
    print("\n--- CONFUSION MATRIX ---")
    print("(Rows: True labels, Columns: Predicted labels)")
    print()
    
    # Header
    header = "          " + " ".join(f"{cls[:4]:>6}" for cls in EMOTION_CLASSES)
    print(header)
    
    # Matrix rows
    for i, cls in enumerate(EMOTION_CLASSES):
        row = f"{cls[:8]:<10}" + " ".join(f"{report.confusion_matrix[i][j]:>6}" for j in range(len(EMOTION_CLASSES)))
        print(row)
    
    print("\n" + "=" * 70)


def save_report(report: MetricsReport, output_path: Path, model_name: str = "model") -> None:
    """Save metrics report to JSON file."""
    output_data = {
        "model_name": model_name,
        "quality_gates": {
            "thresholds": QUALITY_GATES,
            "results": {
                "macro_f1": bool(report.gates_passed["macro_f1"]),
                "balanced_accuracy": bool(report.gates_passed["balanced_accuracy"]),
                "f1_neutral": bool(report.gates_passed["f1_neutral"]),
            },
            "overall_pass": bool(report.overall_pass),
        },
        "metrics": report.to_dict(),
        "emotion_classes": EMOTION_CLASSES,
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nReport saved to: {output_path}")


# =============================================================================
# VISUALIZATION (Optional)
# =============================================================================

def plot_confusion_matrix(report: MetricsReport, output_path: Optional[Path] = None) -> None:
    """
    Plot confusion matrix heatmap.
    
    Requires matplotlib and seaborn (optional visualization).
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("Warning: matplotlib/seaborn not available. Skipping visualization.")
        return
    
    cm = np.array(report.confusion_matrix)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=EMOTION_CLASSES,
        yticklabels=EMOTION_CLASSES,
    )
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Confusion matrix saved to: {output_path}")
    else:
        plt.show()


def plot_per_class_f1(report: MetricsReport, output_path: Optional[Path] = None) -> None:
    """
    Plot per-class F1 scores as bar chart with threshold line.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not available. Skipping visualization.")
        return
    
    classes = list(report.per_class_f1.keys())
    f1_values = list(report.per_class_f1.values())
    
    threshold = QUALITY_GATES["f1_neutral"]
    colors = ['#2ecc71' if v >= threshold else '#e74c3c' for v in f1_values]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(classes, f1_values, color=colors, edgecolor='black')
    
    # Threshold line
    plt.axhline(y=threshold, color='red', linestyle='--', label=f'Threshold ({threshold:.2f})')
    
    # Highlight neutral
    neutral_idx = classes.index('neutral')
    bars[neutral_idx].set_edgecolor('blue')
    bars[neutral_idx].set_linewidth(3)
    
    plt.xlabel('Emotion Class')
    plt.ylabel('F1 Score')
    plt.title('Per-Class F1 Scores')
    plt.ylim(0, 1)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Per-class F1 chart saved to: {output_path}")
    else:
        plt.show()


# =============================================================================
# DEMO MODE
# =============================================================================

def generate_demo_data(n_samples: int = 1000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic prediction data for demonstration.
    
    Creates realistic-looking predictions with:
    - ~85% overall accuracy
    - Some class imbalance
    - Typical confusion patterns (e.g., fear/surprise confusion)
    
    Args:
        n_samples: Number of samples to generate
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (y_true, y_pred) arrays
    """
    np.random.seed(seed)
    
    # Generate true labels with mild imbalance, independent of class count.
    n_classes = len(EMOTION_CLASSES)
    if n_classes == 3:
        class_weights = np.array([0.34, 0.32, 0.34], dtype=float)
    else:
        class_weights = np.ones(n_classes, dtype=float)
    class_weights = class_weights / class_weights.sum()
    y_true = np.random.choice(n_classes, size=n_samples, p=class_weights)

    # Slightly higher accuracy for neutral to mirror baseline importance.
    class_accuracies = np.full(n_classes, 0.82, dtype=float)
    class_accuracies[NEUTRAL_INDEX] = 0.87
    
    y_pred = np.zeros_like(y_true)
    for i in range(n_samples):
        true_class = y_true[i]
        if np.random.random() < class_accuracies[true_class]:
            y_pred[i] = true_class
        else:
            # Misclassify uniformly to any other class.
            alternatives = [idx for idx in range(n_classes) if idx != true_class]
            y_pred[i] = int(np.random.choice(alternatives))
    
    return y_true, y_pred


def run_demo() -> None:
    """Run demonstration with synthetic data."""
    print("\n" + "=" * 70)
    print("DEMO MODE: Quality Gate Metrics Evaluation")
    print("=" * 70)
    print("\nGenerating synthetic prediction data...")
    
    y_true, y_pred = generate_demo_data(n_samples=2000)
    
    print(f"Generated {len(y_true)} samples across {len(EMOTION_CLASSES)} emotion classes")
    print("\nClass distribution (true labels):")
    for i, cls in enumerate(EMOTION_CLASSES):
        count = np.sum(y_true == i)
        print(f"  {cls}: {count} ({100*count/len(y_true):.1f}%)")
    
    # Compute metrics
    print("\nComputing metrics...")
    report = compute_all_metrics(y_true, y_pred)
    
    # Print report
    print_report(report, model_name="Demo Model (Synthetic Data)")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    save_report(report, output_dir / "demo_quality_gate_metrics.json", model_name="demo_model")
    
    # Generate visualizations
    try:
        plot_confusion_matrix(report, output_dir / "demo_confusion_matrix.png")
        plot_per_class_f1(report, output_dir / "demo_per_class_f1.png")
    except Exception as e:
        print(f"Visualization skipped: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate emotion classification model against quality gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run demo with synthetic data
    python 01_quality_gate_metrics.py --demo
    
    # Evaluate real predictions
    python 01_quality_gate_metrics.py --predictions results/predictions.npz
    
    # Save visualizations
    python 01_quality_gate_metrics.py --demo --plot
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with synthetic data"
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        help="Path to .npz file containing y_true and y_pred arrays"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for results (default: stats/results/)"
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate visualization plots"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="model",
        help="Name of the model being evaluated"
    )
    parser.add_argument(
        "--emotion-classes",
        type=str,
        default=None,
        help="Comma-separated class names (default: happy,sad,neutral or .npz class_names)",
    )
    parser.add_argument("--macro-f1-threshold", type=float, default=DEFAULT_QUALITY_GATES["macro_f1"])
    parser.add_argument("--balanced-accuracy-threshold", type=float, default=DEFAULT_QUALITY_GATES["balanced_accuracy"])
    parser.add_argument("--f1-neutral-threshold", type=float, default=DEFAULT_QUALITY_GATES["f1_neutral"])
    
    args = parser.parse_args()
    
    cli_classes = None
    if args.emotion_classes:
        cli_classes = [x.strip() for x in args.emotion_classes.split(",") if x.strip()]

    runtime_gates = {
        "macro_f1": args.macro_f1_threshold,
        "balanced_accuracy": args.balanced_accuracy_threshold,
        "f1_neutral": args.f1_neutral_threshold,
    }

    if args.demo:
        _configure_runtime(classes=cli_classes or list(DEFAULT_EMOTION_CLASSES), quality_gates=runtime_gates)
        run_demo()
    elif args.predictions:
        # Load predictions from file
        if not args.predictions.exists():
            print(f"Error: Predictions file not found: {args.predictions}")
            sys.exit(1)
        
        data = np.load(args.predictions, allow_pickle=True)
        y_true = data['y_true']
        y_pred = data['y_pred']
        file_classes = [str(x) for x in data["class_names"].tolist()] if "class_names" in data.files else None
        _configure_runtime(classes=cli_classes or file_classes or list(DEFAULT_EMOTION_CLASSES), quality_gates=runtime_gates)
        
        # Compute metrics
        report = compute_all_metrics(y_true, y_pred)
        
        # Print report
        print_report(report, model_name=args.model_name)
        
        # Save results
        output_dir = args.output or Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        save_report(report, output_dir / f"{args.model_name}_quality_gate_metrics.json", args.model_name)
        
        if args.plot:
            plot_confusion_matrix(report, output_dir / f"{args.model_name}_confusion_matrix.png")
            plot_per_class_f1(report, output_dir / f"{args.model_name}_per_class_f1.png")
        
        # Exit with appropriate code
        sys.exit(0 if report.overall_pass else 1)
    else:
        parser.print_help()
        print("\nError: Must specify --demo or --predictions")
        sys.exit(1)


if __name__ == "__main__":
    main()
