# Week 6: Deployment Controls & Monitoring

**Duration**: ~6 hours  
**Goal**: Build deployment management UI for Jetson edge deployment  
**Prerequisites**: Weeks 1-5 completed, understanding of ML deployment

---

## Day 1: Understanding Deployment Pipeline (2 hours)

### 1.1 Deployment Architecture

The model deployment follows a staged rollout:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Deployment Pipeline                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐│
│   │  ONNX   │───▶│ TensorRT│───▶│ Shadow  │───▶│ Canary  │───▶│Rollout││
│   │ Export  │    │ Convert │    │  Test   │    │  10%    │    │ 100% ││
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘    └──────┘│
│       │                              │              │              │    │
│       │                              ▼              ▼              ▼    │
│       │                        ┌───────────────────────────────────────┐│
│       │                        │         Gate B Validation            ││
│       │                        │  FPS ≥ 25 | Latency p50 ≤ 120ms     ││
│       │                        │  GPU Memory ≤ 2.5GB | F1 ≥ 0.80     ││
│       │                        └───────────────────────────────────────┘│
│       │                                                                 │
│       ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    Jetson Xavier NX (10.0.4.150)                │  │
│   │  DeepStream Pipeline ──▶ TensorRT Engine ──▶ Emotion Output    │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Gate B Requirements

From `AGENTS.md`:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| FPS | ≥ 25 | Frames per second on Jetson |
| Latency p50 | ≤ 120 ms | 50th percentile inference time |
| Latency p95 | ≤ 250 ms | 95th percentile inference time |
| GPU Memory | ≤ 2.5 GB | Maximum GPU memory usage |
| Macro F1 | ≥ 0.80 | Maintained accuracy on edge |

### 1.3 Current State

Open `apps/web/pages/04_Deploy.py`:

```python
# Current stub (13 lines)
st.title("04 — Deploy")
st.info("This page will track deployment status...")
st.markdown("- Engine version: `unknown`\n- FPS: `unknown`...")
```

**What's needed:**
- Engine status display
- Deployment controls (shadow → canary → rollout)
- Gate B validation results
- Rollback functionality
- Live inference metrics

---

## Day 2: Implement Deployment Dashboard (2.5 hours)

### 2.1 Complete Deploy Page Implementation

Replace `apps/web/pages/04_Deploy.py`:

