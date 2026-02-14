# Phase 1 Statistical Analysis

**Project**: Reachy Emotion Recognition  
**Version**: 1.0.0  
**Last Updated**: 2026-01-28

---

## Overview

This module provides statistical analysis tools for evaluating emotion classification model performance in Phase 1 of the Reachy project. It includes:

1. **Quality Gate Metrics** — Univariate evaluation against pass/fail thresholds
2. **Stuart-Maxwell Test** — Multivariate comparison of prediction patterns
3. **Per-class Paired t-Tests** — Identification of which emotion classes changed

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r stats/requirements-stats.txt
```

### Run Demo

```bash
# Quality gate evaluation
python stats/scripts/01_quality_gate_metrics.py --demo

# Stuart-Maxwell test
python stats/scripts/02_stuart_maxwell_test.py --demo

# Per-class paired t-tests
python stats/scripts/03_perclass_paired_ttests.py --demo
```

---

## Directory Structure

```
stats/
├── README.md                    # This file
├── requirements-stats.txt       # Python dependencies
├── task_checklist.md           # Implementation checklist
│
├── scripts/                    # Python analysis scripts
│   ├── __init__.py
│   ├── 01_quality_gate_metrics.py
│   ├── 02_stuart_maxwell_test.py
│   └── 03_perclass_paired_ttests.py
│
├── curriculum/                 # Learning materials
│   ├── CURRICULUM_INDEX.md     # Start here
│   ├── TUTORIAL_01_UNIVARIATE_METRICS.md
│   ├── TUTORIAL_02_STUART_MAXWELL.md
│   └── TUTORIAL_03_PAIRED_TTESTS.md
│
├── data/                       # Sample input data (gitignored)
│   └── .gitkeep
│
└── results/                    # Output files (gitignored)
    └── .gitkeep
```

---

## Analysis Pipeline

### Step 1: Quality Gate Evaluation

Evaluate a single model against quality thresholds.

```bash
# With real predictions
python stats/scripts/01_quality_gate_metrics.py \
    --predictions results/predictions.npz \
    --model-name "enet_b0_8_best_vgaf"

# Demo mode
python stats/scripts/01_quality_gate_metrics.py --demo
```

**Quality Gates:**
| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Macro F1 | ≥ 0.84 | Overall classification quality |
| Balanced Accuracy | ≥ 0.82 | Class imbalance protection |
| F1 Neutral | ≥ 0.80 | Phase 2 baseline stability |

### Step 2: Stuart-Maxwell Test

Compare prediction patterns between base and fine-tuned models.

```bash
# With real predictions
python stats/scripts/02_stuart_maxwell_test.py \
    --predictions results/paired_predictions.npz

# Demo mode
python stats/scripts/02_stuart_maxwell_test.py --demo
```

**Input format** (`paired_predictions.npz`):
```python
np.savez('paired_predictions.npz',
    base_preds=base_model_predictions,      # shape: [n_samples]
    finetuned_preds=finetuned_predictions   # shape: [n_samples]
)
```

### Step 3: Per-class Paired t-Tests

Identify which emotion classes changed significantly.

```bash
# With real fold metrics
python stats/scripts/03_perclass_paired_ttests.py \
    --metrics results/fold_metrics.json

# Demo mode
python stats/scripts/03_perclass_paired_ttests.py --demo
```

**Input format** (`fold_metrics.json`):
```json
{
  "base_metrics": {
    "anger": [0.82, 0.84, 0.81, ...],
    "contempt": [0.65, 0.68, 0.63, ...],
    ...
  },
  "finetuned_metrics": {
    "anger": [0.84, 0.86, 0.83, ...],
    "contempt": [0.73, 0.76, 0.71, ...],
    ...
  }
}
```

---

## Decision Tree

```
┌─────────────────────────────────────────┐
│  Evaluate Base Model (Quality Gates)    │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │ FAIL              │ PASS
        ▼                   ▼
