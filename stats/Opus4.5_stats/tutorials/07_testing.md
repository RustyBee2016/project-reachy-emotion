# Tutorial 07: Testing Your Code

This tutorial covers unit testing for the statistical analysis package. Writing tests ensures your code works correctly and continues to work as you make changes.

---

## Learning Objectives

By the end of this tutorial, you will:

1. Understand why testing statistical code is crucial
2. Run the existing test suite
3. Write new tests for edge cases
4. Use test-driven development practices

---

## Part 1: Why Test Statistical Code?

### The Stakes Are High

Statistical code makes decisions:
- "Model A is significantly better" → Deploy Model A
- "Gate A passed" → Model goes to production

**A bug could mean deploying the wrong model.**

### Common Bugs in Statistical Code

| Bug Type | Example | Consequence |
|----------|---------|-------------|
| Off-by-one | Using N instead of N-1 in variance | Biased estimates |
| Index swap | Rows/columns mixed in confusion matrix | Wrong metrics |
| Edge case | Division by zero when class is missing | Crash or NaN |
| Formula error | Wrong chi-square formula | Invalid p-values |

### Testing Catches These

```python
def test_balanced_accuracy_simple():
    """Verify formula with hand-calculated example."""
    # Known case: 75% recall class 0, 66.7% recall class 1
    cm = np.array([[3, 1], [2, 4]])
    
    ba = compute_balanced_accuracy(cm)
    expected = (0.75 + 4/6) / 2  # 0.708
    
    assert abs(ba - expected) < 0.001, f"Expected {expected}, got {ba}"
```

---

## Part 2: Running the Test Suite

### Location

Tests are in: `stats/Opus4.5_stats/phase_1/tests/test_phase1_stats.py`

### Using pytest

```bash
# Run all tests
pytest stats/Opus4.5_stats/phase_1/tests/ -v

# Run specific test file
pytest stats/Opus4.5_stats/phase_1/tests/test_phase1_stats.py -v

# Run specific test class
pytest stats/Opus4.5_stats/phase_1/tests/test_phase1_stats.py::TestUnivariateMetrics -v

# Run specific test
pytest stats/Opus4.5_stats/phase_1/tests/test_phase1_stats.py::TestUnivariateMetrics::test_confusion_matrix_basic -v
```

### Using unittest (built-in)

```bash
# Run all tests
python -m unittest stats.Opus4.5_stats.phase_1.tests.test_phase1_stats -v

# Run from the tests directory
cd stats/Opus4.5_stats/phase_1/tests
python -m unittest test_phase1_stats -v
```

### Expected Output

```
test_balanced_accuracy (test_phase1_stats.TestUnivariateMetrics) ... ok
test_confusion_matrix_basic (test_phase1_stats.TestUnivariateMetrics) ... ok
test_confusion_matrix_empty_raises (test_phase1_stats.TestUnivariateMetrics) ... ok
...
----------------------------------------------------------------------
Ran 25 tests in 0.342s

OK
```

---

## Part 3: Understanding the Test Structure

### Test Classes

The test file is organized into logical groups:

```python
class TestUnivariateMetrics(unittest.TestCase):
    """Test univariate metric computations."""
    
class TestMultivariateTests(unittest.TestCase):
    """Test multivariate comparison tests."""
    
class TestPairedTests(unittest.TestCase):
    """Test paired t-tests and effect sizes."""
    
class TestInputValidation(unittest.TestCase):
    """Test input validation across all modules."""
    
class TestDemoDataReproducibility(unittest.TestCase):
    """Test that demo data produces consistent results."""
    
class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
```

### Anatomy of a Test

```python
def test_confusion_matrix_basic(self):
    """Test confusion matrix computation."""
    # 1. ARRANGE: Set up test data
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0])
    
    # 2. ACT: Call the function
    cm = compute_confusion_matrix(y_true, y_pred, num_classes=2)
    
    # 3. ASSERT: Check the result
    expected = np.array([[3, 1], [2, 4]])
    np.testing.assert_array_equal(cm, expected)
```

### The `setUp` Method

```python
class TestUnivariateMetrics(unittest.TestCase):
    def setUp(self):
        """Set up test data - runs before EACH test."""
        self.y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
        self.y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0, 0])
        self.num_classes = 2
    
    def test_something(self):
        # self.y_true, self.y_pred are available here
        cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
        ...
```

---

## Part 4: Types of Tests

### 1. Happy Path Tests

Test normal, expected inputs:

```python
def test_macro_f1(self):
    """Test macro F1 computation."""
    cm = compute_confusion_matrix(self.y_true, self.y_pred, self.num_classes)
    _, _, f1, _ = compute_per_class_metrics(cm)
    macro = compute_macro_f1(f1)
    
    # Should be average of per-class F1 scores
    expected = np.mean(list(f1.values()))
    self.assertAlmostEqual(macro, expected, places=4)
```

### 2. Edge Case Tests

Test boundary conditions:

