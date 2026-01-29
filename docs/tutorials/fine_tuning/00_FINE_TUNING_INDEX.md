# Fine-Tuning Guide for Emotion Classification

**Project**: Reachy Emotion Recognition  
**Audience**: Junior Engineers  
**Duration**: 2-3 weeks  
**Last Updated**: 2026-01-28

---

## Overview

This guide teaches you how to fine-tune a ResNet-50 emotion classification model for the Reachy robot. By the end, you'll understand:

1. **What fine-tuning is** and why we use it
2. **How transfer learning works** for emotion recognition
3. **The two-phase training strategy** (frozen → unfrozen backbone)
4. **How to prepare data** for training
5. **How to run training** and monitor progress
6. **How to evaluate** and validate against Gate A requirements

---

## Prerequisites

Before starting, ensure you have:

- [ ] Completed database tutorials (Weeks 1-4 of Phase 1)
- [ ] Basic Python knowledge (functions, classes, loops)
- [ ] Understanding of what neural networks do (high-level)
- [ ] Access to Ubuntu 1 (training server with GPU)

**Not required** (you'll learn these):
- Deep learning experience
- PyTorch knowledge
- Understanding of ResNet architecture

---

## Guide Structure

| Guide | Topic | Duration | Difficulty |
|-------|-------|----------|------------|
| [01_WHAT_IS_FINE_TUNING.md](01_WHAT_IS_FINE_TUNING.md) | Concepts & Theory | 1-2 hours | Beginner |
| [02_ENVIRONMENT_SETUP.md](02_ENVIRONMENT_SETUP.md) | Setup & Dependencies | 1-2 hours | Beginner |
| [03_DATA_PREPARATION.md](03_DATA_PREPARATION.md) | Dataset Preparation | 2-3 hours | Beginner |
| [04_TRAINING_WALKTHROUGH.md](04_TRAINING_WALKTHROUGH.md) | Running Training | 3-4 hours | Intermediate |
| [05_MONITORING_DEBUGGING.md](05_MONITORING_DEBUGGING.md) | MLflow & Debugging | 2-3 hours | Intermediate |
| [06_EVALUATION_GATE_A.md](06_EVALUATION_GATE_A.md) | Evaluation & Gate A | 2-3 hours | Intermediate |
| [07_EXPORT_DEPLOYMENT.md](07_EXPORT_DEPLOYMENT.md) | Export to ONNX | 1-2 hours | Intermediate |

**Total**: ~15-20 hours over 2-3 weeks

---

## Quick Reference

### Key Commands

```bash
# Train 2-class model (happy/sad)
python trainer/train_resnet50.py --config fer_finetune/specs/resnet50_emotion_2cls.yaml

# Train 8-class model (all emotions)
python trainer/train_resnet50.py --config fer_finetune/specs/resnet50_emotion_8cls.yaml

# Resume training from checkpoint
python trainer/train_resnet50.py --config fer_finetune/specs/resnet50_emotion_2cls.yaml --resume outputs/latest.pth

# Export to ONNX
python trainer/train_resnet50.py --export-only --resume outputs/best_model.pth --export-path exports/
```

### Key Files

```
trainer/
├── train_resnet50.py           # Main training script
├── fer_finetune/
│   ├── config.py               # Training configuration
│   ├── model.py                # ResNet-50 model definition
│   ├── dataset.py              # Data loading
│   ├── train.py                # Training loop
│   ├── evaluate.py             # Metrics computation
│   ├── export.py               # ONNX export
│   └── specs/
│       ├── resnet50_emotion_2cls.yaml  # 2-class config
│       └── resnet50_emotion_8cls.yaml  # 8-class config
```

### Gate A Requirements

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Macro F1 | ≥ 0.84 | Average F1 across all classes |
| Balanced Accuracy | ≥ 0.85 | Average recall per class |
| Per-class F1 | ≥ 0.75 (floor: 0.70) | Each class must perform well |
| ECE | ≤ 0.08 | Calibration error |
| Brier | ≤ 0.16 | Probability prediction error |

---

## Learning Path

### Week 1: Foundations
- Day 1-2: Read Guide 01 (What is Fine-Tuning)
- Day 3: Complete Guide 02 (Environment Setup)
- Day 4-5: Work through Guide 03 (Data Preparation)

### Week 2: Training
- Day 1-2: Complete Guide 04 (Training Walkthrough)
- Day 3: Work through Guide 05 (Monitoring & Debugging)
- Day 4-5: Complete Guide 06 (Evaluation & Gate A)

### Week 3: Deployment (Optional)
- Day 1-2: Complete Guide 07 (Export & Deployment)
- Day 3-5: Practice with different configurations

---

## Glossary

| Term | Definition |
|------|------------|
| **Fine-tuning** | Adapting a pre-trained model to a new task |
| **Transfer learning** | Using knowledge from one task to help another |
| **Backbone** | The main feature extraction part of the network |
| **Head** | The classification layer at the end |
| **Epoch** | One complete pass through the training data |
| **Batch** | A small group of samples processed together |
| **Learning rate** | How big the update steps are during training |
| **Checkpoint** | A saved snapshot of the model during training |
| **Gate A** | Quality requirements for model deployment |

---

## Getting Help

If you get stuck:

1. Check the troubleshooting section in each guide
2. Review the error message carefully
3. Search the codebase for similar patterns
4. Ask a senior engineer for help

---

*Let's begin with [Guide 01: What is Fine-Tuning?](01_WHAT_IS_FINE_TUNING.md)*
