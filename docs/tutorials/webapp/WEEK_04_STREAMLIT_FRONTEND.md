# Week 4: Streamlit Frontend Development

**Duration**: ~6 hours  
**Goal**: Build and extend Streamlit pages with proper state management  
**Prerequisites**: Weeks 1-3 completed, Streamlit basics

---

## Day 1: Streamlit Fundamentals (2 hours)

### 1.1 Understanding Streamlit Architecture

Streamlit re-runs the entire script on every interaction. This creates challenges:

```
User clicks button
       ↓
Entire script re-executes
       ↓
All variables reset to defaults
       ↓
UI re-renders

Solution: Session State persists data across reruns
```

### 1.2 Session State Basics

Open `apps/web/session_manager.py` and understand the pattern:

```python
# Session state initialization pattern
if "variable_name" not in st.session_state:
    st.session_state.variable_name = default_value

# Better pattern with defaults dict
defaults = {
    "current_video": None,
    "selected_videos": [],
    "filter_split": "temp",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
```

### 1.3 Page Structure Pattern

Every page should follow this structure:

```python
# apps/web/pages/XX_PageName.py

from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import after path setup
import apps.web.path_setup  # noqa: F401
from apps.web import api_client

# Page configuration (MUST be first Streamlit call)
st.set_page_config(page_title="Page Name", layout="wide")

# Title
st.title("XX — Page Name")

# Initialize session state
def _init_state():
    defaults = {"key": "value"}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Page content
def main():
    st.write("Page content here")

if __name__ == "__main__":
    main()
```

### 1.4 Exercise: Analyze Existing Pages

Compare `00_Home.py` (complete) with `03_Train.py` (placeholder):

```python
# 00_Home.py - Well structured
# - Proper imports and path setup
# - Session state initialization
# - Modular functions (_upload_section, _generation_section, etc.)
# - Error handling with try/except
# - API client usage

# 03_Train.py - Placeholder (needs implementation)
# - Basic structure only
# - Single button with API call
# - No real functionality
```

### Checkpoint 4.1
- [ ] Understand Streamlit re-run behavior
- [ ] Know how to use session state
- [ ] Can identify complete vs. placeholder pages

---

## Day 2: Building the Generate Page (2 hours)

### 2.1 Current State Analysis

Open `apps/web/pages/01_Generate.py`:

```python
# Current minimal implementation
st.set_page_config(page_title="Generate", layout="wide")
st.title("01 — Generate")
st.info("Prototype inputs for video generation...")
```

### 2.2 Implement Full Generate Page

Replace `apps/web/pages/01_Generate.py`:

