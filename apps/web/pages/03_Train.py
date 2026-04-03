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


st.divider()
st.subheader("Manifest + Frame Extraction")

if "train_run_id" not in st.session_state:
    st.session_state["train_run_id"] = ""
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
    """Create training dataset (frame extraction) via API - no split."""
    if not dataset_run_id:
        st.error("Please enter a run_ID for the dataset")
        return

    try:
        with st.spinner(f"Extracting training frames for {dataset_run_id}..."):
            resp = api_client.prepare_run_frames(
                run_id=dataset_run_id,
                train_fraction=1.0,  # Use all videos
                dry_run=False,
                face_crop=False,
                correlation_id=None,
                idempotency_key=None,
            )
        st.success(f"✓ Training dataset created: {resp.get('train_count', 0)} frames in /train/run/{dataset_run_id}/")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Training dataset creation failed: {exc}")


dataset_col1, dataset_col2, dataset_col3 = st.columns(3)
with dataset_col1:
    st.markdown("**Training Dataset**")
    st.caption("Extract frames from Luma videos (all in one directory)")
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
st.subheader("🚀 ML Runs — EfficientNet-B0")
st.caption(
    "Launch training, validation, or test runs. Select model type to determine available operations."
)

# Model type selection
model_type = st.selectbox(
    "Model Type",
    options=["Variant 1", "Variant 2", "Base Model"],
    index=0,
    help=(
        "**Base Model**: HSEmotion pretrained (test only)\n\n"
        "**Variant 1**: Base + Luma synthetic videos (train/validate/test)\n\n"
        "**Variant 2**: Fine-tuned Variant 1 (validate/test only)"
    ),
    key="ml_model_type",
)

# Map display name to variant identifier
model_variant_map = {
    "Base Model": "base",
    "Variant 1": "variant_1",
    "Variant 2": "variant_2",
}
selected_variant = model_variant_map[model_type]

# Default checkpoint paths per model type
default_checkpoints = {
    "base": "/media/rusty_admin/project_data/reachy_emotion/checkpoints/hsemotion/enet_b0_8_best_vgaf.pth",
    "variant_1": "/media/rusty_admin/project_data/reachy_emotion/checkpoints/efficientnet_b0_3cls/best_model.pth",
    "variant_2": "/media/rusty_admin/project_data/reachy_emotion/checkpoints/efficientnet_b0_3cls_finetuned/best_model.pth",
}

ml_run_id = st.text_input(
    "ML Run ID (auto-generated if empty)",
    value=st.session_state.get("train_run_id", ""),
    key="ml_run_id_input",
)
ml_checkpoint = st.text_input(
    "Checkpoint path (required for Validate/Test)",
    value=default_checkpoints[selected_variant],
    key="ml_checkpoint_input",
    help=f"Default checkpoint for {model_type}",
)

# Display model-specific requirements
if model_type == "Base Model":
    st.info("ℹ️ **Base Model**: Only test evaluation available. Requires test dataset.")
elif model_type == "Variant 1":
    st.info("ℹ️ **Variant 1**: Full pipeline available. Requires training frames + validation + test datasets.")
else:  # Variant 2
    st.info("ℹ️ **Variant 2**: Validation and test available. Uses Variant 1 checkpoint as starting point.")


def _launch_ml_run(mode: str) -> None:
    """Trigger a training, validation, or test run via the backend."""
    try:
        resp = api_client.launch_ml_run(
            mode=mode,
            run_id=ml_run_id or None,
            variant=selected_variant,
            checkpoint=ml_checkpoint or None,
            test_data_dir=None,  # Uses run-scoped test dataset at /test/<run_id>
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


# Button availability based on model type
can_train = model_type == "Variant 1"
can_validate = model_type in ["Variant 1", "Variant 2"]
can_test = True  # All models can be tested

ml_col1, ml_col2, ml_col3 = st.columns(3)
with ml_col1:
    st.markdown("**Training Run**")
    st.caption("Full pipeline: train → evaluate → Gate A")
    if st.button(
        "🚀 Start Training",
        use_container_width=True,
        type="primary",
        disabled=not can_train,
        help="Only available for Variant 1" if not can_train else "Train model on Luma synthetic videos",
    ):
        _launch_ml_run("train")

with ml_col2:
    st.markdown("**Validation Run**")
    st.caption("Evaluate checkpoint on validation split")
    if st.button(
        "📊 Start Validation",
        use_container_width=True,
        disabled=not can_validate,
        help="Not available for Base Model" if not can_validate else "Evaluate on AffectNet validation set",
    ):
        _launch_ml_run("validate")

with ml_col3:
    st.markdown("**Test Run**")
    st.caption("Evaluate on AffectNet test dataset")
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
