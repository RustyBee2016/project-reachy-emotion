# Tutorial 2: Stuart-Maxwell Test for Model Comparison with Python

## Learning Objectives

By the end of this tutorial, you will understand:
- How to implement the Stuart-Maxwell test using scipy and NumPy
- Matrix operations for statistical computing in Python
- Advanced dataclass patterns for structured statistical results
- NumPy array manipulation for contingency table analysis
- Statistical visualization with matplotlib and seaborn

## Statistical Background

### What is the Stuart-Maxwell Test?

The Stuart-Maxwell test answers this critical question: **"Did fine-tuning systematically change how the model classifies emotions?"**

It's the **multi-class extension of McNemar's test**, designed for comparing two models on the same dataset. Think of it as detecting whether your model's "personality" changed after training.

### Real-World Scenario

```python
# Before fine-tuning: Base model predictions
base_predictions = ['neutral', 'happiness', 'anger', 'neutral', 'sadness']

# After fine-tuning: Same samples, new predictions  
finetuned_predictions = ['neutral', 'surprise', 'anger', 'sadness', 'sadness']

# Question: Did fine-tuning systematically shift prediction patterns?
# Stuart-Maxwell test provides the statistical answer
```

### Key Concepts

**Marginal Homogeneity**: Do both models predict each emotion class with the same frequency?

**Contingency Table**: Cross-tabulation showing agreement/disagreement patterns
```
              Fine-tuned Model
              A  H  N  S  Total
Base    A    [5  1  2  0]   8    ← Base predicted Anger 8 times
Model   H    [0  7  1  1]   9    ← Base predicted Happiness 9 times  
        N    [1  2 15  2]  20    ← Base predicted Neutral 20 times
        S    [0  0  1  6]   7    ← Base predicted Sadness 7 times
       Total  6 10 19  9   44
```

## Script Structure and Imports

```python
#!/usr/bin/env python3
"""
Stuart-Maxwell Test for Emotion Classification Model Comparison

This script implements the Stuart-Maxwell test to compare prediction patterns
between two emotion classification models using scipy and NumPy.
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
from scipy.stats import chi2
from scipy.linalg import pinv  # Pseudo-inverse for singular matrices
```

**Key Libraries**:
- **scipy.stats.chi2**: Chi-squared distribution for p-value calculation
- **scipy.linalg.pinv**: Pseudo-inverse for handling singular covariance matrices
- **NumPy**: Matrix operations and numerical computing

## Core Data Structures

### Comprehensive Result Dataclass

```python
@dataclass
class StuartMaxwellResult:
    """Comprehensive results from Stuart-Maxwell test analysis."""
    
    # Test statistics
    chi_squared: float
    p_value: float
    degrees_of_freedom: int
    significant: bool
    alpha: float
    
    # Effect size and interpretation
    effect_size: float
    effect_interpretation: str
    
    # Sample information
    n_samples: int
    n_classes: int
    
    # Contingency analysis
    contingency_table: List[List[int]]
    marginal_differences: Dict[str, float]
    row_marginals: Dict[str, int]
    col_marginals: Dict[str, int]
    
    # Agreement analysis
    agreement_rate: float
    n_agreements: int
    n_disagreements: int
    class_agreement_rates: Dict[str, float]
    
    # Additional statistics
    covariance_matrix: List[List[float]]
    is_singular: bool
    condition_number: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @property
    def summary(self) -> str:
        """Generate a brief summary of results."""
        significance = "SIGNIFICANT" if self.significant else "NOT SIGNIFICANT"
        return (f"Stuart-Maxwell Test: {significance} "
                f"(χ² = {self.chi_squared:.4f}, p = {self.p_value:.6f}, "
                f"effect = {self.effect_interpretation})")
```

## Core Statistical Implementation

### Building the Contingency Table

