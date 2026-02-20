# Tutorial 3: Per-Class Paired t-Tests with Python

## Learning Objectives

By the end of this tutorial, you will understand:
- How to perform paired t-tests using scipy.stats
- Multiple comparison corrections with statsmodels
- Effect size calculations with Python
- Advanced pandas data manipulation for statistical analysis
- Statistical diagnostics and assumption checking

## Statistical Background

### What are Per-Class Paired t-Tests?

After the Stuart-Maxwell test tells you that prediction patterns changed, per-class paired t-tests answer: **"WHICH specific emotion classes improved or degraded?"**

This is crucial for emotion classification because:
- Different emotions have different baseline difficulties
- Fine-tuning might help some emotions while hurting others
- You need to know if critical emotions (like neutral) improved

### The Paired Design

**Why "paired"?** Because we compare the same model evaluated on the same cross-validation folds:

```python
# Example: 5-fold cross-validation results
fold_data = pd.DataFrame({
    'fold': [1, 2, 3, 4, 5],
    'emotion_class': 'anger',
    'base_f1': [0.82, 0.85, 0.79, 0.83, 0.81],      # Base model F1 scores
    'finetuned_f1': [0.87, 0.89, 0.84, 0.88, 0.86]  # Fine-tuned model F1 scores
})

# Each fold is a "pair" - same data, two different models
differences = fold_data['finetuned_f1'] - fold_data['base_f1']
# [0.05, 0.04, 0.05, 0.05, 0.05] - consistently positive!
```

### Multiple Comparisons Problem

**The Problem**: Testing 8 emotion classes means 8 hypothesis tests. By chance alone, we expect 8 × 0.05 = 0.4 false positives at α = 0.05.

**The Solution**: Adjust p-values to control the False Discovery Rate (FDR) or Family-Wise Error Rate (FWER).

## Script Structure and Imports

```python
#!/usr/bin/env python3
"""
Per-Class Paired t-Tests for Emotion Classification Analysis

This script performs paired t-tests on fold-level F1 scores to identify
which emotion classes improved after fine-tuning.
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
from scipy import stats
from statsmodels.stats.multitest import multipletests
```

**Key Libraries**:
- **scipy.stats**: Statistical tests (ttest_rel, shapiro, etc.)
- **statsmodels.stats.multitest**: Multiple comparison corrections
- **pandas**: Data manipulation and grouping operations

## Core Data Structures

### Comprehensive Result Dataclass

```python
@dataclass
class PerClassTestResult:
    """Results for a single emotion class paired t-test."""
    
    class_name: str
    n_folds: int
    
    # Basic statistics
    mean_base: float
    mean_finetuned: float
    mean_difference: float
    std_difference: float
    se_difference: float
    
    # Test statistics
    t_statistic: float
    p_value_raw: float
    p_value_adjusted: Optional[float]
    significant: bool
    df: int
    
    # Confidence interval
    ci_lower: float
    ci_upper: float
    
    # Effect size
    cohens_d: float
    effect_interpretation: str
    
    # Diagnostics
    normality_p: Optional[float]
    outliers: List[int]
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class PerClassAnalysisResult:
    """Complete per-class analysis results."""
    
    # Test parameters
    correction_method: str
    alpha: float
    n_classes_tested: int
    
    # Individual class results
    class_results: Dict[str, PerClassTestResult]
    
    # Summary statistics
    n_improved: int
    n_degraded: int
    n_unchanged: int
    
    # Multiple comparisons info
    fdr_estimate: float
    significant_classes: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)
```

## Core Statistical Implementation

### Enhanced Paired t-Test Function

