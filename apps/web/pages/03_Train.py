from __future__ import annotations

from collections import Counter
from typing import Any, Dict

import streamlit as st

from apps.web import api_client

st.set_page_config(page_title="Training", layout="wide")
st.title("03 - Training")

# ============================================================================
# Thresholds
# ============================================================================

TOTAL_VIDEO_THRESHOLD = 9001
PER_EMOTION_THRESHOLD = 3000
EMOTION_CLASSES = ("happy", "sad", "neutral")

# Extraction-complete statuses that allow training initiation.
_EXTRACTION_COMPLETE = {"completed", "completed_gate_passed"}

# Training in-progress statuses.
_TRAINING_IN_PROGRESS = {"training", "evaluating", "sampling"}

# Initialize session state for tracking extraction results.
if "last_extraction_run_id" not in st.session_state:
    st.session_state.last_extraction_run_id = None
if "last_extraction_status" not in st.session_state:
    st.session_state.last_extraction_status = None


def _items_for_split(split: str) -> list[dict]:
    data = api_client.list_videos(split=split, limit=1000, offset=0)
    raw_items = data.get("items", []) if isinstance(data, dict) else []
    return [it for it in raw_items if isinstance(it, dict)]


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _render_status_panel(title: str, payload: Dict[str, Any]) -> None:
    st.markdown(f"**{title}**")
    run_status = str(payload.get("status") or "unknown").lower()
    metrics = _as_dict(payload.get("metrics"))
    error_message = payload.get("error_message")
    blocked_reason = metrics.get("blocked_reason")

    if run_status == "blocked":
        st.warning(f"Blocked: {blocked_reason or 'pipeline gate not satisfied'}")
    elif run_status in {"completed", "completed_gate_passed"}:
        st.success(f"Completed ({run_status})")
    elif run_status == "completed_gate_failed":
        st.error(f"Completed but Gate A failed ({run_status})")
    elif run_status in _TRAINING_IN_PROGRESS | {"pending", "running"}:
        st.info(f"In progress ({run_status})")
    elif run_status in {"failed", "error", "cancelled"}:
        st.error(f"Failed ({run_status})")
    else:
        st.caption(f"Status: {run_status}")

    if run_status == "blocked":
        counts = _as_dict(metrics.get("counts"))
        min_required = metrics.get("min_required_per_class")
        if counts:
            st.caption(
                "Test counts "
                f"(happy={counts.get('happy', 0)}, sad={counts.get('sad', 0)}, neutral={counts.get('neutral', 0)})"
            )
        if min_required is not None:
            st.caption(f"Minimum required per class: {min_required}")

    # Show Gate A results if available.
    gate_results = metrics.get("gate_a_gates") or metrics.get("gate_results")
    if isinstance(gate_results, dict):
        st.markdown("**Gate A Results:**")
        for gate_name, passed in gate_results.items():
            icon = "PASS" if passed else "FAIL"
            st.caption(f"  {gate_name}: {icon}")

    if error_message:
        st.caption(f"Error: {error_message}")

    st.json(payload)


# ============================================================================
# Train/Test Split Overview + Readiness Check
# ============================================================================

train_counts: Counter = Counter()
train_total = 0
try:
    train_items = _items_for_split("train")
    train_counts = Counter((it.get("label") or "unlabeled") for it in train_items)
    train_total = len(train_items)
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load train split: {exc}")
    train_items = []

test_total = 0
try:
    test_items = _items_for_split("test")
    test_counts = Counter((it.get("label") or "no_label") for it in test_items)
    test_total = len(test_items)
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load test split: {exc}")
    test_items = []

col1, col2 = st.columns(2)
with col1:
    st.subheader("Train Split")
    st.metric("Total", train_total)
    st.json(dict(train_counts))

with col2:
    st.subheader("Test Split")
    st.metric("Total", test_total)
    st.json(dict(test_counts))

# ============================================================================
# Per-Emotion Readiness Gauges
# ============================================================================

st.divider()
st.subheader("Extraction Readiness")

emotion_met = {}
gauge_cols = st.columns(len(EMOTION_CLASSES) + 1)

for idx, emotion in enumerate(EMOTION_CLASSES):
    count = train_counts.get(emotion, 0)
    met = count >= PER_EMOTION_THRESHOLD
    emotion_met[emotion] = met
    delta_val = count - PER_EMOTION_THRESHOLD
    with gauge_cols[idx]:
        st.metric(
            label=f"{emotion.capitalize()}",
            value=f"{count:,}",
            delta=f"{delta_val:+,} vs {PER_EMOTION_THRESHOLD:,}",
            delta_color="normal" if met else "inverse",
        )

all_emotions_met = all(emotion_met.values())
total_met = train_total >= TOTAL_VIDEO_THRESHOLD
extraction_enabled = all_emotions_met and total_met

