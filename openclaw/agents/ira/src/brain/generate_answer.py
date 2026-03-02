#!/usr/bin/env python3
"""
UNIFIED RESPONSE GENERATOR with Multi-Pass Reliability Pipeline
================================================================

Single entrypoint for all response generation (Email + Telegram).
Implements a 3-pass pipeline for production-grade reliability:

    Pass 1: Draft Generation - Comprehensive draft from query + context
    Pass 2: Fact Extraction & Verification - Verify against canonical database
    Pass 3: Final Polish - Apply corrections and business rules

Usage:
    from generate_answer import generate_answer, ResponseObject
    
    result = generate_answer(
        intent="What's the price for PF1?",
        context_pack=context,
        channel="telegram"
    )
"""

import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

# Use centralized config for path setup
try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import OPENAI_API_KEY, get_logger, setup_import_paths
    setup_import_paths()
    logger = get_logger(__name__)
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    sys.path.insert(0, str(SKILLS_DIR / "conversation"))
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    import logging
    logger = logging.getLogger(__name__)

# Production resilience layer
try:
    from core.resilience import (
        with_resilience, openai_breaker,
        retry_with_exponential_backoff
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

# Error monitoring
try:
    from error_monitor import track_error, track_warning
except ImportError:
    def track_error(component, error, context=None, severity="error"): pass
    def track_warning(component, message, context=None): pass

# Try to import Replika integration
try:
    from replika_integration import ConversationalEnhancer, create_enhancer
    REPLIKA_AVAILABLE = True
except ImportError:
    REPLIKA_AVAILABLE = False
    logger.debug("Replika integration not available")

# Try to import Truth Hints
try:
    from truth_hints import get_truth_hint, TruthHint
    TRUTH_HINTS_AVAILABLE = True
except ImportError:
    TRUTH_HINTS_AVAILABLE = False
    logger.debug("Truth hints not available")

# Try to import Email Styling
try:
    from email_styling import (
        EmailStyler, EMAIL_STYLE_PROMPT, RecipientRelationship,
        format_email, check_email_quality
    )
    EMAIL_STYLING_AVAILABLE = True
except ImportError:
    EMAIL_STYLING_AVAILABLE = False
    logger.debug("Email styling not available")

# Try to import Email Polish (final refinement pass)
try:
    from email_polish import EmailPolisher, polish_email
    EMAIL_POLISH_AVAILABLE = True
except ImportError:
    EMAIL_POLISH_AVAILABLE = False
    logger.debug("Email polish not available")

# Try to import Lesson Injector (continuous learning integration)
try:
    # Path: brain -> src -> ira -> agents -> openclaw -> Ira (project root) -> agents/apollo
    _project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    sys.path.insert(0, str(_project_root / "agents" / "apollo"))
    from lesson_injector import inject_lessons, get_agent_guidance
    LESSON_INJECTION_AVAILABLE = True
    logger.info("Lesson injection enabled - Ira will apply learned lessons")
except ImportError:
    LESSON_INJECTION_AVAILABLE = False
    def inject_lessons(query): return ""
    def get_agent_guidance(agent): return ""

# Try to import Proactive Questions Engine
try:
    from proactive_questions import (
        get_proactive_questions, format_proactive_questions,
        ProactiveQuestion, get_proactive_engine
    )
    PROACTIVE_AVAILABLE = True
except ImportError:
    PROACTIVE_AVAILABLE = False
    logger.debug("Proactive questions not available")

# Try to import Quote Generator
try:
    from quote_generator import QuoteGenerator, generate_quote, format_quote
    from quote_email_formatter import format_quote_email, format_quote_telegram
    QUOTE_AVAILABLE = True
except ImportError:
    QUOTE_AVAILABLE = False
    logger.debug("Quote generator not available")

# Try to import Sales Quote Generator for PDF generation
try:
    sys.path.insert(0, str(SKILLS_DIR))
    from sales.quote_generator import (
        SalesQuoteGenerator as PDFQuoteGenerator,
        generate_quote as generate_pdf_quote,
    )
    PDF_QUOTE_AVAILABLE = True
except ImportError:
    PDF_QUOTE_AVAILABLE = False
    logger.debug("PDF quote generator not available")

# Try to import Machine Database for fact verification
try:
    from machine_database import get_machine, MACHINE_SPECS, MachineSpec, find_machines_by_size
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False
    logger.debug("Machine database not available")

# Try to import Machine Recommender for size-based recommendations
try:
    from machine_recommender import recommend_from_query, RecommendationResult
    MACHINE_RECOMMENDER_AVAILABLE = True
except ImportError:
    MACHINE_RECOMMENDER_AVAILABLE = False

# Try to import Sales Qualifier for vague inquiry detection
try:
    from sales_qualifier import (
        qualify_inquiry, is_vague_inquiry, format_qualifying_response,
        QualificationResult, is_specific_model_query,
        detect_img_requirement, detect_impossible_request, ImpossibleRequestResult
    )
    SALES_QUALIFIER_AVAILABLE = True
except ImportError:
    SALES_QUALIFIER_AVAILABLE = False
    is_specific_model_query = lambda x: False
    logger.debug("Sales qualifier not available")

# Try to import Deterministic Series Router (runs before LLM)
try:
    from deterministic_router import route_to_series
    DETERMINISTIC_ROUTER_AVAILABLE = True
except ImportError:
    DETERMINISTIC_ROUTER_AVAILABLE = False
    logger.debug("Deterministic router not available")

# Try to import Detailed Recommendation formatter
try:
    from detailed_recommendation import format_detailed_recommendation, format_comparison
    DETAILED_RECOMMENDATION_AVAILABLE = True
except ImportError:
    DETAILED_RECOMMENDATION_AVAILABLE = False
    logger.debug("Detailed recommendation formatter not available")

# Try to import Email Packager for beautiful branded emails
try:
    from email_packager import (
        MachinecraftEmailPackager, package_email, PackagedEmail
    )
    EMAIL_PACKAGER_AVAILABLE = True
except ImportError:
    EMAIL_PACKAGER_AVAILABLE = False
    logger.debug("Email packager not available")

# Try to import Fact Checker (unified in src/agents/fact_checker/)
try:
    from src.agents.fact_checker.agent import FactChecker, verify_reply, FactIssue
    FACT_CHECKER_AVAILABLE = True
except ImportError:
    try:
        from openclaw.agents.ira.src.agents.fact_checker.agent import FactChecker, verify_reply, FactIssue
        FACT_CHECKER_AVAILABLE = True
    except ImportError:
        FACT_CHECKER_AVAILABLE = False
        logger.debug("Fact checker not available")

# Try to import Knowledge Health for response validation
try:
    from knowledge_health import validate_response as kh_validate_response, BUSINESS_RULES
    KNOWLEDGE_HEALTH_AVAILABLE = True
except ImportError:
    KNOWLEDGE_HEALTH_AVAILABLE = False
    logger.debug("Knowledge health not available")

# Try to import Production Guardrails (P0 fix - NeMo-style guardrails)
try:
    from guardrails import (
        get_guardrails, check_input, check_output, 
        evaluate_response_quality, GuardrailAction
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    logger.debug("Production guardrails not available")

# Try to import NLU Processor (P2 fix - spaCy-based NLU)
try:
    from nlu_processor import get_nlu_processor, NLUResult, Intent
    NLU_AVAILABLE = True
except ImportError:
    NLU_AVAILABLE = False
    logger.debug("NLU processor not available")

# Quality tracking for consolidated knowledge
try:
    from qdrant_retriever import (
        get_consolidated_knowledge_ids, 
        record_feedback_for_citations,
        record_knowledge_feedback
    )
    QUALITY_TRACKING_AVAILABLE = True
except ImportError:
    QUALITY_TRACKING_AVAILABLE = False
    logger.debug("Quality tracking not available")
    def get_consolidated_knowledge_ids(citations): return []
    def record_feedback_for_citations(citations, was_helpful): return 0
    def record_knowledge_feedback(knowledge_id, was_helpful): return False


# =============================================================================
# IRA'S PERSONALITY
# =============================================================================

IRA_OPENERS = [
    "🎯 Right then.",
    "📋 Here's what I've got.",
    "💡 Let me walk you through this.",
    "🔍 Ah, this is interesting.",
]

IRA_CLOSERS = [
    "Make sense? 🤔",
    "Want me to dig deeper? 🔍",
    "Your move! 💬",
    "Need anything else? 💡",
]

IRA_DRY_HUMOR = [
    "Not to be dramatic, but",
    "Shocking, I know. 😏",
    "As one does.",
]

EMOTIONAL_OPENERS = {
    "positive": ["🎉 That's great to hear!", "✨ Excellent!", "💯 Love it."],
    "stressed": ["🤝 I hear you - let's tackle this together.", "✅ Understood. Let me help."],
    "frustrated": ["🙏 I completely understand.", "⚡ That's not good - let's fix this."],
    "curious": ["💡 Good question!", "📚 Let me explain."],
    "urgent": ["⚡ On it.", "🚀 Let's move quickly."],
    "grateful": ["😊 Happy to help!", "✅ Glad it worked out."],
    "uncertain": ["💡 Let me clarify.", "👍 No worries, I'll explain."],
}


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

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


# =============================================================================
# RESPONSE GENERATION WITH REPLIKA ENHANCEMENTS
# =============================================================================

def _apply_personality(
    text: str,
    confidence: str = "high",
    channel: str = "telegram",
    emotional_state: Optional[str] = None,
    warmth: str = "stranger"
) -> str:
    """
    Apply Ira's personality to response text.
    Now with emotional calibration from Replika integration.
    """
    parts = []
    
    # Emotional opener takes priority if detected
    if emotional_state and emotional_state != "neutral":
        openers = EMOTIONAL_OPENERS.get(emotional_state, [])
        if openers:
            parts.append(random.choice(openers))
            parts.append("")
    elif channel in ["telegram"] and warmth in ["trusted", "warm"]:
        # Warmer relationships get more personality
        if random.random() < 0.3:
            parts.append(random.choice(IRA_OPENERS))
            parts.append("")
    
    parts.append(text)
    
    # Add closer for telegram (not for stressed/urgent)
    if channel == "telegram" and emotional_state not in ["urgent", "stressed", "frustrated"]:
        if random.random() < 0.3:
            parts.append("")
            parts.append(random.choice(IRA_CLOSERS))
    
    return "\n".join(parts)


def _detect_mem0_rag_conflict(mem0_context: str, rag_chunks: list) -> str:
    """
    P1 Audit: Detect when Mem0 and RAG disagree on same fact (e.g. price).
    Returns conflict instruction string if conflict found, else "".
    """
    if not mem0_context or not rag_chunks:
        return ""
    mem0_str = (mem0_context or "")
    rag_text = " ".join(c.get("text", "") for c in (rag_chunks or [])[:5])
    # Extract (model, price) from mem0
    mem0_matches = re.findall(
        r"(FCS[-\s]?\d+|PF1[-\s]?[A-Z]?[-\s]?\d{4}|AM[-\s]?\d{4})[^$€₹]*(?:[$€₹]|Rs\.?|INR)\s*([\d,]+)",
        mem0_str,
        re.IGNORECASE
    )
    if not mem0_matches:
        return ""
    # Extract (model, price) from RAG
    rag_matches = re.findall(
        r"(FCS[-\s]?\d+|PF1[-\s]?[A-Z]?[-\s]?\d{4}|AM[-\s]?\d{4})[^$€₹]*(?:[$€₹]|Rs\.?|INR)\s*([\d,]+)",
        rag_text,
        re.IGNORECASE
    )
    for m_model, m_price in mem0_matches[:3]:
        m_norm = re.sub(r"[\s-]", "", m_model.upper())
        m_val = m_price.replace(",", "")
        for r_model, r_price in rag_matches[:5]:
            r_norm = re.sub(r"[\s-]", "", r_model.upper())
            r_val = r_price.replace(",", "")
            if m_norm == r_norm and m_val != r_val:
                                return (
                    "\n\n=== SOURCE CONFLICT (P1 Audit) ===\n"
                    "PERSONAL MEMORY and DOCUMENTS disagree on the same fact (e.g. price). "
                    "CITE BOTH SOURCES. Do NOT synthesize a compromise value. "
                    "Say: 'My memory says X; our documents say Y. Please confirm with sales.'\n"
                    "=== END CONFLICT ===\n\n"
                )
    return ""


def _estimate_tokens(text: str) -> int:
    """P2 Audit: Approximate token count (~4 chars/token for OpenAI)."""
    if not text:
        return 0
    return len(text) // 4

def _build_system_prompt(
    context_pack: ContextPack,
    channel: str,
    conversational_enhancement: Optional[Dict] = None,
    truth_hint: Optional[Any] = None,
    intent: str = ""
) -> str:
    """
    Build system prompt with Replika-inspired enhancements.
    Uses SOUL.md if available for identity definition.
    """
    # Use SOUL.md content if available, otherwise use default
    if context_pack.soul_context:
        base_prompt = context_pack.soul_context + "\n\n"
        base_prompt += """ADDITIONAL PERSONALITY:
- Confident but not arrogant
- Analytical (MBB consulting style)
- Occasionally dry British humor
- Genuinely helpful

RESPONSE STYLE:
- Be conversational, not robotic
- Match the user's energy level
- Keep responses focused and useful
"""
    else:
        base_prompt = """You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies (India).
Machinecraft manufactures thermoforming machines since 1976.

PERSONALITY:
- Confident but not arrogant
- Analytical (MBB consulting style)
- Occasionally dry British humor
- Genuinely helpful

RESPONSE STYLE:
- Be conversational, not robotic
- Match the user's energy level
- Keep responses focused and useful
"""

    # =========================================================================
    # ATHENA COACHING (2026-02-28) - Critical style improvements
    # Based on analysis of 100 real sales conversations with Rushabh
    # =========================================================================
    base_prompt += """

ATHENA COACHING (CRITICAL - Apply these in EVERY response):

1. WARM GREETING (Apply 100% of the time):
   - START with: "Hi!", "Hey", or "Hi there" 
   - NEVER use: "Dear", "Greetings", "Hello there"
   - Example: "Hi! Happy to help with that."

2. BE CONCISE (Rushabh's emails are 3-5 sentences):
   - Get to the answer FAST
   - Skip lengthy intros like "Thank you for your inquiry about..."
   - Target: 100-150 words for simple queries
   - If you're over 200 words, you're too verbose

3. ACTION LANGUAGE (Be proactive, not passive):
   - USE: "Let me...", "I'll...", "Let's..."
   - AVOID: "Please find attached", "You may want to consider"
   - Example: "Let me send you the specs" NOT "Please find the specs attached"

4. WARMTH PHRASES (Use naturally):
   - "Happy to help!", "Sounds good", "No problem", "Sure thing"
   - Sprinkle these in - Rushabh is warm but direct

5. CALL-TO-ACTION (End every response with one):
   - Short CTAs: "Let me know.", "Questions?", "Make sense?"
   - Avoid: Long closing paragraphs

EXAMPLE OF GOOD RESPONSE:
"Hi! Happy to help.

For your 2000x2000mm requirement, the PF1-C-2020 is the best fit. Price is EUR 180,000 EXW, 4-month lead time.

Let me know if you want the detailed specs."

EXAMPLE OF BAD RESPONSE (TOO FORMAL/LONG):
"Dear Sir/Madam, Thank you for your interest in Machinecraft Technologies' thermoforming solutions. We are pleased to provide you with information regarding your inquiry. Our PF1 series..."

6. FORMATTING DISCIPLINE (CRITICAL):
   - Write in natural flowing prose, like a real person
   - Bold (**text**) is ONLY for machine model names (e.g. **PF1-C-2020**) — nothing else
   - Do NOT bold section headers, adjectives, phrases, or emphasis words
   - Do NOT create formatted "report-style" responses with headers and sections
   - Bullet points only for listing 3+ comparable items (e.g. specs, options)
   - No emoji spam — one per message max, zero is fine
   - If the response reads like a formatted document, rewrite it as a conversation
"""
    
    # =========================================================================
    # IDENTITY-AWARE CONTEXT - Adjust behavior based on who you're talking to
    # =========================================================================
    if context_pack.identity:
        user_name = context_pack.identity.get("name", "")
        user_role = context_pack.identity.get("role", "")
        
        if user_name:
            base_prompt += f"\n\nYOU ARE TALKING TO: {user_name}"
            if user_role:
                base_prompt += f" ({user_role.upper()})"
            base_prompt += "\n"
        
        if context_pack.is_internal:
            base_prompt += """
INTERNAL USER MODE:
- This is a Machinecraft team member. Be direct and transparent.
- Share internal information, metrics, and strategies freely.
- No need for sales pitch - they know the products.
- You can discuss financials, margins, pipeline, and sensitive data.
- If they ask about the company, give insider details not public info.
"""
            if user_role == "founder":
                base_prompt += """
FOUNDER MODE:
- You're talking to the boss! Be respectful but direct.
- Give unfiltered insights and honest assessments.
- Share concerns, risks, and opportunities openly.
- They have full access to everything - no information restrictions.
- Help them make decisions, don't hedge or be vague.
"""
    else:
        # External user - default sales/support mode
        base_prompt += """
EXTERNAL USER MODE:
- This appears to be an external contact (customer, prospect, or visitor).
- Be helpful but protect sensitive internal information.
- Focus on product benefits and customer value.
"""
    
    # =========================================================================
    # QUERY UNDERSTANDING - What they're asking for (Phase 0.5)
    # =========================================================================
    if context_pack.query_analysis_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nQUERY UNDERSTANDING"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.query_analysis_context}"
    elif context_pack.query_intent:
        base_prompt += f"\n\nDETECTED INTENT: {context_pack.query_intent}"
        if context_pack.query_entities:
            entities_str = ", ".join([f"{k}: {v}" for k, v in context_pack.query_entities.items() if v])
            if entities_str:
                base_prompt += f"\nEXTRACTED ENTITIES: {entities_str}"
        if context_pack.query_constraints:
            constraints_str = ", ".join([f"{c.get('type', '')}: {c.get('value', '')}" for c in context_pack.query_constraints])
            if constraints_str:
                base_prompt += f"\nCONSTRAINTS: {constraints_str}"
    
    # Response length guidance - Dynamic based on query complexity
    # This is critical for user experience - don't write essays for simple questions
    response_length = context_pack.suggested_response_length or "medium"
    length_guidance = {
        "short": (
            "RESPONSE LENGTH: KEEP IT SHORT (100-200 words max)\n"
            "- Answer directly and concisely\n"
            "- Skip lengthy explanations or context\n"
            "- One or two key points only\n"
            "- Good for: greetings, yes/no, single facts, clarifications"
        ),
        "medium": (
            "RESPONSE LENGTH: MODERATE (300-500 words)\n"
            "- Provide a balanced response with key details\n"
            "- Include relevant specs or context\n"
            "- Good for: standard queries, single machine info, comparisons"
        ),
        "long": (
            "RESPONSE LENGTH: COMPREHENSIVE (600-1000 words)\n"
            "- Provide detailed technical information\n"
            "- Include tables, comparisons, and full context\n"
            "- Address all aspects of complex queries\n"
            "- Good for: multi-machine comparisons, detailed recommendations"
        ),
        "very_long": (
            "RESPONSE LENGTH: EXTENSIVE (1000+ words)\n"
            "- Full technical deep-dive with all relevant details\n"
            "- Include comprehensive tables and specifications\n"
            "- Address all edge cases and considerations\n"
            "- Good for: complex RFQ responses, detailed proposals"
        ),
    }.get(response_length, "")
    
    if length_guidance:
        base_prompt += f"\n\n{'=' * 40}\n{length_guidance}\n{'=' * 40}"
    
    # =========================================================================
    # CUSTOMER CONTEXT - Who you're speaking to (Phase 0.7)
    # =========================================================================
    if context_pack.customer_context_formatted:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nCUSTOMER PROFILE"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.customer_context_formatted}"
    elif context_pack.customer_name or context_pack.customer_company:
        base_prompt += "\n\nCUSTOMER INFO:"
        if context_pack.customer_name:
            base_prompt += f"\n- Name: {context_pack.customer_name}"
        if context_pack.customer_company:
            base_prompt += f"\n- Company: {context_pack.customer_company}"
        if context_pack.customer_role:
            base_prompt += f"\n- Role: {context_pack.customer_role}"
        if context_pack.customer_relationship and context_pack.customer_relationship != "unknown":
            base_prompt += f"\n- Relationship: {context_pack.customer_relationship}"
    
    # Customer communication style instructions
    if context_pack.customer_style_instructions:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nCOMMUNICATION STYLE GUIDANCE"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.customer_style_instructions}"
    elif context_pack.customer_style and context_pack.customer_style not in ["default", "unknown"]:
        style_guidance = {
            "technical_detailed": "This customer prefers detailed technical explanations with specifications.",
            "technical_concise": "This customer prefers brief, technical responses without lengthy explanations.",
            "business_formal": "Use professional, formal business language. Focus on value propositions.",
            "casual_friendly": "Be warm and conversational while remaining professional.",
            "executive_brief": "Keep it brief and executive-summary style. Lead with conclusions.",
        }.get(context_pack.customer_style, "")
        if style_guidance:
            base_prompt += f"\n\nSTYLE GUIDANCE: {style_guidance}"
    
    # Add conversation context (last 8 messages, 600 chars each for continuity)
    if context_pack.recent_messages:
        base_prompt += "\n\nCONVERSATION HISTORY (use this to maintain continuity — reference prior messages when user says 'above', 'that', 'the ones you mentioned', etc.):\n"
        for msg in context_pack.recent_messages[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:600]
            base_prompt += f"{role.upper()}: {content}\n"
    
    # P1 Audit: conflict detection between Mem0 and RAG
    conflict_instruction = _detect_mem0_rag_conflict(
        getattr(context_pack, "mem0_context", "") or "",
        getattr(context_pack, "rag_chunks", []) or []
    )
    if conflict_instruction:
        base_prompt += conflict_instruction

    # Add RAG context — use more chunks with more text for grounded answers
    if context_pack.rag_chunks:
        base_prompt += "\n\nRELEVANT KNOWLEDGE (use this to ground your response — do NOT contradict these facts). Only state facts explicitly present in the provided text. If information is missing, say 'Not specified in the document.':\n"
        for chunk in context_pack.rag_chunks[:12]:
            base_prompt += f"[{chunk.get('filename', 'unknown')}]: {chunk.get('text', '')[:1500]}\n"
    
    # Add memory guidance (woven context from Memory Weaver)
    if context_pack.memory_guidance:
        # Use structured memory guidance instead of raw dumps
        system_addition = context_pack.memory_guidance.get("system_addition", "")
        if system_addition:
            base_prompt += f"\n{system_addition}"
        
        user_context = context_pack.memory_guidance.get("user_context", "")
        if user_context:
            base_prompt += f"\n\n{user_context}"
        
        response_guidance = context_pack.memory_guidance.get("response_guidance", "")
        if response_guidance:
            base_prompt += f"\n\nMEMORY RESPONSE GUIDANCE:\n{response_guidance}"
    elif context_pack.user_memories:
        # Fallback: raw memory dump if weaver not available
        base_prompt += "\n\nWHAT I REMEMBER ABOUT THIS USER:\n"
        for mem in context_pack.user_memories[:3]:
            base_prompt += f"- {mem.get('memory_text', '')}\n"
    
    # Add entity memories if available (and not already in guidance)
    if context_pack.entity_memories and not context_pack.memory_guidance:
        base_prompt += "\n\nRELEVANT ENTITY KNOWLEDGE:\n"
        for mem in context_pack.entity_memories[:3]:
            entity = mem.get('entity_name', 'Unknown')
            text = mem.get('memory_text', '')
            base_prompt += f"- [{entity}] {text}\n"
    
    # Add memory reasoning trace (inner monologue)
    if context_pack.reasoning_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nMY THOUGHTS BEFORE RESPONDING"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.reasoning_context}"

    # Add meta-cognitive guidance (knowledge state assessment)
    if context_pack.metacognitive_guidance:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nKNOWLEDGE STATE ASSESSMENT"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.metacognitive_guidance}"

    # Add episodic context (temporal history - what happened before)
    if context_pack.episodic_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nPAST INTERACTIONS (What happened before)"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.episodic_context}"
        base_prompt += "\n\nUse this history to provide continuity. Reference past interactions when relevant."
    
    # Add procedural guidance (step-by-step instructions for the task)
    if context_pack.procedure_guidance:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nTASK PROCEDURE (How to handle this)"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.procedure_guidance}"
        base_prompt += "\n\nFollow these steps in order. You may adapt language but preserve the workflow."
    
    # Add Mem0 semantic memory context (AI memory layer - what I remember)
    if context_pack.mem0_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nPERSONAL MEMORY (What I remember about you)"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{context_pack.mem0_context}"
        base_prompt += "\n\nUse these memories naturally to personalize responses. Don't explicitly say 'I remember' unless relevant."

    # Add cross-channel context (email conversations with this contact)
    cross_channel_context = context_pack.extra.get("cross_channel_context", "") if hasattr(context_pack, 'extra') and context_pack.extra else ""
    if not cross_channel_context and isinstance(context_pack, dict):
        cross_channel_context = context_pack.get("cross_channel_context", "")
    
    if cross_channel_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nCROSS-CHANNEL CONTEXT (Recent Email Conversations)"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{cross_channel_context}"
        base_prompt += "\n\nThis contact has also been in email communication. Use this context to:"
        base_prompt += "\n- Provide continuity (reference ongoing discussions if relevant)"
        base_prompt += "\n- Avoid asking questions already answered in email"
        base_prompt += "\n- Acknowledge their inquiry if they're following up on an email topic"
    
    # Add competitor intelligence context if available
    competitor_context = ""
    if hasattr(context_pack, 'competitor_context') and context_pack.competitor_context:
        competitor_context = context_pack.competitor_context
    elif isinstance(context_pack, dict):
        competitor_context = context_pack.get("competitor_context", "")
    
    if competitor_context:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nCOMPETITOR INTELLIGENCE (Strategic Positioning)"
        base_prompt += "\n" + "=" * 40
        base_prompt += f"\n{competitor_context}"

    # =========================================================================
    # REPLIKA-INSPIRED ENHANCEMENTS
    # =========================================================================
    if conversational_enhancement:
        base_prompt += "\n\n" + "=" * 40
        base_prompt += "\nCONVERSATIONAL CALIBRATION\n"
        base_prompt += "=" * 40 + "\n"
        
        # Emotional calibration
        emotional_state = conversational_enhancement.get("emotional_state", "neutral")
        if emotional_state != "neutral":
            calibration_guidance = {
                "positive": "User is in a positive mood. Match their energy. Celebrate with them.",
                "stressed": "User seems stressed. Be calm and reassuring. Acknowledge before solving.",
                "frustrated": "User is frustrated. Validate first, then move quickly to solutions.",
                "curious": "User is curious. Feed their interest. Be generous with information.",
                "urgent": "User needs urgency. Cut pleasantries. Get to the point fast.",
                "grateful": "User is grateful. Accept graciously. Build on the positive moment.",
                "uncertain": "User seems uncertain. Be patient. Break things down clearly.",
            }
            guidance = calibration_guidance.get(emotional_state)
            if guidance:
                base_prompt += f"\nEMOTIONAL STATE: {emotional_state.upper()}\n{guidance}\n"
        
        # Relationship warmth
        warmth = conversational_enhancement.get("warmth", "stranger")
        if warmth in ["trusted", "warm"]:
            base_prompt += f"\nRELATIONSHIP: {warmth.upper()} - Be personable. You have rapport.\n"
        
        # Prompt additions from enhancement
        additions = conversational_enhancement.get("prompt_additions", [])
        for addition in additions[:3]:
            base_prompt += f"\n{addition}"
        
        # Milestones to celebrate
        milestones = conversational_enhancement.get("milestones", [])
        if milestones:
            base_prompt += f"\nMILESTONE TO ACKNOWLEDGE: {milestones[0].get('type', '')}\n"
        
        # Suggested opener
        opener = conversational_enhancement.get("suggested_opener", "")
        if opener:
            base_prompt += f"\nSUGGESTED OPENER: {opener}\n"
        
        base_prompt += "=" * 40 + "\n"
    
    # Add truth hint if available (ground truth for common questions)
    if truth_hint:
        base_prompt += "\n" + "=" * 40
        base_prompt += "\nVERIFIED ANSWER (USE THIS AS GROUND TRUTH)\n"
        base_prompt += "=" * 40 + "\n"
        base_prompt += f"Category: {truth_hint.category}\n"
        base_prompt += f"Answer: {truth_hint.answer}\n"
        base_prompt += "\nUse this verified information as the foundation of your response. "
        base_prompt += "You may rephrase and adapt to context, but maintain accuracy.\n"
        base_prompt += "=" * 40 + "\n"
    
    # Channel-specific guidance
    if channel == "telegram":
        base_prompt += """

TELEGRAM FORMATTING:
- Keep responses concise (max 300 words, shorter is better)
- Write naturally, like a smart colleague texting — not a formatted report
- Use bold sparingly: only for machine model names or one key term per message
  Do NOT bold section headers, do NOT bold every other phrase
- Use bullet points (•) only when listing 3+ items — not for every sentence
- One emoji per message is plenty. Zero is fine too. Never stack emojis.
- No section headers like "Quick Answer" or "Details:" — just talk naturally
- End with a short CTA: "Let me know.", "Questions?", "Make sense?"

GOOD example:
"Hi! For 4mm ABS, the PF1-C-2020 is your best bet — closed chamber, servo drives, handles up to 8mm.

Price is around EUR 180,000 EXW, 12-16 week lead time.

Want the full spec sheet?"

BAD example (too formatted, too many asterisks):
"🎯 **Quick Answer**
Here's what you need to know...

📋 **Details:**
• **Machine:** PF1-C-2020
• **Price:** EUR 180,000
• **Lead time:** 12-16 weeks

💡 **Need more info?** Just ask!"
"""
    else:
        # Add email formatting guidelines
        if EMAIL_STYLING_AVAILABLE:
            base_prompt += "\n" + EMAIL_STYLE_PROMPT
        else:
            base_prompt += "\nProvide thorough responses appropriate for email."
    

    # BRAIN REWIRE INJECTION
    # Load hard rules from brain rewire analysis
    _hard_rules_path = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "brain" / "hard_rules.txt"
    if _hard_rules_path.exists():
        try:
            _hard_rules = _hard_rules_path.read_text().strip()
            if _hard_rules:
                base_prompt += "\n\n" + _hard_rules
                logger.debug("Injected hard rules from brain rewire")
        except Exception as _e:
            logger.warning(f"Failed to load hard rules: {_e}")

    # =========================================================================
    # CONTINUOUS LEARNING INJECTION
    # Inject lessons learned from simulated conversations and stress tests
    # =========================================================================
    if LESSON_INJECTION_AVAILABLE:
        # Use the intent parameter for lesson matching
        query_for_lessons = intent or (context_pack.query_intent if context_pack.query_intent else "")
        
        lesson_prompt = inject_lessons(query_for_lessons)
        if lesson_prompt:
            base_prompt += lesson_prompt
            logger.debug("Injected learned lessons into system prompt")
    
    # =========================================================================
    # TRAINING REINFORCEMENT INJECTION
    # Load weak-area reinforcements + Rushabh's insights from brain training
    # =========================================================================
    _training_weights_path = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "brain" / "training_weights.json"
    if _training_weights_path.exists():
        try:
            _tw = json.loads(_training_weights_path.read_text())
            _inject_lines = []

            _reinforcements = _tw.get("reinforcements", [])
            if _reinforcements:
                _inject_lines.append("\nTRAINING REINFORCEMENT (facts Rushabh flagged — pay extra attention):")
                for _r in _reinforcements[:10]:
                    _inject_lines.append(f"  - {_r['fact']}")

            _insights = _tw.get("rushabh_insights", [])
            if _insights:
                _inject_lines.append("\nRUSHABH'S INSIGHTS (from training commentary):")
                for _ins in _insights[:8]:
                    _inject_lines.append(f"  - Context: {_ins['context'][:80]}... Insight: {_ins['insight'][:150]}")

            if _inject_lines:
                base_prompt += "\n".join(_inject_lines)
                logger.debug("Injected %d training reinforcements + %d insights", len(_reinforcements), len(_insights))
        except Exception as _e:
            logger.warning(f"Failed to load training weights: {_e}")

    # P2 Audit: token budget (~128K for gpt-4o)
    _tok = _estimate_tokens(base_prompt)
    if _tok > 90000:
        logger.warning("P2 token budget: prompt ~%d tokens, truncating", _tok)
        base_prompt = base_prompt[:360000] + "\n\n[Context truncated for token budget]"
    return base_prompt


def _call_llm(prompt: str, user_message: str, model: str = "gpt-4o-mini", max_tokens: int = 800) -> str:
    """Call OpenAI API with resilience."""
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        def do_completion():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=max_tokens,
                temperature=0.4
            )
        
        # Apply circuit breaker if available
        if RESILIENCE_AVAILABLE:
            try:
                response, used_fallback = openai_breaker.execute(
                    do_completion,
                    fallback_result=None
                )
                if used_fallback or response is None:
                    track_warning("generate_answer", "OpenAI unavailable, using fallback response")
                    return "I'm experiencing connectivity issues with my language model. Please try again in a moment."
            except Exception as e:
                track_error("generate_answer", e, {"operation": "llm_call", "model": model})
                return f"I'm having trouble generating a response right now. Error: {str(e)[:100]}"
        else:
            response = do_completion()
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        track_error("generate_answer", e, {"operation": "llm_call", "model": model})
        return f"I'm having trouble generating a response right now. Error: {str(e)[:100]}"


# =============================================================================
# MULTI-PASS RELIABILITY PIPELINE
# =============================================================================

@dataclass
class FactualClaim:
    """A factual claim extracted from response text."""
    claim_type: str  # "price", "spec", "dimension", "feature", "date"
    claim_text: str
    entity: Optional[str] = None  # Machine model if applicable
    value: Optional[str] = None
    context: str = ""


@dataclass
class FactCorrection:
    """A correction for a factual claim."""
    original_claim: str
    corrected_value: str
    correction_reason: str
    confidence: float = 1.0
    source: str = "database"


def extract_and_verify_facts(
    draft_text: str,
    machines_context: List[Dict] = None
) -> Tuple[List[FactualClaim], List[FactCorrection]]:
    """
    PASS 2: Extract factual claims from draft and verify against database.
    
    This is the core of the reliability pipeline:
    1. Use LLM to extract all factual claims (prices, specs, dimensions)
    2. Query the machine database to verify each claim
    3. Return list of corrections needed
    
    Args:
        draft_text: The draft response to verify
        machines_context: List of machines mentioned in context
    
    Returns:
        (claims, corrections) - all extracted claims and any corrections needed
    """
    claims = []
    corrections = []
    
    if not MACHINE_DB_AVAILABLE:
        logger.warning("Machine database not available for fact verification")
        return claims, corrections
    
    # Extract claims using regex patterns (faster than LLM for structured data)
    
    # Price claims (INR)
    price_pattern = r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|L|lakh)?'
    for match in re.finditer(price_pattern, draft_text, re.IGNORECASE):
        price_str = match.group(1).replace(',', '')
        context_start = max(0, match.start() - 150)
        context_end = min(len(draft_text), match.end() + 50)
        context = draft_text[context_start:context_end]
        
        claims.append(FactualClaim(
            claim_type="price",
            claim_text=match.group(0),
            value=price_str,
            context=context
        ))
    
    # Dimension claims (forming area)
    dimension_pattern = r'(\d{3,4})\s*[x×]\s*(\d{3,4})\s*(?:mm)?'
    for match in re.finditer(dimension_pattern, draft_text):
        context_start = max(0, match.start() - 150)
        context_end = min(len(draft_text), match.end() + 50)
        context = draft_text[context_start:context_end]
        
        claims.append(FactualClaim(
            claim_type="dimension",
            claim_text=match.group(0),
            value=f"{match.group(1)} x {match.group(2)}",
            context=context
        ))
    
    # Power spec claims (kW)
    power_pattern = r'(\d+(?:\.\d+)?)\s*(?:kW|KW|kilowatt)'
    for match in re.finditer(power_pattern, draft_text):
        context_start = max(0, match.start() - 150)
        context_end = min(len(draft_text), match.end() + 50)
        context = draft_text[context_start:context_end]
        
        claims.append(FactualClaim(
            claim_type="spec",
            claim_text=match.group(0),
            value=match.group(1),
            context=context
        ))
    
    # Vacuum pump claims (m³/hr)
    vacuum_pattern = r'(\d+)\s*m[³3]/hr'
    for match in re.finditer(vacuum_pattern, draft_text):
        context_start = max(0, match.start() - 150)
        context_end = min(len(draft_text), match.end() + 50)
        context = draft_text[context_start:context_end]
        
        claims.append(FactualClaim(
            claim_type="vacuum",
            claim_text=match.group(0),
            value=match.group(1),
            context=context
        ))
    
    # Model number extraction
    model_pattern = r'(PF1-[A-Z]-\d{4}|PF2-[A-Z]\d{4}|AM-[A-Z]?-?\d{4}|IMG[S]?-\d{4})'
    models_mentioned = re.findall(model_pattern, draft_text, re.IGNORECASE)
    models_mentioned = list(set([m.upper() for m in models_mentioned]))
    
    # Verify claims against database
    for claim in claims:
        model_in_context = None
        for model in models_mentioned:
            if model in claim.context.upper():
                model_in_context = model
                break
        
        if not model_in_context:
            continue
        
        machine = get_machine(model_in_context)
        if not machine:
            continue
        
        claim.entity = model_in_context
        
        # Verify price claims
        if claim.claim_type == "price" and machine.price_inr:
            try:
                claimed_price = float(claim.value)
                if claimed_price < 100000:
                    claimed_price = claimed_price * 100000
                
                expected_price = machine.price_inr
                tolerance = expected_price * 0.05
                
                if abs(claimed_price - expected_price) > tolerance:
                    corrections.append(FactCorrection(
                        original_claim=claim.claim_text,
                        corrected_value=f"₹{expected_price:,}",
                        correction_reason=f"Price for {model_in_context} is ₹{expected_price:,} (claimed: {claim.claim_text})",
                        source="machine_database"
                    ))
            except (ValueError, TypeError):
                pass
        
        # Verify dimension claims
        elif claim.claim_type == "dimension" and machine.forming_area_raw:
            dims = claim.value.split(" x ")
            if len(dims) == 2:
                try:
                    claimed_w, claimed_h = int(dims[0]), int(dims[1])
                    expected_w, expected_h = machine.forming_area_raw
                    
                    matches_normal = abs(claimed_w - expected_w) < 50 and abs(claimed_h - expected_h) < 50
                    matches_rotated = abs(claimed_w - expected_h) < 50 and abs(claimed_h - expected_w) < 50
                    
                    if not (matches_normal or matches_rotated):
                        corrections.append(FactCorrection(
                            original_claim=claim.claim_text,
                            corrected_value=f"{expected_w} x {expected_h} mm",
                            correction_reason=f"Forming area for {model_in_context} is {expected_w} x {expected_h} mm",
                            source="machine_database"
                        ))
                except (ValueError, TypeError):
                    pass
        
        # Verify power claims
        elif claim.claim_type == "spec" and machine.heater_power_kw:
            try:
                claimed_kw = float(claim.value)
                expected_kw = machine.heater_power_kw
                
                if abs(claimed_kw - expected_kw) > 5:
                    corrections.append(FactCorrection(
                        original_claim=claim.claim_text,
                        corrected_value=f"{int(expected_kw)} kW",
                        correction_reason=f"Heater power for {model_in_context} is {int(expected_kw)} kW",
                        source="machine_database"
                    ))
            except (ValueError, TypeError):
                pass
        
        # Verify vacuum claims
        elif claim.claim_type == "vacuum" and machine.vacuum_pump_capacity:
            try:
                claimed_vacuum = int(claim.value)
                expected_match = re.search(r'(\d+)', machine.vacuum_pump_capacity)
                if expected_match:
                    expected_vacuum = int(expected_match.group(1))
                    
                    if abs(claimed_vacuum - expected_vacuum) > 20:
                        corrections.append(FactCorrection(
                            original_claim=claim.claim_text,
                            corrected_value=f"{expected_vacuum} m³/hr",
                            correction_reason=f"Vacuum pump for {model_in_context} is {expected_vacuum} m³/hr",
                            source="machine_database"
                        ))
            except (ValueError, TypeError):
                pass
    
    return claims, corrections