```python
def perform_paired_ttest(base_scores: np.ndarray, 
                        ft_scores: np.ndarray,
                        class_name: str,
                        alpha: float = 0.05) -> PerClassTestResult:
    """
    Perform enhanced paired t-test for a single emotion class.
    
    Args:
        base_scores: Base model F1 scores across folds
        ft_scores: Fine-tuned model F1 scores across folds
        class_name: Name of emotion class
        alpha: Significance level
        
    Returns:
        PerClassTestResult with comprehensive statistics
    """
    # Input validation
    if len(base_scores) != len(ft_scores):
        raise ValueError(f"Mismatched array lengths: {len(base_scores)} vs {len(ft_scores)}")
    
    if len(base_scores) < 3:
        raise ValueError(f"Insufficient data for class {class_name}: {len(base_scores)} folds")
    
    n_folds = len(base_scores)
    differences = ft_scores - base_scores
    
    # Basic statistics
    mean_base = np.mean(base_scores)
    mean_ft = np.mean(ft_scores)
    mean_diff = np.mean(differences)
    std_diff = np.std(differences, ddof=1)  # Sample standard deviation
    se_diff = std_diff / np.sqrt(n_folds)
    
    # Handle zero variance case
    if std_diff < 1e-10:
        return create_zero_variance_result(class_name, mean_base, mean_ft, n_folds)
    
    # Perform paired t-test
    t_stat, p_value = stats.ttest_rel(ft_scores, base_scores)
    df = n_folds - 1
    
    # Confidence interval for mean difference
    t_critical = stats.t.ppf(1 - alpha/2, df)
    ci_lower = mean_diff - t_critical * se_diff
    ci_upper = mean_diff + t_critical * se_diff
    
    # Effect size (Cohen's d for paired samples)
    cohens_d = mean_diff / std_diff
    effect_interpretation = interpret_cohens_d(cohens_d)
    
    # Statistical diagnostics
    normality_p = None
    if n_folds >= 3:
        try:
            if n_folds <= 50:
                _, normality_p = stats.shapiro(differences)
            else:
                _, normality_p = stats.normaltest(differences)
        except:
            normality_p = None
    
    # Outlier detection using IQR method
    Q1 = np.percentile(differences, 25)
    Q3 = np.percentile(differences, 75)
    IQR = Q3 - Q1
    outlier_mask = (differences < Q1 - 1.5*IQR) | (differences > Q3 + 1.5*IQR)
    outliers = np.where(outlier_mask)[0].tolist()
    
    return PerClassTestResult(
        class_name=class_name,
        n_folds=n_folds,
        mean_base=mean_base,
        mean_finetuned=mean_ft,
        mean_difference=mean_diff,
        std_difference=std_diff,
        se_difference=se_diff,
        t_statistic=t_stat,
        p_value_raw=p_value,
        p_value_adjusted=None,  # Will be filled later
        significant=False,      # Will be updated after correction
        df=df,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cohens_d=cohens_d,
        effect_interpretation=effect_interpretation,
        normality_p=normality_p,
        outliers=outliers
    )

def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"
```

## Multiple Comparison Corrections

### Benjamini-Hochberg Implementation

