from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Dict

import streamlit as st

from apps.web import api_client
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Training", layout="wide")
render_navigation_bar()
st.title("03 - Training")


_SPLIT_COUNT_LIMIT = 500  # enough for label distribution; avoids fetching 40K+ items


def _items_for_split(split: str, limit: int = _SPLIT_COUNT_LIMIT) -> list[dict]:
    items: list[dict] = []
    offset = 0
    page_limit = 10
    while len(items) < limit:
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
        train_data = api_client.list_videos(split="train", limit=10, offset=0)
        train_total = train_data.get("total", 0)
        train_sample = train_data.get("items", [])
        train_counts = Counter(_resolve_label(it) for it in train_sample if isinstance(it, dict))
        st.subheader("Train Split")
        st.metric("Total", train_total)
        st.caption("Label distribution (first 10 videos)")
        st.json(dict(train_counts))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load train split: {exc}")

with col2:
    try:
        test_data = api_client.list_videos(split="test", limit=10, offset=0)
        test_total = test_data.get("total", 0)
        test_sample = test_data.get("items", [])
        test_counts = Counter((it.get("label") or "no_label") for it in test_sample if isinstance(it, dict))
        st.subheader("Test Split")
        st.metric("Total", test_total)
        st.caption("Label distribution (first 10 videos)")
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
if "pending_generated_run_id" in st.session_state:
    # Apply pending run-id updates before the text_input widget is created.
    st.session_state["train_run_id"] = st.session_state.pop("pending_generated_run_id")
if st.session_state.pop("generated_run_id_notice", False):
    st.info("Generated run ID. Leave empty to auto-generate the next run_xxxx on the backend.")

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
    "Split run into train_ds/valid_ds (DEPRECATED)",
    key="prepare_split_run",
    help="DEPRECATED: Creates 90/10 split subdirectories. Use 'Dataset Preparation' section below to create dedicated AffectNet validation datasets instead.",
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

st.caption(
    "Source videos are read from local folders: "
    "`videos/train/happy`, `videos/train/sad`, `videos/train/neutral`."
)


def _trigger_prepare_run(*, mode: str = "inherit") -> None:
    if mode == "live":
        effective_dry_run = False
    elif mode == "dry_run":
        effective_dry_run = True
    else:
        effective_dry_run = dry_run

    if mode == "live" and dry_run:
        st.info("Dry run toggle is ON, but manual execute runs in live mode.")
    if mode == "dry_run" and not dry_run:
        st.info("Dry run toggle is OFF, but manual validate runs in dry-run mode.")
    try:
        corr_id = str(uuid.uuid4())
        resp = api_client.prepare_run_frames(
            run_id=run_id or None,
            train_fraction=sample_fraction,
            dry_run=effective_dry_run,
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
        if mode == "dry_run":
            st.success(f"Manual validate plan completed for run: {resp.get('run_id', 'unknown')}")
        elif effective_dry_run:
            st.success(f"Dry-run validated frame dataset plan for run: {resp.get('run_id', 'unknown')}")
        elif mode == "live":
            st.success(f"Manual execute live completed for run: {resp.get('run_id', 'unknown')}")
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


action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)
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
        _trigger_prepare_run(mode="inherit")

with action_col3:
    if st.button("Manual Validate Plan", use_container_width=True):
        _trigger_prepare_run(mode="dry_run")

with action_col4:
    if st.button("Manual Execute Live", use_container_width=True):
        _trigger_prepare_run(mode="live")

with action_col5:
    if st.button("Generate New Run ID", use_container_width=True):
        st.session_state["pending_generated_run_id"] = f"run_{(uuid.uuid4().int % 10000):04d}"
        st.session_state["generated_run_id_notice"] = True
        st.rerun()

st.divider()
st.subheader("📦 Dataset Preparation")
st.caption(
    "Create validation and test datasets from AffectNet for a specific run. "
    "Use the same run_ID for datasets and training to ensure consistency."
)

# Dataset creation run ID (shared with training)
dataset_run_id = st.text_input(
    "Dataset Run ID (e.g., run_0300)",
    value=st.session_state.get("train_run_id", ""),
    key="dataset_run_id_input",
    help="This run_ID will be used for both validation and test datasets, and should match your training run_ID"
)

# Dataset creation parameters in expander
with st.expander("⚙️ Dataset Parameters", expanded=False):
    val_samples = st.number_input(
        "Validation samples per class",
        min_value=100,
        max_value=2000,
        value=500,
        step=50,
        help="Number of images per emotion class for validation (default: 500)"
    )
    test_samples = st.number_input(
        "Test samples per class",
        min_value=50,
        max_value=1000,
        value=250,
        step=50,
        help="Number of images per emotion class for test (default: 250)"
    )
    val_confidence = st.slider(
        "Validation min confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.6,
        step=0.1,
        help="Minimum soft-label confidence for validation images"
    )
    val_seed = st.number_input("Validation seed", value=42, help="Random seed for validation sampling")
    test_seed = st.number_input("Test seed", value=142, help="Random seed for test sampling (different from validation)")


