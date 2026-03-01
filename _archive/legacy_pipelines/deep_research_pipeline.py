#!/usr/bin/env python3
"""
DEEP RESEARCH PIPELINE - Thorough, Multi-Source Answer Generation
===================================================================

When IRA receives an email/message, this pipeline:

1. CHUNK & UNDERSTAND
   - Break email into logical parts
   - Identify the core question(s)
   - Detect intent (pricing? specs? comparison? general?)

2. MULTI-SOURCE MEMORY SEARCH
   - Search Mem0 for user history and preferences
   - Search PostgreSQL for entity memories
   - Search Qdrant for relevant documents

3. NEAREST NEIGHBOR DOCUMENT SELECTION
   - Embed the query with Voyage AI
   - Find most relevant files in data/imports/
   - Extract relevant chunks from PDFs/Excel

4. SELF-REASONING & VALIDATION
   - ReAct pattern: Thought → Action → Observation
   - Ask: "Is this the right answer?"
   - Refine if confidence is low

5. RESPONSE GENERATION
   - Draft reply with IRA's personality
   - Include all brain logic (machine recommender, etc.)
   - Format appropriately for channel

6. QUESTION GENERATION
   - Generate 2-3 follow-up questions for Rushabh
   - Questions should clarify requirements or suggest next steps
   - Be relevant to the specific topic

This pipeline TAKES TIME - quality over speed (20-60+ seconds is OK).

Usage:
    from deep_research_pipeline import DeepResearchPipeline
    
    pipeline = DeepResearchPipeline()
    result = pipeline.research(
        query="What is the price of PF1-C-2015?",
        user_id="customer@example.com",
        channel="email"
    )
"""

import json
import logging
import os
import re
import sys
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
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
sys.path.insert(0, str(SRC_DIR / "common"))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logger = logging.getLogger("ira.deep_research")

# Paths
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
RESEARCH_CACHE_FILE = PROJECT_ROOT / "data" / "research_cache.json"

# =============================================================================
# IMPORTS - External Services
# =============================================================================

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ImportError:
    OPENAI_AVAILABLE = False
    openai_client = None

# Voyage AI (for embeddings)
try:
    import voyageai
    VOYAGE_AVAILABLE = True
    voyage_client = voyageai.Client()
except ImportError:
    VOYAGE_AVAILABLE = False
    voyage_client = None

# Qdrant (vector database)
try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
    qdrant_client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
except ImportError:
    QDRANT_AVAILABLE = False
    qdrant_client = None

# Mem0 (memory service)
try:
    from unified_mem0 import get_unified_mem0
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    get_unified_mem0 = None

# Machine Database
try:
    from machine_database import get_machine, MACHINE_SPECS, find_machines_by_size
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False

# Machine Recommender
try:
    from machine_recommender import recommend_from_query
    RECOMMENDER_AVAILABLE = True
except ImportError:
    RECOMMENDER_AVAILABLE = False

# Knowledge Graph
try:
    from knowledge_graph import KnowledgeGraph
    KNOWLEDGE_GRAPH_AVAILABLE = True
except ImportError:
    KNOWLEDGE_GRAPH_AVAILABLE = False
    KnowledgeGraph = None

# Entity Extractor (for knowledge graph queries)
try:
    sys.path.insert(0, str(SRC_DIR / "conversation"))
    from entity_extractor import EntityExtractor
    ENTITY_EXTRACTOR_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTOR_AVAILABLE = False
    EntityExtractor = None

# Competitive Intelligence Data - Import from centralized config
try:
    from config import COMPETITOR_DATA, COMPETITOR_ALIASES, MACHINECRAFT_POSITIONING
    CONFIG_COMPETITOR_DATA_AVAILABLE = True
except ImportError:
    CONFIG_COMPETITOR_DATA_AVAILABLE = False
    # Fallback for standalone usage
    COMPETITOR_DATA = {
        "ILLIG": {"country": "Germany", "price_range": "2-3x Machinecraft"},
        "Kiefel": {"country": "Germany", "price_range": "2.5-4x Machinecraft"},
    }
    COMPETITOR_ALIASES = {"illig": "ILLIG", "kiefel": "Kiefel"}
    MACHINECRAFT_POSITIONING = {}

# PDF/Document extraction
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Excel reading
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class QueryUnderstanding:
    """Result of understanding a query."""
    original_query: str
    core_questions: List[str]  # The actual questions being asked
    intent: str  # pricing, specs, comparison, recommendation, general
    entities: Dict[str, List[str]]  # machines, materials, dimensions, etc.
    urgency: str  # low, medium, high
    complexity: str  # simple, moderate, complex
    keywords: List[str]


@dataclass
class MemorySearchResult:
    """Result from memory search."""
    source: str  # mem0, postgres, qdrant
    content: str
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentMatch:
    """A matched document from data/imports/."""
    filename: str
    filepath: Path
    relevance_score: float
    matched_chunks: List[str]
    file_type: str  # pdf, xlsx, docx


@dataclass
class ReasoningStep:
    """A single reasoning step."""
    thought: str
    action: str
    observation: str
    confidence: float


@dataclass
class FollowUpQuestion:
    """A follow-up question for Rushabh."""
    question: str
    purpose: str  # clarify, suggest, expand
    priority: str  # high, medium, low


@dataclass
class ConflictResult:
    """Result from conflict detection."""
    has_conflict: bool
    conflict_type: str  # price, spec, fact, none
    conflicting_values: List[str]
    sources: List[str]
    entity: str
    severity: str  # critical, warning, info
    recommendation: str


@dataclass
class DeepResearchResult:
    """Complete result from deep research."""
    query: str
    understanding: QueryUnderstanding
    memory_results: List[MemorySearchResult]
    document_matches: List[DocumentMatch]
    reasoning_chain: List[ReasoningStep]
    draft_response: str
    follow_up_questions: List[FollowUpQuestion]
    confidence: float
    processing_time_seconds: float
    sources_used: List[str]
    # Conflict detection
    conflict_detected: bool = False
    conflict_details: Optional[ConflictResult] = None


# =============================================================================
# QUERY UNDERSTANDING - Step 1
# =============================================================================

