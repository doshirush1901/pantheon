#!/usr/bin/env python3
"""
Query Analyzer - Multi-Stage Query Understanding Pipeline
==========================================================

Implements Strategy 2 from DEEP_REPLY_IMPROVEMENT_STRATEGY.md:
- Intent classification (what the user wants)
- Entity extraction (what they're asking about)
- Constraint detection (requirements/conditions)

This moves beyond simple keyword matching to nuanced, context-aware
query understanding using LLM-based analysis.

Usage:
    from openclaw.agents.ira.src.conversation.query_analyzer import (
        QueryAnalyzer, QueryAnalysis, analyze_query
    )
    
    analysis = analyze_query("What's the best machine for 2m x 1.5m truck bedliners?")
    print(analysis.intent)  # "RECOMMENDATION_REQUEST"
    print(analysis.entities)  # {"size": "2000x1500mm", "application": "truck bedliners"}
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from config import get_openai_client, get_logger, FAST_LLM_MODEL
    CONFIG_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    FAST_LLM_MODEL = "gpt-4o-mini"
    
    def get_openai_client():
        import openai
        import os
        return openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class QueryIntent(str, Enum):
    """Possible query intents for Machinecraft conversations."""
    SPEC_REQUEST = "SPEC_REQUEST"
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    PRICE_INQUIRY = "PRICE_INQUIRY"
    TECHNICAL_QUESTION = "TECHNICAL_QUESTION"
    QUOTE_REQUEST = "QUOTE_REQUEST"
    AVAILABILITY = "AVAILABILITY"
    SUPPORT = "SUPPORT"
    GREETING = "GREETING"
    FOLLOW_UP = "FOLLOW_UP"
    CLARIFICATION = "CLARIFICATION"
    COMPETITOR_COMPARISON = "COMPETITOR_COMPARISON"
    UNKNOWN = "UNKNOWN"


COMPETITOR_NAMES = [
    # European Premium
    "illig", "kiefel", "geiss", "frimo", "cannon", "cms", "wm thermoforming",
    # North American
    "gn thermoforming", "gn forming", "brown machine", "sencorp",
    # Asian
    "litai", "gn packaging",
    # Entry-level
    "formech", "belovac",
    # Regional/Specialized
    "gabler", "ridat",
    # Generic terms customers might use
    "chinese machine", "taiwan machine", "german machine",
]


class QueryUrgency(str, Enum):
    """Urgency level of the query."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ExtractedConstraint:
    """A constraint or requirement extracted from the query."""
    constraint_type: str
    value: str
    reasoning: str = ""


@dataclass
class QueryAnalysis:
    """
    Complete analysis of a user query.
    
    Contains:
    - Primary intent (what the user wants)
    - Secondary intents (additional goals)
    - Extracted entities (machines, materials, sizes, etc.)
    - Constraints (requirements that must be met)
    - Urgency level
    - Confidence score
    """
    intent: QueryIntent = QueryIntent.UNKNOWN
    secondary_intents: List[QueryIntent] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: List[ExtractedConstraint] = field(default_factory=list)
    urgency: QueryUrgency = QueryUrgency.MEDIUM
    confidence: float = 0.0
    raw_query: str = ""
    reasoning: str = ""
    suggested_response_length: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent": self.intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "entities": self.entities,
            "constraints": [
                {"type": c.constraint_type, "value": c.value, "reasoning": c.reasoning}
                for c in self.constraints
            ],
            "urgency": self.urgency.value,
            "confidence": self.confidence,
            "raw_query": self.raw_query,
            "reasoning": self.reasoning,
            "suggested_response_length": self.suggested_response_length,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryAnalysis":
        """Create from dictionary."""
        return cls(
            intent=QueryIntent(data.get("intent", "UNKNOWN")),
            secondary_intents=[QueryIntent(i) for i in data.get("secondary_intents", [])],
            entities=data.get("entities", {}),
            constraints=[
                ExtractedConstraint(
                    constraint_type=c.get("type", ""),
                    value=c.get("value", ""),
                    reasoning=c.get("reasoning", ""),
                )
                for c in data.get("constraints", [])
            ],
            urgency=QueryUrgency(data.get("urgency", "medium")),
            confidence=data.get("confidence", 0.0),
            raw_query=data.get("raw_query", ""),
            reasoning=data.get("reasoning", ""),
            suggested_response_length=data.get("suggested_response_length", "medium"),
        )
    
    def has_entity(self, entity_type: str) -> bool:
        """Check if a specific entity type was extracted."""
        return entity_type in self.entities and self.entities[entity_type]
    
    def get_entity(self, entity_type: str, default: Any = None) -> Any:
        """Get an extracted entity by type."""
        return self.entities.get(entity_type, default)
    
    def to_prompt_context(self) -> str:
        """Format analysis for inclusion in LLM prompts."""
        parts = [f"[Query Understanding]"]
        parts.append(f"Intent: {self.intent.value}")
        
        if self.entities:
            entity_strs = [f"  - {k}: {v}" for k, v in self.entities.items() if v]
            if entity_strs:
                parts.append("Entities:\n" + "\n".join(entity_strs))
        
        if self.constraints:
            constraint_strs = [f"  - {c.constraint_type}: {c.value}" for c in self.constraints]
            parts.append("Constraints:\n" + "\n".join(constraint_strs))
        
        parts.append(f"Urgency: {self.urgency.value}")
        parts.append(f"Suggested response length: {self.suggested_response_length}")
        
        return "\n".join(parts)


