# Train the Trainer: ML Pipeline Instruction Guide

**Project**: Reachy Emotion Recognition  
**Audience**: Technical Trainers / Senior Engineers  
**Purpose**: Prepare trainers to onboard new ML engineers  
**Last Updated**: 2026-01-31  
**Preparation Time**: 2-3 hours

---

## Your Role as Trainer

You'll be guiding new ML engineers through our emotion classification training pipeline. This document helps you:

1. **Understand the big picture** before diving into details
2. **Anticipate common questions** and have answers ready
3. **Know what to demonstrate** vs. what to let them discover
4. **Recognize when learners are stuck** and how to help

---

## Part 1: Pre-Training Checklist (Before the Session)

### Environment Verification

Run these commands on Ubuntu 1 to ensure the training environment is ready:

```bash
# Verify GPU is available
nvidia-smi

# Verify Python environment
conda activate reachy_ml
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

# Verify key packages
python -c "import timm, albumentations, mlflow; print('All packages installed')"

# Verify data exists (for demo)
ls -la /media/project_data/reachy_emotion/videos/train/
ls -la /media/project_data/reachy_emotion/videos/test/
```

### Materials to Have Ready

| Material | Location | Purpose |
|----------|----------|---------|
| Onboarding Guide | `docs/tutorials/fine_tuning/ML_PIPELINE_ONBOARDING_GUIDE.md` | Primary learner reference |
| Fine-Tuning Index | `docs/tutorials/fine_tuning/00_FINE_TUNING_INDEX.md` | Navigation hub |
| 2-class Config | `trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml` | Walkthrough example |
| Sample videos | `/media/project_data/reachy_emotion/videos/` | Demo data |

### Pre-Session Test Run

**Do a quick training run yourself** to catch any environment issues:

```bash
cd /path/to/reachy_emotion

# Quick 2-epoch test
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --run-id trainer_test_$(date +%Y%m%d)
```

Stop after 1-2 epochs (Ctrl+C) — you just want to verify the pipeline starts correctly.

---

## Part 2: Curriculum Overview

### Recommended Session Structure

| Session | Duration | Topic | Trainer Role |
|---------|----------|-------|--------------|
| **1** | 1 hour | Architecture & Why EfficientNet-B0 | Present + Discuss |
| **2** | 1.5 hours | Hands-on Inference | Guide + Observe |
| **3** | 2 hours | Training Walkthrough | Demonstrate + Pair |
| **4** | 1 hour | Debugging & Troubleshooting | Problem-solve together |
| **5** | 30 min | Gate Validation & Export | Review + Q&A |

**Total**: ~6 hours over 2-3 days

### Learning Objectives by Session

#### Session 1: Architecture
By the end, learners should be able to:
- [ ] Explain why EfficientNet-B0 was chosen over ResNet-50
- [ ] Describe what HSEmotion weights provide
- [ ] Draw the two-phase training strategy on a whiteboard

#### Session 2: Inference
By the end, learners should be able to:
- [ ] Load a pre-trained model in Python
- [ ] Run inference on a single image
- [ ] Interpret confidence scores

#### Session 3: Training
By the end, learners should be able to:
- [ ] Explain each section of the YAML config
- [ ] Start a training run from the command line
- [ ] Interpret training logs (loss, F1, phase transitions)
- [ ] Resume from a checkpoint

#### Session 4: Debugging
By the end, learners should be able to:
- [ ] Diagnose common errors (CUDA OOM, missing data, etc.)
- [ ] Adjust hyperparameters to fix underfitting/overfitting
- [ ] Use MLflow to compare runs

#### Session 5: Validation & Export
By the end, learners should be able to:
- [ ] Explain Gate A requirements
- [ ] Export a model to ONNX
- [ ] Understand the deployment path to Jetson

---

## Part 3: Key Concepts to Emphasize

### Concept 1: Why Transfer Learning?

**Analogy to use**: "Imagine teaching someone to recognize your family members. You don't teach them what a face is first — they already know that. You just show them the specific faces. That's transfer learning."

**Key points**:
- HSEmotion already learned "what faces expressing emotions look like"
- We only need to teach "which emotions we care about" (happy vs sad)
- This is why we freeze the backbone initially

### Concept 2: Two-Phase Training

**Visual to draw**:

```
Epoch:    1   2   3   4   5   6   7   8   ...
          |---Phase 1---|---Phase 2--------->
          
Phase 1:  Backbone FROZEN, Head TRAINS (fast learning)
Phase 2:  Backbone UNFROZEN, Both FINE-TUNE (careful adjustment)
```

**Why it matters**: 
- Phase 1 prevents "catastrophic forgetting" of HSEmotion knowledge
- Phase 2 allows domain adaptation to our specific video data

### Concept 3: Quality Gates

**Framing**: "Think of gates as automated code review for models."

| Gate | When | What it checks | Who approves |
|------|------|----------------|--------------|
| Gate A | After training | Accuracy, F1, calibration | Automated |
| Gate B | On Jetson | Latency, memory, FPS | Automated |
| Gate C | User rollout | Real-world performance | Human |

