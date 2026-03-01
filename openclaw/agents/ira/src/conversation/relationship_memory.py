"""
Relationship Memory Layer - Tracks emotional/relational context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class RelationshipWarmth(Enum):
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FAMILIAR = "familiar"
    WARM = "warm"
    TRUSTED = "trusted"


class MomentType(Enum):
    PERSONAL_SHARE = "personal_share"
    CELEBRATION = "celebration"
    DIFFICULTY = "difficulty"
    PREFERENCE = "preference"
    GRATITUDE = "gratitude"
    FRUSTRATION = "frustration"


@dataclass
class MemorableMoment:
    moment_type: MomentType
    content: str
    timestamp: datetime
    context: str = ""
    follow_up_done: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "moment_type": self.moment_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "follow_up_done": self.follow_up_done,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemorableMoment":
        return cls(
            moment_type=MomentType(data["moment_type"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            context=data.get("context", ""),
            follow_up_done=data.get("follow_up_done", False),
        )


@dataclass
class LearnedPreference:
    category: str
    preference: str
    confidence: float
    learned_from: str
    learned_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "preference": self.preference,
            "confidence": self.confidence,
            "learned_from": self.learned_from,
            "learned_at": self.learned_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LearnedPreference":
        return cls(
            category=data["category"],
            preference=data["preference"],
            confidence=data["confidence"],
            learned_from=data["learned_from"],
            learned_at=datetime.fromisoformat(data["learned_at"]),
        )


@dataclass
class ContactRelationship:
    contact_id: str
    name: str
    warmth: RelationshipWarmth = RelationshipWarmth.STRANGER
    warmth_score: float = 0.0
    memorable_moments: List[MemorableMoment] = field(default_factory=list)
    learned_preferences: List[LearnedPreference] = field(default_factory=list)
    interaction_count: int = 0
    positive_interactions: int = 0
    last_interaction: Optional[datetime] = None
    relationship_started: Optional[datetime] = None
    personal_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "warmth": self.warmth.value,
            "warmth_score": self.warmth_score,
            "memorable_moments": [m.to_dict() for m in self.memorable_moments],
            "learned_preferences": [p.to_dict() for p in self.learned_preferences],
            "interaction_count": self.interaction_count,
            "positive_interactions": self.positive_interactions,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "relationship_started": self.relationship_started.isoformat() if self.relationship_started else None,
            "personal_context": self.personal_context,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContactRelationship":
        rel = cls(
            contact_id=data["contact_id"],
            name=data["name"],
            warmth=RelationshipWarmth(data.get("warmth", "stranger")),
            warmth_score=data.get("warmth_score", 0.0),
            interaction_count=data.get("interaction_count", 0),
            positive_interactions=data.get("positive_interactions", 0),
            personal_context=data.get("personal_context", {}),
        )
        if data.get("last_interaction"):
            rel.last_interaction = datetime.fromisoformat(data["last_interaction"])
        if data.get("relationship_started"):
            rel.relationship_started = datetime.fromisoformat(data["relationship_started"])
        rel.memorable_moments = [MemorableMoment.from_dict(m) for m in data.get("memorable_moments", [])]
        rel.learned_preferences = [LearnedPreference.from_dict(p) for p in data.get("learned_preferences", [])]
        return rel
    
    def get_preference(self, category: str) -> Optional[str]:
        matching = [p for p in self.learned_preferences if p.category == category]
        if not matching:
            return None
        return max(matching, key=lambda p: p.confidence).preference
    
    def get_recent_moments(self, days: int = 30) -> List[MemorableMoment]:
        cutoff = datetime.now() - timedelta(days=days)
        return [m for m in self.memorable_moments if m.timestamp > cutoff]
    
    def needs_followup(self) -> List[MemorableMoment]:
        return [m for m in self.memorable_moments 
                if not m.follow_up_done and m.moment_type in [MomentType.DIFFICULTY, MomentType.CELEBRATION]]


class RelationshipMemory:
    PERSONAL_SIGNALS = {
        "personal_share": ["my daughter", "my son", "my wife", "my family", "vacation", "birthday"],
        "celebration": ["excited", "great news", "thrilled", "celebrating", "successful"],
        "difficulty": ["struggling", "stressed", "worried", "delayed", "problem"],
        "gratitude": ["thank you", "thanks", "appreciate", "grateful", "helpful"],
    }
    
    PREFERENCE_SIGNALS = {
        "formality": {"formal": ["dear sir", "kind regards"], "casual": ["hey", "cheers", "thanks!"]},
        "communication_style": {"detailed": ["please explain", "more details"], "brief": ["quick question", "briefly"]},
    }
    
    def __init__(self):
        self.relationships: Dict[str, ContactRelationship] = {}
    
    def get_or_create(self, contact_id: str, name: str = "") -> ContactRelationship:
        if contact_id not in self.relationships:
            self.relationships[contact_id] = ContactRelationship(
                contact_id=contact_id,
                name=name or contact_id.split("@")[0],
                relationship_started=datetime.now(),
            )
        return self.relationships[contact_id]
    
    def process_interaction(self, contact_id: str, message: str, response: str, name: str = "", is_positive: bool = True) -> Dict:
        rel = self.get_or_create(contact_id, name)
        rel.interaction_count += 1
        rel.last_interaction = datetime.now()
        if is_positive:
            rel.positive_interactions += 1
        
        detected = {"moments": [], "preferences": [], "warmth_change": 0}
        message_lower = message.lower()
        
        for moment_type, signals in self.PERSONAL_SIGNALS.items():
            for signal in signals:
                if signal in message_lower:
                    moment = MemorableMoment(
                        moment_type=MomentType(moment_type),
                        content=message[:200],
                        timestamp=datetime.now(),
                        context=signal,
                    )
                    rel.memorable_moments.append(moment)
                    detected["moments"].append(moment.to_dict())
                    detected["warmth_change"] += 3 if moment_type == "gratitude" else 2
                    break
        
        rel.warmth_score = min(100, rel.warmth_score + detected["warmth_change"])
        rel.warmth = self._score_to_warmth(rel.warmth_score)
        return detected
    
    def _score_to_warmth(self, score: float) -> RelationshipWarmth:
        if score >= 80: return RelationshipWarmth.TRUSTED
        elif score >= 60: return RelationshipWarmth.WARM
        elif score >= 40: return RelationshipWarmth.FAMILIAR
        elif score >= 20: return RelationshipWarmth.ACQUAINTANCE
        return RelationshipWarmth.STRANGER
    
    def get_relationship_context(self, contact_id: str) -> Dict:
        if contact_id not in self.relationships:
            return {"warmth": "stranger", "formality": "professional", "moments_to_reference": [], "pending_followups": [], "preferences": {}}
        rel = self.relationships[contact_id]
        return {
            "warmth": rel.warmth.value,
            "warmth_score": rel.warmth_score,
            "interaction_count": rel.interaction_count,
            "relationship_duration_days": (datetime.now() - rel.relationship_started).days if rel.relationship_started else 0,
            "moments_to_reference": [m.to_dict() for m in rel.get_recent_moments()[-3:]],
            "pending_followups": [m.to_dict() for m in rel.needs_followup()],
            "preferences": {},
        }
    
    def get_proactive_care_suggestions(self, contact_id: str) -> List[Dict]:
        if contact_id not in self.relationships:
            return []
        rel = self.relationships[contact_id]
        suggestions = []
        for moment in rel.needs_followup():
            suggestions.append({
                "type": "care_followup" if moment.moment_type == MomentType.DIFFICULTY else "celebration_followup",
                "message": moment.content[:100],
                "priority": 1 if moment.moment_type == MomentType.DIFFICULTY else 2,
            })
        return suggestions
    
    def to_dict(self) -> Dict:
        return {cid: rel.to_dict() for cid, rel in self.relationships.items()}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RelationshipMemory":
        memory = cls()
        for cid, rel_data in data.items():
            memory.relationships[cid] = ContactRelationship.from_dict(rel_data)
        return memory


def apply_relationship_to_prompt(base_prompt: str, relationship_context: Dict) -> str:
    additions = []
    warmth = relationship_context.get("warmth", "stranger")
    if warmth in ["trusted", "warm"]:
        additions.append(f"RELATIONSHIP: {warmth.upper()} relationship - be personable.")
    moments = relationship_context.get("moments_to_reference", [])
    if moments:
        additions.append(f"PERSONAL CONTEXT: {moments[-1].get('content', '')[:80]}")
    return base_prompt + ("\n\n" + "\n".join(additions) if additions else "")
