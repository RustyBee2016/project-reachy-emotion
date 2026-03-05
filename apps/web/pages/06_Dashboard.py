from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Dashboard", layout="wide")
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
        "confusion_matrix": [[1, 0], [0, 2]],
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


def _render_gate_flags(gates: dict[str, bool]) -> None:
    st.markdown("**Gate A Checks**")
    for gate_name, passed in gates.items():
        if passed:
            st.success(f"{gate_name}: pass")
        else:
            st.error(f"{gate_name}: fail")


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
        options=["Rows", "TP/FP/FN/TN Template", "Heat Map"],
        index=2,
        key="dashboard_confusion_view",
    )
    if view == "Rows":
        _render_confusion_matrix_rows(matrix)
    elif view == "TP/FP/FN/TN Template":
        _render_confusion_matrix_template(matrix)
    else:
        _render_confusion_matrix_heatmap(matrix)


def _render_training_dashboard(payload: dict) -> None:
    metrics = payload.get("gate_a_metrics", {})
    gates = payload.get("gate_a_gates", {})

    st.subheader("Training Run Results")
    st.write(f"Run ID: `{payload.get('run_id', 'unknown')}`")

    top_cols = st.columns(5)
    top_cols[0].metric("Accuracy", f"{float(metrics.get('accuracy', 0.0)):.4f}")
    top_cols[1].metric("Precision (Macro)", f"{float(metrics.get('precision_macro', 0.0)):.4f}")
    top_cols[2].metric("Recall (Macro)", f"{float(metrics.get('recall_macro', 0.0)):.4f}")
    top_cols[3].metric("F1 (Macro)", f"{float(metrics.get('f1_macro', 0.0)):.4f}")
    top_cols[4].metric("Balanced Accuracy", f"{float(metrics.get('balanced_accuracy', 0.0)):.4f}")

    cal_cols = st.columns(3)
    cal_cols[0].metric("ECE", f"{float(metrics.get('ece', 0.0)):.6f}")
    cal_cols[1].metric("Brier", f"{float(metrics.get('brier', 0.0)):.6f}")
    cal_cols[2].metric("MCE", f"{float(metrics.get('mce', 0.0)):.6f}")

    detail_cols = st.columns(2)
    with detail_cols[0]:
        _render_confusion_matrix(metrics.get("confusion_matrix", []))
    with detail_cols[1]:
        _render_gate_flags(gates)

    st.markdown("**Raw Payload**")
    st.json(payload)


run_type = st.selectbox(
    "Select Run Type",
    options=["Training Run", "Validation Run", "Test Run"],
    index=0,
)

if run_type == "Training Run":
    _render_training_dashboard(TRAINING_RESULTS_PLACEHOLDER)
elif run_type == "Validation Run":
    st.info("Validation dashboard view is not implemented yet.")
else:
    st.info("Test dashboard view is not implemented yet.")
