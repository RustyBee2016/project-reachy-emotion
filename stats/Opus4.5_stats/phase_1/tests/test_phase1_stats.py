"""
Unit Tests for Phase 1 Statistical Analysis
============================================

Tests cover:
    - Univariate metric computations
    - Multivariate comparison tests
    - Paired t-tests and BH correction
    - Edge cases and input validation
    - Demo data reproducibility
"""

import unittest
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from univariate import (
    compute_confusion_matrix,
    compute_precision,
    compute_recall,
    compute_f1,
    compute_per_class_metrics,
    compute_macro_f1,
    compute_balanced_accuracy,
    compute_all_univariate_metrics,
    validate_gate_a,
)
from multivariate import (
    build_contingency_table,
    stuart_maxwell_test,
    mcnemar_test_per_class,
    cohens_kappa,
)
from paired_tests import (
    paired_t_test,
    cohens_d,
    interpret_cohens_d,
    benjamini_hochberg_correction,
    run_per_class_paired_tests,
)
from run_analysis import generate_demo_data


class TestUnivariateMetrics(unittest.TestCase):
    """Test univariate metric computations."""
    
    def setUp(self):
        """Set up test data."""
        # Simple 2-class case
        self.y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
        self.y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0])
        self.num_classes = 2
    
    def test_confusion_matrix_basic(self):
        """Test confusion matrix computation."""
        cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
        
        # True: 4 class 0, 6 class 1
        # Pred: 0 gets 3 correct, 1 wrong -> [3, 1]
        #       1 gets 4 correct, 2 wrong -> [2, 4]
        expected = np.array([[3, 1], [2, 4]])
        assert_array_equal(cm, expected)
    
    def test_confusion_matrix_empty_raises(self):
        """Test that empty arrays raise ValueError."""
        with self.assertRaises(ValueError):
            compute_confusion_matrix(np.array([]), np.array([]), 2)
    
    def test_confusion_matrix_length_mismatch_raises(self):
        """Test that mismatched array lengths raise ValueError."""
        with self.assertRaises(ValueError):
            compute_confusion_matrix(np.array([0, 1]), np.array([0]), 2)
    
    def test_precision_recall_f1(self):
        """Test precision, recall, F1 computation."""
        cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
        
        # Class 0: TP=3, FP=2, FN=1
        # Precision = 3/(3+2) = 0.6
        # Recall = 3/(3+1) = 0.75
        # F1 = 2 * 0.6 * 0.75 / (0.6 + 0.75) = 0.667
        
        prec_0 = compute_precision(cm, 0)
        rec_0 = compute_recall(cm, 0)
        f1_0 = compute_f1(prec_0, rec_0)
        
        self.assertAlmostEqual(prec_0, 0.6, places=4)
        self.assertAlmostEqual(rec_0, 0.75, places=4)
        self.assertAlmostEqual(f1_0, 0.6667, places=3)
    
    def test_macro_f1(self):
        """Test macro F1 computation."""
        cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
        _, _, f1, _ = compute_per_class_metrics(cm)
        macro = compute_macro_f1(f1)
        
        # Should be average of per-class F1 scores
        expected = np.mean(list(f1.values()))
        self.assertAlmostEqual(macro, expected, places=4)
    
    def test_balanced_accuracy(self):
        """Test balanced accuracy computation."""
        cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
        ba = compute_balanced_accuracy(cm)
        
        # Recall class 0 = 0.75, Recall class 1 = 4/6 = 0.667
        # BA = (0.75 + 0.667) / 2 = 0.708
        self.assertAlmostEqual(ba, (0.75 + 4/6) / 2, places=3)
    
    def test_perfect_predictions(self):
        """Test metrics with perfect predictions."""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        
        results = compute_all_univariate_metrics(y_true, y_pred, 2, ["A", "B"])
        
        self.assertEqual(results.macro_f1, 1.0)
        self.assertEqual(results.balanced_accuracy, 1.0)
        for i in range(2):
            self.assertEqual(results.f1[i], 1.0)
    
    def test_gate_a_validation_pass(self):
        """Test Gate A validation passing."""
        # Create results that pass all thresholds
        y_true = np.array([0]*50 + [1]*50)
        y_pred = y_true.copy()
        y_pred[:5] = 1 - y_pred[:5]  # Small error
        y_pred[50:55] = 1 - y_pred[50:55]
        
        results = compute_all_univariate_metrics(y_true, y_pred, 2, ["happy", "sad"])
        gate_result = validate_gate_a(results)
        
        self.assertTrue(gate_result.passed)
        self.assertEqual(len(gate_result.failures), 0)
    
    def test_gate_a_validation_fail(self):
        """Test Gate A validation failing."""
        # Create results that fail thresholds
        y_true = np.array([0]*50 + [1]*50)
        y_pred = np.array([0]*100)  # All predicted as class 0
        
        results = compute_all_univariate_metrics(y_true, y_pred, 2, ["happy", "sad"])
        gate_result = validate_gate_a(results)
        
        self.assertFalse(gate_result.passed)
        self.assertGreater(len(gate_result.failures), 0)


