# Tutorial 03: HSEmotion Fine-Tuning with PyTorch

## Overview

This tutorial covers fine-tuning emotion recognition models using the
**HSEmotion** library and its successor **EmotiEffLib** — both developed by
Andrey Savchenko at HSE University. These provide EfficientNet-based backbones
pretrained on AffectNet that outperform ResNet-18 on standard benchmarks while
being lighter and faster.

This is **Path B** from the [overview](01_overview.md).

> **Key advantage**: No Docker, no TAO containers — pure PyTorch training with
> `pip install` dependencies. The resulting ONNX model can be converted to
> TensorRT for the same Jetson DeepStream deployment.

---

## References

- **HSEmotion repository**: [av-savchenko/hsemotion](https://github.com/av-savchenko/hsemotion)
- **EmotiEffLib repository**: [sb-ai-lab/EmotiEffLib](https://github.com/sb-ai-lab/EmotiEffLib)
- **Training notebooks** (EmotiEffLib):
  - `training_and_examples/affectnet/train_emotions-pytorch.ipynb` — Main PyTorch training
  - `training_and_examples/affectnet/train_affectnet_march2021_pytorch.ipynb` — AffectNet training
  - `training_and_examples/affectnet/evaluate_affectnet_march2021_pytorch.ipynb` — Evaluation
  - `training_and_examples/affectnet/train_emotions-pytorch-afew-vgaf.ipynb` — AFEW + VGAF
  - `training_and_examples/AFEW_train.ipynb` — AFEW dataset
  - `training_and_examples/VGAF_train.ipynb` — VGAF dataset
  - `training_and_examples/display_emotions.ipynb` — GradCAM visualization
  - `training_and_examples/video_summarizer.ipynb` — Video emotion analysis
- **PyPI packages**: `hsemotion`, `hsemotion-onnx`, `emotiefflib`
- **Paper**: Savchenko, A.V. (2021). "Facial expression and attributes recognition based on multi-task learning of lightweight neural networks." *IEEE SISY*.

---

## Prerequisites

```bash
pip install torch torchvision timm
pip install hsemotion          # or: pip install emotiefflib[torch]
```

---

## Available Pretrained Models

### HSEmotion models

| Model | Backbone | Classes | Input Size | Dataset |
|-------|----------|---------|------------|---------|
| `enet_b0_8_best_vgaf` | EfficientNet-B0 | 8 | 224×224 | AffectNet + VGAF |
| `enet_b0_8_best_afew` | EfficientNet-B0 | 8 | 224×224 | AffectNet + AFEW |
| `enet_b2_8` | EfficientNet-B2 | 8 | 260×260 | AffectNet |
| `enet_b0_8_va_mtl` | EfficientNet-B0 | 8 | 224×224 | AffectNet (MTL) |
| `enet_b2_7` | EfficientNet-B2 | 7 | 260×260 | AffectNet |

### Emotion labels

**8-class**: Anger, Contempt, Disgust, Fear, Happiness, Neutral, Sadness, Surprise

**7-class**: Anger, Disgust, Fear, Happiness, Neutral, Sadness, Surprise

---

## Step 1: Load a Pretrained Model

### Using HSEmotion

```python
from hsemotion.facial_emotions import HSEmotionRecognizer

# Load pretrained model
model_name = 'enet_b0_8_best_vgaf'
recognizer = HSEmotionRecognizer(model_name=model_name, device='cuda')

# Quick inference on a face crop
import cv2
face_img = cv2.imread('face_crop.jpg')
emotion, scores = recognizer.predict_emotions(face_img)
print(f"Predicted: {emotion}, scores: {scores}")
```

### Using EmotiEffLib (recommended for new work)

```python
from emotiefflib.facial_analysis import EmotiEffLibRecognizer

recognizer = EmotiEffLibRecognizer(
    engine="torch",
    model_name="enet_b0_8_best_vgaf",
    device="cuda"
)

# Single image
emotion_labels, scores = recognizer.predict_emotions(face_img)
print(f"Predicted: {emotion_labels[0]}")

# Extract features (for custom classifiers)
features = recognizer.extract_features(face_img)
print(f"Feature dim: {features.shape}")  # (1, 1280) for EfficientNet-B0
```

---

## Step 2: Fine-Tune for Custom Emotion Classes

This section adapts the approach from the EmotiEffLib training notebooks to the
Reachy project's 2-class (happy/sad) and 6-class scenarios.

### 2.1 Prepare the dataset

```python
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from pathlib import Path
from PIL import Image

class EmotionDataset(Dataset):
    """Face emotion dataset compatible with HSEmotion preprocessing."""

    def __init__(self, root_dir, transform=None, classes=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.classes = classes or sorted([
            d.name for d in self.root_dir.iterdir() if d.is_dir()
        ])
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}

        self.samples = []
        for cls_name in self.classes:
            cls_dir = self.root_dir / cls_name
            for img_path in cls_dir.glob('*.jpg'):
                self.samples.append((img_path, self.class_to_idx[cls_name]))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, label


# Preprocessing must match HSEmotion's ImageNet normalization
IMG_SIZE = 224  # 260 for EfficientNet-B2

train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
    transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# Create datasets
classes_2 = ['happy', 'sad']
train_dataset = EmotionDataset('/videos/train', train_transform, classes_2)
val_dataset = EmotionDataset('/videos/test', val_transform, classes_2)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True,
                          num_workers=4, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False,
                        num_workers=4, pin_memory=True)
```

### 2.2 Load backbone and replace the classifier head

```python
import timm
import torch.nn as nn

def create_hsemotion_model(model_name, num_classes, pretrained_path=None):
    """
    Create an EfficientNet model with HSEmotion pretrained weights
    and a custom classification head.

    Based on the approach from:
    EmotiEffLib/training_and_examples/affectnet/train_emotions-pytorch.ipynb
    """
    # Load the EfficientNet backbone
    if 'b0' in model_name:
        backbone = timm.create_model('efficientnet_b0', pretrained=True)
        feature_dim = 1280
    elif 'b2' in model_name:
        backbone = timm.create_model('efficientnet_b2', pretrained=True)
        feature_dim = 1408
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    # Optionally load HSEmotion pretrained weights
    if pretrained_path:
        state_dict = torch.load(pretrained_path, map_location='cpu')
        # Handle mismatched classifier head
        state_dict = {k: v for k, v in state_dict.items()
                      if not k.startswith('classifier')}
        backbone.load_state_dict(state_dict, strict=False)

    # Replace the classifier head for our class count
    backbone.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(feature_dim, num_classes)
    )

    return backbone


# For 2-class (happy/sad)
model = create_hsemotion_model('enet_b0', num_classes=2)
model = model.cuda()
```

### 2.3 Training loop

The training approach follows the HSEmotion/EmotiEffLib notebooks, which use
label smoothing cross-entropy and optionally SAM (Sharpness-Aware Minimization)
for better generalization.

```python
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.metrics import f1_score, balanced_accuracy_score
import numpy as np


def train_hsemotion(model, train_loader, val_loader, num_classes,
                    num_epochs=40, lr=0.001, device='cuda'):
    """
    Train an HSEmotion-style model with the approach from the EmotiEffLib
    training notebooks.
    """
    # Loss with label smoothing (matches EmotiEffLib approach)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    # Two-phase fine-tuning:
    # Phase 1: Freeze backbone, train head only
    # Phase 2: Unfreeze all, train with lower LR

    # Phase 1: Frozen backbone
    for param in model.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True

    optimizer = optim.AdamW(model.classifier.parameters(),
                            lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=5, eta_min=lr * 0.01)

    print("Phase 1: Training classifier head (backbone frozen)")
    for epoch in range(5):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            running_loss += loss.item()
        scheduler.step()
        val_metrics = evaluate(model, val_loader, device)
        print(f"  Epoch {epoch+1}/5 - loss: {running_loss/len(train_loader):.4f} "
              f"- val_f1: {val_metrics['f1_macro']:.4f}")

    # Phase 2: Unfreeze all layers
    print("\nPhase 2: Fine-tuning all layers")
    for param in model.parameters():
        param.requires_grad = True

    optimizer = optim.AdamW(model.parameters(),
                            lr=lr * 0.1, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer,
                                  T_max=num_epochs - 5,
                                  eta_min=lr * 0.001)

    best_f1 = 0.0
    patience_counter = 0

    for epoch in range(num_epochs - 5):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            running_loss += loss.item()

        scheduler.step()
        val_metrics = evaluate(model, val_loader, device)

        print(f"  Epoch {epoch+6}/{num_epochs} - "
              f"loss: {running_loss/len(train_loader):.4f} - "
              f"val_f1: {val_metrics['f1_macro']:.4f} - "
              f"val_acc: {val_metrics['balanced_acc']:.4f}")

        # Save best model
        if val_metrics['f1_macro'] > best_f1:
            best_f1 = val_metrics['f1_macro']
            torch.save(model.state_dict(), 'best_model.pth')
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= 10:
                print(f"  Early stopping at epoch {epoch+6}")
                break

    print(f"\nBest validation F1: {best_f1:.4f}")
    return model


def evaluate(model, val_loader, device='cuda'):
    """Evaluate model and return metrics matching Gate A requirements."""
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            outputs = model(images)
            preds = outputs.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    return {
        'f1_macro': f1_score(all_labels, all_preds, average='macro'),
        'f1_per_class': f1_score(all_labels, all_preds, average=None),
        'balanced_acc': balanced_accuracy_score(all_labels, all_preds),
        'accuracy': (all_preds == all_labels).mean(),
    }


# Run training
model = train_hsemotion(model, train_loader, val_loader, num_classes=2)
```

---

## Step 3: Export to ONNX

```python
import torch.onnx

# Load best checkpoint
model.load_state_dict(torch.load('best_model.pth'))
model.eval()

# Export
dummy_input = torch.randn(1, 3, 224, 224).cuda()
torch.onnx.export(
    model,
    dummy_input,
    'emotionnet_hsemotion_2cls.onnx',
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={
        'input': {0: 'batch_size'},
        'output': {0: 'batch_size'}
    },
    opset_version=13
)

print("ONNX model exported: emotionnet_hsemotion_2cls.onnx")
```

### Using EmotiEffLib's built-in converter

EmotiEffLib also provides a conversion script:

```bash
# From the EmotiEffLib repository
python training_and_examples/convert_pt_to_onnx.py \
  --model_path best_model.pth \
  --output_path emotionnet_hsemotion_2cls.onnx
```

---

## Step 4: Convert to TensorRT for Jetson

```bash
# On the Jetson (or using the TAO export container)
/usr/src/tensorrt/bin/trtexec \
  --onnx=emotionnet_hsemotion_2cls.onnx \
  --saveEngine=emotionnet_hsemotion_2cls_fp16.engine \
  --fp16 \
  --workspace=2048 \
  --minShapes=input:1x3x224x224 \
  --optShapes=input:1x3x224x224 \
  --maxShapes=input:16x3x224x224
```

The resulting `.engine` file slots directly into the DeepStream SGIE config —
the same deployment path as the TAO-exported model.

---

## Step 5: Integration with MLflow

Log the HSEmotion training run using the existing MLflow tracker:

```python
from trainer.mlflow_tracker import MLflowTracker

tracker = MLflowTracker(experiment_name='hsemotion_2cls')
tracker.start_training(
    run_id='hsemotion_enet_b0_2cls_001',
    config={
        'model_arch': 'efficientnet_b0',
        'num_classes': 2,
        'batch_size': 32,
        'learning_rate': 0.001,
        'num_epochs': 40,
        'optimizer': 'adamw',
        'backbone': 'hsemotion_enet_b0_8_best_vgaf',
    },
    tags={'training_path': 'hsemotion', 'config_file': 'none'}
)

# After training, log the ONNX model
tracker.log_model('emotionnet_hsemotion_2cls.onnx', model_name='hsemotion')

# Log gate results
tracker.log_validation_results(
    gate_name='gate_a',
    passed=True,
    metrics={'f1_macro': 0.88, 'balanced_accuracy': 0.87}
)

tracker.end_training(status='FINISHED')
```

---

## Key Notebooks from the HSEmotion / EmotiEffLib Ecosystem

For a more interactive development experience, adapt these notebooks from the
EmotiEffLib repository:

| Notebook | Purpose | Location in EmotiEffLib repo |
|----------|---------|---------------------------|
| `train_emotions-pytorch.ipynb` | Core training loop with EfficientNet | `training_and_examples/affectnet/` |
| `evaluate_affectnet_march2021_pytorch.ipynb` | Evaluation and metrics | `training_and_examples/affectnet/` |
| `display_emotions.ipynb` | GradCAM visualization of model attention | `training_and_examples/` |
| `AFEW_train.ipynb` | Video-based training (AFEW dataset) | `training_and_examples/` |
| `VGAF_train.ipynb` | Video-based training (VGAF dataset) | `training_and_examples/` |
| `video_summarizer.ipynb` | Emotion analysis across video clips | `training_and_examples/` |

### Adapting EmotiEffLib notebooks for Reachy

1. Replace the AffectNet data paths with `/videos/train` and `/videos/test`.
2. Change `num_classes` from 8 to 2 (or 6).
3. Update the class labels to match the Reachy config.
4. Add MLflow logging calls (see above).
5. Export to ONNX at the end of training.

---

## Comparison with TAO Path

| Aspect | TAO EmotionNet | HSEmotion fine-tune |
|--------|---------------|---------------------|
| Backbone | ResNet-18 | EfficientNet-B0/B2 |
| Pretrained on | ImageNet | AffectNet (emotion-specific) |
| Parameters | ~11M | ~5M (B0) / ~9M (B2) |
| Infrastructure | Docker + TAO 4.x | pip install + PyTorch |
| Export path | TAO → .etlt → TRT | PyTorch → ONNX → TRT |
| Iteration speed | Slower (container startup) | Faster (native Python) |
| DeepStream compat | Direct | Via ONNX → trtexec |

---

## Next Steps

- For a drop-in inference API without training, see
  [04_emotiefflib_guide.md](04_emotiefflib_guide.md).
- For audiovisual approaches, see
  [05_multimodal_emotion.md](05_multimodal_emotion.md).
- For a full comparison table, see
  [06_model_comparison.md](06_model_comparison.md).
