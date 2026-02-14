from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.append(PROJECT_ROOT_STR)

import apps.web.path_setup  # noqa: F401
from apps.web import api_client
from apps.web.components.video_player import render_video_or_thumb

st.set_page_config(page_title="Label & Promote", layout="wide")

st.title("02 — Label & Promote")

st.caption("Browse clips and promote with split/label policy enforcement.")

split = st.selectbox("Split", ["temp", "train", "test"], index=0)
execute_mode = st.toggle("Execute promotions (otherwise dry-run)", value=False)

result = None
err: Exception | None = None
try:
    result = api_client.list_videos(split=split, limit=50, offset=0)
except Exception as e:  # noqa: BLE001
    err = e

if err:
    st.error("Failed to fetch list_videos. Configure REACHY_API_BASE and ensure API is reachable.")
    st.exception(err)
else:
    items: list[dict[str, object]]
    if isinstance(result, list):
        items = [it for it in result if isinstance(it, dict)]
    elif isinstance(result, dict):
        raw_items = result.get("items", [])
        if isinstance(raw_items, list):
            items = [it for it in raw_items if isinstance(it, dict)]
        else:
            items = []
    else:
        items = []
    if not items:
        st.info("No items found for selected split.")
    else:
        for it in items:
            with st.container(border=True):
                cols = st.columns([3, 2, 2, 2, 3])
                raw_video_id = it.get("video_id") or it.get("id") or it.get("name") or "unknown"
                video_id = str(raw_video_id)
                raw_file_path = it.get("file_path")
                file_path = str(raw_file_path) if raw_file_path is not None else ""
                size = it.get("size_bytes", "?")
                mtime = it.get("mtime", "?")
                label = it.get("label")

                with cols[0]:
                    st.markdown(f"**{video_id}**")
                    st.caption(file_path)
                with cols[1]:
                    st.text(f"size: {size}")
                    st.text(f"mtime: {mtime}")
                with cols[2]:
                    st.text(f"label: {label}")
                with cols[3]:
                    url = api_client.video_url(file_path)
                    thumb = api_client.thumb_url(video_id)
                    render_video_or_thumb(url=url, thumb_url=thumb, width=160)
                with cols[4]:
                    with st.popover("Promote"):
                        dest = st.radio("Destination", ["train", "test"], horizontal=True)
                        lbl = None
                        if dest == "train":
                            lbl = st.selectbox("Label", ["happy", "sad", "neutral"], index=0)
                        action_label = "Promote Now" if execute_mode else "Simulate Promote"
                        if st.button(action_label, key=f"prom_{video_id}"):
                            try:
                                resp = api_client.promote(
                                    video_id=str(video_id),
                                    dest_split=dest,
                                    label=lbl,
                                    dry_run=not execute_mode,
                                    use_gateway=True,
                                )
                                if execute_mode:
                                    st.success("Promotion executed.")
                                else:
                                    st.success("Promotion plan (dry-run).")
                                st.json(resp)
                            except Exception as e:  # noqa: BLE001
                                st.error("Promotion failed.")
                                st.exception(e)
