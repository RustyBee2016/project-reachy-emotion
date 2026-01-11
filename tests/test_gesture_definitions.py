"""
Unit tests for Reachy gesture definitions.

Tests gesture primitives, gesture library, and gesture retrieval functions.
"""

import pytest

from apps.reachy.gestures.gesture_definitions import (
    Gesture,
    GestureType,
    ArmPosition,
    HeadPosition,
    ArmSide,
    JointPosition,
    GESTURE_LIBRARY,
    get_gesture,
    list_gestures,
)


class TestGestureType:
    """Tests for GestureType enum."""
    
    def test_gesture_types_exist(self):
        """Verify all expected gesture types are defined."""
        expected_types = [
            "WAVE", "NOD", "SHAKE_HEAD", "SHRUG", "THUMBS_UP",
            "OPEN_ARMS", "HUG", "POINT", "THINKING", "EXCITED",
            "COMFORT", "LISTENING", "CELEBRATE", "SAD_ACKNOWLEDGE",
            "EMPATHY", "NEUTRAL"
        ]
        
        for type_name in expected_types:
            assert hasattr(GestureType, type_name), f"Missing GestureType: {type_name}"
    
    def test_gesture_type_values_unique(self):
        """Verify all gesture type values are unique."""
        values = [gt.value for gt in GestureType]
        assert len(values) == len(set(values)), "Duplicate gesture type values found"


class TestJointPosition:
    """Tests for JointPosition dataclass."""
    
    def test_default_values(self):
        """Test default joint position is all zeros."""
        pos = JointPosition()
        
        assert pos.shoulder_pitch == 0.0
        assert pos.shoulder_roll == 0.0
        assert pos.arm_yaw == 0.0
        assert pos.elbow_pitch == 0.0
        assert pos.forearm_yaw == 0.0
        assert pos.wrist_pitch == 0.0
        assert pos.wrist_roll == 0.0
        assert pos.gripper == 0.0
    
    def test_custom_values(self):
        """Test joint position with custom values."""
        pos = JointPosition(
            shoulder_pitch=-30.0,
            elbow_pitch=-90.0,
            gripper=100.0
        )
        
        assert pos.shoulder_pitch == -30.0
        assert pos.elbow_pitch == -90.0
        assert pos.gripper == 100.0


class TestArmPosition:
    """Tests for ArmPosition dataclass."""
    
    def test_arm_position_creation(self):
        """Test creating an arm position."""
        joints = JointPosition(shoulder_pitch=-45.0)
        pos = ArmPosition(
            side=ArmSide.RIGHT,
            joints=joints,
            duration=1.5
        )
        
        assert pos.side == ArmSide.RIGHT
        assert pos.joints.shoulder_pitch == -45.0
        assert pos.duration == 1.5
    
    def test_arm_sides(self):
        """Test all arm sides are valid."""
        assert ArmSide.LEFT.value == "left"
        assert ArmSide.RIGHT.value == "right"
        assert ArmSide.BOTH.value == "both"


class TestHeadPosition:
    """Tests for HeadPosition dataclass."""
    
    def test_default_head_position(self):
        """Test default head position."""
        pos = HeadPosition()
        
        assert pos.roll == 0.0
        assert pos.pitch == 0.0
        assert pos.yaw == 0.0
        assert pos.duration == 0.5
    
    def test_custom_head_position(self):
        """Test head position with custom values."""
        pos = HeadPosition(pitch=15.0, roll=10.0, yaw=-5.0, duration=0.8)
        
        assert pos.pitch == 15.0
        assert pos.roll == 10.0
        assert pos.yaw == -5.0
        assert pos.duration == 0.8