def _generate_draft(
    intent: str,
    system_prompt: str,
    model: str = "gpt-4o-mini"
) -> str:
    """
    PASS 1: Generate comprehensive draft response.
    
    This generates a detailed, comprehensive draft based on:
    - The user's query (intent)
    - System prompt with all context (RAG, memories, etc.)
    
    The draft may contain factual errors that will be corrected in Pass 2.
    """
    return _call_llm(system_prompt, intent, model=model, max_tokens=1000)


def _polish_with_corrections(
    draft: str,
    corrections: List[FactCorrection],
    intent: str,
    channel: str = "telegram"
) -> str:
    """
    PASS 3: Polish the draft by incorporating corrections.
    
    Takes the original draft and list of corrections and produces
    a polished, accurate final response.
    """
    if not corrections:
        return draft
    
    # Build correction instructions
    corrections_text = "\n".join([
        f"- WRONG: {c.original_claim} → CORRECT: {c.corrected_value} ({c.correction_reason})"
        for c in corrections
    ])
    
    polish_prompt = f"""You are revising a draft response to fix factual errors.

CORRECTIONS TO APPLY:
{corrections_text}

INSTRUCTIONS:
1. Apply ALL corrections listed above
2. Maintain the same tone, structure, and helpful nature of the original
3. Do not add new information - only fix the errors
4. The final output must be accurate and well-written
5. Keep the response {'concise (max 400 words)' if channel == 'telegram' else 'thorough'}

Revise the following draft to incorporate these corrections:

ORIGINAL DRAFT:
{draft}

Return ONLY the revised response, no explanations."""

    polished = _call_llm(
        "You are Ira, a precise technical assistant. Apply the corrections exactly as specified.",
        polish_prompt,
        model="gpt-4o-mini",
        max_tokens=1000
    )
    
    return polished if polished and not polished.startswith("I'm having trouble") else draft


