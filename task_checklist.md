# Task Checklist: Reachy Mini Integration with Emotion-Driven LLM & Gestures

**Project:** Reachy_Local_08.4.2  
**Created:** 2026-01-11  
**Status:** In Progress

---

## Phase 1: Environment Setup

- [x] **1.1** Configure Python 3.12 as default interpreter (Windows)
  - Install Python 3.12 if not present
  - Update PATH and `py` launcher defaults
  - Verify with `python --version`

- [x] **1.2** Update `pyproject.toml` to require Python 3.12
  - Change `requires-python` constraint

---

## Phase 2: Reachy SDK Integration

- [x] **2.1** Create `apps/reachy/` module structure
  - `__init__.py`
  - `config.py` - Reachy connection settings
  - `gestures/` - Gesture definitions and controller

- [x] **2.2** Implement Reachy gesture controller
  - `gestures/gesture_definitions.py` - Define gesture primitives (wave, nod, shrug, etc.)
  - `gestures/gesture_controller.py` - Interface with Reachy SDK for arm/head movements
  - `gestures/emotion_gesture_map.py` - Map emotions to appropriate gestures

---

## Phase 3: LLM Integration (GPT-5.2)

- [x] **3.1** Create `apps/llm/` module structure
  - `__init__.py`
  - `config.py` - OpenAI API configuration
  - `client.py` - GPT-5.2 API client

- [x] **3.2** Implement empathetic prompt engine
  - `prompts/emotion_prompts.py` - Emotion-aware system prompts
  - `prompts/gesture_keywords.py` - Keywords that trigger gestures

- [x] **3.3** Implement LLM response processor
  - `response_parser.py` - Parse LLM responses for gesture keywords
  - `emotion_adapter.py` - Adapt LLM behavior based on detected emotion

---

## Phase 4: Emotion → LLM → Gesture Pipeline

- [x] **4.1** Create pipeline orchestrator
  - `apps/pipeline/emotion_llm_gesture.py` - Main pipeline coordinator
  - Receive emotion events from Jetson
  - Send emotion context to LLM
  - Parse response for gesture cues
  - Dispatch gestures to Reachy

- [x] **4.2** Update Jetson emotion client
  - Extend `jetson/emotion_client.py` to handle gesture cues
  - Add callback mechanism for gesture dispatch

- [x] **4.3** Create WebSocket cue handler
  - Handle `cue` events from gateway
  - Route gesture commands to Reachy controller

---

## Phase 5: Testing

- [x] **5.1** Unit tests for gesture mapping
  - `tests/test_gesture_definitions.py`
  - `tests/test_emotion_gesture_map.py`

- [x] **5.2** Unit tests for LLM integration
  - `tests/test_llm_client.py`
  - `tests/test_response_parser.py`
  - `tests/test_emotion_prompts.py`

- [x] **5.3** Integration tests for pipeline
  - `tests/test_emotion_llm_gesture_pipeline.py`
  - Mock emotion events → verify gesture output

---

## Phase 6: Documentation & Memory Bank

- [x] **6.1** Update `AGENTS.md` with new Reachy gesture agent
- [ ] **6.2** Update `memory-bank/requirements.md` with LLM/gesture specs
- [x] **6.3** Create decision record for GPT-5.2 model selection
- [ ] **6.4** Update `README.md` with Reachy Mini setup instructions

---

## Notes

- **LLM Model:** GPT-5.2 (best for empathetic, nuanced responses)
- **Reachy SDK:** Requires Python 3.12
- **Gesture Keywords:** Parsed from LLM responses (e.g., `[WAVE]`, `[NOD]`, `[HUG]`)
- **Privacy:** All processing local-first; LLM API calls are the only external dependency
