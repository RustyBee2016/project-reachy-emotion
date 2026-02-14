# Guide 09: Web UI Data Workflow

**Duration**: 1-2 hours  
**Difficulty**: Beginner  
**Prerequisites**: Guide 03 (Data Preparation) concepts understood

---

## Overview

This guide explains how to use the **Streamlit web application** to:

1. Generate synthetic emotion videos using Luma AI
2. Label and review generated videos
3. Promote videos to training/test datasets
4. Monitor dataset balance and readiness

**The web UI is the primary interface for dataset curation in the Reachy project.**

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DATA WORKFLOW ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Web UI      │    │  FastAPI     │    │  PostgreSQL  │              │
│  │  (Streamlit) │───▶│  Backend     │───▶│  Database    │              │
│  │  Port: 8501  │    │  Port: 8000  │    │  Port: 5432  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                    │                       │
│         │                   │                    │                       │
│         ▼                   ▼                    ▼                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FILE SYSTEM                                   │   │
│  │  /media/project_data/reachy_emotion/videos/                      │   │
│  │  ├── temp/     ← New videos land here                            │   │
│  │  ├── train/    ← Promoted training videos (with labels)          │   │
│  │  └── test/     ← Promoted test videos (no labels)                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | URL | Purpose |
|-----------|-----|---------|
| **Streamlit UI** | http://10.0.4.140:8501 | User interface for all operations |
| **FastAPI Backend** | http://10.0.4.130:8000 | Media management API |
| **PostgreSQL** | 10.0.4.130:5432 | Metadata storage |
| **File Storage** | /media/project_data/... | Video and frame storage |

---

## 2. Accessing the Web UI

### Step 2.1: Open the Application

```bash
# From your local machine, open browser to:
http://10.0.4.140:8501

# Or SSH tunnel if needed:
ssh -L 8501:localhost:8501 your_username@10.0.4.140
# Then open: http://localhost:8501
```

### Step 2.2: Navigate the Interface

The web UI has these main pages:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  REACHY EMOTION - Web Interface                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📊 Dashboard          Overview of system status and metrics             │
│  ─────────────────────────────────────────────────────────────────────  │
│  🎬 Generate           Create synthetic emotion videos                   │
│  ─────────────────────────────────────────────────────────────────────  │
│  🏷️ Label              Review and label videos in temp/                  │
│  ─────────────────────────────────────────────────────────────────────  │
│  🚀 Promote            Move videos to train/ or test/                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  🏋️ Train              Monitor training runs and Gate A                  │
│  ─────────────────────────────────────────────────────────────────────  │
│  📦 Deploy             Deployment status and Gate B                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Generating Synthetic Videos

### Step 3.1: Navigate to Generate Page

1. Click **"Generate"** in the sidebar
2. You'll see the video generation interface

### Step 3.2: Configure Generation

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Generate Emotion Videos                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Target Emotion:  [Happy ▼]                                             │
│                                                                          │
│  Prompt Template: [Default Happy Expression ▼]                          │
│                                                                          │
│  Custom Prompt:                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ A person with a genuine smile, showing happiness and warmth,     │   │
│  │ natural lighting, portrait style, subtle head movement           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Number of Videos: [5]                                                   │
│                                                                          │
│  [ Generate Videos ]                                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 3.3: Generation Process

When you click "Generate Videos":

1. **API Call** → Luma AI generates video from prompt
2. **Download** → Video downloaded to `temp/` folder
3. **Metadata** → Recorded in PostgreSQL (prompt, timestamp, intended emotion)
4. **Thumbnail** → Generated for preview
5. **Status** → Video appears in Label queue

### Step 3.4: Monitor Generation

```
Generation Progress:
────────────────────────────────────────────────────────────
Video 1/5: ✅ Complete (video_abc123.mp4)
Video 2/5: ✅ Complete (video_def456.mp4)
Video 3/5: ⏳ Generating... (45 seconds remaining)
Video 4/5: ⏸️ Queued
Video 5/5: ⏸️ Queued
────────────────────────────────────────────────────────────
```

---

## 4. Labeling Videos

### Step 4.1: Navigate to Label Page

1. Click **"Label"** in the sidebar
2. Videos from `temp/` appear for review

