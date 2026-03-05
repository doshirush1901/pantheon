"""
Proactive Conversation Engine - Proactive follow-ups and care actions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum

if TYPE_CHECKING:
    from .relationship_memory import RelationshipMemory


class ActionType(Enum):
    QUESTION = "question"
    SUGGESTION = "suggestion"
    FOLLOW_UP = "follow_up"
    INFO = "info"
    NEXT_STEP = "next_step"
    CARE = "care"


@dataclass
class ProactiveAction:
    action_type: ActionType
    content: str
    priority: int
    context: Dict = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type.value,
            "content": self.content,
            "priority": self.priority,
            "context": self.context,
        }


class ProactiveEngine:
    SLOT_QUESTIONS = {
        "application": "What products will you be thermoforming with this?",
        "volume": "What production volume are you targeting?",
        "timeline": "When are you looking to have this operational?",
    }
    
    VALUE_ADDS = {
        "price_mentioned": "By the way, we also offer financing options if that would be helpful.",
        "quote_requested": "Would you like me to include optional accessories in the quote?",
    }
    
    def __init__(self):
        self.pending_actions: List[ProactiveAction] = []
        self.actions_taken: List[str] = []
    
    def analyze_turn(self, message: str, response: str, context: Dict, goal_status: Dict) -> List[ProactiveAction]:
        actions = []
        completion = goal_status.get("completion", 100)
        remaining_slots = goal_status.get("remaining_slots", [])
        
        if completion < 80 and remaining_slots:
            slot = remaining_slots[0]
            question = self.SLOT_QUESTIONS.get(slot)
            if question and question not in self.actions_taken:
                actions.append(ProactiveAction(action_type=ActionType.QUESTION, content=question, priority=2))
        
        return actions[:2]
    
    def mark_action_taken(self, action_content: str) -> None:
        self.actions_taken.append(action_content)
    
    def get_relationship_based_actions(self, contact_id: str, relationship_memory: "RelationshipMemory") -> List[ProactiveAction]:
        actions = []
        care_suggestions = relationship_memory.get_proactive_care_suggestions(contact_id)
        
        for suggestion in care_suggestions:
            if suggestion["message"] in self.actions_taken:
                continue
            actions.append(ProactiveAction(
                action_type=ActionType.CARE,
                content=f"Check in: {suggestion['message']}",
                priority=suggestion["priority"],
                context={"care_type": suggestion["type"]}
            ))
        
        return actions[:2]
    
    def reset(self) -> None:
        self.pending_actions = []
        self.actions_taken = []