```python
# apps/web/pages/01_Generate.py
"""Video Generation Page - Interface for creating synthetic training videos."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import apps.web.path_setup  # noqa: F401
from apps.web import api_client

st.set_page_config(page_title="Generate Videos", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .gen-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
    }
    .emotion-chip {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
    .happy { background-color: #d4edda; color: #155724; }
    .sad { background-color: #cce5ff; color: #004085; }
    .neutral { background-color: #e2e3e5; color: #383d41; }
</style>
""", unsafe_allow_html=True)


def _init_state():
    """Initialize session state variables."""
    defaults = {
        "gen_queue": [],
        "gen_history": [],
        "selected_emotion": "happy",
        "prompt_template": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _prompt_templates() -> dict:
    """Return emotion-specific prompt templates."""
    return {
        "happy": [
            "a happy person smiling at the camera",
            "a joyful person laughing",
            "a person expressing happiness while {activity}",
        ],
        "sad": [
            "a sad person looking down",
            "a person with a melancholy expression",
            "a person expressing sadness while {activity}",
        ],
        "angry": [
            "an angry person with furrowed brows",
            "a person expressing frustration",
            "a person showing anger while {activity}",
        ],
        "neutral": [
            "a person with a neutral expression",
            "a person looking calmly at the camera",
            "a person with no particular emotion while {activity}",
        ],
    }


def _render_prompt_builder():
    """Render the prompt building section."""
    st.subheader("🎬 Prompt Builder")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        emotion = st.selectbox(
            "Target Emotion",
            options=["happy", "sad", "neutral"],
            key="selected_emotion_select",
        )
        st.session_state.selected_emotion = emotion
        
        templates = _prompt_templates()[emotion]
        template_choice = st.selectbox(
            "Template",
            options=["Custom"] + templates,
            key="template_select",
        )
    
    with col2:
        if template_choice == "Custom":
            prompt = st.text_area(
                "Video Description",
                placeholder=f"Describe a {emotion} scene...",
                height=100,
                key="custom_prompt",
            )
        else:
            # Allow customization of template
            activity = st.text_input(
                "Activity (optional)",
                placeholder="e.g., eating, reading, walking",
                key="activity_input",
            )
            if activity and "{activity}" in template_choice:
                prompt = template_choice.format(activity=activity)
            else:
                prompt = template_choice.replace(" while {activity}", "")
            
            st.info(f"**Generated prompt:** {prompt}")
    
    return prompt, emotion


def _render_generation_settings():
    """Render video generation settings."""
    st.subheader("⚙️ Generation Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        duration = st.selectbox(
            "Duration",
            options=["3s", "5s", "10s"],
            index=1,
            key="duration_select",
        )
    
    with col2:
        resolution = st.selectbox(
            "Resolution",
            options=["480p", "720p", "1080p"],
            index=1,
            key="resolution_select",
        )
    
    with col3:
        aspect_ratio = st.selectbox(
            "Aspect Ratio",
            options=["16:9", "4:3", "3:4", "1:1"],
            index=2,  # 3:4 for portrait
            key="aspect_select",
        )
    
    return {
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    }


def _submit_generation(prompt: str, emotion: str, settings: dict):
    """Submit video generation request."""
    correlation_id = str(uuid.uuid4())
    
    try:
        response = api_client.request_generation(
            prompt=prompt,
            correlation_id=correlation_id,
            params={
                "emotion": emotion,
                "duration": settings["duration"],
                "resolution": settings["resolution"],
                "aspect_ratio": settings["aspect_ratio"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        # Add to queue
        st.session_state.gen_queue.append({
            "id": correlation_id,
            "prompt": prompt,
            "emotion": emotion,
            "status": response.get("status", "queued"),
            "submitted_at": datetime.now().isoformat(),
            "response": response,
        })
        
        st.success(f"✅ Generation queued: {correlation_id[:8]}...")
        return True
        
    except Exception as e:
        st.error(f"❌ Generation failed: {e}")
        return False


def _render_generation_queue():
    """Render the generation queue."""
    st.subheader("📋 Generation Queue")
    
    if not st.session_state.gen_queue:
        st.info("No pending generations. Submit a prompt above to get started.")
        return
    
    for idx, item in enumerate(st.session_state.gen_queue):
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{item['prompt'][:50]}...**")
                st.caption(f"ID: {item['id'][:8]} | Emotion: {item['emotion']}")
            
            with col2:
                status = item.get("status", "unknown")
                if status == "completed":
                    st.success("✓ Done")
                elif status == "failed":
                    st.error("✗ Failed")
                else:
                    st.warning("⏳ Pending")
            
            with col3:
                if st.button("Remove", key=f"remove_{item['id']}"):
                    st.session_state.gen_queue.pop(idx)
                    st.rerun()


def _render_batch_generation():
    """Render batch generation controls."""
    st.subheader("🔄 Batch Generation")
    
    st.caption("Generate multiple videos for dataset balancing.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        batch_emotion = st.selectbox(
            "Emotion",
            options=["happy", "sad", "neutral"],
            key="batch_emotion",
        )
    
    with col2:
        batch_count = st.number_input(
            "Count",
            min_value=1,
            max_value=10,
            value=5,
            key="batch_count",
        )
    
    with col3:
        if st.button("Generate Batch", type="primary"):
            templates = _prompt_templates()[batch_emotion]
            st.info(f"Would generate {batch_count} {batch_emotion} videos")
            # TODO: Implement batch generation
            st.warning("Batch generation not yet implemented")


def main():
    """Main page function."""
    _init_state()
    
    st.title("01 — Generate Videos")
    st.caption("Create synthetic training videos using AI video generation.")
    
    # API Status
    try:
        api_client.media_api_base()
        st.sidebar.success("✓ API Connected")
    except Exception:
        st.sidebar.error("✗ API Disconnected")
    
    # Main content
    prompt, emotion = _render_prompt_builder()
    
    st.divider()
    
    settings = _render_generation_settings()
    
    # Submit button
    col1, col2 = st.columns([3, 1])
    with col2:
        submit_disabled = not prompt or len(prompt) < 10
        if st.button(
            "🚀 Generate Video",
            type="primary",
            disabled=submit_disabled,
            use_container_width=True,
        ):
            _submit_generation(prompt, emotion, settings)
    
    st.divider()
    
    _render_generation_queue()
    
    st.divider()
    
    _render_batch_generation()


if __name__ == "__main__":
    main()
```

