from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Dashboard", layout="wide")
render_navigation_bar()
st.title("06 - Dashboard")
st.caption("Run-level results dashboard (training, validation, test).")


TRAINING_RESULTS_PLACEHOLDER = {
    "run_type": "training",
    "run_id": "run_0001",
    "gate_a_metrics": {
        "accuracy": 1.0,
        "precision_macro": 1.0,
        "recall_macro": 1.0,
        "f1_macro": 1.0,
        "balanced_accuracy": 1.0,
        "f1_class_0": 1.0,
        "f1_happy": 1.0,
        "f1_class_1": 1.0,
        "f1_sad": 1.0,
        "f1_class_2": 1.0,
        "f1_neutral": 1.0,
        "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "ece": 0.48958078026771545,
        "brier": 0.3802821991121825,
        "mce": 0.5812406241893768,
    },
    "gate_a_gates": {
        "macro_f1": True,
        "balanced_accuracy": True,
        "per_class_f1": False,
        "ece": False,
        "brier": False,
    },
}

VALIDATION_RESULTS_PLACEHOLDER = {
    "run_type": "validation",
    "run_id": "run_0002",
    "gate_a_metrics": {
        "accuracy": 0.9375,
        "precision_macro": 0.9401,
        "recall_macro": 0.9350,
        "f1_macro": 0.9369,
        "balanced_accuracy": 0.9350,
        "f1_class_0": 0.9412,
        "f1_happy": 0.9412,
        "f1_class_1": 0.9326,
        "f1_sad": 0.9326,
        "f1_class_2": 0.9300,
        "f1_neutral": 0.9300,
        "confusion_matrix": [[30, 1, 2], [1, 31, 1], [2, 1, 27]],
        "ece": 0.061200000000000004,
        "brier": 0.0843,
        "mce": 0.1178,
    },
    "gate_a_gates": {
        "macro_f1": True,
        "balanced_accuracy": True,
        "per_class_f1": True,
        "ece": True,
        "brier": True,
    },
}

TEST_RESULTS_PLACEHOLDER = {
    "run_type": "test",
    "run_id": "run_0003",
    "gate_a_metrics": {
        "accuracy": 0.9023,
        "precision_macro": 0.9054,
        "recall_macro": 0.8998,
        "f1_macro": 0.9017,
        "balanced_accuracy": 0.8998,
        "f1_class_0": 0.9070,
        "f1_happy": 0.9070,
        "f1_class_1": 0.8963,
        "f1_sad": 0.8963,
        "f1_class_2": 0.8940,
        "f1_neutral": 0.8940,
        "confusion_matrix": [[38, 3, 2], [2, 37, 4], [3, 3, 36]],
        "ece": 0.0894,
        "brier": 0.1299,
        "mce": 0.1731,
    },
    "gate_a_gates": {
        "macro_f1": True,
        "balanced_accuracy": True,
        "per_class_f1": False,
        "ece": False,
        "brier": False,
    },
}

# Variant-specific placeholders for dashboard run-type selection.
VARIANT_1_TRAINING_RESULTS = {
    **TRAINING_RESULTS_PLACEHOLDER,
    "model_variant": "variant_1",
}
VARIANT_1_VALIDATION_RESULTS = {
    **VALIDATION_RESULTS_PLACEHOLDER,
    "model_variant": "variant_1",
}
VARIANT_1_TEST_RESULTS = {
    **TEST_RESULTS_PLACEHOLDER,
    "model_variant": "variant_1",
}

VARIANT_2_TRAINING_RESULTS = {
    **TRAINING_RESULTS_PLACEHOLDER,
    "run_id": "v2_run_0001",
    "model_variant": "variant_2",
}
VARIANT_2_VALIDATION_RESULTS = {
    **VALIDATION_RESULTS_PLACEHOLDER,
    "run_id": "v2_run_0002",
    "model_variant": "variant_2",
}
VARIANT_2_TEST_RESULTS = {
    **TEST_RESULTS_PLACEHOLDER,
    "run_id": "v2_run_0003",
    "model_variant": "variant_2",
}

