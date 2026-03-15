"""
Unit tests for emotion-to-gesture mapping.

Tests the EmotionGestureMapper class and keyword parsing functionality.
"""

import pytest

from apps.reachy.gestures.emotion_gesture_map import (
    EmotionGestureMapper,
    GestureKeyword,
    KEYWORD_TO_GESTURE,
    EMOTION_GESTURE_MAP,
    EmotionGestureMapping,
)
from apps.reachy.gestures.gesture_definitions import GestureType, Gesture


class TestGestureKeyword:
    """Tests for GestureKeyword enum."""
    
    def test_all_keywords_defined(self):
        """Verify all expected keywords are defined."""
        expected = [
            "WAVE", "NOD", "SHAKE", "SHRUG", "THUMBS_UP",
            "OPEN_ARMS", "HUG", "THINK", "EXCITED", "COMFORT",
            "LISTEN", "CELEBRATE", "EMPATHY", "SAD_ACK"
        ]
        
        for kw in expected:
            assert hasattr(GestureKeyword, kw), f"Missing keyword: {kw}"
    
    def test_keyword_values_match_names(self):
        """Verify keyword values match their names."""
        for kw in GestureKeyword:
            assert kw.value == kw.name


class TestKeywordToGestureMapping:
    """Tests for keyword-to-gesture mapping."""
    
    def test_all_keywords_mapped(self):
        """Verify all keywords have gesture mappings."""
        for kw in GestureKeyword:
            assert kw in KEYWORD_TO_GESTURE, f"Keyword {kw.name} not mapped to gesture"
    
    def test_mappings_are_valid_gesture_types(self):
        """Verify all mappings point to valid GestureType values."""
        for kw, gt in KEYWORD_TO_GESTURE.items():
            assert isinstance(gt, GestureType), f"Invalid mapping for {kw.name}"
    
    def test_specific_mappings(self):
        """Test specific keyword-to-gesture mappings."""
        assert KEYWORD_TO_GESTURE[GestureKeyword.WAVE] == GestureType.WAVE
        assert KEYWORD_TO_GESTURE[GestureKeyword.NOD] == GestureType.NOD
        assert KEYWORD_TO_GESTURE[GestureKeyword.HUG] == GestureType.HUG
        assert KEYWORD_TO_GESTURE[GestureKeyword.EMPATHY] == GestureType.EMPATHY
        assert KEYWORD_TO_GESTURE[GestureKeyword.SAD_ACK] == GestureType.SAD_ACKNOWLEDGE


class TestEmotionGestureMap:
    """Tests for emotion-to-gesture mapping."""
    
    def test_happy_mapping_exists(self):
        """Verify happy emotion mapping exists."""
        assert "happy" in EMOTION_GESTURE_MAP
        mapping = EMOTION_GESTURE_MAP["happy"]
        assert isinstance(mapping, EmotionGestureMapping)
    
    def test_sad_mapping_exists(self):
        """Verify sad emotion mapping exists."""
        assert "sad" in EMOTION_GESTURE_MAP
        mapping = EMOTION_GESTURE_MAP["sad"]
        assert isinstance(mapping, EmotionGestureMapping)
    
    def test_happy_has_appropriate_gestures(self):
        """Verify happy emotion has positive gestures."""
        mapping = EMOTION_GESTURE_MAP["happy"]
        
        positive_gestures = {
            GestureType.CELEBRATE,
            GestureType.EXCITED,
            GestureType.THUMBS_UP,
        }
        
        all_gestures = set(mapping.primary_gestures + mapping.secondary_gestures)
        assert len(positive_gestures & all_gestures) > 0
    
    def test_sad_has_supportive_gestures(self):
        """Verify sad emotion has supportive gestures."""
        mapping = EMOTION_GESTURE_MAP["sad"]
        
        supportive_gestures = {
            GestureType.COMFORT,
            GestureType.EMPATHY,
            GestureType.HUG,
            GestureType.SAD_ACKNOWLEDGE,
        }
        
        all_gestures = set(mapping.primary_gestures + mapping.secondary_gestures)
        assert len(supportive_gestures & all_gestures) > 0


