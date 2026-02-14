# Tutorial 1: Quality Gate Metrics Analysis with Python

## Learning Objectives

By the end of this tutorial, you will understand:
- How to use scikit-learn for classification metrics computation
- The structure and benefits of Python dataclasses for data organization
- Type hints and modern Python practices for robust code
- Command-line argument parsing with argparse
- JSON output formatting and file handling with pathlib

## Statistical Background

### What are Quality Gates?

Quality gates are **pass/fail thresholds** that determine if an emotion classification model is ready for deployment. They serve as a **quality control checkpoint** before releasing a model to production.

For the Reachy emotion project, we have three critical metrics:

1. **Macro F1 ≥ 0.84**: Overall classification quality across all emotions
2. **Balanced Accuracy ≥ 0.82**: Protection against class imbalance bias  
3. **F1 Neutral ≥ 0.80**: Critical for Phase 2 baseline (neutral serves as reference point)

### Why These Specific Thresholds?

```python
QUALITY_GATES = {
    'macro_f1': 0.84,           # High enough for reliable emotion detection
    'balanced_accuracy': 0.82,  # Ensures all emotions are detected fairly
    'f1_neutral': 0.80          # Neutral class is baseline for intensity modeling
}
```

**Real-world impact**: If F1 Neutral drops below 0.80, the robot might misinterpret neutral expressions as emotional, leading to inappropriate responses.

## Script Structure and Imports

```python
#!/usr/bin/env python3
"""
Quality Gate Metrics Analysis for Emotion Classification

This script evaluates emotion classification models against predefined quality gates
using scikit-learn metrics and provides comprehensive reporting.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, classification_report, 
    f1_score, balanced_accuracy_score,
    precision_recall_fscore_support
)
```

**Key Patterns**:
- **Docstring**: Clear module description following Google style
- **Type imports**: Modern typing for better code documentation
- **Pathlib**: Modern file handling instead of os.path
- **Dataclasses**: Structured data containers

## Core Data Structures

### Emotion Classes Definition

```python
EMOTION_CLASSES = [
    'anger', 'contempt', 'disgust', 'fear',
    'happiness', 'neutral', 'sadness', 'surprise'
]

NEUTRAL_CLASS = 'neutral'
NEUTRAL_INDEX = EMOTION_CLASSES.index(NEUTRAL_CLASS)  # 5
```

**Why this order?** It matches the HSEmotion model output indices. The order matters for confusion matrix calculations and consistent indexing.

### Dataclass for Results

```python
@dataclass
class MetricsReport:
    """Comprehensive metrics report for emotion classification."""
    
    # Core metrics
    macro_f1: float
    balanced_accuracy: float
    f1_neutral: float
    accuracy: float
    
    # Per-class metrics
    per_class_precision: Dict[str, float]
    per_class_recall: Dict[str, float]
    per_class_f1: Dict[str, float]
    per_class_support: Dict[str, int]
    
    # Additional information
    confusion_matrix: List[List[int]]
    n_samples: int
    class_distribution: Dict[str, int]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
```

**Benefits of Dataclasses**:
- **Type safety**: Clear field types
- **Automatic methods**: `__init__`, `__repr__`, `__eq__` generated automatically
- **JSON serialization**: Easy conversion to dictionary
- **IDE support**: Better autocomplete and error detection

## Core Metrics Computation

### Using Scikit-Learn for Robust Metrics

