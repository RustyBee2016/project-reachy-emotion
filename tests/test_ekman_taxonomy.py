"""
Unit tests for the Ekman 8-class PPE taxonomy module.

Validates that all 8 emotion classes return valid EkmanBehaviorProfile
instances and that all helper functions work correctly.
"""
import pytest

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


VALID_EXPRESSIVENESS_HINTS = {"full", "moderate", "subtle", "minimal"}
VALID_STRATEGIES = {
    "amplify_positive",
    "provide_support",
    "engage_openly",
    "de_escalate",
    "reassure",
    "redirect",
    "engage_curiously",
    "match_and_explore",
}


class TestEkmanClassCoverage:
    """All 8 Ekman classes must have complete behavior profiles."""

    def test_all_eight_classes_present(self):
        """EKMAN_8_CLASSES has exactly 8 entries."""
        assert len(EKMAN_8_CLASSES) == 8
        expected = {"anger", "contempt", "disgust", "fear", "happy", "neutral", "sad", "surprise"}
        assert set(EKMAN_8_CLASSES) == expected

    def test_behavior_map_covers_all_eight_classes(self):
        """EKMAN_BEHAVIOR_MAP has an entry for every Ekman class."""
        for emotion in EKMAN_8_CLASSES:
            assert emotion in EKMAN_BEHAVIOR_MAP, f"Missing profile for: {emotion}"

    def test_phase1_classes_subset_of_ekman(self):
        """Phase 1 classes are all valid Ekman classes."""
        for cls in PHASE1_CLASSES:
            assert cls in EKMAN_8_CLASSES

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_profile_fields_are_non_empty(self, emotion):
        """Every profile has non-empty required string fields."""
        profile = EKMAN_BEHAVIOR_MAP[emotion]
        assert profile.emotion == emotion
        assert profile.response_strategy, f"Empty response_strategy for {emotion}"
        assert profile.llm_tone, f"Empty llm_tone for {emotion}"
        assert profile.primary_gesture_keywords, f"Empty gesture keywords for {emotion}"
        assert profile.gesture_expressiveness_hint, f"Empty hint for {emotion}"
        assert profile.intensity_label, f"Empty intensity_label for {emotion}"

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_expressiveness_hint_is_valid(self, emotion):
        """Every profile uses a recognised expressiveness hint."""
        profile = EKMAN_BEHAVIOR_MAP[emotion]
        assert profile.gesture_expressiveness_hint in VALID_EXPRESSIVENESS_HINTS, (
            f"{emotion}: unexpected hint '{profile.gesture_expressiveness_hint}'"
        )

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_response_strategy_is_valid(self, emotion):
        """Every profile uses a recognised response strategy."""
        profile = EKMAN_BEHAVIOR_MAP[emotion]
        assert profile.response_strategy in VALID_STRATEGIES, (
            f"{emotion}: unknown strategy '{profile.response_strategy}'"
        )

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_bool_fields_are_bool(self, emotion):
        """de_escalate and validate_first must be bools."""
        profile = EKMAN_BEHAVIOR_MAP[emotion]
        assert isinstance(profile.de_escalate, bool)
        assert isinstance(profile.validate_first, bool)


class TestGetBehaviorProfile:
    """Tests for get_behavior_profile() helper."""

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_returns_correct_profile(self, emotion):
        profile = get_behavior_profile(emotion)
        assert isinstance(profile, EkmanBehaviorProfile)
        assert profile.emotion == emotion

    def test_case_insensitive_lookup(self):
        assert get_behavior_profile("Happy").emotion == "happy"
        assert get_behavior_profile("SAD").emotion == "sad"
        assert get_behavior_profile("NEUTRAL").emotion == "neutral"

    def test_unknown_emotion_falls_back_to_neutral(self):
        profile = get_behavior_profile("confused")
        assert profile.emotion == "neutral"

    def test_empty_string_falls_back_to_neutral(self):
        profile = get_behavior_profile("")
        assert profile.emotion == "neutral"


class TestPhase1ToEkman:
    """Phase 1 identity mapping."""

    def test_happy_maps_to_happy(self):
        assert phase1_to_ekman("happy") == "happy"

    def test_sad_maps_to_sad(self):
        assert phase1_to_ekman("sad") == "sad"

    def test_neutral_maps_to_neutral(self):
        assert phase1_to_ekman("neutral") == "neutral"

    def test_unknown_falls_back_to_neutral(self):
        assert phase1_to_ekman("confused") == "neutral"

    def test_case_insensitive(self):
        assert phase1_to_ekman("HAPPY") == "happy"


class TestIsValidEmotion:
    """Validation helper."""

    @pytest.mark.parametrize("emotion", EKMAN_8_CLASSES)
    def test_all_ekman_classes_are_valid(self, emotion):
        assert is_valid_emotion(emotion) is True

    def test_invalid_emotions(self):
        assert is_valid_emotion("confused") is False
        assert is_valid_emotion("bored") is False
        assert is_valid_emotion("") is False

    def test_case_insensitive(self):
        assert is_valid_emotion("Happy") is True
        assert is_valid_emotion("ANGER") is True


class TestGetResponseStrategy:
    """Response strategy retrieval."""

    def test_happy_is_amplify_positive(self):
        assert get_response_strategy("happy") == "amplify_positive"

    def test_sad_is_provide_support(self):
        assert get_response_strategy("sad") == "provide_support"

    def test_anger_is_de_escalate(self):
        assert get_response_strategy("anger") == "de_escalate"

    def test_fear_is_reassure(self):
        assert get_response_strategy("fear") == "reassure"

    def test_unknown_returns_neutral_strategy(self):
        assert get_response_strategy("confused") == "engage_openly"


class TestDeEscalateProfiles:
    """Emotions that require de-escalation should flag it."""

    def test_anger_requires_deescalation(self):
        assert EKMAN_BEHAVIOR_MAP["anger"].de_escalate is True

    def test_contempt_requires_deescalation(self):
        assert EKMAN_BEHAVIOR_MAP["contempt"].de_escalate is True

    def test_happy_does_not_require_deescalation(self):
        assert EKMAN_BEHAVIOR_MAP["happy"].de_escalate is False

    def test_surprise_does_not_require_deescalation(self):
        assert EKMAN_BEHAVIOR_MAP["surprise"].de_escalate is False


class TestValidateFirstProfiles:
    """Emotions that require validation before support."""

    def test_sad_requires_validation(self):
        assert EKMAN_BEHAVIOR_MAP["sad"].validate_first is True

    def test_anger_requires_validation(self):
        assert EKMAN_BEHAVIOR_MAP["anger"].validate_first is True

    def test_happy_does_not_require_validation(self):
        assert EKMAN_BEHAVIOR_MAP["happy"].validate_first is False
