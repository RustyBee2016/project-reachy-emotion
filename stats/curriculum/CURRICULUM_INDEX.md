# Phase 1 Statistical Analysis Curriculum

**Project**: Reachy Emotion Recognition  
**Version**: 1.0.0  
**Last Updated**: 2026-01-28

---

## Overview

This curriculum teaches junior engineers and data scientists how to implement and interpret statistical analysis for emotion classification model evaluation. The focus is on **Phase 1** of the Reachy project: comparing a base emotion recognition model against a fine-tuned version.

### What You'll Learn

1. **Univariate Quality Gate Metrics** — How to evaluate a single model against pass/fail thresholds
2. **Stuart-Maxwell Test** — How to detect if fine-tuning changed prediction patterns
3. **Per-class Paired t-Tests** — How to identify which specific emotion classes improved or degraded

---

## Prerequisites

### Technical Skills
- Basic Python programming (functions, classes, NumPy arrays)
- Familiarity with classification metrics (accuracy, precision, recall)
- Understanding of hypothesis testing concepts (p-values, significance)

### Software Requirements
```bash
# Install dependencies
pip install -r stats/requirements-stats.txt
```

### Recommended Background Reading
- [scikit-learn Classification Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [Understanding P-values](https://www.statsdirect.com/help/basics/p_values.htm)
- [Multiple Comparison Problem](https://en.wikipedia.org/wiki/Multiple_comparisons_problem)

---

## Learning Path

### Module 1: Univariate Quality Gate Metrics
**Duration**: 2-3 hours  
**Difficulty**: Beginner

| Resource | Description |
|----------|-------------|
| [Tutorial 01](TUTORIAL_01_UNIVARIATE_METRICS.md) | Complete guide with three explanation levels |
| [Script 01](../scripts/01_quality_gate_metrics.py) | Python implementation |
| Demo Command | `python stats/scripts/01_quality_gate_metrics.py --demo` |

**Learning Objectives**:
- Understand why Macro F1, Balanced Accuracy, and F1 Neutral are chosen
- Compute these metrics from predictions
- Interpret quality gate pass/fail results
- Read and understand the confusion matrix

---

### Module 2: Stuart-Maxwell Test
**Duration**: 3-4 hours  
**Difficulty**: Intermediate

| Resource | Description |
|----------|-------------|
| [Tutorial 02](TUTORIAL_02_STUART_MAXWELL.md) | Complete guide with three explanation levels |
| [Script 02](../scripts/02_stuart_maxwell_test.py) | Python implementation |
| Demo Command | `python stats/scripts/02_stuart_maxwell_test.py --demo` |

**Learning Objectives**:
- Understand when to use Stuart-Maxwell vs. other tests
- Build and interpret a contingency table
- Compute the test statistic and p-value
- Interpret significant vs. non-significant results

---

### Module 3: Per-class Paired t-Tests
**Duration**: 3-4 hours  
**Difficulty**: Intermediate

| Resource | Description |
|----------|-------------|
| [Tutorial 03](TUTORIAL_03_PAIRED_TTESTS.md) | Complete guide with three explanation levels |
| [Script 03](../scripts/03_perclass_paired_ttests.py) | Python implementation |
| Demo Command | `python stats/scripts/03_perclass_paired_ttests.py --demo` |

**Learning Objectives**:
- Understand paired vs. unpaired tests
- Apply Benjamini-Hochberg correction for multiple comparisons
- Interpret adjusted p-values
- Identify which emotion classes changed significantly

---

## Tutorial Structure

Each tutorial follows a consistent three-tier structure:

### Tier 1: Middle School Explanation
- Uses everyday analogies
- No mathematical notation
- Focuses on intuition

### Tier 2: College Freshman (CS) Explanation
- Introduces basic formulas
- Shows Python pseudocode
- Explains computational steps

### Tier 3: Graduate Data Science Explanation
- Full mathematical derivations
- Statistical assumptions and limitations
- Connections to broader statistical theory

---

## Practical Workflow

### Step 1: Evaluate Single Model (Quality Gates)
```bash
# Run quality gate evaluation
python stats/scripts/01_quality_gate_metrics.py --predictions results/predictions.npz
```

**Decision**: Does the model pass all three quality gates?
- **Yes** → Model is ready for deployment consideration
- **No** → Model needs improvement before proceeding

### Step 2: Compare Base vs. Fine-tuned (Stuart-Maxwell)
```bash
# Run Stuart-Maxwell test
python stats/scripts/02_stuart_maxwell_test.py --predictions results/paired_predictions.npz
```

**Decision**: Did fine-tuning change prediction patterns?
- **Significant** → Proceed to per-class analysis
- **Not Significant** → Fine-tuning had no detectable effect

### Step 3: Identify Changed Classes (Per-class t-Tests)
```bash
# Run per-class analysis
python stats/scripts/03_perclass_paired_ttests.py --metrics results/fold_metrics.json
```

**Decision**: Which classes improved or degraded?
- Use results to guide next iteration of synthetic data generation
- Pay special attention to neutral class (Phase 2 baseline)

---

## Analysis Decision Tree

```
                    ┌─────────────────────────────┐
                    │  Evaluate Base Model        │
                    │  (Quality Gate Metrics)     │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │  Pass All Gates?            │
                    └─────────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │ NO                │                   │ YES
              ▼                   │                   ▼
    ┌─────────────────┐           │         ┌─────────────────┐
    │ Improve Model   │           │         │ Fine-tune with  │
    │ Before Proceed  │           │         │ Synthetic Data  │
    └─────────────────┘           │         └────────┬────────┘
                                  │                  │
                                  │                  ▼
                                  │         ┌─────────────────┐
                                  │         │ Stuart-Maxwell  │
                                  │         │ Test            │
                                  │         └────────┬────────┘
                                  │                  │
                                  │    ┌─────────────┼─────────────┐
                                  │    │ NOT SIG     │             │ SIGNIFICANT
                                  │    ▼             │             ▼
                                  │  ┌───────────┐   │   ┌───────────────────┐
                                  │  │ No Effect │   │   │ Per-class t-Tests │
                                  │  │ Detected  │   │   └─────────┬─────────┘
                                  │  └───────────┘   │             │
                                  │                  │             ▼
                                  │                  │   ┌───────────────────┐
                                  │                  │   │ Identify Changed  │
                                  │                  │   │ Classes           │
                                  │                  │   └───────────────────┘
                                  │                  │
                                  └──────────────────┘
```

---

## Quick Reference: When to Use Each Method

| Scenario | Method | Script |
|----------|--------|--------|
| "Does this model meet our quality standards?" | Quality Gates | `01_quality_gate_metrics.py` |
| "Did fine-tuning change anything?" | Stuart-Maxwell | `02_stuart_maxwell_test.py` |
| "Which emotions improved/degraded?" | Per-class t-Tests | `03_perclass_paired_ttests.py` |

---

## Common Questions

### Q: Why not just compare accuracy?
**A**: Accuracy can be misleading with imbalanced classes. A model could achieve 80% accuracy by always predicting "happiness" if that's the most common class. Macro F1 and Balanced Accuracy protect against this.

### Q: Why use Stuart-Maxwell instead of just comparing F1 scores?
**A**: Stuart-Maxwell tests whether the *pattern* of predictions changed, not just the aggregate accuracy. Two models could have identical F1 scores but make completely different predictions on individual samples.

### Q: Why do we need multiple comparison correction?
**A**: Running 8 tests (one per emotion class) at α=0.05 gives a 34% chance of at least one false positive. Benjamini-Hochberg controls this inflation while being less conservative than alternatives like Bonferroni.

### Q: What if Stuart-Maxwell is significant but no individual classes are?
**A**: This means changes were diffuse across classes rather than concentrated. The overall pattern shifted, but no single class drove the change.

---

## Assessment Checkpoints

After completing each module, you should be able to:

### Module 1 Checkpoint
- [ ] Explain why Macro F1 is preferred over accuracy for imbalanced data
- [ ] Calculate F1 for a single class given TP, FP, FN
- [ ] Interpret a confusion matrix to identify common misclassifications
- [ ] Run the quality gate script and explain the output

### Module 2 Checkpoint
- [ ] Explain what "marginal homogeneity" means in plain terms
- [ ] Build a contingency table from paired predictions
- [ ] Interpret a significant vs. non-significant Stuart-Maxwell result
- [ ] Explain why this test uses paired data

### Module 3 Checkpoint
- [ ] Explain the difference between paired and unpaired t-tests
- [ ] Describe why multiple comparison correction is necessary
- [ ] Interpret adjusted p-values from Benjamini-Hochberg
- [ ] Identify which classes improved/degraded from the output

---

## Additional Resources

### Project Documentation
- [AGENTS.md](../../AGENTS.md) — Agent roles and system architecture
- [requirements.md](../../memory-bank/requirements.md) — Full project requirements
- [Quality Gates](../../memory-bank/requirements.md#7-model-deployment--quality-gates) — Gate A/B/C definitions

### External References
- [HSEmotion Library](https://github.com/HSE-asavchenko/face-emotion-recognition) — Base model source
- [AffectNet Dataset](http://mohammadmahoor.com/affectnet/) — Training data reference
- [scikit-learn Metrics](https://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics) — Metric implementations

---

## Feedback

If you find errors or have suggestions for improving this curriculum, please:
1. Open an issue in the project repository
2. Tag it with `curriculum` and `stats`
3. Include the specific tutorial/section reference

---

**Maintained by**: Reachy Emotion Team  
**Contact**: rustybee255@gmail.com
