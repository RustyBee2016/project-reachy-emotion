# Phase 1 Statistical Analysis - Task Checklist

**Project**: Reachy Emotion Recognition  
**Branch**: `capstone-stats-phase-1`  
**Created**: 2026-01-28  
**Purpose**: Implement statistical analysis scripts and curriculum for Phase 1 emotion classification model evaluation

---

## Overview

This checklist tracks the implementation of statistical analysis tools for comparing the base model (`enet_b0_8_best_vgaf`) against a fine-tuned version trained on synthetic video data.

### Statistical Methods

| Method | Purpose | Script |
|--------|---------|--------|
| Univariate Quality Gates | Pass/fail evaluation against thresholds | `01_quality_gate_metrics.py` |
| Stuart-Maxwell Test | Detect systematic prediction pattern changes | `02_stuart_maxwell_test.py` |
| Per-class Paired t-Tests | Identify which emotion classes changed | `03_perclass_paired_ttests.py` |

---

## Implementation Tasks

### Phase 1: Directory Structure and Dependencies

- [x] Create `stats/` directory structure
- [x] Create `stats/scripts/` for Python scripts
- [x] Create `stats/curriculum/` for tutorials
- [x] Create `stats/data/` for sample data
- [x] Create `stats/results/` for output files
- [x] Create `requirements-stats.txt` with dependencies

### Phase 2: Script 1 - Univariate Quality Gate Metrics

- [x] Create `stats/scripts/01_quality_gate_metrics.py`
  - [x] Implement Macro F1 calculation
  - [x] Implement Balanced Accuracy calculation
  - [x] Implement Per-class F1 (especially Neutral) calculation
  - [x] Implement quality gate pass/fail logic
  - [x] Add confusion matrix generation
  - [x] Add visualization functions
  - [x] Add demo mode with synthetic data
  - [x] Add comprehensive docstrings

### Phase 3: Script 2 - Stuart-Maxwell Test

- [x] Create `stats/scripts/02_stuart_maxwell_test.py`
  - [x] Implement contingency table construction
  - [x] Implement marginal difference calculation
  - [x] Implement covariance matrix computation
  - [x] Implement chi-squared test statistic
  - [x] Implement p-value calculation
  - [x] Add interpretation helper functions
  - [x] Add demo mode with synthetic data
  - [x] Add comprehensive docstrings

### Phase 4: Script 3 - Per-class Paired t-Tests

- [x] Create `stats/scripts/03_perclass_paired_ttests.py`
  - [x] Implement paired t-test for each emotion class
  - [x] Implement Benjamini-Hochberg correction
  - [x] Implement results summary table
  - [x] Add visualization of per-class changes
  - [x] Add demo mode with synthetic data
  - [x] Add comprehensive docstrings

### Phase 5: Curriculum - Tutorial Index

- [x] Create `stats/curriculum/CURRICULUM_INDEX.md`
  - [x] Overview of statistical analysis for Phase 1
  - [x] Learning objectives
  - [x] Prerequisites
  - [x] Tutorial sequence

### Phase 6: Tutorial 1 - Univariate Metrics

- [x] Create `stats/curriculum/TUTORIAL_01_UNIVARIATE_METRICS.md`
  - [x] Middle-school level explanation
  - [x] College freshman explanation
  - [x] Graduate-level explanation with equations
  - [x] Script walkthrough with annotated code
  - [x] Output interpretation guide
  - [x] Practice exercises

### Phase 7: Tutorial 2 - Stuart-Maxwell Test

- [x] Create `stats/curriculum/TUTORIAL_02_STUART_MAXWELL.md`
  - [x] Middle-school level explanation
  - [x] College freshman explanation
  - [x] Graduate-level explanation with equations
  - [x] Script walkthrough with annotated code
  - [x] Output interpretation guide
  - [x] Practice exercises

### Phase 8: Tutorial 3 - Per-class Paired t-Tests

- [x] Create `stats/curriculum/TUTORIAL_03_PAIRED_TTESTS.md`
  - [x] Middle-school level explanation
  - [x] College freshman explanation
  - [x] Graduate-level explanation with equations
  - [x] Script walkthrough with annotated code
  - [x] Output interpretation guide
  - [x] Practice exercises

### Phase 9: Integration and Testing

- [ ] Create `stats/scripts/run_full_analysis.py` (orchestrator)
- [ ] Test all scripts with synthetic data
- [ ] Verify output formats are consistent
- [ ] Create sample output files in `stats/results/`

### Phase 10: Documentation

- [x] Create `stats/README.md` with usage instructions
- [ ] Update `memory-bank/index.md` with stats curriculum links
- [ ] Commit all files to branch

---

## Quality Gates (from requirements.md)

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Macro F1 | ≥ 0.84 | Overall classification quality |
| Balanced Accuracy | ≥ 0.82 | Class imbalance protection |
| F1 (Neutral) | ≥ 0.80 | Phase 2 baseline stability |

---

## Dependencies

```
numpy>=1.24.0
scipy>=1.11.0
pandas>=2.0.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
statsmodels>=0.14.0
```

---

## Notes

- All scripts include demo mode for testing without real model predictions
- Tutorials are tiered for different experience levels
- Scripts output both console summaries and JSON files for programmatic use