class QueryAnalyzer:
    """Analyze and understand incoming queries."""
    
    INTENT_PATTERNS = {
        "pricing": [
            r"price|cost|budget|quote|how much|₹|rs\.?|lakhs?|crores?",
            r"expensive|cheap|afford|pricing|rate",
        ],
        "specs": [
            r"specification|spec|dimension|size|capacity|power",
            r"forming area|heater|vacuum|tonnage|thickness",
        ],
        "comparison": [
            r"compare|versus|vs\.?|difference|better|which one",
            r"between|or\s+\w+\?",
        ],
        "recommendation": [
            r"recommend|suggest|suitable|best|ideal|right machine",
            r"need a machine|looking for|want to|require",
        ],
        "general": [
            r"how|what|when|where|why|who|tell me|explain",
        ],
    }
    
    def __init__(self):
        self.logger = logging.getLogger("ira.query_analyzer")
    
    def analyze(self, query: str) -> QueryUnderstanding:
        """Analyze a query to understand what's being asked."""
        self.logger.info(f"Analyzing query: {query[:100]}...")
        
        # Detect intent
        intent = self._detect_intent(query)
        
        # Extract entities
        entities = self._extract_entities(query)
        
        # Break into core questions
        core_questions = self._extract_questions(query)
        
        # Assess complexity
        complexity = self._assess_complexity(query, entities)
        
        # Detect urgency
        urgency = self._detect_urgency(query)
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        return QueryUnderstanding(
            original_query=query,
            core_questions=core_questions,
            intent=intent,
            entities=entities,
            urgency=urgency,
            complexity=complexity,
            keywords=keywords
        )
    
    def _detect_intent(self, query: str) -> str:
        """Detect primary intent."""
        query_lower = query.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return "general"
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query."""
        entities = {
            "machines": [],
            "materials": [],
            "dimensions": [],
            "applications": [],
            "companies": [],
        }
        
        # Machine models - use full capture groups with prefix
        machine_patterns = [
            (r'(PF1)[-\s]?([A-Z])[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}-{m[2]}"),  # PF1-C-2015
            (r'(PF2)[-\s]?([A-Z])[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}-{m[2]}"),  # PF2-P2020
            (r'(AM)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),  # AM-5060
            (r'(AMP)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),  # AMP-5060
            (r'(IMG)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),  # IMG-1350
            (r'(FCS)[-\s]?(\d{4})[-\s]?(\d)ST', lambda m: f"{m[0]}-{m[1]}-{m[2]}ST"),  # FCS-6050-3ST
            (r'(UNO)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),  # UNO-1208
            (r'(DUO)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),  # DUO-1208
        ]
        
        for pattern, formatter in machine_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                model = formatter(match).upper()
                if model not in entities["machines"]:
                    entities["machines"].append(model)
        
        # Materials
        material_patterns = [
            r'ABS|HDPE|PP|PET|PS|PVC|PMMA|PC|acrylic|polycarbonate',
            r'polyethylene|polypropylene|polystyrene',
        ]
        for pattern in material_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["materials"].extend([m.upper() for m in matches])
        
        # Dimensions (mm)
        dim_pattern = r'(\d{3,4})\s*(?:x|×|by)\s*(\d{3,4})\s*(?:mm)?'
        dim_matches = re.findall(dim_pattern, query, re.IGNORECASE)
        entities["dimensions"] = [f"{d[0]}x{d[1]}" for d in dim_matches]
        
        # Applications
        app_patterns = [
            r'bedliner|automotive|packaging|tray|container|signage',
            r'dashboard|door panel|luggage|enclosure|bathtub|spa',
        ]
        for pattern in app_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["applications"].extend(matches)
        
        return entities
    
    def _extract_questions(self, query: str) -> List[str]:
        """Extract core questions from query."""
        questions = []
        
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+', query)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if it's a question
            if any([
                sentence.endswith('?'),
                sentence.lower().startswith(('what', 'how', 'when', 'where', 'why', 'which', 'can', 'is', 'are', 'do', 'does')),
            ]):
                questions.append(sentence)
            elif len(questions) == 0:
                # First sentence might be an implicit question
                questions.append(sentence)
        
        return questions if questions else [query]
    
    def _assess_complexity(self, query: str, entities: Dict) -> str:
        """Assess query complexity."""
        # Count factors
        num_questions = len(re.findall(r'\?', query))
        num_entities = sum(len(v) for v in entities.values())
        word_count = len(query.split())
        
        if num_questions > 2 or num_entities > 3 or word_count > 100:
            return "complex"
        elif num_questions > 1 or num_entities > 1 or word_count > 50:
            return "moderate"
        else:
            return "simple"
    
    def _detect_urgency(self, query: str) -> str:
        """Detect urgency level."""
        urgent_patterns = [
            r'urgent|asap|immediately|today|now|quick',
            r'deadline|rush|critical|emergency',
        ]
        
        for pattern in urgent_patterns:
            if re.search(pattern, query.lower()):
                return "high"
        
        return "medium"
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords."""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'can', 'this',
                     'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
                     'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
                     'her', 'its', 'our', 'their', 'what', 'which', 'who', 'whom',
                     'whose', 'where', 'when', 'why', 'how', 'and', 'or', 'but',
                     'if', 'then', 'else', 'for', 'of', 'to', 'from', 'with', 'about',
                     'please', 'thanks', 'thank', 'hi', 'hello', 'dear', 'regards'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        keywords = [w for w in words if w not in stopwords]
        
        # Dedupe while preserving order
        seen = set()
        return [w for w in keywords if not (w in seen or seen.add(w))][:10]


# =============================================================================
# COMPETITIVE INTELLIGENCE - Competitor Analysis
# =============================================================================

class CompetitiveIntelligence:
    """
    Provides competitor analysis and comparison context.
    
    When queries mention competitor brands (ILLIG, Kiefel, etc.),
    this module provides:
    - Competitor strengths and weaknesses
    - Price positioning relative to Machinecraft
    - Suggested response strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.competitive_intel")
        self.competitor_data = COMPETITOR_DATA
        self.aliases = COMPETITOR_ALIASES
    
    def detect_competitors(self, query: str) -> List[str]:
        """Detect competitor mentions in query."""
        query_lower = query.lower()
        detected = []
        
        # Check for exact matches and aliases
        for alias, canonical in self.aliases.items():
            if alias in query_lower:
                if canonical not in detected:
                    detected.append(canonical)
        
        # Also check direct matches against competitor names
        for competitor in self.competitor_data.keys():
            if competitor.lower() in query_lower and competitor not in detected:
                detected.append(competitor)
        
        return detected
    
    def get_comparison(
        self,
        query: str,
        competitors: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get competitive intelligence for detected competitors.
        
        Returns structured comparison data for each competitor.
        """
        if competitors is None:
            competitors = self.detect_competitors(query)
        
        if not competitors:
            return []
        
        self.logger.info(f"Generating competitive intelligence for: {competitors}")
        
        comparisons = []
        for competitor in competitors:
            data = self.competitor_data.get(competitor)
            if not data:
                continue
            
            comparison = {
                "competitor": competitor,
                "country": data.get("country", "Unknown"),
                "price_position": data.get("price_range", "Unknown"),
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "typical_customers": data.get("typical_customers", "Unknown"),
                "positioning": data.get("positioning", "Unknown"),
                "notable_models": data.get("notable_models", []),
            }
            comparisons.append(comparison)
        
        return comparisons
    
    def format_comparison_context(self, competitors: List[str]) -> str:
        """
        Format competitor data as context for the LLM.
        
        Provides structured comparison with Machinecraft positioning guidance.
        """
        comparisons = self.get_comparison("", competitors)
        
        if not comparisons:
            return ""
        
        lines = ["## Competitive Intelligence\n"]
        
        for comp in comparisons:
            lines.append(f"### {comp['competitor']} ({comp['country']})")
            lines.append(f"- **Price vs Machinecraft**: {comp['price_position']}")
            lines.append(f"- **Positioning**: {comp['positioning']}")
            
            if comp['strengths']:
                lines.append(f"- **Their strengths**: {', '.join(comp['strengths'])}")
            
            if comp['weaknesses']:
                lines.append(f"- **Their weaknesses**: {', '.join(comp['weaknesses'])}")
            
            lines.append(f"- **Typical customers**: {comp['typical_customers']}")
            
            if comp['notable_models']:
                lines.append(f"- **Notable models**: {', '.join(comp['notable_models'])}")
            
            lines.append("")
        
        # Add Machinecraft positioning strategy
        lines.append("### Machinecraft Positioning Strategy")
        lines.append("- Emphasize **VALUE** proposition (quality + competitive pricing)")
        lines.append("- Highlight **FAST delivery** (8-12 weeks vs 6-9 months for Europeans)")
        lines.append("- Stress **LOCAL support** and responsiveness")
        lines.append("- Focus on **CUSTOMIZATION** capability")
        lines.append("- Mention **PROVEN track record** with similar applications")
        lines.append("")
        lines.append("*Note: Be professional and factual. Never disparage competitors directly.*")
        lines.append("*Instead, highlight Machinecraft's strengths that address the customer's needs.*")
        
        return "\n".join(lines)


# =============================================================================
# MULTI-SOURCE MEMORY SEARCH - Step 2
# =============================================================================

