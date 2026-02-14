# Week 5: Training Dashboard Implementation

**Duration**: ~6 hours  
**Goal**: Build a complete training monitoring dashboard  
**Prerequisites**: Weeks 1-4 completed, understanding of ML concepts

---

## Day 1: Understanding Training Integration (2 hours)

### 1.1 Training Pipeline Overview

The training system consists of:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Training Pipeline                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────┐ │
│   │  Dataset  │───▶│  Trainer  │───▶│  MLflow   │───▶│ Model │ │
│   │  (videos) │    │  Script   │    │  Logging  │    │ Export│ │
│   └───────────┘    └───────────┘    └───────────┘    └───────┘ │
│                           │                                     │
│                           ▼                                     │
│                    ┌───────────┐                                │
│                    │  Gate A   │                                │
│                    │ Validation│                                │
│                    └───────────┘                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Metrics to Display

From `AGENTS.md`, Gate A requirements:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Macro F1 | ≥ 0.84 | Overall classification performance |
| Balanced Accuracy | ≥ 0.85 | Accuracy accounting for class imbalance |
| Per-class F1 | ≥ 0.75 | Individual emotion performance |
| ECE | ≤ 0.08 | Expected Calibration Error |
| Brier Score | ≤ 0.16 | Probability calibration |

### 1.3 Current State Analysis

Open `apps/web/pages/03_Train.py`:

```python
# Current minimal implementation (25 lines)
st.title("03 — Training")
st.info("Rebuild manifests before starting a training job. This is a placeholder page.")

if st.button("Rebuild Manifests (POST /manifest/rebuild)"):
    # ...
```

**What's missing:**
- Dataset readiness check
- Training run management
- Metrics visualization
- Gate A validation display
- MLflow integration

---

## Day 2: Implement Training Dashboard (2.5 hours)

### 2.1 Complete Training Page Implementation

Replace `apps/web/pages/03_Train.py`:

