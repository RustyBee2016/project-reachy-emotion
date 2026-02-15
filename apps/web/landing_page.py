from __future__ import annotations

"""
Reachy Emotion Recognition - Landing Page (Streamlit)
Ubuntu 2 - Web UI for video generation, upload, and emotion labeling
"""

import streamlit as st
from streamlit.errors import StreamlitAPIException

# Page configuration must be the first Streamlit command (guarded for reruns)
try:
    st.set_page_config(
        page_title="Capstone Video App",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
except StreamlitAPIException:
    # Streamlit may auto-run another page first; ignore duplicate configuration
    pass

import uuid
from pathlib import Path
from datetime import datetime
import os
from typing import Optional
from dotenv import load_dotenv
from luma_client import LumaVideoGenerator, send_to_n8n_ingest
from api_client import (
    promote as promote_via_gateway,
    reject_video,
    upload_video as ingest_video,
    list_videos as list_videos_api,
    stage_to_dataset_all,
    register_local_video,
)


# Helpers


def _extract_video_id(payload: dict | None) -> Optional[str]:
    if not payload:
        return None
    candidates = ("video_id", "clip", "id")
    for key in candidates:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _extract_file_path(payload: dict | None) -> Optional[str]:
    if not payload:
        return None
    value = payload.get("file_path") or payload.get("path")
    if isinstance(value, str) and value:
        return value
    return None


def _refresh_video_metadata(current: dict) -> Optional[str]:
    """Attempt to resolve video_id/file_path from backend listings."""

    filename = None
    for key in ("backend_path", "path", "name"):
        candidate = current.get(key)
        if isinstance(candidate, str) and candidate:
            filename = Path(candidate).name
            break

    if not filename:
        return None

    try:
        listing = list_videos_api(split="temp", limit=200, offset=0)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Unable to query temp videos for metadata: {exc}")
        return None

    # Parse items from response
    for item in listing.get("items", []):
        file_path = item.get("file_path")
        if file_path and Path(file_path).name == filename:
            current["video_id"] = item.get("video_id")
            current["backend_path"] = file_path
            return current.get("video_id")

    return None


def _ensure_video_id(current: dict) -> Optional[str]:
    """Return cached video_id or attempt to refresh it."""

    video_id = current.get("video_id")
    if isinstance(video_id, str) and video_id:
        return video_id
    return _refresh_video_metadata(current)


def _is_uuid_identifier(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def _legacy_clip_identifier(current: dict, video_id: Optional[str]) -> Optional[str]:
    backend_path = current.get("backend_path")
    if isinstance(backend_path, str) and backend_path:
        return Path(backend_path).name

    name = current.get("name")
    if isinstance(name, str) and name:
        return Path(name).name

    if isinstance(video_id, str) and video_id:
        return video_id

    path = current.get("path")
    if isinstance(path, str) and path:
        return Path(path).name

    return None

# Load environment variables from the Streamlit app directory before access
WEB_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(WEB_ENV_PATH, override=False)

# Configuration - Load from environment variables
# These can be overridden by creating a .env file (see .env.template)
GATEWAY_URL = os.getenv("REACHY_GATEWAY_BASE", "http://10.0.4.140:8000")
MEDIA_MOVER_URL = os.getenv("REACHY_API_BASE", "http://10.0.4.130:8083")
# VIDEO_DATA_DIR previously pointed at the Ubuntu 1 local path:
# VIDEO_DATA_DIR = "/media/rusty_admin/project_data/reachy_emotion/videos/temp"
# Switch Streamlit writes to the Ubuntu 2 NFS mount so gateway + UI share storage.
VIDEO_DATA_DIR = "/mnt/videos/temp"

# n8n Configuration
N8N_HOST = os.getenv("N8N_HOST", "10.0.4.130")
N8N_PORT = os.getenv("N8N_PORT", "5678")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "webhook/video_gen_hook")
N8N_WEBHOOK_URL = f"http://{N8N_HOST}:{N8N_PORT}/{N8N_WEBHOOK_PATH}"
N8N_INGEST_TOKEN = os.getenv("N8N_INGEST_TOKEN", "")

# Luma AI Configuration
LUMAAI_API_KEY = os.getenv("LUMAAI_API_KEY", "")

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
if "luma_client" not in st.session_state:
    try:
        if LUMAAI_API_KEY:
            st.session_state.luma_client = LumaVideoGenerator(api_key=LUMAAI_API_KEY)
        else:
            st.session_state.luma_client = None
    except Exception as e:
        st.session_state.luma_client = None
        st.warning(f"⚠️ Luma AI not configured: {str(e)}")

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
                file_bytes = uploaded_file.getvalue()

                temp_path = Path(f"/tmp/{uploaded_file.name}")
                with open(temp_path, "wb") as f:
                    f.write(file_bytes)

                ingest_payload = ingest_video(
                    file_name=uploaded_file.name,
                    file_bytes=file_bytes,
                    upload_for_training=upload_for_training,
                    correlation_id=correlation_id,
                )

                video_id = _extract_video_id(ingest_payload)
                backend_path = _extract_file_path(ingest_payload)

                st.session_state.current_video = {
                    "path": str(temp_path),
                    "name": uploaded_file.name,
                    "for_training": upload_for_training,
                    "correlation_id": correlation_id,
                    "video_id": video_id,
                    "backend_path": backend_path,
                }

                if not video_id:
                    st.warning(
                        "Video uploaded but backend did not return an identifier yet. "
                        "The app will attempt to resolve it automatically before promotion."
                    )

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
            correlation_id = str(uuid.uuid4())
            if not st.session_state.luma_client:
                st.error("❌ Luma AI client not configured. Check LUMAAI_API_KEY in .env")
            else:
                try:
                    st.session_state.generation_active = True
                    
                    # Add to queue immediately
                    st.session_state.video_queue.append(
                        {
                            "prompt": video_prompt,
                            "status": "generating",
                            "correlation_id": correlation_id,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    
                    st.info(f"🎬 Generating video with Luma AI: '{video_prompt}'")
                    
                    # Generate video using Luma AI
                    with st.spinner("Generating video... This may take 1-2 minutes"):
                        video_path, generation_meta = st.session_state.luma_client.generate_and_download(
                            prompt=video_prompt,
                            output_path=Path(VIDEO_DATA_DIR),
                            model="ray-2",
                            resolution="720p",
                            duration="5s",
                            aspect_ratio="3:4"
                        )
                    
                    st.success(f"✅ Video generated: {video_path.name}")
                    
                    # Send to n8n Ingest Agent
                    n8n_response: dict | None = None
                    if N8N_INGEST_TOKEN:
                        try:
                            with st.spinner("Sending to n8n Ingest Agent..."):
                                n8n_response = send_to_n8n_ingest(
                                    video_file_path=video_path,
                                    n8n_webhook_url=N8N_WEBHOOK_URL,
                                    ingest_token=N8N_INGEST_TOKEN,
                                    correlation_id=correlation_id
                                )
                            st.success(f"✅ Sent to n8n: {n8n_response}")
                        except Exception as e:
                            st.warning(f"⚠️ Failed to send to n8n: {str(e)}")
                    
                    # Update session state
                    video_id = None
                    backend_path = None
                    if isinstance(n8n_response, dict):
                        video_id = _extract_video_id(n8n_response)
                        backend_path = _extract_file_path(n8n_response)

                    st.session_state.current_video = {
                        "path": str(video_path),
                        "name": video_path.name,
                        "for_training": False,
                        "correlation_id": correlation_id,
                        "generation_id": generation_meta.get("id"),
                        "video_id": video_id,
                        "backend_path": backend_path,
                    }

                    if not video_id:
                        rel_path = f"temp/{video_path.name}"
                        try:
                            register_response = register_local_video(
                                file_path=rel_path,
                                correlation_id=correlation_id,
                                metadata={"generator": "luma", "prompt": video_prompt},
                                file_name=video_path.name,
                                idempotency_key=correlation_id,
                            )
                            video_id = _extract_video_id(register_response)
                            backend_path = _extract_file_path(register_response) or rel_path
                            st.session_state.current_video["video_id"] = video_id
                            st.session_state.current_video["backend_path"] = backend_path
                        except Exception as e:  # noqa: BLE001
                            st.warning(f"Unable to register local video: {e}")

                    if not video_id:
                        _refresh_video_metadata(st.session_state.current_video)  # best-effort lookup
                    
                    # Update queue status
                    for item in st.session_state.video_queue:
                        if item["correlation_id"] == correlation_id:
                            item["status"] = "completed"
                            item["video_path"] = str(video_path)
                            break
                    
                    st.rerun()
                    
                except Exception as e:  # noqa: BLE001
                    st.error(f"❌ Generation failed: {str(e)}")
                    # Update queue status
                    for item in st.session_state.video_queue:
                        if item["correlation_id"] == correlation_id:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            break

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
    emotion_options = ["neutral", "happy", "sad"]
    selected_emotion = st.selectbox(
        "Emotion",
        options=emotion_options,
        label_visibility="collapsed",
        key="emotion_select",
    )
    st.caption("(happy, sad, neutral)")

    if st.button("❌ Incorrect", key="delete_video", use_container_width=True):
        if st.session_state.current_video:
            try:
                current = st.session_state.current_video
                video_id = _ensure_video_id(current)
                if not video_id:
                    st.error("Unable to resolve video ID for removal. Please retry after refresh.")
                else:
                    correlation_id = str(uuid.uuid4())
                    reject_video(
                        video_id=video_id,
                        correlation_id=correlation_id,
                        reason="incorrect",
                    )
                    st.warning("Video marked as incorrect and removal requested")
                    st.session_state.current_video = None
                    st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Delete failed: {str(e)}")

    if st.button("✅ Submit Classification", type="primary", use_container_width=True):
        if st.session_state.current_video and selected_emotion:
            try:
                current = st.session_state.current_video
                video_id = _ensure_video_id(current)
                if not video_id:
                    st.error(
                        "Unable to resolve video ID for promotion. Please wait a moment or refresh before trying again."
                    )
                else:
                    correlation_id = str(uuid.uuid4())
                    stage_succeeded = False

                    if _is_uuid_identifier(video_id):
                        try:
                            response = stage_to_dataset_all(
                                video_ids=[video_id],
                                label=selected_emotion,
                                dry_run=False,
                                correlation_id=correlation_id,
                            )
                            stage_succeeded = True
                            st.success(f"✅ Classified as: **{selected_emotion}**")
                            st.info("Video staged to dataset_all with metadata saved to database")

                            promoted = response.get("promoted_ids", [])
                            skipped = response.get("skipped_ids", [])
                            failed = response.get("failed_ids", [])
                            if promoted:
                                st.caption(f"✅ Promoted: {len(promoted)} video(s)")
                            if skipped:
                                st.caption(f"⏭️ Skipped: {len(skipped)} video(s)")
                            if failed:
                                st.warning(f"⚠️ Failed: {len(failed)} video(s)")
                        except Exception as stage_exc:  # noqa: BLE001
                            st.warning(
                                f"Stage endpoint failed ({stage_exc}); falling back to legacy promote flow."
                            )

                    if not stage_succeeded:
                        clip_id = _legacy_clip_identifier(current, video_id)
                        if not clip_id:
                            st.error("Unable to resolve a clip identifier for legacy promotion.")
                        else:
                            promote_via_gateway(
                                video_id=clip_id,
                                dest_split="train",
                                label=selected_emotion,
                                dry_run=False,
                                correlation_id=correlation_id,
                                use_gateway=True,
                                idempotency_key=correlation_id,
                            )
                            st.success(f"✅ Classified as: **{selected_emotion}**")
                            st.info("Video promoted to train split via gateway compatibility path")

                    st.session_state.current_video = None
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
    st.caption(f"🖥️ Media API: {MEDIA_MOVER_URL}")
with col_footer2:
    st.caption(f"🖥️ Gateway: {GATEWAY_URL}")
with col_footer3:
    st.caption(f"📁 Video Storage: {VIDEO_DATA_DIR}")
