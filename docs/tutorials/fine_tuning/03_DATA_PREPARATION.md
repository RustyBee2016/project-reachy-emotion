# Guide 03: Data Preparation

**Duration**: 2-3 hours  
**Difficulty**: Beginner  
**Prerequisites**: Guide 02 complete (environment set up)

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Understand the required data format
- [ ] Know how to organize images for training
- [ ] Understand train/validation splits
- [ ] Know what data augmentation is and why it helps
- [ ] Be able to create data loaders

---

## 1. Data Format Requirements

### Directory Structure

The training code expects images organized by class:

```
data/
├── train/                  # Training images (80% of data)
│   ├── happy/              # Class folder
│   │   ├── image_001.jpg
│   │   ├── image_002.jpg
│   │   └── ...
│   └── sad/                # Class folder
│       ├── image_001.jpg
│       ├── image_002.jpg
│       └── ...
│
└── val/                    # Validation images (20% of data)
    ├── happy/
    │   ├── image_101.jpg
    │   └── ...
    └── sad/
        ├── image_101.jpg
        └── ...
```

### Image Requirements

| Requirement | Specification |
|-------------|---------------|
| Format | JPG, PNG, or JPEG |
| Size | Any (will be resized to 224×224) |
| Color | RGB (3 channels) |
| Content | Face clearly visible |
| Quality | Reasonably clear (not too blurry) |

### Minimum Data Requirements

| Configuration | Minimum per class | Recommended per class |
|---------------|-------------------|----------------------|
| 2-class (happy/sad) | 100 images | 500+ images |
| 8-class (all emotions) | 50 images | 200+ images |

**More data = better results** (generally)

---

## 2. Understanding Train/Val Split

### Why Split the Data?

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WHY TRAIN/VAL SPLIT?                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Training Data (80%)              Validation Data (20%)            │
│   ─────────────────────            ────────────────────             │
│   Model LEARNS from this           Model is TESTED on this          │
│                                                                      │
│   ┌─────────────────┐              ┌─────────────────┐              │
│   │ Adjust weights  │              │ Check if model  │              │
│   │ to minimize     │              │ generalizes to  │              │
│   │ errors          │              │ unseen data     │              │
│   └─────────────────┘              └─────────────────┘              │
│                                                                      │
│   If we only used training data:                                    │
│   - Model might MEMORIZE training images                            │
│   - Would fail on new images (overfitting)                          │
│                                                                      │
│   Validation data tells us if the model actually learned            │
│   the CONCEPT of emotions, not just memorized examples.             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Split Guidelines

| Split | Percentage | Purpose |
|-------|------------|---------|
| Train | 80% | Model learns from these |
| Validation | 20% | Check generalization |

**Important**: Never use validation images for training!

---

## 3. Organizing Your Data

### Step 3.1: Create Directory Structure

```bash
# Navigate to project
cd /path/to/reachy_emotion

# Create data directories
mkdir -p data/train/happy
mkdir -p data/train/sad
mkdir -p data/val/happy
mkdir -p data/val/sad

# Verify structure
tree data/
```

### Step 3.2: Copy Images to Folders

If you have images in a flat directory:

```bash
# Example: Move happy images to train folder
# (Adjust paths to your actual image locations)

# Copy 80% to train, 20% to val
# This is a simple example - you may need to adjust

# For happy images
cp /source/happy/image_*.jpg data/train/happy/  # First 80%
cp /source/happy/image_*.jpg data/val/happy/    # Last 20%

# For sad images
cp /source/sad/image_*.jpg data/train/sad/
cp /source/sad/image_*.jpg data/val/sad/
```

### Step 3.3: Automated Split Script

For a proper random split, use this script:

```python
#!/usr/bin/env python3
"""
Split images into train/val sets.

Usage:
    python split_data.py --source /path/to/images --dest data/ --split 0.8
"""

import os
import shutil
import random
import argparse
from pathlib import Path

def split_data(source_dir, dest_dir, train_ratio=0.8, seed=42):
    """
    Split images from source into train/val in dest.
    
    Args:
        source_dir: Directory with class subfolders
        dest_dir: Destination directory
        train_ratio: Fraction for training (default 0.8)
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    
    source = Path(source_dir)
    dest = Path(dest_dir)
    
    # Create destination directories
    (dest / 'train').mkdir(parents=True, exist_ok=True)
    (dest / 'val').mkdir(parents=True, exist_ok=True)
    
    # Process each class folder
    for class_dir in source.iterdir():
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        print(f"Processing class: {class_name}")
        
        # Create class folders in train and val
        (dest / 'train' / class_name).mkdir(exist_ok=True)
        (dest / 'val' / class_name).mkdir(exist_ok=True)
        
        # Get all images
        images = list(class_dir.glob('*.jpg')) + \
                 list(class_dir.glob('*.jpeg')) + \
                 list(class_dir.glob('*.png'))
        
        # Shuffle
        random.shuffle(images)
        
        # Split
        split_idx = int(len(images) * train_ratio)
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # Copy to destinations
        for img in train_images:
            shutil.copy(img, dest / 'train' / class_name / img.name)
        
        for img in val_images:
            shutil.copy(img, dest / 'val' / class_name / img.name)
        
        print(f"  Train: {len(train_images)}, Val: {len(val_images)}")
    
    print("\nDone!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Source directory')
    parser.add_argument('--dest', required=True, help='Destination directory')
    parser.add_argument('--split', type=float, default=0.8, help='Train ratio')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    split_data(args.source, args.dest, args.split, args.seed)
```

