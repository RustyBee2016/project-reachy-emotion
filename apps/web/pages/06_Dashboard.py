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


def _render_confusion_matrix(matrix: list[list[int]]) -> None:
    st.markdown("**Confusion Matrix**")
    if not matrix:
        st.info("No confusion matrix available.")
        return
    for idx, row in enumerate(matrix):
        st.write(f"Row {idx}: {row}")


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
