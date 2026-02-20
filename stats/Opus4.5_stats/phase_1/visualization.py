"""
Visualization Functions for Phase 1 Statistical Analysis
=========================================================

Provides plotting functions for:
    - Confusion matrices
    - Per-class F1 score comparisons
    - Contingency tables
    - Marginal differences
    - Effect sizes (Cohen's d)
    - McNemar test results

All plots use matplotlib/seaborn with consistent styling.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

from .univariate import UnivariateResults
from .multivariate import StuartMaxwellResult, McNemarResult
from .paired_tests import PairedTestResult


# =============================================================================
# Style Configuration
# =============================================================================

def set_style() -> None:
    """
    Set consistent plot style.
    
    Attempts to use seaborn style with fallback for different matplotlib versions.
    """
    style_options = [
        'seaborn-v0_8-whitegrid',  # matplotlib >= 3.6
        'seaborn-whitegrid',        # matplotlib < 3.6
        'ggplot',                   # fallback
    ]
    
    for style in style_options:
        try:
            plt.style.use(style)
            return
        except OSError:
            continue
    
    # If all fail, use default
    pass


# =============================================================================
# Confusion Matrix Visualization
# =============================================================================

def plot_confusion_matrix(
    results: UnivariateResults,
    model_name: str = "Model",
    normalize: bool = False,
    figsize: Tuple[int, int] = (8, 6),
    cmap: str = "Blues",
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot confusion matrix as a heatmap.
    
    Args:
        results: UnivariateResults containing confusion matrix
        model_name: Name for plot title
        normalize: If True, show percentages instead of counts
        figsize: Figure size (width, height)
        cmap: Colormap name
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    cm = results.confusion_matrix.copy()
    if normalize:
        cm = cm.astype(float)
        row_sums = cm.sum(axis=1, keepdims=True)
        cm = np.divide(cm, row_sums, where=row_sums != 0)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if HAS_SEABORN:
        fmt = ".2%" if normalize else "d"
        sns.heatmap(
            cm,
            annot=True,
            fmt=fmt,
            cmap=cmap,
            xticklabels=results.class_names,
            yticklabels=results.class_names,
            ax=ax
        )
    else:
        im = ax.imshow(cm, cmap=cmap)
        plt.colorbar(im, ax=ax)
        
        # Add text annotations
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                text = f"{val:.2%}" if normalize else f"{int(val)}"
                ax.text(j, i, text, ha='center', va='center', color='black')
        
        ax.set_xticks(range(len(results.class_names)))
        ax.set_yticks(range(len(results.class_names)))
        ax.set_xticklabels(results.class_names)
        ax.set_yticklabels(results.class_names)
    
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix: {model_name}")
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# F1 Score Comparison
# =============================================================================

def plot_f1_comparison(
    results_a: UnivariateResults,
    results_b: UnivariateResults,
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot per-class F1 score comparison between two models.
    
    Args:
        results_a: UnivariateResults for model A
        results_b: UnivariateResults for model B
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    class_names = results_a.class_names
    x = np.arange(len(class_names))
    width = 0.35
    
    f1_a = [results_a.f1[i] for i in range(len(class_names))]
    f1_b = [results_b.f1[i] for i in range(len(class_names))]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    bars_a = ax.bar(x - width/2, f1_a, width, label=model_a_name, color='steelblue')
    bars_b = ax.bar(x + width/2, f1_b, width, label=model_b_name, color='coral')
    
    # Add value labels on bars
    for bar in bars_a:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    
    for bar in bars_b:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel("Class")
    ax.set_ylabel("F1 Score")
    ax.set_title(f"Per-Class F1 Comparison: {model_a_name} vs {model_b_name}")
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.axhline(y=0.75, color='red', linestyle='--', alpha=0.5, label='F1 Floor (0.75)')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# Contingency Table Visualization
# =============================================================================

def plot_contingency_table(
    contingency_table: np.ndarray,
    class_names: List[str],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    figsize: Tuple[int, int] = (12, 6),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot contingency table as a heatmap.
    
    Args:
        contingency_table: Table from build_contingency_table (4 x num_classes)
        class_names: List of class names
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    row_labels = [
        f"Both correct",
        f"{model_a_name} ✓, {model_b_name} ✗",
        f"{model_a_name} ✗, {model_b_name} ✓",
        f"Both incorrect"
    ]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if HAS_SEABORN:
        sns.heatmap(
            contingency_table,
            annot=True,
            fmt="d",
            cmap="YlOrRd",
            xticklabels=class_names,
            yticklabels=row_labels,
            ax=ax
        )
    else:
        im = ax.imshow(contingency_table, cmap="YlOrRd", aspect='auto')
        plt.colorbar(im, ax=ax)
        
        for i in range(contingency_table.shape[0]):
            for j in range(contingency_table.shape[1]):
                ax.text(j, i, str(int(contingency_table[i, j])),
                        ha='center', va='center', color='black')
        
        ax.set_xticks(range(len(class_names)))
        ax.set_yticks(range(len(row_labels)))
        ax.set_xticklabels(class_names)
        ax.set_yticklabels(row_labels)
    
    ax.set_xlabel("Class")
    ax.set_title(f"Contingency Table: {model_a_name} vs {model_b_name}")
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# Marginal Differences Plot
# =============================================================================

def plot_marginal_differences(
    stuart_maxwell_result: StuartMaxwellResult,
    class_names: List[str],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot marginal differences from Stuart-Maxwell test.
    
    Args:
        stuart_maxwell_result: StuartMaxwellResult with marginal data
        class_names: List of class names
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    x = np.arange(len(class_names))
    width = 0.35
    
    # Left plot: Marginal counts
    ax1 = axes[0]
    ax1.bar(x - width/2, stuart_maxwell_result.marginal_a, width,
            label=model_a_name, color='steelblue')
    ax1.bar(x + width/2, stuart_maxwell_result.marginal_b, width,
            label=model_b_name, color='coral')
    ax1.set_xlabel("Class")
    ax1.set_ylabel("Count")
    ax1.set_title("Marginal Prediction Counts")
    ax1.set_xticks(x)
    ax1.set_xticklabels(class_names)
    ax1.legend()
    
    # Right plot: Differences
    ax2 = axes[1]
    colors = ['green' if d > 0 else 'red' for d in stuart_maxwell_result.marginal_diff]
    ax2.bar(x, stuart_maxwell_result.marginal_diff, color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_xlabel("Class")
    ax2.set_ylabel(f"Difference ({model_a_name} - {model_b_name})")
    ax2.set_title("Marginal Differences")
    ax2.set_xticks(x)
    ax2.set_xticklabels(class_names)
    
    # Add significance annotation
    sig_text = "Significant" if stuart_maxwell_result.significant else "Not significant"
    fig.suptitle(f"Stuart-Maxwell Test: p={stuart_maxwell_result.p_value:.4f} ({sig_text})",
                 fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# Cohen's d Effect Size Plot
# =============================================================================

def plot_cohens_d_effect_sizes(
    paired_results: List[PairedTestResult],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot Cohen's d effect sizes for each class.
    
    Args:
        paired_results: List of PairedTestResult from paired tests
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    class_names = [r.class_name for r in paired_results]
    d_values = [r.cohens_d for r in paired_results]
    significant = [r.significant_corrected for r in paired_results]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(class_names))
    colors = ['darkgreen' if s else 'gray' for s in significant]
    
    bars = ax.barh(x, d_values, color=colors, alpha=0.7)
    
    # Add reference lines for effect size thresholds
    for threshold, label in [(0.2, 'Small'), (0.5, 'Medium'), (0.8, 'Large')]:
        ax.axvline(x=threshold, color='blue', linestyle='--', alpha=0.3)
        ax.axvline(x=-threshold, color='blue', linestyle='--', alpha=0.3)
    
    ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
    
    ax.set_yticks(x)
    ax.set_yticklabels(class_names)
    ax.set_xlabel(f"Cohen's d (positive favors {model_a_name})")
    ax.set_title(f"Effect Sizes: {model_a_name} vs {model_b_name}")
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='darkgreen', alpha=0.7, label='Significant (BH corrected)'),
        Patch(facecolor='gray', alpha=0.7, label='Not significant')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# McNemar's Test Results Plot
# =============================================================================

def plot_mcnemar_results(
    mcnemar_results: List[McNemarResult],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot McNemar's test results showing discordant pairs.
    
    Args:
        mcnemar_results: List of McNemarResult from McNemar tests
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        figsize: Figure size
        save_path: Optional path to save figure
        
    Returns:
        matplotlib Figure object
    """
    set_style()
    
    class_names = [r.class_name for r in mcnemar_results]
    b_values = [r.b for r in mcnemar_results]  # A correct, B incorrect
    c_values = [r.c for r in mcnemar_results]  # A incorrect, B correct
    significant = [r.significant for r in mcnemar_results]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(class_names))
    width = 0.35
    
    bars_b = ax.bar(x - width/2, b_values, width,
                    label=f'{model_a_name} ✓, {model_b_name} ✗',
                    color='steelblue')
    bars_c = ax.bar(x + width/2, c_values, width,
                    label=f'{model_a_name} ✗, {model_b_name} ✓',
                    color='coral')
    
    # Mark significant comparisons
    for i, sig in enumerate(significant):
        if sig:
            max_val = max(b_values[i], c_values[i])
            ax.annotate('*', xy=(i, max_val + 2), ha='center', fontsize=16, fontweight='bold')
    
    ax.set_xlabel("Class")
    ax.set_ylabel("Count (Discordant Pairs)")
    ax.set_title(f"McNemar's Test: Discordant Pairs")
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


