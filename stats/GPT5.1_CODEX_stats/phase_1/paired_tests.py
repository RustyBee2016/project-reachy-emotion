"""
Per-Class Paired t-Tests with Benjamini-Hochberg Correction

Implements:
    - Paired t-test for comparing F1 scores across folds
    - Cohen's d effect size calculation
    - Benjamini-Hochberg FDR correction for multiple testing
"""

import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PairedTestResult:
    """Results from a paired t-test for a single class."""
    class_name: str
    mean_difference: float
    std_difference: float
    t_statistic: float
    degrees_of_freedom: int
    p_value: float
    p_value_adjusted: Optional[float]
    cohens_d: float
    effect_size_interpretation: str
    reject_null: bool
    reject_null_adjusted: Optional[bool]
    base_mean: float
    ft_mean: float
    n_folds: int


def paired_t_test(
    base_scores: np.ndarray,
    ft_scores: np.ndarray,
    class_name: str,
    alpha: float = 0.05
) -> PairedTestResult:
    """
    Perform paired t-test comparing F1 scores between models.
    
    H0: Mean F1 difference = 0 (no improvement)
    H1: Mean F1 difference ≠ 0 (significant change)
    
    Args:
        base_scores: F1 scores from base model across folds
        ft_scores: F1 scores from fine-tuned model across folds
        class_name: Name of the class being tested
        alpha: Significance level
        
    Returns:
        PairedTestResult with test statistics
    """
    n = len(base_scores)
    
    # Compute differences
    differences = ft_scores - base_scores
    mean_diff = float(np.mean(differences))
    std_diff = float(np.std(differences, ddof=1))
    
    # t-statistic
    if std_diff == 0:
        t_stat = np.inf if mean_diff > 0 else (-np.inf if mean_diff < 0 else 0.0)
        p_value = 0.0 if mean_diff != 0 else 1.0
    else:
        se = std_diff / np.sqrt(n)
        t_stat = float(mean_diff / se)
        df = n - 1
        p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df)))
    
    # Cohen's d effect size
    cohens_d = compute_cohens_d(mean_diff, std_diff)
    effect_interp = interpret_cohens_d(cohens_d)
    
    return PairedTestResult(
        class_name=class_name,
        mean_difference=mean_diff,
        std_difference=std_diff,
        t_statistic=t_stat,
        degrees_of_freedom=n - 1,
        p_value=p_value,
        p_value_adjusted=None,  # Set later by BH correction
        cohens_d=cohens_d,
        effect_size_interpretation=effect_interp,
        reject_null=p_value < alpha,
        reject_null_adjusted=None,  # Set later
        base_mean=float(np.mean(base_scores)),
        ft_mean=float(np.mean(ft_scores)),
        n_folds=n,
    )


def compute_cohens_d(mean_diff: float, std_diff: float) -> float:
    """
    Compute Cohen's d effect size.
    
    d = mean_difference / std_difference
    
    Args:
        mean_diff: Mean of differences
        std_diff: Standard deviation of differences
        
    Returns:
        Cohen's d value
    """
    if std_diff == 0:
        return np.inf if mean_diff > 0 else (-np.inf if mean_diff < 0 else 0.0)
    return float(mean_diff / std_diff)


def interpret_cohens_d(d: float) -> str:
    """
    Interpret Cohen's d effect size.
    
    Args:
        d: Cohen's d value
        
    Returns:
        Interpretation string
    """
    abs_d = abs(d)
    if abs_d < 0.2:
        return "Negligible"
    elif abs_d < 0.5:
        return "Small"
    elif abs_d < 0.8:
        return "Medium"
    elif abs_d < 2.0:
        return "Large"
    else:
        return "Very Large"


