"""
Emotion Smoother for Temporal Consistency

Prevents rapid emotion fluctuations (flicker) by requiring consistent
predictions over a sliding window before changing the reported emotion.

The Problem:
    At 30 FPS, independent frame predictions can oscillate rapidly:
    Frame 1: happy (0.72) → Frame 2: neutral (0.51) → Frame 3: happy (0.68)
    
    Without smoothing, this causes "gesture thrashing" where the robot
    starts a gesture, interrupts it, starts another, creating jarring UX.

The Solution:
    Maintain a sliding window of recent predictions. Only report an emotion
    if it dominates the window (appears in ≥60% of recent frames).
    
    This means:
    - Isolated noise frames are filtered out
    - Real emotion changes require ~0.3-0.5 seconds of consistency
    - During transitions, return "uncertain" to hold current gesture

Usage:
    from shared.utils.emotion_smoother import EmotionSmoother
    
    smoother = EmotionSmoother(window_size=15, min_consistency=0.6)
    
    # In inference loop:
    for frame in video_stream:
        raw_emotion, raw_confidence = model.predict(frame)
        smoothed = smoother.smooth(raw_emotion, raw_confidence)
        
        if smoothed.emotion != "uncertain":
            robot.set_gesture(smoothed.emotion)
"""

from collections import deque, Counter, defaultdict
from dataclasses import dataclass
from typing import Optional, List, Tuple, Deque
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class SmoothingMode(Enum):
    """Smoothing algorithm selection."""
    MAJORITY_VOTE = "majority_vote"  # Simple count-based
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence scores
    EXPONENTIAL_DECAY = "exponential_decay"  # Recent frames weighted more


@dataclass
class SmoothedResult:
    """Result of emotion smoothing."""
    
    raw_emotion: str
    raw_confidence: float
    emotion: str  # Smoothed emotion (may be "uncertain")
    confidence: float  # Aggregated confidence
    is_stable: bool  # True if emotion is consistent
    consistency_ratio: float  # Fraction of window with dominant emotion
    window_size: int
    transition_in_progress: bool  # True if emotion is changing