```python
def build_contingency_table(base_labels: List[str], 
                          ft_labels: List[str]) -> np.ndarray:
    """
    Build contingency table from paired predictions.
    
    Args:
        base_labels: Base model predictions
        ft_labels: Fine-tuned model predictions
        
    Returns:
        K x K contingency table as numpy array
        
    Raises:
        ValueError: If inputs have different lengths or invalid labels
    """
    # Input validation
    if len(base_labels) != len(ft_labels):
        raise ValueError(f"Length mismatch: base={len(base_labels)}, ft={len(ft_labels)}")
    
    if len(base_labels) == 0:
        raise ValueError("Empty input arrays")
    
    # Validate emotion labels
    valid_labels = set(EMOTION_CLASSES)
    invalid_base = set(base_labels) - valid_labels
    invalid_ft = set(ft_labels) - valid_labels
    
    if invalid_base:
        raise ValueError(f"Invalid base labels: {invalid_base}")
    if invalid_ft:
        raise ValueError(f"Invalid fine-tuned labels: {invalid_ft}")
    
    # Create contingency table using pandas crosstab for convenience
    df = pd.DataFrame({
        'base': pd.Categorical(base_labels, categories=EMOTION_CLASSES),
        'ft': pd.Categorical(ft_labels, categories=EMOTION_CLASSES)
    })
    
    # Build contingency table
    contingency = pd.crosstab(df['base'], df['ft'], dropna=False)
    
    # Ensure all emotion classes are represented
    for cls in EMOTION_CLASSES:
        if cls not in contingency.index:
            contingency.loc[cls] = 0
        if cls not in contingency.columns:
            contingency[cls] = 0
    
    # Reorder to match EMOTION_CLASSES order
    contingency = contingency.reindex(index=EMOTION_CLASSES, columns=EMOTION_CLASSES, fill_value=0)
    
    return contingency.values.astype(int)
```

### Computing Marginal Differences

```python
def compute_marginal_differences(contingency_table: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute marginal differences for Stuart-Maxwell test.
    
    Args:
        contingency_table: K x K contingency table
        
    Returns:
        Tuple of (marginal_differences, row_marginals, col_marginals)
    """
    # Compute marginals
    row_marginals = contingency_table.sum(axis=1)  # Base model predictions per class
    col_marginals = contingency_table.sum(axis=0)  # Fine-tuned model predictions per class
    
    # Marginal differences: d_i = n_{i.} - n_{.i}
    marginal_differences = row_marginals - col_marginals
    
    return marginal_differences, row_marginals, col_marginals
```

**Interpretation**:
- **Positive difference**: Base model predicted this emotion more often
- **Negative difference**: Fine-tuned model predicted this emotion more often
- **Zero difference**: Both models predicted this emotion equally often

## Covariance Matrix Construction

### The Mathematical Foundation

```python
def build_covariance_matrix(contingency_table: np.ndarray) -> Tuple[np.ndarray, bool, float]:
    """
    Build covariance matrix for Stuart-Maxwell test.
    
    The covariance matrix V has elements:
    - V[i,i] = n_{i.} + n_{.i} - 2*n_{ii} (diagonal: variance of marginal difference)
    - V[i,j] = -(n_{ij} + n_{ji}) (off-diagonal: covariance between classes)
    
    Args:
        contingency_table: K x K contingency table
        
    Returns:
        Tuple of (covariance_matrix, is_singular, condition_number)
    """
    k = contingency_table.shape[0]
    row_marginals = contingency_table.sum(axis=1)
    col_marginals = contingency_table.sum(axis=0)
    
    # Initialize covariance matrix
    V = np.zeros((k, k))
    
    for i in range(k):
        for j in range(k):
            if i == j:
                # Diagonal: variance of marginal difference for class i
                V[i, i] = row_marginals[i] + col_marginals[i] - 2 * contingency_table[i, i]
            else:
                # Off-diagonal: covariance between classes i and j
                V[i, j] = -(contingency_table[i, j] + contingency_table[j, i])
    
    # Check if matrix is singular
    try:
        condition_number = np.linalg.cond(V)
        is_singular = condition_number > 1e12  # Practical threshold for singularity
    except np.linalg.LinAlgError:
        condition_number = np.inf
        is_singular = True
    
    return V, is_singular, condition_number
```