### Step 4.2: Review Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Label Videos                                            Pending: 12     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                   │   │
│  │                    [VIDEO PLAYER]                                │   │
│  │                                                                   │   │
│  │              video_abc123.mp4                                    │   │
│  │              Generated: 2026-02-05 10:30:00                      │   │
│  │              Intended emotion: happy                             │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Does this video show the intended emotion clearly?                      │
│                                                                          │
│  Assigned Label: [Happy ▼]   [Sad ▼]   [Unclear/Reject]                │
│                                                                          │
│  Notes: ┌────────────────────────────────────────────────────────────┐  │
│         │ Clear happy expression, good lighting                       │  │
│         └────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  [ ← Previous ]   [ Accept & Next → ]   [ Reject ]                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 4.3: Labeling Guidelines

| Decision | When to Use | Outcome |
|----------|-------------|---------|
| **Accept as Happy** | Clear happy expression visible | Ready for promotion |
| **Accept as Sad** | Clear sad expression visible | Ready for promotion |
| **Reject** | Unclear, multiple emotions, poor quality | Moved to rejected/ |

### Step 4.4: Quality Criteria

For a video to be labeled:

- [ ] **Face clearly visible** throughout the video
- [ ] **Single dominant emotion** (not mixed)
- [ ] **Consistent expression** for at least 2 seconds
- [ ] **Good video quality** (not blurry, well-lit)
- [ ] **Natural appearance** (not obviously synthetic artifacts)

---

## 5. Promoting Videos to Datasets

### Step 5.1: Navigate to Promote Page

1. Click **"Promote"** in the sidebar
2. View labeled videos ready for promotion

### Step 5.2: Promotion Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Promote to Dataset                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Current Dataset Status:                                                 │
│  ────────────────────────────────────────────────────────────────────── │
│  TRAIN SET                          TEST SET                             │
│  Happy: 245 videos                  Happy: 48 videos                     │
│  Sad:   238 videos                  Sad:   52 videos                     │
│  ────────────────────                ────────────────────                │
│  Total: 483 videos                  Total: 100 videos                    │
│  Balance: 50.7% / 49.3% ✅          Balance: 48% / 52% ✅               │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  Videos Ready for Promotion: 15                                          │
│                                                                          │
│  ┌────────┬──────────┬──────────┬─────────────────────────────────────┐ │
│  │ Select │ Thumbnail│ Label    │ Destination                          │ │
│  ├────────┼──────────┼──────────┼─────────────────────────────────────┤ │
│  │ [✓]    │ 🖼️       │ Happy    │ [Train ▼]                           │ │
│  │ [✓]    │ 🖼️       │ Sad      │ [Train ▼]                           │ │
│  │ [✓]    │ 🖼️       │ Happy    │ [Test ▼]                            │ │
│  │ [ ]    │ 🖼️       │ Sad      │ [Train ▼]                           │ │
│  └────────┴──────────┴──────────┴─────────────────────────────────────┘ │
│                                                                          │
│  [ Select All ]  [ Promote Selected (3) ]                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 5.3: Promotion Rules

**For Training Set (`train/`):**
- Videos MUST have a label (happy or sad)
- Aim for 50/50 class balance
- No minimum per class, but more is better

**For Test Set (`test/`):**
- Videos should NOT have labels stored (labels are ground truth only)
- Used for final evaluation
- Aim for at least 20 per class for statistical validity

### Step 5.4: Balance Monitoring

```
Dataset Balance Check:
────────────────────────────────────────────────────────────

TRAINING SET
┌──────────────────────────────────────────────────────────┐
│ Happy: ████████████████████████████████████████ 245 (50.7%)
│ Sad:   ███████████████████████████████████████  238 (49.3%)
└──────────────────────────────────────────────────────────┘
Balance Ratio: 0.97 ✅ (threshold: > 0.80)

TEST SET  
┌──────────────────────────────────────────────────────────┐
│ Happy: ████████████████████████████████████████  48 (48.0%)
│ Sad:   ██████████████████████████████████████████ 52 (52.0%)
└──────────────────────────────────────────────────────────┘
Balance Ratio: 0.92 ✅ (threshold: > 0.80)

Overall Status: ✅ READY FOR TRAINING
  - Train set: 483 videos (minimum: 200)
  - Test set: 100 videos (minimum: 40)
  - Both sets balanced
```

