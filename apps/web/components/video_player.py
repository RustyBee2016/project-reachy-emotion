from typing import Optional

import streamlit as st


def render_video_or_thumb(url: Optional[str], thumb_url: Optional[str] = None, width: int = 480) -> None:
    if url and url.lower().endswith((".mp4", ".webm", ".mov")):
        st.video(url, format="video/mp4")
    elif thumb_url:
        st.image(thumb_url, width=width)
    else:
        st.write("No preview available.")
