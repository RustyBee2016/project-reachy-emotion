"""
Gesture Modulator: Degree-Based Gesture Expressiveness

Scales gesture parameters (amplitude, speed, range) based on emotion
confidence scores, enabling nuanced expression that matches the 
certainty of emotion detection.

This is a core component of the robot's Emotional Intelligence (EQ) —
a robot with high EQ doesn't just detect emotions, it expresses
appropriate uncertainty through its physical behavior.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import copy

from apps.reachy.gestures.gesture_definitions import (
    Gesture,
    GestureType,
    ArmPosition,
    HeadPosition,
    JointPosition,
    GESTURE_LIBRARY,
)


class ExpressivenessLevel(Enum):
    """Expressiveness tiers based on confidence."""
    FULL = "full"           # 0.90-1.00: Maximum amplitude, normal speed
    MODERATE = "moderate"   # 0.75-0.89: 75% amplitude, slightly slower
    SUBTLE = "subtle"       # 0.60-0.74: 50% amplitude, deliberate pacing
    MINIMAL = "minimal"     # 0.40-0.59: 25% amplitude, slow/tentative
    ABSTAIN = "abstain"     # < 0.40: No emotion-specific gesture


@dataclass
class ModulationParams:
    """Parameters for gesture modulation."""
    amplitude_multiplier: float  # Scale factor for joint angles (0-1)
    speed_multiplier: float      # Scale factor for duration (>1 = slower)
    head_tilt_multiplier: float  # Scale factor for head movements
    expressiveness: ExpressivenessLevel


# Confidence thresholds and their corresponding modulation parameters
CONFIDENCE_TIERS: list[Tuple[float, ModulationParams]] = [
    (0.90, ModulationParams(
        amplitude_multiplier=1.0,
        speed_multiplier=1.0,
        head_tilt_multiplier=1.0,
        expressiveness=ExpressivenessLevel.FULL
    )),
    (0.75, ModulationParams(
        amplitude_multiplier=0.75,
        speed_multiplier=1.25,  # 25% slower
        head_tilt_multiplier=0.75,
        expressiveness=ExpressivenessLevel.MODERATE
    )),
    (0.60, ModulationParams(
        amplitude_multiplier=0.50,
        speed_multiplier=1.5,   # 50% slower
        head_tilt_multiplier=0.50,
        expressiveness=ExpressivenessLevel.SUBTLE
    )),
    (0.40, ModulationParams(
        amplitude_multiplier=0.25,
        speed_multiplier=2.0,   # 100% slower (half speed)
        head_tilt_multiplier=0.25,
        expressiveness=ExpressivenessLevel.MINIMAL
    )),
]


def get_modulation_params(confidence: float) -> ModulationParams:
    """
    Get modulation parameters for a given confidence score.
    
    Args:
        confidence: Emotion detection confidence [0, 1]
        
    Returns:
        ModulationParams for the appropriate expressiveness tier
    """
    for threshold, params in CONFIDENCE_TIERS:
        if confidence >= threshold:
            return params
    
    # Below all thresholds - abstain
    return ModulationParams(
        amplitude_multiplier=0.0,
        speed_multiplier=1.0,
        head_tilt_multiplier=0.0,
        expressiveness=ExpressivenessLevel.ABSTAIN
    )


def _modulate_joint_position(
    joints: JointPosition,
    amplitude_multiplier: float
) -> JointPosition:
    """
    Scale joint angles by amplitude multiplier.
    
    Args:
        joints: Original joint positions
        amplitude_multiplier: Scale factor (0-1)
        
    Returns:
        Modulated JointPosition
    """
    return JointPosition(
        shoulder_pitch=joints.shoulder_pitch * amplitude_multiplier,
        shoulder_roll=joints.shoulder_roll * amplitude_multiplier,
        arm_yaw=joints.arm_yaw * amplitude_multiplier,
        elbow_pitch=joints.elbow_pitch * amplitude_multiplier,
        forearm_yaw=joints.forearm_yaw * amplitude_multiplier,
        wrist_pitch=joints.wrist_pitch * amplitude_multiplier,
        wrist_roll=joints.wrist_roll * amplitude_multiplier,
        gripper=joints.gripper,  # Don't scale gripper
    )


def _modulate_arm_position(
    arm_pos: ArmPosition,
    params: ModulationParams
) -> ArmPosition:
    """
    Modulate an arm position based on confidence parameters.
    
    Args:
        arm_pos: Original arm position
        params: Modulation parameters
        
    Returns:
        Modulated ArmPosition
    """
    return ArmPosition(
        side=arm_pos.side,
        joints=_modulate_joint_position(
            arm_pos.joints,
            params.amplitude_multiplier
        ),
        duration=arm_pos.duration * params.speed_multiplier,
    )


def _modulate_head_position(
    head_pos: HeadPosition,
    params: ModulationParams
) -> HeadPosition:
    """
    Modulate a head position based on confidence parameters.
    
    Args:
        head_pos: Original head position
        params: Modulation parameters
        
    Returns:
        Modulated HeadPosition
    """
    return HeadPosition(
        roll=head_pos.roll * params.head_tilt_multiplier,
        pitch=head_pos.pitch * params.head_tilt_multiplier,
        yaw=head_pos.yaw * params.head_tilt_multiplier,
        duration=head_pos.duration * params.speed_multiplier,
    )


def modulate_gesture(
    gesture: Gesture,
    confidence: float
) -> Optional[Gesture]:
    """
    Modulate a gesture based on emotion confidence score.
    
    This is the core function for degree-modulated expressiveness.
    The same gesture is performed with varying intensity based on
    how confident the model is about the detected emotion.
    
    Args:
        gesture: Base gesture to modulate
        confidence: Model confidence score [0, 1]
        
    Returns:
        Modulated Gesture, or None if confidence is too low (abstain)
        
    Example:
        >>> empathy = GESTURE_LIBRARY[GestureType.EMPATHY]
        >>> # High confidence: full expression
        >>> modulate_gesture(empathy, 0.95)  # Returns full gesture
        >>> # Moderate confidence: tempered expression
        >>> modulate_gesture(empathy, 0.72)  # Returns 75% amplitude, slower
        >>> # Low confidence: abstain
        >>> modulate_gesture(empathy, 0.35)  # Returns None
    """
    params = get_modulation_params(confidence)
    
    if params.expressiveness == ExpressivenessLevel.ABSTAIN:
        return None
    
    # Create modulated copies of arm and head sequences
    modulated_arms = [
        _modulate_arm_position(arm, params)
        for arm in gesture.arm_sequence
    ]
    
    modulated_heads = [
        _modulate_head_position(head, params)
        for head in gesture.head_sequence
    ]
    
    # Calculate new total duration
    total_duration = gesture.total_duration * params.speed_multiplier
    
    return Gesture(
        name=f"{gesture.name}_{params.expressiveness.value}",
        gesture_type=gesture.gesture_type,
        description=f"{gesture.description} (modulated: {params.expressiveness.value})",
        arm_sequence=modulated_arms,
        head_sequence=modulated_heads,
        total_duration=total_duration,
        loop=gesture.loop,
        loop_count=gesture.loop_count,
    )


def get_modulated_gesture_for_emotion(
    emotion: str,
    confidence: float,
    gesture_type: Optional[GestureType] = None
) -> Optional[Gesture]:
    """
    Get a modulated gesture appropriate for the emotion and confidence.
    
    If no specific gesture_type is provided, uses the default for the emotion.
    
    Args:
        emotion: Detected emotion label
        confidence: Model confidence score [0, 1]
        gesture_type: Optional specific gesture to use
        
    Returns:
        Modulated Gesture, or None if abstaining
    """
    from apps.reachy.gestures.emotion_gesture_map import (
        EmotionGestureMapper,
    )
    
    mapper = EmotionGestureMapper()
    
    if gesture_type is None:
        gesture_type = mapper.get_default_gesture(emotion)
    
    base_gesture = GESTURE_LIBRARY.get(gesture_type)
    
    if base_gesture is None:
        return None
    
    return modulate_gesture(base_gesture, confidence)


class GestureModulator:
    """
    Stateful gesture modulator that tracks expressiveness decisions.
    
    This class wraps the modulation functions and provides logging/metrics
    for observability of the EQ system's behavior.
    """
    
    def __init__(self):
        self._last_expressiveness: Optional[ExpressivenessLevel] = None
        self._modulation_count: int = 0
        self._abstain_count: int = 0
    
    def modulate(
        self,
        gesture: Gesture,
        confidence: float
    ) -> Optional[Gesture]:
        """
        Modulate a gesture and track statistics.
        
        Args:
            gesture: Base gesture to modulate
            confidence: Model confidence score
            
        Returns:
            Modulated gesture or None if abstaining
        """
        params = get_modulation_params(confidence)
        self._last_expressiveness = params.expressiveness
        
        result = modulate_gesture(gesture, confidence)
        
        if result is None:
            self._abstain_count += 1
        else:
            self._modulation_count += 1
        
        return result
    
    def get_expressiveness_for_confidence(
        self,
        confidence: float
    ) -> ExpressivenessLevel:
        """Get the expressiveness level for a confidence score."""
        return get_modulation_params(confidence).expressiveness
    
    @property
    def last_expressiveness(self) -> Optional[ExpressivenessLevel]:
        """Get the last expressiveness level used."""
        return self._last_expressiveness
    
    @property
    def stats(self) -> dict:
        """Get modulation statistics."""
        total = self._modulation_count + self._abstain_count
        return {
            "total_requests": total,
            "modulated": self._modulation_count,
            "abstained": self._abstain_count,
            "abstain_rate": self._abstain_count / total if total > 0 else 0.0,
        }
    
    def reset_stats(self) -> None:
        """Reset modulation statistics."""
        self._modulation_count = 0
        self._abstain_count = 0