---

## 6. Monitoring Training Readiness

### Step 6.1: Dashboard Overview

The Dashboard shows real-time status:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  REACHY EMOTION - Dashboard                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATA PIPELINE STATUS                                                    │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📥 Temp Queue        │  15 videos awaiting labeling                    │
│  🏷️ Labeled           │  8 videos ready for promotion                   │
│  🚀 Train Set         │  483 videos (balanced ✅)                        │
│  📊 Test Set          │  100 videos (balanced ✅)                        │
│                                                                          │
│  TRAINING READINESS                                                      │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  ✅ Minimum train samples met (483 ≥ 200)                               │
│  ✅ Minimum test samples met (100 ≥ 40)                                 │
│  ✅ Train set balanced (ratio: 0.97)                                    │
│  ✅ Test set balanced (ratio: 0.92)                                     │
│                                                                          │
│  [ 🏋️ START TRAINING ]                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 6.2: Training Trigger

When all conditions are met, the "Start Training" button becomes active:

1. Click **"Start Training"**
2. Select configuration: `efficientnet_b0_emotion_2cls.yaml`
3. Set run name (optional)
4. Training begins on Ubuntu 1

---

## 7. API Endpoints Reference

For automation and scripting, these API endpoints are available:

### Video Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/media/videos` | GET | List all videos |
| `/api/media/videos/{id}` | GET | Get video details |
| `/api/media/promote` | POST | Promote video to train/test |
| `/api/media/label` | PUT | Update video label |
| `/api/media/stats` | GET | Get dataset statistics |

### Example: Get Dataset Stats

```bash
curl -X GET "http://10.0.4.130:8000/api/media/stats" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "train": {
    "happy": 245,
    "sad": 238,
    "total": 483,
    "balance_ratio": 0.97
  },
  "test": {
    "happy": 48,
    "sad": 52,
    "total": 100,
    "balance_ratio": 0.92
  },
  "temp": {
    "unlabeled": 15,
    "labeled": 8
  },
  "ready_for_training": true
}
```

---

## 8. Best Practices

### Data Quality

1. **Generate diverse prompts** — Vary lighting, angles, and expressions
2. **Reject ambiguous videos** — Better to have less data than noisy data
3. **Maintain balance** — Keep both classes within 60/40 ratio

### Workflow Efficiency

1. **Batch generation** — Generate 10-20 videos at a time
2. **Regular labeling sessions** — Don't let temp/ queue grow too large
3. **Promote frequently** — Keep datasets current

### Quality Control

1. **Review promoted videos periodically** — Spot-check for errors
2. **Track rejection rate** — High rejection indicates prompt issues
3. **Monitor training metrics** — Poor F1 may indicate labeling problems

---

## 9. Troubleshooting

### Issue: Videos Not Appearing in Label Queue

**Check:**
1. Generation completed successfully
2. FastAPI service is running: `systemctl status fastapi-media`
3. Database connection: `psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion`

### Issue: Promotion Fails

**Check:**
1. File permissions on `/media/project_data/`
2. Disk space: `df -h /media/project_data/`
3. API logs: `journalctl -u fastapi-media -f`

### Issue: Balance Warning

**Solution:**
- Generate more videos for the minority class
- Temporarily pause promotion of majority class

---

## 10. Summary

### Workflow Recap

```
Generate → Label → Promote → Train
   │         │        │        │
   │         │        │        └─► EfficientNet-B0 fine-tuning
   │         │        └─────────► Move to train/ or test/
   │         └──────────────────► Human review and labeling
   └────────────────────────────► Luma AI video creation
```

### Key URLs

| Service | URL |
|---------|-----|
| Web UI | http://10.0.4.140:8501 |
| API Docs | http://10.0.4.130:8000/docs |
| MLflow | http://10.0.4.130:5000 |

### Next Steps

1. Generate your first batch of videos
2. Practice the labeling workflow
3. Build up dataset to training threshold
4. Run your first training job

---

*Continue to [Guide 04: Training Walkthrough](04_TRAINING_WALKTHROUGH.md) when your dataset is ready.*
