from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Dict

import streamlit as st

from apps.web import api_client
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Fine-Tune", layout="wide")
render_navigation_bar()
st.title("07 - Fine-Tune (Variant 2)")

st.markdown(
    """
    **Variant 2** — Pre-trained *and* fine-tuned HSEmotion EfficientNet-B0 model,
    augmented with Luma-generated synthetic videos.

    This page exposes every tuneable hyperparameter for EfficientNet-B0 fine-tuning.
    Adjust the knobs below and launch a fine-tuning run. The backend writes a
    run-specific YAML with your overrides and spawns the training subprocess.

    | Model variant | Description | Page |
    |:---:|---|:---:|
    | **Base** | HSEmotion default weights, no synthetic data | — |
    | **Variant 1** | HSEmotion default weights + Luma synthetic videos | 03 Train |
    | **Variant 2** | HSEmotion fine-tuned + Luma synthetic videos | **07 Fine-Tune** |

    All three variants are evaluated against the same fixed test dataset at
    `videos/test/affectnet_test_dataset`.
    """
)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
AFFECTNET_TEST_DIR = (
    "/media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset"
)
DEFAULT_CHECKPOINT = (
    "/media/rusty_admin/project_data/reachy_emotion/checkpoints/"
    "variant_1/var1_run_0102/best_model.pth"
)
EFFICIENTNET_BLOCKS = [
    "blocks.0", "blocks.1", "blocks.2", "blocks.3",
    "blocks.4", "blocks.5", "blocks.6", "conv_head",
]


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


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Overview
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Dataset Overview")
col_train, col_test = st.columns(2)
with col_train:
    try:
        train_data = api_client.list_videos(split="train", limit=10, offset=0)
        train_total = train_data.get("total", 0)
        train_sample = [it for it in train_data.get("items", []) if isinstance(it, dict)]
        train_counts = Counter(_resolve_label(it) for it in train_sample)
        st.metric("Train Total", train_total)
        st.caption("Label distribution (first 10 videos)")
        st.json(dict(train_counts))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load train split: {exc}")

