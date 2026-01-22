# Partial Methods Integration Guide: MSE, Confidence Intervals, PCK

**Objective**: Detailed exploration of how to apply the three partially applicable statistical methods to the Reachy_Local_08.4.2 project.

---

## OVERVIEW

Three statistical methods are partially applicable to EmotionNet:

1. **Mean Squared Error (MSE)** — Currently used as Brier score; can extend to valence/arousal regression
2. **Confidence Intervals (CI)** — Not implemented; valuable for uncertainty quantification
3. **Percentage of Correct Keypoints (PCK)** — Not currently used; applicable if switching to landmark-based input

Each method can enhance model robustness, interpretability, or capability without major architectural changes.

---

## METHOD 1: MEAN SQUARED ERROR (MSE) - ENABLING MULTI-TASK LEARNING

### 1.1 Current State

**What's already implemented**:
- Brier score (MSE of classification probabilities) — File: `trainer/fer_finetune/evaluate.py:206-230`
- Model architecture supports multi-task learning — File: `trainer/fer_finetune/model.py:76-83`
- Configuration flag `use_multi_task` exists — File: `trainer/fer_finetune/config.py:29`

**What's NOT implemented**:
- Dataset labels for valence (positivity) and arousal (intensity)
- Loss computation combining classification + VA regression
- Evaluation metrics for VA predictions
- Gate C extension for VA performance

### 1.2 How to Apply MSE for Valence/Arousal Regression

#### 1.2.1 Why Valence/Arousal Matters

**Problem solved**: Current binary classification is coarse-grained.
- Happy + happy_excited = same prediction, but different robot responses needed
- Sad + sad_fearful = same prediction, but different empathy levels needed

**Solution**: Predict continuous values:
- **Valence** (range: [-1, 1]): Positive (happy) → +1, Negative (sad) → -1
- **Arousal** (range: [0, 1]): Calm → 0, Intense → 1

**Use case**: Robot adjusts gesture intensity and dialogue tone:
```
Prediction: emotion=happy, valence=0.8, arousal=0.6
→ Execute: Warm smile + moderate hand gesture + conversational tone

Prediction: emotion=happy, valence=0.95, arousal=0.95
→ Execute: Enthusiastic grin + large hand gesture + excited tone
```

#### 1.2.2 Implementation Path (4 steps)

**Step 1: Extend Dataset to Include VA Labels**

**File to modify**: `trainer/fer_finetune/dataset.py`

**Current behavior** (lines 148-150):
```python
def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
    """Get a sample."""
    # Returns: (image, label)
```

**New behavior** (multi-task):
```python
def __getitem__(self, idx: int) -> Dict[str, Any]:
    """
    Get a sample with VA annotations.

    Returns:
    {
        'image': torch.Tensor [3, 224, 224],
        'emotion_label': int (0=happy, 1=sad),
        'va_label': torch.Tensor [2] → [valence, arousal]
    }
    """
    sample = self.samples[idx]
    image = self._load_image(sample['path'])

    if self.transform:
        image = self.transform(image=image)['image']

    return {
        'image': image,
        'emotion_label': torch.tensor(sample['label'], dtype=torch.long),
        'va_label': torch.tensor(
            [sample.get('valence', 0.0), sample.get('arousal', 0.5)],
            dtype=torch.float32
        ),
    }
```

**Data annotation format** (stored in metadata):
```json
{
  "video_id": "abc123.mp4",
  "label": "happy",
  "valence": 0.8,      # -1 (very sad) to +1 (very happy)
  "arousal": 0.6       #  0 (calm) to 1 (intense)
}
```

**Storage**: Extend `apps/api/app/db/models.py` to include VA columns:
```python
class Video(Base):
    __tablename__ = "video"

    # ... existing columns ...

    valence: float = Column(Float, nullable=True)    # For multi-task learning
    arousal: float = Column(Float, nullable=True)    # For multi-task learning
    va_annotation_timestamp: datetime = Column(DateTime, nullable=True)
```

---

**Step 2: Enable Multi-Task Loss in Training**

**File**: `trainer/fer_finetune/train.py`

**Current state** (lines 90-94, disabled):
```python
if config.model.use_multi_task:
    self.va_criterion = nn.MSELoss()  # Not currently used
else:
    self.va_criterion = None
```