with gauge_cols[-1]:
    delta_total = train_total - TOTAL_VIDEO_THRESHOLD
    st.metric(
        label="Total",
        value=f"{train_total:,}",
        delta=f"{delta_total:+,} vs {TOTAL_VIDEO_THRESHOLD:,}",
        delta_color="normal" if total_met else "inverse",
    )

if extraction_enabled:
    st.success("All thresholds met. Frame extraction is enabled.")
else:
    shortfalls = []
    for emotion in EMOTION_CLASSES:
        count = train_counts.get(emotion, 0)
        if count < PER_EMOTION_THRESHOLD:
            shortfalls.append(f"{emotion}: need {PER_EMOTION_THRESHOLD - count:,} more")
    if not total_met:
        shortfalls.append(f"total: need {TOTAL_VIDEO_THRESHOLD - train_total:,} more")
    st.warning(
        "Frame extraction is disabled until all thresholds are met. "
        f"Shortfalls: {'; '.join(shortfalls)}"
    )


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
    if st.button(
        "Extract Frames",
        type="primary",
        use_container_width=True,
        disabled=not extraction_enabled,
    ):
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
                    # Track extraction completion in session state.
                    st.session_state.last_extraction_run_id = resp.get("run_id")
                    st.session_state.last_extraction_status = "completed"
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
# Initiate ML Training Run
# ============================================================================

st.divider()
st.subheader("Initiate Training Run")
st.caption(
    "Once frame extraction is complete, initiate EfficientNet-B0 fine-tuning. "
    "This notifies the n8n Training Orchestrator (Agent 5) to start the ML "
    "pipeline: train, evaluate, and validate against Gate A thresholds."
)

# Determine if a run is ready to initiate training.
# Check session state first (from a just-completed extraction), then allow
# manual entry for runs completed in prior sessions.
initiate_run_id = st.text_input(
    "Run ID to initiate",
    value=st.session_state.last_extraction_run_id or "",
    placeholder="run_0001",
    help="Enter the run_id from a completed frame extraction.",
    key="initiate_run_id",
)

config_path = st.text_input(
    "Training config path",
    value="trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml",
    help="Path to the EfficientNet training YAML configuration.",
    key="training_config_path",
)

# Check whether the specified run has completed extraction.
run_ready = False
run_status_msg = ""
if initiate_run_id.strip():
    try:
        run_info = _as_dict(api_client.get_training_status(initiate_run_id.strip()))
        current_status = str(run_info.get("status", "unknown")).lower()
        if current_status in _EXTRACTION_COMPLETE:
            run_ready = True
            run_status_msg = f"Run {initiate_run_id} extraction complete. Ready to train."
        elif current_status in _TRAINING_IN_PROGRESS:
            run_status_msg = f"Run {initiate_run_id} is already in progress ({current_status})."
        elif current_status in {"failed", "error", "cancelled"}:
            run_status_msg = f"Run {initiate_run_id} has failed. Cannot initiate training."
        else:
            run_status_msg = f"Run {initiate_run_id} status: {current_status}. Extraction must complete first."
    except Exception:  # noqa: BLE001
        run_status_msg = f"Run {initiate_run_id} not found. Extract frames first."

if run_status_msg:
    if run_ready:
        st.success(run_status_msg)
    else:
        st.warning(run_status_msg)

if st.button(
    "Initiate Run",
    type="primary",
    use_container_width=True,
    disabled=not run_ready,
):
    try:
        with st.spinner("Initiating training run..."):
            resp = api_client.initiate_run(
                run_id=initiate_run_id.strip(),
                config_path=config_path.strip(),
            )
        resp_status = resp.get("status", "unknown")
        n8n_notified = resp.get("n8n_notified", False)
        message = resp.get("message", "")

        if resp_status == "accepted":
            if n8n_notified:
                st.success(
                    f"Training initiated for **{resp.get('run_id')}**. "
                    f"n8n Agent 5 has been notified and is orchestrating the pipeline."
                )
            else:
                st.warning(
                    f"Training run status updated for **{resp.get('run_id')}**, "
                    f"but n8n notification may have failed. {message}"
                )
            # Clear extraction state so button reflects new status on rerun.
            st.session_state.last_extraction_status = None
        else:
            st.warning(f"Unexpected response: {resp_status}")

        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to initiate training: {exc}")


# ============================================================================
# Training Run Status
# ============================================================================

st.divider()
st.subheader("Training Run Status")
status_run_id = st.text_input(
    "Run ID to check",
    value=initiate_run_id if initiate_run_id.strip() else (
        extract_run_id if extract_run_id.strip() else "run_0001"
    ),
    key="status_run_id",
)
if st.button("Refresh Training Status"):
    try:
        run_payload = _as_dict(api_client.get_training_status(status_run_id))
        _render_status_panel(f"Run: {status_run_id}", run_payload)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Status fetch failed: {exc}")