```python
def compute_classification_metrics(y_true: List[str], y_pred: List[str]) -> MetricsReport:
    """
    Compute comprehensive classification metrics using scikit-learn.
    
    Args:
        y_true: Ground truth emotion labels
        y_pred: Predicted emotion labels
        
    Returns:
        MetricsReport containing all computed metrics
        
    Raises:
        ValueError: If input arrays have different lengths or contain invalid labels
    """
    # Input validation
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")
    
    if len(y_true) == 0:
        raise ValueError("Empty input arrays")
    
    # Validate emotion labels
    valid_labels = set(EMOTION_CLASSES)
    invalid_true = set(y_true) - valid_labels
    invalid_pred = set(y_pred) - valid_labels
    
    if invalid_true:
        raise ValueError(f"Invalid true labels: {invalid_true}")
    if invalid_pred:
        raise ValueError(f"Invalid predicted labels: {invalid_pred}")
    
    # Convert to numpy arrays for sklearn
    y_true_array = np.array(y_true)
    y_pred_array = np.array(y_pred)
    
    # Compute core metrics using sklearn
    macro_f1 = f1_score(y_true_array, y_pred_array, 
                       labels=EMOTION_CLASSES, average='macro')
    balanced_acc = balanced_accuracy_score(y_true_array, y_pred_array)
    accuracy = (y_true_array == y_pred_array).mean()
    
    # Per-class metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true_array, y_pred_array, 
        labels=EMOTION_CLASSES, average=None
    )
    
    # Create per-class dictionaries
    per_class_precision = dict(zip(EMOTION_CLASSES, precision))
    per_class_recall = dict(zip(EMOTION_CLASSES, recall))
    per_class_f1 = dict(zip(EMOTION_CLASSES, f1))
    per_class_support = dict(zip(EMOTION_CLASSES, support.astype(int)))
    
    # F1 for neutral class specifically
    f1_neutral = per_class_f1[NEUTRAL_CLASS]
    
    # Confusion matrix
    cm = confusion_matrix(y_true_array, y_pred_array, labels=EMOTION_CLASSES)
    
    # Class distribution
    unique, counts = np.unique(y_true_array, return_counts=True)
    class_distribution = dict(zip(unique, counts.astype(int)))
    
    return MetricsReport(
        macro_f1=macro_f1,
        balanced_accuracy=balanced_acc,
        f1_neutral=f1_neutral,
        accuracy=accuracy,
        per_class_precision=per_class_precision,
        per_class_recall=per_class_recall,
        per_class_f1=per_class_f1,
        per_class_support=per_class_support,
        confusion_matrix=cm.tolist(),  # Convert numpy array to list for JSON
        n_samples=len(y_true),
        class_distribution=class_distribution
    )
```

### Understanding Scikit-Learn Metrics

**Key Functions**:
- `f1_score(..., average='macro')`: Unweighted mean of F1 scores
- `balanced_accuracy_score()`: Macro-averaged recall (handles class imbalance)
- `precision_recall_fscore_support()`: All per-class metrics in one call
- `confusion_matrix()`: Cross-tabulation of predictions vs truth

**Why sklearn over manual calculation?**
- **Tested and optimized**: Handles edge cases automatically
- **Consistent API**: Same interface across all metrics
- **Performance**: Optimized C implementations
- **Documentation**: Extensive examples and explanations

## Quality Gate Evaluation

### Enhanced Gate Logic

```python
@dataclass
class QualityGateResult:
    """Result of quality gate evaluation."""
    metric_name: str
    value: float
    threshold: float
    passed: bool
    margin: float
    
    @property
    def risk_level(self) -> str:
        """Assess risk level based on margin."""
        if self.margin > 0.05:
            return "LOW"
        elif self.margin > 0:
            return "MEDIUM"
        else:
            return "HIGH"

def evaluate_quality_gates(metrics: MetricsReport) -> Dict[str, QualityGateResult]:
    """
    Evaluate metrics against quality gate thresholds.
    
    Args:
        metrics: Computed classification metrics
        
    Returns:
        Dictionary mapping gate names to evaluation results
    """
    gates = {}
    
    # Macro F1 gate
    gates['macro_f1'] = QualityGateResult(
        metric_name='Macro F1',
        value=metrics.macro_f1,
        threshold=QUALITY_GATES['macro_f1'],
        passed=metrics.macro_f1 >= QUALITY_GATES['macro_f1'],
        margin=metrics.macro_f1 - QUALITY_GATES['macro_f1']
    )
    
    # Balanced accuracy gate
    gates['balanced_accuracy'] = QualityGateResult(
        metric_name='Balanced Accuracy',
        value=metrics.balanced_accuracy,
        threshold=QUALITY_GATES['balanced_accuracy'],
        passed=metrics.balanced_accuracy >= QUALITY_GATES['balanced_accuracy'],
        margin=metrics.balanced_accuracy - QUALITY_GATES['balanced_accuracy']
    )
    
    # F1 neutral gate
    gates['f1_neutral'] = QualityGateResult(
        metric_name='F1 Neutral',
        value=metrics.f1_neutral,
        threshold=QUALITY_GATES['f1_neutral'],
        passed=metrics.f1_neutral >= QUALITY_GATES['f1_neutral'],
        margin=metrics.f1_neutral - QUALITY_GATES['f1_neutral']
    )
    
    return gates
```

## Enhanced Reporting

### Comprehensive Console Output

