# Phase 1 Completion: 8-Week Learning Plan

**Project**: Reachy Emotion Recognition  
**Goal**: Complete Phase 1 (Database + Statistical Analysis)  
**Duration**: 8 weeks  
**Last Updated**: 2026-01-28

---

## Overview

This 8-week plan guides you through completing **Phase 1** of the Reachy Emotion Recognition project, which includes:

1. **Database mastery** — Understanding and working with the PostgreSQL schema
2. **Statistical analysis** — Implementing and interpreting model evaluation metrics
3. **Quality gate validation** — Ensuring models meet Gate A requirements
4. <mark>**Training pipeline basics** — Running and evaluating emotion classification training</mark>

### What This Plan Integrates

This plan combines two existing curricula:

| Curriculum               | Location                    | Duration  | Weeks |
| ------------------------ | --------------------------- | --------- | ----- |
| Database Fundamentals    | `docs/database/curriculum/` | ~28 hours | 1-4   |
| Statistical Analysis     | `stats/curriculum/`         | ~11 hours | 5-7   |
| Integration & Validation | (new content)               | ~8 hours  | 8     |

---

## Weekly Schedule

| Week | Focus                                    | Hours | Key Deliverable        |
| ---- | ---------------------------------------- | ----- | ---------------------- |
| 1    | Database Fundamentals + PostgreSQL       | 8     | SQL queries working    |
| 2    | Reachy Schema + Stored Procedures        | 7     | Schema understood      |
| 3    | SQLAlchemy ORM + API Integration         | 8     | Python DB access       |
| 4    | Migrations + Troubleshooting             | 5     | Database operational   |
| 5    | Quality Gate Metrics                     | 4     | Script 01 running      |
| 6    | Stuart-Maxwell + Paired t-Tests          | 6     | Scripts 02-03 running  |
| 7    | Calibration Metrics + Orchestration      | 5     | Full analysis pipeline |
| 8    | Gate A Validation + Training Integration | 5     | Phase 1 complete       |

**Total**: ~48 hours over 8 weeks (~6 hours/week)

---

## Prerequisites

Before starting:

- [ ] PostgreSQL 16 installed (`sudo apt install postgresql-16`)
- [ ] Python 3.10+ with pip
- [ ] Project repository cloned
- [ ] Basic Python knowledge (functions, classes)

---

## Week-by-Week Tutorials

### Weeks 1-4: Database Track

| Week | Tutorial                                                                       | Modules Covered |
| ---- | ------------------------------------------------------------------------------ | --------------- |
| 1    | [WEEK_01_DATABASE_FUNDAMENTALS.md](WEEK_01_DATABASE_FUNDAMENTALS.md)           | Modules 1-2     |
| 2    | [WEEK_02_REACHY_SCHEMA.md](WEEK_02_REACHY_SCHEMA.md)                           | Modules 3-4     |
| 3    | [WEEK_03_PYTHON_ORM.md](WEEK_03_PYTHON_ORM.md)                                 | Modules 5-6     |
| 4    | [WEEK_04_MIGRATIONS_TROUBLESHOOTING.md](WEEK_04_MIGRATIONS_TROUBLESHOOTING.md) | Modules 7-8     |

### Weeks 5-7: Statistical Analysis Track

| Week | Tutorial                                                                     | Modules Covered    |
| ---- | ---------------------------------------------------------------------------- | ------------------ |
| 5    | [WEEK_05_QUALITY_GATE_METRICS.md](WEEK_05_QUALITY_GATE_METRICS.md)           | Stats Module 1     |
| 6    | [WEEK_06_STATISTICAL_TESTS.md](WEEK_06_STATISTICAL_TESTS.md)                 | Stats Modules 2-3  |
| 7    | [WEEK_07_CALIBRATION_ORCHESTRATION.md](WEEK_07_CALIBRATION_ORCHESTRATION.md) | ECE, Brier, MLflow |

### Week 8: Integration

| Week | Tutorial                                                     | Focus             |
| ---- | ------------------------------------------------------------ | ----------------- |
| 8    | [WEEK_08_GATE_A_VALIDATION.md](WEEK_08_GATE_A_VALIDATION.md) | Gate A + Training |

---

## Learning Objectives

### By End of Week 4 (Database Complete)

- [ ] Write SQL queries (SELECT, INSERT, UPDATE, DELETE)
- [ ] Understand all 12 Reachy database tables
- [ ] Use SQLAlchemy ORM in Python
- [ ] Run database migrations
- [ ] Debug common database issues

### By End of Week 7 (Stats Complete)

- [ ] Compute Macro F1, Balanced Accuracy, F1 Neutral
- [ ] Run Stuart-Maxwell test for model comparison
- [ ] Apply Benjamini-Hochberg correction for multiple tests
- [ ] Compute ECE and Brier calibration metrics
- [ ] Run full analysis pipeline with MLflow logging

### By End of Week 8 (Phase 1 Complete)

- [ ] Validate models against Gate A requirements
- [ ] Integrate stats scripts with training pipeline
- [ ] Generate comprehensive evaluation reports
- [ ] Understand Phase 2 readiness criteria

---

## Gate A Requirements (Target)

By the end of this plan, you'll be able to validate models against:

| Metric            | Threshold            | Script                         |
| ----------------- | -------------------- | ------------------------------ |
| Macro F1          | ≥ 0.84               | `01_quality_gate_metrics.py`   |
| Balanced Accuracy | ≥ 0.85               | `01_quality_gate_metrics.py`   |
| Per-class F1      | ≥ 0.75 (floor: 0.70) | `03_perclass_paired_ttests.py` |
| ECE               | ≤ 0.08               | `01_quality_gate_metrics.py`   |
| Brier Score       | ≤ 0.16               | `01_quality_gate_metrics.py`   |

---

## Quick Start

```bash
# Week 1: Start with database setup
cd docs/database/curriculum
# Read 00-CURRICULUM-OVERVIEW.md, then 01-MODULE-DATABASE-FUNDAMENTALS.md

# Week 5: Start statistical analysis
cd stats/curriculum
# Read CURRICULUM_INDEX.md, then TUTORIAL_01_UNIVARIATE_METRICS.md

# Week 8: Run Gate A validation
python trainer/gate_a_validator.py --checkpoint outputs/best_model.pt
```

---

## Support Resources

| Resource              | Location                           |
| --------------------- | ---------------------------------- |
| Database Setup Guide  | `docs/database/08-SETUP-GUIDE.md`  |
| Database Known Issues | `docs/database/07-KNOWN-ISSUES.md` |
| Stats Scripts         | `stats/scripts/`                   |
| Stats Curriculum      | `stats/curriculum/`                |
| Project Requirements  | `memory-bank/requirements.md`      |

---

## Next Steps After Phase 1

Once Phase 1 is complete, you'll be ready for:

- **Phase 2**: n8n workflow automation, Jetson deployment
- **Phase 3**: LLM integration, gesture control
- **Production**: Full system deployment

See `docs/tutorials/` for Phase 2+ tutorials (system integration focus).

---

*Let's begin with [Week 1: Database Fundamentals](WEEK_01_DATABASE_FUNDAMENTALS.md)!*
