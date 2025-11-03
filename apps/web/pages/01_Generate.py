import streamlit as st

st.set_page_config(page_title="Generate Clips", layout="wide")

st.title("01 — Generate Synthetic Clips")

st.info(
    "This page will host controls to generate short emotion clips via external tools or local scripts."
)

with st.form("gen_form"):
    col1, col2 = st.columns(2)
    with col1:
        prompt = st.text_input("Prompt / Notes", value="happy face, neutral background")
        duration = st.number_input("Duration (s)", min_value=1, max_value=10, value=3)
    with col2:
        emotion = st.selectbox("Target Emotion", ["happy", "sad"], index=0)
        count = st.slider("Number of clips", min_value=1, max_value=10, value=3)
    submitted = st.form_submit_button("Preview Plan (No-Op)")

if submitted:
    st.success("Plan generated (no-op). This is a placeholder; hook up to generator later.")
    st.json({"prompt": prompt, "duration": duration, "emotion": emotion, "count": count})