```python
def print_quality_gate_report(metrics: MetricsReport, gates: Dict[str, QualityGateResult], 
                             model_name: str = "model") -> None:
    """Print comprehensive quality gate report to console."""
    
    print("=" * 80)
    print(f"QUALITY GATE ANALYSIS - {model_name.upper()}")
    print("=" * 80)
    
    # Overall status
    overall_pass = all(gate.passed for gate in gates.values())
    status_symbol = "✅ PASS" if overall_pass else "❌ FAIL"
    print(f"\nOverall Status: {status_symbol}")
    
    # Individual gate results
    print(f"\n{'Metric':<25} {'Value':<10} {'Threshold':<10} {'Status':<10} {'Margin':<10} {'Risk':<10}")
    print("-" * 80)
    
    for gate in gates.values():
        status_symbol = "PASS ✓" if gate.passed else "FAIL ✗"
        print(f"{gate.metric_name:<25} {gate.value:<10.4f} {gate.threshold:<10.4f} "
              f"{status_symbol:<10} {gate.margin:+10.4f} {gate.risk_level:<10}")
    
    # Per-class performance summary
    print(f"\n--- PER-CLASS PERFORMANCE ---")
    print(f"{'Class':<12} {'Precision':<10} {'Recall':<10} {'F1':<10} {'Support':<10}")
    print("-" * 60)
    
    for cls in EMOTION_CLASSES:
        precision = metrics.per_class_precision[cls]
        recall = metrics.per_class_recall[cls]
        f1 = metrics.per_class_f1[cls]
        support = metrics.per_class_support[cls]
        
        # Highlight neutral class
        marker = " ★" if cls == NEUTRAL_CLASS else ""
        print(f"{cls:<12} {precision:<10.3f} {recall:<10.3f} {f1:<10.3f} {support:<10}{marker}")
    
    # Class distribution analysis
    print(f"\n--- CLASS DISTRIBUTION ---")
    total_samples = sum(metrics.class_distribution.values())
    print(f"Total Samples: {total_samples}")
    
    for cls in EMOTION_CLASSES:
        count = metrics.class_distribution.get(cls, 0)
        percentage = (count / total_samples) * 100 if total_samples > 0 else 0
        print(f"{cls:<12}: {count:>6} ({percentage:>5.1f}%)")
```

## Visualization Creation

### Confusion Matrix Heatmap

```python
def create_confusion_matrix_plot(metrics: MetricsReport, output_path: Optional[Path] = None) -> None:
    """Create and save confusion matrix heatmap."""
    
    # Convert confusion matrix back to numpy array
    cm = np.array(metrics.confusion_matrix)
    
    # Create figure
    plt.figure(figsize=(10, 8))
    
    # Create heatmap with annotations
    sns.heatmap(cm, 
                annot=True, 
                fmt='d',
                cmap='Blues',
                xticklabels=EMOTION_CLASSES,
                yticklabels=EMOTION_CLASSES,
                cbar_kws={'label': 'Count'})
    
    plt.title('Confusion Matrix - Emotion Classification')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Confusion matrix saved: {output_path}")
    else:
        plt.show()
    
    plt.close()

def create_per_class_performance_plot(metrics: MetricsReport, 
                                    output_path: Optional[Path] = None) -> None:
    """Create per-class performance bar chart."""
    
    # Prepare data for plotting
    classes = EMOTION_CLASSES
    precision = [metrics.per_class_precision[cls] for cls in classes]
    recall = [metrics.per_class_recall[cls] for cls in classes]
    f1 = [metrics.per_class_f1[cls] for cls in classes]
    
    # Create subplot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(classes))
    width = 0.25
    
    # Create bars
    bars1 = ax.bar(x - width, precision, width, label='Precision', alpha=0.8)
    bars2 = ax.bar(x, recall, width, label='Recall', alpha=0.8)
    bars3 = ax.bar(x + width, f1, width, label='F1-Score', alpha=0.8)
    
    # Customize plot
    ax.set_xlabel('Emotion Class')
    ax.set_ylabel('Score')
    ax.set_title('Per-Class Performance Metrics')
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.0)
    
    # Highlight neutral class
    neutral_idx = EMOTION_CLASSES.index(NEUTRAL_CLASS)
    ax.axvline(x=neutral_idx, color='red', linestyle='--', alpha=0.5, label='Neutral Class')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Performance plot saved: {output_path}")
    else:
        plt.show()
    
    plt.close()
```

## Demo Data Generation

### Realistic Synthetic Data