class TestMultivariateTests(unittest.TestCase):
    """Test multivariate comparison tests."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(123)
        self.y_true = np.array([0]*50 + [1]*50)
        self.pred_a = self.y_true.copy()
        self.pred_b = self.y_true.copy()
        
        # Model A: 5 errors
        self.pred_a[:5] = 1
        # Model B: 8 errors (different samples)
        self.pred_b[50:58] = 0
        
        self.num_classes = 2
    
    def test_contingency_table_shape(self):
        """Test contingency table has correct shape."""
        ct = build_contingency_table(self.y_true, self.pred_a, self.pred_b, self.num_classes)
        self.assertEqual(ct.shape, (4, self.num_classes))
    
    def test_contingency_table_sums(self):
        """Test contingency table row sums equal class counts."""
        ct = build_contingency_table(self.y_true, self.pred_a, self.pred_b, self.num_classes)
        
        # Each column should sum to the number of samples in that class
        for c in range(self.num_classes):
            col_sum = ct[:, c].sum()
            expected = (self.y_true == c).sum()
            self.assertEqual(col_sum, expected)
    
    def test_stuart_maxwell_identical_predictions(self):
        """Test Stuart-Maxwell with identical predictions."""
        result = stuart_maxwell_test(self.pred_a, self.pred_a, self.num_classes)
        
        # Should not be significant when comparing model with itself
        self.assertAlmostEqual(result.statistic, 0.0, places=4)
        self.assertFalse(result.significant)
    
    def test_cohens_kappa_perfect_agreement(self):
        """Test Cohen's Kappa with perfect agreement."""
        result = cohens_kappa(self.pred_a, self.pred_a, self.num_classes)
        
        self.assertAlmostEqual(result.kappa, 1.0, places=4)
        self.assertEqual(result.interpretation, "Almost Perfect")
    
    def test_cohens_kappa_range(self):
        """Test that Kappa is in valid range."""
        result = cohens_kappa(self.pred_a, self.pred_b, self.num_classes)
        
        self.assertGreaterEqual(result.kappa, -1.0)
        self.assertLessEqual(result.kappa, 1.0)
    
    def test_mcnemar_test_per_class(self):
        """Test McNemar's test returns results for each class."""
        ct = build_contingency_table(self.y_true, self.pred_a, self.pred_b, self.num_classes)
        results = mcnemar_test_per_class(ct, ["class_0", "class_1"])
        
        self.assertEqual(len(results), self.num_classes)
        for r in results:
            self.assertGreaterEqual(r.p_value, 0.0)
            self.assertLessEqual(r.p_value, 1.0)


class TestPairedTests(unittest.TestCase):
    """Test paired t-tests and effect sizes."""
    
    def test_paired_t_test_basic(self):
        """Test basic paired t-test."""
        scores_a = np.array([0.85, 0.86, 0.84, 0.87, 0.85])
        scores_b = np.array([0.80, 0.81, 0.79, 0.82, 0.80])
        
        t_stat, p_value, mean_diff, std_diff = paired_t_test(scores_a, scores_b)
        
        # A is better, so mean diff should be positive
        self.assertGreater(mean_diff, 0)
        self.assertLess(p_value, 0.05)  # Should be significant
    
    def test_paired_t_test_no_difference(self):
        """Test paired t-test with identical scores."""
        scores = np.array([0.85, 0.86, 0.84, 0.87, 0.85])
        
        t_stat, p_value, mean_diff, std_diff = paired_t_test(scores, scores)
        
        self.assertAlmostEqual(mean_diff, 0.0)
        self.assertAlmostEqual(p_value, 1.0)
    
    def test_cohens_d_calculation(self):
        """Test Cohen's d effect size calculation."""
        scores_a = np.array([0.85, 0.86, 0.84, 0.87, 0.85])
        scores_b = np.array([0.80, 0.81, 0.79, 0.82, 0.80])
        
        d = cohens_d(scores_a, scores_b)
        
        # Effect should be positive (A better than B)
        self.assertGreater(d, 0)
    
    def test_cohens_d_interpretation(self):
        """Test Cohen's d interpretation."""
        self.assertIn("Negligible", interpret_cohens_d(0.1))
        self.assertIn("Small", interpret_cohens_d(0.3))
        self.assertIn("Medium", interpret_cohens_d(0.6))
        self.assertIn("Large", interpret_cohens_d(1.0))
        
        # Test direction
        self.assertIn("favoring A", interpret_cohens_d(0.5))
        self.assertIn("favoring B", interpret_cohens_d(-0.5))
    
    def test_benjamini_hochberg_basic(self):
        """Test Benjamini-Hochberg correction."""
        # P-values where some should survive correction
        p_values = [0.001, 0.01, 0.02, 0.03, 0.05, 0.10, 0.50]
        
        significant = benjamini_hochberg_correction(p_values, alpha=0.05)
        
        # First few should be significant
        self.assertTrue(significant[0])  # 0.001
        self.assertTrue(significant[1])  # 0.01
        
        # Last ones should not be significant
        self.assertFalse(significant[-1])  # 0.50
    
    def test_benjamini_hochberg_all_significant(self):
        """Test BH correction when all p-values are small."""
        p_values = [0.001, 0.002, 0.003]
        
        significant = benjamini_hochberg_correction(p_values, alpha=0.05)
        
        self.assertTrue(all(significant))
    
    def test_benjamini_hochberg_none_significant(self):
        """Test BH correction when no p-values are significant."""
        p_values = [0.20, 0.30, 0.40, 0.50]
        
        significant = benjamini_hochberg_correction(p_values, alpha=0.05)
        
        self.assertFalse(any(significant))
    
    def test_run_per_class_paired_tests(self):
        """Test full per-class paired test pipeline."""
        f1_folds_a = {
            0: np.array([0.85, 0.86, 0.84, 0.87, 0.85]),
            1: np.array([0.82, 0.83, 0.81, 0.84, 0.82])
        }
        f1_folds_b = {
            0: np.array([0.80, 0.81, 0.79, 0.82, 0.80]),
            1: np.array([0.78, 0.79, 0.77, 0.80, 0.78])
        }
        
        results = run_per_class_paired_tests(
            f1_folds_a, f1_folds_b,
            class_names=["happy", "sad"]
        )
        
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIsNotNone(r.rank)
            self.assertIn(r.significant_corrected, [True, False])


