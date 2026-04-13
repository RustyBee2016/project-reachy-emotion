"""
Evaluation module for emotion classifier.

Computes:
- Classification metrics (accuracy, precision, recall, F1)
- Per-class metrics
- Calibration metrics (ECE, Brier score)
- Confusion matrix
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import sklearn, provide fallbacks
try:
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        balanced_accuracy_score,
        confusion_matrix,
        classification_report,
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn not available, using basic metric implementations")


def compute_metrics(
    y_true: List[int],
    y_pred: List[int],
    class_names: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    Compute classification metrics.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Optional class names for reporting
    
    Returns:
        Dictionary of metrics
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    metrics = {}
    
    if SKLEARN_AVAILABLE:
        metrics['accuracy'] = accuracy_score(y_true, y_pred)
        metrics['precision_macro'] = precision_score(y_true, y_pred, average='macro', zero_division=0)
        metrics['recall_macro'] = recall_score(y_true, y_pred, average='macro', zero_division=0)
        metrics['f1_macro'] = f1_score(y_true, y_pred, average='macro', zero_division=0)
        metrics['balanced_accuracy'] = balanced_accuracy_score(y_true, y_pred)
        
        # Per-class F1
        f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
        for i, f1 in enumerate(f1_per_class):
            metrics[f'f1_class_{i}'] = f1
            if class_names and i < len(class_names):
                metrics[f'f1_{class_names[i]}'] = f1
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
    else:
        # Basic implementations
        metrics['accuracy'] = np.mean(y_true == y_pred)
        
        # Per-class metrics
        unique_classes = np.unique(np.concatenate([y_true, y_pred]))
        f1_scores = []
        
        for cls in unique_classes:
            tp = np.sum((y_true == cls) & (y_pred == cls))
            fp = np.sum((y_true != cls) & (y_pred == cls))
            fn = np.sum((y_true == cls) & (y_pred != cls))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            f1_scores.append(f1)
            metrics[f'f1_class_{cls}'] = f1
        
        metrics['f1_macro'] = np.mean(f1_scores) if f1_scores else 0
        metrics['balanced_accuracy'] = metrics['accuracy']  # Simplified
    
    return metrics


def compute_calibration_metrics(
    y_true: List[int],
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, float]:
    """
    Compute calibration metrics.
    
    Args:
        y_true: Ground truth labels
        y_prob: Predicted probabilities [N, C]
        n_bins: Number of bins for ECE
    
    Returns:
        Dictionary with ECE and Brier score
    """
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    
    metrics = {}
    
    # Expected Calibration Error (ECE)
    metrics['ece'] = expected_calibration_error(y_true, y_prob, n_bins)
    
    # Brier score
    metrics['brier'] = brier_score(y_true, y_prob)
    
    # Maximum Calibration Error (MCE)
    metrics['mce'] = maximum_calibration_error(y_true, y_prob, n_bins)
    
    return metrics


def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    ECE measures how well predicted probabilities match actual accuracy.
    Lower is better. Gate A requires ECE ≤ 0.12.
    
    Args:
        y_true: Ground truth labels [N]
        y_prob: Predicted probabilities [N, C]
        n_bins: Number of calibration bins
    
    Returns:
        ECE value in [0, 1]
    """
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            ece += np.abs(avg_accuracy - avg_confidence) * prop_in_bin
    
    return float(ece)


