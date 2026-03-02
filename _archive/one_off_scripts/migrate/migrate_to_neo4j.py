#!/usr/bin/env python3
"""
Migrate Ira Knowledge Graph to Neo4j

This script:
1. Reads existing knowledge graph from JSON
2. Creates nodes and relationships in Neo4j
3. Sets up proper indexes for fast queries

Usage:
    python scripts/migrate_to_neo4j.py

Prerequisites:
    - Neo4j running on localhost:7687
    - pip install neo4j
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Neo4j connection
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "ira_knowledge_graph")

PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
GRAPH_FILE = KNOWLEDGE_DIR / "knowledge_graph.json"
CLUSTERS_FILE = KNOWLEDGE_DIR / "clusters.json"


def connect_neo4j():
    """Connect to Neo4j database."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return driver


def setup_constraints(driver):
    """Set up Neo4j constraints and indexes."""
    with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT knowledge_node_id IF NOT EXISTS FOR (k:Knowledge) REQUIRE k.id IS UNIQUE",
            "CREATE CONSTRAINT cluster_id IF NOT EXISTS FOR (c:Cluster) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT source_path IF NOT EXISTS FOR (s:Source) REQUIRE s.path IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX knowledge_type IF NOT EXISTS FOR (k:Knowledge) ON (k.knowledge_type)",
            "CREATE INDEX knowledge_entity IF NOT EXISTS FOR (k:Knowledge) ON (k.entity)",
            "CREATE FULLTEXT INDEX knowledge_text IF NOT EXISTS FOR (k:Knowledge) ON EACH [k.text, k.summary]",
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Warning: {e}")
        
        for index in indexes:
            try:
                session.run(index)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Warning: {e}")
        
        print("✓ Constraints and indexes created")


def load_graph_data():
    """Load existing knowledge graph data."""
    nodes = {}
    edges = []
    clusters = []
    
    if GRAPH_FILE.exists():
        data = json.loads(GRAPH_FILE.read_text())
        nodes = data.get('nodes', {})
        edges = data.get('edges', [])
    
    if CLUSTERS_FILE.exists():
        clusters_data = json.loads(CLUSTERS_FILE.read_text())
        if isinstance(clusters_data, list):
            clusters = clusters_data
        elif isinstance(clusters_data, dict):
            inner = clusters_data.get('clusters', clusters_data)
            if isinstance(inner, list):
                clusters = inner
            elif isinstance(inner, dict):
                clusters = list(inner.values())
    
    return nodes, edges, clusters


def migrate_nodes(driver, nodes):
    """Migrate knowledge nodes to Neo4j."""
    print(f"\nMigrating {len(nodes)} knowledge nodes...")
    
    # Handle both list and dict formats
    if isinstance(nodes, dict):
        node_list = [(nid, ndata) for nid, ndata in nodes.items()]
    else:
        node_list = [(n.get('id', f'node_{i}'), n) for i, n in enumerate(nodes)]
    
    with driver.session() as session:
        # Batch insert for performance
        batch_size = 100
        
        for i in range(0, len(node_list), batch_size):
            batch = node_list[i:i + batch_size]
            
            for node_id, node_data in batch:
                # Create Knowledge node
                query = """
                MERGE (k:Knowledge {id: $id})
                SET k.text = $text,
                    k.entity = $entity,
                    k.knowledge_type = $knowledge_type,
                    k.source_file = $source_file,
                    k.summary = $summary,
                    k.topic = $topic,
                    k.cluster_id = $cluster_id
                """
                
                session.run(query, {
                    "id": node_id,
                    "text": node_data.get('text', '')[:5000],  # Truncate long text
                    "entity": node_data.get('entity', ''),
                    "knowledge_type": node_data.get('knowledge_type', 'general'),
                    "source_file": node_data.get('source_file', ''),
                    "summary": node_data.get('summary', '')[:2000],
                    "topic": node_data.get('topic', ''),
                    "cluster_id": node_data.get('cluster_id', ''),
                })
                
                # Create Entity node and relationship
                entity = node_data.get('entity', '')
                if entity:
                    session.run("""
                        MERGE (e:Entity {name: $name})
                        WITH e
                        MATCH (k:Knowledge {id: $kid})
                        MERGE (k)-[:ABOUT]->(e)
                    """, {"name": entity, "kid": node_id})
                
                # Create Source node and relationship
                source = node_data.get('source_file', '')
                if source:
                    session.run("""
                        MERGE (s:Source {path: $path})
                        WITH s
                        MATCH (k:Knowledge {id: $kid})
                        MERGE (k)-[:FROM_SOURCE]->(s)
                    """, {"path": source, "kid": node_id})
            
            print(f"  Migrated {min(i + batch_size, len(node_list))}/{len(node_list)} nodes")
    
    print(f"✓ Migrated {len(nodes)} knowledge nodes")