with col_test:
    try:
        test_data = api_client.list_videos(split="test", limit=10, offset=0)
        test_total = test_data.get("total", 0)
        test_sample = [it for it in test_data.get("items", []) if isinstance(it, dict)]
        test_counts = Counter((it.get("label") or "no_label") for it in test_sample)
        st.metric("Test Total (AffectNet)", test_total)
        st.caption("Label distribution (first 10 videos)")
        st.json(dict(test_counts))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load test split: {exc}")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Usage Guide (collapsible)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("Fine-Tuning Parameter Guide", expanded=False):
    st.markdown(
        """
### How to use this page

Each section below groups related hyperparameters. Hover over the **ⓘ** help
icons for parameter-specific guidance. Here is a quick summary of every knob:

---

#### 1 — Backbone Freezing Strategy
Controls *transfer learning*: how much of the pre-trained EfficientNet-B0
backbone to keep frozen vs. retrain.

- **Freeze backbone epochs** — Number of initial epochs where only the
  classification head is trained while the CNN backbone weights are locked.
  This preserves the robust facial-feature representations learned from
  VGGFace2 + AffectNet. *Typical range: 3–10.*
- **Layers to unfreeze (Phase 2)** — After the frozen phase, these backbone
  layers are unlocked for fine-tuning with a smaller learning rate.
  Later blocks (`blocks.5`, `blocks.6`, `conv_head`) capture higher-level
  features and are safer to retrain. *Unlocking earlier blocks (0–3) risks
  catastrophic forgetting.*

---

#### 2 — Learning Rate & Schedule
The most impactful fine-tuning knob. Too high → destroy pre-trained features;
too low → never adapt.

- **Learning rate** — Peak rate reached after warmup. For fine-tuning use
  1e-4 to 3e-4; the backbone uses 1/10th of this via differential LR.
- **Min learning rate** — Floor for cosine/plateau decay. Prevents the
  optimizer from stalling completely.
- **LR scheduler** — Decay strategy:
  - *cosine* — Smooth cosine anneal with warm restarts (default, recommended).
  - *plateau* — Reduces LR on validation plateau (reactive).
- **Warmup epochs** — Linearly ramps LR from ~0 to target. Prevents early
  large gradients from corrupting weights. *Typical: 2–5 epochs.*

---

#### 3 — Regularization
Prevents overfitting, critical when the dataset is small (< 5 k samples).

- **Weight decay** — L2 penalty on weights. Keeps magnitudes small. *0.0001
  is a good starting point.*
- **Dropout rate** — Fraction of neurons randomly zeroed during training in
  the classification head. Higher = more regularization. *0.2–0.5.*
- **Label smoothing** — Softens one-hot targets (e.g., `[0, 1, 0]` →
  `[0.033, 0.933, 0.033]`). Reduces overconfidence and improves calibration.
  *0.05–0.2.*
- **Gradient clip norm** — Caps gradient magnitude to prevent exploding
  gradients, especially important during Phase 2 unfreezing. *1.0 is standard.*

---

#### 4 — Data Augmentation
Artificially increases dataset diversity during training.

- **Mixup alpha** — Controls the Beta distribution used to blend pairs of
  training images. Higher α = stronger blending. *0 disables mixup; 0.1–0.4
  is typical for emotion data.*
- **Mixup probability** — Chance that a given batch uses mixup. *0.3–0.5.*

---

#### 5 — Training Configuration
Core loop settings.

- **Batch size** — Samples per gradient update. Larger batches train faster
  but need more VRAM and produce less gradient noise. *16–64.*
- **Number of epochs** — Total passes through the dataset. With early
  stopping, the actual run often finishes sooner. *15–50.*
- **Mixed precision (FP16)** — Uses half-precision floats for forward/backward
  passes with a GradScaler. Cuts VRAM usage ~40 % and speeds training.
  *Recommended ON for NVIDIA GPUs.*

---

#### 6 — Early Stopping
Halts training when the validation metric plateaus, preventing overfitting.

- **Enabled** — Toggle early stopping on/off.
- **Patience** — Epochs without improvement before stopping. *5–15.*
- **Min delta** — Minimum improvement to count as progress. *0.001.*
- **Monitor metric** — Metric to watch (default: `val_f1_macro`).

---

#### 7 — Class Balance
Handles the reality that emotion datasets are almost always imbalanced.

- **Use class weights** — Weight loss by inverse class frequency so the
  model doesn't ignore rare classes.
- **Class weight power** — Dampening exponent: 1.0 = full inverse frequency,
  0.5 = square-root dampening (less aggressive). *0.5 is a safe default.*

---

#### 8 — Input & Frame Sampling
How video frames are selected and sized before entering the model.

- **Input resolution** — Pixel size of each frame fed to EfficientNet-B0.
  Higher resolution captures subtle micro-expressions (tear ducts, lip
  corners) but uses more VRAM. *224 is standard; 260 is the EfficientNet-B0
  compound-scaled resolution.*
- **Frame sampling** — Strategy for picking frames from each video:
  - *middle* — Single center frame (fast, deterministic).
  - *random* — Random frame each epoch (natural augmentation).
  - *multi* — Multiple frames per video (set count below).
- **Frames per video** — Number of frames extracted per video when using
  *multi* sampling. More frames = more data but slower epochs. *1–10.*

---

#### 9 — Post-Inference Smoothing (Preview)
This parameter applies *after* model inference during deployment, not during
training. It is shown here for experiment planning.

- **Smoothing window (K)** — Size of the sliding median/box filter applied
  to frame-level predictions when running on video streams. A larger window
  (50–100 frames ≈ 2–4 s at 25 fps) produces stable "mood" output by
  filtering frame-to-frame jitter. *Tune on validation video after training.*

---

#### 10 — Reproducibility
- **Seed** — Random seed for PyTorch, NumPy, and CUDA. Ensures identical
  results across runs with the same data and config.
        """
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Run Identity
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Run Configuration")

if "ft_run_id" not in st.session_state:
    st.session_state["ft_run_id"] = ""

id_col1, id_col2 = st.columns([3, 1])
with id_col1:
    ft_run_id = st.text_input(
        "Fine-Tune Run ID (auto-generated if empty)",
        key="ft_run_id",
        help="Leave blank to auto-generate the next run_xxxx ID.",
    )
with id_col2:
    st.write("")  # spacing
    st.write("")
    if st.button("Generate Run ID", use_container_width=True):
        st.session_state["ft_run_id"] = f"ft_{(uuid.uuid4().int % 10000):04d}"
        st.rerun()

ft_checkpoint = st.text_input(
    "Checkpoint path (for validate/test; defaults to best_model.pth)",
    value=DEFAULT_CHECKPOINT,
    key="ft_checkpoint",
)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# FINE-TUNING PARAMETERS
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Fine-Tuning Parameters")

# ─── 1. Backbone Freezing Strategy ────────────────────────────────────────
st.markdown("#### 1 — Backbone Freezing Strategy")
freeze_col1, freeze_col2 = st.columns(2)
with freeze_col1:
    freeze_backbone_epochs = st.slider(
        "Freeze backbone epochs",
        min_value=0,
        max_value=20,
        value=5,
        step=1,
        help=(
            "Number of epochs where the EfficientNet-B0 backbone is frozen and only "
            "the classification head trains. Preserves pre-trained facial features."
        ),
    )
with freeze_col2:
    unfreeze_layers = st.multiselect(
        "Layers to unfreeze (Phase 2)",
        options=EFFICIENTNET_BLOCKS,
        default=["blocks.5", "blocks.6", "conv_head"],
        help=(
            "Backbone layers unlocked after the frozen phase. Later blocks capture "
            "higher-level features and are safer to fine-tune."
        ),
    )

# ─── 2. Learning Rate & Schedule ──────────────────────────────────────────
st.markdown("#### 2 — Learning Rate & Schedule")
lr_col1, lr_col2, lr_col3, lr_col4 = st.columns(4)
with lr_col1:
    learning_rate = st.select_slider(
        "Learning rate",
        options=[1e-5, 3e-5, 5e-5, 1e-4, 2e-4, 3e-4, 5e-4, 1e-3],
        value=3e-4,
        format_func=lambda x: f"{x:.0e}",
        help="Peak learning rate after warmup. The backbone uses 1/10th of this in Phase 2.",
    )
with lr_col2:
    min_lr = st.select_slider(
        "Min learning rate",
        options=[1e-7, 5e-7, 1e-6, 5e-6, 1e-5],
        value=1e-6,
        format_func=lambda x: f"{x:.0e}",
        help="Floor for the LR scheduler decay.",
    )
with lr_col3:
    lr_scheduler = st.selectbox(
        "LR scheduler",
        options=["cosine", "plateau"],
        index=0,
        help="Cosine: smooth anneal with warm restarts. Plateau: reduce on validation stall.",
    )
with lr_col4:
    warmup_epochs = st.slider(
        "Warmup epochs",
        min_value=0,
        max_value=10,
        value=3,
        step=1,
        help="Linearly ramps LR from ~0 to target over this many epochs.",
    )

# ─── 3. Regularization ───────────────────────────────────────────────────
st.markdown("#### 3 — Regularization")
reg_col1, reg_col2, reg_col3, reg_col4 = st.columns(4)
with reg_col1:
    weight_decay = st.select_slider(
        "Weight decay",
        options=[0.0, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2],
        value=1e-4,
        format_func=lambda x: f"{x:.0e}" if x > 0 else "0",
        help="L2 regularization penalty. Keeps weight magnitudes small.",
    )
with reg_col2:
    dropout_rate = st.slider(
        "Dropout rate",
        min_value=0.0,
        max_value=0.7,
        value=0.3,
        step=0.05,
        help="Fraction of neurons randomly zeroed in the classification head during training.",
    )
with reg_col3:
    label_smoothing = st.slider(
        "Label smoothing",
        min_value=0.0,
        max_value=0.3,
        value=0.1,
        step=0.01,
        help="Softens one-hot targets. Reduces overconfidence and improves calibration (ECE).",
    )
with reg_col4:
    gradient_clip_norm = st.slider(
        "Gradient clip norm",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="Maximum gradient norm. Prevents exploding gradients, especially during Phase 2.",
    )

# ─── 4. Data Augmentation ────────────────────────────────────────────────
st.markdown("#### 4 — Data Augmentation")
aug_col1, aug_col2 = st.columns(2)
with aug_col1:
    mixup_alpha = st.slider(
        "Mixup alpha",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.05,
        help=(
            "Beta distribution parameter for blending image pairs. "
            "0 = disabled. 0.1–0.4 typical for emotion data."
        ),
    )
with aug_col2:
    mixup_probability = st.slider(
        "Mixup probability",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.05,
        help="Chance of applying mixup to a given batch.",
    )

# ─── 5. Training Configuration ───────────────────────────────────────────
st.markdown("#### 5 — Training Configuration")
train_col1, train_col2, train_col3 = st.columns(3)
with train_col1:
    batch_size = st.select_slider(
        "Batch size",
        options=[8, 16, 32, 64, 128],
        value=32,
        help="Samples per gradient step. Larger = faster but more VRAM.",
    )
with train_col2:
    num_epochs = st.slider(
        "Number of epochs",
        min_value=5,
        max_value=100,
        value=30,
        step=5,
        help="Maximum training passes. Early stopping may terminate sooner.",
    )
with train_col3:
    mixed_precision = st.toggle(
        "Mixed precision (FP16)",
        value=True,
        help="Half-precision training. Cuts VRAM ~40 % and speeds up training on NVIDIA GPUs.",
    )

# ─── 6. Early Stopping ───────────────────────────────────────────────────
st.markdown("#### 6 — Early Stopping")
es_col1, es_col2, es_col3, es_col4 = st.columns(4)
with es_col1:
    early_stopping_enabled = st.toggle(
        "Enabled",
        value=True,
        key="ft_early_stop",
        help="Halt training when validation metric stops improving.",
    )
with es_col2:
    patience = st.slider(
        "Patience",
        min_value=3,
        max_value=30,
        value=10,
        step=1,
        disabled=not early_stopping_enabled,
        help="Epochs without improvement before stopping.",
    )
with es_col3:
    min_delta = st.number_input(
        "Min delta",
        min_value=0.0,
        max_value=0.1,
        value=0.001,
        step=0.0005,
        format="%.4f",
        disabled=not early_stopping_enabled,
        help="Minimum improvement to count as progress.",
    )
with es_col4:
    monitor_metric = st.selectbox(
        "Monitor metric",
        options=["val_f1_macro", "val_loss", "val_balanced_accuracy"],
        index=0,
        disabled=not early_stopping_enabled,
        help="Metric to watch for early stopping.",
    )

# ─── 7. Class Balance ────────────────────────────────────────────────────
st.markdown("#### 7 — Class Balance")
cb_col1, cb_col2 = st.columns(2)
with cb_col1:
    use_class_weights = st.toggle(
        "Use class weights",
        value=True,
        key="ft_class_weights",
        help="Weight loss by inverse class frequency so rare emotions are not ignored.",
    )
with cb_col2:
    class_weight_power = st.slider(
        "Class weight power",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        disabled=not use_class_weights,
        help="Dampening exponent: 1.0 = full inverse, 0.5 = sqrt (less aggressive).",
    )

# ─── 8. Input & Frame Sampling ───────────────────────────────────────────
st.markdown("#### 8 — Input & Frame Sampling")
inp_col1, inp_col2, inp_col3 = st.columns(3)
with inp_col1:
    input_size = st.select_slider(
        "Input resolution",
        options=[128, 160, 192, 224, 260, 300],
        value=224,
        help=(
            "Pixel size of each frame. 224 is standard; 260 is the "
            "EfficientNet-B0 compound-scaled resolution."
        ),
    )
with inp_col2:
    frame_sampling = st.selectbox(
        "Frame sampling strategy",
        options=["middle", "random", "multi"],
        index=0,
        help="How frames are picked from each video: center, random, or multi-frame.",
    )
with inp_col3:
    frames_per_video = st.slider(
        "Frames per video",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        disabled=(frame_sampling != "multi"),
        help="Number of frames per video (only for 'multi' sampling).",
    )

# ─── 9. Post-Inference Smoothing (Preview) ───────────────────────────────
st.markdown("#### 9 — Post-Inference Smoothing *(preview — applies at deployment, not training)*")
smoothing_col1, smoothing_col2 = st.columns([2, 2])
with smoothing_col1:
    smoothing_window = st.slider(
        "Smoothing window K (frames)",
        min_value=1,
        max_value=150,
        value=75,
        step=5,
        help=(
            "Sliding median/box filter over frame-level predictions. "
            "50–100 frames ≈ 2–4 s at 25 fps. Tune on validation video after training."
        ),
    )
with smoothing_col2:
    st.caption(
        f"At 25 fps, K={smoothing_window} ≈ {smoothing_window / 25.0:.1f} s temporal window."
    )
    st.info(
        "This value is recorded in run metadata for later deployment configuration. "
        "It does **not** affect the training loop."
    )

# ─── 10. Reproducibility ─────────────────────────────────────────────────
st.markdown("#### 10 — Reproducibility")
seed_col1, seed_col2 = st.columns(2)
with seed_col1:
    seed = st.number_input(
        "Seed",
        min_value=0,
        max_value=2**31 - 1,
        value=42,
        step=1,
        help="Random seed for PyTorch, NumPy, and CUDA.",
    )
with seed_col2:
    deterministic = st.toggle(
        "Deterministic mode",
        value=True,
        key="ft_deterministic",
        help="Sets cuDNN to deterministic. Slightly slower but fully reproducible.",
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Build config overrides dict
# ─────────────────────────────────────────────────────────────────────────────


def _build_config_overrides() -> Dict[str, Any]:
    """Assemble a nested dict of config overrides from widget state."""
    return {
        "model": {
            "input_size": int(input_size),
            "dropout_rate": float(dropout_rate),
            "freeze_backbone_epochs": int(freeze_backbone_epochs),
            "unfreeze_layers": list(unfreeze_layers),
        },
        "data": {
            "batch_size": int(batch_size),
            "frame_sampling": frame_sampling,
            "frames_per_video": int(frames_per_video),
            "augmentation_enabled": True,
            "mixup_alpha": float(mixup_alpha),
            "mixup_probability": float(mixup_probability),
        },
        "num_epochs": int(num_epochs),
        "learning_rate": float(learning_rate),
        "weight_decay": float(weight_decay),
        "lr_scheduler": lr_scheduler,
        "warmup_epochs": int(warmup_epochs),
        "min_lr": float(min_lr),
        "label_smoothing": float(label_smoothing),
        "gradient_clip_norm": float(gradient_clip_norm),
        "use_class_weights": bool(use_class_weights),
        "class_weight_power": float(class_weight_power),
        "early_stopping_enabled": bool(early_stopping_enabled),
        "patience": int(patience),
        "min_delta": float(min_delta),
        "monitor_metric": monitor_metric,
        "mixed_precision": bool(mixed_precision),
        "seed": int(seed),
        "deterministic": bool(deterministic),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Config Preview
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("Preview Config Overrides (JSON)", expanded=False):
    overrides = _build_config_overrides()
    overrides_display = dict(overrides)
    overrides_display["_meta"] = {
        "smoothing_window_k": int(smoothing_window),
        "smoothing_window_sec": round(smoothing_window / 25.0, 2),
        "note": "smoothing_window applies at deployment, not training",
    }
    st.json(overrides_display)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Launch Actions
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Launch Fine-Tuning")
st.caption(
    "Variant 2 runs use the same EfficientNet-B0 backbone (`enet_b0_8_best_vgaf`) "
    "and Luma-augmented training data, with your fine-tuning overrides applied."
)


def _launch_ft_run(mode: str) -> None:
    """Launch a fine-tuning, validation, or test run via the backend."""
    try:
        if mode == "train":
            # Use dedicated /api/v1/training/finetune endpoint for Variant 2 training
            overrides = _build_config_overrides()
            resp = api_client.launch_variant2_finetune(
                checkpoint_path=ft_checkpoint,
                run_id=ft_run_id or None,
                epochs=overrides.get("num_epochs", 30),
                freeze_epochs=overrides.get("freeze_epochs", 5),
                unfreeze_layers=overrides.get("unfreeze_layers", ["blocks.5", "blocks.6", "conv_head"]),
                learning_rate=overrides.get("learning_rate", 3e-4),
            )
        else:
            # Use generic /api/v1/training/launch for validate/test modes
            resp = api_client.launch_finetune_run(
                mode=mode,
                run_id=ft_run_id or None,
                variant="variant_2",
                checkpoint=ft_checkpoint or None,
                test_data_dir=AFFECTNET_TEST_DIR if mode == "test" else None,
            )
        st.success(f"{mode.capitalize()} run launched: {resp.get('run_id', 'unknown')}")
        st.json(resp)
    except Exception as exc:  # noqa: BLE001
        if "422" in str(exc) and "checkpoint" in str(exc).lower():
            st.error(
                "No checkpoint found. Run a fine-tuning job first, or provide "
                "an explicit checkpoint path above."
            )
        elif "404" in str(exc):
            st.error(
                "Training launch endpoint not found. Restart the Media Mover API "
                "with the latest code, then retry."
            )
        else:
            st.error(f"{mode.capitalize()} run failed to launch: {exc}")


ft_col1, ft_col2, ft_col3 = st.columns(3)
with ft_col1:
    st.markdown("**Fine-Tuning Run**")
    st.caption("Full pipeline: fine-tune → evaluate → Gate A")
    if st.button(
        "Start Fine-Tuning",
        use_container_width=True,
        type="primary",
        key="btn_ft_train",
    ):
        _launch_ft_run("train")

with ft_col2:
    st.markdown("**Validation Run**")
    st.caption("Evaluate checkpoint on validation split")
    if st.button(
        "Start Validation",
        use_container_width=True,
        key="btn_ft_validate",
    ):
        _launch_ft_run("validate")

with ft_col3:
    st.markdown("**Test Run (AffectNet)**")
    st.caption(f"Evaluate on `{AFFECTNET_TEST_DIR}`")
    if st.button(
        "Start Test Run",
        use_container_width=True,
        key="btn_ft_test",
    ):
        _launch_ft_run("test")


st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Training Status
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Fine-Tuning Status")


def _render_status_panel(title: str, payload: Dict[str, Any]) -> None:
    st.markdown(f"**{title}**")
    run_status = str(payload.get("status") or "unknown").lower()
    metrics = _as_dict(payload.get("metrics"))
    error_message = payload.get("error_message")
    blocked_reason = metrics.get("blocked_reason")

    if run_status == "blocked":
        st.warning(f"Blocked: {blocked_reason or 'pipeline gate not satisfied'}")
    elif run_status in {"completed", "completed_gate_passed", "completed_gate_failed"}:
        st.success(f"Completed ({run_status})")
    elif run_status in {"training", "evaluating", "pending", "sampling", "running"}:
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
                f"(happy={counts.get('happy', 0)}, sad={counts.get('sad', 0)}, "
                f"neutral={counts.get('neutral', 0)})"
            )
        if min_required is not None:
            st.caption(f"Minimum required per class: {min_required}")

    if error_message:
        st.caption(f"Error: {error_message}")

    st.json(payload)


pipeline_id = st.text_input("Pipeline / Run ID", value=ft_run_id, key="ft_status_id")
if st.button("Refresh Status", key="btn_ft_status"):
    try:
        run_payload = _as_dict(api_client.get_training_status(pipeline_id))
        latest_payload = _as_dict(api_client.get_training_status("latest"))
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            _render_status_panel(f"Run: {pipeline_id}", run_payload)
        with status_col2:
            _render_status_panel("Latest Snapshot", latest_payload)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Status fetch failed: {exc}")
