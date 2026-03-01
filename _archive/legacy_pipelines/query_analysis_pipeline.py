#!/usr/bin/env python3
"""
QUERY ANALYSIS PIPELINE - Deep Understanding of User Messages
==============================================================

Pipeline 1 in IRA's processing chain. Analyzes incoming messages to:

┌─────────────────────────────────────────────────────────────────────────────┐
│                    QUERY ANALYSIS PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 1: MESSAGE CLASSIFICATION                                     │   │
│  │  • Is this a question? feedback? greeting? follow-up?              │   │
│  │  • Uses pattern matching + LLM for ambiguous cases                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 2: INTENT DETECTION                                           │   │
│  │  • Pricing? Specs? Comparison? Support? General?                   │   │
│  │  • Multi-intent for complex queries                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 3: ENTITY EXTRACTION                                          │   │
│  │  • Machine models (PF1-C-2015, ATF-1500, etc.)                     │   │
│  │  • Companies (customers, competitors)                               │   │
│  │  • People, dates, quantities                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 4: QUESTION DECOMPOSITION                                     │   │
│  │  • Break compound questions into atomic queries                    │   │
│  │  • Identify dependencies between sub-questions                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 5: COMPLEXITY & URGENCY ASSESSMENT                            │   │
│  │  • Simple (direct answer) vs Complex (needs research)              │   │
│  │  • Urgency level for prioritization                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 6: CONTEXT INTEGRATION                                        │   │
│  │  • Link to previous messages in thread                             │   │
│  │  • Resolve pronouns ("it", "that machine")                         │   │
│  │  • Identify implicit information needs                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  OUTPUT: QueryUnderstanding object with all analysis                       │
└─────────────────────────────────────────────────────────────────────────────┘

Usage:
    from query_analysis_pipeline import QueryAnalyzer, analyze_query
    
    analyzer = QueryAnalyzer()
    understanding = analyzer.analyze(
        message="What is the price of PF1-C-2015 and how does it compare to ATF?",
        previous_messages=[...],
        user_context={...}
    )
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

# Path setup
BRAIN_DIR = Path(__file__).parent
SRC_DIR = BRAIN_DIR.parent
AGENT_DIR = SRC_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logger = logging.getLogger("ira.query_analysis")

# LLM
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    LLM_AVAILABLE = True
except:
    LLM_AVAILABLE = False
    openai_client = None


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class MessageType(str, Enum):
    """Classification of message type."""
    QUESTION = "question"
    FEEDBACK = "feedback"
    GREETING = "greeting"
    FOLLOW_UP = "follow_up"
    ACKNOWLEDGMENT = "acknowledgment"
    COMMAND = "command"
    COMPLAINT = "complaint"
    REQUEST = "request"


class Intent(str, Enum):
    """Primary intent of the message."""
    PRICING = "pricing"
    SPECS = "specs"
    COMPARISON = "comparison"
    AVAILABILITY = "availability"
    SUPPORT = "support"
    GENERAL = "general"
    QUOTE_REQUEST = "quote_request"
    DOCUMENTATION = "documentation"
    CUSTOMIZATION = "customization"


class Complexity(str, Enum):
    """Query complexity level."""
    SIMPLE = "simple"      # Direct answer, single fact
    MEDIUM = "medium"      # Some research needed
    COMPLEX = "complex"    # Multi-step, multiple sources


class Urgency(str, Enum):
    """Urgency level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExtractedEntity:
    """An entity extracted from the message."""
    type: str           # machine, company, person, date, quantity
    value: str          # The extracted value
    normalized: str     # Normalized form (e.g., PF1-C-2015)
    confidence: float   # 0-1 confidence
    span: Tuple[int, int] = (0, 0)  # Character positions


@dataclass
class SubQuestion:
    """A decomposed sub-question."""
    text: str
    intent: Intent
    entities: List[ExtractedEntity]
    depends_on: List[int] = field(default_factory=list)  # Indices of dependent questions