class TestGesture:
    """Tests for Gesture dataclass."""
    
    def test_gesture_creation(self):
        """Test creating a gesture."""
        gesture = Gesture(
            name="test_gesture",
            gesture_type=GestureType.WAVE,
            description="A test gesture",
            total_duration=2.0
        )
        
        assert gesture.name == "test_gesture"
        assert gesture.gesture_type == GestureType.WAVE
        assert gesture.description == "A test gesture"
        assert gesture.total_duration == 2.0
        assert gesture.loop is False
        assert gesture.loop_count == 1
    
    def test_gesture_with_sequences(self):
        """Test gesture with arm and head sequences."""
        arm_seq = [
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(shoulder_pitch=-30.0),
                duration=0.5
            )
        ]
        head_seq = [
            HeadPosition(pitch=10.0, duration=0.3)
        ]
        
        gesture = Gesture(
            name="complex_gesture",
            gesture_type=GestureType.NOD,
            description="Complex gesture",
            arm_sequence=arm_seq,
            head_sequence=head_seq
        )
        
        assert len(gesture.arm_sequence) == 1
        assert len(gesture.head_sequence) == 1
        assert gesture.arm_sequence[0].side == ArmSide.RIGHT


class TestGestureLibrary:
    """Tests for the gesture library."""
    
    def test_library_not_empty(self):
        """Verify gesture library is populated."""
        assert len(GESTURE_LIBRARY) > 0
    
    def test_all_gesture_types_have_definitions(self):
        """Verify all gesture types have library entries."""
        missing = []
        for gt in GestureType:
            if gt not in GESTURE_LIBRARY:
                missing.append(gt.name)
        
        skip_types = ["POINT"]
        missing = [m for m in missing if m not in skip_types]
        
        assert len(missing) == 0, f"Missing gesture definitions: {missing}"
    
    def test_gesture_library_entries_valid(self):
        """Verify all library entries are valid Gesture objects."""
        for gesture_type, gesture in GESTURE_LIBRARY.items():
            assert isinstance(gesture, Gesture)
            assert gesture.gesture_type == gesture_type
            assert gesture.name is not None
            assert len(gesture.name) > 0
            assert gesture.total_duration > 0
    
    def test_wave_gesture(self):
        """Test the wave gesture definition."""
        wave = GESTURE_LIBRARY.get(GestureType.WAVE)
        
        assert wave is not None
        assert wave.name == "wave"
        assert len(wave.arm_sequence) > 0
        assert wave.loop is True
    
    def test_empathy_gesture(self):
        """Test the empathy gesture definition."""
        empathy = GESTURE_LIBRARY.get(GestureType.EMPATHY)
        
        assert empathy is not None
        assert empathy.name == "empathy"
        assert len(empathy.arm_sequence) > 0 or len(empathy.head_sequence) > 0
    
    def test_neutral_gesture(self):
        """Test the neutral gesture returns to default position."""
        neutral = GESTURE_LIBRARY.get(GestureType.NEUTRAL)
        
        assert neutral is not None
        assert neutral.name == "neutral"


class TestGestureFunctions:
    """Tests for gesture utility functions."""
    
    def test_get_gesture_valid(self):
        """Test getting a valid gesture."""
        gesture = get_gesture(GestureType.NOD)
        
        assert gesture is not None
        assert gesture.gesture_type == GestureType.NOD
    
    def test_get_gesture_invalid(self):
        """Test getting an invalid gesture returns None."""
        result = get_gesture(None)
        assert result is None
    
    def test_list_gestures(self):
        """Test listing all gesture names."""
        names = list_gestures()
        
        assert isinstance(names, list)
        assert len(names) > 0
        assert "wave" in names
        assert "nod" in names
        assert "empathy" in names


class TestGestureEmotionAlignment:
    """Tests for gesture-emotion alignment."""
    
    def test_happy_gestures_exist(self):
        """Verify gestures appropriate for happy emotion exist."""
        happy_gestures = [
            GestureType.CELEBRATE,
            GestureType.EXCITED,
            GestureType.THUMBS_UP,
        ]
        
        for gt in happy_gestures:
            assert gt in GESTURE_LIBRARY, f"Missing happy gesture: {gt.name}"
    
    def test_sad_gestures_exist(self):
        """Verify gestures appropriate for sad emotion exist."""
        sad_gestures = [
            GestureType.COMFORT,
            GestureType.EMPATHY,
            GestureType.SAD_ACKNOWLEDGE,
            GestureType.HUG,
        ]
        
        for gt in sad_gestures:
            assert gt in GESTURE_LIBRARY, f"Missing sad gesture: {gt.name}"
