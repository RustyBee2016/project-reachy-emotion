from __future__ import annotations

from sqlalchemy import Enum

VIDEO_SPLIT_ENUM_NAME = "video_split_enum"
EMOTION_ENUM_NAME = "emotion_enum"
SELECTION_TARGET_ENUM_NAME = "training_selection_target_enum"

SplitEnum = Enum(
    "temp",
    "dataset_all",
    "train",
    "test",
    "purged",
    name=VIDEO_SPLIT_ENUM_NAME,
    create_constraint=True,
    native_enum=False,
    validate_strings=True,
)

EmotionEnum = Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    "fearful",
    name=EMOTION_ENUM_NAME,
    create_constraint=True,
    native_enum=False,
    validate_strings=True,
)

SelectionTargetEnum = Enum(
    "train",
    "test",
    name=SELECTION_TARGET_ENUM_NAME,
    create_constraint=True,
    native_enum=False,
    validate_strings=True,
)