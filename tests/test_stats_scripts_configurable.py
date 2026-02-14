from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("sklearn")


def _load_module(path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_gate_script_accepts_runtime_3class_config() -> None:
    mod = _load_module("stats/scripts/01_quality_gate_metrics.py", "stats_script_01")
    mod._configure_runtime(
        classes=["happy", "sad", "neutral"],
        quality_gates={"macro_f1": 0.5, "balanced_accuracy": 0.5, "f1_neutral": 0.5},
    )

    y_true = np.array([0, 1, 2, 0, 1, 2], dtype=int)
    y_pred = np.array([0, 1, 2, 0, 2, 2], dtype=int)
    report = mod.compute_all_metrics(y_true, y_pred)

    assert set(report.per_class_f1.keys()) == {"happy", "sad", "neutral"}
    assert "f1_neutral" in report.gates_passed


def test_stuart_maxwell_script_accepts_runtime_3class_config() -> None:
    mod = _load_module("stats/scripts/02_stuart_maxwell_test.py", "stats_script_02")
    mod._configure_runtime(["happy", "sad", "neutral"])

    base_preds = np.array([0, 1, 2, 0, 1, 2], dtype=int)
    finetuned_preds = np.array([0, 2, 2, 0, 1, 1], dtype=int)
    result = mod.stuart_maxwell_test(base_preds, finetuned_preds)

    assert result.degrees_of_freedom == 2
    assert set(result.marginal_differences.keys()) == {"happy", "sad", "neutral"}


def test_perclass_ttests_script_accepts_runtime_3class_config() -> None:
    mod = _load_module("stats/scripts/03_perclass_paired_ttests.py", "stats_script_03")
    mod._configure_runtime(["happy", "sad", "neutral"])

    base_metrics = {
        "happy": [0.70, 0.72, 0.71, 0.73, 0.72],
        "sad": [0.68, 0.67, 0.69, 0.68, 0.67],
        "neutral": [0.75, 0.76, 0.74, 0.75, 0.76],
    }
    finetuned_metrics = {
        "happy": [0.74, 0.75, 0.73, 0.74, 0.75],
        "sad": [0.70, 0.71, 0.70, 0.69, 0.70],
        "neutral": [0.79, 0.80, 0.78, 0.79, 0.80],
    }

    result = mod.run_perclass_paired_ttests(base_metrics, finetuned_metrics, alpha=0.05)
    assert result.n_classes == 3
    assert {r.emotion_class for r in result.class_results} == {"happy", "sad", "neutral"}
