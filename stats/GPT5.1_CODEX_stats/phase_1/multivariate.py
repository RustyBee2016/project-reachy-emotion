"""
Multivariate Methods for Model Comparison

Implements:
    - Stuart-Maxwell Test (multi-class marginal homogeneity)
    - McNemar's Test (per-class binary comparison)
    - Cohen's Kappa (inter-model agreement)
"""

import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StuartMaxwellResult:
    """Results from Stuart-Maxwell test."""
    chi2_statistic: float
    degrees_of_freedom: int
    p_value: float
    marginal_differences: Dict[str, int]
    contingency_table: np.ndarray
    reject_null: bool
    alpha: float = 0.05


@dataclass
class McNemarResult:
    """Results from McNemar's test for a single class."""
    class_name: str
    n_base_correct_ft_incorrect: int  # n_12
    n_base_incorrect_ft_correct: int  # n_21
    chi2_statistic: float
    p_value: float
    net_improvement: int
    reject_null: bool
    alpha: float = 0.05


@dataclass
class KappaResult:
    """Results from Cohen's Kappa calculation."""
    kappa: float
    observed_agreement: float
    expected_agreement: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    interpretation: str


def build_contingency_table(
    base_preds: np.ndarray,
    ft_preds: np.ndarray,
    num_classes: int
) -> np.ndarray:
    """
    Build K×K contingency table for model comparison.
    
    Entry (i, j) = count of samples where base model predicts class i
    and fine-tuned model predicts class j.
    
    Args:
        base_preds: Predictions from base model
        ft_preds: Predictions from fine-tuned model
        num_classes: Number of classes
        
    Returns:
        Contingency table of shape (num_classes, num_classes)
    """
    table = np.zeros((num_classes, num_classes), dtype=np.int64)
    for b, f in zip(base_preds, ft_preds):
        table[int(b), int(f)] += 1
    return table


def stuart_maxwell_test(
    contingency_table: np.ndarray,
    class_names: List[str],
    alpha: float = 0.05
) -> StuartMaxwellResult:
    """
    Perform Stuart-Maxwell test for marginal homogeneity.
    
    Tests whether the overall distribution of predictions shifted
    between models across all classes simultaneously.
    
    H0: Marginal distributions are equal (no overall shift)
    H1: Marginal distributions differ (significant shift)
    
    Args:
        contingency_table: K×K table of (base_pred, ft_pred) counts
        class_names: List of class names
        alpha: Significance level
        
    Returns:
        StuartMaxwellResult with test statistics and decision
    """
    K = contingency_table.shape[0]
    n = contingency_table.sum()
    
    # Compute row and column marginals
    row_marginals = contingency_table.sum(axis=1)  # Base model class totals
    col_marginals = contingency_table.sum(axis=0)  # FT model class totals
    
    # Marginal differences d_i = n_{i.} - n_{.i}
    d = row_marginals - col_marginals
    marginal_diffs = {class_names[i]: int(d[i]) for i in range(K)}
    
    # For Stuart-Maxwell, we use K-1 classes (drop last for non-singularity)
    d_reduced = d[:-1]
    
    # Compute covariance matrix V
    # V_{ij} = n_{i.} + n_{.i} - 2*n_{ii}  if i == j
    # V_{ij} = -(n_{ij} + n_{ji})          if i != j
    V = np.zeros((K - 1, K - 1))
    
    for i in range(K - 1):
        for j in range(K - 1):
            if i == j:
                V[i, j] = row_marginals[i] + col_marginals[i] - 2 * contingency_table[i, i]
            else:
                V[i, j] = -(contingency_table[i, j] + contingency_table[j, i])
    
    # Handle singular matrix case
    try:
        V_inv = np.linalg.inv(V)
        chi2 = float(d_reduced @ V_inv @ d_reduced)
    except np.linalg.LinAlgError:
        # Use pseudo-inverse if singular
        V_inv = np.linalg.pinv(V)
        chi2 = float(d_reduced @ V_inv @ d_reduced)
    
    df = K - 1
    p_value = float(1 - stats.chi2.cdf(chi2, df))
    
    return StuartMaxwellResult(
        chi2_statistic=chi2,
        degrees_of_freedom=df,
        p_value=p_value,
        marginal_differences=marginal_diffs,
        contingency_table=contingency_table,
        reject_null=p_value < alpha,
        alpha=alpha,
    )


