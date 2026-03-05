"""
Adaptive Communication Style
============================

Replika insight: Learn and adapt to each person's communication style.

Some people like detailed explanations, others want bullet points.
Some prefer formal language, others casual.
Mirror what works for each individual.

This module:
1. Analyzes user's communication patterns
2. Builds a style profile over time
3. Adapts Ira's responses to match
4. Tracks what resonates (via engagement signals)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class StyleProfile:
    """Communication style profile for a contact."""
    contact_id: str
    
    # Formality (0=very casual, 100=very formal)
    formality_score: float = 50.0
    formality_confidence: float = 0.0
    
    # Detail preference (0=brief, 100=comprehensive)
    detail_score: float = 50.0
    detail_confidence: float = 0.0
    
    # Technical level (0=non-technical, 100=expert)
    technical_score: float = 50.0
    technical_confidence: float = 0.0
    
    # Pace (0=patient, 100=urgent)
    pace_score: float = 50.0
    pace_confidence: float = 0.0
    
    # Emoji usage (0=never, 100=frequently)
    emoji_score: float = 30.0
    emoji_confidence: float = 0.0
    
    # Humor receptiveness (0=all business, 100=enjoys humor)
    humor_score: float = 30.0
    humor_confidence: float = 0.0
    
    # Message length typical
    avg_message_length: float = 100.0
    
    # Analysis history
    messages_analyzed: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "contact_id": self.contact_id,
            "formality_score": self.formality_score,
            "detail_score": self.detail_score,
            "technical_score": self.technical_score,
            "pace_score": self.pace_score,
            "emoji_score": self.emoji_score,
            "humor_score": self.humor_score,
            "avg_message_length": self.avg_message_length,
            "messages_analyzed": self.messages_analyzed,
        }
    
    def get_response_guidance(self) -> Dict[str, str]:
        """Get guidance for response generation based on profile."""
        guidance = {}
        
        # Formality
        if self.formality_score > 70:
            guidance["formality"] = "Use formal language. Avoid contractions and slang."
        elif self.formality_score < 30:
            guidance["formality"] = "Be casual and friendly. Contractions are fine."
        else:
            guidance["formality"] = "Use professional but approachable language."
        
        # Detail
        if self.detail_score > 70:
            guidance["detail"] = "Provide comprehensive detail. This person appreciates thorough explanations."
        elif self.detail_score < 30:
            guidance["detail"] = "Keep it brief. Get to the point quickly."
        else:
            guidance["detail"] = "Provide moderate detail with key points highlighted."
        
        # Technical
        if self.technical_score > 70:
            guidance["technical"] = "Use technical terminology freely. They're an expert."
        elif self.technical_score < 30:
            guidance["technical"] = "Avoid jargon. Explain technical concepts simply."
        else:
            guidance["technical"] = "Balance technical accuracy with accessibility."
        
        # Pace
        if self.pace_score > 70:
            guidance["pace"] = "They're in a hurry. Be direct and action-oriented."
        elif self.pace_score < 30:
            guidance["pace"] = "They're patient. Take time to explain thoroughly."
        
        # Emoji
        if self.emoji_score > 60:
            guidance["emoji"] = "Light emoji use is appropriate with this person."
        else:
            guidance["emoji"] = "Stick to text-only responses."
        
        # Humor
        if self.humor_score > 60:
            guidance["humor"] = "They're receptive to light humor."
        else:
            guidance["humor"] = "Keep it professional, skip the jokes."
        
        return guidance


class StyleAnalyzer:
    """
    Analyze communication style from messages.
    """
    
    FORMAL_SIGNALS = [
        (r"\b(dear|regards|sincerely|respectfully)\b", 20),
        (r"\b(would|could|shall|kindly)\b", 5),
        (r"\b(please|thank you)\b", 3),
        (r"[A-Z][a-z]+,?\s+[A-Z][a-z]+", 5),  # Proper capitalization
    ]
    
    CASUAL_SIGNALS = [
        (r"\b(hey|hi|yo|sup|hiya)\b", -15),
        (r"\b(gonna|wanna|gotta|kinda|sorta)\b", -10),
        (r"\b(awesome|cool|great|nice)\b", -5),
        (r"(!{2,})", -5),
        (r"\b(lol|haha|hehe|lmao)\b", -15),
    ]
    
    DETAIL_SIGNALS = [
        (r"\b(detail|comprehensive|thorough|full|complete)\b", 15),
        (r"\b(explain|elaborate|expand)\b", 10),
        (r"\b(specifically|exactly|precisely)\b", 8),
    ]
    
    BRIEF_SIGNALS = [
        (r"\b(brief|quick|short|summary|tldr)\b", -15),
        (r"\b(bottom line|in short|basically)\b", -10),
    ]
    
    TECHNICAL_SIGNALS = [
        (r"\b(spec|specification|tolerance|dimension)\b", 15),
        (r"\b(kW|mm|kg|rpm|psi|bar)\b", 10),
        (r"\b(servo|pneumatic|hydraulic|plc)\b", 10),
        (r"\b(api|sdk|config|parameter)\b", 10),
    ]
    
    URGENT_SIGNALS = [
        (r"\b(asap|urgent|immediately|rush|priority)\b", 20),
        (r"\b(need (it |this )?(now|today|soon))\b", 15),
        (r"\b(deadline|time.?sensitive)\b", 10),
    ]
    
    def analyze_message(self, message: str) -> Dict[str, float]:
        """
        Analyze a single message for style signals.
        Returns dict of style dimensions and scores.
        """
        message_lower = message.lower()
        scores = {
            "formality_delta": 0,
            "detail_delta": 0,
            "technical_delta": 0,
            "pace_delta": 0,
            "message_length": len(message),
        }
        
        # Formality
        for pattern, score in self.FORMAL_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["formality_delta"] += score
        for pattern, score in self.CASUAL_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["formality_delta"] += score
        
        # Detail preference
        for pattern, score in self.DETAIL_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["detail_delta"] += score
        for pattern, score in self.BRIEF_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["detail_delta"] += score
        
        # Technical level
        for pattern, score in self.TECHNICAL_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["technical_delta"] += score
        
        # Pace/urgency
        for pattern, score in self.URGENT_SIGNALS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["pace_delta"] += score
        
        # Emoji usage
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        emoji_count = len(re.findall(emoji_pattern, message))
        scores["emoji_count"] = emoji_count
        
        # Humor signals
        humor_patterns = [r"\b(haha|lol|😂|🤣|joke|kidding)\b", r";[-]?\)"]
        humor_count = sum(1 for p in humor_patterns if re.search(p, message))
        scores["humor_count"] = humor_count
        
        return scores


class AdaptiveStyleEngine:
    """
    Track and adapt to individual communication styles.
    """
    
    def __init__(self):
        self.profiles: Dict[str, StyleProfile] = {}
        self.analyzer = StyleAnalyzer()
    
    def get_or_create_profile(self, contact_id: str) -> StyleProfile:
        """Get or create style profile for a contact."""
        if contact_id not in self.profiles:
            self.profiles[contact_id] = StyleProfile(contact_id=contact_id)
        return self.profiles[contact_id]
    
    def analyze_and_update(
        self,
        contact_id: str,
        message: str,
        was_positive_response: bool = True
    ) -> StyleProfile:
        """
        Analyze a message and update the profile.
        
        Args:
            contact_id: Contact identifier
            message: User's message
            was_positive_response: Did user respond positively to previous style?
        """
        profile = self.get_or_create_profile(contact_id)
        analysis = self.analyzer.analyze_message(message)
        
        # Learning rate decreases as we get more confident
        learning_rate = 0.2 / (1 + profile.messages_analyzed * 0.1)
        
        # Update formality
        if analysis["formality_delta"] != 0:
            delta = analysis["formality_delta"] * learning_rate
            profile.formality_score = max(0, min(100, profile.formality_score + delta))
            profile.formality_confidence = min(1.0, profile.formality_confidence + 0.05)
        
        # Update detail preference
        if analysis["detail_delta"] != 0:
            delta = analysis["detail_delta"] * learning_rate
            profile.detail_score = max(0, min(100, profile.detail_score + delta))
            profile.detail_confidence = min(1.0, profile.detail_confidence + 0.05)
        
        # Update technical level
        if analysis["technical_delta"] != 0:
            delta = analysis["technical_delta"] * learning_rate
            profile.technical_score = max(0, min(100, profile.technical_score + delta))
            profile.technical_confidence = min(1.0, profile.technical_confidence + 0.05)
        
        # Update pace
        if analysis["pace_delta"] != 0:
            delta = analysis["pace_delta"] * learning_rate
            profile.pace_score = max(0, min(100, profile.pace_score + delta))
            profile.pace_confidence = min(1.0, profile.pace_confidence + 0.05)
        
        # Update emoji preference
        if analysis.get("emoji_count", 0) > 0:
            profile.emoji_score = min(100, profile.emoji_score + 10 * learning_rate)
            profile.emoji_confidence = min(1.0, profile.emoji_confidence + 0.05)
        
        # Update humor receptiveness
        if analysis.get("humor_count", 0) > 0:
            profile.humor_score = min(100, profile.humor_score + 15 * learning_rate)
            profile.humor_confidence = min(1.0, profile.humor_confidence + 0.05)
        
        # Update message length tracking
        profile.avg_message_length = (
            profile.avg_message_length * 0.8 + 
            analysis["message_length"] * 0.2
        )
        
        profile.messages_analyzed += 1
        profile.last_updated = datetime.now()
        
        return profile
    
    def get_response_style_prompt(self, contact_id: str) -> str:
        """
        Get prompt addition for response style.
        """
        profile = self.profiles.get(contact_id)
        if not profile or profile.messages_analyzed < 3:
            return ""  # Not enough data yet
        
        guidance = profile.get_response_guidance()
        
        lines = ["\nADAPTIVE STYLE (learned from this user):"]
        for key, value in guidance.items():
            lines.append(f"- {key.upper()}: {value}")
        
        # Response length guidance
        if profile.avg_message_length < 50:
            lines.append("- LENGTH: User sends short messages, keep responses concise.")
        elif profile.avg_message_length > 200:
            lines.append("- LENGTH: User writes detailed messages, match their depth.")
        
        return "\n".join(lines)
