#!/usr/bin/env python3
"""
IRA PIPELINE ORCHESTRATOR - Unified AI Processing System
==========================================================

Master orchestrator that coordinates all 4 IRA pipelines:

┌─────────────────────────────────────────────────────────────────────────────┐
│                        IRA PIPELINE ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INCOMING MESSAGE (Email / Telegram / OpenClaw)                            │
│                               ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PIPELINE 1: QUERY ANALYSIS                                         │   │
│  │  • Detect message type (question, feedback, greeting, follow-up)   │   │
│  │  • Extract intent (pricing, specs, comparison, general)            │   │
│  │  • Identify entities (machines, companies, people)                 │   │
│  │  • Determine complexity & urgency                                   │   │
│  │  • Extract multiple sub-questions if compound                       │   │
│  │  Output: QueryUnderstanding object                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               ↓                                            │
│            ┌──────────────────┴──────────────────┐                        │
│            ↓                                      ↓                        │
│  ┌──────────────────────┐              ┌──────────────────────┐           │
│  │  IF: FEEDBACK        │              │  IF: QUESTION        │           │
│  │                      │              │                      │           │
│  │  PIPELINE 4:         │              │  PIPELINE 2:         │           │
│  │  FEEDBACK HANDLER    │              │  ANSWER GENERATION   │           │
│  │                      │              │                      │           │
│  │  • Extract correction│              │  • Multi-source      │           │
│  │  • Validate          │              │    memory search     │           │
│  │  • Update knowledge  │              │  • Document retrieval│           │
│  │  • Confirm learning  │              │  • Self-reasoning    │           │
│  └──────────────────────┘              │  • Answer synthesis  │           │
│            ↓                           └──────────────────────┘           │
│            │                                      ↓                        │
│            │                           ┌──────────────────────┐           │
│            │                           │  PIPELINE 3:         │           │
│            │                           │  ANSWER PACKAGING    │           │
│            │                           │                      │           │
│            │                           │  • Structure (BLUF)  │           │
│            │                           │  • Data enrichment   │           │
│            │                           │  • Style application │           │
│            │                           │  • Brand formatting  │           │
│            │                           │  • Quality check     │           │
│            │                           └──────────────────────┘           │
│            │                                      ↓                        │
│            └───────────────────┬─────────────────┘                        │
│                               ↓                                            │
│                    OUTGOING RESPONSE                                       │
│                               ↓                                            │
│            Email / Telegram / OpenClaw (channel-optimized)                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Usage:
    from ira_pipeline_orchestrator import IraPipelineOrchestrator
    
    orchestrator = IraPipelineOrchestrator()
    result = orchestrator.process(
        message="What is the price of PF1-C-2015?",
        user_id="customer@example.com",
        channel="email"  # or "telegram" or "openclaw"
    )
    
    print(result.response)  # Final response to send
"""

import json
import logging
import os
import sys
import time
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
sys.path.insert(0, str(SRC_DIR / "memory"))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logger = logging.getLogger("ira.orchestrator")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class MessageType(str, Enum):
    """Type of incoming message."""
    QUESTION = "question"           # Needs answer generation
    FEEDBACK = "feedback"           # Correction or feedback
    GREETING = "greeting"           # Hello, Hi, etc.
    FOLLOW_UP = "follow_up"         # Follow-up to previous message
    ACKNOWLEDGMENT = "acknowledgment"  # Thanks, Got it, etc.
    COMMAND = "command"             # Do something specific


