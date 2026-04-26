# 4-Month Python Curriculum (Intermediate → Advanced)

## Learner Profile
- **Learner:** Rusty
- **Current level:** Intermediate Python programmer with active ML engineering and data science practice
- **Target level after 16 weeks:** Advanced Python engineer for ML systems and agentic AI pipelines
- **Project anchor:** Reachy_Local_08.4.2 codebase (FastAPI, Streamlit, PyTorch, Jetson runtime, tests)

## Why this curriculum is project-aligned
This curriculum is designed from the current repository architecture and workflows:
- API and service orchestration using FastAPI (`apps/api/app/main.py`, `apps/api/routers/gateway.py`)
- Web UI and workflow operations in Streamlit (`apps/web/main_app.py`, `apps/web/pages/*.py`)
- Training + evaluation pipeline (`trainer/train_efficientnet.py`, `trainer/run_efficientnet_pipeline.py`, `trainer/gate_a_validator.py`)
- Agentic orchestration path (emotion → LLM → gesture) (`apps/pipeline/emotion_llm_gesture.py`, `apps/reachy/cue_handler.py`)
- Edge runtime/deployment concerns on Jetson (`jetson/emotion_main.py`, `jetson/deepstream_wrapper.py`, `jetson/gate_b_validator.py`)

## Structure
- **Duration:** 16 weeks (4 months)
- **Cadence:** 5 focused learning days + 1 project day + 1 review/rest day each week
- **Progression:**
  1. Advanced Python foundations and architecture patterns
  2. Production ML engineering and evaluation rigor
  3. Agentic AI systems and reliability engineering
  4. Edge deployment, optimization, and capstone integration

## Weekly Folder Map
- `week_01` to `week_16`: each includes:
  - `curriculum.md` with objectives, theory, code-reading targets, build tasks, checkpoints, and deliverables

## Assessment Model
- **Weekly checks:** syntax + control-flow explain-backs, code tracing, short implementation tasks
- **Bi-weekly milestone:** project artifact merged locally (tests, docs, or feature)
- **Monthly gate:** architecture review + production-quality demo
- **Final gate (Week 16):** end-to-end mini-release for an ML + agentic pipeline feature with tests and runbook notes

## Expected outcome at Week 16
Rusty can confidently design, explain, implement, test, and deploy advanced Python systems for ML + agentic AI, including:
- robust API/service contracts,
- reproducible training/evaluation,
- calibration and quality gates,
- event-driven agent orchestration,
- and edge-aware runtime constraints.