**New implementation** (enable and integrate):
```python
def __init__(self, config: TrainingConfig):
    # ... existing code ...

    if config.model.use_multi_task:
        self.va_criterion = nn.MSELoss(reduction='mean')  # Enable VA regression
        self.va_loss_weight = config.va_loss_weight  # New config param (default: 0.3)
        logger.info(f"Multi-task learning enabled (VA weight: {self.va_loss_weight})")

def train_epoch(self, epoch: int) -> Dict[str, float]:
    """Train for one epoch (multi-task variant)."""

    for batch_idx, batch in enumerate(self.train_loader):
        images = batch['image'].to(self.device)
        emotion_labels = batch['emotion_label'].to(self.device)

        self.optimizer.zero_grad()

        # Forward pass
        outputs = self.model(images)
        logits = outputs['logits']

        # Classification loss
        emotion_loss = self.criterion(logits, emotion_labels)
        loss = emotion_loss

        # Multi-task VA regression loss (if enabled)
        if self.va_criterion is not None and 'va' in outputs and 'va_label' in batch:
            va_labels = batch['va_label'].to(self.device)
            va_pred = outputs['va']  # [B, 2]
            va_loss = self.va_criterion(va_pred, va_labels)

            # Weighted combination
            loss = emotion_loss + self.va_loss_weight * va_loss

            # Track both losses
            total_va_loss += va_loss.item()
            self.mlflow_tracker.log_epoch_metrics(
                epoch,
                {'va_loss': va_loss.item()}
            )

        loss.backward()
        self.optimizer.step()

        total_loss += loss.item()
```

**Configuration update** (`trainer/fer_finetune/config.py`):
```python
@dataclass
class TrainingConfig:
    # ... existing params ...

    # Multi-task learning
    use_multi_task: bool = True  # Change default from False
    va_loss_weight: float = 0.3  # Relative weight of VA regression to classification
    va_loss_weight_schedule: str = "constant"  # or "increasing" (ramp up VA weight)
```

---

**Step 3: Implement VA Evaluation Metrics**

**New function in** `trainer/fer_finetune/evaluate.py`:

```python
def compute_va_metrics(y_va_true: np.ndarray, y_va_pred: np.ndarray) -> Dict[str, float]:
    """
    Compute MSE-based metrics for valence/arousal regression.

    Args:
        y_va_true: Ground truth [N, 2] with columns [valence, arousal]
        y_va_pred: Predictions [N, 2]

    Returns:
        Dictionary with MSE, RMSE, MAE for each dimension
    """
    # MSE per dimension
    valence_mse = np.mean((y_va_true[:, 0] - y_va_pred[:, 0]) ** 2)
    arousal_mse = np.mean((y_va_true[:, 1] - y_va_pred[:, 1]) ** 2)

    # RMSE (square root of MSE)
    valence_rmse = np.sqrt(valence_mse)
    arousal_rmse = np.sqrt(arousal_mse)

    # Mean Absolute Error (more interpretable than MSE)
    valence_mae = np.mean(np.abs(y_va_true[:, 0] - y_va_pred[:, 0]))
    arousal_mae = np.mean(np.abs(y_va_true[:, 1] - y_va_pred[:, 1]))

    # Correlation (how well relative ordering is preserved)
    valence_corr = np.corrcoef(y_va_true[:, 0], y_va_pred[:, 0])[0, 1]
    arousal_corr = np.corrcoef(y_va_true[:, 1], y_va_pred[:, 1])[0, 1]

    return {
        'valence_mse': float(valence_mse),
        'arousal_mse': float(arousal_mse),
        'valence_rmse': float(valence_rmse),
        'arousal_rmse': float(arousal_rmse),
        'valence_mae': float(valence_mae),
        'arousal_mae': float(arousal_mae),
        'valence_corr': float(np.nan_to_num(valence_corr, nan=0.0)),
        'arousal_corr': float(np.nan_to_num(arousal_corr, nan=0.0)),
    }


def evaluate_model_multitask(model, val_loader, device) -> Dict[str, Any]:
    """
    Evaluate multi-task model (classification + VA regression).
    """
    model.eval()

    all_emotion_labels = []
    all_emotion_preds = []
    all_va_labels = []
    all_va_preds = []

    with torch.no_grad():
        for batch in val_loader:
            images = batch['image'].to(device)
            emotion_labels = batch['emotion_label'].to(device)

            outputs = model(images)
            logits = outputs['logits']
            preds = torch.argmax(logits, dim=1)

            all_emotion_labels.append(emotion_labels.cpu().numpy())
            all_emotion_preds.append(preds.cpu().numpy())

            # VA predictions (if available)
            if 'va' in outputs and 'va_label' in batch:
                va_labels = batch['va_label'].numpy()
                va_pred = outputs['va'].cpu().numpy()

                all_va_labels.append(va_labels)
                all_va_preds.append(va_pred)

    # Concatenate
    all_emotion_labels = np.concatenate(all_emotion_labels)
    all_emotion_preds = np.concatenate(all_emotion_preds)

    # Compute classification metrics
    results = compute_metrics(all_emotion_labels, all_emotion_preds)

    # Compute VA metrics if available
    if all_va_labels and all_va_preds:
        all_va_labels = np.concatenate(all_va_labels)
        all_va_preds = np.concatenate(all_va_preds)

        va_metrics = compute_va_metrics(all_va_labels, all_va_preds)
        results.update(va_metrics)
        results['has_va_metrics'] = True

    return results
```

