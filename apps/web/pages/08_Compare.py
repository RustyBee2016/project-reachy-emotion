from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from apps.web.navigation_bar import render_navigation_bar

st.set_page_config(page_title="Compare", layout="wide")
render_navigation_bar()
st.title("08 - Compare")
st.caption(
    "Compare variant model test results against the baseline. "
    "Only variants that outperform the base model are candidates for deployment."
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DASHBOARD_RESULTS_ROOT = (
    Path(__file__).resolve().parents[3] / "stats" / "results" / "runs"
)

# Variant slug → filename prefix used in test result JSONs.
# Files follow the pattern: <prefix>test_<run_id>.json
# e.g. base_test_run_0104.json, var1_test_run_0104.json
_VARIANT_PREFIX: Dict[str, str] = {
    "base": "base_test_",
    "variant_1": "var1_test_",
    "variant_2": "var2_test_",
}

# Key metrics used for comparison (the only metrics that matter for ranking).
KEY_METRICS = ["f1_macro", "balanced_accuracy"]
KEY_PER_CLASS = ["f1_happy", "f1_sad", "f1_neutral"]

# Display-friendly labels for chart axes and section headers.
METRIC_DISPLAY = {
    "f1_macro": "F1 (Macro)",
    "balanced_accuracy": "Balanced Accuracy",
    "f1_happy": "F1 Happy",
    "f1_sad": "F1 Sad",
    "f1_neutral": "F1 Neutral",
}

VARIANT_DISPLAY = {
    "base": "Base Model",
    "variant_1": "Variant 1",
    "variant_2": "Variant 2",
}

# ---------------------------------------------------------------------------
# Placeholder payloads — used when no on-disk JSON exists yet.
# ---------------------------------------------------------------------------

BASE_TEST_PLACEHOLDER: Dict[str, Any] = {
    "run_id": "base_test_001",
    "run_type": "test",
    "model_variant": "base",
    "gate_a_metrics": {
        "accuracy": 0.8125,
        "precision_macro": 0.8190,
        "recall_macro": 0.8080,
        "f1_macro": 0.8120,
        "balanced_accuracy": 0.8080,
        "f1_class_0": 0.8250,
        "f1_happy": 0.8250,
        "f1_class_1": 0.7950,
        "f1_sad": 0.7950,
        "f1_class_2": 0.8160,
        "f1_neutral": 0.8160,
        "confusion_matrix": [[33, 4, 3], [5, 30, 5], [3, 4, 33]],
        "ece": 0.1120,
        "brier": 0.1580,
        "mce": 0.2050,
    },
    "gate_a_gates": {
        "macro_f1": False,
        "balanced_accuracy": False,
        "per_class_f1": False,
        "ece": False,
        "brier": False,
    },
}

VARIANT_1_TEST_PLACEHOLDER: Dict[str, Any] = {
    "run_id": "run_0003",
    "run_type": "test",
    "model_variant": "variant_1",
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
        "per_class_f1": True,
        "ece": False,
        "brier": False,
    },
}

VARIANT_2_TEST_PLACEHOLDER: Dict[str, Any] = {
    "run_id": "run_1003",
    "run_type": "test",
    "model_variant": "variant_2",
    "gate_a_metrics": {
        "accuracy": 0.9297,
        "precision_macro": 0.9320,
        "recall_macro": 0.9285,
        "f1_macro": 0.9298,
        "balanced_accuracy": 0.9285,
        "f1_class_0": 0.9350,
        "f1_happy": 0.9350,
        "f1_class_1": 0.9260,
        "f1_sad": 0.9260,
        "f1_class_2": 0.9280,
        "f1_neutral": 0.9280,
        "confusion_matrix": [[40, 2, 1], [1, 39, 3], [2, 2, 38]],
        "ece": 0.0650,
        "brier": 0.0920,
        "mce": 0.1280,
    },
    "gate_a_gates": {
        "macro_f1": True,
        "balanced_accuracy": True,
        "per_class_f1": True,
        "ece": True,
        "brier": True,
    },
}

