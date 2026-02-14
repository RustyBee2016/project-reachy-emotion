"""
Univariate Statistical Metrics for Emotion Classification
==========================================================

Implements per-model metrics for Phase 1 evaluation:
    - Confusion Matrix computation
    - Precision, Recall, F1 (per-class and macro)
    - Balanced Accuracy
    - Gate A validation against thresholds

Reference: Phase_1_Statistical_Analysis.md Section 2
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


# =============================================================================
# Input Validation Helpers
# =============================================================================

def _validate_arrays(y_true: np.ndarray, y_pred: np.ndarray, name: str = "input") -> None:
    """
    Validate that prediction arrays are valid for metric computation.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        name: Name for error messages
        
    Raises:
        ValueError: If arrays are invalid
    """
    if y_true is None or y_pred is None:
        raise ValueError(f"{name}: Arrays cannot be None")
    
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    
    if len(y_true) == 0 or len(y_pred) == 0:
        raise ValueError(f"{name}: Arrays cannot be empty")
    
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"{name}: Array lengths must match. "
            f"Got y_true={len(y_true)}, y_pred={len(y_pred)}"
        )


def _validate_num_classes(num_classes: int) -> None:
    """Validate number of classes parameter."""
    if num_classes < 2:
        raise ValueError(f"num_classes must be >= 2, got {num_classes}")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class UnivariateResults:
    """Container for univariate metric results."""
    confusion_matrix: np.ndarray
    precision: Dict[int, float]
    recall: Dict[int, float]
    f1: Dict[int, float]
    macro_f1: float
    balanced_accuracy: float
    support: Dict[int, int]
    class_names: List[str]


@dataclass
class GateAResult:
    """Result of Gate A validation check."""
    passed: bool
    macro_f1: float
    balanced_accuracy: float
    f1_per_class: Dict[int, float]
    macro_f1_threshold: float
    balanced_acc_threshold: float
    f1_floor_threshold: float
    failures: List[str]


# =============================================================================
# Core Metric Functions
# =============================================================================

def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int
) -> np.ndarray:
    """
    Compute confusion matrix from predictions.
    
    Args:
        y_true: Ground truth labels (0-indexed)
        y_pred: Predicted labels (0-indexed)
        num_classes: Number of classes
        
    Returns:
        Confusion matrix of shape (num_classes, num_classes)
        where cm[i,j] = count of samples with true label i predicted as j
    """
    _validate_arrays(y_true, y_pred, "compute_confusion_matrix")
    _validate_num_classes(num_classes)
    
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm


def compute_precision(cm: np.ndarray, class_idx: int) -> float:
    """
    Compute precision for a specific class.
    
    Precision = TP / (TP + FP)
    
    Args:
        cm: Confusion matrix
        class_idx: Index of the class
        
    Returns:
        Precision score (0.0 if no predictions for this class)
    """
    tp = cm[class_idx, class_idx]
    fp = cm[:, class_idx].sum() - tp
    denominator = tp + fp
    return float(tp / denominator) if denominator > 0 else 0.0


def compute_recall(cm: np.ndarray, class_idx: int) -> float:
    """
    Compute recall for a specific class.
    
    Recall = TP / (TP + FN)
    
    Args:
        cm: Confusion matrix
        class_idx: Index of the class
        
    Returns:
        Recall score (0.0 if no samples of this class)
    """
    tp = cm[class_idx, class_idx]
    fn = cm[class_idx, :].sum() - tp
    denominator = tp + fn
    return float(tp / denominator) if denominator > 0 else 0.0


def compute_f1(precision: float, recall: float) -> float:
    """
    Compute F1 score from precision and recall.
    
    F1 = 2 * (precision * recall) / (precision + recall)
    
    Args:
        precision: Precision score
        recall: Recall score
        
    Returns:
        F1 score (0.0 if both precision and recall are 0)
    """
    denominator = precision + recall
    return float(2 * precision * recall / denominator) if denominator > 0 else 0.0


def compute_per_class_metrics(
    cm: np.ndarray,
    class_names: Optional[List[str]] = None
) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float], Dict[int, int]]:
    """
    Compute precision, recall, F1, and support for all classes.
    
    Args:
        cm: Confusion matrix
        class_names: Optional list of class names (unused, for API consistency)
        
    Returns:
        Tuple of (precision_dict, recall_dict, f1_dict, support_dict)
    """
    if cm is None or cm.size == 0:
        raise ValueError("Confusion matrix cannot be None or empty")
    
    num_classes = cm.shape[0]
    precision = {}
    recall = {}
    f1 = {}
    support = {}
    
    for i in range(num_classes):
        precision[i] = compute_precision(cm, i)
        recall[i] = compute_recall(cm, i)
        f1[i] = compute_f1(precision[i], recall[i])
        support[i] = int(cm[i, :].sum())
    
    return precision, recall, f1, support


def compute_macro_f1(f1_scores: Dict[int, float]) -> float:
    """
    Compute macro-averaged F1 score.
    
    Args:
        f1_scores: Dictionary mapping class index to F1 score
        
    Returns:
        Macro F1 (unweighted mean of per-class F1 scores)
    """
    if not f1_scores:
        raise ValueError("f1_scores cannot be empty")
    return float(np.mean(list(f1_scores.values())))


def compute_balanced_accuracy(cm: np.ndarray) -> float:
    """
    Compute balanced accuracy (mean of per-class recall).
    
    Balanced Accuracy = (1/K) * sum(Recall_k)
    
    This metric is robust to class imbalance.
    
    Args:
        cm: Confusion matrix
        
    Returns:
        Balanced accuracy score
    """
    if cm is None or cm.size == 0:
        raise ValueError("Confusion matrix cannot be None or empty")
    
    num_classes = cm.shape[0]
    recalls = [compute_recall(cm, i) for i in range(num_classes)]
    return float(np.mean(recalls))


# =============================================================================
# Gate A Validation
# =============================================================================

def validate_gate_a(
    results: UnivariateResults,
    macro_f1_threshold: float = 0.84,
    balanced_acc_threshold: float = 0.85,
    f1_floor_threshold: float = 0.75
) -> GateAResult:
    """
    Validate model against Gate A thresholds.
    
    Gate A Requirements (from requirements_08.4.2.md):
        - Macro F1 >= 0.84
        - Balanced Accuracy >= 0.85
        - Per-class F1 >= 0.75 (floor for all classes)
    
    Args:
        results: UnivariateResults from model evaluation
        macro_f1_threshold: Minimum macro F1 score
        balanced_acc_threshold: Minimum balanced accuracy
        f1_floor_threshold: Minimum F1 for any class
        
    Returns:
        GateAResult with pass/fail status and details
    """
    failures = []
    
    if results.macro_f1 < macro_f1_threshold:
        failures.append(
            f"Macro F1 {results.macro_f1:.4f} < {macro_f1_threshold}"
        )
    
    if results.balanced_accuracy < balanced_acc_threshold:
        failures.append(
            f"Balanced Accuracy {results.balanced_accuracy:.4f} < {balanced_acc_threshold}"
        )
    
    for class_idx, f1_score in results.f1.items():
        if f1_score < f1_floor_threshold:
            class_name = results.class_names[class_idx] if class_idx < len(results.class_names) else f"Class {class_idx}"
            failures.append(
                f"{class_name} F1 {f1_score:.4f} < {f1_floor_threshold}"
            )
    
    return GateAResult(
        passed=len(failures) == 0,
        macro_f1=results.macro_f1,
        balanced_accuracy=results.balanced_accuracy,
        f1_per_class=results.f1,
        macro_f1_threshold=macro_f1_threshold,
        balanced_acc_threshold=balanced_acc_threshold,
        f1_floor_threshold=f1_floor_threshold,
        failures=failures
    )


# =============================================================================
# Full Computation Pipeline
# =============================================================================

def compute_all_univariate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int,
    class_names: Optional[List[str]] = None
) -> UnivariateResults:
    """
    Compute all univariate metrics for a model's predictions.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        num_classes: Number of classes
        class_names: Optional list of class names
        
    Returns:
        UnivariateResults containing all computed metrics
    """
    _validate_arrays(y_true, y_pred, "compute_all_univariate_metrics")
    _validate_num_classes(num_classes)
    
    if class_names is None:
        class_names = [f"Class {i}" for i in range(num_classes)]
    
    cm = compute_confusion_matrix(y_true, y_pred, num_classes)
    precision, recall, f1, support = compute_per_class_metrics(cm)
    macro_f1 = compute_macro_f1(f1)
    balanced_acc = compute_balanced_accuracy(cm)
    
    return UnivariateResults(
        confusion_matrix=cm,
        precision=precision,
        recall=recall,
        f1=f1,
        macro_f1=macro_f1,
        balanced_accuracy=balanced_acc,
        support=support,
        class_names=class_names
    )


# =============================================================================
# Reporting
# =============================================================================

def print_univariate_report(
    results: UnivariateResults,
    model_name: str = "Model",
    gate_a_result: Optional[GateAResult] = None
) -> None:
    """
    Print a formatted report of univariate metrics.
    
    Args:
        results: UnivariateResults to report
        model_name: Name of the model for display
        gate_a_result: Optional Gate A validation result
    """
    print(f"\n{'='*60}")
    print(f"UNIVARIATE METRICS: {model_name}")
    print(f"{'='*60}")
    
    print(f"\nConfusion Matrix:")
    print(results.confusion_matrix)
    
    print(f"\nPer-Class Metrics:")
    print(f"{'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("-" * 55)
    
    for i, name in enumerate(results.class_names):
        print(f"{name:<15} {results.precision[i]:>10.4f} {results.recall[i]:>10.4f} "
              f"{results.f1[i]:>10.4f} {results.support[i]:>10}")
    
    print("-" * 55)
    print(f"\nMacro F1:          {results.macro_f1:.4f}")
    print(f"Balanced Accuracy: {results.balanced_accuracy:.4f}")
    
    if gate_a_result:
        print(f"\n{'='*60}")
        print(f"GATE A VALIDATION: {'PASSED ✓' if gate_a_result.passed else 'FAILED ✗'}")
        print(f"{'='*60}")
        print(f"Thresholds:")
        print(f"  - Macro F1 >= {gate_a_result.macro_f1_threshold}")
        print(f"  - Balanced Accuracy >= {gate_a_result.balanced_acc_threshold}")
        print(f"  - Per-class F1 floor >= {gate_a_result.f1_floor_threshold}")
        
        if gate_a_result.failures:
            print(f"\nFailures:")
            for failure in gate_a_result.failures:
                print(f"  ✗ {failure}")
