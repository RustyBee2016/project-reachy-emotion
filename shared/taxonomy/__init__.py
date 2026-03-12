"""
Shared taxonomy definitions for emotion classification.

Provides Ekman 8-class taxonomy with PPE behavioral profiles
mapping emotions to response strategies, gesture tiers, and LLM tones.
"""

from shared.taxonomy.ekman_taxonomy import (
    EKMAN_8_CLASSES,
    PHASE1_CLASSES,
    EkmanBehaviorProfile,
    EKMAN_BEHAVIOR_MAP,
    get_behavior_profile,
    phase1_to_ekman,
    is_valid_emotion,
    get_response_strategy,
)

__all__ = [
    "EKMAN_8_CLASSES",
    "PHASE1_CLASSES",
    "EkmanBehaviorProfile",
    "EKMAN_BEHAVIOR_MAP",
    "get_behavior_profile",
    "phase1_to_ekman",
    "is_valid_emotion",
    "get_response_strategy",
]
