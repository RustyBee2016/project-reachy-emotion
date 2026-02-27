# Tutorial Companion: Phase 1 Lesson Series for `enet_b0_8_best_vgaf`

**Audience**: Junior ML engineers (with Rusty as technical lead)  
**Scope**: **Phase 1 only** — offline model fine-tuning and evaluation in PyTorch  
**Source tutorial**: [`03_hsemotion_finetuning.md`](03_hsemotion_finetuning.md)  
**Model focus**: `enet_b0_8_best_vgaf` (EfficientNet-B0 pretrained with HSEmotion weights)

---

## How to use this lesson series

This companion breaks the original tutorial into **5 teachable lessons**. Each lesson:

1. Defines learning goals.
2. Walks through the code line by line.
3. Explains Python syntax + ML logic + control flow.
4. Ends with common mistakes and a practical assignment.

> We intentionally skip deployment-specific work (Jetson/TensorRT/DeepStream), because Phase 1 is strictly offline classification.

---

## Lesson 1 — Understand the pretrained model and run a first forward pass

### Learning goals

By the end of this lesson, engineers should be able to:
- Explain what `enet_b0_8_best_vgaf` is.
- Load the model in Python.
- Run one inference on a face crop.
- Interpret outputs (`emotion`, `scores`).

### Code walkthrough (from Step 1)

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

### Line-by-line explanation

1. `from hsemotion.facial_emotions import HSEmotionRecognizer`
   - Python `import` statement.
   - Brings in a class that wraps model loading + preprocessing + inference.

2. `model_name = 'enet_b0_8_best_vgaf'`
   - Stores the exact model identifier in a variable.
   - This is not just a label: it controls which pretrained checkpoint is loaded.

3. `recognizer = HSEmotionRecognizer(model_name=model_name, device='cuda')`
   - Constructs an object instance.
   - `model_name=model_name` uses a keyword argument; this is clearer than positional order.
   - `device='cuda'` places model tensors on GPU.
   - If no GPU, use `device='cpu'`.

4. `import cv2`
   - Imports OpenCV for image I/O.

5. `face_img = cv2.imread('face_crop.jpg')`
   - Reads image from disk into a NumPy array (BGR channel order).
   - Returns `None` if path is wrong; always validate this in production code.

6. `emotion, scores = recognizer.predict_emotions(face_img)`
   - Calls recognizer inference method.
   - Tuple unpacking: first value → `emotion` (best class), second → `scores` (per-class confidences/logits depending on implementation).

7. `print(f"Predicted: {emotion}, scores: {scores}")`
   - f-string interpolation for readable logging.

### Control-flow understanding

There is no explicit loop here. The flow is:
1. Import dependency.
2. Initialize recognizer.
3. Read one image.
4. Infer once.
5. Print result.

### Common mistakes

- Forgetting GPU fallback (`device='cpu'`) on machines without CUDA.
- Passing full-scene image instead of face crop.
- Wrong image path causing `face_img=None`.

### Assignment

- Run inference on 10 face crops and write a small script that logs:
  - file name,
  - top emotion,
  - top score.

---

## Lesson 2 — Build a dataset class and data loaders correctly

### Learning goals

Engineers should be able to:
- Explain why we subclass `Dataset`.
- Understand `__len__` and `__getitem__` roles.
- Build transforms that match EfficientNet-B0 expectations.
- Create `DataLoader` objects for train/validation.

### Code walkthrough (from Step 2.1)

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
```

### Line-by-line explanation

- `class EmotionDataset(Dataset):`
  - Inheritance: your class extends PyTorch's dataset API.

- `def __init__(...)`:
  - Constructor called once when object is created.
  - `root_dir`: dataset root (`/videos/train`, `/videos/test`, etc.).
  - `transform=None`: optional preprocessing pipeline.
  - `classes=None`: if omitted, infer folder names.

- `self.root_dir = Path(root_dir)`
  - Uses `pathlib` object for safer path operations.

- `self.classes = classes or sorted([...])`
  - Python short-circuiting: use `classes` if provided; otherwise infer from subdirectories.
  - `sorted(...)` ensures deterministic class order.

- `self.class_to_idx = {c: i for i, c in enumerate(self.classes)}`
  - Dictionary comprehension mapping class names to integer labels.
  - Example: `{'happy': 0, 'sad': 1, 'neutral': 2}`.

- Building `self.samples`:
  - Outer loop iterates classes.
  - Inner loop scans all JPG files in each class folder.
  - Appends tuple `(image_path, numeric_label)`.

- `__len__`:
  - Returns total number of samples.
  - Used by DataLoader to know epoch length.

- `__getitem__(self, idx)`:
  - Fetches one sample by index.
  - Opens image with PIL and converts to RGB.
  - Applies transforms if provided.
  - Returns `(image_tensor, label_int)`.

### Transform and loader walkthrough

```python
IMG_SIZE = 224

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

