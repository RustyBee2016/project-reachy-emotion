# Train the Trainer: ML Pipeline Instruction Guide

**Project**: Reachy Emotion Recognition  
**Audience**: Technical Trainers / Senior Engineers  
**Purpose**: Prepare trainers to onboard new ML engineers  
**Last Updated**: 2026-02-12  
**Preparation Time**: 3-4 hours

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

# Verify key packages (including HSEmotion weight sources per §6.7)
python -c "
import timm, albumentations, mlflow
try:
    import hsemotion; print('hsemotion: OK')
except ImportError:
    print('hsemotion: MISSING — pip install hsemotion')
try:
    import emotiefflib; print('emotiefflib: OK')
except ImportError:
    print('emotiefflib: MISSING — pip install emotiefflib')
print('Core packages installed')
"

# Verify data exists (for demo)
# dataset_all is the master corpus; train/test are regenerated per run
ls -la /media/project_data/reachy_emotion/videos/dataset_all/
ls -la /media/project_data/reachy_emotion/videos/train/
ls -la /media/project_data/reachy_emotion/videos/test/

# Verify HSEmotion weights are cached
python -c "
from pathlib import Path
w = Path.home() / '.cache' / 'hsemotion' / 'enet_b0_8_best_vgaf.pt'
print(f'HSEmotion weights: {\"CACHED\" if w.exists() else \"NOT CACHED — will download on first run\"}')
"
```

### Materials to Have Ready

**Core (required for every session):**

| Material | Location | Purpose |
|----------|----------|---------|
| Fine-Tuning Index | `00_FINE_TUNING_INDEX.md` | Navigation hub & learning paths |
| Onboarding Guide | `ML_PIPELINE_ONBOARDING_GUIDE.md` | Primary learner reference |
| Quick Start | `08_QUICK_START_HANDS_ON.md` | Session 0 — first hands-on |
| 3-class Config | `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml` | Config walkthrough |
| Sample videos | `/media/project_data/reachy_emotion/videos/` | Demo data |

**Session-specific:**

| Material | Location | Used in |
|----------|----------|---------|
| Web UI Data Workflow | `09_WEB_UI_DATA_WORKFLOW.md` | Session 2 (Data Curation) |
| Worked Example | `10_WORKED_EXAMPLE_COMPLETE_RUN.md` | Session 3 (Training) — "what good looks like" |
| TAO Toolkit Guide | `11_NVIDIA_TAO_TOOLKIT_GUIDE.md` | Session 6 (Advanced, optional) |
| n8n Orchestration | `12_N8N_ORCHESTRATION_GUIDE.md` | Session 6 (Advanced, optional) |
| Requirements §6.7 | `memory-bank/requirements.md` | Model selection rationale (trainer background) |

### Pre-Session Test Run

**Do a quick training run yourself** to catch any environment issues:

```bash
cd /path/to/reachy_emotion

# Quick 2-epoch test
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml \
    --run-id trainer_test_$(date +%Y%m%d)