┌───────────────┐   ┌───────────────────────┐
│ Improve model │   │ Fine-tune with        │
│ before proceed│   │ synthetic data        │
└───────────────┘   └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Stuart-Maxwell Test   │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │ NOT SIGNIFICANT │                 │ SIGNIFICANT
              ▼                 │                 ▼
    ┌─────────────────┐         │       ┌─────────────────────┐
    │ No effect       │         │       │ Per-class t-Tests   │
    │ detected        │         │       └──────────┬──────────┘
    └─────────────────┘         │                  │
                                │                  ▼
                                │       ┌─────────────────────┐
                                │       │ Identify improved/  │
                                │       │ degraded classes    │
                                │       └─────────────────────┘
```

---

## Curriculum

For learning materials, see [curriculum/CURRICULUM_INDEX.md](curriculum/CURRICULUM_INDEX.md).

### Tutorials

| Tutorial | Topic | Duration |
|----------|-------|----------|
| [01](curriculum/TUTORIAL_01_UNIVARIATE_METRICS.md) | Univariate Quality Gate Metrics | 2-3 hours |
| [02](curriculum/TUTORIAL_02_STUART_MAXWELL.md) | Stuart-Maxwell Test | 3-4 hours |
| [03](curriculum/TUTORIAL_03_PAIRED_TTESTS.md) | Per-class Paired t-Tests | 3-4 hours |

Each tutorial includes:
- Three-tier explanations (middle school → college → graduate level)
- Mathematical equations
- Script walkthrough
- Output interpretation
- Practice exercises

---

## Output Files

All scripts generate:
- **Console output**: Human-readable summary
- **JSON file**: Machine-readable detailed results
- **Visualizations** (optional): PNG charts

Example outputs:
```
results/
├── demo_quality_gate_metrics.json
├── demo_confusion_matrix.png
├── demo_per_class_f1.png
├── demo_stuart_maxwell_results.json
├── demo_contingency_heatmap.png
├── demo_marginal_differences.png
├── demo_perclass_ttests_results.json
├── demo_perclass_comparison.png
└── demo_effect_sizes.png
```

---

## Integration with Project

### From Training Pipeline

After training, save predictions for analysis:

```python
import numpy as np

# After evaluation
np.savez('results/predictions.npz',
    y_true=test_labels,
    y_pred=model_predictions
)

# For model comparison
np.savez('results/paired_predictions.npz',
    base_preds=base_model_preds,
    finetuned_preds=finetuned_preds
)
```

### From Cross-Validation

Save fold-level metrics:

```python
import json

fold_metrics = {
    "base_metrics": {cls: [] for cls in EMOTION_CLASSES},
    "finetuned_metrics": {cls: [] for cls in EMOTION_CLASSES}
}

for fold in range(K):
    # ... compute per-class F1 for this fold ...
    for cls in EMOTION_CLASSES:
        fold_metrics["base_metrics"][cls].append(base_f1[cls])
        fold_metrics["finetuned_metrics"][cls].append(ft_f1[cls])

with open('results/fold_metrics.json', 'w') as f:
    json.dump(fold_metrics, f, indent=2)
```

---

## References

### Project Documentation
- [AGENTS.md](../AGENTS.md) — Agent roles and system architecture
- [requirements.md](../memory-bank/requirements.md) — Full project requirements
- [Quality Gates](../memory-bank/requirements.md#7-model-deployment--quality-gates) — Gate A/B/C definitions

### Statistical References
- Stuart, A. (1955). A test for homogeneity of the marginal distributions in a two-way classification. *Biometrika*, 42(3/4), 412-416.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *Journal of the Royal Statistical Society*, 57(1), 289-300.

---

## Contributing

1. Follow existing code style (type hints, docstrings)
2. Add tests for new functionality
3. Update curriculum if adding new methods
4. Tag issues with `stats` and `curriculum`

---

**Maintained by**: Reachy Emotion Team  
**Contact**: rustybee255@gmail.com
