#!/usr/bin/env python3
"""
KNOWLEDGE ENGINE - Unified Knowledge Management System
======================================================

A Cognee-inspired unified knowledge engine that combines:
- Document ingestion (30+ formats)
- Automatic entity extraction
- Knowledge graph construction
- Hybrid search (vector + graph traversal)

This replaces separate calls to:
- Mem0 (memory storage)
- UnifiedRetriever (RAG)
- KnowledgeGraph (entity relationships)

With a single, queryable knowledge interface.

Usage:
    from knowledge_engine import KnowledgeEngine, get_knowledge_engine
    
    engine = get_knowledge_engine()
    
    # Ingest documents
    await engine.ingest_file("path/to/document.pdf")
    
    # Search with graph-enhanced retrieval
    results = await engine.search("PF1 machines for automotive applications")
    
    # Get entity relationships
    relationships = await engine.get_entity_relationships("PF1-C-2015")
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        QDRANT_URL, VOYAGE_API_KEY, OPENAI_API_KEY,
        COLLECTIONS, get_logger
    )
    logger = get_logger(__name__)
    CONFIG_AVAILABLE = True
except ImportError:
    import logging as log_module
    logger = log_module.getLogger(__name__)
    CONFIG_AVAILABLE = False
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    COLLECTIONS = {}

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not available")

try:
    import voyageai
    VOYAGE_AVAILABLE = bool(VOYAGE_API_KEY)
except ImportError:
    VOYAGE_AVAILABLE = False


class SearchType(Enum):
    """Types of search supported by the knowledge engine."""
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    INSIGHTS = "insights"


class KnowledgeType(Enum):
    """Types of knowledge that can be stored."""
    DOCUMENT = "document"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    FACT = "fact"
    EPISODE = "episode"
    PROCEDURE = "procedure"


@dataclass
class KnowledgeItem:
    """A single item of knowledge."""
    id: str
    text: str
    knowledge_type: KnowledgeType
    
    entities: List[str] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    
    source_file: str = ""
    source_type: str = ""
    
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "knowledge_type": self.knowledge_type.value,
            "entities": self.entities,
            "relationships": self.relationships,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
        }


@dataclass
class SearchResult:
    """Result from a knowledge search."""
    items: List[KnowledgeItem]
    query: str
    search_type: SearchType
    
    total_found: int = 0
    search_time_ms: float = 0.0
    graph_traversals: int = 0
    entities_discovered: List[str] = field(default_factory=list)
    
    def to_context_strings(self, max_items: int = 5) -> List[str]:
        """Convert results to context strings for LLM."""
        return [item.text for item in self.items[:max_items]]


@dataclass
class EntityNode:
    """A node in the knowledge graph."""
    id: str
    name: str
    entity_type: str
    
    properties: Dict[str, Any] = field(default_factory=dict)
    connected_to: List[str] = field(default_factory=list)
    mention_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "properties": self.properties,
            "connected_to": self.connected_to,
            "mention_count": self.mention_count,
        }


@dataclass
class RelationshipEdge:
    """An edge (relationship) in the knowledge graph."""
    source_id: str
    target_id: str
    relationship_type: str
    
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    evidence: List[str] = field(default_factory=list)


ENTITY_PATTERNS = {
    "MACHINE": [
        r'(PF1-[A-Z]-\d{4})',
        r'(PF2-[A-Z]?\d{4})',
        r'(AM[P]?-\d{4}(?:-[A-Z])?)',
        r'(IMG[S]?-\d{4})',
    ],
    "MATERIAL": [
        r'\b(ABS|HIPS|PP|PE|PET|PVC|PC|PMMA|HDPE|LDPE|TPO|PETG)\b',
    ],
    "DIMENSION": [
        r'(\d{3,4}\s*[x×]\s*\d{3,4}\s*mm)',
    ],
    "POWER": [
        r'(\d+(?:\.\d+)?\s*kW)',
    ],
    "PRICE": [
        r'(₹[\d,]+|Rs\.?\s*[\d,]+|INR\s*[\d,]+)',
    ],
}


class KnowledgeGraph:
    """
    In-memory knowledge graph for entity relationships.
    
    Stores:
    - Entities (machines, materials, customers, etc.)
    - Relationships between entities
    - Supports graph traversal queries
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self.entities: Dict[str, EntityNode] = {}
        self.relationships: List[RelationshipEdge] = []
        self._adjacency: Dict[str, Set[str]] = {}
        
        if storage_path and storage_path.exists():
            self._load()
    
    def add_entity(self, entity: EntityNode):
        """Add or update an entity."""
        if entity.id in self.entities:
            existing = self.entities[entity.id]
            existing.mention_count += 1
            existing.properties.update(entity.properties)
        else:
            self.entities[entity.id] = entity
            self._adjacency[entity.id] = set()
    
    def add_relationship(self, relationship: RelationshipEdge):
        """Add a relationship between entities."""
        self.relationships.append(relationship)
        
        if relationship.source_id not in self._adjacency:
            self._adjacency[relationship.source_id] = set()
        if relationship.target_id not in self._adjacency:
            self._adjacency[relationship.target_id] = set()
        
        self._adjacency[relationship.source_id].add(relationship.target_id)
        self._adjacency[relationship.target_id].add(relationship.source_id)
    
    def get_neighbors(self, entity_id: str, depth: int = 1) -> Set[str]:
        """Get entities connected to the given entity."""
        if entity_id not in self._adjacency:
            return set()
        
        visited = {entity_id}
        frontier = self._adjacency.get(entity_id, set()).copy()
        
        for _ in range(depth - 1):
            next_frontier = set()
            for node in frontier:
                if node not in visited:
                    visited.add(node)
                    next_frontier.update(self._adjacency.get(node, set()))
            frontier = next_frontier - visited
        
        return frontier | (self._adjacency.get(entity_id, set()) - {entity_id})
    
    def get_entity_context(self, entity_id: str) -> Dict[str, Any]:
        """Get full context for an entity including relationships."""
        entity = self.entities.get(entity_id)
        if not entity:
            return {}
        
        neighbors = self.get_neighbors(entity_id, depth=2)
        related_entities = [
            self.entities[n].to_dict()
            for n in neighbors
            if n in self.entities
        ]
        
        entity_relationships = [
            {
                "type": r.relationship_type,
                "target": r.target_id if r.source_id == entity_id else r.source_id,
                "properties": r.properties
            }
            for r in self.relationships
            if r.source_id == entity_id or r.target_id == entity_id
        ]
        
        return {
            "entity": entity.to_dict(),
            "relationships": entity_relationships,
            "related_entities": related_entities[:10],
        }
    
    def save(self):
        """Save graph to disk."""
        if not self.storage_path:
            return
        
        data = {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relationships": [
                {
                    "source": r.source_id,
                    "target": r.target_id,
                    "type": r.relationship_type,
                    "weight": r.weight,
                }
                for r in self.relationships
            ],
            "saved_at": datetime.now().isoformat(),
        }
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        """Load graph from disk."""
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            for entity_id, entity_data in data.get("entities", {}).items():
                self.entities[entity_id] = EntityNode(
                    id=entity_data["id"],
                    name=entity_data["name"],
                    entity_type=entity_data["entity_type"],
                    properties=entity_data.get("properties", {}),
                    mention_count=entity_data.get("mention_count", 1),
                )
                self._adjacency[entity_id] = set()
            
            for rel_data in data.get("relationships", []):
                self.add_relationship(RelationshipEdge(
                    source_id=rel_data["source"],
                    target_id=rel_data["target"],
                    relationship_type=rel_data["type"],
                    weight=rel_data.get("weight", 1.0),
                ))
                
        except Exception as e:
            logger.warning(f"Failed to load knowledge graph: {e}")