class TestEmotionGestureMapper:
    """Tests for EmotionGestureMapper class."""
    
    @pytest.fixture
    def mapper(self):
        """Create a mapper instance for testing."""
        return EmotionGestureMapper()
    
    def test_get_gestures_for_happy(self, mapper):
        """Test getting gestures for happy emotion."""
        gestures = mapper.get_gestures_for_emotion("happy")
        
        assert isinstance(gestures, list)
        assert len(gestures) > 0
        assert all(isinstance(g, GestureType) for g in gestures)
    
    def test_get_gestures_for_sad(self, mapper):
        """Test getting gestures for sad emotion."""
        gestures = mapper.get_gestures_for_emotion("sad")
        
        assert isinstance(gestures, list)
        assert len(gestures) > 0
        assert GestureType.EMPATHY in gestures or GestureType.COMFORT in gestures
    
    def test_get_gestures_for_unknown_emotion(self, mapper):
        """Test getting gestures for unknown emotion returns neutral."""
        gestures = mapper.get_gestures_for_emotion("confused")
        
        assert gestures == [GestureType.NEUTRAL]
    
    def test_get_gestures_case_insensitive(self, mapper):
        """Test emotion lookup is case-insensitive."""
        gestures_lower = mapper.get_gestures_for_emotion("happy")
        gestures_upper = mapper.get_gestures_for_emotion("HAPPY")
        gestures_mixed = mapper.get_gestures_for_emotion("HaPpY")
        
        assert gestures_lower == gestures_upper == gestures_mixed
    
    def test_get_default_gesture_happy(self, mapper):
        """Test default gesture for happy emotion."""
        default = mapper.get_default_gesture("happy")
        
        assert isinstance(default, GestureType)
        assert default in [GestureType.THUMBS_UP, GestureType.CELEBRATE, GestureType.EXCITED]
    
    def test_get_default_gesture_sad(self, mapper):
        """Test default gesture for sad emotion."""
        default = mapper.get_default_gesture("sad")
        
        assert isinstance(default, GestureType)
        assert default in [GestureType.EMPATHY, GestureType.COMFORT, GestureType.SAD_ACKNOWLEDGE]
    
    def test_get_default_gesture_unknown(self, mapper):
        """Test default gesture for unknown emotion."""
        default = mapper.get_default_gesture("unknown")
        
        assert default == GestureType.NEUTRAL


class TestKeywordParsing:
    """Tests for parsing gesture keywords from LLM responses."""
    
    @pytest.fixture
    def mapper(self):
        """Create a mapper instance for testing."""
        return EmotionGestureMapper()
    
    def test_parse_single_bracket_keyword(self, mapper):
        """Test parsing single keyword in square brackets."""
        response = "I understand how you feel [HUG]."
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 1
        assert keywords[0] == GestureKeyword.HUG
    
    def test_parse_single_angle_keyword(self, mapper):
        """Test parsing single keyword in angle brackets."""
        response = "That's great news <CELEBRATE>!"
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 1
        assert keywords[0] == GestureKeyword.CELEBRATE
    
    def test_parse_multiple_keywords(self, mapper):
        """Test parsing multiple keywords."""
        response = "I hear you [LISTEN]. That sounds difficult [EMPATHY]. I'm here for you [HUG]."
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 3
        assert keywords[0] == GestureKeyword.LISTEN
        assert keywords[1] == GestureKeyword.EMPATHY
        assert keywords[2] == GestureKeyword.HUG
    
    def test_parse_no_keywords(self, mapper):
        """Test parsing response with no keywords."""
        response = "Hello, how are you today?"
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 0
    
    def test_parse_invalid_keyword_ignored(self, mapper):
        """Test that invalid keywords are ignored."""
        response = "Let me [DANCE] for you [NOD]."
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 1
        assert keywords[0] == GestureKeyword.NOD
    
    def test_parse_mixed_valid_invalid(self, mapper):
        """Test parsing with mix of valid and invalid keywords."""
        response = "[WAVE] Hello! [INVALID] How are you? [THUMBS_UP]"
        keywords = mapper.parse_keywords_from_response(response)
        
        assert len(keywords) == 2
        assert GestureKeyword.WAVE in keywords
        assert GestureKeyword.THUMBS_UP in keywords
    
    def test_keywords_to_gestures(self, mapper):
        """Test converting keywords to gesture types."""
        keywords = [GestureKeyword.WAVE, GestureKeyword.NOD, GestureKeyword.HUG]
        gestures = mapper.keywords_to_gestures(keywords)
        
        assert len(gestures) == 3
        assert GestureType.WAVE in gestures
        assert GestureType.NOD in gestures
        assert GestureType.HUG in gestures
    
    def test_extract_gestures_from_response(self, mapper):
        """Test extracting full gesture objects from response."""
        response = "I'm listening [LISTEN] and I understand [EMPATHY]."
        gestures = mapper.extract_gestures_from_response(response)
        
        assert len(gestures) == 2
        assert all(isinstance(g, Gesture) for g in gestures)
    
    def test_strip_keywords_from_response(self, mapper):
        """Test removing keywords from response text."""
        response = "I hear you [LISTEN]. That's wonderful [THUMBS_UP]!"
        clean = mapper.strip_keywords_from_response(response)
        
        assert "[LISTEN]" not in clean
        assert "[THUMBS_UP]" not in clean
        assert "I hear you" in clean
        assert "That's wonderful" in clean
    
    def test_strip_preserves_punctuation(self, mapper):
        """Test that stripping keywords preserves punctuation."""
        response = "Great job [CELEBRATE]!"
        clean = mapper.strip_keywords_from_response(response)
        
        assert clean == "Great job !"


