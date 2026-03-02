#!/usr/bin/env python3
"""
Hybrid Search - Keyword + Semantic Search
==========================================

Implements hybrid search combining:
- BM25 keyword search (lexical matching)
- Semantic vector search (meaning matching)

This provides the best of both worlds:
- Exact keyword matches for model numbers, specs, technical terms
- Semantic understanding for concept-based queries

Usage:
    from hybrid_search import HybridSearcher, hybrid_search
    
    searcher = HybridSearcher()
    results = searcher.search("PF1-C-2015 heater power specifications")
"""

import json
import logging
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Setup paths
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        QDRANT_URL, VOYAGE_API_KEY, OPENAI_API_KEY,
        COLLECTIONS, EMBEDDING_MODEL_VOYAGE,
        get_logger,
    )
    CONFIG_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging as log_module
    logger = log_module.getLogger(__name__)
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    EMBEDDING_MODEL_VOYAGE = "voyage-3"
    COLLECTIONS = {
        "chunks_voyage": "ira_chunks_v4_voyage",
        "emails_voyage": "ira_emails_voyage_v2",
    }


@dataclass
class HybridResult:
    """A result from hybrid search."""
    text: str
    score: float
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    source: str = ""
    filename: str = ""
    doc_type: str = ""
    chunk_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def combined_score(self) -> float:
        return self.score