def _validate_business_rules(
    query: str,
    response: str
) -> Tuple[bool, List[str]]:
    """
    Validate response against business rules before sending.
    
    Uses knowledge_health.py validation if available, otherwise
    performs basic rule checks.
    
    Returns:
        (is_valid, list_of_warnings)
    """
    warnings = []
    
    if KNOWLEDGE_HEALTH_AVAILABLE:
        is_safe, kh_warnings = kh_validate_response(query, response)
        return is_safe, kh_warnings
    
    # Fallback: basic rule checks
    query_lower = query.lower()
    response_lower = response.lower()
    
    # Rule: AM Series thickness limit (max 1.5mm) - CRITICAL RULE
    # AM Series is for thin gauge ONLY. This is a hard rule.
    if ("am" in response_lower or "am-" in response_lower or "am " in response_lower):
        # Check for thick materials (>1.5mm means 2mm+)
        # Multiple patterns to catch various phrasings
        thick_patterns = [
            r'([2-9]|1[0-9])\s*mm\s*(?:thick|sheet)',           # "5mm thick" or "5mm sheet"
            r'thick.*?([2-9]|1[0-9])\s*mm',                      # "thick 5mm"
            r'([2-9]|1[0-9])\s*mm\s+(abs|pmma|pc|petg|hips|pvc|tpo)', # "5mm ABS"
            r'(abs|pmma|pc|petg|hips|pvc).*?([2-9]|1[0-9])\s*mm', # "ABS 5mm"
            r'up\s*to\s*([2-9]|1[0-9])\s*mm',                    # "up to 5mm"
        ]
        combined_text = query_lower + " " + response_lower
        for pattern in thick_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                warnings.append("Business rule violation: AM Series Thickness Limit - AM Series can only handle material thickness ≤1.5mm. For thickness >1.5mm, recommend PF1 or PF2 Series.")
                break
    
    # Rule: Prices must be specific (no placeholders)
    placeholder_patterns = [r'\[insert.*\]', r'\[.*price.*\]', r'contact.*for.*pricing']
    for pattern in placeholder_patterns:
        if re.search(pattern, response_lower):
            warnings.append("Business rule violation: Response contains placeholder or deflects pricing when data may be available.")
    
    # Rule: Heavy gauge requires PF1
    if re.search(r'([3-9]|1[0-9])\s*mm.*thick|heavy.*gauge', query_lower):
        if not re.search(r'pf[-\s]?1', response_lower):
            warnings.append("Business rule: Heavy gauge (>2mm) should recommend PF1 Series.")
    
    is_valid = len(warnings) == 0
    return is_valid, warnings