### Handling Singular Matrices

```python
def stuart_maxwell_test(base_labels: List[str], 
                       ft_labels: List[str], 
                       alpha: float = 0.05) -> StuartMaxwellResult:
    """
    Perform Stuart-Maxwell test for marginal homogeneity.
    
    Args:
        base_labels: Base model predictions
        ft_labels: Fine-tuned model predictions
        alpha: Significance level
        
    Returns:
        StuartMaxwellResult with comprehensive test results
    """
    # Build contingency table
    contingency = build_contingency_table(base_labels, ft_labels)
    n_samples = contingency.sum()
    k = len(EMOTION_CLASSES)
    
    # Compute marginal differences
    marginal_diffs, row_marginals, col_marginals = compute_marginal_differences(contingency)
    
    # Build covariance matrix
    V, is_singular, condition_number = build_covariance_matrix(contingency)
    
    # Reduce to (K-1) x (K-1) to avoid singularity
    # Remove last class as it's linearly dependent on others
    V_reduced = V[:-1, :-1]
    d_reduced = marginal_diffs[:-1]
    
    try:
        if is_singular or condition_number > 1e10:
            # Use pseudo-inverse for numerical stability
            V_inv = pinv(V_reduced)
            print(f"Warning: Using pseudo-inverse (condition number: {condition_number:.2e})")
        else:
            V_inv = np.linalg.inv(V_reduced)
        
        # Compute test statistic: χ² = d' * V^(-1) * d
        chi_squared = float(d_reduced.T @ V_inv @ d_reduced)
        
    except np.linalg.LinAlgError as e:
        raise ValueError(f"Matrix inversion failed: {e}")
    
    # Degrees of freedom
    df = k - 1
    
    # P-value from chi-squared distribution
    p_value = 1 - chi2.cdf(chi_squared, df)
    significant = p_value < alpha
    
    # Effect size (Cramer's V equivalent)
    effect_size = np.sqrt(chi_squared / (n_samples * df))
    effect_interpretation = interpret_effect_size(effect_size)
    
    # Agreement analysis
    n_agreements = np.trace(contingency)  # Sum of diagonal elements
    n_disagreements = n_samples - n_agreements
    agreement_rate = n_agreements / n_samples
    
    # Per-class agreement rates
    class_agreements = np.diag(contingency)
    class_agreement_rates = {}
    for i, cls in enumerate(EMOTION_CLASSES):
        total_true = row_marginals[i]
        if total_true > 0:
            class_agreement_rates[cls] = class_agreements[i] / total_true
        else:
            class_agreement_rates[cls] = 0.0
    
    # Create result object
    return StuartMaxwellResult(
        chi_squared=chi_squared,
        p_value=p_value,
        degrees_of_freedom=df,
        significant=significant,
        alpha=alpha,
        effect_size=effect_size,
        effect_interpretation=effect_interpretation,
        n_samples=n_samples,
        n_classes=k,
        contingency_table=contingency.tolist(),
        marginal_differences=dict(zip(EMOTION_CLASSES, marginal_diffs)),
        row_marginals=dict(zip(EMOTION_CLASSES, row_marginals)),
        col_marginals=dict(zip(EMOTION_CLASSES, col_marginals)),
        agreement_rate=agreement_rate,
        n_agreements=n_agreements,
        n_disagreements=n_disagreements,
        class_agreement_rates=class_agreement_rates,
        covariance_matrix=V.tolist(),
        is_singular=is_singular,
        condition_number=condition_number
    )

def interpret_effect_size(effect_size: float) -> str:
    """Interpret effect size magnitude."""
    if effect_size < 0.1:
        return "negligible"
    elif effect_size < 0.3:
        return "small"
    elif effect_size < 0.5:
        return "medium"
    else:
        return "large"
```

