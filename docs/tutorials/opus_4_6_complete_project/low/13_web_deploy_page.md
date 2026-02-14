# Tutorial 13: Web UI — Deploy Page

> **Priority**: LOW — Phase 3 preparation
> **Time estimate**: 4-6 hours
> **Difficulty**: Easy
> **Prerequisites**: Streamlit basics

---

## Why This Matters

The Deploy page is a 13-line stub with hardcoded "unknown" values.
While actual deployment is a Phase 3 concern, having a status display
page helps track model versions.

---

## Implementation

Replace `apps/web/pages/04_Deploy.py`:

```python
"""
Deployment Status Page — Monitor model versions on edge devices.

Shows:
- Current deployed model version
- Gate B status (latency, memory)
- Deployment history
- Rollback controls (Phase 3)
"""

import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Deploy", page_icon="🚀", layout="wide")

st.title("Deployment Status")

GATEWAY_URL = st.session_state.get("gateway_url", "http://10.0.4.140:8000")

# ---- Current Deployment ----

st.header("Current Deployment")

col1, col2, col3 = st.columns(3)

col1.metric("Model Version", "Not deployed", help="No model has been deployed yet")
col2.metric("Deployment Stage", "N/A", help="shadow → canary → rollout")
col3.metric("Gate B Status", "Pending", help="Latency and memory validation")

st.info(
    "Model deployment to Jetson Xavier NX is a Phase 3 feature. "
    "Complete Phase 1 training and Gate A validation first."
)

# ---- Gate B Thresholds ----

st.header("Gate B Requirements")

st.markdown(
    """
    | Metric | Threshold | Current |
    |--------|-----------|---------|
    | Latency p50 | ≤ 120 ms | Not measured |
    | Latency p95 | ≤ 250 ms | Not measured |
    | GPU Memory | ≤ 2.5 GB | Not measured |
    | Macro F1 | ≥ 0.80 | Not measured |

    These metrics are measured on the Jetson Xavier NX during
    shadow deployment (Phase 3).
    """
)

# ---- Deployment History ----

st.header("Deployment History")

st.dataframe(
    {
        "Date": ["(no deployments)"],
        "Model": ["—"],
        "Stage": ["—"],
        "Status": ["—"],
    },
    use_container_width=True,
)

st.markdown("---")
st.caption(
    "Deployment pipeline: Train → Gate A → Export TensorRT → "
    "Shadow → Gate B → Canary → Rollout"
)
```

---

## Checklist

- [ ] `apps/web/pages/04_Deploy.py` shows deployment status
- [ ] Gate B thresholds displayed
- [ ] Page loads without errors