class BM25Index:
    """
    Simple BM25 index for keyword search.
    
    Implements the BM25 (Okapi BM25) ranking function:
    - Term frequency saturation
    - Document length normalization
    - Inverse document frequency weighting
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 index.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Document length normalization (0-1, 0.75 typical)
        """
        self.k1 = k1
        self.b = b
        
        # Index structures
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # term -> doc count
        self.doc_lengths: Dict[str, int] = {}  # doc_id -> length
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)  # term -> {doc_id -> freq}
        self.documents: Dict[str, str] = {}  # doc_id -> text
        self.metadata: Dict[str, Dict] = {}  # doc_id -> metadata
        
        self.avg_doc_length = 0.0
        self.total_docs = 0
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        
        # Keep hyphenated terms together (for model numbers like PF1-C-2015)
        text_lower = text
        hyphenated = re.findall(r'\b[\w]+-[\w]+(?:-[\w]+)*\b', text_lower)
        tokens.extend([t.replace("-", "") for t in hyphenated])  # Also add without hyphens
        tokens.extend(hyphenated)  # Keep with hyphens
        
        return tokens
    
    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ):
        """Add a document to the index."""
        self.documents[doc_id] = text
        self.metadata[doc_id] = metadata or {}
        
        tokens = self.tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)
        
        # Count term frequencies
        term_freqs = Counter(tokens)
        
        # Update index
        seen_terms = set()
        for term, freq in term_freqs.items():
            self.inverted_index[term][doc_id] = freq
            if term not in seen_terms:
                self.doc_freqs[term] += 1
                seen_terms.add(term)
        
        # Update stats
        self.total_docs = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths.values()) / max(1, self.total_docs)
    
    def add_documents_bulk(
        self,
        documents: List[Tuple[str, str, Dict]],
    ):
        """Add multiple documents at once (more efficient)."""
        for doc_id, text, metadata in documents:
            self.documents[doc_id] = text
            self.metadata[doc_id] = metadata or {}
            
            tokens = self.tokenize(text)
            self.doc_lengths[doc_id] = len(tokens)
            
            term_freqs = Counter(tokens)
            seen_terms = set()
            
            for term, freq in term_freqs.items():
                self.inverted_index[term][doc_id] = freq
                if term not in seen_terms:
                    self.doc_freqs[term] += 1
                    seen_terms.add(term)
        
        self.total_docs = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths.values()) / max(1, self.total_docs)
    
    def _idf(self, term: str) -> float:
        """Calculate inverse document frequency."""
        n = self.doc_freqs.get(term, 0)
        if n == 0:
            return 0.0
        return math.log((self.total_docs - n + 0.5) / (n + 0.5) + 1.0)
    
    def _score_document(self, doc_id: str, query_terms: List[str]) -> float:
        """Calculate BM25 score for a document."""
        score = 0.0
        doc_length = self.doc_lengths.get(doc_id, 0)
        
        if doc_length == 0:
            return 0.0
        
        for term in query_terms:
            if term not in self.inverted_index:
                continue
            
            tf = self.inverted_index[term].get(doc_id, 0)
            if tf == 0:
                continue
            
            idf = self._idf(term)
            
            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            score += idf * numerator / denominator
        
        return score
    
    def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Search for documents matching query.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of (doc_id, score) tuples
        """
        query_terms = self.tokenize(query)
        
        if not query_terms:
            return []
        
        # Find candidate documents (those containing any query term)
        candidates = set()
        for term in query_terms:
            if term in self.inverted_index:
                candidates.update(self.inverted_index[term].keys())
        
        # Score candidates
        scores = []
        for doc_id in candidates:
            score = self._score_document(doc_id, query_terms)
            if score > 0:
                scores.append((doc_id, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]
    
    def save(self, path: str):
        """Save index to file."""
        data = {
            "k1": self.k1,
            "b": self.b,
            "doc_freqs": dict(self.doc_freqs),
            "doc_lengths": self.doc_lengths,
            "inverted_index": {k: dict(v) for k, v in self.inverted_index.items()},
            "documents": self.documents,
            "metadata": self.metadata,
            "avg_doc_length": self.avg_doc_length,
            "total_docs": self.total_docs,
        }
        with open(path, "w") as f:
            json.dump(data, f)
    
    def load(self, path: str):
        """Load index from file."""
        with open(path) as f:
            data = json.load(f)
        
        self.k1 = data.get("k1", 1.5)
        self.b = data.get("b", 0.75)
        self.doc_freqs = defaultdict(int, data.get("doc_freqs", {}))
        self.doc_lengths = data.get("doc_lengths", {})
        self.inverted_index = defaultdict(dict)
        for term, docs in data.get("inverted_index", {}).items():
            self.inverted_index[term] = docs
        self.documents = data.get("documents", {})
        self.metadata = data.get("metadata", {})
        self.avg_doc_length = data.get("avg_doc_length", 0.0)
        self.total_docs = data.get("total_docs", 0)


class HybridSearcher:
    """
    Hybrid search combining BM25 keyword search with semantic vector search.
    
    Features:
    - BM25 for exact keyword/model number matching
    - Semantic search for meaning-based retrieval
    - Score fusion using Reciprocal Rank Fusion (RRF)
    """
    
    def __init__(
        self,
        alpha: float = 0.5,
        rrf_k: int = 60,
        use_voyage: bool = True,
    ):
        """
        Initialize hybrid searcher.
        
        Args:
            alpha: Weight for semantic vs keyword (0=keyword only, 1=semantic only)
            rrf_k: RRF constant (higher = more emphasis on high ranks)
            use_voyage: Prefer Voyage embeddings
        """
        self.alpha = alpha
        self.rrf_k = rrf_k
        self.use_voyage = use_voyage and bool(VOYAGE_API_KEY)
        
        self._qdrant = None
        self._voyage = None
        self._openai = None
        self._bm25_index: Optional[BM25Index] = None
        self._index_path = PROJECT_ROOT / "data" / "knowledge" / "bm25_index.json"
    
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
    
    def _get_bm25_index(self) -> BM25Index:
        """Get or create BM25 index."""
        if self._bm25_index is not None:
            return self._bm25_index
        
        self._bm25_index = BM25Index()
        
        # Try to load from cache
        if self._index_path.exists():
            try:
                self._bm25_index.load(str(self._index_path))
                if self._bm25_index.total_docs > 0:
                    logger.debug(f"Loaded BM25 index with {self._bm25_index.total_docs} docs")
                    return self._bm25_index
            except Exception as e:
                logger.debug(f"Failed to load BM25 index: {e}")
        
        # Build index from Qdrant (lazy, on first search)
        self._build_bm25_index()
        
        return self._bm25_index
    
    def _build_bm25_index(self, max_docs: int = 10000):
        """Build BM25 index from Qdrant documents (main chunks + discovered knowledge)."""
        logger.info("Building BM25 keyword index...")
        
        qdrant = self._get_qdrant()
        collections_to_index = [
            COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage"),
            "ira_discovered_knowledge",
        ]
        
        try:
            documents = []
            
            for collection in collections_to_index:
                offset = None
                try:
                    while len(documents) < max_docs:
                        result = qdrant.scroll(
                            collection_name=collection,
                            limit=500,
                            offset=offset,
                            with_payload=True,
                            with_vectors=False,
                        )
                        
                        points, next_offset = result
                        if not points:
                            break
                        
                        for point in points:
                            payload = point.payload or {}
                            text = payload.get("raw_text") or payload.get("text") or ""
                            if text:
                                documents.append((
                                    f"{collection}:{point.id}",
                                    text[:2000],
                                    {
                                        "filename": payload.get("filename", ""),
                                        "doc_type": payload.get("doc_type", ""),
                                        "machines": payload.get("machines", []),
                                    }
                                ))
                        
                        offset = next_offset
                        if offset is None:
                            break
                except Exception as e:
                    logger.debug(f"Failed to index collection {collection}: {e}")
            
            if documents:
                self._bm25_index.add_documents_bulk(documents)
                logger.info(f"Built BM25 index with {len(documents)} documents from {len(collections_to_index)} collections")
                
                try:
                    self._index_path.parent.mkdir(parents=True, exist_ok=True)
                    self._bm25_index.save(str(self._index_path))
                except Exception as e:
                    logger.debug(f"Failed to save BM25 index: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to build BM25 index: {e}")
    
    def _get_embedding(self, text: str) -> Tuple[List[float], str]:
        """Get embedding for query."""
        if self.use_voyage:
            voyage = self._get_voyage()
            if voyage:
                try:
                    result = voyage.embed([text], model=EMBEDDING_MODEL_VOYAGE, input_type="query")
                    return result.embeddings[0], "voyage"
                except Exception as e:
                    logger.warning(f"Voyage embedding failed: {e}")
        
        # Fallback to OpenAI
        openai = self._get_openai()
        if openai:
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=[text]
            )
            return response.data[0].embedding, "openai"
        
        raise ValueError("No embedding provider available")
    
    def _semantic_search(
        self,
        query: str,
        top_k: int = 30,
    ) -> List[Tuple[str, float, Dict]]:
        """Perform semantic vector search."""
        embedding, provider = self._get_embedding(query)
        
        # Select collection based on embedding provider
        if provider == "voyage":
            collection = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
        else:
            collection = COLLECTIONS.get("chunks_openai_large", "ira_chunks_openai_large_v3")
        
        qdrant = self._get_qdrant()
        
        try:
            results = qdrant.query_points(
                collection_name=collection,
                query=embedding,
                limit=top_k,
                with_payload=True,
            )
            
            return [
                (
                    str(p.id),
                    p.score,
                    p.payload or {},
                )
                for p in results.points
            ]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []
    
    def _keyword_search(
        self,
        query: str,
        top_k: int = 30,
    ) -> List[Tuple[str, float, Dict]]:
        """Perform BM25 keyword search."""
        bm25 = self._get_bm25_index()
        
        results = bm25.search(query, top_k=top_k)
        
        return [
            (
                doc_id,
                score,
                bm25.metadata.get(doc_id, {}),
            )
            for doc_id, score in results
        ]
    
    def _fuse_results(
        self,
        semantic_results: List[Tuple[str, float, Dict]],
        keyword_results: List[Tuple[str, float, Dict]],
    ) -> List[HybridResult]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).
        
        RRF score = sum(1 / (k + rank_i)) for each ranking
        """
        # Build rank maps
        semantic_ranks = {doc_id: rank + 1 for rank, (doc_id, _, _) in enumerate(semantic_results)}
        keyword_ranks = {doc_id: rank + 1 for rank, (doc_id, _, _) in enumerate(keyword_results)}
        
        # Collect all doc IDs and scores
        all_docs = {}
        
        # Add semantic results
        for doc_id, score, metadata in semantic_results:
            if doc_id not in all_docs:
                all_docs[doc_id] = {
                    "semantic_score": score,
                    "keyword_score": 0.0,
                    "metadata": metadata,
                }
            all_docs[doc_id]["semantic_score"] = score
        
        # Add keyword results
        for doc_id, score, metadata in keyword_results:
            if doc_id not in all_docs:
                all_docs[doc_id] = {
                    "semantic_score": 0.0,
                    "keyword_score": 0.0,
                    "metadata": metadata,
                }
            all_docs[doc_id]["keyword_score"] = score
            # Merge metadata
            all_docs[doc_id]["metadata"].update(metadata)
        
        # Calculate RRF scores
        results = []
        for doc_id, data in all_docs.items():
            rrf_score = 0.0
            
            # Semantic contribution
            if doc_id in semantic_ranks:
                rrf_score += self.alpha * (1.0 / (self.rrf_k + semantic_ranks[doc_id]))
            
            # Keyword contribution
            if doc_id in keyword_ranks:
                rrf_score += (1.0 - self.alpha) * (1.0 / (self.rrf_k + keyword_ranks[doc_id]))
            
            metadata = data["metadata"]
            text = self._get_bm25_index().documents.get(doc_id, "")
            
            results.append(HybridResult(
                text=text[:2000] if text else metadata.get("raw_text", metadata.get("text", ""))[:2000],
                score=rrf_score,
                keyword_score=data["keyword_score"],
                semantic_score=data["semantic_score"],
                source="document",
                filename=metadata.get("filename", ""),
                doc_type=metadata.get("doc_type", ""),
                chunk_id=doc_id,
                metadata=metadata,
            ))
        
        # Sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    def search(
        self,
        query: str,
        top_k: int = 15,
        alpha: Optional[float] = None,
    ) -> List[HybridResult]:
        """
        Perform hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            alpha: Override default alpha (0=keyword, 1=semantic)
        
        Returns:
            List of HybridResult objects
        """
        if alpha is not None:
            self.alpha = alpha
        
        # Adjust alpha based on query type
        # More keyword weight for model numbers, specs
        query_lower = query.lower()
        if re.search(r'\bpf1\b|\bam[-\s]?\d|\bimg\b|\bfcs\b', query_lower):
            effective_alpha = 0.3  # More keyword weight for model queries
        elif any(kw in query_lower for kw in ["kw", "m³/hr", "mm", "price", "₹", "$"]):
            effective_alpha = 0.4  # More keyword for spec queries
        else:
            effective_alpha = self.alpha  # Default balance
        
        logger.debug(f"Hybrid search with alpha={effective_alpha}")
        
        # Run both searches
        semantic_results = self._semantic_search(query, top_k=top_k * 2)
        keyword_results = self._keyword_search(query, top_k=top_k * 2)
        
        # Save original alpha and use effective
        original_alpha = self.alpha
        self.alpha = effective_alpha
        
        # Fuse results
        results = self._fuse_results(semantic_results, keyword_results)
        
        # Restore alpha
        self.alpha = original_alpha
        
        return results[:top_k]
    
    def rebuild_index(self):
        """Force rebuild of BM25 index."""
        self._bm25_index = BM25Index()
        self._build_bm25_index()
        return self._bm25_index.total_docs


# Singleton instance
_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    """Get singleton HybridSearcher instance."""
    global _searcher
    if _searcher is None:
        _searcher = HybridSearcher()
    return _searcher


def hybrid_search(
    query: str,
    top_k: int = 15,
    alpha: float = 0.5,
) -> List[HybridResult]:
    """
    Convenience function for hybrid search.
    
    Args:
        query: Search query
        top_k: Number of results
        alpha: Balance between semantic (1) and keyword (0)
    
    Returns:
        List of HybridResult objects
    """
    return get_hybrid_searcher().search(query, top_k, alpha)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Hybrid Search Test")
    print("=" * 60)
    
    searcher = get_hybrid_searcher()
    
    # Test queries
    test_queries = [
        "PF1-C-2015 heater power specifications",
        "vacuum forming machine for truck bedliners",
        "compare PF1 and AM series machines",
        "what is the price of IMG-1350?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        results = searcher.search(query, top_k=5)
        
        for i, r in enumerate(results):
            print(f"{i+1}. Score: {r.score:.4f} (semantic: {r.semantic_score:.4f}, keyword: {r.keyword_score:.4f})")
            print(f"   File: {r.filename}")
            print(f"   Text: {r.text[:100]}...")