@dataclass
class QueryUnderstanding:
    """Complete understanding of the query."""
    # Original
    original_message: str
    
    # Classification
    message_type: MessageType
    primary_intent: Intent
    secondary_intents: List[Intent]
    
    # Entities
    entities: List[ExtractedEntity]
    
    # Decomposition
    sub_questions: List[SubQuestion]
    
    # Assessment
    complexity: Complexity
    urgency: Urgency
    
    # Context
    references_previous: bool = False
    resolved_references: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    keywords: List[str] = field(default_factory=list)
    language: str = "en"
    sentiment: str = "neutral"
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "original_message": self.original_message,
            "message_type": self.message_type.value,
            "primary_intent": self.primary_intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "entities": [
                {"type": e.type, "value": e.value, "normalized": e.normalized}
                for e in self.entities
            ],
            "sub_questions": [
                {"text": q.text, "intent": q.intent.value}
                for q in self.sub_questions
            ],
            "complexity": self.complexity.value,
            "urgency": self.urgency.value,
            "keywords": self.keywords,
            "confidence": self.confidence,
        }


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

# Message type patterns
MESSAGE_TYPE_PATTERNS = {
    MessageType.FEEDBACK: [
        r"^no[!.,]*\s*(it'?s|that'?s|this is|actually|wrong|the\s)",
        r"actually,?\s", r"not correct|incorrect|wrong",
        r"should be|should have been", r"that's not right",
        r"correction:", r"fix:|fix this", r"is a competitor",
        r"is our customer", r"remember this", r"please update",
    ],
    MessageType.GREETING: [
        r"^hi\b", r"^hello\b", r"^hey\b", 
        r"^good (morning|afternoon|evening)",
        r"^greetings", r"^dear\s",
    ],
    MessageType.ACKNOWLEDGMENT: [
        r"^thanks", r"^thank you", r"^got it", r"^understood",
        r"^perfect", r"^great(?!\s+question)", r"^ok\b", r"^okay\b",
        r"^sounds good", r"^makes sense",
    ],
    MessageType.COMPLAINT: [
        r"not happy", r"disappointed", r"frustrated",
        r"doesn't work", r"broken", r"problem with",
        r"issue with", r"complaint",
    ],
    MessageType.COMMAND: [
        r"^send\s", r"^create\s", r"^generate\s",
        r"^please (send|create|generate|make)",
    ],
}

# Intent patterns with weights
INTENT_PATTERNS = {
    Intent.PRICING: {
        "patterns": [r"price|cost|quote|budget|how much|rate|₹|\$|inr|usd|lakh|crore"],
        "weight": 2
    },
    Intent.SPECS: {
        "patterns": [r"spec|specification|technical|feature|capacity|power|dimension|size|weight"],
        "weight": 2
    },
    Intent.COMPARISON: {
        "patterns": [r"compare|vs|versus|difference|better|which one|or\s+the|between"],
        "weight": 3
    },
    Intent.AVAILABILITY: {
        "patterns": [r"available|in stock|delivery|lead time|when can|timeline"],
        "weight": 2
    },
    Intent.SUPPORT: {
        "patterns": [r"problem|issue|help|support|not working|error|trouble"],
        "weight": 2
    },
    Intent.QUOTE_REQUEST: {
        "patterns": [r"quotation|formal quote|proposal|proforma|pi\b"],
        "weight": 3
    },
    Intent.DOCUMENTATION: {
        "patterns": [r"brochure|catalog|datasheet|manual|documentation|pdf"],
        "weight": 2
    },
    Intent.CUSTOMIZATION: {
        "patterns": [r"custom|modify|special|specific requirement|tailor"],
        "weight": 2
    },
}

# Machine model patterns (Machinecraft-specific)
MACHINE_PATTERNS = [
    # PF1 Series (Vacuum Forming)
    (r'(PF1)[-\s]?([A-Z])[-\s]?(\d{4})', lambda m: f"PF1-{m[1]}-{m[2]}", "vacuum_forming"),
    (r'\bPF1\b(?![-\s]?[A-Z])', lambda m: "PF1", "vacuum_forming"),
    
    # PF2 Series (Heavy Duty)
    (r'(PF2)[-\s]?([A-Z])?[-\s]?(\d{4})', lambda m: f"PF2-{m[1] or 'X'}-{m[2]}", "vacuum_forming"),
    
    # ATF Series (Auto Trim)
    (r'(ATF)[-\s]?(\d+)[-\s]?([A-Z])?', lambda m: f"ATF-{m[1]}{'-' + m[2] if m[2] else ''}", "auto_trim"),
    
    # AM Series (Automatic)
    (r'(AM)[-\s]?(\d+)', lambda m: f"AM-{m[1]}", "automatic"),
    
    # SPM Series (Skin Pack)
    (r'(SPM)[-\s]?(\d+)', lambda m: f"SPM-{m[1]}", "skin_pack"),
    
    # BPM Series (Blister Pack)
    (r'(BPM)[-\s]?(\d+)', lambda m: f"BPM-{m[1]}", "blister_pack"),
]

