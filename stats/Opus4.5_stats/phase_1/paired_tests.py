"""
Paired Statistical Tests for Cross-Validation Comparison
=========================================================

Implements paired comparisons for k-fold CV results:
    - Paired t-test for F1 score differences
    - Cohen's d effect size with interpretation
    - Benjamini-Hochberg FDR correction for multiple comparisons

Reference: Phase_1_Statistical_Analysis.md Section 4

Note on Dataclass Design:
-------------------------
PairedTestResult is intentionally mutable (frozen=False, the default) because
the BH correction step updates the `significant_corrected` and `rank` fields
after initial creation. This two-phase construction (create → correct) is
cleaner than passing all BH-corrected values at construction time, which would
require running BH correction before creating any individual result objects.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats


# =============================================================================
# Input Validation
# =============================================================================

def _validate_fold_scores(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    name: str = "input"
) -> None:
    """Validate that fold score arrays are compatible for paired comparison."""
    if scores_a is None or scores_b is None:
        raise ValueError(f"{name}: Score arrays cannot be None")
    
    scores_a = np.asarray(scores_a)
    scores_b = np.asarray(scores_b)
    
    if len(scores_a) == 0:
        raise ValueError(f"{name}: Score arrays cannot be empty")
    
    if len(scores_a) != len(scores_b):
        raise ValueError(
            f"{name}: Score arrays must have same length (same number of folds). "
            f"Got scores_a={len(scores_a)}, scores_b={len(scores_b)}"
        )
    
    if len(scores_a) < 2:
        raise ValueError(
            f"{name}: Need at least 2 folds for paired comparison, got {len(scores_a)}"
        )


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PairedTestResult:
    """
    Result of a paired t-test comparison.
    
    Note: This dataclass is intentionally mutable. The `significant_corrected`
    and `rank` fields are updated after BH correction is applied across all
    tests. This design allows creating results before knowing the full set
    of p-values needed for multiple comparison correction.
    
    Attributes:
        class_idx: Index of the class being compared
        class_name: Name of the class
        mean_diff: Mean difference (A - B) across folds
        std_diff: Standard deviation of differences
        t_statistic: t-test statistic
        p_value: Raw (uncorrected) p-value
        cohens_d: Effect size (Cohen's d)
        effect_interpretation: Verbal interpretation of effect size
        significant_raw: Whether significant at alpha (uncorrected)
        significant_corrected: Whether significant after BH correction
        alpha: Significance level used
        rank: Rank of p-value (for BH correction tracking)
    """
    class_idx: int
    class_name: str
    mean_diff: float
    std_diff: float
    t_statistic: float
    p_value: float
    cohens_d: float
    effect_interpretation: str
    significant_raw: bool
    significant_corrected: bool = False
    alpha: float = 0.05
    rank: int = 0


# =============================================================================
# Core Statistical Functions
# =============================================================================

def paired_t_test(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    alpha: float = 0.05
) -> Tuple[float, float, float, float]:
    """
    Perform paired t-test on fold scores.
    
    Tests H0: mean(scores_a) = mean(scores_b)
    
    Args:
        scores_a: F1 scores from model A across folds
        scores_b: F1 scores from model B across folds
        alpha: Significance level (not used in calculation, for reference)
        
    Returns:
        Tuple of (t_statistic, p_value, mean_diff, std_diff)
    """
    _validate_fold_scores(scores_a, scores_b, "paired_t_test")
    
    scores_a = np.asarray(scores_a, dtype=np.float64)
    scores_b = np.asarray(scores_b, dtype=np.float64)
    
    differences = scores_a - scores_b
    mean_diff = float(np.mean(differences))
    std_diff = float(np.std(differences, ddof=1))
    
    # Handle edge case: no variance in differences
    if std_diff == 0:
        if mean_diff == 0:
            return (0.0, 1.0, mean_diff, std_diff)
        else:
            # Perfect consistent difference - effectively infinite t
            return (float('inf') if mean_diff > 0 else float('-inf'), 0.0, mean_diff, std_diff)
    
    t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
    
    return (float(t_stat), float(p_value), mean_diff, std_diff)


def cohens_d(scores_a: np.ndarray, scores_b: np.ndarray) -> float:
    """
    Compute Cohen's d effect size for paired samples.
    
    Cohen's d = mean(differences) / std(differences)
    
    This is the standardized mean difference, indicating how many
    standard deviations apart the two conditions are.
    
    Args:
        scores_a: Scores from condition A
        scores_b: Scores from condition B
        
    Returns:
        Cohen's d effect size
    """
    _validate_fold_scores(scores_a, scores_b, "cohens_d")
    
    scores_a = np.asarray(scores_a, dtype=np.float64)
    scores_b = np.asarray(scores_b, dtype=np.float64)
    
    differences = scores_a - scores_b
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)
    
    if std_diff == 0:
        return float('inf') if mean_diff != 0 else 0.0
    
    return float(mean_diff / std_diff)


def interpret_cohens_d(d: float) -> str:
    """
    Interpret Cohen's d effect size.
    
    Thresholds (Cohen, 1988):
        |d| < 0.2: Negligible
        0.2 <= |d| < 0.5: Small
        0.5 <= |d| < 0.8: Medium
        |d| >= 0.8: Large
    
    Args:
        d: Cohen's d value
        
    Returns:
        String interpretation of effect size
    """
    abs_d = abs(d)
    
    if abs_d < 0.2:
        magnitude = "Negligible"
    elif abs_d < 0.5:
        magnitude = "Small"
    elif abs_d < 0.8:
        magnitude = "Medium"
    else:
        magnitude = "Large"
    
    if d > 0:
        direction = "favoring A"
    elif d < 0:
        direction = "favoring B"
    else:
        direction = "no difference"
    
    return f"{magnitude} ({direction})"


# =============================================================================
# Multiple Comparison Correction
# =============================================================================

def benjamini_hochberg_correction(
    p_values: List[float],
    alpha: float = 0.05
) -> List[bool]:
    """
    Apply Benjamini-Hochberg FDR correction for multiple comparisons.
    
    Controls the False Discovery Rate (FDR) - the expected proportion
    of rejected null hypotheses that are actually true.
    
    Procedure:
        1. Sort p-values in ascending order
        2. For each p-value at rank i (1-indexed), compute threshold: (i/m) * α
        3. Find largest i where p_i <= threshold
        4. Reject all hypotheses with rank <= i
    
    Args:
        p_values: List of raw p-values
        alpha: Target FDR level (default 0.05)
        
    Returns:
        List of booleans indicating which tests are significant after correction
    """
    if not p_values:
        return []
    
    m = len(p_values)
    
    # Create (index, p_value) pairs and sort by p_value
    indexed_pvals = [(i, p) for i, p in enumerate(p_values)]
    sorted_pvals = sorted(indexed_pvals, key=lambda x: x[1])
    
    # Find the BH threshold
    significant = [False] * m
    max_significant_rank = -1
    
    for rank, (orig_idx, p_val) in enumerate(sorted_pvals, start=1):
        threshold = (rank / m) * alpha
        if p_val <= threshold:
            max_significant_rank = rank
    
    # All tests with rank <= max_significant_rank are significant
    if max_significant_rank > 0:
        for rank, (orig_idx, p_val) in enumerate(sorted_pvals, start=1):
            if rank <= max_significant_rank:
                significant[orig_idx] = True
    
    return significant


# =============================================================================
# Per-Class Paired Test Pipeline
# =============================================================================

def run_per_class_paired_tests(
    f1_scores_a: Dict[int, np.ndarray],
    f1_scores_b: Dict[int, np.ndarray],
    class_names: Optional[List[str]] = None,
    alpha: float = 0.05,
    apply_bh_correction: bool = True
) -> List[PairedTestResult]:
    """
    Run paired t-tests for each class and apply BH correction.
    
    Args:
        f1_scores_a: Dict mapping class_idx -> array of F1 scores across folds (Model A)
        f1_scores_b: Dict mapping class_idx -> array of F1 scores across folds (Model B)
        class_names: Optional list of class names
        alpha: Significance level
        apply_bh_correction: Whether to apply BH correction (default True)
        
    Returns:
        List of PairedTestResult, one per class, with BH correction applied
    """
    if not f1_scores_a or not f1_scores_b:
        raise ValueError("F1 score dictionaries cannot be empty")
    
    if set(f1_scores_a.keys()) != set(f1_scores_b.keys()):
        raise ValueError("F1 score dictionaries must have the same class indices")
    
    num_classes = len(f1_scores_a)
    
    if class_names is None:
        class_names = [f"Class {i}" for i in range(num_classes)]
    
    results = []
    p_values = []
    
    for class_idx in sorted(f1_scores_a.keys()):
        scores_a = np.asarray(f1_scores_a[class_idx])
        scores_b = np.asarray(f1_scores_b[class_idx])
        
        t_stat, p_val, mean_diff, std_diff = paired_t_test(scores_a, scores_b, alpha)
        d = cohens_d(scores_a, scores_b)
        effect_interp = interpret_cohens_d(d)
        
        result = PairedTestResult(
            class_idx=class_idx,
            class_name=class_names[class_idx] if class_idx < len(class_names) else f"Class {class_idx}",
            mean_diff=mean_diff,
            std_diff=std_diff,
            t_statistic=t_stat,
            p_value=p_val,
            cohens_d=d,
            effect_interpretation=effect_interp,
            significant_raw=p_val < alpha,
            alpha=alpha
        )
        results.append(result)
        p_values.append(p_val)
    
    # Apply BH correction
    if apply_bh_correction:
        significant_corrected = benjamini_hochberg_correction(p_values, alpha)
        
        # Update results with correction info
        sorted_indices = np.argsort(p_values)
        for rank, idx in enumerate(sorted_indices, start=1):
            results[idx].rank = rank
            results[idx].significant_corrected = significant_corrected[idx]
    
    return results


# =============================================================================
# Reporting
# =============================================================================

def print_paired_tests_report(
    results: List[PairedTestResult],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B"
) -> None:
    """
    Print a formatted report of paired test results.
    
    Args:
        results: List of PairedTestResult from run_per_class_paired_tests
        model_a_name: Display name for model A
        model_b_name: Display name for model B
    """
    print(f"\n{'='*80}")
    print(f"PAIRED T-TESTS (Per-Class F1): {model_a_name} vs {model_b_name}")
    print(f"{'='*80}")
    
    print(f"\n{'Class':<12} {'Mean Δ':>8} {'Std Δ':>8} {'t':>8} {'p-value':>10} "
          f"{'d':>7} {'Effect':>20} {'Sig (BH)':>10}")
    print("-" * 95)
    
    for r in results:
        sig_str = "Yes*" if r.significant_corrected else ("Yes" if r.significant_raw else "No")
        print(f"{r.class_name:<12} {r.mean_diff:>+8.4f} {r.std_diff:>8.4f} "
              f"{r.t_statistic:>8.3f} {r.p_value:>10.4f} {r.cohens_d:>+7.3f} "
              f"{r.effect_interpretation:>20} {sig_str:>10}")
    
    print("-" * 95)
    print("* Significant after Benjamini-Hochberg correction")
    
    # Summary
    n_sig_raw = sum(1 for r in results if r.significant_raw)
    n_sig_corrected = sum(1 for r in results if r.significant_corrected)
    
    print(f"\nSummary:")
    print(f"  Significant (raw):       {n_sig_raw}/{len(results)}")
    print(f"  Significant (corrected): {n_sig_corrected}/{len(results)}")