```python
def apply_multiple_comparison_correction(results: Dict[str, PerClassTestResult],
                                       method: str = "BH",
                                       alpha: float = 0.05) -> Dict[str, PerClassTestResult]:
    """
    Apply multiple comparison correction to p-values.
    
    Args:
        results: Dictionary of per-class test results
        method: Correction method ('BH', 'bonferroni', 'holm')
        alpha: Family-wise error rate
        
    Returns:
        Updated results with adjusted p-values and significance
    """
    # Extract p-values and class names
    class_names = list(results.keys())
    p_values = [results[cls].p_value_raw for cls in class_names]
    
    # Apply correction using statsmodels
    rejected, p_adjusted, alpha_sidak, alpha_bonf = multipletests(
        p_values, alpha=alpha, method=method, returnsorted=False
    )
    
    # Update results with adjusted p-values
    for i, cls in enumerate(class_names):
        results[cls].p_value_adjusted = p_adjusted[i]
        results[cls].significant = rejected[i]
    
    return results

def run_perclass_analysis(df: pd.DataFrame,
                         correction_method: str = "BH",
                         alpha: float = 0.05) -> PerClassAnalysisResult:
    """
    Run complete per-class paired t-test analysis.
    
    Args:
        df: DataFrame with columns ['emotion_class', 'base_score', 'finetuned_score']
        correction_method: Multiple comparison correction method
        alpha: Significance level
        
    Returns:
        PerClassAnalysisResult with comprehensive analysis
    """
    # Validate input data
    required_cols = ['emotion_class', 'base_score', 'finetuned_score']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check for missing emotion classes
    present_classes = set(df['emotion_class'].unique())
    missing_classes = set(EMOTION_CLASSES) - present_classes
    if missing_classes:
        print(f"Warning: Missing data for classes: {missing_classes}")
    
    # Run tests for each emotion class
    class_results = {}
    
    for cls in EMOTION_CLASSES:
        class_data = df[df['emotion_class'] == cls]
        
        if len(class_data) < 3:
            print(f"Warning: Insufficient data for {cls}: {len(class_data)} folds")
            continue
        
        base_scores = class_data['base_score'].values
        ft_scores = class_data['finetuned_score'].values
        
        try:
            result = perform_paired_ttest(base_scores, ft_scores, cls, alpha)
            class_results[cls] = result
        except Exception as e:
            print(f"Error processing {cls}: {e}")
            continue
    
    # Apply multiple comparison correction
    if class_results:
        class_results = apply_multiple_comparison_correction(
            class_results, correction_method, alpha
        )
    
    # Compute summary statistics
    n_improved = sum(1 for r in class_results.values() 
                    if r.significant and r.mean_difference > 0)
    n_degraded = sum(1 for r in class_results.values() 
                    if r.significant and r.mean_difference < 0)
    n_unchanged = len(class_results) - n_improved - n_degraded
    
    significant_classes = [cls for cls, r in class_results.items() if r.significant]
    
    # Estimate FDR
    n_significant = len(significant_classes)
    fdr_estimate = (n_significant * alpha) / len(class_results) if class_results else 0
    
    return PerClassAnalysisResult(
        correction_method=correction_method,
        alpha=alpha,
        n_classes_tested=len(class_results),
        class_results=class_results,
        n_improved=n_improved,
        n_degraded=n_degraded,
        n_unchanged=n_unchanged,
        fdr_estimate=fdr_estimate,
        significant_classes=significant_classes
    )
```

## Enhanced Reporting

### Comprehensive Console Output

```python
def print_perclass_report(result: PerClassAnalysisResult) -> None:
    """Print comprehensive per-class analysis report."""
    
    print("=" * 80)
    print("PER-CLASS PAIRED T-TESTS ANALYSIS")
    print("=" * 80)
    
    # Summary
    print(f"\n--- ANALYSIS SUMMARY ---")
    print(f"Correction Method: {result.correction_method}")
    print(f"Significance Level: {result.alpha}")
    print(f"Classes Tested: {result.n_classes_tested}")
    print(f"Significant Changes: {len(result.significant_classes)}")
    print(f"Estimated FDR: {result.fdr_estimate:.1%}")
    
    # Outcome summary
    print(f"\n--- OUTCOME SUMMARY ---")
    print(f"Improved Classes: {result.n_improved}")
    print(f"Degraded Classes: {result.n_degraded}")
    print(f"Unchanged Classes: {result.n_unchanged}")
    
    if result.significant_classes:
        print(f"Significant Classes: {', '.join(result.significant_classes)}")
    
    # Detailed results table
    print(f"\n--- DETAILED RESULTS ---")
    header = f"{'Class':<12} {'N':<4} {'Base':<8} {'FT':<8} {'Diff':<8} {'t-stat':<8} {'p-raw':<10} {'p-adj':<10} {'Sig':<5} {'Effect':<8}"
    print(header)
    print("-" * len(header))
    
    # Sort by adjusted p-value for easier interpretation
    sorted_results = sorted(result.class_results.items(), 
                          key=lambda x: x[1].p_value_adjusted or 1)
    
    for cls, res in sorted_results:
        sig_marker = "YES" if res.significant else "no"
        direction = "↑" if res.mean_difference > 0 else "↓" if res.mean_difference < 0 else ""
        neutral_marker = "★" if cls == NEUTRAL_CLASS else ""
        
        print(f"{cls:<12} {res.n_folds:<4} {res.mean_base:<8.4f} {res.mean_finetuned:<8.4f} "
              f"{res.mean_difference:+8.4f} {res.t_statistic:<8.3f} {res.p_value_raw:<10.6f} "
              f"{res.p_value_adjusted:<10.6f} {sig_marker:<3}{direction:<2} {res.effect_interpretation:<8} {neutral_marker}")
```

