# Reachy Emotion Classification System
## High-Level Project Presentation

**Russell Bray**
**Loyola University Chicago — M.S. Computer Science**
**May 2026**

---

# Slide 1: Title

## Reachy Emotion Classification System
### A Privacy-First Emotion Recognition Platform for Social Robotics

- **Author:** Russell Bray
- **Program:** M.S. Computer Science, Loyola University Chicago
- **Date:** May 2026

**Keywords:** Facial emotion recognition, transfer learning, EfficientNet, privacy-first AI, edge deployment, social robotics

---

# Slide 2: Problem & Motivation

## Why Emotion Recognition for Social Robots?

Social companion robots need to perceive and respond to human emotions in real time.

### Three Core Challenges

| Challenge | Requirement |
|-----------|------------|
| **Real-time inference** | < 120 ms latency on edge hardware |
| **Privacy-first** | No raw video leaves the local network |
| **Asymmetric errors** | Not all misclassifications are equal |

### Key Insight
> A robot that misidentifies a neutral person as sad (triggering unsolicited empathy) creates a **worse** user experience than one that misses a happy expression.
>
> Aggregate accuracy alone is insufficient — the **distribution and consequences** of errors must be analyzed.

---

# Slide 3: System Architecture

## Three-Node Local-Only Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│   Ubuntu 1      │    │   Ubuntu 2      │    │  Jetson Xavier NX   │
│   10.0.4.130    │◄──►│   10.0.4.140    │    │  10.0.4.150         │
│                 │    │                 │    │                     │
│ • GPU Training  │    │ • Streamlit UI  │    │ • DeepStream + TRT  │
│ • FastAPI       │    │ • Nginx (HTTPS) │    │ • Real-time FER     │
│ • PostgreSQL    │    │                 │    │ • Reachy Mini Robot │
│ • n8n Agents    │    │                 │    │                     │
│ • MLflow        │    │                 │    │                     │
└─────────────────┘    └─────────────────┘    └─────────────────────┘
```

- **Zero cloud dependencies** — all processing on-premise
- **10-agent n8n orchestration** automates the full ML lifecycle
- **Privacy by architecture** — data minimization enforced by design

---

# Slide 4: Model Design

## EfficientNet-B0 with HSEmotion Pre-Training

**Backbone:** EfficientNet-B0 pre-trained on VGGFace2 (3.3M faces) + AffectNet (450K labeled faces)

**Classification:** 3-class head → Happy, Sad, Neutral

### Two Model Variants

| | Variant 1 (Frozen) | Variant 2 (Fine-Tuned) |
|---|---|---|
| **Backbone** | Completely frozen | blocks.5, blocks.6, conv_head unfrozen |
| **Trainable params** | ~4,000 | ~500,000 |
| **GPU time** | ~2 hours | ~26 hours (90-trial sweep) |
| **Strategy** | Preserve pre-trained features | Adapt backbone to target domain |

### Training Data
- **86,519 synthetic face-cropped frames** from 11,911 AI-generated videos
- **894 real AffectNet photographs** used only at test time (zero real data in training)

---

# Slide 5: The Face Cropping Discovery

## Data Pipeline > Model Architecture

| Configuration | V1 Test F1 | V2 Test F1 |
|--------------|-----------|-----------|
| Without face crop (run_0104) | 0.43 | 0.44 |
| **With face crop (run_0107)** | **0.781** | **0.780** |
| **Improvement** | **+82%** | **+77%** |

### Lesson Learned
- The **single most impactful change** was a preprocessing flag: `face_crop=True`
- The domain gap was in **backgrounds and body context**, not in facial expressions
- A 90-trial hyperparameter sweep (+26 hours GPU) produced negligible improvement
- **Data-centric AI principle:** Pipeline quality often outweighs model complexity

---

# Slide 6: Results — The Deceptive Similarity

## Near-Identical Aggregate Scores Hide Critical Differences

| Metric | V1 | V2 | Winner |
|--------|-----|-----|--------|
| **F1 Macro** | **0.781** | 0.780 | V1 |
| Accuracy | 0.771 | **0.817** | V2 |
| **F1 Happy** | 0.777 | **0.946** | V2 |
| **F1 Sad** | **0.822** | 0.694 | V1 |
| **F1 Neutral** | **0.743** | 0.699 | V1 |

### Performance Equity (Coefficient of Variation)
- **V1 CV = 4.2%** — balanced across all classes
- **V2 CV = 15.1%** — specialized in happy, neglects sad and neutral

### Gate A-Deploy Compliance
- **V1: 6/6 gates PASSED**
- **V2: 4/6 gates FAILED** (sad F1 = 0.694 < 0.70, neutral F1 = 0.699 < 0.70)

---

# Slide 7: Why Variant 1 Was Selected

## Error Consequences Matter More Than Error Rates

### V1's Dominant Error: Happy → Neutral (33.8%)
- Robot **under-reacts** with a calm, neutral demeanor
- **Behaviorally benign** — unlikely to cause social friction
- Zero cross-valence errors (happy ↔ sad)

### V2's Dominant Error: Neutral → Sad (35.1%)
- Robot offers **unsolicited empathy** to people who are simply at rest
- **Behaviorally disruptive** — "I see you're feeling sad..." to a neutral person
- V2 sad precision only 56.5% — wrong nearly half the time

### Real-World Impact
> Neutral is ~75% of real interactions. V2 would trigger inappropriate sadness responses in **~1 in 4 neutral encounters**.

**Decision: Deploy V1 (run_0107) with HIGH confidence**

---

# Slide 8: Deployment Pipeline

## From PyTorch to Real-Time Robot Inference

```
PyTorch Model → ONNX Export → TensorRT (FP16) → DeepStream Pipeline → Reachy Mini
```

### Edge Performance (Jetson Xavier NX)
| Metric | Target | Achieved |
|--------|--------|----------|
| Latency (p50) | ≤ 120 ms | ✅ < 120 ms |
| GPU Memory | ≤ 2.5 GB | ✅ < 0.8 GB |
| Frame Rate | ≥ 25 FPS | ✅ ≥ 25 FPS |

### Safety Features
- **Abstention:** Confidence < 0.60 → no gesture (robot holds current state)
- **5-tier gesture modulation:** Expressiveness scales with prediction confidence
- **Automatic rollback:** Gate B failure restores previous engine

---

# Slide 9: Future Work

## Closing the Synthetic-to-Real Gap

| Priority | Enhancement | Expected Impact |
|----------|------------|-----------------|
| 1 | **Temperature scaling** | ECE 0.102 → ~0.06 (1 day effort) |
| 2 | **Mixed-domain training** (10-20% real data) | F1 0.78 → ~0.84 |
| 3 | **V1+V2 ensemble** (complementary strengths) | Higher per-class F1 |
| 4 | **8-class Ekman expansion** | Anger, fear, disgust, surprise |
| 5 | **Domain adaptation** | Adversarial training, style transfer |

### Base Model Ceiling: F1 = 0.926
The HSEmotion base model (trained on real data) shows what is achievable — a 14.5 pp gap remains as the target for improvement.

---

# Slide 10: Key Takeaways

## Five Lessons from the Reachy Project

1. **Preprocessing > Architecture**
   Face cropping (+82% F1) outperformed a 90-trial hyperparameter sweep

2. **Aggregate metrics deceive**
   F1 macro Δ = 0.001 concealed fundamentally different error profiles (CV 4.2% vs 15.1%)

3. **Define quality gates before evaluation**
   Per-class F1 gates caught a failure that global metrics missed entirely

4. **Error consequences are context-dependent**
   Under-reaction (V1) is far more tolerable than over-reaction (V2) in companion robotics

5. **Privacy constraints become features**
   Local-only processing → lower latency, higher availability, simpler compliance, greater user trust

---

*Slide deck based on: Reachy_Emotion_Classification_Research_Paper_Concise.md*
*Russell Bray — Loyola University Chicago — May 2026*
