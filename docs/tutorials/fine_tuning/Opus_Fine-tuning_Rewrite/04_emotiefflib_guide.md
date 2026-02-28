# Tutorial 04: EmotiEffLib Integration Guide

## Overview

**EmotiEffLib** is the production-ready successor to HSEmotion. It provides a
unified Python API for facial emotion and engagement recognition with both
**PyTorch** and **ONNX Runtime** backends. This tutorial covers using EmotiEffLib
as a drop-in inference module and as a feature extractor for custom classifiers.

This is the quickest path from zero to working emotion recognition — no training
required for initial evaluation.

> **Repository**: [sb-ai-lab/EmotiEffLib](https://github.com/sb-ai-lab/EmotiEffLib)
> **PyPI**: `emotiefflib` (v1.1.1, Apache-2.0)
> **Documentation**: https://sb-ai-lab.github.io/EmotiEffLib/

---

## Installation

```bash
# PyTorch backend (recommended for GPU inference and fine-tuning)
pip install emotiefflib[torch]

# ONNX backend (lighter, CPU-friendly, no PyTorch dependency)
pip install emotiefflib

# Full installation (PyTorch + engagement detection)
pip install emotiefflib[all]
```

### Legacy packages (superseded by EmotiEffLib)

| Package | Status | Replacement |
|---------|--------|-------------|
| `hsemotion` | Legacy (v0.3.0, Dec 2022) | `emotiefflib[torch]` |
| `hsemotion-onnx` | Legacy (v0.3.1, Dec 2022) | `emotiefflib` (ONNX backend) |

---

## Available Models

```python
from emotiefflib.facial_analysis import get_model_list, get_supported_engines

print(get_model_list())
# ['enet_b0_8_best_vgaf', 'enet_b0_8_best_afew', 'enet_b2_8',
#  'enet_b0_8_va_mtl', 'enet_b2_7', 'mbf_va_mtl', 'mobilevit_va_mtl']

print(get_supported_engines())
# ['torch', 'onnx']
```

| Model | Backbone | Classes | Input | AffectNet Acc | Size |
|-------|----------|---------|-------|---------------|------|
| `enet_b0_8_best_vgaf` | EfficientNet-B0 | 8 | 224×224 | ~61% | ~20 MB |
| `enet_b0_8_best_afew` | EfficientNet-B0 | 8 | 224×224 | ~61% | ~20 MB |
| `enet_b0_8_va_mtl` | EfficientNet-B0 | 8+VA | 224×224 | ~60% | ~20 MB |
| `enet_b2_8` | EfficientNet-B2 | 8 | 260×260 | ~63% | ~30 MB |
| `enet_b2_7` | EfficientNet-B2 | 7 | 260×260 | ~66.5% | ~30 MB |
| `mbf_va_mtl` | MobileFaceNet | VA | 112×112 | — | ~14 MB |
| `mobilevit_va_mtl` | MobileViT | VA | 224×224 | — | — |

**Emotion labels (8-class)**: Anger, Contempt, Disgust, Fear, Happiness,
Neutral, Sadness, Surprise

**Emotion labels (7-class)**: Same without Contempt

---

## Quick Start: Single Image Emotion Recognition

```python
import cv2
import numpy as np
from emotiefflib.facial_analysis import EmotiEffLibRecognizer

# Initialize with PyTorch backend
recognizer = EmotiEffLibRecognizer(
    engine="torch",
    model_name="enet_b0_8_best_vgaf",
    device="cuda"  # or "cpu"
)

# Load a face crop (must be aligned/cropped face)
face_img = cv2.imread("face_crop.jpg")

# Predict emotion
emotion_labels, scores = recognizer.predict_emotions(face_img, logits=False)
print(f"Predicted emotion: {emotion_labels[0]}")
print(f"Confidence scores: {scores}")
```

### Using ONNX backend (no PyTorch needed)

```python
recognizer = EmotiEffLibRecognizer(
    engine="onnx",
    model_name="enet_b0_8_best_vgaf",
    device="cpu"
)

emotion_labels, scores = recognizer.predict_emotions(face_img)
```

---

## Feature Extraction for Custom Classifiers

The key value of EmotiEffLib for the Reachy project is using pretrained
backbones as **feature extractors** for a custom 2-class or 6-class head.

```python
# Extract features from a face image
features = recognizer.extract_features(face_img)
print(f"Feature shape: {features.shape}")  # (1, 1280) for B0, (1, 1408) for B2

# Classify from pre-extracted features
emotion, scores = recognizer.classify_emotions(features, logits=True)
```

### Building a custom 2-class classifier on top of EmotiEffLib features

```python
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from pathlib import Path

# 1. Extract features from all training images
train_features = []
train_labels = []

for cls_idx, cls_name in enumerate(['happy', 'sad']):
    cls_dir = Path('/videos/train') / cls_name
    for img_path in cls_dir.glob('*.jpg'):
        face = cv2.imread(str(img_path))
        feat = recognizer.extract_features(face)
        train_features.append(feat.flatten())
        train_labels.append(cls_idx)

X_train = np.array(train_features)
y_train = np.array(train_labels)

# 2. Train a simple classifier on the features
clf = LogisticRegression(max_iter=1000, C=1.0)
clf.fit(X_train, y_train)

# 3. Evaluate
val_features = []
val_labels = []
for cls_idx, cls_name in enumerate(['happy', 'sad']):
    cls_dir = Path('/videos/test') / cls_name
    for img_path in cls_dir.glob('*.jpg'):
        face = cv2.imread(str(img_path))
        feat = recognizer.extract_features(face)
        val_features.append(feat.flatten())
        val_labels.append(cls_idx)

X_val = np.array(val_features)
y_val = np.array(val_labels)

accuracy = clf.score(X_val, y_val)
print(f"2-class accuracy with EmotiEffLib features: {accuracy:.4f}")
```

---

## Video Emotion Recognition

EmotiEffLib supports video-level emotion analysis, demonstrated in the tutorial
notebook `Predict emotions on video.ipynb`.

```python
import cv2

# Process video frame by frame
cap = cv2.VideoCapture('input_video.mp4')
frame_emotions = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Assume face detection is done separately (e.g., MTCNN, RetinaFace)
    # face_crop = detect_and_crop_face(frame)
    face_crop = frame  # placeholder

    emotion, scores = recognizer.predict_emotions(face_crop, logits=False)
    frame_emotions.append({
        'emotion': emotion[0],
        'scores': scores.tolist()
    })

cap.release()

# Aggregate: majority vote or average scores
from collections import Counter
emotion_counts = Counter(e['emotion'] for e in frame_emotions)
dominant_emotion = emotion_counts.most_common(1)[0][0]
print(f"Dominant emotion in video: {dominant_emotion}")
```

---

## Engagement Detection

EmotiEffLib also provides engagement classification (requires the `engagement`
extra):

```python
pip install emotiefflib[all]
```

```python
# Engagement detection from a sequence of face images
face_sequence = [cv2.imread(f"frame_{i:04d}.jpg") for i in range(128)]
engagement = recognizer.predict_engagement(
    face_sequence,
    sliding_window_width=128
)
print(f"Engagement: {'Engaged' if engagement else 'Distracted'}")
```

---

## ONNX Export and TensorRT Conversion

### Export a model to ONNX

EmotiEffLib ships ONNX versions of all models in the repository under
`models/affectnet_emotions/onnx/`. For custom fine-tuned models, use the
provided converter:

```bash
# From the EmotiEffLib repository
python training_and_examples/convert_pt_to_onnx.py \
  --model_path models/affectnet_emotions/enet_b0_8_best_vgaf.pt \
  --output_path enet_b0_8_best_vgaf.onnx
```

### Convert to TensorRT for Jetson deployment

```bash
/usr/src/tensorrt/bin/trtexec \
  --onnx=enet_b0_8_best_vgaf.onnx \
  --saveEngine=enet_b0_8_best_vgaf_fp16.engine \
  --fp16 \
  --workspace=2048
```

This `.engine` file can be used in the DeepStream SGIE config as a drop-in
replacement for the TAO EmotionNet engine.

---

## Integration with the Reachy Pipeline

### As a validation/comparison tool

Use EmotiEffLib to cross-validate TAO EmotionNet predictions:

```python
from emotiefflib.facial_analysis import EmotiEffLibRecognizer

ref_model = EmotiEffLibRecognizer(
    engine="torch",
    model_name="enet_b0_8_best_vgaf",
    device="cuda"
)

# Compare TAO predictions with EmotiEffLib on the same test set
for img_path in test_images:
    face = cv2.imread(str(img_path))
    eff_emotion, eff_scores = ref_model.predict_emotions(face)
    # Compare with TAO model predictions...
```

### As a feature extractor for the training pipeline

Instead of training from ImageNet-pretrained ResNet-18 (TAO), use
EmotiEffLib's AffectNet-pretrained features as input to a lightweight
classifier:

```python
# Extract features once (offline), then train a simple head
# This is faster than full fine-tuning and often competitive
features = ref_model.extract_features(face_batch)
# Feed to sklearn, XGBoost, or a 2-layer MLP
```

---

## Key EmotiEffLib Tutorial Notebooks

These notebooks from the EmotiEffLib repository provide interactive guides:

| Notebook | Purpose | Location |
|----------|---------|----------|
| `One image emotion recognition.ipynb` | Single-image inference | `docs/tutorials/python/` |
| `Predict emotions on video.ipynb` | Frame-by-frame video processing | `docs/tutorials/python/` |
| `Predict engagement and emotions on video.ipynb` | Combined emotion + engagement | `docs/tutorials/python/` |
| `display_emotions.ipynb` | GradCAM visualization | `training_and_examples/` |
| `video_summarizer.ipynb` | Video analysis with face clustering | `training_and_examples/` |

---

## Next Steps

- For full fine-tuning (not just feature extraction), see
  [03_hsemotion_finetuning.md](03_hsemotion_finetuning.md).
- For audiovisual approaches, see
  [05_multimodal_emotion.md](05_multimodal_emotion.md).
- For choosing between approaches, see
  [06_model_comparison.md](06_model_comparison.md).
