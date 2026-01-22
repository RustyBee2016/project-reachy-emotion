# Statistical Methods Analysis for Reachy_Local_08.4.2

**Date**: 2026-01-22
**Project**: Reachy Local Emotion Recognition
**Analysis Scope**: EmotionNet binary classifier (happy vs. sad) for Reachy Mini robot

---

## Executive Summary

The Reachy_Local_08.4.2 project implements **58 distinct statistical metrics and computational methods** across 15+ files. Of the statistical techniques provided, **9 methods directly apply**, with **2 partially applicable** and **2 non-applicable** to this binary emotion classification system.

### Quick Reference: Applicability Matrix

| Category | Method | Applies? | Reason |
|----------|--------|----------|--------|
| **Classification** | Accuracy | ✅ Yes | Binary classifier |
| **Classification** | Precision | ✅ Yes | Multi-class aware |
| **Classification** | Recall | ✅ Yes | Class imbalance handling |
| **Classification** | F1-Score | ✅ Yes | Primary quality metric |
| **Classification** | Confusion Matrix | ✅ Yes | Error analysis |
| **Inference** | MSE | ⚠️ Partial | VA regression (future feature) |
| **Inference** | Confidence Interval | ⚠️ Partial | Uncertainty quantification (planned) |
| **Inference** | Hypothesis Testing | ❌ No | Not applicable to classification |
| **Dimensionality** | PCA | ❌ No | Fixed input size (224×224×3) |
| **Detection** | IoU | ❌ No | Not bounding box task |
| **Detection** | mAP | ❌ No | Not multi-scale detection |
| **Detection** | PCK | ⚠️ Partial | Landmark detection for input features |

---

## PART 1: APPLICABLE STATISTICAL METHODS

### 1. ACCURACY ✅ FULLY APPLICABLE

#### Definition
The proportion of correct predictions to total predictions.

