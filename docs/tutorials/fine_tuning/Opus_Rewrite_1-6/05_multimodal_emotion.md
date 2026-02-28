# Tutorial 05: Multimodal Emotion Recognition

## Overview

This tutorial covers audiovisual approaches to emotion recognition — combining
facial expression analysis with audio cues (speech prosody, tone) for improved
accuracy. This is **Path C** from the [overview](01_overview.md) and is
primarily relevant for research or scenarios where audio context is available
alongside the camera feed.

> **Status**: Exploratory. The Reachy pipeline currently operates on video-only
> input via DeepStream. Integrating audio requires changes to the Jetson
> capture pipeline and is not part of the current deployment plan.

---

## References

### Primary repositories

- **Audiovisual emotion recognition** (bichuyen99):
  [bichuyen99/Audiovisual_emotion_recognition](https://github.com/bichuyen99/Audiovisual_emotion_recognition)
  — Transformer-based audio-visual fusion using HSEmotion features, targeting
  ABAW challenge tasks on the Aff-Wild2 dataset.

- **End-to-End Multimodal emotion recognition** (She-yh):
  [She-yh/End-to-End-Multimodal-emotion-recognition](https://github.com/She-yh/End-to-End-Multimodal-emotion-recognition)
  — Inference-only pipeline using EfficientFace + MFCC audio features with a
  MultiModalCNN fusion model.

### Relationship to HSEmotion

Both projects build on the HSEmotion/EmotiEffLib ecosystem:

- **bichuyen99** uses `enet_b2_8` (EfficientNet-B2 from HSEmotion) as a **frozen
  visual feature extractor** and combines it with audio features via learned
  fusion layers.
- **She-yh** uses EfficientFace (a different model from EfficientNet) trained on
  AffectNet, combined with MFCC audio features.

---

## Architecture: Audiovisual Fusion (bichuyen99)

### Feature extraction

```
Video frames → Face detection → Face crops → EfficientNet-B2 → 1408-dim features
Audio track  → Resampling    → Wav2Vec2    → 768-dim features
                              → VGGish      → 128-dim features
```

### Fusion models

Three task-specific fusion architectures are provided:

| Model | Task | Input Dim | Architecture | Output |
|-------|------|-----------|--------------|--------|
| `EXP_fusion` | Expression classification | 2176 | Conv1D → 4-layer Transformer (128-dim, 4 heads) | 8 classes (softmax) |
| `AU_fusion` | Action Unit detection | 2176 | Same Transformer | 12 AUs (sigmoid) |
| `VA_fusion` | Valence-Arousal estimation | 2176 | Dual-head Transformer | 2 values (tanh) |
| `MLPModel` | Any task | Variable | 2-layer MLP (→ 128 → output) | Task-dependent |

### Audio-visual synchronization

Features are aligned by mapping audio representations to video frames:

```python
audio_scale = len(audio_reps) / num_video_frames
frame_audio_index = int(frame_number * audio_scale)
```

### Key hyperparameters

- Batch size: 32
- Dropout: 0.3
- Transformer heads: 4
- Transformer layers: 4
- Hidden dimension: 128
- Train/val split: 80/20

### Reported performance (Aff-Wild2)

| Task | Best Config | Score |
|------|-------------|-------|
| Expression (F1) | EfficientNet-B2 + Wav2Vec2 + MLP + smoothing | 0.457 |
| Action Units (F1) | EfficientNet-B2 + B0 + VGGish | 0.54 |
| Valence-Arousal (CCC) | Wav2Vec2 + VGGish | 0.510 |

---

## Architecture: End-to-End Multimodal (She-yh)

### Pipeline

```
Raw video → MTCNN face detection → 15 frames → EfficientFace → visual features
Raw audio → Resample 22050 Hz   → 3.6s pad  → MFCC (10 coeff) → audio features
                                                                       │
                                                     MultiModalCNN fusion
                                                           │
                                                    8-class prediction
```

### Configuration

- Input: 224×224 video frames
- Temporal window: 15 frames per 3.6-second segment
- Audio: MFCC with 10 components
- Fusion strategies: late (`lt`), intermediate (`it`), intermediate + attention (`ia`)
- Emotion classes: neutral, calm, happy, sad, angry, fearful, disgust, surprised

### Usage

```bash
# Inference only — no training required
python main.py
# Processes videos from raw_data/ directory
```

---

## Adapting Audiovisual Fusion for Reachy

If the Reachy pipeline were extended to include microphone input, the
bichuyen99 approach could be adapted as follows:

### Step 1: Extract visual features using EmotiEffLib

```python
from emotiefflib.facial_analysis import EmotiEffLibRecognizer
import torch

# Use EmotiEffLib as the visual feature extractor
visual_model = EmotiEffLibRecognizer(
    engine="torch",
    model_name="enet_b2_8",
    device="cuda"
)

# Extract features per frame
visual_features = []
for face_crop in detected_faces:
    feat = visual_model.extract_features(face_crop)  # (1, 1408)
    visual_features.append(feat)

visual_tensor = torch.tensor(visual_features)  # (T, 1408)
```

### Step 2: Extract audio features

```python
import torchaudio

# Load Wav2Vec2 for audio features
bundle = torchaudio.pipelines.WAV2VEC2_BASE
wav2vec_model = bundle.get_model().to('cuda')

# Load and preprocess audio
waveform, sample_rate = torchaudio.load('audio.wav')
if sample_rate != bundle.sample_rate:
    waveform = torchaudio.transforms.Resample(
        sample_rate, bundle.sample_rate
    )(waveform)

with torch.no_grad():
    audio_features, _ = wav2vec_model.extract_features(
        waveform.to('cuda')
    )
    audio_tensor = audio_features[-1]  # Last layer: (1, T_audio, 768)
```

### Step 3: Align and fuse

```python
# Align audio to video frames
num_video_frames = len(visual_features)
audio_scale = audio_tensor.shape[1] / num_video_frames

aligned_audio = []
for i in range(num_video_frames):
    audio_idx = min(int(i * audio_scale), audio_tensor.shape[1] - 1)
    aligned_audio.append(audio_tensor[0, audio_idx])

audio_aligned = torch.stack(aligned_audio)  # (T, 768)

# Concatenate for fusion
fused = torch.cat([visual_tensor, audio_aligned], dim=-1)  # (T, 2176)
```

### Step 4: Fusion classifier

```python
import torch.nn as nn

class EmotionFusionModel(nn.Module):
    """Simple fusion model following bichuyen99's approach."""

    def __init__(self, input_dim=2176, hidden_dim=128, num_classes=2,
                 num_heads=4, num_layers=4, dropout=0.3):
        super().__init__()
        self.proj = nn.Conv1d(input_dim, hidden_dim, kernel_size=1)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        x = self.proj(x.transpose(1, 2)).transpose(1, 2)
        x = self.transformer(x)
        x = x.mean(dim=1)  # temporal average pooling
        return self.classifier(x)

fusion_model = EmotionFusionModel(
    input_dim=2176,  # 1408 visual + 768 audio
    num_classes=2     # happy, sad
)
```

---

## Jupyter Notebooks from Referenced Repositories

### bichuyen99/Audiovisual_emotion_recognition

| Notebook | Purpose |
|----------|---------|
| `audiovisual_emo_reg.ipynb` | Complete workflow: data loading, feature extraction, training, evaluation |
| `testing.ipynb` | Model evaluation pipeline |

### Key scripts

| File | Purpose |
|------|---------|
| `dataset.py` | Aff-Wild2 data loading |
| `extract_feature.py` | Visual + audio feature extraction |
| `models.py` | Transformer & MLP fusion models |
| `metric.py` | F1, Mean CCC evaluation metrics |

### She-yh/End-to-End-Multimodal-emotion-recognition

| File | Purpose |
|------|---------|
| `main.py` | Entry point for inference |
| `extract.py` | Face detection + audio extraction |
| `model.py` | Model loading wrapper |
| `opts.py` | Configuration and hyperparameters |

---

## Considerations for the Reachy Project

### Current limitations

1. **No microphone input**: The Jetson DeepStream pipeline processes video only.
   Adding audio requires hardware (USB/I2S microphone) and GStreamer audio
   source elements.
2. **Latency**: Wav2Vec2 adds ~50 ms inference time per audio segment. The
   combined pipeline may exceed the 120 ms P50 latency target (Gate B).
3. **Synchronization**: Audio-visual alignment on a live stream requires careful
   buffering and timestamp management.

### When multimodal makes sense

- **Offline analysis**: Processing recorded videos where latency is not a
  constraint.
- **Ambiguous expressions**: When facial cues alone are insufficient (e.g.,
  subtle sadness with neutral face but sad voice tone).
- **Research/evaluation**: Comparing visual-only vs. audiovisual accuracy on the
  Reachy dataset.

### Recommended approach

1. Start with visual-only (Path A or B) for production deployment.
2. Use the audiovisual pipeline offline to evaluate potential accuracy gains.
3. If gains are significant, explore lightweight audio features (MFCC) instead
   of Wav2Vec2 to meet latency constraints.

---

## Next Steps

- For visual-only fine-tuning, see
  [03_hsemotion_finetuning.md](03_hsemotion_finetuning.md).
- For a drop-in inference API, see
  [04_emotiefflib_guide.md](04_emotiefflib_guide.md).
- For choosing between approaches, see
  [06_model_comparison.md](06_model_comparison.md).
