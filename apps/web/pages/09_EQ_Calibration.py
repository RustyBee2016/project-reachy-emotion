"""
EQ Calibration Dashboard — Phase 2 Emotional Intelligence Layer

Displays:
- Latest run ECE / Brier / MCE vs Gate A thresholds
- Calibration trend charts across training runs (from MLflow)
- Confidence degree distribution histogram (from obs_samples)
- Expressiveness tier breakdown
- LLM service health status
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import streamlit as st

from apps.web import api_client
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="EQ Calibration", layout="wide")
render_navigation_bar()
st.title("09 — EQ Calibration Dashboard")
st.caption("Phase 2: Emotional Intelligence Layer — calibration, confidence degree, and LLM health")

GATE_A_ECE = 0.08
GATE_A_BRIER = 0.16

EXPRESSIVENESS_COLORS = {
    "full": "#2ecc71",
    "moderate": "#3498db",
    "subtle": "#f39c12",
    "minimal": "#e67e22",
    "abstain": "#e74c3c",
}


def _color_metric(value: float, threshold: float, lower_is_better: bool = True) -> str:
    """Return 'normal', 'inverse', or emoji indicator for a metric."""
    if lower_is_better:
        return "✅" if value <= threshold else "❌"
    return "✅" if value >= threshold else "❌"


def _load_mlflow_runs() -> List[Dict[str, Any]]:
    """
    Load recent training runs from MLflow tracking store.

    Reads the local MLflow file store directly to avoid requiring
    the MLflow server to be running.
    """
    mlflow_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "file:///media/rusty_admin/project_data/reachy_emotion/mlruns",
    )
    runs: List[Dict[str, Any]] = []

    if not mlflow_uri.startswith("file://"):
        return runs

    mlruns_path = mlflow_uri.replace("file://", "")
    if not os.path.isdir(mlruns_path):
        return runs

    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        mlflow.set_tracking_uri(mlflow_uri)
        client = MlflowClient()
        experiments = client.search_experiments()

        for exp in experiments:
            exp_runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                order_by=["start_time DESC"],
                max_results=20,
            )
            for run in exp_runs:
                m = run.data.metrics
                p = run.data.params
                runs.append({
                    "run_id": run.info.run_id[:8],
                    "experiment": exp.name,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "ece": m.get("ece"),
                    "brier": m.get("brier"),
                    "mce": m.get("mce"),
                    "f1_macro": m.get("f1_macro"),
                    "balanced_accuracy": m.get("balanced_accuracy"),
                    "dataset_hash": p.get("dataset_hash", "—"),
                })
    except Exception as exc:
        st.warning(f"MLflow load error: {exc}")

    return runs


def _render_gate_a_panel(runs: List[Dict[str, Any]]) -> None:
    st.subheader("Gate A — Latest Calibration Status")

    calibrated_runs = [r for r in runs if r.get("ece") is not None]
    if not calibrated_runs:
        st.info("No runs with calibration metrics found in MLflow store.")
        return

    latest = calibrated_runs[0]
    ece = latest["ece"]
    brier = latest["brier"]
    mce = latest.get("mce")
    f1 = latest.get("f1_macro")
    bal_acc = latest.get("balanced_accuracy")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        gate = _color_metric(ece, GATE_A_ECE)
        st.metric(
            label=f"ECE {gate}",
            value=f"{ece:.4f}",
            delta=f"threshold ≤ {GATE_A_ECE}",
            delta_color="inverse",
        )
    with col2:
        gate = _color_metric(brier, GATE_A_BRIER)
        st.metric(
            label=f"Brier {gate}",
            value=f"{brier:.4f}",
            delta=f"threshold ≤ {GATE_A_BRIER}",
            delta_color="inverse",
        )
    with col3:
        st.metric(
            label="MCE",
            value=f"{mce:.4f}" if mce is not None else "—",
        )
    with col4:
        gate = _color_metric(f1 or 0.0, 0.84, lower_is_better=False)
        st.metric(
            label=f"F1 Macro {gate}",
            value=f"{f1:.4f}" if f1 is not None else "—",
            delta="threshold ≥ 0.84",
        )
    with col5:
        gate = _color_metric(bal_acc or 0.0, 0.85, lower_is_better=False)
        st.metric(
            label=f"Balanced Acc {gate}",
            value=f"{bal_acc:.4f}" if bal_acc is not None else "—",
            delta="threshold ≥ 0.85",
        )

    overall_pass = (
        ece <= GATE_A_ECE
        and brier <= GATE_A_BRIER
        and (f1 or 0.0) >= 0.84
        and (bal_acc or 0.0) >= 0.85
    )
    if overall_pass:
        st.success(f"Gate A PASSED — run `{latest['run_id']}` ({latest['experiment']})")
    else:
        st.error(f"Gate A FAILED — run `{latest['run_id']}` ({latest['experiment']})")


def _render_calibration_trend(runs: List[Dict[str, Any]]) -> None:
    st.subheader("Calibration Trend — All Runs")

    calibrated = [r for r in runs if r.get("ece") is not None]
    if len(calibrated) < 2:
        st.info("At least 2 calibrated runs needed to show trend.")
        return

    try:
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "run": r["run_id"],
                    "ECE": r["ece"],
                    "Brier": r["brier"],
                    "MCE": r.get("mce"),
                    "F1 Macro": r.get("f1_macro"),
                }
                for r in reversed(calibrated)
            ]
        ).set_index("run")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Calibration Errors (lower is better)**")
            st.line_chart(df[["ECE", "Brier", "MCE"]].dropna(axis=1))
            st.markdown(
                f"<small>Gate A limits — ECE: {GATE_A_ECE} | Brier: {GATE_A_BRIER}</small>",
                unsafe_allow_html=True,
            )
        with col_right:
            st.markdown("**Classification Quality (higher is better)**")
            st.line_chart(df[["F1 Macro"]].dropna(axis=1))

        with st.expander("Raw run data"):
            st.dataframe(df.reset_index())
    except ImportError:
        st.warning("pandas not available — install to see trend charts.")


def _render_confidence_distribution() -> None:
    st.subheader("Confidence Degree Distribution")
    st.caption("Runtime confidence scores logged by the pipeline (obs_samples table)")

    try:
        data = api_client.get_obs_samples(limit=1000)
        samples = data.get("samples", [])
    except Exception as exc:
        st.warning(f"Could not load obs_samples (API offline?): {exc}")
        samples = []

    if not samples:
        st.info(
            "No runtime confidence samples available yet. "
            "Samples are logged when the emotion pipeline is running."
        )
        return

    try:
        import pandas as pd

        df = pd.DataFrame(samples)
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Confidence Score Histogram**")
            if "confidence" in df.columns:
                st.bar_chart(
                    df["confidence"]
                    .dropna()
                    .pipe(lambda s: s.value_counts(bins=10, sort=False))
                )

        with col_right:
            st.markdown("**Expressiveness Tier Breakdown**")
            if "expressiveness_level" in df.columns:
                tier_counts = df["expressiveness_level"].value_counts()
                st.bar_chart(tier_counts)

        if "emotion" in df.columns:
            st.markdown("**Sample Count by Emotion**")
            emotion_counts = df["emotion"].value_counts()
            cols = st.columns(len(emotion_counts))
            for col, (emotion, count) in zip(cols, emotion_counts.items()):
                col.metric(str(emotion).capitalize(), count)

    except ImportError:
        st.warning("pandas not available for distribution charts.")


def _render_llm_health() -> None:
    st.subheader("LLM Service Health")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Check LLM Health"):
            with st.spinner("Probing LLM endpoint..."):
                try:
                    health = api_client.get_llm_health()
                    status = health.get("status", "unknown")
                    model = health.get("model", "—")
                    latency = health.get("latency_ms", 0.0)
                    if status == "ok":
                        st.success(f"LLM OK — model: `{model}` | latency: {latency:.0f}ms")
                    else:
                        st.warning(f"LLM status: `{status}` — {health}")
                except Exception as exc:
                    st.error(f"LLM health check failed: {exc}")

    with col2:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        st.markdown(
            f"**Configured endpoint:** `{base_url}`  \n"
            f"**Model:** `{model}`  \n"
            f"Set `OPENAI_BASE_URL=http://localhost:1234/v1` for LM Studio."
        )


def _render_taxonomy_reference() -> None:
    st.subheader("PPE / Ekman Taxonomy Reference")

    try:
        from shared.taxonomy.ekman_taxonomy import EKMAN_BEHAVIOR_MAP

        try:
            import pandas as pd

            rows = []
            for emotion, profile in EKMAN_BEHAVIOR_MAP.items():
                rows.append(
                    {
                        "Emotion": emotion.capitalize(),
                        "Strategy": profile.response_strategy,
                        "Gesture Tier": profile.gesture_expressiveness_hint,
                        "De-escalate": "✅" if profile.de_escalate else "—",
                        "Validate First": "✅" if profile.validate_first else "—",
                        "Intensity": profile.intensity_label,
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
        except ImportError:
            for emotion, profile in EKMAN_BEHAVIOR_MAP.items():
                st.markdown(
                    f"**{emotion.capitalize()}** — {profile.response_strategy} "
                    f"| tier: {profile.gesture_expressiveness_hint}"
                )
    except ImportError as exc:
        st.warning(f"Taxonomy module not available: {exc}")


runs = _load_mlflow_runs()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Gate A Status", "Calibration Trend", "Runtime Confidence", "Taxonomy Reference"]
)

with tab1:
    _render_gate_a_panel(runs)
    st.divider()
    _render_llm_health()

with tab2:
    _render_calibration_trend(runs)

with tab3:
    _render_confidence_distribution()

with tab4:
    _render_taxonomy_reference()