```python
def generate_demo_data(n_samples: int = 2000, 
                      class_imbalance: float = 0.3,
                      noise_level: float = 0.1,
                      seed: int = 42) -> Tuple[List[str], List[str]]:
    """
    Generate realistic demo data for emotion classification.
    
    Args:
        n_samples: Number of samples to generate
        class_imbalance: Level of class imbalance (0 = balanced, 1 = highly imbalanced)
        noise_level: Amount of prediction noise (0 = perfect, 1 = random)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (y_true, y_pred) lists
    """
    np.random.seed(seed)
    
    print(f"Generating demo data: n={n_samples}, imbalance={class_imbalance}, noise={noise_level}")
    
    # Generate class weights based on imbalance level
    if class_imbalance == 0:
        weights = np.ones(len(EMOTION_CLASSES))
    else:
        # Exponential decay for realistic imbalance
        weights = np.exp(-class_imbalance * np.arange(len(EMOTION_CLASSES)))
    
    weights = weights / weights.sum()
    
    # Generate true labels
    y_true = np.random.choice(EMOTION_CLASSES, size=n_samples, p=weights)
    
    # Realistic per-class accuracies
    base_accuracies = {
        'anger': 0.82, 'contempt': 0.65, 'disgust': 0.72, 'fear': 0.78,
        'happiness': 0.90, 'neutral': 0.88, 'sadness': 0.84, 'surprise': 0.80
    }
    
    # Common confusion patterns
    confusion_patterns = {
        'anger': ['fear', 'disgust'],
        'contempt': ['disgust', 'anger'], 
        'disgust': ['contempt', 'anger'],
        'fear': ['surprise', 'anger'],
        'happiness': ['surprise', 'neutral'],
        'neutral': ['sadness', 'happiness'],
        'sadness': ['neutral', 'fear'],
        'surprise': ['fear', 'happiness']
    }
    
    # Generate predictions with realistic errors
    y_pred = []
    for true_label in y_true:
        accuracy = base_accuracies[true_label] * (1 - noise_level)
        
        if np.random.random() < accuracy:
            y_pred.append(true_label)  # Correct prediction
        else:
            # Realistic confusion
            confused_options = confusion_patterns[true_label]
            y_pred.append(np.random.choice(confused_options))
    
    return y_true.tolist(), y_pred
```

## Command Line Interface

### Argument Parsing with argparse

```python
def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description='Evaluate emotion classification model against quality gates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo with default settings
  python 01_quality_gate_metrics.py --demo
  
  # Demo with class imbalance and noise
  python 01_quality_gate_metrics.py --demo --demo-imbalance 0.5 --demo-noise 0.2 --plot
  
  # Real data analysis
  python 01_quality_gate_metrics.py --predictions-csv results/predictions.csv --output results/gates --plot
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--demo', action='store_true',
                           help='Run with synthetic demo data')
    input_group.add_argument('--predictions-csv', type=Path,
                           help='CSV file with y_true,y_pred columns')
    
    # Demo parameters
    parser.add_argument('--demo-samples', type=int, default=2000,
                       help='Number of demo samples (default: 2000)')
    parser.add_argument('--demo-imbalance', type=float, default=0.3,
                       help='Class imbalance level 0-1 (default: 0.3)')
    parser.add_argument('--demo-noise', type=float, default=0.1,
                       help='Prediction noise level 0-1 (default: 0.1)')
    
    # Output options
    parser.add_argument('--output', type=Path,
                       help='Output directory for results')
    parser.add_argument('--model-name', type=str, default='model',
                       help='Model name for reporting')
    parser.add_argument('--plot', action='store_true',
                       help='Generate visualization plots')
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.demo:
        y_true, y_pred = generate_demo_data(
            n_samples=args.demo_samples,
            class_imbalance=args.demo_imbalance,
            noise_level=args.demo_noise
        )
    else:
        y_true, y_pred = load_predictions_csv(args.predictions_csv)
    
    # Compute metrics
    try:
        metrics = compute_classification_metrics(y_true, y_pred)
        gates = evaluate_quality_gates(metrics)
        
        # Print report
        print_quality_gate_report(metrics, gates, args.model_name)
        
        # Save results
        if args.output:
            save_results(metrics, gates, args.output, args.model_name)
        
        # Generate plots
        if args.plot:
            create_visualizations(metrics, args.output)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Key Takeaways

1. **Scikit-learn provides robust metrics**: Use tested implementations over manual calculations
2. **Dataclasses improve code organization**: Type-safe, self-documenting data structures
3. **Type hints enhance code quality**: Better IDE support and error detection
4. **Pathlib modernizes file handling**: More intuitive than os.path
5. **Comprehensive validation prevents errors**: Check inputs early and thoroughly

## Next Steps

- **Tutorial 2**: Learn Stuart-Maxwell test implementation with scipy
- **Practice**: Run the script with different demo parameters
- **Real Data**: Apply to your own classification results

The quality gate script provides the foundation for all emotion classification evaluation. Master these Python patterns for robust, maintainable data science code!