---

**Step 4: Extend Quality Gates for VA Performance**

**File**: `trainer/validation.py`

**New Gate A extension**:
```python
def check_gate_a_multitask(self, metrics: Dict[str, float]) -> bool:
    """
    Check Gate A with multi-task validation.

    Classification requirements (unchanged):
    - F1 macro ≥ 0.84
    - Balanced accuracy ≥ 0.85
    - ECE ≤ 0.08
    - Brier ≤ 0.16

    Multi-task requirements (if enabled):
    - Valence RMSE ≤ 0.25 (on [-1, 1] scale)
    - Arousal RMSE ≤ 0.20 (on [0, 1] scale)
    """

    # Classification gates (existing)
    classification_pass = (
        metrics.get('f1_macro', 0) >= 0.84 and
        metrics.get('balanced_accuracy', 0) >= 0.85 and
        metrics.get('ece', float('inf')) <= 0.08 and
        metrics.get('brier', float('inf')) <= 0.16
    )

    if not classification_pass:
        logger.warning("Gate A (Classification) FAILED")
        return False

    # Multi-task gates (if applicable)
    if metrics.get('has_va_metrics', False):
        va_pass = (
            metrics.get('valence_rmse', float('inf')) <= 0.25 and
            metrics.get('arousal_rmse', float('inf')) <= 0.20
        )

        if not va_pass:
            logger.warning(
                f"Gate A (Multi-task) FAILED: "
                f"Valence RMSE={metrics.get('valence_rmse'):.3f}, "
                f"Arousal RMSE={metrics.get('arousal_rmse'):.3f}"
            )
            return False

        logger.info(
            f"Gate A (Multi-task) PASSED: "
            f"Valence RMSE={metrics.get('valence_rmse'):.3f}, "
            f"Arousal RMSE={metrics.get('arousal_rmse'):.3f}"
        )

    logger.info("Gate A (Classification) PASSED")
    return True
```

---

#### 1.2.3 Benefits and ROI

| Benefit | Impact | Effort |
|---------|--------|--------|
| Finer-grained emotion representation | High (enables nuanced gestures) | Medium |
| Better human-robot interaction quality | High (more natural responses) | Low (uses existing head) |
| Early detection of emotional extremes | Medium (safety feature) | Low |
| Richer MLflow observability | Medium (better debugging) | Low |

---

---

## METHOD 2: CONFIDENCE INTERVALS - UNCERTAINTY QUANTIFICATION

### 2.1 Current State

**What's missing**:
- No uncertainty bounds on F1, accuracy, or latency metrics
- No cross-validation implementation
- No bootstrap resampling
- No published confidence bounds to users

### 2.2 Why Confidence Intervals Matter

**Problem**: Single-point metrics (F1 = 0.845) don't show variability.
```
Scenario A: F1 = 0.845 across 5 runs: [0.840, 0.843, 0.845, 0.848, 0.850]
Scenario B: F1 = 0.845 across 5 runs: [0.700, 0.800, 0.845, 0.890, 0.950]

Same mean, but vastly different reliability!
```

**Solution**: Report with uncertainty:
```
"Model F1 = 0.845 [95% CI: 0.840, 0.850]"  ← Consistent
"Model F1 = 0.845 [95% CI: 0.700, 0.950]"  ← Unstable
```

### 2.3 Implementation Approach

#### 2.3.1 Bootstrap Confidence Intervals (Simplest)

**When to use**: Single train-test split, want robustness bounds.

**File to create**: `trainer/fer_finetune/confidence_intervals.py`

