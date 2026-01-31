"""
Univariate Metrics for Gate A Validation

Implements:
    - Confusion Matrix computation
    - Per-class Precision, Recall, F1
    - Macro F1 Score
    - Balanced Accuracy
    - Gate A threshold validation
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GateAThresholds:
    """Gate A quality thresholds for deployment eligibility."""
    macro_f1: float = 0.84
    balanced_accuracy: float = 0.85
    per_class_f1_floor: float = 0.75


@dataclass
class UnivariateResults:
    """Container for univariate metric results."""
    macro_f1: float
    balanced_accuracy: float
    per_class_f1: Dict[str, float]
    per_class_precision: Dict[str, float]
    per_class_recall: Dict[str, float]
    confusion_matrix: np.ndarray
    class_names: List[str]
    gate_a_passed: bool
    gate_a_details: Dict[str, bool]


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
        Entry (i, j) = count of samples with true label i predicted as j
    """
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1
    return cm


def compute_precision_recall(
    confusion_matrix: np.ndarray,
    class_names: List[str]
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Compute per-class precision and recall from confusion matrix.
    
    Precision_c = TP_c / (TP_c + FP_c)
    Recall_c = TP_c / (TP_c + FN_c)
    
    Args:
        confusion_matrix: Confusion matrix (true x predicted)
        class_names: List of class names
        
    Returns:
        Tuple of (precision_dict, recall_dict)
    """
    num_classes = len(class_names)
    precision = {}
    recall = {}
    
    for c in range(num_classes):
        tp = confusion_matrix[c, c]
        fp = confusion_matrix[:, c].sum() - tp  # Column sum minus diagonal
        fn = confusion_matrix[c, :].sum() - tp  # Row sum minus diagonal
        
        precision[class_names[c]] = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall[class_names[c]] = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    
    return precision, recall


def compute_per_class_f1(
    precision: Dict[str, float],
    recall: Dict[str, float]
) -> Dict[str, float]:
    """
    Compute per-class F1 scores.
    
    F1_c = 2 * (Precision_c * Recall_c) / (Precision_c + Recall_c)
    
    Args:
        precision: Per-class precision dict
        recall: Per-class recall dict
        
    Returns:
        Per-class F1 dict
    """
    f1 = {}
    for class_name in precision.keys():
        p = precision[class_name]
        r = recall[class_name]
        f1[class_name] = float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return f1


def compute_macro_f1(per_class_f1: Dict[str, float]) -> float:
    """
    Compute Macro F1 score (unweighted average across classes).
    
    Macro F1 = (1/K) * Σ F1_c
    
    Args:
        per_class_f1: Per-class F1 dict
        
    Returns:
        Macro F1 score
    """
    if not per_class_f1:
        return 0.0
    return float(np.mean(list(per_class_f1.values())))


def compute_balanced_accuracy(recall: Dict[str, float]) -> float:
    """
    Compute Balanced Accuracy (macro-averaged recall).
    
    Balanced Accuracy = (1/K) * Σ Recall_c
    
    Args:
        recall: Per-class recall dict
        
    Returns:
        Balanced accuracy score
    """
    if not recall:
        return 0.0
    return float(np.mean(list(recall.values())))


def validate_gate_a(
    macro_f1: float,
    balanced_accuracy: float,
    per_class_f1: Dict[str, float],
    thresholds: Optional[GateAThresholds] = None
) -> Tuple[bool, Dict[str, bool]]:
    """
    Validate whether metrics meet Gate A thresholds.
    
    Args:
        macro_f1: Computed macro F1
        balanced_accuracy: Computed balanced accuracy
        per_class_f1: Per-class F1 scores
        thresholds: Gate A thresholds (uses defaults if None)
        
    Returns:
        Tuple of (overall_pass, details_dict)
    """
    if thresholds is None:
        thresholds = GateAThresholds()
    
    details = {
        'macro_f1': macro_f1 >= thresholds.macro_f1,
        'balanced_accuracy': balanced_accuracy >= thresholds.balanced_accuracy,
    }
    
    # Check per-class F1 floors
    for class_name, f1 in per_class_f1.items():
        details[f'f1_{class_name}'] = f1 >= thresholds.per_class_f1_floor
    
    overall_pass = all(details.values())
    
    return overall_pass, details


def compute_all_univariate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    thresholds: Optional[GateAThresholds] = None
) -> UnivariateResults:
    """
    Compute all univariate metrics and validate Gate A.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: List of class names
        thresholds: Gate A thresholds
        
    Returns:
        UnivariateResults dataclass with all metrics
    """
    num_classes = len(class_names)
    
    # Compute confusion matrix
    cm = compute_confusion_matrix(y_true, y_pred, num_classes)
    
    # Compute precision and recall
    precision, recall = compute_precision_recall(cm, class_names)
    
    # Compute F1 scores
    per_class_f1 = compute_per_class_f1(precision, recall)
    macro_f1 = compute_macro_f1(per_class_f1)
    
    # Compute balanced accuracy
    balanced_acc = compute_balanced_accuracy(recall)
    
    # Validate Gate A
    gate_a_passed, gate_a_details = validate_gate_a(
        macro_f1, balanced_acc, per_class_f1, thresholds
    )
    
    return UnivariateResults(
        macro_f1=macro_f1,
        balanced_accuracy=balanced_acc,
        per_class_f1=per_class_f1,
        per_class_precision=precision,
        per_class_recall=recall,
        confusion_matrix=cm,
        class_names=class_names,
        gate_a_passed=gate_a_passed,
        gate_a_details=gate_a_details,
    )


def print_univariate_report(results: UnivariateResults) -> str:
    """
    Generate a formatted report of univariate metrics.
    
    Args:
        results: UnivariateResults object
        
    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "UNIVARIATE METRICS REPORT (Gate A Validation)",
        "=" * 60,
        "",
        f"Macro F1:          {results.macro_f1:.4f}  (threshold: >= 0.84)",
        f"Balanced Accuracy: {results.balanced_accuracy:.4f}  (threshold: >= 0.85)",
        "",
        "Per-Class Metrics:",
        "-" * 40,
    ]
    
    for class_name in results.class_names:
        p = results.per_class_precision[class_name]
        r = results.per_class_recall[class_name]
        f1 = results.per_class_f1[class_name]
        lines.append(f"  {class_name:10s}  P={p:.3f}  R={r:.3f}  F1={f1:.3f}")
    
    lines.extend([
        "",
        "Gate A Status:",
        "-" * 40,
    ])
    
    for metric, passed in results.gate_a_details.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        lines.append(f"  {metric:20s}  {status}")
    
    overall = "✓ PASSED" if results.gate_a_passed else "✗ FAILED"
    lines.extend([
        "",
        f"Overall Gate A: {overall}",
        "=" * 60,
    ])
    
    return "\n".join(lines)