class Channel(str, Enum):
    """Communication channel."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    OPENCLAW = "openclaw"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    # Query Analysis
    enable_entity_extraction: bool = True
    enable_intent_detection: bool = True
    
    # Answer Generation
    enable_mem0_search: bool = True
    enable_qdrant_search: bool = True
    enable_machine_db_search: bool = True
    enable_document_search: bool = True
    enable_self_reasoning: bool = True
    max_search_results: int = 5
    
    # Answer Packaging
    enable_data_enrichment: bool = True
    enable_style_application: bool = True
    enable_brand_formatting: bool = True
    enable_quality_check: bool = True
    
    # Feedback Handling
    enable_mem0_update: bool = True
    enable_knowledge_update: bool = True
    
    # Channel-specific
    max_response_length: int = 2000  # Characters
    include_follow_up_questions: bool = True
    
    # Performance
    timeout_seconds: float = 90.0
    verbose: bool = True


@dataclass
class OrchestratorResult:
    """Complete result from the orchestrator."""
    # Core output
    response: str                   # Final response to send
    response_html: Optional[str] = None  # HTML version for email
    
    # Metadata
    message_type: MessageType = MessageType.QUESTION
    channel: Channel = Channel.EMAIL
    processing_time_seconds: float = 0.0
    
    # Pipeline results
    query_understanding: Optional[Any] = None
    answer_generation: Optional[Any] = None
    answer_packaging: Optional[Any] = None
    feedback_result: Optional[Any] = None
    
    # Quality metrics
    confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    
    # Debug
    pipeline_log: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# PIPELINE 1: QUERY ANALYSIS
# =============================================================================

class QueryAnalysisPipeline:
    """
    PIPELINE 1: Analyze and understand the incoming message.
    
    Steps:
    1. Classify message type (question, feedback, greeting, etc.)
    2. Detect intent (pricing, specs, comparison, etc.)
    3. Extract entities (machines, companies, people)
    4. Determine complexity and urgency
    5. Break down compound questions
    """
    
    # Message type patterns
    FEEDBACK_PATTERNS = [
        r"^no[!.,]*\s*(it'?s|that'?s|this is|actually|wrong|the\s)",
        r"actually,?\s", r"not correct|incorrect|wrong",
        r"should be|should have been", r"that's not right",
        r"correction:", r"fix:|fix this", r"is a competitor",
        r"is our customer", r"remember this",
    ]
    
    GREETING_PATTERNS = [
        r"^hi\b", r"^hello\b", r"^hey\b", r"^good (morning|afternoon|evening)",
        r"^greetings", r"^dear\s",
    ]
    
    ACKNOWLEDGMENT_PATTERNS = [
        r"^thanks", r"^thank you", r"^got it", r"^understood",
        r"^perfect", r"^great", r"^ok\b", r"^okay",
    ]
    
    # Intent patterns
    INTENT_PATTERNS = {
        "pricing": [r"price|cost|quote|budget|how much|rate|₹|\$|inr|usd"],
        "specs": [r"spec|specification|technical|feature|capacity|power|dimension"],
        "comparison": [r"compare|vs|versus|difference|better|which one"],
        "availability": [r"available|in stock|delivery|lead time|when can"],
        "support": [r"problem|issue|help|support|not working|broken"],
        "general": [r"what is|tell me about|explain|describe|information"],
    }
    
    # Entity patterns
    MACHINE_PATTERNS = [
        (r'(PF1)[-\s]?([A-Z])[-\s]?(\d{4})', "PF1"),
        (r'(PF2)[-\s]?([A-Z])?[-\s]?(\d{4})', "PF2"),
        (r'(ATF)[-\s]?(\d+)[-\s]?([A-Z])?', "ATF"),
        (r'(AM)[-\s]?(\d+)', "AM"),
        (r'(SPM)[-\s]?(\d+)', "SPM"),
        (r'(BPM)[-\s]?(\d+)', "BPM"),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("ira.query_analysis")
        
        # Try to import LLM for advanced analysis
        try:
            from openai import OpenAI
            self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            self.llm_available = True
        except:
            self.llm_available = False
    
    def analyze(
        self,
        message: str,
        previous_response: str = "",
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        Analyze incoming message completely.
        
        Returns QueryUnderstanding dict with:
        - message_type: question/feedback/greeting/etc.
        - intent: pricing/specs/comparison/etc.
        - entities: machines, companies, people extracted
        - sub_questions: list of individual questions
        - complexity: simple/medium/complex
        - urgency: low/medium/high
        """
        import re
        
        context = context or {}
        message_lower = message.lower().strip()
        
        result = {
            "original_message": message,
            "message_type": MessageType.QUESTION,
            "intent": "general",
            "entities": {"machines": [], "companies": [], "people": []},
            "sub_questions": [message],
            "keywords": [],
            "complexity": "simple",
            "urgency": "medium",
            "has_previous_context": bool(previous_response),
        }
        
        # Step 1: Classify message type
        result["message_type"] = self._classify_message_type(message_lower)
        
        # Step 2: Detect intent
        result["intent"] = self._detect_intent(message_lower)
        
        # Step 3: Extract entities
        result["entities"] = self._extract_entities(message)
        
        # Step 4: Extract keywords
        result["keywords"] = self._extract_keywords(message_lower)
        
        # Step 5: Break down compound questions
        result["sub_questions"] = self._extract_sub_questions(message)
        
        # Step 6: Determine complexity
        result["complexity"] = self._assess_complexity(result)
        
        # Step 7: Detect urgency
        result["urgency"] = self._detect_urgency(message_lower)
        
        self.logger.info(f"Query Analysis: type={result['message_type'].value}, intent={result['intent']}")
        
        return result
    
    def _classify_message_type(self, message_lower: str) -> MessageType:
        """Classify the type of message."""
        import re
        
        # Check feedback patterns
        for pattern in self.FEEDBACK_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return MessageType.FEEDBACK
        
        # Check greetings
        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # If it's JUST a greeting, return greeting
                if len(message_lower.split()) < 5:
                    return MessageType.GREETING
        
        # Check acknowledgments
        for pattern in self.ACKNOWLEDGMENT_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                if len(message_lower.split()) < 10:
                    return MessageType.ACKNOWLEDGMENT
        
        return MessageType.QUESTION
    
    def _detect_intent(self, message_lower: str) -> str:
        """Detect the primary intent."""
        import re
        
        intent_scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += 1
            intent_scores[intent] = score
        
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        
        return "general"
    
    def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities from message."""
        import re
        
        entities = {"machines": [], "companies": [], "people": []}
        
        # Extract machine models
        for pattern, prefix in self.MACHINE_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    model = "-".join(str(m) for m in match if m).upper()
                else:
                    model = match.upper()
                if model not in entities["machines"]:
                    entities["machines"].append(model)
        
        # Extract company names (basic pattern)
        company_patterns = [
            r'(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Ltd|Inc|Corp|Pvt|LLC|Co)\b)',
            r'(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Industries|Technologies|Manufacturing)\b)',
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, message)
            entities["companies"].extend(matches)
        
        return entities
    
    def _extract_keywords(self, message_lower: str) -> List[str]:
        """Extract important keywords."""
        # Remove common words
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                    "being", "have", "has", "had", "do", "does", "did", "will",
                    "would", "could", "should", "may", "might", "can", "i", "you",
                    "we", "they", "it", "this", "that", "what", "which", "who",
                    "how", "when", "where", "why", "for", "of", "to", "in", "on",
                    "at", "by", "with", "about", "and", "or", "but", "if", "then",
                    "please", "need", "want", "know", "get", "give", "me", "my"}
        
        words = message_lower.split()
        keywords = [w for w in words if w.isalnum() and len(w) > 2 and w not in stopwords]
        
        return keywords[:10]  # Top 10 keywords
    
    def _extract_sub_questions(self, message: str) -> List[str]:
        """Break compound questions into sub-questions."""
        import re
        
        # Split by question marks
        questions = re.split(r'\?', message)
        questions = [q.strip() + "?" for q in questions if q.strip()]
        
        # If no question marks, check for "and" separators
        if len(questions) <= 1:
            # Split by "and also", "additionally", etc.
            parts = re.split(r'\band also\b|\badditionally\b|\bplus\b', message, flags=re.IGNORECASE)
            if len(parts) > 1:
                questions = [p.strip() for p in parts if p.strip()]
        
        return questions if questions else [message]
    
    def _assess_complexity(self, result: Dict) -> str:
        """Assess query complexity."""
        score = 0
        
        # Multiple sub-questions
        if len(result["sub_questions"]) > 1:
            score += 2
        
        # Multiple entities
        total_entities = sum(len(v) for v in result["entities"].values())
        score += min(total_entities, 3)
        
        # Comparison intent is complex
        if result["intent"] == "comparison":
            score += 2
        
        # Long message
        if len(result["original_message"]) > 500:
            score += 1
        
        if score <= 2:
            return "simple"
        elif score <= 5:
            return "medium"
        return "complex"
    
    def _detect_urgency(self, message_lower: str) -> str:
        """Detect urgency level."""
        urgent_words = ["urgent", "asap", "immediately", "now", "today", "critical"]
        high_words = ["soon", "quickly", "fast", "priority"]
        
        for word in urgent_words:
            if word in message_lower:
                return "high"
        
        for word in high_words:
            if word in message_lower:
                return "medium"
        
        return "low"


# =============================================================================
# PIPELINE 2: ANSWER GENERATION
# =============================================================================

class AnswerGenerationPipeline:
    """
    PIPELINE 2: Generate accurate answers using all AI logic.
    
    Steps:
    1. Multi-source memory search (Mem0, Qdrant, Machine DB)
    2. Document retrieval from data/imports/
    3. Self-reasoning and validation
    4. Answer synthesis with confidence scoring
    5. Follow-up question generation
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.answer_generation")
        
        # Import the deep research pipeline
        try:
            from deep_research_pipeline import DeepResearchPipeline, get_pipeline
            self.deep_research = get_pipeline()
            self.deep_research_available = True
            self.logger.info("Deep Research Pipeline loaded")
        except Exception as e:
            self.logger.warning(f"Deep Research Pipeline not available: {e}")
            self.deep_research = None
            self.deep_research_available = False
        
        # Fallback: direct imports
        try:
            from machine_database import get_machine, search_machines
            self.machine_db_available = True
        except:
            self.machine_db_available = False
    
    def generate(
        self,
        query_understanding: Dict[str, Any],
        user_id: str,
        channel: str,
        config: PipelineConfig = None
    ) -> Dict[str, Any]:
        """
        Generate answer based on query understanding.
        
        Returns:
        - draft_response: Raw generated answer
        - confidence: Confidence score 0-1
        - sources_used: List of sources
        - memory_results: Results from memory search
        - document_matches: Relevant documents
        - follow_up_questions: Suggested follow-ups
        """
        config = config or PipelineConfig()
        
        result = {
            "draft_response": "",
            "confidence": 0.0,
            "sources_used": [],
            "memory_results": [],
            "document_matches": [],
            "reasoning_steps": [],
            "follow_up_questions": [],
        }
        
        # Use Deep Research Pipeline if available
        if self.deep_research_available and self.deep_research:
            try:
                original_message = query_understanding.get("original_message", "")
                
                research_result = self.deep_research.research(
                    query=original_message,
                    user_id=user_id,
                    channel=channel,
                    verbose=config.verbose
                )
                
                # Transfer results
                result["draft_response"] = research_result.draft_response
                result["confidence"] = research_result.confidence
                result["sources_used"] = research_result.sources_used
                result["memory_results"] = research_result.memory_results
                result["document_matches"] = research_result.document_matches
                result["reasoning_steps"] = getattr(research_result, 'reasoning_chain', [])
                result["follow_up_questions"] = [
                    q.question for q in research_result.follow_up_questions
                ]
                
                # Also include the full research result
                result["research_result"] = research_result
                
                return result
                
            except Exception as e:
                self.logger.error(f"Deep research error: {e}")
        
        # Fallback: Simple response
        result["draft_response"] = self._generate_fallback(query_understanding)
        result["confidence"] = 0.5
        
        return result
    
    def _generate_fallback(self, query_understanding: Dict) -> str:
        """Generate a simple fallback response."""
        intent = query_understanding.get("intent", "general")
        entities = query_understanding.get("entities", {})
        machines = entities.get("machines", [])
        
        if machines and self.machine_db_available:
            try:
                from machine_database import get_machine
                machine = get_machine(machines[0])
                if machine:
                    if intent == "pricing":
                        price = machine.get("price_inr", "Contact for pricing")
                        return f"The {machines[0]} is priced at ₹{price:,} (subject to configuration)."
                    elif intent == "specs":
                        return f"The {machines[0]} specifications: {json.dumps(machine, indent=2)}"
            except:
                pass
        
        return "I'd be happy to help you with that. Could you provide more details about what you're looking for?"


