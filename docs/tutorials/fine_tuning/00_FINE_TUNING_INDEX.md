# Fine-Tuning Guide for Emotion Classification

**Project**: Reachy Emotion Recognition  
**Audience**: Junior Engineers  
**Duration**: 2-3 weeks  
**Last Updated**: 2026-01-31

---

## 🆕 New ML Engineers: Start Here!

**[ML_PIPELINE_ONBOARDING_GUIDE.md](ML_PIPELINE_ONBOARDING_GUIDE.md)** — Comprehensive 4-6 hour guide covering:
- EfficientNet-B0 (HSEmotion) architecture overview
- Quick start inference with pre-trained model
- Training with synthetic video data
- Quality gate validation
- ONNX export for Jetson deployment

## 👨‍🏫 Technical Trainers: Preparation Guide

**[TRAIN_THE_TRAINER.md](TRAIN_THE_TRAINER.md)** — 2-3 hour preparation guide covering:
- Pre-session environment verification
- Curriculum structure and session breakdown
- Key concepts to emphasize with teaching analogies
- Common Q&A and demonstration scripts
- Hands-on exercises and assessment rubric

---

## Overview

This guide series teaches you how to fine-tune an **EfficientNet-B0** emotion classification model (HSEmotion pre-trained) for the Reachy robot. By the end, you'll understand:

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
- [ ] Understanding of EfficientNet architecture

---

## Guide Structure

### Core Training Pipeline (Required)

| Guide | Topic | Duration | Difficulty |
|-------|-------|----------|------------|
| [01_WHAT_IS_FINE_TUNING.md](01_WHAT_IS_FINE_TUNING.md) | Concepts & Theory | 1-2 hours | Beginner |
| [02_ENVIRONMENT_SETUP.md](02_ENVIRONMENT_SETUP.md) | Setup & Dependencies | 1-2 hours | Beginner |
| [03_DATA_PREPARATION.md](03_DATA_PREPARATION.md) | Dataset Preparation | 2-3 hours | Beginner |
| [04_TRAINING_WALKTHROUGH.md](04_TRAINING_WALKTHROUGH.md) | Running Training | 3-4 hours | Intermediate |
| [05_MONITORING_DEBUGGING.md](05_MONITORING_DEBUGGING.md) | MLflow & Debugging | 2-3 hours | Intermediate |
| [06_EVALUATION_GATE_A.md](06_EVALUATION_GATE_A.md) | Evaluation & Gate A | 2-3 hours | Intermediate |
| [07_EXPORT_DEPLOYMENT.md](07_EXPORT_DEPLOYMENT.md) | Export to ONNX | 1-2 hours | Intermediate |

### Practical Guides (Highly Recommended)

| Guide | Topic | Duration | Difficulty |
|-------|-------|----------|------------|
| [08_QUICK_START_HANDS_ON.md](08_QUICK_START_HANDS_ON.md) | First Inference & Training | 30-45 min | Beginner |
| [09_WEB_UI_DATA_WORKFLOW.md](09_WEB_UI_DATA_WORKFLOW.md) | Web UI for Data Curation | 1-2 hours | Beginner |
| [10_WORKED_EXAMPLE_COMPLETE_RUN.md](10_WORKED_EXAMPLE_COMPLETE_RUN.md) | Complete Training Reference | Reference | Intermediate |

### Advanced Topics (Production)

| Guide | Topic | Duration | Difficulty |
|-------|-------|----------|------------|
| [11_NVIDIA_TAO_TOOLKIT_GUIDE.md](11_NVIDIA_TAO_TOOLKIT_GUIDE.md) | TAO for Jetson Deployment | 3-4 hours | Advanced |
| [12_N8N_ORCHESTRATION_GUIDE.md](12_N8N_ORCHESTRATION_GUIDE.md) | Automated Training Pipelines | 2-3 hours | Intermediate |

**Total Core**: ~15-20 hours over 2-3 weeks  
**Total with Advanced**: ~25-30 hours over 3-4 weeks

---

## Quick Reference

### Key Commands

```bash
# Train 2-class model (happy/sad) - EfficientNet-B0 (RECOMMENDED)
python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml

# Train 8-class model (all emotions)
python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_8cls.yaml

# Resume training from checkpoint
python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml --resume checkpoints/latest.pth

# Export to ONNX
python trainer/train_efficientnet.py --export-only --resume checkpoints/best_model.pth --export-path exports/

# Legacy: ResNet-50 (for comparison only)
python trainer/train_resnet50.py --config fer_finetune/specs/resnet50_emotion_2cls.yaml
```

### Key Files

```
trainer/
├── train_efficientnet.py       # Main training script (EfficientNet-B0)
├── train_resnet50.py           # Legacy ResNet-50 script
├── fer_finetune/
│   ├── config.py               # Training configuration
│   ├── model_efficientnet.py   # EfficientNet-B0 model (HSEmotion)
│   ├── model.py                # ResNet-50 model (legacy)
│   ├── train_efficientnet.py   # EfficientNet training loop
│   ├── train.py                # ResNet-50 training loop
│   ├── dataset.py              # Data loading
│   ├── evaluate.py             # Metrics computation
│   ├── export.py               # ONNX export
│   └── specs/
│       ├── efficientnet_b0_emotion_2cls.yaml  # 2-class config (RECOMMENDED)
│       ├── efficientnet_b0_emotion_8cls.yaml  # 8-class config
│       ├── resnet50_emotion_2cls.yaml         # Legacy 2-class
│       └── resnet50_emotion_8cls.yaml         # Legacy 8-class
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

### Fast Track (1 week)
For engineers who need to get productive quickly:
- **Day 1**: Guide 08 (Quick Start Hands-On) — 45 min
- **Day 2**: Guide 01 (What is Fine-Tuning) + Guide 02 (Environment Setup) — 3 hours
- **Day 3**: Guide 09 (Web UI Data Workflow) + Guide 03 (Data Preparation) — 4 hours
- **Day 4-5**: Guide 04 (Training Walkthrough) + Guide 05 (Monitoring) — 6 hours

### Standard Track (2-3 weeks)

**Week 1: Foundations**
- Day 1: Guide 08 (Quick Start) — Get hands-on immediately
- Day 2-3: Guide 01 (What is Fine-Tuning) — Understand concepts
- Day 4: Guide 02 (Environment Setup) — Set up your machine
- Day 5: Guide 09 (Web UI Data Workflow) — Learn data curation

**Week 2: Training**
- Day 1-2: Guide 03 (Data Preparation) — Prepare datasets
- Day 3-4: Guide 04 (Training Walkthrough) — Run training
- Day 5: Guide 05 (Monitoring & Debugging) — Track experiments

**Week 3: Evaluation & Production**
- Day 1-2: Guide 06 (Evaluation & Gate A) — Validate models
- Day 3: Guide 07 (Export & Deployment) — Export to ONNX
- Day 4-5: Guide 10 (Worked Example) — Reference a complete run

### Advanced Track (Week 4+)
For production deployment to Jetson:
- Day 1-2: Guide 11 (NVIDIA TAO Toolkit) — Production training
- Day 3: Guide 12 (n8n Orchestration) — Automated pipelines

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