```

Stop after 1-2 epochs (Ctrl+C) — you just want to verify the pipeline starts correctly.

---

## Part 2: Curriculum Overview

### Recommended Session Structure

| Session | Duration | Topic | Trainer Role | Guide(s) |
|---------|----------|-------|--------------|----------|
| **0** | 45 min | Quick Start Hands-On | Observe only | 08 |
| **1** | 1 hour | Architecture & Why EfficientNet-B0 | Present + Discuss | 01 |
| **2** | 1.5 hours | Data Curation & Web UI | Guide + Observe | 03, 09 |
| **3** | 2 hours | Training Walkthrough | Demonstrate + Pair | 04, 10 |
| **4** | 1 hour | Monitoring & Debugging | Problem-solve together | 05 |
| **5** | 1 hour | Gate A Validation & Export | Review + Q&A | 06, 07 |
| **6** | 1 hour | Advanced Topics (optional) | Overview + Discussion | 11, 12 |

**Total**: ~7-8 hours over 3-4 days (Session 6 optional)

### Learning Objectives by Session

#### Session 0: Quick Start (Guide 08)
**Purpose**: Build confidence immediately. Learners see results before theory.
By the end, learners should be able to:
- [ ] Run inference on a test image with the pre-trained model
- [ ] See a training loop execute (even briefly)
- [ ] Feel "I can do this" before any theory

**Trainer role**: Hands off. Let them follow Guide 08 independently. Only help if blocked.

#### Session 1: Architecture (Guide 01)
By the end, learners should be able to:
- [ ] Explain why EfficientNet-B0 was chosen over ResNet-50 (and why NOT B2 — see §6.7)
- [ ] Describe what HSEmotion weights provide vs. timm ImageNet fallback
- [ ] Draw the two-phase training strategy on a whiteboard
- [ ] Explain the weight source fallback chain (HSEmotion → timm → random)

#### Session 2: Data Curation (Guides 03, 09)
By the end, learners should be able to:
- [ ] Explain the `temp → dataset_all → train/test` staging pipeline
- [ ] Use the Streamlit Web UI to generate, label, and promote videos
- [ ] Verify class balance before triggering training
- [ ] Understand why `train/` and `test/` are ephemeral but `dataset_all/` is persistent

#### Session 3: Training (Guides 04, 10)
By the end, learners should be able to:
- [ ] Explain each section of the YAML config (including `use_multi_task: false`)
- [ ] Start a training run from the command line
- [ ] Interpret training logs (loss, F1, phase transitions)
- [ ] Resume from a checkpoint
- [ ] Compare their run against the Worked Example (Guide 10)

#### Session 4: Monitoring & Debugging (Guide 05)
By the end, learners should be able to:
- [ ] Diagnose common errors (CUDA OOM, missing data, import errors)
- [ ] Adjust hyperparameters to fix underfitting/overfitting
- [ ] Use MLflow to compare runs
- [ ] Troubleshoot weight download failures (fallback chain)

#### Session 5: Gate A Validation & Export (Guides 06, 07)
By the end, learners should be able to:
- [ ] Explain Gate A requirements and why each metric matters
- [ ] Export a model to ONNX
- [ ] Understand the 3× latency headroom and shared GPU budget on Jetson
- [ ] Explain the deployment path to Jetson (and why B2 needs a benchmark cycle)

#### Session 6: Advanced Topics — optional (Guides 11, 12)
By the end, learners should be able to:
- [ ] Explain the difference between PyTorch (EfficientNet-B0) and TAO (ResNet-18) pipelines
- [ ] Understand how n8n Agent 5 triggers automated training
- [ ] Know what multi-task training is and when Phase 2 will enable it

---

## Part 3: Key Concepts to Emphasize

### Concept 1: Why Transfer Learning?

**Analogy to use**: "Imagine teaching someone to recognize your family members. You don't teach them what a face is first — they already know that. You just show them the specific faces. That's transfer learning."

**Key points**:
- HSEmotion already learned "what faces expressing emotions look like"
- We only need to teach "which emotions we care about" (happy vs sad vs neutral baseline)
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

### Concept 3: Weight Source Fallback Chain

**Visual to draw** (from Guide 02, Step 6.3):

```
Priority 1: HSEmotion / EmotiEffLib   ← BEST (emotion-specific weights)
       ↓ (if unavailable)
Priority 2: timm + ImageNet           ← OK (general features, slower convergence)
       ↓ (if unavailable)
Priority 3: Random initialization     ← BAD (not recommended)
```

**Key points**:
- `pip install emotiefflib` and `pip install hsemotion` provide emotion-optimized weights
- `timm` provides a general-purpose fallback if HSEmotion download fails
- The training script handles this automatically, but learners should know what's happening
- If behind a firewall: manually copy `enet_b0_8_best_vgaf.pt` to `~/.cache/hsemotion/`

### Concept 4: Data Staging Pipeline

**Visual to draw** (from Guide 03):

```
/videos/temp/  →  /videos/dataset_all/  →  /videos/train/
                                         →  /videos/test/