```python
def test_single_class_predictions(self):
    """Test when all predictions are one class."""
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 0, 0])  # All predicted as class 0
    
    results = compute_all_univariate_metrics(y_true, y_pred, 2, ["A", "B"])
    
    # Class 1 should have 0 precision (no predictions)
    self.assertEqual(results.precision[1], 0.0)
    # Class 1 should have 0 recall (none correct)
    self.assertEqual(results.recall[1], 0.0)
```

### 3. Error Case Tests

Test that errors are raised properly:

```python
def test_confusion_matrix_empty_raises(self):
    """Test that empty arrays raise ValueError."""
    with self.assertRaises(ValueError):
        compute_confusion_matrix(np.array([]), np.array([]), 2)

def test_confusion_matrix_length_mismatch_raises(self):
    """Test that mismatched array lengths raise ValueError."""
    with self.assertRaises(ValueError):
        compute_confusion_matrix(np.array([0, 1]), np.array([0]), 2)
```

### 4. Reproducibility Tests

Test that results are consistent:

```python
def test_demo_data_consistency(self):
    """Test demo data produces same results with same seed."""
    data1 = generate_demo_data()
    data2 = generate_demo_data()
    
    np.testing.assert_array_equal(data1['y_true'], data2['y_true'])
    np.testing.assert_array_equal(data1['pred_a'], data2['pred_a'])
```

---

## Part 5: Key Tests Explained

### Testing Precision/Recall/F1

```python
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
```

**Why this works**: We can hand-calculate the expected values from the confusion matrix.

### Testing Cohen's Kappa

```python
def test_cohens_kappa_perfect_agreement(self):
    """Test Cohen's Kappa with perfect agreement."""
    result = cohens_kappa(self.pred_a, self.pred_a, self.num_classes)
    
    self.assertAlmostEqual(result.kappa, 1.0, places=4)
    self.assertEqual(result.interpretation, "Almost Perfect")
```

**Why this works**: Perfect agreement (model compared to itself) must give κ = 1.0.

### Testing BH Correction

```python
def test_benjamini_hochberg_basic(self):
    """Test Benjamini-Hochberg correction."""
    p_values = [0.001, 0.01, 0.02, 0.03, 0.05, 0.10, 0.50]
    
    significant = benjamini_hochberg_correction(p_values, alpha=0.05)
    
    # First few should be significant
    self.assertTrue(significant[0])  # 0.001
    self.assertTrue(significant[1])  # 0.01
    
    # Last ones should not be significant
    self.assertFalse(significant[-1])  # 0.50
```

**Why this works**: Very small p-values should always survive correction.

---

## Part 6: Writing Your Own Tests

### Template

```python
def test_[what]_[condition](self):
    """[Description of what is being tested]."""
    # Arrange
    input_data = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    self.assertEqual(result, expected_value)
```

### Example: New Edge Case

Let's add a test for a 3-class problem:

```python
def test_three_class_problem(self):
    """Test with 3 classes."""
    y_true = np.array([0, 0, 1, 1, 2, 2])
    y_pred = np.array([0, 1, 1, 2, 2, 0])
    
    cm = compute_confusion_matrix(y_true, y_pred, 3)
    
    # Check shape
    self.assertEqual(cm.shape, (3, 3))
    # Check total
    self.assertEqual(cm.sum(), 6)
    # Check specific cells
    self.assertEqual(cm[0, 0], 1)  # Class 0: 1 correct
    self.assertEqual(cm[1, 1], 1)  # Class 1: 1 correct
    self.assertEqual(cm[2, 2], 1)  # Class 2: 1 correct
```

### Example: Testing a Bug Fix

If you fix a bug, add a test to prevent regression:

```python
def test_division_by_zero_empty_class(self):
    """Regression test: division by zero when a class has no samples."""
    # Bug: crashed when computing precision for class with no predictions
    y_true = np.array([0, 0, 0])  # Only class 0
    y_pred = np.array([0, 0, 0])  # All correct
    
    cm = compute_confusion_matrix(y_true, y_pred, 2)
    
    # Should not crash, should return 0 for class 1
    prec_1 = compute_precision(cm, 1)
    self.assertEqual(prec_1, 0.0)
```

---

## Part 7: Test-Driven Development (TDD)

### The TDD Cycle

1. **Write a failing test** for the feature you want
2. **Write minimal code** to make the test pass
3. **Refactor** to improve the code
4. Repeat

### Example: Adding a New Metric

**Step 1: Write the test first**

```python
def test_specificity(self):
    """Test specificity computation."""
    cm = np.array([[90, 10], [5, 95]])
    
    # Specificity for class 0 = TN / (TN + FP) = 95 / (95 + 10) = 0.905
    spec_0 = compute_specificity(cm, 0)
    self.assertAlmostEqual(spec_0, 0.905, places=3)
```

**Step 2: Run the test (it fails)**

```bash
$ pytest test_phase1_stats.py::test_specificity -v
FAILED - NameError: name 'compute_specificity' is not defined
```

