"""
Unit tests for gesture modulation based on emotion confidence.

Tests the GestureModulator class and degree-based expressiveness scaling.
"""

import pytest

from apps.reachy.gestures.gesture_modulator import (
    GestureModulator,
    ExpressivenessLevel,
    ModulationParams,
    get_modulation_params,
    modulate_gesture,
    get_modulated_gesture_for_emotion,
    CONFIDENCE_TIERS,
)
from apps.reachy.gestures.gesture_definitions import (
    GestureType,
    Gesture,
    GESTURE_LIBRARY,
)


class TestConfidenceTiers:
    """Tests for confidence-to-expressiveness mapping."""
    
    def test_high_confidence_full_expressiveness(self):
        """Test that high confidence (>=0.90) yields full expressiveness."""
        params = get_modulation_params(0.95)
        assert params.expressiveness == ExpressivenessLevel.FULL
        assert params.amplitude_multiplier == 1.0
        
        params = get_modulation_params(0.90)
        assert params.expressiveness == ExpressivenessLevel.FULL
    
    def test_moderate_confidence_moderate_expressiveness(self):
        """Test that moderate confidence (0.75-0.89) yields moderate expressiveness."""
        params = get_modulation_params(0.85)
        assert params.expressiveness == ExpressivenessLevel.MODERATE
        assert params.amplitude_multiplier == 0.75
        
        params = get_modulation_params(0.75)
        assert params.expressiveness == ExpressivenessLevel.MODERATE
    
    def test_low_confidence_subtle_expressiveness(self):
        """Test that low confidence (0.60-0.74) yields subtle expressiveness."""
        params = get_modulation_params(0.70)
        assert params.expressiveness == ExpressivenessLevel.SUBTLE
        assert params.amplitude_multiplier == 0.50
        
        params = get_modulation_params(0.60)
        assert params.expressiveness == ExpressivenessLevel.SUBTLE
    
    def test_very_low_confidence_minimal_expressiveness(self):
        """Test that very low confidence (0.40-0.59) yields minimal expressiveness."""
        params = get_modulation_params(0.55)
        assert params.expressiveness == ExpressivenessLevel.MINIMAL
        assert params.amplitude_multiplier == 0.25
        
        params = get_modulation_params(0.40)
        assert params.expressiveness == ExpressivenessLevel.MINIMAL
    
    def test_below_threshold_abstain(self):
        """Test that very low confidence (<0.40) yields abstain."""
        params = get_modulation_params(0.35)
        assert params.expressiveness == ExpressivenessLevel.ABSTAIN
        assert params.amplitude_multiplier == 0.0
        
        params = get_modulation_params(0.10)
        assert params.expressiveness == ExpressivenessLevel.ABSTAIN
    
    def test_boundary_conditions(self):
        """Test boundary values between tiers."""
        # Just below 0.90 should be MODERATE
        params = get_modulation_params(0.899)
        assert params.expressiveness == ExpressivenessLevel.MODERATE
        
        # Just below 0.75 should be SUBTLE
        params = get_modulation_params(0.749)
        assert params.expressiveness == ExpressivenessLevel.SUBTLE
        
        # Just below 0.60 should be MINIMAL
        params = get_modulation_params(0.599)
        assert params.expressiveness == ExpressivenessLevel.MINIMAL
        
        # Just below 0.40 should be ABSTAIN
        params = get_modulation_params(0.399)
        assert params.expressiveness == ExpressivenessLevel.ABSTAIN


class TestGestureModulation:
    """Tests for gesture modulation function."""
    
    @pytest.fixture
    def empathy_gesture(self):
        """Get the EMPATHY gesture for testing."""
        return GESTURE_LIBRARY[GestureType.EMPATHY]
    
    def test_full_confidence_no_change(self, empathy_gesture):
        """Test that full confidence returns unmodified gesture."""
        modulated = modulate_gesture(empathy_gesture, 0.95)
        
        assert modulated is not None
        assert modulated.gesture_type == empathy_gesture.gesture_type
        # Full expressiveness should preserve original values
        assert modulated.total_duration == empathy_gesture.total_duration
    
    def test_moderate_confidence_reduces_amplitude(self, empathy_gesture):
        """Test that moderate confidence reduces amplitude."""
        modulated = modulate_gesture(empathy_gesture, 0.80)
        
        assert modulated is not None
        # Check arm positions are scaled
        if empathy_gesture.arm_sequence and modulated.arm_sequence:
            orig_shoulder = empathy_gesture.arm_sequence[0].joints.shoulder_roll
            mod_shoulder = modulated.arm_sequence[0].joints.shoulder_roll
            assert abs(mod_shoulder) < abs(orig_shoulder)
            assert abs(mod_shoulder) == pytest.approx(abs(orig_shoulder) * 0.75, rel=0.01)
    
    def test_moderate_confidence_slows_speed(self, empathy_gesture):
        """Test that moderate confidence increases duration (slower speed)."""
        modulated = modulate_gesture(empathy_gesture, 0.80)
        
        assert modulated is not None
        assert modulated.total_duration > empathy_gesture.total_duration
        assert modulated.total_duration == pytest.approx(
            empathy_gesture.total_duration * 1.25, rel=0.01
        )
    
    def test_subtle_confidence_half_amplitude(self, empathy_gesture):
        """Test that subtle confidence uses 50% amplitude."""
        modulated = modulate_gesture(empathy_gesture, 0.65)
        
        assert modulated is not None
        if empathy_gesture.head_sequence and modulated.head_sequence:
            orig_pitch = empathy_gesture.head_sequence[0].pitch
            mod_pitch = modulated.head_sequence[0].pitch
            assert mod_pitch == pytest.approx(orig_pitch * 0.50, rel=0.01)
    
    def test_minimal_confidence_quarter_amplitude(self, empathy_gesture):
        """Test that minimal confidence uses 25% amplitude."""
        modulated = modulate_gesture(empathy_gesture, 0.45)
        
        assert modulated is not None
        if empathy_gesture.arm_sequence and modulated.arm_sequence:
            orig_pitch = empathy_gesture.arm_sequence[0].joints.shoulder_pitch
            mod_pitch = modulated.arm_sequence[0].joints.shoulder_pitch
            assert mod_pitch == pytest.approx(orig_pitch * 0.25, rel=0.01)
    
    def test_abstain_returns_none(self, empathy_gesture):
        """Test that very low confidence returns None (abstain)."""
        modulated = modulate_gesture(empathy_gesture, 0.30)
        assert modulated is None
        
        modulated = modulate_gesture(empathy_gesture, 0.10)
        assert modulated is None
    
    def test_modulated_gesture_name_includes_level(self, empathy_gesture):
        """Test that modulated gesture name indicates expressiveness level."""
        modulated = modulate_gesture(empathy_gesture, 0.80)
        assert "moderate" in modulated.name
        
        modulated = modulate_gesture(empathy_gesture, 0.65)
        assert "subtle" in modulated.name
    
    def test_all_gesture_types_can_be_modulated(self):
        """Test that all gestures in library can be modulated."""
        for gesture_type, gesture in GESTURE_LIBRARY.items():
            modulated = modulate_gesture(gesture, 0.85)
            assert modulated is not None
            assert modulated.gesture_type == gesture_type


