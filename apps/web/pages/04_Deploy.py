from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from apps.web import api_client
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Deploy", layout="wide")
render_navigation_bar()
st.title("04 - Deploy")

pipeline_id = st.text_input("Pipeline ID", value="latest")

col1, col2 = st.columns(2)
with col1:
    if st.button("Refresh Deployment Status", use_container_width=True):
        try:
            status_payload = api_client.get_deployment_status(pipeline_id)
            st.json(status_payload)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to fetch deployment status: {exc}")

with col2:
    if st.button("Request Canary Promotion", use_container_width=True):
        try:
            payload = {
                "status": "requested",
                "target_stage": "canary",
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }
            resp = api_client.update_deployment_status(pipeline_id, payload)
            st.success("Canary deployment request recorded.")
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to request deployment: {exc}")

st.info(
    "This page records deployment intents and reads deployment status. "
    "Actual TensorRT rollout remains controlled by n8n Deployment Agent approvals."
)
