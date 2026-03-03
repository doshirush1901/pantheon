#!/usr/bin/env python3
"""
Unified Retriever - RAG System for Ira
=======================================

Retrieves relevant context from multiple sources:
- Documents (PDFs, Excel files)
- Emails
- Customer data

Features:
- Voyage AI embeddings (recommended - no rate limits)
- OpenAI embeddings (fallback)
- Hybrid search (vector + BM25)
- Reranking with FlashRank
- Query decomposition for complex questions
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import re

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        QDRANT_URL, DATABASE_URL, OPENAI_API_KEY, VOYAGE_API_KEY,
        COLLECTIONS, LEGACY_COLLECTIONS,
        EMBEDDING_MODEL_VOYAGE,
    )
    CONFIG_LOADED = True
except ImportError:
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
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    EMBEDDING_MODEL_VOYAGE = "voyage-3"
    COLLECTIONS = {
        "chunks_voyage": "ira_chunks_v4_voyage",
        "chunks_openai_large": "ira_chunks_openai_large_v3",
        "emails_voyage": "ira_emails_voyage_v2",
        "emails_openai_large": "ira_emails_openai_large_v3",
        "market_research": "ira_market_research_voyage",
    }
    LEGACY_COLLECTIONS = {}

# Collection mappings from config
COLLECTION_DOCS_VOYAGE = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
COLLECTION_DOCS_OPENAI = COLLECTIONS.get("chunks_openai_large", "ira_chunks_openai_large_v3")
COLLECTION_DOCS_OPENAI_SMALL = COLLECTIONS.get("chunks_openai_small", "ira_chunks_openai_small_v3")
COLLECTION_EMAILS_VOYAGE = COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2")
COLLECTION_EMAILS_OPENAI = COLLECTIONS.get("emails_openai_large", "ira_emails_openai_large_v3")
COLLECTION_EMAILS_OPENAI_SMALL = COLLECTIONS.get("emails_openai_small", "ira_emails_openai_small_v3")
COLLECTION_MARKET_RESEARCH = COLLECTIONS.get("market_research", "ira_market_research_voyage")

# Fallback collections (legacy - from config or hardcoded)
COLLECTION_DOCS_VOYAGE_LEGACY = "ira_chunks_v4_voyage"
COLLECTION_EMAILS_VOYAGE_LEGACY = "ira_emails_voyage_v2"
COLLECTION_DOCS_OPENAI_LEGACY = "ira_chunks_v4_openai_large"
COLLECTION_EMAILS_OPENAI_LEGACY = "ira_emails_v4_openai_large"

# Feature flags
USE_VOYAGE = bool(VOYAGE_API_KEY)
PREFER_VOYAGE = os.environ.get("PREFER_VOYAGE", "true").lower() == "true"
USE_HYBRID_SEARCH = os.environ.get("USE_HYBRID_SEARCH", "true").lower() == "true"
USE_RERANKER = os.environ.get("USE_RERANKER", "true").lower() == "true"
# Reranker type: "flashrank" (default, lightweight) or "colbert" (RAGatouille, more accurate)
RERANKER_TYPE = os.environ.get("RERANKER_TYPE", "flashrank").lower()

# Embedding models
VOYAGE_MODEL = EMBEDDING_MODEL_VOYAGE
VOYAGE_DIMENSION = 1024
OPENAI_MODEL = "text-embedding-3-large"
OPENAI_DIMENSION = 3072

# Neo4j integration for graph-enhanced retrieval
try:
    from .neo4j_store import Neo4jStore, get_neo4j_store
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

_logger = logging.getLogger(__name__)

# P0 Audit: Qdrant circuit breaker
try:
    from core.resilience import qdrant_breaker
    QDRANT_RESILIENCE_AVAILABLE = True
except ImportError:
    qdrant_breaker = None
    QDRANT_RESILIENCE_AVAILABLE = False


@dataclass
class UnifiedResult:
    """A single retrieval result."""
    text: str
    score: float
    source: str  # 'document', 'email', 'customer'
    
    # Document metadata
    filename: str = ""
    doc_type: str = ""
    page: Optional[int] = None
    sheet: Optional[str] = None
    
    # Email metadata
    subject: str = ""
    from_email: str = ""
    
    # Extracted entities
    machines: List[str] = field(default_factory=list)
    specs: Dict[str, str] = field(default_factory=dict)
    companies: List[str] = field(default_factory=list)
    
    # Internal
    chunk_id: str = ""
    section_id: str = ""
    section_title: str = ""
    section_text: str = ""
    doc_summary: str = ""
    
    @property
    def source_type(self) -> str:
        return self.source
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "score": self.score,
            "source": self.source,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "subject": self.subject,
            "from_email": self.from_email,
            "machines": self.machines,
        }


@dataclass
class UnifiedResponse:
    """Complete response from unified retrieval."""
    query: str
    results: List[UnifiedResult]
    
    document_count: int = 0
    email_count: int = 0
    customer_count: int = 0
    
    synthesized_answer: str = ""
    confidence: float = 0.0
    retrieval_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "document_count": self.document_count,
            "email_count": self.email_count,
            "synthesized_answer": self.synthesized_answer,
            "confidence": self.confidence,
        }




def _decompose_query(query: str) -> list:
    """
    P2 Audit: Decompose multi-facet queries for better retrieval.
    Returns [query] if not decomposable, else sub-queries.
    """
    q = query.strip().lower()
    # "compare X vs Y" or "X vs Y" or "difference between X and Y"
    compare_match = re.search(
        r"(?:compare|contrast|difference between)\s+(.+?)\s+(?:vs\.?|versus|and)\s+(.+)",
        q, re.IGNORECASE | re.DOTALL
    )
    if compare_match:
        a, b = compare_match.group(1).strip(), compare_match.group(2).strip()
        if len(a) > 3 and len(b) > 3:
            return [f"{a} specifications", f"{b} specifications", query]
    return [query]

class UnifiedRetriever:
    """
    Unified retrieval across documents, emails, and customers.
    
    Features:
    - Voyage AI embeddings (preferred - no rate limits, optimized for retrieval)
    - OpenAI embeddings (fallback)
    - Hybrid search (vector + BM25)
    - FlashRank reranking
    """
    
    def __init__(
        self,
        use_hybrid: bool = True,
        use_reranker: bool = True,
        use_query_decomposition: bool = False,
        use_multi_query: bool = False,
        use_corrective_rag: bool = False,
        use_answer_verification: bool = False,
    ):
        self.use_hybrid = use_hybrid and USE_HYBRID_SEARCH
        self.use_reranker = use_reranker and USE_RERANKER
        self.use_query_decomposition = use_query_decomposition
        self.use_multi_query = use_multi_query
        self.use_corrective_rag = use_corrective_rag
        self.use_answer_verification = use_answer_verification
        
        self._qdrant = None
        self._voyage = None
        self._openai = None
        self._reranker = None
        self._knowledge_graph = None
        self._neo4j = None
    
    def _get_knowledge_graph(self):
        """Get or create KnowledgeGraph instance for graph-based retrieval."""
        if self._knowledge_graph is None:
            try:
                from .knowledge_graph import KnowledgeGraph
                self._knowledge_graph = KnowledgeGraph(verbose=False)
                _logger.debug(f"Loaded knowledge graph: {len(self._knowledge_graph.nodes)} nodes")
            except Exception as e:
                _logger.debug(f"Knowledge graph not available: {e}")
        return self._knowledge_graph
    
    def _get_neo4j(self):
        """Get Neo4j store for graph-enhanced retrieval."""
        if self._neo4j is None and NEO4J_AVAILABLE:
            try:
                self._neo4j = get_neo4j_store()
                if not self._neo4j.is_connected():
                    _logger.debug("Neo4j not connected")
                    self._neo4j = None
                else:
                    _logger.debug("Neo4j connected for graph retrieval")
            except Exception as e:
                _logger.debug(f"Neo4j not available: {e}")
        return self._neo4j
    
    def _extract_entities_from_results(
        self,
        results: List["UnifiedResult"],
        query: str,
    ) -> Set[str]:
        """
        Extract key entities from retrieval results and query for graph lookup.
        
        Extracts:
        - Machine models (PF1-C-2015, AM-5060, etc.)
        - Entity names from result metadata
        - Key terms from query
        """
        entities = set()
        
        machine_patterns = [
            r'\bPF1?[-\s]?[A-Z]?[-\s]?\d{4}\b',
            r'\bPF2[-\s]?\d*\b',
            r'\bAM[-\s]?[A-Z]?[-\s]?\d{4}\b',
            r'\bRE[-\s]?\d+\b',
            r'\bIMG[-\s]?\d+\b',
            r'\bATF[-\s]?\d+\b',
        ]
        
        for pattern in machine_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for m in matches:
                entities.add(m.upper().replace(" ", "-"))
        
        for result in results[:5]:
            if result.machines:
                entities.update(result.machines)
            
            if result.filename:
                filename_matches = []
                for pattern in machine_patterns:
                    filename_matches.extend(re.findall(pattern, result.filename, re.IGNORECASE))
                for m in filename_matches:
                    entities.add(m.upper().replace(" ", "-"))
        
        return entities
    
    def _get_related_from_graph(
        self,
        entities: Set[str],
        max_related: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query knowledge graph for related nodes.
        
        Prefers Neo4j (real graph database) when available, falls back to JSON graph.
        
        For each entity, finds directly related nodes (depth=1) like:
        - Other machines in same series
        - Common applications
        - Related specifications
        """
        if not entities:
            return []
        
        related_items = []
        seen_ids = set()
        
        # Try Neo4j first (preferred - real graph database)
        neo4j = self._get_neo4j()
        if neo4j:
            for entity in entities:
                try:
                    # Get related entities from Neo4j
                    related = neo4j.get_related_entities(entity, depth=2, limit=max_related * 2)
                    
                    for item in related:
                        related_entity = item.get("entity", "")
                        if related_entity in seen_ids:
                            continue
                        seen_ids.add(related_entity)
                        
                        # Get knowledge about this related entity
                        knowledge = neo4j.get_entity_knowledge(related_entity)
                        text = knowledge[0].get("text", "") if knowledge else ""
                        
                        related_items.append({
                            "text": text[:500] if text else f"Related entity: {related_entity}",
                            "entity": related_entity,
                            "source_entity": entity,
                            "relationship": ", ".join(item.get("relationship_types", [])),
                            "strength": 1.0 / (item.get("distance", 1) + 1),
                            "topic": knowledge[0].get("knowledge_type", "") if knowledge else "",
                        })
                    
                    # Record access for learning
                    neo4j.record_access([entity] + [item["entity"] for item in related_items[:3]])
                    
                except Exception as e:
                    _logger.debug(f"Neo4j lookup failed for {entity}: {e}")
            
            if related_items:
                _logger.debug(f"Neo4j found {len(related_items)} related items for {len(entities)} entities")
                related_items.sort(key=lambda x: x.get("strength", 0), reverse=True)
                return related_items[:max_related]
        
        # Fallback to JSON-based knowledge graph
        graph = self._get_knowledge_graph()
        if not graph:
            return []
        
        for entity in entities:
            try:
                related = graph.get_related(entity, depth=1)
                
                for node, edge in related[:max_related]:
                    if node.id in seen_ids:
                        continue
                    seen_ids.add(node.id)
                    
                    related_items.append({
                        "text": node.text,
                        "entity": node.entity,
                        "source_entity": entity,
                        "relationship": edge.relationship_type,
                        "strength": edge.strength,
                        "topic": node.topic,
                    })
            except Exception as e:
                _logger.debug(f"Graph lookup failed for {entity}: {e}")
        
        related_items.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return related_items[:max_related]
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    def _get_voyage(self):
        if self._voyage is None and VOYAGE_API_KEY:
            import voyageai
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def _get_openai(self):
        if self._openai is None and OPENAI_API_KEY:
            from openai import OpenAI
            self._openai = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    def _get_reranker(self):
        """
        Get or create reranker instance.
        
        Supports two reranker types:
        - "flashrank": Fast, lightweight MS-MARCO based reranker (default)
        - "colbert": RAGatouille ColBERT-based reranker (higher accuracy)
        
        Set RERANKER_TYPE env var to switch between them.
        """
        if self._reranker is None:
            if RERANKER_TYPE == "colbert":
                try:
                    from ragatouille import RAGPretrainedModel
                    self._reranker = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
                    self._reranker_type = "colbert"
                    _logger.info("Loaded ColBERT reranker (RAGatouille)")
                except ImportError:
                    _logger.warning("RAGatouille not available, falling back to FlashRank")
                    self._load_flashrank_reranker()
                except Exception as e:
                    _logger.warning(f"Failed to load ColBERT reranker: {e}, falling back to FlashRank")
                    self._load_flashrank_reranker()
            else:
                self._load_flashrank_reranker()
        return self._reranker
    
    def _load_flashrank_reranker(self):
        """Load the default FlashRank reranker."""
        try:
            from flashrank import Ranker
            self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
            self._reranker_type = "flashrank"
            _logger.info("Loaded FlashRank reranker")
        except Exception as e:
            _logger.warning(f"Failed to load FlashRank reranker: {e}")
            self._reranker_type = None
    
    def _get_best_collection(self, preferred: str, fallback: str) -> str:
        """Get the best available collection (preferred if it exists and has data)."""
        qdrant = self._get_qdrant()
        
        try:
            info = qdrant.get_collection(preferred)
            if info.points_count > 0:
                _logger.debug(f"Using {preferred} ({info.points_count} pts)")
                return preferred
        except Exception as e:
                _log = __import__('logging').getLogger('ira.retriever')
                _log.debug("Retrieval log write failed: %s", e, exc_info=True)
        
        # Try fallback
        try:
            info = qdrant.get_collection(fallback)
            if info.points_count > 0:
                _logger.debug(f"Falling back to {fallback} ({info.points_count} pts)")
                return fallback
        except Exception as e:
                _log = __import__('logging').getLogger('ira.retriever')
                _log.debug("Retrieval log write failed: %s", e, exc_info=True)
        
        # Return preferred anyway (may fail at search time)
        return preferred
    
    def _get_embedding(self, text: str, input_type: str = "query") -> Tuple[List[float], str]:
        """Get embedding using preferred provider."""
        if PREFER_VOYAGE and USE_VOYAGE:
            voyage = self._get_voyage()
            if voyage:
                try:
                    result = voyage.embed([text], model=VOYAGE_MODEL, input_type=input_type)
                    return result.embeddings[0], "voyage"
                except Exception as e:
                    _logger.warning(f"Voyage embedding failed: {e}, falling back to OpenAI")
        
        # Fallback to OpenAI
        openai = self._get_openai()
        if openai:
            response = openai.embeddings.create(model=OPENAI_MODEL, input=[text])
            return response.data[0].embedding, "openai"
        
        raise ValueError("No embedding provider available")
    
    def _search_collection(
        self,
        embedding: List[float],
        collection: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """Search a single Qdrant collection."""
        qdrant = self._get_qdrant()
        
        try:
            results = qdrant.query_points(
                collection_name=collection,
                query=embedding,
                limit=top_k,
                with_payload=True,
            )
            
            return [
                {
                    "id": str(p.id),
                    "score": p.score,
                    "payload": p.payload or {},
                }
                for p in results.points
            ]
        except Exception as e:
            _logger.debug(f"Search failed for {collection}: {e}")
            return []
    
    def _rerank_results(
        self,
        query: str,
        results: List[UnifiedResult],
        top_k: int = 10,
    ) -> List[UnifiedResult]:
        """
        Rerank results using the configured reranker.
        
        Supports:
        - FlashRank (default): Fast, uses MS-MARCO MiniLM
        - ColBERT (RAGatouille): Higher accuracy, uses ColBERTv2
        """
        if not self.use_reranker or not results:
            return results[:top_k]
        
        reranker = self._get_reranker()
        if not reranker:
            return results[:top_k]
        
        reranker_type = getattr(self, '_reranker_type', 'flashrank')
        
        try:
            if reranker_type == "colbert":
                return self._rerank_with_colbert(query, results, top_k)
            else:
                return self._rerank_with_flashrank(query, results, top_k)
        except Exception as e:
            _logger.warning(f"Reranking failed: {e}")
            return results[:top_k]
    
    def _rerank_with_flashrank(
        self,
        query: str,
        results: List[UnifiedResult],
        top_k: int
    ) -> List[UnifiedResult]:
        """Rerank using FlashRank MS-MARCO model."""
        from flashrank import RerankRequest
        
        passages = [{"id": i, "text": r.text} for i, r in enumerate(results)]
        request = RerankRequest(query=query, passages=passages)
        reranked = self._reranker.rerank(request)
        
        reranked_results = []
        for item in reranked[:top_k]:
            idx = item["id"]
            result = results[idx]
            result.score = item["score"]
            reranked_results.append(result)
        
        return reranked_results
    
    def _rerank_with_colbert(
        self,
        query: str,
        results: List[UnifiedResult],
        top_k: int
    ) -> List[UnifiedResult]:
        """
        Rerank using RAGatouille ColBERT model.
        
        ColBERT (Contextualized Late Interaction over BERT) provides:
        - Token-level similarity matching
        - Higher accuracy than cross-encoder approaches
        - Better handling of long documents
        """
        docs = [r.text for r in results]
        
        ranked = self._reranker.rerank(
            query=query,
            documents=docs,
            k=min(top_k, len(docs))
        )
        
        reranked_results = []
        for item in ranked:
            doc_text = item.get("content", item.get("text", ""))
            score = item.get("score", 0.0)
            
            for result in results:
                if result.text == doc_text or result.text[:100] == doc_text[:100]:
                    result.score = score
                    reranked_results.append(result)
                    break
        
        seen_ids = set()
        for result in results:
            if result not in reranked_results and len(reranked_results) < top_k:
                if result.chunk_id not in seen_ids:
                    seen_ids.add(result.chunk_id)
                    reranked_results.append(result)
        
        return reranked_results[:top_k]
    
    def retrieve(
        self,
        query: str,
        top_k: int = 15,
        include_documents: bool = True,
        include_emails: bool = True,
    ) -> UnifiedResponse:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return
            include_documents: Search document collections
            include_emails: Search email collections
            
        Returns:
            UnifiedResponse with results and metadata
        """
        import time
        start_time = time.time()
        try:
            return self._retrieve_impl(query, top_k, include_documents, include_emails, start_time)
        except (ConnectionError, OSError, TimeoutError) as e:
            _logger.warning("Qdrant connection failed, returning fallback: %s", e)
            return UnifiedResponse(
                query=query, results=[],
                synthesized_answer="My memory is temporarily unavailable. Please try again later.",
                retrieval_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            _logger.warning("Retrieval failed, returning fallback: %s", e)
            return UnifiedResponse(
                query=query, results=[],
                synthesized_answer="My memory is temporarily unavailable. Please try again later.",
                retrieval_time_ms=(time.time() - start_time) * 1000,
            )

    def _retrieve_impl(self, query, top_k, include_documents, include_emails, start_time):
        all_results = []
        seen_ids = set()
        # P2: query decomposition - increase top_k for compare-style queries
        sub_queries = _decompose_query(query)
        if len(sub_queries) > 1:
            top_k = min(top_k + 15, 30)

        
        # =====================================================================
        # HYBRID SEARCH - Combine keyword (BM25) + semantic (vector) search
        # =====================================================================
        if self.use_hybrid and include_documents:
            try:
                from .hybrid_search import get_hybrid_searcher, HybridResult
                
                hybrid_searcher = get_hybrid_searcher()
                hybrid_results = hybrid_searcher.search(query, top_k=top_k)
                
                for hr in hybrid_results:
                    if hr.chunk_id in seen_ids:
                        continue
                    seen_ids.add(hr.chunk_id)
                    
                    all_results.append(UnifiedResult(
                        text=hr.text,
                        score=hr.score,
                        source="document",
                        filename=hr.filename,
                        doc_type=hr.doc_type,
                        machines=hr.metadata.get("machines", []),
                        chunk_id=hr.chunk_id,
                    ))
                
                _logger.debug(f"Hybrid search returned {len(hybrid_results)} results")
                
                # If hybrid search found enough results, skip pure semantic for documents
                if len(all_results) >= top_k // 2:
                    include_documents = False  # Skip duplicate doc search
                    
            except ImportError:
                _logger.debug("Hybrid search not available, falling back to semantic only")
            except Exception as e:
                _logger.warning(f"Hybrid search failed: {e}, falling back to semantic only")
        
        # Get embedding for semantic search
        embedding, provider = self._get_embedding(query, input_type="query")
        _logger.debug(f"Using {provider} embeddings")
        
        # Choose collections based on provider
        # Try new v2/v3 collections first, fall back to legacy if needed
        if provider == "voyage":
            doc_collection = self._get_best_collection(
                COLLECTION_DOCS_VOYAGE, COLLECTION_DOCS_VOYAGE_LEGACY
            )
            email_collection = self._get_best_collection(
                COLLECTION_EMAILS_VOYAGE, COLLECTION_EMAILS_VOYAGE_LEGACY
            )
        else:
            doc_collection = self._get_best_collection(
                COLLECTION_DOCS_OPENAI, COLLECTION_DOCS_OPENAI_LEGACY
            )
            email_collection = self._get_best_collection(
                COLLECTION_EMAILS_OPENAI, COLLECTION_EMAILS_OPENAI_LEGACY
            )
        
        # Search documents
        if include_documents:
            doc_results = self._search_collection(embedding, doc_collection, top_k=top_k)
            for r in doc_results:
                chunk_id = r["id"]
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                
                p = r["payload"]
                all_results.append(UnifiedResult(
                    text=p.get("raw_text", p.get("text", ""))[:2000],
                    score=r["score"],
                    source="document",
                    filename=p.get("filename", ""),
                    doc_type=p.get("doc_type", ""),
                    machines=p.get("machines", []),
                    specs=p.get("specs", {}),
                    chunk_id=chunk_id,
                ))
        
        # Search emails
        if include_emails:
            email_results = self._search_collection(embedding, email_collection, top_k=top_k)
            for r in email_results:
                chunk_id = r["id"]
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                
                p = r["payload"]
                all_results.append(UnifiedResult(
                    text=p.get("raw_text", p.get("text", ""))[:2000],
                    score=r["score"],
                    source="email",
                    subject=p.get("subject", ""),
                    from_email=p.get("from_email", ""),
                    machines=p.get("machines", []),
                    companies=[p.get("company_domain", "")] if p.get("company_domain") else [],
                    chunk_id=chunk_id,
                ))
        
        # Search market research (company profiles) - only with Voyage embeddings (1024d)
        if include_documents and provider == "voyage" and len(embedding) == 1024:
            try:
                mr_results = self._search_collection(embedding, COLLECTION_MARKET_RESEARCH, top_k=min(top_k, 10))
                for r in mr_results:
                    chunk_id = f"mr_{r['id']}"
                    if chunk_id in seen_ids:
                        continue
                    seen_ids.add(chunk_id)
                    
                    p = r["payload"]
                    all_results.append(UnifiedResult(
                        text=p.get("content", "")[:2000],
                        score=r["score"],
                        source="market_research",
                        filename=p.get("company_name", ""),
                        doc_type="company_profile",
                        companies=[p.get("company_name", "")],
                        chunk_id=chunk_id,
                    ))
            except Exception as e:
                import logging; logging.getLogger("ira.retriever").debug("Retrieval log write failed: %s", e, exc_info=True)
                pass  # Market research collection may not exist
        elif include_documents and provider != "voyage":
            _logger.warning("[Retriever] Voyage AI unavailable — market research collection is not searchable with OpenAI embeddings. Some knowledge may be missing.")
        
        # Search dream-learned knowledge (nightly learning) - only with Voyage embeddings (1024d)
        if include_documents and provider == "voyage" and len(embedding) == 1024:
            dream_collection = COLLECTIONS.get("dream_knowledge", "ira_dream_knowledge_v1")
            try:
                dream_results = self._search_collection(embedding, dream_collection, top_k=min(top_k, 10))
                for r in dream_results:
                    chunk_id = f"dream_{r['id']}"
                    if chunk_id in seen_ids:
                        continue
                    seen_ids.add(chunk_id)
                    
                    p = r["payload"]
                    all_results.append(UnifiedResult(
                        text=p.get("text", p.get("raw_text", ""))[:2000],
                        score=r["score"],
                        source="dream_knowledge",
                        filename=p.get("document", "Dream Learning"),
                        doc_type=p.get("type", "learned_fact"),
                        chunk_id=chunk_id,
                    ))
            except Exception as e:
                import logging; logging.getLogger("ira.retriever").debug("Retrieval log write failed: %s", e, exc_info=True)
                pass  # Dream knowledge collection may not exist yet
        elif include_documents and provider != "voyage":
            _logger.warning("[Retriever] Voyage AI unavailable — dream knowledge collection is not searchable with OpenAI embeddings. Some knowledge may be missing.")
        
        # Search discovered knowledge (from document ingestion) - only with Voyage embeddings (1024d)
        if include_documents and provider == "voyage" and len(embedding) == 1024:
            discovered_collection = COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge")
            try:
                discovered_results = self._search_collection(embedding, discovered_collection, top_k=min(top_k, 10))
                for r in discovered_results:
                    chunk_id = f"discovered_{r['id']}"
                    if chunk_id in seen_ids:
                        continue
                    seen_ids.add(chunk_id)
                    
                    p = r["payload"]
                    all_results.append(UnifiedResult(
                        text=p.get("text", p.get("raw_text", ""))[:2000],
                        score=r["score"],
                        source="discovered_knowledge",
                        filename=p.get("filename", p.get("source_file", "Discovered Knowledge")),
                        doc_type=p.get("doc_type", "machine_spec"),
                        chunk_id=chunk_id,
                        machines=p.get("machines", []),
                    ))
            except Exception as e:
                import logging; logging.getLogger("ira.retriever").debug("Retrieval log write failed: %s", e, exc_info=True)
                pass  # Discovered knowledge collection may not exist yet
        elif include_documents and provider != "voyage":
            _logger.warning("[Retriever] Voyage AI unavailable — discovered knowledge collection is not searchable with OpenAI embeddings. Some knowledge may be missing.")
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Knowledge Graph Integration: Extract entities and find related knowledge
        try:
            entities = self._extract_entities_from_results(all_results, query)
            if entities:
                related_items = self._get_related_from_graph(entities, max_related=5)
                
                for item in related_items:
                    related_text = (
                        f"[Related to {item['source_entity']} via {item['relationship']}]\n"
                        f"{item['text']}"
                    )
                    
                    chunk_id = f"graph_{item.get('entity', '')}_{hash(item['text'])}"
                    if chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        all_results.append(UnifiedResult(
                            text=related_text[:2000],
                            score=item.get("strength", 0.5) * 0.8,
                            source="knowledge_graph",
                            filename=f"Related: {item.get('entity', 'knowledge')}",
                            doc_type=item.get("topic", "related_knowledge"),
                            machines=[item.get("entity", "")] if item.get("entity") else [],
                            chunk_id=chunk_id,
                        ))
                
                if related_items:
                    _logger.debug(f"Added {len(related_items)} related items from knowledge graph")
        except Exception as e:
            _logger.debug(f"Knowledge graph integration error: {e}")
        
        # Re-sort after adding graph results
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Rerank
        if self.use_reranker and len(all_results) > top_k:
            all_results = self._rerank_results(query, all_results, top_k=top_k)
        else:
            all_results = all_results[:top_k]
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        doc_count = sum(1 for r in all_results if r.source == "document")
        email_count = sum(1 for r in all_results if r.source == "email")
        
        # Calculate confidence
        if all_results:
            avg_score = sum(r.score for r in all_results[:5]) / min(5, len(all_results))
            confidence = min(avg_score, 1.0)
        else:
            confidence = 0.0
        
        response = UnifiedResponse(
            query=query,
            results=all_results,
            document_count=doc_count,
            email_count=email_count,
            confidence=confidence,
            retrieval_time_ms=elapsed_ms,
        )
        
        self._log_retrieval(query, all_results)
        
        return response
    
    def _log_retrieval(self, query: str, results: List[UnifiedResult]):
        """Log retrieval for knowledge graph consolidation."""
        try:
            import json
            from datetime import datetime
            
            log_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "knowledge"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "retrieval_log.jsonl"
            
            retrieved_ids = []
            for r in results[:10]:
                if r.chunk_id:
                    retrieved_ids.append(r.chunk_id)
            
            if retrieved_ids:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "query": query[:200],
                    "retrieved_ids": retrieved_ids,
                    "scores": [r.score for r in results[:10]],
                    "sources": [r.source for r in results[:10]],
                }
                
                try:
                    with open(log_file, "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                except (PermissionError, OSError) as e:
                    # P1 Audit: fallback to stderr on log write failure
                    import sys
                    __import__("logging").getLogger("ira.retriever").warning(
                        "Retrieval log write failed (%s), writing to stderr", e
                    )
                    sys.stderr.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            __import__("logging").getLogger("ira.retriever").debug("Retrieval log write failed: %s", e, exc_info=True)
    
    def retrieve_and_synthesize(
        self,
        query: str,
        top_k: int = 15,
        **kwargs
    ) -> UnifiedResponse:
        """
        Retrieve context and synthesize an answer.
        
        Args:
            query: The question to answer
            top_k: Number of context chunks to use
            
        Returns:
            UnifiedResponse with synthesized answer
        """
        response = self.retrieve(query, top_k=top_k, **kwargs)
        
        if not response.results:
            response.synthesized_answer = "I couldn't find relevant information to answer your question."
            return response
        
        # Build context
        context_parts = []
        for i, r in enumerate(response.results[:10]):
            source_info = f"[{r.source.upper()}]"
            if r.filename:
                source_info += f" {r.filename}"
            elif r.subject:
                source_info += f" Subject: {r.subject}"
            
            context_parts.append(f"{source_info}\n{r.text}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer using OpenAI
        openai = self._get_openai()
        if not openai:
            response.synthesized_answer = "No LLM available to generate answer."
            return response
        
        try:
            completion = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that answers questions based on the provided context.
                        
Rules:
- Only use information from the provided context
- If the context doesn't contain the answer, say so
- Be concise and direct
- Cite sources when possible"""
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}"
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            response.synthesized_answer = completion.choices[0].message.content
        except Exception as e:
            _logger.error(f"Failed to generate answer: {e}")
            response.synthesized_answer = f"Error generating answer: {e}"
        
        return response

    def search_market_research(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        use_semantic: bool = True
    ) -> List[UnifiedResult]:
        """
        Search market research database for company information.
        
        Args:
            query: Search query (company name, service, industry, etc.)
            filters: Optional filters (country, service_type, has_data, etc.)
            limit: Maximum results to return
            use_semantic: Use Voyage AI semantic search (default True)
            
        Returns:
            List of UnifiedResult with company profiles
        """
        import psycopg2
        import psycopg2.extras
        import json
        
        # Try semantic search first with Voyage
        if use_semantic and VOYAGE_API_KEY:
            try:
                import voyageai
                from qdrant_client import QdrantClient
                
                voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
                qdrant = QdrantClient(url=QDRANT_URL)
                
                # Get query embedding
                result = voyage.embed([query], model="voyage-3")
                query_vector = result.embeddings[0]
                
                # Search Qdrant using query_points (newer API)
                search_result = qdrant.query_points(
                    collection_name=COLLECTION_MARKET_RESEARCH,
                    query=query_vector,
                    limit=limit
                )
                
                results = []
                for hit in search_result.points:
                    payload = hit.payload
                    results.append(UnifiedResult(
                        text=payload.get('content', ''),
                        score=hit.score,
                        source="market_research",
                        filename=payload.get('company_name', ''),
                        doc_type="company_profile",
                        companies=[payload.get('company_name', '')],
                    ))
                
                if results:
                    return results
            except Exception as e:
                _logger.warning(f"Semantic search failed, falling back to SQL: {e}")
        
        # Fallback to SQL search
        # Market research is in Docker database (use 127.0.0.1 to avoid IPv6 issues)
        MARKET_RESEARCH_DB = 'postgresql://postgres:ira@127.0.0.1:5432/ira'
        
        try:
            conn = psycopg2.connect(MARKET_RESEARCH_DB)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query_lower = query.lower()
            
            # Build dynamic search
            sql = """
                SELECT 
                    company_id, name, website, country, email,
                    thermoforming_services, materials, industries, applications,
                    research_summary, research_confidence
                FROM market_research.companies
                WHERE is_valid = TRUE
                  AND (
                      LOWER(name) LIKE %s
                      OR LOWER(COALESCE(website, '')) LIKE %s
                      OR LOWER(COALESCE(country, '')) LIKE %s
                      OR thermoforming_services::text ILIKE %s
                      OR industries::text ILIKE %s
                      OR materials::text ILIKE %s
                  )
                ORDER BY 
                    CASE WHEN LOWER(name) LIKE %s THEN 0 ELSE 1 END,
                    research_confidence DESC NULLS LAST
                LIMIT %s
            """
            
            search_pattern = f"%{query_lower}%"
            cur.execute(sql, (
                search_pattern, search_pattern, search_pattern,
                search_pattern, search_pattern, search_pattern,
                search_pattern, limit
            ))
            
            results = []
            for row in cur.fetchall():
                # Format company data as text
                services = row.get('thermoforming_services') or []
                if isinstance(services, str):
                    try:
                        services = json.loads(services) if services else []
                    except (json.JSONDecodeError, TypeError):
                        services = []
                materials = row.get('materials') or []
                if isinstance(materials, str):
                    try:
                        materials = json.loads(materials) if materials else []
                    except (json.JSONDecodeError, TypeError):
                        materials = []
                industries = row.get('industries') or []
                if isinstance(industries, str):
                    try:
                        industries = json.loads(industries) if industries else []
                    except (json.JSONDecodeError, TypeError):
                        industries = []
                
                services_str = ', '.join(services) if services else 'N/A'
                materials_str = ', '.join(materials) if materials else 'N/A'
                industries_str = ', '.join(industries) if industries else 'N/A'
                
                text = f"""Company: {row['name']}
Website: {row.get('website', 'N/A')}
Country: {row.get('country', 'N/A')}
Email: {row.get('email', 'N/A')}
Services: {services_str}
Materials: {materials_str}
Industries: {industries_str}
Summary: {row.get('research_summary') or 'N/A'}"""
                
                results.append(UnifiedResult(
                    text=text,
                    score=row.get('research_confidence', 0.5) or 0.5,
                    source="market_research",
                    filename=row['name'],
                    doc_type="company_profile",
                    companies=[row['name']],
                ))
            
            conn.close()
            return results
            
        except Exception as e:
            _logger.error(f"Market research search error: {e}")
            return []

    def get_all_market_research_companies(self, with_data_only: bool = True) -> List[Dict]:
        """Get all companies from market research database."""
        import psycopg2
        import psycopg2.extras
        
        # Market research is in Docker database (use 127.0.0.1 to avoid IPv6 issues)
        MARKET_RESEARCH_DB = 'postgresql://postgres:ira@127.0.0.1:5432/ira'
        
        try:
            conn = psycopg2.connect(MARKET_RESEARCH_DB)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            if with_data_only:
                cur.execute("""
                    SELECT * FROM market_research.companies
                    WHERE is_valid = TRUE
                      AND thermoforming_services IS NOT NULL 
                      AND thermoforming_services != '[]'::jsonb
                    ORDER BY name
                """)
            else:
                cur.execute("""
                    SELECT * FROM market_research.companies
                    WHERE is_valid = TRUE
                    ORDER BY name
                """)
            
            results = cur.fetchall()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            _logger.error(f"Market research fetch error: {e}")
            return []


# CLI for OpenClaw skill
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Unified Retriever Skill")
    parser.add_argument("--query", required=True, help="The user query to search for")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.WARNING)
    
    retriever = UnifiedRetriever()
    response = retriever.retrieve_and_synthesize(args.query)
    
    if args.json:
        print(json.dumps({
            "answer": response.synthesized_answer,
            "confidence": response.confidence,
            "sources": [{"source": r.source, "filename": r.filename, "score": r.score} for r in response.results[:5]],
            "retrieval_time_ms": response.retrieval_time_ms,
        }, indent=2))
    else:
        print(response.synthesized_answer)
        if response.results:
            print(f"\n[Sources: {', '.join(r.filename or r.source for r in response.results[:3])}]")
        print(f"[Confidence: {response.confidence:.0%}]")