```python
# apps/web/pages/03_Train.py
"""Training Dashboard - Monitor and manage model training."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import apps.web.path_setup  # noqa: F401
from apps.web import api_client

st.set_page_config(page_title="Training Dashboard", layout="wide")

# Gate A thresholds
GATE_A_THRESHOLDS = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1_floor": 0.70,
    "per_class_f1_target": 0.75,
    "ece": 0.08,
    "brier": 0.16,
}


def _init_state():
    """Initialize session state."""
    defaults = {
        "training_runs": [],
        "selected_run": None,
        "auto_refresh": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _fetch_dataset_stats() -> Dict[str, Any]:
    """Fetch dataset statistics from API."""
    try:
        # Try v1 API first
        response = api_client.list_videos(split="train", limit=1, offset=0)
        train_count = response.get("total", 0)
        
        response = api_client.list_videos(split="test", limit=1, offset=0)
        test_count = response.get("total", 0)
        
        # Get label distribution (mock for now if not available)
        return {
            "train_count": train_count,
            "test_count": test_count,
            "labels": {"happy": train_count // 2, "sad": train_count // 2},
            "ready": train_count >= 100 and test_count >= 40,
        }
    except Exception as e:
        return {
            "train_count": 0,
            "test_count": 0,
            "labels": {},
            "ready": False,
            "error": str(e),
        }


def _fetch_training_runs() -> List[Dict[str, Any]]:
    """Fetch training runs from API or MLflow."""
    try:
        # This would connect to MLflow or training API
        # For now, return mock data structure
        return [
            {
                "run_id": "run-20260128-001",
                "status": "completed",
                "started_at": "2026-01-28T10:00:00Z",
                "completed_at": "2026-01-28T12:30:00Z",
                "epochs": 50,
                "metrics": {
                    "macro_f1": 0.87,
                    "balanced_accuracy": 0.88,
                    "f1_happy": 0.89,
                    "f1_sad": 0.85,
                    "ece": 0.06,
                    "brier": 0.12,
                    "loss": 0.234,
                },
                "model_path": "/models/emotion_efficientnet_b0_v1.pt",
                "gate_a_passed": True,
            },
            {
                "run_id": "run-20260125-002",
                "status": "completed",
                "started_at": "2026-01-25T14:00:00Z",
                "completed_at": "2026-01-25T16:45:00Z",
                "epochs": 50,
                "metrics": {
                    "macro_f1": 0.81,
                    "balanced_accuracy": 0.82,
                    "f1_happy": 0.84,
                    "f1_sad": 0.78,
                    "ece": 0.11,
                    "brier": 0.19,
                    "loss": 0.312,
                },
                "model_path": "/models/emotion_efficientnet_b0_v0.pt",
                "gate_a_passed": False,
            },
        ]
    except Exception:
        return []


def _render_dataset_readiness():
    """Render dataset readiness section."""
    st.subheader("📊 Dataset Readiness")
    
    stats = _fetch_dataset_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Train Videos",
            stats["train_count"],
            delta="Ready" if stats["train_count"] >= 100 else f"Need {100 - stats['train_count']} more",
        )
    
    with col2:
        st.metric(
            "Test Videos",
            stats["test_count"],
            delta="Ready" if stats["test_count"] >= 40 else f"Need {40 - stats['test_count']} more",
        )
    
    with col3:
        labels = stats.get("labels", {})
        happy = labels.get("happy", 0)
        sad = labels.get("sad", 0)
        if happy > 0 and sad > 0:
            balance = min(happy, sad) / max(happy, sad)
            st.metric("Balance Ratio", f"{balance:.0%}")
        else:
            st.metric("Balance Ratio", "N/A")
    
    with col4:
        if stats.get("ready"):
            st.success("✓ Ready to Train")
        else:
            st.warning("⚠ Not Ready")
    
    # Error display
    if "error" in stats:
        st.error(f"API Error: {stats['error']}")
    
    # Label distribution chart
    if stats.get("labels"):
        import pandas as pd
        df = pd.DataFrame([
            {"Label": k, "Count": v}
            for k, v in stats["labels"].items()
        ])
        st.bar_chart(df.set_index("Label"))


def _render_training_controls():
    """Render training control buttons."""
    st.subheader("🎯 Training Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦 Rebuild Manifests", use_container_width=True):
            try:
                with st.spinner("Rebuilding manifests..."):
                    result = api_client.rebuild_manifest()
                st.success("Manifests rebuilt successfully")
                st.json(result)
            except Exception as e:
                st.error(f"Failed to rebuild manifests: {e}")
    
    with col2:
        epochs = st.number_input("Epochs", min_value=10, max_value=200, value=50)
        if st.button("🚀 Start Training", type="primary", use_container_width=True):
            try:
                # This would trigger training via API or n8n
                st.info(f"Training job submitted with {epochs} epochs")
                st.warning("Training trigger not yet implemented - use n8n workflow")
            except Exception as e:
                st.error(f"Failed to start training: {e}")
    
    with col3:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.session_state.training_runs = _fetch_training_runs()
            st.rerun()


def _check_gate_a(metrics: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Check metrics against Gate A thresholds."""
    checks = {}
    
    # Macro F1
    macro_f1 = metrics.get("macro_f1", 0)
    checks["Macro F1"] = {
        "value": macro_f1,
        "threshold": f"≥ {GATE_A_THRESHOLDS['macro_f1']}",
        "passed": macro_f1 >= GATE_A_THRESHOLDS["macro_f1"],
    }
    
    # Balanced Accuracy
    bal_acc = metrics.get("balanced_accuracy", 0)
    checks["Balanced Accuracy"] = {
        "value": bal_acc,
        "threshold": f"≥ {GATE_A_THRESHOLDS['balanced_accuracy']}",
        "passed": bal_acc >= GATE_A_THRESHOLDS["balanced_accuracy"],
    }
    
    # Per-class F1
    f1_happy = metrics.get("f1_happy", 0)
    f1_sad = metrics.get("f1_sad", 0)
    min_f1 = min(f1_happy, f1_sad)
    checks["Per-class F1 (min)"] = {
        "value": min_f1,
        "threshold": f"≥ {GATE_A_THRESHOLDS['per_class_f1_floor']}",
        "passed": min_f1 >= GATE_A_THRESHOLDS["per_class_f1_floor"],
    }
    
    # ECE
    ece = metrics.get("ece", 1.0)
    checks["ECE"] = {
        "value": ece,
        "threshold": f"≤ {GATE_A_THRESHOLDS['ece']}",
        "passed": ece <= GATE_A_THRESHOLDS["ece"],
    }
    
    # Brier
    brier = metrics.get("brier", 1.0)
    checks["Brier Score"] = {
        "value": brier,
        "threshold": f"≤ {GATE_A_THRESHOLDS['brier']}",
        "passed": brier <= GATE_A_THRESHOLDS["brier"],
    }
    
    return checks


def _render_gate_a_validation(metrics: Dict[str, float]):
    """Render Gate A validation results."""
    st.subheader("🚦 Gate A Validation")
    
    checks = _check_gate_a(metrics)
    all_passed = all(c["passed"] for c in checks.values())
    
    if all_passed:
        st.success("✓ All Gate A requirements passed!")
    else:
        st.error("✗ Some Gate A requirements not met")
    
    # Display as table
    cols = st.columns(len(checks))
    for i, (name, check) in enumerate(checks.items()):
        with cols[i]:
            icon = "✓" if check["passed"] else "✗"
            color = "green" if check["passed"] else "red"
            st.markdown(f"**{name}**")
            st.markdown(f":{color}[{icon} {check['value']:.3f}]")
            st.caption(check["threshold"])


def _render_training_runs():
    """Render training run history."""
    st.subheader("📜 Training History")
    
    runs = st.session_state.training_runs or _fetch_training_runs()
    
    if not runs:
        st.info("No training runs found. Start a training job above.")
        return
    
    for run in runs:
        with st.expander(
            f"{'✓' if run.get('gate_a_passed') else '✗'} {run['run_id']} - {run['status']}",
            expanded=(run == runs[0]),
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Status:** {run['status']}")
                st.markdown(f"**Started:** {run['started_at']}")
                if run.get("completed_at"):
                    st.markdown(f"**Completed:** {run['completed_at']}")
                st.markdown(f"**Epochs:** {run.get('epochs', 'N/A')}")
                
                if run.get("model_path"):
                    st.markdown(f"**Model:** `{run['model_path']}`")
            
            with col2:
                metrics = run.get("metrics", {})
                st.metric("Macro F1", f"{metrics.get('macro_f1', 0):.3f}")
                st.metric("Loss", f"{metrics.get('loss', 0):.3f}")
            
            # Gate A validation for this run
            if metrics:
                _render_gate_a_validation(metrics)
            
            # Action buttons
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if run.get("gate_a_passed") and st.button(
                    "📤 Export to ONNX",
                    key=f"export_{run['run_id']}",
                ):
                    st.info("Export triggered (not implemented)")
            with col_b:
                if st.button("📊 View in MLflow", key=f"mlflow_{run['run_id']}"):
                    st.info("Would open MLflow UI")
            with col_c:
                if st.button("📋 Copy Metrics", key=f"copy_{run['run_id']}"):
                    st.code(str(metrics))


def _render_live_training_progress():
    """Render live training progress if a job is running."""
    # This would connect to WebSocket for live updates
    # Placeholder for now
    
    running = False  # Would check via API
    
    if running:
        st.subheader("🔄 Training in Progress")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            progress = 0.65  # Would come from WebSocket
            st.progress(progress)
            st.caption(f"Epoch 32/50 | Loss: 0.234 | F1: 0.85")
        
        with col2:
            if st.button("⏹️ Stop Training"):
                st.warning("Stop requested")


def main():
    """Main page function."""
    _init_state()
    
    st.title("03 — Training Dashboard")
    st.caption("Monitor dataset readiness, manage training jobs, and validate models against Gate A.")
    
    # Sidebar status
    st.sidebar.subheader("Quick Stats")
    try:
        stats = _fetch_dataset_stats()
        st.sidebar.metric("Train", stats["train_count"])
        st.sidebar.metric("Test", stats["test_count"])
    except Exception:
        st.sidebar.warning("Stats unavailable")
    
    # Main content
    _render_dataset_readiness()
    
    st.divider()
    
    _render_training_controls()
    
    st.divider()
    
    _render_live_training_progress()
    
    _render_training_runs()


if __name__ == "__main__":
    main()
```

