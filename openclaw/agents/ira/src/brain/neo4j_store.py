#!/usr/bin/env python3
"""
NEO4J GRAPH STORE - Unified Graph Database Interface
=====================================================

Provides a single interface for all Neo4j operations in Ira:
- Knowledge ingestion (auto-sync from KnowledgeIngestor)
- Graph retrieval (multi-hop reasoning)
- Dream mode consolidation (relationship tuning)
- Query-time graph enhancement

Usage:
    from neo4j_store import Neo4jStore, get_neo4j_store
    
    store = get_neo4j_store()
    
    # Add knowledge
    store.add_knowledge(id, text, entity, knowledge_type, source_file, metadata)
    
    # Query relationships
    related = store.get_related_entities("PF1-C-3020", depth=2)
    
    # Multi-hop search
    results = store.search_with_relationships("automotive ABS machine", limit=10)
    
    # Dream mode operations
    store.strengthen_relationship(entity1, entity2, rel_type, factor=1.2)
    store.create_relationship(entity1, entity2, rel_type, strength=0.5)

Environment:
    NEO4J_URI: bolt://localhost:7687
    NEO4J_USER: neo4j
    NEO4J_PASSWORD: (set in .env)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


@dataclass
class GraphNode:
    """A node from Neo4j."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


@dataclass
class GraphRelationship:
    """A relationship from Neo4j."""
    source: str
    target: str
    rel_type: str
    properties: Dict[str, Any]


@dataclass
class GraphSearchResult:
    """Result from a graph-enhanced search."""
    entity: str
    knowledge_type: str
    text: str
    source_file: str
    related_entities: List[str]
    relationship_path: List[str]
    score: float