```python
# apps/web/pages/04_Deploy.py
"""Deployment Dashboard - Manage model deployment to Jetson edge device."""

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

st.set_page_config(page_title="Deployment Dashboard", layout="wide")

# Gate B thresholds
GATE_B_THRESHOLDS = {
    "fps": 25,
    "latency_p50_ms": 120,
    "latency_p95_ms": 250,
    "gpu_memory_gb": 2.5,
    "macro_f1": 0.80,
}

# Deployment stages
DEPLOYMENT_STAGES = ["shadow", "canary", "rollout"]


def _init_state():
    """Initialize session state."""
    defaults = {
        "deployment_status": None,
        "selected_engine": None,
        "auto_refresh": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _fetch_jetson_status() -> Dict[str, Any]:
    """Fetch Jetson device status."""
    try:
        # This would call Jetson API endpoint
        # Mock data for development
        return {
            "online": True,
            "hostname": "jetson-nx-01",
            "ip": "10.0.4.150",
            "gpu_utilization": 45,
            "gpu_memory_used_gb": 1.8,
            "gpu_memory_total_gb": 8.0,
            "cpu_utilization": 30,
            "temperature_c": 52,
            "uptime_hours": 168,
        }
    except Exception as e:
        return {"online": False, "error": str(e)}


def _fetch_engine_status() -> Dict[str, Any]:
    """Fetch current deployed engine status."""
    try:
        # This would call deployment API
        # Mock data for development
        return {
            "current_engine": "emotion_resnet50_v1.engine",
            "engine_version": "0.08.4.3",
            "deployment_stage": "rollout",
            "deployed_at": "2026-01-25T14:30:00Z",
            "model_source": "run-20260128-001",
            "gate_b_passed": True,
        }
    except Exception:
        return {"current_engine": None}


def _fetch_inference_metrics() -> Dict[str, Any]:
    """Fetch live inference metrics from Jetson."""
    try:
        # This would call metrics endpoint on Jetson
        # Mock data for development
        return {
            "fps": 28.5,
            "latency_p50_ms": 95,
            "latency_p95_ms": 180,
            "latency_p99_ms": 220,
            "requests_total": 125430,
            "errors_total": 12,
            "error_rate": 0.0001,
            "uptime_seconds": 604800,
        }
    except Exception:
        return {}


def _fetch_available_engines() -> List[Dict[str, Any]]:
    """Fetch list of available engines for deployment."""
    return [
        {
            "name": "emotion_resnet50_v1.engine",
            "version": "0.08.4.3",
            "created_at": "2026-01-28T12:00:00Z",
            "size_mb": 45.2,
            "gate_a_passed": True,
            "source_run": "run-20260128-001",
        },
        {
            "name": "emotion_resnet50_v0.engine",
            "version": "0.08.4.2",
            "created_at": "2026-01-20T10:00:00Z",
            "size_mb": 44.8,
            "gate_a_passed": True,
            "source_run": "run-20260120-001",
        },
    ]


def _render_jetson_status():
    """Render Jetson device status."""
    st.subheader("🖥️ Jetson Device Status")
    
    status = _fetch_jetson_status()
    
    if not status.get("online"):
        st.error(f"❌ Jetson Offline: {status.get('error', 'Connection failed')}")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Status",
            "🟢 Online" if status["online"] else "🔴 Offline",
        )
        st.caption(f"{status['hostname']} ({status['ip']})")
    
    with col2:
        gpu_pct = status["gpu_utilization"]
        st.metric("GPU Utilization", f"{gpu_pct}%")
        st.progress(gpu_pct / 100)
    
    with col3:
        mem_used = status["gpu_memory_used_gb"]
        mem_total = status["gpu_memory_total_gb"]
        st.metric("GPU Memory", f"{mem_used:.1f} / {mem_total:.1f} GB")
        st.progress(mem_used / mem_total)
    
    with col4:
        temp = status["temperature_c"]
        temp_status = "🟢" if temp < 60 else "🟡" if temp < 75 else "🔴"
        st.metric("Temperature", f"{temp_status} {temp}°C")
        st.caption(f"Uptime: {status['uptime_hours']}h")


def _render_engine_status():
    """Render current deployed engine status."""
    st.subheader("⚙️ Deployed Engine")
    
    status = _fetch_engine_status()
    
    if not status.get("current_engine"):
        st.warning("No engine currently deployed")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Engine:** `{status['current_engine']}`")
        st.markdown(f"**Version:** {status['engine_version']}")
        st.markdown(f"**Source:** {status['model_source']}")
    
    with col2:
        stage = status["deployment_stage"]
        stage_colors = {"shadow": "🟡", "canary": "🟠", "rollout": "🟢"}
        st.markdown(f"**Stage:** {stage_colors.get(stage, '⚪')} {stage.title()}")
        st.markdown(f"**Deployed:** {status['deployed_at']}")
    
    with col3:
        if status.get("gate_b_passed"):
            st.success("✓ Gate B Passed")
        else:
            st.error("✗ Gate B Failed")


def _check_gate_b(metrics: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Check metrics against Gate B thresholds."""
    checks = {}
    
    # FPS
    fps = metrics.get("fps", 0)
    checks["FPS"] = {
        "value": fps,
        "threshold": f"≥ {GATE_B_THRESHOLDS['fps']}",
        "passed": fps >= GATE_B_THRESHOLDS["fps"],
    }
    
    # Latency p50
    lat_p50 = metrics.get("latency_p50_ms", 999)
    checks["Latency p50"] = {
        "value": f"{lat_p50} ms",
        "threshold": f"≤ {GATE_B_THRESHOLDS['latency_p50_ms']} ms",
        "passed": lat_p50 <= GATE_B_THRESHOLDS["latency_p50_ms"],
    }
    
    # Latency p95
    lat_p95 = metrics.get("latency_p95_ms", 999)
    checks["Latency p95"] = {
        "value": f"{lat_p95} ms",
        "threshold": f"≤ {GATE_B_THRESHOLDS['latency_p95_ms']} ms",
        "passed": lat_p95 <= GATE_B_THRESHOLDS["latency_p95_ms"],
    }
    
    return checks


def _render_gate_b_validation():
    """Render Gate B validation results."""
    st.subheader("🚦 Gate B Validation")
    
    metrics = _fetch_inference_metrics()
    
    if not metrics:
        st.warning("Metrics not available")
        return
    
    checks = _check_gate_b(metrics)
    all_passed = all(c["passed"] for c in checks.values())
    
    if all_passed:
        st.success("✓ All Gate B requirements met!")
    else:
        st.error("✗ Some Gate B requirements not met")
    
    # Display as columns
    cols = st.columns(len(checks))
    for i, (name, check) in enumerate(checks.items()):
        with cols[i]:
            icon = "✓" if check["passed"] else "✗"
            color = "green" if check["passed"] else "red"
            st.markdown(f"**{name}**")
            st.markdown(f":{color}[{icon} {check['value']}]")
            st.caption(check["threshold"])


def _render_inference_metrics():
    """Render live inference metrics."""
    st.subheader("📊 Inference Metrics")
    
    metrics = _fetch_inference_metrics()
    
    if not metrics:
        st.info("No metrics available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("FPS", f"{metrics.get('fps', 0):.1f}")
    
    with col2:
        st.metric("Latency p50", f"{metrics.get('latency_p50_ms', 0)} ms")
    
    with col3:
        st.metric("Total Requests", f"{metrics.get('requests_total', 0):,}")
    
    with col4:
        error_rate = metrics.get("error_rate", 0) * 100
        st.metric("Error Rate", f"{error_rate:.2f}%")


def _render_deployment_controls():
    """Render deployment control buttons."""
    st.subheader("🎮 Deployment Controls")
    
    engines = _fetch_available_engines()
    current_status = _fetch_engine_status()
    current_stage = current_status.get("deployment_stage", "none")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Engine selection
        engine_names = [e["name"] for e in engines]
        selected_engine = st.selectbox(
            "Select Engine",
            options=engine_names,
            key="deploy_engine_select",
        )
        
        # Show engine details
        engine_info = next((e for e in engines if e["name"] == selected_engine), None)
        if engine_info:
            st.caption(
                f"Version: {engine_info['version']} | "
                f"Size: {engine_info['size_mb']} MB | "
                f"Created: {engine_info['created_at'][:10]}"
            )
    
    with col2:
        st.write("")  # Spacer
        st.write("")
        
        # Stage progression buttons
        if current_stage == "none" or current_stage == "rollout":
            if st.button("🚀 Deploy to Shadow", use_container_width=True):
                st.info(f"Deploying {selected_engine} to shadow...")
                # TODO: Call deployment API
                st.warning("Deployment API not implemented")
        
        elif current_stage == "shadow":
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("⏩ Promote to Canary", use_container_width=True):
                    st.info("Promoting to canary (10% traffic)...")
            with col_b:
                if st.button("⏪ Rollback", use_container_width=True):
                    st.warning("Rolling back from shadow...")
        
        elif current_stage == "canary":
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("⏩ Promote to Rollout", use_container_width=True):
                    st.info("Promoting to full rollout...")
            with col_b:
                if st.button("⏪ Rollback", use_container_width=True):
                    st.warning("Rolling back from canary...")
    
    # Deployment stage indicator
    st.markdown("---")
    st.markdown("**Deployment Pipeline:**")
    
    stages_display = []
    for stage in DEPLOYMENT_STAGES:
        if stage == current_stage:
            stages_display.append(f"**[{stage.upper()}]**")
        elif DEPLOYMENT_STAGES.index(stage) < DEPLOYMENT_STAGES.index(current_stage) if current_stage in DEPLOYMENT_STAGES else False:
            stages_display.append(f"~~{stage}~~")
        else:
            stages_display.append(stage)
    
    st.markdown(" → ".join(stages_display))


def _render_rollback_section():
    """Render rollback controls."""
    st.subheader("🔄 Rollback")
    
    with st.expander("Emergency Rollback", expanded=False):
        st.warning("⚠️ This will immediately roll back to the previous stable engine.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            previous_engines = _fetch_available_engines()[1:]  # Skip current
            if previous_engines:
                rollback_target = st.selectbox(
                    "Rollback to",
                    options=[e["name"] for e in previous_engines],
                    key="rollback_target",
                )
            else:
                st.info("No previous engines available")
                rollback_target = None
        
        with col2:
            if rollback_target:
                if st.button("🔴 Execute Rollback", type="primary"):
                    st.error(f"Rolling back to {rollback_target}...")
                    # TODO: Call rollback API


def main():
    """Main page function."""
    _init_state()
    
    st.title("04 — Deployment Dashboard")
    st.caption("Manage TensorRT engine deployment to Jetson and monitor inference performance.")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.sidebar.info("Auto-refresh enabled")
        # Would use st.rerun() with timer
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    
    # Main content
    _render_jetson_status()
    
    st.divider()
    
    _render_engine_status()
    
    st.divider()
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        _render_gate_b_validation()
    
    with col_right:
        _render_inference_metrics()
    
    st.divider()
    
    _render_deployment_controls()
    
    st.divider()
    
    _render_rollback_section()


if __name__ == "__main__":
    main()
```

