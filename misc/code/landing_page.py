"""
Reachy Emotion Recognition - Landing Page (Streamlit)
Ubuntu 2 - Web UI for video generation, upload, and emotion labeling
"""

import streamlit as st
import requests
import uuid
from pathlib import Path
from datetime import datetime
import json

# Configuration
UBUNTU2_HOST = "10.0.4.140"
UBUNTU1_HOST = "10.0.4.130"
GATEWAY_URL = f"http://{UBUNTU2_HOST}:8000"
MEDIA_MOVER_URL = f"http://{UBUNTU1_HOST}:8081"
VIDEO_DATA_DIR = f"http://{UBUNTU1_HOST}/videos/data_all"

# Page configuration
st.set_page_config(
    page_title="Capstone Video App",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, minimalistic design
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "current_video" not in st.session_state:
    st.session_state.current_video = None
if "generation_active" not in st.session_state:
    st.session_state.generation_active = False
if "video_queue" not in st.session_state:
    st.session_state.video_queue = []

# Header
st.markdown('<h1 class="main-header">Welcome to Capstone Video App</h1>', unsafe_allow_html=True)

# Section 1: Upload Existing Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    uploaded_file = st.file_uploader(
        "Choose File",
        type=["mp4", "avi", "mov", "mkv"],
        label_visibility="collapsed",
        key="file_uploader",
    )

with col2:
    upload_for_training = st.checkbox("Upload for Training", value=False)

with col3:
    if st.button("Upload Video", type="primary", disabled=uploaded_file is None):
        if uploaded_file:
            try:
                correlation_id = str(uuid.uuid4())
                temp_path = Path(f"/tmp/{uploaded_file.name}")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                # TODO: Send to media mover API
                st.session_state.current_video = {
                    "path": str(temp_path),
                    "name": uploaded_file.name,
                    "for_training": upload_for_training,
                    "correlation_id": correlation_id,
                }
                st.success(f"✅ Video uploaded: {uploaded_file.name}")
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Upload failed: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)

# Section 2: Generate Synthetic Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
col4, col5 = st.columns([5, 2])

with col4:
    video_prompt = st.text_input(
        "Describe the video you want to CREATE:",
        placeholder="a happy girl eating lunch",
        label_visibility="visible",
        key="video_prompt",
    )

with col5:
    if st.button("Generate Video", type="primary", disabled=not video_prompt):
        if video_prompt:
            try:
                st.session_state.generation_active = True
                correlation_id = str(uuid.uuid4())
                # TODO: Call video generation API (Luma/Runway/etc.)
                st.info(f"🎬 Generating video: '{video_prompt}'")
                st.session_state.video_queue.append(
                    {
                        "prompt": video_prompt,
                        "status": "generating",
                        "correlation_id": correlation_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Generation failed: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)

# Section 3: Generation Controls
if st.session_state.generation_active:
    col6, col7 = st.columns(2)
    with col6:
        if st.button("🔄 Generate similar videos", key="gen_similar"):
            if video_prompt:
                st.info(f"Generating variations of: '{video_prompt}'")
    with col7:
        if st.button("⏹️ End Video Generation", key="end_gen"):
            st.session_state.generation_active = False
            st.success("Video generation session ended")
            st.rerun()

# Section 4: Watch & Classify Video
st.markdown('<div class="section-container">', unsafe_allow_html=True)
st.markdown("### Watch & classify the video")

col8, col9 = st.columns([3, 2])

with col8:
    if st.session_state.current_video:
        video_path = st.session_state.current_video["path"]
        st.video(video_path)
    else:
        st.markdown(
            """
        <div style="background-color: #2b2b2b; height: 300px; border-radius: 10px; 
                    display: flex; align-items: center; justify-content: center; color: #888;">
            <p style="font-size: 1.2rem;">No video loaded</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

with col9:
    st.markdown("**Enter the emotion type:**")
    emotion_options = ["neutral", "happy", "sad", "angry", "surprise", "fearful"]
    selected_emotion = st.selectbox(
        "Emotion",
        options=emotion_options,
        label_visibility="collapsed",
        key="emotion_select",
    )
    st.caption("(happy, sad, angry, surprised, neutral)")

    if st.button("❌ Incorrect", key="delete_video", use_container_width=True):
        if st.session_state.current_video:
            try:
                correlation_id = str(uuid.uuid4())
                # TODO: Call API to delete/reject video
                st.warning("Video marked as incorrect and will be deleted")
                st.session_state.current_video = None
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Delete failed: {str(e)}")

    if st.button("✅ Submit Classification", type="primary", use_container_width=True):
        if st.session_state.current_video and selected_emotion:
            try:
                correlation_id = str(uuid.uuid4())
                promotion_payload = {
                    "schema_version": "v1",
                    "clip": st.session_state.current_video["name"],
                    "target": "train" if st.session_state.current_video["for_training"] else "test",
                    "label": selected_emotion,
                    "correlation_id": correlation_id,
                }
                # TODO: Send to gateway API
                st.success(f"✅ Classified as: **{selected_emotion}**")
                st.info(
                    f"Video promoted to {'training' if st.session_state.current_video['for_training'] else 'test'} set"
                )
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Classification failed: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)

# Section 5: Video Queue Status
if st.session_state.video_queue:
    st.markdown("### 📋 Video Generation Queue")
    for idx, video in enumerate(st.session_state.video_queue[-5:]):
        with st.expander(f"Video {idx + 1}: {video['prompt'][:50]}..."):
            st.json(video)

# Footer with system info
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer1:
    st.caption(f"🖥️ Ubuntu 1: {UBUNTU1_HOST}")
with col_footer2:
    st.caption(f"🖥️ Ubuntu 2: {UBUNTU2_HOST}")
with col_footer3:
    st.caption(f"📁 Video Storage: {VIDEO_DATA_DIR}")