class MultiSourceMemorySearch:
    """Search multiple memory sources in parallel."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.memory_search")
        
        # Initialize knowledge graph for relationship queries
        self._knowledge_graph = None
        if KNOWLEDGE_GRAPH_AVAILABLE:
            try:
                self._knowledge_graph = KnowledgeGraph(verbose=False)
                self.logger.info("Knowledge graph initialized for memory search")
            except Exception as e:
                self.logger.warning(f"Knowledge graph init failed: {e}")
        
        # Initialize entity extractor
        self._entity_extractor = None
        if ENTITY_EXTRACTOR_AVAILABLE:
            try:
                self._entity_extractor = EntityExtractor()
            except Exception:
                pass
        
        # Initialize competitive intelligence
        self._competitive_intel = CompetitiveIntelligence()
        self.logger.info("Competitive intelligence initialized")
    
    def search(
        self,
        query: str,
        user_id: str,
        understanding: QueryUnderstanding,
        max_results_per_source: int = 5
    ) -> List[MemorySearchResult]:
        """Search all memory sources in parallel."""
        self.logger.info(f"Searching memories for: {query[:50]}...")
        
        results = []
        
        # Run searches in parallel (5 sources: Mem0, Qdrant, Machine DB, Knowledge Graph, Competitive Intel)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # Mem0 search
            if MEM0_AVAILABLE:
                futures[executor.submit(
                    self._search_mem0, query, user_id, max_results_per_source
                )] = "mem0"
            
            # Qdrant search
            if QDRANT_AVAILABLE:
                futures[executor.submit(
                    self._search_qdrant, query, understanding, max_results_per_source
                )] = "qdrant"
            
            # Machine database search (if machine entities found)
            if MACHINE_DB_AVAILABLE and understanding.entities.get("machines"):
                futures[executor.submit(
                    self._search_machine_db, understanding.entities["machines"]
                )] = "machine_db"
            
            # Knowledge Graph search (for entity relationships)
            if self._knowledge_graph is not None:
                futures[executor.submit(
                    self._search_knowledge_graph, query, understanding, max_results_per_source
                )] = "knowledge_graph"
            
            # Competitive Intelligence search (if competitor mentioned)
            detected_competitors = self._competitive_intel.detect_competitors(query)
            if detected_competitors:
                futures[executor.submit(
                    self._search_competitive_intel, query, detected_competitors
                )] = "competitive_intel"
            
            # Collect results
            for future in as_completed(futures, timeout=30):
                source = futures[future]
                try:
                    source_results = future.result()
                    results.extend(source_results)
                    self.logger.info(f"  {source}: {len(source_results)} results")
                except Exception as e:
                    self.logger.error(f"  {source} error: {e}")
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _search_mem0(self, query: str, user_id: str, limit: int) -> List[MemorySearchResult]:
        """Search Mem0 for user memories."""
        results = []
        
        try:
            mem0 = get_unified_mem0()
            
            # Search user memories
            memories = mem0.search(query, user_id=user_id, limit=limit)
            
            for mem in memories:
                results.append(MemorySearchResult(
                    source="mem0",
                    content=mem.get("memory", mem.get("text", "")),
                    relevance_score=mem.get("score", 0.5),
                    metadata={
                        "memory_id": mem.get("id"),
                        "created_at": mem.get("created_at"),
                    }
                ))
        except Exception as e:
            self.logger.error(f"Mem0 search error: {e}")
        
        return results
    
    def _search_qdrant(
        self,
        query: str,
        understanding: QueryUnderstanding,
        limit: int
    ) -> List[MemorySearchResult]:
        """Search Qdrant for relevant documents."""
        results = []
        
        try:
            # Get embedding
            if VOYAGE_AVAILABLE:
                embedding = voyage_client.embed(
                    texts=[query],
                    model="voyage-3"
                ).embeddings[0]
            else:
                return results  # Can't search without embedding
            
            # Search collections
            collections = [
                "ira_chunks_v4_voyage",
                "ira_discovered_knowledge",
                "ira_dream_knowledge_v1",
            ]
            
            for collection in collections:
                try:
                    search_results = qdrant_client.search(
                        collection_name=collection,
                        query_vector=embedding,
                        limit=limit,
                        with_payload=True
                    )
                    
                    for hit in search_results:
                        payload = hit.payload or {}
                        text = payload.get("text", payload.get("raw_text", ""))
                        
                        if text:
                            results.append(MemorySearchResult(
                                source=f"qdrant:{collection}",
                                content=text[:2000],
                                relevance_score=hit.score,
                                metadata={
                                    "filename": payload.get("filename"),
                                    "chunk_id": payload.get("chunk_id"),
                                }
                            ))
                except Exception as e:
                    self.logger.debug(f"Collection {collection}: {e}")
        except Exception as e:
            self.logger.error(f"Qdrant search error: {e}")
        
        return results
    
    def _search_machine_db(self, machine_models: List[str]) -> List[MemorySearchResult]:
        """Search machine database for specific models."""
        results = []
        
        for model in machine_models:
            machine = get_machine(model)
            if machine:
                content = f"""
