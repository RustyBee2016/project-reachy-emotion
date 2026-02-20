from __future__ import annotations

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


# ============================================================================
# Train/Test Split Overview
# ============================================================================

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


# ============================================================================
# Frame Extraction
# ============================================================================

st.divider()
st.subheader("Frame Extraction")
st.caption(
    "Extract random frames from classified videos in train/<emotion>/. "
    "Frames are stored per-emotion and consolidated into a run dataset "
    "at train/run/<run_id>/<emotion>/."
)

extract_col1, extract_col2 = st.columns(2)
with extract_col1:
    extract_run_id = st.text_input(
        "Run ID (run_xxxx)",
        value="",
        placeholder="Auto-generated if empty",
        help="Leave blank to auto-generate the next sequential run ID.",
        key="extract_run_id",
    )
    frames_per_video = st.number_input(
        "Frames per video",
        min_value=1,
        max_value=100,
        value=10,
        step=1,
        help="Number of random frames to sample from each video.",
    )

with extract_col2:
    extract_seed = st.number_input(
        "Random seed",
        min_value=0,
        max_value=2**31 - 1,
        value=0,
        step=1,
        help="Set to 0 for auto-generated seed based on run ID.",
    )
    extract_dry_run = st.toggle("Dry run (preview only)", value=True, key="extract_dry_run")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button("Extract Frames", type="primary", use_container_width=True):
        resolved_run_id = extract_run_id.strip() if extract_run_id.strip() else None
        resolved_seed = extract_seed if extract_seed > 0 else None
        try:
            with st.spinner("Extracting frames..."):
                resp = api_client.extract_frames(
                    run_id=resolved_run_id,
                    seed=resolved_seed,
                    frames_per_video=frames_per_video,
                    dry_run=extract_dry_run,
                )
            resp_status = resp.get("status", "unknown")
            if resp_status in ("completed", "dry_run"):
                if extract_dry_run:
                    st.info(f"Dry run: {resp.get('videos_processed', 0)} videos, "
                            f"{resp.get('train_count', 0)} frames would be extracted.")
                else:
                    st.success(
                        f"Extraction complete: run **{resp.get('run_id')}** - "
                        f"{resp.get('train_count', 0)} frames from "
                        f"{resp.get('videos_processed', 0)} videos."
                    )
            else:
                st.warning(f"Unexpected status: {resp_status}")
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Frame extraction failed: {exc}")

with btn_col2:
    if st.button("Rebuild Manifests", use_container_width=True):
        try:
            resp = api_client.rebuild_manifest()
            st.success("Manifest rebuild requested.")
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Manifest rebuild failed: {exc}")


# ============================================================================
# Training Run Status
# ============================================================================

st.divider()
st.subheader("Training Run Status")
status_run_id = st.text_input(
    "Run ID to check",
    value=extract_run_id if extract_run_id.strip() else "run_0001",
    key="status_run_id",
)
if st.button("Refresh Training Status"):
    try:
        run_payload = _as_dict(api_client.get_training_status(status_run_id))
        _render_status_panel(f"Run: {status_run_id}", run_payload)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Status fetch failed: {exc}")