## Demo Data Generation

### Realistic Fold-Level Metrics

```python
def generate_demo_fold_metrics(n_folds: int = 10,
                              effect_pattern: str = "mixed",
                              seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic fold-level metrics for demo purposes.
    
    Args:
        n_folds: Number of cross-validation folds
        effect_pattern: Pattern of effects ('none', 'all_improve', 'mixed', 'realistic')
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with fold-level metrics
    """
    np.random.seed(seed)
    
    print(f"Generating demo fold metrics: n_folds={n_folds}, pattern={effect_pattern}")
    
    # Base performance levels (realistic for emotion classification)
    base_means = {
        'anger': 0.82, 'contempt': 0.65, 'disgust': 0.72, 'fear': 0.78,
        'happiness': 0.90, 'neutral': 0.88, 'sadness': 0.84, 'surprise': 0.80
    }
    
    # Effect patterns for different scenarios
    effect_patterns = {
        'none': {cls: 0.0 for cls in EMOTION_CLASSES},
        'all_improve': {cls: 0.05 for cls in EMOTION_CLASSES},
        'mixed': {
            'anger': 0.02, 'contempt': 0.08, 'disgust': 0.06, 'fear': 0.03,
            'happiness': -0.02, 'neutral': 0.04, 'sadness': 0.01, 'surprise': 0.02
        },
        'realistic': {
            'anger': 0.015, 'contempt': 0.12, 'disgust': 0.08, 'fear': 0.025,
            'happiness': -0.015, 'neutral': 0.06, 'sadness': 0.02, 'surprise': 0.03
        }
    }
    
    effects = effect_patterns[effect_pattern]
    
    # Generate correlated fold-level metrics
    fold_std = 0.03
    correlation = 0.3  # Moderate correlation between base and fine-tuned
    
    records = []
    
    for cls in EMOTION_CLASSES:
        base_mean = base_means[cls]
        ft_mean = base_mean + effects[cls]
        
        # Generate correlated random effects
        cov_matrix = np.array([[1, correlation], [correlation, 1]]) * (fold_std ** 2)
        fold_effects = np.random.multivariate_normal([0, 0], cov_matrix, n_folds)
        
        # Ensure scores stay in [0, 1] range
        base_scores = np.clip(base_mean + fold_effects[:, 0], 0, 1)
        ft_scores = np.clip(ft_mean + fold_effects[:, 1], 0, 1)
        
        for fold in range(n_folds):
            records.append({
                'fold': fold + 1,
                'emotion_class': cls,
                'base_score': base_scores[fold],
                'finetuned_score': ft_scores[fold]
            })
    
    return pd.DataFrame(records)
```

## Key Takeaways

1. **Paired design is crucial**: Same folds for both models ensure valid comparisons
2. **Multiple comparisons matter**: Always adjust p-values when testing multiple classes
3. **Effect sizes provide context**: Statistical significance without practical importance is misleading
4. **scipy.stats is comprehensive**: Robust implementations of statistical tests
5. **pandas excels at data manipulation**: Grouping and reshaping for statistical analysis

## Next Steps

- **Tutorial 4**: Learn how to integrate all three analyses into a complete workflow
- **Practice**: Run with your own fold-level metrics
- **Real Analysis**: Apply to actual model comparison studies

Per-class paired t-tests are your precision tool for identifying exactly which emotions benefited from fine-tuning!