Save as `scripts/split_data.py` and run:

```bash
python scripts/split_data.py --source /path/to/raw_images --dest data/ --split 0.8
```

---

## 4. Verify Your Data

### Step 4.1: Count Images

```bash
# Count images per class
echo "Training data:"
find data/train -name "*.jpg" -o -name "*.png" | wc -l
for class in data/train/*/; do
    echo "  $(basename $class): $(ls $class | wc -l)"
done

echo "Validation data:"
find data/val -name "*.jpg" -o -name "*.png" | wc -l
for class in data/val/*/; do
    echo "  $(basename $class): $(ls $class | wc -l)"
done
```

Expected output:
```
Training data:
800
  happy: 400
  sad: 400
Validation data:
200
  happy: 100
  sad: 100
```

### Step 4.2: Check Class Balance

```python
# Run this to check balance
from pathlib import Path

data_dir = Path('data')

for split in ['train', 'val']:
    print(f"\n{split.upper()} split:")
    split_dir = data_dir / split
    
    total = 0
    counts = {}
    
    for class_dir in sorted(split_dir.iterdir()):
        if class_dir.is_dir():
            count = len(list(class_dir.glob('*')))
            counts[class_dir.name] = count
            total += count
    
    for class_name, count in counts.items():
        pct = count / total * 100
        print(f"  {class_name}: {count} ({pct:.1f}%)")
    
    # Check balance
    min_count = min(counts.values())
    max_count = max(counts.values())
    ratio = min_count / max_count
    
    if ratio < 0.5:
        print(f"  ⚠️ WARNING: Imbalanced classes (ratio: {ratio:.2f})")
    else:
        print(f"  ✅ Classes reasonably balanced (ratio: {ratio:.2f})")
```

### Step 4.3: Visualize Sample Images

```python
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
import random

def show_samples(data_dir, n_samples=3):
    """Show sample images from each class."""
    data_dir = Path(data_dir)
    
    classes = sorted([d.name for d in (data_dir / 'train').iterdir() if d.is_dir()])
    n_classes = len(classes)
    
    fig, axes = plt.subplots(n_classes, n_samples, figsize=(n_samples*3, n_classes*3))
    
    for i, class_name in enumerate(classes):
        class_dir = data_dir / 'train' / class_name
        images = list(class_dir.glob('*'))
        samples = random.sample(images, min(n_samples, len(images)))
        
        for j, img_path in enumerate(samples):
            img = Image.open(img_path)
            axes[i, j].imshow(img)
            axes[i, j].axis('off')
            if j == 0:
                axes[i, j].set_title(class_name, fontsize=14)
    
    plt.tight_layout()
    plt.savefig('data_samples.png')
    plt.show()
    print("Saved to data_samples.png")

show_samples('data')
```

---

## 5. Data Augmentation

### What is Data Augmentation?

**Data augmentation** = Creating variations of training images to:
- Increase effective dataset size
- Make model more robust
- Prevent overfitting

```
Original Image          Augmented Versions
┌─────────────┐         ┌─────────────┐  ┌─────────────┐
│             │         │   Flipped   │  │   Rotated   │
│    😊       │  ───▶   │     😊      │  │      😊     │
│             │         │             │  │       ↻     │
└─────────────┘         └─────────────┘  └─────────────┘
                        
                        ┌─────────────┐  ┌─────────────┐
                        │   Brighter  │  │   Cropped   │
                        │     😊      │  │    😊       │
                        │      ☀️     │  │             │
                        └─────────────┘  └─────────────┘
```

### Augmentations We Use

| Augmentation | What it does | Why it helps |
|--------------|--------------|--------------|
| Horizontal Flip | Mirror image left-right | Faces can face either direction |
| Random Rotation | Rotate ±15 degrees | Heads aren't always straight |
| Color Jitter | Adjust brightness/contrast | Different lighting conditions |
| Random Crop | Crop and resize | Different face positions |
| Gaussian Blur | Slight blur | Handle lower quality video |

### Augmentation in Code

The training code applies augmentation automatically. Here's what happens:

