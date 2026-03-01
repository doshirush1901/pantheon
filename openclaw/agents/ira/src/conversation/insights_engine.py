"""
Proactive Insights Engine
=========================

Replika insight: The best assistants notice patterns and surface insights.

"I've noticed you always ask about PF1 machines on Mondays - 
do you have a recurring meeting about that?"

This module:
1. Tracks patterns in user behavior and queries
2. Generates insights from observed patterns
3. Surfaces insights at appropriate moments
4. Learns what insights are valuable
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class Pattern:
    """An observed pattern in user behavior."""
    pattern_id: str
    pattern_type: str  # topic_frequency, time_based, sentiment_trend, etc.
    description: str
    confidence: float = 0.5
    occurrences: int = 0
    first_observed: datetime = field(default_factory=datetime.now)
    last_observed: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
        }


@dataclass
class Insight:
    """An insight derived from observed patterns."""
    insight_id: str
    insight_type: str  # behavioral, preference, need, prediction
    title: str
    description: str
    confidence: float = 0.5
    actionable: bool = False
    action_suggestion: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    shared: bool = False
    was_useful: Optional[bool] = None
    source_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "actionable": self.actionable,
            "action_suggestion": self.action_suggestion,
        }


class PatternTracker:
    """
    Track behavioral patterns over time.
    """
    
    def __init__(self):
        self.topic_history: Dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
        self.time_patterns: Dict[str, Dict] = defaultdict(dict)
        self.query_types: Dict[str, List[str]] = defaultdict(list)
    
    def record_interaction(
        self,
        contact_id: str,
        message: str,
        topics: List[str],
        timestamp: datetime = None
    ) -> List[Pattern]:
        """
        Record an interaction and detect patterns.
        
        Returns newly detected or strengthened patterns.
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        patterns_detected = []
        message_lower = message.lower()
        
        # Track topics
        for topic in topics:
            self.topic_history[contact_id].append((timestamp, topic))
        
        # Track time patterns
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        time_key = f"{contact_id}_time"
        if time_key not in self.time_patterns:
            self.time_patterns[time_key] = {
                "hours": defaultdict(int),
                "days": defaultdict(int),
            }
        
        self.time_patterns[time_key]["hours"][hour] += 1
        self.time_patterns[time_key]["days"][day_of_week] += 1
        
        # Track query types
        query_type = self._classify_query(message_lower)
        self.query_types[contact_id].append(query_type)
        
        # Detect patterns
        patterns_detected.extend(self._detect_topic_patterns(contact_id))
        patterns_detected.extend(self._detect_time_patterns(contact_id))
        patterns_detected.extend(self._detect_query_patterns(contact_id))
        
        return patterns_detected
    
    def _classify_query(self, message: str) -> str:
        """Classify the type of query."""
        if re.search(r"\b(price|cost|quote|how much)\b", message):
            return "pricing"
        elif re.search(r"\b(spec|dimension|size|capacity)\b", message):
            return "specification"
        elif re.search(r"\b(delivery|ship|lead time|when)\b", message):
            return "logistics"
        elif re.search(r"\b(problem|issue|error|broken|fix)\b", message):
            return "support"
        elif re.search(r"\b(compare|vs|versus|difference|between)\b", message):
            return "comparison"
        else:
            return "general"
    
    def _detect_topic_patterns(self, contact_id: str) -> List[Pattern]:
        """Detect patterns in topic frequency."""
        patterns = []
        history = self.topic_history.get(contact_id, [])
        
        if len(history) < 5:
            return patterns
        
        # Count topic frequency
        topic_counts = defaultdict(int)
        for _, topic in history[-20:]:  # Last 20 interactions
            topic_counts[topic] += 1
        
        # Detect dominant topics
        for topic, count in topic_counts.items():
            if count >= 3:
                import uuid
                patterns.append(Pattern(
                    pattern_id=str(uuid.uuid4())[:8],
                    pattern_type="topic_frequency",
                    description=f"Frequently asks about {topic}",
                    confidence=min(0.9, count * 0.15),
                    occurrences=count,
                    metadata={"topic": topic}
                ))
        
        return patterns
    
    def _detect_time_patterns(self, contact_id: str) -> List[Pattern]:
        """Detect patterns in interaction timing."""
        patterns = []
        time_key = f"{contact_id}_time"
        
        if time_key not in self.time_patterns:
            return patterns
        
        time_data = self.time_patterns[time_key]
        
        # Detect preferred hours
        hours = time_data.get("hours", {})
        if hours:
            peak_hour = max(hours.keys(), key=lambda h: hours[h])
            if hours[peak_hour] >= 3:
                import uuid
                patterns.append(Pattern(
                    pattern_id=str(uuid.uuid4())[:8],
                    pattern_type="time_preference",
                    description=f"Most active around {peak_hour}:00",
                    confidence=min(0.8, hours[peak_hour] * 0.1),
                    occurrences=hours[peak_hour],
                    metadata={"peak_hour": peak_hour}
                ))
        
        # Detect preferred days
        days = time_data.get("days", {})
        if days:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            peak_day = max(days.keys(), key=lambda d: days[d])
            if days[peak_day] >= 3:
                import uuid
                patterns.append(Pattern(
                    pattern_id=str(uuid.uuid4())[:8],
                    pattern_type="day_preference",
                    description=f"Most active on {day_names[peak_day]}s",
                    confidence=min(0.8, days[peak_day] * 0.1),
                    occurrences=days[peak_day],
                    metadata={"peak_day": peak_day, "day_name": day_names[peak_day]}
                ))
        
        return patterns
    
    def _detect_query_patterns(self, contact_id: str) -> List[Pattern]:
        """Detect patterns in query types."""
        patterns = []
        queries = self.query_types.get(contact_id, [])
        
        if len(queries) < 5:
            return patterns
        
        # Count query types
        type_counts = defaultdict(int)
        for qtype in queries[-20:]:
            type_counts[qtype] += 1
        
        # Detect dominant query types
        for qtype, count in type_counts.items():
            if count >= 3 and qtype != "general":
                import uuid
                patterns.append(Pattern(
                    pattern_id=str(uuid.uuid4())[:8],
                    pattern_type="query_focus",
                    description=f"Frequently asks {qtype} questions",
                    confidence=min(0.85, count * 0.12),
                    occurrences=count,
                    metadata={"query_type": qtype}
                ))
        
        return patterns