**Step 3: Implement the function**

```python
def compute_specificity(cm: np.ndarray, class_idx: int) -> float:
    """Compute specificity (true negative rate) for a class."""
    # TN = all correct predictions for OTHER classes
    tn = np.trace(cm) - cm[class_idx, class_idx]
    # FP = predictions for this class that were wrong
    fp = cm[:, class_idx].sum() - cm[class_idx, class_idx]
    
    denominator = tn + fp
    return float(tn / denominator) if denominator > 0 else 0.0
```

**Step 4: Run the test (it passes)**

```bash
$ pytest test_phase1_stats.py::test_specificity -v
PASSED
```

---

## Part 8: Running Tests in CI/CD

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r stats/Opus4.5_stats/phase_1/requirements.txt
          pip install pytest
      
      - name: Run tests
        run: pytest stats/Opus4.5_stats/phase_1/tests/ -v
```

### Local Pre-Commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running tests..."
pytest stats/Opus4.5_stats/phase_1/tests/ -q

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

---

## Part 9: Code Coverage

### What is Coverage?

Coverage measures what percentage of your code is executed by tests.

### Running with Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage report
pytest stats/Opus4.5_stats/phase_1/tests/ --cov=stats.Opus4.5_stats.phase_1 --cov-report=term-missing
```

### Example Output

```
----------- coverage: ----------
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
stats/Opus4.5_stats/phase_1/univariate.py    120      5    96%   45-49
stats/Opus4.5_stats/phase_1/multivariate.py  150     12    92%   88-99
stats/Opus4.5_stats/phase_1/paired_tests.py   95      3    97%   78-80
-----------------------------------------------------------------------
TOTAL                                        365     20    95%
```

### Target Coverage

- **80%+**: Good for most projects
- **90%+**: High confidence
- **100%**: Often impractical; focus on critical paths

---

## Part 10: Debugging Failed Tests

### Reading Test Failures

```
FAILED test_phase1_stats.py::TestUnivariateMetrics::test_macro_f1
    AssertionError: 0.697 != 0.7 within 4 decimal places
    
    Expected: 0.7000
    Actual:   0.6970
```

### Debugging Steps

1. **Read the error message** — What exactly failed?
2. **Check expected vs actual** — Is the expected value correct?
3. **Print intermediate values** — Add print statements
4. **Run in isolation** — Test just that one test

```bash
# Run just one test with print output
pytest test_phase1_stats.py::TestUnivariateMetrics::test_macro_f1 -v -s
```

### Using pdb

```python
def test_problematic_function(self):
    import pdb; pdb.set_trace()  # Debugger stops here
    
    result = function_under_test(...)
    self.assertEqual(result, expected)
```

---

## Exercise: Write a Test

### Task

Write a test for this scenario:
- Two models that always predict the **opposite** of each other
- Cohen's Kappa should be **negative** (worse than chance)

### Starter Code

```python
def test_perfect_disagreement(self):
    """Test Kappa with perfect disagreement."""
    pred_a = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    pred_b = np.array([1, 1, 1, 1, 0, 0, 0, 0])  # Opposite
    
    result = cohens_kappa(pred_a, pred_b, num_classes=2)
    
    # TODO: What should you assert here?
    # Hint: Kappa should be negative
```

### Solution

```python
def test_perfect_disagreement(self):
    """Test Kappa with perfect disagreement."""
    pred_a = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    pred_b = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    
    result = cohens_kappa(pred_a, pred_b, 2)
    
    self.assertLess(result.kappa, 0)  # Negative kappa
    self.assertEqual(result.agreement_observed, 0.0)  # No agreement
```

---

## Summary

| Concept | Purpose |
|---------|---------|
| **Unit tests** | Verify individual functions work |
| **Edge case tests** | Check boundary conditions |
| **Error tests** | Verify proper error handling |
| **TDD** | Write tests before code |
| **Coverage** | Measure test completeness |

---

## Self-Check Questions

1. Why is testing especially important for statistical code?
2. What's the difference between a happy path test and an edge case test?
3. How do you run just one specific test?
4. What does code coverage measure?

---

## Comprehension Scale

Rate your understanding:

- **1** — I'm confused and need more explanation
- **2** — I kind of get it but have questions
- **3** — I understand and am ready to continue

---

## Congratulations!

You've completed the Phase 1 Statistical Analysis tutorial series! You now understand:

1. ✓ Package structure and imports
2. ✓ Univariate metrics (F1, precision, recall, balanced accuracy)
3. ✓ Multivariate tests (Stuart-Maxwell, McNemar, Cohen's Kappa)
4. ✓ Paired tests with BH correction
5. ✓ Visualization
6. ✓ Running the analysis pipeline
7. ✓ Testing your code

### Next Steps

- Run the demo analysis and explore the results
- Apply the analysis to your own model comparison data
- Extend the test suite with additional edge cases
- Consider contributing improvements back to the codebase

**Happy analyzing!**