def _run_multi_pass_pipeline(
    intent: str,
    system_prompt: str,
    context_pack: Any,
    channel: str = "telegram"
) -> Tuple[str, Dict[str, Any]]:
    """
    Execute the 3-pass reliability pipeline.
    
    Pass 1: Draft Generation
    Pass 2: Fact Extraction & Verification  
    Pass 3: Final Polish with corrections
    
    Returns:
        (final_response, debug_info)
    """
    debug_info = {
        "pipeline_used": True,
        "pass1_draft_generated": False,
        "pass2_facts_checked": False,
        "pass2_claims_found": 0,
        "pass2_corrections_made": 0,
        "pass3_polished": False,
        "business_rules_validated": False,
        "business_rule_warnings": [],
    }
    
    # PASS 1: Generate Draft
    logger.debug("Multi-pass pipeline: Generating draft (Pass 1)")
    draft = _generate_draft(intent, system_prompt)
    debug_info["pass1_draft_generated"] = True
    
    if draft.startswith("I'm having trouble"):
        return draft, debug_info
    
    # PASS 2: Fact Extraction & Verification
    logger.debug("Multi-pass pipeline: Verifying facts (Pass 2)")
    machines_context = context_pack.rag_chunks if hasattr(context_pack, 'rag_chunks') else []
    
    claims, corrections = extract_and_verify_facts(draft, machines_context)
    debug_info["pass2_facts_checked"] = True
    debug_info["pass2_claims_found"] = len(claims)
    debug_info["pass2_corrections_made"] = len(corrections)
    
    if corrections:
        debug_info["corrections"] = [
            {"original": c.original_claim, "corrected": c.corrected_value, "reason": c.correction_reason}
            for c in corrections
        ]
        logger.info(f"Multi-pass pipeline: Found {len(corrections)} corrections needed")
    
    # PASS 3: Polish with Corrections
    if corrections:
        logger.debug("Multi-pass pipeline: Polishing with corrections (Pass 3)")
        final_response = _polish_with_corrections(draft, corrections, intent, channel)
        debug_info["pass3_polished"] = True
    else:
        final_response = draft
        debug_info["pass3_polished"] = False
    
    # FINAL VALIDATION: Business Rules
    logger.debug("Multi-pass pipeline: Validating business rules")
    is_valid, warnings = _validate_business_rules(intent, final_response)
    debug_info["business_rules_validated"] = True
    debug_info["business_rule_warnings"] = warnings
    
    if warnings:
        logger.warning(f"Business rule warnings: {warnings}")
        # Add a note and correction if AM series thickness violation detected
        if any("AM Series" in w for w in warnings):
            # This is a critical error - AM series can only handle ≤1.5mm
            # Replace any AM recommendation with PF1 recommendation
            if "am-" in final_response.lower() or "am series" in final_response.lower():
                # Add strong correction note
                final_response += "\n\n**⚠️ Important Correction:** The AM Series is designed for thin-gauge materials (≤1.5mm thickness only). For your requirement of thicker sheets, the **PF1 Series** is the appropriate choice. The PF1 offers closed-chamber, heavy-gauge forming capability for materials up to 10mm."
                logger.info("Applied AM Series thickness correction to response")
    
    return final_response, debug_info