INTERPRETATION_DIR = Path(__file__).resolve().parents[3] / "stats" / "interpretations"
DASHBOARD_RESULTS_ROOT = Path(__file__).resolve().parents[3] / "stats" / "results" / "runs"
INTERPRETATION_FILE_MAP = {
    "Accuracy": "accuracy.md",
    "Precision (Macro)": "precision.md",
    "Recall (Macro)": "recall.md",
    "F1 (Macro)": "macro_f1.md",
    "Balanced Accuracy": "balanced_accuracy.md",
    "F1 (per Class)": "per_class_f1.md",
    "ECE": "ece.md",
    "Brier": "brier.md",
    "MCE": "mce.md",
}
MOST_USEFUL_METRICS = {
    "F1 (Macro)",
    "Balanced Accuracy",
    "F1 (per Class)",
}

GATE_LABEL_MAP = {
    "macro_f1": "F1 (Macro)",
    "balanced_accuracy": "Balanced Accuracy",
    "per_class_f1": "F1 (per Class)",
    "ece": "ECE",
    "brier": "Brier",
    "mce": "MCE",
}


def _render_gate_flags(gates: dict[str, bool]) -> None:
    st.markdown("**Gate A Checks**")
    for gate_name, passed in gates.items():
        display_name = GATE_LABEL_MAP.get(gate_name, gate_name)
        if passed:
            st.success(f"{display_name}: pass")
        else:
            st.error(f"{display_name}: fail")


def _render_confusion_matrix_rows(matrix: list[list[int]]) -> None:
    st.markdown("**Confusion Matrix (Rows)**")
    if not matrix:
        st.info("No confusion matrix available.")
        return
    for idx, row in enumerate(matrix):
        st.write(f"Row {idx}: {row}")