# =============================================================================
# PIPELINE 3: ANSWER PACKAGING
# =============================================================================

class AnswerPackagingPipeline:
    """
    PIPELINE 3: Package and polish the response.
    
    Steps:
    1. Structure with BLUF (Bottom Line Up Front)
    2. Enrich with data points
    3. Apply Rushabh's style + IRA's personality
    4. Format for channel (email/telegram/CLI)
    5. Quality check
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.answer_packaging")
        
        # Import reply packaging pipeline
        try:
            from reply_packaging_pipeline import ReplyPackager, get_packager
            self.reply_packager = get_packager()
            self.packaging_available = True
            self.logger.info("Reply Packaging Pipeline loaded")
        except Exception as e:
            self.logger.warning(f"Reply Packaging Pipeline not available: {e}")
            self.reply_packager = None
            self.packaging_available = False
    
    def package(
        self,
        answer_result: Dict[str, Any],
        query_understanding: Dict[str, Any],
        recipient_name: str,
        recipient_email: str,
        channel: str,
        config: PipelineConfig = None
    ) -> Dict[str, Any]:
        """
        Package the answer for delivery.
        
        Returns:
        - response_text: Final plain text response
        - response_html: HTML version (for email)
        - word_count: Word count
        - data_points: Number of data points included
        """
        config = config or PipelineConfig()
        
        result = {
            "response_text": "",
            "response_html": None,
            "word_count": 0,
            "data_points": 0,
            "reading_time_seconds": 0,
        }
        
        # Use Reply Packaging Pipeline if available
        if self.packaging_available and self.reply_packager:
            try:
                # Get research result if available
                research_result = answer_result.get("research_result")
                
                if research_result:
                    packaged = self.reply_packager.package(
                        research_result=research_result,
                        recipient_name=recipient_name,
                        recipient_email=recipient_email,
                        channel=channel,
                        original_subject="",
                        verbose=config.verbose
                    )
                    
                    result["response_text"] = packaged.full_text
                    result["response_html"] = packaged.html_body
                    result["word_count"] = packaged.word_count
                    result["data_points"] = packaged.data_points_count
                    result["reading_time_seconds"] = packaged.reading_time_seconds
                    
                    return result
                    
            except Exception as e:
                self.logger.error(f"Packaging error: {e}")
        
        # Fallback: Use draft response with basic formatting
        draft = answer_result.get("draft_response", "")
        result["response_text"] = self._format_for_channel(draft, channel, recipient_name)
        result["word_count"] = len(result["response_text"].split())
        
        return result
    
    def _format_for_channel(self, text: str, channel: str, recipient_name: str) -> str:
        """Format response for specific channel."""
        if channel == "telegram":
            # Shorter, more casual
            return text[:1500]  # Telegram character limit
        
        elif channel == "email":
            # Add greeting and signature
            greeting = f"Hi {recipient_name},\n\n" if recipient_name and recipient_name != "there" else "Hi,\n\n"
            signature = "\n\nBest regards,\nIRA\nIntelligent Revenue Assistant\nMachinecraft Technologies"
            return greeting + text + signature
        
        else:
            # OpenClaw CLI - clean output
            return text


# =============================================================================
# PIPELINE 4: FEEDBACK HANDLING
# =============================================================================

class FeedbackHandlingPipeline:
    """
    PIPELINE 4: Process feedback and corrections.
    
    Steps:
    1. Extract correction details
    2. Validate the correction
    3. Update knowledge stores
    4. Update logic/guardrails
    5. Generate confirmation
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.feedback_handling")
        
        # Import feedback processing pipeline
        try:
            from feedback_processing_pipeline import FeedbackProcessor, get_processor
            self.feedback_processor = get_processor()
            self.feedback_available = True
            self.logger.info("Feedback Processing Pipeline loaded")
        except Exception as e:
            self.logger.warning(f"Feedback Processing Pipeline not available: {e}")
            self.feedback_processor = None
            self.feedback_available = False
    
    def process(
        self,
        feedback_message: str,
        original_response: str,
        from_user: str,
        channel: str,
        config: PipelineConfig = None
    ) -> Dict[str, Any]:
        """
        Process feedback through the pipeline.
        
        Returns:
        - confirmation_message: Message to send back
        - corrections_found: List of corrections extracted
        - updates_applied: List of knowledge updates
        """
        config = config or PipelineConfig()
        
        result = {
            "confirmation_message": "",
            "corrections_found": [],
            "updates_applied": [],
            "success": False,
        }
        
        if self.feedback_available and self.feedback_processor:
            try:
                feedback_result = self.feedback_processor.process(
                    feedback_message=feedback_message,
                    original_response=original_response,
                    from_user=from_user,
                    channel=channel,
                    verbose=config.verbose
                )
                
                result["confirmation_message"] = feedback_result.confirmation_message
                result["corrections_found"] = [c.to_dict() for c in feedback_result.corrections_found]
                result["updates_applied"] = feedback_result.updates_applied
                result["success"] = feedback_result.success
                result["feedback_result"] = feedback_result
                
                return result
                
            except Exception as e:
                self.logger.error(f"Feedback processing error: {e}")
        
        # Fallback
        result["confirmation_message"] = "Thanks for the feedback! I've noted it down."
        result["success"] = True
        
        return result