def benjamini_hochberg_correction(
    p_values: List[float],
    alpha: float = 0.05
) -> Tuple[List[float], List[bool]]:
    """
    Apply Benjamini-Hochberg FDR correction for multiple testing.
    
    Procedure:
    1. Rank p-values from smallest to largest
    2. For each rank k, compute threshold = (k/m) * α
    3. Find largest k where p_(k) ≤ threshold
    4. Reject all H0 with p_(i) ≤ p_(k)
    
    Args:
        p_values: List of raw p-values
        alpha: Target FDR level
        
    Returns:
        Tuple of (adjusted_p_values, reject_decisions)
    """
    m = len(p_values)
    if m == 0:
        return [], []
    
    # Get sorted indices
    sorted_indices = np.argsort(p_values)
    sorted_pvals = np.array(p_values)[sorted_indices]
    
    # Compute adjusted p-values
    # p_adj(i) = min(p(i) * m/i, 1), with monotonicity constraint
    adjusted = np.zeros(m)
    for i in range(m - 1, -1, -1):
        rank = i + 1
        raw_adjusted = sorted_pvals[i] * m / rank
        if i == m - 1:
            adjusted[i] = min(raw_adjusted, 1.0)
        else:
            adjusted[i] = min(raw_adjusted, adjusted[i + 1], 1.0)
    
    # Map back to original order
    adjusted_original = np.zeros(m)
    adjusted_original[sorted_indices] = adjusted
    
    # Determine rejections
    reject_decisions = [p_adj < alpha for p_adj in adjusted_original]
    
    return list(adjusted_original), reject_decisions


def run_per_class_paired_tests(
    base_fold_scores: Dict[str, List[float]],
    ft_fold_scores: Dict[str, List[float]],
    class_names: List[str],
    alpha: float = 0.05,
    apply_bh_correction: bool = True
) -> List[PairedTestResult]:
    """
    Run paired t-tests for all classes with optional BH correction.
    
    Args:
        base_fold_scores: Dict mapping class_name -> list of F1 scores per fold
        ft_fold_scores: Dict mapping class_name -> list of F1 scores per fold
        class_names: List of class names to test
        alpha: Significance level
        apply_bh_correction: Whether to apply Benjamini-Hochberg correction
        
    Returns:
        List of PairedTestResult, one per class (with adjusted p-values if BH applied)
    """
    results = []
    
    for class_name in class_names:
        base_scores = np.array(base_fold_scores[class_name])
        ft_scores = np.array(ft_fold_scores[class_name])
        
        result = paired_t_test(base_scores, ft_scores, class_name, alpha)
        results.append(result)
    
    # Apply BH correction if requested
    if apply_bh_correction:
        p_values = [r.p_value for r in results]
        adjusted_pvals, reject_decisions = benjamini_hochberg_correction(p_values, alpha)
        
        for i, result in enumerate(results):
            result.p_value_adjusted = adjusted_pvals[i]
            result.reject_null_adjusted = reject_decisions[i]
    
    return results


def print_paired_tests_report(results: List[PairedTestResult]) -> str:
    """
    Generate formatted report of paired t-test results.
    
    Args:
        results: List of PairedTestResult objects
        
    Returns:
        Formatted report string
    """
    lines = [
        "=" * 80,
        "PER-CLASS PAIRED t-TESTS (with Benjamini-Hochberg Correction)",
        "=" * 80,
        "",
        "Cross-Validation F1 Score Comparison:",
        "-" * 60,
    ]
    
    # Header
    lines.append(
        f"{'Class':10s}  {'Base Mean':>10s}  {'FT Mean':>10s}  {'Δ':>8s}  "
        f"{'t':>8s}  {'p':>10s}  {'p_adj':>10s}  {'d':>8s}  {'Effect':>12s}"
    )
    lines.append("-" * 100)
    
    for r in results:
        sig_raw = "*" if r.reject_null else ""
        sig_adj = "*" if r.reject_null_adjusted else "" if r.reject_null_adjusted is not None else "?"
        p_adj_str = f"{r.p_value_adjusted:.6f}" if r.p_value_adjusted is not None else "N/A"
        
        lines.append(
            f"{r.class_name:10s}  {r.base_mean:10.4f}  {r.ft_mean:10.4f}  "
            f"{r.mean_difference:+8.4f}  {r.t_statistic:8.2f}  "
            f"{r.p_value:10.6f}{sig_raw}  {p_adj_str}{sig_adj}  "
            f"{r.cohens_d:8.2f}  {r.effect_size_interpretation:>12s}"
        )
    
    lines.extend([
        "",
        "Legend: * = significant at α=0.05",
        "",
        "Effect Size Interpretation (Cohen's d):",
        "  |d| < 0.2: Negligible",
        "  0.2 ≤ |d| < 0.5: Small",
        "  0.5 ≤ |d| < 0.8: Medium",
        "  0.8 ≤ |d| < 2.0: Large",
        "  |d| ≥ 2.0: Very Large",
        "",
        "=" * 80,
    ])
    
    return "\n".join(lines)
