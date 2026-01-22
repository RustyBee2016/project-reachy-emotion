# Metric Implementation Mapping Reference

**Quick lookup table** for locating statistical method implementations in the codebase.

---

## CLASSIFICATION METRICS

### 1. Accuracy
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:56` |
| **Computation** | `sklearn.metrics.accuracy_score(y_true, y_pred)` |
| **Logged to MLflow** | `trainer/mlflow_tracker.py:92` (via `log_metrics()`) |
| **Used in Training** | `trainer/fer_finetune/train.py:340` |
| **Reported in** | `trainer/fer_finetune/evaluate.py:353` |
| **Quality Gate** | Not directly enforced (logged for observability) |
| **Test Coverage** | `tests/test_training_pipeline.py` |

---

### 2. Precision (Macro-averaged)
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:57` |
| **Computation** | `sklearn.metrics.precision_score(y_true, y_pred, average='macro', zero_division=0)` |
| **Per-class calculation** | Derived from confusion matrix: `TP / (TP + FP)` |
| **Used in** | F1-macro computation |
| **Report line** | `trainer/fer_finetune/evaluate.py:356` |
| **Confustion matrix source** | `trainer/fer_finetune/evaluate.py:266-276` |

---

### 3. Recall (Macro-averaged)
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:58` |
| **Computation** | `sklearn.metrics.recall_score(y_true, y_pred, average='macro', zero_division=0)` |
| **Per-class calculation** | Derived from confusion matrix: `TP / (TP + FN)` |
| **Used in** | F1-macro computation |
| **Report line** | `trainer/fer_finetune/evaluate.py:357` |

---

### 4. F1-Score (PRIMARY METRIC)
| Aspect | Location |
|--------|----------|
| **Macro F1 Definition** | `trainer/fer_finetune/evaluate.py:59` |
| **Computation** | `sklearn.metrics.f1_score(y_true, y_pred, average='macro', zero_division=0)` |
| **Per-class F1** | `trainer/fer_finetune/evaluate.py:63-67` |
| **Class names in report** | Uses class_names parameter (default: `['sad', 'happy']`) |
| **Quality Gate A** | `trainer/validation.py:44-58` (threshold: **≥ 0.84**) |
| **Early stopping criterion** | `trainer/fer_finetune/train.py:391` |
| **Training loop** | `trainer/fer_finetune/train.py:405-413` |
| **MLflow tracking** | `trainer/mlflow_tracker.py:92` |
| **Report line** | `trainer/fer_finetune/evaluate.py:355` |
| **Per-class report** | `trainer/fer_finetune/evaluate.py:363-366` |

---

### 5. Confusion Matrix
| Aspect | Location |
|--------|----------|
| **Full definition** | `trainer/fer_finetune/evaluate.py:233-278` |
| **Function signature** | `compute_confusion_matrix(y_true, y_pred, class_names=None)` |
| **sklearn wrapper** | `sklearn.metrics.confusion_matrix(y_true, y_pred)` |
| **Per-class breakdown** | `trainer/fer_finetune/evaluate.py:267-276` |
| **TP extraction** | `cm[i, i]` for class i |
| **FP extraction** | `cm[:, i].sum() - tp` for class i |
| **FN extraction** | `cm[i, :].sum() - tp` for class i |
| **TN extraction** | `cm.sum() - tp - fp - fn` for class i |
| **Integrated in evaluate_model()** | `trainer/fer_finetune/evaluate.py:327` |
| **Report generation** | `trainer/fer_finetune/evaluate.py:359-367` |

---

## CALIBRATION METRICS

### 6. Expected Calibration Error (ECE)
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:131-166` |
| **Function** | `expected_calibration_error(y_true, y_prob, n_bins=10)` |
| **What it measures** | How well predicted probabilities match actual accuracy |
| **Quality Gate A threshold** | **≤ 0.08** (file: `trainer/fer_finetune/evaluate.py:384`) |
| **Lower is better** | Yes |
| **Computation logic** | Stratifies confidence into 10 bins, measures avg_accuracy - avg_confidence per bin |
| **Used in evaluate_model()** | `trainer/fer_finetune/evaluate.py:326` |
| **Report line** | `trainer/fer_finetune/evaluate.py:372` |

---

