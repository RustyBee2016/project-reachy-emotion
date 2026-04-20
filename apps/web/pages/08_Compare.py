from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Compare — Deployment Decision", layout="wide")
render_navigation_bar()
st.title("08 - Compare: Deployment Decision")
st.caption(
    "Head-to-head comparison of Variant 1 vs Variant 2 on real-world test data. "
    "The best-performing variant is recommended for deployment."
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DASHBOARD_RESULTS_ROOT = (
    Path(__file__).resolve().parents[3] / "stats" / "results" / "runs"
)

_VARIANT_PREFIX: Dict[str, str] = {
    "variant_1": "var1_test_",
    "variant_2": "var2_test_",
}

# Gate A-deploy thresholds (real-world tier, per ADR 011).
GATE_A_DEPLOY_THRESHOLDS: Dict[str, Tuple[str, float]] = {
    "f1_macro": (">=", 0.75),
    "balanced_accuracy": (">=", 0.75),
    "per_class_f1": (">=", 0.70),
    "ece": ("<=", 0.12),
}

KEY_METRICS = ["f1_macro", "balanced_accuracy"]
KEY_CALIBRATION = ["ece", "brier"]
KEY_PER_CLASS = ["f1_happy", "f1_sad", "f1_neutral"]

METRIC_DISPLAY = {
    "f1_macro": "F1 (Macro)",
    "balanced_accuracy": "Balanced Accuracy",
    "f1_happy": "F1 Happy",
    "f1_sad": "F1 Sad",
    "f1_neutral": "F1 Neutral",
}

CALIBRATION_DISPLAY = {
    "ece": "ECE",
    "brier": "Brier",
    "mce": "MCE",
}

VARIANT_DISPLAY = {
    "variant_1": "Variant 1 (Frozen Backbone)",
    "variant_2": "Variant 2 (Fine-Tuned Backbone)",
}

VARIANT_SHORT = {
    "variant_1": "V1",
    "variant_2": "V2",
}

# Composite score weights: classification accuracy is primary, calibration secondary.
_W_F1 = 0.50
_W_BAL_ACC = 0.20
_W_PER_CLASS = 0.15
_W_CALIBRATION = 0.15

# ---------------------------------------------------------------------------
# Placeholder payloads — used when no on-disk JSON exists yet.
# ---------------------------------------------------------------------------

VARIANT_1_TEST_PLACEHOLDER: Dict[str, Any] = {
    "run_id": "var1_placeholder",
    "run_type": "test",
    "model_variant": "variant_1",
    "gate_a_metrics": {
        "accuracy": 0.0, "precision_macro": 0.0, "recall_macro": 0.0,
        "f1_macro": 0.0, "balanced_accuracy": 0.0,
        "f1_class_0": 0.0, "f1_happy": 0.0,
        "f1_class_1": 0.0, "f1_sad": 0.0,
        "f1_class_2": 0.0, "f1_neutral": 0.0,
        "confusion_matrix": [], "ece": 1.0, "brier": 1.0, "mce": 1.0,
    },
    "gate_a_gates": {},
}

VARIANT_2_TEST_PLACEHOLDER: Dict[str, Any] = {
    "run_id": "var2_placeholder",
    "run_type": "test",
    "model_variant": "variant_2",
    "gate_a_metrics": {
        "accuracy": 0.0, "precision_macro": 0.0, "recall_macro": 0.0,
        "f1_macro": 0.0, "balanced_accuracy": 0.0,
        "f1_class_0": 0.0, "f1_happy": 0.0,
        "f1_class_1": 0.0, "f1_sad": 0.0,
        "f1_class_2": 0.0, "f1_neutral": 0.0,
        "confusion_matrix": [], "ece": 1.0, "brier": 1.0, "mce": 1.0,
    },
    "gate_a_gates": {},
}

FALLBACK_PAYLOADS: Dict[str, Dict[str, Any]] = {
    "variant_1": VARIANT_1_TEST_PLACEHOLDER,
    "variant_2": VARIANT_2_TEST_PLACEHOLDER,
}

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_all_test_results(variant: str) -> List[Tuple[Dict[str, Any], Path]]:
    """Return every test-run JSON for *variant*, newest first, with file paths."""
    prefix = _VARIANT_PREFIX.get(variant, f"{variant}_")
    run_dir = DASHBOARD_RESULTS_ROOT / "test"
    results: List[Tuple[Dict[str, Any], Path]] = []
    if run_dir.exists():
        for path in sorted(
            [p for p in run_dir.glob("*.json") if p.name.startswith(prefix)],
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        ):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    loaded.setdefault("model_variant", variant)
                    loaded.setdefault("run_type", "test")
                    loaded.setdefault("run_id", path.stem)
                    results.append((loaded, path))
            except Exception:  # noqa: BLE001
                continue
    return results


def _load_best_test_result(variant: str) -> Tuple[Dict[str, Any], Optional[Path]]:
    """Load the highest-scoring test-run JSON for *variant*."""
    all_results = _load_all_test_results(variant)
    if all_results:
        all_results.sort(key=lambda t: _composite_score(t[0]), reverse=True)
        return all_results[0]
    fallback = dict(FALLBACK_PAYLOADS.get(variant, VARIANT_1_TEST_PLACEHOLDER))
    fallback["model_variant"] = variant
    return fallback, None


def _composite_score(payload: Dict[str, Any]) -> float:
    """Weighted composite: classification accuracy + calibration quality.

    Weights: F1 Macro (50%), Balanced Accuracy (20%),
             mean per-class F1 (15%), calibration (15%).
    Calibration component uses (1 - ECE) so higher is better.
    """
    m = payload.get("gate_a_metrics", {})
    f1_macro = float(m.get("f1_macro", 0.0))
    bal_acc = float(m.get("balanced_accuracy", 0.0))
    per_class = [
        float(m.get("f1_happy", 0.0)),
        float(m.get("f1_sad", 0.0)),
        float(m.get("f1_neutral", 0.0)),
    ]
    per_class_mean = sum(per_class) / max(len(per_class), 1)
    ece = float(m.get("ece", 1.0))
    calibration = 1.0 - min(ece, 1.0)
    return (
        _W_F1 * f1_macro
        + _W_BAL_ACC * bal_acc
        + _W_PER_CLASS * per_class_mean
        + _W_CALIBRATION * calibration
    )


def _check_gate_a_deploy(payload: Dict[str, Any]) -> Dict[str, bool]:
    """Check Gate A-deploy (real-world tier) thresholds."""
    m = payload.get("gate_a_metrics", {})
    results: Dict[str, bool] = {}
    for metric, (op, threshold) in GATE_A_DEPLOY_THRESHOLDS.items():
        if metric == "per_class_f1":
            vals = [
                float(m.get("f1_happy", 0.0)),
                float(m.get("f1_sad", 0.0)),
                float(m.get("f1_neutral", 0.0)),
            ]
            results[metric] = all(v >= threshold for v in vals)
        elif op == ">=":
            results[metric] = float(m.get(metric, 0.0)) >= threshold
        elif op == "<=":
            results[metric] = float(m.get(metric, 1.0)) <= threshold
    results["overall"] = all(results.values())
    return results


def _extract_key_metrics(payload: Dict[str, Any]) -> Dict[str, float]:
    """Pull the key comparison metrics from a payload into a flat dict."""
    m = payload.get("gate_a_metrics", {})
    return {
        display: float(m.get(key, 0.0))
        for key, display in METRIC_DISPLAY.items()
    }


def _safe_float(val: object) -> float:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------


def _build_recommendation(
    v1: Dict[str, Any],
    v2: Dict[str, Any],
    v1_gate: Dict[str, bool],
    v2_gate: Dict[str, bool],
) -> Tuple[str, str, str]:
    """Return (recommended_variant, rationale, confidence_level).

    confidence_level is one of: 'high', 'moderate', 'low'.
    """
    v1_score = _composite_score(v1)
    v2_score = _composite_score(v2)
    v1_pass = v1_gate.get("overall", False)
    v2_pass = v2_gate.get("overall", False)
    v1m = v1.get("gate_a_metrics", {})
    v2m = v2.get("gate_a_metrics", {})

    # Case: only one passes Gate A-deploy
    if v1_pass and not v2_pass:
        return (
            "variant_1",
            "Variant 1 passes Gate A-deploy thresholds; Variant 2 does not.",
            "high",
        )
    if v2_pass and not v1_pass:
        return (
            "variant_2",
            "Variant 2 passes Gate A-deploy thresholds; Variant 1 does not.",
            "high",
        )

    # Case: both pass or both fail — compare on composite
    score_diff = abs(v1_score - v2_score)
    winner = "variant_1" if v1_score >= v2_score else "variant_2"
    loser = "variant_2" if winner == "variant_1" else "variant_1"

    # Build rationale
    parts: List[str] = []
    f1_diff = _safe_float(v1m.get("f1_macro")) - _safe_float(v2m.get("f1_macro"))
    ece_diff = _safe_float(v1m.get("ece")) - _safe_float(v2m.get("ece"))

    if winner == "variant_1":
        if f1_diff > 0:
            parts.append(f"V1 leads on F1 Macro (+{f1_diff:.4f})")
        if ece_diff > 0:
            parts.append("V2 has better calibration (lower ECE)")
        parts.append(
            "V1 frozen backbone offers simpler deployment: deterministic inference, "
            "faster retraining, easier rollback"
        )
    else:
        if f1_diff < 0:
            parts.append(f"V2 leads on F1 Macro (+{-f1_diff:.4f})")
        if ece_diff > 0:
            parts.append("V2 has better calibration (lower ECE)")
        parts.append(
            "V2 fine-tuned backbone enables domain adaptation but requires "
            "more parameters to manage"
        )

    rationale = ". ".join(parts) + "."

    if score_diff < 0.005:
        confidence = "low"
    elif score_diff < 0.02:
        confidence = "moderate"
    else:
        confidence = "high"

    return winner, rationale, confidence


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _render_head_to_head_bar_chart(
    v1: Dict[str, Any], v2: Dict[str, Any]
) -> None:
    """Grouped bar chart: V1 vs V2 across key metrics."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        st.warning("Matplotlib or NumPy not available.")
        return

    v1_metrics = _extract_key_metrics(v1)
    v2_metrics = _extract_key_metrics(v2)
    metric_labels = list(v1_metrics.keys())
    n_metrics = len(metric_labels)

    v1_values = list(v1_metrics.values())
    v2_values = list(v2_metrics.values())

    x = np.arange(n_metrics)
    bar_width = 0.32

    fig, ax = plt.subplots(figsize=(10, 5.5))
    v1_run = v1.get("run_id", "V1")
    v2_run = v2.get("run_id", "V2")
    bars1 = ax.bar(
        x - bar_width / 2, v1_values, bar_width,
        label=f"Variant 1 ({v1_run})", color="#2196F3",
    )
    bars2 = ax.bar(
        x + bar_width / 2, v2_values, bar_width,
        label=f"Variant 2 ({v2_run})", color="#4CAF50",
    )

    for bars in (bars1, bars2):
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0, height + 0.005,
                f"{height:.3f}", ha="center", va="bottom",
                fontsize=8, fontweight="bold",
            )

    ax.set_ylabel("Score")
    ax.set_title("Variant 1 vs Variant 2 — Key Metrics (Real-World Test)")
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, rotation=15, ha="right")
    ax.set_ylim(0, 1.08)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True, use_container_width=True)


def _render_calibration_bar_chart(
    v1: Dict[str, Any], v2: Dict[str, Any]
) -> None:
    """Calibration metrics bar chart (lower is better)."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return

    v1m = v1.get("gate_a_metrics", {})
    v2m = v2.get("gate_a_metrics", {})
    labels = list(CALIBRATION_DISPLAY.values())
    keys = list(CALIBRATION_DISPLAY.keys())
    v1_vals = [_safe_float(v1m.get(k)) for k in keys]
    v2_vals = [_safe_float(v2m.get(k)) for k in keys]

    x = np.arange(len(labels))
    bar_width = 0.32

    fig, ax = plt.subplots(figsize=(7, 4))
    bars1 = ax.bar(x - bar_width / 2, v1_vals, bar_width, label="Variant 1", color="#2196F3")
    bars2 = ax.bar(x + bar_width / 2, v2_vals, bar_width, label="Variant 2", color="#4CAF50")

    for bars in (bars1, bars2):
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0, height + 0.003,
                f"{height:.4f}", ha="center", va="bottom", fontsize=8, fontweight="bold",
            )

    ax.set_ylabel("Score (lower is better)")
    ax.set_title("Calibration Metrics")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # Draw ECE threshold line
    ece_threshold = GATE_A_DEPLOY_THRESHOLDS.get("ece", ("<=", 0.12))[1]
    ax.axhline(y=ece_threshold, color="#FF5722", linestyle="--", alpha=0.7, label=f"ECE threshold ({ece_threshold})")
    ax.legend(loc="upper right")

    fig.tight_layout()
    st.pyplot(fig, clear_figure=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Section rendering
# ---------------------------------------------------------------------------


def _render_side_by_side_table(
    v1: Dict[str, Any], v2: Dict[str, Any]
) -> None:
    """Side-by-side metric comparison table with delta and winner indicator."""
    v1m = v1.get("gate_a_metrics", {})
    v2m = v2.get("gate_a_metrics", {})

    rows = [
        ("F1 (Macro)", "f1_macro", True),
        ("Balanced Accuracy", "balanced_accuracy", True),
        ("Accuracy", "accuracy", True),
        ("Precision (Macro)", "precision_macro", True),
        ("Recall (Macro)", "recall_macro", True),
        ("F1 Happy", "f1_happy", True),
        ("F1 Sad", "f1_sad", True),
        ("F1 Neutral", "f1_neutral", True),
        ("ECE", "ece", False),
        ("Brier", "brier", False),
        ("MCE", "mce", False),
    ]

    header = "| Metric | Variant 1 | Variant 2 | Delta (V1-V2) | Winner |"
    sep = "|--------|-----------|-----------|---------------|--------|"
    lines = [header, sep]

    for display, key, higher_better in rows:
        v1_val = _safe_float(v1m.get(key))
        v2_val = _safe_float(v2m.get(key))
        delta = v1_val - v2_val
        if abs(delta) < 1e-6:
            winner = "Tie"
        elif higher_better:
            winner = "**V1**" if delta > 0 else "**V2**"
        else:
            winner = "**V1**" if delta < 0 else "**V2**"

        fmt = ".6f" if key in ("ece", "brier", "mce") else ".4f"
        lines.append(
            f"| {display} | {v1_val:{fmt}} | {v2_val:{fmt}} | {delta:+{fmt}} | {winner} |"
        )

    st.markdown("\n".join(lines))


def _render_gate_a_deploy_status(
    gate_results: Dict[str, bool], variant_label: str
) -> None:
    """Show Gate A-deploy pass/fail badges."""
    overall = gate_results.get("overall", False)
    if overall:
        st.success(f"{variant_label}: Gate A-deploy **PASSED**")
    else:
        st.error(f"{variant_label}: Gate A-deploy **FAILED**")

    gate_display = {
        "f1_macro": f"F1 Macro >= {GATE_A_DEPLOY_THRESHOLDS['f1_macro'][1]}",
        "balanced_accuracy": f"Balanced Accuracy >= {GATE_A_DEPLOY_THRESHOLDS['balanced_accuracy'][1]}",
        "per_class_f1": f"Per-Class F1 >= {GATE_A_DEPLOY_THRESHOLDS['per_class_f1'][1]}",
        "ece": f"ECE <= {GATE_A_DEPLOY_THRESHOLDS['ece'][1]}",
    }
    for gate_key, display in gate_display.items():
        passed = gate_results.get(gate_key, False)
        if passed:
            st.caption(f"  :green[PASS] {display}")
        else:
            st.caption(f"  :red[FAIL] {display}")


def _render_all_metrics(payload: Dict[str, Any]) -> None:
    """Display ALL test results for a given payload."""
    metrics = payload.get("gate_a_metrics", {})

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

    cls_cols = st.columns(3)
    cls_cols[0].metric("F1 Happy", f"{_safe_float(metrics.get('f1_happy')):.4f}")
    cls_cols[1].metric("F1 Sad", f"{_safe_float(metrics.get('f1_sad')):.4f}")
    cls_cols[2].metric("F1 Neutral", f"{_safe_float(metrics.get('f1_neutral')):.4f}")

    cm = metrics.get("confusion_matrix", [])
    if cm:
        st.markdown("**Confusion Matrix**")
        class_names = ["Happy", "Sad", "Neutral"]
        for idx, row in enumerate(cm):
            label = class_names[idx] if idx < len(class_names) else str(idx)
            st.write(f"  {label}: {row}")


# ---------------------------------------------------------------------------
# Main page logic
# ---------------------------------------------------------------------------

# Load best test results for each variant (no base model).
v1_payload, v1_path = _load_best_test_result("variant_1")
v2_payload, v2_path = _load_best_test_result("variant_2")

v1_is_placeholder = v1_path is None
v2_is_placeholder = v2_path is None

# Gate A-deploy checks
v1_gate = _check_gate_a_deploy(v1_payload)
v2_gate = _check_gate_a_deploy(v2_payload)

# Composite scores
v1_score = _composite_score(v1_payload)
v2_score = _composite_score(v2_payload)

# Recommendation
recommended, rationale, confidence = _build_recommendation(
    v1_payload, v2_payload, v1_gate, v2_gate
)

# ---------------------------------------------------------------------------
# Section 1: Recommendation Banner
# ---------------------------------------------------------------------------
st.markdown("---")

if v1_is_placeholder and v2_is_placeholder:
    st.warning(
        "No test results found for either variant. "
        "Run test jobs to populate comparison data."
    )
else:
    rec_display = VARIANT_DISPLAY.get(recommended, recommended)
    rec_short = VARIANT_SHORT.get(recommended, recommended)
    conf_color = {"high": "green", "moderate": "orange", "low": "red"}[confidence]

    st.subheader(f"Recommended for Deployment: {rec_display}")
    st.markdown(
        f"**Confidence:** :{conf_color}[{confidence.upper()}] "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Composite Score:** {rec_short} = {max(v1_score, v2_score):.4f} "
        f"vs {min(v1_score, v2_score):.4f}"
    )
    st.info(rationale)

    # Temperature scaling notices
    v1_temp = _safe_float(v1_payload.get("gate_a_metrics", {}).get("temperature", 0))
    v2_temp = _safe_float(v2_payload.get("gate_a_metrics", {}).get("temperature", 0))
    if v1_temp > 0 or v2_temp > 0:
        parts = []
        if v1_temp > 0:
            parts.append(f"V1 T={v1_temp:.4f}")
        if v2_temp > 0:
            parts.append(f"V2 T={v2_temp:.4f}")
        st.caption(
            f"Temperature scaling applied: {', '.join(parts)}. "
            "Calibration-adjusted confidence scores (classification unchanged)."
        )

    # Gate A-deploy status side by side
    g1, g2 = st.columns(2)
    with g1:
        _render_gate_a_deploy_status(v1_gate, "Variant 1")
    with g2:
        _render_gate_a_deploy_status(v2_gate, "Variant 2")

# ---------------------------------------------------------------------------
# Section 2: Head-to-Head Chart
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Head-to-Head: Key Metrics")

if not v1_is_placeholder or not v2_is_placeholder:
    _render_head_to_head_bar_chart(v1_payload, v2_payload)

# ---------------------------------------------------------------------------
# Section 3: Side-by-Side Metric Table
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Side-by-Side Metric Comparison")

if not v1_is_placeholder or not v2_is_placeholder:
    _render_side_by_side_table(v1_payload, v2_payload)

# ---------------------------------------------------------------------------
# Section 4: Calibration Chart
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Calibration Quality")
st.caption("Lower values indicate better-calibrated confidence scores.")

if not v1_is_placeholder or not v2_is_placeholder:
    _render_calibration_bar_chart(v1_payload, v2_payload)

# ---------------------------------------------------------------------------
# Section 5: Per-Class Breakdown (expandable)
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("Per-Class Breakdown", expanded=False):
    v1m = v1_payload.get("gate_a_metrics", {})
    v2m = v2_payload.get("gate_a_metrics", {})

    classes = ["happy", "sad", "neutral"]
    for cls in classes:
        key = f"f1_{cls}"
        v1_val = _safe_float(v1m.get(key))
        v2_val = _safe_float(v2m.get(key))
        delta = v1_val - v2_val
        winner = "V1" if delta > 0 else ("V2" if delta < 0 else "Tie")
        cols = st.columns([2, 2, 2, 1])
        cols[0].metric(f"V1 — F1 {cls.title()}", f"{v1_val:.4f}")
        cols[1].metric(f"V2 — F1 {cls.title()}", f"{v2_val:.4f}")
        cols[2].metric("Delta (V1-V2)", f"{delta:+.4f}")
        cols[3].markdown(f"**{winner}**")

    # Confusion matrices side by side
    st.markdown("---")
    st.markdown("**Confusion Matrices**")
    cm1, cm2 = st.columns(2)
    with cm1:
        st.markdown("**Variant 1**")
        cm = v1m.get("confusion_matrix", [])
        class_labels = ["Happy", "Sad", "Neutral"]
        if cm:
            for idx, row in enumerate(cm):
                label = class_labels[idx] if idx < len(class_labels) else str(idx)
                st.write(f"  {label}: {row}")
    with cm2:
        st.markdown("**Variant 2**")
        cm = v2m.get("confusion_matrix", [])
        if cm:
            for idx, row in enumerate(cm):
                label = class_labels[idx] if idx < len(class_labels) else str(idx)
                st.write(f"  {label}: {row}")

# ---------------------------------------------------------------------------
# Section 6: Architectural Trade-offs
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("Architectural Trade-offs", expanded=False):
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("#### Variant 1 — Frozen Backbone")
        st.markdown(
            """
- **Architecture**: HSEmotion EfficientNet-B0 backbone fully frozen + new 3-class head
- **Training surface**: Only classification head (~4K parameters)
- **Retraining speed**: Fast — only head weights update
- **Inference**: Deterministic backbone, consistent feature extraction
- **Rollback**: Simple — swap head weights only
- **Risk profile**: Lower — backbone integrity preserved from VGGFace2+AffectNet pre-training
            """
        )
    with t2:
        st.markdown("#### Variant 2 — Fine-Tuned Backbone")
        st.markdown(
            """
- **Architecture**: V1 checkpoint + selective backbone unfreezing (blocks.5, blocks.6, conv_head)
- **Training surface**: Head + ~500K backbone parameters
- **Retraining speed**: Slower — more parameters, two-phase schedule
- **Inference**: Adapted features, potentially better domain fit
- **Rollback**: More complex — full model swap required
- **Risk profile**: Higher — backbone drift possible, calibration sensitivity
            """
        )

# ---------------------------------------------------------------------------
# Section 7: Data Sources & Methodology
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("How Comparison Works", expanded=False):
    st.markdown(
        """
**Data Source:**
Results are loaded from `stats/results/runs/test/var1_test_<run_id>.json` and
`stats/results/runs/test/var2_test_<run_id>.json`.

**Ranking Logic:**
1. For each variant, the page loads all test-run JSONs and selects the one with
   the highest composite score.
2. Composite score = 0.50 x F1 Macro + 0.20 x Balanced Accuracy
   + 0.15 x mean(F1 Happy, F1 Sad, F1 Neutral) + 0.15 x (1 - ECE).
3. Gate A-deploy thresholds (real-world tier per ADR 011) are checked independently.
4. The variant with the higher composite score is recommended for deployment.
   If only one variant passes Gate A-deploy, it is automatically recommended.

**Gate A-deploy Thresholds (Real-World Tier):**
- F1 Macro >= 0.75
- Balanced Accuracy >= 0.75
- Per-Class F1 >= 0.70
- ECE <= 0.12

**Temperature Scaling (Post-Hoc Calibration):**
Results may include temperature-scaled predictions. Temperature scaling
(Guo et al., 2017) divides logits by a learned scalar T before softmax.
T is learned by minimizing NLL on a held-out 30% stratified calibration
split of the real-world test data, then applied to the remaining 70%
evaluation split (or the full test set for final reporting). Temperature
scaling adjusts confidence scores without changing predicted classes
(argmax is preserved). T < 1 sharpens, T > 1 softens.

**Note:** The base model (8-class HSEmotion head) is excluded from this comparison.
Only Variant 1 and Variant 2 (3-class heads trained on project data) are evaluated
as deployment candidates.
        """
    )

# ---------------------------------------------------------------------------
# Raw data (debugging)
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("Raw payload data (for debugging)")
col_d1, col_d2 = st.columns(2)
with col_d1:
    src_label = f"Loaded from `{v1_path}`" if v1_path else "Using placeholder"
    with st.expander(f"Variant 1 ({v1_payload.get('run_id', '?')}) — {src_label}"):
        st.json(v1_payload)
with col_d2:
    src_label = f"Loaded from `{v2_path}`" if v2_path else "Using placeholder"
    with st.expander(f"Variant 2 ({v2_payload.get('run_id', '?')}) — {src_label}"):
        st.json(v2_payload)