def _check_grounding(
    response: str,
    rag_chunks: List[Dict],
    truth_hint: Optional[Any],
    query: str
) -> tuple:
    """
    Check if response is grounded in the provided context.
    
    Returns:
        (score: float, reason: str) where score is 0-1
    """
    if not response:
        return 0.0, "Empty response"
    
    # If we have a truth hint and response matches it, high confidence
    if truth_hint:
        hint_keywords = truth_hint.answer.lower().split()[:10]
        response_lower = response.lower()
        matches = sum(1 for kw in hint_keywords if kw in response_lower and len(kw) > 3)
        if matches >= 3:
            return 0.95, "Response matches verified truth hint"
    
    # No RAG chunks = can't verify grounding
    if not rag_chunks:
        # Check for hallucination indicators
        hallucination_patterns = [
            "pf1-300", "pf1-400", "pf1-500", "pf1-600", "pf1-700",  # Fake model numbers
            "re-300", "re-400", "re-500", "re-600",  # Fake RE models
            "starting from $", "typically costs", "generally priced",  # Vague pricing
        ]
        response_lower = response.lower()
        for pattern in hallucination_patterns:
            if pattern in response_lower:
                return 0.2, f"Potential hallucination detected: {pattern}"
        
        return 0.4, "No RAG context to verify against"
    
    # Extract key terms from chunks
    chunk_text = " ".join([c.get("text", "")[:500] for c in rag_chunks]).lower()
    
    # Check for specific facts in response that should be in chunks
    response_lower = response.lower()
    
    # Extract numbers and model names from response
    import re
    response_numbers = set(re.findall(r'\d{3,}', response))
    chunk_numbers = set(re.findall(r'\d{3,}', chunk_text))
    
    # Model names mentioned in response
    model_patterns = re.findall(r'pf\d?-?\d+|am-?\d+|re-?\d+', response_lower)
    chunk_models = re.findall(r'pf\d?-?\d+|am-?\d+|re-?\d+', chunk_text)
    
    # Calculate grounding score
    score = 0.5  # Base score for having context
    
    # Bonus for numbers that appear in both
    if response_numbers and chunk_numbers:
        overlap = len(response_numbers & chunk_numbers)
        if overlap > 0:
            score += 0.2
    
    # Bonus for model names in chunks
    if model_patterns:
        models_grounded = sum(1 for m in model_patterns if m in chunk_text)
        if models_grounded == len(model_patterns):
            score += 0.2
        elif models_grounded > 0:
            score += 0.1
        else:
            score -= 0.2  # Penalty for ungrounded model names
    
    # Check for known hallucination patterns
    fake_models = ["pf1-300", "pf1-400", "pf1-500", "pf1-600", "pf1-700", "pf1-800"]
    for fake in fake_models:
        if fake in response_lower and fake not in chunk_text:
            return 0.2, f"Hallucinated model number: {fake}"
    
    # Cap score
    score = min(score, 1.0)
    
    if score >= 0.7:
        reason = "Response appears well-grounded in context"
    elif score >= 0.5:
        reason = "Response partially grounded in context"
    else:
        reason = "Response may contain unverified information"
    
    return score, reason


def _add_uncertainty_marker(response: str, reason: str) -> str:
    """Add uncertainty marker to poorly grounded response."""
    # Don't add marker if response already has caveats
    caveat_indicators = [
        "i'm not sure", "i don't have", "i couldn't find",
        "based on available", "please verify", "contact us"
    ]
    if any(ind in response.lower() for ind in caveat_indicators):
        return response
    
    # Add a subtle caveat
    caveat = "\n\n_Note: Please verify specific details with our sales team._"
    return response + caveat


def _extract_quote_params(message: str) -> dict:
    """
    Extract quote parameters from a message.
    
    Returns dict with forming_size, variant, materials if found.
    """
    import re
    params = {}
    
    # Extract forming size (e.g., "2000x1500", "2000 x 1500", "2m x 1.5m")
    size_patterns = [
        r'(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*(?:mm)?',  # 2000x1500 or 2000 x 1500
        r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*m(?:eter|m)?',  # 2 x 1.5 m
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, message)
        if match:
            w, h = float(match.group(1)), float(match.group(2))
            if w < 100 and h < 100:
                w, h = int(w * 1000), int(h * 1000)
            else:
                w, h = int(w), int(h)
            params["forming_size"] = (w, h)
            break
    
    # Extract variant
    if "servo" in message.lower() or "pf1-x" in message.lower():
        params["variant"] = "X"
    elif "pneumatic" in message.lower() or "pf1-c" in message.lower():
        params["variant"] = "C"
    elif "automatic" in message.lower() or "autoload" in message.lower():
        params["variant"] = "X"
    
    # Extract materials
    materials = []
    material_list = ["hdpe", "abs", "pp", "ps", "pvc", "pmma", "pc", "pet", "petg", "tpo", "hips"]
    for mat in material_list:
        if mat in message.lower():
            materials.append(mat.upper())
    if materials:
        params["materials"] = materials
    
    return params


def _try_generate_quote(message: str, channel: str = "telegram") -> str:
    """
    Try to generate a quote if enough info is in the message.
    
    Returns formatted quote string or empty string if not enough info.
    """
    if not QUOTE_AVAILABLE:
        return ""
    
    params = _extract_quote_params(message)
    
    if "forming_size" not in params:
        return ""
    
    try:
        quote = generate_quote(
            forming_size=params["forming_size"],
            variant=params.get("variant", "C"),
            materials=params.get("materials"),
        )
        
        if channel == "telegram":
            return format_quote_telegram(quote, compact=True)
        else:
            return format_quote_email(quote, tone="professional")
    except Exception as e:
        logger.warning(f"Quote generation failed: {e}")
        return ""


def generate_pdf_quote_for_customer(
    customer_id: str,
    machine_id: str,
    quantity: int = 1,
    options: Dict[str, Any] = None,
) -> Optional[str]:
    """
    Generate a PDF quote for a specific customer and machine.
    
    This is triggered when QUOTE_REQUEST intent is detected and 
    sufficient information is available.
    
    Args:
        customer_id: Unified identity customer ID
        machine_id: Machine model (e.g., "PF1-C-2015")
        quantity: Number of machines
        options: Additional options dict
    
    Returns:
        Path to generated PDF or None if generation failed
    """
    if not PDF_QUOTE_AVAILABLE:
        logger.warning("PDF quote generation not available")
        return None
    
    try:
        pdf_path = generate_pdf_quote(
            customer_id=customer_id,
            machine_id=machine_id,
            quantity=quantity,
            options=options,
            generate_pdf=True,
            track_in_crm=True,
        )
        logger.info(f"PDF quote generated: {pdf_path}")
        return pdf_path
    except ValueError as e:
        logger.warning(f"PDF quote generation failed (invalid params): {e}")
        return None
    except Exception as e:
        logger.error(f"PDF quote generation error: {e}")
        return None


