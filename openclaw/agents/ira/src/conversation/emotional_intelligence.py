"""
Emotional Intelligence Layer - Detects emotional state and calibrates response.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class EmotionalState(Enum):
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    STRESSED = "stressed"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    URGENT = "urgent"
    GRATEFUL = "grateful"
    UNCERTAIN = "uncertain"


class EmotionalIntensity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class EmotionalReading:
    primary_state: EmotionalState
    intensity: EmotionalIntensity
    secondary_state: Optional[EmotionalState] = None
    signals_detected: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "primary_state": self.primary_state.value,
            "intensity": self.intensity.value,
            "secondary_state": self.secondary_state.value if self.secondary_state else None,
            "signals_detected": self.signals_detected,
            "confidence": self.confidence,
        }


class EmotionalIntelligence:
    SIGNALS = {
        EmotionalState.POSITIVE: {
            "strong": [r"\b(thrilled|amazing|fantastic|excellent)\b", r"!{2,}"],
            "moderate": [r"\b(happy|pleased|excited|delighted)\b", r":[-]?\)|😊"],
            "mild": [r"\b(good|nice|fine)\b"],
        },
        EmotionalState.STRESSED: {
            "strong": [r"\b(desperate|overwhelm|panic|crisis)\b"],
            "moderate": [r"\b(stressed|anxious|worried|concerned|pressure|deadline)\b"],
            "mild": [r"\b(bit worried|tight timeline)\b"],
        },
        EmotionalState.FRUSTRATED: {
            "strong": [r"\b(furious|unacceptable|ridiculous)\b"],
            "moderate": [r"\b(frustrated|annoyed|disappointed)\b", r"\b(not working|broken)\b"],
            "mild": [r"\b(bit frustrated)\b"],
        },
        EmotionalState.CURIOUS: {
            "strong": [r"\b(fascinated|intrigued)\b"],
            "moderate": [r"\b(curious|wondering|interested)\b", r"\b(how does|what is|why)\b"],
            "mild": [r"\?$"],
        },
        EmotionalState.URGENT: {
            "strong": [r"\b(emergency|critical|urgent|asap|immediately)\b"],
            "moderate": [r"\b(soon|quickly|priority|rush)\b"],
            "mild": [r"\b(when can|how soon)\b"],
        },
        EmotionalState.GRATEFUL: {
            "strong": [r"\b(so grateful|deeply appreciate|can't thank you enough)\b"],
            "moderate": [r"\b(thank you so much|really appreciate)\b"],
            "mild": [r"\bthanks\b"],
        },
        EmotionalState.UNCERTAIN: {
            "strong": [r"\b(completely lost|no idea)\b"],
            "moderate": [r"\b(confused|unsure|not sure)\b"],
            "mild": [r"\b(maybe|perhaps)\b", r"\?{2,}"],
        },
    }
    
    def __init__(self):
        self.emotional_history: Dict[str, List[EmotionalReading]] = {}
    
    def read_emotion(self, message: str) -> EmotionalReading:
        message_lower = message.lower()
        detections = {}
        
        for state, intensity_patterns in self.SIGNALS.items():
            signals_found = []
            best_intensity = None
            for intensity_name, patterns in intensity_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        signals_found.append(pattern)
                        if best_intensity is None:
                            best_intensity = EmotionalIntensity[intensity_name.upper()]
            if signals_found:
                confidence = min(0.9, 0.3 + len(signals_found) * 0.2)
                detections[state] = (best_intensity or EmotionalIntensity.MILD, signals_found, confidence)
        
        if not detections:
            return EmotionalReading(primary_state=EmotionalState.NEUTRAL, intensity=EmotionalIntensity.MILD, confidence=0.5)
        
        sorted_states = sorted(detections.items(), key=lambda x: (x[1][2], len(x[1][1])), reverse=True)
        primary = sorted_states[0]
        secondary = sorted_states[1] if len(sorted_states) > 1 else None
        
        return EmotionalReading(
            primary_state=primary[0],
            intensity=primary[1][0],
            secondary_state=secondary[0] if secondary else None,
            signals_detected=primary[1][1],
            confidence=primary[1][2]
        )
    
    def track_emotion(self, contact_id: str, reading: EmotionalReading) -> None:
        if contact_id not in self.emotional_history:
            self.emotional_history[contact_id] = []
        self.emotional_history[contact_id].append(reading)
        if len(self.emotional_history[contact_id]) > 20:
            self.emotional_history[contact_id] = self.emotional_history[contact_id][-20:]
    
    def get_response_calibration(self, reading: EmotionalReading) -> Dict:
        calibrations = {
            EmotionalState.NEUTRAL: {"energy": "balanced", "guidance": None},
            EmotionalState.POSITIVE: {"energy": "upbeat", "guidance": "Match their energy. Celebrate with them."},
            EmotionalState.STRESSED: {"energy": "calm", "guidance": "Acknowledge the stress first. Be the calm in their storm."},
            EmotionalState.FRUSTRATED: {"energy": "calm_controlled", "guidance": "Validate frustration first. Move quickly to solutions."},
            EmotionalState.CURIOUS: {"energy": "engaged", "guidance": "Feed their curiosity. Be generous with information."},
            EmotionalState.URGENT: {"energy": "focused", "guidance": "Cut pleasantries. Get to the point. Show you understand time matters."},
            EmotionalState.GRATEFUL: {"energy": "warm", "guidance": "Accept graciously. Build on the positive moment."},
            EmotionalState.UNCERTAIN: {"energy": "steady", "guidance": "Be patient. Break things down. Don't overwhelm."},
        }
        return calibrations.get(reading.primary_state, calibrations[EmotionalState.NEUTRAL])


EMOTIONAL_OPENERS = {
    EmotionalState.POSITIVE: ["That's great to hear!", "Excellent!", "Love it."],
    EmotionalState.STRESSED: ["I hear you - let's tackle this together.", "Understood. Let me help sort this out."],
    EmotionalState.FRUSTRATED: ["I completely understand the frustration.", "That's not good - let's fix this."],
    EmotionalState.CURIOUS: ["Good question!", "Let me walk you through this."],
    EmotionalState.URGENT: ["On it.", "Let's move quickly on this."],
    EmotionalState.GRATEFUL: ["Happy to help!", "Glad it worked out."],
    EmotionalState.UNCERTAIN: ["Let me clarify.", "No worries, I'll explain."],
}


def get_emotional_opener(state: EmotionalState) -> str:
    import random
    openers = EMOTIONAL_OPENERS.get(state, [""])
    return random.choice(openers) if openers else ""


def apply_emotional_calibration(base_prompt: str, calibration: Dict) -> str:
    if calibration.get("guidance"):
        return base_prompt + f"\n\nEMOTIONAL CALIBRATION: {calibration['guidance']}"
    return base_prompt


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Emotional Intelligence Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    detect_parser = subparsers.add_parser("detect", help="Detect emotion in text")
    detect_parser.add_argument("--text", required=True, help="Text to analyze")
    detect_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.command == "detect":
        detector = EmotionalIntelligence()
        reading = detector.read_emotion(args.text)
        calibration = detector.get_response_calibration(reading)
        
        if args.json:
            print(json.dumps({
                "primary_state": reading.primary_state.value,
                "intensity": reading.intensity.value,
                "secondary_state": reading.secondary_state.value if reading.secondary_state else None,
                "confidence": reading.confidence,
                "signals": reading.signals_detected,
                "calibration": calibration,
                "suggested_opener": get_emotional_opener(reading.primary_state),
            }, indent=2))
        else:
            print(f"Emotion: {reading.primary_state.value} ({reading.intensity.value})")
            print(f"Confidence: {reading.confidence:.0%}")
            if calibration.get("guidance"):
                print(f"Guidance: {calibration['guidance']}")
            opener = get_emotional_opener(reading.primary_state)
            if opener:
                print(f"Suggested opener: {opener}")