### Concept 4: Why Calibration Matters

**Scenario to present**: "The model says it's 95% confident someone is happy. But is that confidence trustworthy?"

- **ECE (Expected Calibration Error)**: Measures if confidence matches accuracy
- **Well-calibrated**: When model says 80% confident, it's right ~80% of the time
- **Why it matters for robots**: We modulate gestures based on confidence

---

## Part 4: Common Questions & Answers

### Architecture Questions

**Q: Why not use a larger model like EfficientNet-B2?**
> A: B2 offers higher accuracy but exceeds our Jetson latency budget (120ms). B0 gives us 3× headroom (~40ms), leaving room for gesture planning. We may revisit B2 when hardware constraints relax.

**Q: What's the difference between HSEmotion and ImageNet weights?**
> A: ImageNet teaches "general object recognition" (cats, cars, etc.). HSEmotion teaches "facial emotion recognition" specifically — it's already seen millions of faces with emotion labels. Starting from HSEmotion gives us a huge head start.

**Q: Can we add more emotion classes later?**
> A: Yes! The 8-class config (`efficientnet_b0_emotion_8cls.yaml`) is ready. We start with binary (happy/sad) for Phase 1 simplicity, but the architecture supports all 8 Ekman emotions.

### Training Questions

**Q: How long does training take?**
> A: With ~500 videos per class and 30 epochs:
> - GPU (RTX 3090): ~30-45 minutes
> - GPU (RTX 4090): ~15-20 minutes
> - CPU only: Several hours (not recommended)

**Q: What if my F1 score is stuck below 0.84?**
> A: Checklist:
> 1. Data balance — equal happy/sad videos?
> 2. Data quality — are faces clearly visible?
> 3. More epochs — try 50 instead of 30
> 4. Learning rate — try 0.0001 instead of 0.0003
> 5. More data — can you generate more synthetic videos?

**Q: When should I use mixup augmentation?**
> A: Mixup helps with:
> - Small datasets (< 1000 samples)
> - Overfitting (training loss << validation loss)
> - Improving calibration (more gradual confidence)
> 
> Reduce or disable if:
> - Dataset is large and diverse
> - Model is underfitting

### Debugging Questions

**Q: I get "CUDA out of memory" — what do I do?**
> A: Reduce batch size in the config:
> ```yaml
> data:
>   batch_size: 16  # Was 32
> ```
> Also check if other processes are using the GPU: `nvidia-smi`

**Q: Training loss goes down but validation loss goes up — what's wrong?**
> A: Classic overfitting. Solutions:
> 1. Increase dropout (`dropout_rate: 0.4`)
> 2. Enable/increase mixup (`mixup_alpha: 0.3`)
> 3. Add more training data
> 4. Reduce epochs or enable early stopping

---

## Part 5: Demonstration Scripts

### Demo 1: Quick Inference (5 minutes)

Use this to show the model working before diving into training:

```python
# demo_inference.py
import torch
from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

# Load model
model = create_efficientnet_model(num_classes=2, pretrained=True)
model.eval()

# Show model summary
print(f"Total parameters: {model.get_total_params():,}")
print(f"Trainable parameters: {model.get_trainable_params():,}")

# Explain: "Notice most params are NOT trainable yet — backbone is frozen"
```

### Demo 2: Config Walkthrough (10 minutes)

Open the config file and walk through each section:

```bash
# Display config with comments
cat trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml
```

**Talking points for each section**:
- `model:` — "This is WHAT we're training"
- `data:` — "This is WHAT we're training on"
- `num_epochs, learning_rate:` — "This is HOW we're training"
- `gate_a_*:` — "This is our SUCCESS criteria"

### Demo 3: Live Training (15 minutes)

Start training and narrate what's happening:

```bash
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --run-id demo_session
```

**Narration points**:
1. "See 'Model params: X trainable' — that's just the head"
2. "Watch the loss decrease each epoch"
3. "Notice 'Transitioning to Phase 2' — backbone unfreezing"
4. "Trainable params jumped — now fine-tuning backbone too"
5. "Gate A check at the end — did we pass?"

### Demo 4: MLflow Exploration (10 minutes)

```bash
# Start MLflow UI
mlflow ui --backend-store-uri file:///workspace/mlruns

# Open browser to http://localhost:5000
```

**Show learners**:
1. How to find their experiment
2. How to compare runs side-by-side
3. How to view training curves
4. How to download artifacts

---

## Part 6: Hands-On Exercises

### Exercise 1: Modify and Train (30 minutes)

**Instructions for learners**:
1. Copy the 2-class config to a new file
2. Change one hyperparameter (e.g., learning rate)
3. Run training with a unique run-id
4. Compare results in MLflow

**Success criteria**: They can explain why their change affected results.

### Exercise 2: Diagnose a Problem (20 minutes)

**Setup**: Intentionally create a broken config:
```yaml
data:
  batch_size: 256  # Too large — will cause OOM
```

