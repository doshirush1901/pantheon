"""Response types extracted from generate_answer.py."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from qdrant_retriever import record_knowledge_feedback
except ImportError:
    def record_knowledge_feedback(knowledge_id, was_helpful):
        return False


class ResponseMode(Enum):
    SALES = "sales"
    GENERAL = "general"
    OPS = "ops"
    INTRO = "intro"


class ConfidenceLevel(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Citation:
    text: str
    filename: str
    page: Optional[int] = None
    source_group: str = "business"
    score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "filename": self.filename,
            "page": self.page,
            "source_group": self.source_group,
            "score": self.score
        }


@dataclass
class ResponseObject:
    text: str
    mode: ResponseMode
    confidence: ConfidenceLevel
    confidence_reason: str = ""
    citations: List[Citation] = field(default_factory=list)
    clarifying_questions: List[str] = field(default_factory=list)
    channel: str = "telegram"
    generation_path: str = "unified"
    debug_info: Dict[str, Any] = field(default_factory=dict)
    consolidated_knowledge_ids: List[str] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "mode": self.mode.value,
            "confidence": self.confidence.value,
            "confidence_reason": self.confidence_reason,
            "citations": [c.to_dict() for c in self.citations],
            "clarifying_questions": self.clarifying_questions,
            "channel": self.channel,
            "generation_path": self.generation_path,
            "debug_info": self.debug_info,
            "consolidated_knowledge_ids": self.consolidated_knowledge_ids,
            "agents_used": self.agents_used,
        }

    def record_feedback(self, was_helpful: bool) -> int:
        """
        Record feedback for all consolidated knowledge used in this response.

        Call this when:
        - User gives positive reaction (thumbs up, thanks, good answer) -> was_helpful=True
        - User gives negative reaction (wrong, correction, bad answer) -> was_helpful=False

        Returns:
            Number of knowledge items that had feedback recorded
        """
        count = 0
        for knowledge_id in self.consolidated_knowledge_ids:
            if record_knowledge_feedback(knowledge_id, was_helpful):
                count += 1
        return count


@dataclass
class ContextPack:
    recent_messages: List[Dict] = field(default_factory=list)
    rolling_summary: str = ""
    open_questions: List[Dict] = field(default_factory=list)
    key_entities: Dict = field(default_factory=dict)
    kg_facts: List[Dict] = field(default_factory=list)
    rag_chunks: List[Dict] = field(default_factory=list)
    identity: Optional[Dict] = None
    is_internal: bool = False
    thread_id: str = ""
    current_mode: str = "general"
    current_stage: str = "new"
    user_memories: List[Dict] = field(default_factory=list)
    entity_memories: List[Dict] = field(default_factory=list)
    memory_guidance: Dict = field(default_factory=dict)
    reasoning_context: str = ""
    metacognitive_guidance: str = ""
    conversational_enhancement: Optional[Dict] = None
    episodic_context: str = ""          # NEW: Temporal context from past events
    procedure_guidance: str = ""         # NEW: Step-by-step guidance for tasks
    mem0_context: str = ""               # NEW: Mem0 semantic memory context
    brain_state: Optional[Any] = None    # NEW: Reference to BrainState for feedback
    soul_context: str = ""               # NEW: Ira's identity from SOUL.md
    competitor_context: str = ""         # NEW: Competitor intelligence context
    is_competitor_comparison: bool = False  # NEW: Flag for competitor queries
    competitors_mentioned: List[str] = field(default_factory=list)  # NEW: Competitors detected

    # Query Analysis (Phase 0.5 - Multi-stage understanding)
    query_intent: str = ""                # Detected intent (RECOMMENDATION, SPEC_REQUEST, etc.)
    query_entities: Dict = field(default_factory=dict)  # Extracted entities
    query_constraints: List[Dict] = field(default_factory=list)  # Requirements/constraints
    query_analysis_context: str = ""      # Formatted query analysis for prompt
    suggested_response_length: str = "medium"  # Dynamic response length

    # Customer Context (Phase 0.7 - Profile awareness)
    customer_name: Optional[str] = None
    customer_company: Optional[str] = None
    customer_role: Optional[str] = None
    customer_style: str = "default"       # Communication style preference
    customer_relationship: str = "unknown"  # INTERNAL, PROSPECT, ACTIVE_CUSTOMER, etc.
    customer_context_formatted: str = ""   # Formatted customer context for prompt
    customer_style_instructions: str = ""  # Style-specific instructions

    # Extra fields from BrainState (catch-all for extensibility)
    extra: Dict = field(default_factory=dict)

    def to_dict(self):
        """Serialize to JSON-safe dict. Skips brain_state."""
        return {k: getattr(self, k) for k in [
            "recent_messages", "rolling_summary", "kg_facts", "rag_chunks",
            "key_entities", "open_questions", "identity", "is_internal",
            "thread_id", "current_mode", "current_stage", "user_memories",
            "entity_memories", "memory_guidance", "reasoning_context",
            "metacognitive_guidance", "episodic_context", "procedure_guidance",
            "mem0_context", "soul_context", "competitor_context",
            "is_competitor_comparison", "competitors_mentioned",
            "query_intent", "query_entities", "query_constraints",
            "query_analysis_context", "suggested_response_length",
            "customer_name", "customer_company", "customer_role",
            "customer_style", "customer_relationship",
            "customer_context_formatted", "customer_style_instructions", "extra"
        ]}

    @classmethod
    def from_dict(cls, d: Dict) -> "ContextPack":
        return cls(
            recent_messages=d.get("recent_messages", []),
            rolling_summary=d.get("rolling_summary", ""),
            kg_facts=d.get("kg_facts", []),
            rag_chunks=d.get("rag_chunks", []),
            key_entities=d.get("key_entities", {}),
            open_questions=d.get("open_questions", []),
            identity=d.get("identity"),
            is_internal=d.get("is_internal", False),
            thread_id=d.get("thread_id", ""),
            current_mode=d.get("current_mode", "general"),
            current_stage=d.get("current_stage", "new"),
            user_memories=d.get("user_memories", []),
            entity_memories=d.get("entity_memories", []),
            memory_guidance=d.get("memory_guidance", {}),
            reasoning_context=d.get("reasoning_context", ""),
            metacognitive_guidance=d.get("metacognitive_guidance", ""),
            conversational_enhancement=d.get("conversational_enhancement"),
            episodic_context=d.get("episodic_context", ""),
            procedure_guidance=d.get("procedure_guidance", ""),
            mem0_context=d.get("mem0_context", ""),
            brain_state=d.get("brain_state"),
            soul_context=d.get("soul_context", ""),
            competitor_context=d.get("competitor_context", ""),
            is_competitor_comparison=d.get("is_competitor_comparison", False),
            competitors_mentioned=d.get("competitors_mentioned", []),
            # Query Analysis fields
            query_intent=d.get("query_intent", ""),
            query_entities=d.get("query_entities", {}),
            query_constraints=d.get("query_constraints", []),
            query_analysis_context=d.get("query_analysis_context", ""),
            suggested_response_length=d.get("suggested_response_length", "medium"),
            # Customer Context fields
            customer_name=d.get("customer_name"),
            customer_company=d.get("customer_company"),
            customer_role=d.get("customer_role"),
            customer_style=d.get("customer_style", "default"),
            customer_relationship=d.get("customer_relationship", "unknown"),
            customer_context_formatted=d.get("customer_context_formatted", ""),
            customer_style_instructions=d.get("customer_style_instructions", ""),
            extra=d.get("extra", {}),
        )

    def has_conversation_history(self) -> bool:
        return bool(self.recent_messages or self.rolling_summary)