class InsightsEngine:
    """
    Generate and manage insights from observed patterns.
    
    Now with optional SQLite persistence for insights.
    """

    def __init__(self, store=None):
        self.pattern_tracker = PatternTracker()
        self.patterns: Dict[str, List[Pattern]] = defaultdict(list)
        self.insights: Dict[str, List[Insight]] = defaultdict(list)
        self.insights_shared: Dict[str, datetime] = {}  # insight_id -> when shared
        self.sharing_cooldown = timedelta(days=14)
        self.store = store  # Optional RelationshipStore for persistence
    
    def record_interaction(
        self,
        contact_id: str,
        message: str,
        topics: List[str],
        timestamp: datetime = None
    ) -> None:
        """Record an interaction and update patterns."""
        new_patterns = self.pattern_tracker.record_interaction(
            contact_id, message, topics, timestamp
        )
        
        # Merge with existing patterns
        existing_ids = {p.pattern_id for p in self.patterns[contact_id]}
        for pattern in new_patterns:
            if pattern.pattern_id not in existing_ids:
                self.patterns[contact_id].append(pattern)
        
        # Try to generate new insights
        self._generate_insights(contact_id)
    
    def _generate_insights(self, contact_id: str) -> None:
        """Generate insights from patterns."""
        import uuid
        patterns = self.patterns.get(contact_id, [])
        
        if len(patterns) < 2:
            return
        
        existing_titles = {i.title for i in self.insights[contact_id]}
        
        # Insight: Topic expert
        topic_patterns = [p for p in patterns if p.pattern_type == "topic_frequency"]
        for tp in topic_patterns:
            if tp.confidence > 0.6:
                topic = tp.metadata.get("topic", "this area")
                title = f"Expert interest in {topic}"
                if title not in existing_titles:
                    insight = Insight(
                        insight_id=str(uuid.uuid4())[:8],
                        insight_type="preference",
                        title=title,
                        description=f"This contact frequently asks about {topic}. "
                                  f"They may be researching or have a recurring need in this area.",
                        confidence=tp.confidence,
                        actionable=True,
                        action_suggestion=f"Proactively share updates about {topic}.",
                        source_patterns=[tp.pattern_id]
                    )
                    self.insights[contact_id].append(insight)
                    self._persist_insight(contact_id, insight)
        
        # Insight: Time-based availability
        time_patterns = [p for p in patterns if p.pattern_type in ["time_preference", "day_preference"]]
        for tp in time_patterns:
            if tp.confidence > 0.5:
                desc = tp.description
                title = f"Availability pattern: {desc}"
                if title not in existing_titles:
                    insight = Insight(
                        insight_id=str(uuid.uuid4())[:8],
                        insight_type="behavioral",
                        title=title,
                        description=f"This contact is {desc.lower()}. "
                                  f"Consider timing your outreach accordingly.",
                        confidence=tp.confidence,
                        actionable=True,
                        action_suggestion=f"Schedule follow-ups around their active times.",
                        source_patterns=[tp.pattern_id]
                    )
                    self.insights[contact_id].append(insight)
                    self._persist_insight(contact_id, insight)
        
        # Insight: Query focus
        query_patterns = [p for p in patterns if p.pattern_type == "query_focus"]
        for qp in query_patterns:
            if qp.confidence > 0.6:
                qtype = qp.metadata.get("query_type", "")
                type_meanings = {
                    "pricing": "may be in active buying/budgeting phase",
                    "specification": "doing technical evaluation",
                    "logistics": "likely planning a purchase or project",
                    "support": "may have ongoing issues that need addressing",
                    "comparison": "evaluating options, competitive situation",
                }
                meaning = type_meanings.get(qtype, "has a recurring need")
                title = f"Focus on {qtype} suggests they {meaning}"
                if title not in existing_titles:
                    insight = Insight(
                        insight_id=str(uuid.uuid4())[:8],
                        insight_type="need",
                        title=title,
                        description=f"Based on their query patterns, this contact {meaning}.",
                        confidence=qp.confidence,
                        actionable=True,
                        action_suggestion=self._get_action_for_query_type(qtype),
                        source_patterns=[qp.pattern_id]
                    )
                    self.insights[contact_id].append(insight)
                    self._persist_insight(contact_id, insight)
    
    def _get_action_for_query_type(self, query_type: str) -> str:
        """Get actionable suggestion for query type."""
        actions = {
            "pricing": "Share any promotions or financing options.",
            "specification": "Offer a detailed comparison or spec sheet.",
            "logistics": "Proactively share lead times and delivery options.",
            "support": "Check if there are unresolved issues. Offer dedicated support.",
            "comparison": "Highlight unique value propositions.",
        }
        return actions.get(query_type, "Follow up with relevant information.")
    
    def _persist_insight(self, contact_id: str, insight: Insight) -> None:
        """Persist an insight to SQLite if store is available."""
        if not self.store:
            return
        try:
            self.store.add_insight(
                contact_id=contact_id,
                insight_id=insight.insight_id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                confidence=insight.confidence,
                actionable=insight.actionable,
                action_suggestion=insight.action_suggestion,
            )
        except Exception as e:
            print(f"[insights_engine] Failed to persist insight: {e}")
    
    def get_insights(
        self,
        contact_id: str,
        min_confidence: float = 0.5,
        actionable_only: bool = False,
        unshared_only: bool = True
    ) -> List[Insight]:
        """
        Get insights for a contact.
        """
        insights = self.insights.get(contact_id, [])
        
        filtered = []
        for insight in insights:
            if insight.confidence < min_confidence:
                continue
            if actionable_only and not insight.actionable:
                continue
            if unshared_only and insight.shared:
                continue
            if insight.insight_id in self.insights_shared:
                if datetime.now() - self.insights_shared[insight.insight_id] < self.sharing_cooldown:
                    continue
            
            filtered.append(insight)
        
        return sorted(filtered, key=lambda x: x.confidence, reverse=True)
    
    def mark_shared(self, insight_id: str, was_useful: bool = True) -> None:
        """Mark an insight as shared and track usefulness."""
        self.insights_shared[insight_id] = datetime.now()
        
        # Update the insight
        for contact_id, insights in self.insights.items():
            for insight in insights:
                if insight.insight_id == insight_id:
                    insight.shared = True
                    insight.was_useful = was_useful
                    return
    
    def get_insight_prompt_addition(self, contact_id: str) -> str:
        """Get prompt addition with relevant insights."""
        insights = self.get_insights(contact_id, min_confidence=0.6, actionable_only=True)
        
        if not insights:
            return ""
        
        lines = ["\nINSIGHTS ABOUT THIS CONTACT:"]
        for insight in insights[:2]:
            lines.append(f"- {insight.title}")
            if insight.action_suggestion:
                lines.append(f"  Action: {insight.action_suggestion}")
        
        return "\n".join(lines)