### Checkpoint 6.1
- [ ] Implemented complete Deploy Dashboard
- [ ] Displays Jetson device status
- [ ] Shows Gate B validation checks
- [ ] Has deployment stage controls
- [ ] Includes rollback functionality

---

## Day 3: Adding Real-Time Monitoring (1.5 hours)

### 3.1 WebSocket Integration for Live Metrics

Update deployment page to use WebSocket client:

```python
# Add to 04_Deploy.py

from apps.web.websocket_client import WebSocketClient, EventType

def _connect_metrics_stream():
    """Connect to Jetson metrics WebSocket stream."""
    if "metrics_ws" not in st.session_state:
        gateway_url = os.getenv("REACHY_GATEWAY_BASE", "http://10.0.4.140:8000")
        st.session_state.metrics_ws = WebSocketClient(
            server_url=gateway_url,
            device_id="deploy-ui",
        )
    
    return st.session_state.metrics_ws


def _render_live_metrics_chart():
    """Render real-time metrics chart."""
    st.subheader("📈 Live Metrics (Last 5 minutes)")
    
    # This would use data from WebSocket
    # For now, show placeholder
    import pandas as pd
    import numpy as np
    
    # Mock time series data
    timestamps = pd.date_range(end=datetime.now(), periods=60, freq="5S")
    fps_data = np.random.normal(28, 2, 60)
    latency_data = np.random.normal(95, 15, 60)
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "FPS": fps_data,
        "Latency (ms)": latency_data,
    })
    
    tab1, tab2 = st.tabs(["FPS", "Latency"])
    
    with tab1:
        st.line_chart(df.set_index("timestamp")["FPS"])
    
    with tab2:
        st.line_chart(df.set_index("timestamp")["Latency (ms)"])
```