```python
# From trainer/fer_finetune/dataset.py (simplified)

import albumentations as A
from albumentations.pytorch import ToTensorV2

def get_train_transforms(input_size=224):
    """Augmentation for training images."""
    return A.Compose([
        # Resize to slightly larger, then crop
        A.Resize(int(input_size * 1.1), int(input_size * 1.1)),
        A.RandomCrop(input_size, input_size),
        
        # Geometric transforms
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=15, p=0.3),
        
        # Color transforms
        A.ColorJitter(
            brightness=0.2,
            contrast=0.2,
            saturation=0.2,
            hue=0.1,
            p=0.5
        ),
        
        # Blur (simulates low quality)
        A.GaussianBlur(blur_limit=(3, 5), p=0.1),
        
        # Normalize to ImageNet stats
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
        
        # Convert to PyTorch tensor
        ToTensorV2(),
    ])

def get_val_transforms(input_size=224):
    """No augmentation for validation - just resize and normalize."""
    return A.Compose([
        A.Resize(input_size, input_size),
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
        ToTensorV2(),
    ])
```

**Note**: Validation images are NOT augmented - we want consistent evaluation.

---

## 6. Creating Data Loaders

### What is a Data Loader?

A **data loader** feeds batches of images to the model during training:

```
Dataset (1000 images)
        │
        │  DataLoader (batch_size=32)
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Batch 1      Batch 2      Batch 3      ...      Batch 31          │
│  [32 imgs]    [32 imgs]    [32 imgs]             [32 imgs]         │
└─────────────────────────────────────────────────────────────────────┘
        │
        │  Each batch is processed by GPU
        ▼
    Model Training
```

### Test Data Loading

```python
"""Test that data loading works correctly."""

from pathlib import Path
import torch
from trainer.fer_finetune.dataset import create_dataloaders

# Create data loaders
train_loader, val_loader = create_dataloaders(
    data_dir='data',
    batch_size=32,
    num_workers=4,
    input_size=224,
    class_names=['happy', 'sad'],
)

print(f"Training batches: {len(train_loader)}")
print(f"Validation batches: {len(val_loader)}")

# Get one batch
images, labels = next(iter(train_loader))

print(f"\nBatch shape: {images.shape}")
print(f"Labels shape: {labels.shape}")
print(f"Label values: {labels[:10]}")

# Verify image normalization
print(f"\nImage stats:")
print(f"  Min: {images.min():.3f}")
print(f"  Max: {images.max():.3f}")
print(f"  Mean: {images.mean():.3f}")
```

Expected output:
```
Training batches: 25
Validation batches: 7

Batch shape: torch.Size([32, 3, 224, 224])
Labels shape: torch.Size([32])
Label values: tensor([0, 1, 0, 1, 1, 0, 0, 1, 1, 0])

Image stats:
  Min: -2.118
  Max: 2.640
  Mean: 0.012
```

---

## 7. Using Synthetic Data (Optional)

If you don't have enough real data, you can generate synthetic images:

### From Reachy's Video Generation

The Reachy project can generate synthetic emotion videos using Luma AI:

```bash
# Generate videos through the web UI
# Then extract frames for training

# Extract frames from video
ffmpeg -i video.mp4 -vf "fps=1" frames/frame_%04d.jpg
```

### Creating Test Data

For testing the pipeline, create synthetic data:

```python
"""Create synthetic test data for pipeline verification."""

import numpy as np
from PIL import Image
from pathlib import Path

def create_synthetic_data(output_dir, n_per_class=50):
    """Create simple synthetic images for testing."""
    output_dir = Path(output_dir)
    
    classes = ['happy', 'sad']
    colors = {
        'happy': (255, 255, 0),   # Yellow
        'sad': (0, 0, 255),       # Blue
    }
    
    for split in ['train', 'val']:
        n = n_per_class if split == 'train' else n_per_class // 4
        
        for class_name in classes:
            class_dir = output_dir / split / class_name
            class_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(n):
                # Create colored image with noise
                img = np.full((224, 224, 3), colors[class_name], dtype=np.uint8)
                noise = np.random.randint(-30, 30, (224, 224, 3), dtype=np.int16)
                img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                # Save
                Image.fromarray(img).save(class_dir / f'synthetic_{i:04d}.jpg')
            
            print(f"Created {n} images in {class_dir}")

# Create synthetic data
create_synthetic_data('data_synthetic')
```

---

## 8. Data Preparation Checklist

Before training, verify:

| Check | Command/Action | Expected |
|-------|----------------|----------|
| Directory structure | `tree data/` | train/ and val/ with class folders |
| Image count | Count script | At least 100 per class |
| Class balance | Balance script | Ratio > 0.5 |
| Images load | Data loader test | No errors |
| Batch shape | Print batch | [32, 3, 224, 224] |
| Labels correct | Print labels | 0 and 1 for 2-class |

---

## 9. Summary

### What You've Learned

1. ✅ Data must be organized in class folders
2. ✅ Train/val split prevents overfitting
3. ✅ 80/20 split is standard
4. ✅ Data augmentation increases effective dataset size
5. ✅ Data loaders feed batches to the model
6. ✅ Validation data is NOT augmented

### What's Next

In the next guide, we'll run the actual training:
- Configure training parameters
- Start training
- Monitor progress
- Understand the training loop

---

## Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Directory structure for data | __ |
| Train/val split purpose | __ |
| Data augmentation | __ |
| Data loaders | __ |
| Verifying data is correct | __ |

---

*Next: [Guide 04: Training Walkthrough](04_TRAINING_WALKTHROUGH.md)*
