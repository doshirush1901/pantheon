"""
Memory Surfacing Engine
=======================

Replika insight: Don't just store memories - surface them at the right moment.

"I remember you mentioned your daughter's graduation last month - how did it go?"

This module:
1. Detects opportunities to surface relevant memories
2. Generates natural memory references
3. Avoids awkward or forced memory mentions
4. Tracks what's been surfaced to avoid repetition
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class MemoryReference:
    """A memory that could be referenced."""
    memory_id: str
    memory_text: str
    memory_type: str
    created_at: datetime
    relevance_score: float = 0.0
    surfacing_text: str = ""
    last_surfaced: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "memory_text": self.memory_text,
            "memory_type": self.memory_type,
            "relevance_score": self.relevance_score,
            "surfacing_text": self.surfacing_text,
        }


class MemorySurfacingEngine:
    """
    Surface memories naturally in conversation.
    
    Key principles:
    1. Only surface if genuinely relevant
    2. Don't be creepy ("I remember everything you said...")
    3. Use natural phrasing ("You mentioned..." not "I have in my database...")
    4. Don't repeat recently surfaced memories
    """
    
    SURFACING_TEMPLATES = {
        "fact": [
            "You mentioned {memory}",
            "I recall you said {memory}",
            "If I remember right, {memory}",
        ],
        "preference": [
            "I know you prefer {memory}",
            "Based on your preference for {memory}",
            "Since you mentioned liking {memory}",
        ],
        "context": [
            "Given that {memory}",
            "Considering {memory}",
            "With {memory} in mind",
        ],
        "celebration": [
            "How did {memory} go?",
            "I remember {memory} - hope it went well!",
            "Any update on {memory}?",
        ],
        "difficulty": [
            "How are things going with {memory}?",
            "Hope {memory} has gotten better",
            "Any progress on {memory}?",
        ],
    }
    
    TRIGGER_PATTERNS = {
        "greeting": [
            r"^(hi|hello|hey|good (morning|afternoon|evening))",
            r"^how are you",
        ],
        "followup_opportunity": [
            r"\b(update|news|progress|how('?s| is| are))\b",
            r"\b(remember|recall|last time)\b",
        ],
        "topic_match": [
            r"\b(machine|quote|price|order|delivery)\b",
        ],
    }
    
    def __init__(self):
        self.surfaced_recently: Dict[str, datetime] = {}  # memory_id -> when surfaced
        self.surfacing_cooldown = timedelta(days=7)  # Don't re-surface for 7 days
    
    def find_surfacing_opportunities(
        self,
        user_message: str,
        memories: List[Dict],
        relationship_warmth: str = "stranger"
    ) -> List[MemoryReference]:
        """
        Find memories that could be naturally surfaced.
        
        Args:
            user_message: Current user message
            memories: List of stored memories
            relationship_warmth: Current relationship warmth level
        
        Returns:
            List of memories that could be surfaced, with suggested phrasing
        """
        opportunities = []
        message_lower = user_message.lower()
        
        # Don't surface for strangers (would be weird)
        if relationship_warmth in ["stranger", "acquaintance"]:
            warmth_multiplier = 0.3
        elif relationship_warmth == "familiar":
            warmth_multiplier = 0.6
        else:
            warmth_multiplier = 1.0
        
        # Check if this is a good moment for memory surfacing
        is_greeting = any(re.search(p, message_lower) for p in self.TRIGGER_PATTERNS["greeting"])
        is_followup_moment = any(re.search(p, message_lower) for p in self.TRIGGER_PATTERNS["followup_opportunity"])
        
        for memory in memories:
            memory_id = str(memory.get("id", memory.get("memory_text", "")[:20]))
            memory_text = memory.get("memory_text", "")
            memory_type = memory.get("memory_type", "fact")
            created_at = memory.get("created_at")
            
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except (ValueError, TypeError):
                    created_at = datetime.now()
            elif created_at is None:
                created_at = datetime.now()
            
            # Skip recently surfaced
            if memory_id in self.surfaced_recently:
                if datetime.now() - self.surfaced_recently[memory_id] < self.surfacing_cooldown:
                    continue
            
            # Calculate relevance
            relevance = self._calculate_relevance(
                memory_text=memory_text,
                memory_type=memory_type,
                user_message=message_lower,
                is_greeting=is_greeting,
                is_followup_moment=is_followup_moment,
                created_at=created_at
            )
            
            relevance *= warmth_multiplier
            
            if relevance > 0.5:
                surfacing_text = self._generate_surfacing_text(
                    memory_text=memory_text,
                    memory_type=memory_type,
                    is_greeting=is_greeting
                )
                
                opportunities.append(MemoryReference(
                    memory_id=memory_id,
                    memory_text=memory_text,
                    memory_type=memory_type,
                    created_at=created_at,
                    relevance_score=relevance,
                    surfacing_text=surfacing_text,
                ))
        
        # Sort by relevance and return top 2
        opportunities.sort(key=lambda x: x.relevance_score, reverse=True)
        return opportunities[:2]
    
    def _calculate_relevance(
        self,
        memory_text: str,
        memory_type: str,
        user_message: str,
        is_greeting: bool,
        is_followup_moment: bool,
        created_at: datetime
    ) -> float:
        """Calculate how relevant a memory is to surface now."""
        relevance = 0.0
        memory_lower = memory_text.lower()
        
        # Direct keyword overlap
        memory_words = set(re.findall(r'\b\w+\b', memory_lower))
        message_words = set(re.findall(r'\b\w+\b', user_message))
        
        common_words = memory_words & message_words
        stop_words = {"the", "a", "is", "are", "was", "were", "i", "you", "we", "they", "it"}
        meaningful_overlap = common_words - stop_words
        
        if meaningful_overlap:
            relevance += len(meaningful_overlap) * 0.15
        
        # Greeting is a good time for follow-up memories
        if is_greeting and memory_type in ["celebration", "difficulty"]:
            days_old = (datetime.now() - created_at).days
            if 7 <= days_old <= 30:
                relevance += 0.4
        
        # Follow-up moment boosts context memories
        if is_followup_moment:
            relevance += 0.2
        
        # Recent memories are more relevant
        days_old = (datetime.now() - created_at).days
        if days_old < 7:
            relevance += 0.2
        elif days_old < 30:
            relevance += 0.1
        
        # Type-based relevance
        type_relevance = {
            "celebration": 0.3,  # Good to follow up on
            "difficulty": 0.3,   # Shows care
            "preference": 0.2,   # Useful for personalization
            "fact": 0.1,         # Generic
            "context": 0.2,      # Business-relevant
        }
        relevance += type_relevance.get(memory_type, 0.1)
        
        return min(1.0, relevance)
    
    def _generate_surfacing_text(
        self,
        memory_text: str,
        memory_type: str,
        is_greeting: bool
    ) -> str:
        """Generate natural text for surfacing a memory."""
        import random
        
        templates = self.SURFACING_TEMPLATES.get(memory_type, self.SURFACING_TEMPLATES["fact"])
        template = random.choice(templates)
        
        # Shorten memory for natural phrasing
        short_memory = memory_text
        if len(memory_text) > 50:
            short_memory = memory_text[:47] + "..."
        
        return template.format(memory=short_memory)
    
    def mark_surfaced(self, memory_id: str) -> None:
        """Mark a memory as recently surfaced."""
        self.surfaced_recently[memory_id] = datetime.now()
    
    def should_surface_any(
        self,
        warmth: str,
        message_length: int,
        is_first_message: bool
    ) -> bool:
        """
        Decide if this is a good moment to surface memories at all.
        
        Don't surface if:
        - Very short message (probably quick question)
        - First message (let them state their purpose first)
        - Stranger (would be creepy)
        """
        if is_first_message:
            return False
        
        if message_length < 20:
            return False
        
        if warmth in ["stranger"]:
            return False
        
        return True


def generate_memory_reference_prompt_addition(
    opportunities: List[MemoryReference],
    max_references: int = 1
) -> str:
    """
    Generate prompt addition for memory surfacing.
    
    Returns text to add to system prompt.
    """
    if not opportunities:
        return ""
    
    additions = ["\nMEMORY SURFACING OPPORTUNITY:"]
    additions.append("Consider naturally referencing these memories if relevant:")
    
    for opp in opportunities[:max_references]:
        additions.append(f"- {opp.surfacing_text} (relevance: {opp.relevance_score:.1f})")
    
    additions.append("Only reference if it fits naturally. Don't force it.")
    return "\n".join(additions)