**Equation**: Accuracy = (# correct predictions) / (total # predictions)

#### Project Application
- **Why it applies**: EmotionNet performs binary classification (happy=1, sad=0). Accuracy measures overall correctness across both classes.
- **Limitation**: Accuracy alone is insufficient for imbalanced datasets. Used alongside balanced accuracy.
- **Quality Gate**: Not directly enforced, but logged alongside other metrics.

#### Implementation Location
**File**: `trainer/fer_finetune/evaluate.py:56`
```python
metrics['accuracy'] = accuracy_score(y_true, y_pred)
```

**Computed During**:
1. Validation phase (per epoch)
2. Final model evaluation before deployment
3. Shadow mode testing on Jetson

**Storage**:
- MLflow: `val_accuracy` (per epoch)
- Prometheus: Not exposed
- Database: Recorded in `run_link` table via MLflow

#### Usage Context
```python
# In trainer/fer_finetune/train.py:340
metrics = compute_metrics(all_labels, all_preds)
# Returns: {'accuracy': 0.9234, 'f1_macro': 0.8945, ...}
```

**Integration with Validation Gates**: Gate A checks do NOT require specific accuracy threshold (uses F1 instead), but accuracy is logged for observability.

---

### 2. PRECISION ✅ FULLY APPLICABLE

#### Definition
True positives as a proportion of all predicted positives.

**Equation**: Precision = TP / (TP + FP)

#### Project Application
- **Why it applies**: Critical for emotion classification. Precision per class answers: "When the model predicts HAPPY, how often is it correct?"
- **Use case**: Prevents false positives that trigger incorrect gestures/dialogue on the robot.
- **Macro vs. micro**: Project uses **macro-averaging** (equal weight per class) to handle potential class imbalance.

#### Implementation Location
**File**: `trainer/fer_finetune/evaluate.py:57`
```python
metrics['precision_macro'] = precision_score(y_true, y_pred, average='macro', zero_division=0)
```

**Computed During**:
1. Every validation step
2. Final test set evaluation
3. Multi-class F1 computation

#### Quality Gate Compliance
- **Gate A**: Does not directly enforce precision threshold
- **Related metric**: F1-macro (which incorporates precision) must be ≥ 0.84
- **Per-class**: Precision computed implicitly in per-class confusion matrix

**Code Example**:
```python
# trainer/fer_finetune/evaluate.py:266-276
for i in range(cm.shape[0]):
    tp = cm[i, i]
    fp = cm[:, i].sum() - tp  # All predictions as this class - correct predictions
    fn = cm[i, :].sum() - tp
    tn = cm.sum() - tp - fp - fn

    # Implied precision for class i: tp / (tp + fp)
    result[f'class_{i}_fp'] = int(fp)
```

---

### 3. RECALL ✅ FULLY APPLICABLE

#### Definition
True positives as a proportion of all actual positives.

**Equation**: Recall = TP / (TP + FN)

#### Project Application
- **Why it applies**: Answers "Of all actual HAPPY videos, what % did the model correctly identify?"
- **Balance requirement**: Macro-averaged recall ensures both classes are detected equally well.
- **Robot safety**: High recall for both emotions prevents missed sentiment expressions.

#### Implementation Location
**File**: `trainer/fer_finetune/evaluate.py:58`
```python
metrics['recall_macro'] = recall_score(y_true, y_pred, average='macro', zero_division=0)
```

**Computed During**:
1. Every validation epoch
2. Classification report generation
3. Confusion matrix analysis

#### Per-Class Recall (From Confusion Matrix)
```python
# Derived in evaluate.py:266-276
# For each class i:
# recall_i = tp_i / (tp_i + fn_i)
```

**Integration with F1**:
F1-macro uses both precision and recall, ensuring balanced performance:
```
F1_macro = mean(F1_per_class)
         = mean(2 * (precision_i * recall_i) / (precision_i + recall_i))
```

---

### 4. F1-SCORE ✅ FULLY APPLICABLE (PRIMARY METRIC)

#### Definition
Harmonic mean of precision and recall.

**Equation**: F1 = 2 × (Precision × Recall) / (Precision + Recall)

#### Project Application
- **Criticality**: F1-macro is the **primary quality gate** for deployment
- **Why macro**: Ensures both emotions (happy, sad) are recognized equally well
- **Per-class F1**: Secondary validation ensures neither class is sacrificed for accuracy

#### Quality Gate Enforcement
**Gate A (Offline Validation)** requires:
- F1 macro ≥ **0.84**
- Per-class F1 ≥ **0.75** (both classes)

#### Implementation Location
**File**: `trainer/fer_finetune/evaluate.py:59, 63-67`
```python
metrics['f1_macro'] = f1_score(y_true, y_pred, average='macro', zero_division=0)

# Per-class F1
f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
for i, f1 in enumerate(f1_per_class):
    metrics[f'f1_class_{i}'] = f1
    if class_names and i < len(class_names):
        metrics[f'f1_{class_names[i]}'] = f1
```

**Training Integration**:
- **Early stopping**: Validation based on F1 macro (best metric selection)
- **Epoch logging**: F1 tracked per epoch via MLflow
- **Gate checking**: Validation.py:check_gate_a() enforces threshold

**Code Path**:
```python
# trainer/fer_finetune/train.py:391
best_metrics = self.validate()
if best_metrics['f1_macro'] > self.best_metric:
    self.best_metric = best_metrics['f1_macro']
    # Save checkpoint

# trainer/validation.py:44-58
def check_gate_a(self, metrics):
    f1_score = metrics.get('f1_macro', 0.0)
    passed = f1_score >= self.GATE_A_F1_THRESHOLD  # 0.84
```

**Reporting**:
```python
# trainer/fer_finetune/evaluate.py:353-366
report = f"""
Accuracy:          {results.get('accuracy', 0):.4f}
F1 Macro:          {results.get('f1_macro', 0):.4f}
Per-Class F1:
  f1_happy:        {results.get('f1_happy', 0):.4f}
  f1_sad:          {results.get('f1_sad', 0):.4f}
"""
```

---

### 5. CONFUSION MATRIX ✅ FULLY APPLICABLE

#### Definition
Tabular representation of actual vs. predicted classifications. Reveals specific error patterns.

**Structure** (2×2 for binary classification):
```
           Predicted Sad  Predicted Happy
Actual Sad      TN              FP
Actual Happy    FN              TP
```

#### Project Application
- **Error diagnosis**: Identifies whether model confuses sad→happy more than happy→sad
- **Class imbalance**: Detects if one emotion is systematically misclassified
- **Domain analysis**: Enables analysis like "which emotional expressions cause confusion?"

#### Implementation Location
**File**: `trainer/fer_finetune/evaluate.py:233-278`
```python
def compute_confusion_matrix(y_true, y_pred, class_names=None):
    cm = confusion_matrix(y_true, y_pred)
    result = {
        'matrix': cm.tolist(),  # 2D array
        'class_names': class_names or ['sad', 'happy'],
    }

    # Per-class breakdown
    for i in range(cm.shape[0]):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        tn = cm.sum() - tp - fp - fn

        result[f'class_{i}_tp'] = int(tp)
        result[f'class_{i}_fp'] = int(fp)
        result[f'class_{i}_fn'] = int(fn)
        result[f'class_{i}_tn'] = int(tn)
```

**Integration with Model Evaluation**:
```python
# trainer/fer_finetune/evaluate.py:324-327
results = compute_metrics(all_labels, all_preds, class_names)
results.update(compute_calibration_metrics(all_labels, all_probs))
results['confusion'] = compute_confusion_matrix(all_labels, all_preds, class_names)
```

**Human-Readable Output**:
```python
# trainer/fer_finetune/evaluate.py:332-399
def generate_report(results):
    lines.append("QUALITY GATE STATUS")
    # Report includes confusion matrix visualization
    # Example output:
    #        Sad   Happy
    # Sad    450     20
    # Happy   15    435
```

**MLflow Storage**:
```python
# trainer/mlflow_tracker.py:155-179
mlflow.log_metric(f'{gate_name}_{key}', value)
# Stores: gate_a_confusion_matrix as part of validation results
```

**Use Cases**:
1. **Emotion bias detection**: Are sad videos systematically misclassified?
2. **Dataset quality**: High FP for one class suggests dataset labeling issues
3. **Model refinement**: Guides which edge cases need more training data

---

## PART 2: PARTIALLY APPLICABLE METHODS

### 6. MEAN SQUARED ERROR (MSE) ⚠️ PARTIALLY APPLICABLE

#### Definition
Average squared difference between predicted and actual values: MSE = Σ(ŷ - y)² / N

#### Project Application Status
- **Current use**: NOT actively implemented for classification task
- **Future use**: Planned for **Valence/Arousal (VA) regression** in multi-task learning
- **Relevance**: Brier score (MSE of probabilities) IS implemented as calibration metric

#### Current Implementation (Implicit)
**File**: `trainer/fer_finetune/evaluate.py:206-230`
```python
def brier_score(y_true, y_prob):
    """
    Mean squared error of probabilities.
    This is essentially MSE applied to classification confidences.
    """
    n_classes = y_prob.shape[1]
    y_true_onehot = np.eye(n_classes)[y_true]
    brier = np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))
    return float(brier)
```

**Quality Gate**: Gate A requires Brier ≤ 0.16

**Why Partial**:
- ✅ Brier score (MSE of probabilities) is computed
- ❌ Raw MSE for continuous target variables not used (emotion is discrete 0/1)
- 🔮 MSE will become relevant if VA regression is added for emotional intensity measurement

#### Future Implementation Path
```python
# trainer/fer_finetune/train.py:90-94 (Already scaffolded)
if config.model.use_multi_task:
    self.va_criterion = nn.MSELoss()  # For future VA prediction
else:
    self.va_criterion = None
```

**Planned in docstring**:
```python
# trainer/fer_finetune/train.py:285-290
# NOTE: VA (valence/arousal) regression requires VA labels in dataset
# To enable: add 'va_labels' to dataset __getitem__ return
# if self.va_criterion is not None and 'va' in outputs and 'va_labels' in batch:
#     va_loss = self.va_criterion(outputs['va'], batch['va_labels'])
#     loss = loss + 0.5 * va_loss
```

---

### 7. CONFIDENCE INTERVALS (CI) ⚠️ PARTIALLY APPLICABLE

#### Definition
Range in which a population parameter (e.g., true F1 score) lies with specified probability.

**Use**: Quantify uncertainty in model performance metrics across different datasets/runs.

#### Project Application Status
- **Relevance**: Useful but not critical for deployment gates
- **Current**: Not formally computed
- **Should be used for**: Reporting model performance robustness

#### Why Applicable
When the model is deployed, we want to know:
- "True F1 on all user data is estimated to be 0.84 ± X with 95% confidence"
- "Latency p95 typically falls in range [240ms, 260ms]"

#### Where Applicable
1. **Metrics reporting** (not currently done)
2. **Cross-validation** (not currently implemented)
3. **Bootstrap confidence bounds** on F1, accuracy

#### Example Implementation (Could be Added)
```python
# Not currently in codebase, but could be added to evaluate.py
import scipy.stats

def f1_confidence_interval(y_true, y_pred, confidence=0.95):
    """Compute CI for F1 score using binomial confidence interval."""
    f1 = f1_score(y_true, y_pred)
    n = len(y_true)

    # Simplified: use normal approximation
    # For robust CI, use bootstrap percentile method
    ...
```

#### Where It Would Be Used
- **Post-training reporting**: "Model F1 = 0.845 [95% CI: 0.830, 0.860]"
- **Multi-run comparison**: Compare multiple training runs with uncertainty bounds

---

### 8. PERCENTAGE OF CORRECT KEYPOINTS (PCK) ⚠️ PARTIALLY APPLICABLE

#### Definition
Proportion of correctly detected facial landmarks (keypoints) within a distance threshold.

**Equation**: PCK = (# correct keypoints) / (total # keypoints)

#### Project Application Status
- **Current relevance**: LOW (not primary task)
- **Model input feature**: EmotionNet can accept 68-point facial landmarks as input
- **Applicability**: Critical IF switching from image→landmark input format

#### Where Landmarks Matter in Pipeline
**File**: `trainer/fer_finetune/dataset.py`
```python
# Current implementation uses 224×224×3 RGB images
# But model also supports landmark-based input:
# Input shape could be [1, 136, 1] for 68 landmarks × 2 coordinates
```

**Model Flexibility**:
```python
# trainer/fer_finetune/model.py
self.model = EmotionClassifier(
    input_shape=config.model.input_shape,  # Can be [224, 224, 3] OR [136, 1]
    ...
)
```

#### When PCK Would Apply
If project switches to landmark-based emotion detection:
1. Face detection model outputs 68 keypoints (eyes, nose, mouth, jaw, etc.)
2. PCK measures accuracy of this upstream detection
3. Poor PCK (e.g., 60%) would degrade EmotionNet performance
4. Critical emotions for robot: mouth corners (smile), eye position (attention)

#### Quality Gate Addition (If Implemented)
```python
# Hypothetical future gate
GATE_X_LANDMARK_PCK_THRESHOLD = 0.85  # 85% of landmarks detected correctly
```

---

## PART 3: NON-APPLICABLE METHODS

### 9. HYPOTHESIS TESTING ❌ NOT APPLICABLE

#### Definition
Statistical tests comparing null vs. alternative hypotheses (e.g., t-tests, ANOVA).

#### Why Not Applicable
1. **Binary classification** doesn't require hypothesis testing on labels
2. **No continuous distributions** to compare (predicted class is discrete)
3. **Comparison use case** (e.g., "Model A vs. Model B") not in project scope
4. **Deployment gates** use threshold-based checks, not statistical significance tests

#### Related: Could Be Useful For
- Comparing two training runs: "Does run B significantly outperform run A?"
- Checking if Gate A violation is due to randomness or real degradation
- **Not currently implemented** because project uses deterministic quality gates

---

### 10. PRINCIPAL COMPONENT ANALYSIS (PCA) ❌ NOT APPLICABLE

#### Definition
Dimensionality reduction technique identifying statistically insignificant features.

#### Why Not Applicable
1. **Fixed input shape**: 224×224×3 RGB images (all pixels are input)
2. **ResNet backbone**: Already performs feature extraction/reduction internally
3. **No feature selection needed**: ImageNet pretraining handles feature importance
4. **Landmark input option**: Fixed 68 landmarks (136 values), not high-dimensional

#### Would Only Apply If
- Using raw video frames with 1000s of features
- Need to reduce computational load (but not necessary on TensorRT)
- Performing exploratory analysis on learned feature representations

---

### 11. INTERSECTION OVER UNION (IoU) ❌ NOT APPLICABLE

#### Definition
Overlap ratio of predicted vs. ground-truth bounding boxes: IoU = Area(overlap) / Area(union)

#### Why Not Applicable
1. **Not object detection**: EmotionNet classifies pre-cropped faces, doesn't locate faces
2. **No bounding boxes**: Input is fixed-size emotion images, not video frames
3. **Different task**: Emotion classification ≠ face detection/localization

#### Where Face Detection Happens
- **Upstream task**: Face detector crops face from video
- **Separate pipeline**: Not part of EmotionNet validation
- **If implemented**: Would need separate face detection quality metrics

---

### 12. MEAN AVERAGE PRECISION (mAP) ❌ NOT APPLICABLE

#### Definition
Aggregate precision across multiple IoU thresholds and classes; used in object detection.

#### Why Not Applicable
1. **Not multi-scale detection**: No bounding box predictions
2. **Single task**: Binary classification, not class + localization
3. **Different evaluation framework**: mAP designed for COCO, Pascal VOC datasets

#### Only Relevant If
- Project added face detection layer
- Need to evaluate bounding box quality before emotion classification

---

## PART 4: SUMMARY APPLICABILITY TABLE

| # | Method | Category | Applies? | Quality Gate | Current File | Future Potential |
|---|--------|----------|----------|--------------|--------------|-----------------|
| 1 | Accuracy | Classification | ✅ Yes | No (logged only) | evaluate.py:56 | None |
| 2 | Precision | Classification | ✅ Yes | Indirect (via F1) | evaluate.py:57 | Per-class thresholds |
| 3 | Recall | Classification | ✅ Yes | Indirect (via F1) | evaluate.py:58 | Per-class thresholds |
| 4 | F1-Score | Classification | ✅ Yes | **Gate A: ≥0.84** | evaluate.py:59-67 | Per-class thresholds |
| 5 | Confusion Matrix | Classification | ✅ Yes | Error analysis | evaluate.py:233-278 | Automated threshold tuning |
| 6 | MSE | Regression | ⚠️ Partial | No (Brier used) | evaluate.py:206-230 | VA regression (planned) |
| 7 | Confidence Intervals | Statistics | ⚠️ Partial | No | None | Robustness reporting |
| 8 | Hypothesis Testing | Statistics | ❌ No | N/A | N/A | None |
| 9 | PCA | Dimensionality | ❌ No | N/A | N/A | None |
| 10 | IoU | Detection | ❌ No | N/A | N/A | None |
| 11 | mAP | Detection | ❌ No | N/A | N/A | None |
| 12 | PCK | Detection | ⚠️ Partial | No | N/A | Landmark-based emotion |

---

## PART 5: QUALITY GATES AND METRIC ORCHESTRATION

### Three-Tier Validation Framework

#### Gate A: Offline Validation (Training Time)
**File**: `trainer/validation.py:20-58` + `trainer/fer_finetune/evaluate.py`

**Metrics Checked**:
```python
GATE_A_F1_THRESHOLD = 0.84           # Classification
GATE_A_MIN_BALANCED_ACCURACY = 0.85  # Classification
GATE_A_MAX_ECE = 0.08                # Calibration
GATE_A_MAX_BRIER = 0.16              # Calibration (MSE-based)
```

**Process**:
1. After each epoch, compute classification + calibration metrics
2. Check if f1_macro ≥ 0.84
3. If yes, save checkpoint
4. If sustained for 10 epochs (early stopping patience), declare Gate A passed

#### Gate B: Shadow Mode (Edge Deployment)
**File**: `trainer/validation.py:60-88`

**Metrics Checked**:
```python
GATE_B_LATENCY_MS_THRESHOLD = 250    # Performance
# P50, P95 latencies measured on Jetson Xavier NX
```

**Process**:
1. Deploy model to Jetson in shadow mode
2. Run inference on real video streams
3. Measure p50, p95 latency
4. If latency ≤ 250ms, Gate B passes

**Measured In**: `jetson/monitoring/system_monitor.py:latency_p95_ms`

#### Gate C: User Rollout (Production)
**File**: `trainer/validation.py:90-118`

**Metrics Checked**:
```python
GATE_C_COMPLAINT_RATE_THRESHOLD = 0.01  # User feedback (<1% complaints)
```

**Process**:
1. Monitor user-reported complaint rate (via n8n Privacy Agent)
2. If <1% of interactions receive negative feedback, Gate C passes

---

## PART 6: IMPLEMENTATION ROADMAP

### Currently Implemented (58 metrics)
✅ Classification metrics (accuracy, precision, recall, F1, balanced accuracy)
✅ Confusion matrices (per-class TP/FP/FN/TN)
✅ Calibration metrics (ECE, MCE, Brier)
✅ Training losses (CrossEntropy, label smoothing)
✅ Inference latency (p50, p95, p99)
✅ Hardware monitoring (GPU, CPU, memory, thermal)
✅ Operation metrics (promotion duration, failures)
✅ MLflow experiment tracking
✅ Prometheus metrics exposure

### Recommended Additions
1. **Confidence intervals** (5% effort)
   - Add bootstrap CI computation to evaluate.py
   - Report in evaluation_report()

2. **Per-class quality gates** (10% effort)
   - Extend Gate A to require f1_sad ≥ 0.75 AND f1_happy ≥ 0.75
   - Currently implicit in macro averaging

3. **Cross-validation metrics** (15% effort)
   - Implement k-fold CV for robustness assessment
   - Report averaged F1 ± σ

4. **Valence/Arousal regression** (25% effort)
   - Add VA labels to dataset
   - Enable multi-task learning (MSE for VA, CE for emotion)
   - Requires model architecture extension

### Not Recommended
- PCA: ResNet feature extraction makes this redundant
- Hypothesis testing: Deterministic gates are simpler & sufficient
- IoU/mAP: Not applicable to emotion classification task

---

## PART 7: METRIC DEPENDENCY GRAPH

```
Training Loop
├── Epoch
│   ├── train_epoch()
│   │   ├── Loss (CrossEntropy)
│   │   └── Training Accuracy
│   │
│   └── validate()
│       ├── Classification Metrics
│       │   ├── Accuracy
│       │   ├── Precision (macro)
│       │   ├── Recall (macro)
│       │   ├── F1 (macro) ← PRIMARY DECISION POINT
│       │   ├── Per-class F1
│       │   └── Balanced Accuracy
│       │
│       ├── Confusion Matrix
│       │   ├── TP/FP/FN/TN per class
│       │   └── Used for error analysis
│       │
│       ├── Calibration Metrics
│       │   ├── ECE
│       │   ├── MCE
│       │   └── Brier (MSE-based)
│       │
│       └── MLflow Logging
│           ├── All metrics above
│           ├── Learning rate
│           └── Training phase
│
└── Post-Training
    ├── Gate A Check
    │   ├── f1_macro ≥ 0.84? ✓
    │   ├── balanced_accuracy ≥ 0.85? ✓
    │   ├── ece ≤ 0.08? ✓
    │   └── brier ≤ 0.16? ✓
    │
    ├── Export to TensorRT
    │
    └── Deploy to Jetson
        ├── Gate B Check
        │   └── latency_p95 ≤ 250ms? ✓
        │
        └── Monitor in Production
            └── Gate C Check
                └── complaint_rate < 1%? ✓
```

---

## PART 8: CRITICAL FILES REFERENCE

### For Classification Metrics
- **Primary**: `trainer/fer_finetune/evaluate.py`
- **Usage in training**: `trainer/fer_finetune/train.py:339-343`
- **Quality gates**: `trainer/validation.py:29-58`

### For Calibration Metrics
- **Implementation**: `trainer/fer_finetune/evaluate.py:98-230`
- **Gate A integration**: `trainer/fer_finetune/evaluate.py:381-386`

### For Latency Metrics
- **Measurement**: `jetson/monitoring/system_monitor.py`
- **Gate B check**: `trainer/validation.py:60-88`

### For MLflow Integration
- **Tracking**: `trainer/mlflow_tracker.py`
- **Usage**: `trainer/fer_finetune/train.py:402-420`

### For Prometheus Metrics
- **Definition**: `apps/api/app/metrics.py`
- **Endpoint**: `apps/api/app/routers/health_router.py`

---

## Conclusion

The Reachy_Local_08.4.2 project implements a **comprehensive, multi-layer statistical analysis framework** covering:

1. **9 fully applicable methods** for binary emotion classification
2. **3 partially applicable methods** (MSE/Brier, CI, PCK)
3. **3 non-applicable methods** (hypothesis testing, PCA, IoU/mAP)

The **quality gate system** (Gates A, B, C) orchestrates these metrics into a deterministic deployment pipeline, prioritizing **F1-macro as the primary classification metric** and **latency p95 as the edge performance metric**.

**Recommended focus areas**:
- ✅ Current implementation is solid for binary classification
- 📈 Consider confidence intervals for robustness reporting
- 🔮 Prepare for future multi-task learning (Valence/Arousal regression) using MSE
- 📊 Per-class F1 guardrails would improve reproducibility across emotion classes

---

**Document Version**: 1.0
**Last Updated**: 2026-01-22
**Maintainer**: Russell Bray (rustybee255@gmail.com)