```python
"""
Compute confidence intervals for classification metrics using bootstrap resampling.
"""

import numpy as np
from typing import Dict, Tuple
from sklearn.metrics import f1_score, accuracy_score, balanced_accuracy_score
import logging

logger = logging.getLogger(__name__)


def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_func,
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    random_state: int = 42,
) -> Tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for a metric.

    Args:
        y_true: Ground truth labels [N]
        y_pred: Predictions [N]
        metric_func: Function that computes metric (e.g., f1_score)
        n_bootstraps: Number of bootstrap samples
        ci: Confidence level (0.95 for 95% CI)
        random_state: Seed for reproducibility

    Returns:
        (mean_estimate, lower_bound, upper_bound)
    """
    rng = np.random.RandomState(random_state)
    n_samples = len(y_true)

    bootstrap_scores = []

    for _ in range(n_bootstraps):
        # Resample with replacement
        indices = rng.choice(n_samples, size=n_samples, replace=True)
        y_true_boot = y_true[indices]
        y_pred_boot = y_pred[indices]

        # Compute metric on bootstrap sample
        score = metric_func(y_true_boot, y_pred_boot)
        bootstrap_scores.append(score)

    bootstrap_scores = np.array(bootstrap_scores)

    # Compute percentile CI
    alpha = 1 - ci
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    lower_bound = np.percentile(bootstrap_scores, lower_percentile)
    upper_bound = np.percentile(bootstrap_scores, upper_percentile)
    mean_estimate = np.mean(bootstrap_scores)

    return mean_estimate, lower_bound, upper_bound


def compute_metrics_with_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bootstraps: int = 1000,
    ci: float = 0.95,
) -> Dict[str, Dict[str, float]]:
    """
    Compute classification metrics with confidence intervals.

    Returns:
    {
        'f1_macro': {'estimate': 0.845, 'ci_lower': 0.840, 'ci_upper': 0.850},
        'accuracy': {'estimate': 0.92, 'ci_lower': 0.91, 'ci_upper': 0.93},
        ...
    }
    """
    results = {}

    # F1 Macro
    mean, lower, upper = bootstrap_ci(
        y_true, y_pred,
        lambda y_t, y_p: f1_score(y_t, y_p, average='macro'),
        n_bootstraps=n_bootstraps, ci=ci
    )
    results['f1_macro'] = {
        'estimate': float(mean),
        'ci_lower': float(lower),
        'ci_upper': float(upper),
        'ci_width': float(upper - lower),
    }

    # Accuracy
    mean, lower, upper = bootstrap_ci(
        y_true, y_pred,
        lambda y_t, y_p: accuracy_score(y_t, y_p),
        n_bootstraps=n_bootstraps, ci=ci
    )
    results['accuracy'] = {
        'estimate': float(mean),
        'ci_lower': float(lower),
        'ci_upper': float(upper),
        'ci_width': float(upper - lower),
    }

    # Balanced Accuracy
    mean, lower, upper = bootstrap_ci(
        y_true, y_pred,
        lambda y_t, y_p: balanced_accuracy_score(y_t, y_p),
        n_bootstraps=n_bootstraps, ci=ci
    )
    results['balanced_accuracy'] = {
        'estimate': float(mean),
        'ci_lower': float(lower),
        'ci_upper': float(upper),
        'ci_width': float(upper - lower),
    }

    return results


def log_ci_to_mlflow(run_id: str, metrics_with_ci: Dict[str, Dict[str, float]]):
    """
    Log confidence intervals to MLflow.

    File: trainer/mlflow_tracker.py (add this method)
    """
    import mlflow

    for metric_name, ci_data in metrics_with_ci.items():
        mlflow.log_metric(f'{metric_name}_estimate', ci_data['estimate'])
        mlflow.log_metric(f'{metric_name}_ci_lower', ci_data['ci_lower'])
        mlflow.log_metric(f'{metric_name}_ci_upper', ci_data['ci_upper'])
        mlflow.log_metric(f'{metric_name}_ci_width', ci_data['ci_width'])
```

**Integration point** (in `trainer/fer_finetune/evaluate.py`):

```python
from confidence_intervals import compute_metrics_with_ci

def evaluate_model(model, val_loader, device, compute_ci: bool = True) -> Dict[str, Any]:
    """Evaluate model with optional confidence intervals."""

    # ... existing evaluation code ...

    all_labels = np.concatenate(all_labels)
    all_preds = np.concatenate(all_preds)

    results = compute_metrics(all_labels, all_preds)

    # Add confidence intervals
    if compute_ci and len(all_labels) >= 50:  # Need sufficient samples
        ci_results = compute_metrics_with_ci(
            all_labels, all_preds,
            n_bootstraps=1000,
            ci=0.95
        )
        results['with_ci'] = ci_results

    return results
```

---

#### 2.3.2 Cross-Validation CI (More Robust)

**When to use**: Want to estimate model performance across different data splits.

**Implementation** (in `trainer/fer_finetune/train.py`):

