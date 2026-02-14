"""
Visualization Functions for Phase 1 Statistical Analysis

Implements:
    - Confusion matrix heatmaps
    - Per-class F1 bar charts
    - Contingency table visualization
    - Effect size plots
    - Marginal difference plots
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .univariate import UnivariateResults
from .multivariate import StuartMaxwellResult, McNemarResult, KappaResult
from .paired_tests import PairedTestResult


def set_style():
    """Set consistent plotting style."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: List[str],
    title: str = "Confusion Matrix",
    normalize: bool = False,
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (8, 6)
) -> plt.Figure:
    """
    Plot confusion matrix as heatmap.
    
    Args:
        cm: Confusion matrix
        class_names: List of class names
        title: Plot title
        normalize: Whether to normalize rows
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    if normalize:
        cm_plot = cm.astype('float') / cm.sum(axis=1, keepdims=True)
        fmt = '.2%'
    else:
        cm_plot = cm
        fmt = 'd'
    
    sns.heatmap(
        cm_plot,
        annot=True,
        fmt=fmt,
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        square=True,
        cbar_kws={'label': 'Count' if not normalize else 'Proportion'}
    )
    
    ax.set_xlabel('Predicted Label')
    ax.set_ylabel('True Label')
    ax.set_title(title)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_per_class_f1_comparison(
    base_f1: Dict[str, float],
    ft_f1: Dict[str, float],
    class_names: List[str],
    title: str = "Per-Class F1 Score Comparison",
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot per-class F1 scores comparing base and fine-tuned models.
    
    Args:
        base_f1: Base model F1 scores per class
        ft_f1: Fine-tuned model F1 scores per class
        class_names: List of class names
        title: Plot title
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(class_names))
    width = 0.35
    
    base_scores = [base_f1[c] for c in class_names]
    ft_scores = [ft_f1[c] for c in class_names]
    
    bars1 = ax.bar(x - width/2, base_scores, width, label='Base Model', color='steelblue', alpha=0.8)
    bars2 = ax.bar(x + width/2, ft_scores, width, label='Fine-Tuned', color='darkorange', alpha=0.8)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)
    
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)
    
    # Add Gate A threshold line
    ax.axhline(y=0.75, color='red', linestyle='--', linewidth=2, label='Gate A Floor (0.75)')
    
    ax.set_xlabel('Emotion Class')
    ax.set_ylabel('F1 Score')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.legend()
    ax.set_ylim(0, 1.1)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_contingency_table(
    contingency_table: np.ndarray,
    class_names: List[str],
    title: str = "Model Prediction Contingency Table",
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (8, 6)
) -> plt.Figure:
    """
    Plot contingency table showing prediction agreement between models.
    
    Args:
        contingency_table: K×K contingency table
        class_names: List of class names
        title: Plot title
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    sns.heatmap(
        contingency_table,
        annot=True,
        fmt='d',
        cmap='YlOrRd',
        xticklabels=[f'FT: {c}' for c in class_names],
        yticklabels=[f'Base: {c}' for c in class_names],
        ax=ax,
        square=True,
        cbar_kws={'label': 'Count'}
    )
    
    ax.set_xlabel('Fine-Tuned Model Prediction')
    ax.set_ylabel('Base Model Prediction')
    ax.set_title(title)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_marginal_differences(
    marginal_diffs: Dict[str, int],
    title: str = "Marginal Differences (Stuart-Maxwell)",
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (8, 5)
) -> plt.Figure:
    """
    Plot marginal differences from Stuart-Maxwell test.
    
    Args:
        marginal_diffs: Dict of class_name -> marginal difference
        title: Plot title
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    classes = list(marginal_diffs.keys())
    diffs = list(marginal_diffs.values())
    
    colors = ['green' if d > 0 else ('red' if d < 0 else 'gray') for d in diffs]
    
    bars = ax.bar(classes, diffs, color=colors, alpha=0.7, edgecolor='black')
    
    # Add value labels
    for bar, val in zip(bars, diffs):
        height = bar.get_height()
        ax.annotate(f'{val:+d}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3 if height >= 0 else -12),
                    textcoords="offset points",
                    ha='center', va='bottom' if height >= 0 else 'top',
                    fontsize=11, fontweight='bold')
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_xlabel('Emotion Class')
    ax.set_ylabel('Marginal Difference (Base - FT)')
    ax.set_title(title)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_effect_sizes(
    results: List[PairedTestResult],
    title: str = "Cohen's d Effect Sizes",
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot Cohen's d effect sizes from paired t-tests.
    
    Args:
        results: List of PairedTestResult
        title: Plot title
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    classes = [r.class_name for r in results]
    cohens_d = [r.cohens_d for r in results]
    
    colors = plt.cm.RdYlGn([min(d / 50, 1.0) for d in cohens_d])  # Scale for visualization
    
    bars = ax.barh(classes, cohens_d, color=colors, edgecolor='black', alpha=0.8)
    
    # Add value labels
    for bar, d in zip(bars, cohens_d):
        width = bar.get_width()
        ax.annotate(f'd = {d:.2f}',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=10)
    
    # Add effect size threshold lines
    ax.axvline(x=0.2, color='gray', linestyle=':', linewidth=1, label='Small (0.2)')
    ax.axvline(x=0.8, color='gray', linestyle='--', linewidth=1, label='Large (0.8)')
    
    ax.set_xlabel("Cohen's d")
    ax.set_ylabel('Emotion Class')
    ax.set_title(title)
    ax.legend(loc='lower right')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_mcnemar_comparison(
    results: List[McNemarResult],
    title: str = "McNemar's Test: Error Rate Changes",
    save_path: Optional[Path] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot McNemar's test results showing discordant pairs.
    
    Args:
        results: List of McNemarResult
        title: Plot title
        save_path: Optional path to save figure
        figsize: Figure size
        
    Returns:
        Matplotlib figure
    """
    set_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    classes = [r.class_name for r in results]
    x = np.arange(len(classes))
    width = 0.35
    
    n12 = [r.n_base_correct_ft_incorrect for r in results]  # FT got wrong
    n21 = [r.n_base_incorrect_ft_correct for r in results]  # FT corrected
    
    bars1 = ax.bar(x - width/2, n12, width, label='Base ✓, FT ✗ (FT errors)', 
                   color='salmon', edgecolor='darkred')
    bars2 = ax.bar(x + width/2, n21, width, label='Base ✗, FT ✓ (FT corrections)', 
                   color='lightgreen', edgecolor='darkgreen')
    
    # Add significance markers
    for i, r in enumerate(results):
        if r.reject_null:
            max_height = max(n12[i], n21[i])
            ax.annotate('*', xy=(x[i], max_height), xytext=(0, 5),
                        textcoords="offset points", ha='center', fontsize=16, fontweight='bold')
    
    ax.set_xlabel('Emotion Class')
    ax.set_ylabel('Number of Samples')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def create_all_plots(
    base_results: UnivariateResults,
    ft_results: UnivariateResults,
    sm_result: StuartMaxwellResult,
    mcnemar_results: List[McNemarResult],
    paired_results: List[PairedTestResult],
    output_dir: Path,
    prefix: str = "phase1"
) -> Dict[str, Path]:
    """
    Create all visualization plots and save to output directory.
    
    Args:
        base_results: Univariate results for base model
        ft_results: Univariate results for fine-tuned model
        sm_result: Stuart-Maxwell test result
        mcnemar_results: McNemar test results
        paired_results: Paired t-test results
        output_dir: Directory to save plots
        prefix: Filename prefix
        
    Returns:
        Dict mapping plot name to file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_plots = {}
    
    # Confusion matrices
    path = output_dir / f"{prefix}_confusion_base.png"
    plot_confusion_matrix(base_results.confusion_matrix, base_results.class_names,
                         title="Base Model Confusion Matrix", save_path=path)
    saved_plots['confusion_base'] = path
    plt.close()
    
    path = output_dir / f"{prefix}_confusion_ft.png"
    plot_confusion_matrix(ft_results.confusion_matrix, ft_results.class_names,
                         title="Fine-Tuned Model Confusion Matrix", save_path=path)
    saved_plots['confusion_ft'] = path
    plt.close()
    
    # Per-class F1 comparison
    path = output_dir / f"{prefix}_per_class_f1.png"
    plot_per_class_f1_comparison(base_results.per_class_f1, ft_results.per_class_f1,
                                 base_results.class_names, save_path=path)
    saved_plots['per_class_f1'] = path
    plt.close()
    
    # Contingency table
    path = output_dir / f"{prefix}_contingency.png"
    plot_contingency_table(sm_result.contingency_table, base_results.class_names,
                          save_path=path)
    saved_plots['contingency'] = path
    plt.close()
    
    # Marginal differences
    path = output_dir / f"{prefix}_marginal_diffs.png"
    plot_marginal_differences(sm_result.marginal_differences, save_path=path)
    saved_plots['marginal_diffs'] = path
    plt.close()
    
    # Effect sizes
    path = output_dir / f"{prefix}_effect_sizes.png"
    plot_effect_sizes(paired_results, save_path=path)
    saved_plots['effect_sizes'] = path
    plt.close()
    
    # McNemar comparison
    path = output_dir / f"{prefix}_mcnemar.png"
    plot_mcnemar_comparison(mcnemar_results, save_path=path)
    saved_plots['mcnemar'] = path
    plt.close()
    
    return saved_plots
