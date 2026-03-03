#!/usr/bin/env python3
"""
GRAPH-ENHANCED RETRIEVER - GraphRAG for Multi-hop Reasoning
============================================================

A LightRAG-inspired retriever that combines:
- Vector similarity search
- Knowledge graph traversal
- Multi-hop reasoning chains

This enables complex queries like:
- "What machines are suitable for customers who use ABS in automotive?"
- "Which PF1 machines have been successful for packaging applications?"
- "What's the relationship between sheet thickness and machine series?"

Features:
1. LOCAL SEARCH: Entity-centric retrieval with neighbors
2. GLOBAL SEARCH: High-level summarization across topics
3. HYBRID SEARCH: Combines local + global + vector
4. INSIGHT GENERATION: Synthesizes patterns from graph

Usage:
    from graph_retriever import GraphRetriever, get_graph_retriever
    
    retriever = get_graph_retriever()
    
    # Simple search
    results = await retriever.search("PF1 for automotive")
    
    # Multi-hop reasoning
    results = await retriever.reason("Why is PF1 better than AM for thick materials?")
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
from typing import Any, Dict, List, Optional, Set, Tuple

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

sys.path.insert(0, str(AGENT_DIR))

try:
    from config import OPENAI_API_KEY, get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_module
    logger = log_module.getLogger(__name__)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

try:
    from src.brain.unified_retriever import UnifiedRetriever
    UNIFIED_RETRIEVER_AVAILABLE = True
except ImportError:
    UNIFIED_RETRIEVER_AVAILABLE = False
    logger.warning("UnifiedRetriever not available")

try:
    from src.memory.knowledge_engine import (
        KnowledgeEngine, get_knowledge_engine, SearchType as KESearchType
    )
    KNOWLEDGE_ENGINE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_ENGINE_AVAILABLE = False
    logger.warning("KnowledgeEngine not available")

try:
    from src.brain.neo4j_store import Neo4jStore, get_neo4j_store
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("Neo4j store not available")


class GraphSearchMode(Enum):
    """Search modes for graph retrieval."""
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    NAIVE = "naive"


@dataclass
class EntityContext:
    """Context gathered from an entity and its neighborhood."""
    entity_id: str
    entity_type: str
    
    direct_relationships: List[Dict] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    co_occurrence_context: str = ""
    
    relevance_score: float = 0.0
    hop_distance: int = 0


@dataclass
class ReasoningChain:
    """A multi-hop reasoning chain through the knowledge graph."""
    steps: List[Dict] = field(default_factory=list)
    entities_visited: List[str] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0


@dataclass
class GraphSearchResult:
    """Result from graph-enhanced search."""
    query: str
    mode: GraphSearchMode
    
    contexts: List[str]
    entities_found: List[str]
    relationships_traversed: int
    
    vector_score: float = 0.0
    graph_score: float = 0.0
    combined_score: float = 0.0
    
    reasoning_chain: Optional[ReasoningChain] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_context_string(self, max_contexts: int = 5) -> str:
        """Combine contexts into a single string."""
        return "\n\n".join(self.contexts[:max_contexts])


MACHINECRAFT_ENTITIES = {
    "SERIES": ["PF1", "PF2", "AM", "AMP", "IMG", "IMGS", "FCS", "UNO", "DUO", "PLAY", "ATF"],
    "MATERIAL": ["ABS", "HIPS", "PP", "PE", "PET", "PVC", "PC", "PMMA", "HDPE", "LDPE", "TPO", "PETG"],
    "APPLICATION": ["automotive", "packaging", "food", "medical", "industrial", "consumer"],
    "FEATURE": ["servo", "pneumatic", "vacuum", "pressure", "twin-sheet"],
}

IMPLICIT_RELATIONSHIPS = {
    ("PF1", "heavy_gauge"): {"type": "suitable_for", "weight": 0.9},
    ("PF1", "thick_material"): {"type": "suitable_for", "weight": 0.9},
    ("AM", "thin_gauge"): {"type": "suitable_for", "weight": 0.9},
    ("AM", "light_material"): {"type": "suitable_for", "weight": 0.9},
    ("PF1", "automotive"): {"type": "common_application", "weight": 0.7},
    ("AM", "packaging"): {"type": "common_application", "weight": 0.7},
}


class GraphRetriever:
    """
    GraphRAG-style retriever combining vector search with graph traversal.
    
    Search modes:
    - LOCAL: Start from entities in query, expand through relationships
    - GLOBAL: High-level topic search using community summaries
    - HYBRID: Combine local + global for comprehensive results
    - NAIVE: Simple vector search fallback
    """
    
    def __init__(self):
        self._unified_retriever = None
        self._knowledge_engine = None
        self._openai = None
        self._neo4j_store = None
        
        self._entity_index: Dict[str, List[str]] = {}
        self._community_summaries: Dict[str, str] = {}
        self._build_entity_index()
    
    @property
    def neo4j_store(self):
        """Get Neo4j store instance (lazy loading)."""
        if self._neo4j_store is None and NEO4J_AVAILABLE:
            try:
                self._neo4j_store = get_neo4j_store()
                if not self._neo4j_store.is_connected():
                    self._neo4j_store = None
                    logger.warning("Neo4j not connected, using fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize Neo4j: {e}")
        return self._neo4j_store
    
    @property
    def unified_retriever(self):
        if self._unified_retriever is None and UNIFIED_RETRIEVER_AVAILABLE:
            self._unified_retriever = UnifiedRetriever()
        return self._unified_retriever
    
    @property
    def knowledge_engine(self):
        if self._knowledge_engine is None and KNOWLEDGE_ENGINE_AVAILABLE:
            self._knowledge_engine = get_knowledge_engine()
        return self._knowledge_engine
    
    @property
    def openai_client(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    def _build_entity_index(self):
        """Build index of entities from domain knowledge."""
        import re
        
        for category, entities in MACHINECRAFT_ENTITIES.items():
            for entity in entities:
                entity_lower = entity.lower()
                if entity_lower not in self._entity_index:
                    self._entity_index[entity_lower] = []
                self._entity_index[entity_lower].append(category)
        
        for (entity1, entity2), rel in IMPLICIT_RELATIONSHIPS.items():
            e1_lower = entity1.lower()
            e2_lower = entity2.lower()
            if e1_lower not in self._entity_index:
                self._entity_index[e1_lower] = []
            if e2_lower not in self._entity_index:
                self._entity_index[e2_lower] = []
    
    async def search(
        self,
        query: str,
        mode: GraphSearchMode = GraphSearchMode.HYBRID,
        top_k: int = 10
    ) -> GraphSearchResult:
        """
        Perform graph-enhanced search.
        
        Args:
            query: Search query
            mode: Search mode (LOCAL, GLOBAL, HYBRID, NAIVE)
            top_k: Number of results to return
        
        Returns:
            GraphSearchResult with contexts and metadata
        """
        entities = self._extract_entities(query)
        logger.debug(f"Extracted entities: {entities}")
        
        contexts = []
        entities_found = list(entities)
        relationships_traversed = 0
        vector_score = 0.0
        graph_score = 0.0
        
        if mode == GraphSearchMode.NAIVE:
            vector_results = await self._vector_search(query, top_k)
            contexts = vector_results
            vector_score = 1.0
        
        elif mode == GraphSearchMode.LOCAL:
            for entity in entities:
                entity_context = await self._local_search(entity, depth=2)
                contexts.extend(entity_context.co_occurrence_context.split("\n\n"))
                entities_found.extend(entity_context.related_entities)
                relationships_traversed += len(entity_context.direct_relationships)
                graph_score = max(graph_score, entity_context.relevance_score)
            
            if not contexts:
                contexts = await self._vector_search(query, top_k)
                vector_score = 0.5
        
        elif mode == GraphSearchMode.GLOBAL:
            global_context = await self._global_search(query)
            contexts.append(global_context)
            
            vector_results = await self._vector_search(query, top_k // 2)
            contexts.extend(vector_results)
            vector_score = 0.5
            graph_score = 0.5
        
        else:
            for entity in entities[:3]:
                entity_context = await self._local_search(entity, depth=2)
                if entity_context.co_occurrence_context:
                    contexts.append(entity_context.co_occurrence_context)
                entities_found.extend(entity_context.related_entities)
                relationships_traversed += len(entity_context.direct_relationships)
                graph_score = max(graph_score, entity_context.relevance_score)
            
            vector_results = await self._vector_search(query, top_k)
            contexts.extend(vector_results)
            vector_score = 0.7
        
        contexts = self._deduplicate_contexts(contexts)
        
        combined_score = 0.4 * vector_score + 0.6 * graph_score if graph_score > 0 else vector_score
        
        return GraphSearchResult(
            query=query,
            mode=mode,
            contexts=contexts[:top_k],
            entities_found=list(set(entities_found)),
            relationships_traversed=relationships_traversed,
            vector_score=vector_score,
            graph_score=graph_score,
            combined_score=combined_score,
        )
    
    async def reason(
        self,
        query: str,
        max_hops: int = 3
    ) -> GraphSearchResult:
        """
        Perform multi-hop reasoning through the knowledge graph.
        
        This is useful for complex questions like:
        - "Why is PF1 better than AM for automotive applications?"
        - "What's the relationship between sheet thickness and machine selection?"
        
        Args:
            query: Reasoning query
            max_hops: Maximum hops through the graph
        
        Returns:
            GraphSearchResult with reasoning chain
        """
        entities = self._extract_entities(query)
        
        chain = ReasoningChain(entities_visited=list(entities))
        all_contexts = []
        
        for entity in entities:
            initial_context = await self._local_search(entity, depth=1)
            chain.steps.append({
                "hop": 0,
                "entity": entity,
                "found": initial_context.related_entities[:5],
                "context": initial_context.co_occurrence_context[:500]
            })
            all_contexts.append(initial_context.co_occurrence_context)
        
        current_entities = set(entities)
        for hop in range(1, max_hops):
            next_entities = set()
            
            for entity in current_entities:
                neighbors = await self._get_entity_neighbors(entity)
                for neighbor in neighbors:
                    if neighbor not in chain.entities_visited:
                        next_entities.add(neighbor)
                        chain.entities_visited.append(neighbor)
            
            for entity in list(next_entities)[:3]:
                hop_context = await self._local_search(entity, depth=1)
                chain.steps.append({
                    "hop": hop,
                    "entity": entity,
                    "found": hop_context.related_entities[:3],
                    "context": hop_context.co_occurrence_context[:300]
                })
                all_contexts.append(hop_context.co_occurrence_context)
            
            current_entities = next_entities
            
            if not current_entities:
                break
        
        chain.final_answer = await self._synthesize_reasoning(query, chain, all_contexts)
        chain.confidence = min(0.9, 0.3 * len(chain.steps))
        
        return GraphSearchResult(
            query=query,
            mode=GraphSearchMode.HYBRID,
            contexts=all_contexts,
            entities_found=chain.entities_visited,
            relationships_traversed=len(chain.steps),
            combined_score=chain.confidence,
            reasoning_chain=chain,
        )
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract known entities from text."""
        import re
        
        entities = []
        text_lower = text.lower()
        
        for entity in self._entity_index.keys():
            if entity in text_lower:
                entities.append(entity.upper() if len(entity) <= 4 else entity)
        
        model_patterns = [
            r'(PF1-[A-Z]-\d{4})',
            r'(PF2-[A-Z]?\d{4})',
            r'(AM[P]?-\d{4})',
            r'(IMG[S]?-\d{4})',
        ]
        for pattern in model_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend([m.upper() for m in matches])
        
        return list(set(entities))
    
    async def _vector_search(self, query: str, top_k: int = 10) -> List[str]:
        """Perform vector similarity search."""
        if self.unified_retriever:
            try:
                results = self.unified_retriever.search(query, top_k=top_k)
                return [r.text for r in results if hasattr(r, 'text')]
            except Exception as e:
                logger.warning(f"UnifiedRetriever search failed: {e}")
        
        if self.knowledge_engine:
            try:
                results = await self.knowledge_engine.search(
                    query, 
                    search_type=KESearchType.VECTOR,
                    top_k=top_k
                )
                return [item.text for item in results.items]
            except Exception as e:
                logger.warning(f"KnowledgeEngine search failed: {e}")
        
        return []
    
    async def _local_search(
        self,
        entity: str,
        depth: int = 2
    ) -> EntityContext:
        """
        Perform local search starting from an entity.
        
        Gathers context from:
        - Neo4j graph (if available) - real multi-hop traversal
        - Direct relationships from domain knowledge
        - Neighboring entities
        - Co-occurrence in documents
        """
        entity_lower = entity.lower()
        
        direct_relationships = []
        related_entities = []
        
        # Try Neo4j first for real graph traversal
        if self.neo4j_store:
            try:
                # Get related entities from Neo4j (multi-hop)
                neo4j_related = self.neo4j_store.get_related_entities(entity, depth=depth, limit=20)
                for item in neo4j_related:
                    related_entities.append(item["entity"])
                    for rel_type in item.get("relationship_types", []):
                        direct_relationships.append({
                            "type": rel_type,
                            "weight": 1.0 / (item["distance"] + 1),
                            "source": entity,
                            "target": item["entity"],
                        })
                
                # Get knowledge directly about this entity
                entity_knowledge = self.neo4j_store.get_entity_knowledge(entity)
                
                # Record access for dream mode learning
                if related_entities:
                    self.neo4j_store.record_access([entity] + related_entities[:5])
                
                logger.debug(f"Neo4j found {len(related_entities)} related entities for {entity}")
            except Exception as e:
                logger.warning(f"Neo4j lookup failed for {entity}: {e}")
        
        # Fallback to implicit relationships if Neo4j didn't find anything
        if not direct_relationships:
            for (e1, e2), rel in IMPLICIT_RELATIONSHIPS.items():
                if e1.lower() == entity_lower or e2.lower() == entity_lower:
                    direct_relationships.append({
                        "type": rel["type"],
                        "weight": rel["weight"],
                        "source": e1 if e1.lower() != entity_lower else e2,
                        "target": e2 if e1.lower() != entity_lower else e1,
                    })
            
            for rel in direct_relationships:
                target = rel["target"]
                if target.lower() != entity_lower:
                    related_entities.append(target)
        
        co_occurrence_context = ""
        if self.knowledge_engine:
            try:
                context = await self.knowledge_engine.get_entity_relationships(entity)
                if context:
                    related_entities.extend([
                        e["name"] for e in context.get("related_entities", [])
                        if "name" in e
                    ])
                    
                    search_result = await self.knowledge_engine.search(
                        f"information about {entity}",
                        search_type=KESearchType.VECTOR,
                        top_k=3
                    )
                    co_occurrence_context = "\n\n".join([
                        item.text for item in search_result.items
                    ])
            except Exception as e:
                logger.debug(f"Knowledge engine lookup failed for {entity}: {e}")
        
        if not co_occurrence_context:
            vector_results = await self._vector_search(entity, top_k=3)
            co_occurrence_context = "\n\n".join(vector_results)
        
        return EntityContext(
            entity_id=entity,
            entity_type=self._entity_index.get(entity_lower, ["UNKNOWN"])[0],
            direct_relationships=direct_relationships,
            related_entities=list(set(related_entities)),
            co_occurrence_context=co_occurrence_context,
            relevance_score=0.5 + 0.1 * len(direct_relationships),
            hop_distance=0,
        )
    
    async def _global_search(self, query: str) -> str:
        """
        Perform global search using high-level topic understanding.
        
        This provides a broader perspective than local entity search.
        """
        prompt = f"""Based on the query, provide a high-level summary of relevant knowledge about Machinecraft thermoforming machines.

Query: {query}

Consider:
- Machine series (PF1 for heavy gauge, AM for light gauge)
- Materials commonly processed (ABS, HIPS, PP, etc.)
- Applications (automotive, packaging, food)
- Key specifications (forming area, heater power, vacuum)

Provide a concise, informative summary."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a Machinecraft product expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Global search LLM call failed: {e}")
            return ""
    
    async def _get_entity_neighbors(self, entity: str) -> List[str]:
        """Get neighboring entities from the knowledge graph."""
        neighbors = set()
        
        entity_lower = entity.lower()
        for (e1, e2), rel in IMPLICIT_RELATIONSHIPS.items():
            if e1.lower() == entity_lower:
                neighbors.add(e2)
            elif e2.lower() == entity_lower:
                neighbors.add(e1)
        
        if self.knowledge_engine:
            try:
                context = await self.knowledge_engine.get_entity_relationships(entity)
                for related in context.get("related_entities", []):
                    if "name" in related:
                        neighbors.add(related["name"])
            except Exception:
                pass
        
        return list(neighbors)
    
    async def _synthesize_reasoning(
        self,
        query: str,
        chain: ReasoningChain,
        contexts: List[str]
    ) -> str:
        """Synthesize a final answer from reasoning chain."""
        context_text = "\n\n".join([c for c in contexts if c][:5])
        
        steps_text = "\n".join([
            f"Step {s['hop']}: Found {s['entity']} → related to {s['found'][:3]}"
            for s in chain.steps
        ])
        
        prompt = f"""Based on the following reasoning chain and context, answer the question.