### 2.3 Test the Page

```bash
streamlit run apps/web/main_app.py
# Navigate to Generate page
```

### Checkpoint 4.2
- [ ] Implemented full Generate page
- [ ] Uses session state for queue management
- [ ] Has prompt builder with templates
- [ ] Integrates with API client

---

## Day 3: Implementing Batch Operations (2 hours)

### 3.1 Complete Video Management TODO Items

Open `apps/web/pages/05_Video_Management.py` and implement the missing functions:

```python
# Add these implementations to 05_Video_Management.py

def perform_batch_labeling(label: str):
    """Apply label to selected videos."""
    api_client = SessionManager.get_api_client()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(st.session_state.selected_videos)
    successful = 0
    failed = 0
    
    for i, video_id in enumerate(st.session_state.selected_videos):
        try:
            status_text.text(f"Labeling {i+1}/{total}: {video_id[:8]}...")
            
            # Call relabel API endpoint
            result = api_client.relabel_video(
                video_id=video_id,
                label=label,
            )
            
            if result.get('status') == 'success':
                successful += 1
            else:
                failed += 1
        
        except Exception as e:
            st.error(f"Error labeling {video_id[:8]}...: {e}")
            failed += 1
        
        progress_bar.progress((i + 1) / total)
    
    status_text.empty()
    progress_bar.empty()
    
    st.success(f"Labeling completed: {successful} successful, {failed} failed")
    SessionManager.add_notification(
        f"Batch labeling: {successful} videos labeled as '{label}'",
        "success" if failed == 0 else "warning"
    )


def perform_batch_delete():
    """Delete selected videos with confirmation."""
    st.warning(f"⚠️ This will permanently delete {len(st.session_state.selected_videos)} videos!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        confirm_text = st.text_input(
            "Type 'DELETE' to confirm",
            key="delete_confirm",
        )
    
    with col2:
        if st.button("🗑️ Confirm Delete", type="primary"):
            if confirm_text != "DELETE":
                st.error("Please type 'DELETE' to confirm")
                return
            
            api_client = SessionManager.get_api_client()
            
            progress_bar = st.progress(0)
            total = len(st.session_state.selected_videos)
            deleted = 0
            
            for i, video_id in enumerate(st.session_state.selected_videos):
                try:
                    api_client.delete_video(video_id)
                    deleted += 1
                except Exception as e:
                    st.error(f"Failed to delete {video_id[:8]}: {e}")
                
                progress_bar.progress((i + 1) / total)
            
            progress_bar.empty()
            st.success(f"Deleted {deleted}/{total} videos")
            st.session_state.selected_videos = []
            st.rerun()
```

### 3.2 Add Missing API Client Methods

Add to `apps/web/api_client.py`:

```python
# Add these methods to api_client.py

@retry_on_failure()
def relabel_video(video_id: str, label: str) -> Dict[str, Any]:
    """Update the label of a video.
    
    Args:
        video_id: Video ID to relabel
        label: New emotion label
        
    Returns:
        Response with update status
    """
    url = f"{_base_url()}/api/v1/media/{video_id}/label"
    payload = {"label": label}
    resp = requests.put(url, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


@retry_on_failure()
def delete_video(video_id: str) -> Dict[str, Any]:
    """Delete a video from the system.
    
    Args:
        video_id: Video ID to delete
        
    Returns:
        Response with deletion status
    """
    url = f"{_base_url()}/api/v1/media/{video_id}"
    resp = requests.delete(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_dataset_stats() -> Dict[str, Any]:
    """Get statistics about the dataset splits.
    
    Returns:
        Dictionary with counts per split and label
    """
    url = f"{_base_url()}/api/v1/media/stats"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
```

### 3.3 Create Reusable Components