### 3.2 Add Deployment API Client Methods

Add to `apps/web/api_client.py`:

```python
# Add these methods to api_client.py

def get_jetson_status() -> Dict[str, Any]:
    """Get Jetson device status."""
    url = f"{_gateway_base()}/api/jetson/status"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_deployment_status() -> Dict[str, Any]:
    """Get current deployment status."""
    url = f"{_gateway_base()}/api/deployment/status"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def deploy_engine(
    engine_name: str,
    target_stage: str = "shadow",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Deploy an engine to Jetson."""
    url = f"{_gateway_base()}/api/deployment/deploy"
    payload = {
        "engine_name": engine_name,
        "target_stage": target_stage,
        "dry_run": dry_run,
    }
    resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def promote_deployment(target_stage: str) -> Dict[str, Any]:
    """Promote current deployment to next stage."""
    url = f"{_gateway_base()}/api/deployment/promote"
    payload = {"target_stage": target_stage}
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def rollback_deployment(target_engine: Optional[str] = None) -> Dict[str, Any]:
    """Rollback to previous or specified engine."""
    url = f"{_gateway_base()}/api/deployment/rollback"
    payload = {}
    if target_engine:
        payload["target_engine"] = target_engine
    resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()
```

### Checkpoint 6.2
- [ ] Added live metrics visualization
- [ ] Added deployment API client methods
- [ ] WebSocket integration for real-time updates

---

## Week 6 Deliverables Checklist

- [ ] Complete Deploy Dashboard implementation
- [ ] Jetson device status display
- [ ] Gate B validation visualization
- [ ] Deployment stage controls (shadow → canary → rollout)
- [ ] Rollback functionality with confirmation
- [ ] Inference metrics display
- [ ] API client methods for deployment operations

---

## Next Steps

Proceed to [Week 7: Testing & Quality Assurance](WEEK_07_TESTING_QA.md) to:
- Write comprehensive unit tests
- Create integration tests
- Achieve 80%+ code coverage
- Set up CI/CD testing pipeline
