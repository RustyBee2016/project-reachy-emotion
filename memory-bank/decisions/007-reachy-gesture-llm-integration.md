# ADR-007: Reachy Mini Gesture and LLM Integration

**Status:** Accepted  
**Date:** 2026-01-11  
**Author:** Russell Bray / Cascade  

---

## Context

The Reachy_Local_08.4.2 project requires integration of the Reachy Mini companion robot with emotion-driven interaction capabilities. The system must:

1. Receive real-time emotion predictions from the Jetson edge device
2. Generate empathetic LLM responses tailored to the user's emotional state
3. Execute appropriate physical gestures on the Reachy robot that complement the verbal response

This creates a cohesive human-robot interaction experience where Reachy responds both verbally and physically to the user's emotions.

---

## Decision

### LLM Model Selection: GPT-5.2

Selected **GPT-5.2** (OpenAI's flagship model) for empathetic interaction because:

- **Best general-purpose reasoning** for nuanced emotional understanding
- **Large context window** for maintaining conversation history
- **Superior language generation** for natural, empathetic responses
- **Cost-effective** compared to GPT-5.2 Pro for real-time interaction

Alternatives considered:
- GPT-5.2 Pro: More capable but higher latency and cost; overkill for emotional support
- GPT-5 Mini: Faster but less nuanced emotional understanding
- GPT-5 Nano: Too limited for empathetic conversation

### Gesture Keyword System

Implemented an **embedded keyword system** where the LLM includes gesture triggers in its responses:

```
Format: [KEYWORD] or <KEYWORD>
Example: "I hear you [LISTEN]. That sounds difficult [EMPATHY]."
```

**Supported Keywords:**
- `WAVE` - Friendly greeting
- `NOD` - Agreement/understanding
- `SHAKE` - Disagreement/concern
- `SHRUG` - Uncertainty
- `THUMBS_UP` - Encouragement
- `OPEN_ARMS` - Welcoming
- `HUG` - Deep comfort
- `THINK` - Reflection
- `EXCITED` - Celebration
- `COMFORT` - Soothing
- `LISTEN` - Active listening
- `CELEBRATE` - Major achievements
- `EMPATHY` - Profound understanding
- `SAD_ACK` - Validating sadness

### Emotion-to-Gesture Mapping

Default gestures for each emotion when LLM doesn't specify:

| Emotion | Primary Gestures | Default |
|---------|-----------------|---------|
| Happy | CELEBRATE, EXCITED, THUMBS_UP | THUMBS_UP |
| Sad | COMFORT, EMPATHY, SAD_ACK | EMPATHY |
| Neutral | NOD, LISTEN | NEUTRAL |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Emotion-LLM-Gesture Pipeline                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────┐        │
│  │  Jetson  │───▶│  Pipeline   │───▶│  GPT-5.2 API     │        │
│  │ (emotion)│    │ Orchestrator│    │  (empathetic     │        │
│  └──────────┘    └──────┬──────┘    │   response)      │        │
│                         │           └────────┬─────────┘        │
│                         │                    │                  │
│                         ▼                    ▼                  │
│                  ┌──────────────┐    ┌──────────────┐           │
│                  │   Gesture    │◀───│   Keyword    │           │
│                  │  Controller  │    │   Parser     │           │
│                  └──────┬───────┘    └──────────────┘           │
│                         │                                       │
│                         ▼                                       │
│                  ┌──────────────┐                               │
│                  │ Reachy Mini  │                               │
│                  │   (robot)    │                               │
│                  └──────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Consequences

### Positive

- **Cohesive interaction**: Verbal and physical responses are synchronized
- **Flexible**: LLM can choose appropriate gestures contextually
- **Extensible**: New gestures can be added by extending the keyword system
- **Testable**: Mock LLM client enables testing without API calls
- **Privacy-preserving**: Emotion detection stays on-device; only text goes to LLM

### Negative

- **API dependency**: Requires OpenAI API for production use
- **Latency**: LLM API calls add ~500-2000ms to response time
- **Cost**: GPT-5.2 API usage incurs per-token costs

### Mitigations

- Mock client for development/testing
- Response caching for common interactions (future)
- Fallback to default gestures if LLM unavailable

---

## Implementation

### New Modules

- `apps/reachy/` - Reachy configuration and gesture control
- `apps/llm/` - LLM client and emotion-aware prompts
- `apps/pipeline/` - Emotion-LLM-Gesture orchestrator

### Key Files

- `apps/reachy/gestures/gesture_definitions.py` - 16 gesture primitives
- `apps/reachy/gestures/emotion_gesture_map.py` - Keyword parsing and mapping
- `apps/reachy/gestures/gesture_controller.py` - Reachy SDK interface
- `apps/llm/client.py` - GPT-5.2 async client with mock
- `apps/llm/prompts/emotion_prompts.py` - Emotion-aware system prompts
- `apps/pipeline/emotion_llm_gesture.py` - Main pipeline orchestrator

### Tests

- `tests/test_gesture_definitions.py`
- `tests/test_emotion_gesture_map.py`
- `tests/test_llm_client.py`
- `tests/test_emotion_llm_gesture_pipeline.py`

---

## Requirements

- **Python 3.12+** (Reachy SDK requirement)
- **OpenAI API key** for production LLM calls
- **Reachy Mini robot** (or simulation mode for testing)

---

## Related

- `AGENTS.md` - Agent definitions
- `memory-bank/requirements.md` - Project requirements
- `memory-bank/decisions/006-resnet50-affectnet-rafdb.md` - Emotion model decision
