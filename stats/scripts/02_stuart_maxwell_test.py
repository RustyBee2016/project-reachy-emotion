"""
Script 2: Stuart-Maxwell Test for Model Comparison
==================================================

Purpose:
    Compare prediction patterns between base and fine-tuned emotion classification
    models using the Stuart-Maxwell test for marginal homogeneity.
    
    This test answers: "Did fine-tuning systematically change how the model 
    classifies emotions?"

Background:
    The Stuart-Maxwell test is a multi-class extension of McNemar's test.
    Given two models classifying the same samples, it tests whether the
    marginal distributions of predictions differ - i.e., whether the overall
    pattern of predictions shifted systematically.

Usage:
    # With real predictions
    python 02_stuart_maxwell_test.py --predictions results/paired_predictions.npz
    
    # Demo mode with synthetic data
    python 02_stuart_maxwell_test.py --demo

Output:
    - Chi-squared statistic and p-value
    - Interpretation of results
    - Contingency table visualization
    - JSON file with detailed results

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
from scipy import stats


# =============================================================================
# CONFIGURATION
# =============================================================================

# Emotion class labels (8-class HSEmotion)
EMOTION_CLASSES = [
    "anger",
    "contempt", 
    "disgust",
    "fear",
    "happiness",
    "neutral",
    "sadness",
    "surprise",
]

# Significance level
ALPHA = 0.05


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StuartMaxwellResult:
    """Result of Stuart-Maxwell test."""
    chi_squared: float
    degrees_of_freedom: int
    p_value: float
    significant: bool
    alpha: float
    
    # Marginal differences
    marginal_differences: Dict[str, float]
    
    # Contingency table
    contingency_table: List[List[int]]
    
    # Sample counts
    n_samples: int
    n_agreements: int
    n_disagreements: int
    agreement_rate: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# =============================================================================
# STUART-MAXWELL TEST IMPLEMENTATION
# =============================================================================

def build_contingency_table(
    base_preds: np.ndarray,
    finetuned_preds: np.ndarray,
    n_classes: int
) -> np.ndarray:
    """
    Build K×K contingency table from paired predictions.
    
    Entry (i, j) counts samples where:
    - Base model predicted class i
    - Fine-tuned model predicted class j
    
    The diagonal represents agreement (both models predicted the same class).
    Off-diagonal entries represent disagreements.
    
    Args:
        base_preds: Predictions from base model (shape: [n_samples])
        finetuned_preds: Predictions from fine-tuned model (shape: [n_samples])
        n_classes: Number of emotion classes
    
    Returns:
        Contingency table (shape: [n_classes, n_classes])
    """
    table = np.zeros((n_classes, n_classes), dtype=int)
    
    for base_pred, ft_pred in zip(base_preds, finetuned_preds):
        table[base_pred, ft_pred] += 1
    
    return table


def compute_marginal_differences(table: np.ndarray) -> np.ndarray:
    """
    Compute marginal differences d_i = n_{i.} - n_{.i}.
    
    For each class i:
    - n_{i.} = row marginal = sum of row i = count of base model predicting class i
    - n_{.i} = column marginal = sum of column i = count of fine-tuned model predicting class i
    - d_i = n_{i.} - n_{.i} = shift in prediction frequency for class i
    
    A positive d_i means the base model predicted class i more often than the fine-tuned model.
    A negative d_i means the fine-tuned model predicted class i more often.
    
    Args:
        table: K×K contingency table
    
    Returns:
        Marginal differences (shape: [K])
    """
    row_marginals = table.sum(axis=1)  # n_{i.}
    col_marginals = table.sum(axis=0)  # n_{.i}
    return row_marginals - col_marginals


def compute_covariance_matrix(table: np.ndarray) -> np.ndarray:
    """
    Compute covariance matrix V for the marginal differences.
    
    For the Stuart-Maxwell test, the covariance matrix elements are:
    
    V_{ii} = n_{i.} + n_{.i} - 2*n_{ii}
    V_{ij} = -(n_{ij} + n_{ji})  for i ≠ j
    
    where:
    - n_{i.} = row marginal for class i
    - n_{.i} = column marginal for class i
    - n_{ii} = diagonal entry (agreements for class i)
    - n_{ij} = off-diagonal entry
    
    Args:
        table: K×K contingency table
    
    Returns:
        Covariance matrix (shape: [K-1, K-1])
        Note: We use K-1 dimensions because one class is dropped for identifiability
    """
    K = table.shape[0]
    
    row_marginals = table.sum(axis=1)
    col_marginals = table.sum(axis=0)
    
    # Build full K×K covariance matrix first
    V_full = np.zeros((K, K))
    
    for i in range(K):
        for j in range(K):
            if i == j:
                # Diagonal: V_{ii} = n_{i.} + n_{.i} - 2*n_{ii}
                V_full[i, i] = row_marginals[i] + col_marginals[i] - 2 * table[i, i]
            else:
                # Off-diagonal: V_{ij} = -(n_{ij} + n_{ji})
                V_full[i, j] = -(table[i, j] + table[j, i])
    
    # Drop last row and column for non-singularity
    # (marginal differences sum to zero, so one is redundant)
    V_reduced = V_full[:-1, :-1]
    
    return V_reduced


def stuart_maxwell_test(
    base_preds: np.ndarray,
    finetuned_preds: np.ndarray,
    alpha: float = ALPHA
) -> StuartMaxwellResult:
    """
    Perform Stuart-Maxwell test for marginal homogeneity.
    
    The test statistic is:
    
        χ²_SM = d^T V^{-1} d
    
    where:
    - d = (d_1, ..., d_{K-1})^T is the vector of marginal differences (reduced)
    - V is the covariance matrix of d
    
    Under H_0 (marginal homogeneity), χ²_SM ~ χ²(K-1).
    
    Interpretation:
    - H_0: The models have the same marginal prediction distributions
    - H_1: The models have different marginal prediction distributions
    
    A significant result means the fine-tuned model systematically changed
    its prediction patterns compared to the base model.
    
    Args:
        base_preds: Predictions from base model (shape: [n_samples])
        finetuned_preds: Predictions from fine-tuned model (shape: [n_samples])
        alpha: Significance level (default: 0.05)
    
    Returns:
        StuartMaxwellResult containing test statistics and interpretation
    """
    n_classes = len(EMOTION_CLASSES)
    n_samples = len(base_preds)
    
    # Build contingency table
    table = build_contingency_table(base_preds, finetuned_preds, n_classes)
    
    # Compute marginal differences
    d_full = compute_marginal_differences(table)
    d_reduced = d_full[:-1]  # Drop last element
    
    # Compute covariance matrix
    V = compute_covariance_matrix(table)
    
    # Check if covariance matrix is invertible
    try:
        V_inv = np.linalg.inv(V)
    except np.linalg.LinAlgError:
        # Use pseudo-inverse if singular
        V_inv = np.linalg.pinv(V)
    
    # Compute test statistic: χ²_SM = d^T V^{-1} d
    chi_squared = float(d_reduced @ V_inv @ d_reduced)
    
    # Degrees of freedom = K - 1
    df = n_classes - 1
    
    # Compute p-value
    p_value = 1 - stats.chi2.cdf(chi_squared, df)
    
    # Determine significance
    significant = p_value < alpha
    
    # Compute agreement statistics
    n_agreements = int(np.trace(table))
    n_disagreements = n_samples - n_agreements
    agreement_rate = n_agreements / n_samples
    
    # Create marginal differences dict
    marginal_diffs = {cls: float(d_full[i]) for i, cls in enumerate(EMOTION_CLASSES)}
    
    return StuartMaxwellResult(
        chi_squared=chi_squared,
        degrees_of_freedom=df,
        p_value=p_value,
        significant=significant,
        alpha=alpha,
        marginal_differences=marginal_diffs,
        contingency_table=table.tolist(),
        n_samples=n_samples,
        n_agreements=n_agreements,
        n_disagreements=n_disagreements,
        agreement_rate=agreement_rate,
    )


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_report(result: StuartMaxwellResult) -> None:
    """Print formatted Stuart-Maxwell test report to console."""
    
    print("\n" + "=" * 70)
    print("STUART-MAXWELL TEST: Model Comparison")
    print("=" * 70)
    
    # Test Overview
    print("\n--- TEST OVERVIEW ---")
    print("Question: Did fine-tuning systematically change prediction patterns?")
    print(f"Samples analyzed: {result.n_samples}")
    print(f"Agreement rate: {result.agreement_rate:.2%} ({result.n_agreements} samples)")
    print(f"Disagreement rate: {1-result.agreement_rate:.2%} ({result.n_disagreements} samples)")
    
    # Test Results
    print("\n--- TEST RESULTS ---")
    print(f"Chi-squared statistic: {result.chi_squared:.4f}")
    print(f"Degrees of freedom: {result.degrees_of_freedom}")
    print(f"P-value: {result.p_value:.6f}")
    print(f"Significance level (α): {result.alpha}")
    
    # Interpretation
    print("\n--- INTERPRETATION ---")
    if result.significant:
        print("Result: SIGNIFICANT")
        print(f"The p-value ({result.p_value:.6f}) is less than α ({result.alpha}).")
        print("→ Fine-tuning CHANGED the model's prediction patterns.")
        print("→ Proceed to per-class analysis to understand WHERE changes occurred.")
    else:
        print("Result: NOT SIGNIFICANT")
        print(f"The p-value ({result.p_value:.6f}) is greater than α ({result.alpha}).")
        print("→ No systematic change in prediction patterns detected.")
        print("→ Fine-tuning had no statistically detectable effect.")
    
    # Marginal Differences
    print("\n--- MARGINAL DIFFERENCES ---")
    print("(Positive = base model predicted more; Negative = fine-tuned predicted more)")
    print(f"{'Class':<15} {'Difference':>12} {'Direction':>15}")
    print("-" * 45)
    
    for cls, diff in result.marginal_differences.items():
        if diff > 0:
            direction = "← Base more"
        elif diff < 0:
            direction = "→ Fine-tuned more"
        else:
            direction = "No change"
        print(f"{cls:<15} {diff:>+12.0f} {direction:>15}")
    
    # Contingency Table
    print("\n--- CONTINGENCY TABLE ---")
    print("(Rows: Base model predictions, Columns: Fine-tuned model predictions)")
    print()
    
    # Header
    header = "          " + " ".join(f"{cls[:4]:>6}" for cls in EMOTION_CLASSES)
    print(header)
    
    # Matrix rows
    for i, cls in enumerate(EMOTION_CLASSES):
        row = f"{cls[:8]:<10}" + " ".join(f"{result.contingency_table[i][j]:>6}" for j in range(len(EMOTION_CLASSES)))
        print(row)
    
    print("\n" + "=" * 70)


def save_report(result: StuartMaxwellResult, output_path: Path) -> None:
    """Save Stuart-Maxwell test results to JSON file."""
    output_data = {
        "test_name": "Stuart-Maxwell Test",
        "description": "Test for marginal homogeneity in paired categorical data",
        "hypothesis": {
            "null": "Models have the same marginal prediction distributions",
            "alternative": "Models have different marginal prediction distributions",
        },
        "results": result.to_dict(),
        "emotion_classes": EMOTION_CLASSES,
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nReport saved to: {output_path}")


# =============================================================================
# VISUALIZATION (Optional)
# =============================================================================

def plot_contingency_heatmap(result: StuartMaxwellResult, output_path: Optional[Path] = None) -> None:
    """
    Plot contingency table as heatmap.
    
    Diagonal shows agreements, off-diagonal shows disagreements.
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("Warning: matplotlib/seaborn not available. Skipping visualization.")
        return
    
    table = np.array(result.contingency_table)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        table,
        annot=True,
        fmt='d',
        cmap='YlOrRd',
        xticklabels=EMOTION_CLASSES,
        yticklabels=EMOTION_CLASSES,
    )
    plt.xlabel('Fine-tuned Model Predictions')
    plt.ylabel('Base Model Predictions')
    plt.title(f'Prediction Agreement Table\n(Agreement rate: {result.agreement_rate:.1%})')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Contingency heatmap saved to: {output_path}")
    else:
        plt.show()


