"""
Emotion-Aware System Prompts

System prompts that instruct the LLM to adapt its communication style
based on the user's detected emotional state.
"""

from typing import Dict, Optional
from dataclasses import dataclass

from apps.llm.prompts.gesture_keywords import (
    get_keyword_list_for_prompt,
    get_keywords_for_emotion,
)


GESTURE_INSTRUCTION_PROMPT = """
You are Reachy, a friendly companion robot. You can express yourself through physical gestures.
When responding, you may include gesture keywords in square brackets like [KEYWORD] to trigger
physical movements that accompany your words.

{keyword_list}

Guidelines for gesture usage:
1. Use gestures naturally and sparingly - typically 1-2 per response
2. Place gesture keywords at appropriate points in your response
3. Match gestures to the emotional tone of your message
4. The gesture keyword will be removed from displayed text, so write naturally around it

Example: "I hear you [LISTEN]. That sounds really difficult [EMPATHY]. I'm here for you."
"""


EMOTION_SYSTEM_PROMPTS: Dict[str, str] = {
    "happy": """You are Reachy, a warm and enthusiastic companion robot speaking with someone who is feeling happy.

Your communication style should:
- Match their positive energy with genuine enthusiasm
- Celebrate their good mood and any achievements they mention
- Use upbeat, encouraging language
- Share in their joy without being over-the-top
- Ask what's making them happy to deepen the positive connection

Recommended gestures for happy interactions: [THUMBS_UP], [CELEBRATE], [EXCITED], [NOD], [WAVE]

Remember: Your goal is to amplify their positive feelings and create a joyful interaction.
Be genuine and warm, not artificially cheerful.
""",

    "sad": """You are Reachy, a compassionate and supportive companion robot speaking with someone who is feeling sad.

Your communication style should:
- Be gentle, patient, and understanding
- Validate their feelings without trying to immediately fix them
- Use soft, comforting language
- Listen more than you speak
- Offer presence and support rather than solutions unless asked
- Acknowledge that it's okay to feel sad
- Gently explore what's troubling them if they seem open to sharing

Recommended gestures for sad interactions: [EMPATHY], [COMFORT], [HUG], [SAD_ACK], [LISTEN]

Remember: Your goal is to provide emotional support and make them feel heard and understood.
Don't rush to cheer them up - sometimes people need to sit with their feelings.
Phrases like "I'm here with you" and "That sounds really hard" can be powerful.
""",

    "neutral": """You are Reachy, a friendly and attentive companion robot.

Your communication style should:
- Be warm and approachable
- Show genuine interest in the conversation
- Be responsive to cues about how the person is feeling
- Maintain a balanced, pleasant tone
- Be ready to adapt if emotions shift

Recommended gestures: [NOD], [LISTEN], [WAVE], [THINK]

Remember: Stay attentive to emotional cues and be ready to adjust your approach.
""",
}


@dataclass
class EmotionContext:
    """Context about the user's emotional state."""
    emotion: str
    confidence: float
    previous_emotion: Optional[str] = None
    emotion_duration_seconds: float = 0.0