**Task**: Have learners identify and fix the issue.

**Learning outcome**: Reading error messages, adjusting config.

### Exercise 3: Resume from Checkpoint (15 minutes)

**Instructions**:
1. Start a training run
2. Stop it after 5 epochs (Ctrl+C)
3. Resume from the checkpoint
4. Verify it continues from epoch 6

**Learning outcome**: Understanding checkpointing and recovery.

---

## Part 7: Assessment Rubric

Use this to evaluate learner readiness:

| Skill | Beginner | Competent | Proficient |
|-------|----------|-----------|------------|
| **Load model** | Needs help | Can do with docs | Can do from memory |
| **Run training** | Follows exact commands | Modifies config | Creates new configs |
| **Interpret logs** | Confused by output | Identifies key metrics | Diagnoses issues |
| **Debug errors** | Asks for help | Searches docs/code | Fixes independently |
| **Explain architecture** | Reads from guide | Explains in own words | Teaches others |

**Minimum for "ready to work independently"**: Competent in all areas.

---

## Part 8: Trainer Tips

### Pacing

- **Go slow on concepts** — learners often nod but don't understand
- **Go fast on typing** — they can copy commands from docs
- **Pause after errors** — let them read the message first

### Checking Understanding

Instead of "Does that make sense?", ask:
- "What do you think will happen if we change X?"
- "Can you explain Phase 2 in your own words?"
- "What metric would you check to see if this worked?"

### When Learners Are Stuck

1. **Don't give the answer immediately** — ask guiding questions
2. **Point to the right file/section** — let them find it
3. **Normalize confusion** — "This trips everyone up at first"

### Common Trainer Mistakes

| Mistake | Why it's bad | Instead do |
|---------|--------------|------------|
| Typing too fast | Learners can't follow | Narrate each step |
| Skipping errors | Misses teaching moment | Walk through the error |
| Doing it for them | No learning happens | Guide their hands |
| Too much theory | Bores learners | Mix with hands-on |

---

## Part 9: Resources for Trainers

### Documents to Know Well

1. **ML_PIPELINE_ONBOARDING_GUIDE.md** — Learner's primary reference
2. **00_FINE_TUNING_INDEX.md** — Navigation and quick reference
3. **memory-bank/requirements.md** (Section 6.7) — Model selection rationale
4. **AGENTS.md** (Agent 5) — Training orchestrator role

### Code to Understand

```
trainer/
├── train_efficientnet.py          # Entry point — understand CLI args
├── fer_finetune/
│   ├── model_efficientnet.py      # Model class — understand forward()
│   ├── train_efficientnet.py      # Trainer class — understand train()
│   └── config.py                  # Config dataclass — know all options
```

### External References

- [HSEmotion GitHub](https://github.com/HSE-asavchenko/hsemotion) — Original model source
- [timm documentation](https://huggingface.co/docs/timm) — Backbone library
- [MLflow docs](https://mlflow.org/docs/latest/index.html) — Experiment tracking

---

## Part 10: Post-Training Checklist

After each training session, verify learner readiness:

- [ ] Can load model and run inference independently
- [ ] Can start training from command line
- [ ] Can interpret training output (loss, F1, phase transition)
- [ ] Can resume from checkpoint
- [ ] Can explain Gate A requirements
- [ ] Knows where to find documentation
- [ ] Has completed at least one solo training run

### Handoff to Project Work

Once a learner passes the checklist:
1. Assign them a real training task (e.g., "train on the latest batch of synthetic videos")
2. Have them document their run in MLflow
3. Review their results together
4. Celebrate their first model! 🎉

---

## Appendix: Quick Reference Card

Print this for learners:

```
╔══════════════════════════════════════════════════════════════╗
║           EfficientNet-B0 Training Quick Reference           ║
╠══════════════════════════════════════════════════════════════╣
║ TRAIN (2-class):                                             ║
║   python trainer/train_efficientnet.py \                     ║
║     --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml ║
║                                                              ║
║ RESUME:                                                      ║
║   python trainer/train_efficientnet.py \                     ║
║     --config <config> --resume checkpoints/latest.pth        ║
║                                                              ║
║ EXPORT:                                                      ║
║   python trainer/train_efficientnet.py \                     ║
║     --export-only --resume checkpoints/best_model.pth        ║
║                                                              ║
║ MLFLOW:                                                      ║
║   mlflow ui --backend-store-uri file:///workspace/mlruns     ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║ GATE A REQUIREMENTS:                                         ║
║   • Macro F1 ≥ 0.84    • Balanced Accuracy ≥ 0.85           ║
║   • Per-class F1 ≥ 0.75    • ECE ≤ 0.08    • Brier ≤ 0.16  ║
╠══════════════════════════════════════════════════════════════╣
║ COMMON FIXES:                                                ║
║   • OOM error → Reduce batch_size                            ║
║   • Low F1 → More epochs, check data balance                 ║
║   • Overfitting → Increase dropout, add mixup                ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Good luck training your trainers!*
