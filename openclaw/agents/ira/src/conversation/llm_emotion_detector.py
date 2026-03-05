#!/usr/bin/env python3
"""
LLM-Based Emotion Detector
==========================

Uses LLM to accurately detect emotional state from messages.
Much more accurate than regex patterns - catches nuance, sarcasm, etc.

Falls back to fast regex detection for high-volume scenarios.
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Try to import centralized config
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config import OPENAI_API_KEY
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmotionalState(Enum):
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    STRESSED = "stressed"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    URGENT = "urgent"
    GRATEFUL = "grateful"
    UNCERTAIN = "uncertain"
    DISAPPOINTED = "disappointed"
    EXCITED = "excited"


class EmotionalIntensity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class EmotionalReading:
    primary_state: EmotionalState
    intensity: EmotionalIntensity
    confidence: float
    secondary_states: List[EmotionalState]
    signals: List[str]
    method: str  # "llm" or "regex"
    
    def to_dict(self) -> Dict:
        return {
            "primary_state": self.primary_state.value,
            "intensity": self.intensity.value,
            "confidence": self.confidence,
            "secondary_states": [s.value for s in self.secondary_states],
            "signals": self.signals,
            "method": self.method,
        }


LLM_PROMPT = """Analyze the emotional state of this message. Be concise.

Message:
{message}

Respond in JSON format:
{
  "primary_state": "one of: neutral, positive, stressed, frustrated, curious, urgent, grateful, uncertain, disappointed, excited",
  "intensity": "one of: mild, moderate, strong",
  "confidence": 0.0-1.0,
  "secondary_states": ["list of other emotions present"],
  "signals": ["specific phrases or patterns that indicate the emotion"]
}