## Enhanced Reporting

### Comprehensive Console Output

```python
def print_stuart_maxwell_report(result: StuartMaxwellResult) -> None:
    """Print comprehensive Stuart-Maxwell test report."""
    
    print("=" * 80)
    print("STUART-MAXWELL TEST FOR MARGINAL HOMOGENEITY")
    print("=" * 80)
    
    # Test results summary
    print(f"\n--- TEST RESULTS ---")
    status = "SIGNIFICANT CHANGE" if result.significant else "NO SIGNIFICANT CHANGE"
    symbol = "✅" if result.significant else "❌"
    print(f"Result: {symbol} {status}")
    print(f"Chi-squared statistic: {result.chi_squared:.6f}")
    print(f"P-value: {result.p_value:.6f}")
    print(f"Degrees of freedom: {result.degrees_of_freedom}")
    print(f"Significance level: {result.alpha}")
    print(f"Effect size: {result.effect_size:.4f} ({result.effect_interpretation})")
    
    # Sample information
    print(f"\n--- SAMPLE INFORMATION ---")
    print(f"Total samples: {result.n_samples:,}")
    print(f"Overall agreement rate: {result.agreement_rate:.1%}")
    print(f"Agreements: {result.n_agreements:,}")
    print(f"Disagreements: {result.n_disagreements:,}")
    
    # Marginal differences analysis
    print(f"\n--- MARGINAL DIFFERENCES ANALYSIS ---")
    print("(Positive = base model predicted more; Negative = fine-tuned predicted more)")
    print(f"{'Class':<12} {'Difference':<12} {'Base Count':<12} {'FT Count':<12} {'Agreement':<12}")
    print("-" * 65)
    
    for cls in EMOTION_CLASSES:
        diff = result.marginal_differences[cls]
        base_count = result.row_marginals[cls]
        ft_count = result.col_marginals[cls]
        agreement = result.class_agreement_rates[cls]
        
        print(f"{cls:<12} {diff:+12.0f} {base_count:<12} {ft_count:<12} {agreement:<12.1%}")
    
    # Matrix condition information
    if result.is_singular:
        print(f"\n--- NUMERICAL NOTES ---")
        print(f"⚠️  Covariance matrix is near-singular (condition: {result.condition_number:.2e})")
        print("   Used pseudo-inverse for numerical stability")
```

## Advanced Visualizations

### Enhanced Contingency Heatmap

