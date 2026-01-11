"""
Emotion-to-Gesture Mapping

Maps detected emotions to appropriate Reachy gestures and defines
keywords that can be parsed from LLM responses to trigger gestures.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set
import re

from apps.reachy.gestures.gesture_definitions import GestureType, Gesture, GESTURE_LIBRARY


class GestureKeyword(Enum):
    """
    Keywords that can appear in LLM responses to trigger gestures.
    
    Format in LLM response: [KEYWORD] or <KEYWORD>
    Example: "I understand how you feel [HUG]. Let me help you."
    """
    WAVE = "WAVE"
    NOD = "NOD"
    SHAKE = "SHAKE"
    SHRUG = "SHRUG"
    THUMBS_UP = "THUMBS_UP"
    OPEN_ARMS = "OPEN_ARMS"
    HUG = "HUG"
    POINT = "POINT"
    THINK = "THINK"
    EXCITED = "EXCITED"
    COMFORT = "COMFORT"
    LISTEN = "LISTEN"
    CELEBRATE = "CELEBRATE"
    EMPATHY = "EMPATHY"
    SAD_ACK = "SAD_ACK"


KEYWORD_TO_GESTURE: Dict[GestureKeyword, GestureType] = {
    GestureKeyword.WAVE: GestureType.WAVE,
    GestureKeyword.NOD: GestureType.NOD,
    GestureKeyword.SHAKE: GestureType.SHAKE_HEAD,
    GestureKeyword.SHRUG: GestureType.SHRUG,
    GestureKeyword.THUMBS_UP: GestureType.THUMBS_UP,
    GestureKeyword.OPEN_ARMS: GestureType.OPEN_ARMS,
    GestureKeyword.HUG: GestureType.HUG,
    GestureKeyword.THINK: GestureType.THINKING,
    GestureKeyword.EXCITED: GestureType.EXCITED,
    GestureKeyword.COMFORT: GestureType.COMFORT,
    GestureKeyword.LISTEN: GestureType.LISTENING,
    GestureKeyword.CELEBRATE: GestureType.CELEBRATE,
    GestureKeyword.EMPATHY: GestureType.EMPATHY,
    GestureKeyword.SAD_ACK: GestureType.SAD_ACKNOWLEDGE,
}


@dataclass
class EmotionGestureMapping:
    """Mapping from an emotion to its associated gestures."""
    emotion: str
    primary_gestures: List[GestureType]
    secondary_gestures: List[GestureType]
    default_gesture: GestureType


EMOTION_GESTURE_MAP: Dict[str, EmotionGestureMapping] = {
    "happy": EmotionGestureMapping(
        emotion="happy",
        primary_gestures=[
            GestureType.CELEBRATE,
            GestureType.EXCITED,
            GestureType.THUMBS_UP,
        ],
        secondary_gestures=[
            GestureType.WAVE,
            GestureType.NOD,
            GestureType.OPEN_ARMS,
        ],
        default_gesture=GestureType.THUMBS_UP,
    ),
    "sad": EmotionGestureMapping(
        emotion="sad",
        primary_gestures=[
            GestureType.COMFORT,
            GestureType.EMPATHY,
            GestureType.SAD_ACKNOWLEDGE,
        ],
        secondary_gestures=[
            GestureType.HUG,
            GestureType.LISTENING,
            GestureType.NOD,
        ],
        default_gesture=GestureType.EMPATHY,
    ),
}


class EmotionGestureMapper:
    """
    Maps emotions to gestures and parses LLM responses for gesture keywords.
    
    This class provides the bridge between:
    1. Detected emotions → appropriate gestures
    2. LLM response keywords → specific gestures
    """
    
    KEYWORD_PATTERN = re.compile(r'\[([A-Z_]+)\]|<([A-Z_]+)>')
    
    def __init__(self):
        self._keyword_set: Set[str] = {k.value for k in GestureKeyword}
    
    def get_gestures_for_emotion(self, emotion: str) -> List[GestureType]:
        """
        Get appropriate gestures for a detected emotion.
        
        Args:
            emotion: Detected emotion label (e.g., "happy", "sad")
            
        Returns:
            List of appropriate gesture types, ordered by priority
        """
        emotion_lower = emotion.lower()
        mapping = EMOTION_GESTURE_MAP.get(emotion_lower)
        
        if mapping:
            return mapping.primary_gestures + mapping.secondary_gestures
        
        return [GestureType.NEUTRAL]
    
    def get_default_gesture(self, emotion: str) -> GestureType:
        """
        Get the default gesture for an emotion.
        
        Args:
            emotion: Detected emotion label
            
        Returns:
            Default gesture type for the emotion
        """
        emotion_lower = emotion.lower()
        mapping = EMOTION_GESTURE_MAP.get(emotion_lower)
        
        if mapping:
            return mapping.default_gesture
        
        return GestureType.NEUTRAL
    
    def parse_keywords_from_response(self, llm_response: str) -> List[GestureKeyword]:
        """
        Parse gesture keywords from an LLM response.
        
        Looks for patterns like [KEYWORD] or <KEYWORD> in the response.
        
        Args:
            llm_response: The text response from the LLM
            
        Returns:
            List of gesture keywords found in order of appearance
        """
        keywords = []
        
        for match in self.KEYWORD_PATTERN.finditer(llm_response):
            keyword_str = match.group(1) or match.group(2)
            
            if keyword_str in self._keyword_set:
                try:
                    keyword = GestureKeyword(keyword_str)
                    keywords.append(keyword)
                except ValueError:
                    pass
        
        return keywords
    
    def keywords_to_gestures(self, keywords: List[GestureKeyword]) -> List[GestureType]:
        """
        Convert gesture keywords to gesture types.
        
        Args:
            keywords: List of gesture keywords
            
        Returns:
            List of corresponding gesture types
        """
        return [
            KEYWORD_TO_GESTURE[kw]
            for kw in keywords
            if kw in KEYWORD_TO_GESTURE
        ]
    
    def extract_gestures_from_response(self, llm_response: str) -> List[Gesture]:
        """
        Extract full gesture definitions from an LLM response.
        
        Args:
            llm_response: The text response from the LLM
            
        Returns:
            List of Gesture objects to execute
        """
        keywords = self.parse_keywords_from_response(llm_response)
        gesture_types = self.keywords_to_gestures(keywords)
        
        gestures = []
        for gt in gesture_types:
            gesture = GESTURE_LIBRARY.get(gt)
            if gesture:
                gestures.append(gesture)
        
        return gestures
    
    def strip_keywords_from_response(self, llm_response: str) -> str:
        """
        Remove gesture keywords from LLM response for clean display.
        
        Args:
            llm_response: The text response from the LLM
            
        Returns:
            Response text with keywords removed
        """
        cleaned = self.KEYWORD_PATTERN.sub('', llm_response)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def get_gesture_for_emotion_context(
        self,
        emotion: str,
        confidence: float,
        llm_response: Optional[str] = None
    ) -> List[Gesture]:
        """
        Get gestures based on emotion context and optional LLM response.
        
        Priority:
        1. Keywords in LLM response (if provided)
        2. Default gesture for emotion (if confidence > 0.7)
        3. Neutral gesture
        
        Args:
            emotion: Detected emotion label
            confidence: Confidence score (0-1)
            llm_response: Optional LLM response to parse for keywords
            
        Returns:
            List of gestures to execute
        """
        gestures = []
        
        if llm_response:
            gestures = self.extract_gestures_from_response(llm_response)
        
        if not gestures and confidence > 0.7:
            default_type = self.get_default_gesture(emotion)
            default_gesture = GESTURE_LIBRARY.get(default_type)
            if default_gesture:
                gestures = [default_gesture]
        
        if not gestures:
            neutral = GESTURE_LIBRARY.get(GestureType.NEUTRAL)
            if neutral:
                gestures = [neutral]
        
        return gestures