```

**Key points**:
- `dataset_all/` is the **persistent master corpus** — never deleted
- `train/` and `test/` are **regenerated each fine-tuning run** via randomized sampling
- This prevents data leakage and ensures reproducible experiments
- Learners will interact with the Web UI (Guide 09) to move data through this pipeline

### Concept 5: Quality Gates

**Framing**: "Think of gates as automated code review for models."

| Gate | When | What it checks | Who approves |
|------|------|----------------|--------------|
| Gate A | After training | Accuracy, F1, calibration | Automated |
| Gate B | On Jetson | Latency, memory, FPS | Automated |
| Gate C | User rollout | Real-world performance | Human |

### Concept 6: Why Calibration Matters

**Scenario to present**: "The model says it's 95% confident someone is happy. But is that confidence trustworthy?"

- **ECE (Expected Calibration Error)**: Measures if confidence matches accuracy
- **Well-calibrated**: When model says 80% confident, it's right ~80% of the time
- **Why it matters for robots**: We modulate gestures based on confidence (5-tier system)

### Concept 7: Latency Headroom & Shared GPU Budget

**Visual to draw** (from Guide 07):

```
Jetson Xavier NX — 120 ms total budget:
├── Emotion inference:     ~40 ms  (EfficientNet-B0)
├── Gesture planner:       ~25 ms
├── Future features:       ~15 ms
└── Thermal/overhead:      ~40 ms
```

**Key points**:
- EfficientNet-B0 uses only ~⅓ of the latency budget — this is **intentional**
- The rest is reserved for gesture planning and future multimodal features
- This is why EfficientNet-B2 is NOT approved — it would consume the entire budget
- Per §6.7: B2 requires a full benchmark/validation cycle before any promotion

### Concept 8: Multi-Task Training (Phase 2 Preview)

**When learners ask about `use_multi_task: false` in the config**:

```
Phase 1 (now):     [Image] → [EfficientNet-B0] → [happy/sad/neutral]

Phase 2 (future):  [Image] → [EfficientNet-B0] → [happy/sad/neutral]     (categorical head)
                                                 → [0.0 – 1.0]    (degree head)
                                                 → [gesture cue]   (alignment head)
```

**Key points**:
- Phase 2 adds degree-of-emotion (how intensely) and gesture alignment outputs
- Requires degree labels from the web UI slider annotations — not yet available
- Config will change to `use_multi_task: true` with additional loss weights
- Gate A thresholds will be updated for multi-task evaluation
- **Action for trainers**: Tell learners "don't enable this yet, but know it's coming"

---

## Part 4: Common Questions & Answers

### Architecture Questions

**Q: Why not use a larger model like EfficientNet-B2?**
> A: B2 offers higher accuracy but is expected to exceed Jetson latency (≤120 ms) and GPU memory (≤2.5 GB) limits. B0 gives us 3× headroom (~40 ms, ~0.8 GB), leaving room for gesture planning and future features. Per requirements §6.7, B2 requires a full benchmark/validation cycle and Gate B re-establishment before any promotion. Don't let learners experiment with B2 in production without this process.

**Q: What's the difference between HSEmotion and ImageNet weights?**
> A: ImageNet teaches "general object recognition" (cats, cars, etc.). HSEmotion teaches "facial emotion recognition" specifically — it's already seen millions of faces with emotion labels. Starting from HSEmotion gives us a huge head start. If HSEmotion weights are unavailable, the code falls back to timm's ImageNet weights automatically — but training will take longer to converge.

**Q: What's the difference between `hsemotion` and `emotiefflib`?**
> A: Both provide EfficientNet weights optimized for emotion recognition from the same research group (HSE). `emotiefflib` is the newer, video-optimized package. We install both for maximum compatibility. See `requirements.md §6.7` for details.

**Q: Can we add more emotion classes later?**
> A: Yes! The 8-class config (`efficientnet_b0_emotion_8cls.yaml`) is ready. We start with 3-class (happy/sad/neutral) for Phase 1 simplicity, but the architecture supports all 8 Ekman emotions.

**Q: What is `use_multi_task: false` in the config?**
> A: Phase 2 will add degree-of-emotion (scalar 0–1) and gesture alignment heads alongside the current categorical head. It's disabled now because the degree labels and gesture targets don't exist yet. Tell learners: "Know it's coming, don't enable it yet." See Guide 04 Appendix.

**Q: Why does the TAO guide use ResNet-18 instead of EfficientNet-B0?**
> A: Two parallel pipelines exist. PyTorch + EfficientNet-B0 is for development and experimentation. TAO + ResNet-18 is for production Jetson deployment when TAO's built-in TensorRT optimization matters. Both must independently pass Gate A and Gate B. See Guide 11 §1.3 for the full comparison.

### Training Questions

**Q: How long does training take?**
> A: With ~500 videos per class and 30 epochs:
> - GPU (RTX 3090): ~30-45 minutes
> - GPU (RTX 4090): ~15-20 minutes
> - CPU only: Several hours (not recommended)

**Q: What if my F1 score is stuck below 0.84?**
> A: Checklist:
> 1. Data balance — equal happy/sad/neutral counts?
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
model = create_efficientnet_model(num_classes=3, pretrained=True)
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
cat trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml
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
    --config fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml \
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
1. Copy the 3-class config to a new file
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

### Exercise 4: Data Curation Workflow (30 minutes)

**Instructions for learners** (requires Web UI running on Ubuntu 2):
1. Open the Streamlit UI at `http://10.0.4.140:8501`
2. Generate 6 synthetic videos (2 happy, 2 sad, 2 neutral)
3. Label each video in the labeling interface
4. Promote videos from `temp` → `dataset_all`
5. Verify the videos appear in `dataset_all/` on the filesystem
6. Check class balance in the UI dashboard