def mcnemar_test(
    y_true: np.ndarray,
    base_preds: np.ndarray,
    ft_preds: np.ndarray,
    class_idx: int,
    class_name: str,
    alpha: float = 0.05,
    continuity_correction: bool = True
) -> McNemarResult:
    """
    Perform McNemar's test for a single class.
    
    Tests whether two models differ in their error rates for a specific
    class using paired binary outcomes (correct/incorrect).
    
    H0: Models have equal error rates
    H1: Models have different error rates
    
    Args:
        y_true: Ground truth labels
        base_preds: Base model predictions
        ft_preds: Fine-tuned model predictions
        class_idx: Index of class to test
        class_name: Name of the class
        alpha: Significance level
        continuity_correction: Whether to apply continuity correction
        
    Returns:
        McNemarResult with test statistics and decision
    """
    # Binary correctness for the target class
    base_correct = (base_preds == y_true)
    ft_correct = (ft_preds == y_true)
    
    # Filter to samples where true label is this class
    mask = (y_true == class_idx)
    base_correct_class = base_correct[mask]
    ft_correct_class = ft_correct[mask]
    
    # Build 2×2 table
    #                    FT Correct  FT Incorrect
    # Base Correct       n_11        n_12
    # Base Incorrect     n_21        n_22
    
    n_11 = np.sum(base_correct_class & ft_correct_class)
    n_12 = np.sum(base_correct_class & ~ft_correct_class)  # Base ✓, FT ✗
    n_21 = np.sum(~base_correct_class & ft_correct_class)  # Base ✗, FT ✓
    n_22 = np.sum(~base_correct_class & ~ft_correct_class)
    
    # McNemar's test statistic
    discordant = n_12 + n_21
    
    if discordant == 0:
        chi2 = 0.0
        p_value = 1.0
    else:
        if continuity_correction:
            chi2 = float((abs(n_12 - n_21) - 1) ** 2 / discordant)
        else:
            chi2 = float((n_12 - n_21) ** 2 / discordant)
        
        p_value = float(1 - stats.chi2.cdf(chi2, 1))
    
    return McNemarResult(
        class_name=class_name,
        n_base_correct_ft_incorrect=int(n_12),
        n_base_incorrect_ft_correct=int(n_21),
        chi2_statistic=chi2,
        p_value=p_value,
        net_improvement=int(n_21 - n_12),
        reject_null=p_value < alpha,
        alpha=alpha,
    )


def cohens_kappa(
    contingency_table: np.ndarray,
    confidence_level: float = 0.95
) -> KappaResult:
    """
    Compute Cohen's Kappa for inter-model agreement.
    
    Measures agreement between models beyond chance, indicating
    how similarly they classify samples.
    
    Args:
        contingency_table: K×K table of (base_pred, ft_pred) counts
        confidence_level: Confidence level for CI
        
    Returns:
        KappaResult with kappa, SE, CI, and interpretation
    """
    n = contingency_table.sum()
    K = contingency_table.shape[0]
    
    # Observed agreement: proportion where both models agree
    p_o = float(np.diag(contingency_table).sum() / n)
    
    # Expected agreement by chance
    row_marginals = contingency_table.sum(axis=1) / n
    col_marginals = contingency_table.sum(axis=0) / n
    p_e = float(np.sum(row_marginals * col_marginals))
    
    # Kappa coefficient
    if p_e == 1.0:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = float((p_o - p_e) / (1 - p_e))
    
    # Standard error (simplified formula)
    if p_e == 1.0:
        se = 0.0
    else:
        se = float(np.sqrt(p_o * (1 - p_o) / (n * (1 - p_e) ** 2)))
    
    # Confidence interval
    z = stats.norm.ppf((1 + confidence_level) / 2)
    ci_lower = float(kappa - z * se)
    ci_upper = float(kappa + z * se)
    
    # Interpretation
    if kappa < 0.20:
        interpretation = "Slight agreement"
    elif kappa < 0.40:
        interpretation = "Fair agreement"
    elif kappa < 0.60:
        interpretation = "Moderate agreement"
    elif kappa < 0.80:
        interpretation = "Substantial agreement"
    else:
        interpretation = "Almost perfect agreement"
    
    return KappaResult(
        kappa=kappa,
        observed_agreement=p_o,
        expected_agreement=p_e,
        standard_error=se,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        interpretation=interpretation,
    )


