"""Reachy Emotion Recognition - Landing Page (Streamlit)

Ubuntu 2 - Web UI for video generation, upload, and emotion labeling
Version: 0.09.1
Updated: 2026-01-31
"""

import streamlit as st
import requests
import uuid
import os
from pathlib import Path
from datetime import datetime
import json
from typing import Optional, Dict, Any, Tuple

# =============================================================================
# Configuration (environment variables with sensible defaults)
# =============================================================================
# Per requirements.md: Ubuntu 1 = 10.0.4.130 (storage/ML), Ubuntu 2 = 10.0.4.140 (gateway/UI)
UBUNTU1_HOST = os.getenv("UBUNTU1_HOST", "10.0.4.130")
UBUNTU2_HOST = os.getenv("UBUNTU2_HOST", "10.0.4.140")

# Gateway API on Ubuntu 2 (this machine)
GATEWAY_URL = os.getenv("GATEWAY_URL", f"http://{UBUNTU2_HOST}:8000")

# Media Mover API on Ubuntu 1 (direct access, port 8083 per requirements)
MEDIA_MOVER_URL = os.getenv("MEDIA_MOVER_URL", f"http://{UBUNTU1_HOST}:8083")
MEDIA_BASE = f"{MEDIA_MOVER_URL}/api"

# Nginx-served static content on Ubuntu 1
THUMBS_BASE = f"http://{UBUNTU1_HOST}/thumbs"
VIDEO_DATA_DIR = f"http://{UBUNTU1_HOST}/videos/data_all"

# API timeouts (seconds)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", "30"))

# =============================================================================
# API Helper Functions
# =============================================================================