**Success criteria**: They can explain why `dataset_all` exists instead of promoting directly to `train/`.

**Learning outcome**: Understanding the full data staging pipeline and Web UI integration.

### Exercise 5: Weight Download Troubleshooting (15 minutes)

**Setup**: Temporarily rename the HSEmotion cache to simulate a missing weights scenario:
```bash
# Simulate missing weights (trainer does this before exercise)
mv ~/.cache/hsemotion ~/.cache/hsemotion_backup
```

**Task**: Have learners:
1. Try to load the model — observe what happens
2. Check the fallback chain (Guide 02, Step 6.3)
3. Identify that timm ImageNet weights are being used instead
4. Restore the cache and verify HSEmotion weights load

```bash
# Restore after exercise
mv ~/.cache/hsemotion_backup ~/.cache/hsemotion
```

**Learning outcome**: Understanding the weight source fallback and how to troubleshoot download failures.

### Exercise 6: Compare Against Worked Example (20 minutes)

**Instructions**:
1. Open Guide 10 (Worked Example) side-by-side with their MLflow run
2. Compare their training curves against the reference
3. Identify any differences in convergence, final metrics, or phase transitions
4. Write a 3-sentence summary of what they observed

**Success criteria**: They can articulate why their results differ from the reference (different data, random seed, etc.).

**Learning outcome**: Using the Worked Example as a calibration tool.

---

## Part 7: Assessment Rubric

Use this to evaluate learner readiness:

| Skill | Beginner | Competent | Proficient |
|-------|----------|-----------|------------|
| **Load model** | Needs help | Can do with docs | Can do from memory |
| **Data curation** | Confused by staging | Uses Web UI with guidance | Explains dataset_all flow |
| **Run training** | Follows exact commands | Modifies config | Creates new configs |
| **Interpret logs** | Confused by output | Identifies key metrics | Diagnoses issues |
| **Debug errors** | Asks for help | Searches docs/code | Fixes independently |
| **Explain architecture** | Reads from guide | Explains in own words | Teaches others |
| **Weight sources** | Doesn't know | Knows HSEmotion vs timm | Can troubleshoot fallback |

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

**Must-read before your first session:**

1. **ML_PIPELINE_ONBOARDING_GUIDE.md** — Learner's primary reference
2. **00_FINE_TUNING_INDEX.md** — Navigation hub with learning paths (Fast/Standard/Advanced)
3. **memory-bank/requirements.md §6.7** — Model selection rationale (EfficientNet-B0 vs B2)
4. **08_QUICK_START_HANDS_ON.md** — What learners do first (know it cold)
5. **10_WORKED_EXAMPLE_COMPLETE_RUN.md** — Reference for "what good looks like"

**Know well for Q&A:**

6. **09_WEB_UI_DATA_WORKFLOW.md** — Data curation pipeline (dataset_all staging)
7. **11_NVIDIA_TAO_TOOLKIT_GUIDE.md §1.3** — TAO vs PyTorch explanation
8. **12_N8N_ORCHESTRATION_GUIDE.md** — Agent 5 automated training workflow
9. **AGENTS.md** (Agent 5) — Training orchestrator role