def run_all_mcnemar_tests(
    y_true: np.ndarray,
    base_preds: np.ndarray,
    ft_preds: np.ndarray,
    class_names: List[str],
    alpha: float = 0.05
) -> List[McNemarResult]:
    """
    Run McNemar's test for all classes.
    
    Args:
        y_true: Ground truth labels
        base_preds: Base model predictions
        ft_preds: Fine-tuned model predictions
        class_names: List of class names
        alpha: Significance level
        
    Returns:
        List of McNemarResult, one per class
    """
    results = []
    for idx, name in enumerate(class_names):
        result = mcnemar_test(
            y_true, base_preds, ft_preds,
            class_idx=idx, class_name=name, alpha=alpha
        )
        results.append(result)
    return results


def print_multivariate_report(
    sm_result: StuartMaxwellResult,
    mcnemar_results: List[McNemarResult],
    kappa_result: KappaResult,
    class_names: List[str]
) -> str:
    """
    Generate formatted report of multivariate test results.
    
    Args:
        sm_result: Stuart-Maxwell test result
        mcnemar_results: List of McNemar test results
        kappa_result: Cohen's Kappa result
        class_names: List of class names
        
    Returns:
        Formatted report string
    """
    lines = [
        "=" * 70,
        "MULTIVARIATE ANALYSIS REPORT (Model Comparison)",
        "=" * 70,
        "",
        "1. STUART-MAXWELL TEST (Overall Distributional Shift)",
        "-" * 50,
        f"   χ² statistic:     {sm_result.chi2_statistic:.4f}",
        f"   Degrees of freedom: {sm_result.degrees_of_freedom}",
        f"   p-value:          {sm_result.p_value:.6f}",
        f"   Decision:         {'Reject H₀' if sm_result.reject_null else 'Fail to reject H₀'}",
        "",
        "   Marginal Differences:",
    ]
    
    for name, diff in sm_result.marginal_differences.items():
        lines.append(f"     {name}: {diff:+d}")
    
    lines.extend([
        "",
        "2. McNEMAR'S TESTS (Per-Class Error Rate Comparison)",
        "-" * 50,
    ])
    
    for result in mcnemar_results:
        status = "FT better" if result.net_improvement > 0 else ("FT worse" if result.net_improvement < 0 else "No diff")
        sig = "*" if result.reject_null else ""
        lines.append(
            f"   {result.class_name:10s}  n₁₂={result.n_base_correct_ft_incorrect:4d}  "
            f"n₂₁={result.n_base_incorrect_ft_correct:4d}  "
            f"χ²={result.chi2_statistic:7.2f}  p={result.p_value:.4f}{sig}  {status}"
        )
    
    lines.extend([
        "",
        "3. COHEN'S KAPPA (Inter-Model Agreement)",
        "-" * 50,
        f"   Kappa (κ):          {kappa_result.kappa:.4f}",
        f"   Observed agreement: {kappa_result.observed_agreement:.4f}",
        f"   Expected agreement: {kappa_result.expected_agreement:.4f}",
        f"   95% CI:             [{kappa_result.ci_lower:.4f}, {kappa_result.ci_upper:.4f}]",
        f"   Interpretation:     {kappa_result.interpretation}",
        "",
        "=" * 70,
    ])
    
    return "\n".join(lines)