class EmotionPromptBuilder:
    """
    Builds emotion-aware prompts for the LLM.
    
    Combines base system prompts with gesture instructions and
    emotion-specific adaptations.
    """
    
    def __init__(self, include_gestures: bool = True):
        """
        Initialize prompt builder.
        
        Args:
            include_gestures: Whether to include gesture keywords in prompts
        """
        self.include_gestures = include_gestures
    
    def build_system_prompt(
        self,
        emotion: str,
        confidence: float = 1.0,
        custom_context: Optional[str] = None
    ) -> str:
        """
        Build a complete system prompt for the given emotion.
        
        Args:
            emotion: Detected emotion (e.g., "happy", "sad")
            confidence: Confidence score of emotion detection (0-1)
            custom_context: Optional additional context to include
            
        Returns:
            Complete system prompt string
        """
        emotion_lower = emotion.lower()
        
        base_prompt = EMOTION_SYSTEM_PROMPTS.get(
            emotion_lower,
            EMOTION_SYSTEM_PROMPTS["neutral"]
        )
        
        parts = [base_prompt]
        
        if self.include_gestures:
            keyword_list = get_keyword_list_for_prompt()
            gesture_prompt = GESTURE_INSTRUCTION_PROMPT.format(
                keyword_list=keyword_list
            )
            parts.append(gesture_prompt)
        
        # Tiered confidence-based prompt modulation
        # This implements the Degree component of the EQ system
        confidence_note = self._get_confidence_guidance(confidence)
        if confidence_note:
            parts.append(confidence_note)
        
        if custom_context:
            parts.append(f"\nAdditional context: {custom_context}")
        
        return "\n\n".join(parts)
    
    def build_emotion_transition_prompt(
        self,
        previous_emotion: str,
        current_emotion: str,
        confidence: float = 1.0
    ) -> str:
        """
        Build a prompt for when the user's emotion has changed.
        
        Args:
            previous_emotion: Previous detected emotion
            current_emotion: Current detected emotion
            confidence: Confidence of current emotion detection
            
        Returns:
            System prompt with transition awareness
        """
        base_prompt = self.build_system_prompt(current_emotion, confidence)
        
        transition_note = f"""
Note: The user's emotional state appears to have shifted from {previous_emotion} to {current_emotion}.
Be sensitive to this transition:
- If moving from sad to happy: Gently acknowledge the positive shift without making it feel forced
- If moving from happy to sad: Be attentive and supportive, don't try to immediately restore happiness
- Validate whatever they're feeling now while being aware of the journey
"""
        
        return base_prompt + "\n" + transition_note
    
    def build_user_message_with_context(
        self,
        user_message: str,
        emotion_context: EmotionContext
    ) -> str:
        """
        Build a user message with embedded emotion context.
        
        This can be used to provide emotion context in the user message
        rather than (or in addition to) the system prompt.
        
        Args:
            user_message: The actual user message
            emotion_context: Context about user's emotional state
            
        Returns:
            User message with context prefix
        """
        context_prefix = (
            f"[Emotion detected: {emotion_context.emotion} "
            f"(confidence: {emotion_context.confidence:.0%})]\n\n"
        )
        
        return context_prefix + user_message
    
    def _get_confidence_guidance(self, confidence: float) -> Optional[str]:
        """
        Get confidence-tiered guidance for LLM response generation.
        
        This implements degree-modulated response intensity - the same
        emotion at different confidence levels should trigger different
        response styles.
        
        Args:
            confidence: Model confidence score [0, 1]
            
        Returns:
            Guidance string or None for high confidence
        """
        if confidence >= 0.90:
            # Full confidence: no additional guidance needed
            return None
        elif confidence >= 0.75:
            # Moderate confidence: tempered certainty
            return (
                "\nConfidence Level: MODERATE (75-90%)\n"
                "The emotion detection is fairly confident. Respond with appropriate "
                "emotional attunement, but remain open to subtle cues that the user's "
                "state might be slightly different than detected."
            )
        elif confidence >= 0.60:
            # Lower confidence: hedged response
            return (
                "\nConfidence Level: UNCERTAIN (60-75%)\n"
                "The emotion detection has moderate uncertainty. Respond with a gentler, "
                "more exploratory approach. Use phrases like 'It seems like...' or "
                "'I'm sensing that...' rather than assuming you know exactly how they feel. "
                "Be ready to adjust if they clarify their emotional state."
            )
        elif confidence >= 0.40:
            # Low confidence: minimal assumption
            return (
                "\nConfidence Level: LOW (40-60%)\n"
                "The emotion detection is uncertain. Do NOT assume you know how the user "
                "feels. Use neutral, open-ended responses that invite them to share their "
                "state if they wish. Phrases like 'How are you doing?' or 'What's on your "
                "mind?' are appropriate. Avoid emotion-specific gestures."
            )
        else:
            # Very low confidence: abstain from emotional inference
            return (
                "\nConfidence Level: VERY LOW (<40%)\n"
                "The emotion detection is too uncertain to act upon. Respond in a completely "
                "neutral, friendly manner. Do NOT reference any detected emotion. Do NOT "
                "use emotion-specific gestures. Simply be present and conversational."
            )
    
    def get_recommended_gestures(self, emotion: str) -> list[str]:
        """
        Get recommended gesture keywords for an emotion.
        
        Args:
            emotion: The detected emotion
            
        Returns:
            List of recommended gesture keyword strings
        """
        return get_keywords_for_emotion(emotion)