def migrate_edges(driver, edges: List[Dict[str, Any]]):
    """Migrate relationships to Neo4j.
    
    Note: Edge source_id/target_id are entity names, not node IDs.
    We create relationships between Entity nodes.
    """
    print(f"\nMigrating {len(edges)} relationships...")
    
    # Group edges by relationship type for batch processing
    edges_by_type = defaultdict(list)
    for edge in edges:
        rel_type = edge.get('relationship_type', 'RELATED_TO')
        edges_by_type[rel_type].append(edge)
    
    created_count = 0
    with driver.session() as session:
        for rel_type, type_edges in edges_by_type.items():
            # Sanitize relationship type for Neo4j
            safe_rel_type = rel_type.upper().replace(' ', '_').replace('-', '_')
            
            batch_size = 500
            type_created = 0
            for i in range(0, len(type_edges), batch_size):
                batch = type_edges[i:i + batch_size]
                
                for edge in batch:
                    source_name = edge.get('source_id', '')
                    target_name = edge.get('target_id', '')
                    strength = edge.get('strength', 0.5)
                    
                    if source_name and target_name:
                        # Create Entity nodes if they don't exist and link them
                        query = f"""
                        MERGE (source:Entity {{name: $source_name}})
                        MERGE (target:Entity {{name: $target_name}})
                        MERGE (source)-[r:{safe_rel_type}]->(target)
                        SET r.strength = $strength
                        RETURN count(r) as created
                        """
                        try:
                            result = session.run(query, {
                                "source_name": source_name,
                                "target_name": target_name,
                                "strength": strength,
                            })
                            type_created += 1
                        except Exception as e:
                            pass  # Skip invalid relationships
            
            created_count += type_created
            print(f"  {safe_rel_type}: {type_created} relationships")
    
    print(f"✓ Created {created_count} entity relationships")


def migrate_clusters(driver, clusters: List[Dict[str, Any]]):
    """Migrate clusters to Neo4j."""
    print(f"\nMigrating {len(clusters)} clusters...")
    
    with driver.session() as session:
        for i, cluster in enumerate(clusters):
            cluster_id = cluster.get('id', f'cluster_{i}')
            name = cluster.get('name', f'Cluster {i}')
            topic = cluster.get('topic', '')
            node_ids = cluster.get('node_ids', cluster.get('items', cluster.get('item_ids', [])))
            
            # Create Cluster node
            session.run("""
                MERGE (c:Cluster {id: $id})
                SET c.name = $name,
                    c.topic = $topic,
                    c.size = $size
            """, {
                "id": cluster_id,
                "name": name,
                "topic": topic,
                "size": len(node_ids),
            })
            
            # Link knowledge nodes to cluster
            for node_id in node_ids:
                session.run("""
                    MATCH (k:Knowledge {id: $kid})
                    MATCH (c:Cluster {id: $cid})
                    MERGE (k)-[:IN_CLUSTER]->(c)
                """, {"kid": node_id, "cid": cluster_id})
    
    print(f"✓ Migrated {len(clusters)} clusters")