def _create_validation_dataset() -> None:
    """Create validation dataset via API."""
    if not dataset_run_id:
        st.error("Please enter a run_ID for the dataset")
        return
    
    try:
        with st.spinner(f"Creating validation dataset for {dataset_run_id}..."):
            resp = api_client.create_validation_dataset(
                run_id=dataset_run_id,
                samples_per_class=val_samples,
                min_confidence=val_confidence,
                seed=val_seed,
            )
        st.success(f"✓ Validation dataset created: {resp['total_samples']} images")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Validation dataset creation failed: {exc}")


def _create_test_dataset() -> None:
    """Create test dataset via API."""
    if not dataset_run_id:
        st.error("Please enter a run_ID for the dataset")
        return
    
    try:
        with st.spinner(f"Creating test dataset for {dataset_run_id}..."):
            resp = api_client.create_test_dataset(
                run_id=dataset_run_id,
                samples_per_class=test_samples,
                source="validation",
                seed=test_seed,
            )
        st.success(f"✓ Test dataset created: {resp['total_samples']} images (unlabeled)")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Test dataset creation failed: {exc}")


def _create_training_dataset() -> None:
    """Create training dataset (frame extraction) via API."""
    if not dataset_run_id:
        st.error("Please enter a run_ID for the dataset")
        return

    try:
        with st.spinner(f"Creating training dataset for {dataset_run_id}..."):
            resp = api_client.create_training_dataset(
                run_id=dataset_run_id,
                train_fraction=0.9,
                split_run=True,
                split_train_ratio=0.9,
                dry_run=False,
            )
        st.success(f"✓ Training dataset created for run: {resp.get('run_id', dataset_run_id)}")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Training dataset creation failed: {exc}")


dataset_col1, dataset_col2, dataset_col3 = st.columns(3)
with dataset_col1:
    st.markdown("**Training Dataset**")
    st.caption("Extract frames from labeled videos (train_ds + valid_ds)")
    if st.button("🎬 Create Training Dataset", use_container_width=True, type="primary"):
        _create_training_dataset()

with dataset_col2:
    st.markdown("**Validation Dataset**")
    st.caption(f"Create {val_samples} images/class from AffectNet")
    if st.button("📊 Create Validation Dataset", use_container_width=True):
        _create_validation_dataset()

with dataset_col3:
    st.markdown("**Test Dataset**")
    st.caption(f"Create {test_samples} images/class (unlabeled)")
    if st.button("🧪 Create Test Dataset", use_container_width=True):
        _create_test_dataset()

st.divider()
st.subheader("🚀 ML Runs — EfficientNet-B0 (Frozen Backbone)")
st.caption(
    "Launch training, validation, or test runs using the EfficientNet-B0 model "
    "with HSEmotion pretrained weights (`enet_b0_8_best_vgaf`). "
    "All runs use frozen-backbone settings from `efficientnet_b0_emotion_3cls.yaml`. "
    "Use the same run_ID as your datasets above."
)

ml_run_id = st.text_input(
    "ML Run ID (auto-generated if empty)",
    value=st.session_state.get("train_run_id", ""),
    key="ml_run_id_input",
)
ml_checkpoint = st.text_input(
    "Checkpoint path (required for Validate/Test; defaults to best_model.pth)",
    value="/media/rusty_admin/project_data/reachy_emotion/checkpoints/efficientnet_b0_3cls/best_model.pth",
    key="ml_checkpoint_input",
)

AFFECTNET_TEST_DIR = "/media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset"


def _launch_ml_run(mode: str) -> None:
    """Trigger a training, validation, or test run via the backend."""
    try:
        resp = api_client.launch_ml_run(
            mode=mode,
            run_id=ml_run_id or None,
            variant="variant_1",
            checkpoint=ml_checkpoint or None,
            test_data_dir=AFFECTNET_TEST_DIR if mode == "test" else None,
        )
        st.success(f"{mode.capitalize()} run launched: {resp.get('run_id', 'unknown')}")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        if "422" in str(exc) and "checkpoint" in str(exc).lower():
            st.error(
                "No checkpoint found. Run a training job first, or provide "
                "an explicit checkpoint path above."
            )
        elif "404" in str(exc):
            st.error(
                "Training launch endpoint not found. Restart the Media Mover API "
                "with the latest code, then retry."
            )
        else:
            st.error(f"{mode.capitalize()} run failed to launch: {exc}")


ml_col1, ml_col2, ml_col3 = st.columns(3)
with ml_col1:
    st.markdown("**Training Run**")
    st.caption("Full pipeline: train → evaluate → Gate A")
    if st.button("🚀 Start Training", use_container_width=True, type="primary"):
        _launch_ml_run("train")

with ml_col2:
    st.markdown("**Validation Run**")
    st.caption("Evaluate checkpoint on validation split")
    if st.button("📊 Start Validation", use_container_width=True):
        _launch_ml_run("validate")

with ml_col3:
    st.markdown("**Test Run (AffectNet)**")
    st.caption(f"Evaluate on `{AFFECTNET_TEST_DIR}`")
    if st.button("🧪 Start Test", use_container_width=True):
        _launch_ml_run("test")


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
