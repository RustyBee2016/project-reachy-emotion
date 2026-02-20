"""
Multivariate Statistical Tests for Model Comparison
=====================================================

Implements tests for comparing two emotion classification models:
    - Stuart-Maxwell Test: Marginal homogeneity (overall distribution shift)
    - McNemar's Test: Per-class error rate comparison
    - Cohen's Kappa: Inter-model agreement

Reference: Phase_1_Statistical_Analysis.md Section 3

Implementation Note on McNemar's Test:
--------------------------------------
This module implements McNemar's test manually rather than using scipy.stats.mcnemar
for the following reasons:
    1. Educational clarity: The manual implementation makes the test logic transparent
    2. Per-class extension: We need per-class McNemar tests, not just binary
    3. Consistent CI calculation: We compute exact binomial CIs for the odds ratio
    4. Integration with contingency table: Reuses our build_contingency_table function

For standard binary McNemar's test, scipy.stats.mcnemar is equally valid.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats


# =============================================================================
# Input Validation
# =============================================================================

def _validate_prediction_arrays(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    name: str = "input"
) -> None:
    """Validate that all prediction arrays are compatible."""
    if y_true is None or pred_a is None or pred_b is None:
        raise ValueError(f"{name}: Arrays cannot be None")
    
    y_true = np.asarray(y_true)
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    
    if len(y_true) == 0:
        raise ValueError(f"{name}: Arrays cannot be empty")
    
    if not (len(y_true) == len(pred_a) == len(pred_b)):
        raise ValueError(
            f"{name}: All arrays must have same length. "
            f"Got y_true={len(y_true)}, pred_a={len(pred_a)}, pred_b={len(pred_b)}"
        )


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StuartMaxwellResult:
    """Result of Stuart-Maxwell test for marginal homogeneity."""
    statistic: float
    p_value: float
    df: int
    marginal_a: np.ndarray
    marginal_b: np.ndarray
    marginal_diff: np.ndarray
    significant: bool
    alpha: float


@dataclass
class McNemarResult:
    """Result of McNemar's test for a specific class."""
    class_idx: int
    class_name: str
    b: int  # A correct, B incorrect
    c: int  # A incorrect, B correct
    statistic: float
    p_value: float
    odds_ratio: float
    ci_lower: float
    ci_upper: float
    significant: bool
    alpha: float
    winner: Optional[str]


@dataclass
class KappaResult:
    """Result of Cohen's Kappa for inter-model agreement."""
    kappa: float
    std_error: float
    ci_lower: float
    ci_upper: float
    p_value: float
    agreement_observed: float
    agreement_expected: float
    interpretation: str


# =============================================================================
# Contingency Table Construction
# =============================================================================

def build_contingency_table(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    num_classes: int
) -> np.ndarray:
    """
    Build a contingency table comparing two models' predictions.
    
    The table has shape (4, num_classes) with rows:
        0: Both correct
        1: A correct, B incorrect
        2: A incorrect, B correct
        3: Both incorrect
    
    Args:
        y_true: Ground truth labels
        pred_a: Predictions from model A
        pred_b: Predictions from model B
        num_classes: Number of classes
        
    Returns:
        Contingency table of shape (4, num_classes)
    """
    _validate_prediction_arrays(y_true, pred_a, pred_b, "build_contingency_table")
    
    if num_classes < 2:
        raise ValueError(f"num_classes must be >= 2, got {num_classes}")
    
    y_true = np.asarray(y_true)
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    
    table = np.zeros((4, num_classes), dtype=np.int64)
    
    for i in range(len(y_true)):
        true_class = y_true[i]
        if true_class < 0 or true_class >= num_classes:
            continue
            
        a_correct = pred_a[i] == true_class
        b_correct = pred_b[i] == true_class
        
        if a_correct and b_correct:
            table[0, true_class] += 1
        elif a_correct and not b_correct:
            table[1, true_class] += 1
        elif not a_correct and b_correct:
            table[2, true_class] += 1
        else:
            table[3, true_class] += 1
    
    return table