def maximum_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Maximum Calibration Error (MCE).
    
    MCE is the maximum gap between confidence and accuracy across bins.
    
    Args:
        y_true: Ground truth labels
        y_prob: Predicted probabilities
        n_bins: Number of calibration bins
    
    Returns:
        MCE value
    """
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    max_gap = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        
        if in_bin.sum() > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            gap = np.abs(avg_accuracy - avg_confidence)
            max_gap = max(max_gap, gap)
    
    return float(max_gap)


def brier_score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> float:
    """
    Compute Brier score (mean squared error of probabilities).
    
    Lower is better. Gate A requires Brier ≤ 0.16.
    
    Args:
        y_true: Ground truth labels [N]
        y_prob: Predicted probabilities [N, C]
    
    Returns:
        Brier score
    """
    n_classes = y_prob.shape[1]
    
    # One-hot encode true labels
    y_true_onehot = np.eye(n_classes)[y_true]
    
    # Mean squared error
    brier = np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))
    
    return float(brier)


def compute_confusion_matrix(
    y_true: List[int],
    y_pred: List[int],
    class_names: Optional[List[str]] = None,
) -> Dict[str, any]:
    """
    Compute and format confusion matrix.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Class names for labeling
    
    Returns:
        Dictionary with confusion matrix and derived metrics
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    if SKLEARN_AVAILABLE:
        cm = confusion_matrix(y_true, y_pred)
    else:
        # Basic implementation
        n_classes = max(max(y_true), max(y_pred)) + 1
        cm = np.zeros((n_classes, n_classes), dtype=int)
        for t, p in zip(y_true, y_pred):
            cm[t, p] += 1
    
    result = {
        'matrix': cm.tolist(),
        'class_names': class_names or [str(i) for i in range(cm.shape[0])],
    }
    
    # Per-class metrics from confusion matrix
    for i in range(cm.shape[0]):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        tn = cm.sum() - tp - fp - fn
        
        result[f'class_{i}_tp'] = int(tp)
        result[f'class_{i}_fp'] = int(fp)
        result[f'class_{i}_fn'] = int(fn)
        result[f'class_{i}_tn'] = int(tn)
    
    return result


def evaluate_model(
    model,
    dataloader,
    device: str = 'cuda',
    class_names: Optional[List[str]] = None,
) -> Dict[str, any]:
    """
    Evaluate a model on a dataset.
    
    Args:
        model: PyTorch model
        dataloader: DataLoader for evaluation
        device: Device to run on
        class_names: Class names
    
    Returns:
        Complete evaluation results
    """
    import torch
    
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            
            outputs = model(images)
            if isinstance(outputs, dict):
                logits = outputs['logits']
            else:
                logits = outputs
            
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
    
    # Compute all metrics
    results = compute_metrics(all_labels, all_preds, class_names)
    results.update(compute_calibration_metrics(all_labels, np.array(all_probs)))
    results['confusion'] = compute_confusion_matrix(all_labels, all_preds, class_names)
    
    return results


def generate_report(
    results: Dict[str, any],
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a human-readable evaluation report.
    
    Args:
        results: Evaluation results dictionary
        output_path: Optional path to save report
    
    Returns:
        Report string
    """
    lines = [
        "=" * 60,
        "EMOTION CLASSIFIER EVALUATION REPORT",
        "=" * 60,
        "",
        "CLASSIFICATION METRICS",
        "-" * 40,
        f"Accuracy:          {results.get('accuracy', 0):.4f}",
        f"Balanced Accuracy: {results.get('balanced_accuracy', 0):.4f}",
        f"F1 Macro:          {results.get('f1_macro', 0):.4f}",
        f"Precision Macro:   {results.get('precision_macro', 0):.4f}",
        f"Recall Macro:      {results.get('recall_macro', 0):.4f}",
        "",
        "PER-CLASS F1 SCORES",
        "-" * 40,
    ]
    
    # Add per-class F1
    for key, value in results.items():
        if key.startswith('f1_class_') or key.startswith('f1_happy') or key.startswith('f1_sad'):
            lines.append(f"  {key}: {value:.4f}")
    
    lines.extend([
        "",
        "CALIBRATION METRICS",
        "-" * 40,
        f"ECE:   {results.get('ece', 0):.4f} (target: ≤0.12)",
        f"MCE:   {results.get('mce', 0):.4f}",
        f"Brier: {results.get('brier', 0):.4f} (target: ≤0.16)",
        "",
        "QUALITY GATE STATUS",
        "-" * 40,
    ])
    
    # Gate A check
    gate_a_passed = (
        results.get('f1_macro', 0) >= 0.84 and
        results.get('balanced_accuracy', 0) >= 0.85 and
        results.get('ece', 1) <= 0.12 and
        results.get('brier', 1) <= 0.16
    )
    
    lines.append(f"Gate A: {'PASSED ✓' if gate_a_passed else 'FAILED ✗'}")
    lines.append("")
    lines.append("=" * 60)
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {output_path}")
    
    return report