### Code to Understand

```
trainer/
├── train_efficientnet.py          # Entry point — understand CLI args
├── fer_finetune/
│   ├── model_efficientnet.py      # Model class — understand forward()
│   │                               # Also: weight loading & fallback logic
│   ├── train_efficientnet.py      # Trainer class — understand train()
│   └── config.py                  # Config dataclass — know all options
│                                   # Including use_multi_task (Phase 2)
├── tao/
│   ├── specs/emotionnet_3cls.yaml # TAO config (ResNet-18, not EfficientNet)
│   └── docker-compose-tao.yml    # TAO container definitions
```

### External References

- [HSEmotion GitHub](https://github.com/HSE-asavchenko/hsemotion) — Original model source
- [EmotiEffLib PyPI](https://pypi.org/project/emotiefflib/) — Video-optimized emotion weights
- [timm documentation](https://huggingface.co/docs/timm) — Backbone library (fallback weights)
- [MLflow docs](https://mlflow.org/docs/latest/index.html) — Experiment tracking
- [EfficientNet paper](https://arxiv.org/abs/1905.11946) — Architecture reference

---

## Part 10: Post-Training Checklist

After each training session, verify learner readiness:

**Core skills (all required):**
- [ ] Can load model and run inference independently
- [ ] Can use Web UI to generate, label, and promote videos
- [ ] Can explain the `dataset_all` staging pipeline
- [ ] Can start training from command line
- [ ] Can interpret training output (loss, F1, phase transition)
- [ ] Can resume from checkpoint
- [ ] Can explain Gate A requirements
- [ ] Can explain why EfficientNet-B0 (not B2) — reference §6.7
- [ ] Knows the weight source fallback chain (HSEmotion → timm → random)
- [ ] Knows where to find documentation (Guide index, learning paths)
- [ ] Has completed at least one solo training run

**Awareness (can explain at high level):**
- [ ] Knows `use_multi_task: false` exists and what Phase 2 will change
- [ ] Knows TAO exists as an alternative production pipeline
- [ ] Knows n8n Agent 5 can trigger automated training
- [ ] Understands 3× latency headroom and shared GPU budget on Jetson

### Handoff to Project Work

Once a learner passes the core checklist:
1. Assign them a real training task (e.g., "train on the latest batch of synthetic videos")
2. Have them curate data through the Web UI first (not just handed a dataset)
3. Have them document their run in MLflow
4. Have them compare against Guide 10 (Worked Example)
5. Review their results together
6. Celebrate their first model! 🎉

---

## Appendix: Quick Reference Card

Print this for learners:

```
╔══════════════════════════════════════════════════════════════╗
║           EfficientNet-B0 Training Quick Reference           ║
╠══════════════════════════════════════════════════════════════╣
║ TRAIN (3-class):                                             ║
║   python trainer/train_efficientnet.py \                     ║
║     --config fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml ║
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
║ WEB UI:  http://10.0.4.140:8501  (data curation)            ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║ DATA FLOW:                                                   ║
║   temp/ → dataset_all/ → train/ + test/                      ║
║   (dataset_all is persistent; train/test regenerated per run)║
╠══════════════════════════════════════════════════════════════╣
║ WEIGHT SOURCES (§6.7):                                       ║
║   1. HSEmotion/EmotiEffLib (best)  2. timm (fallback)       ║
╠══════════════════════════════════════════════════════════════╣
║ GATE A REQUIREMENTS:                                         ║
║   • Macro F1 ≥ 0.84    • Balanced Accuracy ≥ 0.85           ║
║   • Per-class F1 ≥ 0.75    • ECE ≤ 0.08    • Brier ≤ 0.16  ║
╠══════════════════════════════════════════════════════════════╣
║ COMMON FIXES:                                                ║
║   • OOM error → Reduce batch_size                            ║
║   • Low F1 → More epochs, check data balance                 ║
║   • Overfitting → Increase dropout, add mixup                ║
║   • Weights missing → Check ~/.cache/hsemotion/ (see §6.3)  ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Good luck training your trainers!*
