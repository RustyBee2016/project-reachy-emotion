"""
Gesture Definitions for Reachy Mini

Defines gesture primitives including arm positions, head movements, and
composite gestures that can be executed on the Reachy Mini robot.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple


class GestureType(Enum):
    """Types of gestures Reachy can perform."""
    WAVE = auto()
    NOD = auto()
    SHAKE_HEAD = auto()
    SHRUG = auto()
    THUMBS_UP = auto()
    OPEN_ARMS = auto()
    HUG = auto()
    POINT = auto()
    THINKING = auto()
    EXCITED = auto()
    COMFORT = auto()
    LISTENING = auto()
    CELEBRATE = auto()
    SAD_ACKNOWLEDGE = auto()
    EMPATHY = auto()
    NEUTRAL = auto()


class ArmSide(Enum):
    """Which arm to use."""
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


@dataclass
class JointPosition:
    """Position for a single joint in degrees."""
    shoulder_pitch: float = 0.0
    shoulder_roll: float = 0.0
    arm_yaw: float = 0.0
    elbow_pitch: float = 0.0
    forearm_yaw: float = 0.0
    wrist_pitch: float = 0.0
    wrist_roll: float = 0.0
    gripper: float = 0.0


@dataclass
class ArmPosition:
    """Complete arm position specification."""
    side: ArmSide
    joints: JointPosition
    duration: float = 1.0


@dataclass
class HeadPosition:
    """Head position specification."""
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    duration: float = 0.5


@dataclass
class Gesture:
    """
    Complete gesture definition.
    
    A gesture consists of a sequence of arm and head positions
    that are executed in order to create an expressive movement.
    """
    name: str
    gesture_type: GestureType
    description: str
    arm_sequence: List[ArmPosition] = field(default_factory=list)
    head_sequence: List[HeadPosition] = field(default_factory=list)
    total_duration: float = 2.0
    loop: bool = False
    loop_count: int = 1
    
    def __post_init__(self):
        if not self.arm_sequence and not self.head_sequence:
            pass


GESTURE_LIBRARY: dict[GestureType, Gesture] = {
    GestureType.WAVE: Gesture(
        name="wave",
        gesture_type=GestureType.WAVE,
        description="Friendly wave greeting",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-10.0,
                    shoulder_roll=-15.0,
                    elbow_pitch=-90.0,
                    wrist_roll=0.0,
                ),
                duration=0.5,
            ),
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-10.0,
                    shoulder_roll=-15.0,
                    elbow_pitch=-90.0,
                    wrist_roll=30.0,
                ),
                duration=0.3,
            ),
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-10.0,
                    shoulder_roll=-15.0,
                    elbow_pitch=-90.0,
                    wrist_roll=-30.0,
                ),
                duration=0.3,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=5.0, duration=0.5),
        ],
        total_duration=1.5,
        loop=True,
        loop_count=3,
    ),
    
    GestureType.NOD: Gesture(
        name="nod",
        gesture_type=GestureType.NOD,
        description="Affirmative head nod",
        head_sequence=[
            HeadPosition(pitch=15.0, duration=0.3),
            HeadPosition(pitch=-5.0, duration=0.3),
            HeadPosition(pitch=10.0, duration=0.3),
            HeadPosition(pitch=0.0, duration=0.3),
        ],
        total_duration=1.2,
    ),
    
    GestureType.SHAKE_HEAD: Gesture(
        name="shake_head",
        gesture_type=GestureType.SHAKE_HEAD,
        description="Negative head shake",
        head_sequence=[
            HeadPosition(yaw=20.0, duration=0.25),
            HeadPosition(yaw=-20.0, duration=0.25),
            HeadPosition(yaw=15.0, duration=0.25),
            HeadPosition(yaw=-15.0, duration=0.25),
            HeadPosition(yaw=0.0, duration=0.25),
        ],
        total_duration=1.25,
    ),
    
    GestureType.SHRUG: Gesture(
        name="shrug",
        gesture_type=GestureType.SHRUG,
        description="Uncertain shrug with both arms",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=0.0,
                    shoulder_roll=-30.0,
                    elbow_pitch=-45.0,
                    forearm_yaw=45.0,
                ),
                duration=0.5,
            ),
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=0.0,
                    shoulder_roll=0.0,
                    elbow_pitch=0.0,
                    forearm_yaw=0.0,
                ),
                duration=0.5,
            ),
        ],
        head_sequence=[
            HeadPosition(roll=10.0, pitch=5.0, duration=0.5),
            HeadPosition(roll=0.0, pitch=0.0, duration=0.5),
        ],
        total_duration=1.0,
    ),
    
    GestureType.THUMBS_UP: Gesture(
        name="thumbs_up",
        gesture_type=GestureType.THUMBS_UP,
        description="Positive thumbs up gesture",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-30.0,
                    shoulder_roll=-20.0,
                    elbow_pitch=-60.0,
                    wrist_pitch=0.0,
                    gripper=100.0,
                ),
                duration=0.6,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=10.0, duration=0.3),
        ],
        total_duration=1.0,
    ),
    
    GestureType.OPEN_ARMS: Gesture(
        name="open_arms",
        gesture_type=GestureType.OPEN_ARMS,
        description="Welcoming open arms gesture",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-20.0,
                    shoulder_roll=-60.0,
                    elbow_pitch=-30.0,
                    forearm_yaw=0.0,
                ),
                duration=0.8,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=5.0, duration=0.5),
        ],
        total_duration=1.5,
    ),
    
    GestureType.HUG: Gesture(
        name="hug",
        gesture_type=GestureType.HUG,
        description="Comforting hug gesture",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-20.0,
                    shoulder_roll=-60.0,
                    elbow_pitch=-30.0,
                ),
                duration=0.5,
            ),
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-10.0,
                    shoulder_roll=-20.0,
                    elbow_pitch=-90.0,
                ),
                duration=0.8,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=15.0, roll=5.0, duration=0.8),
        ],
        total_duration=2.0,
    ),
    
    GestureType.THINKING: Gesture(
        name="thinking",
        gesture_type=GestureType.THINKING,
        description="Thoughtful pose with hand near chin",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-45.0,
                    shoulder_roll=10.0,
                    elbow_pitch=-120.0,
                    wrist_pitch=20.0,
                ),
                duration=0.8,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=-10.0, roll=5.0, duration=0.5),
        ],
        total_duration=1.5,
    ),
    
    GestureType.EXCITED: Gesture(
        name="excited",
        gesture_type=GestureType.EXCITED,
        description="Excited celebration with raised arms",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-90.0,
                    shoulder_roll=-30.0,
                    elbow_pitch=-20.0,
                ),
                duration=0.4,
            ),
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-80.0,
                    shoulder_roll=-40.0,
                    elbow_pitch=-30.0,
                ),
                duration=0.3,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=-10.0, duration=0.3),
            HeadPosition(pitch=5.0, duration=0.2),
        ],
        total_duration=1.0,
        loop=True,
        loop_count=2,
    ),
    
    GestureType.COMFORT: Gesture(
        name="comfort",
        gesture_type=GestureType.COMFORT,
        description="Gentle comforting gesture",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-30.0,
                    shoulder_roll=-30.0,
                    elbow_pitch=-60.0,
                ),
                duration=0.8,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=10.0, roll=8.0, duration=0.6),
        ],
        total_duration=1.5,
    ),
    
    GestureType.LISTENING: Gesture(
        name="listening",
        gesture_type=GestureType.LISTENING,
        description="Attentive listening pose",
        head_sequence=[
            HeadPosition(pitch=5.0, roll=5.0, duration=0.5),
        ],
        total_duration=0.5,
    ),
    
    GestureType.CELEBRATE: Gesture(
        name="celebrate",
        gesture_type=GestureType.CELEBRATE,
        description="Celebratory gesture for happy moments",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-100.0,
                    shoulder_roll=-45.0,
                    elbow_pitch=-10.0,
                ),
                duration=0.5,
            ),
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-90.0,
                    shoulder_roll=-50.0,
                    elbow_pitch=-20.0,
                ),
                duration=0.3,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=-15.0, duration=0.4),
        ],
        total_duration=1.5,
        loop=True,
        loop_count=2,
    ),
    
    GestureType.SAD_ACKNOWLEDGE: Gesture(
        name="sad_acknowledge",
        gesture_type=GestureType.SAD_ACKNOWLEDGE,
        description="Acknowledging sadness with empathy",
        head_sequence=[
            HeadPosition(pitch=15.0, roll=10.0, duration=0.8),
            HeadPosition(pitch=10.0, roll=5.0, duration=0.5),
        ],
        arm_sequence=[
            ArmPosition(
                side=ArmSide.RIGHT,
                joints=JointPosition(
                    shoulder_pitch=-20.0,
                    shoulder_roll=-20.0,
                    elbow_pitch=-45.0,
                ),
                duration=0.8,
            ),
        ],
        total_duration=1.5,
    ),
    
    GestureType.EMPATHY: Gesture(
        name="empathy",
        gesture_type=GestureType.EMPATHY,
        description="Deep empathetic gesture with open posture",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(
                    shoulder_pitch=-15.0,
                    shoulder_roll=-40.0,
                    elbow_pitch=-45.0,
                ),
                duration=1.0,
            ),
        ],
        head_sequence=[
            HeadPosition(pitch=12.0, roll=8.0, duration=0.8),
        ],
        total_duration=2.0,
    ),
    
    GestureType.NEUTRAL: Gesture(
        name="neutral",
        gesture_type=GestureType.NEUTRAL,
        description="Return to neutral resting position",
        arm_sequence=[
            ArmPosition(
                side=ArmSide.BOTH,
                joints=JointPosition(),
                duration=1.0,
            ),
        ],
        head_sequence=[
            HeadPosition(duration=0.5),
        ],
        total_duration=1.0,
    ),
}


def get_gesture(gesture_type: GestureType) -> Optional[Gesture]:
    """Get a gesture definition by type."""
    return GESTURE_LIBRARY.get(gesture_type)


def list_gestures() -> List[str]:
    """List all available gesture names."""
    return [g.name for g in GESTURE_LIBRARY.values()]
