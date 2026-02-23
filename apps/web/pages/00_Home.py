from __future__ import annotations

import sys
import uuid
from collections import Counter
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


def _normalize_emotion_label(raw_label: object, file_path: object) -> Optional[str]:
    if isinstance(raw_label, str):
        normalized = raw_label.strip().lower()
        if normalized in {"happy", "sad", "neutral"}:
            return normalized

    if isinstance(file_path, str):
        parts = Path(file_path).parts
        if len(parts) >= 2 and parts[0] == "train" and parts[1] in {"happy", "sad", "neutral"}:
            return parts[1]
        name = Path(file_path).name.lower()
        for label in ("happy", "sad", "neutral"):
            if name.startswith(f"{label}_"):
                return label

    return None


def _render_train_balance_counters() -> None:
    counts = Counter({"happy": 0, "sad": 0, "neutral": 0})
    try:
        listing = api_client.list_videos(split="train", limit=5000, offset=0)
        for item in listing.get("items", []):
            label = _normalize_emotion_label(item.get("label"), item.get("file_path"))
            if label in counts:
                counts[label] += 1
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Unable to load train label counters: {exc}")
        return

    min_count = min(counts.values()) if counts else 0
    underrepresented = sorted([label for label, value in counts.items() if value == min_count])
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Happy", counts["happy"])
    col_b.metric("Sad", counts["sad"])
    col_c.metric("Neutral", counts["neutral"])
    col_d.metric("Total Labeled", counts["happy"] + counts["sad"] + counts["neutral"])
    if underrepresented:
        st.caption(f"Underrepresented class(es): {', '.join(underrepresented)}")


def _refresh_video_metadata(current: Dict[str, Any]) -> Optional[str]:
    """Resolve a missing video_id by matching current file name against temp listing."""
    file_path = current.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return None

    filename = Path(file_path).name
    try:
        listing = api_client.list_videos(split="temp", limit=200, offset=0)
    except Exception:
        return None

    for item in listing.get("items", []):
        candidate_path = item.get("file_path")
        if isinstance(candidate_path, str) and Path(candidate_path).name == filename:
            candidate_id = item.get("video_id")
            if isinstance(candidate_id, str) and candidate_id:
                current["video_id"] = candidate_id
                current["file_path"] = candidate_path
                return candidate_id
    return None


def _ensure_video_id(current: Dict[str, Any]) -> Optional[str]:
    video_id = current.get("video_id")
    if isinstance(video_id, str) and video_id:
        return video_id
    return _refresh_video_metadata(current)


def _upload_section() -> None:
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 2])
    upload_for_training = True

    with col1:
        uploaded_file = st.file_uploader(
            "Choose File",
            type=["mp4", "avi", "mov", "mkv", "mpeg4"],
            label_visibility="collapsed",
            key="home_file_uploader",
        )

    with col2:
        st.caption("Classification flow targets train split.")

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
                    video_id = payload.get("video_id") or payload.get("clip")
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
    video_id = _ensure_video_id(current)
    if not video_id:
        st.error("Unable to resolve video ID for reject.")
        return
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
    video_id = _ensure_video_id(current)
    if not video_id:
        st.error("Unable to resolve video ID for promotion.")
        return
    dest_split = "train"
    label = selected_emotion

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
        dest_label = "training"
        st.markdown("**Enter the emotion type:**")
        emotions = ["neutral", "happy", "sad"]
        selected_emotion = st.selectbox(
            "Emotion",
            options=emotions,
            label_visibility="collapsed",
            key="home_emotion_select",
        )
        st.caption("(happy, sad, neutral)")

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
_render_train_balance_counters()
_upload_section()
_generation_section()
_classification_section()
_footer()
