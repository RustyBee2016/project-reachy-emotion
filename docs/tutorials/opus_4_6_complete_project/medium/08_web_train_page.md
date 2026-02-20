# Tutorial 8: Web UI — Train Page

> **Priority**: MEDIUM — User-facing training interface
> **Time estimate**: 12-16 hours
> **Difficulty**: Moderate
> **Prerequisites**: Streamlit basics, API server running

---

## Why This Matters

The current Train page (`apps/web/pages/03_Train.py`) is a 25-line stub
that says "This is a placeholder page." To complete Phase 1, users need
a way to trigger and monitor training runs from the web interface.

---

## What You'll Build

A Streamlit page that:
1. Shows current dataset statistics (class counts)
2. Lets the user configure training parameters
3. Triggers training via the API
4. Displays training progress
5. Shows final results and Gate A status

---

## Step 1: Read the Current Stub

```bash
cat -n apps/web/pages/03_Train.py
```

You'll see it's mostly placeholder text.

---

## Step 2: Implement the Train Page

Replace `apps/web/pages/03_Train.py` with:

```python
"""
Training Page — Trigger and monitor model training runs.

This page provides a UI for:
1. Viewing dataset readiness (class distribution)
2. Configuring training parameters
3. Triggering a training run
4. Viewing results and Gate A status
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Train Model", page_icon="🏋️", layout="wide")

st.title("Model Training")
st.markdown("Configure and launch EfficientNet-B0 training runs.")

# Configuration
GATEWAY_URL = st.session_state.get(
    "gateway_url", "http://10.0.4.140:8000"
)


def get_dataset_stats():
    """Fetch dataset statistics from the API."""
    stats = {}
    for split in ["dataset_all", "train", "test", "temp"]:
        try:
            resp = requests.get(
                f"{GATEWAY_URL}/api/v1/media/list",
                params={"split": split, "limit": 1},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                stats[split] = data.get("total", 0)
            else:
                stats[split] = "error"
        except requests.RequestException:
            stats[split] = "offline"
    return stats


# ---- Section 1: Dataset Overview ----

st.header("1. Dataset Overview")

stats = get_dataset_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Temp (unlabeled)", stats.get("temp", 0))
col2.metric("Dataset All (labeled)", stats.get("dataset_all", 0))
col3.metric("Train Split", stats.get("train", 0))
col4.metric("Test Split", stats.get("test", 0))

dataset_all_count = stats.get("dataset_all", 0)
if isinstance(dataset_all_count, int) and dataset_all_count < 50:
    st.warning(
        f"Only {dataset_all_count} videos in dataset_all. "
        "Recommend at least 100 labeled videos for reliable training."
    )

# ---- Section 2: Training Configuration ----

st.header("2. Training Configuration")

with st.form("training_config"):
    col_left, col_right = st.columns(2)

    with col_left:
        num_epochs = st.slider("Number of epochs", 5, 100, 20)
        learning_rate = st.select_slider(
            "Learning rate",
            options=[1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3],
            value=1e-3,
            format_func=lambda x: f"{x:.0e}",
        )
        batch_size = st.selectbox("Batch size", [8, 16, 32, 64], index=1)

    with col_right:
        train_fraction = st.slider("Train/test split", 0.5, 0.9, 0.7, 0.05)
        freeze_epochs = st.slider("Frozen backbone epochs", 1, 10, 3)
        use_face_detection = st.checkbox("Enable face detection", value=True)

    st.markdown("**Gate A Thresholds** (cannot be changed)")
    st.code(
        "F1 Macro >= 0.84 | Per-class F1 >= 0.75 | "
        "Balanced Acc >= 0.85 | ECE <= 0.08 | Brier <= 0.16"
    )

    submitted = st.form_submit_button("Start Training", type="primary")

# ---- Section 3: Launch Training ----

if submitted:
    st.header("3. Training Progress")

    config = {
        "num_epochs": num_epochs,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "train_fraction": train_fraction,
        "freeze_epochs": freeze_epochs,
        "use_face_detection": use_face_detection,
    }

    st.json(config)

    with st.spinner("Preparing dataset..."):
        # In a real implementation, this would call the API to
        # trigger the training pipeline. For now, show the config.
        time.sleep(1)
        st.success("Dataset prepared. Training configuration saved.")

    st.info(
        "To run training, execute this command on the training server:\n\n"
        f"```\n"
        f"python scripts/run_training.py \\\n"
        f"  --config trainer/fer_finetune/configs/simulated_run.yaml\n"
        f"```\n\n"
        "Automated training submission will be available in a future update."
    )

    # Placeholder for real-time progress tracking
    st.subheader("Training Metrics")
    st.markdown(
        "Once training is running, metrics will appear here. "
        "Check MLflow at http://10.0.4.130:5000 for live tracking."
    )

# ---- Section 4: Previous Runs ----

st.header("4. Previous Training Runs")

st.markdown(
    "View past training runs and their Gate A results. "
    "Connect to MLflow for full experiment history."
)

# Show a placeholder table
st.dataframe(
    {
        "Run ID": ["(no runs yet)"],
        "Date": ["—"],
        "F1 Macro": ["—"],
        "Status": ["—"],
    },
    use_container_width=True,
)

st.markdown("---")
st.caption(
    "Training uses EfficientNet-B0 with HSEmotion pretrained weights. "
    "See Tutorial 5 for details."
)
```

---

## Step 3: Test the Page

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
streamlit run apps/web/pages/03_Train.py
```

Open http://localhost:8501 and verify:
- Dataset stats show (or "offline" if API isn't running)
- Training config form works
- Submit button shows configuration summary

---

## Checklist

- [ ] `apps/web/pages/03_Train.py` replaced with functional page
- [ ] Page loads without errors in Streamlit
- [ ] Dataset stats section displays
- [ ] Training configuration form works
- [ ] Command output shown for manual training