class EmotionSmoother:
    """
    Temporal smoother for emotion predictions.
    
    Maintains a sliding window of recent predictions and only reports
    an emotion when it consistently dominates the window.
    
    Attributes:
        window_size: Number of frames to consider (default: 15 = 0.5s at 30 FPS)
        min_consistency: Minimum fraction of window for dominant emotion (default: 0.6)
        mode: Smoothing algorithm to use
        uncertain_label: Label returned during transitions
    """
    
    # Recommended settings for different frame rates
    SETTINGS_30FPS = {"window_size": 15, "min_consistency": 0.6}  # 0.5s window
    SETTINGS_15FPS = {"window_size": 8, "min_consistency": 0.6}   # 0.5s window
    SETTINGS_10FPS = {"window_size": 5, "min_consistency": 0.6}   # 0.5s window
    
    def __init__(
        self,
        window_size: int = 15,
        min_consistency: float = 0.6,
        mode: SmoothingMode = SmoothingMode.CONFIDENCE_WEIGHTED,
        uncertain_label: str = "uncertain",
        decay_factor: float = 0.9,  # For exponential decay mode
    ):
        """
        Initialize emotion smoother.
        
        Args:
            window_size: Number of frames in sliding window
            min_consistency: Minimum ratio for dominant emotion (0.0-1.0)
            mode: Smoothing algorithm to use
            uncertain_label: Label returned when no clear dominant emotion
            decay_factor: Weight decay for exponential mode (0.0-1.0)
        """
        if window_size < 1:
            raise ValueError(f"Window size must be ≥1, got {window_size}")
        if not 0.0 < min_consistency <= 1.0:
            raise ValueError(f"min_consistency must be in (0, 1], got {min_consistency}")
        
        self.window_size = window_size
        self.min_consistency = min_consistency
        self.mode = mode
        self.uncertain_label = uncertain_label
        self.decay_factor = decay_factor
        
        # Sliding window: stores (emotion, confidence, timestamp)
        self.history: Deque[Tuple[str, float, float]] = deque(maxlen=window_size)
        
        # Track last stable emotion for transition detection
        self._last_stable_emotion: Optional[str] = None
        self._transition_start_time: Optional[float] = None
        
        logger.info(
            f"EmotionSmoother initialized: window={window_size}, "
            f"consistency={min_consistency}, mode={mode.value}"
        )
    
    def smooth(self, emotion: str, confidence: float) -> SmoothedResult:
        """
        Add a prediction and get smoothed result.
        
        Args:
            emotion: Raw predicted emotion
            confidence: Raw confidence score (0.0-1.0)
        
        Returns:
            SmoothedResult with temporal smoothing applied
        """
        timestamp = time.time()
        self.history.append((emotion, confidence, timestamp))
        
        # Not enough data yet - return raw prediction
        if len(self.history) < self.window_size // 2:
            return SmoothedResult(
                raw_emotion=emotion,
                raw_confidence=confidence,
                emotion=emotion,
                confidence=confidence,
                is_stable=False,
                consistency_ratio=1.0,
                window_size=len(self.history),
                transition_in_progress=False,
            )
        
        # Calculate dominant emotion based on mode
        if self.mode == SmoothingMode.MAJORITY_VOTE:
            dominant, ratio, agg_confidence = self._majority_vote()
        elif self.mode == SmoothingMode.CONFIDENCE_WEIGHTED:
            dominant, ratio, agg_confidence = self._confidence_weighted()
        else:  # EXPONENTIAL_DECAY
            dominant, ratio, agg_confidence = self._exponential_decay()
        
        # Determine if stable
        is_stable = ratio >= self.min_consistency
        
        # Detect transition
        transition_in_progress = False
        if is_stable:
            if self._last_stable_emotion is not None and dominant != self._last_stable_emotion:
                logger.debug(f"Emotion transition: {self._last_stable_emotion} → {dominant}")
            self._last_stable_emotion = dominant
            self._transition_start_time = None
        else:
            transition_in_progress = True
            if self._transition_start_time is None:
                self._transition_start_time = timestamp
        
        # Return smoothed result
        final_emotion = dominant if is_stable else self.uncertain_label
        final_confidence = agg_confidence if is_stable else 0.0
        
        return SmoothedResult(
            raw_emotion=emotion,
            raw_confidence=confidence,
            emotion=final_emotion,
            confidence=final_confidence,
            is_stable=is_stable,
            consistency_ratio=ratio,
            window_size=len(self.history),
            transition_in_progress=transition_in_progress,
        )
    
    def _majority_vote(self) -> Tuple[str, float, float]:
        """
        Simple majority vote smoothing.
        
        Returns:
            (dominant_emotion, consistency_ratio, average_confidence)
        """
        emotions = [e for e, c, t in self.history]
        counts = Counter(emotions)
        dominant, count = counts.most_common(1)[0]
        ratio = count / len(self.history)
        
        # Average confidence for dominant emotion
        confidences = [c for e, c, t in self.history if e == dominant]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return dominant, ratio, avg_confidence
    
    def _confidence_weighted(self) -> Tuple[str, float, float]:
        """
        Confidence-weighted voting.
        
        High-confidence predictions count more than low-confidence ones.
        
        Returns:
            (dominant_emotion, weighted_ratio, weighted_confidence)
        """
        weighted_votes: dict[str, float] = {}
        
        for emotion, confidence, _ in self.history:
            weighted_votes[emotion] = weighted_votes.get(emotion, 0.0) + confidence
        
        total_weight = sum(weighted_votes.values())
        if total_weight == 0:
            return self.uncertain_label, 0.0, 0.0
        
        dominant = max(weighted_votes.keys(), key=lambda k: weighted_votes[k])
        ratio = weighted_votes[dominant] / total_weight
        
        # Weighted average confidence for dominant
        dominant_weights = [c for e, c, t in self.history if e == dominant]
        avg_confidence = sum(dominant_weights) / len(dominant_weights) if dominant_weights else 0.0
        
        return dominant, ratio, avg_confidence
    
    def _exponential_decay(self) -> Tuple[str, float, float]:
        """
        Exponential decay weighting (recent frames matter more).
        
        Returns:
            (dominant_emotion, weighted_ratio, weighted_confidence)
        """
        weighted_votes: dict[str, float] = {}
        total_weight = 0.0
        
        # Most recent frame has weight 1.0, older frames decay
        history_list = list(self.history)
        for i, (emotion, confidence, _) in enumerate(history_list):
            # Decay based on position (0 = oldest, len-1 = newest)
            age = len(history_list) - 1 - i
            weight = (self.decay_factor ** age) * confidence
            weighted_votes[emotion] = weighted_votes.get(emotion, 0.0) + weight
            total_weight += weight
        
        if total_weight == 0:
            return self.uncertain_label, 0.0, 0.0
        
        dominant = max(weighted_votes.keys(), key=lambda k: weighted_votes[k])
        ratio = weighted_votes[dominant] / total_weight
        
        # Recent confidence for dominant
        recent_dominant = [(c, t) for e, c, t in history_list[-5:] if e == dominant]
        avg_confidence = sum(c for c, t in recent_dominant) / len(recent_dominant) if recent_dominant else 0.0
        
        return dominant, ratio, avg_confidence
    
    def reset(self) -> None:
        """Clear history and reset state."""
        self.history.clear()
        self._last_stable_emotion = None
        self._transition_start_time = None
        logger.debug("EmotionSmoother reset")
    
    def get_window_stats(self) -> dict:
        """
        Get current window statistics for debugging/monitoring.
        
        Returns:
            Dict with window state information
        """
        if not self.history:
            return {"empty": True}
        
        emotions = [e for e, c, t in self.history]
        counts = Counter(emotions)
        
        return {
            "window_size": len(self.history),
            "max_window_size": self.window_size,
            "emotion_counts": dict(counts),
            "last_stable_emotion": self._last_stable_emotion,
            "oldest_timestamp": self.history[0][2] if self.history else None,
            "newest_timestamp": self.history[-1][2] if self.history else None,
        }


# Factory functions for common configurations
def create_smoother_30fps() -> EmotionSmoother:
    """Create smoother optimized for 30 FPS video."""
    return EmotionSmoother(**EmotionSmoother.SETTINGS_30FPS)


def create_smoother_15fps() -> EmotionSmoother:
    """Create smoother optimized for 15 FPS video."""
    return EmotionSmoother(**EmotionSmoother.SETTINGS_15FPS)


def create_smoother_10fps() -> EmotionSmoother:
    """Create smoother optimized for 10 FPS video."""
    return EmotionSmoother(**EmotionSmoother.SETTINGS_10FPS)
