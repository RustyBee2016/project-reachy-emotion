from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Dict

import streamlit as st

from apps.web import api_client

st.set_page_config(page_title="Training", layout="wide")
st.title("03 - Training")


def _items_for_split(split: str) -> list[dict]:
    items: list[dict] = []
    offset = 0
    page_limit = 10
    while True:
        data = api_client.list_videos(split=split, limit=page_limit, offset=offset)
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(raw_items, list):
            break
        batch = [it for it in raw_items if isinstance(it, dict)]
        items.extend(batch)
        if not data.get("has_more"):
            break
        offset += len(batch)
        if not batch:
            break
    return items


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _resolve_label(item: Dict[str, Any]) -> str:
    raw_label = item.get("label")
    if isinstance(raw_label, str):
        normalized = raw_label.strip().lower()
        if normalized in {"happy", "sad", "neutral"}:
            return normalized

    file_path = item.get("file_path")
    if isinstance(file_path, str):
        parts = file_path.split("/")
        if len(parts) >= 2 and parts[0] == "train" and parts[1] in {"happy", "sad", "neutral"}:
            return parts[1]
        name = parts[-1].lower()
        for label in ("happy", "sad", "neutral"):
            if name.startswith(f"{label}_"):
                return label
    return "unlabeled"


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
        train_counts = Counter(_resolve_label(it) for it in train_items)
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
st.subheader("Manifest + Frame Extraction")

if "train_run_id" not in st.session_state:
    st.session_state["train_run_id"] = ""
if "prepare_split_run" not in st.session_state:
    st.session_state["prepare_split_run"] = False
if "prepare_split_train_ratio" not in st.session_state:
    st.session_state["prepare_split_train_ratio"] = 0.9
if "prepare_strip_valid_labels" not in st.session_state:
    st.session_state["prepare_strip_valid_labels"] = True
if "prepare_persist_valid_metadata" not in st.session_state:
    st.session_state["prepare_persist_valid_metadata"] = True
if "prepare_face_crop" not in st.session_state:
    st.session_state["prepare_face_crop"] = False
if "prepare_face_confidence" not in st.session_state:
    st.session_state["prepare_face_confidence"] = 0.6

run_id = st.text_input("Run ID (run_xxxx, optional)", key="train_run_id")
sample_fraction = st.slider(
    "Train fraction (compat metadata)",
    min_value=0.1,
    max_value=1.0,
    value=0.8,
    step=0.1,
)
dry_run = st.toggle("Dry run", value=True)
face_crop = st.toggle(
    "Enable face-crop extraction (OpenCV DNN)",
    key="prepare_face_crop",
    help="Detect faces with OpenCV DNN, crop to face ROI, resize to 224x224, and skip frames without faces.",
)
face_confidence = st.slider(
    "Face detection confidence",
    min_value=0.3,
    max_value=0.95,
    value=float(st.session_state["prepare_face_confidence"]),
    step=0.05,
    key="prepare_face_confidence",
    disabled=not face_crop,
)
split_run = st.toggle(
    "Split run into train_ds/valid_ds",
    key="prepare_split_run",
    help="When enabled, move frames into train_ds_<run_id> and valid_ds_<run_id> after extraction.",
)
split_train_ratio = st.slider(
    "Split train ratio",
    min_value=0.5,
    max_value=0.95,
    value=float(st.session_state["prepare_split_train_ratio"]),
    step=0.05,
    key="prepare_split_train_ratio",
    disabled=not split_run,
)
strip_valid_labels = st.toggle(
    "Strip valid_ds label prefixes",
    key="prepare_strip_valid_labels",
    disabled=not split_run,
    help="Removes happy_/sad_/neutral_ prefixes from valid_ds filenames while keeping labels in manifests.",
)
persist_valid_metadata = st.toggle(
    "Persist valid_ds metadata",
    key="prepare_persist_valid_metadata",
    disabled=not split_run,
    help="Writes valid split frame rows to extracted_frame for run-level lineage/auditing.",
)
if dry_run and split_run:
    st.caption("Dry run validates extraction only. Split/move and valid metadata persistence run when Dry run is OFF.")

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
    if st.button("Prepare 10-Frame Run", use_container_width=True):
        try:
            corr_id = str(uuid.uuid4())
            resp = api_client.prepare_run_frames(
                run_id=run_id or None,
                train_fraction=sample_fraction,
                dry_run=dry_run,
                face_crop=face_crop,
                face_target_size=224,
                face_confidence=face_confidence,
                split_run=split_run,
                split_train_ratio=split_train_ratio,
                strip_valid_labels=strip_valid_labels,
                persist_valid_metadata=bool(split_run and persist_valid_metadata),
                correlation_id=corr_id,
                idempotency_key=corr_id,
            )
            if dry_run:
                st.success(f"Dry-run validated frame dataset plan for run: {resp.get('run_id', 'unknown')}")
            else:
                st.success(f"Prepared frame dataset for run: {resp.get('run_id', 'unknown')}")
            st.json(resp)
        except Exception as exc:  # noqa: BLE001
            if "404 Client Error" in str(exc) and "prepare-run-frames" in str(exc):
                st.error(
                    "Frame extraction endpoint is missing on the running backend. "
                    "Restart fastapi-media with module apps.api.app.main:app, then retry."
                )
            st.error(f"Frame extraction failed: {exc}")

with action_col3:
    if st.button("Generate New Run ID", use_container_width=True):
        st.session_state["train_run_id"] = f"run_{(uuid.uuid4().int % 10000):04d}"
        st.info("Generated run ID. Leave empty to auto-generate the next run_xxxx on the backend.")

st.divider()
st.subheader("Training Status")
pipeline_id = st.text_input("Pipeline ID", value=st.session_state.get("train_run_id", ""))
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