Machine: {machine.model}
Series: {machine.series}
Forming Area: {machine.forming_area_mm}
Price (INR): ₹{machine.price_inr:,}
Max Sheet Thickness: {machine.max_sheet_thickness_mm}mm
Heater Power: {machine.heater_power_kw}kW
Description: {machine.description}
Features: {', '.join(machine.features)}
Applications: {', '.join(machine.applications)}
""".strip()
                
                results.append(MemorySearchResult(
                    source="machine_database",
                    content=content,
                    relevance_score=1.0,  # Exact match
                    metadata={"model": model, "price_inr": machine.price_inr}
                ))
        
        return results
    
    def _search_knowledge_graph(
        self,
        query: str,
        understanding: QueryUnderstanding,
        limit: int
    ) -> List[MemorySearchResult]:
        """
        Search knowledge graph for entity relationships.
        
        Finds related entities and their relationships to provide
        additional context beyond direct memory matches.
        """
        results = []
        
        if not self._knowledge_graph:
            return results
        
        try:
            # Extract entities from query
            entities_to_search = []
            
            # Get machine entities from understanding
            if understanding.entities.get("machines"):
                entities_to_search.extend(understanding.entities["machines"])
            
            # Also try extracting with entity extractor for broader coverage
            if self._entity_extractor:
                extracted = self._entity_extractor.extract(query)
                entities_to_search.extend(extracted.machines)
                entities_to_search.extend(extracted.applications)
                entities_to_search.extend(extracted.materials)
            
            # Deduplicate
            entities_to_search = list(set(entities_to_search))
            
            if not entities_to_search:
                return results
            
            self.logger.info(f"  Searching knowledge graph for entities: {entities_to_search}")
            
            # Query knowledge graph for each entity
            seen_relationships = set()
            
            for entity in entities_to_search[:3]:  # Limit to top 3 entities
                try:
                    # Get related nodes via graph traversal (depth 2 for friends-of-friends)
                    related = self._knowledge_graph.get_related(
                        entity_or_id=entity,
                        depth=2,
                        relationship_types=None  # All relationship types
                    )
                    
                    for node, edge in related[:limit]:
                        # Create unique key to avoid duplicates
                        rel_key = (edge.source_id, edge.target_id, edge.relationship_type)
                        if rel_key in seen_relationships:
                            continue
                        seen_relationships.add(rel_key)
                        
                        # Format relationship as context
                        relationship_text = self._format_kg_relationship(entity, node, edge)
                        
                        results.append(MemorySearchResult(
                            source="knowledge_graph",
                            content=relationship_text,
                            relevance_score=edge.strength * 0.8,  # Slightly lower than direct matches
                            metadata={
                                "source_entity": entity,
                                "related_entity": node.entity,
                                "relationship_type": edge.relationship_type,
                                "node_topic": node.topic,
                            }
                        ))
                        
                except Exception as e:
                    self.logger.debug(f"  KG search for '{entity}' failed: {e}")
            
            self.logger.info(f"  Knowledge graph: found {len(results)} relationships")
            
        except Exception as e:
            self.logger.error(f"Knowledge graph search error: {e}")
        
        return results[:limit]
    
    def _format_kg_relationship(self, query_entity: str, node, edge) -> str:
        """Format a knowledge graph relationship as readable context."""
        rel_type = edge.relationship_type.replace("_", " ")
        
        # Build context string based on relationship type
        if edge.relationship_type == "same_series":
            return f"{query_entity} is in the same series as {node.entity}. {node.text[:200]}"
        
        elif edge.relationship_type == "same_model_family":
            return f"{query_entity} and {node.entity} are in the same model family. {node.text[:200]}"
        
        elif edge.relationship_type == "size_progression":
            direction = edge.metadata.get("direction", "related")
            size_info = edge.metadata.get("size_increase", "")
            return f"{node.entity} is a {direction} option from {query_entity} (size diff: {size_info}mm). {node.text[:200]}"
        
        elif edge.relationship_type == "application_overlap":
            apps = edge.metadata.get("common_applications", [])
            return f"{query_entity} and {node.entity} share applications: {', '.join(apps)}. {node.text[:200]}"
        
        elif edge.relationship_type == "material_compatibility":
            mats = edge.metadata.get("common_materials", [])
            return f"{query_entity} and {node.entity} both process: {', '.join(mats)}. {node.text[:200]}"
        
        elif edge.relationship_type == "similar_content":
            return f"Related knowledge to {query_entity}: {node.text[:250]}"
        
        elif edge.relationship_type == "same_cluster":
            return f"Related topic to {query_entity} (cluster: {edge.metadata.get('cluster', 'unknown')}): {node.text[:200]}"
        
        else:
            return f"{query_entity} is {rel_type} to {node.entity}: {node.text[:200]}"
    
    def _search_competitive_intel(
        self,
        query: str,
        competitors: List[str]
    ) -> List[MemorySearchResult]:
        """
        Search competitive intelligence for competitor comparisons.
        
        Returns structured competitor analysis as memory search results.
        """
        results = []
        
        if not competitors:
            return results
        
        self.logger.info(f"  Searching competitive intelligence for: {competitors}")
        
        try:
            # Get comparison data for each competitor
            comparisons = self._competitive_intel.get_comparison(query, competitors)
            
            for comp in comparisons:
                # Format as detailed context
                content = self._format_competitor_context(comp)
                
                results.append(MemorySearchResult(
                    source="competitive_intel",
                    content=content,
                    relevance_score=0.95,  # High relevance when competitor is explicitly mentioned
                    metadata={
                        "competitor": comp["competitor"],
                        "country": comp["country"],
                        "price_position": comp["price_position"],
                        "is_comparison_query": True,
                    }
                ))
            
            # Add Machinecraft positioning strategy as a separate result
            if comparisons:
                strategy = self._get_positioning_strategy(competitors)
                results.append(MemorySearchResult(
                    source="competitive_intel",
                    content=strategy,
                    relevance_score=0.90,
                    metadata={
                        "type": "positioning_strategy",
                        "competitors_addressed": competitors,
                    }
                ))
            
            self.logger.info(f"  Competitive intel: found {len(results)} comparison results")
            
        except Exception as e:
            self.logger.error(f"Competitive intelligence search error: {e}")
        
        return results
    
    def _format_competitor_context(self, comp: Dict[str, Any]) -> str:
        """Format competitor comparison as readable context."""
        lines = [
            f"## {comp['competitor']} ({comp['country']})",
            f"Price vs Machinecraft: {comp['price_position']}",
            f"Market positioning: {comp['positioning']}",
        ]
        
        if comp['strengths']:
            lines.append(f"Their strengths: {', '.join(comp['strengths'])}")
        
        if comp['weaknesses']:
            lines.append(f"Their weaknesses: {', '.join(comp['weaknesses'])}")
        
        lines.append(f"Typical customers: {comp['typical_customers']}")
        
        if comp.get('notable_models'):
            lines.append(f"Notable models: {', '.join(comp['notable_models'])}")
        
        return "\n".join(lines)
    
    def _get_positioning_strategy(self, competitors: List[str]) -> str:
        """Get Machinecraft positioning strategy against specific competitors."""
        # Determine competitor tier for strategy
        european_premium = {"ILLIG", "Kiefel", "GEISS", "FRIMO"}
        north_american = {"GN Thermoforming", "Brown Machine"}
        asian_budget = {"Litai"}
        
        competitor_set = set(competitors)
        
        lines = ["## Machinecraft Positioning Strategy"]
        
        if competitor_set & european_premium:
            lines.extend([
                "Against European premium brands:",
                "- Emphasize 40-60% cost savings with comparable quality",
                "- Highlight 8-12 week delivery vs 6-9 months",
                "- Stress local support and responsiveness",
                "- Focus on customization capability",
            ])
        
        if competitor_set & north_american:
            lines.extend([
                "Against North American options:",
                "- Competitive pricing with better value",
                "- Strong technical support via remote diagnostics",
                "- Proven track record in similar applications",
            ])
        
        if competitor_set & asian_budget:
            lines.extend([
                "Against budget Asian options:",
                "- Superior build quality and longevity",
                "- Better resale value",
                "- Professional after-sales support",
                "- Lower total cost of ownership",
            ])
        
        lines.extend([
            "",
            "General guidelines:",
            "- Be professional and factual; never disparage competitors",
            "- Focus on Machinecraft's strengths that address customer needs",
            "- Offer factory visits or reference customers when appropriate",
        ])
        
        return "\n".join(lines)


# =============================================================================
# NEAREST NEIGHBOR DOCUMENT SELECTION - Step 3
# =============================================================================

class DocumentSelector:
    """Select the most relevant documents from data/imports/."""
    
    # Document categories and patterns
    DOCUMENT_CATEGORIES = {
        "price_list": {
            "patterns": ["price", "pricing", "plastindia", "quote", "cost"],
            "files": ["Price List", "Quotation", "Quote"],
        },
        "catalogue": {
            "patterns": ["catalogue", "catalog", "brochure", "machine", "series"],
            "files": ["Catalogue", "Brochure", "Machine"],
        },
        "quotation": {
            "patterns": ["pf1", "pf2", "am", "fcs", "quote", "offer"],
            "files": ["PF1", "Quotation", "Offer"],
        },
        "technical": {
            "patterns": ["spec", "technical", "manual", "operating"],
            "files": ["Manual", "Specification", "Technical"],
        },
        "company": {
            "patterns": ["company", "about", "history", "machinecraft"],
            "files": ["Company", "About", "History", "Evolution"],
        },
        "market": {
            "patterns": ["market", "analysis", "industry", "competitor"],
            "files": ["Market", "Analysis", "Industry"],
        },
    }
    
    def __init__(self):
        self.logger = logging.getLogger("ira.doc_selector")
        self.imports_dir = IMPORTS_DIR
        self._file_embeddings_cache = {}
    
    def select_documents(
        self,
        query: str,
        understanding: QueryUnderstanding,
        max_documents: int = 3
    ) -> List[DocumentMatch]:
        """Select most relevant documents using nearest neighbor."""
        self.logger.info(f"Selecting documents for: {query[:50]}...")
        
        # Get all available files
        available_files = self._get_available_files()
        self.logger.info(f"  Found {len(available_files)} files in imports/")
        
        if not available_files:
            return []
        
        # Score documents based on multiple factors
        scored_docs = []
        
        for filepath in available_files:
            score = self._score_document(filepath, query, understanding)
            if score > 0.1:  # Minimum threshold
                scored_docs.append((filepath, score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Extract chunks from top documents
        matches = []
        for filepath, score in scored_docs[:max_documents]:
            try:
                chunks = self._extract_relevant_chunks(filepath, query)
                matches.append(DocumentMatch(
                    filename=filepath.name,
                    filepath=filepath,
                    relevance_score=score,
                    matched_chunks=chunks,
                    file_type=filepath.suffix.lower()[1:]
                ))
                self.logger.info(f"  ✓ {filepath.name}: {score:.2f} ({len(chunks)} chunks)")
            except Exception as e:
                self.logger.error(f"  Error extracting {filepath.name}: {e}")
        
        return matches
    
    def _get_available_files(self) -> List[Path]:
        """Get all readable files from imports directory."""
        files = []
        
        if not self.imports_dir.exists():
            return files
        
        for ext in ["*.pdf", "*.xlsx", "*.docx", "*.csv", "*.txt"]:
            files.extend(self.imports_dir.glob(ext))
            # Also check Quotes subdirectory
            files.extend((self.imports_dir / "Quotes").glob(ext))
        
        return [f for f in files if f.is_file() and not f.name.startswith('.')]
    
    def _score_document(
        self,
        filepath: Path,
        query: str,
        understanding: QueryUnderstanding
    ) -> float:
        """Score a document's relevance to the query."""
        score = 0.0
        filename_lower = filepath.name.lower()
        
        # 1. Category matching (based on query intent)
        intent = understanding.intent
        if intent in self.DOCUMENT_CATEGORIES:
            category = self.DOCUMENT_CATEGORIES[intent]
            for pattern in category["patterns"]:
                if pattern in filename_lower:
                    score += 0.3
                    break
            for file_pattern in category["files"]:
                if file_pattern.lower() in filename_lower:
                    score += 0.2
                    break
        
        # 2. Entity matching (machines, materials mentioned)
        for machines in understanding.entities.get("machines", []):
            if machines.lower() in filename_lower:
                score += 0.4
        
        # 3. Keyword matching
        for keyword in understanding.keywords[:5]:
            if keyword in filename_lower:
                score += 0.15
        
        # 4. Query terms in filename
        query_words = set(query.lower().split())
        filename_words = set(re.findall(r'\w+', filename_lower))
        overlap = len(query_words & filename_words)
        score += overlap * 0.1
        
        # 5. Special case: Price-related queries
        if understanding.intent == "pricing":
            if any(p in filename_lower for p in ["price", "quote", "plastindia", "offer"]):
                score += 0.3
        
        return min(score, 1.0)
    
    def _extract_relevant_chunks(
        self,
        filepath: Path,
        query: str,
        max_chunks: int = 3
    ) -> List[str]:
        """Extract relevant text chunks from a document."""
        chunks = []
        
        try:
            if filepath.suffix.lower() == ".pdf" and PDF_AVAILABLE:
                chunks = self._extract_from_pdf(filepath, query, max_chunks)
            elif filepath.suffix.lower() in [".xlsx", ".csv"] and PANDAS_AVAILABLE:
                chunks = self._extract_from_excel(filepath, query, max_chunks)
            elif filepath.suffix.lower() == ".txt":
                chunks = self._extract_from_text(filepath, query, max_chunks)
        except Exception as e:
            self.logger.error(f"Chunk extraction error for {filepath.name}: {e}")
        
        return chunks
    
    def _extract_from_pdf(self, filepath: Path, query: str, max_chunks: int) -> List[str]:
        """Extract relevant chunks from PDF."""
        chunks = []
        
        with pdfplumber.open(str(filepath)) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += text + "\n"
            
            if all_text:
                # Split into paragraphs
                paragraphs = [p.strip() for p in all_text.split('\n\n') if p.strip()]
                
                # Score paragraphs by relevance to query
                query_terms = set(query.lower().split())
                scored = []
                
                for para in paragraphs:
                    if len(para) < 50:
                        continue
                    para_terms = set(para.lower().split())
                    overlap = len(query_terms & para_terms)
                    scored.append((para, overlap))
                
                # Sort and take top
                scored.sort(key=lambda x: x[1], reverse=True)
                chunks = [p for p, _ in scored[:max_chunks]]
        
        return chunks
    
    def _extract_from_excel(self, filepath: Path, query: str, max_chunks: int) -> List[str]:
        """Extract relevant chunks from Excel/CSV."""
        chunks = []
        
        try:
            if filepath.suffix.lower() == ".csv":
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Convert to text
            text = df.to_string()
            
            # Take first chunk and relevant rows
            chunks.append(text[:1000])
            
            # Search for query terms in rows
            query_terms = query.lower().split()
            for idx, row in df.iterrows():
                row_text = " ".join(str(v) for v in row.values)
                if any(term in row_text.lower() for term in query_terms):
                    chunks.append(row_text[:500])
                    if len(chunks) >= max_chunks:
                        break
        except Exception as e:
            self.logger.error(f"Excel extraction error: {e}")
        
        return chunks[:max_chunks]
    
    def _extract_from_text(self, filepath: Path, query: str, max_chunks: int) -> List[str]:
        """Extract relevant chunks from text file."""
        text = filepath.read_text(errors='ignore')
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        return paragraphs[:max_chunks]