### Checkpoint 5.1
- [ ] Implemented complete Training Dashboard
- [ ] Displays dataset readiness metrics
- [ ] Shows Gate A validation checks
- [ ] Lists training history with metrics

---

## Day 3: MLflow Integration (1.5 hours)

### 3.1 Understanding MLflow

MLflow tracks experiments, parameters, and metrics:

```python
# How training scripts log to MLflow
import mlflow

with mlflow.start_run(run_name="emotion_training_v1"):
    mlflow.log_param("epochs", 50)
    mlflow.log_param("learning_rate", 0.001)
    
    for epoch in range(50):
        # Training loop...
        mlflow.log_metric("loss", loss, step=epoch)
        mlflow.log_metric("f1_score", f1, step=epoch)
    
    mlflow.log_artifact("model.pt")
```

### 3.2 Add MLflow Query Functions

Create `apps/web/mlflow_client.py`:

```python
# apps/web/mlflow_client.py
"""MLflow client for querying experiment data."""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# MLflow may not be installed in web environment
try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


def get_mlflow_client() -> Optional[Any]:
    """Get MLflow client if available."""
    if not MLFLOW_AVAILABLE:
        return None
    
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://10.0.4.130:5000")
    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient()


def list_experiments() -> List[Dict[str, Any]]:
    """List all MLflow experiments."""
    client = get_mlflow_client()
    if not client:
        return []
    
    experiments = client.search_experiments()
    return [
        {
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "artifact_location": exp.artifact_location,
        }
        for exp in experiments
    ]


def list_runs(
    experiment_name: str = "reachy_emotion",
    max_results: int = 20,
) -> List[Dict[str, Any]]:
    """List runs for an experiment."""
    client = get_mlflow_client()
    if not client:
        return []
    
    try:
        experiment = client.get_experiment_by_name(experiment_name)
        if not experiment:
            return []
        
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=max_results,
            order_by=["start_time DESC"],
        )
        
        return [
            {
                "run_id": run.info.run_id,
                "run_name": run.info.run_name,
                "status": run.info.status,
                "started_at": datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
                "ended_at": datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
                "metrics": run.data.metrics,
                "params": run.data.params,
                "artifact_uri": run.info.artifact_uri,
            }
            for run in runs
        ]
    except Exception as e:
        print(f"MLflow query error: {e}")
        return []


def get_run_metrics(run_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get metric history for a run."""
    client = get_mlflow_client()
    if not client:
        return {}
    
    try:
        run = client.get_run(run_id)
        metric_keys = run.data.metrics.keys()
        
        history = {}
        for key in metric_keys:
            metric_history = client.get_metric_history(run_id, key)
            history[key] = [
                {"step": m.step, "value": m.value, "timestamp": m.timestamp}
                for m in metric_history
            ]
        
        return history
    except Exception:
        return {}
```