classes_3 = ['happy', 'sad', 'neutral']
train_dataset = EmotionDataset('/videos/train', train_transform, classes_3)
val_dataset = EmotionDataset('/videos/test', val_transform, classes_3)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True,
                          num_workers=4, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False,
                        num_workers=4, pin_memory=True)
```

### Important Phase 1 adaptation

The original tutorial shows `classes_2 = ['happy', 'sad']` as an example. For Reachy Phase 1 training targets, use **3-class**:

- `happy`
- `sad`
- `neutral`

### Common mistakes

- Inconsistent class order between train and val.
- Forgetting ImageNet normalization values.
- Wrong directory layout (`root/class_name/*.jpg`).

### Assignment

- Print `len(train_dataset)` and first 3 samples.
- Verify label mapping manually (`class_to_idx`).

---

## Lesson 3 — Create the model and swap the classifier head safely

### Learning goals

Engineers should be able to:
- Explain backbone vs head.
- Use `timm` to instantiate EfficientNet-B0.
- Replace classification head for new class count.
- Understand optional pretrained checkpoint loading.

### Code walkthrough (from Step 2.2)

```python
import timm
import torch.nn as nn


def create_hsemotion_model(model_name, num_classes, pretrained_path=None):
    if 'b0' in model_name:
        backbone = timm.create_model('efficientnet_b0', pretrained=True)
        feature_dim = 1280
    elif 'b2' in model_name:
        backbone = timm.create_model('efficientnet_b2', pretrained=True)
        feature_dim = 1408
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    if pretrained_path:
        state_dict = torch.load(pretrained_path, map_location='cpu')
        state_dict = {k: v for k, v in state_dict.items()
                      if not k.startswith('classifier')}
        backbone.load_state_dict(state_dict, strict=False)

    backbone.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(feature_dim, num_classes)
    )

    return backbone


model = create_hsemotion_model('enet_b0', num_classes=3)
model = model.cuda()
```

### Line-by-line explanation

- `import timm`
  - External model zoo used to create EfficientNet variants.

- `import torch.nn as nn`
  - Namespace alias for neural network layers.

- `def create_hsemotion_model(...):`
  - Factory function: encapsulates model construction logic.

- `if 'b0' in model_name:`
  - String check decides which backbone to use.
  - For this phase, we expect B0 path.

- `backbone = timm.create_model('efficientnet_b0', pretrained=True)`
  - Builds EfficientNet-B0 with pretrained weights (ImageNet when used directly via timm).

- `feature_dim = 1280`
  - Number of features feeding the classifier layer for B0.

- `if pretrained_path:` block
  - Optional: load a custom checkpoint from disk.
  - `map_location='cpu'` allows loading even without GPU.
  - Dictionary comprehension filters out old classifier keys to avoid size mismatch.
  - `strict=False` tolerates missing/new keys.

- Replacing head:
  - `nn.Dropout(p=0.3)` regularization.
  - `nn.Linear(feature_dim, num_classes)` final logits layer.

- `return backbone`
  - Returns configured model object.

- `model = ... num_classes=3`
  - Phase 1 class count should be 3.

- `model = model.cuda()`
  - Move all model parameters to GPU memory.

### Common mistakes

- Setting wrong `num_classes` (must match dataset labels).
- Not filtering old classifier weights when loading checkpoint.
- Hardcoding B2 dims for a B0 model.

### Assignment

- Print `model.classifier` and confirm output dimension equals 3.

---

## Lesson 4 — Train in two phases and evaluate correctly

### Learning goals

Engineers should be able to:
- Explain why we freeze then unfreeze.
- Read and modify training loop structure.
- Understand optimizer/scheduler/loss interactions.
- Compute F1 and balanced accuracy for Gate A context.

### Code walkthrough (from Step 2.3)

```python
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
```
- Multiclass loss.
- `label_smoothing=0.1` softens targets to improve generalization.

```python
for param in model.parameters():
    param.requires_grad = False
for param in model.classifier.parameters():
    param.requires_grad = True
```
- Freeze all layers first.
- Unfreeze only classifier head (phase 1 within training).

```python
optimizer = optim.AdamW(model.classifier.parameters(), lr=lr, weight_decay=0.01)
scheduler = CosineAnnealingLR(optimizer, T_max=5, eta_min=lr * 0.01)
```
- AdamW updates only trainable params passed to it.
- Cosine LR gradually decays over 5 epochs.

```python
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
```
- Outer loop = epoch loop.
- Inner loop = mini-batch loop.
- Standard update order:
  1. move tensors to device,
  2. clear grads,
  3. forward pass,
  4. compute loss,
  5. backward pass,
  6. gradient clipping,
  7. optimizer step.

Then phase 2:

```python
for param in model.parameters():
    param.requires_grad = True
optimizer = optim.AdamW(model.parameters(), lr=lr * 0.1, weight_decay=0.01)
```
- Unfreeze whole network.
- Lower LR (10x smaller) to avoid destroying pretrained features.

Early stopping logic:

```python
if val_metrics['f1_macro'] > best_f1:
    best_f1 = val_metrics['f1_macro']
    torch.save(model.state_dict(), 'best_model.pth')
    patience_counter = 0
else:
    patience_counter += 1
    if patience_counter >= 10:
        break
```
- Keep best checkpoint by validation macro-F1.
- Stop after 10 non-improving epochs.

### Evaluation function logic

- `model.eval()` switches off training-only behavior (e.g., dropout randomness).
- `torch.no_grad()` disables gradient tracking for faster inference.
- `argmax(dim=1)` converts logits to predicted class index.
- Metrics returned:
  - `f1_macro`
  - `f1_per_class`
  - `balanced_acc`
  - `accuracy`

### Common mistakes

- Forgetting `model.eval()` during validation.
- Not moving labels to same device for loss computation.
- Measuring only accuracy (not enough for imbalanced classes).

### Assignment

- Add one print statement per epoch showing current learning rate.

---

## Lesson 5 — Save artifacts and track experiments (Phase 1 only)

### Learning goals

Engineers should be able to:
- Export trained model to ONNX for reproducibility and downstream use.
- Log training metadata and metrics to MLflow.
- Keep all steps local and auditable.

### ONNX export walkthrough (from Step 3)

```python
model.load_state_dict(torch.load('best_model.pth'))
model.eval()

dummy_input = torch.randn(1, 3, 224, 224).cuda()
torch.onnx.export(
    model,
    dummy_input,
    'emotionnet_hsemotion_3cls.onnx',
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={
        'input': {0: 'batch_size'},
        'output': {0: 'batch_size'}
    },
    opset_version=13
)
```

- Load best checkpoint first.
- `dummy_input` defines input tensor shape contract.
- `dynamic_axes` keeps batch dimension flexible.
- Output file name should reflect Phase 1 class count (`3cls`).

### MLflow logging walkthrough (from Step 5)

```python
from trainer.mlflow_tracker import MLflowTracker

tracker = MLflowTracker(experiment_name='hsemotion_3cls')
tracker.start_training(
    run_id='hsemotion_enet_b0_3cls_001',
    config={
        'model_arch': 'efficientnet_b0',
        'num_classes': 3,
        'batch_size': 32,
        'learning_rate': 0.001,
        'num_epochs': 40,
        'optimizer': 'adamw',
        'backbone': 'hsemotion_enet_b0_8_best_vgaf',
    },
    tags={'training_path': 'hsemotion', 'phase': 'phase_1_offline'}
)
```

- Use explicit config dictionary for reproducibility.
- Ensure `num_classes=3` for Reachy Phase 1.
- Tag run as offline/phase 1 for traceability.

Complete run logging:

```python
tracker.log_model('emotionnet_hsemotion_3cls.onnx', model_name='hsemotion')
tracker.log_validation_results(
    gate_name='gate_a',
    passed=True,
    metrics={'f1_macro': 0.88, 'balanced_accuracy': 0.87}
)
tracker.end_training(status='FINISHED')
```

### Common mistakes

- Exporting before loading best checkpoint.
- Mismatch between trained class count and ONNX filename.
- Forgetting to close MLflow run (`end_training`).

### Assignment

- Produce one MLflow run that logs:
  - training config,
  - best macro-F1,
  - ONNX artifact,
  - Gate A pass/fail decision.

---

## Suggested training schedule for Rusty's junior team

- **Day 1**: Lesson 1 + Lesson 2 (data + first inference)
- **Day 2**: Lesson 3 (model surgery/head replacement)
- **Day 3**: Lesson 4 (full training loop)
- **Day 4**: Lesson 5 (artifacts + experiment tracking)
- **Day 5**: Practical dry-run from clean environment and peer code review

---

## Final checklist (Phase 1)

Before a junior engineer marks training complete, they must confirm:

- [ ] Model is `enet_b0_8_best_vgaf`-based EfficientNet-B0.
- [ ] Class list is exactly `['happy', 'sad', 'neutral']`.
- [ ] Two-phase fine-tuning ran successfully.
- [ ] Best checkpoint is saved (`best_model.pth`).
- [ ] ONNX exported with 224×224 input and dynamic batch axis.
- [ ] MLflow run includes config + metrics + artifact.