Create `apps/web/components/dataset_stats.py`:

```python
# apps/web/components/dataset_stats.py
"""Dataset statistics component."""

import streamlit as st
from typing import Dict, Any


def render_dataset_stats(stats: Dict[str, Any]):
    """Render dataset statistics in a grid layout.
    
    Args:
        stats: Dictionary with split counts and label distributions
    """
    st.subheader("📊 Dataset Statistics")
    
    # Split counts
    col1, col2, col3, col4 = st.columns(4)
    
    splits = stats.get("splits", {})
    
    with col1:
        st.metric("Temp", splits.get("temp", 0))
    with col2:
        st.metric("Train", splits.get("train", 0))
    with col3:
        st.metric("Test", splits.get("test", 0))
    with col4:
        st.metric("Total", splits.get("total", 0))
    
    # Label distribution
    st.caption("Label Distribution (Train Split)")
    
    labels = stats.get("labels", {})
    if labels:
        import pandas as pd
        df = pd.DataFrame([
            {"Label": k, "Count": v}
            for k, v in labels.items()
        ])
        st.bar_chart(df.set_index("Label"))
    
    # Balance indicator
    if "happy" in labels and "sad" in labels and "neutral" in labels:
        happy = labels["happy"]
        sad = labels["sad"]
        neutral = labels["neutral"]
        total = happy + sad + neutral
        
        if total > 0:
            classes = [happy, sad, neutral]
            valid_classes = [c for c in classes if c > 0]
            balance = (min(valid_classes) / max(valid_classes)) if valid_classes else 0
            
            if balance >= 0.8:
                st.success(f"✓ Dataset balanced ({balance:.0%})")
            elif balance >= 0.5:
                st.warning(f"⚠ Dataset imbalanced ({balance:.0%})")
            else:
                st.error(f"✗ Dataset severely imbalanced ({balance:.0%})")


def render_mini_stats():
    """Render compact stats for sidebar."""
    from apps.web import api_client
    
    try:
        stats = api_client.get_dataset_stats()
        splits = stats.get("splits", {})
        
        st.sidebar.metric("Videos (temp)", splits.get("temp", 0))
        st.sidebar.metric("Videos (train)", splits.get("train", 0))
        
    except Exception:
        st.sidebar.warning("Stats unavailable")
```

### Checkpoint 4.3
- [ ] Implemented batch labeling function
- [ ] Implemented batch delete with confirmation
- [ ] Added relabel and delete API client methods
- [ ] Created dataset stats component

---

## UI/UX Best Practices

### Layout Guidelines

```python
# Use columns for side-by-side content
col1, col2 = st.columns([2, 1])  # 2:1 ratio

# Use containers for grouping
with st.container(border=True):
    st.write("Grouped content")

# Use expanders for optional content
with st.expander("Advanced Options"):
    st.write("Hidden by default")

# Use tabs for related views
tab1, tab2 = st.tabs(["View 1", "View 2"])
```

### Feedback Patterns

```python
# Loading states
with st.spinner("Loading..."):
    data = api_client.fetch_data()

# Progress bars
progress = st.progress(0)
for i in range(100):
    progress.progress(i + 1)

# Status messages
st.success("✓ Operation completed")
st.warning("⚠ Warning message")
st.error("✗ Error occurred")
st.info("ℹ Information")

# Toast notifications (Streamlit 1.28+)
st.toast("Quick notification")
```

### Form Handling

```python
# Use forms to batch inputs
with st.form("my_form"):
    name = st.text_input("Name")
    age = st.number_input("Age")
    submitted = st.form_submit_button("Submit")
    
    if submitted:
        st.write(f"Hello {name}, age {age}")
```

---

## Week 4 Deliverables Checklist

- [ ] Understand Streamlit session state
- [ ] Implemented full Generate page (`01_Generate.py`)
- [ ] Implemented batch labeling in Video Management
- [ ] Implemented batch delete with confirmation
- [ ] Added API client methods (relabel, delete, stats)
- [ ] Created reusable dataset stats component

---

## Next Steps

Proceed to [Week 5: Training Dashboard Implementation](WEEK_05_TRAINING_DASHBOARD.md) to:
- Build the complete Training page
- Display training metrics and progress
- Integrate with MLflow for experiment tracking
- Add real-time training status updates
