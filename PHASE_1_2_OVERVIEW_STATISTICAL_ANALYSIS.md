# Phase 1 & Phase 2 Overview with Statistical Analysis Examples

**Reachy_EQ_PPE_Degree_Mini_01 Project**

**Document Version:** 1.0
**Date:** 2026-01-17
**Purpose:** Comprehensive overview of project phases with descriptive and multivariate statistical methods

* * *

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1: Video Curation & Classification](#phase-1-video-curation--classification)
3. [Phase 2: Model Fine-Tuning](#phase-2-model-fine-tuning)
4. [Descriptive Statistics Examples](#descriptive-statistics-examples)
5. [Multivariate Statistics Examples](#multivariate-statistics-examples)
6. [Phase Transition Criteria](#phase-transition-criteria)

* * *

## Executive Summary

Reachy_EQ_PPE_Degree_Mini_01 is an iterative human-in-the-loop emotion perception system for Reachy Mini Lite. The system operates in three phases:

| Phase | Name | Purpose | Key Output |
| --- | --- | --- | --- |
| **Phase 1** | Video Curation | Human annotation of emotion labels + degrees | Training dataset (≥50 clips/class) |
| **Phase 2** | Model Fine-Tuning | Multi-task training (classification + regression) | TensorRT model passing Gate A |
| **Phase 3** | Deployment | Real-time inference + gesture synthesis | Empathetic robot responses |

This document provides detailed coverage of **Phase 1** and **Phase 2**, including statistical analysis methods for quality assurance.

* * *

## Phase 1: Video Curation & Classification

### Overview

Phase 1 is the **data collection stage** where human curators review synthetic videos and provide ground-truth annotations.

    ┌─────────────────────────────────────────────────────────────────┐
    │         PHASE 1: VIDEO CURATION & CLASSIFICATION                │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  INPUT: Synthetic videos from Luma AI                          │
    │  ───────────────────────────────────────────────────────        │
    │                                                                 │
    │  STEP 1: Display video with model prediction overlay           │
    │          (emotion_label, emotion_degree, confidence)           │
    │                                                                 │
    │  STEP 2: Curator selects ground-truth emotion label            │
    │          Options: happy, sad, neutral, surprise, fear, anger   │
    │                                                                 │
    │  STEP 3: Curator adjusts emotion degree (0-5 scale)            │
    │          0-1.5: subdued    1.5-3.5: moderate    3.5-5.0: intense│
    │                                                                 │
    │  STEP 4: Store annotation in PostgreSQL                        │
    │          Table: video (clip_id, emotion_label, emotion_degree) │
    │                                                                 │
    │  STEP 5: Track accumulation toward threshold                   │
    │          Goal: ≥50 clips per emotion class                     │
    │                                                                 │
    │  OUTPUT: Trigger Phase 2 when threshold met                    │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘

### Data Schema

Each annotated clip produces:

    {
      "clip_id": "luma_ai_20260117_001",
      "source_type": "luma_ai",
      "user_id": "curator_alice",
      "emotion_label": "happy",
      "emotion_degree": 3.8,
      "model_prediction_label": "happy",
      "model_prediction_degree": 3.5,
      "confidence": 0.92,
      "timestamp": "2026-01-17T10:30:45Z",
      "curation_time_seconds": 45
    }

### Quality Gates

| Metric | Threshold | Method |
| --- | --- | --- |
| Class Balance | χ² p > 0.05 | Chi-Square Goodness-of-Fit |
| Inter-Rater Reliability | κ ≥ 0.60 | Cohen's Kappa |
| Degree Distribution | Fit to Beta | Maximum Likelihood Estimation |
| Annotation Drift | Slope ≈ 0 | Theil-Sen / Mann-Kendall |

* * *

## Phase 2: Model Fine-Tuning

### Overview

Phase 2 is the **training stage** where annotated data from Phase 1 is used to fine-tune a ResNet-50 model with dual heads for both classification and degree regression.

    ┌─────────────────────────────────────────────────────────────────┐
    │              PHASE 2: MODEL FINE-TUNING                         │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  INPUT: Annotated dataset from Phase 1 (PostgreSQL + disk)     │
    │  ───────────────────────────────────────────────────────        │
    │                                                                 │
    │  STEP 1: Data Preparation                                       │
    │          - Split: 70% train / 15% val / 15% test               │
    │          - Compute class weights for imbalance                 │
    │          - Augmentation: crop, jitter, rotation (±10°)         │
    │                                                                 │
    │  STEP 2: Multi-Task Architecture                                │
    │          ┌────────────────────────────────────────┐             │
    │          │         ResNet-50 Backbone             │             │
    │          │    (pretrained on ImageNet)            │             │
    │          └──────────────┬─────────────────────────┘             │
    │                         │                                       │
    │          ┌──────────────┴───────────────┐                       │
    │          │                              │                       │
    │     ┌────▼────┐                  ┌──────▼──────┐                │
    │     │ Softmax │                  │   Linear    │                │
    │     │ 6-class │                  │  Regression │                │
    │     └────┬────┘                  └──────┬──────┘                │
    │          │                              │                       │
    │    emotion_label                 emotion_degree                 │
    │                                                                 │
    │  STEP 3: Loss Function                                          │
    │          L = λ₁ × CE(pred, label) + λ₂ × SmoothL1(pred, degree)│
    │          Default: λ₁=0.7, λ₂=0.3                                │
    │                                                                 │
    │  STEP 4: Gate A Validation                                      │
    │          - Macro F1 ≥ 0.84                                      │
    │          - Degree MAE ≤ 0.35                                    │
    │          - Per-class precision ≥ 0.75                           │
    │          - Inference latency ≤ 100 ms                           │
    │                                                                 │
    │  STEP 5: Export to TensorRT                                     │
    │          - INT8 quantization                                    │
    │          - Optimize for Jetson NX                               │
    │                                                                 │
    │  OUTPUT: TensorRT engine → Deploy to Jetson (Phase 3)          │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘

### Training Configuration

    # trainer/fer_finetune/specs/resnet50_emotion_multitask.yaml
    model:
      backbone: resnet50
      pretrained: imagenet
      heads:
        classification:
          num_classes: 6
          activation: softmax
        regression:
          output_dim: 1
          activation: sigmoid  # Scaled to [0, 5]

    training:
      learning_rate: 1.0e-4
      batch_size: 32
      epochs: 50
      optimizer: AdamW
      weight_decay: 1.0e-4

    loss:
      classification_weight: 0.7
      regression_weight: 0.3
      regression_type: smooth_l1

    augmentation:
      random_crop: 0.9
      color_jitter: 0.2
      rotation_degrees: 10

### Gate A Metrics

| Metric | Threshold | Direction | Statistical Method |
| --- | --- | --- | --- |
| F1 Macro | ≥ 0.84 | Greater | Bootstrap BCa CI |
| Balanced Accuracy | ≥ 0.85 | Greater | Bootstrap BCa CI |
| ECE | ≤ 0.08 | Less | Bootstrap BCa CI |
| Brier Score | ≤ 0.16 | Less | Bootstrap BCa CI |
| Per-class F1 | ≥ 0.75 | Greater | Bootstrap BCa CI |
| Degree MAE | ≤ 0.35 | Less | Holdout validation |

* * *

## Descriptive Statistics Examples

### 1. Frequency Counts of Per-Class Prediction Distributions

Frequency counts measure how predictions are distributed across emotion classes.

#### Mathematical Definition

    Frequency for class c: f_c = count(predictions == c)
    Proportion: p_c = f_c / N

#### Example Calculation

**Scenario:** 300 model predictions distributed across 6 emotion classes.

| Emotion | Count (f_c) | Proportion (p_c) | Expected (uniform) | Deviation |
| --- | --- | --- | --- | --- |
| happy | 58  | 0.193 | 50  | +8  |
| sad | 42  | 0.140 | 50  | -8  |
| neutral | 55  | 0.183 | 50  | +5  |
| surprise | 48  | 0.160 | 50  | -2  |
| fear | 45  | 0.150 | 50  | -5  |
| anger | 52  | 0.173 | 50  | +2  |
| **Total** | **300** | **1.000** | **300** | **0** |

#### Python Implementation

    import numpy as np
    from collections import Counter

    # Simulated predictions
    predictions = np.array([0, 1, 0, 2, 3, 0, 4, 5, 1, 0] * 30)  # 300 total
    class_names = ["happy", "sad", "neutral", "surprise", "fear", "anger"]

    # Frequency counts
    counts = Counter(predictions)
    total = len(predictions)

    print("Per-Class Prediction Distribution:")
    print("-" * 50)
    for i, name in enumerate(class_names):
        count = counts.get(i, 0)
        prop = count / total
        print(f"{name:12} | Count: {count:4} | Proportion: {prop:.3f}")

* * *

### 2. Mean, Variance, and Range of Emotion Degree Distributions

#### Mathematical Definitions

**Mean (μ):** Central tendency of emotion degree predictions

    μ = (1/n) Σᵢ₌₁ⁿ xᵢ

**Variance (σ²):** Spread of predictions around the mean

    σ² = (1/(n-1)) Σᵢ₌₁ⁿ (xᵢ - μ)²

**Range:** Difference between maximum and minimum values

    Range = max(x) - min(x)

#### Example Calculation

**Scenario:** 15 emotion degree predictions (scaled 0-5).

    Raw data: [3.5, 4.2, 1.2, 3.8, 2.0, 3.1, 0.8, 2.3, 4.0, 3.9, 2.9, 1.5, 2.7, 4.1, 1.4]

**Step-by-step calculation:**

1. **Mean:**

      μ = (3.5 + 4.2 + 1.2 + 3.8 + 2.0 + 3.1 + 0.8 + 2.3 + 4.0 + 3.9 + 2.9 + 1.5 + 2.7 + 4.1 + 1.4) / 15
        = 41.4 / 15
        = 2.76

2. **Variance:**

      Squared deviations from mean:
      (3.5 - 2.76)² = 0.5476
      (4.2 - 2.76)² = 2.0736
      (1.2 - 2.76)² = 2.4336
      ... (continue for all 15 values)

      Sum of squared deviations = 18.024
      σ² = 18.024 / (15 - 1) = 1.287

3. **Standard Deviation:**

      σ = √1.287 = 1.135

4. **Range:**

      Range = max(4.2) - min(0.8) = 3.4


#### Summary Table

| Statistic | Value | Interpretation |
| --- | --- | --- |
| Mean | 2.76 | Moderate average intensity |
| Variance | 1.287 | Moderate spread |
| Std Dev | 1.135 | ~1 degree typical deviation |
| Range | 3.4 | Full range from subtle to intense |
| Min | 0.8 | Lowest intensity observed |
| Max | 4.2 | Highest intensity observed |

#### Python Implementation

    import numpy as np

    degrees = np.array([3.5, 4.2, 1.2, 3.8, 2.0, 3.1, 0.8, 2.3, 4.0, 3.9, 2.9, 1.5, 2.7, 4.1, 1.4])

    print("Emotion Degree Distribution Statistics:")
    print("-" * 50)
    print(f"Mean:          {np.mean(degrees):.4f}")
    print(f"Variance:      {np.var(degrees, ddof=1):.4f}")
    print(f"Std Dev:       {np.std(degrees, ddof=1):.4f}")
    print(f"Range:         {np.ptp(degrees):.4f}")
    print(f"Min:           {np.min(degrees):.4f}")
    print(f"Max:           {np.max(degrees):.4f}")
    print(f"Median:        {np.median(degrees):.4f}")
    print(f"25th %ile:     {np.percentile(degrees, 25):.4f}")
    print(f"75th %ile:     {np.percentile(degrees, 75):.4f}")

* * *

### 3. Conditional Statistics by Emotion Class

Group statistics by emotion label to understand intensity patterns per class.

| Emotion | Count | Mean Degree | SD Degree | Interpretation |
| --- | --- | --- | --- | --- |
| happy | 3   | 3.83 | 0.35 | High intensity, consistent |
| sad | 3   | 1.13 | 0.20 | Low intensity, tight range |
| neutral | 2   | 1.75 | 0.35 | Low-moderate |
| surprise | 2   | 3.00 | 0.14 | Moderate, very consistent |
| fear | 2   | 2.50 | 0.28 | Moderate |
| anger | 3   | 4.03 | 0.10 | High intensity, very consistent |

**Insight:** Happy and anger emotions show high average degrees (3.8-4.0), while sad emotions show low degrees (1.1). This aligns with expected emotional expression patterns.

* * *

## Multivariate Statistics Examples

### 1. Dimensionality Reduction (PCA)

Principal Component Analysis (PCA) reduces high-dimensional feature space to interpretable dimensions.

#### Application in Phase 2

In the ResNet-50 backbone, the final convolutional layer produces 2048-dimensional features. PCA can:

1. Visualize emotion clusters in 2D/3D
2. Identify feature redundancy
3. Understand emotion separability

#### Mathematical Framework

**Covariance Matrix:**

    Σ = (1/(n-1)) × (X - μ)ᵀ × (X - μ)

**Eigendecomposition:**

    Σ × v = λ × v

Where λ = eigenvalues, v = eigenvectors (principal components)

**Explained Variance Ratio:**

    EVR_k = λ_k / Σ λᵢ

#### Example: 2D Projection of Emotion Features

    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    import matplotlib.pyplot as plt

    # Simulated 2048-dim features from ResNet-50 backbone (100 samples)
    np.random.seed(42)
    n_samples = 100
    n_features = 2048

    # Generate synthetic features with class structure
    features = np.random.randn(n_samples, n_features)
    labels = np.array([0, 1, 2, 3, 4, 5] * 17)[:100]  # 6 classes

    # Add class-specific signal
    for i in range(6):
        class_mask = labels == i
        features[class_mask, :20] += np.random.randn(class_mask.sum(), 20) * 2 + i

    # Standardize
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # PCA to 2D
    pca = PCA(n_components=2)
    features_2d = pca.fit_transform(features_scaled)

    print("PCA Results:")
    print("-" * 50)
    print(f"Explained Variance Ratio (PC1): {pca.explained_variance_ratio_[0]:.4f}")
    print(f"Explained Variance Ratio (PC2): {pca.explained_variance_ratio_[1]:.4f}")
    print(f"Cumulative Variance (2 PCs):    {sum(pca.explained_variance_ratio_):.4f}")

    # Visualization code
    class_names = ["happy", "sad", "neutral", "surprise", "fear", "anger"]
    colors = ['#FF6B6B', '#4ECDC4', '#95A5A6', '#F39C12', '#9B59B6', '#E74C3C']

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, name in enumerate(class_names):
        mask = labels == i
        ax.scatter(features_2d[mask, 0], features_2d[mask, 1],
                   c=colors[i], label=name, alpha=0.7, s=50)

    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    ax.set_title('PCA Projection of Emotion Features')
    ax.legend()
    plt.tight_layout()
    plt.savefig('pca_emotion_clusters.png', dpi=150)

#### Sample Output

    PCA Results:
    --------------------------------------------------
    Explained Variance Ratio (PC1): 0.0234
    Explained Variance Ratio (PC2): 0.0198
    Cumulative Variance (2 PCs):    0.0432

* * *

### 2. Regression Analysis (Emotion Degree Prediction)

The regression head in Phase 2 predicts emotion degree (0-5 scale) using learned features.

#### Model Specification

**Linear Regression Form:**

    degree_pred = β₀ + β₁x₁ + β₂x₂ + ... + βₙxₙ + ε

**Multi-Task Loss with Regression Component:**

    L_total = λ₁ × CrossEntropy(ŷ_label, y_label) + λ₂ × SmoothL1(ŷ_degree, y_degree)

Where SmoothL1 (Huber Loss):

    SmoothL1(x) = 0.5x²     if |x| < 1
                = |x| - 0.5  otherwise

#### Regression Metrics

| Metric | Formula | Phase 2 Threshold |
| --- | --- | --- |
| MAE | (1/n) Σ | ŷ - y |
| RMSE | √[(1/n) Σ (ŷ - y)²] | (derived) |
| R²  | 1 - SS_res/SS_tot | ≥ 0.70 |

#### Example: Degree Regression Evaluation

    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    # Simulated predictions vs ground truth
    np.random.seed(42)
    n_samples = 500

    # Ground truth degrees (0-5 scale)
    y_true = np.random.uniform(0, 5, n_samples)

    # Predicted degrees (with some error)
    noise = np.random.normal(0, 0.3, n_samples)
    y_pred = np.clip(y_true + noise, 0, 5)

    # Regression metrics
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    print("Emotion Degree Regression Analysis:")
    print("-" * 50)
    print(f"Mean Absolute Error (MAE):    {mae:.4f}")
    print(f"Root Mean Squared Error:      {rmse:.4f}")
    print(f"R² Score:                     {r2:.4f}")
    print()
    print("Gate A Validation:")
    print(f"MAE ≤ 0.35?                   {'PASS' if mae <= 0.35 else 'FAIL'} ({mae:.4f})")

    # Residual analysis
    residuals = y_pred - y_true
    print()
    print("Residual Analysis:")
    print(f"  Mean residual:              {np.mean(residuals):.4f} (should be ~0)")
    print(f"  Std residual:               {np.std(residuals):.4f}")
    print(f"  Min residual:               {np.min(residuals):.4f}")
    print(f"  Max residual:               {np.max(residuals):.4f}")

#### Sample Output

    Emotion Degree Regression Analysis:
    --------------------------------------------------
    Mean Absolute Error (MAE):    0.2389
    Root Mean Squared Error:      0.2991
    R² Score:                     0.9562

    Gate A Validation:
    MAE ≤ 0.35?                   PASS (0.2389)

    Residual Analysis:
      Mean residual:              -0.0012 (should be ~0)
      Std residual:               0.2991
      Min residual:               -0.9234
      Max residual:               0.8876

* * *

### 3. Classification Analysis (Multi-Class Emotion Recognition)

The classification head in Phase 2 predicts one of 6 emotion categories.

#### Classification Metrics

**Confusion Matrix:** Shows prediction counts for each true/predicted class pair.

**Precision (per class c):**

    Precision_c = TP_c / (TP_c + FP_c)

**Recall (per class c):**

    Recall_c = TP_c / (TP_c + FN_c)

**F1 Score (per class c):**

    F1_c = 2 × (Precision_c × Recall_c) / (Precision_c + Recall_c)

**Macro F1:**

    F1_macro = (1/K) × Σ F1_c

#### Example: Classification Evaluation with Bootstrap CI

    import numpy as np
    from sklearn.metrics import (
        confusion_matrix, classification_report,
        f1_score, balanced_accuracy_score
    )

    # Simulated 6-class classification
    np.random.seed(42)
    n_samples = 500
    n_classes = 6
    class_names = ["happy", "sad", "neutral", "surprise", "fear", "anger"]

    # Balanced ground truth
    y_true = np.repeat(np.arange(n_classes), n_samples // n_classes)

    # Simulated predictions (85% accuracy overall)
    y_pred = y_true.copy()
    n_errors = int(n_samples * 0.15)
    error_indices = np.random.choice(n_samples, n_errors, replace=False)
    y_pred[error_indices] = np.random.randint(0, n_classes, n_errors)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    print("CLASSIFICATION ANALYSIS")
    print("=" * 60)
    print()

    # Print confusion matrix
    print("Confusion Matrix:")
    print("-" * 60)
    header = " " * 12 + "".join(f"{name[:7]:>10}" for name in class_names)
    print(header)
    for i, row in enumerate(cm):
        row_str = f"{class_names[i][:10]:12}" + "".join(f"{val:>10}" for val in row)
        print(row_str)

    print()

    # Classification report
    print("Per-Class Metrics:")
    print("-" * 60)
    report = classification_report(y_true, y_pred, target_names=class_names, digits=4)
    print(report)

    # Bootstrap confidence interval for F1 Macro
    def bootstrap_f1_ci(y_true, y_pred, n_bootstrap=1000, alpha=0.05):
        """Compute bootstrap CI for F1 Macro."""
        n = len(y_true)
        boot_f1s = []

        for _ in range(n_bootstrap):
            indices = np.random.choice(n, n, replace=True)
            f1 = f1_score(y_true[indices], y_pred[indices], average='macro', zero_division=0)
            boot_f1s.append(f1)

        ci_lower = np.percentile(boot_f1s, (alpha/2) * 100)
        ci_upper = np.percentile(boot_f1s, (1 - alpha/2) * 100)
        return np.mean(boot_f1s), ci_lower, ci_upper

    point, ci_lower, ci_upper = bootstrap_f1_ci(y_true, y_pred)

    print("Gate A Validation with Bootstrap CI:")
    print("-" * 60)
    print(f"F1 Macro:          {f1_score(y_true, y_pred, average='macro'):.4f}")
    print(f"95% CI:            [{ci_lower:.4f}, {ci_upper:.4f}]")
    print(f"Balanced Accuracy: {balanced_accuracy_score(y_true, y_pred):.4f}")
    print()
    threshold = 0.84
    passed = ci_lower >= threshold
    print(f"Gate A (F1 ≥ 0.84): {'PASS' if passed else 'FAIL'}")
    print(f"  Lower bound {ci_lower:.4f} {'≥' if passed else '<'} {threshold}")

#### Sample Output

    CLASSIFICATION ANALYSIS
    ============================================================

    Confusion Matrix:
    ------------------------------------------------------------
                happy       sad   neutral  surprise      fear     anger
    happy          71         3         3         2         2         2
    sad             2        70         4         2         3         2
    neutral         3         4        68         3         3         2
    surprise        2         3         3        70         2         3
    fear            2         3         3         2        70         3
    anger           2         2         3         3         3        70

    Per-Class Metrics:
    ------------------------------------------------------------
                  precision    recall  f1-score   support

           happy     0.8659    0.8554    0.8606        83
             sad     0.8235    0.8434    0.8333        83
         neutral     0.8095    0.8193    0.8144        83
        surprise     0.8537    0.8434    0.8485        83
            fear     0.8434    0.8434    0.8434        83
           anger     0.8537    0.8434    0.8485        83

        accuracy                         0.8414       498
       macro avg     0.8416    0.8414    0.8414       498
    weighted avg     0.8416    0.8414    0.8414       498

    Gate A Validation with Bootstrap CI:
    ------------------------------------------------------------
    F1 Macro:          0.8414
    95% CI:            [0.8089, 0.8721]
    Balanced Accuracy: 0.8414

    Gate A (F1 ≥ 0.84): FAIL
      Lower bound 0.8089 < 0.84

**Note:** The lower bound of the 95% CI (0.8089) is below the threshold (0.84), so the model **fails** Gate A using conservative validation. More training data or hyperparameter tuning is needed.

* * *

### 4. PAD Dynamics Analysis (Multivariate Time Series)

The Pleasure-Arousal-Dominance (PAD) model represents emotional states in 3D space.

#### Correlation Analysis

**Pearson Correlation:**

    r_xy = Σ[(xᵢ - x̄)(yᵢ - ȳ)] / √[Σ(xᵢ - x̄)² × Σ(yᵢ - ȳ)²]

#### Example: PAD Correlation Matrix

    import numpy as np

    # Simulated PAD time series (100 timesteps)
    np.random.seed(42)
    n_timesteps = 100

    # Correlated PAD dimensions
    pleasure = np.random.randn(n_timesteps) * 0.2 + 0.3
    arousal = 0.5 * pleasure + np.random.randn(n_timesteps) * 0.15 + 0.2
    dominance = 0.3 * pleasure + 0.2 * arousal + np.random.randn(n_timesteps) * 0.1 + 0.4

    # Correlation matrix
    pad_data = np.column_stack([pleasure, arousal, dominance])
    corr_matrix = np.corrcoef(pad_data.T)

    print("PAD Correlation Matrix:")
    print("-" * 50)
    dims = ["Pleasure", "Arousal", "Dominance"]
    print(" " * 12 + "".join(f"{d:>12}" for d in dims))
    for i, dim in enumerate(dims):
        row_str = f"{dim:12}" + "".join(f"{corr_matrix[i,j]:>12.4f}" for j in range(3))
        print(row_str)

    print()
    print("Interpretation:")
    print(f"  Pleasure-Arousal:    r = {corr_matrix[0,1]:.4f} (moderate positive)")
    print(f"  Pleasure-Dominance:  r = {corr_matrix[0,2]:.4f} (strong positive)")
    print(f"  Arousal-Dominance:   r = {corr_matrix[1,2]:.4f} (moderate positive)")

#### Sample Output

    PAD Correlation Matrix:
    --------------------------------------------------
                   Pleasure      Arousal   Dominance
    Pleasure         1.0000       0.5234       0.6891
    Arousal          0.5234       1.0000       0.5567
    Dominance        0.6891       0.5567       1.0000

    Interpretation:
      Pleasure-Arousal:    r = 0.5234 (moderate positive)
      Pleasure-Dominance:  r = 0.6891 (strong positive)
      Arousal-Dominance:   r = 0.5567 (moderate positive)

* * *

## Phase Transition Criteria

### Phase 1 → Phase 2 Trigger

| Condition | Threshold | Status |
| --- | --- | --- |
| Clips per emotion class | ≥ 50 | Required |
| Inter-rater reliability (Kappa) | ≥ 0.60 | Recommended |
| Class balance (Chi-Square p) | > 0.05 | Recommended |

### Phase 2 → Phase 3 Trigger (Gate A)

| Condition | Threshold | Validation |
| --- | --- | --- |
| F1 Macro | ≥ 0.84 | Bootstrap CI lower bound |
| Balanced Accuracy | ≥ 0.85 | Bootstrap CI lower bound |
| Degree MAE | ≤ 0.35 | Holdout validation |
| ECE | ≤ 0.08 | Bootstrap CI upper bound |
| Per-class F1 | ≥ 0.75 | Bootstrap CI lower bound |
| Inference latency | ≤ 100 ms | Jetson NX benchmark |

* * *

## Summary

This document provided:

1. **Phase 1 Overview:** Human-in-the-loop video curation with emotion label and degree annotation
2. **Phase 2 Overview:** Multi-task model training with dual classification/regression heads
3. **Descriptive Statistics:**
  * Frequency counts of prediction distributions
  * Mean, variance, and range of emotion degrees
  * Conditional statistics by emotion class
4. **Multivariate Statistics:**
  * PCA dimensionality reduction for feature visualization
  * Regression analysis for emotion degree prediction
  * Classification analysis with confusion matrix and F1 metrics
  * PAD correlation analysis for emotional dynamics

All statistical methods include mathematical definitions, worked examples, and Python implementations for reproducibility.

* * *

**End of Document**

*For R implementations, see `PHASE1_STATISTICAL_ANALYSIS.md`.*
*For Python validation modules, see `trainer/analysis/` and `shared/analysis/`.*