def create_derived_relationships(driver):
    """Create additional derived relationships."""
    print("\nCreating derived relationships...")
    
    with driver.session() as session:
        # Connect entities that appear together
        session.run("""
            MATCH (k1:Knowledge)-[:ABOUT]->(e1:Entity)
            MATCH (k2:Knowledge)-[:ABOUT]->(e2:Entity)
            WHERE k1 <> k2 AND e1 <> e2
            AND (k1)-[:SAME_SOURCE|SAME_CLUSTER]-(k2)
            MERGE (e1)-[:CO_OCCURS_WITH]->(e2)
        """)
        
        # Create machine hierarchy (if PF1, FCS, etc. patterns exist)
        session.run("""
            MATCH (e1:Entity), (e2:Entity)
            WHERE e1.name STARTS WITH 'PF1' AND e2.name = 'PF1'
            AND e1 <> e2
            MERGE (e1)-[:VARIANT_OF]->(e2)
        """)
        
        session.run("""
            MATCH (e1:Entity), (e2:Entity)
            WHERE e1.name STARTS WITH 'FCS' AND e2.name = 'FCS'
            AND e1 <> e2
            MERGE (e1)-[:VARIANT_OF]->(e2)
        """)
    
    print("✓ Created derived relationships")


def print_graph_stats(driver):
    """Print statistics about the migrated graph."""
    print("\n" + "=" * 60)
    print("NEO4J KNOWLEDGE GRAPH STATISTICS")
    print("=" * 60)
    
    with driver.session() as session:
        # Node counts
        result = session.run("MATCH (k:Knowledge) RETURN count(k) as count")
        knowledge_count = result.single()["count"]
        
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        entity_count = result.single()["count"]
        
        result = session.run("MATCH (s:Source) RETURN count(s) as count")
        source_count = result.single()["count"]
        
        result = session.run("MATCH (c:Cluster) RETURN count(c) as count")
        cluster_count = result.single()["count"]
        
        # Relationship counts
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        
        print(f"\nNodes:")
        print(f"  Knowledge items: {knowledge_count}")
        print(f"  Entities: {entity_count}")
        print(f"  Sources: {source_count}")
        print(f"  Clusters: {cluster_count}")
        print(f"\nRelationships: {rel_count}")
        
        # Top entities
        result = session.run("""
            MATCH (e:Entity)<-[:ABOUT]-(k:Knowledge)
            RETURN e.name as entity, count(k) as knowledge_count
            ORDER BY knowledge_count DESC
            LIMIT 10
        """)
        
        print("\nTop Entities by Knowledge Count:")
        for record in result:
            if record["entity"]:
                print(f"  {record['entity']}: {record['knowledge_count']}")
        
        # Relationship type distribution
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\nRelationship Types:")
        for record in result:
            print(f"  {record['rel_type']}: {record['count']}")


def main():
    print("=" * 60)
    print("Ira Knowledge Graph -> Neo4j Migration")
    print("=" * 60)
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")
    
    try:
        driver = connect_neo4j()
        driver.verify_connectivity()
        print("✓ Connected to Neo4j")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure Neo4j is running:")
        print("  docker-compose up -d neo4j")
        sys.exit(1)
    
    try:
        # Load existing data
        print("\nLoading existing knowledge graph...")
        nodes, edges, clusters = load_graph_data()
        print(f"  Nodes: {len(nodes)}")
        print(f"  Edges: {len(edges)}")
        print(f"  Clusters: {len(clusters)}")
        
        # Setup database
        setup_constraints(driver)
        
        # Migrate data
        migrate_nodes(driver, nodes)
        migrate_edges(driver, edges)
        migrate_clusters(driver, clusters)
        
        # Create derived relationships
        create_derived_relationships(driver)
        
        # Print stats
        print_graph_stats(driver)
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)
        print("\nAccess Neo4j Browser at: http://localhost:7474")
        print("Login: neo4j / ira_knowledge_graph")
        print("\nTry these Cypher queries:")
        print("  MATCH (k:Knowledge) RETURN k LIMIT 25")
        print("  MATCH (e:Entity)<-[:ABOUT]-(k) RETURN e, k LIMIT 50")
        print("  MATCH path = (k1:Knowledge)-[*1..2]-(k2:Knowledge) RETURN path LIMIT 100")
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()
