# Guide 06: Evaluation & Gate A Validation

**Duration**: 2-3 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Guide 05 complete, training finished

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Understand all Gate A metrics
- [ ] Know how to run evaluation on a trained model
- [ ] Be able to interpret evaluation results
- [ ] Know what to do if Gate A fails

---

## 1. Gate A Requirements Recap

### What is Gate A?

**Gate A** is the quality checkpoint that models must pass before being considered for deployment. It ensures the model meets minimum performance standards.

### Gate A Thresholds

| Metric | Threshold | What it measures |
|--------|-----------|------------------|
| **Macro F1** | ≥ 0.84 | Overall classification quality |
| **Balanced Accuracy** | ≥ 0.85 | Performance across all classes |
| **Per-class F1** | ≥ 0.75 (floor: 0.70) | Each class performs well |
| **ECE** | ≤ 0.08 | Confidence calibration |
| **Brier Score** | ≤ 0.16 | Probability prediction quality |

### Why These Thresholds?

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WHY THESE THRESHOLDS?                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Macro F1 ≥ 0.84                                                    │
│  ─────────────────                                                  │
│  Industry standard for emotion recognition is 0.70-0.85.            │
│  0.84 ensures competitive performance with room for real-world      │
│  degradation.                                                        │
│                                                                      │
│  Balanced Accuracy ≥ 0.85                                           │
│  ────────────────────────                                           │
│  Prevents the model from ignoring rare classes. A model that        │
│  always predicts "happy" would have high accuracy but low           │
│  balanced accuracy.                                                  │
│                                                                      │
│  Per-class F1 ≥ 0.75                                                │
│  ────────────────────                                               │
│  Ensures no single class is poorly recognized. The robot needs      │
│  to respond appropriately to ALL emotions.                          │
│                                                                      │
│  ECE ≤ 0.08                                                         │
│  ──────────                                                         │
│  Confidence scores should match actual accuracy. If the model       │
│  says 90% confident, it should be right ~90% of the time.           │
│  Important for gesture intensity decisions.                         │
│                                                                      │
│  Brier ≤ 0.16                                                       │
│  ───────────                                                        │
│  Overall probability prediction quality. Lower is better.           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Understanding the Metrics

### Macro F1 Score

**F1** combines precision and recall into a single metric.

```
For each class:
    Precision = TP / (TP + FP)   "Of predictions, how many correct?"
    Recall    = TP / (TP + FN)   "Of actual, how many found?"
    F1        = 2 × (Precision × Recall) / (Precision + Recall)

Macro F1 = Average of F1 scores across all classes
```

**Example**:
```
Class     Precision  Recall   F1
─────────────────────────────────
happy     0.90       0.85     0.87
sad       0.82       0.88     0.85

Macro F1 = (0.87 + 0.85) / 2 = 0.86 ✅ (≥ 0.84)
```

### Balanced Accuracy

**Balanced Accuracy** = Average recall across all classes.

```
Balanced Accuracy = (Recall_happy + Recall_sad + Recall_neutral) / 3
                  = (0.85 + 0.88 + 0.865) / 3
                  = 0.865 ✅ (≥ 0.85)
```

**Why "balanced"?** It gives equal weight to each class, regardless of how many samples each has.

### Expected Calibration Error (ECE)

**ECE** measures if confidence scores match actual accuracy.

```
Bin predictions by confidence:
┌────────────────────────────────────────────────────────────────────┐
│ Confidence Bin │ Avg Confidence │ Actual Accuracy │ |Difference| │
├────────────────┼────────────────┼─────────────────┼──────────────┤
│ 0.5 - 0.6      │ 0.55           │ 0.52            │ 0.03         │
│ 0.6 - 0.7      │ 0.65           │ 0.61            │ 0.04         │
│ 0.7 - 0.8      │ 0.75           │ 0.73            │ 0.02         │
│ 0.8 - 0.9      │ 0.85           │ 0.82            │ 0.03         │
│ 0.9 - 1.0      │ 0.95           │ 0.91            │ 0.04         │
└────────────────┴────────────────┴─────────────────┴──────────────┘

ECE = Weighted average of |Difference| = 0.032 ✅ (≤ 0.08)
```

**Good calibration**: When model says 80% confident, it's right ~80% of the time.

### Brier Score

**Brier Score** = Mean squared error of probability predictions.

```
For each sample:
    True label (one-hot): [1, 0]  (happy)
    Predicted probs:      [0.85, 0.15]
    
    Squared error = (1-0.85)² + (0-0.15)² = 0.0225 + 0.0225 = 0.045

Brier = Average of squared errors across all samples
```

**Lower is better**. Perfect predictions would have Brier = 0.

---

## 3. Running Evaluation

### Using the Gate A Validator

```bash
# Run Gate A validation on a trained model
python trainer/gate_a_validator.py \
    --checkpoint outputs/checkpoints/best_model.pth \
    --test-dir data/val \
    --model-name my_model_v1
```

### Expected Output