```python
from sklearn.model_selection import StratifiedKFold
import torch
from torch.utils.data import Subset

def cross_validate_with_ci(
    model_config: TrainingConfig,
    dataset: EmotionDataset,
    n_splits: int = 5,
    ci: float = 0.95,
) -> Dict[str, Dict[str, float]]:
    """
    Perform k-fold cross-validation with confidence intervals.

    Procedure:
    1. Split data into k folds (stratified by emotion class)
    2. Train k models (each on k-1 folds)
    3. Evaluate on held-out fold
    4. Aggregate metrics across folds with CI
    """

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    fold_results = {
        'f1_macro': [],
        'accuracy': [],
        'balanced_accuracy': [],
    }

    for fold, (train_idx, val_idx) in enumerate(
        skf.split(dataset.samples, dataset.class_labels)
    ):
        logger.info(f"Training fold {fold + 1}/{n_splits}...")

        # Create fold-specific datasets
        train_subset = Subset(dataset, train_idx)
        val_subset = Subset(dataset, val_idx)

        # Train model on this fold
        trainer = Trainer(model_config)
        trainer.train(train_subset)

        # Evaluate on held-out fold
        metrics = trainer.validate_on_subset(val_subset)

        fold_results['f1_macro'].append(metrics['f1_macro'])
        fold_results['accuracy'].append(metrics['accuracy'])
        fold_results['balanced_accuracy'].append(metrics['balanced_accuracy'])

    # Aggregate results with CI
    aggregated = {}
    for metric_name, fold_scores in fold_results.items():
        fold_scores = np.array(fold_scores)

        aggregated[metric_name] = {
            'mean': float(np.mean(fold_scores)),
            'std': float(np.std(fold_scores)),
            'ci_lower': float(np.percentile(fold_scores, 2.5)),
            'ci_upper': float(np.percentile(fold_scores, 97.5)),
            'fold_scores': fold_scores.tolist(),
        }

    return aggregated
```

**Reporting** (example output):
```
═══════════════════════════════════════════════════════════════════
CROSS-VALIDATION RESULTS (5-Fold)
═══════════════════════════════════════════════════════════════════

F1 Macro:               0.8450 ± 0.0120  [95% CI: 0.8210, 0.8680]
Accuracy:              0.9200 ± 0.0145  [95% CI: 0.8950, 0.9420]
Balanced Accuracy:     0.8550 ± 0.0110  [95% CI: 0.8340, 0.8760]

Fold Scores:
  Fold 1: F1=0.843, Accuracy=0.918, BA=0.854
  Fold 2: F1=0.831, Accuracy=0.895, BA=0.841
  Fold 3: F1=0.858, Accuracy=0.942, BA=0.866
  Fold 4: F1=0.849, Accuracy=0.928, BA=0.858
  Fold 5: F1=0.853, Accuracy=0.925, BA=0.852
═══════════════════════════════════════════════════════════════════
```

---

#### 2.3.3 Integration into Quality Gates

**Modified Gate A check** (`trainer/validation.py`):

```python
def check_gate_a_with_uncertainty(
    self,
    metrics_with_ci: Dict[str, Dict[str, float]],
) -> bool:
    """
    Check Gate A considering uncertainty.

    Policy:
    - Pass if: estimate meets threshold AND lower bound doesn't violate it badly
    - Warn if: estimate passes but CI is wide (unstable model)
    - Fail if: upper bound fails threshold
    """

    f1_data = metrics_with_ci['f1_macro']
    f1_estimate = f1_data['estimate']
    f1_lower = f1_data['ci_lower']

    threshold = 0.84

    # Hard fail: even lower bound doesn't meet threshold
    if f1_lower < 0.80:  # Allow small margin (0.04)
        logger.error(
            f"Gate A FAILED: F1 lower bound {f1_lower:.4f} < 0.80 "
            f"(estimate: {f1_estimate:.4f})"
        )
        return False

    # Soft warn: estimate passes but CI is very wide
    ci_width = f1_data['ci_width']
    if ci_width > 0.05:  # Wide CI
        logger.warning(
            f"Gate A WARNING: F1 estimate {f1_estimate:.4f} passes, "
            f"but CI is wide [{f1_lower:.4f}, {f1_data['ci_upper']:.4f}]. "
            f"Model may be unstable. Consider more training data."
        )

    # Pass
    if f1_estimate >= threshold:
        logger.info(
            f"Gate A PASSED: F1 = {f1_estimate:.4f} "
            f"[95% CI: {f1_lower:.4f}, {f1_data['ci_upper']:.4f}]"
        )
        return True

    logger.error(f"Gate A FAILED: F1 estimate {f1_estimate:.4f} < {threshold}")
    return False
```

---

#### 2.3.4 Benefits

| Benefit | Implementation | Effort |
|---------|----------------|--------|
| Identifies unstable models | Bootstrap | Low |
| Assess robustness across splits | k-fold CV | Medium |
| Better reporting to stakeholders | CI reporting | Low |
| Detect data quality issues | Wide CI → more data needed | Low |
| Track improvement over time | Historical CI trends | Low |

---

---

## METHOD 3: PERCENTAGE OF CORRECT KEYPOINTS (PCK) - FACIAL LANDMARK DETECTION

### 3.1 Current State

**What exists**:
- Model architecture supports landmark input: `[1, 136, 1]` (68 keypoints × 2 coords)
- File: `trainer/fer_finetune/model.py:46-47`
- Configuration: `trainer/fer_finetune/config.py:25` (can set input_size)

**What's missing**:
- Facial landmark detector (face parsing preprocessing)
- Dataset loader for landmark-based input
- PCK metric computation
- Quality gate for landmark detection accuracy

