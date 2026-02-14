"""
Script 3: Per-Class Paired t-Tests with Benjamini-Hochberg Correction
=====================================================================

Purpose:
    Identify which specific emotion classes showed statistically significant
    changes after fine-tuning, using paired t-tests with multiple comparison
    correction.
    
    This script answers: "WHICH emotion classes improved or degraded after
    fine-tuning?"

Background:
    After the Stuart-Maxwell test detects that prediction patterns changed,
    per-class paired t-tests identify WHERE those changes occurred.
    
    The Benjamini-Hochberg procedure controls the False Discovery Rate (FDR),
    preventing spurious findings when running multiple tests.

Usage:
    # With real fold-level metrics
    python 03_perclass_paired_ttests.py --metrics results/fold_metrics.json
    
    # Demo mode with synthetic data
    python 03_perclass_paired_ttests.py --demo

Output:
    - Per-class test results with adjusted p-values
    - Summary of significant changes
    - Visualization of per-class F1 changes
    - JSON file with detailed results

Author: Reachy Emotion Team
Version: 1.0.0
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_EMOTION_CLASSES = ["happy", "sad", "neutral"]
EMOTION_CLASSES = list(DEFAULT_EMOTION_CLASSES)

# Significance level
ALPHA = 0.05


def _configure_runtime(classes: Optional[List[str]] = None) -> None:
    """Configure runtime class labels."""
    global EMOTION_CLASSES
    if classes:
        normalized = [str(x).strip().lower() for x in classes if str(x).strip()]
        if len(normalized) < 2:
            raise ValueError("At least 2 emotion classes are required")
        EMOTION_CLASSES = normalized


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PerClassTestResult:
    """Result of paired t-test for a single emotion class."""
    emotion_class: str
    mean_base: float
    mean_finetuned: float
    mean_difference: float
    std_difference: float
    t_statistic: float
    p_value_raw: float
    p_value_adjusted: float
    significant: bool
    direction: str  # "improved", "degraded", or "unchanged"
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["mean_base"] = float(self.mean_base)
        data["mean_finetuned"] = float(self.mean_finetuned)
        data["mean_difference"] = float(self.mean_difference)
        data["std_difference"] = float(self.std_difference)
        data["t_statistic"] = float(self.t_statistic)
        data["p_value_raw"] = float(self.p_value_raw)
        data["p_value_adjusted"] = float(self.p_value_adjusted)
        data["significant"] = bool(self.significant)
        return data


@dataclass
class PairedTTestsResult:
    """Complete results of per-class paired t-tests."""
    # Individual class results
    class_results: List[PerClassTestResult]
    
    # Summary statistics
    n_folds: int
    n_classes: int
    alpha: float
    correction_method: str
    
    # Counts
    n_significant: int
    n_improved: int
    n_degraded: int
    n_unchanged: int
    
    # Lists of affected classes
    improved_classes: List[str]
    degraded_classes: List[str]
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["alpha"] = float(self.alpha)
        data["n_significant"] = int(self.n_significant)
        data["n_improved"] = int(self.n_improved)
        data["n_degraded"] = int(self.n_degraded)
        data["n_unchanged"] = int(self.n_unchanged)
        data["class_results"] = [r.to_dict() for r in self.class_results]
        return data


# =============================================================================
# STATISTICAL FUNCTIONS
# =============================================================================

def paired_t_test(
    base_scores: np.ndarray,
    finetuned_scores: np.ndarray
) -> Tuple[float, float, float, float, float]:
    """
    Perform paired t-test for a single emotion class.
    
    The paired t-test compares the mean difference between two related groups.
    Since both models are evaluated on the same folds, the observations are paired.
    
    Test statistic:
        t = d̄ / (s_d / √n)
    
    where:
        d̄ = mean of differences (finetuned - base)
        s_d = standard deviation of differences
        n = number of folds
    
    Args:
        base_scores: F1 scores from base model across folds (shape: [n_folds])
        finetuned_scores: F1 scores from fine-tuned model across folds (shape: [n_folds])
    
    Returns:
        Tuple of (mean_diff, std_diff, t_statistic, p_value, mean_base, mean_ft)
    """
    differences = finetuned_scores - base_scores
    
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)  # Sample std with Bessel's correction
    n = len(differences)
    
    # Handle edge case of zero variance
    if std_diff < 1e-10:
        if abs(mean_diff) < 1e-10:
            return mean_diff, std_diff, 0.0, 1.0, np.mean(base_scores), np.mean(finetuned_scores)
        else:
            # Perfect consistency - treat as highly significant
            t_stat = np.sign(mean_diff) * 100.0
            p_value = 1e-10
            return mean_diff, std_diff, t_stat, p_value, np.mean(base_scores), np.mean(finetuned_scores)
    
    # Compute t-statistic
    t_stat = mean_diff / (std_diff / np.sqrt(n))
    
    # Two-tailed p-value
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-1))
    
    return mean_diff, std_diff, t_stat, p_value, np.mean(base_scores), np.mean(finetuned_scores)


def benjamini_hochberg_correction(p_values: np.ndarray, alpha: float = ALPHA) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply Benjamini-Hochberg procedure for multiple comparison correction.
    
    The BH procedure controls the False Discovery Rate (FDR) - the expected
    proportion of false positives among rejected hypotheses.
    
    Procedure:
    1. Rank p-values from smallest to largest: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
    2. Find the largest k such that p_(k) ≤ (k/m) * α
    3. Reject all hypotheses with rank ≤ k
    
    Adjusted p-values are computed as:
        p_adj_(i) = min(p_(i) * m/i, 1)
    
    with monotonicity enforcement (adjusted p-values are non-decreasing).
    
    Args:
        p_values: Array of raw p-values (shape: [n_tests])
        alpha: Significance level (default: 0.05)
    
    Returns:
        Tuple of (adjusted_p_values, significant_mask)
    """
    m = len(p_values)
    
    # Get sorted indices
    sorted_indices = np.argsort(p_values)
    sorted_p_values = p_values[sorted_indices]
    
    # Compute adjusted p-values
    adjusted = np.zeros(m)
    for i in range(m):
        rank = i + 1
        adjusted[i] = sorted_p_values[i] * m / rank
    
    # Enforce monotonicity (adjusted p-values should be non-decreasing)
    # Work backwards from largest to smallest
    for i in range(m - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
    
    # Cap at 1.0
    adjusted = np.minimum(adjusted, 1.0)
    
    # Reorder to original order
    adjusted_original_order = np.zeros(m)
    adjusted_original_order[sorted_indices] = adjusted
    
    # Determine significance
    significant = adjusted_original_order < alpha
    
    return adjusted_original_order, significant


def run_perclass_paired_ttests(
    base_metrics: Dict[str, List[float]],
    finetuned_metrics: Dict[str, List[float]],
    alpha: float = ALPHA
) -> PairedTTestsResult:
    """
    Run paired t-tests for all emotion classes with BH correction.
    
    Args:
        base_metrics: Dict mapping emotion class to list of F1 scores across folds
                      e.g., {"anger": [0.82, 0.84, 0.81, ...], ...}
        finetuned_metrics: Same structure for fine-tuned model
        alpha: Significance level (default: 0.05)
    
    Returns:
        PairedTTestsResult containing all test results and summary
    """
    n_classes = len(EMOTION_CLASSES)
    n_folds = len(list(base_metrics.values())[0])
    
    # Run paired t-test for each class
    raw_p_values = []
    test_results_raw = []
    
    for cls in EMOTION_CLASSES:
        base_scores = np.array(base_metrics[cls])
        ft_scores = np.array(finetuned_metrics[cls])
        
        mean_diff, std_diff, t_stat, p_value, mean_base, mean_ft = paired_t_test(
            base_scores, ft_scores
        )
        
        raw_p_values.append(p_value)
        test_results_raw.append({
            'class': cls,
            'mean_base': mean_base,
            'mean_ft': mean_ft,
            'mean_diff': mean_diff,
            'std_diff': std_diff,
            't_stat': t_stat,
            'p_raw': p_value,
        })
    
    # Apply Benjamini-Hochberg correction
    raw_p_values = np.array(raw_p_values)
    adjusted_p_values, significant_mask = benjamini_hochberg_correction(raw_p_values, alpha)
    
    # Build final results
    class_results = []
    improved_classes = []
    degraded_classes = []
    
    for i, cls in enumerate(EMOTION_CLASSES):
        raw = test_results_raw[i]
        is_significant = significant_mask[i]
        
        # Determine direction
        if is_significant:
            if raw['mean_diff'] > 0:
                direction = "improved"
                improved_classes.append(cls)
            else:
                direction = "degraded"
                degraded_classes.append(cls)
        else:
            direction = "unchanged"
        
        result = PerClassTestResult(
            emotion_class=cls,
            mean_base=raw['mean_base'],
            mean_finetuned=raw['mean_ft'],
            mean_difference=raw['mean_diff'],
            std_difference=raw['std_diff'],
            t_statistic=raw['t_stat'],
            p_value_raw=raw['p_raw'],
            p_value_adjusted=adjusted_p_values[i],
            significant=is_significant,
            direction=direction,
        )
        class_results.append(result)
    
    # Summary counts
    n_significant = int(np.sum(significant_mask))
    n_improved = len(improved_classes)
    n_degraded = len(degraded_classes)
    n_unchanged = n_classes - n_significant
    
    return PairedTTestsResult(
        class_results=class_results,
        n_folds=n_folds,
        n_classes=n_classes,
        alpha=alpha,
        correction_method="Benjamini-Hochberg",
        n_significant=n_significant,
        n_improved=n_improved,
        n_degraded=n_degraded,
        n_unchanged=n_unchanged,
        improved_classes=improved_classes,
        degraded_classes=degraded_classes,
    )


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_report(result: PairedTTestsResult) -> None:
    """Print formatted per-class paired t-tests report to console."""
    
    print("\n" + "=" * 70)
    print("PER-CLASS PAIRED T-TESTS: Fine-Tuning Effect Analysis")
    print("=" * 70)
    
    # Test Overview
    print("\n--- TEST OVERVIEW ---")
    print("Question: Which emotion classes changed significantly after fine-tuning?")
    print(f"Number of folds: {result.n_folds}")
    print(f"Number of classes tested: {result.n_classes}")
    print(f"Significance level (α): {result.alpha}")
    print(f"Multiple comparison correction: {result.correction_method}")
    
    # Summary
    print("\n--- SUMMARY ---")
    print(f"Significant changes: {result.n_significant} / {result.n_classes} classes")
    print(f"  - Improved: {result.n_improved} classes")
    print(f"  - Degraded: {result.n_degraded} classes")
    print(f"  - Unchanged: {result.n_unchanged} classes")
    
    if result.improved_classes:
        print(f"\nImproved classes: {', '.join(result.improved_classes)}")
    if result.degraded_classes:
        print(f"Degraded classes: {', '.join(result.degraded_classes)}")
    
    # Detailed Results Table
    print("\n--- DETAILED RESULTS ---")
    print(f"{'Class':<12} {'Base F1':>10} {'FT F1':>10} {'Diff':>10} {'t-stat':>10} {'p-raw':>12} {'p-adj':>12} {'Sig?':>8}")
    print("-" * 90)
    
    # Sort by adjusted p-value for readability
    sorted_results = sorted(result.class_results, key=lambda x: x.p_value_adjusted)
    
    for r in sorted_results:
        sig_marker = "YES ✓" if r.significant else "no"
        diff_sign = "+" if r.mean_difference > 0 else ""
        
        # Highlight significant results
        if r.significant:
            direction_marker = "↑" if r.direction == "improved" else "↓"
        else:
            direction_marker = ""
        
        print(f"{r.emotion_class:<12} {r.mean_base:>10.4f} {r.mean_finetuned:>10.4f} "
              f"{diff_sign}{r.mean_difference:>9.4f} {r.t_statistic:>10.3f} "
              f"{r.p_value_raw:>12.6f} {r.p_value_adjusted:>12.6f} {sig_marker:>6} {direction_marker}")
    
    # Interpretation
    print("\n--- INTERPRETATION ---")
    
    if result.n_significant == 0:
        print("No individual classes showed significant changes after correction.")
        print("→ Fine-tuning effects were diffuse across classes, not concentrated.")
    else:
        print(f"Fine-tuning produced significant changes in {result.n_significant} class(es):")
        
        for r in result.class_results:
            if r.significant:
                change_pct = (r.mean_finetuned - r.mean_base) / r.mean_base * 100
                direction = "improved" if r.direction == "improved" else "degraded"
                print(f"  • {r.emotion_class}: {direction} by {abs(change_pct):.1f}% "
                      f"(F1: {r.mean_base:.3f} → {r.mean_finetuned:.3f})")
        
        # Special note for neutral class
        neutral_result = next((r for r in result.class_results if r.emotion_class == "neutral"), None)
        if neutral_result and neutral_result.significant:
            if neutral_result.direction == "improved":
                print("\n→ IMPORTANT: Neutral class improved, strengthening Phase 2 baseline.")
            else:
                print("\n→ WARNING: Neutral class degraded, potentially affecting Phase 2 baseline.")
    
    print("\n" + "=" * 70)


def save_report(result: PairedTTestsResult, output_path: Path) -> None:
    """Save per-class paired t-tests results to JSON file."""
    output_data = {
        "test_name": "Per-Class Paired t-Tests",
        "description": "Paired t-tests for each emotion class with Benjamini-Hochberg correction",
        "hypothesis": {
            "null": "No difference in F1 score between base and fine-tuned models for this class",
            "alternative": "F1 score differs between base and fine-tuned models for this class",
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

def plot_perclass_comparison(result: PairedTTestsResult, output_path: Optional[Path] = None) -> None:
    """
    Plot per-class F1 comparison between base and fine-tuned models.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available. Skipping visualization.")
        return
    
    classes = [r.emotion_class for r in result.class_results]
    base_f1 = [r.mean_base for r in result.class_results]
    ft_f1 = [r.mean_finetuned for r in result.class_results]
    significant = [r.significant for r in result.class_results]
    
    x = np.arange(len(classes))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    bars1 = ax.bar(x - width/2, base_f1, width, label='Base Model', color='#3498db', alpha=0.8)
    bars2 = ax.bar(x + width/2, ft_f1, width, label='Fine-tuned Model', color='#2ecc71', alpha=0.8)
    
    # Highlight significant changes
    for i, sig in enumerate(significant):
        if sig:
            ax.annotate('*', xy=(x[i], max(base_f1[i], ft_f1[i]) + 0.02),
                       ha='center', fontsize=20, color='red')
    
    ax.set_xlabel('Emotion Class')
    ax.set_ylabel('F1 Score')
    ax.set_title('Per-Class F1 Comparison: Base vs. Fine-tuned Model\n(* = significant change after BH correction)')
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 1.1)
    
    # Add grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Per-class comparison chart saved to: {output_path}")
    else:
        plt.show()


def plot_effect_sizes(result: PairedTTestsResult, output_path: Optional[Path] = None) -> None:
    """
    Plot effect sizes (F1 differences) with confidence intervals.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available. Skipping visualization.")
        return
    
    # Sort by effect size
    sorted_results = sorted(result.class_results, key=lambda x: x.mean_difference, reverse=True)
    
    classes = [r.emotion_class for r in sorted_results]
    diffs = [r.mean_difference for r in sorted_results]
    stds = [r.std_difference for r in sorted_results]
    significant = [r.significant for r in sorted_results]
    
    # Compute 95% CI (approximate)
    n = result.n_folds
    ci_multiplier = stats.t.ppf(0.975, df=n-1)
    ci_half_widths = [ci_multiplier * s / np.sqrt(n) for s in stds]
    
    colors = ['#2ecc71' if d > 0 else '#e74c3c' for d in diffs]
    edge_colors = ['black' if sig else 'gray' for sig in significant]
    line_widths = [2 if sig else 1 for sig in significant]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    y_pos = np.arange(len(classes))
    
    ax.barh(y_pos, diffs, xerr=ci_half_widths, color=colors, 
            edgecolor=edge_colors, linewidth=line_widths, capsize=5, alpha=0.8)
    
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(classes)
    ax.set_xlabel('F1 Difference (Fine-tuned - Base)')
    ax.set_title('Effect Sizes with 95% Confidence Intervals\n(Bold border = significant after BH correction)')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', label='Improvement'),
        Patch(facecolor='#e74c3c', label='Degradation'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Effect sizes chart saved to: {output_path}")
    else:
        plt.show()


# =============================================================================
# DEMO MODE
# =============================================================================

def generate_demo_fold_metrics(
    n_folds: int = 10,
    seed: int = 42,
    effect_pattern: str = "mixed"
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
    """
    Generate synthetic fold-level F1 metrics for demonstration.
    
    Args:
        n_folds: Number of cross-validation folds
        seed: Random seed for reproducibility
        effect_pattern: "none", "all_improve", "all_degrade", or "mixed"
    
    Returns:
        Tuple of (base_metrics, finetuned_metrics) dicts
    """
    np.random.seed(seed)
    
    # Base model mean F1 scores per class
    base_means = {cls: 0.82 for cls in EMOTION_CLASSES}
    if "neutral" in base_means:
        base_means["neutral"] = 0.86
    
    # Effect sizes (fine-tuned - base) depending on pattern
    if effect_pattern == "none":
        effects = {cls: 0.0 for cls in EMOTION_CLASSES}
    elif effect_pattern == "all_improve":
        effects = {cls: 0.05 for cls in EMOTION_CLASSES}
    elif effect_pattern == "all_degrade":
        effects = {cls: -0.05 for cls in EMOTION_CLASSES}
    else:  # mixed - realistic pattern
        effects = {cls: 0.02 for cls in EMOTION_CLASSES}
        if "happy" in effects:
            effects["happy"] = -0.01
        if "neutral" in effects:
            effects["neutral"] = 0.04
    
    # Standard deviation for fold-to-fold variation
    fold_std = 0.03
    
    base_metrics = {}
    finetuned_metrics = {}
    
    for cls in EMOTION_CLASSES:
        base_mean = base_means[cls]
        ft_mean = base_mean + effects[cls]
        
        # Generate fold scores with some correlation between base and fine-tuned
        # (same folds should have similar difficulty)
        fold_difficulty = np.random.normal(0, fold_std/2, n_folds)
        
        base_scores = base_mean + fold_difficulty + np.random.normal(0, fold_std/2, n_folds)
        ft_scores = ft_mean + fold_difficulty + np.random.normal(0, fold_std/2, n_folds)
        
        # Clip to valid range
        base_scores = np.clip(base_scores, 0, 1)
        ft_scores = np.clip(ft_scores, 0, 1)
        
        base_metrics[cls] = base_scores.tolist()
        finetuned_metrics[cls] = ft_scores.tolist()
    
    return base_metrics, finetuned_metrics


def run_demo(effect_pattern: str = "mixed", n_folds: int = 10) -> None:
    """Run demonstration with synthetic fold-level metrics."""
    print("\n" + "=" * 70)
    print("DEMO MODE: Per-Class Paired t-Tests")
    print("=" * 70)
    print(f"\nGenerating synthetic fold-level metrics (pattern: {effect_pattern}, folds: {n_folds})...")
    
    base_metrics, ft_metrics = generate_demo_fold_metrics(
        n_folds=n_folds,
        effect_pattern=effect_pattern
    )
    
    print(f"Generated {n_folds}-fold metrics for {len(EMOTION_CLASSES)} emotion classes")
    
    # Show sample of generated data
    print("\nSample fold metrics (first 3 folds):")
    print(f"{'Class':<12} {'Base (folds 1-3)':<30} {'Fine-tuned (folds 1-3)':<30}")
    print("-" * 75)
    for cls in EMOTION_CLASSES[:3]:
        base_str = ", ".join(f"{v:.3f}" for v in base_metrics[cls][:3])
        ft_str = ", ".join(f"{v:.3f}" for v in ft_metrics[cls][:3])
        print(f"{cls:<12} [{base_str}] [{ft_str}]")
    print("...")
    
    # Run per-class paired t-tests
    print("\nRunning per-class paired t-tests with Benjamini-Hochberg correction...")
    result = run_perclass_paired_ttests(base_metrics, ft_metrics)
    
    # Print report
    print_report(result)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    save_report(result, output_dir / "demo_perclass_ttests_results.json")
    
    # Save the fold metrics for reference
    fold_data = {
        "base_metrics": base_metrics,
        "finetuned_metrics": ft_metrics,
        "n_folds": n_folds,
        "effect_pattern": effect_pattern,
    }
    with open(output_dir / "demo_fold_metrics.json", 'w') as f:
        json.dump(fold_data, f, indent=2)
    print(f"Fold metrics saved to: {output_dir / 'demo_fold_metrics.json'}")
    
    # Generate visualizations
    try:
        plot_perclass_comparison(result, output_dir / "demo_perclass_comparison.png")
        plot_effect_sizes(result, output_dir / "demo_effect_sizes.png")
    except Exception as e:
        print(f"Visualization skipped: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Per-class paired t-tests with Benjamini-Hochberg correction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run demo with mixed effects (some classes improve, some degrade)
    python 03_perclass_paired_ttests.py --demo
    
    # Run demo with no effect (should find no significant changes)
    python 03_perclass_paired_ttests.py --demo --effect-pattern none
    
    # Analyze real fold metrics
    python 03_perclass_paired_ttests.py --metrics results/fold_metrics.json
    
    # Save visualizations
    python 03_perclass_paired_ttests.py --demo --plot
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with synthetic data"
    )
    parser.add_argument(
        "--effect-pattern",
        type=str,
        choices=["none", "all_improve", "all_degrade", "mixed"],
        default="mixed",
        help="Effect pattern for demo data (default: mixed)"
    )
    parser.add_argument(
        "--n-folds",
        type=int,
        default=10,
        help="Number of folds for demo data (default: 10)"
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        help="Path to JSON file containing fold-level metrics"
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
    parser.add_argument(
        "--emotion-classes",
        type=str,
        default=None,
        help="Comma-separated class names (default: inferred from metrics file, else happy,sad,neutral)",
    )
    
    args = parser.parse_args()
    
    cli_classes = [x.strip() for x in args.emotion_classes.split(",")] if args.emotion_classes else None

    if args.demo:
        _configure_runtime(cli_classes or list(DEFAULT_EMOTION_CLASSES))
        run_demo(effect_pattern=args.effect_pattern, n_folds=args.n_folds)
    elif args.metrics:
        # Load metrics from file
        if not args.metrics.exists():
            print(f"Error: Metrics file not found: {args.metrics}")
            sys.exit(1)
        
        with open(args.metrics, 'r') as f:
            data = json.load(f)

        base_metrics = data['base_metrics']
        ft_metrics = data['finetuned_metrics']
        inferred_classes = sorted(set(base_metrics.keys()) & set(ft_metrics.keys()))
        _configure_runtime(cli_classes or inferred_classes or list(DEFAULT_EMOTION_CLASSES))
        
        # Run per-class paired t-tests
        result = run_perclass_paired_ttests(base_metrics, ft_metrics, alpha=args.alpha)
        
        # Print report
        print_report(result)
        
        # Save results
        output_dir = args.output or Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        save_report(result, output_dir / "perclass_ttests_results.json")
        
        if args.plot:
            plot_perclass_comparison(result, output_dir / "perclass_comparison.png")
            plot_effect_sizes(result, output_dir / "effect_sizes.png")
        
        # Exit with code indicating number of significant changes
        sys.exit(0)
    else:
        parser.print_help()
        print("\nError: Must specify --demo or --metrics")
        sys.exit(1)


if __name__ == "__main__":
    main()
