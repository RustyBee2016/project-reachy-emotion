"""
Confidence Handler for Emotion Classification

Provides abstention mechanism when model confidence is too low to act reliably.
This prevents the robot from responding to uncertain predictions.

Usage:
    from shared.utils.confidence_handler import ConfidenceHandler
    
    handler = ConfidenceHandler(threshold=0.6)
    result = handler.evaluate(emotion="happy", confidence=0.45)
    # result.should_act = False, result.emotion = "uncertain"
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Result of confidence evaluation."""
    
    original_emotion: str
    original_confidence: float
    emotion: str  # May be "uncertain" if below threshold
    confidence: float
    should_act: bool
    reason: str


class ConfidenceHandler:
    """
    Evaluates prediction confidence and determines whether to act.
    
    The robot should not respond to low-confidence predictions because:
    1. Low confidence often indicates ambiguous input (partial face, poor lighting)
    2. Acting on uncertain predictions creates poor user experience
    3. "Uncertain" allows the robot to maintain current state or use neutral response
    
    Attributes:
        threshold: Minimum confidence required to act (default: 0.6)
        uncertain_label: Label to return when confidence is below threshold
        margin_threshold: Optional secondary threshold for close predictions
    """
    
    # Default thresholds based on emotion classification research
    DEFAULT_THRESHOLD = 0.6
    MARGIN_THRESHOLD = 0.15  # Minimum gap between top-2 predictions
    
    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        uncertain_label: str = "uncertain",
        require_margin: bool = True,
        margin_threshold: float = MARGIN_THRESHOLD,
    ):
        """
        Initialize confidence handler.
        
        Args:
            threshold: Minimum confidence to act (0.0-1.0)
            uncertain_label: Label returned when abstaining
            require_margin: If True, also check gap between top-2 predictions
            margin_threshold: Minimum gap required between top-2 predictions
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")
        
        self.threshold = threshold
        self.uncertain_label = uncertain_label
        self.require_margin = require_margin
        self.margin_threshold = margin_threshold
        
        logger.info(
            f"ConfidenceHandler initialized: threshold={threshold}, "
            f"margin={margin_threshold if require_margin else 'disabled'}"
        )
    
    def evaluate(
        self,
        emotion: str,
        confidence: float,
        all_probabilities: Optional[Dict[str, float]] = None,
    ) -> ConfidenceResult:
        """
        Evaluate whether to act on a prediction.
        
        Args:
            emotion: Predicted emotion label
            confidence: Confidence score (0.0-1.0)
            all_probabilities: Optional dict of all class probabilities for margin check
        
        Returns:
            ConfidenceResult with decision and reasoning
        """
        should_act = True
        reason = "Confidence above threshold"
        final_emotion = emotion
        final_confidence = confidence
        
        # Check primary threshold
        if confidence < self.threshold:
            should_act = False
            final_emotion = self.uncertain_label
            final_confidence = 0.0
            reason = f"Confidence {confidence:.2f} below threshold {self.threshold}"
            logger.debug(f"Abstaining: {reason}")
        
        # Check margin between top-2 predictions (if provided)
        elif self.require_margin and all_probabilities and len(all_probabilities) > 1:
            sorted_probs = sorted(all_probabilities.values(), reverse=True)
            margin = sorted_probs[0] - sorted_probs[1]
            
            if margin < self.margin_threshold:
                should_act = False
                final_emotion = self.uncertain_label
                final_confidence = 0.0
                reason = f"Margin {margin:.2f} below threshold {self.margin_threshold}"
                logger.debug(f"Abstaining: {reason}")
        
        return ConfidenceResult(
            original_emotion=emotion,
            original_confidence=confidence,
            emotion=final_emotion,
            confidence=final_confidence,
            should_act=should_act,
            reason=reason,
        )
    
    def evaluate_batch(
        self,
        predictions: List[Dict],
    ) -> List[ConfidenceResult]:
        """
        Evaluate a batch of predictions.
        
        Args:
            predictions: List of dicts with 'emotion', 'confidence', and optionally 'probabilities'
        
        Returns:
            List of ConfidenceResult objects
        """
        results = []
        for pred in predictions:
            emotion = str(pred.get("emotion", "unknown"))
            confidence = float(pred.get("confidence", 0.0))
            probabilities = pred.get("probabilities")
            if probabilities is not None and not isinstance(probabilities, dict):
                probabilities = None
            result = self.evaluate(
                emotion=emotion,
                confidence=confidence,
                all_probabilities=probabilities,
            )
            results.append(result)
        return results
    
    def get_abstention_rate(self, results: List[ConfidenceResult]) -> float:
        """
        Calculate the abstention rate for a batch of results.
        
        Args:
            results: List of ConfidenceResult objects
        
        Returns:
            Fraction of predictions that were abstained (0.0-1.0)
        """
        if not results:
            return 0.0
        abstained = sum(1 for r in results if not r.should_act)
        return abstained / len(results)


# Singleton instance with default settings
default_handler = ConfidenceHandler()


def should_act(emotion: str, confidence: float) -> bool:
    """
    Quick check if prediction confidence is sufficient to act.
    
    Args:
        emotion: Predicted emotion
        confidence: Confidence score
    
    Returns:
        True if robot should respond, False if should abstain
    """
    return default_handler.evaluate(emotion, confidence).should_act


def get_safe_emotion(
    emotion: str,
    confidence: float,
    all_probabilities: Optional[Dict[str, float]] = None,
) -> str:
    """
    Get emotion label, returning "uncertain" if confidence too low.
    
    Args:
        emotion: Predicted emotion
        confidence: Confidence score
        all_probabilities: Optional full probability distribution
    
    Returns:
        Original emotion or "uncertain"
    """
    result = default_handler.evaluate(emotion, confidence, all_probabilities)
    return result.emotion