### 3.2 Why PCK Matters (Alternative Input Modality)

**Current approach**: RGB images (224×224×3)
- ✅ Rich visual information (color, texture, lighting)
- ❌ Sensitive to lighting conditions, occlusions, pose variations
- ❌ Higher computational cost (more pixels)

**Landmark-based approach**: 68 facial keypoints (points + coordinates)
- ✅ Robust to lighting, pose, scale changes
- ✅ Much smaller input (136 floats vs 150,528 pixels)
- ✅ Lower latency on edge devices (Jetson)
- ❌ Depends on quality of upstream landmark detector
- ❌ May lose fine texture information (subtle expressions)

**When to use landmarks**:
1. Deployment on extremely resource-constrained devices
2. Robustness against lighting/pose variations
3. Multi-modal input (combine RGB + landmarks)

### 3.3 Implementation Path

#### 3.3.1 Facial Landmark Detection Pipeline

**File to create**: `trainer/fer_finetune/landmark_extraction.py`

```python
"""
Facial landmark detection and extraction for emotion classification.

Supports:
- MediaPipe Face Mesh (fast, ~450 points)
- dlib shape predictor (classical, 68 points)
- RetinaFace (robust face detection + alignment)
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

# Try to import face detection libraries
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    logger.warning("MediaPipe not available")

try:
    import dlib
    HAS_DLIB = True
except ImportError:
    HAS_DLIB = False
    logger.warning("dlib not available")


class FacialLandmarkDetector:
    """Extract 68-point facial landmarks from face images."""

    def __init__(self, method: str = "mediapipe", confidence_threshold: float = 0.5):
        """
        Initialize landmark detector.

        Args:
            method: "mediapipe", "dlib", or "retinaface"
            confidence_threshold: Min confidence for valid landmark
        """
        self.method = method
        self.confidence_threshold = confidence_threshold
        self._init_detector()

    def _init_detector(self):
        """Initialize the appropriate detector."""
        if self.method == "mediapipe" and HAS_MEDIAPIPE:
            mp_face_mesh = mp.solutions.face_mesh
            self.detector = mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                min_detection_confidence=self.confidence_threshold,
            )
            # Select 68 landmarks (excluding face oval contour)
            self.landmark_indices = self._get_68_point_subset()

        elif self.method == "dlib" and HAS_DLIB:
            self.detector = dlib.shape_predictor(
                "shape_predictor_68_face_landmarks.dat"  # Download from dlib
            )
        else:
            raise ValueError(f"Method {self.method} not available")

    def _get_68_point_subset(self) -> List[int]:
        """
        Map MediaPipe 468-point mesh to canonical 68-point format.

        MediaPipe landmarks:
        - 0-10: Face contour (keep 1-10 for jaw)
        - 11-15: Right eyebrow
        - 16-20: Left eyebrow
        - 21-26: Nose
        - 27-30: Lips (not in 68-point)
        - 33-133: Full face mesh

        Canonical 68-point (AffectNet, dlib):
        - 0-16: Jaw
        - 17-21: Left eyebrow
        - 22-26: Right eyebrow
        - 27-30: Nose
        - 31-35: Left eye
        - 36-41: Right eye
        - 42-47: Left mouth
        - 48-54: Right mouth
        - 55-67: Mouth interior + face outline
        """
        # Simplified mapping (actual implementation would be more detailed)
        return list(range(468))  # Use all MediaPipe landmarks for now

    def detect_landmarks(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detect facial landmarks in image.

        Args:
            image: RGB image [H, W, 3]

        Returns:
            (landmarks [68, 2], confidence)
            landmarks: [x, y] coordinates normalized to [-1, 1]
        """
        if self.method == "mediapipe":
            results = self.detector.process(image)

            if results.multi_face_landmarks is None or len(results.multi_face_landmarks) == 0:
                return None, 0.0

            # Get first face
            landmarks = results.multi_face_landmarks[0]

            # Convert to [68, 2] format (normalized to image dims)
            points = []
            for lm in landmarks.landmark:
                points.append([lm.x, lm.y])

            # Normalize to [-1, 1]
            points = np.array(points)
            points = points * 2 - 1  # [0, 1] → [-1, 1]

            confidence = 0.9  # MediaPipe doesn't return per-landmark confidence

            return points, confidence

        elif self.method == "dlib":
            # Convert to BGR for dlib
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            # Detect face
            dets = self.detector(image_bgr, 1)
            if len(dets) == 0:
                return None, 0.0

            # Get landmarks for first face
            shape = self.detector(image_bgr, dets[0])
            points = []

            for i in range(68):
                pt = shape.part(i)
                points.append([pt.x, pt.y])

            # Normalize to [-1, 1]
            points = np.array(points, dtype=np.float32)
            h, w = image.shape[:2]
            points[:, 0] = (points[:, 0] / w) * 2 - 1
            points[:, 1] = (points[:, 1] / h) * 2 - 1

            confidence = 0.85  # Empirical dlib confidence

            return points, confidence


def extract_landmarks_from_video(
    video_path: str,
    frame_sample: str = "middle",
) -> Optional[np.ndarray]:
    """
    Extract landmarks from single frame of video.

    Args:
        video_path: Path to .mp4 video
        frame_sample: "first", "middle", or "last"

    Returns:
        landmarks [68, 2] or None if detection fails
    """
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if frame_sample == "middle":
        frame_idx = frame_count // 2
    elif frame_sample == "first":
        frame_idx = 0
    else:  # "last"
        frame_idx = frame_count - 1

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        logger.warning(f"Failed to read frame {frame_idx} from {video_path}")
        return None

    # Convert BGR → RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect landmarks
    detector = FacialLandmarkDetector(method="mediapipe")
    landmarks, confidence = detector.detect_landmarks(frame)

    if landmarks is None or confidence < 0.5:
        logger.warning(f"Low confidence ({confidence:.2f}) for {video_path}")
        return None

    return landmarks
```