```
============================================================
GATE A VALIDATION
============================================================
Model: my_model_v1
Checkpoint: outputs/checkpoints/best_model.pth

Evaluating model on test set...
Computing metrics...

============================================================
GATE A VALIDATION RESULTS
============================================================

Model: my_model_v1
Timestamp: 2026-01-28T23:45:00

--- Metrics ---
Macro F1:           0.8534 (threshold: 0.84)
Balanced Accuracy:  0.8612 (threshold: 0.85)
ECE:                0.0623 (threshold: 0.08)
Brier:              0.1234 (threshold: 0.16)

--- Per-class F1 ---
  ✅ happy: 0.8723
  ✅ sad: 0.8345

--- Gate Results ---
  macro_f1: ✅ PASS
  balanced_accuracy: ✅ PASS
  per_class_f1: ✅ PASS
  ece: ✅ PASS
  brier: ✅ PASS

============================================================
OVERALL: ✅ PASS
============================================================

Recommendations:
  • ✅ Model passes all Gate A requirements!

Results saved to: outputs/gate_a/gate_a_my_model_v1_20260128_234500.json
```

### Manual Evaluation Script

If you want more control:

```python
"""Manual evaluation script."""

import torch
import numpy as np
from pathlib import Path
from sklearn.metrics import f1_score, balanced_accuracy_score, confusion_matrix

from trainer.fer_finetune.model_efficientnet import load_pretrained_model
from trainer.fer_finetune.dataset import create_dataloaders

def evaluate_model(checkpoint_path, data_dir, class_names):
    """
    Evaluate a trained model and compute Gate A metrics.
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load model
    model = load_pretrained_model(
        checkpoint_path,
        num_classes=len(class_names),
        device=device,
    )
    model.eval()
    
    # Create data loader
    _, val_loader = create_dataloaders(
        data_dir=data_dir,
        batch_size=32,
        num_workers=4,
        input_size=224,
        class_names=class_names,
    )
    
    # Collect predictions
    all_true = []
    all_pred = []
    all_prob = []
    
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            
            outputs = model(images)
            logits = outputs['logits']
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            
            all_true.extend(labels.cpu().numpy())
            all_pred.extend(preds.cpu().numpy())
            all_prob.extend(probs.cpu().numpy())
    
    y_true = np.array(all_true)
    y_pred = np.array(all_pred)
    y_prob = np.array(all_prob)
    
    # Compute metrics
    metrics = {}
    
    # Macro F1
    metrics['macro_f1'] = f1_score(y_true, y_pred, average='macro')
    
    # Balanced Accuracy
    metrics['balanced_accuracy'] = balanced_accuracy_score(y_true, y_pred)
    
    # Per-class F1
    f1_per_class = f1_score(y_true, y_pred, average=None)
    for i, name in enumerate(class_names):
        metrics[f'f1_{name}'] = f1_per_class[i]
    
    # ECE
    metrics['ece'] = compute_ece(y_true, y_prob)
    
    # Brier
    metrics['brier'] = compute_brier(y_true, y_prob)
    
    # Confusion matrix
    metrics['confusion_matrix'] = confusion_matrix(y_true, y_pred)
    
    return metrics

def compute_ece(y_true, y_prob, n_bins=10):
    """Compute Expected Calibration Error."""
    y_pred = np.argmax(y_prob, axis=1)
    confidences = np.max(y_prob, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            ece += np.abs(avg_accuracy - avg_confidence) * prop_in_bin
    
    return ece

def compute_brier(y_true, y_prob):
    """Compute Brier Score."""
    n_samples, n_classes = y_prob.shape
    y_true_onehot = np.zeros((n_samples, n_classes))
    y_true_onehot[np.arange(n_samples), y_true] = 1
    return np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))

# Run evaluation
metrics = evaluate_model(
    'outputs/checkpoints/best_model.pth',
    'data',
    ['happy', 'sad', 'neutral'],
)

# Print results
print("\n=== EVALUATION RESULTS ===\n")
print(f"Macro F1:           {metrics['macro_f1']:.4f} (threshold: 0.84)")
print(f"Balanced Accuracy:  {metrics['balanced_accuracy']:.4f} (threshold: 0.85)")
print(f"ECE:                {metrics['ece']:.4f} (threshold: 0.08)")
print(f"Brier:              {metrics['brier']:.4f} (threshold: 0.16)")
print(f"\nPer-class F1:")
print(f"  happy: {metrics['f1_happy']:.4f}")
print(f"  sad:   {metrics['f1_sad']:.4f}")
print(f"  neutral: {metrics['f1_neutral']:.4f}")
print(f"\nConfusion Matrix:")
print(metrics['confusion_matrix'])
```

---

## 4. Interpreting Results

### Reading the Confusion Matrix

```
Confusion Matrix:
              Predicted
            happy    sad   neutral
Actual  happy  [45]     3        2
        sad      4    [43]       3
        neutral  2      5      [43]

Reading:
- 45 happy images correctly classified as happy
- 43 sad images correctly classified as sad
- 43 neutral images correctly classified as neutral
- Off-diagonal counts show confusion between emotion pairs

Diagonal = correct predictions (higher is better)
Off-diagonal = errors (lower is better)
```

