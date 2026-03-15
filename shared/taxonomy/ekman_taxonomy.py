"""
Ekman 8-Class Emotion Taxonomy with PPE Behavioral Profiles

Defines the full Ekman emotion taxonomy and maps each emotion to a
behavioral profile (PPE — Personality-Perceived-Emotion) that guides:
  - Response strategy for the LLM
  - Gesture expressiveness tier
  - LLM tone/style
  - Intensity hint for confidence-scaled expression

Phase 1 uses 3-class (happy, sad, neutral).
Phase 2 expands to full 8-class Ekman taxonomy.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


EKMAN_8_CLASSES: List[str] = [
    "anger",
    "contempt",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]

PHASE1_CLASSES: List[str] = ["happy", "neutral", "sad"]

PHASE1_TO_EKMAN: Dict[str, str] = {
    "happy": "happy",
    "neutral": "neutral",
    "sad": "sad",
}


@dataclass
class EkmanBehaviorProfile:
    """
    Behavioral profile for a detected emotion.

    Guides the robot's response strategy, gesture selection, and LLM tone
    based on the detected Ekman emotion class.

    Attributes:
        emotion: Canonical emotion label (Ekman class name)
        response_strategy: High-level strategy for the LLM response
        llm_tone: Stylistic guidance string injected into the system prompt
        primary_gesture_keywords: Ordered list of preferred gesture keywords
        gesture_expressiveness_hint: Suggested starting tier (overridden by confidence)
        de_escalate: Whether this emotion requires de-escalation behaviour
        validate_first: Whether to validate feelings before offering support
        intensity_label: Human-readable intensity description for this emotion
    """

    emotion: str
    response_strategy: str
    llm_tone: str
    primary_gesture_keywords: List[str]
    gesture_expressiveness_hint: str
    de_escalate: bool
    validate_first: bool
    intensity_label: str


EKMAN_BEHAVIOR_MAP: Dict[str, EkmanBehaviorProfile] = {
    "happy": EkmanBehaviorProfile(
        emotion="happy",
        response_strategy="amplify_positive",
        llm_tone=(
            "Be warm, enthusiastic, and genuinely celebratory. "
            "Match their positive energy without being over-the-top. "
            "Ask what is making them happy to deepen the connection."
        ),
        primary_gesture_keywords=["THUMBS_UP", "CELEBRATE", "EXCITED", "NOD", "WAVE"],
        gesture_expressiveness_hint="full",
        de_escalate=False,
        validate_first=False,
        intensity_label="joyful",
    ),
    "sad": EkmanBehaviorProfile(
        emotion="sad",
        response_strategy="provide_support",
        llm_tone=(
            "Be gentle, patient, and understanding. Validate feelings without "
            "trying to fix them immediately. Use soft, comforting language. "
            "Listen more than you speak. Acknowledge it is okay to feel sad."
        ),
        primary_gesture_keywords=["EMPATHY", "COMFORT", "HUG", "SAD_ACK", "LISTEN"],
        gesture_expressiveness_hint="moderate",
        de_escalate=False,
        validate_first=True,
        intensity_label="sorrowful",
    ),
    "neutral": EkmanBehaviorProfile(
        emotion="neutral",
        response_strategy="engage_openly",
        llm_tone=(
            "Be warm and approachable. Show genuine interest in the conversation. "
            "Maintain a balanced, pleasant tone. Be ready to adapt if emotions shift."
        ),
        primary_gesture_keywords=["NOD", "LISTEN", "THINK", "WAVE"],
        gesture_expressiveness_hint="subtle",
        de_escalate=False,
        validate_first=False,
        intensity_label="calm",
    ),
    "anger": EkmanBehaviorProfile(
        emotion="anger",
        response_strategy="de_escalate",
        llm_tone=(
            "Be calm, non-confrontational, and validating. Acknowledge that their "
            "frustration is understandable. Do NOT be dismissive or argue. Use "
            "measured, steady language. Give them space to vent before responding."
        ),
        primary_gesture_keywords=["LISTEN", "NOD", "SHRUG"],
        gesture_expressiveness_hint="minimal",
        de_escalate=True,
        validate_first=True,
        intensity_label="frustrated",
    ),
    "fear": EkmanBehaviorProfile(
        emotion="fear",
        response_strategy="reassure",
        llm_tone=(
            "Be calm, reassuring, and grounding. Acknowledge their fear as valid. "
            "Use steady, unhurried language. Offer a sense of safety and presence. "
            "Avoid anything that could amplify anxiety."
        ),
        primary_gesture_keywords=["COMFORT", "EMPATHY", "OPEN_ARMS"],
        gesture_expressiveness_hint="subtle",
        de_escalate=False,
        validate_first=True,
        intensity_label="anxious",
    ),
    "disgust": EkmanBehaviorProfile(
        emotion="disgust",
        response_strategy="redirect",
        llm_tone=(
            "Be empathetic but gently redirect the conversation toward more "
            "constructive territory. Acknowledge their reaction without reinforcing "
            "the negative. Use neutral, measured language."
        ),
        primary_gesture_keywords=["SHRUG", "NOD", "LISTEN"],
        gesture_expressiveness_hint="minimal",
        de_escalate=False,
        validate_first=True,
        intensity_label="repulsed",
    ),
    "contempt": EkmanBehaviorProfile(
        emotion="contempt",
        response_strategy="engage_curiously",
        llm_tone=(
            "Be curious and non-judgmental. Gently explore what is behind the "
            "contempt without amplifying it. Use open-ended questions. Maintain "
            "a calm, even tone that models respectful engagement."
        ),
        primary_gesture_keywords=["SHRUG", "NOD"],
        gesture_expressiveness_hint="minimal",
        de_escalate=True,
        validate_first=False,
        intensity_label="dismissive",
    ),
    "surprise": EkmanBehaviorProfile(
        emotion="surprise",
        response_strategy="match_and_explore",
        llm_tone=(
            "Match their surprise energy lightly. Express shared curiosity or "
            "enthusiasm. Ask what surprised them to understand context — surprise "
            "can be positive or negative so be ready to pivot tone quickly."
        ),
        primary_gesture_keywords=["EXCITED", "OPEN_ARMS", "NOD"],
        gesture_expressiveness_hint="moderate",
        de_escalate=False,
        validate_first=False,
        intensity_label="startled",
    ),
}


def get_behavior_profile(emotion: str) -> EkmanBehaviorProfile:
    """
    Get the behavioral profile for a detected emotion.

    Falls back to neutral if the emotion is unknown or not in the taxonomy.

    Args:
        emotion: Emotion label string (case-insensitive)

    Returns:
        EkmanBehaviorProfile for the emotion
    """
    return EKMAN_BEHAVIOR_MAP.get(emotion.lower(), EKMAN_BEHAVIOR_MAP["neutral"])


def phase1_to_ekman(emotion: str) -> str:
    """
    Map a Phase 1 3-class label to its Ekman canonical name.

    Phase 1 labels are already valid Ekman labels (happy/sad/neutral),
    so this is an identity mapping with fallback to neutral.

    Args:
        emotion: Phase 1 emotion label

    Returns:
        Canonical Ekman label
    """
    return PHASE1_TO_EKMAN.get(emotion.lower(), "neutral")


def is_valid_emotion(emotion: str) -> bool:
    """
    Check whether a string is a valid Ekman class label.

    Args:
        emotion: Emotion label to check

    Returns:
        True if the emotion is in the 8-class Ekman taxonomy
    """
    return emotion.lower() in EKMAN_BEHAVIOR_MAP


def get_response_strategy(emotion: str) -> str:
    """
    Get the response strategy string for a given emotion.

    Args:
        emotion: Emotion label

    Returns:
        Response strategy string (e.g., "provide_support", "de_escalate")
    """
    return get_behavior_profile(emotion).response_strategy