def _render_confusion_matrix_template(matrix: list[list[int]]) -> None:
    st.markdown("**Confusion Matrix (TP/FP/FN/TN Template)**")
    if not matrix:
        st.info("No confusion matrix available.")
        return
    if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        st.warning("Template view supports 2x2 matrices only. Showing row view instead.")
        _render_confusion_matrix_rows(matrix)
        return

    tp = matrix[0][0]
    fp = matrix[0][1]
    fn = matrix[1][0]
    tn = matrix[1][1]

    st.markdown(
        f"""
<div style="border:1px solid #444;padding:12px;border-radius:8px;">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
    <div style="border:2px solid #45c3ad;padding:10px;border-radius:6px;">
      <strong>TRUE POSITIVE</strong><br/>Value: {tp}
    </div>
    <div style="border:2px solid #e85d4a;padding:10px;border-radius:6px;">
      <strong>FALSE POSITIVE</strong><br/>Value: {fp}
    </div>
    <div style="border:2px solid #e85d4a;padding:10px;border-radius:6px;">
      <strong>FALSE NEGATIVE</strong><br/>Value: {fn}
    </div>
    <div style="border:2px solid #45c3ad;padding:10px;border-radius:6px;">
      <strong>TRUE NEGATIVE</strong><br/>Value: {tn}
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_confusion_matrix_heatmap(matrix: list[list[int]]) -> None:
    st.markdown("**Confusion Matrix (Heat Map)**")
    if not matrix:
        st.info("No confusion matrix available.")
        return
    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Matplotlib/Numpy not available for heat map rendering: {exc}")
        _render_confusion_matrix_rows(matrix)
        return

    cm = np.asarray(matrix, dtype=float)
    if cm.ndim != 2 or cm.shape[0] == 0 or cm.shape[1] == 0:
        st.warning("Invalid confusion matrix shape.")
        _render_confusion_matrix_rows(matrix)
        return

    n_rows, n_cols = cm.shape
    labels_x = [str(i) for i in range(n_cols)]
    labels_y = [str(i) for i in range(n_rows)]

    # Preferred path: sklearn display for robust axis + colorbar layout.
    used_sklearn = False
    try:
        from sklearn.metrics import ConfusionMatrixDisplay

        fig, ax = plt.subplots(figsize=(6.2, 5.2))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels_x)
        disp.plot(ax=ax, cmap="viridis", colorbar=True, values_format="g")
        ax.set_xlabel("Predicted label", labelpad=10)
        ax.set_ylabel("True label", labelpad=10)
        ax.set_xticklabels(labels_x)
        ax.set_yticklabels(labels_y)
        used_sklearn = True

        # Improve text contrast against cell color.
        max_val = float(cm.max()) if float(cm.max()) > 0 else 1.0
        threshold = max_val * 0.5
        for i in range(n_rows):
            for j in range(n_cols):
                if disp.text_[i, j] is not None:
                    disp.text_[i, j].set_color("white" if cm[i, j] < threshold else "#202020")
                    disp.text_[i, j].set_fontweight("bold")
    except Exception:
        # Fallback if sklearn isn't installed.
        fig, ax = plt.subplots(figsize=(6.2, 5.2))
        im = ax.imshow(cm, cmap="viridis", aspect="equal")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=10)

        max_val = float(cm.max()) if float(cm.max()) > 0 else 1.0
        threshold = max_val * 0.5
        for i in range(n_rows):
            for j in range(n_cols):
                val = int(cm[i, j]) if float(cm[i, j]).is_integer() else float(cm[i, j])
                ax.text(
                    j,
                    i,
                    f"{val}",
                    ha="center",
                    va="center",
                    color="white" if cm[i, j] < threshold else "#202020",
                    fontweight="bold",
                )

        ax.set_xticks(np.arange(n_cols))
        ax.set_yticks(np.arange(n_rows))
        ax.set_xticklabels(labels_x)
        ax.set_yticklabels(labels_y)
        ax.set_xlabel("Predicted label", labelpad=10)
        ax.set_ylabel("True label", labelpad=10)
        ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1)
        ax.tick_params(which="minor", bottom=False, left=False)

    fig.tight_layout()
    st.pyplot(fig, clear_figure=True, use_container_width=False)
    if used_sklearn:
        st.caption("Heat map rendered with scikit-learn ConfusionMatrixDisplay.")


def _render_confusion_matrix(matrix: list[list[int]]) -> None:
    view = st.selectbox(
        "Confusion Matrix View",
        options=["Rows", "Heat Map"],
        index=1,
        key="dashboard_confusion_view",
    )
    if view == "Rows":
        _render_confusion_matrix_rows(matrix)
    else:
        _render_confusion_matrix_heatmap(matrix)


def _read_interpretation(metric_name: str) -> str:
    file_name = INTERPRETATION_FILE_MAP.get(metric_name)
    if not file_name:
        return f"No interpretation mapping found for '{metric_name}'."
    file_path = INTERPRETATION_DIR / file_name
    if not file_path.exists():
        return f"Interpretation file not found: {file_path}"
    return file_path.read_text(encoding="utf-8").strip() or "(empty interpretation file)"


def _render_statistical_interpretations() -> None:
    st.markdown("**Statistical Interpretations**")
    metric_names = list(INTERPRETATION_FILE_MAP.keys())
    display_options = [
        f"🟢 {name}" if name in MOST_USEFUL_METRICS else name
        for name in metric_names
    ]
    display_to_metric = dict(zip(display_options, metric_names))
    selected_display = st.selectbox(
        "Select Statistic",
        options=display_options,
        index=display_options.index("🟢 F1 (Macro)") if "🟢 F1 (Macro)" in display_options else 0,
        key="dashboard_stat_interpretation_metric",
    )
    metric_name = display_to_metric[selected_display]
    interpretation_text = _read_interpretation(metric_name)
    st.text_area(
        "Interpretation",
        value=interpretation_text,
        height=250,
        disabled=True,
    )
    st.caption("🟢 indicates highest-priority metrics for model selection.")


def _render_run_dashboard(payload: dict, title: str) -> None:
    metrics = payload.get("gate_a_metrics", {})
    gates = payload.get("gate_a_gates", {})

    st.subheader(title)
    variant_label = payload.get("model_variant", "unknown")
    st.write(f"Run ID: `{payload.get('run_id', 'unknown')}` — Model Variant: `{variant_label}`")

    def _safe_float(val: object) -> float:
        try:
            return float(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    top_cols = st.columns(5)
    top_cols[0].metric("Accuracy", f"{_safe_float(metrics.get('accuracy')):.4f}")
    top_cols[1].metric("Precision (Macro)", f"{_safe_float(metrics.get('precision_macro')):.4f}")
    top_cols[2].metric("Recall (Macro)", f"{_safe_float(metrics.get('recall_macro')):.4f}")
    top_cols[3].metric("F1 (Macro)", f"{_safe_float(metrics.get('f1_macro')):.4f}")
    top_cols[4].metric("Balanced Accuracy", f"{_safe_float(metrics.get('balanced_accuracy')):.4f}")

    cal_cols = st.columns(3)
    cal_cols[0].metric("ECE", f"{_safe_float(metrics.get('ece')):.6f}")
    cal_cols[1].metric("Brier", f"{_safe_float(metrics.get('brier')):.6f}")
    cal_cols[2].metric("MCE", f"{_safe_float(metrics.get('mce')):.6f}")

    detail_cols = st.columns(2)
    with detail_cols[0]:
        _render_confusion_matrix(metrics.get("confusion_matrix", []))
    with detail_cols[1]:
        _render_gate_flags(gates)
        _render_statistical_interpretations()

    st.markdown("**Raw Payload**")
    st.json(payload)


RUN_TYPE_MAP: dict[str, str] = {
    "Training Run": "train",
    "Validation Run": "validate",
    "Test Run": "test",
    "Base Model Test Run": "base_model_test",
}

_RUN_TYPE_FALLBACK: dict[str, dict] = {
    "train": TRAINING_RESULTS_PLACEHOLDER,
    "validate": VALIDATION_RESULTS_PLACEHOLDER,
    "test": TEST_RESULTS_PLACEHOLDER,
    "base_model_test": TEST_RESULTS_PLACEHOLDER,
}


def _run_result_path(run_type_dir: str, run_id: str) -> Path:
    return DASHBOARD_RESULTS_ROOT / run_type_dir / f"{run_id}.json"


def _load_dashboard_payload(run_type_label: str, run_id: str) -> tuple[dict, Path | None]:
    run_type_dir = RUN_TYPE_MAP[run_type_label]
    fallback_payload = dict(_RUN_TYPE_FALLBACK.get(run_type_dir, TRAINING_RESULTS_PLACEHOLDER))
    fallback_payload.setdefault("model_variant", "unknown")
    fallback_payload["run_type"] = run_type_dir
    fallback_payload["run_id"] = run_id or "—"

    if not run_id:
        return fallback_payload, None

    result_path = _run_result_path(run_type_dir, run_id)
    if not result_path.exists():
        return fallback_payload, None

    try:
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Failed to parse result file at `{result_path}`: {exc}. Using fallback payload.")
        return fallback_payload, None

    if not isinstance(loaded, dict):
        st.warning(f"Invalid payload in `{result_path}` (expected JSON object). Using fallback payload.")
        return fallback_payload, None

    loaded.setdefault("model_variant", "unknown")
    loaded.setdefault("run_type", run_type_dir)
    loaded.setdefault("run_id", result_path.stem)
    return loaded, result_path


sel_col, id_col = st.columns([2, 3])
with sel_col:
    run_type_label = st.selectbox(
        "Run Type",
        options=list(RUN_TYPE_MAP.keys()),
        index=0,
        key="dashboard_run_type",
    )
with id_col:
    run_id_input = st.text_input(
        "Run ID",
        value="",
        placeholder="e.g. run_0042",
        key="dashboard_run_id",
    )

selected_payload, selected_path = _load_dashboard_payload(run_type_label, run_id_input.strip())
selected_title = f"{run_type_label} Results"
if selected_path is not None:
    st.caption(f"Loaded from `{selected_path}`")
elif run_id_input.strip():
    st.warning(
        f"No result file found for run ID `{run_id_input.strip()}` "
        f"under `stats/results/runs/{RUN_TYPE_MAP[run_type_label]}/`. "
        "Showing fallback placeholder data."
    )
else:
    st.info(
        f"Enter a Run ID above to load saved results. "
        f"Files are stored as `stats/results/runs/{RUN_TYPE_MAP[run_type_label]}/<run_id>.json`."
    )

_render_run_dashboard(selected_payload, selected_title)
