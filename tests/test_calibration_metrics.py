"""
Regression tests for ECE / Brier / MCE calibration metrics.

Uses synthetic data with known analytical answers to guard against
regressions in compute_calibration_metrics(), expected_calibration_error(),
maximum_calibration_error(), and brier_score().
"""
import numpy as np
import pytest

from trainer.fer_finetune.evaluate import (
    compute_calibration_metrics,
    expected_calibration_error,
    maximum_calibration_error,
    brier_score,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic probability arrays with known properties
# ---------------------------------------------------------------------------

@pytest.fixture
def perfect_calibration():
    """
    Perfectly calibrated predictor: predicted probability == empirical accuracy.

    3-class, 90 samples split evenly across three confidence levels.
    ECE should be 0.0 (or very close).
    """
    rng = np.random.default_rng(42)
    n = 300  # 100 per confidence bucket
    y_true = []
    y_prob = []

    for conf in (0.5, 0.75, 1.0):
        for _ in range(100):
            correct_class = rng.integers(0, 3)
            wrong_class = (correct_class + 1) % 3

            # Assign `conf` to the correct class
            probs = np.full(3, (1 - conf) / 2)
            probs[correct_class] = conf
            y_prob.append(probs)

            # Correct with probability == conf
            if rng.random() < conf:
                y_true.append(correct_class)
            else:
                y_true.append(wrong_class)

    return np.array(y_true), np.array(y_prob)


@pytest.fixture
def overconfident_predictor():
    """
    Always predicts confidence=0.99 but is only 50% accurate.
    ECE should be close to 0.49.
    """
    n = 200
    y_true = np.array([i % 2 for i in range(n)])  # alternating 0, 1
    y_prob = np.zeros((n, 3))
    y_prob[:, 0] = 0.99   # always says class 0 with 99% confidence
    y_prob[:, 1] = 0.005
    y_prob[:, 2] = 0.005
    return y_true, y_prob


@pytest.fixture
def uniform_predictor():
    """
    Always outputs uniform probabilities (1/3 each).
    Brier score should equal 2/3 * (1 - 1/3)^2 * ... ≈ expected value.
    """
    n = 300
    y_true = np.tile([0, 1, 2], 100)
    y_prob = np.full((n, 3), 1 / 3)
    return y_true, y_prob


@pytest.fixture
def perfect_predictor():
    """
    Perfect predictions (confidence=1.0, always correct).
    ECE=0, Brier=0, MCE=0.
    """
    n = 90
    y_true = np.tile([0, 1, 2], 30)
    y_prob = np.zeros((n, 3))
    for i, label in enumerate(y_true):
        y_prob[i, label] = 1.0
    return y_true, y_prob


# ---------------------------------------------------------------------------
# Tests: ECE
# ---------------------------------------------------------------------------

class TestExpectedCalibrationError:
    def test_perfect_predictor_ece_is_zero(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        ece = expected_calibration_error(y_true, y_prob)
        assert ece == pytest.approx(0.0, abs=1e-6)

    def test_overconfident_ece_is_high(self, overconfident_predictor):
        y_true, y_prob = overconfident_predictor
        ece = expected_calibration_error(y_true, y_prob)
        assert ece > 0.3, f"Expected ECE > 0.3 for overconfident predictor, got {ece:.4f}"

    def test_ece_is_in_unit_interval(self, perfect_calibration):
        y_true, y_prob = perfect_calibration
        ece = expected_calibration_error(y_true, y_prob)
        assert 0.0 <= ece <= 1.0

    def test_gate_a_threshold(self, perfect_predictor):
        """Perfect predictor must pass Gate A ECE ≤ 0.08."""
        y_true, y_prob = perfect_predictor
        ece = expected_calibration_error(y_true, y_prob)
        assert ece <= 0.08

    def test_ece_returns_float(self, uniform_predictor):
        y_true, y_prob = uniform_predictor
        result = expected_calibration_error(y_true, y_prob)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Tests: Brier Score
# ---------------------------------------------------------------------------

class TestBrierScore:
    def test_perfect_predictor_brier_is_zero(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        score = brier_score(y_true, y_prob)
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_uniform_predictor_brier(self, uniform_predictor):
        """Uniform predictor: Brier = mean over samples of sum((p-y)^2)."""
        y_true, y_prob = uniform_predictor
        score = brier_score(y_true, y_prob)
        # Each sample: correct class: (1/3 - 1)^2 + 2*(1/3)^2 = 4/9 + 2/9 = 6/9 ≈ 0.667
        expected = 6 / 9
        assert score == pytest.approx(expected, rel=0.02)

    def test_brier_score_nonnegative(self, overconfident_predictor):
        y_true, y_prob = overconfident_predictor
        score = brier_score(y_true, y_prob)
        assert score >= 0.0

    def test_gate_a_threshold(self, perfect_predictor):
        """Perfect predictor must pass Gate A Brier ≤ 0.16."""
        y_true, y_prob = perfect_predictor
        score = brier_score(y_true, y_prob)
        assert score <= 0.16

    def test_brier_returns_float(self, uniform_predictor):
        y_true, y_prob = uniform_predictor
        result = brier_score(y_true, y_prob)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Tests: MCE
# ---------------------------------------------------------------------------

class TestMaximumCalibrationError:
    def test_perfect_predictor_mce_is_zero(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        mce = maximum_calibration_error(y_true, y_prob)
        assert mce == pytest.approx(0.0, abs=1e-6)

    def test_overconfident_mce_is_high(self, overconfident_predictor):
        y_true, y_prob = overconfident_predictor
        mce = maximum_calibration_error(y_true, y_prob)
        assert mce > 0.3, f"Expected MCE > 0.3, got {mce:.4f}"

    def test_mce_ge_ece(self, perfect_calibration):
        """MCE is always >= ECE (it is the maximum, not the average)."""
        y_true, y_prob = perfect_calibration
        ece = expected_calibration_error(y_true, y_prob)
        mce = maximum_calibration_error(y_true, y_prob)
        assert mce >= ece - 1e-9  # allow tiny floating point slack

    def test_mce_in_unit_interval(self, uniform_predictor):
        y_true, y_prob = uniform_predictor
        mce = maximum_calibration_error(y_true, y_prob)
        assert 0.0 <= mce <= 1.0


# ---------------------------------------------------------------------------
# Tests: compute_calibration_metrics() (combined)
# ---------------------------------------------------------------------------

class TestComputeCalibrationMetrics:
    def test_returns_all_three_metrics(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        result = compute_calibration_metrics(y_true.tolist(), y_prob)
        assert "ece" in result
        assert "brier" in result
        assert "mce" in result

    def test_all_metrics_are_floats(self, uniform_predictor):
        y_true, y_prob = uniform_predictor
        result = compute_calibration_metrics(y_true.tolist(), y_prob)
        for key in ("ece", "brier", "mce"):
            assert isinstance(result[key], float), f"{key} is not float"

    def test_perfect_predictor_passes_gate_a(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        result = compute_calibration_metrics(y_true.tolist(), y_prob)
        assert result["ece"] <= 0.08, f"ECE {result['ece']:.4f} fails Gate A"
        assert result["brier"] <= 0.16, f"Brier {result['brier']:.4f} fails Gate A"

    def test_overconfident_predictor_fails_gate_a(self, overconfident_predictor):
        y_true, y_prob = overconfident_predictor
        result = compute_calibration_metrics(y_true.tolist(), y_prob)
        assert result["ece"] > 0.08 or result["brier"] > 0.16, (
            "Overconfident predictor should fail Gate A"
        )

    def test_accepts_list_input(self, perfect_predictor):
        y_true, y_prob = perfect_predictor
        result = compute_calibration_metrics(list(y_true), np.array(y_prob))
        assert result["ece"] >= 0.0

    def test_single_sample_does_not_crash(self):
        """Single sample edge case should not raise."""
        y_true = [0]
        y_prob = np.array([[0.9, 0.05, 0.05]])
        result = compute_calibration_metrics(y_true, y_prob)
        assert "ece" in result