def handle_quote_request_intent(
    message: str,
    customer_id: Optional[str] = None,
    channel: str = "telegram",
) -> Tuple[str, Optional[str]]:
    """
    Handle a QUOTE_REQUEST intent by generating appropriate response and PDF.
    
    Args:
        message: The user's message
        customer_id: Customer's identity ID (if known)
        channel: Response channel
    
    Returns:
        Tuple of (response_text, pdf_path or None)
    """
    params = _extract_quote_params(message)
    
    if "forming_size" not in params:
        return ("I'd be happy to prepare a quote for you. Could you please specify the forming area size you need? For example: \"2000 x 1500 mm\"", None)
    
    forming_size = params["forming_size"]
    w_cm = forming_size[0] // 10
    h_cm = forming_size[1] // 10
    w_str = str(w_cm // 10) if w_cm >= 100 else str(w_cm)
    h_str = str(h_cm // 10) if h_cm >= 100 else str(h_cm)
    variant = params.get("variant", "C")
    machine_id = f"PF1-{variant}-{w_str}{h_str}"
    
    text_quote = _try_generate_quote(message, channel)
    
    pdf_path = None
    if customer_id and PDF_QUOTE_AVAILABLE:
        pdf_path = generate_pdf_quote_for_customer(
            customer_id=customer_id,
            machine_id=machine_id,
            quantity=params.get("quantity", 1),
        )
    
    response = text_quote
    if pdf_path:
        response += f"\n\n📄 I've generated a formal PDF quote for you: `{Path(pdf_path).name}`"
        if channel == "telegram":
            response += "\n_I can send this to your email if you'd like._"
    
    return (response, pdf_path)


async def _run_input_guardrails(message: str) -> Tuple[bool, Optional[str], Dict]:
    """
    Run production guardrails on input message.
    
    Returns:
        (allowed, alternative_response, metadata)
    """
    if not GUARDRAILS_AVAILABLE:
        return True, None, {}
    
    try:
        result = await check_input(message)
        return result.allowed, result.alternative_response, {
            "detected_issues": result.detected_issues,
            "guardrails_checked": True,
        }
    except Exception as e:
        logger.warning(f"Input guardrails failed: {e}")
        return True, None, {"guardrails_error": str(e)}


async def _run_output_guardrails(
    response: str,
    context: List[str],
    query: str
) -> Tuple[str, Dict]:
    """
    Run production guardrails on output response.
    
    Returns:
        (verified_response, metadata)
    """
    if not GUARDRAILS_AVAILABLE:
        return response, {}
    
    try:
        result = await check_output(response, context, query)
        
        if result.modified_content:
            verified_response = result.modified_content
        elif not result.allowed and result.alternative_response:
            verified_response = result.alternative_response
        else:
            verified_response = response
        
        return verified_response, {
            "guardrails_action": result.action.value if hasattr(result.action, 'value') else str(result.action),
            "guardrails_warnings": result.warnings,
            "guardrails_confidence": result.confidence,
        }
    except Exception as e:
        logger.warning(f"Output guardrails failed: {e}")
        return response, {"guardrails_error": str(e)}


def _run_nlu_analysis(message: str) -> Optional[NLUResult]:
    """Run NLU analysis on the message if available."""
    if not NLU_AVAILABLE:
        return None
    
    try:
        return get_nlu_processor().process(message)
    except Exception as e:
        logger.warning(f"NLU analysis failed: {e}")
        return None


def generate_answer(
    intent: str,
    context_pack: Optional[Union[ContextPack, Dict]] = None,
    channel: str = "telegram",
    thread_id: str = "",
    use_deep_retrieval: bool = True,
    use_multi_pass: bool = True,
    use_guardrails: bool = True
) -> ResponseObject:
    """
    UNIFIED RESPONSE GENERATOR with Multi-Pass Reliability Pipeline.
    
    This is the main entry point for all response generation.
    
    Implements a 3-pass pipeline (when use_multi_pass=True):
        Pass 1: Draft Generation - Comprehensive draft from query + context
        Pass 2: Fact Extraction & Verification - Verify against database
        Pass 3: Final Polish - Apply corrections and business rules
    
    Additional features (P0-P2 fixes):
        - Production guardrails (input/output validation)
        - spaCy-based NLU for intent/entity extraction
    
    Args:
        intent: The user's message/query
        context_pack: Context including conversation history, RAG chunks, etc.
        channel: "telegram" or "email"
        thread_id: Optional thread ID
        use_deep_retrieval: Whether to use deep retrieval (future)
        use_multi_pass: Whether to use the multi-pass reliability pipeline
        use_guardrails: Whether to use production guardrails (default True)
    
    Returns:
        ResponseObject with response and metadata
    """
    import asyncio
    
    nlu_result = _run_nlu_analysis(intent)
    
    if use_guardrails and GUARDRAILS_AVAILABLE:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            allowed, alt_response, input_meta = loop.run_until_complete(
                _run_input_guardrails(intent)
            )
            
            if not allowed and alt_response:
                return ResponseObject(
                    text=alt_response,
                    mode=ResponseMode.GENERAL,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_reason="Guardrails: blocked input",
                    channel=channel,
                    generation_path="guardrails_blocked",
                    debug_info={
                        "guardrails_blocked": True,
                        **input_meta,
                        "nlu_intent": nlu_result.intent.value if nlu_result else None,
                    }
                )
        except Exception as e:
            logger.warning(f"Guardrails execution failed: {e}")
            input_meta = {"guardrails_error": str(e)}
    else:
        input_meta = {}
    
    # Normalize context_pack
    if context_pack is None:
        context_pack = ContextPack()
    elif isinstance(context_pack, dict):
        context_pack = ContextPack.from_dict(context_pack)
    
    if nlu_result and not context_pack.query_intent:
        context_pack.query_intent = nlu_result.intent.value
        context_pack.query_entities = {
            "machines": nlu_result.get_machine_models(),
            "materials": nlu_result.get_materials(),
            "dimensions": [f"{d[0]}x{d[1]}" for d in nlu_result.get_dimensions()],
        }
        context_pack.query_constraints = [c.to_dict() for c in nlu_result.constraints]
    
    # =========================================================================
    # MACHINE RECOMMENDATION - Use structured database for recommendations
    # =========================================================================
    machine_recommendation = None
    if MACHINE_RECOMMENDER_AVAILABLE:
        # Check if this is a recommendation query (by NLU intent or keywords)
        is_recommendation_query = False
        if nlu_result and hasattr(nlu_result, 'intent'):
            is_recommendation_query = nlu_result.intent.value == "RECOMMENDATION"
        
        # Also check for recommendation keywords
        recommend_keywords = ["recommend", "suggest", "which machine", "suitable", "best for", "need a machine"]
        if any(kw in intent.lower() for kw in recommend_keywords):
            is_recommendation_query = True
        
        # Check for dimension keywords that indicate size-based selection
        if any(kw in intent.lower() for kw in ["x", "size", "mm", "meter", "part"]):
            is_recommendation_query = True
        
        # Check for general machine interest (should trigger qualification)
        machine_interest_keywords = [
            "interested in", "looking for", "need", "want", "require",
            "thermoforming", "vacuum forming", "forming machine",
            "pf1 series", "pf2 series", "inquiry", "enquiry", "quote"
        ]
        if any(kw in intent.lower() for kw in machine_interest_keywords):
            is_recommendation_query = True
        
        # Internal users (founder/team) should never get sales qualification
        # questions. They know the products -- just answer their question.
        if context_pack.is_internal:
            is_recommendation_query = False
        
        if is_recommendation_query:
            # =========================================================================
            # DETERMINISTIC ROUTING - Rule-based series selection (runs before LLM)
            # =========================================================================
            det_route = None
            if DETERMINISTIC_ROUTER_AVAILABLE:
                try:
                    det_route = route_to_series(intent)
                    if det_route and det_route.get("bypass_llm_routing"):
                        logger.info(
                            f"Deterministic routing: {det_route['series']} "
                            f"(confidence: {det_route['confidence']:.2f}, "
                            f"reason: {det_route['reason']})"
                        )
                except Exception as e:
                    logger.warning(f"Deterministic router error: {e}")
                    det_route = None

            # =========================================================================
            # IMG PROCESS DETECTION - Route to IMG series if needed
            # (Also caught by deterministic router, but kept as fallback)
            # =========================================================================
            if SALES_QUALIFIER_AVAILABLE and detect_img_requirement(intent):
                logger.info("Detected IMG process requirement - routing to IMG series")
                # For IMG queries, recommend IMG series directly
                img_response = f"""Hi!

Based on your requirements for TPO forming with grain retention, you need our **IMG Series** (In-Mold Graining) machines.

The IMG series is specifically designed for:
• TPO/PP composite forming with grain texture retention
• Class-A automotive interior surfaces
• High-fidelity texture reproduction

**Why IMG, not PF1/PF2?**
Standard thermoforming machines (PF1/PF2) cannot maintain grain texture during forming. The IMG series uses a specialized process that preserves the original surface finish.

**Available Models:**
• IMG-2220: 2200 x 2000 mm forming area
• IMG-2518: 2500 x 1800 mm forming area

To provide accurate pricing and specs, I need a few details:
→ What is your exact forming area requirement?
→ What cycle time are you targeting?
→ What is your annual production volume?

This is specialized equipment - happy to arrange a technical discussion with our IMG product team.

─
Best,
Ira

Machinecraft Technologies
ira@machinecraft.org"""
                
                return ResponseObject(
                    text=img_response,
                    mode=ResponseMode.SALES,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_reason="IMG process requirement detected",
                    channel=channel,
                    debug_info={"action": "img_series_recommendation"}
                )
            
            # =========================================================================
            # IMPOSSIBLE REQUEST CHECK - Manage expectations for unrealistic requests
            # =========================================================================
            if SALES_QUALIFIER_AVAILABLE:
                impossible_check = detect_impossible_request(intent)
                if impossible_check.is_impossible:
                    logger.info(f"Impossible request detected: {impossible_check.reasons}")
                    
                    # Build expectation management response
                    reasons_text = "\n".join(f"• {r}" for r in impossible_check.reasons)
                    suggestions_text = "\n\n".join(impossible_check.suggestions)
                    
                    expectation_response = f"""Hi!

Thanks for reaching out. I want to be upfront about a few things regarding your requirements:

**Constraints to Consider:**
{reasons_text}

**What We Can Do:**
{suggestions_text}

Let's work together to find the best solution within realistic parameters. Could you share:
→ Is there flexibility on the timeline?
→ What's driving the specific size requirement?
→ Is budget fixed, or can we discuss options?

Happy to jump on a call to discuss alternatives that might work better for your situation.

─
Best,
Ira

Machinecraft Technologies
ira@machinecraft.org"""
                    
                    return ResponseObject(
                        text=expectation_response,
                        mode=ResponseMode.SALES,
                        confidence=ConfidenceLevel.HIGH,
                        confidence_reason="Managing expectations for impossible request",
                        channel=channel,
                        debug_info={
                            "action": "expectation_management",
                            "reasons": impossible_check.reasons
                        }
                    )
            
            # =========================================================================
            # QUALIFICATION CHECK - Ask questions if inquiry is too vague
            # Skip if asking about a specific model (e.g., PF1-C-2015 price)
            # =========================================================================
            if SALES_QUALIFIER_AVAILABLE and not is_specific_model_query(intent):
                qualification = qualify_inquiry(intent)
                
                if qualification.should_ask_questions:
                    # Inquiry is too vague - need more info before recommending
                    logger.info(f"Inquiry is vague (score={qualification.qualification_score:.2f}). Asking qualifying questions.")
                    
                    # Extract customer name if present
                    customer_name = None
                    import re
                    name_match = re.search(r'(?:Thanks|Regards|Best)[,\s]+([A-Z][a-z]+)', intent)
                    if name_match:
                        customer_name = name_match.group(1)
                    
                    # Build understood context from extracted info
                    understood_context = ""
                    if qualification.extracted_info.get('application'):
                        understood_context = f"looking for a machine for {qualification.extracted_info['application'].lower()} applications"
                    elif 'thermoform' in intent.lower() or 'vacuum' in intent.lower():
                        understood_context = "looking for a thermoforming machine"
                    
                    # Use email packager for beautiful formatting (preferred)
                    if EMAIL_PACKAGER_AVAILABLE:
                        packaged = package_email(
                            content="",
                            email_type="qualifying",
                            customer_name=customer_name,
                            understood_context=understood_context,
                            questions=qualification.qualifying_questions,
                        )
                        qualifying_response = packaged.body_plain
                        logger.info(f"Using email packager for qualifying questions (word_count={packaged.word_count})")
                    else:
                        # Fallback to basic formatter
                        qualifying_response = format_qualifying_response(qualification, customer_name)
                    
                    # Store in context for later
                    context_pack.query_analysis_context = (
                        context_pack.query_analysis_context or ""
                    ) + f"\n\nINQUIRY QUALIFICATION:\nScore: {qualification.qualification_score:.2f}\nMissing: {[m.value for m in qualification.missing_info]}\nExtracted: {qualification.extracted_info}"
                    
                    # Return early with qualifying questions
                    return ResponseObject(
                        text=qualifying_response,
                        mode=ResponseMode.SALES,
                        confidence=ConfidenceLevel.HIGH,
                        confidence_reason="Asking qualifying questions before recommendation",
                        clarifying_questions=qualification.qualifying_questions,
                        channel=channel,
                        debug_info={
                            "qualification_score": qualification.qualification_score,
                            "missing_info": [m.value for m in qualification.missing_info],
                            "action": "asking_qualifying_questions"
                        }
                    )
            
            try:
                # If deterministic router picked a series, augment the query
                # so the recommender selects from the correct series.
                recommender_query = intent
                if det_route and det_route.get("bypass_llm_routing"):
                    series_hint = det_route["series"]
                    recommender_query = f"[SERIES:{series_hint}] {intent}"
                    logger.info(
                        f"Deterministic override: forcing recommender to {series_hint} series"
                    )

                logger.info(f"Using machine recommender for query: {recommender_query[:100]}")
                machine_recommendation = recommend_from_query(recommender_query, nlu_result)
                
                if machine_recommendation and machine_recommendation.best_match:
                    best = machine_recommendation.best_match
                    
                    # =================================================================
                    # BEAUTIFUL EMAIL PACKAGING - Use email packager for branded response
                    # when we have high confidence (fit_score > 0.7)
                    # =================================================================
                    if (EMAIL_PACKAGER_AVAILABLE or DETAILED_RECOMMENDATION_AVAILABLE) and best.fit_score > 0.7:
                        # Extract customer name from query
                        customer_name = None
                        import re
                        name_match = re.search(r'(?:Thanks|Regards|Best)[,\s]+([A-Z][a-z]+)', intent)
                        if name_match:
                            customer_name = name_match.group(1)
                        
                        # Extract application/material from query or NLU
                        application = None
                        materials = None
                        if nlu_result:
                            mats = nlu_result.get_materials()
                            if mats:
                                materials = ", ".join(mats)
                        
                        # Look for industry keywords
                        intent_lower = intent.lower()
                        for industry in ["aerospace", "automotive", "sanitary", "packaging", "telecom", "medical", "refrigerat"]:
                            if industry in intent_lower:
                                application = industry.capitalize()
                                break
                        
                        # Get alternatives
                        alt_models = []
                        if machine_recommendation.alternative_matches:
                            alt_models = [alt.model for alt in machine_recommendation.alternative_matches[:2]]
                        
                        # Use email packager for beautiful formatting (preferred)
                        if EMAIL_PACKAGER_AVAILABLE:
                            packaged = package_email(
                                content="",
                                email_type="recommendation",
                                customer_name=customer_name,
                                machine_model=best.model,
                                application=application,
                                materials=materials,
                                alternatives=alt_models,
                            )
                            detailed_response = packaged.body_plain
                            logger.info(f"Using email packager for {best.model} (word_count={packaged.word_count})")
                        else:
                            # Fallback to detailed_recommendation
                            detailed_response = format_detailed_recommendation(
                                machine_model=best.model,
                                customer_name=customer_name,
                                application=application,
                                materials=materials,
                                include_pricing=True,
                                include_terms=True,
                            )
                            if alt_models:
                                detailed_response += f"\n\n**Alternative Options:** {', '.join(alt_models)} - let me know if you'd like details on these."
                        
                        logger.info(f"Returning packaged recommendation for {best.model} (fit_score={best.fit_score:.2f})")
                        
                        return ResponseObject(
                            text=detailed_response,
                            mode=ResponseMode.SALES,
                            confidence=ConfidenceLevel.HIGH,
                            confidence_reason=f"Packaged recommendation for {best.model} with fit_score={best.fit_score:.2f}",
                            channel=channel,
                            debug_info={
                                "machine_recommended": best.model,
                                "fit_score": best.fit_score,
                                "match_reasons": best.match_reasons,
                                "action": "packaged_recommendation",
                                "deterministic_route": det_route,
                            }
                        )
                    
                    # Fallback: Inject recommendation into context for LLM to use
                    recommendation_context = f"""
VERIFIED MACHINE RECOMMENDATION (from structured database):
-----------------------------------------------------------
Best Match: {best.model}
Forming Area: {best.forming_area}
Price: ₹{best.price_inr:,}
Max Sheet Thickness: {best.max_sheet_thickness}mm
Heater Power: {best.heater_power_kw} kW
Vacuum Pump: {best.vacuum_pump}

Match Reasons:
{chr(10).join('- ' + r for r in best.match_reasons)}

{'Warnings: ' + chr(10).join('- ' + w for w in best.warnings) if best.warnings else ''}

Fit Score: {best.fit_score:.2f}
-----------------------------------------------------------
IMPORTANT: Generate a DETAILED response with full technical specifications.
Include: Machine overview, key features (bullet points), technical specs table,
pricing with disclaimers, delivery terms, and warranty information.
The response should be professional and comprehensive like a formal quotation email.
"""
                    # Add alternatives if available
                    if machine_recommendation.alternative_matches:
                        recommendation_context += "\n\nAlternatives:\n"
                        for alt in machine_recommendation.alternative_matches[:3]:
                            recommendation_context += f"- {alt.model} ({alt.forming_area}) - ₹{alt.price_inr:,}\n"
                    
                    # Inject into context_pack
                    if not context_pack.rag_chunks:
                        context_pack.rag_chunks = []
                    
                    # Prepend as a high-priority RAG chunk
                    context_pack.rag_chunks.insert(0, {
                        "text": recommendation_context,
                        "filename": "machine_database.py",
                        "doc_type": "verified_recommendation",
                        "score": 1.0,
                        "machines": [best.model],
                    })
                    
                    # Also add to query analysis context
                    context_pack.query_analysis_context = (
                        context_pack.query_analysis_context or ""
                    ) + f"\n\nMACHINE RECOMMENDATION RESULT:\n{machine_recommendation.formatted_response}"
                    
                    logger.info(f"Machine recommendation: {best.model} (fit_score={best.fit_score:.2f})")
                    
            except Exception as e:
                logger.warning(f"Machine recommender failed: {e}")
    
    # Extract conversational enhancement if present
    conv_enhancement = context_pack.conversational_enhancement
    
    # Determine emotional state and warmth for personality application
    emotional_state = None
    warmth = "stranger"
    if conv_enhancement:
        emotional_state = conv_enhancement.get("emotional_state")
        warmth = conv_enhancement.get("warmth", "stranger")
    
    # Check for truth hint (ground truth for common questions)
    truth_hint = None
    if TRUTH_HINTS_AVAILABLE:
        truth_hint = get_truth_hint(intent)
    
    # Build system prompt with all enhancements
    system_prompt = _build_system_prompt(
        context_pack=context_pack,
        channel=channel,
        conversational_enhancement=conv_enhancement,
        truth_hint=truth_hint,
        intent=intent
    )
    
    # Determine response mode early (used for pipeline decisions)
    mode = ResponseMode.GENERAL
    intent_lower = intent.lower()
    if any(kw in intent_lower for kw in ["price", "quote", "cost", "machine", "pf1", "specification", "spec"]):
        mode = ResponseMode.SALES
    elif any(kw in intent_lower for kw in ["who are you", "what are you", "introduce"]):
        mode = ResponseMode.INTRO
    
    # =========================================================================
    # MULTI-PASS RELIABILITY PIPELINE
    # Use for SALES queries or when explicitly requested
    # =========================================================================
    pipeline_debug_info = {}
    
    if use_multi_pass and mode == ResponseMode.SALES and MACHINE_DB_AVAILABLE:
        logger.info("Using multi-pass reliability pipeline for SALES query")
        
        raw_response, pipeline_debug_info = _run_multi_pass_pipeline(
            intent=intent,
            system_prompt=system_prompt,
            context_pack=context_pack,
            channel=channel
        )
    else:
        # Standard single-pass generation for non-sales queries
        raw_response = _call_llm(system_prompt, intent)
        pipeline_debug_info = {"pipeline_used": False}
    
    # =========================================================================
    # HALLUCINATION DETECTION - Check if response is grounded in context
    # =========================================================================
    grounding_score, grounding_reason = _check_grounding(
        response=raw_response,
        rag_chunks=context_pack.rag_chunks,
        truth_hint=truth_hint,
        query=intent
    )
    
    # If poorly grounded and we have context, add disclaimer
    # Skip if pipeline already validated (it does its own checking)
    if grounding_score < 0.5 and context_pack.rag_chunks and not pipeline_debug_info.get("pipeline_used"):
        raw_response = _add_uncertainty_marker(raw_response, grounding_reason)
    
    # Apply personality (openers, closers, emotional calibration)
    final_text = _apply_personality(
        text=raw_response,
        confidence="high" if grounding_score > 0.7 or pipeline_debug_info.get("pipeline_used") else "medium",
        channel=channel,
        emotional_state=emotional_state,
        warmth=warmth
    )
    
    # =========================================================================
    # QUOTE GENERATION - Auto-generate quote if enough info provided
    # =========================================================================
    quote_text = ""
    if mode == ResponseMode.SALES and any(kw in intent_lower for kw in ["price", "quote", "cost"]):
        quote_text = _try_generate_quote(intent, channel)
        if quote_text:
            final_text += "\n\n" + quote_text
    
    # =========================================================================
    # FINAL BUSINESS RULE VALIDATION (if not done by pipeline)
    # =========================================================================
    if not pipeline_debug_info.get("business_rules_validated") and KNOWLEDGE_HEALTH_AVAILABLE:
        is_valid, warnings = kh_validate_response(intent, final_text)
        pipeline_debug_info["business_rule_warnings"] = warnings
        pipeline_debug_info["business_rules_validated"] = True
        
        if warnings:
            logger.warning(f"Business rule warnings (final check): {warnings}")
    
    # =========================================================================
    # CRITICAL AM SERIES CHECK - Always validate before returning
    # This catches cases where AM is incorrectly recommended for thick materials
    # =========================================================================
    final_text_lower = final_text.lower()
    intent_lower_check = intent.lower()
    
    if ("am-" in final_text_lower or "am " in final_text_lower or "am series" in final_text_lower):
        # Check for thick materials (>1.5mm) using simple string matching
        combined_check = intent_lower_check + " " + final_text_lower
        
        # Check for patterns like "5mm abs", "5mm sheet", "5mm thick"
        am_violation = False
        import re as regex_module
        thick_patterns = [
            r'([2-9]|1[0-9])\s*mm\s*(?:thick|sheet)',
            r'([2-9]|1[0-9])\s*mm\s+(abs|pmma|pc|petg|hips|pvc|tpo)',
            r'(abs|pmma|pc|petg|hips|pvc).*?([2-9]|1[0-9])\s*mm',
            r'up\s*to\s*([2-9]|1[0-9])\s*mm',
        ]
        for pattern in thick_patterns:
            if regex_module.search(pattern, combined_check, regex_module.IGNORECASE):
                am_violation = True
                break
        
        if am_violation:
            logger.warning("AM Series thickness violation detected - adding correction")
            final_text += "\n\n**⚠️ Important Correction:** The AM Series is designed for thin-gauge materials (≤1.5mm thickness only). For your requirement of thicker sheets (>1.5mm), the **PF1 Series** is the appropriate choice. The PF1 offers closed-chamber, heavy-gauge forming capability for materials up to 10mm. Let me know if you'd like specifications for the PF1 series instead."
            pipeline_debug_info["am_series_correction_applied"] = True
    
    # =========================================================================
    # CRITICAL PF1 SERIES CHECK - Catch incorrect "flexible" / "thin-gauge" / "packaging" claims
    # PF1 is HEAVY-GAUGE ONLY (2-8mm ABS, HDPE, PC, etc.), NOT for flexible materials
    # =========================================================================
    import re as regex_module  # ensure available even if AM block didn't run
    if ("pf1" in final_text_lower or "pf-1" in final_text_lower or "pf 1" in final_text_lower):
        pf1_misuse = False
        pf1_misuse_phrases = [
            "flexible packaging", "flexible material", "thin gauge", "thin-gauge",
            "food tray", "food container", "blister pack", "clamshell",
            "food packaging", "flexible film", "thin film", "roll-fed",
            "primarily.*flexible", "designed for flexible", "suited for flexible",
        ]
        for phrase in pf1_misuse_phrases:
            if regex_module.search(phrase, final_text_lower, regex_module.IGNORECASE):
                pf1_misuse = True
                break

        if pf1_misuse:
            logger.warning("PF1 Series misuse detected - response incorrectly describes PF1 for flexible/thin-gauge use")
            final_text = regex_module.sub(
                r'(?i)(pf1[^.]*(?:flexible|thin[- ]gauge|food tray|blister|clamshell|food packaging|food container)[^.]*\.)',
                '',
                final_text
            ).strip()
            final_text += "\n\n**⚠️ Clarification:** The PF1 Series is a **heavy-gauge** thermoforming machine for thick sheet materials (2–8mm). It processes ABS, HDPE, PC, PMMA, HIPS, and similar heavy-gauge plastics. It is used for automotive interiors, refrigerator liners, truck bedliners, luggage, EV parts, and industrial enclosures. For thin-gauge or flexible packaging (≤1.5mm), the **AM Series** is the correct choice."
            pipeline_debug_info["pf1_misuse_correction_applied"] = True

    # Determine confidence based on grounding and pipeline results
    if truth_hint:
        confidence = ConfidenceLevel.HIGH
        confidence_reason = f"Verified answer from truth hints ({truth_hint.id})"
    elif pipeline_debug_info.get("pipeline_used") and pipeline_debug_info.get("pass2_corrections_made", 0) == 0:
        confidence = ConfidenceLevel.HIGH
        confidence_reason = "Multi-pass pipeline verified - no corrections needed"
    elif pipeline_debug_info.get("pipeline_used"):
        confidence = ConfidenceLevel.HIGH
        confidence_reason = f"Multi-pass pipeline verified - {pipeline_debug_info.get('pass2_corrections_made', 0)} corrections applied"
    elif grounding_score > 0.7:
        confidence = ConfidenceLevel.HIGH
        confidence_reason = grounding_reason
    elif grounding_score > 0.4:
        confidence = ConfidenceLevel.MEDIUM
        confidence_reason = grounding_reason
    else:
        confidence = ConfidenceLevel.LOW
        confidence_reason = grounding_reason
    
    # Extract consolidated knowledge IDs for quality tracking
    consolidated_ids = []
    if QUALITY_TRACKING_AVAILABLE and context_pack.rag_chunks:
        for chunk in context_pack.rag_chunks:
            if isinstance(chunk, dict):
                if chunk.get("is_consolidated_knowledge") and chunk.get("knowledge_id"):
                    consolidated_ids.append(chunk["knowledge_id"])
                elif chunk.get("doc_type") in ("learned_fact", "dream_knowledge", "consolidated"):
                    chunk_id = chunk.get("knowledge_id") or chunk.get("chunk_id") or ""
                    if chunk_id:
                        consolidated_ids.append(chunk_id)
    
    # Build response object with combined debug info
    debug_info = {
        "emotional_state": emotional_state,
        "warmth": warmth,
        "rag_chunks_used": len(context_pack.rag_chunks),
        "has_conversation_history": context_pack.has_conversation_history(),
        "truth_hint_used": truth_hint.id if truth_hint else None,
        "grounding_score": grounding_score,
        "quote_generated": bool(quote_text),
        "consolidated_knowledge_used": len(consolidated_ids),
    }
    debug_info.update(pipeline_debug_info)
    
    response = ResponseObject(
        text=final_text,
        mode=mode,
        confidence=confidence,
        confidence_reason=confidence_reason,
        channel=channel,
        generation_path="multi_pass_reliability" if pipeline_debug_info.get("pipeline_used") else "unified_replika_enhanced",
        debug_info=debug_info,
        consolidated_knowledge_ids=consolidated_ids,
    )
    
    # Add clarifying questions using proactive engine
    if PROACTIVE_AVAILABLE and emotional_state not in ["urgent", "stressed", "frustrated"]:
        # Get conversation history for context
        history = []
        if context_pack.recent_messages:
            history = [msg.get("content", "") for msg in context_pack.recent_messages[-5:]]
        
        # Generate proactive questions
        proactive_qs = get_proactive_questions(
            message=intent,
            context={"intent": intent_lower, "topic": mode.value if mode else "general"},
            history=history,
            max_questions=2,
            emotional_state=emotional_state or "neutral",
        )
        
        if proactive_qs:
            response.clarifying_questions = [q.question for q in proactive_qs]
            
            # Append questions to response text if not already asking something
            if not response.text.rstrip().endswith("?"):
                question_text = format_proactive_questions(proactive_qs, style="conversational")
                response.text += question_text
                
                # Mark questions as asked
                engine = get_proactive_engine()
                for q in proactive_qs:
                    engine.mark_asked(q.question)
    elif not PROACTIVE_AVAILABLE and mode == ResponseMode.SALES:
        # Fallback to basic question if proactive engine not available
        if not any(kw in intent_lower for kw in ["price", "quote"]):
            response.clarifying_questions = ["What application are you looking at?"]
    
    return response


# =============================================================================
# EMAIL-SPECIFIC GENERATION
# =============================================================================

def generate_email_response(
    intent: str,
    context_pack: Optional[Union[ContextPack, Dict]] = None,
    thread_id: str = "",
    sender_email: str = "",
    sender_name: Optional[str] = None,
) -> ResponseObject:
    """
    Generate email response with Replika enhancements and proper email styling.
    
    Email responses use emotional calibration and follow email best practices:
    - Warm but professional tone
    - Proper structure (greeting, body, closing)
    - Email-safe formatting
    """
    # Initialize enhancer for email if available
    conv_enhancement = None
    warmth_level = "acquaintance"
    
    if REPLIKA_AVAILABLE and sender_email:
        try:
            enhancer = create_enhancer()
            enhancement = enhancer.process_message(
                contact_id=sender_email,
                message=intent,
                channel="email"
            )
            warmth_level = enhancement.relationship_context.get("warmth", "acquaintance")
            conv_enhancement = {
                "emotional_state": enhancement.emotional_reading.primary_state.value,
                "warmth": warmth_level,
                "prompt_additions": enhancement.prompt_additions,
                "suggested_opener": enhancement.suggested_opener,
            }
        except Exception as e:
            logger.warning(f"Email enhancement error: {e}")
    
    # Normalize context_pack and add enhancement
    if context_pack is None:
        context_pack = ContextPack()
    elif isinstance(context_pack, dict):
        context_pack = ContextPack.from_dict(context_pack)
    
    if conv_enhancement:
        context_pack.conversational_enhancement = conv_enhancement
    
    # Generate using main function (body content only)
    response = generate_answer(
        intent=intent,
        context_pack=context_pack,
        channel="email",
        thread_id=thread_id
    )
    
    # Extract style profile for polish pass
    style_profile_dict = None
    emotional_state = "neutral"
    if conv_enhancement:
        emotional_state = conv_enhancement.get("emotional_state", "neutral")
        # Get style profile from enhancement if available
        style_profile_dict = conv_enhancement.get("style_profile")
    
    # =========================================================================
    # POLISH PASS - Refine with brand voice, Rushabh's style, Ira's humor
    # =========================================================================
    if EMAIL_POLISH_AVAILABLE:
        try:
            polisher = EmailPolisher()
            polish_result = polisher.polish(
                draft_email=response.text,
                recipient_style=style_profile_dict,
                emotional_state=emotional_state,
                warmth=warmth_level,
                use_llm=True  # Full LLM polish for emails
            )
            
            response.text = polish_result.polished
            response.debug_info["email_polished"] = True
            response.debug_info["polish_changes"] = polish_result.changes_made
            response.debug_info["humor_added"] = polish_result.humor_added
            
            if polish_result.changes_made:
                logger.debug(f"Email polished: {', '.join(polish_result.changes_made)}")
                
        except Exception as e:
            logger.warning(f"Email polish error: {e}")
            response.debug_info["email_polished"] = False
    
    # =========================================================================
    # EMAIL STYLING - Add greeting, closing, signature
    # =========================================================================
    if EMAIL_STYLING_AVAILABLE:
        try:
            styler = EmailStyler()
            
            # Map warmth level to RecipientRelationship
            relationship_map = {
                "stranger": RecipientRelationship.STRANGER,
                "acquaintance": RecipientRelationship.ACQUAINTANCE,
                "warm": RecipientRelationship.WARM,
                "trusted": RecipientRelationship.TRUSTED,
            }
            relationship = relationship_map.get(warmth_level, RecipientRelationship.ACQUAINTANCE)
            
            # Format the email with proper structure
            formatted_text = styler.format_email_response(
                content=response.text,
                recipient_name=sender_name,
                relationship=relationship,
                include_greeting=True,
                include_closing=True,
                include_signature=True,
                signature_name="Ira",
                signature_title="Machinecraft",
                add_offer_help=True,
            )
            
            # Quality check
            quality = check_email_quality(formatted_text)
            response.debug_info["email_quality_score"] = quality["quality_score"]
            response.debug_info["email_word_count"] = quality["word_count"]
            if quality["spam_triggers"]:
                response.debug_info["spam_triggers_found"] = quality["spam_triggers"]
            
            response.text = formatted_text
            response.debug_info["email_styled"] = True
            response.debug_info["relationship_level"] = warmth_level
            
        except Exception as e:
            logger.warning(f"Email styling error: {e}")
            response.debug_info["email_styled"] = False
    
    # Post-response update if enhancer available
    if REPLIKA_AVAILABLE and sender_email:
        try:
            enhancer = create_enhancer()
            enhancer.post_response_update(
                contact_id=sender_email,
                message=intent,
                response=response.text,
                was_positive=response.confidence == ConfidenceLevel.HIGH
            )
        except Exception as e:
            import logging
            logging.getLogger("ira.brain").warning("Post-response enhancer failed: %s", e, exc_info=True)
    
    return response


# =============================================================================
# QUALITY FEEDBACK INTEGRATION
# =============================================================================

def record_response_feedback(
    response: ResponseObject,
    was_helpful: bool,
) -> int:
    """
    Record feedback for a generated response.
    
    Call this when receiving user feedback on a response:
    - Positive reactions (thumbs up, "thanks", "great") -> was_helpful=True
    - Negative reactions (thumbs down, corrections, "wrong") -> was_helpful=False
    
    This updates quality scores for any consolidated knowledge used in the response,
    helping identify which knowledge is actually useful vs. unhelpful.
    
    Args:
        response: The ResponseObject from generate_answer
        was_helpful: Whether the user found the response helpful
    
    Returns:
        Number of knowledge items that had feedback recorded
    """
    return response.record_feedback(was_helpful)


def record_feedback_by_ids(
    knowledge_ids: List[str],
    was_helpful: bool,
) -> int:
    """
    Record feedback using knowledge IDs directly.
    
    Use this when you've stored the knowledge IDs from a previous response
    and want to record feedback later.
    
    Args:
        knowledge_ids: List of knowledge IDs (from response.consolidated_knowledge_ids)
        was_helpful: Whether the response was helpful
    
    Returns:
        Number of knowledge items that had feedback recorded
    """
    count = 0
    for kid in knowledge_ids:
        if record_knowledge_feedback(kid, was_helpful):
            count += 1
    return count


if __name__ == "__main__":
    # Test
    test_messages = [
        "What's the price for PF1?",
        "Thanks so much for your help!",
        "We're really stressed about the deadline",
        "This is urgent - need response ASAP",
    ]
    
    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"INPUT: {msg}")
        print("="*60)
        result = generate_answer(msg, channel="telegram")
        print(f"MODE: {result.mode.value}")
        print(f"DEBUG: {result.debug_info}")
        print(f"CONSOLIDATED KNOWLEDGE IDS: {result.consolidated_knowledge_ids}")
        print(f"RESPONSE:\n{result.text}")