# =============================================================================
# CONFLICT DETECTION - Step 3.5 (Critical Safety Check)
# =============================================================================

class RetrievalConflictDetector:
    """
    Detect conflicts in retrieved data BEFORE generating a response.
    
    This is a critical safety check to prevent IRA from stating contradictory facts.
    If a conflict is found, the pipeline halts and returns a conflict response.
    
    Types of conflicts detected:
    - Price conflicts: Same machine, different prices
    - Spec conflicts: Same machine, different specifications
    - Fact conflicts: Contradictory statements about same entity
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.conflict_detector")
        
        # Try to import the document_ingestor ConflictDetector for enhanced detection
        try:
            sys.path.insert(0, str(SRC_DIR / "memory"))
            from document_ingestor import ConflictDetector as DocConflictDetector
            self.doc_conflict_detector = DocConflictDetector()
            self.enhanced_detection = True
        except ImportError:
            self.doc_conflict_detector = None
            self.enhanced_detection = False
        
        # Load learned corrections to check against
        self.corrections_file = BRAIN_DIR / "learned_corrections.json"
        self.corrections = self._load_corrections()
    
    def _load_corrections(self) -> Dict:
        """Load previously learned corrections."""
        if self.corrections_file.exists():
            try:
                return json.loads(self.corrections_file.read_text())
            except:
                pass
        return {"corrections": [], "competitors": [], "existing_customers": []}
    
    def find_conflicts(
        self,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch],
        understanding: 'QueryUnderstanding'
    ) -> Optional[ConflictResult]:
        """
        Find conflicts in the retrieved data.
        
        Args:
            memory_results: Results from Mem0, Qdrant, Machine DB
            document_matches: Relevant documents found
            understanding: Query understanding for context
        
        Returns:
            ConflictResult if conflict found, None otherwise
        """
        self.logger.info("Checking for conflicts in retrieved data...")
        
        # Check 1: Price conflicts
        price_conflict = self._check_price_conflicts(memory_results, document_matches)
        if price_conflict and price_conflict.severity == "critical":
            self.logger.warning(f"CRITICAL: Price conflict detected for {price_conflict.entity}")
            return price_conflict
        
        # Check 2: Spec conflicts
        spec_conflict = self._check_spec_conflicts(memory_results, document_matches)
        if spec_conflict and spec_conflict.severity == "critical":
            self.logger.warning(f"CRITICAL: Spec conflict detected for {spec_conflict.entity}")
            return spec_conflict
        
        # Check 3: Fact conflicts (using LLM if enhanced detection available)
        if self.enhanced_detection:
            fact_conflict = self._check_fact_conflicts(memory_results, understanding)
            if fact_conflict and fact_conflict.severity == "critical":
                self.logger.warning(f"CRITICAL: Fact conflict detected for {fact_conflict.entity}")
                return fact_conflict
        
        # Check 4: Conflicts with learned corrections
        correction_conflict = self._check_against_corrections(memory_results)
        if correction_conflict:
            self.logger.warning(f"Data conflicts with learned correction: {correction_conflict.entity}")
            return correction_conflict
        
        self.logger.info("No critical conflicts detected")
        return None
    
    def _check_price_conflicts(
        self,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> Optional[ConflictResult]:
        """Check for price conflicts for the same machine."""
        prices_by_machine: Dict[str, List[Tuple[int, str]]] = {}
        
        # Extract prices from memory results
        for mem in memory_results:
            content = mem.content.lower()
            
            # Find machine model mentions
            machine_patterns = [
                r'(pf1[-\s]?[a-z][-\s]?\d{4})',
                r'(pf2[-\s]?[a-z]?[-\s]?\d{4})',
                r'(atf[-\s]?\d+[-\s]?[a-z]?)',
                r'(am[-\s]?\d+)',
            ]
            
            for pattern in machine_patterns:
                machine_match = re.search(pattern, content, re.IGNORECASE)
                if machine_match:
                    machine = machine_match.group(1).upper().replace(' ', '-')
                    
                    # Find price mentions
                    price_patterns = [
                        r'₹\s*([\d,]+)',
                        r'rs\.?\s*([\d,]+)',
                        r'([\d,]+)\s*(?:lakh|lac)',
                        r'price[:\s]+([\d,]+)',
                    ]
                    
                    for price_pattern in price_patterns:
                        price_match = re.search(price_pattern, content, re.IGNORECASE)
                        if price_match:
                            try:
                                price_str = price_match.group(1).replace(',', '')
                                price = int(price_str)
                                
                                # Normalize to lakhs if needed
                                if price < 10000:
                                    price = price * 100000  # Assume lakhs
                                
                                if machine not in prices_by_machine:
                                    prices_by_machine[machine] = []
                                prices_by_machine[machine].append((price, mem.source))
                            except ValueError:
                                pass
        
        # Check for conflicts (>10% difference)
        for machine, prices in prices_by_machine.items():
            if len(prices) < 2:
                continue
            
            values = [p[0] for p in prices]
            min_price, max_price = min(values), max(values)
            
            if max_price > 0 and (max_price - min_price) / max_price > 0.10:
                return ConflictResult(
                    has_conflict=True,
                    conflict_type="price",
                    conflicting_values=[f"₹{p[0]:,} from {p[1]}" for p in prices],
                    sources=[p[1] for p in prices],
                    entity=machine,
                    severity="critical",
                    recommendation=f"Multiple prices found for {machine}: ₹{min_price:,} to ₹{max_price:,}. Human review required."
                )
        
        return None
    
    def _check_spec_conflicts(
        self,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> Optional[ConflictResult]:
        """Check for specification conflicts for the same machine."""
        specs_by_machine: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        
        # Key specs to check
        spec_patterns = {
            "heater_power": r'heater[:\s]+(\d+)\s*kw',
            "forming_area": r'forming\s*area[:\s]+([\d]+)\s*[x×]\s*([\d]+)',
            "vacuum_pump": r'vacuum[:\s]+(\d+)\s*(?:m3|cfm)',
            "tonnage": r'(\d+)\s*(?:ton|tonne)',
        }
        
        for mem in memory_results:
            content = mem.content.lower()
            
            # Find machine
            machine_match = re.search(r'(pf1|pf2|atf|am|spm|bpm)[-\s]?[a-z0-9-]+', content, re.IGNORECASE)
            if not machine_match:
                continue
            
            machine = machine_match.group(0).upper().replace(' ', '-')
            
            if machine not in specs_by_machine:
                specs_by_machine[machine] = {}
            
            # Find specs
            for spec_name, pattern in spec_patterns.items():
                spec_match = re.search(pattern, content, re.IGNORECASE)
                if spec_match:
                    value = spec_match.group(1)
                    if spec_name not in specs_by_machine[machine]:
                        specs_by_machine[machine][spec_name] = []
                    specs_by_machine[machine][spec_name].append((value, mem.source))
        
        # Check for conflicts
        for machine, specs in specs_by_machine.items():
            for spec_name, values in specs.items():
                if len(values) < 2:
                    continue
                
                unique_values = set(v[0] for v in values)
                if len(unique_values) > 1:
                    return ConflictResult(
                        has_conflict=True,
                        conflict_type="spec",
                        conflicting_values=[f"{v[0]} from {v[1]}" for v in values],
                        sources=[v[1] for v in values],
                        entity=f"{machine} {spec_name}",
                        severity="critical",
                        recommendation=f"Conflicting {spec_name} values for {machine}. Human review required."
                    )
        
        return None
    
    def _check_fact_conflicts(
        self,
        memory_results: List[MemorySearchResult],
        understanding: 'QueryUnderstanding'
    ) -> Optional[ConflictResult]:
        """Use LLM to detect subtle fact conflicts."""
        if len(memory_results) < 2:
            return None
        
        # Get content from memory results
        contents = [mem.content for mem in memory_results[:5]]  # Limit to 5
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            prompt = f"""Analyze these retrieved facts for any contradictions:

