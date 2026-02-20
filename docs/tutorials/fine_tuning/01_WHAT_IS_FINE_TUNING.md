# Guide 01: What is Fine-Tuning?

**Duration**: 1-2 hours  
**Difficulty**: Beginner  
**Prerequisites**: None

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Understand what fine-tuning means
- [ ] Know why we use transfer learning
- [ ] Understand the two-phase training strategy
- [ ] Know what EfficientNet-B0 is and why we use it

---

## 1. The Problem We're Solving

### What Reachy Needs

The Reachy robot needs to recognize human emotions from video:
- **Input**: Video frames showing a person's face
- **Output**: Emotion classification (happy, sad, neutral, angry, etc.)

### Why This is Hard

Training a neural network from scratch requires:
- **Millions of labeled images** (we don't have this)
- **Weeks of training time** (expensive)
- **Risk of poor results** (might not work)

### The Solution: Transfer Learning

Instead of starting from scratch, we use a model that already learned useful features from millions of images, then adapt it to our specific task.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRANSFER LEARNING                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Pre-trained Model              Our Task                           │
│   (ImageNet: 14M images)         (Emotion: ~10K images)             │
│                                                                      │
│   ┌─────────────────┐            ┌─────────────────┐                │
│   │ Learned:        │            │ Need to learn:  │                │
│   │ - Edges         │ ────────▶  │ - Facial        │                │
│   │ - Textures      │  Transfer  │   expressions   │                │
│   │ - Shapes        │  Knowledge │ - Emotion       │                │
│   │ - Objects       │            │   patterns      │                │
│   └─────────────────┘            └─────────────────┘                │
│                                                                      │
│   Result: Train faster with less data and better results!           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. What is Fine-Tuning?

### Simple Analogy

Imagine you're a chef who learned to cook Italian food for 10 years. Now you want to cook Japanese food.

**Option A: Start from scratch**
- Forget everything you know
- Learn to hold a knife again
- Takes 10 more years

**Option B: Transfer your skills (Fine-tuning)**
- Keep your knife skills, timing, flavor sense
- Just learn the new recipes and techniques
- Takes a few months

Fine-tuning is Option B for neural networks.

### Technical Definition

**Fine-tuning** = Taking a pre-trained model and training it further on your specific dataset.

```
Pre-trained Model (ImageNet)
        │
        │  Fine-tune on emotion data
        ▼
Emotion Classifier (Reachy)
```

### What Gets Transferred?

A neural network learns features in layers:

```
Layer 1 (Early): Edges, colors, simple patterns
        ↓
Layer 2: Textures, gradients
        ↓
Layer 3: Parts (eyes, nose, mouth)
        ↓
Layer 4: Objects (faces, expressions)
        ↓
Layer 5 (Late): High-level concepts
        ↓
Classification Head: "This is happy/sad/neutral/angry"
```

**Early layers** learn general features useful for ANY image task.
**Later layers** learn task-specific features.

When fine-tuning:
- **Keep** early layer knowledge (edges, textures)
- **Adapt** later layers for emotions
- **Replace** classification head for our classes

---

## 3. Our Model: EfficientNet-B0 (HSEmotion)

### What is EfficientNet-B0?

**EfficientNet-B0** is a neural network architecture designed by Google in 2019. It uses a "compound scaling" method that balances network depth, width, and resolution to achieve excellent accuracy with fewer parameters than older architectures.

### Why EfficientNet-B0?

| Feature | Benefit for Reachy |
|---------|-------------------|
| **Efficient** | Smaller model, faster inference |
| **High accuracy** | State-of-the-art on emotion benchmarks |
| **Edge-optimized** | Runs well on Jetson Xavier NX |
| **HSEmotion pre-trained** | VGGFace2 + AffectNet weights available |
| **3× latency headroom** | ~40 ms vs 120 ms budget — leaves room for gesture planning |
| **3× memory headroom** | ~0.8 GB vs 2.5 GB budget — protects future multimodal features |

### What About EfficientNet-B2?

HSEmotion also provides `enet_b2_8` weights, which offer higher accuracy in unconstrained settings. However, **B2 is not approved for production** because:

- Expected to **exceed** Jetson latency limit (≤120 ms)
- Expected to **exceed** Jetson GPU memory limit (≤2.5 GB)
- Requirements mandate a full **benchmark/validation cycle** and Gate B re-establishment before any promotion to B2

**Bottom line**: Use B0 unless the hardware constraints change. See `requirements.md §6.7` for the full rationale.

### EfficientNet-B0 Architecture (Simplified)

```
Input Image (224×224×3)
        │
        ▼
┌───────────────────┐
│   Conv Stem       │  ← Initial feature extraction
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Blocks 1-4      │  ← MBConv blocks (early layers)
│   (early blocks)  │     Keep frozen during Phase 1
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Blocks 5-6      │  ← MBConv blocks (late layers)
│   (late blocks)   │     We unfreeze these in Phase 2
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Conv Head       │  ← Final convolution
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Global Avg Pool  │  ← Reduces to 1280 features
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Classification   │  ← We replace this for emotions
│      Head (FC)    │
└───────────────────┘
        │
        ▼
Output: [happy, sad, neutral, angry, ...]
```

### Pre-trained Weights (HSEmotion)

Our model uses **HSEmotion** weights (`enet_b0_8_best_vgaf`), pre-trained on:
1. **VGGFace2** (3.3 million facial images)
2. **AffectNet** (450K facial images with 8 emotions)

This gives us an exceptional starting point specifically optimized for facial emotion recognition.

---

## 4. Two-Phase Training Strategy

### Why Two Phases?

If we unfreeze everything at once:
- Early layers might "forget" useful features
- Training is unstable
- Results are worse

Instead, we train in two phases:

### Phase 1: Train Head Only (Frozen Backbone)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: FROZEN BACKBONE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────┐                                               │
│   │   Backbone      │  🔒 FROZEN (no updates)                       │
│   │ (EfficientNet)  │  - Keeps pre-trained knowledge                │
│   │                 │  - Parameters don't change                    │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │  Classification │  🔓 TRAINABLE                                 │
│   │      Head       │  - Learns to classify emotions                │
│   │   (new layer)   │  - Fast training (few parameters)             │
│   └─────────────────┘                                               │
│                                                                      │
│   Duration: ~5 epochs                                                │
│   Purpose: Adapt head to emotion classes                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**What happens**:
- Backbone extracts features (frozen, doesn't learn)
- Head learns to map features → emotions
- Fast because only ~4,000 parameters update

### Phase 2: Fine-tune Backbone (Selective Unfreezing)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: SELECTIVE UNFREEZING                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────┐                                               │
│   │  Layers 1-3     │  🔒 FROZEN (still)                            │
│   │  (early layers) │  - Keep general features                      │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │    Layer 4      │  🔓 TRAINABLE (unfrozen)                      │
│   │  (late layer)   │  - Adapts to emotion-specific features        │
│   │                 │  - Lower learning rate (0.1× head)            │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │  Classification │  🔓 TRAINABLE                                 │
│   │      Head       │  - Continues learning                         │
│   └─────────────────┘                                               │
│                                                                      │
│   Duration: ~15 epochs                                               │
│   Purpose: Adapt backbone to emotion-specific features              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**What happens**:
- Layer 4 learns emotion-specific features
- Head continues improving
- Slower because more parameters, but better results

### Why Different Learning Rates?

```
Component          Learning Rate    Why?
─────────────────────────────────────────────────────────────
Classification     1.0× (base)      New layer, needs to learn fast
Head

Layer 4            0.1× (lower)     Already has good features,
(backbone)                          just needs small adjustments
```

If backbone learns too fast, it "forgets" useful pre-trained features.

---

## 5. Training Concepts

### Epochs

An **epoch** = one complete pass through all training data.

```
Training Data: 1000 images
Batch Size: 32 images

1 Epoch = 1000 / 32 = ~31 batches
         = Model sees every image once
```

Typical training: 20-50 epochs

### Batches

A **batch** = small group of images processed together.

```
Why batches?
- Can't fit all images in GPU memory
- Provides stable gradient estimates
- Allows parallelization

Typical batch size: 16-64 images
```

### Learning Rate

The **learning rate** controls how big the update steps are.

```
Too high:  Model overshoots, never converges
           Loss: 2.3 → 5.1 → 12.4 → NaN  ❌

Too low:   Model learns very slowly
           Loss: 2.3 → 2.29 → 2.28 → ...  ❌

Just right: Model converges smoothly
            Loss: 2.3 → 1.8 → 1.2 → 0.5  ✅
```

Our default: `0.001` (1e-3) for head, `0.0001` (1e-4) for backbone

### Loss Function

The **loss** measures how wrong the model's predictions are.

```
Prediction: [0.8, 0.1, 0.1]  (80% happy, 10% sad, 10% angry)
True label: [1.0, 0.0, 0.0]  (100% happy)

Loss = Cross-entropy(prediction, true) = 0.22  (low = good)
```

Goal: Minimize loss by adjusting model weights.

---

## 6. Our Training Configuration

### 2-Class Model (Happy/Sad)

For the Reachy robot, we now use 3-class classification with a neutral baseline:

| Setting | Value | Why |
|---------|-------|-----|
| Classes | 3 (happy, sad, neutral) | Adds a neutral baseline for comparison while staying tractable |
| Input size | 224×224 | Standard for EfficientNet-B0 |
| Batch size | 32 | Good balance of speed/stability |
| Phase 1 epochs | 5 | Enough to train head |
| Phase 2 epochs | 15 | Fine-tune backbone |
| Learning rate | 0.001 | Standard starting point |
| Optimizer | AdamW | Modern, works well |

### 8-Class Model (All Emotions)

For full emotion recognition:

| Setting | Value |
|---------|-------|
| Classes | 8 (anger, contempt, disgust, fear, happiness, neutral, sadness, surprise) |
| Total epochs | 30 |
| Everything else | Same as 3-class |

---

## 7. Knowledge Check

Test your understanding:

1. **What is fine-tuning?**
   <details>
   <summary>Answer</summary>
   Taking a pre-trained model and training it further on your specific dataset.
   </details>

2. **Why do we use two-phase training?**
   <details>
   <summary>Answer</summary>
   To prevent the backbone from "forgetting" useful pre-trained features. Phase 1 trains only the head, Phase 2 carefully fine-tunes the backbone with a lower learning rate.
   </details>

3. **What is an epoch?**
   <details>
   <summary>Answer</summary>
   One complete pass through all training data.
   </details>

4. **Why does the backbone use a lower learning rate than the head?**
   <details>
   <summary>Answer</summary>
   The backbone already has good features from pre-training. Large updates would destroy this knowledge. Small updates allow gentle adaptation.
   </details>

5. **What does the loss measure?**
   <details>
   <summary>Answer</summary>
   How wrong the model's predictions are. Lower loss = better predictions.
   </details>

---

## 8. Summary

### Key Takeaways

1. **Fine-tuning** adapts a pre-trained model to a new task
2. **Transfer learning** saves time and improves results
3. **EfficientNet-B0** is our backbone, pre-trained on emotion data (HSEmotion)
4. **Two-phase training** protects pre-trained knowledge
5. **Phase 1**: Frozen backbone, train head only
6. **Phase 2**: Unfreeze blocks 5-6, fine-tune with lower LR

### What's Next

In the next guide, we'll set up the training environment:
- Install dependencies
- Verify GPU access
- Download pre-trained weights

---

## Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| What fine-tuning is | __ |
| Why transfer learning helps | __ |
| Two-phase training strategy | __ |
| What epochs and batches are | __ |
| What learning rate controls | __ |

**All 3s?** → Ready for [Guide 02: Environment Setup](02_ENVIRONMENT_SETUP.md)  
**Any 1s?** → Re-read those sections before continuing

---

*Next: [Guide 02: Environment Setup](02_ENVIRONMENT_SETUP.md)*
