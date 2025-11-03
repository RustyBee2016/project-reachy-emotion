from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.append(PROJECT_ROOT_STR)

import apps.web.path_setup  # noqa: F401
from apps.web import api_client
from apps.web.components.video_player import render_video_or_thumb

st.set_page_config(page_title="Home", layout="wide", initial_sidebar_state="collapsed")

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
    .video-placeholder {
        background-color: #2b2b2b;
        height: 300px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #888;
    }
</style>
""",
    unsafe_allow_html=True,
)


def _ensure_state() -> None:
    defaults = {
        "current_video": None,
        "generation_active": False,
        "video_queue": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_current_video(payload: Dict[str, Any]) -> None:
    st.session_state.current_video = payload


def _upload_section() -> None:
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        uploaded_file = st.file_uploader(
            "Choose File",
            type=["mp4", "avi", "mov", "mkv", "mpeg4"],
            label_visibility="collapsed",
            key="home_file_uploader",
        )

    with col2:
        upload_for_training = st.checkbox("Upload for Training", value=False)

    with col3:
        if st.button("Upload Video", type="primary", disabled=uploaded_file is None):
            if uploaded_file is None:
                st.warning("Please select a file before uploading.")
            else:
                correlation_id = str(uuid.uuid4())
                try:
                    payload = api_client.upload_video(
                        file_name=uploaded_file.name,
                        file_bytes=uploaded_file.getvalue(),
                        upload_for_training=upload_for_training,
                        correlation_id=correlation_id,
                    )
                    video_id = (
                        payload.get("video_id")
                        or payload.get("clip")
                        or Path(uploaded_file.name).stem
                    )
                    file_path = payload.get("file_path") or f"videos/temp/{uploaded_file.name}"
                    _set_current_video(
                        {
                            "video_id": video_id,
                            "file_path": file_path,
                            "for_training": upload_for_training,
                            "correlation_id": correlation_id,
                            "metadata": payload,
                        }
                    )
                    st.success(f"✅ Video uploaded: {uploaded_file.name}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ Upload failed: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)


def _handle_generation(prompt: str) -> None:
    correlation_id = str(uuid.uuid4())
    try:
        resp = api_client.request_generation(
            prompt=prompt,
            correlation_id=correlation_id,
            params={"timestamp": datetime.utcnow().isoformat()},
        )
        st.session_state.generation_active = True
        st.session_state.video_queue.append(
            {
                "prompt": prompt,
                "status": resp.get("status", "queued"),
                "correlation_id": correlation_id,
                "response": resp,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        st.info(f"🎬 Generating video for prompt: '{prompt}'")
    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ Generation failed: {exc}")


def _generation_section() -> None:
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    col_left, col_right = st.columns([5, 2])

    with col_left:
        prompt = st.text_input(
            "Describe the video you want to CREATE:",
            placeholder="a happy girl eating lunch",
            key="home_video_prompt",
        )

    with col_right:
        if st.button("Generate Video", type="primary", disabled=not prompt):
            if not prompt:
                st.warning("Enter a prompt before requesting generation.")
            else:
                _handle_generation(prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.generation_active:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Generate similar videos", key="home_gen_similar"):
                if prompt:
                    _handle_generation(prompt)
                else:
                    st.info("Enter a prompt to generate similar videos.")
        with col_b:
            if st.button("⏹️ End Video Generation", key="home_end_generation"):
                st.session_state.generation_active = False
                st.success("Video generation session ended.")


def _resolve_video_sources() -> Dict[str, Optional[str]]:
    current = st.session_state.current_video or {}
    file_path = current.get("file_path")
    video_id = current.get("video_id")
    url = api_client.video_url(file_path) if file_path else None
    thumb = api_client.thumb_url(video_id) if video_id else None
    return {"video_url": url, "thumb_url": thumb}


def _reject_current_video(reason: Optional[str] = None) -> None:
    current = st.session_state.current_video
    if not current:
        return
    correlation_id = str(uuid.uuid4())
    video_id = current.get("video_id")
    try:
        api_client.reject_video(video_id=video_id, correlation_id=correlation_id, reason=reason)
        st.warning("Video marked as incorrect and deletion has been requested.")
        st.session_state.current_video = None
    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ Reject failed: {exc}")


def _promote_current_video(selected_emotion: str) -> None:
    current = st.session_state.current_video
    if not current:
        return
    correlation_id = str(uuid.uuid4())
    video_id = current.get("video_id")
    for_training = bool(current.get("for_training"))
    dest_split = "train" if for_training else "test"
    label = selected_emotion if for_training else None

    try:
        resp = api_client.promote(
            video_id=video_id,
            dest_split=dest_split,
            label=label,
            dry_run=False,
            correlation_id=correlation_id,
            use_gateway=True,
        )
        st.success(f"✅ Classified as **{selected_emotion}**; promoted to {dest_split}.")
        st.json(resp)
        st.session_state.current_video = None
    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ Promotion failed: {exc}")


def _classification_section() -> None:
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("### Watch & classify the video")

    col_video, col_controls = st.columns([3, 2])
    sources = _resolve_video_sources()

    with col_video:
        if sources["video_url"] or sources["thumb_url"]:
            render_video_or_thumb(
                url=sources["video_url"] or sources["thumb_url"],
                thumb_url=sources["thumb_url"],
            )
        else:
            st.markdown('<div class="video-placeholder">No video loaded</div>', unsafe_allow_html=True)

    with col_controls:
        current = st.session_state.current_video
        dest_label = "training" if current and current.get("for_training") else "test"
        st.markdown("**Enter the emotion type:**")
        emotions = ["neutral", "happy", "sad", "angry", "surprise", "fearful"]
        selected_emotion = st.selectbox(
            "Emotion",
            options=emotions,
            label_visibility="collapsed",
            key="home_emotion_select",
        )
        st.caption("(happy, sad, angry, surprised, neutral, fearful)")

        if st.button("❌ Incorrect", key="home_delete_video", use_container_width=True):
            if current:
                _reject_current_video(reason="incorrect")
            else:
                st.info("No video selected.")

        if st.button("✅ Submit Classification", type="primary", use_container_width=True):
            if current:
                _promote_current_video(selected_emotion)
            else:
                st.info("Upload or select a video before classifying.")
        st.caption(f"Will promote to **{dest_label}** once submitted.")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.video_queue:
        st.markdown("### 📋 Video Generation Queue")
        for idx, video in enumerate(st.session_state.video_queue[-5:]):
            with st.expander(f"Video {idx + 1}: {video['prompt'][:50]}"):
                st.json(video)


def _footer() -> None:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    media_caption = api_client.video_storage_caption("temp")
    with col1:
        st.caption(f"🖥️ API Base: {_base_label()}")
    with col2:
        st.caption(f"🖥️ Gateway: {_gateway_label()}")
    with col3:
        st.caption(f"📁 Video Storage: {media_caption}")


def _base_label() -> str:
    base = api_client._base_url()  # type: ignore[attr-defined]
    return base


def _gateway_label() -> str:
    return api_client._gateway_base()  # type: ignore[attr-defined]


# Page content
_ensure_state()
st.markdown('<h1 class="main-header">Welcome to Capstone Video App</h1>', unsafe_allow_html=True)
_upload_section()
_generation_section()
_classification_section()
_footer()