FACTS:
{chr(10).join(f'{i+1}. {c[:300]}' for i, c in enumerate(contents))}

QUESTION CONTEXT: {understanding.intent}

Are there any contradictory facts? Output JSON:
{{"has_conflict": true/false, "conflict_type": "fact/none", "entity": "what entity", "details": "explanation"}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Detect factual contradictions. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("has_conflict"):
                    return ConflictResult(
                        has_conflict=True,
                        conflict_type="fact",
                        conflicting_values=[data.get("details", "Unknown conflict")],
                        sources=[mem.source for mem in memory_results[:3]],
                        entity=data.get("entity", "unknown"),
                        severity="critical" if "price" in data.get("details", "").lower() else "warning",
                        recommendation=f"Conflicting facts detected: {data.get('details', '')}"
                    )
        except Exception as e:
            self.logger.error(f"LLM conflict detection error: {e}")
        
        return None
    
    def _check_against_corrections(
        self,
        memory_results: List[MemorySearchResult]
    ) -> Optional[ConflictResult]:
        """Check if retrieved data conflicts with learned corrections."""
        corrections = self.corrections.get("corrections", [])
        
        for mem in memory_results:
            content = mem.content.lower()
            
            for correction in corrections:
                incorrect = str(correction.get("incorrect", "")).lower()
                correct = str(correction.get("correct", "")).lower()
                topic = correction.get("topic", "")
                
                # If content contains the incorrect value but not the correct one
                if incorrect and incorrect in content and correct and correct not in content:
                    return ConflictResult(
                        has_conflict=True,
                        conflict_type="correction_violation",
                        conflicting_values=[
                            f"Retrieved: {incorrect}",
                            f"Corrected: {correct}"
                        ],
                        sources=[mem.source],
                        entity=topic,
                        severity="critical",
                        recommendation=f"Retrieved data contains previously corrected error: '{incorrect}' should be '{correct}'"
                    )
        
        return None


# =============================================================================
# SELF-REASONING & VALIDATION - Step 4
# =============================================================================

class ReasoningEngine:
    """ReAct-style reasoning for answer validation."""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.reasoning")
    
    def reason(
        self,
        query: str,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> Tuple[List[ReasoningStep], float]:
        """Reason about the answer using ReAct pattern."""
        self.logger.info("Starting reasoning chain...")
        
        steps = []
        confidence = 0.0
        
        # Step 1: Assess what we found
        step1 = self._assess_evidence(memory_results, document_matches, understanding)
        steps.append(step1)
        
        # Step 2: Validate against query intent
        step2 = self._validate_against_intent(understanding, memory_results, document_matches)
        steps.append(step2)
        
        # Step 3: Check for conflicts
        step3 = self._check_conflicts(memory_results, document_matches)
        steps.append(step3)
        
        # Step 4: Synthesize answer
        step4 = self._synthesize_answer(understanding, memory_results, document_matches)
        steps.append(step4)
        
        # Calculate overall confidence
        confidence = sum(s.confidence for s in steps) / len(steps)
        
        self.logger.info(f"Reasoning complete. Confidence: {confidence:.2f}")
        
        return steps, confidence
    
    def _assess_evidence(
        self,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch],
        understanding: QueryUnderstanding
    ) -> ReasoningStep:
        """Assess what evidence we have."""
        thought = f"The query is asking about '{understanding.intent}'. "
        thought += f"I found {len(memory_results)} memory results and {len(document_matches)} document matches."
        
        action = "Evaluate evidence quality"
        
        # Check if we have high-quality matches
        high_quality_memory = sum(1 for m in memory_results if m.relevance_score > 0.7)
        high_quality_docs = sum(1 for d in document_matches if d.relevance_score > 0.5)
        
        observation = f"Found {high_quality_memory} high-quality memories and {high_quality_docs} relevant documents."
        
        confidence = min((high_quality_memory + high_quality_docs) / 5, 1.0)
        
        return ReasoningStep(
            thought=thought,
            action=action,
            observation=observation,
            confidence=confidence
        )
    
    def _validate_against_intent(
        self,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> ReasoningStep:
        """Validate results match query intent."""
        intent = understanding.intent
        
        thought = f"The user wants '{intent}' information. Let me check if results address this."
        action = f"Validate results for {intent} intent"
        
        # Check if results contain intent-specific content
        all_content = " ".join(m.content for m in memory_results)
        all_content += " ".join(" ".join(d.matched_chunks) for d in document_matches)
        content_lower = all_content.lower()
        
        intent_keywords = {
            "pricing": ["price", "₹", "inr", "cost", "lakh", "crore"],
            "specs": ["mm", "kw", "capacity", "dimension", "power"],
            "recommendation": ["suitable", "recommend", "ideal", "best"],
            "comparison": ["vs", "compare", "difference"],
        }
        
        keywords = intent_keywords.get(intent, [])
        found_keywords = sum(1 for k in keywords if k in content_lower)
        
        if found_keywords > 0:
            observation = f"Results contain {found_keywords} intent-relevant keywords. Good match."
            confidence = min(found_keywords / len(keywords) if keywords else 0.5, 1.0)
        else:
            observation = "Results may not directly address the query intent."
            confidence = 0.3
        
        return ReasoningStep(
            thought=thought,
            action=action,
            observation=observation,
            confidence=confidence
        )
    
    def _check_conflicts(
        self,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> ReasoningStep:
        """Check for conflicting information."""
        thought = "Checking for any conflicting information in the results."
        action = "Conflict detection"
        
        # Simple conflict detection: Look for different prices for same machine
        prices = {}
        conflicts = []
        
        for result in memory_results:
            # Extract prices from content
            price_matches = re.findall(r'₹([\d,]+)', result.content)
            model_matches = re.findall(r'(PF1-[A-Z]-\d{4}|AM-\d{4})', result.content)
            
            for model in model_matches:
                for price in price_matches:
                    price_val = int(price.replace(',', ''))
                    if model in prices and abs(prices[model] - price_val) > 100000:
                        conflicts.append(f"{model}: ₹{prices[model]:,} vs ₹{price_val:,}")
                    prices[model] = price_val
        
        if conflicts:
            observation = f"Found {len(conflicts)} potential price conflicts: {conflicts[:2]}"
            confidence = 0.5
        else:
            observation = "No obvious conflicts found in the data."
            confidence = 0.9
        
        return ReasoningStep(
            thought=thought,
            action=action,
            observation=observation,
            confidence=confidence
        )
    
    def _synthesize_answer(
        self,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> ReasoningStep:
        """Synthesize the final answer."""
        thought = "Combining all evidence to form a comprehensive answer."
        action = "Answer synthesis"
        
        # Count sources used
        sources = set()
        sources.update(m.source for m in memory_results)
        sources.update(f"doc:{d.filename}" for d in document_matches)
        
        total_content = sum(len(m.content) for m in memory_results)
        total_content += sum(len(" ".join(d.matched_chunks)) for d in document_matches)
        
        if total_content > 500:
            observation = f"Synthesized answer from {len(sources)} sources with {total_content} characters of context."
            confidence = 0.85
        elif total_content > 100:
            observation = f"Limited context available ({total_content} chars) but can formulate response."
            confidence = 0.6
        else:
            observation = "Insufficient context for confident answer. May need to ask clarifying questions."
            confidence = 0.3
        
        return ReasoningStep(
            thought=thought,
            action=action,
            observation=observation,
            confidence=confidence
        )


# =============================================================================
# QUESTION GENERATION - Step 6
# =============================================================================

class QuestionGenerator:
    """Generate follow-up questions for Rushabh."""
    
    QUESTION_TEMPLATES = {
        "pricing": [
            "Should I provide a detailed quotation for {entity}?",
            "Would you like me to compare pricing with alternative machines?",
            "Is the budget range around ₹{price_range} workable for this customer?",
        ],
        "specs": [
            "Should I include the full technical specifications in the response?",
            "Are there specific features the customer prioritized?",
            "Do we have any installation reference for this configuration?",
        ],
        "recommendation": [
            "Should I prioritize cost-efficiency or production capacity in this recommendation?",
            "Are there any specific constraints (space, power) I should consider?",
            "Would a factory visit be helpful for this customer?",
        ],
        "comparison": [
            "Which factors matter most: price, capacity, or features?",
            "Should I include lead time comparison?",
            "Are there competitive machines they're also considering?",
        ],
        "general": [
            "Is there additional context from past interactions with this customer?",
            "Should I suggest scheduling a call to discuss further?",
            "Would a detailed proposal be appropriate at this stage?",
        ],
    }
    
    def __init__(self):
        self.logger = logging.getLogger("ira.question_gen")
    
    def generate(
        self,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        confidence: float
    ) -> List[FollowUpQuestion]:
        """Generate relevant follow-up questions."""
        self.logger.info("Generating follow-up questions...")
        
        questions = []
        intent = understanding.intent
        templates = self.QUESTION_TEMPLATES.get(intent, self.QUESTION_TEMPLATES["general"])
        
        # Generate questions based on context
        entities = understanding.entities
        
        # Question 1: Based on what we found
        if confidence < 0.7:
            questions.append(FollowUpQuestion(
                question="I'm not 100% confident in my answer. Should I dig deeper or check with the team?",
                purpose="clarify",
                priority="high"
            ))
        
        # Question 2: Entity-specific
        if entities.get("machines"):
            machine = entities["machines"][0]
            questions.append(FollowUpQuestion(
                question=f"Should I include detailed specs for {machine} in my response?",
                purpose="expand",
                priority="medium"
            ))
        
        # Question 3: Intent-specific from templates
        if templates:
            template = templates[0]
            # Try to fill in template
            entity = entities.get("machines", ["this machine"])[0] if entities.get("machines") else "this machine"
            filled = template.format(entity=entity, price_range="50-80 Lakhs")
            
            questions.append(FollowUpQuestion(
                question=filled,
                purpose="suggest",
                priority="medium"
            ))
        
        # Question 4: Next steps
        questions.append(FollowUpQuestion(
            question="Would you like me to schedule a follow-up with the customer?",
            purpose="suggest",
            priority="low"
        ))
        
        return questions[:3]  # Return top 3


# =============================================================================
# RESPONSE GENERATION - Step 5
# =============================================================================

class ResponseGenerator:
    """Generate responses with IRA's personality."""
    
    IRA_PERSONALITY = """You are IRA, Machinecraft's AI sales assistant.

Communication Style:
- Professional yet warm and personable
- Technical expertise delivered in accessible language  
- Proactive in suggesting solutions
- Confident but not pushy
- Uses bullet points and tables for clarity

Key Behaviors:
- Always provide specific machine recommendations when asked
- Include prices in INR when available
- Mention relevant features and applications
- Suggest next steps (call, factory visit, quotation)
- Ask clarifying questions if needed

Sign off style: "Let me know if you need anything else!" or similar warm closing
"""
    
    def __init__(self):
        self.logger = logging.getLogger("ira.response_gen")
    
    def generate(
        self,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch],
        reasoning_steps: List[ReasoningStep],
        channel: str = "email"
    ) -> str:
        """Generate a response with IRA's personality."""
        self.logger.info("Generating response...")
        
        if not OPENAI_AVAILABLE:
            return self._generate_fallback(understanding, memory_results, document_matches)
        
        # Build context
        context_parts = []
        
        # Add memory context
        for mem in memory_results[:5]:
            context_parts.append(f"[{mem.source}]\n{mem.content[:500]}")
        
        # Add document context
        for doc in document_matches[:3]:
            chunks_text = "\n".join(doc.matched_chunks[:2])
            context_parts.append(f"[From: {doc.filename}]\n{chunks_text[:500]}")
        
        # Add reasoning summary
        reasoning_summary = "\n".join([
            f"- {step.thought} → {step.observation}"
            for step in reasoning_steps[-2:]
        ])
        
        context = "\n\n".join(context_parts)
        
        # Generate with LLM
        system_prompt = self.IRA_PERSONALITY
        
        user_prompt = f"""CUSTOMER QUERY:
{understanding.original_query}

QUERY INTENT: {understanding.intent}
ENTITIES DETECTED: {json.dumps(understanding.entities)}

RESEARCH FINDINGS:
{context}

REASONING:
{reasoning_summary}

Based on the above, generate a helpful response as IRA.
- Be specific with prices and specs if available
- Use appropriate formatting for {channel}
- Keep it concise but complete (300-500 words)
- Include a call to action or next step"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"LLM generation error: {e}")
            return self._generate_fallback(understanding, memory_results, document_matches)
    
    def _generate_fallback(
        self,
        understanding: QueryUnderstanding,
        memory_results: List[MemorySearchResult],
        document_matches: List[DocumentMatch]
    ) -> str:
        """Fallback response generation without LLM."""
        parts = [f"Regarding your question about {understanding.intent}:\n"]
        
        # Add relevant content
        for mem in memory_results[:2]:
            if "machine_database" in mem.source:
                parts.append(mem.content)
        
        parts.append("\nLet me know if you need more details!")
        
        return "\n\n".join(parts)


# =============================================================================
# MAIN PIPELINE
# =============================================================================

class DeepResearchPipeline:
    """
    Complete deep research pipeline for thorough answer generation.
    
    This is the main class that orchestrates all components.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ira.deep_research")
        
        # Initialize components
        self.query_analyzer = QueryAnalyzer()
        self.memory_search = MultiSourceMemorySearch()
        self.document_selector = DocumentSelector()
        self.conflict_detector = RetrievalConflictDetector()  # NEW: Conflict detection
        self.reasoning_engine = ReasoningEngine()
        self.question_generator = QuestionGenerator()
        self.response_generator = ResponseGenerator()
        
        self.logger.info("Deep Research Pipeline initialized")
        self.logger.info("  - Conflict detection: ENABLED")
        self.logger.info(f"  - Knowledge graph: {'ENABLED' if KNOWLEDGE_GRAPH_AVAILABLE else 'DISABLED'}")
        self.logger.info("  - Competitive intelligence: ENABLED")
    
    def research(
        self,
        query: str,
        user_id: str,
        channel: str = "email",
        verbose: bool = True
    ) -> DeepResearchResult:
        """
        Run the complete deep research pipeline.
        
        Args:
            query: The user's query/email
            user_id: User identifier (email address, chat ID, etc.)
            channel: Communication channel (email, telegram, api)
            verbose: Whether to log detailed progress
        
        Returns:
            DeepResearchResult with all findings and generated response
        """
        start_time = time.time()
        
        if verbose:
            self.logger.info("=" * 60)
            self.logger.info("DEEP RESEARCH PIPELINE")
            self.logger.info("=" * 60)
            self.logger.info(f"Query: {query[:100]}...")
            self.logger.info(f"User: {user_id}")
            self.logger.info(f"Channel: {channel}")
        
        # Step 1: Understand the query
        if verbose:
            self.logger.info("\n[STEP 1] Understanding query...")
        understanding = self.query_analyzer.analyze(query)
        if verbose:
            self.logger.info(f"  Intent: {understanding.intent}")
            self.logger.info(f"  Complexity: {understanding.complexity}")
            self.logger.info(f"  Questions: {understanding.core_questions}")
        
        # Step 2: Search memories
        if verbose:
            self.logger.info("\n[STEP 2] Searching memories...")
        memory_results = self.memory_search.search(
            query=query,
            user_id=user_id,
            understanding=understanding
        )
        if verbose:
            self.logger.info(f"  Found {len(memory_results)} memory results")
        
        # Step 3: Select documents
        if verbose:
            self.logger.info("\n[STEP 3] Selecting documents...")
        document_matches = self.document_selector.select_documents(
            query=query,
            understanding=understanding
        )
        if verbose:
            self.logger.info(f"  Selected {len(document_matches)} documents")
            for doc in document_matches:
                self.logger.info(f"    - {doc.filename} (score: {doc.relevance_score:.2f})")
        
        # Step 3.5: CONFLICT DETECTION (Critical Safety Check)
        if verbose:
            self.logger.info("\n[STEP 3.5] Checking for conflicts...")
        conflict = self.conflict_detector.find_conflicts(
            memory_results=memory_results,
            document_matches=document_matches,
            understanding=understanding
        )
        
        if conflict and conflict.has_conflict and conflict.severity == "critical":
            # HALT PIPELINE - Return conflict response
            if verbose:
                self.logger.warning("⚠️ CRITICAL CONFLICT DETECTED - HALTING PIPELINE")
                self.logger.warning(f"  Type: {conflict.conflict_type}")
                self.logger.warning(f"  Entity: {conflict.entity}")
                self.logger.warning(f"  Values: {conflict.conflicting_values}")
            
            conflict_response = (
                f"I've found conflicting information about {conflict.entity}.\n\n"
                f"**Conflict Type:** {conflict.conflict_type}\n"
                f"**Details:** {', '.join(conflict.conflicting_values[:3])}\n\n"
                f"To ensure accuracy, I'm flagging this for human review. "
                f"Rushabh will verify the correct information and get back to you shortly.\n\n"
                f"My apologies for any inconvenience!"
            )
            
            processing_time = time.time() - start_time
            
            return DeepResearchResult(
                query=query,
                understanding=understanding,
                memory_results=memory_results,
                document_matches=document_matches,
                reasoning_chain=[],
                draft_response=conflict_response,
                follow_up_questions=[],
                confidence=0.0,  # Zero confidence due to conflict
                processing_time_seconds=processing_time,
                sources_used=[m.source for m in memory_results],
                conflict_detected=True,
                conflict_details=conflict
            )
        
        if verbose:
            self.logger.info("  ✓ No critical conflicts - proceeding")
        
        # Step 4: Reason about the answer
        if verbose:
            self.logger.info("\n[STEP 4] Reasoning...")
        reasoning_steps, confidence = self.reasoning_engine.reason(
            query=query,
            understanding=understanding,
            memory_results=memory_results,
            document_matches=document_matches
        )
        if verbose:
            self.logger.info(f"  Confidence: {confidence:.2f}")
        
        # Step 5: Generate response
        if verbose:
            self.logger.info("\n[STEP 5] Generating response...")
        draft_response = self.response_generator.generate(
            understanding=understanding,
            memory_results=memory_results,
            document_matches=document_matches,
            reasoning_steps=reasoning_steps,
            channel=channel
        )
        if verbose:
            self.logger.info(f"  Response length: {len(draft_response)} chars")
        
        # Step 6: Generate follow-up questions
        if verbose:
            self.logger.info("\n[STEP 6] Generating questions for Rushabh...")
        follow_up_questions = self.question_generator.generate(
            understanding=understanding,
            memory_results=memory_results,
            confidence=confidence
        )
        if verbose:
            for q in follow_up_questions:
                self.logger.info(f"  - [{q.priority}] {q.question}")
        
        # Compile sources
        sources = list(set(m.source for m in memory_results))
        sources.extend([f"doc:{d.filename}" for d in document_matches])
        
        processing_time = time.time() - start_time
        
        if verbose:
            self.logger.info("\n" + "=" * 60)
            self.logger.info(f"COMPLETE in {processing_time:.1f}s | Confidence: {confidence:.2f}")
            self.logger.info("=" * 60)
        
        return DeepResearchResult(
            query=query,
            understanding=understanding,
            memory_results=memory_results,
            document_matches=document_matches,
            reasoning_chain=reasoning_steps,
            draft_response=draft_response,
            follow_up_questions=follow_up_questions,
            confidence=confidence,
            processing_time_seconds=processing_time,
            sources_used=sources,
            conflict_detected=False,  # No conflicts - safe to proceed
            conflict_details=None
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_pipeline_instance = None


def get_pipeline() -> DeepResearchPipeline:
    """Get singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = DeepResearchPipeline()
    return _pipeline_instance


def deep_research(
    query: str,
    user_id: str,
    channel: str = "email"
) -> DeepResearchResult:
    """
    Convenience function for deep research.
    
    Usage:
        result = deep_research(
            query="What is the price of PF1-C-2015?",
            user_id="customer@example.com"
        )
        print(result.draft_response)
    """
    pipeline = get_pipeline()
    return pipeline.research(query, user_id, channel)


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    parser = argparse.ArgumentParser(description="Deep Research Pipeline")
    parser.add_argument("query", nargs="?", default="What is the price of PF1-C-2015?")
    parser.add_argument("--user", default="test@example.com")
    parser.add_argument("--channel", default="email", choices=["email", "telegram", "api"])
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("DEEP RESEARCH PIPELINE - TEST RUN")
    print("=" * 70)
    
    result = deep_research(args.query, args.user, args.channel)
    
    print("\n" + "-" * 70)
    print("DRAFT RESPONSE:")
    print("-" * 70)
    print(result.draft_response)
    
    print("\n" + "-" * 70)
    print("QUESTIONS FOR RUSHABH:")
    print("-" * 70)
    for q in result.follow_up_questions:
        print(f"  [{q.priority}] {q.question}")
    
    print("\n" + "-" * 70)
    print(f"Completed in {result.processing_time_seconds:.1f}s")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Sources: {len(result.sources_used)}")