def plot_marginal_differences(result: StuartMaxwellResult, output_path: Optional[Path] = None) -> None:
    """
    Plot marginal differences as bar chart.
    
    Shows which classes the models disagree on most.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not available. Skipping visualization.")
        return
    
    classes = list(result.marginal_differences.keys())
    diffs = list(result.marginal_differences.values())
    
    colors = ['#3498db' if d >= 0 else '#e74c3c' for d in diffs]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(classes, diffs, color=colors, edgecolor='black')
    
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.xlabel('Emotion Class')
    plt.ylabel('Marginal Difference (Base - Fine-tuned)')
    plt.title('Prediction Frequency Shifts After Fine-tuning')
    plt.xticks(rotation=45)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', label='Base model predicted more'),
        Patch(facecolor='#e74c3c', label='Fine-tuned model predicted more'),
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Marginal differences chart saved to: {output_path}")
    else:
        plt.show()


# =============================================================================
# DEMO MODE
# =============================================================================

def generate_demo_data(
    n_samples: int = 2000,
    seed: int = 42,
    effect_size: str = "medium"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic paired prediction data for demonstration.
    
    Creates realistic predictions where the fine-tuned model shows
    improvement in some classes (contempt, disgust) and slight
    degradation in others (happiness).
    
    Args:
        n_samples: Number of samples to generate
        seed: Random seed for reproducibility
        effect_size: "none", "small", "medium", or "large"
    
    Returns:
        Tuple of (y_true, base_preds, finetuned_preds)
    """
    np.random.seed(seed)
    
    n_classes = len(EMOTION_CLASSES)
    
    # Generate true labels with some imbalance
    class_weights = [0.10, 0.05, 0.08, 0.10, 0.22, 0.20, 0.15, 0.10]
    y_true = np.random.choice(n_classes, size=n_samples, p=class_weights)
    
    # Base model accuracies per class
    base_accuracies = [0.82, 0.65, 0.72, 0.78, 0.90, 0.88, 0.84, 0.80]
    
    # Fine-tuned model accuracies (effect depends on effect_size)
    if effect_size == "none":
        ft_accuracies = base_accuracies.copy()
    elif effect_size == "small":
        ft_accuracies = [0.83, 0.68, 0.74, 0.79, 0.89, 0.89, 0.85, 0.81]
    elif effect_size == "medium":
        ft_accuracies = [0.84, 0.75, 0.80, 0.82, 0.88, 0.91, 0.86, 0.83]
    else:  # large
        ft_accuracies = [0.88, 0.82, 0.85, 0.86, 0.85, 0.93, 0.88, 0.87]
    
    # Confusion patterns for misclassifications
    confusion_map = {
        0: [3, 2],      # anger -> fear, disgust
        1: [2, 0],      # contempt -> disgust, anger
        2: [1, 0],      # disgust -> contempt, anger
        3: [7, 0],      # fear -> surprise, anger
        4: [7, 5],      # happiness -> surprise, neutral
        5: [6, 4],      # neutral -> sadness, happiness
        6: [5, 3],      # sadness -> neutral, fear
        7: [3, 4],      # surprise -> fear, happiness
    }
    
    base_preds = np.zeros(n_samples, dtype=int)
    ft_preds = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        true_class = y_true[i]
        
        # Base model prediction
        if np.random.random() < base_accuracies[true_class]:
            base_preds[i] = true_class
        else:
            base_preds[i] = np.random.choice(confusion_map[true_class])
        
        # Fine-tuned model prediction
        if np.random.random() < ft_accuracies[true_class]:
            ft_preds[i] = true_class
        else:
            ft_preds[i] = np.random.choice(confusion_map[true_class])
    
    return y_true, base_preds, ft_preds