# Company patterns
COMPANY_PATTERNS = [
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Ltd|Inc|Corp|Pvt|LLC|Co|Industries|Technologies)\b',
    r'\b(Machinecraft|ILLIG|Kiefel|GN Thermoforming|Formech|MAAC)\b',
]


# =============================================================================
# QUERY ANALYZER
# =============================================================================

class QueryAnalyzer:
    """
    Comprehensive query analyzer for IRA.
    
    Performs deep analysis of incoming messages to understand:
    - What type of message is this?
    - What does the user want?
    - What entities are mentioned?
    - How complex is the query?
    """
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and LLM_AVAILABLE
        self.logger = logging.getLogger("ira.query_analyzer")
    
    def analyze(
        self,
        message: str,
        previous_messages: List[Dict] = None,
        user_context: Dict = None
    ) -> QueryUnderstanding:
        """
        Perform complete analysis of the message.
        
        Args:
            message: The incoming message text
            previous_messages: List of previous messages in conversation
            user_context: Known context about the user
        
        Returns:
            QueryUnderstanding with complete analysis
        """
        previous_messages = previous_messages or []
        user_context = user_context or {}
        
        self.logger.info(f"Analyzing: {message[:100]}...")
        
        # Step 1: Message Classification
        message_type = self._classify_message_type(message)
        
        # Step 2: Intent Detection
        primary_intent, secondary_intents = self._detect_intents(message)
        
        # Step 3: Entity Extraction
        entities = self._extract_entities(message)
        
        # Step 4: Question Decomposition
        sub_questions = self._decompose_questions(message, entities)
        
        # Step 5: Complexity Assessment
        complexity = self._assess_complexity(message, entities, sub_questions)
        
        # Step 6: Urgency Detection
        urgency = self._detect_urgency(message)
        
        # Step 7: Context Resolution
        references_previous, resolved = self._resolve_context(
            message, previous_messages, entities
        )
        
        # Step 8: Extract Keywords
        keywords = self._extract_keywords(message)
        
        # Step 9: Sentiment Analysis
        sentiment = self._analyze_sentiment(message)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            message_type, primary_intent, entities, complexity
        )
        
        understanding = QueryUnderstanding(
            original_message=message,
            message_type=message_type,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=entities,
            sub_questions=sub_questions,
            complexity=complexity,
            urgency=urgency,
            references_previous=references_previous,
            resolved_references=resolved,
            keywords=keywords,
            sentiment=sentiment,
            confidence=confidence,
        )
        
        self.logger.info(
            f"Analysis complete: type={message_type.value}, "
            f"intent={primary_intent.value}, complexity={complexity.value}"
        )
        
        return understanding
    
    def _classify_message_type(self, message: str) -> MessageType:
        """Classify the type of message."""
        message_lower = message.lower().strip()
        
        for msg_type, patterns in MESSAGE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    # For greetings/acks, check if message is short
                    if msg_type in [MessageType.GREETING, MessageType.ACKNOWLEDGMENT]:
                        if len(message_lower.split()) < 10:
                            return msg_type
                    else:
                        return msg_type
        
        # Default to question
        return MessageType.QUESTION
    
    def _detect_intents(self, message: str) -> Tuple[Intent, List[Intent]]:
        """Detect primary and secondary intents."""
        message_lower = message.lower()
        
        intent_scores = {}
        for intent, config in INTENT_PATTERNS.items():
            score = 0
            for pattern in config["patterns"]:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                score += len(matches) * config["weight"]
            intent_scores[intent] = score
        
        # Sort by score
        sorted_intents = sorted(
            intent_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Primary is highest scoring (or GENERAL if none)
        primary = sorted_intents[0][0] if sorted_intents[0][1] > 0 else Intent.GENERAL
        
        # Secondary are others with score > 0
        secondary = [
            intent for intent, score in sorted_intents[1:]
            if score > 0
        ]
        
        return primary, secondary
    
    def _extract_entities(self, message: str) -> List[ExtractedEntity]:
        """Extract all entities from the message."""
        entities = []
        
        # Extract machine models
        for pattern, formatter, category in MACHINE_PATTERNS:
            for match in re.finditer(pattern, message, re.IGNORECASE):
                groups = match.groups()
                normalized = formatter(groups).upper()
                
                entities.append(ExtractedEntity(
                    type="machine",
                    value=match.group(0),
                    normalized=normalized,
                    confidence=0.95,
                    span=(match.start(), match.end())
                ))
        
        # Extract companies
        for pattern in COMPANY_PATTERNS:
            for match in re.finditer(pattern, message):
                entities.append(ExtractedEntity(
                    type="company",
                    value=match.group(0),
                    normalized=match.group(0).strip(),
                    confidence=0.8,
                    span=(match.start(), match.end())
                ))
        
        # Extract quantities with units
        quantity_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(units?|pcs?|pieces?|nos?|lakhs?|crores?|mm|cm|m|kg|kw|kva|hp)'
        for match in re.finditer(quantity_pattern, message, re.IGNORECASE):
            entities.append(ExtractedEntity(
                type="quantity",
                value=match.group(0),
                normalized=f"{match.group(1)} {match.group(2).lower()}",
                confidence=0.9,
                span=(match.start(), match.end())
            ))
        
        # Extract currency amounts
        currency_pattern = r'(?:₹|Rs\.?|INR|USD|\$)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(lakhs?|crores?|k|m)?'
        for match in re.finditer(currency_pattern, message, re.IGNORECASE):
            entities.append(ExtractedEntity(
                type="currency",
                value=match.group(0),
                normalized=match.group(0),
                confidence=0.95,
                span=(match.start(), match.end())
            ))
        
        return entities
    
    def _decompose_questions(
        self,
        message: str,
        entities: List[ExtractedEntity]
    ) -> List[SubQuestion]:
        """Decompose compound questions into sub-questions."""
        sub_questions = []
        
        # Split by question marks
        parts = re.split(r'\?', message)
        parts = [p.strip() for p in parts if p.strip()]
        
        if not parts:
            parts = [message]
        
        # Also split by "and also", "additionally"
        expanded_parts = []
        for part in parts:
            sub_parts = re.split(
                r'\band also\b|\badditionally\b|\balso\b(?=\s+what|\s+how|\s+can)',
                part,
                flags=re.IGNORECASE
            )
            expanded_parts.extend([p.strip() for p in sub_parts if p.strip()])
        
        for i, part in enumerate(expanded_parts):
            # Detect intent for this sub-question
            intent, _ = self._detect_intents(part)
            
            # Find entities in this part
            part_entities = [
                e for e in entities
                if e.value.lower() in part.lower()
            ]
            
            sub_questions.append(SubQuestion(
                text=part if part.endswith("?") else part + "?",
                intent=intent,
                entities=part_entities,
                depends_on=[]
            ))
        
        return sub_questions if sub_questions else [
            SubQuestion(text=message, intent=Intent.GENERAL, entities=entities)
        ]
    
    def _assess_complexity(
        self,
        message: str,
        entities: List[ExtractedEntity],
        sub_questions: List[SubQuestion]
    ) -> Complexity:
        """Assess the complexity of the query."""
        score = 0
        
        # Multiple sub-questions
        score += (len(sub_questions) - 1) * 2
        
        # Multiple entities
        score += min(len(entities), 3)
        
        # Comparison queries are complex
        if any(q.intent == Intent.COMPARISON for q in sub_questions):
            score += 3
        
        # Long messages tend to be complex
        if len(message) > 500:
            score += 2
        elif len(message) > 200:
            score += 1
        
        # Technical terms
        technical_terms = ["specification", "tolerance", "capacity", "throughput"]
        for term in technical_terms:
            if term in message.lower():
                score += 1
        
        if score <= 2:
            return Complexity.SIMPLE
        elif score <= 5:
            return Complexity.MEDIUM
        return Complexity.COMPLEX
    
    def _detect_urgency(self, message: str) -> Urgency:
        """Detect urgency level."""
        message_lower = message.lower()
        
        critical_words = ["urgent", "asap", "immediately", "emergency", "critical"]
        high_words = ["today", "soon", "quickly", "fast", "priority", "rush"]
        medium_words = ["this week", "shortly", "when possible"]
        
        for word in critical_words:
            if word in message_lower:
                return Urgency.CRITICAL
        
        for word in high_words:
            if word in message_lower:
                return Urgency.HIGH
        
        for word in medium_words:
            if word in message_lower:
                return Urgency.MEDIUM
        
        return Urgency.LOW
    
    def _resolve_context(
        self,
        message: str,
        previous_messages: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[bool, Dict[str, str]]:
        """Resolve references to previous context."""
        resolved = {}
        references_previous = False
        
        # Check for pronouns that reference previous context
        pronoun_patterns = [
            r'\b(it|that|this|the machine|the one|same one)\b',
            r'\b(those|these|them)\b',
        ]
        
        for pattern in pronoun_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                references_previous = True
                break
        
        # Try to resolve from previous messages
        if references_previous and previous_messages:
            last_msg = previous_messages[-1] if previous_messages else {}
            last_entities = last_msg.get("entities", [])
            
            # Map "it" to last mentioned machine
            for e in last_entities:
                if isinstance(e, dict) and e.get("type") == "machine":
                    resolved["it"] = e.get("normalized", e.get("value"))
                    resolved["that machine"] = resolved["it"]
                    break
        
        return references_previous, resolved
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Extract important keywords."""
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "i", "you",
            "we", "they", "it", "this", "that", "what", "which", "who",
            "how", "when", "where", "why", "for", "of", "to", "in", "on",
            "at", "by", "with", "about", "and", "or", "but", "if", "then",
            "please", "need", "want", "know", "get", "give", "me", "my",
            "your", "our", "their", "its", "hi", "hello", "thanks", "thank"
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', message.lower())
        
        # Filter and dedupe
        keywords = []
        seen = set()
        for word in words:
            if word not in stopwords and len(word) > 2 and word not in seen:
                keywords.append(word)
                seen.add(word)
        
        return keywords[:15]
    
    def _analyze_sentiment(self, message: str) -> str:
        """Simple sentiment analysis."""
        message_lower = message.lower()
        
        positive_words = ["great", "excellent", "wonderful", "happy", "pleased", "thank"]
        negative_words = ["disappointed", "frustrated", "unhappy", "problem", "issue", "wrong"]
        
        positive_count = sum(1 for w in positive_words if w in message_lower)
        negative_count = sum(1 for w in negative_words if w in message_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
    
    def _calculate_confidence(
        self,
        message_type: MessageType,
        intent: Intent,
        entities: List[ExtractedEntity],
        complexity: Complexity
    ) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.7  # Base confidence
        
        # Clear message type increases confidence
        if message_type != MessageType.QUESTION:
            confidence += 0.1
        
        # Having entities increases confidence
        if entities:
            confidence += min(len(entities) * 0.05, 0.15)
        
        # Simple queries are more confident
        if complexity == Complexity.SIMPLE:
            confidence += 0.1
        elif complexity == Complexity.COMPLEX:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_analyzer_instance = None


def get_analyzer() -> QueryAnalyzer:
    """Get singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = QueryAnalyzer()
    return _analyzer_instance


def analyze_query(
    message: str,
    previous_messages: List[Dict] = None,
    user_context: Dict = None
) -> QueryUnderstanding:
    """
    Convenience function to analyze a query.
    
    Usage:
        understanding = analyze_query("What is the price of PF1-C-2015?")
        print(understanding.primary_intent)  # Intent.PRICING
    """
    analyzer = get_analyzer()
    return analyzer.analyze(message, previous_messages, user_context)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    parser = argparse.ArgumentParser(description="Query Analysis Pipeline")
    parser.add_argument("message", nargs="?", help="Message to analyze")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    
    args = parser.parse_args()
    
    analyzer = get_analyzer()
    
    if args.test:
        test_cases = [
            "What is the price of PF1-C-2015?",
            "Compare PF1 and ATF series for food packaging",
            "No, the price should be ₹60 Lakhs not ₹65",
            "Hi there!",
            "Thanks, that's helpful!",
            "I need urgent quote for 5 machines - PF1-C-2015 and ATF-1500",
            "What's the heater power and forming area of the AM-500?",
        ]
        
        for message in test_cases:
            print(f"\n{'=' * 70}")
            print(f"MESSAGE: {message}")
            print("=" * 70)
            
            understanding = analyzer.analyze(message)
            
            print(f"\nANALYSIS:")
            print(f"  Type: {understanding.message_type.value}")
            print(f"  Intent: {understanding.primary_intent.value}")
            print(f"  Secondary: {[i.value for i in understanding.secondary_intents]}")
            print(f"  Entities: {[(e.type, e.normalized) for e in understanding.entities]}")
            print(f"  Complexity: {understanding.complexity.value}")
            print(f"  Urgency: {understanding.urgency.value}")
            print(f"  Keywords: {understanding.keywords[:5]}")
            print(f"  Confidence: {understanding.confidence:.2f}")
    
    elif args.message:
        understanding = analyzer.analyze(args.message)
        print(json.dumps(understanding.to_dict(), indent=2))
    
    else:
        parser.print_help()
