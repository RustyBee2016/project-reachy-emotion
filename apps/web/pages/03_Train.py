from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

import apps.web.path_setup  # noqa: F401
from apps.web import api_client

st.set_page_config(page_title="Training", layout="wide")

st.title("03 — Training")

st.info("Rebuild manifests before starting a training job. This is a placeholder page.")

if st.button("Rebuild Manifests (POST /manifest/rebuild)"):
    try:
        resp = api_client.rebuild_manifest()
        st.success("Manifest rebuild triggered.")
        st.json(resp)
    except Exception as e:  # noqa: BLE001
        st.error("Failed to rebuild manifests.")
        st.exception(e)
