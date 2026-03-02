#!/usr/bin/env python3
"""
REASONING ENGINE - Ira's "Thinking Before Acting" System
=========================================================

Goal: Always arrive at the RIGHT answer in the QUICKEST possible way.

The Reasoning Engine implements this decision flow:

    Query → [Assess Confidence] → High? → Answer Directly
                    ↓
                   Low?
                    ↓
            [Identify Gaps] → What info is missing?
                    ↓
            [Route to Source] → Memory? Files? CRM? Ask User?
                    ↓
            [Extract & Store] → Get data, save to memory
                    ↓
            [Generate Answer] → Respond with confidence

Key Principles:
1. QUICK PATH: If Ira knows, answer immediately without unnecessary questions
2. SMART QUESTIONS: If unsure, ask the RIGHT clarifying question
3. SOURCE ROUTING: Know which file/database contains what data
4. MEMORY FIRST: Always check memory before searching files
5. LEARN & STORE: Store retrieved data in memory for future use

Usage:
    from reasoning_engine import ReasoningEngine, think_and_respond
    
    engine = ReasoningEngine()
    result = engine.reason("What are the hot leads in Europe?")
    
    if result.can_answer:
        print(result.answer)
    else:
        print(result.clarifying_question)
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))
sys.path.insert(0, str(SKILLS_DIR / "conversation"))
sys.path.insert(0, str(SKILLS_DIR / "memory"))

try:
    from config import PROJECT_ROOT, get_openai_client
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    get_openai_client = None


# =============================================================================
# DATA SOURCE REGISTRY - What data lives where
# =============================================================================

DATA_SOURCES = {
    "leads": {
        "description": "Sales leads, contacts, prospects",
        "keywords": ["lead", "leads", "contact", "contacts", "prospect", "customer", "client"],
        "file_patterns": ["*Contacts*.csv", "*Contacts*.xlsx", "*Leads*.xlsx"],
        "retrieval_method": "leads_database",
        "confidence_boost": 0.3,
    },
    "pricing": {
        "description": "Machine prices, quotes, pricing history",
        "keywords": ["price", "pricing", "cost", "quote", "quotation", "rate", "how much"],
        "file_patterns": ["*Quote*.pdf", "*Quotation*.xlsx", "*Price*.xlsx"],
        "retrieval_method": "pricing_learner",
        "confidence_boost": 0.25,
    },
    "technical_specs": {
        "description": "Machine specifications, dimensions, capacities",
        "keywords": ["spec", "specification", "dimension", "size", "capacity", "model", "pf1", "pf-1"],
        "file_patterns": ["*Catalogue*.pdf", "*PF1*.pdf", "*Spec*.pdf"],
        "retrieval_method": "qdrant_search",
        "confidence_boost": 0.2,
    },
    "company_info": {
        "description": "Machinecraft company information, history, team",
        "keywords": ["company", "machinecraft", "history", "team", "about", "founded"],
        "file_patterns": ["*Evolution*.pdf", "*Company*.pdf", "*About*.pdf"],
        "retrieval_method": "qdrant_search",
        "confidence_boost": 0.2,
    },
    "competitor": {
        "description": "Competitor information, comparisons",
        "keywords": ["competitor", "frimo", "illig", "kiefel", "cms", "compare", "vs", "versus"],
        "file_patterns": ["*Competitor*.xlsx", "*Competitor*.pdf"],
        "retrieval_method": "qdrant_search",
        "confidence_boost": 0.2,
    },
    "customer_history": {
        "description": "Past customer interactions, email history",
        "keywords": ["email", "conversation", "history", "previous", "last time", "discussed"],
        "file_patterns": [],
        "retrieval_method": "memory_search",
        "confidence_boost": 0.15,
    },
}


class ConfidenceLevel(str, Enum):
    """How confident Ira is that she can answer."""
    HIGH = "high"       # Can answer immediately (>0.8)
    MEDIUM = "medium"   # Probably can, but might need to search (0.5-0.8)
    LOW = "low"         # Need to search or ask questions (0.2-0.5)
    UNKNOWN = "unknown" # No idea, need to ask (<0.2)


class ActionType(str, Enum):
    """What action Ira should take."""
    ANSWER_DIRECTLY = "answer_directly"
    SEARCH_MEMORY = "search_memory"
    SEARCH_DOCUMENTS = "search_documents"
    SEARCH_CRM = "search_crm"
    ASK_CLARIFICATION = "ask_clarification"
    ESCALATE = "escalate"


@dataclass
class DataGap:
    """A piece of information Ira doesn't have."""
    description: str
    possible_sources: List[str]
    clarifying_question: str
    priority: int = 1


