#!/usr/bin/env python3
"""
MEMORY WEAVER - How Memories Influence Responses

╔════════════════════════════════════════════════════════════════════╗
║  Memory Trigger decides WHEN to retrieve                           ║
║  Memory Weaver decides HOW to use what was retrieved               ║
╚════════════════════════════════════════════════════════════════════╝

Based on research insight: Raw memory dumps in prompts are suboptimal.
Memories should be:
- Selectively included based on relevance
- Formatted for the specific task
- Prioritized when context window is limited
- Used to guide (not dictate) responses
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import re


class WeaveStrategy(Enum):
    """How memories should influence the response."""
    PERSONALIZE = "personalize"      # Adapt tone/content to user
    RECALL = "recall"                # Explicitly reference past
    CONTEXTUALIZE = "contextualize"  # Add background without mention
    CONSTRAIN = "constrain"          # Use as guardrails (corrections)
    ENRICH = "enrich"                # Add entity knowledge
    NONE = "none"                    # Don't use memories


@dataclass
class WovenContext:
    """
    Memories processed and ready for prompt injection.
    
    Instead of dumping raw memories, we provide:
    - system_injection: Goes in system prompt
    - user_injection: Prepended to user context
    - instructions: Specific guidance for the LLM
    """
    system_injection: str = ""
    user_injection: str = ""
    instructions: List[str] = field(default_factory=list)
    strategy: WeaveStrategy = WeaveStrategy.NONE
    memories_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryWeaver:
    """
    Transforms retrieved memories into actionable prompt context.
    
    Key insight: Different message types need different memory usage:
    - Greeting → personalize with name/preferences
    - Technical question → add entity knowledge, skip personal
    - Follow-up → recall past discussion explicitly
    - Correction scenario → constrain with learned corrections
    """
    
    def weave(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str,
        message_intent: str = None,
        mode: str = None
    ) -> WovenContext:
        """
        Weave memories into prompt context.
        
        Args:
            user_memories: List of UserMemory objects
            entity_memories: List of EntityMemory objects  
            message: The user's current message
            message_intent: Extracted intent (optional)
            mode: Response mode like "answer", "clarify" (optional)
            
        Returns:
            WovenContext ready for prompt injection
        """
        # Determine strategy based on message type
        strategy = self._determine_strategy(message, message_intent, mode)
        
        if strategy == WeaveStrategy.NONE:
            return WovenContext(strategy=strategy)
        
        # Build context based on strategy
        if strategy == WeaveStrategy.PERSONALIZE:
            return self._weave_personalize(user_memories, entity_memories, message)
        elif strategy == WeaveStrategy.RECALL:
            return self._weave_recall(user_memories, entity_memories, message)
        elif strategy == WeaveStrategy.CONTEXTUALIZE:
            return self._weave_contextualize(user_memories, entity_memories, message)
        elif strategy == WeaveStrategy.CONSTRAIN:
            return self._weave_constrain(user_memories, entity_memories, message)
        elif strategy == WeaveStrategy.ENRICH:
            return self._weave_enrich(user_memories, entity_memories, message)
        
        return WovenContext(strategy=strategy)
    
    def _determine_strategy(
        self,
        message: str,
        intent: str = None,
        mode: str = None
    ) -> WeaveStrategy:
        """Determine the best weaving strategy for this message."""
        msg_lower = message.lower()
        
        # Explicit recall triggers
        recall_patterns = [
            r"last time", r"we (discussed|talked)", r"you (said|mentioned)",
            r"remember when", r"as i (said|mentioned)", r"previously",
            r"earlier", r"before"
        ]
        for pattern in recall_patterns:
            if re.search(pattern, msg_lower):
                return WeaveStrategy.RECALL
        
        # Greeting → personalize
        if re.match(r"^(hi|hello|hey|good (morning|afternoon|evening))[\s!.,]*$", msg_lower):
            return WeaveStrategy.PERSONALIZE
        
        # Questions about self → personalize
        if re.search(r"(what do you know|what have you learned|my memories)", msg_lower):
            return WeaveStrategy.RECALL
        
        # Technical/product questions → enrich with entity knowledge
        technical_keywords = [
            "price", "spec", "feature", "how does", "what is",
            "compare", "difference", "cost", "quote", "order"
        ]
        if any(kw in msg_lower for kw in technical_keywords):
            return WeaveStrategy.ENRICH
        
        # Follow-up mode → contextualize
        if mode in ["followup", "clarify"]:
            return WeaveStrategy.CONTEXTUALIZE
        
        # Correction detection → constrain
        correction_patterns = [r"^no[,.]", r"actually", r"i meant", r"not quite"]
        for pattern in correction_patterns:
            if re.search(pattern, msg_lower):
                return WeaveStrategy.CONSTRAIN
        
        # Default: contextualize (subtle background)
        return WeaveStrategy.CONTEXTUALIZE
    
    def _weave_personalize(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str
    ) -> WovenContext:
        """Weave for personalization - adapt tone and content to user."""
        context = WovenContext(strategy=WeaveStrategy.PERSONALIZE)
        
        if not user_memories:
            return context
        
        # Extract key personalization facts
        name = None
        company = None
        preferences = []
        facts = []
        
        for mem in user_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            mem_type = mem.memory_type if hasattr(mem, 'memory_type') else 'fact'
            
            # Look for name
            name_match = re.search(r"name is (\w+)", text, re.IGNORECASE)
            if name_match and not name:
                name = name_match.group(1)
            
            # Look for company
            company_patterns = [
                r"(?:works at|from|with|company is) ([A-Z][A-Za-z0-9\s&]+)",
                r"([A-Z][A-Za-z0-9\s&]+) (?:employee|manager|director|CEO)"
            ]
            for pattern in company_patterns:
                match = re.search(pattern, text)
                if match and not company:
                    company = match.group(1).strip()
            
            if mem_type == "preference":
                preferences.append(text)
            else:
                facts.append(text)
        
        # Build system injection
        system_parts = []
        if name or company or preferences:
            system_parts.append("USER CONTEXT (use naturally, don't explicitly mention you remember):")
            if name:
                system_parts.append(f"- User's name: {name}")
            if company:
                system_parts.append(f"- Company: {company}")
            for pref in preferences[:3]:
                system_parts.append(f"- {pref}")
        
        context.system_injection = "\n".join(system_parts)
        context.instructions = [
            "Address the user by name if known",
            "Adapt communication style to their preferences",
            "Reference their company context if relevant"
        ]
        context.memories_used = len(user_memories)
        context.metadata = {"name": name, "company": company}
        
        return context
    
    def _weave_recall(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str
    ) -> WovenContext:
        """Weave for explicit recall - reference past interactions."""
        context = WovenContext(strategy=WeaveStrategy.RECALL)
        
        all_memories = []
        
        # Format user memories
        for mem in user_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            mem_type = mem.memory_type if hasattr(mem, 'memory_type') else 'fact'
            source = mem.source_channel if hasattr(mem, 'source_channel') else 'conversation'
            all_memories.append(f"[{mem_type}] {text} (from {source})")
        
        # Format entity memories
        for mem in entity_memories:
            entity = mem.entity_name if hasattr(mem, 'entity_name') else 'Unknown'
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            all_memories.append(f"[about {entity}] {text}")
        
        if all_memories:
            context.system_injection = "PAST INTERACTIONS & LEARNED FACTS:\n" + "\n".join(all_memories[:10])
            context.instructions = [
                "You MAY explicitly reference these past facts when relevant",
                "Use phrases like 'As you mentioned before...' or 'I remember you said...'",
                "Connect current question to past context"
            ]
        
        context.memories_used = len(all_memories)
        return context
    
    def _weave_contextualize(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str
    ) -> WovenContext:
        """Weave for subtle context - background without explicit mention."""
        context = WovenContext(strategy=WeaveStrategy.CONTEXTUALIZE)
        
        background = []
        
        # Add relevant user facts
        for mem in user_memories[:5]:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            background.append(f"- {text}")
        
        # Add entity context
        for mem in entity_memories[:3]:
            entity = mem.entity_name if hasattr(mem, 'entity_name') else 'Unknown'
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            background.append(f"- Re {entity}: {text}")
        
        if background:
            context.user_injection = "BACKGROUND CONTEXT (use implicitly):\n" + "\n".join(background)
            context.instructions = [
                "Use this context to inform your response",
                "Do NOT explicitly say 'I remember' or reference having memory",
                "Let the context guide your answer naturally"
            ]
        
        context.memories_used = len(background)
        return context
    
    def _weave_constrain(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str
    ) -> WovenContext:
        """Weave for constraints - use corrections as guardrails."""
        context = WovenContext(strategy=WeaveStrategy.CONSTRAIN)
        
        corrections = []
        constraints = []
        
        for mem in user_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            mem_type = mem.memory_type if hasattr(mem, 'memory_type') else 'fact'
            
            if mem_type == "correction":
                corrections.append(text)
            else:
                constraints.append(text)
        
        if corrections:
            context.system_injection = (
                "IMPORTANT CORRECTIONS (user has corrected these before):\n" +
                "\n".join(f"⚠️ {c}" for c in corrections[:5])
            )
            context.instructions = [
                "Pay special attention to these corrections",
                "Do NOT repeat previous mistakes",
                "The user has explicitly corrected these points before"
            ]
        elif constraints:
            context.system_injection = "USER CONSTRAINTS:\n" + "\n".join(constraints[:5])
            context.instructions = ["Respect these known user constraints"]
        
        context.memories_used = len(corrections) + len(constraints)
        return context
    
    def _weave_enrich(
        self,
        user_memories: List[Any],
        entity_memories: List[Any],
        message: str
    ) -> WovenContext:
        """Weave for enrichment - add entity/domain knowledge."""
        context = WovenContext(strategy=WeaveStrategy.ENRICH)
        
        knowledge = []
        
        # Entity memories are primary
        for mem in entity_memories:
            entity = mem.entity_name if hasattr(mem, 'entity_name') else 'Unknown'
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            knowledge.append(f"[{entity}] {text}")
        
        # Add relevant user context (like their company's needs)
        for mem in user_memories[:3]:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem)
            mem_type = mem.memory_type if hasattr(mem, 'memory_type') else 'fact'
            if mem_type in ["fact", "context"]:
                knowledge.append(f"[user context] {text}")
        
        if knowledge:
            context.system_injection = (
                "RELEVANT KNOWLEDGE:\n" +
                "\n".join(knowledge[:10])
            )
            context.instructions = [
                "Use this knowledge to enhance your answer",
                "Connect entity facts to the user's specific needs",
                "Prioritize accuracy from known facts"
            ]
        
        context.memories_used = len(knowledge)
        return context
    
    def format_for_prompt(self, woven: WovenContext) -> Dict[str, str]:
        """
        Format woven context for direct prompt injection.
        
        Returns dict with:
            - system_addition: Add to system prompt
            - user_context: Prepend to user message context
            - response_guidance: Instructions for response
        """
        result = {
            "system_addition": "",
            "user_context": "",
            "response_guidance": ""
        }
        
        if woven.strategy == WeaveStrategy.NONE:
            return result
        
        if woven.system_injection:
            result["system_addition"] = f"\n\n{woven.system_injection}"
        
        if woven.user_injection:
            result["user_context"] = f"{woven.user_injection}\n\n"
        
        if woven.instructions:
            result["response_guidance"] = "\n".join(f"• {i}" for i in woven.instructions)
        
        return result


# Singleton
_weaver: Optional[MemoryWeaver] = None


def get_memory_weaver() -> MemoryWeaver:
    global _weaver
    if _weaver is None:
        _weaver = MemoryWeaver()
    return _weaver


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    from dataclasses import dataclass
    
    @dataclass
    class MockMemory:
        memory_text: str
        memory_type: str = "fact"
        source_channel: str = "telegram"
    
    @dataclass 
    class MockEntityMemory:
        entity_name: str
        memory_text: str
    
    weaver = MemoryWeaver()
    
    # Test user memories
    user_mems = [
        MockMemory("User's name is John", "fact"),
        MockMemory("Works at ABC Manufacturing", "fact"),
        MockMemory("Prefers concise responses", "preference"),
        MockMemory("Previously asked about PF1 pricing", "context"),
    ]
    
    entity_mems = [
        MockEntityMemory("ABC Manufacturing", "Industrial client, 50 employees"),
        MockEntityMemory("PF1", "Thermoforming machine, price range $50k-80k"),
    ]
    
    test_cases = [
        ("hi!", "greeting"),
        ("what do you know about me?", "recall"),
        ("what is the price of PF1?", "technical"),
        ("as I mentioned before, we need 5 units", "followup"),
        ("no, I meant the other model", "correction"),
    ]
    
    print("=" * 60)
    print("MEMORY WEAVER TEST")
    print("=" * 60)
    
    for msg, expected_type in test_cases:
        woven = weaver.weave(user_mems, entity_mems, msg)
        formatted = weaver.format_for_prompt(woven)
        
        print(f"\n📝 Message: '{msg}'")
        print(f"   Strategy: {woven.strategy.value}")
        print(f"   Memories used: {woven.memories_used}")
        if woven.instructions:
            print(f"   Instructions: {woven.instructions[0][:50]}...")
        if formatted["system_addition"]:
            preview = formatted["system_addition"][:80].replace("\n", " ")
            print(f"   System: {preview}...")
    
    print("\n" + "=" * 60)