```python
def create_contingency_heatmap(result: StuartMaxwellResult, 
                              output_path: Optional[Path] = None) -> None:
    """Create enhanced contingency table heatmap."""
    
    # Convert contingency table to DataFrame for easier plotting
    cm = np.array(result.contingency_table)
    df = pd.DataFrame(cm, index=EMOTION_CLASSES, columns=EMOTION_CLASSES)
    
    # Create figure
    plt.figure(figsize=(10, 8))
    
    # Create heatmap with custom annotations
    annot_array = np.empty_like(cm, dtype=object)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            count = cm[i, j]
            pct = (count / cm.sum()) * 100
            # Bold diagonal (agreement) cells
            if i == j:
                annot_array[i, j] = f"**{count}**\n({pct:.1f}%)"
            else:
                annot_array[i, j] = f"{count}\n({pct:.1f}%)"
    
    # Create heatmap
    sns.heatmap(df, 
                annot=annot_array, 
                fmt='',
                cmap='Blues',
                cbar_kws={'label': 'Count'},
                square=True)
    
    # Customize plot
    plt.title(f'Prediction Agreement Matrix\n'
             f'χ² = {result.chi_squared:.4f}, p = {result.p_value:.6f} | '
             f'Agreement Rate: {result.agreement_rate:.1%} | '
             f'Effect: {result.effect_interpretation}')
    plt.xlabel('Fine-tuned Model Predictions')
    plt.ylabel('Base Model Predictions')
    
    # Highlight diagonal for agreement
    for i in range(len(EMOTION_CLASSES)):
        plt.gca().add_patch(plt.Rectangle((i, i), 1, 1, fill=False, edgecolor='red', lw=2))
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Contingency heatmap saved: {output_path}")
    else:
        plt.show()
    
    plt.close()

def create_marginal_differences_plot(result: StuartMaxwellResult,
                                   output_path: Optional[Path] = None) -> None:
    """Create marginal differences bar chart."""
    
    # Prepare data
    classes = EMOTION_CLASSES
    differences = [result.marginal_differences[cls] for cls in classes]
    colors = ['red' if d < 0 else 'blue' for d in differences]
    
    # Create plot
    plt.figure(figsize=(12, 6))
    
    bars = plt.bar(classes, differences, color=colors, alpha=0.7, edgecolor='black')
    
    # Add value labels on bars
    for bar, diff in zip(bars, differences):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + (5 if height > 0 else -15),
                f'{diff:+.0f}', ha='center', va='bottom' if height > 0 else 'top')
    
    # Customize plot
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.8)
    plt.title(f'Marginal Differences by Emotion Class\n'
             f'Total Absolute Change: {sum(abs(d) for d in differences):.0f} | '
             f'Significant: {"Yes" if result.significant else "No"}')
    plt.xlabel('Emotion Class')
    plt.ylabel('Marginal Difference (Base - Fine-tuned)')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='blue', alpha=0.7, label='Base Model More'),
                      Patch(facecolor='red', alpha=0.7, label='Fine-tuned Model More')]
    plt.legend(handles=legend_elements)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Marginal differences plot saved: {output_path}")
    else:
        plt.show()
    
    plt.close()
```

## Demo Data Generation

### Realistic Paired Predictions

```python
def generate_demo_paired_predictions(n_samples: int = 2000,
                                   effect_size: str = "medium",
                                   seed: int = 42) -> Tuple[List[str], List[str]]:
    """
    Generate realistic paired predictions for demo purposes.
    
    Args:
        n_samples: Number of sample pairs to generate
        effect_size: Effect size level ('none', 'small', 'medium', 'large')
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (base_predictions, finetuned_predictions)
    """
    np.random.seed(seed)
    
    print(f"Generating demo paired predictions: n={n_samples}, effect_size={effect_size}")
    
    # Realistic class distribution (slightly imbalanced)
    class_weights = np.array([0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10])
    
    # Generate true labels
    y_true = np.random.choice(EMOTION_CLASSES, size=n_samples, p=class_weights)
    
    # Base model accuracies (realistic values)
    base_accuracies = {
        'anger': 0.82, 'contempt': 0.65, 'disgust': 0.72, 'fear': 0.78,
        'happiness': 0.90, 'neutral': 0.88, 'sadness': 0.84, 'surprise': 0.80
    }
    
    # Effect size modifications for fine-tuned model
    effect_modifications = {
        'none': {cls: 0.0 for cls in EMOTION_CLASSES},
        'small': {
            'anger': 0.01, 'contempt': 0.03, 'disgust': 0.02, 'fear': 0.01,
            'happiness': -0.01, 'neutral': 0.01, 'sadness': 0.01, 'surprise': 0.01
        },
        'medium': {
            'anger': 0.02, 'contempt': 0.10, 'disgust': 0.08, 'fear': 0.04,
            'happiness': -0.02, 'neutral': 0.03, 'sadness': 0.02, 'surprise': 0.03
        },
        'large': {
            'anger': 0.06, 'contempt': 0.17, 'disgust': 0.13, 'fear': 0.08,
            'happiness': -0.05, 'neutral': 0.05, 'sadness': 0.04, 'surprise': 0.07
        }
    }
    
    modifications = effect_modifications[effect_size]
    ft_accuracies = {cls: min(0.95, base_accuracies[cls] + modifications[cls]) 
                     for cls in EMOTION_CLASSES}
    
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
    
    # Generate base model predictions
    base_predictions = []
    for true_label in y_true:
        if np.random.random() < base_accuracies[true_label]:
            base_predictions.append(true_label)
        else:
            confused_options = confusion_patterns[true_label]
            base_predictions.append(np.random.choice(confused_options))
    
    # Generate fine-tuned predictions (correlated with base but with improvements)
    ft_predictions = []
    for i, true_label in enumerate(y_true):
        base_pred = base_predictions[i]
        
        # If base was correct, fine-tuned has higher chance of being correct
        if base_pred == true_label:
            if np.random.random() < ft_accuracies[true_label]:
                ft_predictions.append(true_label)
            else:
                confused_options = confusion_patterns[true_label]
                ft_predictions.append(np.random.choice(confused_options))
        else:
            # If base was wrong, fine-tuned has chance to correct it
            correction_prob = modifications[true_label] * 2  # Higher correction for improved classes
            if np.random.random() < correction_prob:
                ft_predictions.append(true_label)  # Correct the error
            else:
                ft_predictions.append(base_pred)  # Keep same error
    
    return base_predictions, ft_predictions
```

