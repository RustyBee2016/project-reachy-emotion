# Phase 1 Statistical Analysis Tutorial Series

Welcome to the tutorial series for the Phase 1 Statistical Analysis package. This series is designed for junior data scientists joining the Reachy emotion recognition team.

---

## Prerequisites

- Python 3.8+
- Basic Python programming (functions, classes, dictionaries)
- Basic statistics knowledge (mean, standard deviation, hypothesis testing)
- Understanding of classification problems

## Quick Setup

```bash
# Install dependencies
pip install -r ../phase_1/requirements.txt

# Verify installation
python -c "from stats.Opus4.5_stats import phase_1; print('Success!')"
```

---

## Tutorial Index

| # | Tutorial | File | Time | Topics |
|---|----------|------|------|--------|
| 00 | [Overview and Setup](00_overview_and_setup.md) | — | 20 min | Package overview, data format, Gate A |
| 01 | [Package Structure](01_package_structure.md) | `__init__.py` | 15 min | Python packages, imports, `__all__` |
| 02 | [Univariate Metrics](02_univariate_metrics.md) | `univariate.py` | 45 min | Confusion matrix, F1, precision, recall |
| 03 | [Multivariate Tests](03_multivariate_tests.md) | `multivariate.py` | 60 min | Stuart-Maxwell, McNemar, Cohen's Kappa |
| 04 | [Paired Tests](04_paired_tests.md) | `paired_tests.py` | 45 min | Paired t-test, Cohen's d, BH correction |
| 05 | [Visualization](05_visualization.md) | `visualization.py` | 30 min | Heatmaps, bar charts, effect size plots |
| 06 | [Running Analysis](06_running_analysis.md) | `run_analysis.py` | 30 min | CLI usage, batch processing, exports |
| 07 | [Testing](07_testing.md) | `test_phase1_stats.py` | 30 min | Unit tests, TDD, coverage |

**Total estimated time: ~4.5 hours**

---

## Recommended Learning Path

### Day 1: Foundations (2 hours)
1. Complete Tutorial 00 (Overview)
2. Complete Tutorial 01 (Package Structure)
3. Complete Tutorial 02 (Univariate Metrics)

### Day 2: Model Comparison (2 hours)
4. Complete Tutorial 03 (Multivariate Tests)
5. Complete Tutorial 04 (Paired Tests)

### Day 3: Practical Application (1.5 hours)
6. Complete Tutorial 05 (Visualization)
7. Complete Tutorial 06 (Running Analysis)
8. Complete Tutorial 07 (Testing)

---

## Key Concepts Quick Reference

### Gate A Thresholds
| Metric | Threshold |
|--------|-----------|
| Macro F1 | ≥ 0.84 |
| Balanced Accuracy | ≥ 0.85 |
| Per-class F1 Floor | ≥ 0.75 |

### Statistical Tests
| Test | Question Answered |
|------|-------------------|
| **Stuart-Maxwell** | Do models have different prediction patterns? |
| **McNemar's** | Is one model better for a specific class? |
| **Cohen's Kappa** | How much do models agree beyond chance? |
| **Paired t-test** | Is the F1 difference significant across CV folds? |

### Effect Size Interpretation (Cohen's d)
| \|d\| | Interpretation |
|-------|----------------|
| < 0.2 | Negligible |
| 0.2 - 0.5 | Small |
| 0.5 - 0.8 | Medium |
| ≥ 0.8 | Large |

---

## How to Use These Tutorials

### Self-Study Mode
1. Read each tutorial in order
2. Run the code examples in a Python environment
3. Answer the self-check questions
4. Rate your comprehension (1-3 scale)
5. If rating < 3, review or ask questions before proceeding

### Team Workshop Mode
1. Assign one tutorial per session
2. Have team members present key concepts
3. Work through exercises together
4. Discuss real-world applications

---

## File Mapping

```
stats/Opus4.5_stats/
├── __init__.py              ← Tutorial 01
├── phase_1/
│   ├── __init__.py          ← Tutorial 01
│   ├── univariate.py        ← Tutorial 02
│   ├── multivariate.py      ← Tutorial 03
│   ├── paired_tests.py      ← Tutorial 04
│   ├── visualization.py     ← Tutorial 05
│   ├── run_analysis.py      ← Tutorial 06
│   ├── requirements.txt     ← Tutorial 00
│   └── tests/
│       └── test_phase1_stats.py  ← Tutorial 07
└── tutorials/
    ├── README.md            ← You are here
    ├── 00_overview_and_setup.md
    ├── 01_package_structure.md
    ├── 02_univariate_metrics.md
    ├── 03_multivariate_tests.md
    ├── 04_paired_tests.md
    ├── 05_visualization.md
    ├── 06_running_analysis.md
    └── 07_testing.md
```

---

## Running Examples

### Quick Demo
```bash
python -m stats.Opus4.5_stats.phase_1.run_analysis --demo --output demo_results/
```

### Run Tests
```bash
pytest stats/Opus4.5_stats/phase_1/tests/ -v
```

---

## Getting Help

1. **Check the tutorial** — Most common questions are answered
2. **Read the docstrings** — `help(function_name)` in Python
3. **Look at the tests** — They show expected behavior
4. **Ask the team** — We're here to help!

---

## Contributing

Found an error or have a suggestion?
1. Note the tutorial number and section
2. Describe the issue or improvement
3. Submit to the team lead for review

---

Happy learning! 🎓
