"""
Gesture Keywords for LLM Responses

Defines the keywords that the LLM should embed in responses to trigger
specific Reachy robot gestures.
"""

from typing import Dict, List


GESTURE_KEYWORDS: List[str] = [
    "WAVE",
    "NOD",
    "SHAKE",
    "SHRUG",
    "THUMBS_UP",
    "OPEN_ARMS",
    "HUG",
    "THINK",
    "EXCITED",
    "COMFORT",
    "LISTEN",
    "CELEBRATE",
    "EMPATHY",
    "SAD_ACK",
]


KEYWORD_DESCRIPTIONS: Dict[str, str] = {
    "WAVE": "Friendly wave greeting - use when greeting or saying goodbye",
    "NOD": "Affirmative head nod - use to show agreement or understanding",
    "SHAKE": "Head shake - use to express disagreement or concern",
    "SHRUG": "Shoulder shrug - use when uncertain or acknowledging complexity",
    "THUMBS_UP": "Positive thumbs up - use to encourage or celebrate small wins",
    "OPEN_ARMS": "Welcoming open arms - use to show openness and acceptance",
    "HUG": "Comforting hug gesture - use for deep emotional support moments",
    "THINK": "Thoughtful pose - use when considering or reflecting",
    "EXCITED": "Excited celebration - use for very positive moments",
    "COMFORT": "Gentle comfort gesture - use to soothe and reassure",
    "LISTEN": "Attentive listening pose - use to show active listening",
    "CELEBRATE": "Full celebration - use for major achievements or breakthroughs",
    "EMPATHY": "Deep empathetic gesture - use to show profound understanding",
    "SAD_ACK": "Acknowledge sadness - use to validate sad feelings",
}


def get_keyword_list_for_prompt() -> str:
    """
    Generate a formatted list of keywords for inclusion in system prompts.
    
    Returns:
        Formatted string describing available gesture keywords
    """
    lines = ["Available gesture keywords (use format [KEYWORD]):"]
    
    for keyword in GESTURE_KEYWORDS:
        description = KEYWORD_DESCRIPTIONS.get(keyword, "")
        lines.append(f"  - [{keyword}]: {description}")
    
    return "\n".join(lines)


def get_keywords_for_emotion(emotion: str) -> List[str]:
    """
    Get recommended keywords for a specific emotion.
    
    Args:
        emotion: The detected emotion (e.g., "happy", "sad")
        
    Returns:
        List of recommended gesture keywords
    """
    emotion_lower = emotion.lower()
    
    emotion_keyword_map = {
        "happy": ["THUMBS_UP", "CELEBRATE", "EXCITED", "NOD", "WAVE"],
        "sad": ["EMPATHY", "COMFORT", "HUG", "SAD_ACK", "LISTEN"],
        "neutral": ["NOD", "LISTEN", "THINK", "WAVE"],
        "anger": ["LISTEN", "NOD", "SHRUG"],
        "fear": ["COMFORT", "EMPATHY", "OPEN_ARMS"],
        "disgust": ["SHRUG", "NOD", "LISTEN"],
        "contempt": ["SHRUG", "NOD"],
        "surprise": ["EXCITED", "OPEN_ARMS", "NOD"],
    }
    
    return emotion_keyword_map.get(emotion_lower, ["NOD", "LISTEN"])