FALLBACK_PAYLOADS: Dict[str, Dict[str, Any]] = {
    "base": BASE_TEST_PLACEHOLDER,
    "variant_1": VARIANT_1_TEST_PLACEHOLDER,
    "variant_2": VARIANT_2_TEST_PLACEHOLDER,
}

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_latest_test_result(variant: str) -> Tuple[Dict[str, Any], Optional[Path]]:
    """Load the most recent test-run JSON for *variant*, falling back to placeholder."""
    prefix = _VARIANT_PREFIX.get(variant, f"{variant}_")
    run_dir = DASHBOARD_RESULTS_ROOT / "test"
    if run_dir.exists():
        candidates = sorted(
            [p for p in run_dir.glob("*.json") if p.name.startswith(prefix)],
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
        if candidates:
            try:
                loaded = json.loads(candidates[0].read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    loaded.setdefault("model_variant", variant)
                    loaded.setdefault("run_type", "test")
                    loaded.setdefault("run_id", candidates[0].stem)
                    return loaded, candidates[0]
            except Exception:  # noqa: BLE001
                pass  # fall through to placeholder

    fallback = dict(FALLBACK_PAYLOADS.get(variant, BASE_TEST_PLACEHOLDER))
    fallback["model_variant"] = variant
    return fallback, None


def _all_test_results(variant: str) -> List[Dict[str, Any]]:
    """Return every test-run JSON for *variant*, newest first."""
    prefix = _VARIANT_PREFIX.get(variant, f"{variant}_")
    run_dir = DASHBOARD_RESULTS_ROOT / "test"
    results: List[Dict[str, Any]] = []
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
                    results.append(loaded)
            except Exception:  # noqa: BLE001
                continue
    if not results:
        fallback = dict(FALLBACK_PAYLOADS.get(variant, BASE_TEST_PLACEHOLDER))
        fallback["model_variant"] = variant
        results.append(fallback)
    return results


def _composite_score(payload: Dict[str, Any]) -> float:
    """Compute a single ranking score from the key metrics.

    The score is the average of f1_macro, balanced_accuracy, and
    the mean of per-class F1 scores.  Higher is better.
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
    return (f1_macro + bal_acc + per_class_mean) / 3.0


def _beats_base(variant_payload: Dict[str, Any], base_payload: Dict[str, Any]) -> bool:
    """Return True if *variant_payload* exceeds *base_payload* on ALL key metrics."""
    vm = variant_payload.get("gate_a_metrics", {})
    bm = base_payload.get("gate_a_metrics", {})
    for key in KEY_METRICS + KEY_PER_CLASS:
        if float(vm.get(key, 0.0)) <= float(bm.get(key, 0.0)):
            return False
    return True


def _best_test_for_variant(
    variant: str, base_payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Return the highest-scoring test result for *variant* that beats base, or None."""
    all_runs = _all_test_results(variant)
    qualifying = [r for r in all_runs if _beats_base(r, base_payload)]
    if not qualifying:
        return None
    qualifying.sort(key=_composite_score, reverse=True)
    return qualifying[0]


# ---------------------------------------------------------------------------
# Metric extraction helper
# ---------------------------------------------------------------------------


def _extract_key_metrics(payload: Dict[str, Any]) -> Dict[str, float]:
    """Pull the key comparison metrics from a payload into a flat dict."""
    m = payload.get("gate_a_metrics", {})
    return {
        display: float(m.get(key, 0.0))
        for key, display in METRIC_DISPLAY.items()
    }


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _render_comparison_bar_chart(
    base_payload: Dict[str, Any],
    ranked_variants: List[Dict[str, Any]],
) -> None:
    """Grouped bar chart: base + top 2 variant models across key metrics."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        st.warning("Matplotlib or NumPy not available — cannot render bar chart.")
        return

    base_metrics = _extract_key_metrics(base_payload)
    metric_labels = list(base_metrics.keys())
    n_metrics = len(metric_labels)

    # Build groups: base is always first; then up to 2 ranked variants.
    group_labels = ["Base Model"]
    group_values = [list(base_metrics.values())]
    colors = ["#6c757d"]  # grey for base

    variant_colors = ["#2196F3", "#4CAF50"]  # blue, green
    for idx, v_payload in enumerate(ranked_variants[:2]):
        v_name = VARIANT_DISPLAY.get(
            v_payload.get("model_variant", "?"), v_payload.get("model_variant", "?")
        )
        run_id = v_payload.get("run_id", "?")
        group_labels.append(f"{v_name} ({run_id})")
        group_values.append(list(_extract_key_metrics(v_payload).values()))
        colors.append(variant_colors[idx % len(variant_colors)])

    n_groups = len(group_labels)
    x = np.arange(n_metrics)
    bar_width = 0.25
    offsets = np.linspace(
        -(n_groups - 1) * bar_width / 2,
        (n_groups - 1) * bar_width / 2,
        n_groups,
    )

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, (label, values, color) in enumerate(
        zip(group_labels, group_values, colors)
    ):
        bars = ax.bar(x + offsets[i], values, bar_width, label=label, color=color)
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.005,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

    ax.set_ylabel("Score")
    ax.set_title("Key Metric Comparison: Base vs. Variant Models")
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, rotation=15, ha="right")
    ax.set_ylim(0, 1.08)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Section rendering
# ---------------------------------------------------------------------------


def _render_all_metrics(payload: Dict[str, Any]) -> None:
    """Display ALL test results for a given payload."""
    metrics = payload.get("gate_a_metrics", {})
    gates = payload.get("gate_a_gates", {})

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

    cls_cols = st.columns(3)
    cls_cols[0].metric("F1 Happy", f"{float(metrics.get('f1_happy', 0.0)):.4f}")
    cls_cols[1].metric("F1 Sad", f"{float(metrics.get('f1_sad', 0.0)):.4f}")
    cls_cols[2].metric("F1 Neutral", f"{float(metrics.get('f1_neutral', 0.0)):.4f}")

    cm = metrics.get("confusion_matrix", [])
    if cm:
        st.markdown("**Confusion Matrix**")
        for idx, row in enumerate(cm):
            st.write(f"Row {idx}: {row}")

    if gates:
        st.markdown("**Gate A Checks**")
        gate_label_map = {
            "macro_f1": "F1 (Macro)",
            "balanced_accuracy": "Balanced Accuracy",
            "per_class_f1": "F1 (per Class)",
            "ece": "ECE",
            "brier": "Brier",
            "mce": "MCE",
        }
        for gate_name, passed in gates.items():
            display_name = gate_label_map.get(gate_name, gate_name)
            if passed:
                st.success(f"{display_name}: pass")
            else:
                st.error(f"{display_name}: fail")


def _render_key_metric_deltas(
    variant_payload: Dict[str, Any], base_payload: Dict[str, Any]
) -> None:
    """Show key metrics as Streamlit metrics with delta vs base."""
    vm = variant_payload.get("gate_a_metrics", {})
    bm = base_payload.get("gate_a_metrics", {})

    cols = st.columns(5)
    for idx, (key, display) in enumerate(METRIC_DISPLAY.items()):
        v_val = float(vm.get(key, 0.0))
        b_val = float(bm.get(key, 0.0))
        delta = v_val - b_val
        delta_str = f"{delta:+.4f} vs base"
        cols[idx % 5].metric(display, f"{v_val:.4f}", delta=delta_str)


# ---------------------------------------------------------------------------
# Main page logic
# ---------------------------------------------------------------------------

# Load baseline
base_payload, base_path = _load_latest_test_result("base")

# Find best qualifying variant results (must beat base on all key metrics)
best_v1 = _best_test_for_variant("variant_1", base_payload)
best_v2 = _best_test_for_variant("variant_2", base_payload)

# Rank qualifying variants by composite score (highest first)
qualifying_variants: List[Dict[str, Any]] = []
if best_v1 is not None:
    qualifying_variants.append(best_v1)
if best_v2 is not None:
    qualifying_variants.append(best_v2)

qualifying_variants.sort(key=_composite_score, reverse=True)

# ---------------------------------------------------------------------------
# Bar Chart — always visible at top
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Key Metric Comparison")
if qualifying_variants:
    _render_comparison_bar_chart(base_payload, qualifying_variants)
else:
    st.info(
        "No variant models currently outperform the base model on all key metrics. "
        "Run test jobs on Variant 1 or Variant 2 to populate comparison data."
    )
    _render_comparison_bar_chart(base_payload, [])

# ---------------------------------------------------------------------------
# Section 1: Base Model (always displayed)
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Section 1 — Base Model (Baseline)")
st.caption(
    "The base EfficientNet-B0 model (HSEmotion `enet_b0_8_best_vgaf` default weights, "
    "no synthetic data). Every variant must outperform these results to be a deployment candidate."
)
st.write(f"Run ID: `{base_payload.get('run_id', 'unknown')}` — Model Variant: `base`")
if base_path:
    st.caption(f"Loaded from `{base_path}`")
else:
    st.warning("Using placeholder data. Add a JSON file to `stats/results/dashboard_runs/base/test/`.")
_render_all_metrics(base_payload)

# ---------------------------------------------------------------------------
# Section 2: Highest-performing variant
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Section 2 — Highest-Performing Variant")

if len(qualifying_variants) >= 1:
    top_variant = qualifying_variants[0]
    v_name = VARIANT_DISPLAY.get(
        top_variant.get("model_variant", "?"), top_variant.get("model_variant", "?")
    )
    st.caption(
        f"**{v_name}** — outperforms the base model on all key metrics."
    )
    st.write(
        f"Run ID: `{top_variant.get('run_id', 'unknown')}` — "
        f"Model Variant: `{top_variant.get('model_variant', 'unknown')}`"
    )
    _render_key_metric_deltas(top_variant, base_payload)
    with st.expander("Full Test Results", expanded=False):
        _render_all_metrics(top_variant)
else:
    st.info(
        "No variant model currently outperforms the base model on all key metrics "
        "(F1 Macro, Balanced Accuracy, F1 per Class). Run more test jobs to populate this section."
    )

# ---------------------------------------------------------------------------
# Section 3: Second-highest-performing variant
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Section 3 — Second-Highest-Performing Variant")

if len(qualifying_variants) >= 2:
    second_variant = qualifying_variants[1]
    v_name = VARIANT_DISPLAY.get(
        second_variant.get("model_variant", "?"), second_variant.get("model_variant", "?")
    )
    st.caption(
        f"**{v_name}** — also outperforms the base model, but ranks below Section 2."
    )
    st.write(
        f"Run ID: `{second_variant.get('run_id', 'unknown')}` — "
        f"Model Variant: `{second_variant.get('model_variant', 'unknown')}`"
    )
    _render_key_metric_deltas(second_variant, base_payload)
    with st.expander("Full Test Results", expanded=False):
        _render_all_metrics(second_variant)
else:
    st.info(
        "No second variant model available. Both Variant 1 and Variant 2 must outperform "
        "the base model to populate this section."
    )

# ---------------------------------------------------------------------------
# Data source summary
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("How Comparison Works", expanded=False):
    st.markdown(
        """
**Data Source:**
Results are loaded from `stats/results/runs/test/<prefix>_test_<run_id>.json`.

**Naming Convention:**
```
stats/results/runs/test/
├── base_test_run_0104.json      # Base model test
├── var1_test_run_0104.json      # Variant 1 test
└── var2_test_run_0104.json      # Variant 2 test
```

Prefix mapping: `base_test_` = Base Model, `var1_test_` = Variant 1, `var2_test_` = Variant 2.

**Ranking Logic:**
1. For each variant (`variant_1`, `variant_2`), the page scans all test-run JSONs matching its prefix.
2. A variant test result **qualifies** only if it beats the base model on **every** key metric:
   F1 (Macro), Balanced Accuracy, F1 Happy, F1 Sad, F1 Neutral.
3. Qualifying results are ranked by a composite score (average of F1 Macro, Balanced Accuracy, and mean per-class F1).
4. The top-scoring result goes to **Section 2**; the runner-up goes to **Section 3**.

**After each test run**, the training pipeline writes a dashboard JSON payload to the
`stats/results/runs/test/` folder with the appropriate variant prefix.
This page automatically picks up the latest results.
        """
    )

st.markdown("---")
st.caption("Raw payload data (for debugging)")
with st.expander("Base Model Payload"):
    st.json(base_payload)
for idx, vp in enumerate(qualifying_variants):
    v_label = VARIANT_DISPLAY.get(vp.get("model_variant", "?"), vp.get("model_variant", "?"))
    with st.expander(f"Ranked #{idx + 1}: {v_label} ({vp.get('run_id', '?')})"):
        st.json(vp)