class TestGetModulatedGestureForEmotion:
    """Tests for emotion-based modulated gesture retrieval."""
    
    def test_happy_emotion_high_confidence(self):
        """Test getting modulated gesture for happy emotion with high confidence."""
        gesture = get_modulated_gesture_for_emotion("happy", 0.92)
        
        assert gesture is not None
        assert "full" in gesture.name
    
    def test_sad_emotion_moderate_confidence(self):
        """Test getting modulated gesture for sad emotion with moderate confidence."""
        gesture = get_modulated_gesture_for_emotion("sad", 0.78)
        
        assert gesture is not None
        assert "moderate" in gesture.name
    
    def test_unknown_emotion_low_confidence_abstains(self):
        """Test that unknown emotion with low confidence abstains."""
        gesture = get_modulated_gesture_for_emotion("confused", 0.35)
        assert gesture is None
    
    def test_specific_gesture_type_override(self):
        """Test providing specific gesture type."""
        gesture = get_modulated_gesture_for_emotion(
            "happy",
            0.85,
            gesture_type=GestureType.HUG
        )
        
        assert gesture is not None
        assert gesture.gesture_type == GestureType.HUG


class TestGestureModulatorClass:
    """Tests for the stateful GestureModulator class."""
    
    @pytest.fixture
    def modulator(self):
        """Create a modulator instance."""
        return GestureModulator()
    
    @pytest.fixture
    def empathy_gesture(self):
        """Get the EMPATHY gesture for testing."""
        return GESTURE_LIBRARY[GestureType.EMPATHY]
    
    def test_tracks_last_expressiveness(self, modulator, empathy_gesture):
        """Test that modulator tracks last expressiveness level."""
        modulator.modulate(empathy_gesture, 0.85)
        assert modulator.last_expressiveness == ExpressivenessLevel.MODERATE
        
        modulator.modulate(empathy_gesture, 0.65)
        assert modulator.last_expressiveness == ExpressivenessLevel.SUBTLE
    
    def test_tracks_modulation_count(self, modulator, empathy_gesture):
        """Test that modulator tracks modulation count."""
        modulator.modulate(empathy_gesture, 0.90)
        modulator.modulate(empathy_gesture, 0.80)
        modulator.modulate(empathy_gesture, 0.70)
        
        assert modulator.stats["modulated"] == 3
        assert modulator.stats["abstained"] == 0
    
    def test_tracks_abstain_count(self, modulator, empathy_gesture):
        """Test that modulator tracks abstain count."""
        modulator.modulate(empathy_gesture, 0.90)
        modulator.modulate(empathy_gesture, 0.30)  # Abstain
        modulator.modulate(empathy_gesture, 0.25)  # Abstain
        
        assert modulator.stats["modulated"] == 1
        assert modulator.stats["abstained"] == 2
        assert modulator.stats["abstain_rate"] == pytest.approx(2/3, rel=0.01)
    
    def test_reset_stats(self, modulator, empathy_gesture):
        """Test resetting modulation statistics."""
        modulator.modulate(empathy_gesture, 0.90)
        modulator.modulate(empathy_gesture, 0.30)
        modulator.reset_stats()
        
        assert modulator.stats["total_requests"] == 0
        assert modulator.stats["modulated"] == 0
        assert modulator.stats["abstained"] == 0
    
    def test_get_expressiveness_for_confidence(self, modulator):
        """Test convenience method for getting expressiveness level."""
        assert modulator.get_expressiveness_for_confidence(0.95) == ExpressivenessLevel.FULL
        assert modulator.get_expressiveness_for_confidence(0.80) == ExpressivenessLevel.MODERATE
        assert modulator.get_expressiveness_for_confidence(0.65) == ExpressivenessLevel.SUBTLE
        assert modulator.get_expressiveness_for_confidence(0.50) == ExpressivenessLevel.MINIMAL
        assert modulator.get_expressiveness_for_confidence(0.30) == ExpressivenessLevel.ABSTAIN