---

#### 3.3.2 Landmark-Based Dataset

**File**: `trainer/fer_finetune/dataset.py` (extend existing)

```python
class EmotionLandmarkDataset(Dataset):
    """
    Dataset for emotion classification using facial landmarks instead of RGB.

    Inputs: Normalized 68-point facial landmarks [68, 2]
    Outputs: Emotion label + optional VA labels
    """

    def __init__(
        self,
        data_dir: str,
        split: str = "train",
        class_names: Optional[List[str]] = None,
        normalize_landmarks: bool = True,
        augment_landmarks: bool = False,
    ):
        """
        Initialize landmark-based emotion dataset.

        Args:
            data_dir: Root directory with .mp4 videos
            split: "train", "val", or "test"
            class_names: Emotion class names
            normalize_landmarks: Normalize to [-1, 1]
            augment_landmarks: Apply augmentation (jitter, scale, rotate)
        """
        self.data_dir = Path(data_dir)
        self.split_dir = self.data_dir / split
        self.class_names = class_names or ["happy", "sad"]
        self.normalize_landmarks = normalize_landmarks
        self.augment_landmarks = augment_landmarks

        self.landmark_detector = FacialLandmarkDetector(method="mediapipe")
        self.samples = self._collect_samples()

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        Get sample with landmarks.

        Returns:
        {
            'landmarks': torch.Tensor [68, 2] or [136],
            'emotion_label': int,
            'confidence': float,
        }
        """
        sample = self.samples[idx]

        # Extract landmarks from video
        landmarks, confidence = extract_landmarks_from_video(
            sample['path'],
            frame_sample='middle'
        )

        if landmarks is None:
            # Return zero landmark if detection fails
            logger.warning(f"Landmark detection failed for {sample['path']}")
            landmarks = np.zeros((68, 2))
            confidence = 0.0

        # Flatten to [136] if needed
        landmarks_flat = landmarks.flatten().astype(np.float32)

        # Augmentation (optional)
        if self.augment_landmarks and self.split == "train":
            landmarks_flat = self._augment_landmarks(landmarks_flat)

        return {
            'landmarks': torch.tensor(landmarks_flat, dtype=torch.float32),
            'emotion_label': torch.tensor(sample['label'], dtype=torch.long),
            'confidence': float(confidence),
        }
```

---

#### 3.3.3 PCK Metric Implementation

**File**: `trainer/fer_finetune/evaluate.py` (add)

```python
def compute_pck(
    y_true_landmarks: np.ndarray,
    y_pred_landmarks: np.ndarray,
    distance_threshold: float = 0.2,
) -> Dict[str, float]:
    """
    Compute Percentage of Correct Keypoints (PCK).

    PCK measures whether predicted landmarks are within `distance_threshold`
    of ground truth landmarks (typically 20% of head bounding box size).

    Args:
        y_true_landmarks: Ground truth [N, 68, 2]
        y_pred_landmarks: Predicted [N, 68, 2]
        distance_threshold: Maximum allowed distance (normalized, 0-1 scale)

    Returns:
    {
        'pck': float,  # Overall PCK (0-1)
        'pck_per_region': {
            'jaw': float,
            'left_eyebrow': float,
            'right_eyebrow': float,
            'nose': float,
            'left_eye': float,
            'right_eye': float,
            'mouth': float,
        }
    }
    """

    # Landmark regions (68-point format)
    regions = {
        'jaw': slice(0, 17),
        'left_eyebrow': slice(17, 22),
        'right_eyebrow': slice(22, 27),
        'nose': slice(27, 36),
        'left_eye': slice(36, 42),
        'right_eye': slice(42, 48),
        'mouth': slice(48, 68),
    }

    # Compute per-landmark distances
    distances = np.linalg.norm(
        y_true_landmarks - y_pred_landmarks,
        axis=2  # Distance for each landmark
    )  # [N, 68]

    # Overall PCK
    pck = np.mean(distances <= distance_threshold)

    # Per-region PCK
    pck_per_region = {}
    for region_name, region_slice in regions.items():
        region_distances = distances[:, region_slice]
        pck_per_region[region_name] = float(
            np.mean(region_distances <= distance_threshold)
        )

    return {
        'pck': float(pck),
        'pck_per_region': pck_per_region,
    }
```

