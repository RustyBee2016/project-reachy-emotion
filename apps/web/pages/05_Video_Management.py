from __future__ import annotations

import uuid
from datetime import datetime

import streamlit as st

from apps.web import api_client
from apps.web.components.video_player import render_video_or_thumb


def _is_uuid_identifier(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False

st.set_page_config(page_title="Video Management", layout="wide")
st.title("05 - Video Management")

if "batch_selected" not in st.session_state:
    st.session_state.batch_selected = []

split = st.selectbox("Split", ["temp", "train", "test"], index=0)
limit = st.slider("Limit", min_value=10, max_value=200, value=50, step=10)

try:
    response = api_client.list_videos(split=split, limit=limit, offset=0)
    items = response.get("items", []) if isinstance(response, dict) else []
except Exception as exc:  # noqa: BLE001
    items = []
    st.error(f"Failed to list videos: {exc}")

if not items:
    st.info("No videos found for selected split.")
else:
    for item in items:
        vid = str(item.get("video_id", "unknown"))
        path = str(item.get("file_path", ""))
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        with col1:
            selected = st.checkbox("Select", key=f"sel_{vid}", value=(vid in st.session_state.batch_selected))
            if selected and vid not in st.session_state.batch_selected:
                st.session_state.batch_selected.append(vid)
            if not selected and vid in st.session_state.batch_selected:
                st.session_state.batch_selected.remove(vid)
        with col2:
            st.write(vid)
            st.caption(path)
        with col3:
            render_video_or_thumb(api_client.video_url(path), api_client.thumb_url(vid), width=160)
        with col4:
            st.write(f"Label: {item.get('label') or '(none)'}")
            st.write(f"Size: {item.get('size_bytes', '?')}")

st.divider()
st.subheader("Batch Promote / Stage")
st.write(f"Selected videos: {len(st.session_state.batch_selected)}")

dest_split = st.selectbox("Destination", ["train", "test"], index=0)
label = None
if dest_split == "train":
    label = st.selectbox("Label", ["happy", "sad", "neutral"], index=0)
dry_run = st.toggle("Dry run", value=True)

if st.button("Execute Batch Promote", disabled=not st.session_state.batch_selected):
    ok = 0
    failed = 0
    skipped = 0
    for vid in list(st.session_state.batch_selected):
        try:
            correlation_id = str(uuid.uuid4())

            if split == "temp":
                if not _is_uuid_identifier(vid):
                    # Temp listings can expose filename stems; skip non-UUID to avoid false promotions.
                    skipped += 1
                    continue
                api_client.promote(
                    video_id=vid,
                    dest_split="train",
                    label=label or "neutral",
                    dry_run=dry_run,
                    correlation_id=correlation_id,
                    use_gateway=True,
                )
            else:
                if not _is_uuid_identifier(vid):
                    skipped += 1
                    continue
                api_client.promote(
                    video_id=vid,
                    dest_split=dest_split,
                    label=label,
                    dry_run=dry_run,
                    correlation_id=correlation_id,
                    use_gateway=True,
                )
            ok += 1
        except Exception:
            failed += 1
    st.success(
        f"Batch complete at {datetime.utcnow().isoformat()} | success={ok} failed={failed} skipped={skipped}"
    )
    if skipped:
        st.warning("Some items were skipped because they lacked UUID identifiers required by promotion APIs.")
    if not dry_run:
        st.session_state.batch_selected = []