@dataclass
class ReasoningResult:
    """Result of the reasoning process."""
    query: str
    confidence: float
    confidence_level: ConfidenceLevel
    
    can_answer: bool
    answer: Optional[str] = None
    
    # If can't answer directly
    action: ActionType = ActionType.ANSWER_DIRECTLY
    clarifying_question: Optional[str] = None
    data_gaps: List[DataGap] = field(default_factory=list)
    
    # Source routing
    suggested_sources: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    
    # Retrieved context
    retrieved_context: str = ""
    sources_checked: List[str] = field(default_factory=list)
    
    # Timing
    reasoning_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "confidence": self.confidence,
            "can_answer": self.can_answer,
            "action": self.action.value,
            "clarifying_question": self.clarifying_question,
            "suggested_sources": self.suggested_sources,
        }


class ReasoningEngine:
    """
    Ira's thinking engine - decides the fastest path to the right answer.
    
    Flow:
    1. Analyze query → What is being asked?
    2. Check memory → Do I already know this?
    3. Assess confidence → Can I answer now?
    4. If confident → Answer directly
    5. If not → Either search sources OR ask clarifying question
    6. After retrieval → Store in memory, then answer
    """
    
    def __init__(self):
        self.memory_client = None
        self.knowledge_retriever = None
        self._init_components()
    
    def _init_components(self):
        """Initialize memory and retrieval components."""
        # Mem0 for memory
        try:
            from mem0 import MemoryClient
            api_key = os.environ.get("MEM0_API_KEY")
            if api_key:
                self.memory_client = MemoryClient(api_key=api_key)
        except Exception as e:
            logger.warning("Mem0 not available: %s", e)
        
        # Knowledge retriever
        try:
            from knowledge_retriever import KnowledgeRetriever
            self.knowledge_retriever = KnowledgeRetriever()
        except Exception as e:
            logger.warning("Knowledge retriever not available: %s", e)
    
    def reason(
        self,
        query: str,
        user_id: str = "system_ira",
        context: Dict[str, Any] = None,
    ) -> ReasoningResult:
        """
        Main reasoning entry point.
        
        Decides the fastest path to answer the query correctly.
        """
        import time
        start_time = time.time()
        
        context = context or {}
        logger.info("[reasoning] Query: '%s...'", query[:50])
        
        # Step 1: Analyze what's being asked
        query_analysis = self._analyze_query(query)
        logger.debug("[reasoning] Analysis: %s", query_analysis)
        
        # Step 2: Check memory first (fastest path)
        memory_context, memory_confidence = self._check_memory(query, user_id)
        
        # Step 3: Identify which data sources might have the answer
        relevant_sources = self._identify_sources(query, query_analysis)
        
        # Step 4: Calculate overall confidence
        confidence = self._calculate_confidence(
            query_analysis, memory_confidence, relevant_sources, context
        )
        confidence_level = self._confidence_to_level(confidence)
        
        logger.info("[reasoning] Confidence: %.2f (%s)", confidence, confidence_level.value)
        
        # Step 5: Decide action based on confidence
        if confidence >= 0.7:
            # HIGH CONFIDENCE - Answer directly using memory + minimal search
            result = self._answer_directly(
                query, user_id, query_analysis, memory_context, relevant_sources
            )
        elif confidence >= 0.4:
            # MEDIUM CONFIDENCE - Search sources, then answer
            result = self._search_and_answer(
                query, user_id, query_analysis, relevant_sources
            )
        else:
            # LOW CONFIDENCE - Need clarification OR deep search
            if self._should_ask_clarification(query_analysis):
                result = self._ask_clarification(query, query_analysis)
            else:
                result = self._deep_search_and_answer(
                    query, user_id, query_analysis, relevant_sources
                )
        
        result.reasoning_time_ms = (time.time() - start_time) * 1000
        logger.info("[reasoning] Completed in %.0fms, can_answer=%s",
                   result.reasoning_time_ms, result.can_answer)
        
        return result
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze what the query is asking for."""
        query_lower = query.lower()
        
        analysis = {
            "query": query,
            "query_type": "unknown",
            "entities": [],
            "constraints": [],
            "is_question": "?" in query,
            "is_request": any(w in query_lower for w in ["get", "pull", "find", "show", "give", "list"]),
            "needs_data": False,
            "ambiguous": False,
        }
        
        # Detect query type from keywords
        for source_name, source_info in DATA_SOURCES.items():
            if any(kw in query_lower for kw in source_info["keywords"]):
                analysis["query_type"] = source_name
                analysis["needs_data"] = True
                break
        
        # Detect entities (companies, products, locations)
        # Locations
        locations = re.findall(r'\b(europe|germany|france|austria|india|usa|uk|asia)\b', query_lower)
        if locations:
            analysis["entities"].extend([{"type": "location", "value": l} for l in locations])
        
        # Products
        products = re.findall(r'\b(pf1|pf-1|pf\d|am-\d+|re-\d+)\b', query_lower)
        if products:
            analysis["entities"].extend([{"type": "product", "value": p.upper()} for p in products])
        
        # Check for ambiguity
        vague_terms = ["something", "anything", "some", "stuff", "things"]
        analysis["ambiguous"] = any(t in query_lower for t in vague_terms)
        
        return analysis
    
    def _check_memory(self, query: str, user_id: str) -> Tuple[str, float]:
        """Check Mem0 memory for relevant information."""
        if not self.memory_client:
            return "", 0.0
        
        try:
            # Search user's memories
            results = self.memory_client.search(
                query=query,
                version="v2",
                filters={"user_id": user_id},
                top_k=5,
            )
            
            # Also search system memories
            system_results = self.memory_client.search(
                query=query,
                version="v2",
                filters={"user_id": "system_ira"},
                top_k=5,
            )
            
            all_memories = []
            all_memories.extend(results.get("memories", results.get("results", [])))
            all_memories.extend(system_results.get("memories", system_results.get("results", [])))
            
            if not all_memories:
                return "", 0.0
            
            # Calculate confidence based on memory relevance
            max_score = max(m.get("score", 0) for m in all_memories)
            avg_score = sum(m.get("score", 0) for m in all_memories) / len(all_memories)
            
            # Build context from memories
            context_parts = []
            for mem in all_memories[:5]:
                if mem.get("score", 0) > 0.5:
                    context_parts.append(f"• {mem.get('memory', '')}")
            
            memory_context = "\n".join(context_parts) if context_parts else ""
            confidence = min(1.0, (max_score * 0.6 + avg_score * 0.4))
            
            logger.debug("[reasoning] Memory: %d hits, confidence=%.2f", len(all_memories), confidence)
            return memory_context, confidence
            
        except Exception as e:
            logger.error("[reasoning] Memory check error: %s", e)
            return "", 0.0
    
    def _identify_sources(self, query: str, analysis: Dict) -> List[str]:
        """Identify which data sources are likely to have the answer."""
        query_lower = query.lower()
        relevant = []
        
        for source_name, source_info in DATA_SOURCES.items():
            score = 0
            for kw in source_info["keywords"]:
                if kw in query_lower:
                    score += 1
            
            if score > 0:
                relevant.append((source_name, score))
        
        # Sort by score
        relevant.sort(key=lambda x: x[1], reverse=True)
        
        return [s[0] for s in relevant[:3]]
    
    def _calculate_confidence(
        self,
        analysis: Dict,
        memory_confidence: float,
        sources: List[str],
        context: Dict,
    ) -> float:
        """Calculate overall confidence in ability to answer."""
        confidence = memory_confidence
        
        # Boost if we identified specific sources
        if sources:
            confidence += DATA_SOURCES.get(sources[0], {}).get("confidence_boost", 0.1)
        
        # Reduce if query is ambiguous
        if analysis.get("ambiguous"):
            confidence *= 0.7
        
        # Boost if we have entities to search for
        if analysis.get("entities"):
            confidence += 0.1
        
        # Boost if this is a direct request (not vague question)
        if analysis.get("is_request"):
            confidence += 0.1
        
        # Reduce if we don't know the query type
        if analysis.get("query_type") == "unknown":
            confidence *= 0.8
        
        return min(1.0, max(0.0, confidence))
    
    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level."""
        if confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.4:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNKNOWN
    
    def _should_ask_clarification(self, analysis: Dict) -> bool:
        """Decide if we should ask a clarifying question."""
        # Ask if query is ambiguous
        if analysis.get("ambiguous"):
            return True
        
        # Ask if no specific entities and vague query
        if not analysis.get("entities") and analysis.get("query_type") == "unknown":
            return True
        
        return False
    
    def _answer_directly(
        self,
        query: str,
        user_id: str,
        analysis: Dict,
        memory_context: str,
        sources: List[str],
    ) -> ReasoningResult:
        """High confidence - answer using memory + quick search."""
        logger.info("[reasoning] HIGH confidence - answering directly")
        
        # Quick retrieval from identified sources
        additional_context = ""
        if self.knowledge_retriever and sources:
            try:
                result = self.knowledge_retriever.retrieve(query, user_id, max_results=5)
                additional_context = result.get_context(max_tokens=1500)
            except Exception as e:
                logger.error("[reasoning] Quick retrieval error: %s", e)
        
        # Combine contexts
        full_context = memory_context
        if additional_context:
            full_context += f"\n\n{additional_context}"
        
        return ReasoningResult(
            query=query,
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            can_answer=True,
            action=ActionType.ANSWER_DIRECTLY,
            retrieved_context=full_context,
            suggested_sources=sources,
            sources_checked=["memory"] + sources,
        )
    
    def _search_and_answer(
        self,
        query: str,
        user_id: str,
        analysis: Dict,
        sources: List[str],
    ) -> ReasoningResult:
        """Medium confidence - search sources, then answer."""
        logger.info("[reasoning] MEDIUM confidence - searching sources: %s", sources)
        
        retrieved_context = ""
        sources_checked = []
        
        # Search each identified source
        for source in sources:
            source_info = DATA_SOURCES.get(source, {})
            method = source_info.get("retrieval_method", "qdrant_search")
            
            try:
                if method == "leads_database":
                    context = self._search_leads(query)
                elif method == "pricing_learner":
                    context = self._search_pricing(query)
                elif method == "memory_search":
                    context, _ = self._check_memory(query, user_id)
                else:
                    context = self._search_qdrant(query, user_id)
                
                if context:
                    retrieved_context += f"\n\n[From {source}]:\n{context}"
                    sources_checked.append(source)
                    
            except Exception as e:
                logger.error("[reasoning] Search error for %s: %s", source, e)
        
        # Store retrieved knowledge in memory
        if retrieved_context and self.memory_client:
            self._store_in_memory(query, retrieved_context, user_id)
        
        return ReasoningResult(
            query=query,
            confidence=0.6,
            confidence_level=ConfidenceLevel.MEDIUM,
            can_answer=bool(retrieved_context),
            action=ActionType.SEARCH_DOCUMENTS,
            retrieved_context=retrieved_context,
            suggested_sources=sources,
            sources_checked=sources_checked,
        )
    
    def _ask_clarification(self, query: str, analysis: Dict) -> ReasoningResult:
        """Low confidence + ambiguous - ask clarifying question."""
        logger.info("[reasoning] LOW confidence - asking clarification")
        
        # Generate smart clarifying question
        question = self._generate_clarifying_question(query, analysis)
        
        return ReasoningResult(
            query=query,
            confidence=0.2,
            confidence_level=ConfidenceLevel.LOW,
            can_answer=False,
            action=ActionType.ASK_CLARIFICATION,
            clarifying_question=question,
            data_gaps=[
                DataGap(
                    description="Need more specific information",
                    possible_sources=list(DATA_SOURCES.keys()),
                    clarifying_question=question,
                )
            ],
        )
    
    def _deep_search_and_answer(
        self,
        query: str,
        user_id: str,
        analysis: Dict,
        sources: List[str],
    ) -> ReasoningResult:
        """Low confidence but specific - do deep search."""
        logger.info("[reasoning] LOW confidence - deep search across all sources")
        
        retrieved_context = ""
        sources_checked = []
        
        # Search ALL sources
        all_sources = list(DATA_SOURCES.keys())
        for source in all_sources:
            try:
                source_info = DATA_SOURCES.get(source, {})
                method = source_info.get("retrieval_method", "qdrant_search")
                
                if method == "leads_database":
                    context = self._search_leads(query)
                elif method == "pricing_learner":
                    context = self._search_pricing(query)
                else:
                    context = self._search_qdrant(query, user_id)
                
                if context:
                    retrieved_context += f"\n\n[From {source}]:\n{context}"
                    sources_checked.append(source)
                    
            except Exception:
                pass
        
        # Store in memory
        if retrieved_context and self.memory_client:
            self._store_in_memory(query, retrieved_context, user_id)
        
        return ReasoningResult(
            query=query,
            confidence=0.4 if retrieved_context else 0.1,
            confidence_level=ConfidenceLevel.LOW,
            can_answer=bool(retrieved_context),
            action=ActionType.SEARCH_DOCUMENTS,
            retrieved_context=retrieved_context,
            suggested_sources=sources,
            sources_checked=sources_checked,
        )
    
    def _generate_clarifying_question(self, query: str, analysis: Dict) -> str:
        """Generate a smart clarifying question."""
        query_type = analysis.get("query_type", "unknown")
        
        questions = {
            "leads": "Which region or country are you interested in? (Europe, US, Asia?) And are you looking for hot leads with recent activity or all contacts?",
            "pricing": "Which machine model are you asking about? (e.g., PF1-C-2020, PF1-E-1515) And is this for a specific customer?",
            "technical_specs": "Which machine or feature would you like specifications for?",
            "competitor": "Which competitor are you comparing against? (FRIMO, Illig, CMS, etc.)",
            "unknown": "Could you help me understand what specific information you're looking for? For example: leads/contacts, pricing, technical specs, or company information?",
        }
        
        return questions.get(query_type, questions["unknown"])
    
    def _search_leads(self, query: str) -> str:
        """Search CRM/Leads database."""
        try:
            from leads_database import get_leads_db
            db = get_leads_db()
            
            # Parse query for filters
            query_lower = query.lower()
            region = "Europe" if "europe" in query_lower else None
            hot_only = "hot" in query_lower or "active" in query_lower
            
            leads = db.query(region=region, hot_only=hot_only, limit=10)
            
            if not leads:
                return ""
            
            lines = [f"Found {len(leads)} leads:"]
            for lead in leads[:10]:
                lines.append(f"• {lead.full_name} - {lead.company} ({lead.country}) - {lead.email}")
                if lead.comments:
                    lines.append(f"  Notes: {lead.comments[:80]}...")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error("[reasoning] Leads search error: %s", e)
            return ""
    
    def _search_pricing(self, query: str) -> str:
        """Search pricing data."""
        try:
            from pricing_learner import get_pricing_learner
            learner = get_pricing_learner()
            
            # Extract machine model from query
            models = re.findall(r'pf1[-\s]?([a-z])[-\s]?(\d{4})', query.lower())
            if models:
                variant, size = models[0]
                estimate = learner.estimate_price(f"PF1-{variant.upper()}-{size}")
                if estimate:
                    return f"Price estimate for PF1-{variant.upper()}-{size}: {estimate}"
            
            return ""
            
        except Exception as e:
            logger.error("[reasoning] Pricing search error: %s", e)
            return ""
    
    def _search_qdrant(self, query: str, user_id: str) -> str:
        """Search Qdrant vector database."""
        if not self.knowledge_retriever:
            return ""
        
        try:
            result = self.knowledge_retriever.retrieve(query, user_id, max_results=5)
            return result.get_context(max_tokens=1500)
        except Exception as e:
            logger.error("[reasoning] Qdrant search error: %s", e)
            return ""
    
    def _store_in_memory(self, query: str, context: str, user_id: str):
        """Store retrieved knowledge in Mem0 for future use."""
        if not self.memory_client:
            return
        
        try:
            # Store a summary of what was found
            summary = f"Query '{query[:50]}...' was answered with data from: {context[:200]}..."
            self.memory_client.add(
                messages=[{"role": "assistant", "content": summary}],
                user_id="system_ira",
                metadata={"type": "retrieval_cache", "original_query": query[:100]},
            )
            logger.debug("[reasoning] Stored retrieval in memory")
        except Exception as e:
            logger.error("[reasoning] Memory store error: %s", e)
    
    def introspect_on_reply(
        self,
        original_query: str,
        user_reply: str,
        user_id: str,
    ) -> ReasoningResult:
        """
        When user replies to a clarifying question, introspect on where
        the data might be and retrieve it.
        
        This implements the "think about where data can be" flow.
        """
        logger.info("[reasoning] Introspecting on reply: '%s...'", user_reply[:50])
        
        # Combine original query with reply for better understanding
        combined_query = f"{original_query} {user_reply}"
        
        # Re-analyze with new information
        analysis = self._analyze_query(combined_query)
        
        # Now we have more info - identify sources with higher confidence
        sources = self._identify_sources(combined_query, analysis)
        
        logger.info("[reasoning] After introspection, sources: %s", sources)
        
        # Do targeted search
        return self._search_and_answer(combined_query, user_id, analysis, sources)


