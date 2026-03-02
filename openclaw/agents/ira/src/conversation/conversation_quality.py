"""
Conversation Quality Tracker
============================

Replika insight: Track conversation quality over time to understand
relationship health and improve interactions.

This module:
1. Scores each conversation turn
2. Tracks quality trends over time
3. Identifies declining relationships early
4. Suggests improvements
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import json


class QualityDimension(Enum):
    """Dimensions of conversation quality."""
    ENGAGEMENT = "engagement"           # How engaged is the user?
    SATISFACTION = "satisfaction"       # Satisfied with responses?
    RAPPORT = "rapport"                 # Building relationship?
    EFFECTIVENESS = "effectiveness"     # Getting things done?
    SENTIMENT = "sentiment"             # Positive vs negative tone?


@dataclass
class TurnQuality:
    """Quality score for a single conversation turn."""
    turn_id: str
    timestamp: datetime
    scores: Dict[str, float] = field(default_factory=dict)  # dimension -> 0-100
    overall_score: float = 50.0
    signals: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp.isoformat(),
            "scores": self.scores,
            "overall_score": self.overall_score,
            "signals": self.signals,
        }


@dataclass
class ConversationHealth:
    """Overall health of a conversation/relationship."""
    contact_id: str
    health_score: float = 50.0  # 0-100
    trend: str = "stable"  # improving, stable, declining
    risk_level: str = "low"  # low, medium, high
    last_updated: datetime = field(default_factory=datetime.now)
    turn_history: List[TurnQuality] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "contact_id": self.contact_id,
            "health_score": self.health_score,
            "trend": self.trend,
            "risk_level": self.risk_level,
            "last_updated": self.last_updated.isoformat(),
            "insights": self.insights,
        }


class QualitySignals:
    """Signals that indicate conversation quality."""
    
    POSITIVE_ENGAGEMENT = [
        r"\b(thanks|thank you|great|perfect|exactly|helpful)\b",
        r"\b(yes|yep|correct|right|agreed)\b",
        r"\b(tell me more|can you explain|interested)\b",
        r"!+$",  # Exclamation marks
        r"\?{1,2}$",  # Questions (engaged)
    ]
    
    NEGATIVE_ENGAGEMENT = [
        r"\b(no|nope|wrong|incorrect)\b",
        r"\b(confused|don't understand|unclear)\b",
        r"\b(already (told|said|asked)|again)\b",
        r"\b(frustrated|annoyed|disappointed)\b",
        r"\b(never mind|forget it|whatever)\b",
    ]
    
    RAPPORT_BUILDING = [
        r"\b(appreciate|grateful|you're (great|helpful|awesome))\b",
        r"\b(looking forward|excited|can't wait)\b",
        r"\b(we|our|together|partnership)\b",
        r"(😊|👍|🙏|❤️|✅)",
    ]
    
    RAPPORT_DECLINING = [
        r"\b(disappointed|expected (more|better))\b",
        r"\b(last time|before you said)\b",
        r"\b(competitor|alternative|other option)\b",
        r"\b(escalate|manager|supervisor)\b",
    ]
    
    SATISFACTION = [
        r"\b(perfect|exactly what|just what)\b",
        r"\b(solved|resolved|fixed|working)\b",
        r"\b(recommend|will use again)\b",
    ]
    
    DISSATISFACTION = [
        r"\b(still (not|waiting|broken))\b",
        r"\b(doesn't (work|help|answer))\b",
        r"\b(useless|waste of time)\b",
    ]


class ConversationQualityTracker:
    """
    Track and analyze conversation quality over time.
    
    Key insight from Replika: Relationships have health that can be measured
    and improved. Don't wait for explicit complaints - detect issues early.
    """
    
    def __init__(self):
        self.signals = QualitySignals()
        self.health_records: Dict[str, ConversationHealth] = {}
    
    def score_turn(
        self,
        contact_id: str,
        user_message: str,
        assistant_response: str,
        response_time_ms: int = 0,
        had_citations: bool = False
    ) -> TurnQuality:
        """
        Score a single conversation turn.
        """
        import re
        import uuid
        
        scores = {}
        signals_detected = []
        message_lower = user_message.lower()
        
        # Engagement score
        engagement = 50
        for pattern in self.signals.POSITIVE_ENGAGEMENT:
            if re.search(pattern, message_lower, re.IGNORECASE):
                engagement += 10
                signals_detected.append(f"+engagement: {pattern}")
        for pattern in self.signals.NEGATIVE_ENGAGEMENT:
            if re.search(pattern, message_lower, re.IGNORECASE):
                engagement -= 15
                signals_detected.append(f"-engagement: {pattern}")
        scores["engagement"] = max(0, min(100, engagement))
        
        # Rapport score
        rapport = 50
        for pattern in self.signals.RAPPORT_BUILDING:
            if re.search(pattern, message_lower, re.IGNORECASE):
                rapport += 15
                signals_detected.append(f"+rapport: {pattern}")
        for pattern in self.signals.RAPPORT_DECLINING:
            if re.search(pattern, message_lower, re.IGNORECASE):
                rapport -= 20
                signals_detected.append(f"-rapport: {pattern}")
        scores["rapport"] = max(0, min(100, rapport))
        
        # Satisfaction score
        satisfaction = 50
        for pattern in self.signals.SATISFACTION:
            if re.search(pattern, message_lower, re.IGNORECASE):
                satisfaction += 20
                signals_detected.append(f"+satisfaction: {pattern}")
        for pattern in self.signals.DISSATISFACTION:
            if re.search(pattern, message_lower, re.IGNORECASE):
                satisfaction -= 25
                signals_detected.append(f"-satisfaction: {pattern}")
        scores["satisfaction"] = max(0, min(100, satisfaction))
        
        # Effectiveness (based on response quality)
        effectiveness = 50
        if had_citations:
            effectiveness += 15
        if len(assistant_response) > 100:
            effectiveness += 10
        if response_time_ms > 0 and response_time_ms < 3000:
            effectiveness += 10
        scores["effectiveness"] = min(100, effectiveness)
        
        # Overall score (weighted average)
        weights = {"engagement": 0.3, "rapport": 0.25, "satisfaction": 0.25, "effectiveness": 0.2}
        overall = sum(scores.get(dim, 50) * weight for dim, weight in weights.items())
        
        turn = TurnQuality(
            turn_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            scores=scores,
            overall_score=overall,
            signals=signals_detected
        )
        
        # Update health record
        self._update_health(contact_id, turn)
        
        return turn
    
    def _update_health(self, contact_id: str, turn: TurnQuality) -> None:
        """Update conversation health based on new turn."""
        if contact_id not in self.health_records:
            self.health_records[contact_id] = ConversationHealth(contact_id=contact_id)
        
        health = self.health_records[contact_id]
        health.turn_history.append(turn)
        
        # Keep last 20 turns
        if len(health.turn_history) > 20:
            health.turn_history = health.turn_history[-20:]
        
        # Calculate rolling health score
        recent_scores = [t.overall_score for t in health.turn_history[-10:]]
        health.health_score = sum(recent_scores) / len(recent_scores)
        
        # Determine trend
        if len(health.turn_history) >= 5:
            first_half = health.turn_history[:len(health.turn_history)//2]
            second_half = health.turn_history[len(health.turn_history)//2:]
            
            first_avg = sum(t.overall_score for t in first_half) / len(first_half)
            second_avg = sum(t.overall_score for t in second_half) / len(second_half)
            
            if second_avg > first_avg + 5:
                health.trend = "improving"
            elif second_avg < first_avg - 5:
                health.trend = "declining"
            else:
                health.trend = "stable"
        
        # Determine risk level
        if health.health_score < 30 or health.trend == "declining":
            health.risk_level = "high"
        elif health.health_score < 50:
            health.risk_level = "medium"
        else:
            health.risk_level = "low"
        
        # Generate insights
        health.insights = self._generate_insights(health)
        health.last_updated = datetime.now()
    
    def _generate_insights(self, health: ConversationHealth) -> List[str]:
        """Generate actionable insights from health data."""
        insights = []
        
        if health.trend == "declining":
            insights.append("Relationship quality is declining. Consider more personalized follow-up.")
        
        if health.health_score < 40:
            insights.append("Low satisfaction detected. May need to address underlying concerns.")
        
        # Check for specific patterns
        recent_signals = []
        for turn in health.turn_history[-5:]:
            recent_signals.extend(turn.signals)
        
        if any("-rapport" in s for s in recent_signals):
            insights.append("Rapport signals declining. Be warmer and more personal.")
        
        if any("-satisfaction" in s for s in recent_signals):
            insights.append("User seems dissatisfied. Ask for feedback directly.")
        
        return insights[:3]
    
    def get_health(self, contact_id: str) -> Optional[ConversationHealth]:
        """Get health record for a contact."""
        return self.health_records.get(contact_id)
    
    def get_at_risk_contacts(self, threshold: float = 40.0) -> List[ConversationHealth]:
        """Get contacts with low health scores."""
        at_risk = [
            h for h in self.health_records.values()
            if h.health_score < threshold or h.trend == "declining"
        ]
        return sorted(at_risk, key=lambda h: h.health_score)
    
    def get_improvement_suggestions(self, contact_id: str) -> List[str]:
        """Get suggestions for improving a specific relationship."""
        health = self.health_records.get(contact_id)
        if not health:
            return ["Build rapport with personalized interactions."]
        
        suggestions = []
        
        # Check weakest dimensions
        if health.turn_history:
            recent = health.turn_history[-5:]
            avg_scores = {}
            for dim in ["engagement", "rapport", "satisfaction", "effectiveness"]:
                scores = [t.scores.get(dim, 50) for t in recent]
                avg_scores[dim] = sum(scores) / len(scores)
            
            weakest = min(avg_scores.items(), key=lambda x: x[1])
            
            dimension_suggestions = {
                "engagement": "Ask more follow-up questions to increase engagement.",
                "rapport": "Reference personal details and past conversations.",
                "satisfaction": "Ask directly if there's anything you can improve.",
                "effectiveness": "Provide more detailed, cited responses.",
            }
            suggestions.append(dimension_suggestions.get(weakest[0], ""))
        
        suggestions.extend(health.insights)
        return [s for s in suggestions if s][:5]
