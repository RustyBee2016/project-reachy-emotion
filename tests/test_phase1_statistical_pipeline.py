from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

MODULE_PATH = Path(__file__).resolve().parents[1] / "stats/scripts/04_phase1_statistical_pipeline.py"
spec = importlib.util.spec_from_file_location("phase1_stats_pipeline", MODULE_PATH)
phase1_stats_pipeline = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(phase1_stats_pipeline)

_prediction_shift = phase1_stats_pipeline._prediction_shift
_quality_metrics = phase1_stats_pipeline._quality_metrics


def test_quality_metrics_outputs_expected_keys():
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_pred = np.array([0, 1, 2, 0, 1, 2])
    y_prob = np.array(
        [
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.7, 0.2, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.2, 0.7],
        ]
    )
    metrics = _quality_metrics(y_true, y_pred, y_prob, ["happy", "sad", "neutral"])
    assert "f1_macro" in metrics
    assert "balanced_accuracy" in metrics
    assert "ece" in metrics
    assert "brier" in metrics
    assert "confusion" in metrics


def test_prediction_shift_shape():
    base = np.array([0, 1, 2, 0, 1, 2])
    finetuned = np.array([0, 1, 1, 0, 2, 2])
    shift = _prediction_shift(base, finetuned, ["happy", "sad", "neutral"])
    assert "contingency_table" in shift
    assert "marginal_delta" in shift
    assert set(shift["marginal_delta"].keys()) == {"happy", "sad", "neutral"}
