# Codebase Review for Curriculum Design

## Scope Reviewed
To align the curriculum with real work, I reviewed representative modules across:
- API/Gateway services
- Web UI workflows
- ML training and evaluation pipeline
- Agentic AI orchestration
- Jetson edge runtime
- Test coverage patterns

## Key Architectural Areas

### 1) Service/API Layer
- FastAPI app composition and lifecycle exist in `apps/api/app/main.py`.
- Routing and event/promotion pathways are implemented in `apps/api/routers/gateway.py` and `apps/api/routers/media.py`.
- Config/dependency boundaries are represented in `apps/api/app/config.py`, `apps/api/app/settings.py`, and `apps/api/app/deps.py`.

**Curriculum impact:** Early weeks emphasize control flow tracing, typing, async handling, and service architecture.

### 2) Web UI + Workflow Operations
- Streamlit workflow and page orchestration sit under `apps/web/main_app.py` and `apps/web/pages/`.
- Client interactions and websocket behavior appear in `apps/web/api_client.py`, `apps/web/api_client_v2.py`, and `apps/web/websocket_client.py`.

**Curriculum impact:** Mid-foundation modules reinforce state management, API contracts, and reliability patterns.

### 3) ML Training / Evaluation Stack
- Primary training entrypoints include `trainer/train_efficientnet.py` and `trainer/fer_finetune/train_efficientnet.py`.
- Dataset prep and run management include `trainer/prepare_dataset.py` and `trainer/split_run_dataset.py`.
- Evaluation/gating logic includes `trainer/gate_a_validator.py` and `trainer/fer_finetune/evaluate.py`.
- Experiment tracking via `trainer/mlflow_tracker.py`.

**Curriculum impact:** Core middle block (Weeks 6–9) focuses on reproducibility, PyTorch internals, calibration, and MLflow ops.

### 4) Agentic AI Pipeline
- Emotion → LLM → gesture orchestration appears in `apps/pipeline/emotion_llm_gesture.py`.
- LLM client/prompt assets are in `apps/llm/client.py` and `apps/llm/prompts/`.
- Gesture mapping/control surfaces are in `apps/reachy/gestures/` and cue routing in `apps/reachy/cue_handler.py`.

**Curriculum impact:** Weeks 10–11 focus on event-driven agent design, contracts, retries, and failure handling.

### 5) Edge Runtime + Deployment
- Inference runtime and stream integration are implemented in `jetson/emotion_main.py` and `jetson/deepstream_wrapper.py`.
- Deployment validation logic exists in `jetson/gate_b_validator.py`.

**Curriculum impact:** Weeks 12–13 focus on deployment constraints, runtime profiling, and performance engineering.

### 6) Testing & Quality Culture
- Broad test suite spans API, pipeline, calibration, deployment, and integration (`tests/`).
- Useful anchors: `tests/test_training_pipeline.py`, `tests/test_run_efficientnet_pipeline_contract.py`, `tests/test_calibration_metrics.py`, `tests/test_deployment.py`, `tests/apps/api/`.

**Curriculum impact:** Testing discipline is threaded across all weeks with specific weekly validation tasks.

## Design Decisions for This Curriculum
1. **Project-first pedagogy:** every week ties directly to existing modules.
2. **Control-flow-first explanations:** each week requires explain-back of real code paths.
3. **Progressive complexity:** advanced Python → ML engineering depth → agentic reliability → edge optimization.
4. **Artifact-driven learning:** each week ends with a concrete deliverable, not just reading.
5. **Capstone integration:** week 16 requires production-like end-to-end behavior plus tests/docs.
