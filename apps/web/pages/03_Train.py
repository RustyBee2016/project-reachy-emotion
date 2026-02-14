from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Dict

import streamlit as st

from apps.web import api_client

st.set_page_config(page_title="Training", layout="wide")
st.title("03 - Training")


def _items_for_split(split: str) -> list[dict]:
    data = api_client.list_videos(split=split, limit=1000, offset=0)
    raw_items = data.get("items", []) if isinstance(data, dict) else []
    return [it for it in raw_items if isinstance(it, dict)]


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _render_status_panel(title: str, payload: Dict[str, Any]) -> None:
    st.markdown(f"**{title}**")
    status = str(payload.get("status") or "unknown").lower()
    metrics = _as_dict(payload.get("metrics"))
    error_message = payload.get("error_message")
    blocked_reason = metrics.get("blocked_reason")

    if status == "blocked":
        st.warning(f"Blocked: {blocked_reason or 'pipeline gate not satisfied'}")
    elif status in {"completed", "completed_gate_passed", "completed_gate_failed"}:
        st.success(f"Completed ({status})")
    elif status in {"training", "evaluating", "pending", "sampling", "running"}:
        st.info(f"In progress ({status})")
    elif status in {"failed", "error", "cancelled"}:
        st.error(f"Failed ({status})")
    else:
        st.caption(f"Status: {status}")

    if status == "blocked":
        counts = _as_dict(metrics.get("counts"))
        min_required = metrics.get("min_required_per_class")
        if counts:
            st.caption(
                "Test counts "
                f"(happy={counts.get('happy', 0)}, sad={counts.get('sad', 0)}, neutral={counts.get('neutral', 0)})"
            )
        if min_required is not None:
            st.caption(f"Minimum required per class: {min_required}")

    if error_message:
        st.caption(f"Error: {error_message}")

    st.json(payload)


col1, col2 = st.columns(2)
with col1:
    try:
        train_items = _items_for_split("train")
        train_counts = Counter((it.get("label") or "unlabeled") for it in train_items)
        st.subheader("Train Split")
        st.metric("Total", len(train_items))
        st.json(dict(train_counts))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load train split: {exc}")

with col2:
    try:
        test_items = _items_for_split("test")
        test_counts = Counter((it.get("label") or "no_label") for it in test_items)
        st.subheader("Test Split")
        st.metric("Total", len(test_items))
        st.json(dict(test_counts))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load test split: {exc}")

st.divider()
st.subheader("Manifest + Sampling")

run_id = st.text_input("Run ID (UUID4)", value=str(uuid.uuid4()))
sample_fraction = st.slider("Sample fraction", min_value=0.1, max_value=1.0, value=0.8, step=0.1)
dry_run = st.toggle("Dry run", value=True)

action_col1, action_col2, action_col3 = st.columns(3)
with action_col1:
    if st.button("Rebuild Manifests", use_container_width=True):
        try:
            resp = api_client.rebuild_manifest()
            st.success("Manifest rebuild requested.")
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Manifest rebuild failed: {exc}")

with action_col2:
    if st.button("Sample Train", use_container_width=True):
        try:
            resp = api_client.sample_split(
                run_id=run_id,
                target_split="train",
                sample_fraction=sample_fraction,
                dry_run=dry_run,
            )
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Sampling train failed: {exc}")

with action_col3:
    if st.button("Sample Test", use_container_width=True):
        try:
            resp = api_client.sample_split(
                run_id=run_id,
                target_split="test",
                sample_fraction=sample_fraction,
                dry_run=dry_run,
            )
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Sampling test failed: {exc}")

st.divider()
st.subheader("Training Status")
pipeline_id = st.text_input("Pipeline ID", value=run_id)
if st.button("Refresh Training Status"):
    try:
        run_payload = _as_dict(api_client.get_training_status(pipeline_id))
        latest_payload = _as_dict(api_client.get_training_status("latest"))
        col_run, col_latest = st.columns(2)
        with col_run:
            _render_status_panel(f"Run: {pipeline_id}", run_payload)
        with col_latest:
            _render_status_panel("Latest Snapshot", latest_payload)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Status fetch failed: {exc}")
