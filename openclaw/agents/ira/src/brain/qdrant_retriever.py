#!/usr/bin/env python3
"""
Qdrant Retriever - Vector search for Ira's knowledge base

Provides the canonical retrieval interface used by telegram_gateway.

Features:
- Minimum score threshold to filter low-quality results
- Query expansion for product names
- Voyage + OpenAI embedding support
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        QDRANT_URL, OPENAI_API_KEY, VOYAGE_API_KEY,
        COLLECTIONS,
    )
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False

# Production resilience layer
try:
    from core.resilience import (
        with_resilience, qdrant_breaker, voyage_breaker, openai_breaker,
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

# Quality tracking for consolidated knowledge
try:
    from src.memory.memory_consolidator import MemoryConsolidator
    QUALITY_TRACKING_AVAILABLE = True
except ImportError:
    QUALITY_TRACKING_AVAILABLE = False

if not CONFIG_LOADED:
    CONFIG_LOADED = False
    # Fallback to direct env loading
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    COLLECTIONS = {
        "chunks_voyage": "ira_chunks_v4_voyage",
        "chunks_openai_large": "ira_chunks_v4_openai_large",
        "emails_voyage": "ira_emails_voyage_v2",
        "emails_openai_large": "ira_emails_v4_openai_large",
        "market_research": "ira_market_research_voyage",
    }

# Minimum score thresholds (Voyage cosine similarity typically 0.2-0.5)
MIN_SCORE_THRESHOLD = 0.20  # Below this, results are too irrelevant
GOOD_SCORE_THRESHOLD = 0.35  # Above this, results are reliable

# Query expansion mappings for Machinecraft products
QUERY_EXPANSIONS = {
    r'\bpf[-\s]?1\b': ['PF1', 'PF-1', 'pressure forming', 'single station thermoforming'],
    r'\bpf[-\s]?2\b': ['PF2', 'PF-2', 'twin sheet forming'],
    r'\bam\b': ['AM series', 'twin sheet', 'automotive'],
    r'\bre\b': ['RE series', 'rotary'],
    r'\bthermoform': ['thermoforming', 'vacuum forming', 'pressure forming'],
    r'\bprice\b': ['price', 'cost', 'quotation', 'quote', 'pricing'],
    r'\bspec\b': ['specification', 'specs', 'technical', 'dimensions'],
}


@dataclass
class Citation:
    """A citation/chunk from retrieval."""
    text: str
    filename: str
    score: float = 0.0
    source_group: str = "business"
    doc_type: str = "document"
    chunk_id: str = ""
    
    # Email-specific
    subject: str = ""
    from_email: str = ""
    
    # Extracted entities
    machines: List[str] = field(default_factory=list)
    
    # Quality tracking for consolidated knowledge
    is_consolidated_knowledge: bool = False
    knowledge_id: str = ""


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""
    citations: List[Citation]
    query: str
    doc_type_counts: Dict[str, int] = field(default_factory=dict)
    total: int = 0
    engine: str = "qdrant"


class QdrantRetriever:
    """Retriever using Qdrant vector database with FlashRank reranking."""
    
    def __init__(self, use_reranker: bool = True):
        self._qdrant = None
        self._voyage = None
        self._openai = None
        self._reranker = None
        self._use_reranker = use_reranker
    
    def _get_reranker(self):
        """Get or create FlashRank reranker."""
        if self._reranker is None and self._use_reranker:
            try:
                from flashrank import Ranker
                self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
            except ImportError:
                print("[qdrant_retriever] FlashRank not installed, skipping reranking")
            except Exception as e:
                print(f"[qdrant_retriever] Reranker init error: {e}")
        return self._reranker
    
    def _rerank(self, query: str, citations: List[Citation], top_k: int) -> List[Citation]:
        """Rerank citations using FlashRank for better relevance."""
        reranker = self._get_reranker()
        if not reranker or len(citations) <= 1:
            return citations
        
        try:
            from flashrank import RerankRequest
            
            passages = [{"id": i, "text": c.text[:1000]} for i, c in enumerate(citations)]
            request = RerankRequest(query=query, passages=passages)
            reranked = reranker.rerank(request)
            
            # Reorder citations based on reranker scores
            result = []
            for item in reranked[:top_k]:
                idx = item["id"]
                citation = citations[idx]
                citation.score = item["score"]  # Update with reranker score
                result.append(citation)
            
            return result
        except Exception as e:
            print(f"[qdrant_retriever] Reranking error: {e}")
            return citations[:top_k]
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL, timeout=30)
        return self._qdrant
    
    def _safe_qdrant_query(self, collection_name: str, query: list, limit: int):
        """Execute Qdrant query with circuit breaker protection."""
        qdrant = self._get_qdrant()
        
        def do_query():
            return qdrant.query_points(
                collection_name=collection_name,
                query=query,
                limit=limit,
                with_payload=True,
            )
        
        if RESILIENCE_AVAILABLE:
            try:
                result, used_fallback = qdrant_breaker.execute(do_query, fallback_result=None)
                if used_fallback or result is None:
                    track_warning("qdrant_retriever", f"Qdrant unavailable, returning empty for {collection_name}")
                    return None
                return result
            except Exception as e:
                track_error("qdrant_retriever", e, {"collection": collection_name})
                return None
        else:
            return do_query()
    
    def _get_embedding(self, text: str) -> tuple:
        """Get embedding using available provider with resilience."""
        # Try Voyage first
        if VOYAGE_API_KEY:
            try:
                import voyageai
                if self._voyage is None:
                    self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
                
                # Apply circuit breaker if available
                if RESILIENCE_AVAILABLE:
                    result, used_fallback = voyage_breaker.execute(
                        lambda: self._voyage.embed([text], model="voyage-3", input_type="query"),
                        fallback_result=None
                    )
                    if result is None or used_fallback:
                        pass  # Fall through to OpenAI
                    else:
                        return result.embeddings[0], "voyage", 1024
                else:
                    result = self._voyage.embed([text], model="voyage-3", input_type="query")
                    return result.embeddings[0], "voyage", 1024
            except Exception as e:
                track_warning("qdrant_retriever", f"Voyage embedding failed: {e}")
                pass  # Fall through to OpenAI
        
        # Fallback to OpenAI
        if OPENAI_API_KEY:
            from openai import OpenAI
            if self._openai is None:
                self._openai = OpenAI(api_key=OPENAI_API_KEY)
            
            try:
                if RESILIENCE_AVAILABLE:
                    response, _ = openai_breaker.execute(
                        lambda: self._openai.embeddings.create(
                            model="text-embedding-3-large",
                            input=[text]
                        )
                    )
                else:
                    response = self._openai.embeddings.create(
                        model="text-embedding-3-large",
                        input=[text]
                    )
                return response.data[0].embedding, "openai", 3072
            except Exception as e:
                track_error("qdrant_retriever", e, {"operation": "openai_embedding"})
                raise
        
        raise ValueError("No embedding provider available")
    
    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms for better recall."""
        query_lower = query.lower()
        expansions: Set[str] = set()
        
        for pattern, terms in QUERY_EXPANSIONS.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                expansions.update(terms)
        
        if expansions:
            # Add expansion terms to query
            expansion_str = " ".join(expansions)
            return f"{query} {expansion_str}"
        
        return query
    
    def _enrich_with_graph(self, query: str, citations: List[Citation]) -> List[Citation]:
        """Add Neo4j graph knowledge for entities found in query and results."""
        try:
            from neo4j_store import get_neo4j_store
        except ImportError:
            try:
                from src.brain.neo4j_store import get_neo4j_store
            except ImportError:
                return citations

        try:
            store = get_neo4j_store()
            if not store.is_connected():
                return citations
        except Exception:
            return citations

        entities = set()
        # Match specific models (PF1-C-3020) AND bare series names (PF1, AM)
        model_pattern = re.compile(r'(PF1|PF2|AM|ATF|IMG|FCS)[-\s]?[A-Z]?[-\s]?\d+', re.IGNORECASE)
        series_pattern = re.compile(r'\b(PF1|PF2|AM|ATF|IMG|FCS)\b', re.IGNORECASE)
        for match in model_pattern.finditer(query):
            entities.add(match.group(0).upper().replace(' ', '-'))
        for match in series_pattern.finditer(query):
            entities.add(match.group(1).upper())
        for c in citations[:5]:
            for m in c.machines:
                entities.add(m)

        if not entities:
            return citations

        existing_texts = {c.text[:100] for c in citations}

        for entity in list(entities)[:3]:
            try:
                knowledge = store.get_entity_knowledge(entity)
                for item in knowledge[:3]:
                    text = item.get("text") or item.get("summary") or ""
                    if not text or text[:100] in existing_texts:
                        continue
                    existing_texts.add(text[:100])
                    citations.append(Citation(
                        text=text[:1500],
                        filename=item.get("source_file", f"Graph: {entity}"),
                        score=0.65,
                        source_group="knowledge",
                        doc_type=item.get("knowledge_type", "graph"),
                        machines=[entity],
                    ))
            except Exception:
                continue

        return citations

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        source_group: Optional[str] = None,
        include_doc_types: Optional[List[str]] = None,
        exclude_doc_types: Optional[List[str]] = None,
        min_score: float = MIN_SCORE_THRESHOLD,
        expand_query: bool = True,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            top_k: Number of results
            source_group: Filter by source group ('business', 'governance', 'technical')
            include_doc_types: Only include these doc types
            exclude_doc_types: Exclude these doc types
            min_score: Minimum relevance score (0-1)
            expand_query: Whether to expand query with synonyms
        """
        # Expand query for better recall
        search_query = self._expand_query(query) if expand_query else query
        
        embedding, provider, dim = self._get_embedding(search_query)
        
        # Choose collection based on provider (using centralized config)
        if provider == "voyage":
            doc_collection = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
            email_collection = COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2")
        else:
            doc_collection = COLLECTIONS.get("chunks_openai_large", "ira_chunks_v4_openai_large")
            email_collection = COLLECTIONS.get("emails_openai_large", "ira_emails_v4_openai_large")
        
        qdrant = self._get_qdrant()
        citations = []
        doc_type_counts = {}
        
        # Search documents
        try:
            doc_results = qdrant.query_points(
                collection_name=doc_collection,
                query=embedding,
                limit=top_k,
                with_payload=True,
            )
            
            for p in doc_results.points:
                payload = p.payload or {}
                doc_type = payload.get("doc_type", "document")
                
                # Apply filters
                if include_doc_types and doc_type not in include_doc_types:
                    continue
                if exclude_doc_types and doc_type in exclude_doc_types:
                    continue
                
                doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
                
                citations.append(Citation(
                    text=payload.get("raw_text", payload.get("text", ""))[:1500],
                    filename=payload.get("filename", ""),
                    score=p.score,
                    source_group=payload.get("source_group", "business"),
                    doc_type=doc_type,
                    chunk_id=str(p.id),
                    machines=payload.get("machines", []),
                ))
        except Exception as e:
            print(f"[qdrant_retriever] Doc search error: {e}")
        
        # Search emails
        try:
            email_results = qdrant.query_points(
                collection_name=email_collection,
                query=embedding,
                limit=top_k,
                with_payload=True,
            )
            
            for p in email_results.points:
                payload = p.payload or {}
                
                doc_type_counts["email"] = doc_type_counts.get("email", 0) + 1
                
                citations.append(Citation(
                    text=payload.get("raw_text", payload.get("text", ""))[:1500],
                    filename=f"Email: {payload.get('subject', 'No subject')}",
                    score=p.score,
                    source_group="business",
                    doc_type="email",
                    chunk_id=str(p.id),
                    subject=payload.get("subject", ""),
                    from_email=payload.get("from_email", ""),
                    machines=payload.get("machines", []),
                ))
        except Exception as e:
            print(f"[qdrant_retriever] Email search error: {e}")
        
        # Search dream-learned knowledge (from nightly learning)
        # These are tracked for quality scoring
        if provider == "voyage":
            dream_collection = COLLECTIONS.get("dream_knowledge", "ira_dream_knowledge_v1")
            try:
                dream_results = qdrant.query_points(
                    collection_name=dream_collection,
                    query=embedding,
                    limit=top_k,
                    with_payload=True,
                )
                
                for p in dream_results.points:
                    payload = p.payload or {}
                    knowledge_id = payload.get("knowledge_id", str(p.id))
                    
                    doc_type_counts["dream_knowledge"] = doc_type_counts.get("dream_knowledge", 0) + 1
                    
                    citations.append(Citation(
                        text=payload.get("text", payload.get("raw_text", ""))[:1500],
                        filename=payload.get("document", "Dream Learning"),
                        score=p.score,
                        source_group="knowledge",
                        doc_type=payload.get("type", "learned_fact"),
                        chunk_id=str(p.id),
                        is_consolidated_knowledge=True,
                        knowledge_id=knowledge_id,
                    ))
                    
                    # Track retrieval for quality scoring
                    if QUALITY_TRACKING_AVAILABLE:
                        try:
                            consolidator = MemoryConsolidator(verbose=False)
                            consolidator.record_knowledge_retrieval(knowledge_id)
                        except Exception:
                            pass  # Don't block retrieval for tracking errors
            except Exception:
                pass  # Dream knowledge collection may not exist yet
        
        # Search discovered knowledge (from document ingestion/scanning)
        if provider == "voyage":
            discovered_collection = COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge")
            try:
                discovered_results = qdrant.query_points(
                    collection_name=discovered_collection,
                    query=embedding,
                    limit=top_k,
                    with_payload=True,
                )
                
                for p in discovered_results.points:
                    payload = p.payload or {}
                    
                    doc_type_counts["discovered_knowledge"] = doc_type_counts.get("discovered_knowledge", 0) + 1
                    
                    citations.append(Citation(
                        text=payload.get("text", payload.get("raw_text", ""))[:1500],
                        filename=payload.get("filename", payload.get("source_file", "Discovered Knowledge")),
                        score=p.score,
                        source_group="knowledge",
                        doc_type=payload.get("doc_type", "machine_spec"),
                        chunk_id=str(p.id),
                        machines=payload.get("machines", []),
                    ))
            except Exception:
                pass  # Discovered knowledge collection may not exist yet
        
        # Enrich with Neo4j graph context for entities found in results
        citations = self._enrich_with_graph(query, citations)

        # Sort by score and limit
        citations.sort(key=lambda c: c.score, reverse=True)
        
        # Apply minimum score threshold (before reranking)
        citations = [c for c in citations if c.score >= min_score]
        
        # Rerank with FlashRank for better relevance
        if self._use_reranker and len(citations) > 1:
            citations = self._rerank(query, citations, top_k * 2)  # Rerank more, then limit
        
        # Limit results
        citations = citations[:top_k]
        
        # Log quality metrics
        if citations:
            avg_score = sum(c.score for c in citations) / len(citations)
            if avg_score < GOOD_SCORE_THRESHOLD:
                print(f"[qdrant_retriever] Low relevance warning: avg_score={avg_score:.3f} for query '{query[:50]}'")
        
        return RetrievalResult(
            citations=citations,
            query=query,
            doc_type_counts=doc_type_counts,
            total=len(citations),
        )


# Module-level retriever instance
_retriever = None


def get_retriever() -> QdrantRetriever:
    global _retriever
    if _retriever is None:
        _retriever = QdrantRetriever()
    return _retriever


def _json_knowledge_fallback(query: str, top_k: int) -> RetrievalResult:
    """Fallback retrieval from local JSON knowledge files when Qdrant is unavailable."""
    import json
    knowledge_dir = Path(__file__).parent.parent.parent / "data" / "knowledge"
    if not knowledge_dir.exists():
        knowledge_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "knowledge"
    if not knowledge_dir.exists():
        return RetrievalResult(citations=[], query=query, total=0, engine="json_fallback")

    citations = []
    query_terms = set(query.lower().split())

    for json_file in sorted(knowledge_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:30]:
        if json_file.name in ("ingested_hashes.json", "consolidation_log.json",
                               "migration_log.json", "zenkai_log.json",
                               "fusion_log.json", "transformations.json"):
            continue
        try:
            data = json.loads(json_file.read_text())
            items = data if isinstance(data, list) else [data]
            for item in items:
                text = item.get("text", item.get("content", ""))
                if not text or len(text) < 20:
                    continue
                text_lower = text.lower()
                overlap = sum(1 for t in query_terms if t in text_lower)
                if overlap >= 2 or (len(query_terms) == 1 and overlap == 1):
                    citations.append(Citation(
                        text=text[:1500],
                        filename=json_file.name,
                        score=min(0.4 + overlap * 0.1, 0.8),
                        source_group="knowledge",
                        doc_type=item.get("knowledge_type", "general"),
                    ))
        except Exception:
            continue

    citations.sort(key=lambda c: c.score, reverse=True)
    citations = citations[:top_k]
    return RetrievalResult(
        citations=citations, query=query, total=len(citations), engine="json_fallback"
    )


def retrieve(
    query: str,
    top_k: int = 10,
    source_group: Optional[str] = None,
    include_doc_types: Optional[List[str]] = None,
    exclude_doc_types: Optional[List[str]] = None,
    min_score: float = MIN_SCORE_THRESHOLD,
    expand_query: bool = True,
) -> RetrievalResult:
    """Retrieve documents for a query, with JSON fallback if Qdrant fails."""
    try:
        result = get_retriever().retrieve(
            query=query,
            top_k=top_k,
            source_group=source_group,
            include_doc_types=include_doc_types,
            exclude_doc_types=exclude_doc_types,
            min_score=min_score,
            expand_query=expand_query,
        )
        if result.total > 0:
            return result
    except Exception as e:
        print(f"[qdrant_retriever] Qdrant retrieval failed, using JSON fallback: {e}")

    return _json_knowledge_fallback(query, top_k)


# =============================================================================
# QUALITY TRACKING FUNCTIONS
# =============================================================================

def record_knowledge_feedback(
    knowledge_id: str,
    was_helpful: bool,
) -> bool:
    """
    Record feedback on whether consolidated knowledge was helpful.
    
    Call this when the user:
    - Gives positive feedback (thumbs up, "thanks", etc.) -> was_helpful=True
    - Gives negative feedback (correction, "wrong", etc.) -> was_helpful=False
    
    Args:
        knowledge_id: The knowledge ID from Citation.knowledge_id
        was_helpful: True if knowledge helped, False if it was wrong/unhelpful
    
    Returns:
        True if feedback was recorded successfully
    """
    if not QUALITY_TRACKING_AVAILABLE:
        return False
    
    try:
        consolidator = MemoryConsolidator(verbose=False)
        consolidator.record_knowledge_retrieval(knowledge_id, was_helpful=was_helpful)
        return True
    except Exception as e:
        print(f"[qdrant_retriever] Failed to record feedback: {e}")
        return False


def record_feedback_for_citations(
    citations: List[Citation],
    was_helpful: bool,
) -> int:
    """
    Record feedback for all consolidated knowledge in a list of citations.
    
    Args:
        citations: List of Citation objects from retrieval
        was_helpful: Whether the response using these citations was helpful
    
    Returns:
        Number of citations that had feedback recorded
    """
    count = 0
    for citation in citations:
        if citation.is_consolidated_knowledge and citation.knowledge_id:
            if record_knowledge_feedback(citation.knowledge_id, was_helpful):
                count += 1
    return count


def get_consolidated_knowledge_ids(citations: List[Citation]) -> List[str]:
    """
    Extract knowledge IDs from citations that came from consolidated knowledge.
    
    Use this to track which knowledge IDs were used in a response,
    then call record_knowledge_feedback later when you get user feedback.
    """
    return [
        c.knowledge_id 
        for c in citations 
        if c.is_consolidated_knowledge and c.knowledge_id
    ]


if __name__ == "__main__":
    # Test retrieval
    result = retrieve("What machines does Machinecraft make?", top_k=5)
    print(f"Found {result.total} results")
    for c in result.citations[:3]:
        print(f"  [{c.doc_type}] {c.filename}: {c.text[:80]}...")