ANALYSIS_SYSTEM_PROMPT = """You are a query analysis system for Machinecraft Technologies, 
a manufacturer of thermoforming and vacuum forming machines.

Your job is to analyze customer queries and extract:
1. PRIMARY INTENT - What does the user want?
2. ENTITIES - What are they asking about?
3. CONSTRAINTS - What requirements must be met?
4. URGENCY - How urgent is this query?

INTENT TYPES:
- SPEC_REQUEST: Asking for technical specifications
- COMPARISON: Comparing two or more machines/options
- RECOMMENDATION: Asking for advice on which machine to use
- PRICE_INQUIRY: Asking about pricing or cost
- TECHNICAL_QUESTION: General technical/process question
- QUOTE_REQUEST: Requesting a formal quote
- AVAILABILITY: Asking about stock/delivery
- SUPPORT: Need help with existing machine
- GREETING: Just saying hello
- FOLLOW_UP: Following up on previous conversation
- CLARIFICATION: Asking to clarify something
- COMPETITOR_COMPARISON: Comparing Machinecraft to competitors (ILLIG, Kiefel, GN, etc.)
- UNKNOWN: Cannot determine intent

ENTITY TYPES to extract:
- machines: Machine models mentioned (PF1, AM, RE series, etc.)
- applications: Industry/application (automotive, packaging, medical, etc.)
- materials: Plastic materials (ABS, HDPE, PP, etc.)
- dimensions: Forming area sizes (e.g., "2000x1500mm")
- features: Specific features requested
- companies: Company names mentioned
- people: Person names mentioned
- timeline: Delivery/timeline requirements
- competitors: Competitor brands mentioned (ILLIG, Kiefel, GN, Formech, etc.)

CONSTRAINTS to detect:
- Budget constraints (e.g., "under $50,000")
- Size constraints (e.g., "must fit in 3m x 3m space")
- Material constraints (e.g., "must handle HDPE")
- Speed constraints (e.g., "need 100 parts/hour")
- Quality constraints (e.g., "food-grade certification")

RESPONSE LENGTH GUIDANCE:
- short: Simple questions, yes/no, single facts (100-200 words)
- medium: Standard queries, comparisons (400-600 words)
- long: Complex recommendations, detailed technical questions (800-1200 words)

Respond with a JSON object."""

ANALYSIS_USER_PROMPT = """Analyze this query from a customer:

"{query}"

Context (if available):
- Previous messages: {context}
- Customer info: {customer_info}

Return a JSON object with this exact structure:
{{
    "intent": "INTENT_TYPE",
    "secondary_intents": ["OTHER_INTENT"],
    "entities": {{
        "machines": ["PF1-2015"],
        "applications": ["automotive"],
        "materials": ["ABS"],
        "dimensions": ["2000x1500mm"],
        "features": [],
        "companies": [],
        "people": [],
        "timeline": null
    }},
    "constraints": [
        {{"type": "budget", "value": "under $50000", "reasoning": "Customer mentioned budget limit"}}
    ],
    "urgency": "medium",
    "confidence": 0.85,
    "reasoning": "Brief explanation of your analysis",
    "suggested_response_length": "medium"
}}

Be precise with entity extraction. Only include entities actually mentioned.
Set confidence based on how clear the query is (0.0 to 1.0)."""