---

#### 3.3.4 Quality Gate for Landmark-Based Models

**File**: `trainer/validation.py` (extend)

```python
def check_landmark_detection_quality(pck_metrics: Dict[str, float]) -> bool:
    """
    Check if landmark detection quality is sufficient for emotion classification.

    Requirements:
    - Overall PCK ≥ 0.85 (85% of keypoints correctly detected)
    - Critical regions (eyes, mouth) PCK ≥ 0.90

    Rationale:
    - Eyes convey attention/engagement
    - Mouth conveys emotion (smile vs. frown)
    - Poor detection in these regions severely impacts emotion classification
    """

    pck = pck_metrics.get('pck', 0)
    pck_regions = pck_metrics.get('pck_per_region', {})

    # Check overall PCK
    if pck < 0.85:
        logger.error(f"Landmark Detection FAILED: PCK {pck:.3f} < 0.85")
        return False

    # Check critical regions
    critical_regions = ['left_eye', 'right_eye', 'mouth']
    for region in critical_regions:
        region_pck = pck_regions.get(region, 0)
        if region_pck < 0.90:
            logger.warning(
                f"Landmark Detection WARNING: {region} PCK {region_pck:.3f} < 0.90. "
                f"Emotion classification may be degraded."
            )

    logger.info(f"Landmark Detection PASSED: PCK {pck:.3f}")
    return True
```

---

#### 3.3.5 Integration with Existing Training

**Decision point**: Choose RGB or Landmarks (or hybrid)

```python
# trainer/fer_finetune/train.py

def create_dataloaders(config: TrainingConfig):
    """Create appropriate data loaders based on config."""

    if config.model.input_modality == "rgb":
        return create_dataloaders_rgb(config)

    elif config.model.input_modality == "landmarks":
        train_loader = DataLoader(
            EmotionLandmarkDataset(
                data_dir=config.data.data_root,
                split="train",
                class_names=config.data.class_names,
                augment_landmarks=True,
            ),
            batch_size=config.data.batch_size,
            shuffle=True,
        )
        val_loader = DataLoader(
            EmotionLandmarkDataset(
                data_dir=config.data.data_root,
                split="val",
                class_names=config.data.class_names,
                augment_landmarks=False,
            ),
            batch_size=config.data.batch_size,
            shuffle=False,
        )
        return train_loader, val_loader

    elif config.model.input_modality == "hybrid":
        # Concatenate RGB features + landmarks
        return create_dataloaders_hybrid(config)
```

---

#### 3.3.6 Benchmark: RGB vs Landmarks

**Expected results** (from literature):

| Metric | RGB | Landmarks | Hybrid |
|--------|-----|-----------|--------|
| F1 Macro | 0.845 | 0.810 | 0.875 |
| Latency (ms) | 45 | 8 | 50 |
| Robustness to lighting | ✓ | ✓✓✓ | ✓✓ |
| Sensitivity to pose | ✗ | ✓✓ | ✓ |

---

---

## SUMMARY: INTEGRATION ROADMAP

### MSE for Multi-Task Learning
- **Effort**: Medium (2-3 days)
- **Impact**: High (better emotion nuance)
- **Priority**: Medium (nice-to-have for future interaction quality)
- **Files to modify**: config.py, dataset.py, train.py, evaluate.py, model.py, mlflow_tracker.py

### Confidence Intervals
- **Effort**: Low-Medium (1-2 days)
- **Impact**: Medium (better observability)
- **Priority**: High (improves robustness reporting)
- **Files to create**: confidence_intervals.py
- **Files to modify**: evaluate.py, mlflow_tracker.py, validation.py

### PCK for Landmark-Based Input
- **Effort**: Medium-High (3-5 days)
- **Impact**: High (alternative modality for edge deployment)
- **Priority**: Low (specialist use case)
- **Files to create**: landmark_extraction.py
- **Files to modify**: dataset.py, evaluate.py, validation.py, config.py

---

**Implementation Recommendation**: Start with **Confidence Intervals** (quick win for observability), then **MSE/VA** (add rich emotional information), finally **PCK** (specialist use case).