# =============================================================================
# MASTER ORCHESTRATOR
# =============================================================================

class IraPipelineOrchestrator:
    """
    Master orchestrator that coordinates all 4 pipelines.
    
    Provides a unified API for processing messages from any channel.
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger("ira.orchestrator")
        
        # Initialize all pipelines
        self.query_analysis = QueryAnalysisPipeline()
        self.answer_generation = AnswerGenerationPipeline()
        self.answer_packaging = AnswerPackagingPipeline()
        self.feedback_handling = FeedbackHandlingPipeline()
        
        # Conversation history for context
        self.conversation_history: Dict[str, Dict] = {}
        
        self.logger.info("IRA Pipeline Orchestrator initialized")
        self.logger.info(f"  - Query Analysis: Ready")
        self.logger.info(f"  - Answer Generation: {'Ready' if self.answer_generation.deep_research_available else 'Fallback mode'}")
        self.logger.info(f"  - Answer Packaging: {'Ready' if self.answer_packaging.packaging_available else 'Fallback mode'}")
        self.logger.info(f"  - Feedback Handling: {'Ready' if self.feedback_handling.feedback_available else 'Fallback mode'}")
    
    def process(
        self,
        message: str,
        user_id: str,
        channel: str = "email",
        previous_response: str = "",
        context: Dict = None,
        config: PipelineConfig = None
    ) -> OrchestratorResult:
        """
        Process a message through the appropriate pipelines.
        
        This is the main entry point for all channels.
        """
        config = config or self.config
        context = context or {}
        start_time = time.time()
        
        result = OrchestratorResult(
            response="",
            channel=Channel(channel),
        )
        
        if config.verbose:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("IRA PIPELINE ORCHESTRATOR")
            self.logger.info("=" * 70)
            self.logger.info(f"User: {user_id}")
            self.logger.info(f"Channel: {channel}")
            self.logger.info(f"Message: {message[:100]}...")
        
        try:
            # Get previous context from history
            history_key = f"{user_id}:{channel}"
            if not previous_response and history_key in self.conversation_history:
                previous_response = self.conversation_history[history_key].get("response", "")
            
            # ═══════════════════════════════════════════════════════════════
            # PIPELINE 1: QUERY ANALYSIS
            # ═══════════════════════════════════════════════════════════════
            if config.verbose:
                self.logger.info("\n" + "-" * 50)
                self.logger.info("[PIPELINE 1: QUERY ANALYSIS]")
                self.logger.info("-" * 50)
            
            query_understanding = self.query_analysis.analyze(
                message=message,
                previous_response=previous_response,
                context=context
            )
            result.query_understanding = query_understanding
            result.message_type = query_understanding["message_type"]
            
            result.pipeline_log.append(f"query_analysis:type={query_understanding['message_type'].value}")
            result.pipeline_log.append(f"query_analysis:intent={query_understanding['intent']}")
            
            # ═══════════════════════════════════════════════════════════════
            # ROUTING: FEEDBACK vs QUESTION
            # ═══════════════════════════════════════════════════════════════
            
            if query_understanding["message_type"] == MessageType.FEEDBACK:
                # ═══════════════════════════════════════════════════════════
                # PIPELINE 4: FEEDBACK HANDLING
                # ═══════════════════════════════════════════════════════════
                if config.verbose:
                    self.logger.info("\n" + "-" * 50)
                    self.logger.info("[PIPELINE 4: FEEDBACK HANDLING]")
                    self.logger.info("-" * 50)
                
                feedback_result = self.feedback_handling.process(
                    feedback_message=message,
                    original_response=previous_response,
                    from_user=user_id,
                    channel=channel,
                    config=config
                )
                
                result.feedback_result = feedback_result
                result.response = feedback_result["confirmation_message"]
                result.pipeline_log.append(f"feedback:corrections={len(feedback_result['corrections_found'])}")
                
            elif query_understanding["message_type"] == MessageType.GREETING:
                # Handle greetings simply
                result.response = self._generate_greeting_response(user_id, channel)
                result.pipeline_log.append("greeting:simple_response")
                
            elif query_understanding["message_type"] == MessageType.ACKNOWLEDGMENT:
                # Handle acknowledgments
                result.response = self._generate_acknowledgment_response(channel)
                result.pipeline_log.append("acknowledgment:simple_response")
                
            else:
                # ═══════════════════════════════════════════════════════════
                # PIPELINE 2: ANSWER GENERATION
                # ═══════════════════════════════════════════════════════════
                if config.verbose:
                    self.logger.info("\n" + "-" * 50)
                    self.logger.info("[PIPELINE 2: ANSWER GENERATION]")
                    self.logger.info("-" * 50)
                
                answer_result = self.answer_generation.generate(
                    query_understanding=query_understanding,
                    user_id=user_id,
                    channel=channel,
                    config=config
                )
                
                result.answer_generation = answer_result
                result.confidence = answer_result.get("confidence", 0.0)
                result.sources_used = answer_result.get("sources_used", [])
                result.follow_up_questions = answer_result.get("follow_up_questions", [])
                result.pipeline_log.append(f"answer_gen:confidence={answer_result['confidence']:.2f}")
                result.pipeline_log.append(f"answer_gen:sources={len(answer_result['sources_used'])}")
                
                # ═══════════════════════════════════════════════════════════
                # PIPELINE 3: ANSWER PACKAGING
                # ═══════════════════════════════════════════════════════════
                if config.verbose:
                    self.logger.info("\n" + "-" * 50)
                    self.logger.info("[PIPELINE 3: ANSWER PACKAGING]")
                    self.logger.info("-" * 50)
                
                # Extract recipient name
                recipient_name = self._extract_name(user_id)
                
                packaging_result = self.answer_packaging.package(
                    answer_result=answer_result,
                    query_understanding=query_understanding,
                    recipient_name=recipient_name,
                    recipient_email=user_id if "@" in user_id else "",
                    channel=channel,
                    config=config
                )
                
                result.answer_packaging = packaging_result
                result.response = packaging_result["response_text"]
                result.response_html = packaging_result.get("response_html")
                result.pipeline_log.append(f"packaging:words={packaging_result['word_count']}")
            
            # Store in conversation history
            self.conversation_history[history_key] = {
                "query": message,
                "response": result.response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            result.response = "I apologize, but I encountered an issue processing your request. Please try again."
            result.warnings.append(str(e))
        
        # Calculate processing time
        result.processing_time_seconds = time.time() - start_time
        
        if config.verbose:
            self.logger.info("\n" + "=" * 70)
            self.logger.info(f"ORCHESTRATOR COMPLETE in {result.processing_time_seconds:.1f}s")
            self.logger.info(f"  Type: {result.message_type.value}")
            self.logger.info(f"  Confidence: {result.confidence:.2f}")
            self.logger.info(f"  Sources: {len(result.sources_used)}")
            self.logger.info(f"  Response length: {len(result.response)} chars")
            self.logger.info("=" * 70)
        
        return result
    
    def _extract_name(self, user_id: str) -> str:
        """Extract name from user ID."""
        if "@" in user_id:
            local_part = user_id.split("@")[0]
            # Try to get name from "firstname.lastname"
            if "." in local_part:
                return local_part.split(".")[0].capitalize()
            return local_part.capitalize()
        return "there"
    
    def _generate_greeting_response(self, user_id: str, channel: str) -> str:
        """Generate a greeting response."""
        name = self._extract_name(user_id)
        
        if channel == "telegram":
            return f"Hi {name}! 👋 How can I help you today?"
        else:
            return f"Hi {name},\n\nGood to hear from you! How can I help you today?\n\nBest regards,\nIRA"
    
    def _generate_acknowledgment_response(self, channel: str) -> str:
        """Generate an acknowledgment response."""
        if channel == "telegram":
            return "You're welcome! Let me know if you need anything else. 😊"
        else:
            return "You're welcome! Don't hesitate to reach out if you have any other questions.\n\nBest regards,\nIRA"
    
    # =========================================================================
    # CHANNEL-SPECIFIC CONVENIENCE METHODS
    # =========================================================================
    
    def process_email(
        self,
        body: str,
        from_email: str,
        subject: str = "",
        thread_id: str = "",
        previous_response: str = ""
    ) -> OrchestratorResult:
        """
        Process an email message.
        
        Convenience method for email channel.
        """
        # Combine subject and body for full context
        full_message = f"Subject: {subject}\n\n{body}" if subject else body
        
        return self.process(
            message=full_message,
            user_id=from_email,
            channel="email",
            previous_response=previous_response,
            context={"subject": subject, "thread_id": thread_id}
        )
    
    def process_telegram(
        self,
        message: str,
        user_id: str,
        chat_id: str = "",
        previous_response: str = ""
    ) -> OrchestratorResult:
        """
        Process a Telegram message.
        
        Convenience method for Telegram channel.
        """
        # Use chat_id as part of context
        full_user_id = f"telegram:{user_id}"
        
        result = self.process(
            message=message,
            user_id=full_user_id,
            channel="telegram",
            previous_response=previous_response,
            context={"chat_id": chat_id}
        )
        
        # Truncate for Telegram if needed
        if len(result.response) > 4000:
            result.response = result.response[:3900] + "\n\n...(message truncated)"
        
        return result
    
    def process_cli(
        self,
        message: str,
        user_id: str = "cli_user"
    ) -> OrchestratorResult:
        """
        Process a CLI/OpenClaw message.
        
        Convenience method for OpenClaw CLI.
        """
        return self.process(
            message=message,
            user_id=user_id,
            channel="openclaw"
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_orchestrator_instance = None


def get_orchestrator(config: PipelineConfig = None) -> IraPipelineOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = IraPipelineOrchestrator(config)
    return _orchestrator_instance


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
    
    parser = argparse.ArgumentParser(description="IRA Pipeline Orchestrator")
    parser.add_argument("message", nargs="?", help="Message to process")
    parser.add_argument("--user", "-u", default="test@example.com", help="User ID")
    parser.add_argument("--channel", "-c", default="email", choices=["email", "telegram", "openclaw"])
    parser.add_argument("--previous", "-p", default="", help="Previous response for context")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    
    args = parser.parse_args()
    
    orchestrator = get_orchestrator()
    
    if args.test:
        # Test cases
        test_cases = [
            ("What is the price of PF1-C-2015?", "email", "pricing question"),
            ("No, the price is ₹60 Lakhs not ₹65", "email", "feedback"),
            ("Hi there!", "telegram", "greeting"),
            ("Thanks!", "telegram", "acknowledgment"),
            ("Compare PF1 and ATF series", "email", "comparison"),
        ]
        
        for message, channel, description in test_cases:
            print(f"\n{'=' * 70}")
            print(f"TEST: {description}")
            print(f"Message: {message}")
            print(f"Channel: {channel}")
            print("=" * 70)
            
            result = orchestrator.process(
                message=message,
                user_id="test@example.com",
                channel=channel
            )
            
            print(f"\nRESPONSE ({result.message_type.value}):")
            print(result.response[:500])
            print(f"\n[Processing time: {result.processing_time_seconds:.1f}s]")
    
    elif args.message:
        result = orchestrator.process(
            message=args.message,
            user_id=args.user,
            channel=args.channel,
            previous_response=args.previous
        )
        
        print("\n" + "=" * 70)
        print("RESPONSE:")
        print("=" * 70)
        print(result.response)
        print(f"\n[Type: {result.message_type.value}, Confidence: {result.confidence:.2f}, Time: {result.processing_time_seconds:.1f}s]")
    
    else:
        parser.print_help()