# =============================================================================
# Combined Plot Generation
# =============================================================================

def create_all_plots(
    results_a: UnivariateResults,
    results_b: UnivariateResults,
    contingency_table: np.ndarray,
    stuart_maxwell_result: StuartMaxwellResult,
    mcnemar_results: List[McNemarResult],
    paired_results: List[PairedTestResult],
    model_a_name: str = "Model A",
    model_b_name: str = "Model B",
    output_dir: Optional[str] = None,
    show_plots: bool = True
) -> Dict[str, plt.Figure]:
    """
    Create all visualization plots.
    
    Args:
        results_a: UnivariateResults for model A
        results_b: UnivariateResults for model B
        contingency_table: Contingency table from build_contingency_table
        stuart_maxwell_result: Stuart-Maxwell test result
        mcnemar_results: List of McNemar test results
        paired_results: List of paired t-test results
        model_a_name: Display name for model A
        model_b_name: Display name for model B
        output_dir: Optional directory to save plots
        show_plots: Whether to display plots (default True)
        
    Returns:
        Dictionary mapping plot names to Figure objects
    """
    import os
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    def get_save_path(name: str) -> Optional[str]:
        if output_dir:
            return os.path.join(output_dir, f"{name}.png")
        return None
    
    figures = {}
    
    # Confusion matrices
    figures['confusion_matrix_a'] = plot_confusion_matrix(
        results_a, model_a_name,
        save_path=get_save_path(f"confusion_matrix_{model_a_name.lower().replace(' ', '_')}")
    )
    
    figures['confusion_matrix_b'] = plot_confusion_matrix(
        results_b, model_b_name,
        save_path=get_save_path(f"confusion_matrix_{model_b_name.lower().replace(' ', '_')}")
    )
    
    # F1 comparison
    figures['f1_comparison'] = plot_f1_comparison(
        results_a, results_b, model_a_name, model_b_name,
        save_path=get_save_path("f1_comparison")
    )
    
    # Contingency table
    figures['contingency_table'] = plot_contingency_table(
        contingency_table, results_a.class_names, model_a_name, model_b_name,
        save_path=get_save_path("contingency_table")
    )
    
    # Marginal differences
    figures['marginal_differences'] = plot_marginal_differences(
        stuart_maxwell_result, results_a.class_names, model_a_name, model_b_name,
        save_path=get_save_path("marginal_differences")
    )
    
    # Cohen's d effect sizes
    figures['effect_sizes'] = plot_cohens_d_effect_sizes(
        paired_results, model_a_name, model_b_name,
        save_path=get_save_path("effect_sizes")
    )
    
    # McNemar results
    figures['mcnemar_results'] = plot_mcnemar_results(
        mcnemar_results, model_a_name, model_b_name,
        save_path=get_save_path("mcnemar_results")
    )
    
    if show_plots:
        plt.show()
    
    return figures