class QueryAnalyzer:
    """
    Multi-stage query understanding pipeline.
    
    Uses LLM for sophisticated intent classification and entity extraction,
    with fallback to rule-based analysis when LLM is unavailable.
    """
    
    def __init__(self, model: str = None):
        """
        Initialize the query analyzer.
        
        Args:
            model: LLM model to use (defaults to FAST_LLM_MODEL)
        """
        self.model = model or FAST_LLM_MODEL
        self._client = None
    
    @property
    def client(self):
        """Get OpenAI client lazily."""
        if self._client is None:
            if CONFIG_AVAILABLE:
                self._client = get_openai_client()
            else:
                try:
                    from openai import OpenAI
                    import os
                    self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                except Exception:
                    self._client = None
        return self._client
    
    def analyze(
        self,
        query: str,
        context: Optional[List[Dict[str, str]]] = None,
        customer_info: Optional[Dict[str, Any]] = None,
    ) -> QueryAnalysis:
        """
        Analyze a query using multi-stage understanding.
        
        Stage 1: LLM-based intent classification and entity extraction
        Stage 2: Constraint detection and inference
        Stage 3: Confidence calibration and validation
        
        Args:
            query: The user's query text
            context: Previous messages in conversation (optional)
            customer_info: Known info about the customer (optional)
        
        Returns:
            QueryAnalysis object with complete analysis
        """
        if not query or not query.strip():
            return QueryAnalysis(
                intent=QueryIntent.UNKNOWN,
                raw_query=query,
                confidence=0.0,
            )
        
        try:
            if self.client:
                return self._analyze_with_llm(query, context, customer_info)
            else:
                logger.warning("LLM client not available, using rule-based analysis")
                return self._analyze_rule_based(query)
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return self._analyze_rule_based(query)
    
    def _analyze_with_llm(
        self,
        query: str,
        context: Optional[List[Dict[str, str]]] = None,
        customer_info: Optional[Dict[str, Any]] = None,
    ) -> QueryAnalysis:
        """Perform LLM-based query analysis."""
        context_str = ""
        if context:
            context_str = "\n".join([
                f"- {m.get('role', 'user')}: {m.get('content', '')[:100]}..."
                for m in context[-3:]
            ])
        
        customer_str = ""
        if customer_info:
            customer_str = json.dumps(customer_info, default=str)
        
        user_prompt = ANALYSIS_USER_PROMPT.format(
            query=query,
            context=context_str or "None",
            customer_info=customer_str or "None",
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        analysis = QueryAnalysis.from_dict(result)
        analysis.raw_query = query
        
        self._validate_and_enhance(analysis)
        
        return analysis
    
    def _analyze_rule_based(self, query: str) -> QueryAnalysis:
        """Fallback rule-based analysis when LLM is unavailable."""
        import re
        
        query_lower = query.lower()
        analysis = QueryAnalysis(raw_query=query)
        
        competitors_mentioned = [c for c in COMPETITOR_NAMES if c in query_lower]
        
        if competitors_mentioned:
            analysis.intent = QueryIntent.COMPETITOR_COMPARISON
            analysis.entities["competitors"] = competitors_mentioned
        elif any(w in query_lower for w in ["price", "cost", "how much", "pricing", "quote"]):
            analysis.intent = QueryIntent.PRICE_INQUIRY
        elif any(w in query_lower for w in ["compare", "difference", "vs", "versus", "better"]):
            analysis.intent = QueryIntent.COMPARISON
        elif any(w in query_lower for w in ["recommend", "suggest", "best", "which machine", "what machine"]):
            analysis.intent = QueryIntent.RECOMMENDATION
        elif any(w in query_lower for w in ["spec", "specification", "details", "features"]):
            analysis.intent = QueryIntent.SPEC_REQUEST
        elif any(w in query_lower for w in ["how does", "why", "what is", "explain", "how to"]):
            analysis.intent = QueryIntent.TECHNICAL_QUESTION
        elif any(w in query_lower for w in ["quote", "quotation", "proposal"]):
            analysis.intent = QueryIntent.QUOTE_REQUEST
        elif any(w in query_lower for w in ["available", "stock", "delivery", "lead time"]):
            analysis.intent = QueryIntent.AVAILABILITY
        elif any(w in query_lower for w in ["help", "support", "problem", "issue", "broken"]):
            analysis.intent = QueryIntent.SUPPORT
        elif any(w in query_lower for w in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            analysis.intent = QueryIntent.GREETING
        else:
            analysis.intent = QueryIntent.UNKNOWN
        
        machines = []
        machine_patterns = [
            r'\bPF[-\s]?1[-\s]?[A-Z]?[-\s]?\d+\b',
            r'\bPF[-\s]?2[-\s]?\d*\b',
            r'\bAM[-\s]?\d+[A-Z]?\b',
            r'\bRE[-\s]?\d+\b',
            r'\bIMG[-\s]?\d+\b',
        ]
        for pattern in machine_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            machines.extend([m.upper().replace(" ", "-") for m in matches])
        
        materials = []
        material_keywords = ["abs", "hips", "pp", "pe", "hdpe", "pet", "petg", "pc", "pmma", "acrylic", "pvc"]
        for mat in material_keywords:
            if re.search(rf'\b{mat}\b', query_lower):
                materials.append(mat.upper())
        
        applications = []
        app_keywords = ["automotive", "packaging", "medical", "aerospace", "refrigerator", "bathtub", "food"]
        for app in app_keywords:
            if app in query_lower:
                applications.append(app)
        
        dimensions = re.findall(r'\d{3,4}\s*[xX×]\s*\d{3,4}(?:\s*mm)?', query)
        
        # Preserve competitors if already detected, otherwise initialize entities
        existing_competitors = analysis.entities.get("competitors", [])
        analysis.entities = {
            "machines": machines,
            "materials": materials,
            "applications": applications,
            "dimensions": dimensions,
            "competitors": existing_competitors if existing_competitors else competitors_mentioned,
        }
        
        analysis.confidence = 0.6 if analysis.intent != QueryIntent.UNKNOWN else 0.3
        
        self._determine_response_length(analysis)
        
        return analysis
    
    def _validate_and_enhance(self, analysis: QueryAnalysis) -> None:
        """Validate and enhance the analysis."""
        if analysis.intent == QueryIntent.UNKNOWN and analysis.entities.get("machines"):
            analysis.intent = QueryIntent.SPEC_REQUEST
        
        self._determine_response_length(analysis)
        
        self._detect_urgency_signals(analysis)
    
    def _determine_response_length(self, analysis: QueryAnalysis) -> None:
        """Determine suggested response length based on query complexity."""
        if analysis.intent in [QueryIntent.GREETING, QueryIntent.CLARIFICATION]:
            analysis.suggested_response_length = "short"
        elif analysis.intent in [QueryIntent.PRICE_INQUIRY, QueryIntent.AVAILABILITY]:
            analysis.suggested_response_length = "short"
        elif analysis.intent in [QueryIntent.COMPARISON, QueryIntent.RECOMMENDATION]:
            num_machines = len(analysis.entities.get("machines", []))
            if num_machines > 2:
                analysis.suggested_response_length = "long"
            else:
                analysis.suggested_response_length = "medium"
        elif analysis.intent in [QueryIntent.TECHNICAL_QUESTION, QueryIntent.QUOTE_REQUEST]:
            if len(analysis.constraints) > 2:
                analysis.suggested_response_length = "long"
            else:
                analysis.suggested_response_length = "medium"
        else:
            analysis.suggested_response_length = "medium"
    
    def _detect_urgency_signals(self, analysis: QueryAnalysis) -> None:
        """Detect urgency from query content."""
        query_lower = analysis.raw_query.lower()
        
        if any(w in query_lower for w in ["urgent", "asap", "immediately", "emergency", "critical"]):
            analysis.urgency = QueryUrgency.URGENT
        elif any(w in query_lower for w in ["soon", "quickly", "fast", "rush"]):
            analysis.urgency = QueryUrgency.HIGH
        elif any(w in query_lower for w in ["no rush", "when you can", "eventually"]):
            analysis.urgency = QueryUrgency.LOW


_analyzer: Optional[QueryAnalyzer] = None


def get_query_analyzer() -> QueryAnalyzer:
    """Get singleton QueryAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = QueryAnalyzer()
    return _analyzer


def analyze_query(
    query: str,
    context: Optional[List[Dict[str, str]]] = None,
    customer_info: Optional[Dict[str, Any]] = None,
) -> QueryAnalysis:
    """
    Convenience function to analyze a query.
    
    Args:
        query: The user's query text
        context: Previous messages in conversation
        customer_info: Known info about the customer
    
    Returns:
        QueryAnalysis object
    """
    return get_query_analyzer().analyze(query, context, customer_info)


if __name__ == "__main__":
    test_queries = [
        "What's the best machine for making 2m x 1.5m truck bedliners in HDPE?",
        "What is the PF1-2015?",
        "Compare PF1-C-2015 and PF1-C-1812",
        "How much does the AM-5060 cost?",
        "Hi there!",
        "I need this urgently - can you send a quote for automotive interior trim?",
        "What's the vacuum pump size on the PF1-C-3020?",
    ]
    
    analyzer = get_query_analyzer()
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("-" * 60)
        
        analysis = analyzer.analyze(query)
        
        print(f"Intent: {analysis.intent.value}")
        print(f"Confidence: {analysis.confidence:.2f}")
        print(f"Entities: {analysis.entities}")
        print(f"Constraints: {[c.constraint_type for c in analysis.constraints]}")
        print(f"Urgency: {analysis.urgency.value}")
        print(f"Response length: {analysis.suggested_response_length}")