def run_demo(effect_size: str = "medium") -> None:
    """Run demonstration with synthetic data."""
    print("\n" + "=" * 70)
    print("DEMO MODE: Stuart-Maxwell Test")
    print("=" * 70)
    print(f"\nGenerating synthetic paired prediction data (effect size: {effect_size})...")
    
    y_true, base_preds, ft_preds = generate_demo_data(n_samples=2000, effect_size=effect_size)
    
    print(f"Generated {len(y_true)} paired predictions")
    
    # Run Stuart-Maxwell test
    print("\nRunning Stuart-Maxwell test...")
    result = stuart_maxwell_test(base_preds, ft_preds)
    
    # Print report
    print_report(result)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    save_report(result, output_dir / "demo_stuart_maxwell_results.json")
    
    # Generate visualizations
    try:
        plot_contingency_heatmap(result, output_dir / "demo_contingency_heatmap.png")
        plot_marginal_differences(result, output_dir / "demo_marginal_differences.png")
    except Exception as e:
        print(f"Visualization skipped: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Stuart-Maxwell test for comparing model prediction patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run demo with synthetic data (medium effect)
    python 02_stuart_maxwell_test.py --demo
    
    # Run demo with no effect (should be non-significant)
    python 02_stuart_maxwell_test.py --demo --effect-size none
    
    # Analyze real predictions
    python 02_stuart_maxwell_test.py --predictions results/paired_predictions.npz
    
    # Save visualizations
    python 02_stuart_maxwell_test.py --demo --plot
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with synthetic data"
    )
    parser.add_argument(
        "--effect-size",
        type=str,
        choices=["none", "small", "medium", "large"],
        default="medium",
        help="Effect size for demo data (default: medium)"
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        help="Path to .npz file containing base_preds and finetuned_preds arrays"
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
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level (default: 0.05)"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo(effect_size=args.effect_size)
    elif args.predictions:
        # Load predictions from file
        if not args.predictions.exists():
            print(f"Error: Predictions file not found: {args.predictions}")
            sys.exit(1)
        
        data = np.load(args.predictions)
        base_preds = data['base_preds']
        ft_preds = data['finetuned_preds']
        
        # Run Stuart-Maxwell test
        result = stuart_maxwell_test(base_preds, ft_preds, alpha=args.alpha)
        
        # Print report
        print_report(result)
        
        # Save results
        output_dir = args.output or Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        save_report(result, output_dir / "stuart_maxwell_results.json")
        
        if args.plot:
            plot_contingency_heatmap(result, output_dir / "contingency_heatmap.png")
            plot_marginal_differences(result, output_dir / "marginal_differences.png")
        
        # Exit with appropriate code (0 if significant change detected)
        sys.exit(0)
    else:
        parser.print_help()
        print("\nError: Must specify --demo or --predictions")
        sys.exit(1)


if __name__ == "__main__":
    main()