class KnowledgeEngine:
    """
    Unified Knowledge Engine combining vector search and knowledge graph.
    
    Features:
    - Document ingestion with automatic entity extraction
    - Knowledge graph construction
    - Hybrid search (vector + graph traversal)
    - Memory-augmented retrieval
    """
    
    def __init__(
        self,
        collection_name: str = "ira_knowledge_engine",
        graph_path: Optional[Path] = None
    ):
        self.collection_name = collection_name
        
        if QDRANT_AVAILABLE:
            self._qdrant = QdrantClient(url=QDRANT_URL)
            self._ensure_collection()
        else:
            self._qdrant = None
            logger.warning("Qdrant not available - using fallback")
        
        if VOYAGE_AVAILABLE:
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        else:
            self._voyage = None
        
        self._openai = None
        
        graph_storage = graph_path or (
            AGENT_DIR.parent.parent.parent / "data" / "knowledge" / "knowledge_graph.json"
        )
        self.graph = KnowledgeGraph(graph_storage)
        
        self._content_hashes: Set[str] = set()
    
    def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        if not self._qdrant:
            return
        
        try:
            self._qdrant.get_collection(self.collection_name)
        except Exception:
            self._qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1024,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
    
    @property
    def openai_client(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    async def ingest_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Ingest a file into the knowledge engine.
        
        Supports: PDF, DOCX, TXT, MD, JSON, XLSX
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        text = self._extract_text(file_path)
        if not text:
            logger.warning(f"No text extracted from {file_path}")
            return 0
        
        chunks = self._chunk_text(text)
        
        items_added = 0
        for i, chunk in enumerate(chunks):
            content_hash = hashlib.md5(chunk.encode()).hexdigest()
            if content_hash in self._content_hashes:
                continue
            
            entities = self._extract_entities(chunk)
            
            item = KnowledgeItem(
                id=f"{file_path.stem}_{i}_{content_hash[:8]}",
                text=chunk,
                knowledge_type=KnowledgeType.DOCUMENT,
                entities=entities,
                source_file=str(file_path),
                source_type=file_path.suffix.lower(),
                metadata=metadata or {},
                created_at=datetime.now().isoformat(),
            )
            
            await self._store_item(item)
            self._update_graph_from_item(item)
            self._content_hashes.add(content_hash)
            items_added += 1
        
        self.graph.save()
        logger.info(f"Ingested {items_added} chunks from {file_path.name}")
        return items_added
    
    async def ingest_text(
        self,
        text: str,
        source: str = "manual",
        knowledge_type: KnowledgeType = KnowledgeType.FACT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ingest a piece of text directly.
        
        Returns the ID of the created knowledge item.
        """
        content_hash = hashlib.md5(text.encode()).hexdigest()
        if content_hash in self._content_hashes:
            return f"duplicate_{content_hash[:8]}"
        
        entities = self._extract_entities(text)
        
        item = KnowledgeItem(
            id=f"{source}_{content_hash[:8]}",
            text=text,
            knowledge_type=knowledge_type,
            entities=entities,
            source_file=source,
            source_type="text",
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )
        
        await self._store_item(item)
        self._update_graph_from_item(item)
        self._content_hashes.add(content_hash)
        
        return item.id
    
    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResult:
        """
        Search the knowledge base.
        
        Search types:
        - VECTOR: Pure semantic similarity
        - GRAPH: Graph traversal from extracted entities
        - HYBRID: Combine vector and graph results
        - INSIGHTS: Graph-enhanced semantic search
        """
        import time
        start_time = time.time()
        
        items = []
        entities_discovered = []
        graph_traversals = 0
        
        query_entities = self._extract_entities(query)
        entities_discovered.extend(query_entities)
        
        if search_type in [SearchType.VECTOR, SearchType.HYBRID, SearchType.INSIGHTS]:
            vector_results = await self._vector_search(query, top_k=top_k * 2)
            items.extend(vector_results)
        
        if search_type in [SearchType.GRAPH, SearchType.HYBRID, SearchType.INSIGHTS]:
            for entity in query_entities:
                graph_context = self.graph.get_entity_context(entity)
                if graph_context:
                    graph_traversals += 1
                    
                    for rel in graph_context.get("relationships", []):
                        target = rel.get("target", "")
                        if target and target not in entities_discovered:
                            entities_discovered.append(target)
                            
                            graph_items = await self._search_by_entity(target, top_k=3)
                            items.extend(graph_items)
        
        seen_ids = set()
        unique_items = []
        for item in items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)
        
        unique_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResult(
            items=unique_items[:top_k],
            query=query,
            search_type=search_type,
            total_found=len(unique_items),
            search_time_ms=search_time,
            graph_traversals=graph_traversals,
            entities_discovered=entities_discovered,
        )
    
    async def get_entity_relationships(
        self,
        entity_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get all relationships for an entity."""
        return self.graph.get_entity_context(entity_id)
    
    async def _vector_search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[KnowledgeItem]:
        """Perform vector similarity search."""
        if not self._qdrant:
            return []
        
        embedding = await self._get_embedding(query)
        if not embedding:
            return []
        
        try:
            results = self._qdrant.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                with_payload=True,
            )
            
            items = []
            for result in results:
                payload = result.payload or {}
                items.append(KnowledgeItem(
                    id=payload.get("id", str(result.id)),
                    text=payload.get("text", ""),
                    knowledge_type=KnowledgeType(payload.get("knowledge_type", "document")),
                    entities=payload.get("entities", []),
                    source_file=payload.get("source_file", ""),
                    metadata=payload.get("metadata", {}),
                    relevance_score=result.score,
                ))
            
            return items
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _search_by_entity(
        self,
        entity: str,
        top_k: int = 5
    ) -> List[KnowledgeItem]:
        """Search for items mentioning a specific entity."""
        return await self._vector_search(f"information about {entity}", top_k=top_k)
    
    async def _store_item(self, item: KnowledgeItem):
        """Store a knowledge item in the vector database."""
        if not self._qdrant:
            return
        
        embedding = await self._get_embedding(item.text)
        if not embedding:
            return
        
        item.embedding = embedding
        
        try:
            self._qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=hash(item.id) % (2**63),
                        vector=embedding,
                        payload={
                            "id": item.id,
                            "text": item.text,
                            "knowledge_type": item.knowledge_type.value,
                            "entities": item.entities,
                            "source_file": item.source_file,
                            "source_type": item.source_type,
                            "metadata": item.metadata,
                            "created_at": item.created_at,
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to store item: {e}")
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        if self._voyage:
            try:
                result = self._voyage.embed(
                    [text],
                    model="voyage-3",
                    input_type="document"
                )
                return result.embeddings[0]
            except Exception as e:
                logger.warning(f"Voyage embedding failed: {e}")
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None
    
    def _extract_text(self, file_path: Path) -> str:
        """Extract text from a file."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt" or suffix == ".md":
            return file_path.read_text(encoding="utf-8", errors="ignore")
        
        if suffix == ".json":
            try:
                data = json.loads(file_path.read_text())
                return json.dumps(data, indent=2)
            except Exception:
                return ""
        
        if suffix == ".pdf":
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                return "\n\n".join(text_parts)
            except ImportError:
                logger.warning("pdfplumber not available for PDF extraction")
                return ""
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return ""
        
        if suffix == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                return "\n\n".join([p.text for p in doc.paragraphs if p.text])
            except ImportError:
                logger.warning("python-docx not available")
                return ""
            except Exception as e:
                logger.error(f"DOCX extraction failed: {e}")
                return ""
        
        if suffix in [".xlsx", ".xls"]:
            try:
                import pandas as pd
                df = pd.read_excel(file_path)
                return df.to_string()
            except ImportError:
                logger.warning("pandas/openpyxl not available")
                return ""
            except Exception as e:
                logger.error(f"Excel extraction failed: {e}")
                return ""
        
        logger.warning(f"Unsupported file type: {suffix}")
        return ""
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                break_point = text.rfind('. ', start, end)
                if break_point > start + chunk_size // 2:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text using patterns."""
        import re
        entities = []
        
        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    entity = match.upper() if entity_type == "MACHINE" else match
                    if entity not in entities:
                        entities.append(entity)
        
        return entities
    
    def _update_graph_from_item(self, item: KnowledgeItem):
        """Update knowledge graph with entities from item."""
        import re
        
        for entity in item.entities:
            entity_type = "UNKNOWN"
            for etype, patterns in ENTITY_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, entity, re.IGNORECASE):
                        entity_type = etype
                        break
            
            node = EntityNode(
                id=entity,
                name=entity,
                entity_type=entity_type,
                properties={"source": item.source_file},
            )
            self.graph.add_entity(node)
        
        for i, entity1 in enumerate(item.entities):
            for entity2 in item.entities[i+1:]:
                relationship = RelationshipEdge(
                    source_id=entity1,
                    target_id=entity2,
                    relationship_type="co_occurs",
                    evidence=[item.id],
                )
                self.graph.add_relationship(relationship)


_engine_instance: Optional[KnowledgeEngine] = None


def get_knowledge_engine() -> KnowledgeEngine:
    """Get singleton knowledge engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = KnowledgeEngine()
    return _engine_instance


async def search(
    query: str,
    search_type: SearchType = SearchType.HYBRID,
    top_k: int = 10
) -> SearchResult:
    """Convenience function for searching."""
    return await get_knowledge_engine().search(query, search_type, top_k)


async def ingest_file(file_path: Union[str, Path]) -> int:
    """Convenience function for ingesting a file."""
    return await get_knowledge_engine().ingest_file(file_path)


if __name__ == "__main__":
    import asyncio
    
    async def test_engine():
        print("Testing Knowledge Engine\n" + "=" * 50)
        
        engine = get_knowledge_engine()
        
        test_text = """
        The PF1-C-2015 thermoforming machine has a forming area of 2000 x 1500 mm.
        It features a 125 kW heater system and is ideal for processing ABS and HIPS materials.
        The machine costs ₹60,00,000 and is suitable for automotive applications.
        """
        
        print("Ingesting test text...")
        item_id = await engine.ingest_text(
            test_text,
            source="test",
            knowledge_type=KnowledgeType.FACT
        )
        print(f"Created item: {item_id}")
        
        print("\nSearching for 'ABS automotive'...")
        results = await engine.search("ABS automotive", search_type=SearchType.HYBRID)
        print(f"Found {results.total_found} results in {results.search_time_ms:.1f}ms")
        print(f"Graph traversals: {results.graph_traversals}")
        print(f"Entities discovered: {results.entities_discovered}")
        
        for item in results.items[:3]:
            print(f"\n  [{item.relevance_score:.2f}] {item.text[:100]}...")
        
        print("\nGetting entity relationships for PF1-C-2015...")
        relationships = await engine.get_entity_relationships("PF1-C-2015")
        print(f"Relationships: {json.dumps(relationships, indent=2)[:500]}")
        
        print("\n✅ Knowledge Engine test complete")
    
    asyncio.run(test_engine())
