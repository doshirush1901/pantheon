#!/usr/bin/env python3
"""
MEMORY TRIGGER - Intelligent Memory Access Control

╔════════════════════════════════════════════════════════════════════╗
║  Decides WHEN to access memory (not every turn!)                   ║
║  Based on MemGen research: Memory Trigger + Memory Weaver pattern  ║
╚════════════════════════════════════════════════════════════════════╝

Key insight: Most messages don't need memory retrieval.
Retrieving memories on every turn is:
- Slow (API calls to Qdrant + OpenAI)
- Noisy (irrelevant memories pollute context)
- Expensive (embedding costs)

This module decides intelligently when memory IS needed.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class MemoryType(Enum):
    """Types of memory that can be triggered."""
    USER = "user"           # Facts about the person talking
    ENTITY = "entity"       # Facts about companies/contacts mentioned
    EPISODIC = "episodic"   # Past conversation events
    PROCEDURAL = "procedural"  # Learned behaviors (future)


@dataclass
class TriggerDecision:
    """Result of trigger evaluation."""
    should_retrieve: bool
    memory_types: Set[MemoryType]
    reason: str
    priority: str  # "high", "medium", "low"
    query_hints: List[str]  # Suggested queries for retrieval


class MemoryTrigger:
    """
    Evaluates whether memory retrieval is needed for a given message.
    
    Trigger Categories:
    1. EXPLICIT - User asks about memory ("what do you know about me?")
    2. TEMPORAL - References past ("last time", "we discussed")
    3. RELATIONSHIP - Personal/relationship building
    4. ENTITY - Mentions companies/people
    5. CONTEXT - Needs background to answer well
    6. RETURNING - First message in a while from known user
    """
    
    # Explicit memory triggers
    EXPLICIT_PATTERNS = [
        r"what do you (know|remember)",
        r"what have you learned",
        r"show.*memor(y|ies)",
        r"do you remember",
        r"you (said|mentioned|told me)",
        r"i told you",
        r"we (discussed|talked about)",
        r"my preference",
        r"as i (said|mentioned)",
        r"know about me",
        r"remember about me",
    ]
    
    # Temporal triggers (need episodic memory)
    TEMPORAL_PATTERNS = [
        r"last time",
        r"yesterday",
        r"last (week|month|year)",
        r"before",
        r"earlier",
        r"previously",
        r"when we (last |first )?",
        r"the other day",
        r"remember when",
    ]
    
    # Relationship triggers (need user memory)
    RELATIONSHIP_PATTERNS = [
        r"(how are|how've) you",
        r"tell me about yourself",
        r"who am i",
        r"what('s| is) my",
        r"my (company|role|job|position|work)",
        r"i('m| am) (from|at|with)",
        r"my name is",
        r"call me",
    ]
    
    # Context triggers (background helps)
    CONTEXT_KEYWORDS = [
        "follow up", "following up", "as discussed",
        "regarding our", "about our", "continuing",
        "update on", "status of", "progress on",
        "my order", "my quote", "my inquiry",
    ]
    
    # Skip patterns (definitely don't need memory)
    SKIP_PATTERNS = [
        r"^(hi|hello|hey)[\s!.]*$",  # Just greetings
        r"^(yes|no|ok|okay|sure|thanks|thank you)[\s!.]*$",  # Simple responses
        r"^/",  # Commands
        r"^\d+$",  # Just numbers
        r"^(what|how|where|when|why|who) (is|are|do|does|can|will)",  # Generic questions
    ]
    
    def __init__(self):
        self._compile_patterns()
        self._message_count: Dict[str, int] = {}  # Track messages per user
        self._last_retrieval: Dict[str, datetime] = {}  # Track last retrieval time
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self._explicit_re = [re.compile(p, re.IGNORECASE) for p in self.EXPLICIT_PATTERNS]
        self._temporal_re = [re.compile(p, re.IGNORECASE) for p in self.TEMPORAL_PATTERNS]
        self._relationship_re = [re.compile(p, re.IGNORECASE) for p in self.RELATIONSHIP_PATTERNS]
        self._skip_re = [re.compile(p, re.IGNORECASE) for p in self.SKIP_PATTERNS]
    
    def evaluate(
        self,
        message: str,
        user_id: str,
        context: Optional[Dict] = None
    ) -> TriggerDecision:
        """
        Evaluate whether memory retrieval is needed.
        
        Args:
            message: The user's message
            user_id: Unique identifier for the user
            context: Optional context dict with:
                - is_returning_user: bool
                - message_count: int
                - has_identity: bool
                - entities_mentioned: List[str]
        
        Returns:
            TriggerDecision with recommendation
        """
        context = context or {}
        message_lower = message.lower().strip()
        
        # Track message count
        self._message_count[user_id] = self._message_count.get(user_id, 0) + 1
        msg_count = self._message_count[user_id]
        
        memory_types: Set[MemoryType] = set()
        reasons: List[str] = []
        priority = "low"
        query_hints: List[str] = []
        
        # Check explicit memory requests FIRST (highest priority - overrides skips)
        for pattern in self._explicit_re:
            if pattern.search(message_lower):
                memory_types.add(MemoryType.USER)
                reasons.append("Explicit memory request")
                priority = "high"
                query_hints.append(message)
                break
        
        # Check skip patterns (fast path) - only if no explicit trigger matched
        if not memory_types:
            for pattern in self._skip_re:
                if pattern.match(message_lower):
                    return TriggerDecision(
                        should_retrieve=False,
                        memory_types=set(),
                        reason="Simple message, no memory needed",
                        priority="low",
                        query_hints=[]
                    )
        
        # Check temporal references (need episodic)
        for pattern in self._temporal_re:
            if pattern.search(message_lower):
                memory_types.add(MemoryType.EPISODIC)
                memory_types.add(MemoryType.USER)
                reasons.append("Temporal reference")
                priority = "high" if priority != "high" else priority
                query_hints.append(message)
                break
        
        # Check relationship building
        for pattern in self._relationship_re:
            if pattern.search(message_lower):
                memory_types.add(MemoryType.USER)
                reasons.append("Relationship context")
                priority = "medium" if priority == "low" else priority
                break
        
        # Check context keywords
        for kw in self.CONTEXT_KEYWORDS:
            if kw in message_lower:
                memory_types.add(MemoryType.USER)
                memory_types.add(MemoryType.EPISODIC)
                reasons.append(f"Context keyword: {kw}")
                priority = "medium" if priority == "low" else priority
                query_hints.append(kw)
                break
        
        # Check for entities mentioned
        entities = context.get("entities_mentioned", [])
        if entities:
            memory_types.add(MemoryType.ENTITY)
            reasons.append(f"Entities mentioned: {', '.join(entities[:3])}")
            priority = "medium" if priority == "low" else priority
            query_hints.extend(entities)
        
        # Check for returning user (first message in session)
        if context.get("is_returning_user") and msg_count <= 2:
            memory_types.add(MemoryType.USER)
            reasons.append("Returning user, personalize greeting")
            priority = "medium" if priority == "low" else priority
        
        # Periodic refresh: Every 10 messages, light retrieval
        if msg_count % 10 == 0 and not memory_types:
            memory_types.add(MemoryType.USER)
            reasons.append("Periodic memory refresh")
            priority = "low"
        
        # Build decision
        should_retrieve = len(memory_types) > 0
        reason = "; ".join(reasons) if reasons else "No triggers matched"
        
        return TriggerDecision(
            should_retrieve=should_retrieve,
            memory_types=memory_types,
            reason=reason,
            priority=priority,
            query_hints=query_hints[:3]  # Limit hints
        )
    
    def get_retrieval_config(self, decision: TriggerDecision) -> Dict:
        """
        Get retrieval configuration based on decision.
        
        Returns dict with:
            - user_memory_limit: int
            - entity_memory_limit: int
            - episodic_limit: int
            - min_relevance: float
        """
        if not decision.should_retrieve:
            return {
                "user_memory_limit": 0,
                "entity_memory_limit": 0,
                "episodic_limit": 0,
                "min_relevance": 1.0
            }
        
        # High priority = more memories, lower threshold
        if decision.priority == "high":
            return {
                "user_memory_limit": 7,
                "entity_memory_limit": 5,
                "episodic_limit": 3,
                "min_relevance": 0.2
            }
        elif decision.priority == "medium":
            return {
                "user_memory_limit": 4,
                "entity_memory_limit": 3,
                "episodic_limit": 2,
                "min_relevance": 0.4
            }
        else:  # low
            return {
                "user_memory_limit": 2,
                "entity_memory_limit": 1,
                "episodic_limit": 0,
                "min_relevance": 0.6
            }
    
    def reset_session(self, user_id: str):
        """Reset tracking for a user (new session)."""
        self._message_count[user_id] = 0
        self._last_retrieval.pop(user_id, None)


# Singleton
_trigger: Optional[MemoryTrigger] = None


def get_memory_trigger() -> MemoryTrigger:
    global _trigger
    if _trigger is None:
        _trigger = MemoryTrigger()
    return _trigger


# =============================================================================
# QUICK INTEGRATION HELPER
# =============================================================================

def should_retrieve_memory(
    message: str,
    user_id: str,
    context: Optional[Dict] = None
) -> Tuple[bool, Dict]:
    """
    Quick helper to check if memory should be retrieved.
    
    Returns: (should_retrieve: bool, config: dict)
    
    Usage in telegram_gateway.py:
        from memory_trigger import should_retrieve_memory
        
        should_retrieve, config = should_retrieve_memory(text, chat_id, context)
        if should_retrieve:
            memories = pm.retrieve_for_prompt(
                identity_id=identity_id,
                query=text,
                limit=config["user_memory_limit"],
                min_relevance=config["min_relevance"]
            )
    """
    trigger = get_memory_trigger()
    decision = trigger.evaluate(message, user_id, context)
    config = trigger.get_retrieval_config(decision)
    
    if decision.should_retrieve:
        print(f"[memory_trigger] TRIGGER: {decision.reason} ({decision.priority})")
    else:
        print(f"[memory_trigger] SKIP: {decision.reason}")
    
    return decision.should_retrieve, config


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    trigger = MemoryTrigger()
    
    test_messages = [
        # Should SKIP (simple)
        ("hi", False),
        ("hello!", False),
        ("yes", False),
        ("thanks", False),
        ("/help", False),
        
        # Should TRIGGER - explicit
        ("what do you know about me?", True),
        ("do you remember our last conversation?", True),
        ("what have you learned about me?", True),
        
        # Should TRIGGER - temporal
        ("last time we talked about pricing", True),
        ("what did we discuss yesterday?", True),
        ("remember when I mentioned the PF1?", True),
        
        # Should TRIGGER - relationship
        ("I'm from ABC Manufacturing", True),
        ("my company needs thermoforming machines", True),
        
        # Should TRIGGER - context
        ("following up on our discussion", True),
        ("any update on my quote?", True),
        
        # Edge cases - might or might not trigger
        ("what is the price of PF1?", False),  # Generic question
        ("tell me about thermoforming", False),  # Generic question
    ]
    
    print("=" * 60)
    print("MEMORY TRIGGER TEST")
    print("=" * 60)
    
    correct = 0
    total = len(test_messages)
    
    for msg, expected in test_messages:
        decision = trigger.evaluate(msg, "test_user")
        actual = decision.should_retrieve
        status = "✅" if actual == expected else "❌"
        
        if actual == expected:
            correct += 1
        
        print(f"\n{status} '{msg[:40]}...'")
        print(f"   Expected: {expected}, Got: {actual}")
        if decision.should_retrieve:
            print(f"   Reason: {decision.reason}")
            print(f"   Types: {[t.value for t in decision.memory_types]}")
    
    print(f"\n{'=' * 60}")
    print(f"Score: {correct}/{total} ({100*correct/total:.0f}%)")
    print("=" * 60)