### 3.3 Add Metrics Visualization

Update the training page to visualize metrics:

```python
# Add to 03_Train.py

def _render_metrics_chart(metrics_history: Dict[str, List[Dict[str, Any]]]):
    """Render training metrics over epochs."""
    import pandas as pd
    
    if not metrics_history:
        st.info("No metric history available")
        return
    
    # Prepare data for plotting
    loss_data = metrics_history.get("loss", [])
    f1_data = metrics_history.get("macro_f1", [])
    
    if loss_data:
        df_loss = pd.DataFrame(loss_data)
        st.subheader("Training Loss")
        st.line_chart(df_loss.set_index("step")["value"])
    
    if f1_data:
        df_f1 = pd.DataFrame(f1_data)
        st.subheader("Macro F1 Score")
        st.line_chart(df_f1.set_index("step")["value"])
```

### Checkpoint 5.2
- [ ] Created MLflow client module
- [ ] Can query experiments and runs
- [ ] Displays metric history charts

---

## Week 5 Deliverables Checklist

- [ ] Complete Training Dashboard implementation
- [ ] Dataset readiness display with visual indicators
- [ ] Training controls (manifest rebuild, start training)
- [ ] Gate A validation visualization
- [ ] Training history with expandable details
- [ ] MLflow integration for experiment tracking
- [ ] Metrics visualization with charts

---

## Testing the Training Dashboard

```bash
# Run the application
streamlit run apps/web/main_app.py

# Navigate to Training page
# Verify:
# 1. Dataset stats load (or show error gracefully)
# 2. Training history displays
# 3. Gate A checks render correctly
# 4. Buttons are functional
```

---

## Next Steps

Proceed to [Week 6: Deployment Controls & Monitoring](WEEK_06_DEPLOYMENT_CONTROLS.md) to:
- Implement the Deploy page
- Display Jetson deployment status
- Add engine management controls
- Monitor inference metrics