# =============================================================================
# Stuart-Maxwell Test
# =============================================================================

def stuart_maxwell_test(
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    num_classes: int,
    alpha: float = 0.05
) -> StuartMaxwellResult:
    """
    Perform Stuart-Maxwell test for marginal homogeneity.
    
    Tests whether the marginal distributions of predictions from two models
    are statistically equivalent. A significant result indicates the models
    have different overall prediction patterns.
    
    The test statistic follows a chi-square distribution with K-1 degrees
    of freedom, where K is the number of classes.
    
    Args:
        pred_a: Predictions from model A
        pred_b: Predictions from model B
        num_classes: Number of classes
        alpha: Significance level (default 0.05)
        
    Returns:
        StuartMaxwellResult with test statistics and interpretation
    """
    if pred_a is None or pred_b is None:
        raise ValueError("Prediction arrays cannot be None")
    
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    
    if len(pred_a) == 0:
        raise ValueError("Prediction arrays cannot be empty")
    
    if len(pred_a) != len(pred_b):
        raise ValueError(
            f"Prediction arrays must have same length. "
            f"Got pred_a={len(pred_a)}, pred_b={len(pred_b)}"
        )
    
    if num_classes < 2:
        raise ValueError(f"num_classes must be >= 2, got {num_classes}")
    
    # Build agreement matrix
    n = len(pred_a)
    agreement_matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for a, b in zip(pred_a, pred_b):
        if 0 <= a < num_classes and 0 <= b < num_classes:
            agreement_matrix[a, b] += 1
    
    # Compute marginals
    marginal_a = agreement_matrix.sum(axis=1)
    marginal_b = agreement_matrix.sum(axis=0)
    marginal_diff = marginal_a - marginal_b
    
    # For K classes, we use K-1 linearly independent contrasts
    # Build the d vector and S matrix
    d = marginal_diff[:-1].astype(float)
    
    # Covariance matrix S
    S = np.zeros((num_classes - 1, num_classes - 1))
    for i in range(num_classes - 1):
        for j in range(num_classes - 1):
            if i == j:
                S[i, j] = marginal_a[i] + marginal_b[i] - 2 * agreement_matrix[i, i]
            else:
                S[i, j] = -(agreement_matrix[i, j] + agreement_matrix[j, i])
    
    # Compute test statistic
    try:
        S_inv = np.linalg.inv(S)
        chi2_stat = float(d @ S_inv @ d)
    except np.linalg.LinAlgError:
        # Singular matrix - models have identical predictions
        chi2_stat = 0.0
    
    df = num_classes - 1
    p_value = float(1 - stats.chi2.cdf(chi2_stat, df))
    
    return StuartMaxwellResult(
        statistic=chi2_stat,
        p_value=p_value,
        df=df,
        marginal_a=marginal_a,
        marginal_b=marginal_b,
        marginal_diff=marginal_diff,
        significant=p_value < alpha,
        alpha=alpha
    )


# =============================================================================
# McNemar's Test (Per-Class)
# =============================================================================