class Neo4jStore:
    """
    Unified Neo4j interface for Ira's knowledge graph.
    
    Features:
    - Auto-reconnect on connection loss
    - Fallback to JSON graph if Neo4j unavailable
    - Batch operations for performance
    - Query caching for common patterns
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self._driver = None
        self._connected = False
        
    def connect(self) -> bool:
        """Establish connection to Neo4j."""
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if Neo4j is available."""
        if not self._connected:
            return self.connect()
        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            return True
        except:
            self._connected = False
            return self.connect()
    
    # =========================================================================
    # KNOWLEDGE OPERATIONS
    # =========================================================================
    
    def add_knowledge(
        self,
        id: str,
        text: str,
        entity: str,
        knowledge_type: str,
        source_file: str,
        summary: str = "",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add a knowledge item to the graph."""
        if not self.is_connected():
            return False
        
        try:
            with self._driver.session() as session:
                session.run("""
                    MERGE (k:Knowledge {id: $id})
                    SET k.text = $text,
                        k.entity = $entity,
                        k.knowledge_type = $knowledge_type,
                        k.source_file = $source_file,
                        k.summary = $summary,
                        k.updated_at = datetime()
                """, {
                    "id": id,
                    "text": text[:5000],
                    "entity": entity,
                    "knowledge_type": knowledge_type,
                    "source_file": source_file,
                    "summary": summary[:2000] if summary else "",
                })
                
                if entity:
                    session.run("""
                        MERGE (e:Entity {name: $name})
                        WITH e
                        MATCH (k:Knowledge {id: $kid})
                        MERGE (k)-[:ABOUT]->(e)
                    """, {"name": entity, "kid": id})
                
                if source_file:
                    session.run("""
                        MERGE (s:Source {path: $path})
                        WITH s
                        MATCH (k:Knowledge {id: $kid})
                        MERGE (k)-[:FROM_SOURCE]->(s)
                    """, {"path": source_file, "kid": id})
                
            return True
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            return False
    
    def add_knowledge_batch(self, items: List[Dict[str, Any]]) -> int:
        """Add multiple knowledge items efficiently."""
        if not self.is_connected():
            return 0
        
        added = 0
        try:
            with self._driver.session() as session:
                for item in items:
                    session.run("""
                        MERGE (k:Knowledge {id: $id})
                        SET k.text = $text,
                            k.entity = $entity,
                            k.knowledge_type = $knowledge_type,
                            k.source_file = $source_file,
                            k.summary = $summary,
                            k.updated_at = datetime()
                        
                        WITH k
                        FOREACH (e IN CASE WHEN $entity <> '' THEN [1] ELSE [] END |
                            MERGE (ent:Entity {name: $entity})
                            MERGE (k)-[:ABOUT]->(ent)
                        )
                        
                        WITH k
                        FOREACH (s IN CASE WHEN $source_file <> '' THEN [1] ELSE [] END |
                            MERGE (src:Source {path: $source_file})
                            MERGE (k)-[:FROM_SOURCE]->(src)
                        )
                    """, {
                        "id": item.get("id", ""),
                        "text": item.get("text", "")[:5000],
                        "entity": item.get("entity", ""),
                        "knowledge_type": item.get("knowledge_type", "general"),
                        "source_file": item.get("source_file", ""),
                        "summary": item.get("summary", "")[:2000],
                    })
                    added += 1
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
        
        return added
    
    # =========================================================================
    # RELATIONSHIP OPERATIONS
    # =========================================================================
    
    def create_relationship(
        self,
        source_entity: str,
        target_entity: str,
        rel_type: str,
        strength: float = 0.5,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Create or update a relationship between entities."""
        if not self.is_connected():
            return False

        safe_rel_type = rel_type.upper().replace(' ', '_').replace('-', '_')
        clamped = max(0.0, min(1.0, strength))

        try:
            with self._driver.session() as session:
                session.run(f"""
                    MERGE (source:Entity {{name: $source}})
                    MERGE (target:Entity {{name: $target}})
                    MERGE (source)-[r:{safe_rel_type}]->(target)
                    SET r.strength = $strength,
                        r.updated_at = datetime(),
                        r.last_accessed = datetime()
                """, {
                    "source": source_entity,
                    "target": target_entity,
                    "strength": clamped,
                })
            return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    def strengthen_relationship(
        self,
        source_entity: str,
        target_entity: str,
        rel_type: str,
        factor: float = 1.1
    ) -> bool:
        """Strengthen an existing relationship (dream mode learning).

        Strength is clamped to [0, 1] to keep the filter in
        expand_query_with_graph (r.strength > 0.5) meaningful.
        """
        if not self.is_connected():
            return False

        safe_rel_type = rel_type.upper().replace(' ', '_').replace('-', '_')

        try:
            with self._driver.session() as session:
                session.run(f"""
                    MATCH (source:Entity {{name: $source}})-[r:{safe_rel_type}]->(target:Entity {{name: $target}})
                    SET r.strength = CASE
                            WHEN COALESCE(r.strength, 0.5) * $factor > 1.0 THEN 1.0
                            WHEN COALESCE(r.strength, 0.5) * $factor < 0.0 THEN 0.0
                            ELSE COALESCE(r.strength, 0.5) * $factor
                        END,
                        r.access_count = COALESCE(r.access_count, 0) + 1,
                        r.last_accessed = datetime()
                """, {
                    "source": source_entity,
                    "target": target_entity,
                    "factor": factor,
                })
            return True
        except Exception as e:
            logger.error(f"Failed to strengthen relationship: {e}")
            return False
    
    def weaken_relationship(
        self,
        source_entity: str,
        target_entity: str,
        rel_type: str,
        factor: float = 0.9
    ) -> bool:
        """Weaken an existing relationship (decay unused connections)."""
        return self.strengthen_relationship(source_entity, target_entity, rel_type, factor)
    
    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================
    
    def get_related_entities(
        self,
        entity: str,
        depth: int = 2,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get entities related to a given entity up to N hops."""
        if not self.is_connected():
            return []
        
        try:
            with self._driver.session() as session:
                result = session.run(f"""
                    MATCH path = (e:Entity {{name: $entity}})-[*1..{depth}]-(related:Entity)
                    WHERE e <> related
                    WITH related, 
                         min(length(path)) as distance,
                         collect(distinct type(relationships(path)[0])) as rel_types
                    RETURN related.name as entity, 
                           distance,
                           rel_types
                    ORDER BY distance, related.name
                    LIMIT $limit
                """, {"entity": entity, "limit": limit})
                
                return [
                    {
                        "entity": record["entity"],
                        "distance": record["distance"],
                        "relationship_types": record["rel_types"],
                    }
                    for record in result
                ]
        except Exception as e:
            logger.error(f"Failed to get related entities: {e}")
            return []
    
    def get_entity_knowledge(self, entity: str) -> List[Dict[str, Any]]:
        """Get all knowledge about an entity.
        
        Uses exact match first, then prefix match for series names
        (e.g. 'PF1' matches 'PF1-C-3020', 'PF1-X-1210', etc.)
        """
        if not self.is_connected():
            return []

        try:
            with self._driver.session() as session:
                # Exact match first
                result = session.run("""
                    MATCH (k:Knowledge)-[:ABOUT]->(e:Entity {name: $entity})
                    RETURN k.id as id,
                           k.text as text,
                           k.knowledge_type as knowledge_type,
                           k.source_file as source_file,
                           k.summary as summary
                    ORDER BY k.knowledge_type
                """, {"entity": entity})

                records = [dict(record) for record in result]

                # If few results and entity looks like a series name, also do prefix match
                if len(records) < 3 and len(entity) <= 4:
                    prefix_result = session.run("""
                        MATCH (k:Knowledge)-[:ABOUT]->(e:Entity)
                        WHERE e.name STARTS WITH $prefix
                          AND e.name <> $entity
                        RETURN k.id as id,
                               k.text as text,
                               k.knowledge_type as knowledge_type,
                               k.source_file as source_file,
                               k.summary as summary
                        ORDER BY k.knowledge_type
                        LIMIT 10
                    """, {"prefix": entity, "entity": entity})
                    records.extend(dict(r) for r in prefix_result)

                return records
        except Exception as e:
            logger.error(f"Failed to get entity knowledge: {e}")
            return []
    
    def find_path(
        self,
        from_entity: str,
        to_entity: str,
        max_depth: int = 4
    ) -> List[Dict[str, Any]]:
        """Find shortest path between two entities."""
        if not self.is_connected():
            return []
        
        try:
            with self._driver.session() as session:
                result = session.run(f"""
                    MATCH path = shortestPath(
                        (from:Entity {{name: $from}})-[*1..{max_depth}]-(to:Entity {{name: $to}})
                    )
                    RETURN [n IN nodes(path) | n.name] as nodes,
                           [r IN relationships(path) | type(r)] as relationships,
                           length(path) as distance
                """, {"from": from_entity, "to": to_entity})
                
                record = result.single()
                if record:
                    return {
                        "nodes": record["nodes"],
                        "relationships": record["relationships"],
                        "distance": record["distance"],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return None
    
    def search_by_relationship(
        self,
        entity: str,
        rel_type: str,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Find entities connected by a specific relationship type."""
        if not self.is_connected():
            return []
        
        safe_rel_type = rel_type.upper().replace(' ', '_').replace('-', '_')
        
        try:
            with self._driver.session() as session:
                if direction == "outgoing":
                    query = f"MATCH (e:Entity {{name: $entity}})-[r:{safe_rel_type}]->(connected:Entity)"
                elif direction == "incoming":
                    query = f"MATCH (e:Entity {{name: $entity}})<-[r:{safe_rel_type}]-(connected:Entity)"
                else:
                    query = f"MATCH (e:Entity {{name: $entity}})-[r:{safe_rel_type}]-(connected:Entity)"
                
                query += """
                    RETURN connected.name as entity,
                           r.strength as strength
                    ORDER BY r.strength DESC
                """
                
                result = session.run(query, {"entity": entity})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Failed to search by relationship: {e}")
            return []
    
    # =========================================================================
    # GRAPH-ENHANCED SEARCH (for retriever integration)
    # =========================================================================
    
    def expand_query_with_graph(
        self,
        entities: List[str],
        depth: int = 1
    ) -> List[str]:
        """Expand a list of entities with their graph neighbors."""
        if not self.is_connected():
            return entities
        
        expanded = set(entities)
        
        try:
            with self._driver.session() as session:
                for entity in entities:
                    result = session.run(f"""
                        MATCH (e:Entity {{name: $entity}})-[r]->(related:Entity)
                        WHERE r.strength > 0.5
                        RETURN related.name as name
                        ORDER BY r.strength DESC
                        LIMIT 5
                    """, {"entity": entity})
                    
                    for record in result:
                        expanded.add(record["name"])
        except Exception as e:
            logger.error(f"Failed to expand query: {e}")
        
        return list(expanded)
    
    def get_entity_context(self, entity: str) -> Dict[str, Any]:
        """Get rich context for an entity (for RAG enhancement)."""
        if not self.is_connected():
            return {}
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity {name: $entity})
                    OPTIONAL MATCH (e)<-[:ABOUT]-(k:Knowledge)
                    OPTIONAL MATCH (e)-[r]-(related:Entity)
                    WITH e,
                         collect(DISTINCT k.knowledge_type) as knowledge_types,
                         collect(DISTINCT {entity: related.name, rel: type(r)}) as connections
                    RETURN e.name as entity,
                           knowledge_types,
                           connections[0..10] as top_connections
                """, {"entity": entity})
                
                record = result.single()
                if record:
                    return dict(record)
                return {}
        except Exception as e:
            logger.error(f"Failed to get entity context: {e}")
            return {}
    
    # =========================================================================
    # DREAM MODE OPERATIONS
    # =========================================================================
    
    def decay_unused_relationships(self, days_threshold: int = 7, decay_factor: float = 0.95):
        """Decay relationships that haven't been accessed recently.

        Also handles legacy edges that were created before last_accessed was
        set — those are treated as stale and decayed too.
        """
        if not self.is_connected():
            return

        try:
            with self._driver.session() as session:
                # Decay edges that haven't been accessed within the threshold
                result1 = session.run("""
                    MATCH ()-[r]->()
                    WHERE r.last_accessed IS NOT NULL
                      AND r.last_accessed < datetime() - duration({days: $days})
                    SET r.strength = CASE
                            WHEN r.strength * $factor < 0.01 THEN 0.0
                            ELSE r.strength * $factor
                        END
                    RETURN count(r) as decayed
                """, {"days": days_threshold, "factor": decay_factor})
                decayed_recent = result1.single()["decayed"]

                # Decay legacy edges that never had last_accessed set
                result2 = session.run("""
                    MATCH ()-[r]->()
                    WHERE r.last_accessed IS NULL
                      AND r.strength IS NOT NULL
                      AND r.strength > 0.0
                    SET r.strength = CASE
                            WHEN r.strength * $factor < 0.01 THEN 0.0
                            ELSE r.strength * $factor
                        END,
                        r.last_accessed = datetime()
                    RETURN count(r) as decayed
                """, {"factor": decay_factor})
                decayed_legacy = result2.single()["decayed"]

                logger.info("Decayed relationships: %d recent (>%d days) + %d legacy (no last_accessed)",
                            decayed_recent, days_threshold, decayed_legacy)
        except Exception as e:
            logger.error(f"Failed to decay relationships: {e}")
    
    def record_access(self, entities: List[str]):
        """Record that certain entities were accessed together (for learning)."""
        if not self.is_connected() or len(entities) < 2:
            return
        
        try:
            with self._driver.session() as session:
                for i, e1 in enumerate(entities):
                    for e2 in entities[i+1:]:
                        session.run("""
                            MATCH (e1:Entity {name: $e1})
                            MATCH (e2:Entity {name: $e2})
                            MERGE (e1)-[r:CO_ACCESSED]->(e2)
                            SET r.count = COALESCE(r.count, 0) + 1,
                                r.last_accessed = datetime()
                        """, {"e1": e1, "e2": e2})
        except Exception as e:
            logger.error(f"Failed to record access: {e}")
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        if not self.is_connected():
            return {}
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (k:Knowledge) WITH count(k) as knowledge_count
                    MATCH (e:Entity) WITH knowledge_count, count(e) as entity_count
                    MATCH (s:Source) WITH knowledge_count, entity_count, count(s) as source_count
                    MATCH (c:Cluster) WITH knowledge_count, entity_count, source_count, count(c) as cluster_count
                    MATCH ()-[r]->() WITH knowledge_count, entity_count, source_count, cluster_count, count(r) as rel_count
                    RETURN knowledge_count, entity_count, source_count, cluster_count, rel_count
                """)
                
                record = result.single()
                if record:
                    return {
                        "knowledge_items": record["knowledge_count"],
                        "entities": record["entity_count"],
                        "sources": record["source_count"],
                        "clusters": record["cluster_count"],
                        "relationships": record["rel_count"],
                    }
                return {}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Singleton instance