class TestGestureForEmotionContext:
    """Tests for context-aware gesture selection."""
    
    @pytest.fixture
    def mapper(self):
        """Create a mapper instance for testing."""
        return EmotionGestureMapper()
    
    def test_high_confidence_uses_default(self, mapper):
        """Test high confidence emotion uses default gesture."""
        gestures = mapper.get_gesture_for_emotion_context(
            emotion="happy",
            confidence=0.9,
            llm_response=None
        )
        
        assert len(gestures) > 0
        assert all(isinstance(g, Gesture) for g in gestures)
    
    def test_low_confidence_uses_neutral(self, mapper):
        """Test low confidence returns neutral gesture."""
        gestures = mapper.get_gesture_for_emotion_context(
            emotion="happy",
            confidence=0.5,
            llm_response=None
        )
        
        assert len(gestures) > 0
    
    def test_llm_response_overrides_default(self, mapper):
        """Test LLM response keywords override default gestures."""
        gestures = mapper.get_gesture_for_emotion_context(
            emotion="happy",
            confidence=0.9,
            llm_response="Let me give you a hug [HUG]."
        )
        
        assert len(gestures) == 1
        assert gestures[0].gesture_type == GestureType.HUG
    
    def test_empty_response_uses_emotion_default(self, mapper):
        """Test empty LLM response falls back to emotion default."""
        gestures = mapper.get_gesture_for_emotion_context(
            emotion="sad",
            confidence=0.85,
            llm_response=""
        )
        
        assert len(gestures) > 0


# ---------------------------------------------------------------------------
# Phase 2: 8-class Ekman gesture map coverage
# ---------------------------------------------------------------------------

EKMAN_8_EMOTIONS = ["happy", "sad", "neutral", "anger", "fear", "disgust", "contempt", "surprise"]


class TestEkman8ClassGestureMap:
    """All 8 Ekman emotion classes must have valid gesture mappings."""

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_all_ekman_emotions_in_map(self, emotion):
        assert emotion in EMOTION_GESTURE_MAP, f"Missing gesture map for: {emotion}"

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_mapping_is_correct_type(self, emotion):
        mapping = EMOTION_GESTURE_MAP[emotion]
        assert isinstance(mapping, EmotionGestureMapping)

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_primary_gestures_non_empty(self, emotion):
        mapping = EMOTION_GESTURE_MAP[emotion]
        assert len(mapping.primary_gestures) >= 1, f"{emotion}: no primary gestures"

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_default_gesture_is_valid_type(self, emotion):
        mapping = EMOTION_GESTURE_MAP[emotion]
        assert isinstance(mapping.default_gesture, GestureType)

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_default_gesture_in_primary_or_secondary(self, emotion):
        mapping = EMOTION_GESTURE_MAP[emotion]
        all_gestures = set(mapping.primary_gestures + mapping.secondary_gestures)
        assert mapping.default_gesture in all_gestures, (
            f"{emotion}: default_gesture not in primary or secondary gestures"
        )

    def test_neutral_default_is_listening(self):
        mapping = EMOTION_GESTURE_MAP["neutral"]
        assert mapping.default_gesture == GestureType.LISTENING

    def test_anger_default_is_listening(self):
        """Anger defaults to LISTENING to de-escalate."""
        mapping = EMOTION_GESTURE_MAP["anger"]
        assert mapping.default_gesture == GestureType.LISTENING

    def test_fear_default_is_comfort(self):
        mapping = EMOTION_GESTURE_MAP["fear"]
        assert mapping.default_gesture == GestureType.COMFORT

    def test_surprise_has_excited_gesture(self):
        mapping = EMOTION_GESTURE_MAP["surprise"]
        all_gestures = set(mapping.primary_gestures + mapping.secondary_gestures)
        assert GestureType.EXCITED in all_gestures

    def test_de_escalation_emotions_use_calm_gestures(self):
        """Anger and contempt should include LISTENING or NOD as calm anchors."""
        for emotion in ("anger", "contempt"):
            mapping = EMOTION_GESTURE_MAP[emotion]
            all_gestures = set(mapping.primary_gestures + mapping.secondary_gestures)
            calm = {GestureType.LISTENING, GestureType.NOD, GestureType.NEUTRAL}
            assert len(calm & all_gestures) > 0, f"{emotion}: missing calm anchor gesture"


class TestEkman8ClassMapper:
    """EmotionGestureMapper must correctly resolve all 8 Ekman classes."""

    @pytest.fixture
    def mapper(self):
        return EmotionGestureMapper()

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_get_default_gesture_for_all_ekman(self, mapper, emotion):
        default = mapper.get_default_gesture(emotion)
        assert isinstance(default, GestureType), f"{emotion}: default is not GestureType"

    @pytest.mark.parametrize("emotion", EKMAN_8_EMOTIONS)
    def test_get_gestures_returns_list_for_all_ekman(self, mapper, emotion):
        gestures = mapper.get_gestures_for_emotion(emotion)
        assert isinstance(gestures, list)
        assert len(gestures) >= 1

    def test_neutral_default_gesture_resolves(self, mapper):
        default = mapper.get_default_gesture("neutral")
        assert default == GestureType.LISTENING

    def test_fear_default_gesture_resolves(self, mapper):
        default = mapper.get_default_gesture("fear")
        assert default == GestureType.COMFORT