def mcnemar_test_per_class(
    contingency_table: np.ndarray,
    class_names: Optional[List[str]] = None,
    alpha: float = 0.05
) -> List[McNemarResult]:
    """
    Perform McNemar's test for each class.
    
    For each class, tests whether the error rates of models A and B
    are significantly different. Uses the discordant pairs (b, c) where:
        b = samples A got correct but B got wrong
        c = samples A got wrong but B got correct
    
    The test statistic (with continuity correction) is:
        χ² = (|b - c| - 1)² / (b + c)
    
    Args:
        contingency_table: Table from build_contingency_table (4 x num_classes)
        class_names: Optional list of class names
        alpha: Significance level (default 0.05)
        
    Returns:
        List of McNemarResult, one per class
    """
    if contingency_table is None or contingency_table.size == 0:
        raise ValueError("Contingency table cannot be None or empty")
    
    if contingency_table.shape[0] != 4:
        raise ValueError(
            f"Contingency table must have 4 rows, got {contingency_table.shape[0]}"
        )
    
    num_classes = contingency_table.shape[1]
    
    if class_names is None:
        class_names = [f"Class {i}" for i in range(num_classes)]
    
    results = []
    
    for class_idx in range(num_classes):
        b = int(contingency_table[1, class_idx])  # A correct, B incorrect
        c = int(contingency_table[2, class_idx])  # A incorrect, B correct
        
        # McNemar's test with continuity correction
        if b + c == 0:
            chi2_stat = 0.0
            p_value = 1.0
        else:
            chi2_stat = float((abs(b - c) - 1) ** 2 / (b + c))
            p_value = float(1 - stats.chi2.cdf(chi2_stat, df=1))
        
        # Odds ratio and confidence interval
        if c == 0:
            odds_ratio = float('inf') if b > 0 else 1.0
            ci_lower = float('nan')
            ci_upper = float('inf')
        elif b == 0:
            odds_ratio = 0.0
            ci_lower = 0.0
            ci_upper = float('nan')
        else:
            odds_ratio = float(b / c)
            # Log odds ratio confidence interval
            log_or = np.log(odds_ratio)
            se_log_or = np.sqrt(1/b + 1/c)
            z = stats.norm.ppf(1 - alpha/2)
            ci_lower = float(np.exp(log_or - z * se_log_or))
            ci_upper = float(np.exp(log_or + z * se_log_or))
        
        # Determine winner
        significant = p_value < alpha
        if significant:
            winner = "A" if b > c else "B"
        else:
            winner = None
        
        results.append(McNemarResult(
            class_idx=class_idx,
            class_name=class_names[class_idx],
            b=b,
            c=c,
            statistic=chi2_stat,
            p_value=p_value,
            odds_ratio=odds_ratio,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            significant=significant,
            alpha=alpha,
            winner=winner
        ))
    
    return results


# =============================================================================
# Cohen's Kappa
# =============================================================================

def cohens_kappa(
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    num_classes: int,
    alpha: float = 0.05
) -> KappaResult:
    """
    Compute Cohen's Kappa for inter-model agreement.
    
    Kappa measures agreement between two raters (models) beyond chance:
        κ = (P_o - P_e) / (1 - P_e)
    
    where P_o is observed agreement and P_e is expected agreement by chance.
    
    Interpretation (Landis & Koch, 1977):
        < 0.00: Poor
        0.00-0.20: Slight
        0.21-0.40: Fair
        0.41-0.60: Moderate
        0.61-0.80: Substantial
        0.81-1.00: Almost Perfect
    
    Args:
        pred_a: Predictions from model A
        pred_b: Predictions from model B
        num_classes: Number of classes
        alpha: Significance level for CI (default 0.05)
        
    Returns:
        KappaResult with kappa, standard error, CI, and interpretation
    """
    if pred_a is None or pred_b is None:
        raise ValueError("Prediction arrays cannot be None")
    
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    
    if len(pred_a) == 0:
        raise ValueError("Prediction arrays cannot be empty")
    
    if len(pred_a) != len(pred_b):
        raise ValueError(
            f"Prediction arrays must have same length. "
            f"Got pred_a={len(pred_a)}, pred_b={len(pred_b)}"
        )
    
    if num_classes < 2:
        raise ValueError(f"num_classes must be >= 2, got {num_classes}")
    
    n = len(pred_a)
    
    # Build agreement matrix
    agreement_matrix = np.zeros((num_classes, num_classes), dtype=np.float64)
    for a, b in zip(pred_a, pred_b):
        if 0 <= a < num_classes and 0 <= b < num_classes:
            agreement_matrix[a, b] += 1
    
    # Observed agreement
    p_o = float(np.trace(agreement_matrix) / n)
    
    # Expected agreement
    marginal_a = agreement_matrix.sum(axis=1) / n
    marginal_b = agreement_matrix.sum(axis=0) / n
    p_e = float(np.sum(marginal_a * marginal_b))
    
    # Kappa
    if p_e == 1.0:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = float((p_o - p_e) / (1 - p_e))
    
    # Standard error (using the formula from Fleiss et al.)
    # SE = sqrt(p_o * (1 - p_o) / (n * (1 - p_e)^2))
    if p_e == 1.0 or n == 0:
        se = 0.0
    else:
        se = float(np.sqrt(p_o * (1 - p_o) / (n * (1 - p_e) ** 2)))
    
    # Confidence interval
    z = stats.norm.ppf(1 - alpha/2)
    ci_lower = float(kappa - z * se)
    ci_upper = float(kappa + z * se)
    
    # P-value (test H0: kappa = 0)
    if se > 0:
        z_stat = kappa / se
        p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
    else:
        p_value = 0.0 if kappa != 0 else 1.0
    
    # Interpretation
    if kappa < 0:
        interpretation = "Poor (less than chance)"
    elif kappa < 0.20:
        interpretation = "Slight"
    elif kappa < 0.40:
        interpretation = "Fair"
    elif kappa < 0.60:
        interpretation = "Moderate"
    elif kappa < 0.80:
        interpretation = "Substantial"
    else:
        interpretation = "Almost Perfect"
    
    return KappaResult(
        kappa=kappa,
        std_error=se,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        p_value=p_value,
        agreement_observed=p_o,
        agreement_expected=p_e,
        interpretation=interpretation
    )


