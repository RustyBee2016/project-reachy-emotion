from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from trainer.gate_a_validator import GateAThresholds, evaluate_predictions


def test_gate_a_validator_pass_case():
    y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
    y_pred = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
    y_prob = np.array(
        [
            [0.90, 0.05, 0.05],
            [0.05, 0.90, 0.05],
            [0.05, 0.05, 0.90],
            [0.92, 0.04, 0.04],
            [0.04, 0.92, 0.04],
            [0.04, 0.04, 0.92],
            [0.91, 0.05, 0.04],
            [0.06, 0.90, 0.04],
            [0.05, 0.04, 0.91],
        ],
        dtype=np.float32,
    )
    result = evaluate_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        class_names=["happy", "sad", "neutral"],
        thresholds=GateAThresholds(),
    )
    assert result["overall_pass"] is True
    assert result["gates"]["macro_f1"] is True


def test_gate_a_validator_fail_case():
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_pred = np.array([0, 0, 0, 0, 0, 0])
    y_prob = np.array(
        [
            [0.60, 0.20, 0.20],
            [0.60, 0.20, 0.20],
            [0.60, 0.20, 0.20],
            [0.60, 0.20, 0.20],
            [0.60, 0.20, 0.20],
            [0.60, 0.20, 0.20],
        ],
        dtype=np.float32,
    )
    result = evaluate_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        class_names=["happy", "sad", "neutral"],
        thresholds=GateAThresholds(),
    )
    assert result["overall_pass"] is False
    assert result["gates"]["macro_f1"] is False