### What the Numbers Mean

```
Results:
  Macro F1:           0.8534
  Balanced Accuracy:  0.8612
  ECE:                0.0623
  Brier:              0.1234

Interpretation:
  ✅ Macro F1 (0.8534) > 0.84
     → Good overall classification performance
  
  ✅ Balanced Accuracy (0.8612) > 0.85
     → Model performs well on all three classes
  
  ✅ ECE (0.0623) < 0.08
     → Confidence scores are well-calibrated
  
  ✅ Brier (0.1234) < 0.16
     → Probability predictions are accurate
```

---

## 5. What If Gate A Fails?

### Failure Scenarios and Solutions

#### Scenario 1: Low Macro F1

```
Macro F1: 0.78 ❌ (threshold: 0.84)
```

**Possible causes**:
- Not enough training data
- Training stopped too early
- Learning rate too low

**Solutions**:
1. Train for more epochs
2. Add more training data
3. Try higher learning rate
4. Unfreeze more backbone layers

#### Scenario 2: Low Balanced Accuracy

```
Balanced Accuracy: 0.80 ❌ (threshold: 0.85)
Per-class F1:
  happy: 0.92
  sad:   0.68  ← Problem!
```

**Possible causes**:
- Class imbalance in training data
- One class is harder to learn

**Solutions**:
1. Balance training data (equal samples per class)
2. Use class weights in loss function
3. Oversample minority class
4. Add more examples of the weak class

#### Scenario 3: High ECE (Poor Calibration)

```
ECE: 0.12 ❌ (threshold: 0.08)
```

**Possible causes**:
- Model is overconfident
- Not enough regularization

**Solutions**:
1. Increase label smoothing (0.1 → 0.2)
2. Apply temperature scaling (post-training)
3. Add more dropout
4. Use mixup augmentation

#### Scenario 4: One Class Failing

```
Per-class F1:
  happy: 0.88 ✅
  sad:   0.68 ❌ (floor: 0.70)
```

**Solutions**:
1. Add more training examples for "sad"
2. Check if "sad" images are clear and well-labeled
3. Analyze confusion matrix to see what "sad" is confused with
4. Try focal loss to focus on hard examples

### Temperature Scaling (for ECE)

If ECE is too high, apply temperature scaling after training:

```python
"""Temperature scaling for calibration."""

import torch
import torch.nn as nn
from torch.optim import LBFGS

class TemperatureScaler(nn.Module):
    """Learns a temperature parameter to calibrate probabilities."""
    
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1))
    
    def forward(self, logits):
        return logits / self.temperature

def calibrate_temperature(model, val_loader, device):
    """Learn optimal temperature on validation set."""
    
    # Collect all logits and labels
    all_logits = []
    all_labels = []
    
    model.eval()
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            outputs = model(images)
            all_logits.append(outputs['logits'].cpu())
            all_labels.append(labels)
    
    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels)
    
    # Optimize temperature
    scaler = TemperatureScaler()
    criterion = nn.CrossEntropyLoss()
    optimizer = LBFGS([scaler.temperature], lr=0.01, max_iter=50)
    
    def eval_loss():
        optimizer.zero_grad()
        scaled_logits = scaler(logits)
        loss = criterion(scaled_logits, labels)
        loss.backward()
        return loss
    
    optimizer.step(eval_loss)
    
    optimal_temp = scaler.temperature.item()
    print(f"Optimal temperature: {optimal_temp:.4f}")
    
    return optimal_temp

# Usage:
# optimal_temp = calibrate_temperature(model, val_loader, device)
# At inference: probs = softmax(logits / optimal_temp)
```

---

## 6. Evaluation Checklist

Before declaring Gate A passed:

| Check | Status |
|-------|--------|
| Macro F1 ≥ 0.84 | [ ] |
| Balanced Accuracy ≥ 0.85 | [ ] |
| All per-class F1 ≥ 0.70 | [ ] |
| ECE ≤ 0.08 | [ ] |
| Brier ≤ 0.16 | [ ] |
| Confusion matrix reviewed | [ ] |
| Results saved | [ ] |

---

## 7. Summary

### What You've Learned

1. ✅ All Gate A metrics and their meanings
2. ✅ How to run evaluation on a trained model
3. ✅ How to interpret evaluation results
4. ✅ What to do when specific metrics fail
5. ✅ Temperature scaling for calibration

### Key Commands

```bash
# Run Gate A validation
python trainer/gate_a_validator.py \
    --checkpoint outputs/checkpoints/best_model.pth \
    --test-dir data/val \
    --model-name my_model
```

### What's Next

In the final guide, we'll learn about exporting the model:
- Export to ONNX format
- Prepare for Jetson deployment
- Verify the exported model

---

*Next: [Guide 07: Export & Deployment](07_EXPORT_DEPLOYMENT.md)*