_neo4j_store: Optional[Neo4jStore] = None


def get_neo4j_store() -> Neo4jStore:
    """Get the singleton Neo4j store instance."""
    global _neo4j_store
    if _neo4j_store is None:
        _neo4j_store = Neo4jStore()
        _neo4j_store.connect()
    return _neo4j_store


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j Store CLI")
    parser.add_argument("--stats", action="store_true", help="Show graph statistics")
    parser.add_argument("--related", type=str, help="Find entities related to given entity")
    parser.add_argument("--path", nargs=2, help="Find path between two entities")
    parser.add_argument("--depth", type=int, default=2, help="Search depth")
    
    args = parser.parse_args()
    
    store = get_neo4j_store()
    
    if not store.is_connected():
        print("Failed to connect to Neo4j")
        sys.exit(1)
    
    if args.stats:
        stats = store.get_graph_statistics()
        print("\n=== Neo4j Knowledge Graph Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif args.related:
        related = store.get_related_entities(args.related, depth=args.depth)
        print(f"\n=== Entities related to '{args.related}' ===")
        for item in related[:20]:
            print(f"  {item['entity']} (distance: {item['distance']}, via: {item['relationship_types']})")
    
    elif args.path:
        path = store.find_path(args.path[0], args.path[1])
        if path:
            print(f"\n=== Path from '{args.path[0]}' to '{args.path[1]}' ===")
            print(f"  Nodes: {' -> '.join(path['nodes'])}")
            print(f"  Relationships: {path['relationships']}")
            print(f"  Distance: {path['distance']}")
        else:
            print("No path found")
    
    else:
        parser.print_help()
    
    store.close()