# =============================================================================
# Reporting
# =============================================================================

def print_multivariate_report(
    stuart_maxwell: StuartMaxwellResult,
    mcnemar_results: List[McNemarResult],
    kappa_result: KappaResult,
    model_a_name: str = "Model A",
    model_b_name: str = "Model B"
) -> None:
    """
    Print a formatted report of multivariate comparison results.
    
    Args:
        stuart_maxwell: Stuart-Maxwell test result
        mcnemar_results: List of per-class McNemar results
        kappa_result: Cohen's Kappa result
        model_a_name: Display name for model A
        model_b_name: Display name for model B
    """
    print(f"\n{'='*70}")
    print(f"MULTIVARIATE MODEL COMPARISON: {model_a_name} vs {model_b_name}")
    print(f"{'='*70}")
    
    # Stuart-Maxwell
    print(f"\n--- Stuart-Maxwell Test (Marginal Homogeneity) ---")
    print(f"χ² statistic: {stuart_maxwell.statistic:.4f}")
    print(f"Degrees of freedom: {stuart_maxwell.df}")
    print(f"p-value: {stuart_maxwell.p_value:.4f}")
    print(f"Significant at α={stuart_maxwell.alpha}: {'Yes' if stuart_maxwell.significant else 'No'}")
    
    print(f"\nMarginal differences (A - B):")
    for i, diff in enumerate(stuart_maxwell.marginal_diff):
        print(f"  Class {i}: {diff:+d}")
    
    # McNemar's Tests
    print(f"\n--- McNemar's Tests (Per-Class) ---")
    print(f"{'Class':<15} {'b':>6} {'c':>6} {'χ²':>8} {'p-value':>10} {'Winner':>10}")
    print("-" * 60)
    
    for r in mcnemar_results:
        winner_str = r.winner if r.winner else "—"
        print(f"{r.class_name:<15} {r.b:>6} {r.c:>6} {r.statistic:>8.2f} "
              f"{r.p_value:>10.4f} {winner_str:>10}")
    
    # Cohen's Kappa
    print(f"\n--- Cohen's Kappa (Inter-Model Agreement) ---")
    print(f"κ = {kappa_result.kappa:.4f}")
    print(f"Standard Error: {kappa_result.std_error:.4f}")
    print(f"95% CI: [{kappa_result.ci_lower:.4f}, {kappa_result.ci_upper:.4f}]")
    print(f"p-value: {kappa_result.p_value:.4f}")
    print(f"Observed Agreement: {kappa_result.agreement_observed:.4f}")
    print(f"Expected Agreement: {kappa_result.agreement_expected:.4f}")
    print(f"Interpretation: {kappa_result.interpretation}")