class TestInputValidation(unittest.TestCase):
    """Test input validation across all modules."""
    
    def test_univariate_none_input(self):
        """Test univariate functions reject None input."""
        with self.assertRaises(ValueError):
            compute_confusion_matrix(None, None, 2)
    
    def test_multivariate_none_input(self):
        """Test multivariate functions reject None input."""
        with self.assertRaises(ValueError):
            build_contingency_table(None, None, None, 2)
    
    def test_paired_tests_none_input(self):
        """Test paired test functions reject None input."""
        with self.assertRaises(ValueError):
            paired_t_test(None, None)
    
    def test_insufficient_folds(self):
        """Test paired tests require at least 2 folds."""
        scores_a = np.array([0.85])
        scores_b = np.array([0.80])
        
        with self.assertRaises(ValueError):
            paired_t_test(scores_a, scores_b)
    
    def test_invalid_num_classes(self):
        """Test that num_classes < 2 raises error."""
        with self.assertRaises(ValueError):
            compute_confusion_matrix(np.array([0, 0]), np.array([0, 0]), 1)


class TestDemoDataReproducibility(unittest.TestCase):
    """Test that demo data produces consistent results."""
    
    def test_demo_data_structure(self):
        """Test demo data has all required fields."""
        data = generate_demo_data()
        
        required_fields = [
            'y_true', 'pred_a', 'pred_b', 'class_names',
            'num_classes', 'model_a_name', 'model_b_name',
            'f1_folds_a', 'f1_folds_b'
        ]
        
        for field in required_fields:
            self.assertIn(field, data)
    
    def test_demo_data_consistency(self):
        """Test demo data produces same results with same seed."""
        data1 = generate_demo_data()
        data2 = generate_demo_data()
        
        # Arrays should be identical (same random seed)
        np.testing.assert_array_equal(data1['y_true'], data2['y_true'])
        np.testing.assert_array_equal(data1['pred_a'], data2['pred_a'])
        np.testing.assert_array_equal(data1['pred_b'], data2['pred_b'])
    
    def test_demo_metrics_reasonable(self):
        """Test demo data produces reasonable metrics."""
        data = generate_demo_data()
        
        y_true = np.array(data['y_true'])
        pred_a = np.array(data['pred_a'])
        
        results = compute_all_univariate_metrics(
            y_true, pred_a, data['num_classes'], data['class_names']
        )
        
        # Macro F1 should be in reasonable range
        self.assertGreater(results.macro_f1, 0.70)
        self.assertLess(results.macro_f1, 1.0)
        
        # Balanced accuracy should be in reasonable range
        self.assertGreater(results.balanced_accuracy, 0.70)
        self.assertLess(results.balanced_accuracy, 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_single_class_predictions(self):
        """Test when all predictions are one class."""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 0, 0])  # All predicted as class 0
        
        results = compute_all_univariate_metrics(y_true, y_pred, 2, ["A", "B"])
        
        # Class 1 should have 0 precision (no predictions)
        self.assertEqual(results.precision[1], 0.0)
        # Class 1 should have 0 recall (none correct)
        self.assertEqual(results.recall[1], 0.0)
    
    def test_perfect_disagreement(self):
        """Test Kappa with perfect disagreement."""
        pred_a = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        pred_b = np.array([1, 1, 1, 1, 0, 0, 0, 0])  # Opposite
        
        result = cohens_kappa(pred_a, pred_b, 2)
        
        # Kappa should be negative (worse than chance)
        self.assertLess(result.kappa, 0)
    
    def test_three_class_problem(self):
        """Test with 3 classes."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 1, 1, 2, 2, 0])
        
        cm = compute_confusion_matrix(y_true, y_pred, 3)
        
        self.assertEqual(cm.shape, (3, 3))
        self.assertEqual(cm.sum(), 6)


if __name__ == '__main__':
    unittest.main()
