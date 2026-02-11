# Phase 1 Completion Tutorials

> **Audience**: Junior engineer on their first ML project
> **Goal**: Complete all remaining Phase 1 components for Reachy_Local_08.4.2
> **Generated**: 2026-02-10 by Claude Opus 4.6

---

## How to Use These Tutorials

Work through them **in order by priority**. Each tutorial is self-contained
with prerequisites listed at the top. You can complete one per day or batch
them — but always finish all HIGH priority tutorials before moving to MEDIUM.

---

## HIGH Priority (Phase 1 Blocking)

These must be completed before Phase 1 can be considered done.
**Estimated total: 5-7 working days**

| # | Tutorial | Est. Hours | What You'll Build |
|---|----------|-----------|-------------------|
| 1 | [Face Detection](high/01_face_detection.md) | 12-16 | Replace stub `_crop_face()` with real MTCNN face detector |
| 2 | [HSEmotion Weight Verification](high/02_hsemotion_verification.md) | 4-6 | Test that proves correct pretrained weights load |
| 3 | [Promotion Service Audit](high/03_promotion_service_audit.md) | 4-6 | Verify and test the existing promotion pipeline |
| 4 | [Stratified Dataset Splitting](high/04_stratified_splitting.md) | 3-4 | Replace naive shuffle with sklearn stratified split |
| 5 | [Execute a Training Run](high/05_training_run.md) | 8-12 | First real training run that passes Gate A |
| 6 | [Alembic Migration Consolidation](high/06_alembic_consolidation.md) | 4-6 | Fix dual configs, add missing table migrations |

---

## MEDIUM Priority (Reliability & Documentation)

Complete these after all HIGH tutorials pass.
**Estimated total: 5-7 working days**

| # | Tutorial | Est. Hours | What You'll Build |
|---|----------|-----------|-------------------|
| 7 | [CI/CD Pipeline](medium/07_ci_cd_pipeline.md) | 4-6 | GitHub Actions running tests on every PR |
| 8 | [Web UI — Train Page](medium/08_web_train_page.md) | 12-16 | Training submission and monitoring in Streamlit |
| 9 | [Web UI — Generate Page](medium/09_web_generate_page.md) | 6-8 | Wire up Luma AI video generation |
| 10 | [Shared API Contracts](medium/10_shared_contracts.md) | 6-8 | Centralize Pydantic models |
| 11 | [Test Documentation](medium/11_test_documentation.md) | 4-6 | TESTING.md + pytest markers |
| 12 | [Batch Video Operations](medium/12_batch_operations.md) | 6-8 | Implement batch label/delete in Video Management |

---

## LOW Priority (Polish & Future Phases)

Nice-to-have improvements. Can be deferred.
**Estimated total: 3-5 working days (excluding n8n)**

| # | Tutorial | Est. Hours | What You'll Build |
|---|----------|-----------|-------------------|
| 13 | [Web UI — Deploy Page](low/13_web_deploy_page.md) | 4-6 | Basic deployment status display |
| 14 | [pyproject.toml Cleanup](low/14_pyproject_cleanup.md) | 2-3 | Fix version, add missing deps, entry points |
| 15 | [Legacy File Cleanup](low/15_legacy_cleanup.md) | 1-2 | Remove backup files, dead imports |

---

## Prerequisites

Before starting any tutorial, ensure:

1. **Python 3.12** is installed (`python3 --version`)
2. **Project dependencies** are installed:
   ```bash
   cd /home/rusty_admin/projects/reachy_08.4.2
   pip install -e ".[dev,web,trainer]"
   ```
3. **PostgreSQL** is running on Ubuntu 1 (10.0.4.130:5432)
4. **Git** — you're on the `opus-phase-1-stats-v2` branch
5. You've read `CLAUDE.md` at the project root

---

## Key Concepts for Your First ML Project

If you're new to machine learning, here are the concepts you'll encounter:

- **Transfer learning**: Using a model trained on one task (face recognition)
  and adapting it for another (emotion classification)
- **Fine-tuning**: Unfreezing parts of a pretrained model and training them
  on your specific data
- **F1 score**: A metric that balances precision and recall (0-1, higher is better)
- **ECE (Expected Calibration Error)**: How well the model's confidence
  matches its actual accuracy (0-1, lower is better)
- **Gate A**: Quality thresholds your model must pass before deployment
- **Epoch**: One complete pass through all training data
- **Batch**: A small group of samples processed together

---

## Getting Help

- Read `CLAUDE.md` for project architecture
- Read `memory-bank/requirements.md` for detailed requirements
- Check `docs/endpoints.md` for API reference
- Run `pytest tests/apps/api/ -v` to verify your environment works