# =============================================================================
# SINGLETON & CONVENIENCE
# =============================================================================

_engine: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    """Get singleton reasoning engine."""
    global _engine
    if _engine is None:
        _engine = ReasoningEngine()
    return _engine


def think_and_respond(query: str, user_id: str = "system_ira") -> ReasoningResult:
    """Quick reasoning for a query."""
    engine = get_reasoning_engine()
    return engine.reason(query, user_id)


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    engine = ReasoningEngine()
    
    # Test queries
    test_queries = [
        "What are the hot leads in Europe?",
        "Give me pricing for PF1-C-2020",
        "Tell me something about machines",  # Ambiguous - should ask clarification
        "Who is Klaus Heuer?",
    ]
    
    print("=" * 60)
    print("REASONING ENGINE TEST")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("-" * 60)
        
        result = engine.reason(query)
        
        print(f"Confidence: {result.confidence:.2f} ({result.confidence_level.value})")
        print(f"Can answer: {result.can_answer}")
        print(f"Action: {result.action.value}")
        
        if result.clarifying_question:
            print(f"Clarifying Q: {result.clarifying_question}")
        
        if result.retrieved_context:
            print(f"Context preview: {result.retrieved_context[:200]}...")
        
        print(f"Time: {result.reasoning_time_ms:.0f}ms")