Question: {query}

Reasoning Steps:
{steps_text}

Relevant Context:
{context_text}

Provide a clear, specific answer based on the evidence gathered."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a technical expert answering based on gathered evidence."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Reasoning synthesis failed: {e}")
            return "Unable to synthesize reasoning."
    
    def _deduplicate_contexts(self, contexts: List[str]) -> List[str]:
        """Remove duplicate or highly similar contexts."""
        seen_hashes = set()
        unique = []
        
        for context in contexts:
            if not context:
                continue
            content_hash = hashlib.md5(context[:200].encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(context)
        
        return unique


_retriever_instance: Optional[GraphRetriever] = None


def get_graph_retriever() -> GraphRetriever:
    """Get singleton graph retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = GraphRetriever()
    return _retriever_instance


async def search(
    query: str,
    mode: GraphSearchMode = GraphSearchMode.HYBRID,
    top_k: int = 10
) -> GraphSearchResult:
    """Convenience function for graph search."""
    return await get_graph_retriever().search(query, mode, top_k)


async def reason(query: str, max_hops: int = 3) -> GraphSearchResult:
    """Convenience function for multi-hop reasoning."""
    return await get_graph_retriever().reason(query, max_hops)


if __name__ == "__main__":
    import asyncio
    
    async def test_graph_retriever():
        print("Testing Graph Retriever\n" + "=" * 50)
        
        retriever = get_graph_retriever()
        
        print("\n1. Simple HYBRID search:")
        result = await retriever.search(
            "PF1 machines for automotive ABS applications",
            mode=GraphSearchMode.HYBRID
        )
        print(f"   Entities found: {result.entities_found}")
        print(f"   Relationships: {result.relationships_traversed}")
        print(f"   Combined score: {result.combined_score:.2f}")
        print(f"   Contexts: {len(result.contexts)}")
        
        print("\n2. LOCAL entity search:")
        result = await retriever.search(
            "PF1",
            mode=GraphSearchMode.LOCAL
        )
        print(f"   Related entities: {result.entities_found}")
        print(f"   Contexts: {len(result.contexts)}")
        
        print("\n3. Multi-hop REASONING:")
        result = await retriever.reason(
            "Why is PF1 better than AM for thick materials?",
            max_hops=2
        )
        if result.reasoning_chain:
            print(f"   Steps: {len(result.reasoning_chain.steps)}")
            print(f"   Entities visited: {result.reasoning_chain.entities_visited}")
            print(f"   Answer: {result.reasoning_chain.final_answer[:200]}...")
        
        print("\n✅ Graph Retriever test complete")
    
    asyncio.run(test_graph_retriever())