Consider:
- Direct emotional words ("frustrated", "excited")
- Indirect signals (repeated questions, exclamation marks, apologetic tone)
- Context clues (time pressure, past issues mentioned)
- Sarcasm and implied frustration
- Professional vs emotional language mix"""


class LLMEmotionDetector:
    """
    Detects emotions using LLM for accuracy, with regex fallback.
    """
    
    def __init__(self, use_llm: bool = True, cache_results: bool = True):
        self.use_llm = use_llm and OPENAI_AVAILABLE
        self.cache_results = cache_results
        self._cache: Dict[str, EmotionalReading] = {}
        
        # Regex patterns for fallback
        self.patterns = {
            EmotionalState.FRUSTRATED: [
                (r"\b(frustrated|annoyed|irritated|fed up)\b", 0.9),
                (r"\b(again|already told|already asked|still waiting)\b", 0.7),
                (r"\b(this is (ridiculous|unacceptable|absurd))\b", 0.85),
                (r"(!{2,})", 0.5),
                (r"\b(how many times|repeatedly)\b", 0.75),
            ],
            EmotionalState.STRESSED: [
                (r"\b(stressed|overwhelmed|swamped|slammed)\b", 0.9),
                (r"\b(deadline|time crunch|running out of time)\b", 0.7),
                (r"\b(urgent|asap|immediately|critical)\b", 0.6),
                (r"\b(too much|can't keep up|drowning)\b", 0.75),
            ],
            EmotionalState.POSITIVE: [
                (r"\b(great|awesome|excellent|fantastic|wonderful)\b", 0.8),
                (r"\b(thank you|thanks|appreciate)\b", 0.6),
                (r"\b(love it|perfect|exactly what)\b", 0.85),
                (r"(😊|👍|🎉|❤️|✅)", 0.7),
            ],
            EmotionalState.GRATEFUL: [
                (r"\b(grateful|thankful|appreciate)\b", 0.9),
                (r"\b(thanks (so much|a lot|for everything))\b", 0.85),
                (r"\b(you('ve| have) been (so )?(helpful|great))\b", 0.8),
            ],
            EmotionalState.CURIOUS: [
                (r"\b(wondering|curious|interested)\b", 0.8),
                (r"\b(how does|what is|can you explain)\b", 0.6),
                (r"\b(tell me more|learn more)\b", 0.7),
                (r"\?{2,}", 0.5),
            ],
            EmotionalState.URGENT: [
                (r"\b(urgent|asap|immediately|right now)\b", 0.9),
                (r"\b(need (this )?(today|now|immediately))\b", 0.85),
                (r"\b(time.?sensitive|critical|emergency)\b", 0.8),
                (r"\b(can't wait|deadline is)\b", 0.7),
            ],
            EmotionalState.UNCERTAIN: [
                (r"\b(not sure|uncertain|confused|unclear)\b", 0.8),
                (r"\b(maybe|perhaps|possibly|might)\b", 0.5),
                (r"\b(don't (quite )?understand)\b", 0.75),
                (r"\b(what do you mean|can you clarify)\b", 0.7),
            ],
            EmotionalState.DISAPPOINTED: [
                (r"\b(disappointed|let down|expected (more|better))\b", 0.85),
                (r"\b(not what I (expected|wanted|hoped))\b", 0.8),
                (r"\b(unfortunately|sadly|regrettably)\b", 0.6),
            ],
            EmotionalState.EXCITED: [
                (r"\b(excited|thrilled|can't wait|looking forward)\b", 0.85),
                (r"!{3,}", 0.6),
                (r"\b(finally|at last)\b", 0.5),
                (r"(🎉|🚀|😄|🙌)", 0.7),
            ],
        }
    
    def detect(self, message: str, use_llm_override: bool = None) -> EmotionalReading:
        """
        Detect emotional state from message.
        
        Args:
            message: The message to analyze
            use_llm_override: Override default LLM setting for this call
        
        Returns:
            EmotionalReading with detected state
        """
        # Check cache
        cache_key = message[:200]
        if self.cache_results and cache_key in self._cache:
            return self._cache[cache_key]
        
        use_llm = use_llm_override if use_llm_override is not None else self.use_llm
        
        if use_llm:
            result = self._detect_with_llm(message)
            if result:
                if self.cache_results:
                    self._cache[cache_key] = result
                return result
        
        # Fallback to regex
        result = self._detect_with_regex(message)
        if self.cache_results:
            self._cache[cache_key] = result
        return result
    
    def _detect_with_llm(self, message: str) -> Optional[EmotionalReading]:
        """Use LLM for emotion detection."""
        try:
            api_key = OPENAI_API_KEY
            if not api_key:
                return None
            
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are an emotion analysis assistant. Respond only with valid JSON."},
                    {"role": "user", "content": LLM_PROMPT.format(message=message[:1000])}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content)
            
            # Convert to EmotionalReading
            primary = EmotionalState(data.get("primary_state", "neutral"))
            intensity = EmotionalIntensity(data.get("intensity", "mild"))
            confidence = float(data.get("confidence", 0.7))
            secondary = [EmotionalState(s) for s in data.get("secondary_states", []) if s in [e.value for e in EmotionalState]]
            signals = data.get("signals", [])
            
            return EmotionalReading(
                primary_state=primary,
                intensity=intensity,
                confidence=confidence,
                secondary_states=secondary,
                signals=signals,
                method="llm"
            )
            
        except Exception as e:
            print(f"[emotion_detector] LLM detection failed: {e}")
            return None
    
    def _detect_with_regex(self, message: str) -> EmotionalReading:
        """Fallback regex-based detection."""
        message_lower = message.lower()
        
        # Score each emotional state
        scores: Dict[EmotionalState, Tuple[float, List[str]]] = {}
        
        for state, patterns in self.patterns.items():
            state_score = 0.0
            state_signals = []
            
            for pattern, weight in patterns:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                if matches:
                    state_score += weight
                    state_signals.append(f"'{pattern}' matched")
            
            if state_score > 0:
                scores[state] = (state_score, state_signals)
        
        # Determine primary state
        if not scores:
            return EmotionalReading(
                primary_state=EmotionalState.NEUTRAL,
                intensity=EmotionalIntensity.MILD,
                confidence=0.5,
                secondary_states=[],
                signals=["No emotional signals detected"],
                method="regex"
            )
        
        sorted_states = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
        primary_state = sorted_states[0][0]
        primary_score = sorted_states[0][1][0]
        primary_signals = sorted_states[0][1][1]
        
        # Determine intensity
        if primary_score > 1.5:
            intensity = EmotionalIntensity.STRONG
        elif primary_score > 0.8:
            intensity = EmotionalIntensity.MODERATE
        else:
            intensity = EmotionalIntensity.MILD
        
        # Secondary states
        secondary = [s for s, _ in sorted_states[1:3] if scores[s][0] > 0.5]
        
        # Confidence based on signal strength
        confidence = min(0.85, 0.4 + primary_score * 0.2)
        
        return EmotionalReading(
            primary_state=primary_state,
            intensity=intensity,
            confidence=confidence,
            secondary_states=secondary,
            signals=primary_signals[:3],
            method="regex"
        )


# Response calibration guidance
CALIBRATION_GUIDANCE = {
    EmotionalState.NEUTRAL: None,
    EmotionalState.POSITIVE: "User is in a positive mood. Match their energy. Celebrate with them.",
    EmotionalState.STRESSED: "User seems stressed. Be calm and reassuring. Acknowledge the pressure before diving into solutions.",
    EmotionalState.FRUSTRATED: "User is frustrated. Validate their frustration first ('I understand this is frustrating'). Then move quickly to concrete solutions. Avoid being defensive.",
    EmotionalState.CURIOUS: "User is curious and engaged. Feed their interest with detailed information. Encourage their exploration.",
    EmotionalState.URGENT: "User needs urgency. Cut pleasantries. Lead with the answer. Be direct and action-oriented.",
    EmotionalState.GRATEFUL: "User is expressing gratitude. Accept graciously but briefly. Use this positive moment to deepen the relationship.",
    EmotionalState.UNCERTAIN: "User seems uncertain or confused. Be patient and clear. Break things down step by step. Ask if clarification would help.",
    EmotionalState.DISAPPOINTED: "User is disappointed. Acknowledge their disappointment. Take responsibility if appropriate. Focus on what can be done now.",
    EmotionalState.EXCITED: "User is excited! Match their enthusiasm. Build on this positive energy.",
}


def get_response_calibration(reading: EmotionalReading) -> Dict:
    """Get calibration guidance for a response."""
    guidance = CALIBRATION_GUIDANCE.get(reading.primary_state)
    
    return {
        "primary_state": reading.primary_state.value,
        "intensity": reading.intensity.value,
        "guidance": guidance,
        "should_acknowledge": reading.intensity != EmotionalIntensity.MILD and reading.primary_state != EmotionalState.NEUTRAL,
        "suggested_opener": _get_opener(reading),
    }


def _get_opener(reading: EmotionalReading) -> str:
    """Get a suggested opener based on emotional state."""
    if reading.intensity == EmotionalIntensity.MILD:
        return ""
    
    openers = {
        EmotionalState.STRESSED: "I understand things are hectic right now.",
        EmotionalState.FRUSTRATED: "I hear your frustration, and I want to help fix this.",
        EmotionalState.GRATEFUL: "You're very welcome!",
        EmotionalState.URGENT: "",  # Skip opener for urgent - get to the point
        EmotionalState.UNCERTAIN: "Let me help clarify this.",
        EmotionalState.DISAPPOINTED: "I'm sorry this hasn't met your expectations.",
        EmotionalState.EXCITED: "That's great to hear!",
        EmotionalState.POSITIVE: "Glad to hear things are going well!",
        EmotionalState.CURIOUS: "Great question!",
    }
    
    return openers.get(reading.primary_state, "")


# Module-level singleton
_detector: Optional[LLMEmotionDetector] = None


def get_emotion_detector(use_llm: bool = True) -> LLMEmotionDetector:
    """Get or create the emotion detector singleton."""
    global _detector
    if _detector is None:
        _detector = LLMEmotionDetector(use_llm=use_llm)
    return _detector


def detect_emotion(message: str, use_llm: bool = True) -> EmotionalReading:
    """Convenience function to detect emotion."""
    return get_emotion_detector(use_llm).detect(message)
