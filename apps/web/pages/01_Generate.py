from __future__ import annotations

import uuid
from datetime import datetime

import streamlit as st

from apps.web import api_client

st.set_page_config(page_title="Generate Clips", layout="wide")
st.title("01 - Generate Synthetic Clips")

if "generation_requests" not in st.session_state:
    st.session_state.generation_requests = []

with st.form("gen_form"):
    col1, col2 = st.columns(2)
    with col1:
        prompt = st.text_area("Prompt", placeholder="A neutral expression turning into a smile")
        duration = st.number_input("Duration (s)", min_value=1, max_value=10, value=3)
    with col2:
        emotion = st.selectbox("Target Emotion", ["happy", "sad", "neutral"], index=0)
        count = st.slider("Number of clips", min_value=1, max_value=10, value=1)
    submitted = st.form_submit_button("Queue Generation")

if submitted:
    correlation_id = str(uuid.uuid4())
    request_payload = {
        "emotion": emotion,
        "duration_sec": duration,
        "count": count,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    try:
        response = api_client.request_generation(
            prompt=prompt,
            correlation_id=correlation_id,
            params=request_payload,
        )
        st.success("Generation request queued.")
        st.session_state.generation_requests.insert(
            0,
            {
                "prompt": prompt,
                "correlation_id": correlation_id,
                "request": request_payload,
                "response": response,
            },
        )
        st.session_state.generation_requests = st.session_state.generation_requests[:20]
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to queue generation request: {exc}")

if st.session_state.generation_requests:
    st.subheader("Recent Requests")
    for idx, item in enumerate(st.session_state.generation_requests, start=1):
        with st.expander(f"{idx}. {item['prompt'][:70]}"):
            st.json(item)
