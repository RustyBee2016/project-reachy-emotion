import streamlit as st

st.set_page_config(page_title="Deploy", layout="wide")

st.title("04 — Deploy")

st.info(
    "This page will track deployment status and control promotion of TRT engines (shadow → canary → rollout).\n"
    "For now, it is a stub UI."
)

st.markdown("- Engine version: `unknown`\n- FPS (Jetson): `unknown`\n- Latency p50/p95: `unknown` / `unknown`")
