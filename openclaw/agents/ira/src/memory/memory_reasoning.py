#!/usr/bin/env python3
"""
MEMORY REASONING - Think With Memories Before Responding

╔════════════════════════════════════════════════════════════════════╗
║  Key insight: Memories should guide REASONING, not just responses  ║
║                                                                    ║
║  Before: User → Retrieve memories → Dump in prompt → LLM responds  ║
║  After:  User → Retrieve memories → REASON about relevance →       ║
║          Generate reasoning trace → LLM responds with insight      ║
╚════════════════════════════════════════════════════════════════════╝

This is what makes ChatGPT's memory feel "smart" - it thinks with memories.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import from centralized config via brain_orchestrator
try:
    from config import OPENAI_API_KEY
except ImportError:
    import os
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


@dataclass
class ReasoningTrace:
    """
    The result of memory-guided reasoning.
    
    Contains:
    - inner_monologue: What Ira "thought" about the memories
    - relevant_facts: Facts that are relevant to this query
    - connections: Connections made between memories
    - action_hints: Suggested actions based on reasoning
    - confidence: How confident the reasoning is
    """
    inner_monologue: str = ""
    relevant_facts: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    action_hints: List[str] = field(default_factory=list)
    confidence: float = 0.5
    reasoning_time_ms: int = 0
    
    def to_prompt_context(self) -> str:
        """Format reasoning for prompt injection."""
        if not self.inner_monologue:
            return ""
        
        parts = []
        parts.append("REASONING (my thoughts before responding):")
        parts.append(self.inner_monologue)
        
        if self.relevant_facts:
            parts.append("\nKEY FACTS I'M CONSIDERING:")
            for fact in self.relevant_facts[:5]:
                parts.append(f"  • {fact}")
        
        if self.connections:
            parts.append("\nCONNECTIONS I'VE MADE:")
            for conn in self.connections[:3]:
                parts.append(f"  → {conn}")
        
        if self.action_hints:
            parts.append("\nI SHOULD:")
            for hint in self.action_hints[:3]:
                parts.append(f"  ✓ {hint}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict:
        return {
            "inner_monologue": self.inner_monologue,
            "relevant_facts": self.relevant_facts,
            "connections": self.connections,
            "action_hints": self.action_hints,
            "confidence": self.confidence,
            "reasoning_time_ms": self.reasoning_time_ms,
        }


# =============================================================================
# FAST REASONING (Rule-based, no LLM)
# =============================================================================

class FastMemoryReasoner:
    """
    Rule-based reasoning - fast, no API calls.
    
    Use for most messages. Only escalate to LLM reasoning for complex cases.
    """
    
    def reason(
        self,
        message: str,
        user_memories: List[Any],
        entity_memories: List[Any],
        context: Optional[Dict] = None
    ) -> ReasoningTrace:
        """
        Fast rule-based reasoning about memories.
        """
        import time
        start = time.time()
        
        trace = ReasoningTrace()
        msg_lower = message.lower()
        context = context or {}
        
        # Extract memory texts
        user_facts = []
        for mem in user_memories:
            text = mem.memory_text if hasattr(mem, 'memory_text') else str(mem.get('memory_text', ''))
            mem_type = mem.memory_type if hasattr(mem, 'memory_type') else mem.get('memory_type', 'fact')
            user_facts.append((text, mem_type))
        
        entity_facts = []
        for mem in entity_memories:
            entity = mem.entity_name if hasattr(mem, 'entity_name') else mem.get('entity_name', 'Unknown')
            text = mem.memory_text if hasattr(mem, 'memory_text') else mem.get('memory_text', '')
            entity_facts.append((entity, text))
        
        # ===== PATTERN 1: User asking about themselves =====
        if re.search(r"(what do you|do you) (know|remember)", msg_lower):
            trace.inner_monologue = "User is asking what I remember. I should share what I know about them."
            trace.relevant_facts = [f[0] for f in user_facts]
            trace.action_hints = ["List what I remember clearly", "Be honest about gaps"]
            trace.confidence = 0.9
        
        # ===== PATTERN 2: Follow-up / continuation =====
        elif re.search(r"(last time|we (discussed|talked)|as i (said|mentioned)|previously)", msg_lower):
            trace.inner_monologue = "User is referencing past conversation. Let me recall what we discussed."
            # Find most relevant memories
            for text, mtype in user_facts:
                if mtype == "context":
                    trace.relevant_facts.append(text)
            trace.connections = ["This connects to our previous conversation"]
            trace.action_hints = ["Reference the past context explicitly", "Continue from where we left off"]
            trace.confidence = 0.8
        
        # ===== PATTERN 3: User mentioning their company/role =====
        elif re.search(r"(my company|we need|our (team|business)|i('m| am) (from|at|with))", msg_lower):
            trace.inner_monologue = "User is providing context about their company. I should connect this to what I know."
            # Find company-related memories
            for text, mtype in user_facts:
                if any(kw in text.lower() for kw in ["company", "work", "role", "business"]):
                    trace.relevant_facts.append(text)
            for entity, text in entity_facts:
                trace.relevant_facts.append(f"About {entity}: {text}")
            trace.action_hints = ["Acknowledge their context", "Tailor response to their business"]
            trace.confidence = 0.7
        
        # ===== PATTERN 4: Product/quote question =====
        elif re.search(r"(price|quote|cost|spec|feature|model|product)", msg_lower):
            trace.inner_monologue = "User asking about products. Let me check what I know about their needs."
            # Find relevant entity memories
            for entity, text in entity_facts:
                trace.relevant_facts.append(f"{entity}: {text}")
            # Find user's past interests
            for text, mtype in user_facts:
                if any(kw in text.lower() for kw in ["interested", "asked", "needs", "looking"]):
                    trace.relevant_facts.append(text)
            trace.action_hints = ["Consider their past inquiries", "Personalize the recommendation"]
            trace.confidence = 0.75
        
        # ===== PATTERN 5: Correction =====
        elif re.search(r"^(no[,.]|actually|that's not|i meant|not quite)", msg_lower):
            trace.inner_monologue = "User is correcting me. I need to acknowledge and adjust."
            # Find any previous corrections
            for text, mtype in user_facts:
                if mtype == "correction":
                    trace.relevant_facts.append(f"Previous correction: {text}")
            trace.action_hints = ["Acknowledge the correction gracefully", "Don't repeat the mistake"]
            trace.confidence = 0.85
        
        # ===== PATTERN 6: Greeting with known user =====
        elif re.search(r"^(hi|hello|hey|good (morning|afternoon|evening))", msg_lower) and user_facts:
            # Find user's name
            name = None
            for text, _ in user_facts:
                name_match = re.search(r"name is (\w+)", text, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1)
                    break
            
            if name:
                trace.inner_monologue = f"This is {name} greeting me. I should be warm and personal."
                trace.relevant_facts = [f"User's name is {name}"]
                trace.action_hints = [f"Greet {name} by name", "Show I remember them"]
            else:
                trace.inner_monologue = "Returning user greeting. I should be warm."
                trace.action_hints = ["Acknowledge them warmly"]
            trace.confidence = 0.9
        
        # ===== PATTERN 7: General with memories available =====
        elif user_facts or entity_facts:
            trace.inner_monologue = "Processing query with relevant background knowledge."
            # Add top facts
            for text, _ in user_facts[:2]:
                trace.relevant_facts.append(text)
            for entity, text in entity_facts[:2]:
                trace.relevant_facts.append(f"{entity}: {text}")
            trace.confidence = 0.6
        
        # ===== NO RELEVANT PATTERN =====
        else:
            trace.inner_monologue = ""
            trace.confidence = 0.0
        
        trace.reasoning_time_ms = int((time.time() - start) * 1000)
        return trace


# =============================================================================
# DEEP REASONING (LLM-based, for complex cases)
# =============================================================================

REASONING_PROMPT = """You are Ira's inner reasoning process. Given a user message and memories, think through:

1. What do I know about this user that's relevant?
2. What connections can I make?
3. How should this inform my response?

USER MESSAGE: {message}

USER MEMORIES:
{user_memories}

ENTITY MEMORIES:
{entity_memories}

CONTEXT:
{context}

Think step by step, then output JSON:
{{
    "inner_monologue": "My thoughts about this situation...",
    "relevant_facts": ["fact 1", "fact 2"],
    "connections": ["connection 1"],
    "action_hints": ["what I should do"]
}}"""


class DeepMemoryReasoner:
    """
    LLM-based reasoning - slower but more nuanced.
    
    Use for:
    - Complex multi-memory queries
    - Ambiguous situations
    - When user explicitly references past
    """
    
    def reason(
        self,
        message: str,
        user_memories: List[Any],
        entity_memories: List[Any],
        context: Optional[Dict] = None
    ) -> ReasoningTrace:
        """
        Deep LLM-based reasoning about memories.
        """
        import time
        start = time.time()
        
        if not OPENAI_API_KEY:
            print("[memory_reasoning] No OpenAI key, falling back to fast reasoning")
            return FastMemoryReasoner().reason(message, user_memories, entity_memories, context)
        
        # Format memories for prompt
        user_mem_text = ""
        for i, mem in enumerate(user_memories[:7], 1):
            text = mem.memory_text if hasattr(mem, 'memory_text') else mem.get('memory_text', '')
            mtype = mem.memory_type if hasattr(mem, 'memory_type') else mem.get('memory_type', 'fact')
            user_mem_text += f"{i}. [{mtype}] {text}\n"
        
        entity_mem_text = ""
        for i, mem in enumerate(entity_memories[:5], 1):
            entity = mem.entity_name if hasattr(mem, 'entity_name') else mem.get('entity_name', 'Unknown')
            text = mem.memory_text if hasattr(mem, 'memory_text') else mem.get('memory_text', '')
            entity_mem_text += f"{i}. [{entity}] {text}\n"
        
        context_text = json.dumps(context or {}, indent=2)
        
        prompt = REASONING_PROMPT.format(
            message=message,
            user_memories=user_mem_text or "(none)",
            entity_memories=entity_mem_text or "(none)",
            context=context_text
        )
        
        try:
            import httpx
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                trace = ReasoningTrace(
                    inner_monologue=data.get("inner_monologue", ""),
                    relevant_facts=data.get("relevant_facts", []),
                    connections=data.get("connections", []),
                    action_hints=data.get("action_hints", []),
                    confidence=0.85,
                    reasoning_time_ms=int((time.time() - start) * 1000)
                )
                return trace
            
        except Exception as e:
            print(f"[memory_reasoning] LLM error: {e}")
        
        # Fallback to fast reasoning
        trace = FastMemoryReasoner().reason(message, user_memories, entity_memories, context)
        trace.reasoning_time_ms = int((time.time() - start) * 1000)
        return trace


# =============================================================================
# UNIFIED INTERFACE
# =============================================================================

class MemoryReasoner:
    """
    Unified reasoning interface.
    
    Automatically chooses fast vs deep reasoning based on complexity.
    """
    
    def __init__(self):
        self.fast = FastMemoryReasoner()
        self.deep = DeepMemoryReasoner()
        self._use_deep_for = [
            r"(what do you|do you) (know|remember)",
            r"last time we",
            r"as (i|we) (discussed|mentioned|said)",
            r"remember when",
        ]
        self._deep_patterns = [re.compile(p, re.IGNORECASE) for p in self._use_deep_for]
    
    def _needs_deep_reasoning(self, message: str, memory_count: int) -> bool:
        """Decide if this needs LLM reasoning."""
        # Deep reasoning for explicit memory queries
        for pattern in self._deep_patterns:
            if pattern.search(message):
                return True
        
        # Deep reasoning if many memories to consider
        if memory_count > 5:
            return True
        
        return False
    
    def reason(
        self,
        message: str,
        user_memories: List[Any],
        entity_memories: List[Any],
        context: Optional[Dict] = None,
        force_deep: bool = False
    ) -> ReasoningTrace:
        """
        Reason about memories before responding.
        
        Args:
            message: User's message
            user_memories: Retrieved user memories
            entity_memories: Retrieved entity memories
            context: Additional context
            force_deep: Force LLM reasoning
        
        Returns:
            ReasoningTrace with inner monologue and insights
        """
        memory_count = len(user_memories) + len(entity_memories)
        
        if memory_count == 0:
            return ReasoningTrace(confidence=0.0)
        
        if force_deep or self._needs_deep_reasoning(message, memory_count):
            print(f"[memory_reasoning] Using DEEP reasoning ({memory_count} memories)")
            return self.deep.reason(message, user_memories, entity_memories, context)
        else:
            print(f"[memory_reasoning] Using FAST reasoning ({memory_count} memories)")
            return self.fast.reason(message, user_memories, entity_memories, context)


# Singleton
_reasoner: Optional[MemoryReasoner] = None


def get_memory_reasoner() -> MemoryReasoner:
    global _reasoner
    if _reasoner is None:
        _reasoner = MemoryReasoner()
    return _reasoner


def reason_with_memories(
    message: str,
    user_memories: List[Any],
    entity_memories: List[Any],
    context: Optional[Dict] = None
) -> ReasoningTrace:
    """
    Quick helper to reason about memories.
    
    Usage:
        trace = reason_with_memories(message, user_mems, entity_mems)
        if trace.inner_monologue:
            prompt += trace.to_prompt_context()
    """
    return get_memory_reasoner().reason(message, user_memories, entity_memories, context)


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    from dataclasses import dataclass
    
    @dataclass
    class MockMemory:
        memory_text: str
        memory_type: str = "fact"
    
    @dataclass
    class MockEntityMemory:
        entity_name: str
        memory_text: str
    
    user_mems = [
        MockMemory("User's name is John", "fact"),
        MockMemory("Works at ABC Manufacturing", "fact"),
        MockMemory("Previously asked about PF1 pricing", "context"),
        MockMemory("Prefers concise responses", "preference"),
    ]
    
    entity_mems = [
        MockEntityMemory("ABC Manufacturing", "Industrial client with 50 employees"),
        MockEntityMemory("PF1", "Thermoforming machine, $50k-80k range"),
    ]
    
    reasoner = MemoryReasoner()
    
    test_cases = [
        "hi!",
        "what do you know about me?",
        "last time we discussed the PF1, what was the price?",
        "my company needs 5 units",
        "no, I meant the smaller model",
        "what's the price of PF1?",
    ]
    
    print("=" * 70)
    print("MEMORY REASONING TEST")
    print("=" * 70)
    
    for msg in test_cases:
        trace = reasoner.reason(msg, user_mems, entity_mems)
        
        print(f"\n📝 Message: '{msg}'")
        print(f"   Inner monologue: {trace.inner_monologue[:60]}..." if trace.inner_monologue else "   (no reasoning)")
        print(f"   Confidence: {trace.confidence}")
        print(f"   Time: {trace.reasoning_time_ms}ms")
        if trace.relevant_facts:
            print(f"   Facts: {trace.relevant_facts[:2]}")
        if trace.action_hints:
            print(f"   Hints: {trace.action_hints[:2]}")
    
    print("\n" + "=" * 70)