## Command Line Interface

### Usage Examples

```python
def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description='Compare emotion classification models using Stuart-Maxwell test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo with different effect sizes
  python 02_stuart_maxwell_test.py --demo --effect-size none
  python 02_stuart_maxwell_test.py --demo --effect-size medium --plot
  
  # Real data analysis
  python 02_stuart_maxwell_test.py --predictions-csv comparison.csv --output results --plot
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--demo', action='store_true',
                           help='Run with synthetic demo data')
    input_group.add_argument('--predictions-csv', type=Path,
                           help='CSV file with base_pred,finetuned_pred columns')
    
    # Demo parameters
    parser.add_argument('--demo-samples', type=int, default=2000,
                       help='Number of demo samples (default: 2000)')
    parser.add_argument('--effect-size', choices=['none', 'small', 'medium', 'large'],
                       default='medium', help='Demo effect size (default: medium)')
    
    # Analysis parameters
    parser.add_argument('--alpha', type=float, default=0.05,
                       help='Significance level (default: 0.05)')
    
    # Output options
    parser.add_argument('--output', type=Path,
                       help='Output directory for results')
    parser.add_argument('--plot', action='store_true',
                       help='Generate visualization plots')
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.demo:
        base_preds, ft_preds = generate_demo_paired_predictions(
            n_samples=args.demo_samples,
            effect_size=args.effect_size
        )
    else:
        base_preds, ft_preds = load_predictions_csv(args.predictions_csv)
    
    # Perform Stuart-Maxwell test
    try:
        result = stuart_maxwell_test(base_preds, ft_preds, args.alpha)
        
        # Print report
        print_stuart_maxwell_report(result)
        
        # Save results
        if args.output:
            save_results(result, args.output)
        
        # Generate plots
        if args.plot:
            create_visualizations(result, args.output)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Key Takeaways

1. **scipy provides robust statistical functions**: Use tested implementations for chi-squared tests
2. **NumPy excels at matrix operations**: Efficient linear algebra for statistical computing
3. **Handle numerical issues gracefully**: Use pseudo-inverse for singular matrices
4. **Comprehensive result structures**: Dataclasses organize complex statistical outputs
5. **Visualization enhances interpretation**: Heatmaps and bar charts reveal patterns

## Next Steps

- **Tutorial 3**: Learn per-class paired t-tests with scipy.stats
- **Practice**: Run with different effect sizes and interpret results
- **Real Analysis**: Compare your own model versions

The Stuart-Maxwell test is your tool for detecting systematic changes in model behavior. Master it to make informed decisions about model updates!