def get_api_headers(correlation_id: str, idempotency_key: Optional[str] = None) -> Dict[str, str]:
    """Build standard API headers with version and correlation tracking."""
    headers = {
        "X-API-Version": "v1",
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def upload_video_to_server(file_bytes: bytes, filename: str, correlation_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Upload video file to Media Mover ingest endpoint.
    
    Returns:
        Tuple of (success, message, response_data)
    """
    try:
        # Use multipart form upload to Media Mover
        files = {
            "file": (filename, file_bytes, "video/mp4")
        }
        data = {
            "correlation_id": correlation_id,
        }
        
        response = requests.post(
            f"{MEDIA_BASE}/ingest",
            files=files,
            data=data,
            headers={"X-API-Version": "v1", "X-Correlation-ID": correlation_id},
            timeout=UPLOAD_TIMEOUT,
        )
        
        if response.status_code in (200, 201, 202):
            return True, "Upload successful", response.json()
        else:
            error_msg = response.json().get("message", response.text) if response.text else f"HTTP {response.status_code}"
            return False, f"Upload failed: {error_msg}", None
            
    except requests.exceptions.Timeout:
        return False, "Upload timed out - file may be too large", None
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to Media Mover at {MEDIA_MOVER_URL}", None
    except Exception as e:
        return False, f"Upload error: {str(e)}", None


def promote_video(
    clip_name: str,
    target: str,
    label: Optional[str],
    correlation_id: str,
) -> Tuple[bool, str, Optional[Dict]]:
    """Promote video from temp to train/test split via Gateway API.
    
    Per AGENTS.md: test split must have label=NULL.
    
    Returns:
        Tuple of (success, message, response_data)
    """
    # Enforce label policy: test split must have no label
    if target == "test":
        label = None
    
    idempotency_key = str(uuid.uuid4())
    
    payload = {
        "schema_version": "v1",
        "clip": clip_name,
        "target": target,
        "label": label,
        "correlation_id": correlation_id,
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/promote",
            json=payload,
            headers=get_api_headers(correlation_id, idempotency_key),
            timeout=API_TIMEOUT,
        )
        
        if response.status_code in (200, 202):
            return True, "Video promoted successfully", response.json()
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", str(error_data))
            except:
                error_msg = response.text or f"HTTP {response.status_code}"
            return False, f"Promotion failed: {error_msg}", None
            
    except requests.exceptions.Timeout:
        return False, "Gateway request timed out", None
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to Gateway at {GATEWAY_URL}", None
    except Exception as e:
        return False, f"Promotion error: {str(e)}", None


def delete_video(clip_name: str, correlation_id: str) -> Tuple[bool, str]:
    """Mark video as rejected/delete from temp split.
    
    Returns:
        Tuple of (success, message)
    """
    idempotency_key = str(uuid.uuid4())
    
    payload = {
        "schema_version": "v1",
        "clip": clip_name,
        "action": "reject",
        "correlation_id": correlation_id,
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/videos/reject",
            json=payload,
            headers=get_api_headers(correlation_id, idempotency_key),
            timeout=API_TIMEOUT,
        )
        
        if response.status_code in (200, 202, 204):
            return True, "Video rejected successfully"
        elif response.status_code == 404:
            # Endpoint may not exist yet - fall back to just clearing local state
            return True, "Video removed from queue (API endpoint pending)"
        else:
            try:
                error_msg = response.json().get("message", response.text)
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Delete failed: {error_msg}"
            
    except requests.exceptions.ConnectionError:
        # Gateway offline - still allow local state clearing
        return True, "Video removed locally (Gateway offline)"
    except Exception as e:
        return False, f"Delete error: {str(e)}"


def check_service_health() -> Dict[str, bool]:
    """Check health of backend services."""
    status = {"gateway": False, "media_mover": False}
    
    try:
        r = requests.get(f"{GATEWAY_URL}/health", timeout=2)
        status["gateway"] = r.status_code == 200
    except:
        pass
    
    try:
        r = requests.get(f"{MEDIA_MOVER_URL}/health", timeout=2)
        status["media_mover"] = r.status_code == 200
    except:
        pass
    
    return status


def thumb_url_from_path(file_path: str) -> str:
    """Convert a DB-style relative file_path (e.g., 'videos/train/clip_00123.mp4')
    into a no-split thumbnail URL 'http://<host>/thumbs/clip_00123.jpg'.
    """
    stem = Path(file_path).stem if "/" in file_path else Path(str(file_path)).stem
    return f"{THUMBS_BASE}/{stem}.jpg"


def fetch_videos(split: str, limit: int = 12, offset: int = 0):
    try:
        r = requests.get(
            f"{MEDIA_BASE}/videos/list",
            params={"split": split, "limit": limit, "offset": offset},
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("videos", [])
    except Exception as e:
        st.warning(f"Could not fetch videos for split '{split}': {e}")
        return []

# Page configuration
st.set_page_config(
    page_title="Capstone Video App",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, minimalistic design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 2rem;
        color: #1f1f1f;
    }
    .section-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .video-container {
        border-radius: 10px;
        overflow: hidden;
        margin: 1rem 0;
    }
    .emotion-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_video' not in st.session_state:
    st.session_state.current_video = None
if 'generation_active' not in st.session_state:
    st.session_state.generation_active = False
if 'video_queue' not in st.session_state:
    st.session_state.video_queue = []

# Header
st.markdown('<h1 class="main-header">Welcome to Capstone Video App</h1>', unsafe_allow_html=True)

# Section 1: Upload Existing Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    # Element 1: File uploader
    uploaded_file = st.file_uploader(
        "Choose File",
        type=['mp4', 'avi', 'mov', 'mkv'],
        label_visibility="collapsed",
        key="file_uploader"
    )

with col2:
    # Element 2: Upload for training checkbox
    upload_for_training = st.checkbox("Upload for Training", value=False)

with col3:
    # Element 3: Upload Video button
    if st.button("Upload Video", type="primary", disabled=uploaded_file is None):
        if uploaded_file:
            correlation_id = str(uuid.uuid4())
            
            with st.spinner("Uploading video to server..."):
                # Upload to Media Mover API
                success, message, response_data = upload_video_to_server(
                    file_bytes=uploaded_file.getbuffer(),
                    filename=uploaded_file.name,
                    correlation_id=correlation_id,
                )
            
            if success:
                # Store video info in session state
                st.session_state.current_video = {
                    'path': response_data.get('path', f"videos/temp/{uploaded_file.name}") if response_data else f"videos/temp/{uploaded_file.name}",
                    'name': uploaded_file.name,
                    'for_training': upload_for_training,
                    'correlation_id': correlation_id,
                    'video_id': response_data.get('video_id') if response_data else None,
                }
                st.success(f"✅ Video uploaded: {uploaded_file.name}")
                if response_data:
                    st.caption(f"Video ID: {response_data.get('video_id', 'N/A')}")
            else:
                st.error(f"❌ {message}")

st.markdown('</div>', unsafe_allow_html=True)

# Section 2: Generate Synthetic Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
col4, col5 = st.columns([5, 2])

with col4:
    # Element 4: Text input for video generation
    video_prompt = st.text_input(
        "Describe the video you want to CREATE:",
        placeholder="a happy girl eating lunch",
        label_visibility="visible",
        key="video_prompt"
    )

with col5:
    # Element 5: Generate Video button
    if st.button("Generate Video", type="primary", disabled=not video_prompt):
        if video_prompt:
            try:
                st.session_state.generation_active = True
                correlation_id = str(uuid.uuid4())
                
                # TODO: Call video generation API (Luma/Runway/etc.)
                st.info(f"🎬 Generating video: '{video_prompt}'")
                
                # Simulate video generation (replace with actual API call)
                st.session_state.video_queue.append({
                    'prompt': video_prompt,
                    'status': 'generating',
                    'correlation_id': correlation_id,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                st.error(f"❌ Generation failed: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# Section 3: Generation Controls
if st.session_state.generation_active:
    col6, col7 = st.columns(2)
    
    with col6:
        # Element 6: Generate similar videos
        if st.button("🔄 Generate similar videos", key="gen_similar"):
            if video_prompt:
                st.info(f"Generating variations of: '{video_prompt}'")
                # TODO: Call API with variation parameters
    
    with col7:
        # Element 7: End video generation
        if st.button("⏹️ End Video Generation", key="end_gen"):
            st.session_state.generation_active = False
            st.success("Video generation session ended")
            st.rerun()

# Section 4: Watch & Classify Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
st.markdown("### Watch & classify the video")

col8, col9 = st.columns([3, 2])

with col8:
    # Video player
    if st.session_state.current_video:
        video_path = st.session_state.current_video['path']
        st.video(video_path)
        # Placeholder: show how thumb URL will be built for DB items (no effect for local temp file).
        st.caption("Thumb URL format (no split): ")
        st.code(thumb_url_from_path(f"videos/temp/{Path(video_path).name}"), language="text")
    else:
        # Placeholder when no video loaded
        st.markdown("""
        <div style="background-color: #2b2b2b; height: 300px; border-radius: 10px; 
                    display: flex; align-items: center; justify-content: center; color: #888;">
            <p style="font-size: 1.2rem;">No video loaded</p>
        </div>
        """, unsafe_allow_html=True)

with col9:
    # Element 8: Emotion type input
    st.markdown("**Enter the emotion type:**")
    emotion_options = ["neutral", "happy", "sad"]
    
    selected_emotion = st.selectbox(
        "Emotion",
        options=emotion_options,
        label_visibility="collapsed",
        key="emotion_select"
    )
    
    st.caption("(happy, sad, neutral)")
    
    # Element 10: Incorrect/Delete button
    if st.button("❌ Incorrect", key="delete_video", use_container_width=True):
        if st.session_state.current_video:
            correlation_id = str(uuid.uuid4())
            clip_name = st.session_state.current_video.get('name', '')
            
            with st.spinner("Rejecting video..."):
                success, message = delete_video(clip_name, correlation_id)
            
            if success:
                st.warning(f"Video marked as incorrect: {message}")
                st.session_state.current_video = None
                st.rerun()
            else:
                st.error(f"❌ {message}")
        else:
            st.warning("No video selected to reject")
    
    # Submit emotion classification
    if st.button("✅ Submit Classification", type="primary", use_container_width=True):
        if st.session_state.current_video and selected_emotion:
            correlation_id = str(uuid.uuid4())
            clip_name = st.session_state.current_video.get('name', '')
            target = "train" if st.session_state.current_video.get('for_training', False) else "test"
            
            # Per AGENTS.md: test split must have label=NULL
            # The promote_video function enforces this, but show user the policy
            if target == "test":
                st.info("ℹ️ Test split: label will not be stored (per data policy)")
            
            with st.spinner(f"Promoting video to {target} split..."):
                success, message, response_data = promote_video(
                    clip_name=clip_name,
                    target=target,
                    label=selected_emotion,
                    correlation_id=correlation_id,
                )
            
            if success:
                st.success(f"✅ Classified as: **{selected_emotion}**")
                st.info(f"Video promoted to {target} set")
                # Clear current video to allow next classification
                st.session_state.current_video = None
                st.rerun()
            else:
                st.error(f"❌ {message}")
        elif not st.session_state.current_video:
            st.warning("No video loaded - upload or select a video first")
        else:
            st.warning("Please select an emotion before submitting")

st.markdown('</div>', unsafe_allow_html=True)

# Section 5: Video Queue Status (if generation active)
if st.session_state.video_queue:
    st.markdown("### 📋 Video Generation Queue")
    for idx, video in enumerate(st.session_state.video_queue[-5:]):  # Show last 5
        with st.expander(f"Video {idx + 1}: {video['prompt'][:50]}..."):
            st.json(video)

# Section 6: Browse Media (lists + thumbnails)
st.markdown('<div class="section-container">', unsafe_allow_html=True)
st.markdown("### Browse Media")

tab_temp, tab_train, tab_test = st.tabs(["temp", "train", "test"])

def render_split(tab, split: str):
    with tab:
        items = fetch_videos(split=split, limit=12, offset=0)
        if not items:
            st.info(f"No items in '{split}' or service unavailable.")
            return
        cols = st.columns(4)
        for i, item in enumerate(items):
            col = cols[i % 4]
            with col:
                # Support either 'path' or 'file_path' from API response
                fp = item.get('path') or item.get('file_path') or ''
                stem = Path(fp).stem if fp else 'unknown'
                turl = f"{THUMBS_BASE}/{stem}.jpg"
                st.image(turl, caption=stem, use_container_width=True)
                st.caption(f"split={split}")

render_split(tab_temp, 'temp')
render_split(tab_train, 'train')
render_split(tab_test, 'test')

st.markdown('</div>', unsafe_allow_html=True)

# Footer with system info
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer1:
    st.caption(f"🖥️ Ubuntu 1: {UBUNTU1_HOST}")
with col_footer2:
    st.caption(f"🖥️ Ubuntu 2: {UBUNTU2_HOST}")
with col_footer3:
    st.caption(f"📁 Video Storage: {VIDEO_DATA_DIR}")