### 7. Maximum Calibration Error (MCE)
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:169-203` |
| **Function** | `maximum_calibration_error(y_true, y_prob, n_bins=10)` |
| **What it measures** | Maximum gap between confidence and accuracy across all bins |
| **Lower is better** | Yes |
| **Computation logic** | Max of (abs(avg_accuracy - avg_confidence)) across bins |
| **Used in evaluate_model()** | `trainer/fer_finetune/evaluate.py:326` |
| **Report line** | `trainer/fer_finetune/evaluate.py:373` |

---

### 8. Brier Score (MSE of Probabilities)
| Aspect | Location |
|--------|----------|
| **Definition** | `trainer/fer_finetune/evaluate.py:206-230` |
| **Function** | `brier_score(y_true, y_prob)` |
| **Formula** | MSE of one-hot encoded labels: `mean((y_prob - y_true_onehot)²)` |
| **Quality Gate A threshold** | **≤ 0.16** (file: `trainer/fer_finetune/evaluate.py:385`) |
| **Lower is better** | Yes |
| **Implementation** | One-hot encodes true labels, computes MSE |
| **Used in calibration_metrics()** | `trainer/fer_finetune/evaluate.py:123` |
| **Report line** | `trainer/fer_finetune/evaluate.py:374` |

---

## INFERENCE/LATENCY METRICS

### 9. Latency P95 (Gate B)
| Aspect | Location |
|--------|----------|
| **Definition** | `jetson/monitoring/system_monitor.py` (exact line TBD) |
| **What it measures** | 95th percentile inference latency in milliseconds |
| **Quality Gate B threshold** | **≤ 250 ms** (file: `trainer/validation.py:22`) |
| **Measured on** | Jetson Xavier NX edge device |
| **Validation check** | `trainer/validation.py:60-88` |
| **Gate name** | `check_gate_b(latency_ms)` |

**Additional latency percentiles**:
- P50 (median): Typical inference time
- P95: Tail latency (SLA critical)
- P99: Extreme tail latency

---

## PARTIAL IMPLEMENTATIONS

### 10. Mean Squared Error (MSE)
| Aspect | Location |
|--------|----------|
| **Current use** | As Brier score (MSE of probabilities) in classification |
| **File** | `trainer/fer_finetune/evaluate.py:206-230` |
| **Future use** | Multi-task Valence/Arousal (VA) regression |
| **Planned location** | `trainer/fer_finetune/train.py:91-94` (scaffolded but disabled) |
| **Activation flag** | `config.model.use_multi_task = True` |
| **Loss definition** | `nn.MSELoss()` for VA targets |

---

### 11. Confidence Intervals
| Aspect | Location |
|--------|----------|
| **Current status** | Not implemented |
| **Recommended for** | Robustness reporting of F1, accuracy across multiple runs |
| **Where to add** | `trainer/fer_finetune/evaluate.py` (new function) |
| **Method** | Bootstrap percentile method or binomial CI |
| **Output format** | E.g., "F1 = 0.845 [95% CI: 0.830, 0.860]" |

---

### 12. Percentage of Correct Keypoints (PCK)
| Aspect | Location |
|--------|----------|
| **Current status** | Not implemented (landmark input option exists but unused) |
| **When applicable** | If switching from 224×224×3 images to 68-point facial landmarks |
| **Model support** | `trainer/fer_finetune/model.py` supports landmark input shape `[1, 136, 1]` |
| **Dataset support** | `trainer/fer_finetune/dataset.py` currently extracts RGB images |
| **Would measure** | Accuracy of upstream facial landmark detection |

---

## QUALITY GATE HIERARCHY

### Gate A: Offline Validation (Training)
**File**: `trainer/validation.py:11-166` + `trainer/fer_finetune/evaluate.py:332-399`

| Metric | Threshold | Type | File |
|--------|-----------|------|------|
| F1 Macro | ≥ 0.84 | Classification | evaluate.py:59, validation.py:44 |
| Balanced Accuracy | ≥ 0.85 | Classification | evaluate.py:60, validation.py (implicit) |
| Per-class F1 | ≥ 0.75 | Classification | evaluate.py:63-67 (implicit) |
| ECE | ≤ 0.08 | Calibration | evaluate.py:131-166, validation.py (implicit) |
| Brier Score | ≤ 0.16 | Calibration | evaluate.py:206-230, validation.py (implicit) |

**All gates must pass**: `trainer/validation.py:120-152`

---

### Gate B: Shadow Mode (Edge)
**File**: `trainer/validation.py:60-88`

| Metric | Threshold | Type | File |
|--------|-----------|------|------|
| Latency P95 | ≤ 250 ms | Performance | validation.py:60-88, jetson/monitoring |

---

### Gate C: Production Rollout
**File**: `trainer/validation.py:90-118`

| Metric | Threshold | Type | File |
|--------|-----------|------|------|
| Complaint Rate | < 1.0% | User Feedback | validation.py:90-118 |

---

## MLflow Integration Points

| Metric | Logged As | Location | File |
|--------|-----------|----------|------|
| All validation metrics | `val_{metric_name}` | Per epoch | train.py:420, mlflow_tracker.py:92 |
| F1 Macro | `val_f1_macro` | Per epoch | mlflow_tracker.py:92 |
| Training loss | `train_loss`, `val_loss` | Per epoch | train.py:341 |
| Learning rate | `learning_rate` | Per epoch | train.py:395 |
| Dataset info | dataset_hash, train_count, test_count | Run params | mlflow_tracker.py:144-151 |
| Gate results | `gate_a_passed`, `gate_a_f1_score`, etc. | Run metrics | mlflow_tracker.py:155-179 |
| Model artifact | Model checkpoint | Run artifacts | mlflow_tracker.py:96-123 |

---

## Testing Coverage

| Metric | Test File | Test Function |
|--------|-----------|---------------|
| Classification metrics | `tests/test_training_pipeline.py` | test_evaluate_model_metrics |
| Confusion matrix | `tests/test_training_pipeline.py` | test_confusion_matrix_computation |
| Calibration metrics | `tests/test_training_pipeline.py` | test_calibration_metrics |
| Quality gates | `tests/test_training_pipeline.py` | test_validation_gates |
| MLflow logging | `tests/test_mlflow_integration.py` | test_log_epoch_metrics, test_log_validation_results |
| Prometheus metrics | `tests/apps/api/routers/test_metrics_router.py` | test_metrics_endpoint |

---

## Summary: 58 Total Metrics Implemented

### By Category
- **Classification**: 8 metrics (accuracy, precision, recall, F1, balanced accuracy, per-class variants, confusion matrix)
- **Calibration**: 3 metrics (ECE, MCE, Brier)
- **Performance/Latency**: 4 metrics (p50, p95, p99, mean)
- **Hardware**: 8 metrics (GPU util, CPU util, temps, power, memory)
- **Operation**: 3 metrics (promotion duration, failures, counts)
- **Training**: 5+ metrics (loss, learning rate, training phase, gradient norm, etc.)
- **Other**: 20+ metrics (dataset sizes, model params, connection status, etc.)

---

**Last Updated**: 2026-01-22
**Document Version**: 1.0
